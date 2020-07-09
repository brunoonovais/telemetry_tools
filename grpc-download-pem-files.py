# Author's Email: brusilva@cisco.com
# Author's Name: Bruno Novais

import paramiko
import concurrent.futures
import datetime
import argparse
import json
from scp import SCPClient
from typing import List, Dict, Set
import traceback

def scp_pem_file(other_args):
    client = paramiko.client.SSHClient()
    client.connect(other_args['ip'],
                   username=other_args['credentials']['username'],
                   password=other_args['credentials']['password'],
                   look_for_keys=False)
    try:
        scp_client = SCPClient(client.get_transport())
        scp_client.get(other_args["pem_file"], f"{other_args['pem_file_dir']}/{other_args['hostname']}_{other_args['mgmt_ip']}.pem")
        print(f"{other_args['pem_file_dir']}/{other_args['hostname']}_{other_args['mgmt_ip']}.pem")
    except Exception as e:
        print(f'# Error downloading PEM file for {other_args["ip"]}')

def download_pem(params):

    print(f'Process starting for {params["ip"]}')

    try:
        ip = params['ip']
        credentials={'username': params["username"], 'password': params["password"]}
        print(credentials)
        now = datetime.datetime.now()
        today = now.strftime('%Y%m%d%_H%M%S')
        pem_file_dir = params['dir']
        pem_file = '/misc/config/grpc/ems.pem'

        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, **credentials)
        stdin, stdout, stderr = client.exec_command('show run hostname')
        hostname = stdout.readlines()[3].split(' ')[1].split('\n')[0].strip()
        client.close()

        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, **credentials)
        stdin, stdout, stderr = client.exec_command('show platform | in Active')
        active_rp = stdout.readlines()[3].split('/')[1]
        client.close()

        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, **credentials)
        stdin, stdout, stderr = client.exec_command(f'show run interface Mgmt0/{active_rp}/CPU0/0 | include "ipv4 address"')
        mgmt_ip = stdout.readlines()[3].split(' ')[3]
        client.close()

        other_args: Dict = {}
        other_args['ip']:          str = ip
        other_args['mgmt_ip']:     str = mgmt_ip
        other_args['hostname']:    str = hostname
        other_args['credentials']: str = credentials
        other_args['today']            = today
        other_args['pem_file']         = pem_file
        other_args['pem_file_dir']     = pem_file_dir

        scp_pem_file(other_args)

    except Exception as e:
        traceback.print_exc()
        print(f'Failed to download PEM file for {h}. Exception:\n{e}')

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", '-d', type=str, help="Directory to download the PEM files")
    parser.add_argument("--names", '-n', type=str, help="Hosts in format \"ip-1 ip-2 ip-3 ...\"")
    parser.add_argument("--username", '-u', type=str, default="root", help="Username. Default is root")
    parser.add_argument("--password", '-p', type=str, default="lablab", help="Password. Default is lablab")
    arguments = parser.parse_args()
    dir:      str = arguments.dir
    hosts:    str = arguments.names
    username: str = arguments.username
    password: str = arguments.password

    if dir == None:
        print(f'Please provide the directory to download the PEM file(s)')
        exit(1)
    if hosts == None:
        print(f'Please provide at least one ip to download the PEM file')
        exit(2)

    params: List = []
    params_host: Dict = dict()
    for host in hosts.split(' '):
        params_host[host]: Dict = dict()
        params_host[host]['ip'] = host
        params_host[host]['dir']      = dir
        params_host[host]['username'] = username
        params_host[host]['password'] = password
        params.append(params_host[host])

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(hosts)) as executor:
        executor.map(download_pem, params)

if __name__ == '__main__':
    main()

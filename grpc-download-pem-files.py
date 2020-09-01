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
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f'{other_args["ip"]}')
    client.connect(other_args['ip'],
                   port=22,
                   username=other_args['credentials']['username'],
                   password=other_args['credentials']['password'],
                   look_for_keys=False,
                   allow_agent=False,
                   timeout=20)
    #print(f'client for {other_args["hostname"]} == {client}')
    try:
        scp_client = SCPClient(client.get_transport())
        scp_client.get(other_args["pem_file"], f"{other_args['pem_file_dir']}/{other_args['hostname']}_{other_args['mgmt_ip']}.pem")
        print(f"{other_args['pem_file_dir']}/{other_args['hostname']}_{other_args['mgmt_ip']}.pem")
    except Exception as e:
        print(f'# Error downloading PEM file for {other_args["ip"]}')
        print(traceback.print_exc())

def download_pem(params):

    print(f'Process starting for {params["ip"]}')

    try:
        # initial variables
        ip = params['ip']
        credentials={'username': params["username"], 'password': params["password"], "look_for_keys": False, "allow_agent": False}
        print(credentials)
        now = datetime.datetime.now()
        today = now.strftime('%Y%m%d%_H%M%S')
        pem_file_dir = params['dir']
        pem_file = '/misc/config/grpc/ems.pem'

        # grab hostname
        client = paramiko.client.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, **credentials)
        stdin, stdout, stderr = client.exec_command('show run hostname')
        hostname = stdout.readlines()[3].split(' ')[1].split('\n')[0].strip()
        client.close()

        # grab active rp for the pem filename
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, **credentials)
        stdin, stdout, stderr = client.exec_command('show platform | in Active')
        active_rp = stdout.readlines()[3].split('/')[1]
        client.close()

        # grab ipv4 mgmt ip for active
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, **credentials)
        stdin, stdout, stderr = client.exec_command(f'show run interface Mgmt0/{active_rp}/CPU0/0 | include "ipv4 address"')
        mgmt_ip = stdout.readlines()[3].split(' ')[3]
        client.close()

        # putting all variables before calling out the grab_pem_file func
        other_args: Dict = {}
        other_args['ip']:          str = ip
        other_args['mgmt_ip']:     str = mgmt_ip
        other_args['hostname']:    str = hostname
        other_args['credentials']: str = credentials
        other_args['today']            = today
        other_args['pem_file']         = pem_file
        other_args['pem_file_dir']     = pem_file_dir

        #print(json.dumps(other_args, indent=4))
        # scp file from router to pem_file_dir
        scp_pem_file(other_args)

    except Exception as e:
        traceback.print_exc()
        print(f'Failed to download PEM file for {h}. Exception:\n{e}')

def main():

    #### Argparse block ####
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", '-d', type=str, help="Directory to download the PEM files")
    parser.add_argument("--names", '-n', type=str, help="Hosts in format \"ip-1 ip-2 ip-3 ...\"")
    parser.add_argument("--username", '-u', type=str, default="root", help="Username. Default is root")
    parser.add_argument("--password", '-p', type=str, default="lablab", help="Password. Default is lablab")
    arguments = parser.parse_args()
    #### End of Argparse block ####

    # grabbing all variables from arguments
    dir:      str = arguments.dir
    hosts:    str = arguments.names
    username: str = arguments.username
    password: str = arguments.password

    # if no dir is provided, exit
    if dir == None:
        print(f'Please provide the directory to download the PEM file(s)')
        exit(1)
    # if no hosts are provided, exit
    if hosts == None:
        print(f'Please provide at least one ip to download the PEM file')
        exit(2)

    # provide dictionary with arguments
    params: List = []
    params_host: Dict = dict()
    for host in hosts.split(' '):
        params_host[host]: Dict = dict()
        params_host[host]['ip'] = host
        params_host[host]['dir']      = dir
        params_host[host]['username'] = username
        params_host[host]['password'] = password
        params.append(params_host[host])

    #print(json.dumps(params, indent=4))

    #hosts = ['10.8.70.1', '10.8.70.2', '10.8.70.3', '10.8.70.4', '10.8.70.5', '10.8.70.6', '10.8.70.7', '10.8.70.8',
    #         '10.8.70.9', '10.8.70.10']

    #print(hosts)

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(hosts)) as executor:
        executor.map(download_pem, params)

if __name__ == '__main__':
    main()

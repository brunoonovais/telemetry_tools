import json
import argparse
import glob
import time
import sys
import concurrent.futures
from gnmi_manager import GNMIManager
from responses import ParsedSetRequest
from typing import List, Set, Dict, Union

def read_file(file) -> str:
    try:
        with open(file, "r") as fp:
            return fp.read()
    except Exception as e:
        print(f'Exception raised when reading {file}. Exception:\n{e}')

def apply_config(gnmi_host: GNMIManager, config_to_apply: Dict, operation: str, hostname: str) -> None:

    set_request = ParsedSetRequest(config_to_apply)
    print(f'set_request = {set_request}')

    operation_to_request = getattr(set_request, f"{operation}_request")

    response = gnmi_host.set(operation_to_request)
    print(response)

def set_config(host_info) -> None:

    try:
        with GNMIManager(host     = host_info['ip']
                        ,username = host_info['username']
                        ,password = host_info['password']
                        ,port     = host_info['port']
                        ,pem      = host_info['pem_file']
                        ,options  = host_info['options']
                        ,keys_file= host_info['keys_file']) as gnmi_host:

            print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["operation"]}')
            print(f'config_to_apply = {host_info["config_to_apply"]}')
            if 'full_config_to_apply' in host_info:
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["operation"]}, Calling apply_config')
                apply_config(gnmi_host=gnmi_host,
                             config_to_apply=host_info['full_config_to_apply'],
                             operation=host_info['operation'],
                             hostname=host_info['hostname'])
            elif 'config_to_apply' in host_info:
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["operation"]}, Calling apply_config')
                apply_config(gnmi_host=gnmi_host,
                             config_to_apply=host_info['config_to_apply'],
                             operation=host_info['operation'],
                             hostname=host_info['hostname'])

    except Exception as e:
        print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Failed to connect. Exception:\n{e}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",        '-d',  type=str,                   help="Directory of PEM files")
    parser.add_argument("--username",   '-u',  type=str, default="root",   help="Username. Default is root")
    parser.add_argument("--password",   '-p',  type=str, default="lablab", help="Password. Default is lablab")
    parser.add_argument("--port",       '-t',  type=str, default="57400",  help="gRPC port. Default is 57400")
    parser.add_argument("--hosts",      '-i',  type=str,                   help="List of IP(s) to include")
    parser.add_argument("--config",     '-c',  type=str,                   help="File with the configuration to set")
    parser.add_argument("--full_config",'-f',  type=str,                   help="File with the full configuration to set")
    parser.add_argument("--operation",  '-o',  type=str,                   help="Option. \"replace\", \"update\" or \"delete\"")
    parser.add_argument("--yangkeys",   '-y',  type=str,                   help="Yang keys file")
    arguments = parser.parse_args()
    dir:         str = arguments.dir
    username:    str = arguments.username
    password:    str = arguments.password
    port:        str = arguments.port
    hosts:       str = arguments.hosts
    config:      str = arguments.config
    full_config: str = arguments.full_config
    operation:   str = arguments.operation
    keys_file:   str = arguments.yangkeys
    options = [('grpc.ssl_target_name_override', 'ems.cisco.com'), ('grpc.max_receive_message_length', 1000000000)]
    encoding = "JSON_IETF"

    try:
        list_of_hosts: List = [x for x in hosts.split(' ')]
        len_list_of_hosts: int = len(list_of_hosts)
        print(f'list_of_hosts = {list_of_hosts}')
        print(f'len_list_of_hosts = {len_list_of_hosts}')
    except AttributeError as e:
        print(f'Please specify at least one ip with -i option.')
        exit(1)

    if dir == None:
        print(f'Please specify where the PEM files are.')
        exit(1)
    else:
        if len_list_of_hosts == 1:
            pem_files: List = glob.glob(f'{dir}/*{list_of_hosts[0]}*.pem')
        else:
            pem_files: List = [''.join(glob.glob(f'{dir}/*{x}*.pem')) for x in list_of_hosts]
        print(f'pem_files = {pem_files}')

    if config:
        config_to_apply = json.loads(read_file(config))
    else:
        config_to_apply = False

    if full_config:
        full_config_to_apply = json.loads(read_file(full_config))
    else:
        full_config_to_apply = False

    if not operation:
        print('Please specify the type of operation')
        sys.exit(2)
    if operation == "replace" and not full_config:
        print('Please specify the full_config when doing a replace operation')
        sys.exit(3)
    if operation == "delete" and full_config:
        print(f'This will wipe out the full config. Don\'t do that!')
        sys.exit(4)

    metadata_list = list()
    for pem_file in pem_files:
        temp     = pem_file.split('/')[-1]
        hostname = temp.split('_')[0]
        ip       = temp.split('_')[1].split('.pem')[0]

        temp_dict = dict()
        temp_dict['hostname']  = hostname
        temp_dict['pem_file']  = pem_file
        temp_dict['ip']        = ip
        temp_dict['options']   = options
        temp_dict['encoding']  = encoding
        temp_dict['keys_file'] = keys_file
        temp_dict['port']      = port
        temp_dict['username']  = username
        temp_dict['password']  = password
        temp_dict['operation'] = operation
        if config_to_apply: temp_dict['config_to_apply'] = config_to_apply
        if full_config_to_apply: temp_dict['full_config_to_apply'] = full_config_to_apply
        metadata_list.append(temp_dict)

    print(json.dumps(metadata_list, indent=4))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(metadata_list)) as executor:
        executor.map(set_config, metadata_list)

if __name__ == '__main__':
    main()

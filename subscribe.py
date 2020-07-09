# Author's Email: brusilva@cisco.com
# Author's Name: Bruno Novais

import json
import argparse
import glob
import time
import sys
import concurrent.futures
import threading
import traceback
import copy
import ipaddress
import data_converter
from gnmi_manager import GNMIManager
from uploader import ElasticSearchUploader
from typing import List, Set, Dict, Union

def upload_to_es(elastic_obj, responses, host_info) -> bool:
    '''
    This function receives a list of ParsedResponse objects.
    It verifies if the responses is big enough based on batch size, only then we upload.
    We return True whenever an upload occurs so that calling function can reset responses list.
    batch sizes may be adjusted depending on what is being polled.
    '''

    small_models = ['Cisco-IOS-XR-ofa-netflow-oper:net-flow', 'Cisco-IOS-XR-platforms-ofa-oper:ofa']

    batch_size_with_keys = 100
    if len(responses) == host_info["batch_size"]:
        elastic_obj.upload(data=responses)
        return True
    else:
        if ('[' in host_info["models"][0] or host_info["models"][0] in small_models) and len(responses) == batch_size_with_keys:
            elastic_obj.upload(data=responses)
            return True

    return False

def subscribe(host_info_input):

    host_info = list(host_info_input.values())[0]
    try:
        with GNMIManager(host      = host_info['ip']
                        ,username  = host_info['username']
                        ,password  = host_info['password']
                        ,port      = host_info['port']
                        ,pem       = host_info['pem_file']
                        ,options   = host_info['options']
                        ,keys_file = host_info['yang_keys']) as gnmi_host:

            if host_info['elastic'] == "yes":
                es = ElasticSearchUploader('2.2.2.1', '9200')
            else:
                es=None
            try:
                responses = []
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["ip"]}, {host_info["models"]}, Subscribing via {host_info["subscription_mode"]}')
                for response in gnmi_host.subscribe(host_info['encoding'], host_info['models'], host_info['interval'], "STREAM", host_info['subscription_mode']):
                    data_converter.convert_data_single(response)
                    responses.append(response)
                    if es:
                        if upload_to_es(elastic_obj=es, responses=responses, host_info=host_info):
                            print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["ip"]}, {host_info["models"]}, responses size = {len(responses)} and upload is done. Resetting responses')
                            responses = []
            except Exception as e:
                print(e)
                traceback.print_exc()

            if host_info['show'] == "yes":
                for response in responses:
                    print(response)
    except Exception as e:
        print(e)
        traceback.print_exc()

def host_subscribe(host_info):
    with open(host_info['models'], 'r') as fp:
        models_json = json.load(fp)

    print(json.dumps(models_json, indent=4))

    group_host_list = []
    for group in models_json:
        host_info_copy = copy.deepcopy(host_info)
        group_name = list(group.keys())[0]
        host_info_copy['models'] = group[group_name]
        per_group_host = {}
        per_group_host[group_name] = host_info_copy
        group_host_list.append(per_group_host)
                                  
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(group_host_list)) as executor:
        executor.map(subscribe, group_host_list)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",          '-d',   type=str,                   help="Directory of PEM files")
    parser.add_argument("--username",     '-u',   type=str, default="cisco",  help="Username. Default is cisco")
    parser.add_argument("--password",     '-p',   type=str, default="lab123", help="Password. Default is lab123")
    parser.add_argument("--port",         '-t',   type=str, default="57400",  help="gRPC port. Default is 57400")
    parser.add_argument("--hosts",        '-i',   type=str,                   help="List of IP(s) to include")
    parser.add_argument("--models",       '-m',   type=str,                   help="File with models to pull sequentially")
    parser.add_argument("--yang_keys",    '-y',   type=str,                   help="File with yang keys for the release")
    parser.add_argument("--elastic",      '-e',   type=str, default="no",     help="Upload or not to elastic search. Default is no")
    parser.add_argument("--show_output",  '-s',   type=str, default="no",     help="display output or not. Default is no")
    parser.add_argument("--encoding",     '-en',  type=str, default="PROTO",  help="Encoding. PROTO or JSON_IETF. Default is PROTO")
    parser.add_argument("--interval",     '-in',  type=int, default=30,       help="Interval in seconds. Default is 30")
    parser.add_argument("--batch_size",   '-b',   type=int, default=1000,     help="Batch size for ESDB upload. Default is 1000")
    parser.add_argument("--subscription_mode", '-sub_mode', type=str, default="SAMPLE", help="Subscription mode. Default is SAMPLE")
    arguments = parser.parse_args()
    dir:      str = arguments.dir
    username: str = arguments.username
    password: str = arguments.password
    port:     str = arguments.port
    hosts:    str = arguments.hosts
    models:   str = arguments.models
    yang_keys:str = arguments.yang_keys
    elastic:  str = arguments.elastic
    show:     str = arguments.show_output
    encoding: str = arguments.encoding
    interval: int = arguments.interval
    batch_size: int = arguments.batch_size
    subscription_mode: str = arguments.subscription_mode
    options = [('grpc.ssl_target_name_override', 'ems.cisco.com'), ('grpc.max_receive_message_length', 1000000000)]

    try:
        list_of_hosts: List = [x for x in hosts.split(' ')]
        len_list_of_hosts: int = len(list_of_hosts)
    except AttributeError as e:
        parser.print_help()
        print(f'### Please specify at least one ip with -i option.')
        exit(1)

    if not dir:
        parser.print_help()
        print(f'### Please specify where the PEM files are.')
        exit(1)

    if len_list_of_hosts == 1:
        pem_files: List[str] = []
        pem_files: List = glob.glob(f'{dir}/*{list_of_hosts[0]}*.pem')
    else:
        pem_files: List = [''.join(glob.glob(f'{dir}/*{x}*.pem')) for x in list_of_hosts]

    if not models:
        parser.print_help()
        print(f'### Please specify where the models json file is.')
        exit(1)

    if not yang_keys:
        parser.print_help()
        print(f'### Please specify the yang_keys file for the release.')
        exit(3)

    metadata_list = list()
    for pem_file in pem_files:
        temp     = pem_file.split('/')[-1]
        hostname = temp.split('_')[0]
        ip       = temp.split('_')[1].split('.pem')[0]
        try:
            ip_obj = ipaddress.IPv4Address(ip)
        except Exception as e:
            ip_parsed = f"[{ip}]"
        else:
            ip_parsed = ip
        print(pem_file)

        temp_dict = dict()
        temp_dict['hostname']          = hostname
        temp_dict['pem_file']          = pem_file
        temp_dict['ip']                = ip_parsed
        temp_dict['options']           = options
        temp_dict['encoding']          = encoding
        temp_dict['interval']          = interval
        temp_dict['yang_keys']         = yang_keys
        temp_dict['port']              = port
        temp_dict['models']            = models
        temp_dict['username']          = username
        temp_dict['password']          = password
        temp_dict['show']              = show
        temp_dict['batch_size']        = batch_size
        temp_dict['subscription_mode'] = subscription_mode
        if elastic: temp_dict['elastic'] = elastic

        metadata_list.append(temp_dict)

    print(json.dumps(metadata_list, indent=4))

    with concurrent.futures.ProcessPoolExecutor(max_workers=len(metadata_list)) as executor:
        executor.map(host_subscribe, metadata_list)

if __name__ == '__main__':
    main()

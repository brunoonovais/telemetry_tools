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
    #small_models = ['Cisco-IOS-XR-ofa-netflow-oper:net-flow']

    # batch size with keys is defined below. it is small enough since it usually means there's less data to pull.
    batch_size_with_keys = 100
    #print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Uploading to ESDB')
    #print(responses[0].dict_to_upload)
    if len(responses) == host_info["batch_size"]:
        #print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Uploading to ESDB')
        #print(responses)
        elastic_obj.upload(data=responses)
        #print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Uploaded to ESDB')

        return True
    else:
        # if [ is in the model list, then it means it has a key, so the batch size is smaller so we don't wait many occurrences before upload.
        if ('[' in host_info["models"][0] or host_info["models"][0] in small_models) and len(responses) == batch_size_with_keys:
            #print(f'len responses = {len(responses)}')
            #print(f'responses = {responses}')
            #for response in responses:
                #print(response.dict_to_upload)
            #print(f'{time.strftime("%H:%M:%S")}, uploading {host_info["models"]} to ESDB')
            elastic_obj.upload(data=responses)

            return True

    return False

def subscribe(host_info_input):

    #print(f'host_info_input: {host_info_input}')
    host_info = list(host_info_input.values())[0]
    #print(f'host_info inside subscribe = \n\n{host_info}')
    # We create a gnmi_host and connect
    try:
        with GNMIManager(host      = host_info['ip']
                        ,username  = host_info['username']
                        ,password  = host_info['password']
                        ,port      = host_info['port']
                        ,pem       = host_info['pem_file']
                        ,options   = host_info['options']
                        ,keys_file = host_info['yang_keys']) as gnmi_host:

            #print(json.dumps(host_info, indent=4))
            #print('#### THREAD ####')
            # if elastic option is enabled, create an elastic search object for each box
            if host_info['elastic'] == "yes":
                es = ElasticSearchUploader('2.2.2.1', '9200')
            else:
                es=None
            try:
                responses = []
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["ip"]}, {host_info["models"]}, Subscribing via {host_info["subscription_mode"]}')
                for response in gnmi_host.subscribe(host_info['encoding'], host_info['models'], host_info['interval'], "STREAM", host_info['subscription_mode']):
                    #print('appending')
                    #print(response)
                    # we append response to a responses list. the list will be uploaded once it reaches the batch_size
                    data_converter.convert_data_single(response)
                    responses.append(response)
                    #print(len(responses))
                    if es:
                        #print('uploading')
                        if upload_to_es(elastic_obj=es, responses=responses, host_info=host_info):
                            print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["ip"]}, {host_info["models"]}, responses size = {len(responses)} and upload is done. Resetting responses')
                            responses = []
            except Exception as e:
                print(e)
                traceback.print_exc()

            # if show option is specified, we loop through all responses and display them
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
        #print(f'# group = {group}')
        host_info_copy = copy.deepcopy(host_info)
        group_name = list(group.keys())[0]
        #print(f'##  group = {group}\n##  group_name = {group_name}\n##  {group[group_name]}')
        host_info_copy['models'] = group[group_name]
        #print(f'####  host_info[models] = {host_info["models"]}')
        per_group_host = {}
        per_group_host[group_name] = host_info_copy
        #print(f'   per_group_host[group_name][models] = {per_group_host[group_name]["models"]}')
        #print(f'######## json per group host = {per_group_host}')
        group_host_list.append(per_group_host)
        #print(f'############group_host_list = {group_host_list}')
        #print(len(group_host_list))
    #print(f'group_host_list = {group_host_list}')

    # start a thread for each pem file in the pem_files list
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(group_host_list)) as executor:
        executor.map(subscribe, group_host_list)

def main():
    ############################# INITIALIZATION #############################
    #### Argparse block ####
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
    #### End of Argparse block ####

    # grabbing all variables from arguments
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
    # other default variables
    options = [('grpc.ssl_target_name_override', 'ems.cisco.com'), ('grpc.max_receive_message_length', 1000000000)]

    # verify number of hosts
    try:
        list_of_hosts: List = [x for x in hosts.split(' ')]
        len_list_of_hosts: int = len(list_of_hosts)
    except AttributeError as e:
        parser.print_help()
        print(f'### Please specify at least one ip with -i option.')
        exit(1)

    # exit if no directory is provided.
    if not dir:
        parser.print_help()
        print(f'### Please specify where the PEM files are.')
        exit(1)

    # verify if we have 1 or multiple hosts specified, then grab respective pem file(s) in dir.
    if len_list_of_hosts == 1:
        pem_files: List[str] = []
        pem_files: List = glob.glob(f'{dir}/*{list_of_hosts[0]}*.pem')
    else:
        pem_files: List = [''.join(glob.glob(f'{dir}/*{x}*.pem')) for x in list_of_hosts]

    # verify if models has been supplied.
    if not models:
        parser.print_help()
        print(f'### Please specify where the models json file is.')
        exit(1)

    # if yang_keys file is not specified, exit.
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

        # assign a dictionary for each host with all the info, then append to list.
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
    ############################# END OF INITIALIZATION #############################

    # start a thread for each pem file in the pem_files list
    with concurrent.futures.ProcessPoolExecutor(max_workers=len(metadata_list)) as executor:
        executor.map(host_subscribe, metadata_list)


if __name__ == '__main__':
    main()

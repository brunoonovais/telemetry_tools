import json
import argparse
import glob
import time
import traceback
import concurrent.futures
from gnmi_manager import GNMIManager
from uploader import ElasticSearchUploader
from typing import List, Set, Dict, Union

def upload_to_es(elastic_obj, responses, host_info) -> bool:

    print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Config, Uploading to ESDB')
    try:
        elastic_obj.upload(responses)
    except Exception as e:
        traceback.print_exc()
    print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Config, Uploaded to ESDB')

    return True

def parse_response(model: str, config: dict) -> str:
    '''This function will return response received in json in order to write to file later on.
    This is needed so we can format as expected if we want to just set that config later'''
    d = {}
    d[model] = config
    
    return f'{json.dumps(d, indent=4)},'

def get_config(host_info) -> None:
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
                es = False

            if 'show_config' in host_info:
                show_config: bool = True
                temp_config_file = "/tmp/temp_config_file"
                with open(temp_config_file, 'w') as fp:
                    fp.write('[')
                    fp.flush()
            else:
                show_config: bool = False

            if 'filename' in host_info:
                write: bool = True
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Config, Writing to {host_info["filename"]}')
                # just empty out the file
                with open(host_info["filename"], "w") as fp:
                    pass
            else:
                print(f'write is False')
                write: bool = False

            if len(host_info['models']) == 0:
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Config, Pending')
                responses = gnmi_host.get_config(encoding=host_info['encoding'])
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Config, Success!')
            else:
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["models"]}, Pending')
                responses = gnmi_host.get_config(encoding=host_info['encoding'], config_models=host_info["models"])
                print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, {host_info["models"]}, Success!')

            print(f'responses size = {len(responses)}')
            for response in responses:
                config = response.dict_to_upload["config"]
                model = response.dict_to_upload["model"]
                if write:
                    if 'router-configs' in model:
                        continue
                    else:
                        with open(host_info["filename"], "a") as fp:
                            fp.write(parse_response(model, config))
                if show_config:
                    if 'router-configs' in model:
                        continue
                    else:
                        model_and_config_json = {}
                        model_and_config_json[model] = config
                        with open(temp_config_file, 'a') as fp:
                            fp.write(f'{json.dumps(model_and_config_json)},')

            if show_config:
                with open(temp_config_file, 'a') as fp:
                    fp.write('}]')
            if es:
                upload_to_es(elastic_obj=es, responses=responses, host_info=host_info)

    except Exception as e:
        print(f'{time.strftime("%H:%M:%S")}, {host_info["hostname"]}, Failed to connect. Exception:\n{e}')

    return None

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",        '-d',   type=str,                   help="Directory of PEM files")
    parser.add_argument("--username",   '-u',   type=str, default="root",   help="Username. Default is root")
    parser.add_argument("--password",   '-p',   type=str, default="lablab", help="Password. Default is lablab")
    parser.add_argument("--port",       '-t',   type=str, default="57400",  help="gRPC port. Default is 57400")
    parser.add_argument("--hosts",      '-i',   type=str,                   help="List of IP(s) to include")
    parser.add_argument("--models",     '-m',   type=str,                   help="File with models to pull sequentially.")
    parser.add_argument("--elastic",    '-e',   type=str, default="no",     help="Upload or not to elastic search. Default is no")
    parser.add_argument("--show_config",'-s',   type=str,                   help="Display config or not. Default is no")
    parser.add_argument("--write",      '-w',   type=str,                   help="Filename to write the config. Default is None")
    parser.add_argument("--yangkeys",      '-y',   type=str,                   help="Yang Keys file")
    arguments = parser.parse_args()
    directory:   str  = arguments.dir
    username:    str  = arguments.username
    password:    str  = arguments.password
    port:        str  = arguments.port
    hosts:       str  = arguments.hosts
    models:      str  = arguments.models
    elastic:     str  = arguments.elastic
    show_config: str  = arguments.show_config
    write:       str  = arguments.write
    yang_keys:   str  = arguments.yangkeys

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

    if directory == None:
        print(f'Please specify where the PEM files are.')
        exit(1)
    else:
        if len_list_of_hosts == 1:
            pem_files: List[str] = []
            pem_files: List = glob.glob(f'{directory}/*{list_of_hosts[0]}*.pem')
        else:
            pem_files: List = [''.join(glob.glob(f'{directory}/*{x}*.pem')) for x in list_of_hosts]
        print(f'pem_files = {pem_files}')

    if models != None:
        with open(models, "r") as fp:
            models_to_get = fp.read().splitlines()
    else:
        models_to_get = []

    metadata_list = list()
    for pem_file in pem_files:
        temp     = pem_file.split('/')[-1]
        hostname = temp.split('_')[0]
        ip       = temp.split('_')[1].split('.pem')[0]

        temp_dict = dict()
        temp_dict['hostname'] = hostname
        temp_dict['pem_file'] = pem_file
        temp_dict['ip']       = ip
        temp_dict['options']  = options
        temp_dict['encoding'] = encoding
        temp_dict['yang_keys']= yang_keys
        temp_dict['port']     = port
        temp_dict['models']   = models_to_get
        temp_dict['username'] = username
        temp_dict['password'] = password
        if elastic: temp_dict['elastic'] = elastic
        if show_config: temp_dict['show_config'] = show_config
        if write: temp_dict['filename'] = write
        metadata_list.append(temp_dict)
    print(json.dumps(metadata_list, indent=4))

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(metadata_list)) as executor:
        executor.map(get_config, metadata_list)

if __name__ == '__main__':
    main()

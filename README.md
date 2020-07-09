## grpc-download-pem-files.py ##

```
(venv)$ python grpc-download-pem-files.py -h
usage: grpc-download-pem-files.py [-h] [--dir DIR] [--names NAMES]
                                  [--username USERNAME] [--password PASSWORD]

optional arguments:
  -h, --help            show this help message and exit
  --dir DIR, -d DIR     Directory to download the PEM files
  --names NAMES, -n NAMES
                        Hosts in format "ip-1 ip-2 ip-3 ..."
  --username USERNAME, -u USERNAME
                        Username. Default is root
  --password PASSWORD, -p PASSWORD
                        Password. Default is lablab
```

First command to run for a new box - downloads the pem file from the router from /misc/config/grpc/ems.pem and transfers to directory specified.

## yang_download_files.py ##

```
mkdir -p ../../yang_spitfire_721.38i_test/
python yang_download_files.py -d ../../yang_spitfire_721.38i_test/ -y /tmp/yang -u cisco -p lab123 -i "10.8.70.11"
```

Downloads yang files from box and puts into -d directory.
Then runs pyang -f keys module to build keys file and puts into -y filename.

## pyang -f keys 'yang files' ##

Generates yang keys file for a certain list of models.
Install "pyang_keys_module.py" into your pyang installation folder and rename to keys.py to use it individually for a certain model.

## ncclient_get-capabilities.py ##

```
(venv)$ python ncclient_get-capabilities.py -h
usage: ncclient_get-capabilities.py [-h] [--username USERNAME]
                                    [--password PASSWORD] [--host HOST]

optional arguments:
  -h, --help            show this help message and exit
  --username USERNAME, -u USERNAME
                        Username. Default is cisco
  --password PASSWORD, -p PASSWORD
                        Password. Default is lab123
  --host HOST, -i HOST  IP of host
```

Prints capabilities to screen.

## ssh_subscribe.py ##

```
(venv)$ python ssh_subscribe.py -h
usage: ssh_subscribe.py [-h] [-u USERNAME] [-p PASSWORD] -a HOST [-s SEM]
                        [-d DURATION] [-i INTERVAL] [-f FILENAME] [-e ELASTIC]
                        [-o OUTPUT] [-b BULKSIZE]

SSH Stress script

optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --user USERNAME
  -p PASSWORD, --password PASSWORD
                        password
  -a HOST, --host HOST  Host IP address
  -s SEM, --semaphore SEM
                        Number of concurent threads executing ssh connections
  -d DURATION, --duration DURATION
                        Number of seconds each ssh session stays
  -i INTERVAL, --interval INTERVAL
                        Number of seconds between the starts of 2 ssh sessions
  -f FILENAME, --filename FILENAME
                        Path and name of the file which contains the CLI
                        commands. Will run show running-config if not
                        specified
  -e ELASTIC, --elastic ELASTIC
                        Upload or not to elastic search. Default is no
  -o OUTPUT, --output OUTPUT
                        Output the data to a file or not. Default is no
  -b BULKSIZE, --bulksize BULKSIZE
                        Bulk size of the data list

Example:
python ./ssh_script/ssh_subscribe.py -u cisco -p lab123 -a "172.16.42.1" -s 40 -d 10 -i 1 -f /tmp/commands.txt -e yes -b 10&
```

SSH Stress script that opens up many threads to stress SSH on the router.
Script located here: https://github.com/yixingqiu1208/elastic-search-toolkit

## GNMI - get_config.py ##

Install gnmi api from this repository: https://github.com/GregoryBrown/gNMI-API

```
(venv)$ python get_config.py -h
usage: get_config.py [-h] [--dir DIR] [--username USERNAME]
                     [--password PASSWORD] [--port PORT] [--hosts HOSTS]
                     [--models MODELS] [--elastic ELASTIC]
                     [--show_config SHOW_CONFIG] [--write WRITE]

optional arguments:
  -h, --help            show this help message and exit
  --dir DIR, -d DIR     Directory of PEM files
  --username USERNAME, -u USERNAME
                        Username. Default is root
  --password PASSWORD, -p PASSWORD
                        Password. Default is lablab
  --port PORT, -t PORT  gRPC port. Default is 57400
  --hosts HOSTS, -i HOSTS
                        List of IP(s) to include
  --models MODELS, -m MODELS
                        File with models to pull sequentially.
  --elastic ELASTIC, -e ELASTIC
                        Upload or not to elastic search. Default is no
  --show_config SHOW_CONFIG, -s SHOW_CONFIG
                        Display config or not. Default is no
  --write WRITE, -w WRITE
                        Filename to write the config. Default is None

Example:

python get_config.py -d pem_files/ -u cisco -p lab123 -i "10.8.70.11" -s yes
```

uses gNMI get for getting configuration and uploading to Elastic Search.

## GNMI - set_config.py ##

```
(venv)$ python set_config.py -h
usage: set_config.py [-h] [--dir DIR] [--username USERNAME]
                     [--password PASSWORD] [--port PORT] [--hosts HOSTS]
                     [--config CONFIG] [--full_config FULL_CONFIG]
                     [--operation OPERATION]

optional arguments:
  -h, --help            show this help message and exit
  --dir DIR, -d DIR     Directory of PEM files
  --username USERNAME, -u USERNAME
                        Username. Default is root
  --password PASSWORD, -p PASSWORD
                        Password. Default is lablab
  --port PORT, -t PORT  gRPC port. Default is 57400
  --hosts HOSTS, -i HOSTS
                        List of IP(s) to include
  --config CONFIG, -c CONFIG
                        File with the configuration to set
  --full_config FULL_CONFIG, -f FULL_CONFIG
                        File with the full configuration to set
  --operation OPERATION, -o OPERATION
                        Option. "replace", "update" or "delete"

Example: TBD
```

reads config from file in json format and sets it. Important to define operation type.

## GNMI - subscribe.py ##

```(venv)$ python subscribe.py -h
usage: subscribe.py [-h] [--dir DIR] [--username USERNAME]
                    [--password PASSWORD] [--port PORT] [--hosts HOSTS]
                    [--models MODELS] [--yang_keys YANG_KEYS]
                    [--elastic ELASTIC] [--show_output SHOW_OUTPUT]
                    [--encoding ENCODING] [--interval INTERVAL]
                    [--batch_size BATCH_SIZE]
                    [--subscription_mode SUBSCRIPTION_MODE]

optional arguments:
  -h, --help            show this help message and exit
  --dir DIR, -d DIR     Directory of PEM files
  --username USERNAME, -u USERNAME
                        Username. Default is cisco
  --password PASSWORD, -p PASSWORD
                        Password. Default is lab123
  --port PORT, -t PORT  gRPC port. Default is 57400
  --hosts HOSTS, -i HOSTS
                        List of IP(s) to include
  --models MODELS, -m MODELS
                        File with models to pull sequentially
  --yang_keys YANG_KEYS, -y YANG_KEYS
                        File with yang keys for the release
  --elastic ELASTIC, -e ELASTIC
                        Upload or not to elastic search. Default is no
  --show_output SHOW_OUTPUT, -s SHOW_OUTPUT
                        display output or not. Default is no
  --encoding ENCODING, -en ENCODING
                        Encoding. PROTO or JSON_IETF. Default is PROTO
  --interval INTERVAL, -in INTERVAL
                        Interval in seconds. Default is 30
  --batch_size BATCH_SIZE, -b BATCH_SIZE
                        Batch size for ESDB upload. Default is 1000
  --subscription_mode SUBSCRIPTION_MODE, -sub_mode SUBSCRIPTION_MODE
                        Subscription mode. Default is SAMPLE
                        
Example:
python ./subscribe.py -i "172.16.0.1 10.8.70.11 2001:10:8:70::11 2001:172:16:0:1::1" -m ./fna_test_subscribe_2020-06-17.json -d pem_files/ -y yang-keys-sf-72138i.txt -in 60 -e yes -b 20000 -sub_mode SAMPLE&
```

Uses Subscribe method for gNMI operational data. Opens up a process per host and a thread per SubscriptionList.

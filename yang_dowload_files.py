# Author's Email: gregorbr@cisco.com
# Authors' Name: Gregory Brown

import os
from subprocess import run, CalledProcessError
import subprocess
from pathlib import Path
from ncclient import manager
import argparse


class YangDownloader:
    """Used to connect to a netconf box and download the yang models to a location off box

    :param host: The IP address of the host to connect to
    :type host: str
    :param port: The port to connect to defaults to 830
    :type port: int
    :param location: The location where to save the yang file, defaults to the current directory
    :type location: str

    """

    def __init__(self, host: str, username: str, password: str, yang_keys_file: str, port: int = 830, location: str = "."):
        self.host: str = host
        self.username: str = username
        self.password: str = password
        self.port: int = port
        self.location: Path = Path(f"{location}/yang-models")
        self.yang_keys_file: Path = Path(yang_keys_file)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def make_dir(self):
        try:
            self.location.mkdir(exist_ok=True)
        except Exception as error:
            print(error)

    def connect(self):
        self.make_dir()
        print(f'{self.host}, {self.username}, {self.password}, {self.port}')
        with manager.connect(host=self.host, port=self.port, username=self.username, password=self.password, hostkey_verify=False, allow_agent=False, look_for_keys=False) as m:
            schemas_filter = '''<netconf-state xmlns = "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
        <schemas>
        <schema>
        <identifier/>
        </schema>
        </schemas>
        </netconf-state>'''
            data = m.get(filter=('subtree', schemas_filter)).data
            schema_list = [
                n.text
                for n in data.xpath('//*[local-name()="identifier"]')
            ]

            for schema in schema_list:
                print(f"Retrieving module: {schema}")
                rc = m.get_schema(identifier=schema)
                with open(self.location/f"{schema}.yang", "w") as fp:
                    fp.write(rc.data)

    def generate_key_file(self):
        try:
            yang_keys = run([f"pyang -f keys {self.location}/*.yang"], check=True, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
            output = yang_keys.stdout
            print(output)
            with open(self.yang_keys_file, "w") as fp:
                fp.write(output)
        except CalledProcessError as error:
            print(error)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--directory",    '-d',   type=str,                   help="Directory to store yang files")
    parser.add_argument("--yang_keys_file",'-y',  type=str,                   help="Filename of yang-keys-file")
    parser.add_argument("--username",     '-u',   type=str, default="cisco",  help="Username. Default is cisco")
    parser.add_argument("--password",     '-p',   type=str, default="lab123", help="Password. Default is lab123")
    parser.add_argument("--host",         '-i',   type=str,                   help="IP of host")
    arguments = parser.parse_args()
    directory: str = arguments.directory
    yang_keys_file: str = arguments.yang_keys_file
    username:  str = arguments.username
    password:  str = arguments.password
    host:      str = arguments.host

    with YangDownloader(host=host
                       ,username=username
                       ,password=password
                       ,location=directory
                       ,yang_keys_file=yang_keys_file) as yd:
        yd.generate_key_file()


if __name__ == '__main__':
    main()

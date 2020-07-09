#!/usr/bin/env python3

# Author's Email: brusilva@cisco.com
# Author's Name: Bruno Novais

from ncclient import manager, operations, xml_
from lxml import etree
import logging
import argparse

def demo(host, user, password):
    with manager.connect(host=host, port=22, username=user, password=password, timeout=1800, hostkey_verify=False,look_for_keys=False, allow_agent=False) as m:
        try:
            for cap in m.server_capabilities:
                print(cap)
        except operations.rpc.RPCError as e:
            print('RPCError!')
        except xml_.XMLError as e:
            print('XML ERROR')
        finally:
            pass
    exit(0)
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--username",     '-u',   type=str, default="cisco",  help="Username. Default is cisco")
    parser.add_argument("--password",     '-p',   type=str, default="lab123", help="Password. Default is lab123")
    parser.add_argument("--host",         '-i',   type=str,                   help="IP of host")
    arguments = parser.parse_args()
    username:  str = arguments.username
    password:  str = arguments.password
    host:      str = arguments.host

    demo(host=host, user=username, password=password)

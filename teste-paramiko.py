import os
#from dontenv import load_dontenv
from netmiko import ConnectHandler
#from rich import print

#load_dontenv()

#logging.basicConfig(level=logging.DEBUG)

olt_cb = {
    'device_type': 'huawei_olt',
    'host': '10.1.10.14',
    'username': 'fabbyo',
    'password': '23*04F@B%',
    'port': '22'
}

try:
    olt_connect = ConnectHandler(**olt_cb)

    comand = [
        "display current-configuration ont 0/1/0 5",
    ]

    print(olt_connect.send_command(comand))

    olt_connect.disconect()

except Exception as err:
    print(err)
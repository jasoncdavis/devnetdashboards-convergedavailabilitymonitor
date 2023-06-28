#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Obtains the device inventory from ACI APIC controller(s) via REST API
 (GetACIAPICDevices.py)

#                                                                      #
Fetches all the network device hostnames and management IP addresses
from ACI APIC controller(s) REST API.  Updates MySQL database with
inventory data.

Required inputs/variables:
    Reads 'optionsconfig.yaml' file for server address, username and
    password

    optionsconfig.yaml has the following sample:

    DNACenter:
    - host: sandboxdnac.cisco.com
        CheckSSLCert: True  # Or False, if you are not security conscious and using self-signed certs internally
        username: devnetuser
        password: Cisco123!

Outputs:
    Puts device information into MySQL inventory table

Version log:
v1      2021-0317   Ported from AO workflows to Python
v2      2021-0510   Refactored to enable for DevNet Automation 
Exchange

Credits:
"""
__version__ = '2'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"


import sys
import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import ReadEnvironmentVars
import InsertUpdateMySQL


def get_aciapic_authtoken(server):
    # create credentials structure
    name_pwd = {'aaaUser': {'attributes': {'name': server["username"], 'pwd': server["password"]}}}
    json_credentials = json.dumps(name_pwd)
    #print(name_pwd)
    #print(json_credentials)
    # log in to API
    login_url = 'https://' + server["host"] + '/api/aaaLogin.json'
    #print(login_url)
    ssl_verify = server["CheckSSLCert"]
    if ssl_verify == False:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    try:
        post_response = requests.post(login_url, 
                                      data=json_credentials,
                                      verify=ssl_verify)
        # get token from login response structure
        # print(post_response.text)
        auth = json.loads(post_response.text)
        if auth['imdata'][0].get('error') is not None:
            print('Got an error communication with APIC controller')
            if 'FAILED local authentication' in auth['imdata'][0]['error']['attributes']['text']:
                sys.exit('Incorrect credentials - check optionsconfig.yaml')
    except Exception as e:
        print(f'Unable to reach ACI APIC controller {server["host"]}\n'
              f'Got exception: {e}')
        sys.exit(1) # exiing with a non zero value is better for returning from an error

    login_attributes = auth['imdata'][0]['aaaLogin']['attributes']
    #print(login_attributes)
    auth_token = login_attributes['token']
    return auth_token


def get_aciapic_devices(server, authtoken):
    url = "https://" + server["host"] + "/api/class/topSystem.json"
    cookies = {}
    cookies['APIC-Cookie'] = authtoken
       
    # Handle SSL certificate verification and warnings - update per environment and security requirements
    ssl_verify = server["CheckSSLCert"]
    if ssl_verify == False:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    #print(url)
    #print(cookies['APIC-Cookie'])
    #print(ssl_verify)
    # Make REST API request
    response = requests.request(
        "GET",
        url,
        cookies=cookies,
        verify=ssl_verify
        )

    #print(response.json())  
    #print(response.text)  
    return (response.text)


def extract_device_properties(server, deviceinventory):
    deviceparams=[]
    inventory_json = json.loads(deviceinventory)
    for item in inventory_json["imdata"]:
        #["topSystem"]["attributes"]
        #print(item)
        #print('==')
        device_name = item.get('topSystem', {}).get('attributes', {}).get('name', {})
        ip_address = item.get('topSystem', {}).get('attributes', {}).get('oobMgmtAddr', {})
        device_type = item.get('topSystem', {}).get('attributes', {}).get('role', 'Unknown')
        fabric_domain = item.get('topSystem', {}).get('attributes', {}).get('fabricDomain', 'Unknown')
        fabric_id = item.get('topSystem', {}).get('attributes', {}).get('fabricId', 'Unknown')
        device_family = ""
        admin_status = 1 if item.get('topSystem', {}).get('attributes', {}).get('state', 'Unknown') == "in-service" else 0
        #print(f'"{fabric_domain}"-{fabric_id}--{device_name}', ip_address, device_type, admin_status)
        if ip_address != '0.0.0.0':
            deviceparams.append((f'"{fabric_domain}"-{fabric_id}--{device_name}', ip_address, device_type, device_family, server, admin_status))

    return deviceparams


def main():
    serverlist = ReadEnvironmentVars.read_config_file("ACIAPIC")
    deviceresults = []
    for server in serverlist:
        print(f"Processing ACI APIC controller {server['host']}...")
        authtoken = get_aciapic_authtoken(server)
        devices = get_aciapic_devices(server, authtoken)
        deviceresults.extend(extract_device_properties(server["host"], devices))
        devicerecords = len(deviceresults)
        print(f"  Running total records {devicerecords}")
    InsertUpdateMySQL.insertsql(ReadEnvironmentVars.read_config_file("MySQL"),deviceresults)


if __name__ == "__main__":
    main()
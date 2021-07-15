#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Obtains the device inventory from DNA Center via REST API
 (GetDNACDevices.py)

#                                                                      #
Fetches all the network device hostnames and management IP addresses
from DNA Center REST API.  Updates MySQL database with
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
v1      2021-0304   Ported from AO workflows to Python
v2      2021-0425   Refactored to enable for DevNet Automation 
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


def get_dnac_authtoken(server):
    """Get DNA Center Authorization Token for follow-on processing
    
    Uses server parameters to target a specific DNA Center server and
    generate an Authorization Token from the base username and
    password.
    
    :param server: dictionary containing settings of the DNA Center server being polled [eg. host, username, password,  etc.]
    :returns: Token to be used as cookie for follow-on API requests
    """

    url = "https://" + server["host"] + "/dna/system/api/v1/auth/token"
        
    # Provide username and password for basic authentication
    basicAuth = HTTPBasicAuth(server["username"], server["password"])

    # Handle SSL certificate verification and warnings - update per environment and security requirements
    ssl_verify = server["CheckSSLCert"]
    if ssl_verify == False:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Make REST API request
    try:
        response = requests.request(
            "POST",
            url,
            auth=basicAuth,
            verify=ssl_verify
            )
    except requests.exceptions.ConnectionError:
            # Maybe set up for a retry, or continue in a retry loop
            sys.exit(f'Unable to connect to server \'{server["host"]}\'.  Check server state or configuration in optionsconfig.yaml')
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        sys.exit(f'Unable to reach server \'{server["host"]}\' due to network timeout.  Try again later.')
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        sys.exit(f'Unhandled error: {e}')
    else:
        if response.status_code == 401:
            sys.exit(f'Unable to authenticate to server \'{server["host"]}\'.  Check configuration in optionsconfig.yaml')
        else:
            resp_token = json.loads(response.text)
            return (resp_token["Token"])


def get_dnac_devices(server, authtoken):
    """Get DNA Center device list from REST API
    
    Uses server parameters to target a specific DNA Center server and
    a supplied authentication token to perform a REST API extracting
    all DNA Center devices.
    
    :param server: dictionary containing settings of the DNA Center server being polled [eg. host, username, password,  etc.]
    :param authtoken: authentication token used as cookie in API call
    :returns: string of JSON data representing a list of dictionary records of devices and their parameters
    """
    url = "https://" + server["host"] + "/dna/intent/api/v1/network-device"
       
    # Handle SSL certificate verification and warnings - update per environment and security requirements
    ssl_verify = server["CheckSSLCert"]
    if ssl_verify == False:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    headers = {'X-Auth-Token': str(authtoken),
    'Content-type': 'application/json'}

    #print(headers)
    # Make REST API request
    response = requests.request(
        "GET",
        url,
        verify=ssl_verify,
        headers=headers
        )
    
    return (response.text)


def extract_device_properties(server, deviceinventory):
    """Extract the device properties from JSON data
    
    Extracts device properties from input string of JSON encoded data representing a list of device records (dictionaries)
    
    :param server: dictionary containing settings of the DNA Center server being polled [eg. host, username, password,  etc.]
    :param deviceinventory: string of JSON encoded records (as list of dictionaries)
    :returns: string of list of dictionary records of devices and their parameters
    """
    deviceparams=[]
    inventory_json = json.loads(deviceinventory)
    #print(json.dumps(inventory_json, indent=4))
    for item in inventory_json["response"]:
        #print(item)
        device_name = item.get('hostname', {})
        ip_address = item["managementIpAddress"]
        device_type = item.get('type', 'Unknown')
        device_family = item.get('family', 'Unknown')
        admin_status = 1 if item["collectionStatus"] == "Managed" else 0
        deviceparams.append((device_name, ip_address, device_type, device_family, server, admin_status))
    return deviceparams


def main():
    serverlist = ReadEnvironmentVars.read_config_file("DNACenter")
    deviceresults = []
    for server in serverlist:
        print(f"Processing DNA Center server {server['host']}...")
        authtoken = get_dnac_authtoken(server)
        devices = get_dnac_devices(server, authtoken)
        deviceresults.extend(extract_device_properties(server["host"], devices))
        devicerecords = len(deviceresults)
        print(f"  Running total records {devicerecords}")
    InsertUpdateMySQL.insertsql(ReadEnvironmentVars.read_config_file("MySQL"),deviceresults)


if __name__ == "__main__":
    main()
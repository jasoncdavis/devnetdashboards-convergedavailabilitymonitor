#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Obtains the device inventory from Prime Infrastructure via REST API
 (GetPrimeInfraDevices.py)

#                                                                      #
Fetches all the network device hostnames and management IP addresses
from Prime Infrastructure REST API.  Updates MySQL database with
inventory data.

Required inputs/variables:
    Reads 'optionsconfig.yaml' file for server address, username and
    password

    optionsconfig.yaml has the following sample
    PrimeInfrastructure:
    - host: primeinfrasandbox.cisco.com
        CheckSSLCert: True  # Or False, if you are not security conscious and using self-signed certs internally
        username: devnetuser
        password: DevNet123!

Outputs:
    Puts device information into MySQL inventory table

Version log:
v1      2021-0220   Ported from AO workflows to Python
v2      2021-0421   Refactored to enable for DevNet Automation 
Exchange
v3      2023-0622   Add more error handling

Credits:
"""
__version__ = '3'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"


import sys
import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
#import MySQLdb
import ReadEnvironmentVars
import InsertUpdateMySQL


def get_prime_infra_devices(server):
    """Extract Prime Infrastructure devices from REST API
    
    Reads Prime Infrastructure server REST API, extracting device list 
    
    :param server: dictionary containing settings of the Prime Infrastructure server being polled [eg. host, username, password,  etc.]
    :returns: string representing a JSON list of devices and their parameters
    """

    baseurl = "https://" + server["host"] + "/webacs/api/v4/data/Devices.json"
    querystring = "?.full=true"
    url = baseurl + querystring

    # Provide username and password for basic authentication
    basicAuth = HTTPBasicAuth(server["username"], server["password"])

    # Handle SSL certificate verification and warnings - update per environment and security requirements
    ssl_verify = server["CheckSSLCert"]
    if ssl_verify == False:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    # Make REST API request
    try:
        response = requests.request(
            "GET",
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
            return (response.text)


def extract_device_properties(server, deviceinventory):
    """Extract devices properties from JSON string
    
    Reads device inventory as JSON, extracts the fields needed to add as inventory into MySQL
    
    :param server: dictionary containing settings of the Prime Infrastructure server being polled [eg. host, username, password,  etc.]
    :param deviceinventory: string of JSON text representing Prime Infrastructure devices in a list
    :returns: list of dictionary entries representing device parameters
    """

    deviceparams=[]
    inventory_json = json.loads(deviceinventory)
    if inventory_json["queryResponse"]["@count"] == 0:
        sys.exit(f"Prime Infrastructure server {server} had NO inventory to export")
    for entity in inventory_json["queryResponse"]["entity"]:
        device_name = entity.get('devicesDTO', {}).get('deviceName', 'Unknown')
        ip_address = entity["devicesDTO"]["ipAddress"]
        device_type = entity.get('devicesDTO', {}).get('deviceType', 'Unknown')
        device_family = entity.get('devicesDTO', {}).get('productFamily', 'Unknown')
        admin_status = entity["devicesDTO"]["adminStatus"]
        admin_status = 1 if admin_status == "MANAGED" else 0
        deviceparams.append((device_name, ip_address, device_type, device_family, server, admin_status))
    return deviceparams


def main():
    serverlist = ReadEnvironmentVars.read_config_file("PrimeInfrastructure")
    deviceresults = []
    for server in serverlist:
        print(f"Processing Prime Infrastructure server {server['host']}...")
        deviceresults.extend(extract_device_properties(server["host"], get_prime_infra_devices(server)))
        devicerecords = len(deviceresults)
        print(f"  Running total records {devicerecords}")
    #insupd_mysql(read_config_file("MySQL"),deviceresults)
    InsertUpdateMySQL.insertsql(ReadEnvironmentVars.read_config_file("MySQL"),deviceresults)


if __name__ == "__main__":
    main()
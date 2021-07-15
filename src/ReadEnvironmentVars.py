#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Obtains the environment variables from options YAML file
 (ReadEnvironmentVars.py)

#                                                                      #
Reads the requested servertype environment parameters (hostname, 
username, password, etc) from the optionsconfig.yaml file which
defines all server types for the project (MySQL, Prime Infrastructure,
DNA Center, ACI APIC controllers, etc.

Required inputs/variables:
    servertype - string representing the server type and parameters
        to extract

    Reads 'optionsconfig.yaml' file for server address, username,
    password, etc.
    password

    optionsconfig.yaml has the following sample
    PrimeInfrastructure:
    - host: primeinfrasandbox.cisco.com
        CheckSSLCert: True  # Or False, if you are not security conscious and using self-signed certs internally
        username: devnetuser
        password: DevNet123!

Outputs:
    list of dictionary items reflecting the server parameters

Version log:
v1      2021-0623   Created as normalized function across all
    DevNet Dashboard importing scripts

Credits:
"""
__version__ = '1'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"



def read_config_file(servertype):
    """Read environmental settings file
    
    Reads a YAML file that defines environmental parameter and settings

    :param servertype: string defining the type of server settings to extract [eg. PrimeInfrastructure, DNACenter, etc.]
    :returns: List of servertype entries defined in YAML config file
    """
    import yaml

    with open("optionsconfig.yaml", "r") as ymlfile:
        try:
            cfg = yaml.safe_load(ymlfile)
        except yaml.YAMLError as e:
            print(e)
    
    return cfg.get(servertype)


def main(servertype):
    serverlist = read_config_file(servertype)
    return serverlist

if __name__ == "__main__":
    main()
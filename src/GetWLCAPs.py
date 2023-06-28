#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Obtains the device inventory from Wireless LAN Controllers (WLCs)
via NETCONF RPC
 (GetWLCAPs.py)

#                                                                      #
Fetches all the wireless AP and WLC hostnames and management IP
addresses from the WLC NETCONF interface.  Updates MySQL database with
inventory data.

Required inputs/variables:
    Reads 'optionsconfig.yaml' file for server address, username and
    password

    optionsconfig.yaml has the following sample
    WLC:
    - alias: WLC-9800
      host: 192.168.1.10
      username: my_username
      password: my_password

Outputs:
    Puts device information into MySQL inventory table

Version log:
v1      2023-0626   First release

Credits:
"""
__version__ = '1'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - " \
  "https://developer.cisco.com/site/license/cisco-sample-code-license/"


import sys
import InsertUpdateMySQLv3
from ncclient import manager
import xml.etree.ElementTree as ET
import re
import GetEnv


def strip_ns(xml_string):
    return re.sub('xmlns="[^"]+"', '', xml_string)


def get_wap_info(wlc):
    netconfrpc_payload = '''
    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
      <access-point-oper-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-wireless-access-point-oper">
        <capwap-data>
          <wtp-mac/>
          <ip-addr/>
          <device-detail>
            <static-info>
              <board-data>
                <wtp-serial-num/>
              </board-data>
              <ap-models>
                <model/>
              </ap-models>
            </static-info>
            <wtp-version>
              <sw-ver/>
            </wtp-version>
          </device-detail>
          <ap-location>
            <floor/>
            <location/>
          </ap-location>
        </capwap-data>
        <ap-name-mac-map>
          <wtp-name/>
          <wtp-mac/>
          <eth-mac/>
        </ap-name-mac-map>
      </access-point-oper-data>
    </filter>
    '''

    try:
        with manager.connect(host=wlc['host'], port=830,
                             username=wlc['username'],
                             password=wlc['password'],
                             hostkey_verify=False) as ncsession:
            ncreply = ncsession.get(netconfrpc_payload).data_xml
            ncreply_nons = strip_ns(ncreply)
            root = ET.fromstring(ncreply_nons)
            # print(ET.tostring(root, encoding='utf8').decode('utf8'))
    except Exception as e:
        sys.exit(f'Experienced a failure...\n{e}')
    else:
        return root


def extract_xml(xmldata):
    # Convert XML data from NETCONF results into dictionary
    # print(ET.tostring(xmldata, encoding='utf8').decode('utf8'))

    capwap_data = []
    wap_map = []

    for wap in xmldata.iter('capwap-data'):
        wtp_mac = wap.find('wtp-mac').text
        ip_addr = wap.find('ip-addr').text
        serial_num = wap.find('device-detail/static-info/board-data/wtp-serial-num').text
        ap_model = wap.find('device-detail/static-info/ap-models/model').text
        version = wap.find('device-detail/wtp-version/sw-ver/version').text
        release = wap.find('device-detail/wtp-version/sw-ver/release').text
        maint = wap.find('device-detail/wtp-version/sw-ver/maint').text
        # print(wtp_mac, ip_addr, serial_num, ap_model, version, release, maint)
        capwap_data.append((wtp_mac, ip_addr, serial_num, ap_model,
                           f'{version}.{release}.{maint}'))

    for wap in xmldata.iter('ap-name-mac-map'):
        wtp_mac = wap.find('wtp-mac').text
        wtp_name = wap.find('wtp-name').text
        eth_mac = wap.find('eth-mac').text
        # print(wtp_mac, wtp_name, eth_mac)
        wap_map.append((wtp_mac, wtp_name, eth_mac))

    # print(capwap_data)
    # print(wap_map)

    return capwap_data, wap_map


def merge_wap_data(controller, capwap_list, wap_map_list):
    # Merge wireless AP data into common list joined by wireless AP MAC
    merged_list = [(controller,) + x + y[1:] for x in capwap_list
                   for y in wap_map_list if x[0] == y[0]]
    return merged_list


def remap_inventory(deviceresults):
    # Re-order deviceresults into proper sequence for MySQL ingestion
    """
    MySQL inventory tables wants this order:
    `hostname` varchar(45) DEFAULT NULL,
    `mgmt_ip_address` varchar(45) NOT NULL,
    `serial_number` varchar(30) DEFAULT NULL,
    `device_type` varchar(120) DEFAULT NULL,
    `device_group` varchar(45) DEFAULT NULL,
    `model` varchar(45) DEFAULT NULL,
    `source` varchar(30) DEFAULT NULL,
    `software_version` varchar(30) DEFAULT NULL,
    `location` varchar(60) DEFAULT NULL,
    `contacts` varchar(255) DEFAULT NULL,
    `do_ping` tinyint(1) DEFAULT NULL,

    We are getting this in:
    (controller, wtp_mac, ip_addr, serial_num, ap_model, sw_version,
        wtp_name, eth_mac)
    """
    newinventory = []
    # print(f'Device results are\n{deviceresults}')
    for item in deviceresults:
        # print(item)
        newinventory.append((item[6], item[2], item[3], 'Wireless AP',
                             item[0], item[4], 'GetWLCAPs', item[5],
                             None, None, 1))
    return newinventory


def main():
    mysqlenv = GetEnv.getparam("MySQL")
    controllerlist = GetEnv.getparam("WLC")
    deviceresults = []
    for controller in controllerlist:
        print(f"Processing WLC controller '{controller['alias']}' "
              f"/ {controller['host']}...")
        xmlpayload = get_wap_info(controller)
        capwap_list, wap_map_list = extract_xml(xmlpayload)
        merged_list = merge_wap_data(controller['alias'], capwap_list,
                                     wap_map_list)
        # print(f'Merged list of wireless Access Points:\n{merged_list}')
        deviceresults += merged_list

    print(f"Processing {len(deviceresults)} total wireless access points")
    inventorylist = remap_inventory(deviceresults)

    # Parameterized query time - nice...
    SQL = f"""INSERT INTO {mysqlenv["database"]}.inventory
    (hostname, mgmt_ip_address, serial_number, device_type,
    device_group, model, source, software_version, location, contacts,
    do_ping)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE hostname=VALUES(hostname),
    serial_number=VALUES(serial_number),
    device_type=VALUES(device_type),
    model=VALUES(model),
    software_version=VALUES(software_version)
    """

    InsertUpdateMySQLv3.insertsql(mysqlenv, SQL, inventorylist)


if __name__ == "__main__":
    main()

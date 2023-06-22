#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Ping and Update Inventory (PingAndUpdateInventory.py)
#                                                                      #
Fetches all the network devices from the MySQL inventory table to
create a ping list, pings the devices, retrieves the results and 
popluates into MySQL pingresults table.

Required inputs/variables can be defined in the optionsconfig.py file
    LatencyThreshold - desired threshold over which the items will be
        highlighted yellow.  In milliseconds (ms)
    MySQL section - defined the database parameters, username,
        password, database name, etc.
    
v1      2021-0702   DevNet Automation Exchange publication
v2      2023-0622   Add error handling for empty database

Credits:
"""

__filename__ = 'PingAndUpdateInventory.py'
__version__ = '2'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"


import sys
import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import MySQLdb
import subprocess
from datetime import datetime
import ReadEnvironmentVars


# Script-global variables
pingfile = "pingfile.txt"


def get_mysql_devicelist(serverparams):
    """Get device list from MySQL database, inventory table
    
    Queries the MySQL database and inventory table for the device list
    
    :param serverparams: dictionary containing settings of the MySQL server being polled [eg. host, username, password,  etc.]
    :returns: pinglist - string containing list of devices to ping
    """

    db=MySQLdb.connect(host=serverparams["host"],user=serverparams["username"], 
        passwd=serverparams["password"],db=serverparams["database"])

    cursor=db.cursor()
    SQL = f"""SELECT mgmt_ip_address, do_ping FROM {serverparams["database"]}.inventory
    WHERE do_ping = 1 AND mgmt_ip_address != '0.0.0.0'
    """

    cursor.execute(SQL)
    rows = cursor.fetchall()
    print("Number of database records retrieved: " + str(cursor.rowcount))
    cursor.close()
    db.close()

    if cursor.rowcount == 0:
        sys.exit(f'MySQL server {serverparams["host"]} had NO inventory to process\n'
                 'Have you run the "Get*" inventory import scripts yet?')

    pinglist = []
    for row in rows:
        #print(row)
        pinglist.append(row[0])

    return pinglist


def write_to_file(in_devicelist):
    with open(pingfile, "w") as outfile:
        outfile.write("\n".join(in_devicelist))


def execute_fping():
    """Execute fping utility
    
    Executes the fping (fast ping) utility by passing desired
    arguments and redirecting in the ping file.
    
    :param None: 
    :returns: string containing list of devices and their ping results
    """

    output = subprocess.run("fping -c3 -q --json < " + pingfile, shell=True, capture_output=True)
    return output.stdout.decode()


def convert_json_to_sqldata(in_pingresults):
    """Convert JSON data to SQL data
    
    Converts incoming string data of ping results, converts to
    JSON records, then creates a list of entries formatted with 
    necessary parameters and stats
    
    :param in_pingresults: string containing a JSON-like list of 
        device ping results
    :returns: endpoints_down, endpoints_up - list of endpoints that 
        are down and those that are up
    """

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    json_results = json.loads(in_pingresults)
    #print(json_results)
    endpoints_up = []
    endpoints_down = []

    endpoints = json_results["hosts"]
    #print(endpoints)
    for endpoint in endpoints:
        if endpoints[endpoint]["loss_percentage"] == 100:
            endpoints_down.append((endpoint, 0, None, None, None, 1))
        else:
            endpoints_up.append((endpoint, 100 - endpoints[endpoint]["loss_percentage"], endpoints[endpoint]["avg"], endpoints[endpoint]["min"], endpoints[endpoint]["max"], str(timestamp), 0))
    
    #print(endpoints_down)
    #print(endpoints_up)
    return(endpoints_down, endpoints_up)


def insupd_mysql_pingresults(serverparams, status, sql_values):
    """Insert/Update MySQL with Ping Results
    
    Performs Inserts/Updates into MySQL with final results

    :param serverparams: dictionary containing settings of the MySQL server being polled [eg. host, username, password,  etc.]
    :param status: string containing the device status - up or down
    :sql_values: list of tuples containing the SQL values to be inserted/updated
    :returns: None
    """

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db=MySQLdb.connect(host=serverparams["host"],user=serverparams["username"], 
        passwd=serverparams["password"],db=serverparams["database"])

    cursor=db.cursor()

    #print(status)
    #print(sql_values)
    if status == "down":
        SQL = f"""INSERT INTO {serverparams["database"]}.pingresults (mgmt_ip_address, reachable_pct, 
            avg_latency, min_latency, max_latency, down_count) 
          VALUES (%s, %s, %s, %s, %s, %s) 
          ON DUPLICATE KEY UPDATE reachable_pct=0, avg_latency=VALUES(avg_latency), 
            min_latency=VALUES(min_latency), max_latency=VALUES(max_latency), 
            down_count=down_count+1
        """
    else:
        SQL = f"""INSERT INTO {serverparams["database"]}.pingresults (mgmt_ip_address, reachable_pct, 
            avg_latency, min_latency, max_latency, datetime_lastup, down_count) 
          VALUES (%s, %s, %s, %s, %s, %s, %s) 
          ON DUPLICATE KEY UPDATE reachable_pct=100-VALUES(reachable_pct), avg_latency=VALUES(avg_latency), 
            min_latency=VALUES(min_latency), max_latency=VALUES(max_latency), 
            datetime_lastup='{str(timestamp)}', down_count=0
        """

    #print(SQL)
    cursor.executemany(SQL, sql_values)
    db.commit()
    print("Number of database records affected: " + str(cursor.rowcount))

    cursor.close()
    db.close()


def main():
    devicelist = get_mysql_devicelist(ReadEnvironmentVars.read_config_file("MySQL"))
    write_to_file(devicelist)
    pingresults = execute_fping()
    (sqldata_down, sqldata_up) = convert_json_to_sqldata(pingresults)
    insupd_mysql_pingresults(ReadEnvironmentVars.read_config_file("MySQL"), "down", sqldata_down)
    insupd_mysql_pingresults(ReadEnvironmentVars.read_config_file("MySQL"), "up", sqldata_up)

if __name__ == "__main__":
    main()
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@filename: PingAndUpdateInventory.py
"""

"""Obtains the ping results from MySQL and creates the dashboard 
(CreateAvailabilityDashboard.py)

#                                                                      #
Fetches all the ping results from the MySQL database and pingresults
table and creates colorized HTML table results for Apache web docs
directory

Required inputs/variables:
    None

Outputs:
    Puts 'availability.html' in the Apache web docs directory, 
        typically, /var/www/html

Version log:
v1      2021-0702   Published to DevNet Automation Exchange
v2      2023-0628   Change ReadEnvironmentVars to GetEnv; fix reset code

Credits:
"""

__filename__ = 'CreateAvailabilityDashboard.py'
__version__ = '2'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - "\
    "https://developer.cisco.com/site/license/cisco-sample-code-license/"


import sys
import MySQLdb
from datetime import datetime
import os
import GetEnv

### Script-global variables
# Maximum number of cells wide on dashboard; may need to be adjusted
#  for larger monitors
MAX_CELLS_WIDE = 10


def get_mysql_pingresults(serverparams):
    """Get MySQL Ping results
    
    Connects to MySQL datbase with inventory and pingresults tables to 
    extract hostname, IP and stats.

    :param serverparams: dictionary containing settings of the MySQL server [eg. host, database name, username, password,  etc.]
    :returns: list of devices pinged and their results
    """

    db=MySQLdb.connect(host=serverparams["host"],user=serverparams["username"], 
        passwd=serverparams["password"],db=serverparams["database"])

    cursor=db.cursor()
    SQL = f"""SELECT i.hostname, p.mgmt_ip_address, p.reachable_pct, p.avg_latency, p.max_latency,
      p.datetime_lastup, p.down_count FROM {serverparams["database"]}.pingresults as p 
    LEFT JOIN inventory i on p.mgmt_ip_address = i.mgmt_ip_address
    ORDER BY p.reachable_pct ASC, p.down_count DESC, p.avg_latency DESC
    """

    cursor.execute(SQL)
    rows = cursor.fetchall()
    print("Total number of database records retrieved: " + str(cursor.rowcount))
    cursor.close()
    db.close()

    return list(rows)


def get_poll_stats(serverparams, latency_threshold):
    """Get poll stats

    Connects to MySQL database and extracts the statistics about 
    device counts for up, latent, dropping and down devices.

    :param serverparams: dictionary containing settings of the MySQL 
        server [eg. host, database name, username, password,  etc.]
    :param latency_threshold: integer value extracted from 
        optionsconfig.py parameters file.  Allows user to define custom
        threshold.
    :returns: tuple of stats (up, dropping, latent and down device 
        counts)
    """

    db=MySQLdb.connect(host=serverparams["host"],
                       user=serverparams["username"],
                       passwd=serverparams["password"],
                       db=serverparams["database"])

    cursor=db.cursor()
    SQL_DOWN = f"""SELECT COUNT(mgmt_ip_address)
      FROM {serverparams["database"]}.pingresults
      WHERE down_count > 0
      """

    SQL_UP = f"""SELECT COUNT(mgmt_ip_address)
      FROM {serverparams["database"]}.pingresults
      WHERE down_count = 0
      """

    SQL_DROPPING = f"""SELECT COUNT(mgmt_ip_address)
      FROM {serverparams["database"]}.pingresults
      WHERE reachable_pct < 100 AND reachable_pct > 0
      """

    SQL_LATENT = f"""SELECT COUNT(mgmt_ip_address)
      FROM {serverparams["database"]}.pingresults
      WHERE avg_latency > {latency_threshold}
      """

    cursor.execute(SQL_DOWN)
    downcount = cursor.fetchone()

    cursor.execute(SQL_UP)
    upcount = cursor.fetchone()

    cursor.execute(SQL_DROPPING)
    dropcount = cursor.fetchone()

    cursor.execute(SQL_LATENT)
    latentcount = cursor.fetchone()

    #print("Number of down devices: " + str(downcount[0]))
    #print("Number of up devices: " + str(upcount[0]))
    #print("Number of dropping devices: " + str(dropcount[0]))
    #print("Number of latent devices: " + str(latentcount[0]))

    cursor.close()
    db.close()

    return downcount[0], upcount[0], dropcount[0], latentcount[0]


def generate_htmlcells(in_results, threshold):
    """Generate HTML cells

    Generate HTML cells by extracting incoming results and providing
    the necessary HTML tags and formatting.

    :param in_results: dictionary containing ping results from database
    :param threshold: integer or floating point number representing
       custom desired threshold
    :returns: string of table cells rendered as HTML
    """

    tablecells = ""
    for count, endpoint in enumerate(in_results, start=1):
        # print(endpoint)
        # print(endpoint[3])
        # print(type(endpoint[3]))
        if endpoint[2] == 0 or endpoint[2] == None:
            cellhtml = f"""<td class="down">{endpoint[0]}<br>
        {endpoint[1]}<br>
        {str(endpoint[2])}%<br>
        Downcount {endpoint[6]} / Downsince {endpoint[5]}
        </td>
        """
        elif endpoint[2] < 100 and endpoint[2] > 0:
            cellhtml = f"""<td class="dropped">{endpoint[0]}<br>
        {endpoint[1]}<br>
        {str(endpoint[2])}% / avg {str(endpoint[3])} ms / max {str(endpoint[4])} ms
        </td>
        """
        elif endpoint[3] > threshold:
            cellhtml = f"""<td class="latent">{endpoint[0]}<br>
        {endpoint[1]}<br>
        {str(endpoint[2])}% / avg {str(endpoint[3])} ms / max {str(endpoint[4])} ms
        </td>
        """
        else:
            cellhtml = f"""<td class="good">{endpoint[0]}<br>
        {endpoint[1]}<br>
        {str(endpoint[2])}% / avg {str(endpoint[3])} ms / max {str(endpoint[4])} ms
        </td>
        """
        tablecells += cellhtml
        if count % MAX_CELLS_WIDE == 0: tablecells += """</tr>
        <tr>
        """
    return tablecells


def generate_availability_dashboard(cells, downcount, upcount, dropcount, latentcount):
    """Generate Availability dashboard

    Takes in the HTML table cell information along with availability 
    statistics and generates final HTML page.

    :param cells: string representing HTML cell data
    :param downcount, upcount, dropcount, latentcount: integer values
      representing availability stats
    :returns: htmltemplate - string representing final webpage to be
      published
    """

    gen_timestamp = datetime.now().strftime('%H:%M:%S %m-%d-%Y')

    # Note with f-strings and HTML any styles should be escaped with
    # double braces {{}}
    htmltemplate = f"""<html>
  <head>

    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <meta http-equiv="refresh" content="300">

    <title></title>
    <style>
        table {{ table-layout: fixed;
            overflow: hidden;}}
        
        td {{ font-size: 10px; 
            width: calc(100% / 10);
            overflow: hidden;}}

        body {{ background-color: #000000;
	        color: #ffffff;
	        font-family: Helvetica, Arial, Sans-Serif;
	        padding: 80px;}}
		
        TableAvailability {{ background-color: #000000;
	        table-layout: fixed;
	        border-spacing: 0px;}}

        tr {{ background-color: #000000;}}
        td {{ padding: 0.5rem;
	        border-radius: 1rem;}}

        td.down {{font-size: 10px;
            color: white;
            background-color: red;}}

        td.dropped {{ font-size: 10px;
            color: black;
            background-color: orange;}}

        td.latent {{ font-size: 10px;
            color: black;
            background-color: yellow;}}

        td.good {{ font-size: 10px;
            color: black;
            background-color: lime;}}
        
        td.stats {{ font-size: 14px;
            color: black;
            background-color: white;
            text-align: center;}}

        tbody.center {{ text-align: center;}}
    
    </style>
  </head>
  <body>
    <h1>Availability Dashboard</h1>
    <h4>Last generated: {gen_timestamp}</h4>
    <br>
    <table border="1" width="40%" cellspacing="2" cellpadding="2">
        <tbody class="center">
            <tr>
                <th>Up</th>
                <th>Latent</th>
                <th>Dropping</th>
                <th>Down</th>
            </tr>
            <tr>
                <td class="good">{upcount}</td>
                <td class="latent">{latentcount}</td>
                <td class="dropped">{dropcount}</td>
                <td class="down">{downcount}</td>
            <tr>
        </tbody>
    </table>

    <table border="1" width="100%" cellspacing="2" cellpadding="2">
      <tbody>
        <br>

        <tr>
        {cells}
        </tr>
      </tbody>
    </table>
    <br>
  </body>
</html>
    """
    return htmltemplate


def write_to_file(dashboard_location, in_content):
    """Write to file

    Receive HTML content in and writes as file to dashboard publishing
    location

    :param in_content: string representing web page HTML
    :returns: None; file is written to web hosting directory, typically
        /var/www/html
    """
    web_pub_path = os.path.dirname(dashboard_location) ## directory of file
    if not os.path.exists(web_pub_path):
        os.makedirs(web_pub_path)
    with open(dashboard_location, "w") as outfile:
        outfile.write(in_content)


def main():
    latency_threshold = GetEnv.getparam("LatencyThreshold")
    dashboard_location = GetEnv.getparam("DashboardFile")
    mysqlenv = GetEnv.getparam("MySQL")
    results_list = get_mysql_pingresults(mysqlenv)

    downcount, upcount, dropcount, latentcount = get_poll_stats(mysqlenv, latency_threshold)
    availabilitycells = generate_htmlcells(results_list, latency_threshold)
    dashboard = generate_availability_dashboard(availabilitycells, 
                                                downcount, upcount, 
                                                dropcount, latentcount)
    write_to_file(dashboard_location, dashboard)


if __name__ == "__main__":
    main()
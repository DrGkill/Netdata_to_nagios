# ####################################################################
# Script Description :  Nagios/Shinken/centreon/icinga script for 
#						alerting via netdata source
# Author:   Guillaume Seigneuret
# Date:     08/05/2016
# Version:  1.0
#
# Usage:    	Utilisation:
#	netdata_to_nagios.py -H host -p port [-D <datasource>] [-i <interval>] [-c <90>] [-w <80>]
#	
#	Options:
#	 -h, --help 
#		Show detailed help
#	 -H, --host
#		Specify remote netdata host address
#		Default : 127.0.0.1
#	 -p, --port
#		Specify remote netdata port
#		Default : 19999
#	 -D, --datasource
#		Specify which datasource you want to check. 
#		Available datasources :
#			- apps.cpu (default)
#			- system.ram
#	 -i interval
#		Specify an interval in seconds (minimum 2)
#		Default : 2
#	 -w, --warning
#		Specify warning threashold
#	 -c, --critical
#		Specify critical threashold
#
# Usage domain: Made to be lauched by Nagios or Shinken or Centreon or Incinga
#
# Config file:  None
#
# Prerequisites : 
#		- Python 2.7
#		- Netdata on client side
# ####################################################################
# GPL v3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ####################################################################

import os, sys, getopt
import json
import re
import urllib3
import pprint

def usage():
	usage = """
	Utilisation:
	netdata_to_nagios.py -H host -p port [-D <datasource>] [-i <interval>] [-c <90>] [-w <80>]
	
	Options:
	 -h, --help 
		Show detailed help
	 -H, --host
		Specify remote netdata host address
		Default : 127.0.0.1
	 -p, --port
		Specify remote netdata port
		Default : 19999
	 -D, --datasource
		Specify which datasource you want to check. 
		Available datasources :
			- apps.cpu (default)
			- system.ram
	 -i interval
		Specify an interval in seconds (minimum 2)
		Default : 2
	 -w, --warning
		Specify warning threashold
	 -c, --critical
		Specify critical threashold
	"""
	
	return usage

def printp(json):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(json)

def dateReplace(matches):
	#datapoints=re.sub('new Date\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)', dateReplace, res.data)
    datestr='"'
    separator="-"
    for i in range(1,7):
            if (i==6):
                    separator='"'
            datestr = datestr+matches.group(i)+separator
    return datestr

def sysexit(ok_flag,warning_flag,critical_flag):
	if ok_flag:
		return 0
	if warning_flag and not critical_flag:
		return 1
	if critical_flag:
		return 2

def get_from_datasource(hostaddress,port,datasource,interval,warn,crit):
	URL = ""
	if (int(interval) < 2) or (int(interval) > 3600):
		print "Interval problem, should be between 2 and 3600: " + interval
		return None
	
	URL = 'http://'+hostaddress+':'+port+'/api/v1/data?chart='+datasource+'&points='+interval+'&options=seconds'
	
	http = urllib3.PoolManager()
	res = http.request('GET',URL)
	datapoints=json.loads(res.data)
	
	if datasource == "apps.cpu":
		return_value = analyze_cpu_per_process(datapoints,warn,crit)
	elif datasource == "system.ram":
		return_value = analyze_ram(datapoints,warn,crit)
	else: 
		return None
	
	return return_value 
		
def analyze_ram(datapoints,warn,crit):
	ok_flag=False
	warning_flag=False
	critical_flag=False
	sysexitcode=0
	warning_buffer="Warning : "
	critical_buffer="Critical : "
	output_buffer=""
	perfdata_buffer=" | "
	res = dict()
	warn=float(warn)
	crit=float(crit)
	
	"""
	"labels": ["time", "buffers", "used", "cached", "free"],
    "data":   [ 1462723200, 81.61719, 236.6875, 820.4453, 867.7812]
	"""
	nb_of_datapoints=len(datapoints['data'])
	total_ram = datapoints['data'][0][1] + \
		datapoints['data'][0][2] + \
		datapoints['data'][0][3] + \
		datapoints['data'][0][4]
		
	used_ram = 0
	used = 0
	buffers = 0
	cached = 0
	free = 0
	for time in range(0, nb_of_datapoints):
		used_ram = used_ram + datapoints['data'][time][1] + datapoints['data'][time][2]
		used += datapoints['data'][time][2]
		buffers += datapoints['data'][time][1]
		cached += datapoints['data'][time][3]
		free += datapoints['data'][time][4]
		
	used_ram = used_ram/nb_of_datapoints
	used = used/nb_of_datapoints
	buffers = buffers/nb_of_datapoints
	cached = cached/nb_of_datapoints
	free = free/nb_of_datapoints
	
	used_ram_proportion = used_ram / total_ram * 100
	
	perfdata_buffer+="time="+str(datapoints['data'][0][0])+", used="+str(used)+", buffers="+str(buffers)+", cached="+str(cached)+", free="+str(free)
	
	if used_ram_proportion >= warn and used_ram_proportion < crit:
		warning_flag=True
		output_buffer += "RAM used at "+used_ram_proportion+"%"
	elif used_ram_proportion >= crit:
		critical_flag=True
		output_buffer += "RAM used at "+used_ram_proportion+"%"
	else:
		output_buffer="OK"
		ok_flag=True

	output_buffer += perfdata_buffer
	res['output'] = output_buffer
	res['code'] = sysexit(ok_flag,warning_flag,critical_flag)
	
	return res
		
def analyze_cpu_per_process(datapoints,warn,crit):

	ok_flag=False
	warning_flag=False
	critical_flag=False
	sysexitcode=0
	warning_buffer="Warning : "
	critical_buffer="Critical : "
	output_buffer=""
	perfdata_buffer=" | "
	res = dict()
	warn=float(warn)
	crit=float(crit)

	means=dict()
	number_of_proc=0
	nb_of_datapoints=len(datapoints['data'])
	for time in range(0, nb_of_datapoints):
		number_of_proc=len(datapoints['data'][time])
		for process in range(1,number_of_proc):
			if datapoints['labels'][process] not in means:
				means[datapoints['labels'][process]]=0
			act_value = datapoints['data'][time][process]
			if act_value is None:
				act_value=0
			means[datapoints['labels'][process]] += act_value

	for process in means:
		means[process]=means[process]/nb_of_datapoints
		perfdata_buffer+=process+"="+str(means[process])+", "
		if (means[process] >= warn) and means[process] < crit:
			warning_flag=True
			output_buffer+=" "+process+","
		if means[process] >= crit:
			critical_flag=True
			critical_buffer+=" "+process+","
	
	if critical_flag is True:
		output_buffer+=critical_buffer+" "
	if warning_flag is True:
		output_buffer+=warning_buffer+" "

	if critical_flag is False and warning_flag is False:
		output_buffer="OK"
		ok_flag=True

	output_buffer += perfdata_buffer
	res['output'] = output_buffer
	res['code'] = sysexit(ok_flag,warning_flag,critical_flag)
	
	return res

def main(argv):
	try:
        	opts, args = getopt.getopt(argv,"hD:i:w:c:H:p:",["help","datasource=","interval=","warning=","critical=","host=","port="])
	except getopt.GetoptError:
	        print usage()
        	sys.exit(4)
	hostaddress = '127.0.0.1'
	port = '19999'
	interval = '2'
	datasource = 'apps.cpu'
	
	for opt, arg in opts:
		if opt in ('-h', "--help"):
			print usage()
			sys.exit(4)
		elif opt in ("-c", "--critical"):
			critical = arg
		elif opt in ("-w", "--warning"):
			warning = arg
		elif opt in ("-H", "--host"):
			hostaddress = arg
		elif opt in ("-p", "--port"):
			port = arg
		elif opt in ("-D","--datasource"):
			datasource = arg
		elif opt in ("-i", "--interval"):
			interval= arg

	try: 
		warning
	except NameError:
		print "Missing warning threashold !"
		print usage()
		sys.exit(4)
	
	try:
		critical
	except NameError:
		print "Missing critical threashold !"
		print usage()
		sys.exit(4)

	return_values = get_from_datasource(hostaddress,port,datasource,interval,warning,critical)
	if return_values is None:
		sys.exit(4)
	print return_values['output']
	sys.exit(return_values['code'])

if __name__ == "__main__":
   main(sys.argv[1:])

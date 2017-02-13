#!/usr/bin/python
# ####################################################################
# Script Description :  Nagios/Shinken/centreon/icinga script for 
#                        alerting via netdata source
# Author:   Guillaume Seigneuret
# Date:     08/05/2016
# Version:  1.0
#
# Usage:        Utilisation:
#    netdata_to_nagios.py -H host -p port [-D <datasource>] [-i <interval>] [-c <90>] [-w <80>]
#    
#    Options:
#     -h, --help 
#        Show detailed help
#     -H, --host
#        Specify remote netdata host address
#        Default : 127.0.0.1
#     -p, --port
#        Specify remote netdata port
#        Default : 19999
#     -D, --datasource
#        Specify which datasource you want to check. 
#        Available datasources :
#            - apps.cpu (default)
#            - system.ram
#            - disk_util.sda
#            - disk_space._home
#            - apache_local.workers
#            - nginx_local.connections : Check nginx connections
#     -i interval
#        Specify an interval in seconds (minimum 2)
#        Default : 2
#     -w, --warning
#        Specify warning threshold
#     -c, --critical
#        Specify critical threshold
#
# Usage domain: Made to be lauched by Nagios or Shinken or Centreon or Incinga
#
# Config file:  None
#
# Prerequisites : 
#        - Python 2.7
#        - Netdata on client side
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
import urllib2
import pprint

def usage():
    usage = """
    Utilisation:
    netdata_to_nagios.py -H host -p port [-D <datasource>] [-i <interval>] -w <80> -c <90>
    
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
            - apps.cpu (default) Check CPU load per process
            - system.ram : Check REAL RAM consumption
			- system.cpu : Gives CPU laod system view (user, system, nice, irq, softirq, iowait)
            - disk_util.sda : Check disk load (sda, sdb,... can specify the name of your drive)
            - disk_space._ : Check disk space (_ for /, _mnt_disk1 for /mnt/disk1)
            - apache_local.workers : Check apache worker utilization 
            - nginx_local.connections : Check nginx connections
     -i interval
        Specify an interval in seconds (minimum 2)
        Default : 60
        
     -w, --warning
        Specify warning threshold
        
     -c, --critical
        Specify critical threshold
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

def init_datastruct(warn,crit):
    datastruct = dict( \
        ok_flag=False, \
        warning_flag=False, \
        critical_flag=False, \
        sysexitcode=0, \
        warning_buffer="Warning : ", \
        critical_buffer="Critical : ", \
        output_buffer="", \
        perfdata_buffer=" | ", \
        res = dict(), \
        warn=float(warn), \
        crit=float(crit), \
    )
    
    return datastruct

def get_simple_datasource(hostaddress,port,datasource,interval):
    URL = ""
    if (abs(int(interval)) < 1) or (abs(int(interval)) > 3600):
        print "Interval problem, should be between 1 and 3600: " + interval
        return None
    
    URL = 'http://'+hostaddress+':'+port+'/api/v1/data?chart='+datasource+'&after='+interval+'&options=seconds'
    
    req = urllib2.Request(URL)
    
    try:
        res = urllib2.urlopen(req, timeout=3)
    except IOError:
        print "Unable to connect to netdata node, or datasource unknown :("
        sys.exit(3)
        
    return json.loads(res.read())
    
        
def analyze_from_datasource(hostaddress,port,datasource,interval,warn,crit):
        
    datapoints = get_simple_datasource(hostaddress,port,datasource,interval)
    
    if re.match('disk_util',datasource) != None:
        splitted_datasource = re.split('(disk_util).(\w+)',datasource)
        datasource = splitted_datasource[1]
        disk = splitted_datasource[2]
        
    if re.match('disk_space',datasource) != None:
        splitted_datasource = re.split('(disk_space).(\w+)',datasource)
        datasource = splitted_datasource[1]
        partition = splitted_datasource[2]
        
    if datasource == "apps.cpu":
        return_value = analyze_cpu_per_process(datapoints,warn,crit)
        
    elif datasource == "system.ram":
        return_value = analyze_ram(datapoints,warn,crit)
        
    elif datasource == "disk_util":
        return_value = analyze_disk(datapoints,disk,warn,crit)
        
    elif datasource == "disk_space":
        return_value = analyze_disk_space(datapoints,partition,warn,crit)
        
    elif datasource == "system.cpu":
        return_value = analyze_system_cpu(datapoints,warn,crit)
        
    elif re.match('apache(.*).workers',datasource) != None: 
        datasource_connections = re.sub(r'(apache.*).workers',r'\1.connections', datasource)
        datasource_requests = re.sub(r'(apache.*).workers',r'\1.requests', datasource)
        
        apache_connections = get_simple_datasource(hostaddress,port,datasource_connections,interval)
        apache_requests = get_simple_datasource(hostaddress,port,datasource_requests,interval)
        
        return_value = analyze_apache_workers(datapoints, apache_connections, apache_requests, warn,crit)
        
    elif re.match('nginx(.*).connections',datasource) != None: 
        return_value = analyze_nginx_connections(datapoints,warn,crit)
    else: 
        return None
    
    return return_value 

def analyze_nginx_connections(datapoints,warn,crit):
    ds = init_datastruct(warn,crit)
    
    res = dict()
    nb_of_datapoints = len(datapoints['data'])
    
    connections = 0
    
    #"labels": ["time", "active"],
    index_active = datapoints['labels'].index("active")
    for time in range(0, nb_of_datapoints):
        connections += datapoints['data'][time][index_active]
        
    connections_mean = int(connections / nb_of_datapoints)
    
    ds['perfdata_buffer'] += "time=%s, nginx_connections=%s" % (datapoints['data'][-1][0], connections_mean)
    
    if connections_mean >= ds['warn'] and connections_mean < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, nginx max connections almost reached : %d" % (connections_mean)
    elif connections_mean >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, nginx max connections reached : %d" % (connections_mean)
    else:
        ds['output_buffer']="Connections OK"
        ds['ok_flag']=True
        
    ds['output_buffer'] += ds['perfdata_buffer']
    res['output'] = ds['output_buffer']
    res['code'] = sysexit(ds['ok_flag'],ds['warning_flag'],ds['critical_flag'])
    
    return res
    
def analyze_apache_workers(datapoints,apache_connections, apache_requests, warn,crit):
    ds = init_datastruct(warn,crit)
    
    res = dict()
    nb_of_datapoints = len(datapoints['data'])
    
    #"labels": ["time", "idle", "busy"]
    index_idle = datapoints['labels'].index("idle")
    index_busy = datapoints['labels'].index("busy")
    max_workers = datapoints['data'][0][index_idle] + datapoints['data'][0][index_busy]
    
    # Connections
    nb_of_datapoints_conn = len(apache_connections['data'])
    index_conn = apache_connections['labels'].index("connections")
    connections = 0
    
    #print dict(apache_connections)
    
    for time in range(0, nb_of_datapoints_conn):
        connections += apache_connections['data'][time][index_conn]
        
    connections = connections/nb_of_datapoints_conn
    
    # Requests
    nb_of_datapoints_req = len(apache_requests['data'])
    index_req = apache_requests['labels'].index("requests")
    requests = 0
    
    for time in range(0, nb_of_datapoints_req):
        requests += apache_requests['data'][time][index_req]
    
    requests = requests/nb_of_datapoints_req
    
    worker_usage = 0
    
    for time in range(0, nb_of_datapoints):
        worker_usage += datapoints['data'][time][index_busy]
        
    worker_usage = float(worker_usage)
    worker_mean_usage = ((worker_usage/nb_of_datapoints)/max_workers)*100
    
    ds['perfdata_buffer'] += "time=%s, worker_usage=%s, connections=%s, requests=%s" % (datapoints['data'][-1][0], worker_mean_usage, connections, requests)
    
    if worker_mean_usage >= ds['warn'] and worker_mean_usage < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, apache max worker almost reached : %.2f %%" % (worker_mean_usage)
    elif worker_mean_usage >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, apache max worker reached : %.2f %%" % (worker_mean_usage)
    else:
        ds['output_buffer']="Workers OK : %.2f %%" % (worker_mean_usage)
        ds['ok_flag']=True
        
    ds['output_buffer'] += ds['perfdata_buffer']
    res['output'] = ds['output_buffer']
    res['code'] = sysexit(ds['ok_flag'],ds['warning_flag'],ds['critical_flag'])
    
    return res
    
def analyze_system_cpu(datapoints,warn,crit):
    ds = init_datastruct(warn,crit)
    
    res = dict()
    nb_of_datapoints = len(datapoints['data'])
    
    softirq = 0
    irq = 0
    user = 0
    system = 0
    nice = 0
    iowait = 0
    
    index_guest_nice = datapoints['labels'].index("guest_nice")
    index_guest = datapoints['labels'].index("guest")
    index_steal = datapoints['labels'].index("steal")
    index_softirq = datapoints['labels'].index("softirq")
    index_irq = datapoints['labels'].index("irq")
    index_user = datapoints['labels'].index("user")
    index_system = datapoints['labels'].index("system")
    index_nice = datapoints['labels'].index("nice")
    index_iowait = datapoints['labels'].index("iowait")
    
    for time in range(0, nb_of_datapoints):
        #"labels": ["time", "guest_nice", "guest", "steal", "softirq", "irq", "user", "system", "nice", "iowait"]
        #               0             1        2        3          4      5       6         7       8         9
        softirq += datapoints['data'][time][index_softirq]
        irq += datapoints['data'][time][index_irq]
        user += datapoints['data'][time][index_user]
        system += datapoints['data'][time][index_system]
        nice += datapoints['data'][time][index_nice]
        iowait += datapoints['data'][time][index_iowait]
        
    last_point = datapoints['data'][-1][0]
    
    softirq = softirq/nb_of_datapoints
    irq     = irq/nb_of_datapoints
    user    = user/nb_of_datapoints
    system  = system/nb_of_datapoints
    nice    = nice/nb_of_datapoints
    iowait  = iowait/nb_of_datapoints
    
    ds['perfdata_buffer'] += "time=%s, soft_irq=%s, irq=%s, user=%s, system=%s, nice=%s, iowait=%s" \
        % (last_point,softirq,irq,user,system,nice,iowait)
    
    if softirq >= ds['warn'] and softirq < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, network driver may have an issue: soft_irq=%s%" % (softirq)
    elif softirq >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, network driver may have an issue: soft_irq=%s%" % (softirq)
        
    elif irq >= ds['warn'] and irq < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, lots of interruptions: irq=%s%%" % (irq)
    elif irq >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, lots of interruptions: irq=%s%%" % (irq)    
        
    elif user >= ds['warn'] and user < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, an application is highly loaded: user=%s%%" % (user)
    elif user >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, an application is highly loaded: user=%s%%" % (user)
        
    elif system >= ds['warn'] and system < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, system is highly loaded: system=%s%%" % (system)
    elif system >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, system is highly loaded: system=%s%%" % (system)
     
    elif nice >= ds['warn'] and nice < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, scheduling overhead too high: nice=%s%%" % (nice)
    elif nice >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, scheduling overhead too high: nice=%s%%" % (nice)
     
    elif iowait >= ds['warn'] and iowait < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Warining, a disk may be slowing everybody down: iowait=%s%%" % (iowait)
    elif iowait >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical, a disk may be slowing everybody down: iowait=%s%%" % (iowait)
     
    else:
        ds['output_buffer']="CPU OK"
        ds['ok_flag']=True

    ds['output_buffer'] += ds['perfdata_buffer']
    res['output'] = ds['output_buffer']
    res['code'] = sysexit(ds['ok_flag'],ds['warning_flag'],ds['critical_flag'])
    
    return res
    
    return 0
 
def analyze_disk(datapoints,disk,warn,crit):
    ds = init_datastruct(warn,crit)
    
    res = dict()
    nb_of_datapoints = len(datapoints['data'])
    
    occupation_time = 0
    for time in range(0, nb_of_datapoints):
        occupation_time += datapoints['data'][time][1]
        last_point = datapoints['data'][time][0]
    
    occupation_time = occupation_time/nb_of_datapoints
    occ_time_str = str(occupation_time)
    ds['perfdata_buffer'] += "time="+str(last_point)+", occupation_time="+occ_time_str
    
    if occupation_time >= ds['warn'] and occupation_time < ds['crit']:
        ds['warning_flag'] = True
        ds['output_buffer'] += "Occupation time of "+disk+" : "+occ_time_str+"%"
    elif occupation_time >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Occupation time of "+disk+" : "+occ_time_str+"%"
    else:
        ds['output_buffer']="OK : %.2f %%" % occupation_time
        ds['ok_flag']=True

    ds['output_buffer'] += ds['perfdata_buffer']
    res['output'] = ds['output_buffer']
    res['code'] = sysexit(ds['ok_flag'],ds['warning_flag'],ds['critical_flag'])
    
    return res
    
    return 0
    
def analyze_disk_space(datapoints,partition,warn,crit):
    ds = init_datastruct(warn,crit)
    
    res = dict()
    nb_of_datapoints = len(datapoints['data'])
    
    used_space = 0
    #["time", "avail", "used", "reserved for root"]
    index_avail = datapoints['labels'].index("avail")
    index_used = datapoints['labels'].index("used")
    index_reserved = datapoints['labels'].index("reserved for root")
    
    total_available = datapoints['data'][0][index_avail] + datapoints['data'][0][index_used] + datapoints['data'][0][index_reserved]
    for time in range(0, nb_of_datapoints):
        used_space += datapoints['data'][time][index_used]
        
    last_point = datapoints['data'][-1][0]

    used_space = ((used_space/nb_of_datapoints)/total_available)*100
    used_space_str = str(used_space)
    
    ds['perfdata_buffer'] += "time="+str(last_point)+", "+partition+"="+used_space_str
    
    if used_space >= ds['warn'] and available_space < ds['crit']:
        ds['warning_flag']=True
        ds['output_buffer'] += "Warning space left on "+partition+" : "+used_space_str+"%"
    elif used_space >= ds['crit']:
        ds['critical_flag'] = True
        ds['output_buffer'] += "Critical space left on "+partition+" : "+used_space_str+"%"
    else:
        ds['output_buffer']="OK : %.2f %%" % used_space
        ds['ok_flag']=True

    ds['output_buffer'] += ds['perfdata_buffer']
    res['output'] = ds['output_buffer']
    res['code'] = sysexit(ds['ok_flag'],ds['warning_flag'],ds['critical_flag'])
    
    return res
    
    return 0
       
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
    index_buffer = datapoints['labels'].index("buffers")
    index_used = datapoints['labels'].index("used")
    index_cached = datapoints['labels'].index("cached")
    index_free = datapoints['labels'].index("free")
    
    nb_of_datapoints=len(datapoints['data'])
    total_ram = datapoints['data'][0][index_buffer] + \
        datapoints['data'][0][index_used] + \
        datapoints['data'][0][index_cached] + \
        datapoints['data'][0][index_free]
        
    used_ram = 0
    used = 0
    buffers = 0
    cached = 0
    free = 0
    for time in range(0, nb_of_datapoints):
        used_ram = used_ram + datapoints['data'][time][index_buffer] + datapoints['data'][time][index_used]
        used += datapoints['data'][time][index_used]
        buffers += datapoints['data'][time][index_buffer]
        cached += datapoints['data'][time][index_cached]
        free += datapoints['data'][time][index_free]
        
    used_ram = used_ram/nb_of_datapoints
    used = used/nb_of_datapoints
    buffers = buffers/nb_of_datapoints
    cached = cached/nb_of_datapoints
    free = free/nb_of_datapoints
    
    used_ram_proportion = used_ram / total_ram * 100
    
    perfdata_buffer+="time="+str(datapoints['data'][0][0])+", used="+str(used)+", buffers="+str(buffers)+", cached="+str(cached)+", free="+str(free)
    
    if used_ram_proportion >= warn and used_ram_proportion < crit:
        warning_flag=True
        output_buffer += "RAM used at %.2f %%" % used_ram_proportion
    elif used_ram_proportion >= crit:
        critical_flag=True
        output_buffer += "RAM used at %.2f %%" % used_ram_proportion
    else:
        output_buffer="OK : %.2f %%" % used_ram_proportion
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
            warning_buffer+=" "+process+","
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
            sys.exit(3)
    hostaddress = '127.0.0.1'
    port = '19999'
    interval = '-60'
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
            interval= str(0-int(arg))

    try: 
        warning
    except NameError:
        print "Missing warning threshold !"
        print usage()
        sys.exit(3)
    
    try:
        critical
    except NameError:
        print "Missing critical threshold !"
        print usage()
        sys.exit(3)

    return_values = analyze_from_datasource(hostaddress,port,datasource,interval,warning,critical)
    if return_values is None:
        sys.exit(3)
    print return_values['output']
    sys.exit(return_values['code'])

if __name__ == "__main__":
   main(sys.argv[1:])

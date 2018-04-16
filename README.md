Netdata to Nagios, a plugin for alerting on Netdata perfcounters and for long term storage
==========================================================================================

```
root@Nagios:~# python nagios_netdata.py -H 127.0.0.1 -D apps.cpu -i 60 -w 80 -c 90
OK | kernel=0.070277775, log=0.000277777777778, system=0.0130555555556, inetd=0, cron=0.00333333333333, ksmd=0, other=0.000277777777778, lxc=0, ssh=0.00833333055556, netdata=1.35777795556, apache=0.00333333333333, nms=0.025,
```

Table of Contents:
------------------

* [Introduction](#intro)
* [Install](#install)
* [Command options](#options)


<img src="http://www.omegacube.fr/static/img/grafana.png">
Example of graphic in grafana generated with this plugin.

<a name="intro"></a>
### Introduction
Netdata to Nagios is a plugin that allows you to get alert via Netdata perfcounter source. 
<a href=https://github.com/firehol/netdata>Netdata</a> is a neat project that gives you real time metrology.
The plugins works with Nagios, Shinken, Icinga and Centreon.
It also gives perfdata for long time metrology.

<a name="install"></a>
### Install and Config
The plugin only needs Python 2.7, no additional dependancy/module.
It as only be tested on Linux but should perferctly works on other Unix and Windows systems since there is no operating system commands or operating system specific call.


To install the plugin, just paste the file into your plugin diretory and configure your monitoring system like so :

```
cp netdata_to_nagios.py /usr/libexec/nagiosplugins/
chmod +x netdata_to_nagios.py
```

Generic command :
```
define command{
    command_name    check_memory_via_netdata
    command_line    $PLUGIN_PATH$/netdata_to_nagios.py -H $HOSTADDRESS$ -p $ARG1$ -D $ARG2$ -i $ARG3$ -w $ARG4$ -c $ARG5$
}
```
Monitor memory usage:	
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             Memory Usage
    check_command                   check_memory_via_netdata!19999!system.ram!2!80!90
}
```

Monitor CPU usage per application, will alert on which process consume to much CPU:
Can help finding which application is consuming CPU ressources
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!apps.cpu!60!80!90 ; Average cpu load during last 60 seconds
}
```	

Monitor CPU usage at a system level:
Can help finding if CPU is busy because of iowait, irq, system operations, etc.
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!system.cpu!60!80!90 ; Average cpu load during last 60 seconds
}
```

Monitor disk space:
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!disk_space._!60!80!90 ; monitor / partition
}
```

Monitor disk load:
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!disk_util.sda!60!80!90 ; Average load during last 60 seconds
}
```	

Monitor Apache workers:
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!apache_local.workers!60!80!90 ; Average worker consumption during last 60 seconds
}
```

Monitor Nginx workers:
```	
define service{
    use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!nginx_local.connections!60!1900!2048 ; Average worker consumption during last 60 seconds
}
```

<a name="options"></a>
### Command options

Here is the full command options manual :

```
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
            - apps.cpu                  (default) Check CPU load per process
            - system.ram :              Check REAL RAM consumption
            - system.cpu :              Gives CPU laod system view (user, system, nice, irq, softirq, iowait)
            - disk_util.sda :           Check disk load (sda, sdb,... can specify the name of your drive)
            - disk_space.sda1 :         Check disk space (sda2, sdb1,... can specify the name of your partition)
            - apache_local.workers :    Check Apache worker consumption
            - nginx_local.connections : Check nginx connections
            - mdstat.mdstat_health :    Check if there is a faulty md raid array
            
     -i interval
        Specify an interval in seconds (minimum 2)
        Default : 60
        
     -w, --warning
        Specify warning threshold
        
     -c, --critical
        Specify critical threshold

```

More probes will be added soon.

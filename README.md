Netdata to Nagios, a plugin for alerting on Netdata perfcounters
=================================================================

```
root@Nagios:~# python nagios_netdata.py -H 127.0.0.1 -D apps.cpu -i 60 -w 80 -c 90
OK | kernel=0.070277775, log=0.000277777777778, system=0.0130555555556, inetd=0, cron=0.00333333333333, ksmd=0, other=0.000277777777778, lxc=0, ssh=0.00833333055556, netdata=1.35777795556, apache=0.00333333333333, nms=0.025,
```

Table of Contents:
------------------

* [Introduction] (#intro)
* [Install] (#install)
* [Command options] (#options)


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

Monitor memory usage:
```
define command{
    command_name    check_memory_via_netdata
    command_line    $PLUGIN_PATH$/netdata_to_nagios.py -H $HOSTADDRESS$ -p $ARG1$ -D system.ram -i $ARG2$ -w $ARG3$ -c $ARG4$
}
		
define service{
	use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             Memory Usage
    check_command                   check_memory_via_netdata!19999!2!80!90
}
```

Monitor CPU usage per application, will alert on which process consume to much CPU:
```
define command{
    command_name    check_cpu_via_netdata
    command_line    $PLUGIN_PATH$/netdata_to_nagios.py -H $HOSTADDRESS$ -p $ARG1$ -D apps.cpu -i $ARG2$ -w $ARG3$ -c $ARG4$
}
		
define service{
	use                             generic-service         ; Name of service template to use
    host_name                       mymachine
    service_description             CPU Usage per process
    check_command                   check_cpu_via_netdata!19999!60!80!90
}
```
<a name="options"></a>
### Command options

Here is the full command options manual :

```
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
            - disk_util.sda (sda, sdb,... can specify the name of your drive)

     -i interval
        Specify an interval in seconds (minimum 2)
        Default : 60

     -w, --warning
        Specify warning threashold

     -c, --critical
        Specify critical threashold
```

More probes will be added soon.

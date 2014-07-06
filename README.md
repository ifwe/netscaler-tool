# netsclaler-tool

## System Requirements
*  python >= 2.6 and python < 3
*  pip install -r requirements.txt

## NetScaler Requirements
*  Known to work with NS9.3
*  System user account that has appropriate access
  * Depending on your use case, you might only need a system user that is read-only

## Installation
__Notes__:
* Please replace __\<tag\>__ with version you wish to use
* By default, the log file is /var/log/netscaler-tool/netscaler-tool.log, but can be changed with --logfile

### RPM Spec File
1. Download tar.gz specific version of the repo
 1. `https://github.tagged.com/bglogower/netscaler-tool/archive/v<tag>.tar.gz`
1. Use included rpm spec (python-netscalertool.spec) file and newly downloaded tar.gz file to build a rpm
 1. tar xzvf netscaler-tool-\<tag\>.tar.gz netscaler-tool-\<tag\>/python-netscalertool.spec
 1. http://wiki.centos.org/HowTos/SetupRpmBuildEnvironment

## Configuration
1.  Copy netscalertool.conf.example to /etc/netscalertool.conf
1.  Update __user__ to a NetScaler system user
1.  Update __passwd__ for the NetScaler system user
1.  Optional
  * Update __manage_vservers__ with a list of vserver you want to manage
  * Update __external_nodes__ with a script that returns a newline separated list of
    hosts that are allowed to be managed

## Usage
The netscaler-tool is really just a wrapper around netscalerapi.py. If you would like to write your own tool, but not have to worry about interacting with the NetScaler Nitro API, you can just use netscalerapi.py.

The netscaler-tool can take -h or --help optional argument at anytime:

    ./netscalertool.py --help
    usage: netscalertool.py [-h] [--user USER] [--passwd PASSWD] [--nodns]
                            [--debug] [--dryrun]
                            NETSCALER {show,stat,compare,enable,disable,bounce}
                            ...

    positional arguments:
      NETSCALER             IP or name of NetScaler.
      {show,stat,compare,enable,disable,bounce}
        show                sub-command for showing objects
        stat                sub-command for showing object stats
        compare             sub-command for comparing objects
        enable              sub-command for enable objects
        disable             sub-command for disabling objects
        bounce              sub-command for bouncing objects

    optional arguments:
      -h, --help            show this help message and exit
      --user USER           NetScaler user account.
      --passwd PASSWD       Password for user. Default is to fetch from
                            netscalertool.conf
      --nodns              Won't try to resolve any NetScaler objects
      --debug               Shows what's going on
      --dryrun              Dryrun

    ./netscalertool.py 192.168.1.10 show --help
    usage: netscalertool.py NETSCALER show [-h]

                                           {lb-vservers,lb-vserver,cs-vservers,server,servers,services,primary-node,ssl-certs,surge-total,saved-config,running-config,system}
                                       ...

    positional arguments:
      {lb-vservers,lb-vserver,cs-vservers,server,servers,services,primary-node,ssl-certs,surge-total,saved-config,running-config,system}
        lb-vservers         Shows all lb vservers
        lb-vserver          Shows stat(s) of a specified lb vserver
        cs-vservers         Shows all cs vservers
        server              Shows server info
        servers             Shows all servers
        services            Shows all services
        primary-node        Shows which of the two nodes is primary
        ssl-certs           Shows ssl certs and days until expiring
        surge-total         Shows surge total for a lb vserver
        saved-config        Shows saved ns config
        running-config      Shows running ns config
        system              Shows system counters

    optional arguments:
      -h, --help            show this help message and exit


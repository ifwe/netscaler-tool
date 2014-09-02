netscaler-tool
===============

System Requirements
-------------------

-  Python >= 2.6 and Python < 3
-  Python modules are in requirements.txt

NetScaler Requirements
----------------------

-  Known to work with NS9.3 and NS10.1
-  System user account that has appropriate access
-  Depending on your use case, you might only need a system user that
   has read-only permissions

Installation
------------

From PyPI
~~~~~~~~~

**Notes**

-  Don't forget to `modify <#configure>`__ **/etc/netscalertool.conf**
   after installation

   ::

       sudo pip install netscaler-tool
       sudo mkdir -p /var/log/netscaler-tool
       sudo touch /var/log/netscaler-tool/netscaler-tool.log
       sudo chown <user>:<group> /var/log/netscaler-tool/netscaler-tool.log
       sudo chmod <mode> /var/log/netscaler-tool/netscaler-tool.log
       sudo wget -O /etc/netscalertool.conf  https://github.com/tagged/netscaler-tool/blob/master/netscalertool.conf.example

From RPM
~~~~~~~~

**Notes**

-  Please replace **<tag>** with the version you wish to use
-  The rpm will create:

   1. A sample **/etc/netscalertool.conf** that needs to be modified
   2. Directory **/var/log/netscaler-tool**. It is up to you to create
      **/var/log/netscaler-tool/netscaler-tool.log** with the correct
      permissions

1. Download tar.gz specific version of the repo

   -  ``https://github.com/tagged/netscaler-tool/releases/tag/v<tag>.tar.gz``

2. Use included rpm spec (python-netscalertool.spec) file and newly
   downloaded tar.gz file to build a rpm

   1. ``tar xzvf netscaler-tool-\<tag\>.tar.gz netscaler-tool-\<tag\>/python-netscalertool.spec``
   2. http://wiki.centos.org/HowTos/SetupRpmBuildEnvironment

From Source
~~~~~~~~~~~

1. git clone https://github.com/tagged/netscaler-tool.git
2. cd netscaler-tool
3. sudo python setup.py install
4. sudo mkdir -p /var/log/netscaler-tool
5. sudo touch /var/log/netscaler-tool/netscaler-tool.log
6. sudo chown <user>:<group> /var/log/netscaler-tool/netscaler-tool.log
7. sudo chmod <mode> /var/log/netscaler-tool/netscaler-tool.log
8. sudo cp netscalertool.conf.example /etc/netscalertool.conf
9. Modify /etc/netscalertool.conf

Configuration
-------------

1. Update **user** to a NetScaler system user
2. Update **passwd** for the NetScaler system user
3. (Optional)

   -  Update **manage\_vservers** with a list of vserver you want to
      manage
   -  Update **external\_nodes** with a script that returns a newline
      separated list of nodes that are allowed to be managed. If not
      set, all nodes are manageable

Usage
-----

The netscaler-tool is really just a wrapper around netscalerapi.py. If
you would like to write your own tool, but not have to worry about
interacting with the NetScaler Nitro API, you can use netscalerapi.py.

The netscaler-tool can take -h or --help optional argument at anytime:

::

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
                            /etc/netscalertool.conf
      --nodns               Won't try to resolve any NetScaler objects
      --debug               Shows what's going on
      --dryrun              Dryrun

    ./netscalertool.py 192.168.1.10 show --help
    usage: netscalertool.py NETSCALER show [-h]

                                           {lb-vservers,lb-vserver,cs-vservers,server,servers,services,primary-node,ssl-certs,saved-config,running-config,system}
                                       ...

    positional arguments:
      {lb-vservers,lb-vserver,cs-vservers,server,servers,services,primary-node,ssl-certs,saved-config,running-config,system}
        lb-vservers         Shows all lb vservers
        lb-vserver          Shows stat(s) of a specified lb vserver
        cs-vservers         Shows all cs vservers
        server              Shows server info
        servers             Shows all servers
        services            Shows all services
        primary-node        Shows which of the two nodes is primary
        ssl-certs           Shows ssl certs and days until expiring
        saved-config        Shows saved ns config
        running-config      Shows running ns config
        system              Shows system counters

    optional arguments:
      -h, --help            show this help message and exit


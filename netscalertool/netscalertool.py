#!/usr/bin/env python

import argparse
import logging
import netscalerapi
import os
import re
import socket
import subprocess
import sys
import tagops
import yaml


# simplejson is used on CentOS 5, while
# json is used on CentOS 6.
# Trying to import json first, followed
# by simplejson second if there is a failure
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError, e:
        print >> sys.stderr, e
        sys.exit(1)

if os.getenv('SUDO_USER'):
    user = os.getenv('SUDO_USER')
else:
    user = os.getenv('USER')


# Setting up logging
logFile = '/var/log/netscaler-tool/netscaler-tool.log'
try:
    localHost = socket.gethostbyaddr(socket.gethostname())[1][0]
except socket.herror, e:
    localHost = 'localhost'
logger = logging.getLogger(localHost)
logger.setLevel(logging.INFO)

try:
    ch = logging.FileHandler(logFile)
except IOError, e:
    print >> sys.stderr, e
    sys.exit(1)

ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s', datefmt='%b %d %H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)

netscaler_tool_config = "/etc/tagops/netscalertool.conf"


# Used for nicely printing a list
def printList(list):
    for entry in list:
        print entry

    return 0


# Used for printing certain items of a dictionary with output as json
def print_items_json(dict,*args):
    new_dict = {}
    # Testing to see if any attrs were passed
    # in and if so only print those key/values.
    if args[0]:
        for key in sorted(args[0]):
            try:
                new_dict[key] = dict[key]
            except KeyError:
                raise

    print json.dumps(new_dict)

    return 0


# Used by argparse to see if the host specified is alive (pingable)
# Maybe we can have it check the DB to see if the host is a netscaler as well.
class isPingableAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        pingCmd = ['ping','-c','1','-W','2',values]
        process = subprocess.call(pingCmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

        if process != 0:
            msg = "%s is not alive." % (values)
            print >> sys.stderr, msg
            return sys.exit(1)

        setattr(namespace, self.dest, values)


class allowed_to_manage(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            f = open(netscaler_tool_config,'r')
        except IOError, e:
            print >> sys.stderr, e
            sys.exit(1)

        ns_config = yaml.load(f)
        f.close()

        # Checking if specified server is allowed to be managed
        if namespace.subparserName == "server":
            serverList = []
            sql = "SELECT hostname FROM hosts WHERE environment = 'production' ORDER BY hostname"
            try:
                db = tagops.tagOpsReader()
                db.connect()
                output = db.execute(sql)
                db.close()
            except RuntimeError, e:
                print >> sys.stderr, e
                return sys.exit(1)

            for server in output:
                serverList.append(server[0])

            if values in serverList:
                msg = "%s is a production server. You can not enable/disable a production server at this time."\
                      % (values)
                print >> sys.stderr, msg
                logger.info(msg)
                return sys.exit(1)
        # Checking if specified vserver allowed to be managed
        elif namespace.subparserName == "vserver":
            if values not in ns_config["manage_vservers"]:
                msg = "%s is a vserver that is not allowed to be managed. If you would like to change this, please " \
                      "update %s." % (values, netscaler_tool_config)
                print >> sys.stderr, msg
                logger.info(msg)
                return sys.exit(1)

        setattr(namespace, self.dest, values)


class Base(object):
    def __init__(self,args):
        self.args = args
        self.host = args.host
        self.user = args.user
        try:
            self.passwd = self.fetch_passwd(netscaler_tool_config)
        except IOError, e:
            raise
        self.debug = args.debug
        self.dryrun = args.dryrun


    def createClient(self):
        # Creating a client instance
        try:
            self.client = netscalerapi.Client(self.host,self.user,self.passwd,self.debug)
        except RuntimeError, e:
            msg = "Problem creating client instance.\n%s" % (e)
            raise RuntimeError(msg)

        # Login using client instance
        try:
            self.client.login()
        except RuntimeError, e:
            raise RuntimeError(e)

        return self.client


    # Grabs passwd from passwd file.
    def fetch_passwd(self,netscaler_tool_config):
        try:
            f = open(netscaler_tool_config)
        except IOError:
            raise

        # Grab the passwd entry
        passwd = yaml.load(f)['passwd']
        f.close()

        # Returning passwd
        return passwd


    def getBoundServices(self,vserver):
        object = ["lbvserver_binding",vserver]
        listOfBoundServices = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        for service in output['lbvserver_binding'][0]['lbvserver_service_binding']:
            listOfBoundServices.append(service['servicename'])

        listOfBoundServices.sort()
        return listOfBoundServices


    def getSavedConfig(self):
        object = ["nssavedconfig"]

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "There was a problem getting the saved config: %s" % (e)
            raise RuntimeError(msg)

        return output['nssavedconfig']['textblob']


    def getRunningConfig(self):
        object = ["nsrunningconfig"]

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "There was a problem getting the running config: %s" % (e)
            raise RuntimeError(msg)

        return output['nsrunningconfig']['response']


    def getLbvserverServiceBinding(self,vserver):
        servicesIps = {}

        object = ["lbvserver_service_binding",vserver]
        try:
            services = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get info about LB vserver %s on %s.\n%s" % (vserver,self.host,e)
            raise RuntimeError(msg)

        for service in services[object[0]]:
            servicesIps[str(service['servicename'])] = str(service['ipv46'])

        return servicesIps


    def getLb(self):
        attr = self.args.attr
        vserver = self.args.vserver

        object = ["lbvserver",vserver]
        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get info about LB vserver %s on %s.\n%s" % (vserver,self.host,e)
            raise RuntimeError(msg)

        return output[object[0]][0],attr


    def getServerBinding(self,server):
        services = []
        object = ["server_binding",server]
        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get server binding for server %s on %s.\n%s" % (server,self.host,e)
            raise RuntimeError(msg)

        for service in output[object[0]][0]['server_service_binding']:
            services.append(service['servicename'])

        return services


    def getServerBindingServiceDetails(self,server):
        services = {}
        object = ["server_binding",server]

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get server binding for server %s on %s.\n%s" % (server,self.host,e)
            raise RuntimeError(msg)

        return output[object[0]][0]['server_service_binding']

    def vserver(self):
        pass


class Show(Base):
    def __init__(self,args):
        super(Show, self).__init__(args)
        self.client = self.createClient()


    def server(self):
        server = self.args.server

        if self.args.services:
            try:
                list = self.getServerBindingServiceDetails(server)
            except RuntimeError, e:
                msg =  "Problem while trying to get list of services bound to %s.\n%s" % (server,e)
                raise RuntimeError(msg)

            for entry in list:
                print json.dumps(entry)
        else:
            object = ["server",server]
            try:
                output = self.client.getObject(object)
            except RuntimeError, e:
                msg =  "Problem while trying to get list of servers on %s.\n%s" % (self.host,e)
                raise RuntimeError(msg)

            print json.dumps(output['server'][0])


    def servers(self):
        object = ["server"]
        listOfServers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg =  "Problem while trying to get list of servers on %s.\n%s" % (self.host,e)
            raise RuntimeError(msg)

        for server in output['server']:
            listOfServers.append(server['name'])

        printList(sorted(listOfServers))


    def services(self):
        object = ["service"]
        listOfServices = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg =  "Problem while trying to get list of services on %s.\n%s" % (self.host,e)
            raise RuntimeError(msg)

        for service in output['service']:
            listOfServices.append(service['name'])

        printList(sorted(listOfServices))


    def lbvservers(self):
        object = ["lbvserver"]
        listOfLbVservers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of LB vservers on %s.\n%s" % (self.host,e)
            raise RuntimeError(msg)

        for vserver in output['lbvserver']:
            listOfLbVservers.append(vserver['name'])

        printList(sorted(listOfLbVservers))


    def lbvserver(self):
        vserver = self.args.vserver
        attr = self.args.attr
        services = self.args.services
        servers = self.args.servers

        if services:
            output = self.getLbvserverServiceBinding(vserver)
            for service in sorted(output.keys()):
                print service
        elif servers:
            listOfServers = []
            output = self.getLbvserverServiceBinding(vserver)
            for service in sorted(output.keys()):
                try:
                    # Looking up IPs via DNS instead of asking the Netscaler for its
                    # service-to-server binding, since it is slow.
                    print socket.gethostbyaddr(output[service])[0].split('.')[0]
                except socket.herror, e:
                    raise RuntimeError(e)
        else:
            output,attrs = self.getLb()
            if attrs:
                print_items_json(output,attr)
            else:
                print json.dumps(output)



    def csvservers(self):
        object = ["csvserver"]
        listOfCsVservers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of CS vservers on %s.\n%s" % (host,e)
            raise RuntimeError(msg)

        for vserver in output['csvserver']:
            listOfCsVservers.append(vserver['name'])

        printList(sorted(listOfCsVservers))


    def primarynode(self):
        object = ["hanode"]

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get IP of primary node of %s.\n%s" % (host,e)
            raise RuntimeError(msg)

        # Grabbing the IP of the current primary
        print output['hanode'][0]['routemonitor']


    def savedconfig(self):
        print self.getSavedConfig()


    def runningconfig(self):
        print self.getRunningConfig()


    def getServiceStats(self,service,*args):
        mode = 'stats'
        object = ["service",service]
        DictOfServiceStats = {}

        if args:
            object.extend(args)

        try:
            output = self.client.getObject(object,mode)
        except RuntimeError, e:
            raise

        for stat in args:
            try:
                DictOfServiceStats[stat] = output['service'][0][stat]
            except KeyError, e:
                msg = "%s is not a valid stat." % (stat)
                raise KeyError(msg)

        return DictOfServiceStats


    def sslcerts(self):
        object = ["sslcertkey"]
        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise

        if self.args.debug:
            print "\n<SSL Cert Name>:<Days to Expiration>"
        for cert in output['sslcertkey']:
            print "%s:%s" % (cert['certkey'], cert['daystoexpiration'])


    def surgetotal(self):
        vserver = self.args.vserver
        surgeCountTotal = 0

        try:
            output = self.getBoundServices(vserver)
        except RuntimeError, e:
            msg = "Problem getting bound services to %s.\n%s" % (vserver,e)
            raise RuntimeError(msg)

        # Going through the list of services to get surge count.
        for service in output:
            try:
                output = self.getServiceStats(service,'surgecount')
            except RuntimeError, e:
                msg = "Problem getting surgecount of service %s.\n%s" % (service,e)
                raise RuntimeError(msg)

            surge = int(output['surgecount'])
            if self.args.debug:
                print "%s: %d" % (service,surge)
            surgeCountTotal += surge

        if self.args.debug:
            print "\nTotal Surge Queue Size is:"

        print surgeCountTotal

    def system(self):
        mode = 'stats'
        object = ["system" ]
        DictOfServiceStats = {}

        try:
            output = self.client.getObject(object,mode)
        except RuntimeError, e:
            raise
        print json.dumps(output['system'])


class Compare(Base):
    def __init__(self,args):
        super(Compare, self).__init__(args)
        self.client = self.createClient()


    def cleanupConfig(self,config,ignoreREs):
        newConfig = []
        for line in config:
            if not re.match(ignoreREs,line):
                newConfig.append(line)

        return newConfig


    def configs(self):
        # Regex that will be used to ignore lines we know are only in saved or
        # running configs, which will always show up in a diff.
        ignoreREs = "^# Last modified|^set appfw|^set lb monitor https? HTTP"

        # Getting saved and running configs. Splitting on newline
        # to make it easier to compare the two.
        saved = self.getSavedConfig().split('\n')
        running = self.getRunningConfig().split('\n')

        # Parsing configs and creating new lists that exclude
        # anything lines that much ignoreREs.
        saved = self.cleanupConfig(saved,ignoreREs)
        running = self.cleanupConfig(running,ignoreREs)

        # If the configs have differences, why have a problem
        if saved != running:
            # Converted lists to sets so we can find differences
            diff = set(saved) ^ set(running)

            # Returned the sets to lists for formatting purposes
            msg = "Saved and running configs are different:\n%s" % ('\n'.join(list(diff)))
            raise RuntimeError(msg)


    def lbvservers(self):
        dif = None
        vserver1 = self.args.vserver1
        vserver2 = self.args.vserver2

        # If the user tries to compare the same vservers
        if vserver1 == vserver2:
            msg = "%s and %s are the same vserver. Please pick two different vservers." % (vserver1,vserver2)
            raise RuntimeError(msg)

        # Getting a list of bound services to each vserver so that we
        # can compare.
        listOfServices1 = self.getLbvserverServiceBinding(vserver1)
        listOfServices2 = self.getLbvserverServiceBinding(vserver2)

        # If we get a diff, we will let the user know
        diff = set(listOfServices1) ^ set(listOfServices2)
        if diff:
            msg = "The following services are either bound to %s or %s but not both:\n%s" % (vserver1,vserver2,'\n'.join(sorted(list(diff))))
            raise RuntimeError(msg)


class Enable(Base):
    def __init__(self,args):
        super(Enable, self).__init__(args)
        self.client = self.createClient()

    def server(self):
        server = self.args.server
        services = self.getServerBinding(server)

        if self.args.debug:
            print "\nServices bound to %s: %s" % (server,services)

        for service in services:
            properties = {
                'params': {'action': "enable"},
                'service': {'name': str(service)},
            }

            try:
                if self.args.debug:
                    print "\nAttempting to enable service %s" % (service)
                self.client.modifyObject(properties)
            except RuntimeError, e:
                raise


    def vserver (self):
        vserver = self.args.vserver

        properties = {
            'params': {'action': "enable"},
            'vserver': {'name': str(vserver)},
        }

        try:
            if self.args.debug:
                print "\nAttempting to enable vserver %s" % (service)
            self.client.modifyObject(properties)
        except RuntimeError, e:
            raise

        super(Enable,self).vserver()


class Disable(Base):
    def __init__(self,args):
        super(Disable,self).__init__(args)
        self.client = self.createClient()

    def server(self):
        delay = self.args.delay
        server = self.args.server
        services = self.getServerBinding(server)

        if self.args.debug:
            print "\nServices bound to %s: %s" % (server,services)

        for service in services:
            properties = {
                'params': {'action': "disable"},
                'service': {
                    'name': str(service),
                    'delay': delay,
                    'graceful': 'YES',
                },
            }

            try:
                if self.args.debug:
                    print "\nAttempting to disable service %s" % (service)
                self.client.modifyObject(properties)
            except RuntimeError, e:
                raise


    def vserver(self):
        vserver = self.args.vserver

        properties = {
            'params': {'action': "disable"},
            'vserver': {'name': str(vserver)},
        }

        try:
            if self.args.debug:
                print "\nAttempting to enable vserver %s" % (service)
            self.client.modifyObject(properties)
        except RuntimeError, e:
            raise

        super(Disable,self).vserver()


class Bounce(Disable,Enable):
    def vserver(self):
        super(Bounce, self).vserver()


def main():
    # Created parser.
    parser = argparse.ArgumentParser()

    # Global args
    parser.add_argument("host", metavar='NETSCALER', action=isPingableAction, help="IP or name of NetScaler.")
    parser.add_argument("--user", dest="user", help="NetScaler user account.", default="***REMOVED***")
    parser.add_argument("--passwd", dest="passwd", help="Password for user. Default is to fetch from netscalertool.conf"
                                                        " for user ***REMOVED***.")
    parser.add_argument("--nodns", action="store_true", dest="noDns", help="Won't try to resolve any netscaler objects.", default=False)
    parser.add_argument("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_argument("--dryrun", action="store_true", dest="dryrun", help="Dryrun.", default=False)

    # Creating subparser.
    subparser = parser.add_subparsers(dest='topSubparserName')

    # Creating show subparser.
    parserShow = subparser.add_parser('show', help='sub-command for showing objects')
    subparserShow = parserShow.add_subparsers(dest='subparserName')
    parserShowLbVservers = subparserShow.add_parser('lb-vservers', help='Shows all lb vservers')
    parserShowLbVserver = subparserShow.add_parser('lb-vserver', help='Shows stat(s) of a specific lb vserver')
    parserShowLbVserver.add_argument('vserver', help='Shows stats for which vserver')
    parserShowLbVserverGroup = parserShowLbVserver.add_mutually_exclusive_group()
    parserShowLbVserverGroup.add_argument('--attr', dest='attr', nargs='*', help='Shows only the specified attribute(s)')
    parserShowLbVserverGroup.add_argument('--services', action='store_true', help='Shows services bound to specified lb vserver')
    parserShowLbVserverGroup.add_argument('--servers', action='store_true', help='Shows servers bound to specified lb vserver')
    parserShowCsVservers = subparserShow.add_parser('cs-vservers', help='Shows all cs vservers')
    parserShowServer = subparserShow.add_parser('server', help='Shows server info')
    parserShowServer.add_argument('server', help='Shows server details')
    parserShowServer.add_argument('--services', action='store_true', help='Shows services bound to server and their status')
    parserShowServers = subparserShow.add_parser('servers', help='Shows all servers')
    parserShowServices = subparserShow.add_parser('services', help='Shows all services')
    parserShowPrimaryNode = subparserShow.add_parser('primary-node', help='Shows which of the two nodes is primary')
    parserShowSslCerts = subparserShow.add_parser('ssl-certs', help='Shows ssl certs and days until expiring')
    parserShowSurgeTotal = subparserShow.add_parser('surge-total', help='Shows surge total for a lb vserver')
    parserShowSurgeTotal.add_argument('vserver', help='Shows surge total for which lb vserver')
    parserShowSavedConfig = subparserShow.add_parser('saved-config', help='Shows saved ns config')
    parserShowRunningConfig = subparserShow.add_parser('running-config', help='Shows running ns config')
    parserShowSystem = subparserShow.add_parser('system', help='Shows system counters')

    # Creating compare subparser.
    parserCmp = subparser.add_parser('compare', help='sub-command for comparing objects')
    subparserCmp = parserCmp.add_subparsers(dest='subparserName')
    parserCmpConfigs = subparserCmp.add_parser('configs', help='Compares running and saved ns configs')
    parserCmpLbVservers = subparserCmp.add_parser('lb-vservers', help='Compares configs between two vservers')
    parserCmpLbVservers.add_argument('vserver1', metavar='VSERVER1')
    parserCmpLbVservers.add_argument('vserver2', metavar='VSERVER2')

    # Creating enable subparser.
    parserEnable = subparser.add_parser('enable', help='sub-command for enable objects')
    subparserEnable = parserEnable.add_subparsers(dest='subparserName')
    parserEnableServer = subparserEnable.add_parser('server', help='Enable server. Will actually enable all servies bound to server')
    parserEnableServer.add_argument('server', action=allowed_to_manage, help='Server to enable')
    parserEnableVserver = subparserEnable.add_parser('vserver', help='Enable vserver')
    parserEnableVserver.add_argument('vserver', action=allowed_to_manage, help='Vserver to enable')

    # Creating disable subparser.
    parserDisable = subparser.add_parser('disable', help='sub-command for disabling objects')
    subparserDisable = parserDisable.add_subparsers(dest='subparserName')
    parserDisableServer = subparserDisable.add_parser('server', help='Disable server')
    parserDisableServer.add_argument('server', action=allowed_to_manage, help='Server to disable. Will actually disable all services bound to server')
    parserDisableServer.add_argument('--delay', type=int, help='The time allowed (in seconds) for a graceful shutdown. Defaults to 3 seconds', default=3)
    parserDisableVserver = subparserDisable.add_parser('vserver', help='Disable vserver')
    parserDisableVserver.add_argument('vserver', action=allowed_to_manage, help='Vserver to disable')

    # Creating disable subparser.
    parserBounce = subparser.add_parser('bounce', help='sub-command for bouncing objects')
    subparserBounce = parserBounce.add_subparsers(dest='subparserName')
    parserBounceVserver = subparserBounce.add_parser('vserver', help='Bounce vserver')
    parserBounceVserver.add_argument('vserver', action=allowed_to_manage, help='Vserver to bounce')

    # Getting arguments
    args = parser.parse_args()
    debug = args.debug

    retval = 0

    # Showing user flags and their values
    if debug:
        print "Using the following args:"
        for arg in dir(args):
            regex = "(^_{1,2}|^read_file|^read_module|^ensure_value)"
            if re.match(regex,arg):
                continue
            else:
                print "\t%s: %s" % (arg,getattr(args,arg))
        print "\n"

    # Getting method, based on subparser called from argparse.
    method = args.subparserName.replace('-','')

    # Getting class, based on subparser called from argparse.
    try:
        klass = globals()[args.topSubparserName.capitalize()]
    except KeyError:
        msg = "%s, %s is not a valid subparser." % (user,args.topSubparserName)
        print >> sys.stderr, msg
        logger.critical(msg)
        return 1

    try:
        netscalerTool = klass(args)
    except:
        print >> sys.stderr, sys.exc_info()[1]
        logger.critical(sys.exc_info()[1])
        return 1

    # Creating instance and calling one of its method
    # try-try-finally is due to a python 2.4 bug
    try:
        try:
            getattr(netscalerTool,method)()
            msg = "%s executed \'%s\' on %s" % (user,args,args.host)
            logger.info(msg)
        except (AttributeError,RuntimeError,KeyError,IOError):
            msg = "%s, %s" % (user,sys.exc_info()[1])
            print >> sys.stderr, "\n", msg, "\n"
            logger.critical(msg)
            retval = 1
    finally:
        # Saving config if we run a enable or disable command
        if args.topSubparserName in ["bounce","disable","enable"]:
            try:
                netscalerTool.client.saveConfig()
            except RuntimeError, e:
                print >> sys.stderr, "\n", e, "\n"
                logger.critical(msg)
                retval = 1

        # Logging out of NetScaler.
        try:
            netscalerTool.client.logout()
        except RuntimeError, e:
            msg = "%s, %s" % (user,e)
            print >> sys.stderr, msg
            logger.warn(msg)
            retval = 1

        # Exiting program
        return retval


# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


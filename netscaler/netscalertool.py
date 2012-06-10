#!/usr/bin/env python

import sys
import argparse
import json
import netscalerapi
import format
import re
import socket
import subprocess

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


class resolvesAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not noDns:
            try:
                for item in values:
                    socket.gethostbyaddr(item)
            except socket.gaierror, e:
                print >> sys.stderr, "%s does not resolve." % (item)
                return 1

            setattr(namespace, self.dest, values)


class Shared():
    def __init__(self,args):
        self.host = args.host
        self.user = args.user
        self.passwd = self.fetchPasswd(args.passwdFile)
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
    def fetchPasswd(self,passwdFile):
        try:
            f = open(passwdFile,'r')
        except IOError, e:
            raise IOError(e)

        # Reading contents of passwd file.
        passwd = f.readline().strip('\n')

        # Closing file handle
        f.close()

        # Returning passwd
        return passwd


    def getBoundServices(self,vserver):
        object = ['lbvserver_binding',vserver]
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
        object = ['nssavedconfig']

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "There was a problem getting the saved config: %s" % (e)
            raise RuntimeError(msg)

        return output['nssavedconfig']['textblob']


    def getRunningConfig(self):
        object = ['nsrunningconfig']

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "There was a problem getting the running config: %s" % (e)
            raise RuntimeError(msg)

        return output['nsrunningconfig']['response']


class Show():
    def __init__(self,args):
        self.args = args
        self.shared = Shared(self.args)
        self.client = self.shared.createClient()
    

    def services(self):
        object = ['service']
        listOfServices = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg =  "Problem while trying to get list of services on %s.\n%s" % (self.host,e)
            raise RuntimeError(msg)

        for service in output['service']:
            listOfServices.append(service['name'])

        format.printList(sorted(listOfServices))


    def lbvservers(self):
        object = ['lbvserver']
        listOfLbVservers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of LB vservers on %s.\n%s" % (self.host,e)
            raise RuntimeError(msg)

        for vserver in output['lbvserver']:
            listOfLbVservers.append(vserver['name'])

        format.printList(sorted(listOfLbVservers))


    def lbvserver(self):
        vserver = self.args.vserver
        attr = self.args.attr
        services = self.args.services

        if services:
            object = ['lbvserver_service_binding',vserver]
            try:
                output = self.client.getObject(object)
            except RuntimeError, e:
                msg = "Problem while trying to get info about LB vserver %s on %s.\n%s" % (vserver,self.host,e)
                raise RuntimeError(msg)

            for entry in output[object[0]]:
                print entry['servicename']

        else:
            object = ['lbvserver',vserver]
            try:
                output = self.client.getObject(object)
            except RuntimeError, e:
                msg = "Problem while trying to get info about LB vserver %s on %s.\n%s" % (vserver,self.host,e)
                raise RuntimeError(msg)

            # If we only want to print certain attributes
            if attr:
                try:
                    format.printDict(output[object[0]][0],attr)
                except KeyError, e:
                    raise KeyError(e)
            else:
                format.printDict(output[object[0]][0])


    def csvservers(self):
        object = ['csvserver']
        listOfCsVservers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of CS vservers on %s.\n%s" % (host,e)
            raise RuntimeError(msg)

        for vserver in output['csvserver']:
            listOfCsVservers.append(vserver['name'])

        format.printList(sorted(listOfCsVservers))


    def primarynode(self):
        object = ['hanode']

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            msg = "Problem while trying to get IP of primary node of %s.\n%s" % (host,e)
            raise RuntimeError(msg)

        # Grabbing the IP of the current primary
        print output['hanode'][0]['routemonitor']


    def savedconfig(self):
        print self.shared.getSavedConfig()


    def runningconfig(self):
        print self.shared.getRunningConfig()
        

    def getServiceStats(self,service,*args):
        mode = 'stats'
        object = ['service',service]
        DictOfServiceStats = {}

        if args:
            object.extend(args)

        try:
            output = self.client.getObject(object,mode)
        except RuntimeError, e:
            raise RuntimeError(e)

        for stat in args:
            try:
                DictOfServiceStats[stat] = output['service'][0][stat]
            except KeyError, e:
                msg = "%s is not a valid stat." % (stat)
                raise KeyError(msg)

        return DictOfServiceStats


    def surgetotal(self):
        vserver = self.args.vserver
        surgeCountTotal = 0

        try:
            output = self.shared.getBoundServices(vserver)
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


class Compare():
    def __init__(self,args):
        self.args = args
        self.shared = Shared(self.args)
        self.client = self.shared.createClient()


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
        saved = self.shared.getSavedConfig().split('\n')
        running = self.shared.getRunningConfig().split('\n')

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
        vserver1 = self.args.vserver1
        vserver2 = self.args.vserver2

        if vserver1 == vserver2:
            msg = "%s and %s are the same vserver. Please pick two different vservers." % (vserver1,vserver2)
            raise RuntimeError(msg)
    

def main():

    # Created parser.
    parser = argparse.ArgumentParser()

    # Global args
    parser.add_argument("--host", dest='host', metavar='NETSCALER', action=isPingableAction, required=True, help="IP or name of NetScaler.")
    parser.add_argument("--user", dest="user", help="NetScaler user account.", default="***REMOVED***")
    parser.add_argument("--passwd", dest="passwd", help="Password for user. Default is to fetch from passwd file.")
    parser.add_argument("--passwd-file", dest="passwdFile", help="Where password is stored for user. Default is /etc/netscalertool.conf.", default="/etc/netscalertool.conf")
    parser.add_argument("--nodns", action="store_true", dest="noDns", help="Won't try to resolve any netscaler objects.", default=False)
    parser.add_argument("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_argument("--dryrun", action="store_true", dest="dryrun", help="Dryrun.", default=False)

    # Created subparser. 
    subparser = parser.add_subparsers(dest='topSubparserName')

    # Created show subparser.
    parserShow = subparser.add_parser('show', help='sub-command for showing objects')
    subparserShow = parserShow.add_subparsers(dest='subparserName')
    parserShowLbVservers = subparserShow.add_parser('lb-vservers', help='Show all lb vservers')
    parserShowLbVserver = subparserShow.add_parser('lb-vserver', help='Show stat(s) of a specific lb vserver')
    parserShowLbVserver.add_argument('vserver', help='Show stats for which vserver') 
    parserShowLbVserverGroup = parserShowLbVserver.add_mutually_exclusive_group()
    parserShowLbVserverGroup.add_argument('--attr', dest='attr', nargs='*', help='Show only the specified attribute(s)') 
    parserShowLbVserverGroup.add_argument('--services', action='store_true', dest='services', help='Show services bound to lb vserver') 
    parserShowCsVservers = subparserShow.add_parser('cs-vservers', help='Show all cs vservers')
    parserShowServices = subparserShow.add_parser('services', help='Show all services')
    parserShowPrimaryNode = subparserShow.add_parser('primary-node', help='Show which of the two nodes is primary')
    parserShowSurgeTotal = subparserShow.add_parser('surge-total', help='Show surge total for a lb vserver')
    parserShowSurgeTotal.add_argument('vserver', help='Show surge total for which lb vserver')
    parserShowSavedConfig = subparserShow.add_parser('saved-config', help='Show saved ns config')
    parserShowRunningConfig = subparserShow.add_parser('running-config', help='Show running ns config')

    # Created compare subparser.
    parserCmp = subparser.add_parser('compare', help='sub-command for comparing objects')
    subparserCmp = parserCmp.add_subparsers(dest='subparserName')
    parserCmpConfigs = subparserCmp.add_parser('configs', help='Alerts if there is any diff between running and saved ns configs')
    parserCmpLbVservers = subparserCmp.add_parser('lb-vservers', help='Compare configs between two vservers')
    parserCmpLbVservers.add_argument('vserver1', metavar='VSERVER1')
    parserCmpLbVservers.add_argument('vserver2', metavar='VSERVER2')

    # Getting arguments
    args = parser.parse_args()
    debug = args.debug

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
        raise argparse.ArgumentTypeError("%s is not a valid subparser." % args.topSubparserName)

    # Creating instance and calling one of its method
    try:
        netscalerTool = klass(args)
        getattr(netscalerTool,method)()
    except (RuntimeError,KeyError), e:
        if debug:
            print >> sys.stderr, "\n", str(e[0]).strip('\'')
        return 1

    # Logging out of NetScaler.
    try:
        netscalerTool.client.logout()
    except RuntimeError, e:
        print >> sys.stderr, e

    # Exiting program
    return 0


# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


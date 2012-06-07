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


class NetscalerTool():
    def __init__(self,host,user,passwdFile,debug,dryrun):
        self.host = host
        self.user = user
        self.passwd = self.fetchPasswd(passwdFile)
        self.debug = debug    
        self.dryrun = dryrun

        # Creating a client instance that we can use during
        # the rest of this program.
        try:
            self.client = netscalerapi.Client(self.host,self.user,self.passwd,self.debug)
        except RuntimeError, e:
            print >> sys.stderr, "Problem creating client instance.\n%s" % (e)
            return 1

        # Let's login
        try:
            self.client.login() 
        except RuntimeError, e:
            return 1


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


    def getServices(self):
        object = ['service']
        listOfServices = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        for service in output['service']:
            listOfServices.append(service['name'])

        listOfServices.sort()
        return listOfServices


    def getLbVservers(self):
        object = ['lbvserver']
        listOfLbVservers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        for vserver in output['lbvserver']:
            listOfLbVservers.append(vserver['name'])

        listOfLbVservers.sort()
        return listOfLbVservers


    def getLbVserver(self,vserver):
        object = ['lbvserver',vserver]

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        return output['lbvserver'][0]


    def getCsVservers(self):
        object = ['csvserver']
        listOfCsVservers = []

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        for vserver in output['csvserver']:
            listOfCsVservers.append(vserver['name'])

        listOfCsVservers.sort()
        return listOfCsVservers


    def getPrimaryNode(self):
        object = ['hanode']

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        # Grabbing the IP of the current primary
        return output['hanode'][0]['routemonitor']


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


    def getSavedNsConfig(self):
        object = ['nssavedconfig']

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        return output['nssavedconfig']['textblob']


    def getRunningNsConfig(self):
        object = ['nsrunningconfig']

        try:
            output = self.client.getObject(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        return output['nsrunningconfig']['response']
        

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
                print >> sys.stderr, "%s is not a valid stat." % (stat)

        return DictOfServiceStats


    def getSurgeCount(self,vserver):
        surgeCountTotal = 0

        try:
            output = self.getBoundServices(vserver)
        except RuntimeError, e:
            raise RuntimeError(e)

        # Going through the list of services to get surge count.
        for service in output:
            try:
                output = self.getServiceStats(service,'surgecount')
            except RuntimeError, e:
                raise RuntimeError(e)

            surgeCountTotal += int(output['surgecount'])

        return surgeCountTotal
             

def main():

    status = 0
    attributes = None

    # Created parser.
    parser = argparse.ArgumentParser()

    # Created subparser. 
    subparser = parser.add_subparsers()

    # Created show parser to subparser.
    parserShow = subparser.add_parser('show', help='sub-command for showing objects on the NetScaler')
    showSubparser = parserShow.add_subparsers()

    # Adding parsers to showSubparser
    parserShowLbVservers = showSubparser.add_parser('lb-vservers', help='Show all lb vservers')
    parserShowLbVserver = showSubparser.add_parser('lb-vserver', help='Show stat(s) on specific lb vservers')
    parserShowCsVservers = showSubparser.add_parser('cs-vservers', help='Show all cs vservers')
    parserShowServices = showSubparser.add_parser('services', help='Show all services')

    # Global args
    parser.add_argument("--host", dest='host', metavar='NETSCALER', action=isPingableAction, required=True, help="IP or name of NetScaler.")
    parser.add_argument("--user", dest="user", help="NetScaler user account.", default="***REMOVED***")
    parser.add_argument("--passwd", dest="passwd", help="Password for user. Default is to fetch from passwd file.")
    parser.add_argument("--passwd-file", dest="passwdFile", help="Where password is stored for user. Default is /etc/netscalertool.conf.", default="/etc/netscalertool.conf")
    parser.add_argument("--nodns", action="store_true", dest="noDns", help="Won't try to resolve any netscaler objects.", default=False)
    parser.add_argument("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_argument("--dryrun", action="store_true", dest="dryrun", help="Dryrun.", default=False)

    # Getting arguments
    args = parser.parse_args()

    host = args.host
    user = args.user
    passwdFile = args.passwdFile
    debug = args.debug
    dryrun = args.dryrun
    noDns = args.noDns

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

    # Creating a netscalertool object.
    netscalertool = NetscalerTool(host,user,passwdFile,debug,dryrun)

    # Fetching list of all vservers.
    if args.getLbVservers:
        try:
            output = netscalertool.getLbVservers()
            format.printList(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of LB vservers on %s.\n%s" % (host,e)
            status = 1


    # Fetching stats on a specific lb vserver.
    if args.getLbVserver:
        vserver = args.getLbVserver

        if args.attribute:
            attributes = args.attribute

        try:
            output = netscalertool.getLbVserver(vserver)
            if attributes:
                format.printDict(output,attributes)
            else:
                format.printDict(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get info about LB vserver %s on %s.\n%s" % (vserver,host,e)
            status = 1


    # Fetching list of all services.
    elif args.showServices:
        try:
            output = netscalertool.getServices()
            format.printList(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of services on %s.\n%s" % (host,e)
            status = 1


    # Fetching list of all cs vservers.
    elif args.getCsVservers:
        try:
            output = netscalertool.getCsVservers()
            format.printList(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of CS vservers on %s.\n%s" % (host,e)
            status = 1


    # Fetching the current primary node IP.
    elif args.primaryNode:
        try:
            output = netscalertool.getPrimaryNode()
            print output
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get IP of primary node of %s.\n%s" % (host,e)
            status = 1


    # Fetching surge queue size for specified vserver
    elif args.surgeCount:
        vserver = args.surgeCount
        try:
            output = netscalertool.getSurgeCount(vserver)
            if debug:
                print "Total Surge Queue Size is:"
            print output
        except RuntimeError, e:
            print >> sys.stderr, "Problem getting surge queue size of all services bound to vserver %s.\n%s" % (vserver,e)
            status = 1


    # Grabbing the saved ns config
    elif args.getSavedNsConfig:
        try:
            output = netscalertool.getSavedNsConfig()
            print output
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem getting the saved ns.conf: ", e
            status = 1
        except IOError, e:
            pass 

    # Grabbing the running ns config
    elif args.getRunningNsConfig:
        try:
            output = netscalertool.getRunningNsConfig()
            print output
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem getting the running config: ", e
            status = 1
        except IOError, e:
            pass 

    # Logging out of NetScaler.
    try:
        netscalertool.client.logout()
    except RuntimeError, e:
        print >> sys.stderr, e

    # Exiting program
    return status

# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


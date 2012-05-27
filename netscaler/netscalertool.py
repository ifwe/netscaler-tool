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
        if not ignoreDns:
            try:
                for item in values:
                    socket.gethostbyaddr(item)
            except socket.gaierror, e:
                print >> sys.stderr, "%s does not resolve." % (item)
                return 1

            setattr(namespace, self.dest, values)


def fetchPasswd(passwdFile):
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


def getServices(client):
    object = ['service']
    listOfServices = []

    try:
        output = client.getObject(object)
    except RuntimeError, e:
        raise RuntimeError(e)

    for service in output['service']:
        listOfServices.append(service['name'])

    listOfServices.sort()
    return listOfServices


def getLbVservers(client):
    object = ['lbvserver']
    listOfLbVservers = []

    try:
        output = client.getObject(object)
    except RuntimeError, e:
        raise RuntimeError(e)

    for vserver in output['lbvserver']:
        listOfLbVservers.append(vserver['name'])

    listOfLbVservers.sort()
    return listOfLbVservers


def getLbVserver(client,vserver):
    object = ['lbvserver',vserver]

    try:
        output = client.getObject(object)
    except RuntimeError, e:
        raise RuntimeError(e)

    return output['lbvserver'][0]


def getCsVservers(client):
    object = ['csvserver']
    listOfCsVservers = []

    try:
        output = client.getObject(object)
    except RuntimeError, e:
        raise RuntimeError(e)

    for vserver in output['csvserver']:
        listOfCsVservers.append(vserver['name'])

    listOfCsVservers.sort()
    return listOfCsVservers


def getBoundServices(client,vserver):
    command = "getservice"
    arg = {'name':vserver}

    try:
        output = netscalerapi.runCmd(client,command,**arg)
    except RuntimeError, e:
        raise RuntimeError(e)

    print output[0]
    try:
        return output[0].servicename
    except AttributeError:
        e = "Vserver %s doesn't have any service bound to it. You can probably delete it." % (vserver)
        raise RuntimeError(e)


def getSavedNsConfig(client):
    object = ['nssavedconfig']

    try:
        output = client.getObject(object)
    except RuntimeError, e:
        raise RuntimeError(e)

    return output['nssavedconfig']['textblob']


def getRunningNsConfig(client):
    object = ['nsrunningconfig']

    try:
        output = client.getObject(object)
    except RuntimeError, e:
        raise RuntimeError(e)

    return output['nsrunningconfig']['response']
    

def getStatServices(client,service):
    command = "statservice"
    arg = {'name':service}

    try:
        output = netscalerapi.runCmd(client,command,**arg)
    except RuntimeError, e:
        raise RuntimeError(e)

    return output[0].surgecount

def getSurgeQueueSize(client,vserver):
    msg = ""
    surgeCountTotal = 0

    try:
        output = getServices(client,vserver)
    except RuntimeError, e:
        raise RuntimeError(e)

    # Since we got the services bound to the vserver in question, we now
    # need to get surge queue count for each service, but that requires we
    # change wsdl files.
    try:
        client = login(host,user,passwd,debug)
    except RuntimeError, e:
        raise RuntimeError(e)

    # Going through the list of services to get surge count.
    for service in output:
        if debug:
            print "Fetching surge queue count for %s" % (service)

        try:
            output = getStatServices(client,service)
        except RuntimeError, e:
            raise RuntimeError(e)
        
        if debug:
            print "Surge count for %s: %s\n" % (service,output)

        surgeCountTotal =+ int(output)

    return surgeCountTotal
         

def main():

    status = 0
    attributes = None

    # Created parser
    parser = argparse.ArgumentParser()

    # Created subparser 
    subparser = parser.add_subparsers()

    parserShow = subparser.add_parser('show', help='sub-command for showing objects on the NetScaler')

    parserShowGroup = parserShow.add_mutually_exclusive_group(required=True)
    parserShowGroup.add_argument('--lb-vservers', dest='showLbVservers', action='store_true', help='Show all LB vserver.', default=False)
    parserShowGroup.add_argument('--lb-vserver', dest='showLbVserver', metavar='LBVSERVER', nargs='+', help='Show info about a LB vserver.')
    parserShowGroup.add_argument('--cs-vservers', dest='showCsVservers', action='store_true', help='Show all CS vserver.', default=False)
    parserShowGroup.add_argument('--services', dest='showServices', action='store_true', help='Show all services.', default=False)
    parserShowGroup.add_argument('--vserver', dest='showVserver', metavar='VSERVER', help='Show a specific vserver.')
    parserShowGroup.add_argument('--surge-queue-size', metavar='VSERVER', dest='surgeQueueSize', help='Get current surge queue size of all servies bound to specified vserver.')
    parserShowGroup.add_argument('--primary-node', action='store_true', dest='primaryNode', help='List IP of current primary node.', default=False)
    parserShowGroup.add_argument('--saved-config', action='store_true', dest='getSavedNsConfig', help='Shows saved ns.conf', default=False)
    parserShowGroup.add_argument('--running-config', action='store_true', dest='getRunningNsConfig', help='Shows running ns.conf', default=False)

    parser.add_argument("--host", dest='host', metavar='NETSCALER', action=isPingableAction, required=True, help="IP or name of NetScaler.")
    parser.add_argument("--user", dest="user", help="NetScaler user account.", default="***REMOVED***")
    parser.add_argument("--passwd", dest="passwd", help="Password for user. Default is to fetch from passwd file.")
    parser.add_argument("--passwd-file", dest="passwdFile", help="Where password is stored for user. Default is /etc/netscalertool.conf.", default="/etc/netscalertool.conf")
    parser.add_argument("--ignore-dns", action="store_true", dest="ignoreDns", help="Won't try to resolve any netscaler objects.", default=False)
    parser.add_argument("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_argument("--dryrun", action="store_true", dest="dryrun", help="Dryrun.", default=False)

    # Getting arguments
    args = parser.parse_args()

    host = args.host
    user = args.user
    passwdFile = args.passwdFile
    debug = args.debug
    dryrun = args.dryrun
    ignoreDns = args.ignoreDns

    # fetching password from file
    try:
        passwd = fetchPasswd(passwdFile)
    except IOError, e:
        print >> sys.stderr, e
        return 1 

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

    # Creating a client instance that we can use during
    # the rest of this program.
    try:
        client = netscalerapi.Client(host,user,passwd,debug)
    except RuntimeError, e:
        print >> sys.stderr, "Problem creating client instance.\n%s" % (e)
        return 1

    # Let's login
    try:
        sessionID = client.login() 
    except RuntimeError, e:
        return 1

    #############
    #  Showing  #
    #############

    # Fetching list of all vservers.
    if args.showLbVservers:
        try:
            output = getLbVservers(client)
            format.printList(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of LB vservers on %s.\n%s" % (host,e)
            status = 1


    if args.showLbVserver:
        vserver = args.showLbVserver[0]

        # If we get a list greater than 1, we know the user
        # is asking for a attribute of the vserver.
        if len(args.showLbVserver) > 1:
            attributes = args.showLbVserver[1:]

        try:
            output = getLbVserver(client,vserver)
            if attributes:
                format.printDict(output,attributes)
            else:
                format.printDict(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get info about LB vserver %s on %s.\n%s" % (vserver,host,e)
            status = 1


    # Fetching list of all servies.
    elif args.showServices:
        try:
            output = getServices(client)
            format.printList(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of services on %s.\n%s" % (host,e)
            status = 1

    # Fetching list of all cs vservers.
    elif args.showCsVservers:
        try:
            output = getCsVservers(client)
            format.printList(output)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of CS vservers on %s.\n%s" % (host,e)
            status = 1

    # Checking for failover status
    elif args.primaryNode:
        command = "gethanode"
        try:
            output = netscalerapi.runCmd(client,command)
        except RuntimeError, e:
            print >> sys.stderr, e
            try:
                netscalerapi.logout(client)
            except RuntimeError, e:
                print >> sys.stderr, "There was a problem logging out.", e
            return 1

        print "Primary node is:"
        print output[0].name, output[0].ipaddress, "\n"

        try:
            netscalerapi.logout(client)
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem logging out.", e

    # Fetching surge queue size for specified vserver
    elif args.surgeQueueSize:
        try:
            output = getSurgeQueueSize(client,vserver)
        except RuntimeError, e:
            print >> sys.stderr, "Problem getting surge queue size of all services bound to vserver %s.\n%s" % (vserver,e)
            try:
                netscalerapi.logout(client)
            except RuntimeError, e:
                print >> sys.stderr, "There was a problem logging out.", e
            return 1

        if debug:
            print "Total Surge Queue Size is:"
        print output

        try:
            netscalerapi.logout(client)
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem logging out.", e

    elif args.getSavedNsConfig:
        try:
            output = getSavedNsConfig(client)
            print output
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem getting the saved ns.conf: ", e
            status = 1
        except IOError, e:
            pass 

    elif args.getRunningNsConfig:
        try:
            output = getRunningNsConfig(client)
            print output
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem getting the running config: ", e
            status = 1
        except IOError, e:
            pass 

    # Logging out of NetScaler.
    try:
        client.logout()
    except RuntimeError, e:
        print >> sys.stderr, e

    # Exiting program
    return status

# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


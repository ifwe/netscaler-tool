#!/usr/bin/env python

import sys
from optparse import OptionParser
import netscalerapi
import format
import re
import socket

dryrun = None
debug = None
ignoreDns = None
host = None
vserver = None
server = None
service = None
mode = None
wsdl = None
user = None
passwd = None
passwdFile = None
primaryNode = None
surgeQueueSize = None
listVservers = None
listServices = None


def getConnected(host,wsdl,user,passwd):
    
    try:
        client = netscalerapi.connection(host,wsdl)
    except RuntimeError, e:
        raise RuntimeError(e)

    # Logging into NetScaler.
    try:
        netscalerapi.login(client,user,passwd)
    except RuntimeError, e:
        raise RuntimeError(e)

    return client
    

def getListServices(client):
    command = "getservice"
    list = []

    try:
        output = netscalerapi.runCmd(client,command)
    except RuntimeError, e:
        raise RuntimeError(e)

    for entry in output:
        list.append(entry.name)

    list.sort()
    return list


def getListVservers(client):
    command = "getlbvserver"
    list = []

    try:
        output = netscalerapi.runCmd(client,command)
    except RuntimeError, e:
        raise RuntimeError(e)

    for entry in output:
        list.append(entry.name)

    list.sort()
    return list


def getServices(client,vserver):
    command = "getlbvserver"
    arg = {'name':vserver}

    try:
        output = netscalerapi.runCmd(client,command,**arg)
    except RuntimeError, e:
        raise RuntimeError(e)

    try:
        return output[0].servicename
    except AttributeError:
        e = "Vserver %s doesn't have any service bound to it. You can probably delete it." % (vserver)
        raise RuntimeError(e)


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
    wsdl = "NSStat.wsdl"
    wsdlURL = "http://%s/api/%s" % (host,wsdl)
    surgeCountTotal = 0

    try:
        output = getServices(client,vserver)
    except RuntimeError, e:
        raise RuntimeError(e)

    # Since we got the services bound to the vserver in question, we now
    # need to get surge queue count for each service, but that requires we
    # change wsdl files.
    try:
        client = getConnected(host,wsdl,user,passwd)
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


def saveNsConfig(client):
    command = "savensconfig"

    try:
        output = netscalerapi.runCmd(client,command)
    except RuntimeError, e:
        raise RuntimeError(e)


def vserverExists(client, vserver):
    command = "getlbvserver"
    arg = {'name':vserver}

    try:
        output = netscalerapi.runCmd(client,command,**arg)
    except RuntimeError, e:
        raise RuntimeError(e)


def main():
    
    global dryrun
    global debug
    global host
    global ignoreDns
    global vserver
    global server
    global service
    global mode
    global wsdl
    global user
    global passwd
    global passwdFile
    global primaryNode
    global surgeQueueSize
    global listVeservers
    global listServices

    # Getting options from user
    parser = OptionParser()
    parser.add_option("--host", dest='host', help="IP or name of netscaler. Must be specified.")
    parser.add_option("--vserver", dest='vserver', help="Name of vserver you would like to work with.")
    parser.add_option("--server", dest='server', action='append', help="Name of server(s) you would like to work with.")
    parser.add_option("--service", dest='service', action='append', help="Name of service(s) you would like to work with.")
    parser.add_option("--mode", dest='mode', help="Add, Remove, Enable, or Disable vserver/server/service. Valid options are either \"aad\", \"rm\", \"enable\", \"disable\".",default=False)
    parser.add_option("--wsdl", dest='wsdl', help="Name of WSDL. If not specified, will default to NSConfig-tagged.wsdl.", default="NSConfig-tagged.wsdl")
    parser.add_option("--user", dest="user", help="User to login as.", default="***REMOVED***")
    parser.add_option("--passwd", dest="passwd", help="Password for user. Default is to fetch from passwd file.")
    parser.add_option("--passwd-file", dest="passwdFile", help="Where password is stored for user. Default is /etc/netscalertool.conf.", default="/etc/netscalertool.conf")
    parser.add_option("--list-vservers", action="store_true", dest='listVservers', help="List all vservers on NetScaler.")
    parser.add_option("--list-services", action="store_true", dest='listServices', help="List all services on NetScaler.")
    parser.add_option("--primary-node", action="store_true", dest="primaryNode", help="List IP of current primary node", default=False)
    parser.add_option("--surge-queue-size", action="store_true", dest="surgeQueueSize", help="Get current surge queue size of all servies bound to specified vserver. Must also specify --vserver.")
    parser.add_option("--ignore-dns", action="store_true", dest="ignoreDns", help="Won't try to resolve server or vserver.", default=False)
    parser.add_option("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_option("--dryrun", action="store_true", dest="dryrun", help="Don't actually execute any commands.", default=False)
    
    (options, args) = parser.parse_args()

    host = options.host
    vserver = options.vserver
    server = options.server
    service = options.service
    mode = options.mode
    wsdl = options.wsdl
    dryrun = options.dryrun
    debug = options.debug
    ignoreDns = options.ignoreDns
    user = options.user
    passwd = options.passwd
    passwdFile = options.passwdFile
    primaryNode = options.primaryNode
    surgeQueueSize = options.surgeQueueSize
    listVservers = options.listVservers
    listServices = options.listServices


    #########################
    # Checking user's input #
    #########################

    # Checking to see if user specified netscaler (host).
    if not host :
        print "You need to specify a NetScaler with --host=HOST.\n"
        parser.print_help()
        return 1

    # Checking to make sure the user specified vserver when wanting
    # to find the surge queue length of a vserver.
    if surgeQueueSize and not vserver:
        print "You need to specify a vserver!\n"
        parser.print_help()
        return 1

    # Checking to make sure the user specified a vserver when wanting
    # to add/remove a vserver.
    if mode and not vserver: 
        print "You need to specify a vserver or service when specifying --mode!\n"
        parser.print_help()
        return 1

    # Normalizing mode to lower case.
    if mode:
        mode = mode.lower()

        # Checking if the user specified either add or rm with mode.
        if mode != "add" and mode != "rm" and mode != "enable" and mode != "disable":
            print "You need to specify either \"add\", \"rm\", \"enable\", or \"disable\" for mode!\n"
            parser.print_help()
            return 1

    # Let's check to see if vserver resolve.
    if vserver:
        if not ignoreDns:
            try:
                socket.gethostbyaddr(vserver)
            except socket.gaierror, e:
                print >> sys.stderr, "Vserver %s does not resolve. Please create DNS entry and try again.\n" % (vserver)
                return 1

    # Let's check to see if service(s) resolve.
    if service:
        for entry in service:
            if entry.find('['):
                start = entry.find('[')
                middle = entry.find('-')
                end = entry.find(']')
                firstNumber = entry[(start+1):middle] 
                secondNumber = entry[(middle+1):end] 
        
            print range(firstNumber,secondNumber)

    # Let's check to see if servers resolve.
    if server:
        serverList = {}
        for entry in server:
            if entry.find('['):
                start = entry.find('[')
                middle = entry.find('-')
                end = entry.find(']')
                firstNumber = int(entry[(start+1):middle])
                secondNumber = int(entry[(middle+1):end])
                hostNameBase = entry[0:start]
            
            for number in range(firstNumber,secondNumber+1):
                hostName = hostNameBase + str(number)
                serverList[hostName] = ''

        print serverList

    # Can't work on service(s) and server(s) at the same time
    if service and server:
        print "You can specify either server or service, but not both!\n"
        parser.print_help()
        return 1

    ################################
    # End of checking user's input #
    ################################
        
    # fetching password from file
    try:
        passwd = netscalerapi.fetchPasswd(passwdFile)
    except IOError, e:
        print >> sys.stderr, e
        return 1 

    # Showing user flags and their values
    if debug:
        print "Using the following variables:"
        for option in dir(options):
            regex = "(^_{1,2}|^read_file|^read_module|^ensure_value)"
            if re.match(regex,option):
                continue
            else:
                print "\t%s: %s" % (option,getattr(options,option))
        print "\n"

    # Creating a client instance that we can use during
    # the rest of this script to interact with.
    try:
        client = getConnected(host,wsdl,user,passwd)
    except RuntimeError, e:
        print >> sys.stderr, "Problem creating client instance.\n%s" % (e)
        return 1

    # Fetching list of all vservers on specified NetScaler.
    if listVservers:
        try:
            output = getListVservers(client)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of vservers on %s.\n%s" % (host,e)
            try:
                netscalerapi.logout(client)
            except RuntimeError, e:
                print >> sys.stderr, "There was a problem logging out.", e
            return 1

        format.printList(output)
        try:
            netscalerapi.logout(client)
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem logging out.", e
        return 0

    # Fetching list of all servies on specified NetScaler.
    if listServices:
        try:
            output = getListServices(client)
        except RuntimeError, e:
            print >> sys.stderr, "Problem while trying to get list of services on %s.\n%s" % (host,e)
            try:
                netscalerapi.logout(client)
            except RuntimeError, e:
                print >> sys.stderr, "There was a problem logging out.", e
            return 1

        format.printList(output)
        try:
            netscalerapi.logout(client)
        except RuntimeError, e:
            print >> sys.stderr, "There was a problem logging out.", e
        return 0


    # Checking for failover status
    if primaryNode:
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
        return 0 

    # Fetching surge queue size for specified vserver
    if surgeQueueSize:
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
        return 0

    # Adding vserver.
    if mode == 'add' and vserver:
        # Let's check to see if a vserver with that name already exists.
        if status:
            print >> sys.stderr, "%s already exists. Please pick a different name for vserver!\n" % (vserver)
            return 1

        # Let's check if there are server entries.
        try:
            socket.gethostbyaddr(server)
        except socket.gaierror, e:
            print >> sys.stderr, "Server %s does not resolve. Please create DNS entry for %s and try again.\n" % (server,server)
            return 1

    # Removing vserver.
    if mode == 'rm' and vserver:
        pass

    # Logging out of NetScaler.
    try:
        netscalerapi.logout(client)
    except RuntimeError, e:
        print >> sys.stderr, "There was a problem logging out.", e

    # Successfully exiting
    return 0


# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


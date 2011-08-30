#!/usr/bin/env python

import sys
from optparse import OptionParser
import netscalerapi
import format
import re

dryrun = None
debug = None
host = None
wsdl = None
user = None
passwd = None
passwdFile = None
primaryNode = None
surgeQueueSize = None
vserver = None
listVservers = None
listServices = None


def getConnected(host,wsdl,user,passwd):
    client = netscalerapi.connection(host,wsdl)
    if client == 1:
        msg = "Could not establish a connection with %s. Might be due to invalid wsdl file." % (host)
        return 1, msg

    # Logging into NetScaler.
    status, output = netscalerapi.login(client,user,passwd)
    if status:
        msg = "Could not log into %s.\n" % (host)
        return 1, msg

    return 0, client
    

def getListServices(client):
    command = "getservice"
    list = []

    status, output = netscalerapi.runCmd(client,command)
    if status:
        return 1, output

    for entry in output:
        list.append(entry.name)

    list.sort()
    return 0, list


def getListVservers(client):
    command = "getlbvserver"
    list = []

    status, output = netscalerapi.runCmd(client,command)
    if status:
        return 1, output

    for entry in output:
        list.append(entry.name)

    list.sort()
    return 0, list


def getServices(client,vserver):
    command = "getlbvserver"
    arg = {'name':vserver}

    status, output = netscalerapi.runCmd(client,command,**arg)
    if status:
        return 1, output

    return 0, output[0].servicename


def getStatServices(client,service):
    command = "statservice"
    arg = {'name':service}

    status, output = netscalerapi.runCmd(client,command,**arg)
    if status:
        return 1, output

    return 0, output[0].surgecount


def getSurgeQueueSize(client,vserver):
    msg = ""
    wsdl = "NSStat.wsdl"
    wsdlURL = "http://%s/api/%s" % (host,wsdl)
    surgeCountTotal = 0

    status, output = getServices(client,vserver)
    if status:
        msg = "Problem get services bound to vserver %s\n" % (vserver)
        return 1, msg

    # Since we got the services bound to the vserver in question, we now
    # need to get surge queue count for each service, but that requires we
    # change wsdl files.
    status, client = getConnected(host,wsdl,user,passwd)
    if status:
        print "%s\n" % (msg)
        return 1

    # Going through the list of services to get surge count.
    for service in output:
        if debug:
            print "Fetching surge queue count for %s" % (service)

        status, output = getStatServices(client,service)
        
        if debug:
            print "Surge count for %s: %s\n" % (service,output)

        surgeCountTotal =+ int(output)

        
    return 0, surgeCountTotal


def main():
    
    global dryrun
    global debug
    global host
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
    parser.add_option("--vserver", dest='vserver', help="Name of vserver that you would like to work with.")
    parser.add_option("--wsdl", dest='wsdl', help="Name of WSDL. If not specified, will default to NSConfig-tagged.wsdl.", default="NSConfig-tagged.wsdl")
    parser.add_option("--user", dest="user", help="User to login as.", default="***REMOVED***")
    parser.add_option("--passwd", dest="passwd", help="Password for user. Default is to fetch from passwd file.")
    parser.add_option("--passwd-file", dest="passwdFile", help="Where password is stored for user. Default is passwd.txt.", default="/etc/netscalertool.conf")
    parser.add_option("--list-vservers", action="store_true", dest='listVservers', help="List all vservers on NetScaler.")
    parser.add_option("--list-services", action="store_true", dest='listServices', help="List all services on NetScaler.")
    parser.add_option("--primary-node", action="store_true", dest="primaryNode", help="List IP of current primary node", default=False)
    parser.add_option("--surge-queue-size", action="store_true", dest="surgeQueueSize", help="Get current surge queue size of all servies bound to specified vserver. Must also specify --vserver.")
    parser.add_option("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_option("--dryrun", action="store_true", dest="dryrun", help="Don't actually execute any commands.", default=False)
    
    (options, args) = parser.parse_args()

    host = options.host
    vserver = options.vserver
    wsdl = options.wsdl
    dryrun = options.dryrun
    debug = options.debug
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

    ################################
    # End of checking user's input #
    ################################
        
    # fetching password from file
    status, passwd = netscalerapi.fetchPasswd(passwdFile)
    if status:
        print >> sys.stderr, "Problem fetching passwd from %s.\n" % (passwdFile)
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
    status, client = getConnected(host,wsdl,user,passwd)
    if status:
        print >> sys.stderr, "%s\n" % (client)
        return 1

    # Fetching list of all vservers on specified NetScaler.
    if listVservers:
        status, output = getListVservers(client)
        if status:
            print >> sys.stderr, "Problem while trying to get list of vservers on %s." % (host)
            return 1
        else:
            format.printList(output)
            netscalerapi.logout(client)
            return 0

    # Fetching list of all servies on specified NetScaler.
    if listServices:
        status, output = getListServices(client)
        if status:
            print >> sys.stderr, "Problem while trying to get list of services on %s." % (host)
            return 1
        else:
            format.printList(output)
            netscalerapi.logout(client)
            return 0


    # Checking for failover status
    if primaryNode:
        command = "gethanode"
        status , output = netscalerapi.runCmd(client,command)
        if status:
            if debug:
                print >> sys.stderr, "There was a problem running %s:\n%s" % (command,output)
            return 1
        else:
            if debug:
                print "Primary node is:"
            print output[0].name, output[0].ipaddress, "\n"

            netscalerapi.logout(client)
            return 0 

    # Fetching surge queue size for specified vserver
    if surgeQueueSize:
        status, output = getSurgeQueueSize(client,vserver)
        if status:
            print >> sys.stderr, "There was a problem getting surge queue size of vserver %s\n%s" % (vserver,output)
            return 1
        else:
            if debug:
                print "Total Surge Queue Size is:"
            print output

            netscalerapi.logout(client)
            return 0
        

    # Logging out of NetScaler.
    netscalerapi.logout(client)

    # Successfully exiting
    return 0


# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


#!/usr/bin/env python

import sys
from optparse import OptionParser
import netscalerapi

dryrun = None
debug = None
host = None
wsdl = None
user = None
passwd = None
passwdFile = None
failOverStatus = None
surgeQueueSize = None

def main():
    
    global dryrun
    global debug
    global host
    global wsdl
    global user
    global passwd
    global passwdFile
    global failOverStatus
    global surgeQueueSize

    # Getting options from user
    parser = OptionParser()
    parser.add_option("--host", dest='host', help="IP or name of netscaler. Must be specified.")
    parser.add_option("--wsdl", dest='wsdl', help="Name of WSDL. If not specified, will default to NSConfig.wsdl.", default="NSConfig.wsdl")
    parser.add_option("--user", dest="user", help="User to login as.", default="***REMOVED***")
    parser.add_option("--passwd", dest="passwd", help="Password for user. Default is to fetch from passwd file.")
    parser.add_option("--passwd-file", dest="passwdFile", help="Where password is stored for user. Default is passwd.txt.", default="passwd.txt")
    parser.add_option("--failover-status", action="store_true", dest="failOverStatus", help="Detects a recent failover", default=False)
    parser.add_option("--surge-queue-size", dest="surgeQueueSize", help="Get current surge queue size of all servies bound to specified vserver")
    parser.add_option("--debug", action="store_true", dest="debug", help="Shows what's going on.", default=False)
    parser.add_option("--dryrun", action="store_true", dest="dryrun", help="Don't actually execute any commands.", default=False)
    
    (options, args) = parser.parse_args()

    # Checking to see if user specified netscaler (host).
    host = options.host
    if not host:
        print "\nYou need to specify a netscaler!\n"
        parser.print_help()
        return 1

    wsdl = options.wsdl
    dryrun = options.dryrun
    debug = options.debug
    host = options.host
    user = options.user
    passwd = options.passwd
    passwdFile = options.passwdFile
    failOverStatus = options.failOverStatus
    surgeQueueSize = options.surgeQueueSize

    # fetching password from file
    status, passwd = netscalerapi.fetchPasswd(passwdFile)
    if status:
        if debug:
            print >> sys.stderr, "Problem fetching passwd from %s.\n" % (passwdFile)
        return 1 
    else:
        if debug:
            print "Fetching password from %s\n" % (passwdFile)

    # Creating a client instance that we can use during
    # the rest of this script to interact with.
    client = netscalerapi.connection(host,wsdl)    
    if debug:
        print "Created client instance: %s\n" % (client)

    # Logging into NetScaler.
    netscalerapi.login(client,user,passwd)
    if status:
        if debug:
            print "Could not log into %s.\n" % (host)
        return 1
    else:
        if debug:
            print "logged into %s.\n" % (host)

    # Checking for failover status
    if failOverStatus:
        command = "gethanode"
        status , output = netscalerapi.runCmd(client,command)
        if status:
            if debug:
                print >> sys.stderr, "There was a problem running %s:\n%s" % (command,output)
            return 1
        else:
            if debug:
                print "Output from checking node status:\n%s\n" % (output)

    elif surgeQueueSize:
        command = "getlbvserver"
        arg = {'name':surgeQueueSize}
        status, output = netscalerapi.runCmd(client,command,**arg)
        if status:
            if debug:
                print >> sys.stderr, "There was a problem running %s:\n%s" % (command,output)
            return 1
        else:
            if debug:
                print "Output from fetching surge queue size for %s:\n%s\n" % (surgeQueueSize,output.servicename)
        

    # Logging out of NetScaler.
    netscalerapi.logout(client)

    # Successfully exiting
    return 0
    

# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


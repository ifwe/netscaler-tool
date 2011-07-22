#!/usr/bin/env python

import getopt
import sys
from optparse import OptionParser
import netscalerapi

dryrun = None
debug = None
wsdl = None
host = None

def main():
    
    global dryrun
    global debug
    global wsdl
    global host

    # Getting options from user
    parser = OptionParser()
    parser.add_option("--host", dest='host', help="IP or name of netscaler. Must be specified.")
    parser.add_option("--wsdl", dest='wsdl', help="Name of WSDL. I not specified will default to NSConfig.wsdl")
    parser.add_option("--debug", action="store_true", dest="debug", help="Shows what's going on", default=False)
    parser.add_option("--dryrun", action="store_true", dest="dryrun", help="Don't actually run commands", default=False)
    
    (options, args) = parser.parse_args()

    host = options.host
    if not host:
        print "\nYou need to specify a netscaler!\n"
        parser.print_help()

    wsdl = options.wsdl
    dryrun = options.dryrun
    debug = options.debug

    # Successfully exiting
    return 0
    

# Run the script only if the script
# itself is called directly.
if __name__ == '__main__':
    sys.exit(main())


#!/usr/bin/env python

import argparse
import logging
import netscalerapi
import os
import re
import socket
import subprocess
import sys
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

# NetScaler tool configuration file
netscaler_tool_config = "/etc/netscalertool.conf"

# Grabbing the user that is running this script for logging purposes
if os.getenv('SUDO_USER'):
    user = os.getenv('SUDO_USER')
else:
    user = os.getenv('USER')

# Setting up logging
logFile = '/var/log/netscaler-tool/netscaler-tool.log'
try:
    local_host = socket.gethostbyaddr(socket.gethostname())[1][0]
except (socket.herror, socket.gaierror), e:
    localHost = 'localhost'
logger = logging.getLogger(local_host)
logger.setLevel(logging.DEBUG)

try:
    ch = logging.FileHandler(logFile)
except IOError, e:
    print >> sys.stderr, e
    sys.exit(1)

ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s %(name)s - %(levelname)s - %(message)s',
    datefmt='%b %d %H:%M:%S'
)
ch.setFormatter(formatter)
logger.addHandler(ch)


def print_list(list):
    """
    Used for printing a list
    """
    for entry in list:
        print entry

    return 0


def print_items_json(dict, *args):
    """
    Used for printing certain items of a dictionary in json
    """

    new_dict = {}
    # Testing to see if any attrs were passed
    # in and if so only print those key/values.
    try:
        for key in args[0]:
            try:
                new_dict[key] = dict[key]
            except KeyError, e:
                msg = "%s is not a valid attr" % (e,)
                raise KeyError(msg)
    except KeyError:
        raise

    print json.dumps(new_dict)

    return 0


class is_pingable_action(argparse.Action):
    """
    Used by argparse to see if the NetScaler specified is alive (pingable)
    """

    def __call__(self, parser, namespace, values, option_string=None):
        pingCmd = "ping -c 1 -W 2 %s" % (values)
        process = subprocess.call(
            pingCmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if process != 0:
            msg = "%s is not alive." % (values)
            print >> sys.stderr, msg
            return sys.exit(1)

        setattr(namespace, self.dest, values)


class allowed_to_manage(argparse.Action):
    """
    Checks if object is allowed to be managed
    """

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            f = open(netscaler_tool_config, 'r')
        except IOError, e:
            print >> sys.stderr, e
            sys.exit(1)

        ns_config = yaml.load(f)
        f.close()

        if namespace.subparserName == "server":
            # Checking if specified server is allowed to be managed
            if ns_config["external_nodes"]:
                try:
                    cmd = ns_config["external_nodes"]
                    msg = "Running \"%s\" to get a list of manageable " \
                          "servers" % (cmd,)
                    logger.info(msg)
                    manageable_servers = subprocess.check_output(
                        cmd.split()
                    )
                except subprocess.CalledProcessError, e:
                    print >> sys.stderr, e
                    logger.critical(e)
                    sys.exit(1)

                if values not in manageable_servers.split('\n'):
                    msg = "%s is not a manageable server. If you would " \
                          "like to change this, please update " \
                          "external_nodes in %s" % (values,
                                                    netscaler_tool_config)
                    print >> sys.stderr, msg
                    logger.error(msg)
                    sys.exit(1)
            else:
                msg = "external_nodes not set in %s. All servers are " \
                      "allowed to be managed" % (netscaler_tool_config,)
                logger.info(msg)

        # Checking if specified vserver is allowed to be managed
        elif namespace.subparserName == "vserver":
            if values not in ns_config["manage_vservers"]:
                msg = "%s is a vserver that is not allowed to be managed. " \
                      "If you would like to change this, please update %s." \
                      % (values, netscaler_tool_config)
                print >> sys.stderr, msg
                logger.info(msg)
                sys.exit(1)

        setattr(namespace, self.dest, values)


class Base(object):
    def __init__(self, args):
        self.args = args
        self.host = args.host
        self.passwd = args.passwd
        self.user = args.user
        self.debug = args.debug
        self.dryrun = args.dryrun

        try:
            self.config = self.fetch_config(netscaler_tool_config)
        except IOError:
            raise

        # If the operator doesn't specify a user, let's grab it from the config
        if not self.user:
            self.user = self.config['user']

        # If the operator doesn't specify a passwd, let's grab it from the
        # config
        if not self.passwd:
            self.passwd = self.config['passwd']

    def create_client(self):
        # Creating a client instance
        try:
            self.client = netscalerapi.Client(
                self.host, self.user, self.passwd, self.debug
            )
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
    def fetch_config(self, netscaler_tool_config):
        try:
            f = open(netscaler_tool_config)
        except IOError:
            raise

        config = yaml.load(f)
        f.close()

        # Returning passwd
        return config

    def get_bound_services(self, vserver):
        object = ["lbvserver_binding", vserver]
        list_of_bound_services = []

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            raise RuntimeError(e)

        for service in \
                output['lbvserver_binding'][0]['lbvserver_service_binding']:
            list_of_bound_services.append(service['servicename'])

        list_of_bound_services.sort()
        return list_of_bound_services

    def get_saved_config(self):
        object = ["nssavedconfig"]

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "There was a problem getting the saved config: %s" % (e)
            raise RuntimeError(msg)

        return output['nssavedconfig']['textblob']

    def get_running_config(self):
        object = ["nsrunningconfig"]

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "There was a problem getting the running config: %s" % (e)
            raise RuntimeError(msg)

        return output['nsrunningconfig']['response']

    def get_lbvserver_service_binding(self, vserver):
        services_ips = {}

        object = ["lbvserver_service_binding", vserver]
        try:
            services = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get info about LB vserver %s on " \
                  "%s.\n%s" % (vserver, self.host, e)
            raise RuntimeError(msg)

        for service in services[object[0]]:
            services_ips[str(service['servicename'])] = str(service['ipv46'])

        return services_ips

    def get_lb(self):
        attr = self.args.attr
        vserver = self.args.vserver

        object = ["lbvserver", vserver]
        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get info about LB vserver %s on " \
                  "%s.\n%s" % (vserver, self.host, e)
            raise RuntimeError(msg)

        return output[object[0]][0], attr

    def get_server_binding(self, server):
        services = []
        object = ["server_binding", server]
        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get server binding for server %s " \
                  "on %s.\n%s" % (server, self.host, e)
            raise RuntimeError(msg)

        for service in output[object[0]][0]['server_service_binding']:
            services.append(service['servicename'])

        return services

    def get_server_binding_service_details(self, server):
        object = ["server_binding", server]

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get server binding for server %s" \
                  "on %s.\n%s" % (server, self.host, e)
            raise RuntimeError(msg)

        return output[object[0]][0]['server_service_binding']

    def vserver(self):
        pass

class Stat(Base):
    def __init__(self, args):
        super(Stat, self).__init__(args)
        self.client = self.create_client()

    def lbvservers(self):
        stat = self.args.stat
        object = ["lbvserver"]
        try:
            output = self.client.get_object(object,"stats")
        except RunTimeError, e:
            msg = "Could not get stat: %s on %s" % (e, self.host)
            raise RuntimeError(msg)
        for entry in output['lbvserver']:
            print json.dumps({entry['name']: entry[stat]})

class Show(Base):
    def __init__(self, args):
        super(Show, self).__init__(args)
        self.client = self.create_client()

    def server(self):
        server = self.args.server

        if self.args.services:
            try:
                list = self.get_server_binding_service_details(server)
            except RuntimeError, e:
                msg = "Problem while trying to get list of services bound " \
                      "to %s.\n%s" % (server, e)
                raise RuntimeError(msg)

            for entry in list:
                print json.dumps(entry)
        else:
            object = ["server", server]
            try:
                output = self.client.get_object(object)
            except RuntimeError, e:
                msg = "Problem while trying to get list of servers " \
                      "on %s.\n%s" % (self.host, e)
                raise RuntimeError(msg)

            print json.dumps(output['server'][0])

    def servers(self):
        object = ["server"]
        listOfServers = []

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of servers " \
                  "on %s.\n%s" % (self.host, e)
            raise RuntimeError(msg)

        for server in output['server']:
            listOfServers.append(server['name'])

        print_list(sorted(listOfServers))

    def services(self):
        object = ["service"]
        listOfServices = []

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of services " \
                  "on %s.\n%s" % (self.host, e)
            raise RuntimeError(msg)

        for service in output['service']:
            listOfServices.append(service['name'])

        print_list(sorted(listOfServices))

    def lbvservers(self):
        object = ["lbvserver"]
        listOfLbVservers = []

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of LB vservers " \
                  "on %s.\n%s" % (self.host, e)
            raise RuntimeError(msg)

        for vserver in output['lbvserver']:
            listOfLbVservers.append(vserver['name'])

        print_list(sorted(listOfLbVservers))

    def lbvserver(self):
        vserver = self.args.vserver
        attr = self.args.attr
        services = self.args.services
        servers = self.args.servers

        if services:
            output = self.get_lbvserver_service_binding(vserver)
            for service in sorted(output.keys()):
                print service
        elif servers:
            output = self.get_lbvserver_service_binding(vserver)
            for service in sorted(output.keys()):
                try:
                    # Looking up IPs via DNS instead of asking the Netscaler
                    # for its service-to-server binding, since it is slow.
                    print socket.gethostbyaddr(output[service])[0].split(
                        '.')[0]
                except socket.herror, e:
                    raise RuntimeError(e)
        else:
            output, attrs = self.get_lb()
            if attrs:
                print_items_json(output, attr)
            else:
                print json.dumps(output)

    def csvservers(self):
        object = ["csvserver"]
        list_of_cs_vservers = []

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get list of CS vservers " \
                  "on %s.\n%s" % (self.host, e)
            raise RuntimeError(msg)

        for vserver in output['csvserver']:
            list_of_cs_vservers.append(vserver['name'])

        print_list(sorted(list_of_cs_vservers))

    def primarynode(self):
        object = ["hanode"]

        try:
            output = self.client.get_object(object)
        except RuntimeError, e:
            msg = "Problem while trying to get IP of primary node " \
                  "of %s.\n%s" % (self.host, e)
            raise RuntimeError(msg)

        # Grabbing the IP of the current primary
        print output['hanode'][0]['routemonitor']

    def savedconfig(self):
        print self.get_saved_config()

    def runningconfig(self):
        print self.get_running_config()

    def get_service_stats(self, service, *args):
        mode = 'stats'
        object = ["service", service]
        DictOfServiceStats = {}

        if args:
            object.extend(args)

        try:
            output = self.client.get_object(object, mode)
        except RuntimeError:
            raise

        for stat in args:
            try:
                DictOfServiceStats[stat] = output['service'][0][stat]
            except KeyError:
                msg = "%s is not a valid stat." % (stat)
                raise KeyError(msg)

        return DictOfServiceStats

    def sslcerts(self):
        object = ["sslcertkey"]
        try:
            output = self.client.get_object(object)
        except RuntimeError:
            raise

        if self.args.debug:
            print "\n<SSL Cert Name>:<Days to Expiration>"
        for cert in output['sslcertkey']:
            print "%s:%s" % (cert['certkey'], cert['daystoexpiration'])

    def surgetotal(self):
        vserver = self.args.vserver
        surgeCountTotal = 0

        try:
            output = self.get_bound_services(vserver)
        except RuntimeError, e:
            msg = "Problem getting bound services to %s.\n%s" % (vserver, e)
            raise RuntimeError(msg)

        # Going through the list of services to get surge count.
        for service in output:
            try:
                output = self.get_service_stats(service, 'surgecount')
            except RuntimeError, e:
                msg = "Problem getting surgecount of " \
                      "service %s.\n%s" % (service, e)
                raise RuntimeError(msg)

            surge = int(output['surgecount'])
            if self.args.debug:
                print "%s: %d" % (service, surge)
            surgeCountTotal += surge

        if self.args.debug:
            print "\nTotal Surge Queue Size is:"

        print surgeCountTotal

    def system(self):
        mode = 'stats'
        object = ["system"]

        try:
            output = self.client.get_object(object, mode)
        except RuntimeError:
            raise
        print json.dumps(output['system'])


class Compare(Base):
    def __init__(self, args):
        super(Compare, self).__init__(args)
        self.client = self.create_client()

    def cleanup_config(self, config, ignore_res):
        newConfig = []
        for line in config:
            if not re.match(ignore_res, line):
                newConfig.append(line)

        return newConfig

    def configs(self):
        # Regex that will be used to ignore lines we know are only in saved or
        # running configs, which will always show up in a diff.
        ignore_res = "^# Last modified|^set appfw|^set lb monitor https? HTTP"

        # Getting saved and running configs. Splitting on newline
        # to make it easier to compare the two.
        saved = self.get_saved_config().split('\n')
        running = self.get_running_config().split('\n')

        # Parsing configs and creating new lists that exclude
        # anything lines that much ignore_res.
        saved = self.cleanup_config(saved, ignore_res)
        running = self.cleanup_config(running, ignore_res)

        # If the configs have differences, why have a problem
        if saved != running:
            # Converted lists to sets so we can find differences
            diff = set(saved) ^ set(running)

            # Returned the sets to lists for formatting purposes
            msg = "Saved and running configs are different:\n%s" \
                  % ('\n'.join(list(diff)))
            raise RuntimeError(msg)

    def lbvservers(self):
        vserver1 = self.args.vserver1
        vserver2 = self.args.vserver2

        # If the user tries to compare the same vservers
        if vserver1 == vserver2:
            msg = "%s and %s are the same vserver. Please pick two " \
                  "different vservers." % (vserver1, vserver2)
            raise RuntimeError(msg)

        # Getting a list of bound services to each vserver so that we
        # can compare.
        listOfServices1 = self.get_lbvserver_service_binding(vserver1)
        listOfServices2 = self.get_lbvserver_service_binding(vserver2)

        # If we get a diff, we will let the user know
        diff = set(listOfServices1) ^ set(listOfServices2)
        if diff:
            msg = "The following services are either bound to %s or %s but " \
                  "not both:\n%s" % (vserver1, vserver2,
                                     '\n'.join(sorted(list(diff))))
            raise RuntimeError(msg)


class Enable(Base):
    def __init__(self, args):
        super(Enable, self).__init__(args)
        self.client = self.create_client()

    def server(self):
        server = self.args.server
        services = self.get_server_binding(server)

        if self.args.debug:
            print "\nServices bound to %s: %s" % (server, services)

        for service in services:
            properties = {
                'params': {'action': "enable"},
                'service': {'name': str(service)},
            }

            try:
                if self.args.debug:
                    print "\nAttempting to enable service %s" % (service)
                self.client.modify_object(properties)
            except RuntimeError:
                raise

    def vserver(self):
        vserver = self.args.vserver

        properties = {
            'params': {'action': "enable"},
            'vserver': {'name': str(vserver)},
        }

        try:
            if self.args.debug:
                print "\nAttempting to enable vserver %s" % (vserver)
            self.client.modify_object(properties)
        except RuntimeError:
            raise

        super(Enable, self).vserver()


class Disable(Base):
    def __init__(self, args):
        super(Disable, self).__init__(args)
        self.client = self.create_client()

    def server(self):
        delay = self.args.delay
        server = self.args.server
        services = self.get_server_binding(server)

        if self.args.debug:
            print "\nServices bound to %s: %s" % (server, services)

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
                self.client.modify_object(properties)
            except RuntimeError:
                raise

    def vserver(self):
        vserver = self.args.vserver

        properties = {
            'params': {'action': "disable"},
            'vserver': {'name': str(vserver)},
        }

        try:
            if self.args.debug:
                print "\nAttempting to disable vserver %s" % (vserver)
            self.client.modify_object(properties)
        except RuntimeError:
            raise

        super(Disable, self).vserver()


class Bounce(Disable, Enable):
    def vserver(self):
        super(Bounce, self).vserver()


def main():
    # Created parser.
    parser = argparse.ArgumentParser()

    # Global args
    parser.add_argument(
        "host", metavar='NETSCALER', action=is_pingable_action, help="IP or \
        name of NetScaler."
    )
    parser.add_argument("--user", dest="user", help="NetScaler user account.")
    parser.add_argument(
        "--passwd", dest="passwd", help="Password for user. Default is to \
        fetch from netscalertool.conf."
    )
    parser.add_argument(
        "--nodns", action="store_true", dest="noDns", help="Won't try to \
        resolve any netscaler objects.", default=False
    )
    parser.add_argument(
        "--debug", action="store_true", dest="debug", help="Shows what's \
        going on.", default=False
    )
    parser.add_argument(
        "--dryrun", action="store_true", dest="dryrun", help="Dryrun.",
        default=False
    )

    # Creating subparser.
    subparser = parser.add_subparsers(dest='topSubparserName')

    # Creating show subparser.
    parserShow = subparser.add_parser(
        'show', help='sub-command for showing objects'
    )
    subparserShow = parserShow.add_subparsers(dest='subparserName')
    subparserShow.add_parser('lb-vservers', help='Shows all lb vservers')
    parserShowLbVserver = subparserShow.add_parser(
        'lb-vserver', help='Shows stat(s) of a specified lb vserver'
    )
    parserShowLbVserver.add_argument(
        'vserver', help='Shows stats for specified vserver'
    )
    parserShowLbVserverGroup = parserShowLbVserver\
        .add_mutually_exclusive_group()
    parserShowLbVserverGroup.add_argument(
        '--attr', dest='attr', nargs='*', help='Shows only the specified \
        attribute(s)'
    )
    parserShowLbVserverGroup.add_argument(
        '--services', action='store_true', help='Shows services bound to \
        specified lb vserver'
    )
    parserShowLbVserverGroup.add_argument(
        '--servers', action='store_true', help='Shows servers bound to \
        specified lb vserver'
    )
    subparserShow.add_parser('cs-vservers', help='Shows all cs vservers')
    parserShowServer = subparserShow.add_parser(
        'server', help='Shows server info'
    )
    parserShowServer.add_argument('server', help='Shows server details')
    parserShowServer.add_argument(
        '--services', action='store_true', help='Shows services bound to \
        server and their status'
    )
    subparserShow.add_parser('servers', help='Shows all servers')
    subparserShow.add_parser('services', help='Shows all services')
    subparserShow.add_parser(
        'primary-node', help='Shows which of the two nodes is primary'
    )
    subparserShow.add_parser(
        'ssl-certs', help='Shows ssl certs and days until expiring'
    )
    parserShowSurgeTotal = subparserShow.add_parser(
        'surge-total', help='Shows surge total for a lb vserver'
    )
    parserShowSurgeTotal.add_argument(
        'vserver', help='Shows surge total for which lb vserver'
    )
    subparserShow.add_parser('saved-config', help='Shows saved ns config')
    subparserShow.add_parser('running-config', help='Shows running ns config')
    subparserShow.add_parser('system', help='Shows system counters')

    # Creating stat subparser
    parserStat = subparser.add_parser(
        'stat', help='sub-command for showing object stats'
    )
    subparserStat = parserStat.add_subparsers(dest='subparserName')
    parserStatLbVservers = subparserStat.add_parser(
        'lb-vservers', help='Shows stats of all lbvservers'
    )
    parserStatLbVservers.add_argument(
        'stat', help='Select specific stat to display'
    )

    # Creating compare subparser.
    parserCmp = subparser.add_parser(
        'compare', help='sub-command for comparing objects'
    )
    subparserCmp = parserCmp.add_subparsers(dest='subparserName')
    subparserCmp.add_parser(
        'configs', help='Compares running and saved ns configs'
    )
    parserCmpLbVservers = subparserCmp.add_parser(
        'lb-vservers', help='Compares configs between two vservers'
    )
    parserCmpLbVservers.add_argument('vserver1', metavar='VSERVER1')
    parserCmpLbVservers.add_argument('vserver2', metavar='VSERVER2')

    # Creating enable subparser.
    parserEnable = subparser.add_parser(
        'enable', help='sub-command for enable objects'
    )
    subparserEnable = parserEnable.add_subparsers(dest='subparserName')
    parserEnableServer = subparserEnable.add_parser(
        'server', help='Enable server. Will actually enable all servies bound \
        to server'
    )
    parserEnableServer.add_argument(
        'server', action=allowed_to_manage, help='Server to enable'
    )
    parserEnableVserver = subparserEnable.add_parser(
        'vserver', help='Enable vserver'
    )
    parserEnableVserver.add_argument(
        'vserver', action=allowed_to_manage, help='Vserver to enable'
    )

    # Creating disable subparser.
    parserDisable = subparser.add_parser(
        'disable', help='sub-command for disabling objects'
    )
    subparserDisable = parserDisable.add_subparsers(dest='subparserName')
    parserDisableServer = subparserDisable.add_parser(
        'server', help='Disable server'
    )
    parserDisableServer.add_argument(
        'server', action=allowed_to_manage, help='Server to disable. Will \
        actually disable all services bound to server'
    )
    parserDisableServer.add_argument(
        '--delay', type=int, help='The time allowed (in seconds) for a \
        graceful shutdown. Defaults to 3 seconds', default=3
    )
    parserDisableVserver = subparserDisable.add_parser(
        'vserver', help='Disable vserver'
    )
    parserDisableVserver.add_argument(
        'vserver', action=allowed_to_manage, help='Vserver to disable'
    )

    # Creating disable subparser.
    parserBounce = subparser.add_parser(
        'bounce', help='sub-command for bouncing objects'
    )
    subparserBounce = parserBounce.add_subparsers(dest='subparserName')
    parserBounceVserver = subparserBounce.add_parser(
        'vserver', help='Bounce vserver'
    )
    parserBounceVserver.add_argument(
        'vserver', action=allowed_to_manage, help='Vserver to bounce'
    )

    # Getting arguments
    args = parser.parse_args()
    debug = args.debug

    retval = 0

    # Showing user flags and their values
    if debug:
        print "Using the following args:"
        for arg in dir(args):
            regex = "(^_{1,2}|^read_file|^read_module|^ensure_value)"
            if re.match(regex, arg):
                continue
            else:
                print "\t%s: %s" % (arg, getattr(args, arg))
        print

    # Getting method, based on subparser called from argparse.
    method = args.subparserName.replace('-', '')

    # Getting class, based on subparser called from argparse.
    try:
        klass = globals()[args.topSubparserName.capitalize()]
    except KeyError:
        msg = "%s, %s is not a valid subparser." % (user,
                                                    args.topSubparserName)
        print >> sys.stderr, msg
        logger.critical(msg)
        return 1

    try:
        netscaler_tool = klass(args)
    except:
        print >> sys.stderr, sys.exc_info()[1]
        logger.critical(sys.exc_info()[1])
        return 1

    try:
        try:
            getattr(netscaler_tool, method)()
            msg = "%s executed \'%s\' on %s" % (user, args, args.host)
            logger.info(msg)
        except (AttributeError, RuntimeError, KeyError, IOError):
            msg = "%s, %s" % (user, sys.exc_info()[1])
            print >> sys.stderr, msg
            logger.critical(msg)
            retval = 1
    finally:
        # Saving config if we run a enable or disable command
        if args.topSubparserName in ["bounce", "disable", "enable"]:
            try:
                netscaler_tool.client.save_config()
                logger.info("Saving NetScaler config")
            except RuntimeError, e:
                print >> sys.stderr, e
                logger.critical(e)
                retval = 1

        # Logging out of NetScaler.
        try:
            netscaler_tool.client.logout()
            if debug:
                msg = "Logging out of NetScaler %s" % (args.host,)
                logger.debug(msg)
                print "\n", msg
        except RuntimeError, e:
            msg = "%s, %s" % (user, e)
            print >> sys.stderr, msg
            logger.warn(msg)
            retval = 1

        # Exiting program
        return retval


# Run the script only if the script itself is called directly.
if __name__ == '__main__':
    sys.exit(main())

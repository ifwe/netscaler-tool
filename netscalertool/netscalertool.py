#!/usr/bin/env python

"""
Copyright 2014 Tagged Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import json
import logging
import os
import re
import socket
import subprocess
import sys
import time
import yaml

import netscalerapi
import utils


class Base(object):
    def __init__(self, args):
        self.args = args

        try:
            self.config = self.fetch_config()
        except IOError:
            raise

        # If the operator doesn't specify a user, let's grab it from the
        # config
        if not self.args.user:
            self.args.user = self.config['user']

        # If the operator doesn't specify a passwd, let's grab it from the
        # config
        if not self.args.passwd:
            self.args.passwd = self.config['passwd']

        # Creating a client instance
        try:
            self.client = netscalerapi.Client(args)
        except RuntimeError as e:
            msg = "Problem creating client instance.\n%s" % e
            raise RuntimeError(msg)

        # Login using client instance
        try:
            self.client.login()
        except RuntimeError:
            raise

    def fetch_config(self):
        """Fetch configuration from file"""
        try:
            f = open(self.args.ns_config_file)
        except IOError:
            raise

        config = yaml.load(f)
        f.close()

        # Returning passwd
        return config

    def get_bound_services(self, vserver):
        ns_object = ["lbvserver_binding", vserver]
        list_of_bound_services = []

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            raise RuntimeError(e)

        for service in \
                output['lbvserver_binding'][0]['lbvserver_service_binding']:
            list_of_bound_services.append(service['servicename'])

        list_of_bound_services.sort()
        return list_of_bound_services

    def get_saved_config(self):
        ns_object = ["nssavedconfig"]

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "There was a problem getting the saved config: %s" % e
            raise RuntimeError(msg)

        return output['nssavedconfig']['textblob']

    def get_running_config(self):
        ns_object = ["nsrunningconfig"]

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "There was a problem getting the running config: %s" % e
            raise RuntimeError(msg)

        return output['nsrunningconfig']['response']

    def get_lbvserver_service_binding(self, vserver):
        services_ips = {}

        ns_object = ["lbvserver_service_binding", vserver]
        try:
            services = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get info about LB vserver %s on " \
                  "%s.\n%s" % (vserver, self.args.host, e)
            raise RuntimeError(msg)

        try:
            for service in services[ns_object[0]]:
                services_ips[str(service['servicename'])] = str(
                    service['ipv46'])
        except KeyError:
            msg = "%s does not have any services bound to it." % vserver
            raise RuntimeError(msg)

        return services_ips

    def get_lb(self):
        attr = self.args.attr
        vserver = self.args.vserver

        ns_object = ["lbvserver", vserver]
        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get info about LB vserver %s on " \
                  "%s.\n%s" % (vserver, self.args.host, e)
            raise RuntimeError(msg)

        return output[ns_object[0]][0], attr

    def get_server_binding(self, server):
        services = []
        ns_object = ["server_binding", server]
        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get server binding for server %s" \
                  " on %s.\n%s" % (
                      server, self.args.host, e)
            raise RuntimeError(msg)

        for service in output[ns_object[0]][0]['server_service_binding']:
            services.append(service['servicename'])

        return services

    def get_server_binding_service_details(self, server):
        ns_object = ["server_binding", server]

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get server binding for server %s" \
                  "on %s.\n%s" % (server, self.args.host, e)
            raise RuntimeError(msg)

        return output[ns_object[0]][0]['server_service_binding']

    def vserver(self):
        pass


class Stat(Base):
    def lbvservers(self):
        stat = self.args.stat
        ns_object = ["lbvserver"]

        try:
            output = self.client.get_object(ns_object, "stats")
        except RuntimeError as e:
            msg = "Could not get stat: %s on %s" % (e, self.args.host)
            raise RuntimeError(msg)

        for entry in output['lbvserver']:
            try:
                print json.dumps({entry['name']: entry[stat]})
            except KeyError:
                msg = "%s is not a valid stat for lb vservers" % stat
                raise KeyError(msg)

    def ns(self):
        stats = self.args.stats
        ns_object = ["ns"]

        try:
            output = self.client.get_object(ns_object, "stats")
        except RuntimeError as e:
            msg = "Could not get stat: %s on %s" % (e, self.args.host)
            raise RuntimeError(msg)

        if stats:
            specified_stats = {}
            for stat in stats:
                try:
                    specified_stats[stat] = output['ns'][stat]
                except KeyError:
                    msg = "%s is not a valid stat for ns" % stat
                    raise KeyError(msg)

            output['ns'] = specified_stats

        print json.dumps(output['ns'])


class Show(Base):
    def server(self):
        server = self.args.server

        if self.args.services:
            try:
                ns_list = self.get_server_binding_service_details(server)
            except RuntimeError as e:
                msg = "Problem while trying to get list of services bound " \
                      "to %s.\n%s" % (server, e)
                raise RuntimeError(msg)

            for entry in ns_list:
                print json.dumps(entry)
        else:
            ns_object = ["server", server]
            try:
                output = self.client.get_object(ns_object)
            except RuntimeError as e:
                msg = "Problem while trying to get list of servers " \
                      "on %s.\n%s" % (self.args.host, e)
                raise RuntimeError(msg)

            print json.dumps(output['server'][0])

    def servers(self):
        ns_object = ["server"]
        list_of_servers = []

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get list of servers " \
                  "on %s.\n%s" % (self.args.host, e)
            raise RuntimeError(msg)

        for server in output['server']:
            list_of_servers.append(server['name'])

        utils.print_list(sorted(list_of_servers))

    def services(self):
        ns_object = ["service"]
        list_of_services = []

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get list of services " \
                  "on %s.\n%s" % (self.args.host, e)
            raise RuntimeError(msg)

        for service in output['service']:
            list_of_services.append(service['name'])

        utils.print_list(sorted(list_of_services))

    def lbvservers(self):
        ns_object = ["lbvserver"]
        list_of_lbvservers = []

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get list of LB vservers " \
                  "on %s.\n%s" % (self.args.host, e)
            raise RuntimeError(msg)

        for vserver in output['lbvserver']:
            list_of_lbvservers.append(vserver['name'])

        utils.print_list(sorted(list_of_lbvservers))

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
                except socket.herror as e:
                    raise RuntimeError(e)
        else:
            output, attrs = self.get_lb()
            if attrs:
                utils.print_items_json(output, attr)
            else:
                print json.dumps(output)

    def csvservers(self):
        ns_object = ["csvserver"]
        list_of_cs_vservers = []

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get list of CS vservers " \
                  "on %s.\n%s" % (self.args.host, e)
            raise RuntimeError(msg)

        for vserver in output['csvserver']:
            list_of_cs_vservers.append(vserver['name'])

        utils.print_list(sorted(list_of_cs_vservers))

    def primarynode(self):
        ns_object = ["hanode"]

        try:
            output = self.client.get_object(ns_object)
        except RuntimeError as e:
            msg = "Problem while trying to get IP of primary node " \
                  "of %s.\n%s" % (self.args.host, e)
            raise RuntimeError(msg)

        # Grabbing the IP of the current primary
        print output['hanode'][0]['routemonitor']

    def savedconfig(self):
        print self.get_saved_config()

    def runningconfig(self):
        print self.get_running_config()

    def get_service_stats(self, service, *args):
        mode = 'stats'
        ns_object = ["service", service]
        dict_of_service_stats = {}

        if args:
            ns_object.extend(args)

        try:
            output = self.client.get_object(ns_object, mode)
        except RuntimeError:
            raise

        for stat in args:
            try:
                dict_of_service_stats[stat] = output['service'][0][stat]
            except KeyError:
                msg = "%s is not a valid stat." % stat
                raise KeyError(msg)

        return dict_of_service_stats

    def sslcerts(self):
        ns_object = ["sslcertkey"]
        try:
            output = self.client.get_object(ns_object)
        except RuntimeError:
            raise

        if self.args.debug:
            print "\n<SSL Cert Name>:<Days to Expiration>"
        for cert in output['sslcertkey']:
            print "%s:%s" % (cert['certkey'], cert['daystoexpiration'])

    def system(self):
        mode = 'stats'
        ns_object = ["system"]

        try:
            output = self.client.get_object(ns_object, mode)
        except RuntimeError:
            raise
        print json.dumps(output['system'])


def cleanup_config(config, ignore_res):
    new_config = []
    for line in config:
        if not re.match(ignore_res, line):
            new_config.append(line)

    return new_config


class Compare(Base):
    def configs(self):
        # Regex that will be used to ignore lines we know are only in saved or
        # running configs, which will always show up in a diff.
        ignore_res = "^# Last modified|^set appfw|^set lb monitor https? HTTP|^set cache parameter|^set ns tcpParam|^add system user|^set system user"

        # Parsing configs and creating new lists that exclude any lines that
        # much ignore_res.
        saved = cleanup_config(self.get_saved_config().split('\n'),
                               ignore_res)
        running = cleanup_config(self.get_running_config().split('\n'),
                                 ignore_res)

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
        list_of_services1 = self.get_lbvserver_service_binding(vserver1)
        list_of_services2 = self.get_lbvserver_service_binding(vserver2)

        # If we get a diff, we will let the user know
        diff = set(list_of_services1) ^ set(list_of_services2)
        if diff:
            msg = "The following services are either bound to %s or %s but " \
                  "not both:\n%s" % (vserver1, vserver2,
                                     '\n'.join(sorted(list(diff))))
            raise RuntimeError(msg)


class Enable(Base):
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
                    print "\nAttempting to enable service %s" % service
                self.client.modify_object(properties)
            except RuntimeError:
                raise

    def vserver(self):
        debug = self.args.debug
        sleep = self.args.sleep
        vserver = self.args.vserver

        properties = {
            'params': {'action': "enable"},
            'vserver': {'name': str(vserver)},
        }

        try:
            if debug:
                print "\nAttempting to enable vserver %s" % vserver
            if sleep:
                if debug:
                    print "Sleeping %d seconds before enabling %s" % (sleep,
                                                                      vserver)
                time.sleep(sleep)
            self.client.modify_object(properties)
        except RuntimeError:
            raise

        super(Enable, self).vserver()


class Disable(Base):
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
                    print "\nAttempting to disable service %s" % service
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
                print "\nAttempting to disable vserver %s" % vserver
            self.client.modify_object(properties)
        except RuntimeError:
            raise

        super(Disable, self).vserver()


class Bounce(Disable, Enable):
    def vserver(self):
        super(Bounce, self).vserver()


# noinspection PyBroadException
def main():
    ns_config_file = "/etc/netscalertool.conf"
    log_file = "/var/log/netscaler-tool/netscaler-tool.log"

    ##### Setting up logging #####
    # Grabbing the user that is running this script for logging purposes
    if os.getenv('SUDO_USER'):
        user = os.getenv('SUDO_USER')
    else:
        user = os.getenv('USER')

    try:
        local_host = socket.gethostbyaddr(socket.gethostname())[1][0]
    except (socket.herror, socket.gaierror):
        local_host = 'localhost'
    logger = logging.getLogger(local_host)
    logger.setLevel(logging.DEBUG)

    try:
        ch = logging.FileHandler(log_file)
    except IOError as e:
        print >> sys.stderr, e
        sys.exit(1)

    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s - %(levelname)s - %(message)s',
        datefmt='%b %d %H:%M:%S'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    ##### Setting up logging #####

    class IsPingableAction(argparse.Action):
        """
        Used by argparse to check if the NetScaler specified is pingable
        """

        def __call__(self, parser, namespace, values, option_string=None):
            ping_cmd = "ping -c 1 -W 2 %s" % values
            process = subprocess.call(
                ping_cmd.split(), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if process != 0:
                msg = "%s is not alive." % values
                print >> sys.stderr, msg
                return sys.exit(1)

            setattr(namespace, self.dest, values)

    class AllowedToManage(argparse.Action):
        """
        Used by argparse to checks if NetScaler object is allowed to be managed
        """

        def __call__(self, parser, namespace, values, option_string=None):
            ns_config_file = namespace.ns_config_file

            try:
                f = open(ns_config_file, 'r')
                ns_config = yaml.load(f)
                f.close()
            except IOError as e:
                msg = "Problem with %s: %s" % (ns_config_file, e)
                print >> sys.stderr, msg
                sys.exit(1)

            if namespace.subparser_name == "server":
                # Checking if specified server is allowed to be managed
                try:
                    cmd = ns_config["external_nodes"]
                    try:
                        msg = "Running \"%s\" to get a list of manageable " \
                              "servers" % cmd
                        logger.info(msg)
                        manageable_servers = subprocess.check_output(
                            cmd.split()
                        )
                    except (OSError, subprocess.CalledProcessError) as e:
                        msg = "Problem running %s:\n%s" % (cmd, e)
                        print >> sys.stderr, msg
                        logger.critical(msg)
                        sys.exit(1)

                    if values not in manageable_servers.split('\n'):
                        msg = "%s is not a manageable server. If you would " \
                              "like to change this, please update " \
                              "external_nodes in %s" % (values, ns_config_file)
                        print >> sys.stderr, msg
                        logger.error(msg)
                        sys.exit(1)
                except KeyError:
                    msg = "external_nodes not set in %s. All servers are " \
                          "allowed to be managed" % ns_config_file
                    logger.info(msg)

            # Checking if specified vserver is allowed to be managed
            elif namespace.subparser_name == "vserver":
                if values not in ns_config["manage_vservers"]:
                    msg = "%s is a vserver that is not allowed to be " \
                          "managed. If you would like to change this, " \
                          "please update %s." % (
                              values, ns_config_file)
                    print >> sys.stderr, msg
                    logger.info(msg)
                    sys.exit(1)

            setattr(namespace, self.dest, values)

    # Create parser
    parser = argparse.ArgumentParser()

    # Setting some defaults
    parser.set_defaults(ns_config_file=ns_config_file)
    parser.set_defaults(log_file=log_file)

    parser.add_argument(
        "host", metavar='NETSCALER', action=IsPingableAction, help="IP or \
        DNS name of NetScaler"
    )
    parser.add_argument("--user", help="NetScaler user account")
    parser.add_argument(
        "--passwd", dest="passwd", help="Password for user. Default is to \
        fetch from /etc/netscalertool.conf"
    )
    parser.add_argument(
        "--nodns", action="store_true", help="Won't try to resolve any "
        "NetScaler objects", default=False
    )
    parser.add_argument(
        "--debug", action="store_true", help="Shows what's \
        going on", default=False
    )
    parser.add_argument(
        "--dryrun", action="store_true", help="Dryrun", default=False)

    # Creating subparser.
    subparser = parser.add_subparsers(dest='top_subparser_name')

    # Creating show subparser.
    parser_show = subparser.add_parser(
        'show', help='sub-command for showing objects'
    )
    subparser_show = parser_show.add_subparsers(dest='subparser_name')
    subparser_show.add_parser('lb-vservers', help='Shows all lb vservers')
    parser_show_lbvserver = subparser_show.add_parser(
        'lb-vserver', help='Shows stat(s) of a specified lb vserver'
    )
    parser_show_lbvserver.add_argument(
        'vserver', help='Shows stats for specified vserver'
    )
    parser_show_lbvserver_group = parser_show_lbvserver \
        .add_mutually_exclusive_group()
    parser_show_lbvserver_group.add_argument(
        '--attr', dest='attr', nargs='*', help='Shows only the specified \
        attribute(s)'
    )
    parser_show_lbvserver_group.add_argument(
        '--services', action='store_true', help='Shows services bound to \
        specified lb vserver'
    )
    parser_show_lbvserver_group.add_argument(
        '--servers', action='store_true', help='Shows servers bound to \
        specified lb vserver'
    )
    subparser_show.add_parser('cs-vservers', help='Shows all cs vservers')
    parser_show_server = subparser_show.add_parser(
        'server', help='Shows server info'
    )
    parser_show_server.add_argument('server', help='Shows server details')
    parser_show_server.add_argument(
        '--services', action='store_true', help='Shows services bound to \
        server and their status'
    )
    subparser_show.add_parser('servers', help='Shows all servers')
    subparser_show.add_parser('services', help='Shows all services')
    subparser_show.add_parser(
        'primary-node', help='Shows which of the two nodes is primary'
    )
    subparser_show.add_parser(
        'ssl-certs', help='Shows ssl certs and days until expiring'
    )
    subparser_show.add_parser('saved-config', help='Shows saved ns config')
    subparser_show.add_parser('running-config',
                              help='Shows running ns config')
    subparser_show.add_parser('system', help='Shows system counters')

    # Creating stat subparser
    parser_stat = subparser.add_parser(
        'stat', help='sub-command for showing ns_object stats'
    )
    subparser_stat = parser_stat.add_subparsers(dest='subparser_name')
    parser_stat_lb_vservers = subparser_stat.add_parser(
        'lb-vservers', help='Show one statistic of all lbvservers'
    )
    parser_stat_lb_vservers.add_argument(
        'stat', help='Select specific stat to display'
    )
    parser_stat_ns = subparser_stat.add_parser(
        'ns', help='Shows statistics for NetScaler'
    )
    parser_stat_ns.add_argument(
        '--stats', nargs='*', help='Select NetScaler statistics to show'
    )

    # Creating compare subparser.
    parser_cmp = subparser.add_parser(
        'compare', help='sub-command for comparing objects'
    )
    subparser_cmp = parser_cmp.add_subparsers(dest='subparser_name')
    subparser_cmp.add_parser(
        'configs', help='Compares running and saved ns configs'
    )
    parser_cmp_lbvservers = subparser_cmp.add_parser(
        'lb-vservers', help='Compares configs between two vservers'
    )
    parser_cmp_lbvservers.add_argument('vserver1', metavar='VSERVER1')
    parser_cmp_lbvservers.add_argument('vserver2', metavar='VSERVER2')

    # Creating enable subparser.
    parser_enable = subparser.add_parser(
        'enable', help='sub-command for enable objects'
    )
    subparser_enable = parser_enable.add_subparsers(dest='subparser_name')
    parser_enable_server = subparser_enable.add_parser(
        'server',
        help='Enable server. Will actually enable all services bound to '
             'server'
    )
    parser_enable_server.add_argument(
        'server', action=AllowedToManage, help='Server to enable'
    )
    parser_enable_vserver = subparser_enable.add_parser(
        'vserver', help='Enable vserver'
    )
    parser_enable_vserver.add_argument(
        'vserver', action=AllowedToManage, help='Vserver to enable'
    )

    # Creating disable subparser.
    parser_disable = subparser.add_parser(
        'disable', help='sub-command for disabling objects'
    )
    subparser_disable = parser_disable.add_subparsers(dest='subparser_name')
    parser_disable_server = subparser_disable.add_parser(
        'server', help='Disable server'
    )
    parser_disable_server.add_argument(
        'server', action=AllowedToManage, help='Server to disable. actually '
        'disable all services bound to server, to utilize the graceful delay'
    )
    parser_disable_server.add_argument(
        '--delay', type=int, help='The time allowed (in seconds) for a \
        graceful shutdown. Defaults to 3 seconds', default=3
    )
    parser_disable_vserver = subparser_disable.add_parser(
        'vserver', help='Disable vserver'
    )
    parser_disable_vserver.add_argument(
        'vserver', action=AllowedToManage, help='Vserver to disable'
    )

    # Creating bounce subparser
    parser_bounce = subparser.add_parser(
        'bounce', help='sub-command for bouncing objects'
    )
    subparser_bounce = parser_bounce.add_subparsers(dest='subparser_name')
    parser_bounce_vserver = subparser_bounce.add_parser(
        'vserver', help='Bounce vserver'
    )
    parser_bounce_vserver.add_argument(
        'vserver', action=AllowedToManage, help='Vserver to bounce'
    )
    parser_bounce_vserver.add_argument('--sleep', type=int, help='Amount of '
                                       'time to sleep between disabling and '
                                       'enabling vserver')

    # Getting arguments
    args = parser.parse_args()

    # Initialize exit return value to 0
    retval = 0

    # Showing user flags and their values
    if args.debug:
        print "Using the following args:"
        for arg in dir(args):
            regex = "(^_{1,2}|^read_file|^read_module|^ensure_value)"
            if re.match(regex, arg):
                continue
            else:
                print "\t%s: %s" % (arg, getattr(args, arg))
        print

    # Getting method, based on subparser called from argparse.
    method = args.subparser_name.replace('-', '')

    # Getting class, based on subparser called from argparse.
    try:
        klass = globals()[args.top_subparser_name.capitalize()]
    except KeyError:
        msg = "%s, %s is not a valid subparser." % (user,
                                                    args.top_subparser_name)
        print >> sys.stderr, msg
        logger.critical(msg)
        return 1

    # Remove password entry, since this info will be sent to a log
    modified_args = vars(args).copy()
    modified_args['passwd'] = "*****"
    msg = "%s will try to execute \'%s\' on %s" % (
        user, modified_args, modified_args['host'])
    logger.info(msg)

    try:
        netscaler_tool = klass(args)
    except:
        print >> sys.stderr, sys.exc_info()[1]
        logger.critical(sys.exc_info()[1])
        return 1

    try:
        try:
            getattr(netscaler_tool, method)()
        except (AttributeError, RuntimeError, KeyError, IOError):
            msg = "%s, %s" % (user, sys.exc_info()[1])
            print >> sys.stderr, msg
            logger.critical(msg)
            retval = 1
    finally:
        # Saving config if we run a enable or disable command
        if args.top_subparser_name in ["bounce", "disable", "enable"]:
            try:
                netscaler_tool.client.save_config()
                logger.info("Saving NetScaler config")
            except RuntimeError as e:
                print >> sys.stderr, e
                logger.critical(e)
                retval = 1

        # Logging out of NetScaler.
        try:
            netscaler_tool.client.logout()
            if args.debug:
                msg = "Logging out of NetScaler %s" % args.host
                logger.debug(msg)
                print "\n", msg
        except RuntimeError as e:
            msg = "%s, %s" % (user, e)
            print >> sys.stderr, msg
            logger.warn(msg)
            retval = 1

    # Exiting program
    return retval


# Run the script only if the script itself is called directly.
if __name__ == '__main__':
    sys.exit(main())

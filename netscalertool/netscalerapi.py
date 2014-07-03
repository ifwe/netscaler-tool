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

import httplib2
import urllib
import sys
import socket

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


class Client:
    def __init__(self, host, user, passwd, debug):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.debug = debug

        #if self.debug:
        #    httplib2.debuglevel=4

    def login(self):
        """
        For debug purposes, print out the headers and the content of the
        response
        """

        # set the headers and the base URL
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        url = "https://%s/nitro/v1/config/" % (self.host)

        # construct the payload with URL encoding
        payload = {"object": {"login": {"username": self.user, "password":
                   self.passwd}}}
        payload_encoded = urllib.urlencode(payload)

        # create a HTTP object, and use it to submit a POST request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        try:
            response, content = http.request(url, 'POST', body=payload_encoded,
                                             headers=headers)
        except socket.error, e:
            msg = "Problem connecting to netscaler %s:\n%s" % (self.host, e)
            raise RuntimeError(msg)

        data = json.loads(content)
        errorcode = data["errorcode"]

        if response.status not in [200, 201] or errorcode != 0:
            raise RuntimeError(content)

        if self.debug:
            print "Nitro API URL: ", url
            print "\n", json.dumps(response)
            print "\n", json.dumps(content)

        data = json.loads(content)
        self.session_id = data["sessionid"]

    def logout(self):
        """
        Logout of the netscaler
        """

        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Cookie': 'sessionid='+self.session_id}
        url = "https://%s/nitro/v1/config/" % (self.host)

        # construct the payload with URL encoding
        payload = {"object": {"logout": {}}}
        payload_encoded = urllib.urlencode(payload)

        # create a HTTP object, and use it to submit a POST request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        response, content = http.request(url, 'POST', body=payload_encoded,
                                         headers=headers)

        # getting the errorcode to see if there was a problem
        error = json.loads(content)['errorcode']

        if error != 0:
            data = json.loads(content)
            msg = "\nCouldn't logout: %s" % (data["message"])
            raise RuntimeError(msg)

    def save_config(self):
        """
        Save netscaler config
        """

        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Cookie': 'sessionid='+self.session_id}
        url = "https://%s/nitro/v1/config/" % (self.host)

        properties = {
            'params': {"action": "save"},
            "nsconfig": {}
        }

        # construct the payload with URL encoding
        payload = {"object": properties}
        payload_encoded = urllib.urlencode(payload)

        # create a HTTP object, and use it to submit a POST request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        response, content = http.request(url, 'POST', body=payload_encoded,
                                         headers=headers)

        # getting the errorcode to see if there was a problem
        error = json.loads(content)['errorcode']

        if error != 0:
            data = json.loads(content)
            msg = "\nCouldn't save config: %s" % (data["message"])
            raise RuntimeError(msg)

    def get_object(self, object, *args):
        """
        If we get stat in our optional args list, that means we need to change
        the url to handle fetching stat objects
        """
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Cookie': 'sessionid='+self.session_id}

        if 'stats' in args:
            url = "https://%s/nitro/v1/stat/%s" % (self.host, '/'.join(object))
        else:
            url = "https://%s/nitro/v1/config/%s" % (self.host,
                                                     '/'.join(object))

        if self.debug:
            print "URL: ", url

        #create a HTTP object, and use it to submit a GET request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        response, content = http.request(url, 'GET', headers=headers)

        if self.debug:
            print "\nResponse: ", response
            print "\nContent: ", content

        data = json.loads(content)
        errorcode = data["errorcode"]

        if response.status != 200 or errorcode != 0:
            raise RuntimeError(content)

        return data

    def modify_object(self, properties):
        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Cookie': 'sessionid='+self.session_id}

        url = "https://%s/nitro/v1/config" % (self.host)
        if self.debug:
            print "URL: ", url

        # construct the payload with URL encoding
        payload = {"object": properties}
        payload_encoded = urllib.urlencode(payload)
        if self.debug:
            print "Payload: ", payload
            print "Payload Encoded: ", payload_encoded

        # create a HTTP object, and use it to submit a PUT request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        response, content = http.request(url, 'POST', body=payload_encoded,
                                         headers=headers)

        if self.debug:
            print "\nResponse: ", response
            print "\nContent: ", content

        if response.status != 200:
            msg = "Error while modifying %s" % (object[1])
            raise RuntimeError(msg)

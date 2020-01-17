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
import json
import urllib
import socket


class Client:
    def __init__(self, args):
        for k, v in vars(args).iteritems():
            setattr(self, k, v)


    def _call(self, method, path, payload=None, error_message=""):
        """
        Dedupes much of the code necessary to facilitate api requests.
        """

        url = "https://%s%s" % (self.host, path)

        headers = {'Content-type': 'application/json'}
        if 'session_id' in dir(self):
           headers['Cookie'] = 'sessionid='+self.session_id

        payload_encoded = json.dumps(payload) if payload else None

        http = httplib2.Http(disable_ssl_certificate_validation=True)
        try:
            response, content = http.request(url, method, body=payload_encoded,
                                             headers=headers)
        except socket.error, e:
            msg = "Problem connecting to NetScaler %s:\n%s" % (self.host, e)
            raise RuntimeError(msg)

        if len(content) > 0:
            data = json.loads(content)
            errorcode = data["errorcode"]
        else:
            data = None
            errorcode = 0

        if response.status not in [200, 201] or errorcode != 0:
            raise RuntimeError("%s: %s" % (error_message, content))

        return data


    def login(self):
        """
        Starts a session with the netscaler.
        """

        path = "/nitro/v1/config/login"

        payload = {"login": {"username": self.user, "password":
                   self.passwd}}

        data = self._call('POST', path, payload,
                          error_message="Couldn't login")

        self.session_id = data["sessionid"]


    def logout(self):
        """
        Logout of the netscaler
        """

        path = "/nitro/v1/config/logout"

        payload = {"logout": {}}

        data = self._call('POST', path, payload,
                          error_message="Couldn't logout")


    def save_config(self):
        """
        Save netscaler config
        """

        path = "/nitro/v1/config/"

        payload = {'params': {"action": "save"}, "nsconfig": {}}

        self._call('POST', path, payload,
                   error_message="Couldn't save config")


    def get_object(self, ns_object, *args):
        """
        If we get stat in our optional args list, that means we need to change
        the url to handle fetching stat objects
        """

        if 'stats' in args:
            path = "/nitro/v1/stat/%s" % ('/'.join(ns_object))
        else:
            path = "/nitro/v1/config/%s" % ('/'.join(ns_object))

        data = self._call('GET', path,
                          error_message="Couldn't Get object")

        return data

    def modify_object(self, properties):

        path = "/nitro/v1/config"

        data = self._call('POST', path, properties,
                          error_message="Couldn't Modify object")

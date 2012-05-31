import logging
import json
import httplib2
import urllib
import sys

class Client(object):
    
    def __init__(self,host,user,passwd,debug):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.debug = debug


    def login(self):
        #set the headers and the base URL
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        url = "http://%s/nitro/v1/config/" % (self.host)

        #construct the payload with URL encoding
        payload = {"object":{"login":{"username":self.user,"password":self.passwd}}}
        payload_encoded = urllib.urlencode(payload)

        #create a HTTP object, and use it to submit a POST request
        http = httplib2.Http()
        response, content = http.request(url, 'POST', body=payload_encoded, headers=headers)

        data = json.loads(content)
        errorcode = data["errorcode"]

        if response.status != 200 or errorcode != 0:
            raise RuntimeError(content)

        if self.debug:
            #for debug purposes, print out the headers and the content of the response
            print "Nitro API URL: ", url
            print "\n", json.dumps(response, sort_keys=False, indent=4)
            print "\n", json.dumps(content, sort_keys=False, indent=4)

        data = json.loads(content)
        self.sessionID = data["sessionid"]
    
        return True


    def logout(self):
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Cookie': 'sessionid='+self.sessionID}
        url = "http://%s/nitro/v1/config/" % (self.host)

        #construct the payload with URL encoding
        payload = {"object":""}
        payload_encoded = urllib.urlencode(payload)

        #create a HTTP object, and use it to submit a POST request
        http = httplib2.Http()
        response, content = http.request(url, 'POST', body=payload_encoded, headers=headers)

        if content != "(null)":
            data = json.loads(content)
            msg = "\nCouldn't logout: %s" % (data["message"])
            raise RuntimeError(msg)

        return True


    def getObject(self,object):
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Cookie': 'sessionid='+self.sessionID}
        url = "http://%s/nitro/v1/config/%s" % (self.host,'/'.join(object))

        #create a HTTP object, and use it to submit a GET request
        http = httplib2.Http()
        response, content = http.request(url, 'GET', headers=headers)

        data = json.loads(content)
        errorcode = data["errorcode"]

        if response.status != 200 or errorcode != 0:
            raise RuntimeError(content)

        return data


    def saveConfig(client):
        command = "savensconfig"

        try:
            output = runCmd(client,command)
        except RuntimeError, e:
            raise RuntimeError(e)

        return True

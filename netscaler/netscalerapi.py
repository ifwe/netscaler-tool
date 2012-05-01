import logging
import json
import httplib2
import urllib
import sys

class Client(object):

    def __init__(self,host,user,passwd):
        self.host = host
        self.user = user
        self.passwd = passwd


    def login(self,self.host,self.user,self.passwd):
        #set the headers and the base URL
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        url = "http://%s/nitro/v1/config/" % (host)

        #contruct the payload with URL encoding
        payload = {"object":{"login":{"username":user,"password":passwd}}}
        payload_encoded = urllib.urlencode(payload)

        #create a HTTP object, and use it to submit a POST request
        http = httplib2.Http()
        response, content = http.request(url, 'POST', body=payload_encoded, headers=headers)

        if debug:
            #for debug purposes, print out the headers and the content of the response
            print json.dumps(response, sort_keys=False, indent=4)
            print json.dumps(content, sort_keys=False, indent=4)

        data = json.loads(content)
        sessionID = data["sessionid"]

        # Returning sessionID
        return sessionID
        

    def logout(client):
        output = client.service.logout() 
        if output.rc != 0 and output.rc != 1041:
            raise RuntimeError(output.message)
        else:
            return output.message


    def getObject(self.host, sessionID, object):

        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Cookie': 'sessionid='+sessionID}
        url = "http://%s/nitro/v1/config/%s" % (host, object)

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

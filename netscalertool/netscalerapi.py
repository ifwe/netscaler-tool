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
    def __init__(self,host,user,passwd,debug):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.debug = debug

        #if self.debug:
        #    httplib2.debuglevel=4


    def login(self):
        # set the headers and the base URL
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        url = "https://%s/nitro/v1/config/" % (self.host)

        # construct the payload with URL encoding
        payload = {"object":{"login":{"username":self.user,"password":self.passwd}}}
        payloadEncoded = urllib.urlencode(payload)

        # create a HTTP object, and use it to submit a POST request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        try:
            response, content = http.request(url, 'POST', body=payloadEncoded, headers=headers)
        except socket.error, e: 
            msg = "Problem connecting to netscaler %s:\n%s" % (self.host,e)
            raise RuntimeError(msg)

        data = json.loads(content)
        errorcode = data["errorcode"]

        if response.status != 200 or errorcode != 0:
            raise RuntimeError(content)

        if self.debug:
            # for debug purposes, print out the headers and the content of the response
            print "Nitro API URL: ", url
            print "\n", json.dumps(response, sort_keys=False, indent=4)
            print "\n", json.dumps(content, sort_keys=False, indent=4)

        data = json.loads(content)
        self.sessionID = data["sessionid"]
    
        return True


    def logout(self):
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Cookie': 'sessionid='+self.sessionID}
        url = "https://%s/nitro/v1/config/" % (self.host)

        # construct the payload with URL encoding
        payload = {"object":{"logout":{}}}
        payloadEncoded = urllib.urlencode(payload)

        # create a HTTP object, and use it to submit a POST request
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        response, content = http.request(url, 'POST', body=payloadEncoded, headers=headers)

        # getting the errorcode to see if theere was a problem 
        error = json.loads(content)['errorcode']

        if error != 0:
            data = json.loads(content)
            msg = "\nCouldn't logout: %s" % (data["message"])
            raise RuntimeError(msg)

        return True


    def getObject(self,object,*args):
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Cookie': 'sessionid='+self.sessionID}

        # if we get stat in our optional args list, that means we need to change
        # the url to handle fetching stat objects
        if 'stats' in args:
            url = "https://%s/nitro/v1/stat/%s" % (self.host,'/'.join(object))
        else:
            url = "https://%s/nitro/v1/config/%s" % (self.host,'/'.join(object))

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


    def saveConfig(client):
        command = "savensconfig"

        try:
            output = runCmd(client,command)
        except RuntimeError, e:
            raise

        return True

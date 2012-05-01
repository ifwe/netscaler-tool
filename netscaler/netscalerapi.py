import logging
import json
import httplib2
import urllib
import sys

# Register suds.client as a console handler... and disable it.
# This is necessary because sometimes suds.client can be chatty
# with warnings and it confuses end-users.
logging.basicConfig(level=logging.ERROR)
logging.getLogger('suds.client').setLevel(logging.ERROR)
logging.disable(logging.ERROR)

class Client(object):

    def fetchPasswd(passwdFile):
        try:
            f = open(passwdFile,'r')
        except IOError, e:
            raise IOError(e)

        # Reading contents of passwd file.
        passwd = f.readline().strip('\n')

        # Closing file handle
        f.close()

        # Returning passwd
        return passwd


    def login(host,user,passwd,debug):
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


    def getObject(host, sessionID, object):

        listOfVservers = []

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


    def setObject(host, sessionID, object, value):
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Cookie.sessionid': sessionID}
        pass


    def getAllServices(client):
        command = "getservice"
        list = []

        try:
            output = runCmd(client,command)
        except RuntimeError, e:
            raise RuntimeError(e)

        for entry in output:
            list.append(entry.name)

        list.sort()
        return list


    def getAllVservers(client):
        command = "getlbvserver"
        list = []

        try:
            output = runCmd(client,command)
        except RuntimeError, e:
            raise RuntimeError(e)

        for entry in output:
            list.append(entry.name)

        list.sort()
        return list


    def getServicesBound(client,vserver):
        command = "getlbvserver"
        arg = {'name':vserver}

        try:
            output = runCmd(client,command,**arg)
        except RuntimeError, e:
            raise RuntimeError(e)

        try:
            return output[0].servicename
        except AttributeError:
            e = "Vserver %s doesn't have any service bound to it. You can probably delete it." % (vserver)
            raise RuntimeError(e)


    def getStatServices(client,service):
        command = "statservice"
        arg = {'name':service}

        try:
            output = runCmd(client,command,**arg)
        except RuntimeError, e:
            raise RuntimeError(e)

        return output[0].surgecount


    def getSurgeQueueSize(client,vserver):
        wsdl = "NSStat.wsdl"
        wsdlURL = "http://%s/api/%s" % (host,wsdl)
        surgeCountTotal = 0

        try:
            services = getServicesBound(client,vserver)
        except RuntimeError, e:
            raise RuntimeError(e)

        # Since we got the services bound to the vserver in question, we now
        # need to get surge queue count for each service, but that requires we
        # change wsdl files.
        try:
            client = getConnected(host,user,passwd)
        except RuntimeError, e:
            raise RuntimeError(e)

        # Going through the list of services to get surge count.
        for service in services:
            if debug:
                print "Fetching surge queue count for %s" % (service)

            try:
                output = getStatServices(client,service)
            except RuntimeError, e:
                raise RuntimeError(e)

            if debug:
                print "Surge count for %s: %s\n" % (service,output)

            surgeCountTotal =+ int(output)

        return surgeCountTotal


    def getVserver(client, vserver):
        command = "getlbvserver"
        arg = {'name':vserver}

        try:
            output = runCmd(client,command,**arg)
        except RuntimeError, e:
            raise RuntimeError(e)


    def saveConfig(client):
        command = "savensconfig"

        try:
            output = runCmd(client,command)
        except RuntimeError, e:
            raise RuntimeError(e)

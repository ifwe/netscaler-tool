import logging
from suds.client import Client, WebFault
from suds.xsd.doctor import Import, ImportDoctor

# Register suds.client as a console handler... and disable it.
# This is necessary because sometimes suds.client can be chatty
# with warnings and it confuses end-users.
logging.basicConfig(level=logging.ERROR)
logging.getLogger('suds.client').setLevel(logging.ERROR)
logging.disable(logging.ERROR)

def fetchPasswd(passwdFile):
    try:
        f = open(passwdFile,'r')
    except IOError, e:
        return 1, e

    # Reading contents of passwd file.
    passwd = f.readline().strip('\n')

    # Closing file handle
    f.close()

    # Returning passwd
    return 0, passwd


def connection(host,wsdl):

    wsdlUrl = "http://%s/api/%s" % (host,wsdl)
    soapUrl = "http://%s/soap" % (host)

    # fix missing types with ImportDoctor, otherwise we get:
    # suds.TypeNotFound: Type not found: '(Array, # http://schemas.xmlsoap.org/soap/encoding/, )
    _import = Import('http://schemas.xmlsoap.org/soap/encoding/')
    _import.filter.add("urn:NSConfig")
    doctor = ImportDoctor(_import)

    try:
        client = Client(wsdlUrl, doctor=doctor, location=soapUrl, cache=None)
    except: 
        return 1 

    return client
    

def login(client, user, passwd):
    output = client.service.login(username=user, password=passwd)
    if output.rc != 0:
        return 1, output.message
    else:
        return 0, output.message


def logout(client):

    output = client.service.logout() 
    if output.rc != 0:
        return 1, output.message
    else:
        return 0, output.message


def runCmd(client, command, **args):
    output = getattr(client.service, command)(**args)
    if output.rc != 0:
        return 1, output.message
    else:
        return 0, output.List


def autoSave(client):
    pass

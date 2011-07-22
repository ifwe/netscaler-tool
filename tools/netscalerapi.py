import logging
from suds.client import Client, WebFault
from suds.xsd.doctor import Import, ImportDoctor

# Register suds.client as a console handler... and disable it.
# This is necessary because sometimes suds.client can be chatty
# with warnings and it confuses end-users.
logging.basicConfig(level=logging.ERROR)
logging.getLogger('suds.client').setLevel(logging.ERROR)
logging.disable(logging.ERROR)

# Debug is off by default
debug = False

# New of WSDL file
#wsdl = 'NSConfig.wsdl'

# Role user for running commands on nescaler. Password
# will be fetched from file that lives locally on box.
username = '***REMOVED***'
passwdFile = 'passwd.txt'

# Keeps track if the user is logged in or not.
loggedIn = False


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


def client(netscaler,wsdl):

    global loggedIn

    wsdlUrl = "http://%s/api/%s" % (host,wsdl)
    soapUrl = "http://%s/soap" % (host)

    # fix missing types with ImportDoctor, otherwise we get:
    # suds.TypeNotFound: Type not found: '(Array, # http://schemas.xmlsoap.org/soap/encoding/, )
    _import = Import('http://schemas.xmlsoap.org/soap/encoding/')
    _import.filter.add("urn:NSConfig")
    doctor = ImportDoctor(self._import)

    client = Client(wsdlUrl, doctor=doctor, location=soapUrl, **kwargs)
    loggedIn = False

    return client
    

def login(username, passwd,client):
    output = client.service.login(username=username, password=passwd)
    if output.rc != 0:
        return 1, output.message
    else:
        return 0


def logout(client):
    global loggedIn

    if not loggedIn:
        if debug:
            print "No need to logout since you are not logged in" 
    else:
        output = client.service.logout() 
        if output.rc != 0:
            return 1, output.message
        else:
            return 0


def runCmd():
    pass

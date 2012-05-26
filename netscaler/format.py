def printList(list):
    for entry in list:
        print entry

    return 0

def printDict(dict):
    for key in sorted(dict.keys()):
        print "%s: %s" % (key,dict[key])
    
    #for entry in dict.sort():
    #    print "%s: %s" % (entry,dict[entry])

    return 0

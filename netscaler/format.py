def printList(list):
    for entry in list:
        print entry

    return 0

def printDict(dict,*args):
    if args:
        for key in sorted(args[0]):
            print "%s: %s" % (key,dict[key])
    else:
        for key in sorted(dict.keys()):
            print "%s: %s" % (key,dict[key])
        
    return 0

def printList(list):
    for entry in list:
        print entry

    return 0

def printDict(dict,*args):
    if args:
        # Print specific keys
        for key in sorted(args[0]):
            try:
                print "%s: %s" % (key,dict[key])
            except KeyError:
                e = "%s is not a valid attribute." % (key)
                raise KeyError(e)
    else:
        # Print everything
        for key in sorted(dict.keys()):
            print "%s: %s" % (key,dict[key])
        
    return 0

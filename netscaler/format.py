def printList(list):
    for entry in list:
        print entry

    return 0

def printDict(dict,*args):
    # Testing to see if any attrs were passed
    # in and if so only print those key/values.
    if args[0]:
        # Print specific keys
        for key in sorted(args[0]):
            try:
                print "%s: %s" % (key,dict[key])
            except KeyError:
                e = "%s is not a valid attribute." % (key)
                raise KeyError(e)

    # Print everything
    else:
        # Print everything
        for key in sorted(dict.keys()):
            print "%s: %s" % (key,dict[key])
        
    return 0

import sys

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


def print_list(list):
    """
    Used for printing a list
    """
    for entry in list:
        print entry

    return 0


def print_items_json(dict, *args):
    """
    Used for printing certain items of a dictionary in json form
    """

    new_dict = {}
    # Testing to see if any attrs were passed in and if so only print those
    # key/values
    try:
        for key in args[0]:
            try:
                new_dict[key] = dict[key]
            except KeyError, e:
                msg = "%s is not a valid attr" % (e,)
                raise KeyError(msg)
    except KeyError:
        raise

    print json.dumps(new_dict)

    return 0

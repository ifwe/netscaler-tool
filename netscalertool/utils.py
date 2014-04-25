def print_list(list):
    """
    Used for printing a list
    """
    for entry in list:
        print entry

    return 0


def print_items_json(dict, *args):
    """
    Used for printing certain items of a dictionary in json
    """

    new_dict = {}
    # Testing to see if any attrs were passed
    # in and if so only print those key/values.
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

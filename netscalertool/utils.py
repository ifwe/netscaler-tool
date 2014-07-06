"""
Copyright 2014 Tagged Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json


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

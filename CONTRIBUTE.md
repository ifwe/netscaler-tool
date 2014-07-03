# Contribute

## Team members
* Brian Glogower: System Engineer at Tagged Inc.

## Coding Style
* PEP8
* No camelCase, except for classes
* Indents are 4 whitespaces

## Adding/Changing features
* Please send your changes as a pull request

### Add a new top level argument, i.e. show
1. Creating a new parser off of the main subparser
    * ```
    parserShow = subparser.add_parser(
        'show', help='sub-command for showing objects'
    )
    ```

### Add a new second level argument, i.e. lb-vservers
1. Create a new subparser off of parent subparser
    * `subparserShow = parserShow.add_subparsers(dest='subparserName')`
1. Create parser

        subparserShow.add_parser('lb-vservers', help='Shows all lb vservers')

    * If the subparser will need an argument
        -  
        ```parserShowLbVserver.add_argument(
            'vserver', help='Shows stats for specified vserver'
        )```

1. Create new method under respective class

        def lbvservers(self):
            object = ["lbvserver"]
            listOfLbVservers = []

            try:
                output = self.client.get_object(object)
            except RuntimeError as e:
                msg = "Problem while trying to get list of LB vservers " \
                      "on %s.\n%s" % (self.args.host, e)
                raise RuntimeError(msg)

            for vserver in output['lbvserver']:
                listOfLbVservers.append(vserver['name'])

            utils.print_list(sorted(listOfLbVservers))

## Todo
* Fix all camelCase instances
* Write unit tests using pytest

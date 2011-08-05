#!/usr/bin/env python

from distutils.core import setup, find_packages

setup(name='netscaler-tools',
    version='1.0',
    packages = find_packages(),

    author = "Brian Glogower",
    author_email = "bglogower@tagged.com",
    description = "Repository of python functions for retrieving and modifying NetScaler settings."     
    license = "WTFPL",

    entry_points = {
        'console_scripts': [
            'netscaler-tool = netscaler.netscaler-tool:main',
            ]
        },
)

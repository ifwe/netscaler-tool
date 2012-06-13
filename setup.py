#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='netscaler-tool',
    version='1.0',
    packages = find_packages(),

    author = "Brian Glogower",
    author_email = "bglogower@tagged.com",
    description = "Nitro API tool for managing NetScalers.",
    license = "WTFPL",
    install_requires=[
        "httplib2",
        "argparse",
    ],

    entry_points = {
        'console_scripts': [
            'netscaler-tool = netscalertool.netscalertool:main',
            ]
    },
)

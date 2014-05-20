#!/usr/bin/env python

from setuptools import setup, find_packages
import sys

PYTHON_REQ_BLACKLIST = []

if sys.version_info >= (2, 7) or sys.version_info >= (3, 2):
    PYTHON_REQ_BLACKLIST.extend(['argparse', 'ordereddict'])

if sys.version_info >= (2, 6) or sys.version_info >= (3, 1):
    PYTHON_REQ_BLACKLIST.append('simplejson')

def load_requirements(fname):
    requirements = []

    #TODO: use pkg_resources to grab the file (in case we're inside an archive)
    with open(fname, 'r') as reqfile:
        reqs = reqfile.read()

    for req in filter(None, reqs.strip().splitlines()):
        if any(req.startswith(bl) for bl in PYTHON_REQ_BLACKLIST):
            continue
        requirements.append(req)

    return requirements

REQUIREMENTS = load_requirements('requirements.txt')

setup(
    name='netscaler-tool',
    version='1.17',
    packages = find_packages(),

    author = "Brian Glogower",
    author_email = "bglogower@tagged.com",
    description = "Nitro API tool for managing NetScalers.",
    license = "Apache v2.0",
    install_requires=REQUIREMENTS,
    entry_points = {
        'console_scripts': [
            'netscaler-tool = netscalertool.netscalertool:main',
            ]
    },
)

#!/usr/bin/env python

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
import sys

from setuptools import setup, find_packages

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
    version='1.25.1',
    packages=find_packages(),

    author="Brian Glogower",
    author_email="bglogower@tagged.com",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: System :: Networking :: Monitoring',
        'Topic :: System :: Operating System',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    description="Nitro API tool for managing NetScalers.",
    entry_points={
        'console_scripts': [
            'netscaler-tool = netscalertool.netscalertool:main',
        ]
    },
    install_requires=REQUIREMENTS,
    keywords=[
        'API',
        'Automation',
        'library',
        'Nitro',
        'Networking',
        'NetScaler',
    ],
    license="Apache v2.0",
    url="https://github.com/tagged/netscaler-tool",
)

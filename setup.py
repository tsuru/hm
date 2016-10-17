# -*- coding: utf-8 -*-

# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
import codecs

from setuptools import setup, find_packages

from hm import __version__

README = codecs.open('README.rst', encoding='utf-8').read()

setup(
    name="tsuru-hm",
    url="https://github.com/tsuru/hm",
    version=__version__,
    description="Host manager library for tsuru PaaS services",
    long_description=README,
    author="Tsuru",
    author_email="tsuru@corp.globo.com",
    classifiers=[
        "Programming Language :: Python :: 2.7",
    ],
    packages=find_packages(exclude=["docs", "tests"]),
    include_package_data=True,
    install_requires=[
        "boto==2.25.0",
        "pymongo==3.3.0",
        "requests==2.4.3",
        "GloboNetworkAPI==0.2.2",
    ],
    extras_require={
        'tests': [
            "mock==1.0.1",
            "flake8==2.1.0",
            "coverage==3.7.1",
            "freezegun==0.2.8",
        ]
    },
)

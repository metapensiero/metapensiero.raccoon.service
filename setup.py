# -*- coding: utf-8 -*-
# :Project:   metapensiero.raccoon.service -- Service classes for Rocky
# :Created:   gio 24 mar 2016, 19.20.15, CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

import os

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.rst'), encoding='utf-8') as f:
    CHANGES = f.read()
with open(os.path.join(here, 'version.txt'), encoding='utf-8') as f:
    VERSION = f.read().strip()


setup(
    name="metapensiero.raccoon.service",
    version=VERSION,
    url="https://gitlab.com/metapensiero/metapensiero.raccoon.service",

    description="Service classes for Raccoon",
    long_description=README + '\n\n' + CHANGES,

    author="Alberto Berti",
    author_email="alberto@metapensiero.it",

    license="GPLv3+",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        ],
    keywords='',
    packages=['metapensiero.raccoon.' + pkg
              for pkg in find_packages('src/metapensiero/raccoon')],
    package_dir={'': 'src'},
    namespace_packages=['metapensiero', 'metapensiero.raccoon'],

    install_requires=[
        'setuptools',
        'autobahn>=0.13',
        'arstecnica.raccoon.autobahn',
        'metapensiero.raccoon.node',
        'metapensiero.signal>=0.9',
        'metapensiero.reactive',
    ],
    extras_require={
        'dev': [
            'metapensiero.tool.bump_version',
            'docutils'
        ],
        'test': [
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'crossbar>=0.13',
            'metapensiero.raccoon.node[test]',
        ]
    },
    setup_requires=['pytest-runner'],
    tests_require=[
        'metapensiero.raccoon.service[test]'
    ],
)

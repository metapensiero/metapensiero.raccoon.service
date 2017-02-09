# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- Service classes for Rocky
# :Created:   gio 24 mar 2016, 19.20.15, CET
# :Author:    Alberto Berti <alberto@arstecnica.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
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
    name="raccoon.rocky.service",
    version=VERSION,
    url="https://gitlab.com/arstecnica/raccoon.rocky.service",

    description="Service classes for Rocky",
    long_description=README + '\n\n' + CHANGES,

    author="Alberto Berti",
    author_email="alberto@arstecnica.it",

    license="GPLv3+",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        ],
    keywords='',

    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['raccoon', 'raccoon.rocky'],

    install_requires=[
        'setuptools',
        'autobahn>=0.13',
        'arstecnica.raccoon.autobahn',
        'raccoon.rocky.node',
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
            'crossbar>=0.13',
            'raccoon.rocky.node[test]',
        ]
    },
    setup_requires=['pytest-runner'],
    tests_require=[
        'raccoon.rocky.service[test]'
    ],
)

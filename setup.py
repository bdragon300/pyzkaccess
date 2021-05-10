#!/usr/bin/env python

from distutils.core import setup

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='pyzkaccess',
    description='Library and command-line utility '
                'for working with ZKTeco ZKAccess C3-100/200/400 controllers',
    version='0.2',
    author='Igor Derkach',
    author_email='gosha753951@gmail.com',
    url='https://github.com/bdragon300/pyzkaccess',
    license='Apache 2.0',
    python_requires='>=3.5',
    packages=setuptools.find_packages(exclude=['tests', 'docs']),
    long_description=long_description,
    long_description_content_type='text/markdown',
    entry_points={"console_scripts": ["pyzkaccess=pyzkaccess.cli:main"]},
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: Microsoft :: Windows',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Intended Audience :: Telecommunications Industry',
        'Intended Audience :: Customer Service',
        'Topic :: System :: Hardware'
    ],
    # Also tox.ini
    install_requires=[
        'wrapt',
        'fire',
        'prettytable'
    ],
)

#!/usr/bin/env python

from setuptools import setup
import os
from os.path import dirname
import ast
import re

here = os.path.abspath(os.path.dirname(__file__))
os.chdir(here)

_version_re = re.compile(r'__version__\s*=\s*(.*)')
with open(os.path.join(here, 'txdir.py'), 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

with open(os.path.join(here, 'README.rst'), 'rt') as f:
    long_description = f.read()

setup(
    name="txdir",
    version=version,
    description="Creating file tree from text tree and vice versa",
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license="MIT",
    author="Roland Puntaier",
    author_email="roland.puntaier@gmail.com",
    url="https://github.com/rpuntaie/txdir",
    py_modules=["txdir"],
    data_files=[("man/man1", ["txdir.1"])],
    install_requires=['pathspec'],
    python_requires='>=3.6',
    keywords='text tree directory file content template',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: End Users/Desktop',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Desktop Environment :: File Managers',
        'Topic :: System :: Filesystems',
        'Topic :: Utilities',
    ],
    entry_points="""
       [console_scripts]
       txdir=txdir:main
       """
)

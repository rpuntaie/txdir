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
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Topic :: Utilities",
    ],
    entry_points="""
       [console_scripts]
       txdir=txdir:main
       """
)

=================================
txdir(1) Version 1.1.1 \| txdir
=================================

NAME
====

**txdir** — text tree from or to file tree

SYNOPSIS
========

**txdir** [<infile>\|<indir>\|-] [<outdir>\|-] [<options>]


Options::

    -h: help
    -v: version
    -l: flat listing
    -f: exclude files
    -d: include dot files/directories
    -n: exclude file content (don't reapply such a tree as it will empty all files)
    -m: maximum depth
    -c: commands to create directories (from https://github.com/gcmt/mktree)

Files/dirs are ignored via .gitignore.

Command line help::

    usage: txdir [infile] [outdir] [-h] [-v] [-l] [-f] [-d] [-n] [-m M] [-c [C [C ...]]]

    Files/dirs are ignored via .gitignore. If the directory contains unignored
    binary files, exclude files with '-f'. Ignoring content with '-n', then
    reapplying will empty all files. NOTE: EMPTY FILES IN TEXT TREE WILL EMPTY
    ACCORDING FILES IN THE FILE TREE.
    
    positional arguments:
      infile          If a file, it is expected to contain a text tree, flat or
                      indented (none or - is stdin). If a directory, the text tree
                      is created from the file tree (like the Linux tree tool).
      outdir          None or - means printing the tree to stdout. If the
                      parameter is an existing file, nothing is done. If not a
                      directory, the directory is created. The file tree is
                      created in the directory.
    
    optional arguments:
      -h              Print help information.
      -v              Print version information.
      -l              Create a flat listing instead of an indented text tree from
                      file tree.
      -a              Use ASCII instead of unicode when printing the indented text tree.
      -f              Omit files. Just directories, when creating a text tree from
                      a file tree.
      -d              Include dot files/directories when creating a text tree from
                      a file tree.
      -n              Omit file content when creating a text tree from a file
                      tree.
      -m M            Maximum depth to scan when creating a text tree from a file
                      tree.
      -c [C [C ...]]  Directories described with a DSL (',' = end of token, '.' =
                      up dir, '/' = down) `txdir - . -c 'a/b/d.c/d..a/u,v,x,g\.x'`
                      produces the same as `mkdir -p a/{b,c}/d a/u a/v a/x a/g.x`
                      If not within ', use \\ to escape.

DESCRIPTION
===========

- Construct a *file tree* from a text tree.
- Construct a *text tree* from a file tree.

This allows to edit a whole file tree within one file first,
without the necessity to switch files.

The text tree can also be templated
and first run through a tool like `stpl <https://github.com/rpuntaie/stpl>`__
before being processed by ``txdir`` to produce the final file tree.
This usage is like `cookiecutter <https://github.com/cookiecutter/cookiecutter>`__,
only that it has the tree definition in one file.

INSTALLATION
============

To install for user only, do::

   pip install --user txdir

COMMAND USAGE
=============

Without arguments it expects input from ``stdin``::

    txdir

Exit this via ``CTRL+C``.
Use no input argument only in combination with piping, or when using `-c`.

Use on a directory tree where

- binary text files are only in dotted directories (e.g. .git) or
- binary files are ignored via ``.gitignore``

::

    txdir .

produces text output to ``stdout``, similar to ``tree``, but with content,
unless content is suppressed with ``-n``.

You can save the output in a file and edit it::

    txdir -l . > tmp.txt

The ``-l`` option makes the output flat.
You can drop the ``-l``, if you want ``tmp.txt`` contain an indented tree.

NO directory is created, unless a root is provided as second argument::

    txdir tmp.txt .

This applies to the (edited) text tree in ``tmp.txt`` on the current directory.

::

    txdir . again

produces the same tree below ``again``, almost like a ``cp -R . again``.
But internally a text tree of the file tree is created and then applied to the new location.

``txdir`` **does not work for binary files**. If there are binary files, use ``-f`` to exclude files.
Ignoring content with ``-n``, then reapplying, will empty all files.

NOTE: EMPTY FILES IN TEXT TREE WILL EMPTY ACCORDING FILES IN THE FILE TREE.

Note, also, that **text file content must not have an empty first line**.

EXAMPLES
--------

::

   cd ~/tmp
   txdir -c r/a/x,y,z
      └─ r/
         └─ a/
            ├─ x/
            ├─ y/
            └─ z/
   txdir - . -c r/a/x,y,z
   cd r
   tree
      .
      └── a
          ├── x
          ├── y
          └── z
   txdir .
      └─ a/
         ├─ x/
         ├─ y/
         └─ z/
   txdir . > tmp.txt
   #edit tmp.txt
   cat tmp.txt
      ├─ a/
      │  ├─ x/
            ├─ x.txt
                 This is content in x.txt
      │  ├─ y/
            ├─ y.txt
                 This is content in y.txt
   txdir tmp.txt .
   txdir .
      ├─ a/
      │  ├─ x/
      │  │  └─ x.txt
      │  │        This is content in x.txt
      │  ├─ y/
      │  │  └─ y.txt
      │  │        This is content in y.txt
      │  └─ z/
      └─ tmp.txt
            ├─ a/
            │  ├─ x/
                  ├─ x.txt
                       This is content in x.txt
            │  ├─ y/
                  ├─ y.txt
                       This is content in y.txt
   #Note, that what is below tmp.txt is content of tmp.txt, not actual directories.
   #`txdir . | txdir - .` does not create the same tree below ``tmp.txt``,
   #because tmp.txt exists as file and not as directory.
   txdir a b
   txdir . > tmp.txt
   #edit tmp.txt adding {{txt}} and removing the tmp.txt line (else tmp.txt is emptied when applying)
   cat tmp.txt
      ├─ a/
      │  ├─ x/
      │  │  └─ x.txt
      │  │        {{txt}} x.txt
      │  ├─ y/
      │  │  └─ y.txt
      │  │        {{txt}} y.txt
      │  └─ z/
      ├─ b/
      │  ├─ x/
      │  │  └─ x.txt
      │  │        {{txt}} x.txt
      │  ├─ y/
      │  │  └─ y.txt
      │  │        {{txt}} y.txt
      │  └─ z/
   stpl tmp.txt - 'txt="Greeting from"' | txdir - .
   rm tmp.txt
   txdir . -l
      a/x/x.txt
         Greeting from x.txt
      a/y/y.txt
         Greeting from y.txt
      a/z/
      b/x/x.txt
         Greeting from x.txt
      b/y/y.txt
         Greeting from y.txt
      b/z/
   txdir . -l | sed -e "s/ \(.\)\.txt/ \1/g" | txdir - .
   txdir . -l
      a/x/x.txt
         Greeting from x
      a/y/y.txt
         Greeting from y
      a/z/
      b/x/x.txt
         Greeting from x
      b/y/y.txt
         Greeting from y
      b/z/

API USAGE
=========

``txtdir`` is a python module.

Naming:

- ``view`` refers to a text tree view
- ``flat`` is a flat tree listing.
- ``tree`` is the actual file tree

Functions:

- ``set_ascii``, ``set_utf8``
- ``view_to_tree``
- ``tree_to_view``
- ``flat_to_tree``
- ``tree_to_flat``
- ``to_tree`` decides whether ``flat_to_tree`` or ``view_to_tree`` should be used
- ``main`` makes the command line functionality accessible to python

Class:

``TxDir`` can hold a file tree in memory. Its ``content`` represents

- *directory* if *list* of other ``TxDir`` instances
- *link* if *str* with path relative to the location as link target
- *file* if *tuple* of text file lines

``TxDir`` methods::

   __init__(self, name='', parent=None, content=None)
   __iter__(self) #leaves only
   __lt__(self,other) #by name
   __str__(self)
   __repr__(self)
   __call__ = cd
   __truediv__(self, other) #changes and returns root
   root(self)
   path(self)
   mkdir = cd #with content=[]
   cd(self,apath,content=None) #cd or make node if content!=None
   isfile(self)
   isdir(self)
   islink(self)
   view(self)
   flat(self)
   create(self)


static::

    fromcmds(descs)
    fromview(viewstr)
    fromflat(flatstr)
    fromfs(root)

EXAMPLES
--------

::

   >>> import os
   >>> from os.path import expanduser
   >>> from shutil import rmtree
   >>> import sys
   >>> from txdir import *

   >>> os.chdir(expanduser('~/tmp'))

   >>> t = t.fromcmds(['r/a'])
   >>> TxDir('x.txt',t('r/a'),('Text in x',))
   >>> t.view()
   └─ r/
      └─ a/
         └─ x.txt
               Text in x
   >>> t.flat()
   r/a/x.txt
      Text in x

   >>> rmtree('r',ignore_errors=True)
   >>> t.create()

   >>> t = TxDir.fromfs('r')
   >>> t.view()
   └─ a/
      └─ x.txt
            Text in x

   >>> rmtree('r',ignore_errors=True)
   >>> r = TxDir.fromcmds(['r'])
   >>> r = r('r')/t('a') #root is returned
   >>> t('a') == r('r/a') #r and t are roots
   True
   >>> r.flat()
   r/a/x.txt
      Text in x


License
-------

MIT


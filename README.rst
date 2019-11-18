=================================
txdir(1) Version 1.0.0 \| txdir
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
    -n: exclude file content
    -m: maximum depth
    -c: commands to create directories (from https://github.com/gcmt/mktree)

Command line help::

    usage: txdir [infile] [outdir] [-h] [-v] [-l] [-f] [-d] [-w] [-m M] [-c [C [C ...]]]

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
      -f              Omit files. Just directories, when creating a text tree from
                      a file tree.
      -d              Include dot files/directories when creating a text tree from
                      a file tree.
      -n              Omit file content when creating a text tree from a file
                      tree.
      -m M            Maximum depth to scan when creating a text tree from a file
                      tree.
      -c [C [C ...]]  Directories described with a DSL (',' = end of token, '.' =
                      up dir, '/' = down) `txdir - . -c a/b,c/d..a/u,v/g.x,g\.x`
                      produces the same as `mkdir -p a/{b,c}/d a/{u,v} a/x a/g.x`

DESCRIPTION
===========

- Construct a *file tree* from a text tree.
- Construct a *text tree* from a file tree.

This allows to edit a whole file tree within one file first,
without the necessity to switch files.

The text tree can also be templated
and first run through a tool like `stpl <https://github.com/rpuntaie/stpl>`__
before being processed by M to produce the final file tree.

To install for user only, do::

   pip install --user txdir

USAGE
=====

Without arguments it expects input from ``stdin``::

    txdir

Used on a directory tree,
where non-text files are only in dotted directories (e.g. .git)::

    txdir .

it produces one text output to ``stdout``, similar to ``tree``, but with content (unless with ``-n``).

You can save the output in a file and edit it::

    txdir -l . > thisdir.txt

The ``-l`` option make the output flat to distinguish what is content and what is tree.
Don't worry, you can drop the ``-l``, 
as ``txdir . | txdir - .`` does not create the same tree below ``thisdir.txt``,
because ``thisdir.txt`` exists as file already.

No directory is created unless a root directory is provided::

    txdir . again

This produces the same tree below ``again``, almost like a ``cp -R``.
But internally a text tree of the file tree is created and then applied to the new location.

**It does not work for binary files**. If there are binary files, use ``-f`` to exclude files.
Note, also, **the text files must not have an empty first line**.

After editing the file you can apply it on the tree again::

    txdir thisdir.txt .

License
-------

MIT


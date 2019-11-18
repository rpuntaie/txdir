#!/usr/bin/env python

import sys
import os
import re
import argparse
import codecs
from functools import partial
import contextlib
from threading import RLock
from urllib import request
from tempfile import NamedTemporaryFile

__version__ = "1.0.1"

#these can be changed from outside to use e.g. only ASCII
MID = '├'
END = '└'
HOR = '─'
VER = '│'
LNKL = '<-'
LNKR = '->'
DWN = '<<'
prefix_middle_end = [MID+HOR+' ',END+HOR+' ']
prefix_sub_middle_end = [VER+'  ', '   ']

#OS
cwd = lambda: os.getcwd().replace('\\', '/')
cd = os.chdir
mkdir = partial(os.makedirs, exist_ok=True)
relpath = lambda x, start: os.path.relpath(x, start=start).replace('\\', '/')
dirname = lambda x: os.path.dirname(x).replace('\\', '/')
normjoin = lambda *x: os.path.normpath(os.path.join(*x)).replace("\\", "/")
basename = os.path.basename
exists = os.path.exists
isfile = os.path.isfile
isdir = os.path.isdir
islink = os.path.islink
listdir = os.listdir
readlink = os.readlink
symlink = os.symlink

#helpers
_cdlock = RLock()
@contextlib.contextmanager
def with_cwd(apth,cwd=cwd,cd=cd):
    _cdlock.acquire()
    prev_cwd = cwd()
    cd(apth)
    try:
        yield
    finally:
        cd(prev_cwd)
        _cdlock.release()
def filecontent(pd):
    with open(pd, encoding='utf-8') as f:
        yield from f.readlines()
def filewrite(efile,cntlns):
    dexists = dirname(efile)
    if dexists and not exists(dexists):
        mkdir(dexists)
    with open(efile, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(cntlns)
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
@contextlib.contextmanager
def temp():
  try:
    f = NamedTemporaryFile(delete=False)
    tmp_name = f.name
    f.close()
    yield tmp_name
  finally:
    os.unlink(tmp_name)
def urlretrieve(url,tofile,filewrite=filewrite,filecontent=filecontent,eprint=eprint):
    with temp() as f:
        try:
            request.urlretrieve(url, f)
            filewrite(tofile,filecontent(f))
        except Exception as err:
            eprint("Error retrieving "+url+" to "+tofile+':', err)

#functions
MAXDEPTH = 30
def tree_to_view(rootpath = None
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,maxdepth=MAXDEPTH
         #uses
         ,isdir = isdir
         ,normjoin=normjoin
         ,islink=islink
         ,listdir=listdir
         ,filecontent=filecontent
         ,readlink=readlink
         ,name=lambda x:x
         ):
    """
    Returns a generator for a tree view as produced by the linux tree tool,
    but optionally with content of files

    :param rootpath: path of which to create the tree string
    :param with_dot: also include files starting with .
    :param with_files: else only directories are listed
    :param with_content: use this only if all the files are text
    :param maxdepth: max directory depth to list

    :return: generator for the lines

    """
    if rootpath is None:
        rootpath = cwd()
    rootdir = rootpath
    lenprefix = len(prefix_middle_end[0])
    def _tree(p, prefix):
        ds = listdir(p)
        lends = len(ds)
        if len(prefix)//lenprefix >= maxdepth:
            return
        for i, d in enumerate(sorted(ds)):
            dn = name(d)
            if not with_dot and dn.startswith('.'):
                continue
            padding = prefix + prefix_middle_end[i==lends-1]
            pd = normjoin(p, d)
            if islink(pd):
                yield padding + dn + ' ' + LNKR + ' ' + readlink(pd)
            elif isdir(pd):
                yield padding + dn + '/'
                yield from _tree(pd, prefix + prefix_sub_middle_end[i==lends-1])
            elif with_files:
                yield padding + dn
                if with_content:
                    for ln in filecontent(pd):
                        yield prefix + 2*prefix_sub_middle_end[1] + ln.rstrip()
    return _tree(rootdir, '')

def rindices(regex, lns):
    regex = re.compile(regex)
    for i, ln in enumerate(lns):
        if regex.search(ln):
            yield i
def intervals(nms):
    return list(zip(nms[:], nms[1:]))
_re_pth_plus = re.compile(r'^(\w[^ </\\]*)(\s*'+DWN+r'\s*|\s*[\\/]\s*|\s*'+LNKR+r'\s*)*([\w\.].*)*')
_re_lnk_pth_plus = re.compile(r'^(/?\w[^ </\\]*)(\s*'+DWN+r'\s*|\s*[\\/]\s*|\s*'+LNKR+r'\s*)*([\w\.].*)*') #for symlink
_re_skip = re.compile(r'[^\s'+MID+VER+END+HOR+']')
_re_skip_middle = re.compile(r'[^\s'+VER+']')
_re_to_file = re.compile(r'['+MID+END+']')
_re_space = re.compile(r'[^ ]')
def view_to_tree(view_str_list
         ,fullpthroot=None
         #uses
         ,cwd=cwd
         ,mkdir=mkdir
         ,symlink=symlink
         ,withcwd=with_cwd
         ,filewrite=filewrite
         ,eprint=eprint
         ):
    """
    Build a directory tree from a string list as returned by view_to_tree().
    The level is determined by the identation.

    - Ending in ``/``: make a directory leaf

    - Starting with ``/``: make a symlink to the file (``/path/relative/to/root``).
      Append ``<- othername`` if link has another name.

    - ``<<`` to copy file from internet using ``http://`` or locally using ``file:///``

    - Not starting with ├└ are file content.
      The first line must not be empty.

    :param view_str_list: tree as list of lines
    :param fullpthroot: internal use


    Example::

        >>> view_str_list='''
        ...       tmpt
        ...       └─ a
        ...          ├/b/e/f.txt
        ...          ├aa.txt
        ...            this is aa
        ...          └k.txt<<http://docutils.sourceforge.net/docs/user/rst/quickstart.txt
        ...          b
        ...          ├c
        ...          │└d/
        ...          ├k
        ...          │└/b/e
        ...          ├e
        ...          │└f.txt
        ...          └g.txt
        ...            this is g'''.splitlines()
        >>> view_to_tree(view_str_list)
        >>> view_str_list='''
        ...     tmpt
        ...     ├── a
        ...     │   ├── aa.txt
        ...     │   ├── f.txt -> ../../b/e/f.txt
        ...     │   └── k.txt
        ...     └── b
        ...         ├── c
        ...         │   └── d/
        ...         ├── e
        ...         │   └── f.txt
        ...         ├── g.txt
        ...         └── k
        ...             └── e -> ../../../b/e'''.splitlines()
        >>> view_to_tree(view_str_list)
        >>> import shutil
        >>> shutil.rmtree('tmpt')

    """

    pwd = cwd()
    if not fullpthroot:
        fullpthroot = pwd
    for treestart, t in enumerate(view_str_list):
        try:
            ct = _re_skip.search(t).span()[0]
            break
        except:
            continue
    sublst = [t[ct:].rstrip() for t in view_str_list[treestart:]]
    isublst = list(rindices(_re_lnk_pth_plus, sublst))
    isublst.append(len(sublst))
    for strt, last in intervals(isublst):
        file_entry = sublst[strt]
        try:
            efile, delim, url = _re_pth_plus.match(file_entry).groups()
        except: #/symlink/rel/to/root <- name
            lnk = fullpthroot+file_entry
            lndst = basename(lnk)
            try:
                _,lndst = lndst.split(LNKL)
                lnk,_ = lnk.split(LNKL)
            except: pass
            lnk = relpath(lnk.strip(),pwd)
            try:
                symlink(lnk,lndst.strip())
            except: pass
            continue
        if efile:
            if strt < last - 1:
                nxtline = sublst[strt + 1]
                try:
                    ix = _re_to_file.search(nxtline).span()[0]
                    # file name starter found
                    mkdir(efile)
                    with withcwd(efile):
                        view_str_list = sublst[strt + 1:last]
                        view_to_tree(view_str_list,fullpthroot
                                     ,cwd=cwd
                                     ,mkdir=mkdir
                                     ,symlink=symlink
                                     ,withcwd=withcwd
                                     ,filewrite=filewrite
                                     ,eprint=eprint
                                     )
                except:# .. else file content
                    cntent = sublst[strt + 1:last]
                    ct = 0
                    try:
                        ct = _re_skip_middle.search(cntent[0]).span()[0]
                    except:
                        eprint(strt, last, '\n'.join(cntent[:10]))
                        eprint("FIRST LINE OF FILE CONTENT MUST NOT BE EMPTY!")
                    cntlns = [t[ct:] + '\n' for t in cntent]
                    filewrite(efile,cntlns)
            elif delim:
                if '\\' in delim or '/' in delim:
                    mkdir(efile)
                elif LNKR in delim and url and efile: #name -> ../rel/to/here
                    try:
                        symlink(url,efile)
                    except: pass
                elif DWN in delim:
                    urlretrieve(url, efile,filewrite=filewrite,eprint=eprint)
            else:
                filewrite(efile,'')

def tree_to_flat(rootpath = None
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,maxdepth=MAXDEPTH
         #uses
         ,isdir = isdir
         ,normjoin=normjoin
         ,islink=islink
         ,listdir=listdir
         ,filecontent=filecontent
         ,readlink=readlink
         ,name=lambda x:x
         ):
    """
    Returns a generator for a flat tree listing,
    optionally with content of files

    :param rootpath: path of which to create the tree string
    :param with_dot: also include files starting with .
    :param with_files: else only directories are listed
    :param with_content: use this only if all the files are text
    :param maxdepth: max directory depth to list

    :return: generator for the lines

    """

    if rootpath is None:
        rootpath = cwd()
    rootdir = rootpath
    def _tree(p, prefix):
        ds = listdir(p)
        if len(prefix) >= maxdepth:
            return
        for i, d in enumerate(sorted(ds)):
            dn = name(d)
            if not with_dot and dn.startswith('.'):
                continue
            pd = normjoin(p, d)
            nprefix = prefix+[dn]
            thispth = '/'.join(nprefix)
            if islink(pd):
                yield thispth + ' ' + LNKR + ' ' + readlink(pd)
            elif isdir(pd):
                entries = list(_tree(pd, nprefix))
                if entries:
                    yield from entries
                else:
                    yield thispth + '/'
            elif with_files:
                yield thispth
                if with_content:
                    for ln in filecontent(pd):
                        tmpln = ln.rstrip()
                        if tmpln:
                            yield prefix_sub_middle_end[1] + tmpln
                        else:
                            yield ''
    return _tree(rootdir,[])

def flat_to_tree(flat_str_list
         #uses
         ,mkdir=mkdir
         ,symlink=symlink
         ,filewrite=filewrite
         ,eprint=eprint
         ):
    """
    Build a directory tree from a list of strings as returned by tree_to_flat().

    - Ending in ``/``: make a directory leaf

    - Starting with ``/``: make a symlink to the file (``/path/relative/to/root``).
      Append ``<- othername`` if link has another name.

    - ``<<`` to copy file from internet using ``http://`` or locally using ``file:///``

    - Indented lines are file content.
      The first line must not be empty.

    :param flat_str_list: list of lines

    Example::

        >>> flat_str_list='''
        ... tmpt/a/f.txt -> ../b/e/f.txt
        ... tmpt/a/aa.txt
        ...     this is aa
        ...
        ...     end of file
        ... tmpt/b/c/d/
        ... tmpt/b/k/e -> ../e
        ... tmpt/b/e/f.txt
        ... tmpt/b/g.txt
        ...     this is g'''.splitlines()
        >>> flat_to_tree(flat_str_list)
        >>> import shutil
        >>> shutil.rmtree('tmpt')

    """

    i,e = 0,None
    leni = len(flat_str_list)
    while i<leni:
        e = flat_str_list[i].rstrip()
        i = i+1
        if not e:
            continue
        esplit = e.split(LNKR)
        usplit = e.split(DWN)
        if len(esplit) == 2: #islink
            fnm = esplit[0].strip()
            tgt = esplit[1].strip()
            if tgt.startswith('/'):
                tgt = '../'*(len(fnm.split('/'))-1)+tgt[1:]
            dfnm = dirname(fnm)
            if dfnm: mkdir(dfnm)
            try:
                symlink(tgt,fnm)
            except: pass
        elif len(usplit) == 2:
            urlretrieve(usplit[1], usplit[0], filewrite=filewrite,eprint=eprint)
        elif e.endswith('/'):
            mkdir(e)
        else:
            de = dirname(e)
            if de: mkdir(de)
            indent,fllns = 0,[]
            try:
                j = i
                while j<leni:
                    x = flat_str_list[j]
                    if not x or x.startswith(' '):
                        fllns.append(x)
                    else:
                        break
                    j = j+1
                ln0 = fllns[0]
                indent = _re_space.search(ln0).span()[0]
                i = j
            except: pass
            filewrite(e,[x[indent:]+'\n' for x in fllns])

def to_tree(view_or_flat):
    """Check whether a flat text tree or an indented one,
    then create the file tree accordingly"""
    treeidx = list(rindices(_re_to_file, view_or_flat))
    if treeidx:
        view_to_tree(view_or_flat)
    else:
        flat_to_tree(view_or_flat)

#classes
class DirTree:
    def __init__(self, name, parent=None, content=None):
        self.name = name
        self.parent = parent
        if self.parent:
            self.parent.content.append(self)
        self.content = [] if content is None else content

    def __iter__(self):
        """Iterate over leaves, i.e. omitting inner nodes"""
        if self.isdir() and self.content:
            for child in self.content:
                yield from child
        else:
            yield self

    def __lt__(self,other):
        return self.name<other.name

    def __str__(self):
        return f"<{self.__class__.__name__} {self.path()}>"

    def __repr__(self):
        return f"{self.__class__.__name__}(path={self.path()!r})"

    def path(self):
        ntry = [self]
        while ntry[-1].parent:
            ntry.append(ntry[-1].parent)
        pth = '/'.join(x.name for x in reversed(ntry) if x.name)
        return pth

    def mkdir(self,apath,content=None):
        return self.cd(apath,[] if content is None else content)

    def cd(self,apath,content=None):#content != None == make
        c = self
        try:
            apath = [x for x in apath.split('/') if x]
        except:
            pass
        maxi = len(apath)-1
        for i,an in enumerate(apath):
            if c.isdir():
                try:
                    c = next(x for x in c.content if x.name==an)
                    continue
                except:
                    if an == '.': 
                        continue
                    elif an == '..':
                        c = c.parent
                        continue
            if content is None:
                raise FileNotFoundError(f"{an} in {c.path()} while cd to {apath}")
            else:
                c = DirTree(an,c,[] if i<maxi else content)
        return c

    def isfile(self):
        return isinstance(self.content,tuple)

    def isdir(self):
        return isinstance(self.content,list)

    def islink(self):
        return isinstance(self.content,str)

    @staticmethod
    def fromcmds(descs):
        """Creates a DirTree from a list of command strings:

        , = end of token without extra meaning
        . = end of token and up dir ('..' is to times up)
        / = end of token and down the last token

        Args:
            descs (list): A list of command strings

        Returns:
            A DirTree instance.

        """

        def tokenize(string):
            token = ""
            escape = ""
            for i, char in enumerate(string):
                if i == len(string) - 1:
                    yield token + char
                elif char in (".", ",", "/"):
                    if escape:
                        token += char
                        escape = ""
                    else:
                        yield token
                        yield char
                        token = ""
                        escape = ""
                elif char == "\\" and not escape:
                    escape += char
                else:
                    token += char
                    escape = ""

        root = DirTree("")
        for desc in descs:
            current = root
            for token in tokenize(desc):
                if not token or token == ",":
                    continue
                elif token == "/":
                    if current.isdir() and current.content:
                        current = current.content[-1]
                elif token == ".":
                    if current.parent:
                        current = current.parent
                else:
                    node = DirTree(token, parent=current)
        return root

    @staticmethod
    def fromview(viewstr,eprint=eprint):
        """Builds the directory tree from a tree view.

        viewstr:
            A string from the output of DirTree.view().

        """

        root = DirTree("")
        current = root
        def _cwd():
            return current
        def _cd(apath):
            nonlocal current
            if isinstance(apath,str):
                current = next(x for x in current.content if x.name==apath)
            else:
                current = apath
        view_str_list = viewstr.splitlines()
        view_to_tree(view_str_list
                     ,cwd=lambda:'/'+current.path()
                     ,mkdir=lambda apath: current.mkdir(apath)
                     ,symlink=lambda lnk,apath: current.mkdir(apath,lnk)
                     ,withcwd=lambda x: with_cwd(x,_cwd,_cd)
                     ,filewrite=lambda apath,c: current.mkdir(apath,tuple(c))
                     ,eprint=eprint
                     )
        return root

    @staticmethod
    def fromflat(flatstr,eprint=eprint):
        """Builds the directory tree from a tree flat listing.

        flatstr:
            A string from the output of DirTree.flat().

        """

        root = DirTree("")
        flat_str_list = flatstr.splitlines()
        flat_to_tree(flat_str_list
                     ,mkdir=lambda apath: root.mkdir(apath)
                     ,symlink=lambda lnk,apath: root.mkdir(apath,lnk)
                     ,filewrite=lambda apath,c: root.mkdir(apath,tuple(c))
                     ,eprint=eprint
                     )
        return root

    @staticmethod
    def fromfs(root
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,maxdepth=MAXDEPTH
         ):
        v = '\n'.join(tree_to_view(root
             ,with_dot=with_dot
             ,with_files=with_files
             ,with_content=with_content
             ,maxdepth=maxdepth
             ))
        return DirTree.fromview(v)

    def view(self, print=print
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,maxdepth=MAXDEPTH
         ):
        """print tree view with indentation"""
        print('\n'.join(tree_to_view(self
             ,with_dot=with_dot
             ,with_files=with_files
             ,with_content=with_content
             ,maxdepth=maxdepth
             ,isdir=lambda x: x.isdir()
             ,normjoin=lambda *x: x[-1]
             ,islink=lambda x: x.islink()
             ,listdir=lambda x: x.content
             ,filecontent=lambda x: x.content
             ,readlink=lambda x: x.content
             ,name=lambda x: x.name
             )))

    def flat(self, pint=print):
        """print flat tree listing"""
        for e in self:
            print(e.path(),end="")
            if e.islink():
                print(' '+LNKR+' '+e.content)
            elif e.isdir():
                print('/')
            else:
                print()
            if e.isfile():
                for x in e.content:
                    if x.strip():
                        print(prefix_sub_middle_end[1]+x,end="")
                    else:
                        print(x,end="")

    def create(self):
        """create tree in file system"""
        lastdir = None
        for e in self:
            if e.islink():
                mkdir(dirname(e.path()))
                try:
                    symlink(e.content,e.path())
                except: pass
            elif e.isdir():
                lastdir = e.path()
                mkdir(lastdir)
            else:
                mkdir(dirname(e.path()))
                filewrite(e.path(),e.content)
        return lastdir


def main(print=print,**args):
    """Command line functionality."""
    if args:
        for x in 'vlfdn':
            args.setdefault(x,False)
        args.setdefault('m',MAXDEPTH)
        args.setdefault('c',[])
        args.setdefault('infile','-')
        args.setdefault('outdir','-')
        args=argparse.Namespace(**args)
    else:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("-h", action="help", help="Print help information.")
        parser.add_argument(
            "-v",
            action="version",
            version=f"%(prog)s {__version__}",
            help="Print version information.",
        )
        parser.add_argument(
            "-l",
            action="store_true",
            help="Create a flat listing instead of an indented text tree from file tree.",
        )
        parser.add_argument(
            "-f",
            action="store_true",
            help="Omit files. Just directories, when creating a text tree from a file tree.",
        )
        parser.add_argument(
            "-d",
            action="store_true",
            help="Include dot files/directories when creating a text tree from a file tree.",
        )
        parser.add_argument(
            "-n",
            action="store_true",
            help="Omit file content when creating a text tree from a file tree.",
        )
        parser.add_argument(
            "-m",
            action="store",
            default=MAXDEPTH,
            type=int,
            help="Maximum depth to scan when creating a text tree from a file tree.",
        )
        parser.add_argument(
            "-c",
            nargs="*",
            default="",
            help="""Directories described with a DSL
            (',' = end of token,
            '.' = up dir,
            '/' = down)
            `txdir - . -c a/b,c/d..a/u,v/g.x,g\.x` produces the same as
            `mkdir -p a/{b,c}/d a/{u,v} a/x a/g.x`

            """
        )
        parser.add_argument(
            'infile',
            nargs='?',
            default='-',
            help="""If a file, it is expected to contain a text tree, flat or indented (none or - is stdin).
            If a directory, the text tree is created from the file tree (like the Linux tree tool)."""
        )
        parser.add_argument(
            'outdir',
            nargs='?',
            default='-',
            help="""None or - means printing the tree to stdout.
            If the parameter is an existing file, nothing is done.
            If not a directory, the directory is created.
            The file tree is created in the directory."""
        )
        args = parser.parse_args()

    infile       = args.infile
    outdir       = args.outdir
    with_dot     = args.d
    with_files   = not args.f
    with_content = not args.n
    maxdepth     = args.m
    trees        = args.c

    dirtree = None
    if trees:
        dirtree = DirTree.fromcmds(trees)

    fview = []
    inf = isfile(infile)
    if not inf and infile == '-':
        if not trees:
            sys.stdin = codecs.getreader("utf-8")(sys.stdin.detach())
            fview = [x.rstrip() for x in sys.stdin.readlines()]
    elif inf:
        with open(infile,'r',encoding='utf-8') as f:
            fview = [x.rstrip() for x in f.readlines()]
    elif isdir(infile):
        if args.l:
            fview = list(tree_to_flat(infile
                        ,with_dot=with_dot
                        ,with_files=with_files
                        ,with_content=with_content
                        ,maxdepth=maxdepth
                                      ))
        else:
            fview = list(tree_to_view(infile
                             ,with_dot=with_dot
                             ,with_files=with_files
                             ,with_content=with_content
                             ,maxdepth=maxdepth
                                  ))

    outf = isfile(outdir)
    if not outf:
        if outdir == '-':
            if dirtree: dirtree.flat() if args.l else dirtree.view()
            if fview: print('\n'.join(fview))
        else: #dir
            mkdir(outdir)
            with with_cwd(outdir):
                if dirtree: dirtree.create()
                if fview: to_tree(fview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


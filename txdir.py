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
from base64 import b64encode, b64decode
import pathspec

#also in README.rst
__version__ = "2.0.1"

#see test_txdir.py to see how to change
MID = '├'
END = '└'
HOR = '─'
VER = '│'
LNKL = '<-'
LNKR = '->'
DWN = '<<'
MID_END = ['├─ ','└─ ']
SUB_MID_END = ['│  ', '   ']

def set_tree_chars(
         mid = '├'
        ,end = '└'
        ,hor = '─'
        ,ver = '│'
        ,lnkl = '<-'
        ,lnkr = '->'
        ,dwn = '<<'
        ,mid_end = ['├─ ','└─ ']
        ,sub_mid_end = ['│  ', '   ']
): # pragma: no cover
    global MID
    global END
    global HOR
    global VER
    global LNKL
    global LNKR
    global DWN
    global MID_END
    global SUB_MID_END
    MID         = mid
    END         = end
    HOR         = hor
    VER         = ver
    LNKL        = lnkl
    LNKR        = lnkr
    DWN         = dwn
    MID_END     = mid_end
    SUB_MID_END = sub_mid_end

def set_ascii():
    set_tree_chars(
         mid = r"`"
         ,end = "`"
         ,hor = "-"
         ,ver = r"|"
         ,mid_end =     ['`- ', '`- ']
         ,sub_mid_end = ['|  ', '   ']
    )

def set_utf8():
    set_tree_chars()


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
def filecontent(pd,with_binary=False):
    try:
        with open(pd, encoding='utf-8') as f:
            return f.readlines()
    except UnicodeDecodeError:
        if with_binary:
            with open(pd, 'rb') as f:
                return f.read()
def filewrite(efile,cntlns):
    dr = dirname(efile)
    if dr and not exists(dr):
        mkdir(dr)
    if isinstance(cntlns,bytes):
        with open(efile, 'wb') as f:
            f.write(cntlns)
    else:
        with open(efile, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(cntlns)
def fileyield(pd,tpad
             ,with_binary=False
             ,filecontent=filecontent
              ):
    fcontent = filecontent(pd,with_binary=with_binary)
    if fcontent is None:
        return
    if isinstance(fcontent,bytes):
        yield tpad + repr(b64encode(fcontent)) #encloded in b''
    else:
        for ln in fcontent:
            tmpln = ln.rstrip()
            if tmpln:
                yield tpad + tmpln
            else:
                yield ''
def fileput(efile,cntlns,filewrite=filewrite):
    if len(cntlns)==1 and cntlns[0].startswith("b'") and cntlns[0].rstrip().endswith("'"): # enclosed in b''
        #cntlns = [repr(b64encode(b'chk'))] #b'Y2hr'
        cntbytes = b64decode(cntlns[0].rstrip()[2:-1].encode()) #b'chk'
        filewrite(efile,cntbytes)
        return
    filewrite(efile,cntlns)

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
            fco = filecontent(f,with_binary=True)
            if fco:
                filewrite(tofile,fco)
        except Exception as err:
            eprint("Error retrieving "+url+" to "+tofile+':', err)
def up_dir(match
           ,start
           ,listdir=listdir
           ,up=dirname
           ):
    """
    Find a parent path producing a match on one of its entries.
    Without match an empty string is returned.

    :param match: a function returning a bool on a directory entry
    :param start: absolute path or None
    :return: directory with a match on one of its entries

    >>> up_dir(lambda x: False,start=cwd())
    ''

    """

    if any(match(x) for x in listdir(start)):
        return start
    parent = up(start)
    if start == parent:
        try:
            rootres = start.replace('\\','/').strip('/').strip(':')
            if len(rootres)==1 and 'win' in sys.platform: # pragma: no cover
                rootres = ''
            return rootres
        except:
            return None
    if not parent:
        return parent
    return up_dir(match,start=parent,listdir=listdir,up=up)
class GitIgnore:
    def __init__(self
                 ,start
                 ,listdir=listdir
                 ,up=dirname
                 ,normjoin=normjoin
                 ,filecontent=filecontent
                 ,name=lambda x:x
                 ):
        self.spec = None
        gidir = up_dir(lambda x:name(x)=='.gitignore',start=start,listdir=listdir,up=up)
        self.name = name
        if gidir:
            self.spec = pathspec.PathSpec.from_lines('gitwildmatch',filecontent(normjoin(gidir,'.gitignore')))
    def __call__(self,file):
        return self.spec and self.spec.match_file(self.name(file))

#functions
MAXDEPTH = 30
def tree_to_view(rootpath = None
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,with_binary=False
         ,maxdepth=MAXDEPTH
         #uses
         ,isdir = isdir
         ,normjoin=normjoin
         ,islink=islink
         ,listdir=listdir
         ,filecontent=filecontent
         ,readlink=readlink
         ,name=lambda x:x
         ,up=dirname
         ):
    """
    Returns a generator for an indented text view of a directory,
    with content of files.

    :param rootpath: path of which to create the text view
    :param with_dot: also include files starting with .
    :param with_files: else only directories are listed
    :param with_content: use this only if all the files are text
    :param with_binary: include binary files
    :param maxdepth: max directory depth to list

    :return: generator for the lines

    """
    if rootpath is None:
        rootpath = cwd()
    rootdir = rootpath
    lenprefix = len(MID_END[0])
    gitignore = GitIgnore(start=rootpath,listdir=listdir,up=up,normjoin=normjoin,filecontent=filecontent,name=name)
    def _tree(p, prefix):
        ds = listdir(p)
        lends = len(ds)
        if len(prefix)//lenprefix >= maxdepth:
            return
        for i, d in enumerate(sorted(ds)):
            pd = normjoin(p, d)
            if gitignore(pd):
                continue
            dn = name(d)
            if not with_dot and dn.startswith('.'):
                continue
            padding = prefix + MID_END[i==lends-1]
            if islink(pd):
                try:
                    rlink = readlink(pd)
                except: # pragma: no cover
                    rlink = ''
                yield padding + dn + ' ' + LNKR + ' ' + rlink
            elif isdir(pd):
                yield padding + dn + '/'
                yield from _tree(pd, prefix + SUB_MID_END[i==lends-1])
            elif with_files:
                yield padding + dn
                if with_content:
                    tpad = ' '*len(prefix + 2*SUB_MID_END[1])
                    yield from fileyield(pd,tpad
                                         ,with_binary=with_binary
                                         ,filecontent=filecontent
                                         )
    return _tree(rootdir, '')

def rindices(regex, lns):
    regex = re.compile(regex)
    for i, ln in enumerate(lns):
        if regex.search(ln):
            yield i
def intervals(nms):
    return list(zip(nms[:], nms[1:]))
def _rex():
    dwn = re.escape(DWN)
    lnkr = re.escape(LNKR)
    return argparse.Namespace(
    _re_pth_plus = re.compile(r'^(\w[^ </\\]*)(\s*'+dwn+r'\s*|\s*[\\/]\s*|\s*'+lnkr+r'\s*)*([\w\.].*)*')
    ,_re_lnk_pth_plus = re.compile(r'^(/?\w[^ </\\]*)(\s*'+dwn+r'\s*|\s*[\\/]\s*|\s*'+lnkr+r'\s*)*([\w\.].*)*') #for symlink
    ,_re_skip = re.compile(r'[^\s'+re.escape(MID+VER+END+HOR)+']')
    ,_re_skip_middle = re.compile(r'[^\s'+re.escape(VER)+']')
    ,_re_to_file = re.compile(r'['+re.escape(MID+END)+']')
    ,_re_space = re.compile(r'[^ ]')
    )
def view_to_tree(view_str_list
         ,fullpthroot=None
         #uses
         ,cwd=cwd
         ,mkdir=mkdir
         ,symlink=symlink
         ,withcwd=with_cwd
         ,filewrite=filewrite
         ,eprint=eprint
         ,r=None
         ):
    """
    Build a directory from a indented text view as returned by view_to_tree().
    The level is determined by the identation.

    - Ending in ``/``: make a directory leaf

    - Starting with ``/``: make a symlink to the file (``/path/relative/to/root``).
      Append ``<- othername`` if link has another name.

    - ``<<`` to copy file from internet using ``http://`` or locally using ``file:///``

    - Not starting with ├└ are file content.
      The first line must not be empty.

    :param view_str_list: list of lines
    :param fullpthroot: internal use

    """

    _r = r or _rex()
    pwd = cwd()
    if not fullpthroot:
        fullpthroot = pwd
    for treestart, t in enumerate(view_str_list):
        try:
            ct = _r._re_skip.search(t).span()[0]
            break
        except:
            continue
    sublst = [t[ct:].rstrip() for t in view_str_list[treestart:]]
    isublst = list(rindices(_r._re_lnk_pth_plus, sublst))
    isublst.append(len(sublst))
    for strt, last in intervals(isublst):
        file_entry = sublst[strt]
        try:
            efile, delim, url = _r._re_pth_plus.match(file_entry).groups()
        except: #/symlink/rel/to/root <- name
            lnk = fullpthroot+file_entry
            lndst = basename(lnk)
            try:
                _,lndst = lndst.split(LNKL)
                lnk,_ = lnk.split(LNKL)
            except: pass
            try:
                lnk = relpath(lnk.strip().strip('/'),pwd.strip('/'))
                symlink(lnk,lndst.strip())
            except: pass
            continue
        if efile:
            if strt < last - 1:
                nxtline = sublst[strt + 1]
                try:
                    ix = _r._re_to_file.search(nxtline).span()[0]
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
                        ct = _r._re_skip_middle.search(cntent[0]).span()[0]
                    except:
                        eprint(strt, last, '\n'.join(cntent[:10]))
                        eprint("FIRST LINE OF FILE CONTENT MUST NOT BE EMPTY!")
                    cntlns = [t[ct:] + '\n' for t in cntent]
                    fileput(efile,cntlns,filewrite=filewrite)
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
                if not exists(efile):
                    filewrite(efile,'')

def tree_to_flat(rootpath = None
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,with_binary=False
         ,maxdepth=MAXDEPTH
         #uses
         ,isdir = isdir
         ,normjoin=normjoin
         ,islink=islink
         ,listdir=listdir
         ,filecontent=filecontent
         ,readlink=readlink
         ,name=lambda x:x
         ,up=dirname
         ):
    """
    Returns a generator for a flat text listing of a directory
    with content of files

    :param rootpath: path of which to create the text listing
    :param with_dot: also include files starting with .
    :param with_files: else only directories are listed
    :param with_content: use this only if all the files are text
    :param with_binary: include binary files
    :param maxdepth: max directory depth to list

    :return: generator for the lines

    """

    if rootpath is None:
        rootpath = cwd()
    rootdir = rootpath
    gitignore = GitIgnore(start=rootpath,listdir=listdir,up=up,normjoin=normjoin,filecontent=filecontent,name=name)
    def _tree(p, prefix):
        ds = listdir(p)
        if len(prefix) >= maxdepth:
            return
        for i, d in enumerate(sorted(ds)):
            pd = normjoin(p, d)
            if gitignore(pd):
                continue
            dn = name(d)
            if not with_dot and dn.startswith('.'):
                continue
            nprefix = prefix+[dn]
            thispth = '/'.join(nprefix)
            if islink(pd):
                try:
                    rlink = readlink(pd)
                except: # pragma: no cover
                    rlink = ''
                yield thispth + ' ' + LNKR + ' ' + rlink
            elif isdir(pd):
                entries = list(_tree(pd, nprefix))
                if entries:
                    yield from entries
                else:
                    yield thispth + '/'
            elif with_files:
                yield thispth
                if with_content:
                    yield from fileyield(pd,SUB_MID_END[1]
                                         ,with_binary=with_binary
                                         ,filecontent=filecontent
                                         )
    return _tree(rootdir,[])

def flat_to_tree(flat_str_list
         #uses
         ,mkdir=mkdir
         ,symlink=symlink
         ,filewrite=filewrite
         ,eprint=eprint
         ,r=None
         ):
    """
    Build a directory from a list of strings as returned by tree_to_flat().

    - Ending in ``/``: make a directory leaf

    - Starting with ``/``: make a symlink to the file (``/path/relative/to/root``).
      Append ``<- othername`` if link has another name.

    - ``<<`` to copy file from internet using ``http://`` or locally using ``file:///``

    - Indented lines are file content.
      The first line must not be empty.

    :param flat_str_list: list of lines

    """

    _r = r or _rex()
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
                    else: # pragma: no cover (it is covered, but coverage says not)
                        break
                    j = j+1
                ln0 = fllns[0]
                indent = _r._re_space.search(ln0).span()[0]
                i = j
            except: pass
            flcntlns = [x[indent:]+'\n' for x in fllns]
            if flcntlns or not exists(e):
                fileput(e,flcntlns,filewrite=filewrite)

def to_tree(view_or_flat):
    """Check whether a flat listing or indented view,
    then create the directory accordingly"""
    _r = _rex()
    treeidx = list(rindices(_r._re_to_file, view_or_flat))
    if treeidx:
        view_to_tree(view_or_flat,r=_r)
    else:
        flat_to_tree(view_or_flat,r=_r)

#classes
class TxDir:
    """
    ``TxDir`` can hold a directory in memory. Its ``content`` represents

    - *directory* if *list* of other ``TxDir`` instances
    - *link* if *str* with path relative to the location as link target
    - *file* if *tuple* of text file lines

    """

    def __init__(self, name='', parent=None, content=None):
        self.name = name
        self.parent = parent
        if self.parent is None:
            assert self.name == '', "the root node must not have a name"
        elif self.parent is not None:
            assert self.name != '', "non-root nodes must have a name"
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

    def __call__(self,*args,**kwargs):
        return self.cd(*args,**kwargs)

    def __truediv__(self, other):
       self.content.append(other)
       other.parent = self
       return self.root()

    def root(self):
        r = self
        while r.parent:
            r = r.parent
        return r

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
                c = TxDir(an,c,[] if i<maxi else content)
        return c

    def isfile(self):
        return isinstance(self.content,tuple)

    def isdir(self):
        return isinstance(self.content,list)

    def islink(self):
        return isinstance(self.content,str)

    @staticmethod
    def fromcmds(descs):
        """Creates a TxDir from a list of command strings:

        , = end of token without extra meaning
        . = end of token and up dir ('..' is to times up)
        / = end of token and down the last token

        Args:
            descs (list): A list of command strings

        Returns:
            A TxDir instance.

        """

        def tokenize(string):
            token = ""
            escape = ""
            maxi = len(string) - 1
            for i, char in enumerate(string):
                if i == maxi:
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
                    escape = char
                else:
                    token += char
                    escape = ""

        root = TxDir()
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
                    node = TxDir(token, parent=current)
        return root

    @staticmethod
    def fromview(viewstr,eprint=eprint):
        """Builds the directory from an indented view.

        viewstr:
            A string from the output of TxDir.view().

        """

        root = TxDir()
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
        """Builds the directory from a flat listing.

        flatstr:
            A string from the output of TxDir.flat().

        """

        root = TxDir()
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
         ,with_binary=False
         ,maxdepth=MAXDEPTH
         ):
        v = '\n'.join(tree_to_view(root
             ,with_dot=with_dot
             ,with_files=with_files
             ,with_content=with_content
             ,with_binary=with_binary
             ,maxdepth=maxdepth
             ))
        return TxDir.fromview(v)

    def view(self
         ,with_dot=False
         ,with_files=True
         ,with_content=True
         ,with_binary=False
         ,maxdepth=MAXDEPTH
         ):
        """return an indented text view as string"""
        resv = '\n'.join(tree_to_view(self
            ,with_dot=with_dot
            ,with_files=with_files
            ,with_content=with_content
            ,with_binary=with_binary
            ,maxdepth=maxdepth
            ,isdir=lambda x: x.isdir()
            ,normjoin=lambda *x: x[-2].cd(x[-1]) if isinstance(x[-1],str) else x[-1]
            ,islink=lambda x: x.islink()
            ,listdir=lambda x: x.content
            ,filecontent=lambda x,**k: x.content
            ,readlink=lambda x: x.content
            ,name=lambda x: x.name
            ,up=lambda x: x.parent if x.parent else x
            ))
        return resv

    def flat(self):
        """return flat listing as string"""
        flines = ['']
        def print(v='',end='\n'):
            if flines[-1].endswith('\n'):
                flines.append('')
            flines[-1] = flines[-1]+v+end
        for e in self:
            print(e.path(),end='')
            if e.islink():
                print(' '+LNKR+' '+e.content)
            elif e.isdir():
                print('/')
            else:
                print()
            if e.isfile():
                for x in e.content:
                    if x.strip():
                        print(SUB_MID_END[1]+x,end='')
                    else:
                        print(x,end='')
        return ''.join(flines)

    def tree(self):
        """Create directory in file system"""
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
                fileput(e.path(),e.content)
        return lastdir


def main(print=print,**args):
    """Command line functionality."""
    if args:
        for x in 'vablfdn':
            args.setdefault(x,False)
        args.setdefault('m',MAXDEPTH)
        args.setdefault('c',[])
        args.setdefault('infile','-')
        args.setdefault('outdir','-')
        args=argparse.Namespace(**args)
    else:
        parser = argparse.ArgumentParser(add_help=False,description='''\
        Files/dirs are ignored via .gitignore.
        If the directory contains unignored binary files,
        exclude files with '-f'. Ignore content with '-n'.
        Text file content must not have an empty first line.
        '''
        )
        parser.add_argument("-h", action="help", help="Print help information.")
        parser.add_argument(
            "-v",
            action="version",
            version=f"%(prog)s {__version__}",
            help="Print version information.",
        )
        parser.add_argument(
            "-a",
            action="store_true",
            help="Use ASCII instead of unicode when printing the indented view.",
        )
        parser.add_argument(
            "-b",
            action="store_true",
            help="Include content of binary files as base64 encoded.",
        )
        parser.add_argument(
            "-l",
            action="store_true",
            help="Create a flat listing instead of an indented view.",
        )
        parser.add_argument(
            "-f",
            action="store_true",
            help="Omit files. Only list directories.",
        )
        parser.add_argument(
            "-d",
            action="store_true",
            help="Include dot files/directories.",
        )
        parser.add_argument(
            "-n",
            action="store_true",
            help="Omit file content.",
        )
        parser.add_argument(
            "-m",
            action="store",
            default=MAXDEPTH,
            type=int,
            help="Maximum directory depth to scan.",
        )
        parser.add_argument(
            "-c",
            nargs="*",
            default="",
            help="""Directories described with a DSL
            (',' = end of token,
            '.' = up dir,
            '/' = down)
            `txdir - . -c 'a/b/d.c/d..a/u,v,x,g\\.x'` produces the same as
            `mkdir -p a/{b,c}/d a/u a/v a/x a/g.x`
            If not within ', use \\\\ to escape.

            """
        )
        parser.add_argument(
            'infile',
            nargs='?',
            default='-',
            help="""If a file, it is expected to contain a text representation of a directory, flat or indented (none or - is stdin).
            If a directory, the text view is created with file content (unless -n)."""
        )
        parser.add_argument(
            'outdir',
            nargs='?',
            default='-',
            help="""None or - means printing to stdout.
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
    with_binary  = args.b
    maxdepth     = args.m
    trees        = args.c

    if args.a:
        set_ascii()

    tx = None
    if trees:
        tx = TxDir.fromcmds(trees)

    try:
        sys.stdin = codecs.getreader("utf-8")(sys.stdin.detach())
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getreader("utf-8")(sys.stderr.detach())
    except:
        pass
    fview = []
    inf = isfile(infile)
    if not inf and infile == '-':
        if not trees:
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
                        ,with_binary=with_binary
                        ,maxdepth=maxdepth
                                      ))
        else:
            fview = list(tree_to_view(infile
                             ,with_dot=with_dot
                             ,with_files=with_files
                             ,with_content=with_content
                             ,with_binary=with_binary
                             ,maxdepth=maxdepth
                                  ))
    outf = isfile(outdir)
    if not outf:
        if outdir == '-':
            if tx: print(tx.flat()) if args.l else print(tx.view())
            if fview: print('\n'.join(fview))
        else: #dir
            mkdir(outdir)
            with with_cwd(outdir):
                if tx: tx.tree()
                if fview: to_tree(fview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# vim: ts=4 sw=4 sts=4 et noai nocin nosi inde=

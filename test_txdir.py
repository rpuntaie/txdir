import sys
import os
import io
import importlib.machinery
import shutil
from subprocess import run as sprun, PIPE
import pytest

here = os.path.dirname(__file__)

def run(x,**kwargs):
    if 'win' in sys.platform:
        return sprun(x,shell=True,**kwargs)
    else:
        return sprun(x,shell=False,**kwargs)

module_path = os.path.join(os.path.dirname(__file__), "txdir.py")
txdir = importlib.machinery.SourceFileLoader("txdir", module_path).load_module()
fromview = txdir.DirTree.fromview
fromcmds = txdir.DirTree.fromcmds

def test_tree_parsing():

    def eqpth(a, b):
        assert set(x.path() for x in a) == set(b)

    eqpth(fromcmds(["a/b"]), ["a/b"])
    eqpth(fromcmds(["a/b,c"]), ["a/b", "a/c"])
    eqpth(fromcmds(["a/b,c.d"]), ["a/b", "a/c", "d"])
    eqpth(fromcmds(["a/b/c,d..e/f"]), ["a/b/c", "a/b/d", "e/f"])
    eqpth(fromcmds(["a/b/c,d..e/f.g.h"]), ["a/b/c", "a/b/d", "e/f", "g", "h"])

    eqpth(fromcmds(["a", "b"]), ["a", "b"])
    eqpth(fromcmds(["a/b", "c,d"]), ["a/b", "c", "d"])
    eqpth(fromcmds(["a/b,c", "d/e,f.g"]), ["a/b", "a/c", "d/e", "d/f", "g"])

    eqpth(fromcmds(["a//b,c"]), ["a/b", "a/c"])
    eqpth(fromcmds(["a/b,,c"]), ["a/b", "a/c"])
    eqpth(fromcmds(["a/b,c.."]), ["a/b", "a/c"])
    eqpth(fromcmds(["a/,."]), ["a"])
    eqpth(fromcmds(["/,.a"]), ["a"])

    eqpth(fromcmds([r"foo\,bar"]), ["foo,bar"])
    eqpth(fromcmds([r"foo\\,bar"]), ["foo\\", "bar"])
    eqpth(fromcmds([r"foo\bar,baz"]), [r"foobar", "baz"])
    eqpth(fromcmds([r"foo\\bar,baz"]), [r"foo\bar", "baz"])
    eqpth(fromcmds([r"foo\\\bar,baz"]), [r"foo\bar", "baz"])
    eqpth(fromcmds([r"foo\\\\bar,baz"]), [r"foo\\bar", "baz"])

def test_cmd_help():
    r = run([f'{here}/txdir.py','-h'],stdout=PIPE)
    lns = r.stdout.decode()
    assert r.returncode == 0
    assert '-h' in lns
    assert '-v' in lns
    assert '-l' in lns
    assert '-f' in lns
    assert '-d' in lns
    assert '-n' in lns
    assert '-m' in lns
    assert '-c' in lns

def test_cmd_flatlist():
    r = run([f'{here}/txdir.py','-l','-c','a/b'],stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode()
    assert 'a/b/' == lns.strip()

def test_cmd_treelist():
    r = run([f'{here}/txdir.py','-c','a/b'],stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode()
    assert '└─ b' in lns.strip()

def test_cmd_v():
    r = run([f'{here}/txdir.py','-v','a/b'],stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode()
    assert 'txdir' in lns.strip()

@pytest.yield_fixture
def tmpworkdir(tmpdir):
    """
    Create a temporary working working directory.
    """
    cwd = os.getcwd()
    os.chdir(tmpdir.strpath)
    yield tmpdir
    os.chdir(cwd)

def test_cmd_file1(tmpworkdir):
    r = sprun(f"echo a | {here}/txdir.py - .",shell=True)
    assert r.returncode == 0
    assert os.path.exists('a')
    with pytest.raises(NotADirectoryError):
        shutil.rmtree('a')

def test_cmd_dir1(tmpworkdir):
    r = sprun(f"echo a/ | {here}/txdir.py - .",shell=True)
    assert r.returncode == 0
    assert os.path.exists('a')
    shutil.rmtree('a')

@pytest.yield_fixture
def b_with_a(tmpworkdir):
    r = sprun(f"echo a/ | {here}/txdir.py - b",shell=True)
    assert r.returncode == 0
    assert os.path.exists('b/a')
    assert os.path.isdir('b/a')
    yield r
    shutil.rmtree('b')

def test_cmd_cpdir(b_with_a,capsys):
    r = run([f'{here}/txdir.py','b','c'])
    assert r.returncode == 0
    assert os.path.exists('c/a')
    assert os.path.isdir('c/a')

def test_cmd_cpdir1(b_with_a,capsys):
    r = run([f'{here}/txdir.py','.','c'])
    assert r.returncode == 0
    assert os.path.exists('c/b/a')
    assert os.path.isdir('c/b/a')

def test_cmd_showdir(b_with_a,capsys):
    buf = io.StringIO()
    txdir.main(infile='b',print=lambda *a,**ka: print(*a,file=buf,**ka))
    buf.seek(0)
    out = buf.read()
    assert '└─ a/' in out

def test_cmd_copydir(b_with_a,capsys):
    r=sprun(f"{here}/txdir.py b | {here}/txdir.py - witha",shell=True)
    assert r.returncode == 0
    assert os.path.exists('witha/a')
    assert os.path.isdir('witha/a')
    shutil.rmtree('witha')

def test_cmd_fromfile(b_with_a,capsys):
    txdir.main(infile='b')
    captured = capsys.readouterr()
    with open('b/a/ca.txt','w') as f:
        f.write(captured.out)
    txdir.main(infile='b/a/ca.txt',outdir='witha')
    assert os.path.exists('witha/a')
    assert os.path.isdir('witha/a')
    shutil.rmtree('witha')

def test_from_view(b_with_a):
    v = txdir.tree_to_view()
    assert '└─ a/' in '\n'.join(v)

def test_dirtree_from_view1():
    v='''\
    └─ b/
        └─ a/'''
    dirtree = fromview(v)
    assert dirtree.content[0].content[0].path() == 'b/a'
    assert len(repr(dirtree)) > 0
    assert len(str(dirtree)) > 0
    with pytest.raises(FileNotFoundError):
       dirtree.cd('some/where')

def test_dirtree_from_view2(capsys):
    v=''' tmpt
          └─ a
             ├/mnt/b/e/f.txt
             ├aa.txt
               this is aa
             b
             ├c
             │└d/
             ├k
             │└/mnt/b/e
             ├e
             │└f.txt
             └g.txt
               this is g'''
    dirtree = fromview(v)
    dirtree.flat()
    captured = capsys.readouterr()
    assert captured.out == '''\
tmpt/a/f.txt -> ../../mnt/b/e/f.txt
tmpt/a/aa.txt
   this is aa
tmpt/b/c/d/
tmpt/b/k/e -> ../../../mnt/b/e
tmpt/b/e/f.txt
tmpt/b/g.txt
   this is g
'''

def test_dirtree_from_view3(tmpworkdir,capsys):
    v='''\
└─ tmpt/
   ├─ a/
   │  ├─ aa.txt
   │  ├─ f.txt -> ../../b/e/f.txt
   │  └─ k.txt
   └─ b/
      ├─ c/
      │  └─ d/
      ├─ e/
      │  └─ f.txt
      ├─ g.txt
      └─ k/
         └─ e -> ../../../b/e
'''
    dirtree = fromview(v)
    dirtree.view()
    captured = capsys.readouterr()
    assert captured.out == v
    dirtree.create()
    newv = txdir.tree_to_view('.')
    assert '\n'.join(newv) == v.rstrip()

@pytest.yield_fixture
def tree(tmpworkdir):
    lst = '''\
tmpt/a/aa.txt
    this is aa

tmpt/a/f.txt -> ../b/e/f.txt
tmpt/a/u -> /tmpt/a
tmpt/b/c/d/
tmpt/b/k/e -> /tmpt/a
tmpt/b/e/u/f.txt << http://docutils.sourceforge.net/docs/user/rst/quickstart.txt
tmpt/b/.g.txt
         this is g

'''.splitlines()
    txdir.flat_to_tree(lst)
    txdir.flat_to_tree(lst) #no exists already
    f=txdir.tree_to_flat(maxdepth=3)
    assert '\n'.join(f)=='''\
tmpt/a/aa.txt
   this is aa

tmpt/a/f.txt -> ../b/e/f.txt
tmpt/a/u -> ../../tmpt/a
tmpt/b/c/
tmpt/b/e/
tmpt/b/k/'''

def test_flat1(tree):
    dirtree = txdir.DirTree.fromfs('tmpt')
    quick = dirtree.cd('b/e/u/f.txt')
    assert quick!=None
    assert quick.isfile()
    assert len(quick.content)>100

def test_flat2(tree,capsys):
    txdir.main(infile='.',l=True,m=2)
    captured = capsys.readouterr()
    expected = '''\
tmpt/a/
tmpt/b/
'''
    assert captured.out == expected

def test_nodot_nofile(tree):
    r = run([f'{here}/txdir.py','.','-fn','-m','4'],stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode()
    assert lns == '''\
└─ tmpt/
   ├─ a/
   │  ├─ f.txt -> ../b/e/f.txt
   │  └─ u -> ../../tmpt/a
   └─ b/
      ├─ c/
      │  └─ d/
      ├─ e/
      │  └─ u/
      └─ k/
         └─ e -> ../../../tmpt/a
'''

def test_withcontent(tree):
    r = run([f'{here}/txdir.py','.','-d','-m','4'],stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode()
    assert lns == '''\
└─ tmpt/
   ├─ a/
   │  ├─ aa.txt
   │        this is aa
   │        
   │  ├─ f.txt -> ../b/e/f.txt
   │  └─ u -> ../../tmpt/a
   └─ b/
      ├─ .g.txt
            this is g
            
      ├─ c/
      │  └─ d/
      ├─ e/
      │  └─ u/
      └─ k/
         └─ e -> ../../../tmpt/a
'''
def test_dirflat(tmpworkdir,capsys):
    lst = '''\
tmpt/a/aa.txt
    this is aa

tmpt/a/f.txt -> ../b/e/f.txt
tmpt/b/c/d/
tmpt/b/k/e -> /tmpt/a
tmpt/b/e/f.txt
tmpt/b/g.txt
         this is g

'''
    dirtree = txdir.DirTree.fromflat(lst)
    assert dirtree.cd('tmpt/b/c/d')!=None
    assert dirtree.cd('tmpt/b/c/../c')!=None
    assert dirtree.cd('tmpt/b/c/./d')!=None
    assert dirtree.cd(['tmpt','b'])!=None
    dirtree.flat()
    captured = capsys.readouterr()
    expected = '''\
tmpt/a/aa.txt
   this is aa

tmpt/a/f.txt -> ../b/e/f.txt
tmpt/b/c/d/
tmpt/b/k/e -> ../../../tmpt/a
tmpt/b/e/f.txt
tmpt/b/g.txt
   this is g

'''

    assert captured.out == expected

def test_mkdir(tmpworkdir):
    if 'win' in sys.platform:
        return True
    sprun(f'{here}/txdir.py - . -c a/b,c/d..a/u,v/g.x,g\.x',shell=True)
    t1 = txdir.DirTree.fromfs('a')
    shutil.rmtree('a')
    sprun('mkdir -p a/{b,c}/d a/{u,v} a/x a/g.x',shell=True)
    t2 = txdir.DirTree.fromfs('a')
    shutil.rmtree('a')
    tt1 = t1.view()
    tt2 = t2.view()
    assert tt1 == tt2

def test_err1(tmpworkdir,capsys):
    v='''\
└─ tmpt/
   ├─ a/
   │  ├─ /tmpt/b/c/d <- ln_to_d
   └─ b/
      ├─ e/
      │  └─ f.txt
             
             TEXT

             NEWT
      ├─ c/
      │  └─ d/
      │      └─ u/
      │         └─ v/
      │            └─ x/
'''
    t = fromview(v)
    captured = capsys.readouterr()
    assert 'FIRST LINE OF FILE CONTENT MUST NOT BE EMPTY' in captured.err
    t.create()
    t.create() #no file exists error!
    txdir.view_to_tree(v.splitlines()) #no file exists error!
    assert os.path.exists('tmpt/b/e/f.txt')
    res = '\n'.join(txdir.tree_to_view('.',maxdepth=4))
    txdir.view_to_tree(res.splitlines()) #no file exists error!
    assert res == '''\
└─ tmpt/
   ├─ a/
   │  └─ ln_to_d -> ../b/c/d
   └─ b/
      ├─ c/
      │  └─ d/
      └─ e/
         └─ f.txt
               
                TEXT
               
                NEWT'''


def test_err2(tmpworkdir,capsys):
    v='''\
└─ tmpt/
   ├─ a/
   │  ├─ b << a.b.c
'''.splitlines()
    txdir.view_to_tree(v)
    captured = capsys.readouterr()
    assert captured.err.startswith('Error')
    assert not os.path.exists('tmpt/a/b')


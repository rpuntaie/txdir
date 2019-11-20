import sys
import os
import io
import importlib.machinery
import shutil
from subprocess import run as sprun, PIPE
from base64 import b64encode, b64decode
import pytest

here = os.path.dirname(__file__)

def run(x,**kwargs):
    if 'win' in sys.platform:
        return sprun(x,shell=True,**kwargs)
    else:
        return sprun(x,shell=False,**kwargs)

module_path = os.path.join(os.path.dirname(__file__), "txdir.py")
txdir = importlib.machinery.SourceFileLoader("txdir", module_path).load_module()
fromview = txdir.TxDir.fromview
fromcmds = txdir.TxDir.fromcmds

@pytest.fixture(scope="module",params=[True,False])
def u8(request):
    yes = request.param
    global Z
    global MID
    global END
    global VER
    global HOR
    if yes:
       txdir.set_utf8()
       MID = '├'
       END = '└'
       HOR = '─'
       VER = '│'
       Z = ''
       txcmd = f'{here}/txdir.py'
    else:
       Z = '-a'
       txdir.set_ascii()
       MID = r"`"
       END = "`"
       VER = "|"
       HOR = "-"

if 'win' in sys.platform:
   ##Z = ''
   #Z = '-a'
   #txdir.set_tree_chars(
   #     mid = r"`"
   #     ,end = "`"
   #     ,hor = "-"
   #     ,ver = r"|"
   #     ,mid_end =     ['`- ', '`- ']
   #     ,sub_mid_end = ['|  ', '   ']
   #)
   #MID = r"`"
   #END = "`"
   #VER = "|"
   #HOR = "-"
   txcmd = f'{here}\\txdir.py'
else:
   #Z = ''
   txcmd = f'{here}/txdir.py'

def test_tree_parsing(u8):

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

def test_cmd_help(u8):
    r = run([txcmd,'-h'],stdout=PIPE)
    lns = r.stdout.decode('utf-8')
    assert r.returncode == 0
    assert '-h' in lns
    assert '-v' in lns
    assert '-l' in lns
    assert '-f' in lns
    assert '-d' in lns
    assert '-n' in lns
    assert '-m' in lns
    assert '-c' in lns

def test_cmd_flatlist(u8):
    r = run([txcmd,'-l','-c','a/b']+([Z]if Z else[]),stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode('utf-8')
    assert 'a/b/' == lns.strip()

def test_cmd_treelist(u8):
    r = run([txcmd,'-c','a/b']+([Z]if Z else[]),stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode('utf-8')
    assert '└─ b'.replace('─',HOR).replace('└',END) in lns.strip()

def test_cmd_v(u8):
    r = run([txcmd,'-v','a/b']+([Z]if Z else[]),stdout=PIPE)
    assert r.returncode == 0
    lns = r.stdout.decode('utf-8')
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

def test_cmd_file1(tmpworkdir,u8):
    r = sprun("echo a | "+txcmd+" "+Z+" - .",shell=True)
    assert r.returncode == 0
    assert os.path.exists('a')
    with pytest.raises(NotADirectoryError):
        shutil.rmtree('a')

def test_cmd_dir1(tmpworkdir,u8):
    r = sprun(f"echo a/ | "+txcmd+" "+Z+" - .",shell=True)
    assert r.returncode == 0
    assert os.path.exists('a')
    shutil.rmtree('a')

@pytest.yield_fixture
def b_with_a(tmpworkdir):
    r = sprun(f"echo a/ | "+txcmd+" "+Z+" - b",shell=True)
    assert r.returncode == 0
    assert os.path.exists('b/a')
    assert os.path.isdir('b/a')
    yield r
    shutil.rmtree('b')

def test_cmd_cp1(b_with_a,u8):
    r = run([txcmd,'b','c']+([Z]if Z else[]))
    assert r.returncode == 0
    assert os.path.exists('c/a')
    assert os.path.isdir('c/a')

def test_cmd_cp2(b_with_a,u8):
    r = run([txcmd,'.','c']+([Z]if Z else[]))
    assert r.returncode == 0
    assert os.path.exists('c/b/a')
    assert os.path.isdir('c/b/a')

def test_cmd_showdir(b_with_a,u8):
    buf = io.StringIO()
    txdir.main(infile='b',print=lambda *a,**ka: print(*a,file=buf,**ka))
    buf.seek(0)
    out = buf.read()
    assert '└─ a/'.replace('─',HOR).replace('└',END) in out

def test_cmd_copydir(b_with_a,u8):
    r=sprun(txcmd+" "+Z+" b | "+txcmd+" "+Z+" - witha",shell=True)
    assert r.returncode == 0
    assert os.path.exists('witha/a')
    assert os.path.isdir('witha/a')
    shutil.rmtree('witha')

def test_cmd_fromfile(b_with_a,u8):
    buf = io.StringIO()
    txdir.main(infile='b',print=lambda *a,**ka: print(*a,file=buf,**ka))
    buf.seek(0)
    out = buf.read()
    with open('b/a/ca.txt','w',encoding='utf-8') as f:
        f.write(out)
    txdir.main(infile='b/a/ca.txt',outdir='witha')
    assert os.path.exists('witha/a')
    assert os.path.isdir('witha/a')
    shutil.rmtree('witha')

def test_from_view(b_with_a,u8):
    v = txdir.tree_to_view()
    assert '└─ a/'.replace('─',HOR).replace('└',END) in '\n'.join(v)

def test_dirtree_from_view1(u8):
    v='''\
    └─ b/
        └─ a/'''.replace('─',HOR).replace('└',END)
    d = fromview(v)
    assert d.content[0].content[0].path() == 'b/a'
    assert len(repr(d)) > 0
    assert len(str(d)) > 0
    with pytest.raises(FileNotFoundError):
       d.cd('some/where')

def test_dirtree_from_view2(u8):
    v='''

          tmpt
          └─ a
             ├/tmpt/b/e/f.txt
             ├aa.txt
               this is aa
             b
             ├c
             │└d/
             ├k
             │└/tmpt/b/e
             ├e
             │└f.txt
             └g.txt
               this is g'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER)
    d = fromview(v)
    f = d.flat()
    assert f == '''\
tmpt/a/f.txt -> ../b/e/f.txt
tmpt/a/aa.txt
   this is aa
tmpt/b/c/d/
tmpt/b/k/e -> ../e
tmpt/b/e/f.txt
tmpt/b/g.txt
   this is g
'''

def test_dirtree_from_view3(tmpworkdir,u8):
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
         └─ e -> ../../../b/e'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER)
    d = fromview(v)
    rv = d.view()
    assert rv == v
    d.tree()
    newv = txdir.tree_to_view('.')
    assert '\n'.join(newv) == v.rstrip()

@pytest.yield_fixture
def tree(tmpworkdir):
    lst = '''
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

def test_flat1(tree,u8):
    d = txdir.TxDir.fromfs('tmpt')
    quick = d.cd('b/e/u/f.txt')
    assert quick!=None
    assert quick.isfile()
    assert len(quick.content)>100

def test_flat2(tree,u8):
    r = run([txcmd,'.','-l','-m','2'],stdout=PIPE)
    assert r.returncode == 0
    lns = '\n'.join(r.stdout.decode('utf-8').splitlines())
    assert lns  == '''\
tmpt/a/
tmpt/b/'''

def test_nodot_nofile(tree,u8):
    r = run([txcmd,'.','-fn','-m','4']+([Z]if Z else[]),stdout=PIPE)
    assert r.returncode == 0
    lns = '\n'.join(r.stdout.decode('utf-8').splitlines())
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
         └─ e -> ../../../tmpt/a'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER)

def test_withcontent(tree,u8):
    r = run([txcmd,'.','-d','-m','4']+([Z]if Z else[]),stdout=PIPE)
    assert r.returncode == 0
    lns = '\n'.join(r.stdout.decode('utf-8').splitlines())
    assert lns == '''\
└─ tmpt/
   ├─ a/
   │  ├─ aa.txt
            this is aa

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
         └─ e -> ../../../tmpt/a'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER)
def test_dirflat(tmpworkdir,u8):
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
    d = txdir.TxDir.fromflat(lst)
    assert d.cd('tmpt/b/c/d')!=None
    assert d.cd('tmpt/b/c/../c')!=None
    assert d.cd('tmpt/b/c/./d')!=None
    assert d.cd(['tmpt','b'])!=None
    f = d.flat()
    assert f == '''\
tmpt/a/aa.txt
   this is aa

tmpt/a/f.txt -> ../b/e/f.txt
tmpt/b/c/d/
tmpt/b/k/e -> ../../../tmpt/a
tmpt/b/e/f.txt
tmpt/b/g.txt
   this is g

'''

def test_mkdir(tmpworkdir,u8):
    if 'win' in sys.platform:
        return True
    sprun(txcmd+" "+Z+fr" - . -c 'a/b/d.c/d..a/u,v,x,g\.x'",shell=True)
    t1 = txdir.TxDir.fromfs('a')
    shutil.rmtree('a')
    sprun('mkdir -p a/{b,c}/d a/u a/v a/x a/g.x',shell=True)
    t2 = txdir.TxDir.fromfs('a')
    shutil.rmtree('a')
    tt1 = t1.view()
    tt2 = t2.view()
    assert tt1 == tt2

def test_err1(tmpworkdir,capsys,u8):
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
'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER)
    t = fromview(v)
    captured = capsys.readouterr()
    assert 'FIRST LINE OF FILE CONTENT MUST NOT BE EMPTY' in captured.err
    t.tree()
    t.tree() #no file exists error!
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

                NEWT'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER)


def test_err2(tmpworkdir,capsys,u8):
    v='''\
└─ tmpt/
   ├─ a/
   │  ├─ b << a.b.c
'''.replace('─',HOR).replace('└',END).replace('├',MID).replace('│',VER).splitlines()
    txdir.view_to_tree(v)
    captured = capsys.readouterr()
    assert captured.err.startswith('Error')
    assert not os.path.exists('tmpt/a/b')

def test_nobin(tmpworkdir,u8):
    import random
    with open('tmp','wb') as f:
       f.write(b'\xff') #UnicodeDecodeError
    lns = '\n'.join(txdir.tree_to_view('.'))
    assert lns == "└─ tmp".replace('─',HOR).replace('└',END)

def test_wbin(tmpworkdir,u8):
    import random
    with open('tmp','wb') as f:
       f.write(b'\xff') #UnicodeDecodeError
    lns = '\n'.join(txdir.tree_to_view('.',with_binary=True))
    assert lns == '''\
└─ tmp
      '''.replace('─',HOR).replace('└',END)+repr(b64encode(b'\xff'))
    txdir.view_to_tree(lns.splitlines())
    with open('tmp','rb') as f:
       assert f.read()==b'\xff'

def test_git1(tmpworkdir,u8):
    shutil.copy2(f"{here}/.gitignore",os.path.join(tmpworkdir,'.gitignore'))
    ignoren = 'build'
    os.makedirs(ignoren)
    with open(ignoren+'/x.txt','w') as f:
       f.write('Just a test')
    os.makedirs(ignoren+'X')
    with open(ignoren+'X/x.txt','w') as f:
       f.write('Yet Another Test')
    os.makedirs(ignoren+'Y')
    with open(ignoren+'Y/x.txt','w') as f:
       f.write('Yet Another Test')
    lns = '\n'.join(txdir.tree_to_view('.'))
    assert 'Just a test' not in lns
    assert 'Yet Another Test' in lns
    lns = '\n'.join(txdir.tree_to_flat('.'))
    assert 'Just a test' not in lns
    assert 'Yet Another Test' in lns
    txdir.flat_to_tree(lns.splitlines())

def test_git2(u8):
    d = txdir.TxDir.fromcmds(['a/b','c/d'])
    txdir.TxDir('.gitignore',d,('c',))
    txdir.TxDir('b.txt',d('a/b'),('text in b',))
    txdir.TxDir('b.txt',d('c/d'),('text in d',))
    vab = d('a/b').view()
    vcd = d('c/d').view()
    v = d('.').view()
    assert 'text in b' in vab
    assert 'text in d' in vcd
    assert 'text in d' not in v

def test_nonempty(tmpworkdir,u8):
    lst = '''\
t/a/aa.txt
    this is aa
    this is aa
t/b/bb.txt
    this is bb
    this is bb
'''.splitlines()
    txdir.flat_to_tree(lst)
    assert os.path.exists('t/a/aa.txt')
    assert os.path.exists('t/b/bb.txt')
    ps1 = os.stat('t/a/aa.txt').st_size
    ps2 = os.stat('t/b/bb.txt').st_size
    assert ps1 > 0
    assert ps2 > 0
    v = '\n'.join(txdir.tree_to_view(with_content=False))
    txdir.view_to_tree(v.splitlines())
    assert os.path.exists('t/a/aa.txt')
    assert os.path.exists('t/b/bb.txt')
    assert os.stat('t/a/aa.txt').st_size==ps1
    assert os.stat('t/b/bb.txt').st_size==ps2

def test_ascii(tmpworkdir):
    txdir.set_ascii()
    t = txdir.TxDir.fromcmds(['r/a'])
    txdir.TxDir('x.txt',t('r/a'),('Text in x',))
    assert t.view() == '''\
`- r/
   `- a/
      `- x.txt
            Text in x'''
    assert t.flat() == '''\
r/a/x.txt
   Text in x'''
    shutil.rmtree('r',ignore_errors=True)
    t.tree()
    t = txdir.TxDir.fromfs('r')
    assert t.view() == '''\
`- a/
   `- x.txt
         Text in x'''
    shutil.rmtree('r',ignore_errors=True)
    r = txdir.TxDir.fromcmds(['r'])
    r = r('r')/t('a') #root is returned
    assert t('a') == r('r/a') #r and t are roots
    r.flat() == '''\
r/a/x.txt
   Text in x'''


# vim: ts=4 sw=4 sts=4 et noai nocin nosi inde=

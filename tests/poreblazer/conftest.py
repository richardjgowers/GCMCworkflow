import contextlib
import pytest
import os
import shutil


HERE = os.path.dirname(os.path.abspath(__file__))


@contextlib.contextmanager
def indir(d):
    olddir = os.getcwd()
    os.chdir(d)
    try:
        yield
    finally:
        os.chdir(olddir)


@pytest.fixture(scope='session')
def IRMOF1_case_study(tmpdir_factory):
    newdir = tmpdir_factory.mktemp('ir')
    p = os.path.join(newdir, 'IRMOF1')

    shutil.copytree(os.path.join(HERE, 'IRMOF1'), p)

    with indir(p):
        yield

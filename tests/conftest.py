import contextlib
import fireworks as fw
from fireworks.core.rocket_launcher import rapidfire
import os
import pytest
import shutil

import gcmcworkflow as gcwf

HERE = os.path.dirname(os.path.abspath(__file__))

@contextlib.contextmanager
def indir(d):
    olddir = os.getcwd()
    os.chdir(d)
    try:
        yield
    finally:
        os.chdir(olddir)


@pytest.fixture
def in_temp_dir(tmpdir):
    with indir(tmpdir.strpath):
        yield


@pytest.fixture
def in_working_dir(tmpdir):
    shutil.copytree('workdir', tmpdir.join('workdir').strpath)

    with indir(tmpdir.join('workdir').strpath):
        yield


@pytest.fixture
def sample_input(tmpdir):
    """A working template directory

    has "simple_spec" for creating workflow
    Contains a directory called 'template' holding a Raspa input
    """
    p = tmpdir.join('sample_input').strpath

    shutil.copytree(os.path.join(HERE, 'sample_input'), p)
    with indir(p):
        yield os.path.abspath('.')

@pytest.fixture
def short_raspa(tmpdir):
    p = tmpdir.join('short_raspa').strpath

    shutil.copytree(os.path.join(HERE, 'short_raspa'), p)
    with indir(p):
        yield p


@pytest.fixture
def template_contents():
    # all the files in sample_input/template
    return ('CO2.def', 'force_field.def', 'framework.def',
            'IRMOF-1.cif', 'pseudo_atoms.def', 'simulation.input',
            'run.sh')


@pytest.fixture
def launchpad():
    """Returns a function that runs a Firework or Workflow

    TODO: Make this not require a reset
     - Tag the added Workflow with 'test'
     - Make worker only address 'test' jobs
    """
    lp = fw.LaunchPad(
        #host='ds013216.mlab.com',
        #name='wftests',
        #port=13216,
        #username='test',
        #password='dude',
    )
    lp.reset('', require_password=False)

    def do_launch(wf):
        lp.add_wf(wf)
        return rapidfire(lp, fw.FWorker())

    return do_launch


@pytest.fixture
def failed_raspa(tmpdir):
    # a simulation that didn't start correctly
    target = os.path.join('raspa_sims', 'failed')
    dest = tmpdir.strpath
    shutil.copytree(os.path.join(HERE, target), os.path.join(dest, target))

    with indir(dest):
        yield target


@pytest.fixture
def premature_raspa(tmpdir):
    # a simulation that started but didn't exit correctly
    target = os.path.join('raspa_sims', 'premature')
    dest = tmpdir.strpath
    shutil.copytree(os.path.join(HERE, target), os.path.join(dest, target))

    with indir(dest):
        yield target


@pytest.fixture
def successful_raspa(tmpdir):
    # a simulation that exited correctly
    target = os.path.join('raspa_sims', 'success')
    dest = tmpdir.strpath
    shutil.copytree(os.path.join(HERE, target), os.path.join(dest, target))

    with indir(dest):
        yield target


@pytest.fixture()
def dlm_ts():
    return gcwf.utils.read_csv(os.path.join(HERE,
                                            'timeseries/dlm_ts.csv'))


@pytest.fixture()
def twh_ts():
    return gcwf.utils.read_csv(os.path.join(HERE,
                                            'timeseries/twh_ts.csv'))


@pytest.fixture()
def rsp_ts():
    return gcwf.utils.read_csv(os.path.join(HERE,
                                            'timeseries/rsp_ts.csv'))

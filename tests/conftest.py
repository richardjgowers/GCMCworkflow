import contextlib
import fireworks as fw
from fireworks.core.rocket_launcher import launch_rocket
import os
import pytest
import shutil
import yaml

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
    """Returns a function that runs a Firework or Workflow"""
    if 'LP_FILE' in os.environ:
        lp = fw.LaunchPad.from_file(os.environ['LP_FILE'])
    else:
        lp = fw.LaunchPad()
    lp.reset('', require_password=False)

    def do_launch(thingy):
        """wf - firework or Workflow"""
        id_map = lp.add_wf(thingy)
        # id_map is dict of {old: new ids}
        fw_ids = list(id_map.values())

        num_ran = 0
        # run all fireworks from the Workflow we just added
        while True:
            result = lp.fireworks.find_one(
                {'fw_id': {'$in': fw_ids}, 'state': 'READY'},
                projection={'fw_id': True})
            if result is not None:
                launch_rocket(lp, fw_id=result['fw_id'])
                num_ran += 1
            else:
                break
        if num_ran < len(fw_ids):
            raise ValueError("Added workflow didn't complete")

        lp.reset('', require_password=False)

        return

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

@pytest.fixture()
def late_upswing_ts():
    return gcwf.utils.read_csv(os.path.join(HERE,
                                            'timeseries/late_upswing.csv'))

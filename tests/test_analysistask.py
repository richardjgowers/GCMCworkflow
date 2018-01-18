"""Tests for AnalyseSimulation

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import os
import json
import pytest
import shutil
import gcmcworkflow as gcwf


@xs
class TellTale(fw.FiretaskBase):
    def run_task(self, fw_spec):
        # report what was in the fw_spec
        with open(os.path.join(fw_spec['simtree'], 'fw_spec.json'), 'w') as out:
            json.dump(fw_spec, out)


@pytest.fixture()
def analysis_task(successful_raspa, launchpad):
    # run analysis on a successful raspa simulation
    firework = fw.Firework(
        [gcwf.firetasks.AnalyseSimulation(fmt='raspa', parallel_id=1),
         TellTale()],
        spec={'simtree': os.path.abspath(successful_raspa)},
    )
    launchpad(fw.Workflow([firework]))

    yield successful_raspa


@pytest.fixture()
def analysis_task_with_previous(successful_raspa, launchpad):
    # run analysis on a successful raspa simulation
    firework = fw.Firework(
        [gcwf.firetasks.AnalyseSimulation(
            fmt='raspa', parallel_id=1,
            previous_results='0,123\n673,456\n',
        ),
         TellTale()],
        spec={'simtree': os.path.abspath(successful_raspa)},
    )
    launchpad(fw.Workflow([firework]))

    yield successful_raspa


def test_analysis_creates_file(analysis_task):
    assert os.path.exists(os.path.join(analysis_task, 'this_sim_results.csv'))
    assert os.path.exists(os.path.join(analysis_task, 'total_results.csv'))


def test_results(analysis_task):
    fname = os.path.join(analysis_task, 'fw_spec.json')
    with open(fname, 'r') as inf:
        spec = json.load(inf)

    p_id, results = spec['results'][0]

    assert p_id == 1

    results = results.split()

    assert results[0] == '0,147'
    assert results[1] == '673,130'
    assert results[-2] == '66627,142'
    assert results[-1] == '67300,133'


def test_previous_results(analysis_task_with_previous):
    fname = os.path.join(analysis_task_with_previous, 'fw_spec.json')
    with open(fname, 'r') as inf:
        spec = json.load(inf)

    p_id, results = spec['results'][0]

    results = results.split()

    assert results[0] == '0,123'
    assert results[1] == '673,456'
    assert results[2] == '1346,147'

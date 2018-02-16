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
        [gcwf.firetasks.AnalyseSimulation(
            fmt='raspa', temperature=200.0, pressure=100.0,
            parallel_id=1, workdir='.',
        ),
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
            fmt='raspa', temperature=200.0, pressure=100.0,
            parallel_id=1, workdir='.',
            previous_result='0,123\n673,456\n',
        ),
         TellTale()],
        spec={'simtree': os.path.abspath(successful_raspa)},
    )
    launchpad(fw.Workflow([firework]))

    yield successful_raspa


@pytest.fixture()
def successful_raspa_results():
    # tuple of (cycle number, instantaneous mol/kg results)
    return [
        (0, 2.9830315349),
        (673, 2.6380550989),
        (66627, 2.8815678772),
        (67300, 2.6989332935),
    ]

def test_analysis_creates_file(analysis_task):
    assert os.path.exists(os.path.join(analysis_task, 'this_sim_results.csv'))
    assert os.path.exists(os.path.join(analysis_task, 'total_results.csv'))


def test_results(analysis_task, successful_raspa_results):
    fname = os.path.join(analysis_task, 'fw_spec.json')
    with open(fname, 'r') as inf:
        spec = json.load(inf)

    p_id, results = spec['results'][0]

    assert p_id == 1

    results = results.split()

    for res, (ref_cycle, ref_loading) in zip(
            [results[0], results[1], results[-2], results[-1]],
            successful_raspa_results):
        cycle, loading = res.split(',')
        cycle, loading = int(cycle), float(loading)

        assert cycle == ref_cycle
        assert loading == pytest.approx(ref_loading)


def test_previous_results(analysis_task_with_previous, successful_raspa_results):
    fname = os.path.join(analysis_task_with_previous, 'fw_spec.json')
    with open(fname, 'r') as inf:
        spec = json.load(inf)

    p_id, results = spec['results'][0]

    results = results.split()

    assert results[0] == '0,123.0'
    assert results[1] == '673,456.0'
    cyc, loading = results[2].split(',')
    assert cyc == '1346'
    assert float(loading) == pytest.approx(successful_raspa_results[1][1])

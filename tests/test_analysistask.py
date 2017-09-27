"""Tests for AnalyseSimulation

"""
import fireworks as fw
import os
import pytest

import gcmcworkflow as gcwf


@pytest.fixture()
def analysis_task(successful_raspa, launchpad):
    # run analysis on a successful raspa simulation
    firework = fw.Firework(
        gcwf.firetasks.AnalyseSimulation(fmt='raspa', parallel_id=1),
        spec={'simtree': os.path.abspath(successful_raspa)},
    )
    launchpad(fw.Workflow([firework]))

    yield successful_raspa


def test_analysis_creates_file(analysis_task):
    assert os.path.exists(os.path.join(analysis_task, 'results.csv')) # os.path.join(analysis_task, 'results.csv'))

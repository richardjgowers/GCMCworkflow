"""Tests for the Creation of a "Run stage" via make_runstage

Run Stage is a (Copy, Run, Analyse) sequence of Fireworks

"""

import pytest

import fireworks as fw
import gcmcworkflow as gcwf


@pytest.fixture()
def runstage_parameters():
    # a set of typical arguments for make_runstage
    return {
        'parent_fw': None,
        'temperature': 100.0,
        'pressure': 1234.0,
        'ncycles': 4000,
        'parallel_id': 7,
        'fmt': 'raspa',
        'wfname': 'TestWF',
        'template': '/my_template/',
        'workdir': '/my_workdir',
    }


def test_make_runstage_len(runstage_parameters):
    # should return 3 Firework objects
    fws = gcwf.workflow_creator.make_runstage(**runstage_parameters)

    assert len(fws) == 3
    assert all(isinstance(thing, fw.Firework) for thing in fws)


@pytest.fixture()
def copy_fw(runstage_parameters):
    return gcwf.workflow_creator.make_runstage(**runstage_parameters)[0]


@pytest.fixture()
def run_fw(runstage_parameters):
    return gcwf.workflow_creator.make_runstage(**runstage_parameters)[1]


@pytest.fixture()
def analyse_fw(runstage_parameters):
    return gcwf.workflow_creator.make_runstage(**runstage_parameters)[2]


# For each Firework, check that it is the right object inside
def test_copy_fw_identity(copy_fw):
    assert len(copy_fw.tasks) == 1
    assert isinstance(copy_fw.tasks[0], gcwf.firetasks.CopyTemplate)


def test_run_fw_identity(run_fw):
    assert len(run_fw.tasks) == 1
    assert isinstance(run_fw.tasks[0], gcwf.firetasks.RunSimulation)

def test_analyse_fw_identity(analyse_fw):
    assert len(analyse_fw.tasks) == 1
    assert isinstance(analyse_fw.tasks[0], gcwf.firetasks.AnalyseSimulation)


# For each Firework, check its parameters match the input arguments
@pytest.mark.parametrize('arg', gcwf.firetasks.CopyTemplate.required_params)
def test_copy_fw_args(runstage_parameters, copy_fw, arg):
    assert copy_fw.tasks[0][arg] == runstage_parameters[arg]


@pytest.mark.parametrize('arg', gcwf.firetasks.RunSimulation.required_params)
def test_run_fw_args(runstage_parameters, run_fw, arg):
    assert run_fw.tasks[0][arg] == runstage_parameters[arg]


@pytest.mark.parametrize('arg', gcwf.firetasks.AnalyseSimulation.required_params)
def test_analyse_fw_args(runstage_parameters, analyse_fw, arg):
    assert analyse_fw.tasks[0][arg] == runstage_parameters[arg]

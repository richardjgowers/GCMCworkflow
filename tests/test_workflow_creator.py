"""Tests for workflow_creator and related things


"""
import pytest


import gcmcworkflow as gcwf


@pytest.fixture()
def dict_spec(sample_input):
    return dict(
        template={'simulation.input': 'sim\nsettings\n'},
        workdir='',
        name='Hurley',
        pressures=[10.0, 20.0, 30.0],
        temperatures=[204.5, 210.5],
        ncycles=1000,
        nparallel=2,
    )



@pytest.fixture()
def path_spec(sample_input):
    return dict(
        template='template',
        workdir='',
        name='Hurley',
        pressures=[10.0, 20.0, 30.0],
        temperatures=[204.5, 210.5],
        ncycles=1000,
        nparallel=2,
    )


def test_workflow_creator(dict_spec):
    wf = gcwf.workflow_creator.make_workflow(dict_spec)

    nconds = len(dict_spec['pressures']) * len(dict_spec['temperatures'])
    # expected number of Fireworks in workflow is:
    # 1 init
    # nconditions * nparallel simulation FWs
    # nconditions Analyses
    # 1 isotherm create FW
    nexpected = 1 + 3 * nconds * dict_spec['nparallel'] + nconds + 1

    assert len(wf.fws) == nexpected

def test_workflow_identity_and_dependency(dict_spec):
    # check the connectivity between Fireworks
    wf = gcwf.workflow_creator.make_workflow(dict_spec)

    nconds = len(dict_spec['pressures']) * len(dict_spec['temperatures'])

    # types of Fireworks: expected number and the expected number of parents
    fw_types = {
        gcwf.firetasks.InitTemplate: (1, 0),
        gcwf.firetasks.RunSimulation: (nconds * dict_spec['nparallel'], 1),
        gcwf.firetasks.PostProcess: (nconds, dict_spec['nparallel']),
        gcwf.firetasks.IsothermCreate: (1, nconds),
    }

    for fw_type, (n_expected, n_parents) in fw_types.items():
        this_type = [fw for fw in wf.fws
                     if any(isinstance(t, fw_type) for t in fw.tasks)]
        assert len(this_type) == n_expected
        assert all(len(fw.parents) == n_parents for fw in this_type)

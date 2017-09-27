"""Tests for workflow_creator and related things


"""
import pytest


import gcmcworkflow as gcwf


@pytest.fixture()
def simple_spec(sample_input):
    return dict(
        template='template',
        name='Hurley',
        pressures=[10.0, 20.0, 30.0],
        temperatures=[204.5, 210.5],
        ncycles=1000,
        nparallel=2,
    )


def test_workflow_creator(simple_spec):
    wf = gcwf.workflow_creator.make_workflow(simple_spec)

    nconds = len(simple_spec['pressures']) * len(simple_spec['temperatures'])
    # expected number of Fireworks in workflow is:
    # 1 init
    # nconditions * nparallel simulation FWs
    # nconditions Analyses
    # 1 isotherm create FW
    nexpected = 1 + nconds * simple_spec['nparallel'] + nconds + 1

    assert len(wf.fws) == nexpected

def test_workflow_identity_and_dependency(simple_spec):
    # check the connectivity between Fireworks
    wf = gcwf.workflow_creator.make_workflow(simple_spec)

    nconds = len(simple_spec['pressures']) * len(simple_spec['temperatures'])

    # types of Fireworks: expected number and the expected number of parents
    fw_types = {
        gcwf.firetasks.InitTemplate: (1, 0),
        gcwf.firetasks.RunSimulation: (nconds * simple_spec['nparallel'], 1),
        gcwf.firetasks.PostProcess: (nconds, simple_spec['nparallel']),
        gcwf.firetasks.IsothermCreate: (1, nconds),
    }

    for fw_type, (n_expected, n_parents) in fw_types.items():
        this_type = [fw for fw in wf.fws
                     if any(isinstance(t, fw_type) for t in fw.tasks)]
        assert len(this_type) == n_expected
        assert all(len(fw.parents) == n_parents for fw in this_type)

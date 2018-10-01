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
        conditions=[
            (204.5, [10.0, 20.0, 30.0], 0),
            (210.5, [10.0, 20.0, 30.0], 0),
        ],
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

    nconds = 6
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

    nconds = 6

    # types of Fireworks: expected number and the expected number of parents
    fw_types = {
        gcwf.firetasks.InitTemplate: (1, 0),
        gcwf.firetasks.RunSimulation: (nconds * dict_spec['nparallel'], 1),
        gcwf.firetasks.Analyse: (nconds, dict_spec['nparallel']),
        gcwf.firetasks.IsothermCreate: (1, nconds),
    }

    for fw_type, (n_expected, n_parents) in fw_types.items():
        this_type = [fw for fw in wf.fws
                     if any(isinstance(t, fw_type) for t in fw.tasks)]
        assert len(this_type) == n_expected
        assert all(len(fw.parents) == n_parents for fw in this_type)


@pytest.fixture
def grid_spec():
    return dict(
        template={'simulation.input': 'wow\nmy sim\n'},
        workdir='',
        name='GridSpecTest',
        conditions=[
            (10., [10.], 0)
        ],
        ncycles=100,
        nparallel=1,
        use_grid=True,
    )

def test_workflow_with_grid(grid_spec):
    wf = gcwf.workflow_creator.make_workflow(grid_spec)
    # Init, Grid, Copy, Run, PP, Analyse, Isotherm
    assert len(wf.fws) == 7

    grid_fw = [fw for fw in wf.fws
               if any(isinstance(t, gcwf.grids.PrepareGridInput)
                      for t in fw.tasks)]
    assert len(grid_fw) == 1
    

def test_postprocess_with_grid(grid_spec):
    wf = gcwf.workflow_creator.make_workflow(grid_spec)

    pp_fw = [fw for fw in wf.fws
             if any(isinstance(t, gcwf.firetasks.PostProcess)
                    for t in fw.tasks)][0]

    assert pp_fw.tasks[0]['use_grid']


def test_analyse_with_grid(grid_spec):
    wf = gcwf.workflow_creator.make_workflow(grid_spec)

    ana_fw = [fw for fw in wf.fws
             if any(isinstance(t, gcwf.firetasks.Analyse)
                    for t in fw.tasks)][0]

    assert ana_fw.tasks[0]['use_grid']



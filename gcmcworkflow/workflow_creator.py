import itertools
import fireworks as fw
import os

from . import utils
from . import firetasks


def make_workflow(spec, simple=True):
    """Create an entire Isotherm creation Workflow

    Parameters
    ----------
    spec : dict
      has all the information for workflow
    simple : bool, optional
      use decorrelation analysis to determine if to run more sims

    Returns
    -------
    workflow : fw.Workflow
      Workflow object ready to submit to LaunchPad
    """
    temperatures = spec['temperatures']
    pressures = spec['pressures']
    nparallel = spec['nparallel']
    ncycles = spec['ncycles']
    template = spec['template']
    workdir = spec['workdir']
    wfname = spec['name']

    if not isinstance(template, dict):
        dict_template = False
        # Passed path to template
        # if passed path to template, slurp it up

        # old method of slurping up directory
        stuff = utils.slurp_directory(template)
    else:
        dict_template = True
        # Else passed dict of stuff
        stuff = template

    simfmt = utils.guess_format(stuff)
    stuff = utils.escape_template(stuff)

    if dict_template:
        init = fw.Firework(
            firetasks.InitTemplate(contents=stuff, workdir=workdir),
            spec={'_category': wfname},
            name='Template Init'
        )
        setup = [init]
    else:
        init = None
        setup = []

    simulations = []  # list of simulation fireworks
    post_processing = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition = make_Simfireworks(
            parent_fw=init,
            T=T, P=P, ncycles=ncycles, nparallel=nparallel,
            simfmt=simfmt, wfname=wfname,
            template=template, workdir=workdir,
        )
        this_condition_PP = make_PostProcess(
            parent_fw=this_condition,
            T=T, P=P,
            wfname=wfname,
            simple=simple,
        )

        simulations.extend(this_condition)
        post_processing.append(this_condition_PP)

    iso_create = fw.Firework(firetasks.IsothermCreate(workdir=workdir),
                             parents=post_processing,
                             spec={'_category': wfname},
                             name='Isotherm create')

    wf = fw.Workflow(
        setup + simulations + post_processing + [iso_create],
        name=wfname,
        metadata={'GCMCWorkflow': True},  # tag as GCMCWorkflow workflow
    )

    return wf


def make_Simfireworks(parent_fw, T, P, ncycles, nparallel, simfmt, wfname,
                      template, workdir):
    """Make many Simfireworks for a given conditions

    Parameters
    ----------
    parent_fw : fireworks.Firework or None
      Reference to InitTemplate that Simfireworks are children to
    T : float
      temperature
    P : float
      pressure
    ncycles : int
      length of simulation
    nparallel : int
      degree of parallelism
    simfmt : str
      format of the simulation
    wfname : str
      name for this workflow, so FWorkers can find it
    template : str
      path to template files
    workdir : str
      path to where to store results

    Returns
    -------
    sims
      List of SimulationFireworks
    """
    sims = [fw.Firework(
        [firetasks.CopyTemplate(fmt=simfmt, temperature=T, pressure=P,
                                parallel_id=i, ncycles=ncycles,
                                workdir=workdir),
         firetasks.RunSimulation(fmt=simfmt),
         firetasks.AnalyseSimulation(fmt=simfmt, parallel_id=i)],
        spec={
            'template': template,
            '_category': wfname,
        },
        parents=parent_fw,
        name=utils.gen_name(T, P, i),
    ) for i in range(nparallel)]
    return sims


def make_PostProcess(parent_fw, T, P, wfname, simple):
    if simple:
        pp_cls = firetasks.SimplePostProcess
    else:
        pp_cls = firetasks.PostProcess

    return fw.Firework(
        pp_cls(temperature=T, pressure=P),
        spec={'_category': wfname},
        parents=parent_fw,
        name='PostProcess T={} P={}'.format(T, P)
    )

import itertools
import fireworks as fw
import gcmcworkflow as gcwf
import os

from . import utils


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
            gcwf.firetasks.InitTemplate(contents=stuff, workdir=workdir),
            spec={'_category': wfname},
            name='Template Init'
        )
        setup = [init]
    else:
        init = None
        setup = []

    if simple:
        pp_cls = gcwf.firetasks.SimplePostProcess
    else:
        pp_cls = gcwf.firetasks.PostProcess

    simulations = []  # list of simulation fireworks
    post_processing = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition = [
            fw.Firework(
                [gcwf.firetasks.CopyTemplate(fmt=simfmt, temperature=T,
                                             pressure=P, parallel_id=i,
                                             ncycles=ncycles, workdir=workdir),
                 gcwf.firetasks.RunSimulation(fmt=simfmt),
                 gcwf.firetasks.AnalyseSimulation(fmt=simfmt, parallel_id=i)],
                spec={
                    'generation': 1,
                    'template': template,
                    '_category': wfname,
                },
                parents=init,
                name=utils.gen_name(T, P, i),
            ) for i in range(nparallel)]
        this_condition_PP = fw.Firework(
            pp_cls(temperature=T, pressure=P),
            spec={'_category': wfname},
            parents=this_condition,
            name='PostProcess T={} P={}'.format(T, P)
        )
        simulations.extend(this_condition)
        post_processing.append(this_condition_PP)

    iso_create = fw.Firework(gcwf.firetasks.IsothermCreate(workdir=workdir),
                             parents=post_processing,
                             spec={'_category': wfname},
                             name='Isotherm create')

    wf = fw.Workflow(setup + simulations + post_processing + [iso_create],
                     name=wfname)

    return wf


def make_Simfireworks(parent_fw, T, P, ncycles, nparallel, simfmt, wfname,
                      workdir, generation):
    """Make many Simfireworks for a given conditions

    Parameters
    ----------
    parent_fw : fireworks.Firework
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
    workdir : str
      path to where to store results
    generation : int
      iteration counter for this condition
    simple : bool, optional
      use SimplePostProcess or not

    Returns
    -------
    sims
      List of SimulationFireworks
    """
    sims = []
    for i in range(nparallel):
        sims.append(fw.Firework(
            [gcwf.firetasks.CopyTemplate(fmt=simfmt, temperature=T, pressure=P,
                                         parallel_id=i, ncycles=ncycles,
                                         workdir=workdir),
             gcwf.firetasks.RunSimulation(fmt=simfmt),
             gcwf.firetasks.AnalyseSimulation(fmt=simfmt, parallel_id=i)],
            spec={
                'generation': generation,
                '_category': wfname,
              },
            parents=[parent_fw],
            name=utils.gen_name(T, P, i)
        ))
    return sims

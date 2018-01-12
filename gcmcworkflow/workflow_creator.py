import itertools
import fireworks as fw
import gcmcworkflow as gcwf
import os

from . import utils


def make_workflow(spec, simple=False):
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
    wfname = spec['name']
    # Adjust simulation length according to nparallel
    if not ncycles is None:  # can be none to use template default
        ncycles = ncycles // nparallel

    if not isinstance(template, dict):
        # if passed path to template, slurp it up
        stuff = utils.slurp_directory(template)
    else:
        stuff = template

    fmt = utils.guess_format(stuff)

    stuff = utils.escape_template(stuff)

    init = fw.Firework(
        gcwf.firetasks.InitTemplate(contents=stuff),
        spec={'_category': wfname},
        name='Template Init'
    )

    simulations = []  # list of simulation fireworks
    post_processing = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition, this_condition_PP = make_Simfireworks(
            init, T, P, ncycles, nparallel, fmt, wfname, simple=simple)

        simulations.extend(this_condition)
        post_processing.append(this_condition_PP)

    iso_create = fw.Firework(gcwf.firetasks.IsothermCreate(),
                             parents=post_processing,
                             spec={'_category': wfname},
                             name='Isotherm create')

    wf = fw.Workflow([init] + simulations + post_processing + [iso_create],
                     name=wfname)

    return wf


def make_Simfireworks(parent_fw, T, P, ncycles, C, simfmt, category,
                      generation=None, simple=False):
    """Make many Simfireworks for a given conditions

    Creates the required post processing task

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
    C : int
      degree of parallelism
    simfmt : str
      format of the simulation
    category : str
      name for this workflow, so FWorkers can find it
    generation : int, optional
      defaults to 1
    simple : bool, optional
      use SimplePostProcess or not

    Returns
    -------
    sims, post
      List of SimulationFireworks, and PostProcess Firework
    """
    if generation is None:
        generation = 1

    if simple:
        pp_cls = gcwf.firetasks.SimplePostProcess
    else:
        pp_cls = gcwf.firetasks.PostProcess

    sims = []
    for i in range(C):
        sims.append(fw.Firework(
            [gcwf.firetasks.CopyTemplate(fmt=simfmt, temperature=T, pressure=P,
                                         parallel_id=i, ncycles=ncycles),
             gcwf.firetasks.RunSimulation(fmt=simfmt),
             gcwf.firetasks.AnalyseSimulation(fmt=simfmt, parallel_id=i)],
            spec={
                'generation': 1,
                '_category': category,
              },
            parents=[parent_fw],
            name=utils.gen_name(T, P, i)
        ))
    post = fw.Firework(
        pp_cls(temperature=T, pressure=P),
        spec={'_category': category},
        parents=sims,
        name='PostProcess T={} P={}'.format(T, P)
    )
    return sims, post

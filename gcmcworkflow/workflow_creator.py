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
        # Passed path to template
        # if passed path to template, slurp it up

        # old method of slurping up directory
        stuff = None
        slurped = utils.slurp_directory(template)
        simfmt = utils.guess_format(slurped)
    else:
        # Else passed dict of stuff
        stuff = template
        simfmt = utils.guess_format(stuff)
        stuff = utils.escape_template(stuff)

    init = fw.Firework(
        [firetasks.InitTemplate(contents=stuff, workdir=workdir),
         firetasks.CreatePassport(workdir=workdir)],
        spec={
            '_category': wfname,
            'template': template,
        },
        name='Template Init',
    )

    simulations = []  # list of simulation fireworks
    post_processing = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition, this_condition_PP = make_sampling_point(
            parent_fw=init,
            T=T, P=P, ncycles=ncycles, nparallel=nparallel,
            simfmt=simfmt, wfname=wfname,
            template=template, workdir=workdir,
            simple=simple,
        )
        simulations.extend(this_condition)
        post_processing.append(this_condition_PP)

    iso_create = fw.Firework(
        [firetasks.IsothermCreate(workdir=workdir)],
        parents=post_processing,
        spec={'_category': wfname},
        name='Isotherm create',
    )

    wf = fw.Workflow(
        [init] + simulations + post_processing + [iso_create],
        name=wfname,
        metadata={'GCMCWorkflow': True},  # tag as GCMCWorkflow workflow
    )

    return wf


def make_runstage(parent_fw, temperature, pressure, ncycles, parallel_id,
                  fmt, wfname, template, workdir,
                  previous_simdir=None, previous_result=None):
    """Make a single Run stage

    Parameters
    ----------
    parent_fw : fw.Firework or None
      reference to preceeding item in workflow
    temperature, pressure : float
      conditions to sample
    ncycles : int
      number of steps to simulate at this point
    parallel_id : int
      index of the run
    fmt : str
      which format simulation
    wfname : str
      unique workflow name
    template : str
      location of the template files
    workdir : str
      where to place the simulation
    previous_simdir : str, optional
      if a restart, where the simulation
    """
    if ((previous_simdir is None and not previous_result is None) or
        (not previous_simdir is None and previous_result is None)):
        raise ValueError("Must supply *both* previous simdir and result")

    copy = fw.Firework(
        [firetasks.CopyTemplate(
            fmt=fmt, temperature=temperature, pressure=pressure,
            ncycles=ncycles,
            parallel_id=parallel_id,
            workdir=workdir,
            previous_simdir=previous_simdir
        )],
        parents=parent_fw,
        spec={
            'template': template,
            '_category': wfname,
        },
        name='Copy T={} P={} v{}'.format(temperature, pressure, parallel_id),
    )
    run = fw.Firework(
        [firetasks.RunSimulation(fmt=fmt)],
        parents=[copy],
        spec={
            '_category': wfname,
        },
        name=utils.gen_name(temperature, pressure, parallel_id),
    )
    analyse = fw.Firework(
        [firetasks.AnalyseSimulation(
            fmt=fmt, temperature=temperature, pressure=pressure,
            parallel_id=parallel_id,
            workdir=workdir,
            # if this is a restart, pass previous results, else None
            previous_result=previous_result,
        )],
        spec={
            '_allow_fizzled_parents': True,
            '_category': wfname,
        },
        parents=[copy, run],
        name='Analyse T={} P={} v{}'.format(temperature, pressure, parallel_id)
    )

    return copy, run, analyse


def make_sampling_point(parent_fw, T, P, ncycles, nparallel,
                        simfmt, wfname, template, workdir, simple,
                        previous_results=None, previous_simdirs=None):
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
    run_sims, analyse_sims : tuple
      List of SimulationFireworks
    """
    if previous_results is None:
        previous_results = dict()
    if previous_simdirs is None:
        previous_simdirs = dict()

    runs = []
    analyses = []

    for i in range(nparallel):
        copy, run, analyse = make_runstage(
            parent_fw=parent_fw, temperature=T, pressure=P, ncycles=ncycles,
            parallel_id=i, fmt=simfmt, wfname=wfname,
            template=template, workdir=workdir,
            previous_simdir=previous_simdirs.get(i, None),
            previous_result=previous_results.get(i, None),
        )
        runs.append(copy)
        runs.append(run)
        analyses.append(analyse)

    postprocess = fw.Firework(
        [firetasks.PostProcess(temperature=T, pressure=P, workdir=workdir,
                               fmt=simfmt, simple=simple)],
        spec={'_category': wfname},
        parents=analyses,
        name='PostProcess T={} P={}'.format(T, P)
    )

    return runs + analyses, postprocess

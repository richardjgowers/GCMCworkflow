import itertools
import fireworks as fw

from . import utils
from . import firetasks
from . import grids


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

    use_grid = spec.get('use_grid', False)

    init = fw.Firework(
        [firetasks.InitTemplate(contents=stuff, workdir=workdir),
         firetasks.CreatePassport(workdir=workdir)],
        spec={
            '_category': wfname,
            'template': template,
        },
        name='Template Init',
    )

    if use_grid:
        gridmake = fw.Firework(
            [grids.PrepareGridInput(workdir=workdir),
             firetasks.RunSimulation(fmt='raspa')],
            parents=[init],
            spec={
                '_category': wfname,
                'template': template,
            }
            name='Grid Make',
        )
        init_parent = gridmake
        grid = [gridmake]
    else:
        init_parent = init
        grid = []

    simulation_steps = []  # list of simulation fireworks
    analysis_steps = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition, this_condition_analysis = make_sampling_point(
            parent_fw=init_parent,
            temperature=T,
            pressure=P,
            ncycles=ncycles,
            nparallel=nparallel,
            fmt=simfmt,
            wfname=wfname,
            template=template,
            workdir=workdir,
            simple=simple,
            use_grid=use_grid,
        )
        simulation_steps.extend(this_condition)
        analysis_steps.append(this_condition_analysis)

    iso_create = fw.Firework(
        [firetasks.IsothermCreate(workdir=workdir)],
        parents=analysis_steps,
        spec={'_category': wfname},
        name='Isotherm create',
    )

    wf = fw.Workflow(
        [init] + grid + simulation_steps + analysis_steps + [iso_create],
        name=wfname,
        metadata={'GCMCWorkflow': True},  # tag as GCMCWorkflow workflow
    )

    return wf


def make_runstage(parent_fw, temperature, pressure, ncycles, parallel_id,
                  fmt, wfname, template, workdir,
                  previous_simdir=None, previous_result=None, simhash=None,
                  use_grid=False):
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
      if a restart, where the simulation took place
    previous_result : str, optional
      if a restart, csv representation of previous results
    use_grid : bool, optional
      whether to use an energy grid

    Returns
    -------
    copy, run, analyse
      tuple of fw.Firework objects
    """
    if ((previous_simdir is None and not previous_result is None) or
        (not previous_simdir is None and previous_result is None)):
        raise ValueError("Must supply *both* previous simdir and result")
    if simhash is None:
        simhash = ''

    copy = fw.Firework(
        [firetasks.CopyTemplate(
            fmt=fmt,
            temperature=temperature,
            pressure=pressure,
            ncycles=ncycles,
            parallel_id=parallel_id,
            workdir=workdir,
            previous_simdir=previous_simdir,
            use_grid=use_grid,
        )],
        parents=parent_fw,
        spec={
            'template': template,
            'simhash': simhash,
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
    postprocess = fw.Firework(
        [firetasks.PostProcess(
            fmt=fmt,
            temperature=temperature,
            pressure=pressure,
            parallel_id=parallel_id,
            workdir=workdir,
            # if this is a restart, pass previous results, else None
            previous_result=previous_result,
            use_grid=use_grid,
        )],
        spec={
            '_allow_fizzled_parents': True,
            '_category': wfname,
        },
        parents=[copy, run],
        name='PostProcess T={} P={} v{}'.format(
            temperature, pressure, parallel_id)
    )

    return copy, run, postprocess


def make_sampling_point(parent_fw, temperature, pressure, ncycles, nparallel,
                        fmt, wfname, template, workdir, simple,
                        simhash=None, previous_results=None,
                        previous_simdirs=None, use_grid=False):
    """Make many Simfireworks for a given conditions

    Parameters
    ----------
    parent_fw : fireworks.Firework or None
      Reference to InitTemplate that Simfireworks are children to
    temperature, pressure : float
      conditions to sample
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
    simple : bool
      complex recycle loop or not
    simhash : str, optional
      unique string for this simulation template
    previous_results : dict, optional
      mapping of parallel_id to previous results
    previous_simdirs : dict, optional
      mapping of parallel_id to directory where sim took place
    use_grid : bool, optional
      whether to use an energy grid

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
    postprocesses = []

    for i in range(nparallel):
        copy, run, postprocess = make_runstage(
            parent_fw=parent_fw,
            temperature=temperature,
            pressure=pressure,
            ncycles=ncycles,
            parallel_id=i,
            fmt=fmt,
            wfname=wfname,
            template=template,
            workdir=workdir,
            previous_simdir=previous_simdirs.get(i, None),
            previous_result=previous_results.get(i, None),
            simhash=simhash,
            use_grid=use_grid,
        )
        runs.append(copy)
        runs.append(run)
        postprocesses.append(postprocess)

    analysis = fw.Firework(
        [firetasks.Analyse(
            temperature=temperature,
            pressure=pressure,
            workdir=workdir,
            fmt=fmt,
            simple=simple,
            use_grid=use_grid,
        )],
        spec={'_category': wfname},
        parents=postprocesses,
        name='Analyse T={} P={}'.format(temperature, pressure)
    )

    return runs + postprocesses, analysis

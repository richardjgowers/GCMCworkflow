import itertools
import fireworks as fw

from . import utils
from . import firetasks
from . import grids
from . import hyd


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
    nparallel = spec['nparallel']
    ncycles = spec['ncycles']
    template = spec['template']
    workdir = spec['workdir']
    wfname = spec['name']
    use_grid = spec.get('use_grid', False)
    g_req = spec.get('g_req', None)
    max_iters = spec.get('max_iterations', None)

    init = make_init_stage(
        workdir=workdir,
        wfname=wfname,
        template=template,
    )

    if use_grid:
        gridmake = grids.make_grid_firework(workdir, [init], wfname, template)
        init_parent = [init, gridmake]
    else:
        init_parent = [init]

    simulation_steps = []  # list of simulation fireworks
    analysis_steps = []  # list of Analysis fireworks
    adaptive_steps = []
    for (T, pressures, adaptive) in spec['conditions']:
        for P in pressures:
            this_condition, this_condition_analysis = make_sampling_point(
                parent_fw=init_parent,
                temperature=T,
                pressure=P,
                ncycles=ncycles,
                nparallel=nparallel,
                wfname=wfname,
                template=template,
                workdir=workdir,
                simple=simple,
                use_grid=use_grid,
                g_req=g_req,
                max_iterations=max_iters,
            )
            simulation_steps.extend(this_condition)
            analysis_steps.append(this_condition_analysis)
            if adaptive:
                pass

    iso_create = fw.Firework(
        [firetasks.IsothermCreate(workdir=workdir)],
        parents=analysis_steps + adaptive_steps,
        spec={'_category': wfname},
        name='Isotherm create',
    )

    wf = fw.Workflow(
        init_parent + simulation_steps + analysis_steps + [iso_create],
        name=wfname,
        metadata={'GCMCWorkflow': True},  # tag as GCMCWorkflow workflow
    )

    return wf


def make_init_stage(workdir, wfname, template):
    """Make initialisation stage of Workflow

    Parameters
    ----------
    workdir : str
      path to run simulations in
    wfname : str
      unique name for this Workflow
    template : dict or str
      template to use for simulation

    Returns
    -------
    init : fw.Firework
      handles template creation and passport
    """
    if isinstance(template, str) and template.startswith('Hydraspa('):
        first_task = hyd.HydraspaCreate(
            structure_name=template[9:-1],  # strips off HYDRASPA(XYZ)
            workdir=workdir,
        )
        template = None
    else:
        if not isinstance(template, dict):
            # Passed path to template
            # if passed path to template, slurp it up

            # old method of slurping up directory
            stuff = None
            slurped = utils.slurp_directory(template)
        else:
            # Else passed dict of stuff
            stuff = template
            stuff = utils.escape_template(stuff)

        first_task = firetasks.InitTemplate(contents=stuff, workdir=workdir)

    init = fw.Firework(
        [first_task,
         firetasks.CreatePassport(workdir=workdir)],
        spec={
            '_category': wfname,
            'template': template,
        },
        name='Template Init',
    )

    return init


def make_runstage(parent_fw, temperature, pressure, ncycles, parallel_id,
                  wfname, template, workdir,
                  previous_simdir=None, previous_result=None,
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

    copy = fw.Firework(
        [firetasks.CopyTemplate(
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
            '_category': wfname,
        },
        name='Copy T={} P={} v{}'.format(temperature, pressure, parallel_id),
    )
    run = fw.Firework(
        [firetasks.RunSimulation()],
        parents=[copy],
        spec={
            '_category': wfname,
        },
        name=utils.gen_name(temperature, pressure, parallel_id),
    )
    postprocess = fw.Firework(
        [firetasks.PostProcess(
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
                        wfname, template, workdir, simple,
                        previous_results=None, previous_simdirs=None,
                        use_grid=False, g_req=None,
                        iteration=None, max_iterations=None):
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
    wfname : str
      name for this workflow, so FWorkers can find it
    template : str
      path to template files
    workdir : str
      path to where to store results
    simple : bool
      complex recycle loop or not
    previous_results : dict, optional
      mapping of parallel_id to previous results
    previous_simdirs : dict, optional
      mapping of parallel_id to directory where sim took place
    use_grid : bool, optional
      whether to use an energy grid
    g_req : float, optional
      number of decorrelations to sample
    iteration : int, optional
      iteration number for this sampling, defaults to 0
    max_iterations : int, optional
      maximum number of iterations to allow, defaults to infinite

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

    if iteration is None:
        iteration = 0

    for i in range(nparallel):
        copy, run, postprocess = make_runstage(
            parent_fw=parent_fw,
            temperature=temperature,
            pressure=pressure,
            ncycles=ncycles,
            parallel_id=i,
            wfname=wfname,
            template=template,
            workdir=workdir,
            previous_simdir=previous_simdirs.get(i, None),
            previous_result=previous_results.get(i, None),
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
            simple=simple,
            use_grid=use_grid,
            g_req=g_req,
            iteration=iteration,
            max_iterations=max_iterations,
        )],
        spec={'_category': wfname},
        parents=postprocesses,
        name='Analyse T={} P={}'.format(temperature, pressure)
    )

    return runs + postprocesses, analysis

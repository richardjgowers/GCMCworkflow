"""Functions for creating GAFW Fireworks"""
import fireworks as fw

from . import utils
from .firetasks import (
    InitTemplate,
    CopyTemplate,
    RunSimulation,
    IsothermCreate,
)
from .genetics import (
    AssignFitness,
    InitPopulation,
    PassAlong,
    Tournament,
    VaryCandidates,
    ManipulateForcefield,
    EvaluateResult,
    Replacement,
)


# run once at start of GA
def Firstgen_PreGA_FW(template, pop, wf_name):
    """Variant of PreGA for the zeroth generation

    Parameters
    ----------
    template : str
      path to the template for simulations
    pop : tuple of tuples
      description of the initial population
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    firstgen_prega : fireworks.Firework
      Firework for the setup of GA
    """
    stuff = utils.slurp_directory(template)

    return fw.Firework(
        [
        # creates template
        InitTemplate(contents=stuff),
        # creates candidates and population
        InitPopulation(initial_population=pop),
        ],
        spec={
            '_category': wf_name,
        },
        name='Firstgen PreGA',
    )


def PreGA_FW(parent, idx, bounds, wf_name):
    """Operations to set up candidates

    Parameters
    ----------
    parent : fw.Firework
      ref to previous FW
    idx : int
      index of which generation of GA this is
    bounds : tuple
      tuple containing the minimum and maximum bounds for each parameter
      eg `((1.0, 2.0), (10.0, 20.0))` clamps the first value between 1.0 and 2.0
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    prega : fireworks.Firework
    """
    settings = VaryCandidates.default_params.copy()
    settings['bounds'] = bounds
    return fw.Firework(
        [
            Tournament(),
            VaryCandidates(**settings),
            PassAlong(keys=['template', 'parents']),
        ],
        spec={
            '_category': wf_name,
        },
        parents=parent,
        name='PreGA G={}'.format(idx),
    )


def Sim_FW(temperature, pressure, ref, generation_id, candidate_id, ff_updater,
           parent, wf_name):
    """Generate a single simulation Firework

    Parameters
    ----------
    temperature : int
      temperature
    pressure : int
      pressure
    ref : float
      desired result for this T & P
    generation_id : int
      id of the generation
    candidate_id : int
      which candidate this simulation refers to
    ff_updater : function
      function which does the manipulation of forcefield files
    parent : fw.Firework
      the preceeding Firework to this Firework
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    sim : fireworks.Firework
    """
    # convert python function to pickle form
    ff_updater = utils.pickle_func(ff_updater)

    return fw.Firework(
        [
            CopyTemplate(
                temperature=temperature,
                pressure=pressure,
                parallel_id=generation_id,
            ),
            ManipulateForcefield(
                candidate_id=candidate_id,
                updater=ff_updater,
            ),
            RunSimulation(),
            EvaluateResult(
                reference=ref,
                temperature=temperature,
                pressure=pressure,
            ),
        ],
        spec={
            '_category': wf_name,
        },
        parents=parent,
        name='Sim T={} P={} C={}'.format(temperature, pressure, candidate_id),
    )


def PostSim_FW(generation_id, candidate_id, parents, wf_name):
    """Collects Sims from different conditions in one candidate fitness

    Parameters
    ----------
    generation_id : int
      id of the generation
    candidate_id : int
      id of this candidate
    parents : list of fw.Firework
      references to the preceeding Fireworks for this candidate
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    postsim : fireworks.Firework
    """
    return fw.Firework(
        [
            IsothermCreate(),
            AssignFitness(candidate_id=candidate_id),
        ],
        spec={
            '_category': wf_name,
        },
        parents=parents,
        name='PostSim G={} C={}'.format(generation_id, candidate_id),
    )


def PostGA_FW(generation_id, parents, wf_name):
    """Operations to finish the GA generation

    Parameters
    ----------
    generation_id : int
      id of the generation
    parents : list of fw.Firework
      references to PostSim Fireworks
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    postga : fireworks.Firework
    """
    return fw.Firework(
        [
            Replacement(),
            PassAlong(keys=['template'])
        ],
        spec = {
            '_category': wf_name,
        },
        parents=parents,
        name='PostGA G={}'.format(generation_id),
    )


def make_sampling_stage(conditions, generation_id, candidate_id,
                        ff_updater, parent, wf_name):
    """Make a sampling stage for a single candidate

    Parameters
    ----------
    conditions : tuple of tuples
      tuple of (T, P, ref) for each condition
    generation_id : int
      id of the generation
    candidate_id : int
      id of this candidate
    ff_updater : function
      function which does the manipulation of forcefield files
    parent : fw.Firework
      reference to preceeding Firework
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    sim_fws, gather_fw : list, fw.Firework
    """
    sim_fws = []
    for T, P, ref in conditions:
        sim_fws.append(
            Sim_FW(
                temperature=T,
                pressure=P,
                ref=ref,
                generation_id=generation_id,
                candidate_id=candidate_id,
                ff_updater=ff_updater,
                parent=parent,
                wf_name=wf_name,
            ),
        )
    final_fw = PostSim_FW(
        generation_id=generation_id,
        candidate_id=candidate_id,
        parents=sim_fws,
        wf_name=wf_name,
    )

    return sim_fws, final_fw


def make_first_generation(template, ncandidates, initial_pop,
                          conditions, ff_updater, wf_name):
    """Make the first generation of a GA

    Parameters
    ----------
    template : str
      path to template
    ncandidates : int
      number of candidates in the generation
    initial_pop : tuple
      tuple describing initial population
    conditions : tuple of tuples
      tuple of (T, P, reference_result) for each condition
    ff_updater : function
      function which does the manipulation of forcefield files
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    list of Fireworks
      ordered so that final FW is the post GA FW
    """
    # make initial population
    pre = Firstgen_PreGA_FW(template=template, pop=initial_pop, wf_name=wf_name)

    sims = []
    final_fws = []
    for i in range(ncandidates):
        sim_fws, final_fw = make_sampling_stage(
            conditions=conditions,
            generation_id=0,
            candidate_id=i,
            ff_updater=ff_updater,
            parent=pre,
            wf_name=wf_name,
        )
        sims.extend(sim_fws)
        final_fws.append(final_fw)

    post = PostGA_FW(
        generation_id=0,
        parents=final_fws + [pre],
        wf_name=wf_name,
    )

    return [pre] + sims + final_fws + [post]


def make_generation_n(ncandidates, conditions, bounds, ff_updater, parent,
                      generation_id, wf_name):
    """Make the nth generation of a GA

    Parameters
    ----------
    ncandidates : int
      number of candidates in the generation
    conditions : tuple of tuples
      tuple of (T, P, reference result) for each point to match
    bounds : tuple
      tuple containing the minimum and maximum bounds for each parameter
      eg `((1.0, 2.0), (10.0, 20.0))` clamps the first value between 1.0 and 2.0
    ff_updater : function
      function which does the manipulation of forcefield files
    parent : fw.Firework
      reference to preceeding Firework
    generation_id : int
      index of the generation
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    fireworks : list
      list of fw.Firework instances
    """
    pre = PreGA_FW(
        parent=parent,
        idx=generation_id,
        bounds=bounds,
        wf_name=wf_name,
    )

    sims = []
    final_fws = []
    for i in range(ncandidates):
        sim_fws, final_fw = make_sampling_stage(
            conditions=conditions,
            generation_id=generation_id,
            candidate_id=i,
            ff_updater=ff_updater,
            parent=pre,
            wf_name=wf_name,
        )
        sims.extend(sim_fws)
        final_fws.append(final_fw)

    post = PostGA_FW(
        generation_id=generation_id,
        parents=final_fws + [pre],
        wf_name=wf_name,
    )

    return [pre] + sims + final_fws + [post]


def make_genetic_workflow(ngens, ncandidates, template, initial_pop, bounds,
                          conditions, ff_updater, wf_name):
    """Make a genetic alg. forcefield optimisation workflow

    Parameters
    ----------
    ngens : int
      number of generations to run algorithm for
    ncandidates : int
      number of candidates in the generation
    template : str
      path to the template
    initial_pop : tuple of tuples
      description of initial candidates
    bounds : tuple
      tuple containing the minimum and maximum bounds for each parameter
      eg `((1.0, 2.0), (10.0, 20.0))` clamps the first value between 1.0 and 2.0
    conditions : tuple of tuples
      tuple of (T, P, reference result) for each point to match
    ff_updater : function
      function which does the manipulation of forcefield files
    wf_name : str
      unique key to refer to this workflow by

    Returns
    -------
    workflow : fw.Workflow
      the Workflow ready to be put on launchpad
    """
    first = make_first_generation(template=template,
                                  initial_pop=initial_pop,
                                  ncandidates=ncandidates,
                                  conditions=conditions,
                                  ff_updater=ff_updater,
                                  wf_name=wf_name,
    )
    gen = first

    fws = first
    for gen_id in range(ngens):
        # the parent FW for next generation is last FW in previous gen
        parent = gen[-1]
        gen = make_generation_n(ncandidates=ncandidates,
                                bounds=bounds,
                                conditions=conditions,
                                parent=parent,
                                generation_id=gen_id + 1,
                                ff_updater=ff_updater,
                                wf_name=wf_name,
        )
        fws.extend(gen)

    return fw.Workflow(fws, name=wf_name)

"""Functions for post processing of simulations

"""
import fireworks as fw
import pandas as pd

from gcmcworkflow import utils


def gen_restart_sims(old_generation, T, P):
    """Generate some new simulations from old generation

    Parameters
    ----------
    old_generation : list
      list of Treants of old simulations
    """
    from gcmcworkflow import firetasks as ft

    new_sims = []

    last_gen = old_generation.categories['generation'][0]
    # TODO: Could optimise the number of cycles based on the amount of data
    # gathered last time around
    last_ncycles = old_generation.categories['ncycles'][0]

    # TODO:
    # If we want to limit the number of possible generations, here is the place to do it
    # Maybe Raise GenerationLimitError when asked for a new generation
    # this would then make this condition essentially fail to get sampled
    # if last_gen == GEN_LIMIT:
    #    raise GenerationLimitError

    # TODO: Should iterate over parallel_id to ensure that continuations are dovetailed properly
    # ie g1 p1 -> g2 p1 -> g3 p1 forms a timeseries
    for old_tree in old_generation:
        # restart shares same parallel_id
        p_id = old_tree.categories['parallel_id']
        old_loc = old_tree.abspath

        # for each old treant from the last generation,
        # restart task,
        # run task
        # analyse task
        New_sims.append(fw.Firework(
            [ft.CreateRestart(loc=old_loc),
             ft.RunSimulation(),
             ft.AnalyseSimulation()],
            spec={'temperature': T,
                  'pressure': P,
                  'ncycles': last_ncycles,
                  'parallel_id': p_id,
                  'generation': last_gen + 1},
            name=utils.gen_name(T, P, p_id)
        ))

    post = fw.Firework(
        ft.PostProcess(temperature=T, pressure=P),
        parents=new_sims,
        name='PostProcess T={} P={}'.format(T, P)
    )
    return new_sims + [post]


def find_latest_generation(bundle):
    """Find the youngest generation from a bundle

    Parameters
    ----------
    bundle : datreant.Bundle
      bundle of all the simulations for this condition

    Returns
    -------
    youngest : datreant.Bundle
      bundle of the youngest generation from the original bundle
    """
    genwise = bundle.categories.groupby('generation')
    return genwise[max(genwise.keys())]


def group_timeseries(sims):
    """Group together same parallel ids

    Returns
    -------
    dict of {parallel_id: pd.Series}
    """
    timeseries = {}

    for p_id, p_sims in sims.categories.groupby('parallel_id').items():
        # p_sims is many simulations at (T, P, p_id), varying over g
        raw_series = [
            utils.read_csv(tree[RESULTS_FILENAME].abspath)
            for tree in sorted(p_sims,
                               key=lambda x: x.categories['generation'])
        ]
        for i, s in enumerate(raw_series):
            if i == 0:
                # don't have to adjust first series index
                continue
            prev = raw_series[i - 1]
            # ensure that this series index continues from afterwards
            # ie no overlaps
            s.index += prev.index.max() + (prev.index[1] - prev.index[0])

        ts = pd.concat(raw_series)
        ts.name = 'density'
        ts.index.name = 'time'
        timeseries[p_id] = ts

    return timeseries

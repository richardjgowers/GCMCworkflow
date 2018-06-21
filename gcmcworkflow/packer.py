"""
SimFW

Analyse

CheckFlat

"""
import itertools
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import hydraspa as hrsp
import os
import numpy as np

from . import firetasks
from . import grids
from . import utils
from .workflow_creator import (
    process_template,
    make_init_stage,
    make_sampling_point,
)


def kinda_equal(result_a, result_b):
    """Are two results sort of equal?

    Parameters
    ----------
    result_a, result_b : tuple of (mean, std)

    Returns
    -------
    equal : bool
      True if results are within one std of each other
    """
    a, da = result_a
    a_low, a_high = a - da, a + da
    b, db = result_b
    b_low, b_high = b - db, b + db

    return ((b_low < a_high < b_high) or
            (a_low < b_high < a_high))


@xs
class HydraspaCreate(fw.FiretaskBase):
    """Creates simulation template from Hydraspa

    Replaces InitTemplate task
    """
    required_params = ['structure_name']
    optional_params = ['workdir']

    def run_task(self, fw_spec):
        target = self.get('workdir', '')

        # create template using hydraspa
        hrsp.cli_create(
            structure=self['structure_name'],
            gas='Ar',
            forcefield='UFF',
            outdir=target,
        )

        return fw.FWAction(
            update_spec={'template': os.path.join(target, 'template')},
        )


@xs
class CapacityDecider(fw.FiretaskBase):
    required_params = ['fmt', 'workdir']
    optional_params = ['previous_results']

    @staticmethod
    def make_detour(previous, wfname, fmt, template, workdir, simhash):
        # make more simulations at higher pressures
        temperature = max(r[0] for r in previous)
        max_pressure = max(r[1] for r in previous)
        new_pressures = [max_pressure * 2, max_pressure * 4, max_pressure * 8]

        new_sims = []
        new_pps = []

        for P in new_presures:
            runs, pps = make_sampling_point(
                parent_fw=None,
                temperature=temperature,
                pressure=P,
                ncycles=None,
                nparallel=1,
                fmt=fmt,
                wfname=wfname,
                template=template,
                workdir=workdir,
                simple=False,
                simhash=simhash,
            )
            new_sims.extend(runs)
            new_pps.append(pps)

        new_me = fw.Firework(
            [self.__class__(
                fmt=fmt,
                workdir=workdir,
                previous_results=previous,
            )],
            parents=pps,
            spec={
                '_category': wfname,
                'template': template,
                'simhash': simhash,
            },
        )

        return fw.Workflow(new_sims + new_pps + [new_me])

    @staticmethod
    def decide_if_flat(results):
        """Decide if results are flat

        Returns
        -------
        decision : bool
          True if flat
        """
        # tuples of mean and std for each P
        results = [(r[2], r[3]) for r in results]
        # check all pairs of results are "kinda_equal"
        # ie their mean +- std overlap
        return all(kinda_equal(x, y)
                   for x, y in itertools.combinations(results, 2))

    def run_task(self, fw_spec):
        # results are given as (T, P, mean, std, g)
        total_results = (fw_spec['results_array'] +
                         self.get('previous_results', []))

        finished = self.decide_if_flat(fw_spec['results_array'])

        if not finished:
            # issue detour with more pressures
            return fw.FWAction(
                detours=self.make_detour(
                    previous=total_results,
                    wfname=fw_spec['_category'],
                    fmt=self['fmt'],
                    template=fw_spec['template'],
                    workdir=self['workdir'],
                    simhash=fw_spec['simhash'],
                 )
            )
        else:
            # continue to IsothermCreate
            return fw.FWAction(
                update_spec={'results_array': total_results}
            )


def make_capacity_measurement(struc, workdir):
    """Create an entire Isotherm creation Workflow

    Parameters
    ----------
    struc : str
      name of structure to build capacity measurement for
    workdir : str
      where to run simulation

    Returns
    -------
    workflow : fw.Workflow
      Workflow object ready to submit to LaunchPad
    """
    temperatures = [78.0]
    pressures = [10000000, 20000000, 40000000]
    nparallel = 1
    ncycles = 10000

    wfname = struc + '_capacity'
    template = ''
    simfmt = 'raspa'
    # work in directory with name of structure
    workdir = os.path.join(workdir, struc)

    init = fw.Firework(
        [HydraspaCreate(structure_name=struc, workdir=workdir),
         firetasks.CreatePassport(workdir=workdir)],
        spec={
            '_category': wfname,
        },
        name='Template Init',
    )

    gridmake = grids.make_grid_firework(workdir, [init], wfname, template)

    simulation_steps = []  # list of simulation fireworks
    analysis_steps = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition, this_condition_analysis = make_sampling_point(
            parent_fw=gridmake,
            temperature=T,
            pressure=P,
            ncycles=ncycles,
            nparallel=nparallel,
            fmt=simfmt,
            wfname=wfname,
            template=template,
            workdir=workdir,
            simple=False,
            use_grid=True,
        )
        simulation_steps.extend(this_condition)
        analysis_steps.append(this_condition_analysis)

    capacity = fw.Firework(
        [CapacityDecider(fmt=simfmt, workdir=workdir)],
        # pass init to give template in spec
        parents=[init] + analysis_steps,
        spec={
            '_category': wfname,
            'template': template,
        },
        name='Capacity decider',
    )

    iso_create = fw.Firework(
        [firetasks.IsothermCreate(workdir=workdir)],
        parents=[capacity],
        spec={'_category': wfname},
        name='Isotherm create',
    )

    wf = fw.Workflow(
        [init, gridmake] + simulation_steps + analysis_steps + [capacity, iso_create],
        name=wfname,
        metadata={'GCMCWorkflow': True},  # tag as GCMCWorkflow workflow
    )

    return wf

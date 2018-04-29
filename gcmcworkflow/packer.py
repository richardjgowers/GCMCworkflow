"""
SimFW

Analyse

CheckFlat

"""
import itertools
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import numpy as np

from . import firetasks
from . import utils
from .workflow_creator import make_sampling_point


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
        # sort by pressure
        vals = np.array([r[2] for r in results])
        mean = vals.mean()

        # are all values within 5% of the mean?
        return np.abs(((vals - mean) / mean) < 0.05).all()

    def run_rask(self, fw_spec):
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


def make_capacity_measurement(spec):
    """Create an entire Isotherm creation Workflow

    Parameters
    ----------
    spec : dict
      has all the information for workflow

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

    simulation_steps = []  # list of simulation fireworks
    analysis_steps = []  # list of post processing fireworks
    for T, P in itertools.product(temperatures, pressures):
        this_condition, this_condition_analysis = make_sampling_point(
            parent_fw=init,
            temperature=T,
            pressure=P,
            ncycles=ncycles,
            nparallel=nparallel,
            fmt=simfmt,
            wfname=wfname,
            template=template,
            workdir=workdir,
            simple=False,
        )
        simulation_steps.extend(this_condition)
        analysis_steps.append(this_condition_analysis)

    capacity = fw.Firework(
        [CapacityDecider(fmt=simfmt, workdir=workdir)],
        # pass init to give template in spec
        parents=[init] + analysis_steps,
        spec={'_category': wfname},
        name='Capacity decider',
    )

    iso_create = fw.Firework(
        [firetasks.IsothermCreate(workdir=workdir)],
        parents=[capacity],
        spec={'_category': wfname},
        name='Isotherm create',
    )

    wf = fw.Workflow(
        [init] + simulation_steps + analysis_steps + [capacity, iso_create],
        name=wfname,
        metadata={'GCMCWorkflow': True},  # tag as GCMCWorkflow workflow
    )

    return wf

"""
SimFW

PostProcess

CheckFlat

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import numpy as np

from . import firetasks
#from .workflow_creator import make_Simfireworks, make_PostProcess


@xs
class CapacityDecider(fw.FiretaskBase):
    required_params = ['nparallel']
    optional_params = ['previous_results']

    @staticmethod
    def make_detour(nparallel, previous):
        # make more simulations at higher pressures
        temperature = max(r[0] for r in previous)
        max_pressure = max(r[1] for r in previous)
        new_pressures = [max_pressure * 2, max_pressure * 4, max_pressure * 8]

        new_sims = []
        new_pps = []

        for P in new_presures:
            new_sims = [make_Simfireworks(
                parent_fw=None,
                T=temperature, P=P, ncycles=None,
                wfname='Capacity', template=None,
                workdir=None) for P in new_pressures]

            pp = make_PostProcess()

        new_me = fw.Firework(
            self.__class__(nparallel=nparallel, previous_results=previous),
            parents=new_pps,
        )

    @staticmethod
    def decide_if_flat(results):
        """Decide if results are flat

        Returns
        -------
        decision : bool
          True if flat
        """
        # sort by pressure
        results = sorted(results, key=lambda x: x[1])
        vals = np.array([r[2] for r in results[-3:]])
        mean = vals.mean()

        # are all values within 5% of the mean?
        return np.abs(((vals - mean) / mean) < 0.05).all()

    def run_rask(self, fw_spec):
        # results are given as (T, P, mean, std, g)
        results = (fw_spec['results_array'] +
                   self.get('previous_results', []))

        finished = self.decide_if_flat(results)

        if not finished:
            # issue detour with more pressures
            return fw.FWAction(
                detours=self.make_detour(
                    previous=results,
                    nparallel=self['nparallel'],
                )
            )
        else:
            # continue to IsothermCreate
            return fw.FWAction(
                update_spec={'results_array': results}
            )


def make_packing_workflow(spec, simple=True):
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

    flat_decide = fw.Firework(
        CapacityDecider(),
    )

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

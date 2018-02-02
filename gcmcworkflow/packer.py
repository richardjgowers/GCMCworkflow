"""
SimFW

PostProcess

CheckFlat

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import numpy as np

from . import firetasks as ft


@xs
class CapacityDecider(fw.FiretaskBase):
    @staticmethod
    def make_detour(results):
        # make more simulations at higher pressures
        return

    @staticmethod
    def decide_if_flat(results):
        """Decide if results are flat

        Returns
        -------
        decision : bool
          True if flat
        """
        Pvals = np.array([r[2] for r in results[-3:]])
        Pmean = Pvals.mean()

        # are all values within 5% of the mean?
        return np.abs(((Pvals - Pmean) / Pmean) < 0.05).all()

    def run_rask(self, fw_spec):
        # results are given as (T, P, mean, std, g)
        results = sorted(fw_spec['results_array'], key=lambda x: (x[0], x[1]))

        finished = self.decide_if_flat(results)

        if not finished:
            # issue detour with more pressures
            return fw.FWAction(
                detours=[]
            )
        else:
            # continue to IsothermCreate
            return fw.FWAction()

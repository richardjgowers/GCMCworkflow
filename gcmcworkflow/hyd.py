# hydraspa interface things
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import hydraspa as hrsp
import os


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

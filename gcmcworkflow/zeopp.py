"""Firetasks for running ZeoPP calculations


"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import glob
import os
import subprocess


@xs
class PrepareStructure(fw.FiretaskBase):
    # copies the structure onto the work directory
    # prequisite for any future ZeoPP calculation
    required_params = ['structure', 'name', 'workdir']

    def run_task(self, fw_spec):
        newdir = os.path.join(self['workdir'], self['name'])
        os.mkdir(newdir)
        with open(os.path.join(newdir, self['name'] + '.cif'), 'w') as out:
            out.write(self['structure'])

        return fw.FWAction(update_spec={'structure_dir': newdir})


ZEO_PP_COMMANDS = {
    'pore_diameter': 'network -ha -res {filename}',
}

@xs
class ZeoPP(fw.FiretaskBase):
    # need to pass list of requested calculations
    required_params = ['calculations']

    def run_task(self, fw_spec):
        old_dir = os.getcwd()
        os.chdir(fw_spec['structure_dir'])

        fn = glob.glob('*.cif')[0]

        try:
            for calc in self['calculations']:
                p = subprocess.run(
                    ZEO_PP_COMMANDS[calc].format(filename=fn),
                    check=True, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
        except subprocess.CalledProcessError as e:
            # CPE has following attributes:
            # - returncode
            # - cmd
            # - stdout
            # - stderr
            raise ValueError("{} failed with errorcode '{}' and stderr '{}'"
                             "".format(calc, e.returncode, e.stderr))
        finally:
            os.chdir(old_dir)

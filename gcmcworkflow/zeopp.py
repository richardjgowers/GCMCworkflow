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
    'channel_identification': 'network -ha -chan {radius} {filename}',
    'surface_area': 'network -ha -sa {radius} {radius} 2000 {filename}',
    'accessible_volume': 'network -ha -vol {radius} {radius} 50000 {filename}',
    'probe_volume': 'network -ha -volpo {radius} {radius} 50000 {filename}',
    'psd': 'network -ha -psd {radius} {radius} 50000 {filename}',
    'raytrace': 'network -ha -ray_atom {radius} {radius} 50000 {filename}',
    'vmd_grid': 'network -ha -gridG {filename}',
    'structure_analysis': 'network -ha -strinfo {filename}',
    'oms_count': 'network -ha -oms {filename}',
}


@xs
class ZeoPP(fw.FiretaskBase):
    # need to pass list of requested calculations
    required_params = ['calculations']
    optional_params = ['radius']

    def run_task(self, fw_spec):
        old_dir = os.getcwd()
        os.chdir(fw_spec['structure_dir'])

        fn = glob.glob('*.cif')[0]
        rad = self.get('radius', 1.2)

        try:
            for calc in self['calculations']:
                p = subprocess.run(
                    ZEO_PP_COMMANDS[calc].format(filename=fn, radius=rad),
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

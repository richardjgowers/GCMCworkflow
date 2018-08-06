"""Stuff for handling energy grids

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import glob
import os
import shutil
import subprocess

from . import raspatools


@xs
class PrepareGridInput(fw.FiretaskBase):
    required_params = ['workdir']

    def grid_exists(self, fw_spec):
        """See if a grid is required

        Make simple simulation, try and run it, check output
        """
        newdir = os.path.join(self['workdir'], 'gridtest')
        if os.path.exists(newdir):
            shutil.rmtree(newdir)
        shutil.copytree(fw_spec['template'], newdir)
        raspatools.update_input(newdir, T=1.0, P=1.0, ncycles=10, use_grid=True)
        old_dir = os.getcwd()
        os.chdir(newdir)
        subprocess.run('simulate simulation.input',
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        os.chdir(old_dir)
        try:
            raspatools.check_exit(newdir)
        except ValueError:
            return False
        else:
            return True

    def create_grid_input(self, fw_spec):
        # copy the template to its own directory
        newdir = os.path.join(self['workdir'], 'gridmake')
        # delete if already existing
        if os.path.exists(newdir):
            shutil.rmtree(newdir)
        shutil.copytree(fw_spec['template'], newdir)

        gastypes = raspatools.determine_gastypes(newdir)

        # rewrite simulation.input completely
        # which keys in input file to keep from original
        to_keep = (
            'Forcefield',
            'CutOffVDW',
            'ChargeMethod',
            'CutOffChargeCharge',
            'EwaldPrecision',
            'UseChargesFromCIFFile',
            'Framework',
            'FrameworkName',
            'UnitCells',
        )
        simfile = os.path.join(newdir, 'simulation.input')
        os.rename(simfile, simfile + '.bak')
        with open(simfile, 'w') as fout, open(simfile + '.bak', 'r') as fin:
            # Redefine simulation type
            fout.write('SimulationType MakeGrid\n')
            fout.write('\n')
            for line in fin:
                # Go through old file and keep selected lines
                if line.rstrip().startswith(to_keep):
                    fout.write(line)
            # Then add the lines for making grids
            fout.write('\n')
            fout.write('SpacingVDWGrid 0.1\n')
            fout.write('SpacingCoulombGrid 0.1\n')
            fout.write('NumberOfGrids {}\n'.format(len(gastypes)))
            fout.write('GridTypes     {}\n'.format(' '.join(gastypes)))

        return os.path.abspath(newdir)

    def run_gridmake(self, location):
        old_dir = os.getcwd()
        os.chdir(location)
        p = subprocess.run('simulate simulation.input',
                       check=True,
                       shell=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        os.chdir(old_dir)
        with open('stdout', 'wb') as outf:
            outf.write(p.stdout)
        with open('stderr', 'wb') as outf:
            outf.write(p.stderr)

    def run_task(self, fw_spec):
        if not self.grid_exists(fw_spec):
            target = self.create_grid_input(fw_spec)
            self.run_gridmake(target)


@xs
class RmGrid(fw.FiretaskBase):
    # at end of workflow, get rid of grid to save space
    required_params = ['raspa_dir', 'structure_name']

    def run_task(self, fw_spec):
        grid_dir = os.path.join(self['raspa_dir'], 'share', 'raspa', 'grids')

        targets = glob.glob(os.path.join(grid_dir, '*', self['structure_name'] + '*'))

        for t in targets:
            shutil.rmtree(t)


def make_grid_firework(workdir, parents, wfname, template):
    """Create Firework which prepares grid

    Parameters
    ----------
    workdir : str
      where to run the grid making
    parents : list
      references to previous Fireworks in Workflow
    wfname : str
      unique name for Workflow
    template : str or dict
      either path to template or dict of contents

    Returns
    -------
    gridmake : fw.Firework
    """
    return fw.Firework(
        [PrepareGridInput(workdir=workdir)],
        parents=parents,
        spec={
            '_category': wfname,
            'template': template,
        },
        name='Grid Make',
    )

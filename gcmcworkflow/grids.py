"""Stuff for handling energy grids

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import os
import shutil

from . import firetasks
from . import raspatools


@xs
class PrepareGridInput(fw.FiretaskBase):
    required_params = ['workdir']

    def run_task(self, fw_spec):
        # copy the template to its own directory
        newdir = os.path.join(self['workdir'], 'gridmake')
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

        return fw.FWAction(
            update_spec={
                'simtree': os.path.abspath(newdir),
                'template': fw_spec['template'],
                'simhash': fw_spec['simhash'],
        })


@xs
class DestroyGrid(fw.FiretaskBase):
    # at end of workflow, get rid of grid to save space
    def run_task(self, fw_spec):
        # figure out where Raspa is installed
        # find appropriate grid(s)
        pass

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
        [PrepareGridInput(workdir=workdir),
         firetasks.RunSimulation(fmt='raspa')],
        parents=parents,
        spec={
            '_category': wfname,
            'template': template,
        },
        name='Grid Make',
    )

"""Functions for working with raspa simulations


"""
import os
import re
import random

from hydraspa.gather import parse_results
from hydraspa.util import is_finished

from . import utils


def check_exit(tree):
    """Check

    Returns
    -------
    True/False if simulation starteed but did/didn't finish

    Raises
    ------
    ValueError
      if simulation didn't start
    """
    ret_code = is_finished(tree)

    if ret_code == 2:
        raise ValueError("Output not created")
    elif ret_code == 1:
        return False
    else:
        return True


def update_input(treant, T, P, ncycles, use_grid=False):
    """Update the simulation input for a given treant

    If any parameters are None, the value present in the input file is not altered.

    Parameters
    ----------
    treant : str
      the simulation directory to work on
    T : float
      temperature to simulate
    P : float
      pressure to simulate
    ncycles : int
      number of cycles to simulate (in this run)
    """
    simfile = os.path.join(treant, 'simulation.input')
    # make backup of old input for debugging purposes
    os.rename(simfile, simfile + '.bak')

    seeded = False
    seedline = 'RandomSeed {}\n'.format(random.randint(1, 1e6))
    # which lines we shouldn't blindly copy over
    forbidden = (
        'UseTabularGrid',
        'SpacingVDWGrid',
        'SpacingCoulombGrid',
        'NumberOfGrids',
        'GridTypes',
    )

    with open(simfile, 'w') as newfile, open(simfile + '.bak', 'r') as oldfile:
        for line in oldfile:
            if re.match(r'^\s*(?:RandomSeed)', line):
                seeded = True
                line = seedline
            elif 'ExternalPressure' in line:
                line = "ExternalPressure {}\n".format(P)
            elif 'ExternalTemperature' in line:
                line = "ExternalTemperature {}\n".format(T)
            elif 'NumberOfCycles' in line:
                line = "NumberOfCycles {}\n".format(ncycles)
            if not line.lstrip().startswith(forbidden):
                newfile.write(line)
        if not seeded:
            newfile.write(seedline)
        if use_grid:
            gastypes = determine_gastypes(treant)

            newfile.write('\n')
            newfile.write('UseTabularGrid     yes\n')
            newfile.write('SpacingVDWGrid     0.1\n')
            newfile.write('SpacingCoulombGrid 0.1\n')
            newfile.write('NumberOfGrids      {}\n'.format(len(gastypes)))
            newfile.write('GridTypes          {}\n'.format(' '.join(gastypes)))


def set_restart(simtree):
    """Set a simulation input to be a restart"""
    simfile = os.path.join(simtree, 'simulation.input')

    os.rename(simfile, simfile + '.bak')
    with open(simfile, 'w') as newfile, open(simfile + '.bak', 'r') as oldfile:
        for line in oldfile:
            if 'RestartFile' in line:
                line = 'RestartFile yes\n'
            newfile.write(line)


def determine_gastypes(simdir):
    """Determine all atom types in gas species

    Parameters
    ----------
    simdir : str
      where the simulation lives, will look for 'pseudo_atoms.def'

    Returns
    -------
    gastype : list of str
    """
    with open(os.path.join(simdir, 'pseudo_atoms.def'), 'r') as f:
        f.readline()
        ntypes = int(f.readline().strip())
        f.readline()
        types = [f.readline().split()[0] for _ in range(ntypes)]
    return [t for t in types if not t == 'UNIT']


def parse_ncycles(simdir):
    """Grab ncycles from simulation.input in simdir"""
    with open(os.path.join(simdir, 'simulation.input'), 'r') as f:
        for line in f:
            mat = re.search(r'\s*(?:NumberOfCycles)\s*(\d+)', line)

            if mat is not None:
                break
        else:
            raise ValueError("Couldn't deduce NCycles")

    return int(mat.groups()[0])


def calc_remainder(simdir):
    """Calculate the number of additional cycles required for this simulation"""
    results = parse_results(simdir)

    nreq = parse_ncycles(simdir)

    last_index = results.index.max()

    return nreq - last_index

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


def update_input(treant, T, P, ncycles):
    """Update the simulation input for a given treant

    If any parameters are None, the value present in the input file is not altered.

    Parameters
    ----------
    treant : str
      the simulation directory to work on
    T : float or None
      temperature to simulate
    P : float or None
      pressure to simulate
    ncycles : int or None
      number of cycles to simulate (in this run)
    """
    simfile = os.path.join(treant, 'simulation.input')
    # make backup of old input for debugging purposes
    os.rename(simfile, simfile + '.bak')

    seeded = False
    seedline = 'RandomSeed {}\n'.format(random.randint(1, 1e6))

    with open(simfile, 'w') as newfile, open(simfile + '.bak', 'r') as oldfile:
        for line in oldfile:
            if re.match(r'^\s*(?:RandomSeed)', line):
                seeded = True
                line = seedline
            elif ('ExternalPressure' in line) and (P is not None):
                line = "ExternalPressure {}\n".format(P)
            elif ('ExternalTemperature' in line) and (T is not None):
                line = "ExternalTemperature {}\n".format(T)
            elif ('NumberOfCycles' in line) and (ncycles is not None):
                line = "NumberOfCycles {}\n".format(ncycles)
            newfile.write(line)
        if not seeded:
            newfile.write(seedline)


def set_restart(simtree):
    """Set a simulation input to be a restart"""
    simfile = os.path.join(simtree, 'simulation.input')

    os.rename(simfile, simfile + '.bak')
    with open(simfile, 'w') as newfile, open(simfile + '.bak', 'r') as oldfile:
        for line in oldfile:
            if 'RestartFile' in line:
                line = 'RestartFile yes\n'
            newfile.write(line)


def calc_remainder(simdir):
    """Calculate the number of additional cycles required for this simulation"""
    results = parse_results(simdir)

    last_index = results.index.max()

    with open(os.path.join(simdir, 'simulation.input'), 'r') as f:
        for line in f:
            mat = re.search(r'\s*(?:NumberOfCycles)\s*(\d+)', line)

            if mat is not None:
                break
        else:
            raise ValueError("Couldn't deduce NCycles")

    nreq = int(mat.groups()[0])

    return nreq - last_index

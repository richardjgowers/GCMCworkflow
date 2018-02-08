"""Functions for working with raspa simulations


"""
import glob
import numpy as np
import os
import pandas as pd
import re
import random

from . import utils

# Regex patterns to grab stuff from Raspa output
# grabs the integer values before and after 'out of'
# eg '20 out of 200' -> (20, 200)
CYCLE_PAT = re.compile(r'^[C].+?(\d+)(?: out of )(\d+)')
# grab the integer molecules of Component 0
# eg 'Component 0 ... 150/0/0' -> (150,)
NABS_PAT = re.compile(r'(?:Component 0).+?(?:(\d+)\/\d\/\d)')

# matches the instantaneous mol/kg on this line:              vvvvvvvvvvvv
# absolute adsorption:   0.00000 (avg.   0.00000) [mol/uc],   0.0000000000 (avg.   0.0000000000) [mol/kg],   0.0000000000 (avg.   0.0000000000) [mg/g]
MMOL_PAT = re.compile(r'^(?:\s+absolute adsorption:).+?(\d+\.\d+)(?=\s+\(avg\.\s+\d+\.\d+\)\s+\[mol\/kg\])')


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
    # check it exists
    try:
        outfile = glob.glob(os.path.join(tree, 'Output/System_0/*.data'))[0]
    except IndexError:
        # if the glob couldn't be sliced...
        raise ValueError("Output not created")

    # check last 10 lines of file for this
    if not b'Simulation finished' in utils.tail(outfile, 10):
        #raise ValueError("Output did not exit correctly")
        return False

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


def parse_results(tree):
    """Parse results from a Raspa simulation, returns absolute mol/kg

    Ignores all values from [Init] period. Simulations shouldn't be using
    this option anyway, as we're dealing with equilibration ourselves.

    Parameters
    ----------
    tree: str
      path where the simulation took place

    Returns
    -------
    results : pandas.Series
      absolute loadings in mol/kg
    """
    # return pandas series of the results
    outfile = glob.glob(os.path.join(tree, 'Output/System_0/*.data'))[0]

    cycles = []
    values = []

    with open(outfile, 'r') as inf:
        for line in inf:
            cmat = re.search(CYCLE_PAT, line)
            if cmat:
                cycles.append(cmat.groups()[0])
                continue
            lmat = re.search(MMOL_PAT, line)
            if lmat:
                values.append(lmat.groups()[0])

    cycles = np.array(cycles, dtype=np.int)
    values = np.array(values, dtype=np.float32)

    df = pd.Series(values, index=cycles)
    df.name = 'density'
    df.index.name = 'time'

    return df

def parse_results_simple(tree):
    outfile = glob.glob(os.path.join(tree, 'Output/System_0/*.data'))[0]

    wantval = False
    with open(outfile, 'r') as inf:
        for line in inf:
            if wantval and line.lstrip('\t').startswith(
                    'Average loading absolute [molecules/unit cell]'):
                line = line.split(']')[1]
                line = line.split('+')[0]
                val = float(line)
                break
            if line.startswith('Number of molecules:'):
                wantval = True
    return val


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

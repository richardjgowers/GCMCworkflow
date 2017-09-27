"""Functions for working with raspa simulations


"""
import glob
import numpy as np
import os
import pandas as pd
import re

from . import utils

# Regex patterns to grab stuff from Raspa output
# grabs the integer values before and after 'out of'
# eg '20 out of 200' -> (20, 200)
CYCLE_PAT = re.compile(r'^[C].+?(\d+)(?: out of )(\d+)')
# grab the integer molecules of Component 0
# eg 'Component 0 ... 150/0/0' -> (150,)
NABS_PAT = re.compile(r'(?:Component 0).+?(?:(\d+)\/\d\/\d)')


def check_exit(tree):
    # check it exists
    try:
        outfile = glob.glob(os.path.join(tree, 'Output/System_0/*.data'))[0]
    except IndexError:
        # if the glob couldn't be sliced...
        raise ValueError("Output not created")

    # check last 10 lines of file for this
    if not b'Simulation finished' in utils.tail(outfile, 10):
        raise ValueError("Output did not exit correctly")

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
    with open(simfile, 'w') as newfile, open(simfile + '.bak', 'r') as oldfile:
        for line in oldfile:
            if ('ExternalPressure' in line) and (P is not None):
                line = "ExternalPressure {}\n".format(P)
            elif ('ExternalTemperature' in line) and (T is not None):
                line = "ExternalTemperature {}\n".format(T)
            elif ('NumberOfCycles' in line) and (ncycles is not None):
                line = "NumberOfCycles {}\n".format(ncycles)
            newfile.write(line)


def parse_results(tree):
    """Parse results from a Raspa treant

    Ignores all values from [Init] period. Simulations shouldn't be using
    this option anyway, as we're dealing with equilibration ourselves.

    Parameters
    ----------
    tree: str
      path where the simulation took place

    Returns
    -------
    results : pandas.Series
    """
    # return pandas series of the results
    outfile = glob.glob(os.path.join(tree, 'Output/System_0/*.data'))[0]

    cycles = []
    values = []
    # flip/flop between trying to parse a cycle number
    # necessary because there are more cycle number labels than nabs lines
    want_cycle = True
    with open(outfile, 'r') as inf:
        for line in inf:
            if want_cycle:
                m = re.match(CYCLE_PAT, line)
                if m is not None:
                    cycles.append(m.groups()[0])
                    want_cycle = False
            else:
                m = re.match(NABS_PAT, line)
                if m is not None:
                    values.append(m.groups()[0])
                    want_cycle = True

    cycles = np.array(cycles, dtype=np.int)
    values = np.array(values, dtype=np.int)

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

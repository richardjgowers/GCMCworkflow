from collections import namedtuple
import dill
import glob
import io
import numpy as np
import os
import pandas as pd
import re
import subprocess


def guess_format(stuff):
    """Guess the format of a slurped up input

    Parameters
    ----------
    stuff : dict
    """
    if any(re.match('.*?simulation\.input.*?', fn) for fn in stuff):
        return 'raspa'
    else:
        raise ValueError("Unknown template format")


NAME_PATTERN = re.compile('^Sim')
SIM_GRAB = re.compile('^Sim T=(\d+\.\d+) P=(\d+\.\d+) v(\d+)')
def gen_name(T, P, idx):
    """Generate a name for an individual simulation

    T - temperature
    P - pressure
    idx - parallel id
    """
    name = "Sim "
    if T is not None:
        name += "T={} ".format(T)
    if P is not None:
        name += "P={}".format(P)
    name += " v{}".format(idx)
    return name


# little namespace for holding parsed simpaths
SimPath = namedtuple('SimPath', 'path,simhash,T,P,gen_id,parallel_id')

SIM_PATH_PATTERN = re.compile(
    r'sim_(.{7})?_T(\d+\.?\d*)_P(\d+\.?\d*)_gen(\d+)_v(\d+)')
def gen_sim_path(simhash, T, P, gen_id, p_id):
    """Generate a path name for a simulation

    Parameters
    ----------
    simhash : str
      7 digit hash of the simulation (or '')
    T, P : float
      temperature and pressure
    gen_id : int
      generation id, iteration number of simulation
    p_id : int
      parallel id, index within a particular generation

    Returns
    -------
    path : str
    """
    return 'sim_{hash}_T{t}_P{p}_gen{g}_v{i}'.format(
        hash=simhash, t=T, p=P, g=gen_id, i=p_id
    )


def parse_sim_path(path):
    """Parse a simulation path name

    Returns
    -------
    simhash, temperature, pressure, generation, parallel_id
    """
    match = re.search(SIM_PATH_PATTERN, path)

    simhash, T, P, gen, par = match.groups()
    if simhash is None:
        simhash = ''

    return SimPath(path, simhash, float(T), float(P), int(gen), int(par))


def find_last_generation(workdir, simhash, T, P, p_id):
    """Find the index of the last generation run"""
    simdirs = glob.glob(os.path.join(workdir, gen_sim_path(simhash, T, P, '*', p_id)))

    gens = (parse_sim_path(s).gen_id for s in simdirs)

    try:
        return max(gens)
    except ValueError:
        return 0


def tail(fn, n):
    """Similar to 'tail -n *n* *fn*'

    Parameters
    ----------
    fn : str
      Path to file to tail
    n : int
      Number of lines to return

    Returns
    -------
    A bytes string representing the output.  Use ``.split()`` to get lines.
    """
    p = subprocess.Popen(['tail', '-n', str(n), fn],
                         stdout=subprocess.PIPE)
    p.wait()  # allow subprocess to finish
    stdout, stderr = p.communicate()

    return stdout


def save_csv(data, path):
    """Save a Series to a csv file

    Parameters
    ----------
    data : pandas.Series
      Series of results.  Assumed to have time as this index, with arbitrary other columns
    path : str
    """
    # label the index to be time
    data.index.name = 'time'

    data.to_csv(path, header=True)


def read_csv(path):
    """Read a csv into a Series

    Parameters
    ----------
    path : str

    Returns
    -------
    results : pandas.Series
      data from csv file with the time column as the index
    """
    df = pd.read_csv(path, comment='#')
    df = df.set_index('time')
    return df.squeeze()  # converts to a Series


def slurp_directory(path):
    """Slurp up contents of directory into dict

    Opposite of dump_directory

    Returns
    -------
    dict of {filename: content}
    """
    data = {}

    for root, subdir, filenames in os.walk(path):
        for fn in filenames:
            with open(os.path.join(root, fn), 'r') as fh:
                data[fn] = fh.read()
    return data


def escape_template(template):
    """Remove dots from filenames in template

    Parameters
    ----------
    template : dict

    Returns
    -------
    escaped_template : dict
    """
    return {k.replace('.', '*'): v for k, v in template.items()}


def dump_directory(template_dir, stuff):
    """Spit out contents of directory

    Opposite of slurp_directory

    Parameters
    ----------
    template_dir : str
      path to write contents of stuff to
    stuff : dict
      dictionary of filename: contents

    Returns
    -------
    path : str
      absolute path to the written template
    """
    os.mkdir(template_dir)
    for filepath, contents in stuff.items():
        filepath = filepath.replace('*', '.')
        with open(os.path.join(template_dir, filepath), 'w',
                  newline='\n', encoding='utf8') as outfile:
            outfile.write(contents.replace('\r\n', '\n'))
    return os.path.abspath(template_dir)


def pickle_func(func):
    """Serialise a Python function

    The function must contain all imports within it

    Reciprocal function to unpickle_func

    Returns
    -------
    pickled : str
      Pickled version of the function
    """
    return str(dill.dumps(func), 'raw_unicode_escape')


def unpickle_func(picklestr):
    """Convert a pickled function back to a function

    Reciprocal function to pickle_func

    Returns
    -------
    func : function
      callable version of the function
    """
    return dill.loads(bytes(picklestr, 'raw_unicode_escape'))


def make_series(ts):
    """Convert ascii representation of series to Pandas Series"""
    return pd.read_csv(
        io.StringIO(ts),
        header=None,
        index_col=0,
        squeeze=True,
    )


def conv_to_number(val):
    """Convert a string to a float value

    Can apply either a k (thousand) or M (million) multiplier prefix

    Parameter
    ---------
    val : str
      String representing the number(s)

    Returns
    -------
    value : float
      float value representation

    Examples
    --------
    '50'   -> 50.0
    '100k' -> 100,000.0
    '5.6M' -> 5,600,000.0
    """
    if str(val)[-1].isalpha():
        val, suffix = val[:-1], val[-1]
        try:
            multi = {'k': 1e3, 'M':1e6}[suffix]
        except KeyError:
            raise ValueError("Unrecognised suffix {}".format(suffix))
    else:
        multi = 1

    return float(val) * multi


# 3 numbers, comma separated, whitespace allowed
# first 2 floats with optional suffix, start and end of range
# last integer, number of values in range
RANGE_PAT = re.compile(r'\w{8}'  # adaptive/linspace/logspace
                       '\(\s*(\d*\.?\d*\w?)\s*,\s*'  # float with suffix
                       '(\d*\.?\d*\w?)\s*,\s*'  # float with suffix
                       '(\d+)\s*\)'  # integer
)


def logspace(start, stop, number):
    """logspace that works like np.linspace"""
    p1 = np.log10(start)
    p2 = np.log10(stop)
    return np.logspace(p1, p2, num=number, endpoint=True)

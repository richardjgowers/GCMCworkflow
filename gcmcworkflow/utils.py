import dill
import io
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


def gen_name(T, P, idx):
    """Generate a name for an individual simulation

    T - temperature
    P - pressure
    idx - parallel id
    """
    name = ""
    if T is not None:
        name += "T={} ".format(T)
    if P is not None:
        name += "P={}".format(P)
    name += " v{}".format(idx)
    return name

def gen_sim_path(T, P, gen_id, p_id):
    """Generate a path name for a simulation

    Parameters
    ----------
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
    return 'sim_{t}_{p}_gen{g}_v{i}'.format(
        t=T, p=P, g=gen_id, i=p_id
    )

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
    df = pd.read_csv(path)
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

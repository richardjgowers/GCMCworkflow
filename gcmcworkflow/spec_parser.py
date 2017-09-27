import yaml
import os


def read_spec(path):
    """Read a spec file, return a dict of what it means

    output dict:
    {
    template: absolute path to template to use
    name: name of workflow
    pressures: list of pressures as floats, or [None]
    temperatures: list of temps as floats, or [None]
    ncycles: int of ncycles or None
    nparallel: int or 1
    }
    """
    with open(path, 'r') as inf:
        raw = yaml.load(inf)
    # convert all fields to correct types
    # if not present, replace with ``None``
    output = {}
    output['template'] = os.path.abspath(raw['template'])
    try:
        output['name'] = raw['name']
    except KeyError:
        output['name'] = 'GCMCWorkflow'
    try:
        output['pressures'] = [float(v) for v in  raw['pressures']]
    except KeyError:
        output['pressures'] = [None]
    try:
        output['temperatures'] = [float(v) for v in raw['temperatures']]
    except KeyError:
        output['temperatures'] = [None]
    try:
        output['nparallel'] = int(raw['nparallel'])
    except KeyError:
        output['nparallel'] = 1
    try:
        output['ncycles'] = int(raw['ncycles'])
    except KeyError:
        output['ncycles'] = None

    return output


def read_lpad_spec(path):
    """Read a launchpad spec file

    Parameters
    ----------
    path : str
      path to the yaml file

    Returns
    -------
    out : dict
      dict of the yaml
    """
    with open(path, 'r') as inf:
        raw = yaml.load(inf)

    return raw

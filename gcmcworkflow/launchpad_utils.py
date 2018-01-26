# functions for querying the launchpad
from collections import defaultdict
import fireworks as fw
import re
import yaml

from .utils import NAME_PATTERN, SIM_GRAB


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


def get_lpad(spec=None):
    """Get a LaunchPad

    Parameters
    ----------
    spec : dict, optional
      options for launchpad

    Returns
    -------
    lpad : fw.LaunchPad
    """
    if spec:
        lpad_spec = read_lpad_spec(spec)
    else:
        lpad_spec = dict()

    return fw.LaunchPad(**lpad_spec)


def submit_workflow(workflow, lp=None, lpspec=None):
    """Add a Workflow to LaunchPad, checking for duplicate names"""
    if lp is None:
        lp = get_lpad(lpspec)

    if not workflow.name in get_workflow_names(lp):
        lp.add_wf(workflow)
    else:
        raise ValueError("Duplicate workflow name")


def get_workflow_names(lp=None, lpspec=None):
    """Return list of defined wf names"""
    if lp is None:
        lp = get_lpad(lpspec)

    wfs = lp.workflows.find({'metadata': {'GCMCWorkflow': True}},
                            {'name': True})  # retrieve only names

    return [entry['name'] for entry in wfs]


def get_workflow(wfname, lp=None, lpspec=None):
    """Retrieve a given GCMCWorkflow"""
    if lp is None:
        lp = get_lpad(lpspec)

    return lp.workflows.find_one({'metadata': {'GCMCWorkflow': True},
                                  'name': wfname})


def get_workflow_report(wfname, lp=None, lpspec=None):
    if lp is None:
        lp = get_lpad(lpspec)

    wf = get_workflow(wfname, lp)

    # make report for check cli
    # grab sim fireworks from this workflow
    sims = lp.fireworks.find(
        {'fw_id': {'$in': wf['nodes']}, 'name': NAME_PATTERN},
        {'name': True, 'state': True},  # only name and state required
    )

    status = defaultdict(list)

    for sim in sims:
        T, P, v = re.match(SIM_GRAB, sim['name']).groups()
        status[T, P].append(sim['state'])

    return status

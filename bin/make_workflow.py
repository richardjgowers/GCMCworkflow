#!/usr/bin/env python
"""Create a GCMC workflow and stage it on launchpad

``genspec`` creates an empty specfile to fill out

``submit``  adds a Workflow to the launchpad

specfile defines the dimensions of the GCMC sampling to perform.
lpspec defines the parameters for the job database, without this
the workflow will be submitted to the mongodb on localhost.

To execute the workflow once created, use ``rlaunch``

Usage:
  make_workflow.py genspec
  make_workflow.py submit <specfile> [-l <lpspec>] [--simple]

Options:
  -h --help
  -v --version
  -l --launchpad  Launchpad yaml file (job database)
"""
import docopt
import fireworks as fw
import sys

import gcmcworkflow as gcwf


if __name__ == '__main__':
    args = docopt.docopt(__doc__, version=gcwf.__version__)

    if args['genspec']:
        gcwf.spec_parser.generate_spec()
    elif args['submit']:
        specs = gcwf.read_spec(args['<specfile>'])
        wf = gcwf.make_workflow(specs, simple=args['--simple'])

        if args['--launchpad']:
            lpad_spec = gcwf.read_lpad_spec(args['<lpspec>'])
        else:
            # defaults to localhost
            lpad_spec = dict()
        lp = fw.LaunchPad(**lpad_spec)
        lp.add_wf(wf)

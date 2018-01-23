"""Fireworks for running Poreblazer

Requires 'poreblazer.exe' available in path (conda package available).
"""
#import datreant.core as dtr
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import os
import subprocess
# screening package
from hydraspa import poreblazer as pb


@xs
class PoreblazerTask(fw.FiretaskBase):
    # run poreblazer on input

    # workdir - where to store output
    # name - structure name from hydraspa to operate on
    required_params = ['workdir', 'structure_name']

    @staticmethod
    def run_poreblazer():
        try:
            p = subprocess.run(
                'poreblazer.exe < input.dat',
                check=True,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            raise ValueError("Poreblazer failed with errorcode: '{}' "
                             "and stderr: '{}'".format(
                                 e.returncode, e.stderr))
        with open('stdout.txt', 'wb') as out:
            out.write(p.stdout)
        with open('stderr.txt', 'wb') as out:
            out.write(p.stderr)

    def create_datreant_record(self, name):
        t = dtr.Treant('.')
        t.tags.add('poreblazer')
        t.categories['structure'] = name

    def run_task(self, fw_spec):
        # jump to correct location
        os.chdir(self['workdir'])
        # make directory for *this* structure
        os.makedirs(self['structure_name'])
        os.chdir(self['structure_name'])

        pb.create_input(self['structure_name'])

        self.run_poreblazer()

        self.create_datreant_record(self['structure_name'])

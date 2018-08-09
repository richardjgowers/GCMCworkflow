import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import os
import shutil
import time


@xs
class RmDir(fw.FiretaskBase):
    """Delete contents in *target"""
    required_params = ['target', 'ignore_errors']

    def run_task(self, fw_spec):
        shutil.rmtree(self['target'], ignore_errors=self['ignore_errors'])


@xs
class ZipDir(fw.FiretaskBase):
    """Zip contents of *src* into directory *dst*"""
    required_params = ['src', 'dst']

    def run_task(self, fw_spec):
        shutil.make_archive(self['dst'], 'zip', self['src'])


@xs
class FailTask(fw.FiretaskBase):
    def run_task(self, fw_spec):
        raise ValueError

@xs
class NothingTask(fw.FiretaskBase):
    def run_task(self, fw_spec):
        return None

@xs
class WaitTask(fw.FiretaskBase):
    required_params = ['duration']

    def run_task(self, fw_spec):
        time.sleep(self['duration'])

"""Firetasks for running ZeoPP calculations


"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs


@xs
class ZeoPPVolume(fw.FiretaskBase):
    def run_task(self, fw_spec):
        pass

from functools import partial
import glob
import os
import pytest
import fireworks as fw

import gcmcworkflow as gcwf


@pytest.fixture
def RASPA_FILES():
    return ['CO2.def', 'force_field.def', 'framework.def',
            'IRMOF-1.cif', 'pseudo_atoms.def', 'simulation.input']


@pytest.fixture
def InitTempFW(sample_input):
    firework = fw.Firework(
        gcwf.firetasks.InitTemplate(
            contents=gcwf.utils.slurp_directory('template')),
        spec={"workdir": ".",
              "name":"Template init test"}
    )
    return firework

@pytest.fixture
def LaunchedInitTempFW(InitTempFW, launchpad):
    launchpad(fw.Workflow([InitTempFW]))
    return


class TestTemplateInit(object):
    def test_template_creation(self, LaunchedInitTempFW, RASPA_FILES):
        for f in RASPA_FILES:
            assert os.path.exists(os.path.join('template', f))


class TestTemplateCopy(object):
    DEFAULT_TEMPERATURE = 208.0
    DEFAULT_PRESSURE = 50.0
    DEFAULT_NCYCLES = 1000

    @staticmethod
    @pytest.fixture
    def copytemplate(sample_input, launchpad):
        cp1 = fw.Firework(
            gcwf.firetasks.CopyTemplate(temperature=10, pressure=20,
                                        ncycles=1234, parallel_id=1,
                                        fmt='raspa'),
            spec={
                'template': os.path.join(sample_input, 'template'),
                'generation': 1,
            }
        )
        wf = fw.Workflow([cp1])
        launchpad(wf)
        print(os.listdir())
        return glob.glob('sim_*')[0]

    @staticmethod
    def get_field(t, key):
        # return the value after *key* in the simulation input
        with open(os.path.join(t, 'simulation.input'), 'r') as fin:
            for line in fin:
                if key in line:
                    val = line.split()[1]
        return val

    def get_pressure(self, t):
        return float(self.get_field(t, 'ExternalPressure'))

    def get_temperature(self, t):
        return float(self.get_field(t, 'ExternalTemperature'))

    def get_ncycles(self, t):
        return int(self.get_field(t, 'NumberOfCycles'))

    def test_template_copy(self, copytemplate, RASPA_FILES):
        for f in RASPA_FILES:
            assert os.path.exists(os.path.join(copytemplate, f))

    def test_template_pressure(self, copytemplate):
        assert self.get_pressure(copytemplate) == 20

    def test_template_temperature(self, copytemplate):
        assert self.get_temperature(copytemplate) == 10

    def test_template_ncycles(self, copytemplate):
        assert self.get_ncycles(copytemplate) == 1234


@pytest.fixture
def run_raspa(short_raspa, launchpad):
    job = fw.Firework([gcwf.firetasks.RunSimulation(fmt='raspa')],
                       spec={'simtree': short_raspa})
    launchpad(fw.Workflow([job]))

class TestSimulationRun(object):
    @pytest.mark.skip
    def test_run_simulation(self, run_raspa):
        assert os.path.exists('Output')
        assert os.path.exists('stdout')
        assert os.path.exists('stderr')

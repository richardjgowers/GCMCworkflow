import fireworks as fw
import gcmcworkflow as gcwf
import os
import pytest
import shutil

ZEO_PP_INSTALLED = shutil.which('network') is not None
ZEO_PP_SKIP = pytest.mark.skipif(not ZEO_PP_INSTALLED,
                                 reason='Zeo++ not found in PATH')


HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(HERE, 'zeopp_reference')

def make_zeopp_fw(calcname):
    with open(os.path.join(REF_DIR, 'IRMOF-1.cif'), 'r') as fin:
        irmof = fin.read()

    # make a zeopp calc on IRMOF-1
    return fw.Workflow([fw.Firework([
        gcwf.zeopp.PrepareStructure(
            structure=irmof,
            name='IRMOF-1',
            workdir=os.getcwd(),
        ),
        gcwf.zeopp.ZeoPP(calculations=[calcname]),
    ])])


@pytest.fixture
def reference_results():
    ref = {}

    with open(os.path.join(REF_DIR, 'IRMOF-1.res'), 'r') as fin:
        ref['pore_diameter'] = fin.read()

    return ref


@ZEO_PP_SKIP
def test_pore_diameter(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('pore_diameter'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.res'), 'r').read()

    assert result == reference_results['pore_diameter']

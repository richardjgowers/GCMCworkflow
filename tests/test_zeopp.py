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
        gcwf.zeopp.ZeoPP(calculations=[calcname], radius=1.88),
    ])])


@pytest.fixture
def reference_results():
    ref = {}

    for filename, key in (
            ('IRMOF-1.res', 'pore_diameter'),
            ('IRMOF-1.chan', 'channel_identification'),
            ('IRMOF-1.sa', 'surface_area'),
            ('IRMOF-1.vol', 'accessible_volume'),
            ('IRMOF-1.volpo', 'probe_volume'),
            ('IRMOF-1.psd_histo', 'psd'),
            ('IRMOF-1.ray_atom', 'raytrace'),
            ('IRMOF-1.strinfo', 'structure_analysis'),
    ):
        with open(os.path.join(REF_DIR, filename), 'r') as fin:
            ref[key] = fin.read()

    return ref


@ZEO_PP_SKIP
def test_pore_diameter(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('pore_diameter'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.res'), 'r').read()

    assert result == reference_results['pore_diameter']


@ZEO_PP_SKIP
def test_channel_identification(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('channel_identification'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.chan'), 'r').read()

    assert result == reference_results['channel_identification']


@ZEO_PP_SKIP
def test_surface_area(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('surface_area'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.sa'), 'r').read()

    assert result == reference_results['surface_area']


@ZEO_PP_SKIP
def test_accessible_volume(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('accessible_volume'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.vol'), 'r').read()

    assert result == reference_results['accessible_volume']


@ZEO_PP_SKIP
def test_probe_occupiable_volume(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('probe_volume'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.volpo'), 'r').read()

    assert result == reference_results['probe_volume']


@ZEO_PP_SKIP
def test_psd(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('psd'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.psd_histo'), 'r').read()

    assert result == reference_results['psd']


@ZEO_PP_SKIP
def test_raytrace(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('raytrace'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.ray_atom'), 'r').read()

    assert result == reference_results['raytrace']


@ZEO_PP_SKIP
def test_structure_analysis(in_temp_dir, reference_results, launchpad):
    launchpad(make_zeopp_fw('structure_analysis'))

    result = open(os.path.join('IRMOF-1', 'IRMOF-1.strinfo'), 'r').read()

    assert result == reference_results['structure_analysis']

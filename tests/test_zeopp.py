import gcmcworkflow as gcwf
import os
import pytest
import shutil

ZEO_PP_INSTALLED = shutil.which('network') is not None
ZEO_PP_SKIP = pytest.mark.skipif(not ZEO_PP_INSTALLED,
                                 reason='Zeo++ not found in PATH')


HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(HERE, 'IRMOF-1')


@pytest.fixture
def reference_results():
    ref = {}

    with open(os.path.join(REF_DIR, 'IRMOF-1.res'), 'r') as fin:
        ref['pore_diameter'] = fin.read()

    return ref


@ZEO_PP_SKIP
def test_pore_diameter(reference_results, launchpad):
    pass

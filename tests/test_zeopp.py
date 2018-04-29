import pytest
import shutil

ZEO_PP_INSTALLED = shutil.which('network') is not None


@pytest.mark.skipif(not ZEO_PP_INSTALLED, reason='Zeo++ not installed')
def test_zeopp():
    assert 1 == 2

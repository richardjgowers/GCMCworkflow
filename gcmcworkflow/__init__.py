__version__ = '0.6.0'

DEFAULT_MAX_ITERATIONS = 4
DEFAULT_NCYCLES = 2000
DEFAULT_G_REQ = 5

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from .errors import NotEquilibratedError

from . import fw_utils
from . import utils
from . import analysis
from . import formats

from . import hyd

from . import spec_parser
from .spec_parser import read_spec

from . import raspatools
from . import firetasks

from . import zeopp

from . import grids

from . import workflow_creator
from .workflow_creator import make_workflow

from . import genetics
from . import make_genetics

from .poreblazer import PoreblazerTask

from . import launchpad_utils

from .tests import run_tests

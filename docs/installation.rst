Installing GCMCWorkflow
=======================

Installing the GCMCWorkflow package
"""""""""""""""""""""""""""""""""""

The easiest way to install the GCMCWorkflow Python package is using Anaconda_
from the conda-forge channel::

  conda install -c conda-forge gcmcworkflow
  
or pip_::

  pip install gcmcworkflow

.. _Anaconda: https://anaconda.org
.. _Pip: https://pypi.org


Setting up a Launchpad
""""""""""""""""""""""

GCMCWorkflow is powered by Fireworks_ and requires a functioning LaunchPad
(database of jobs).
For instructions on how to do this, please consult the `official instructions`_
Ultimately this should result in a `my_launchpad.yaml` file, which works with
the various Fireworks commands such as `lpad get_fws`.

.. _Fireworks: https://materialsproject.github.io/fireworks/
.. _official instructions: https://materialsproject.github.io/fireworks/installation.html


Setting up required drivers
"""""""""""""""""""""""""""

GCMCWorkflow does not perform the individual GCMC simulations, but instead
relies on a driver program beneath it.
I.e. you use GCMCWorkflow, GCMCWorkflow uses Raspa.

GCMCWorkflow can currently use the following drivers:
 - `zeo++`_
 - Raspa_

.. _`zeo++`: http://zeoplusplus.org
.. _Raspa: https://www.iraspa.org/RASPA/index.html

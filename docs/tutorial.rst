GCMCWorkflow tutorial
=====================

In this tutorial we will automate running three isotherms of Argon in IRMOF-1
using GCMCWorkflow.
To follow this tutorial, you will need to have installed this package
succesfully.
To check this, try running ``gcmcworkflow -h`` from the terminal,
you should see the help message for the command line tool we will
be using.


Preparing input files
"""""""""""""""""""""

In order to run our GCMC simulations we must provide a single working
input for Raspa.
This file will be used as a template for all further simulations,
with the temperature, pressure and simulation duration settings
being customised as necessary.
The forcefield setup and MC move descriptions will not be modified however,
so these should be checked!

For this tutorial you can use your own Raspa input files, or alternatively
by running the following command you can use the tutorial example files::

  gcmcworkflow tutorial gen_inputfiles


Preparing the spec file
"""""""""""""""""""""""

With the Raspa input ready, we now create the input file for GCMCWorkflow,
know as the 'spec' file.
This file will have all the information on sampling we want to perform,
using the Raspa input we just prepared.

A template for this spec file can be generated using the
``gcmcworkflow genspec`` command.
Thie file should follow yaml formatting rules, edit the spec file to
read as follows,
these settings will be explained below.

.. code-block:: yaml
  
  name: IRMOF1_Ar_tutorial
  template: ./irmof/
  workdir: ./
  g_req: 3
  max_iterations: 2
  use_grid: true
  conditions:
   - pressures: [10k, 20k, 40k]
     temperatures: [78.0, 98.0]
   - pressures: [50k, 0.1M]
     temperatures: [118.0]
  
Explaining the spec file lines:
 - **name** -- this is a unique identifier for this Workflow. It must be
   unique on the LaunchPad and will be used to refer to this Workflow
   in the future
 - **template** -- path to the simulation input we want to use.  This
   directory will be slurped into the Workflow.
 - **workdir** -- path to where we want to run the simulations.  This
   path must be accessible on the workstation you want to execute the
   workflow, ie it might be a path on your HPC cluster.
 - **g_req** -- this is the desired simulation length, expressed as a
   multiple of the number of statistical decorrelations after equilibration
   to run for.
   Larger values will take longer, but be more statistically reliable
   answers, 3-5 seems to work ok.
 - **max_iterations** -- simulations will be restarted to gather enough
   data as defined above, this setting allows a maximum to the number
   of times a point is restarted.
 - **use_grid** -- Raspa allows for energy grids to be used to accelerate
   the GCMC sampling.  This is often a good idea, except for very short
   simulations.
 - **conditions** -- starts a list of the system conditions we want to
   sample.  Each entry must give temperatures and pressures.
   In this example we will run pressures of 10, 20, and 40 kPa
   for temperatures 78.0 and 98.0 K, then 50,000 and 100,000 kPa at a
   temperature of 118.0 K.


Submitting work to LaunchPad
""""""""""""""""""""""""""""

Now we've defined our input and desired sampling we need to submit
this information to our LaunchPad.
Most of the time (unless you are locally running a MongoDB server)
you will have a file called ``my_launchpad.yaml`` which holds the
details to connect to the Fireworks LaunchPad.

Before submitting work to the LaunchPad it is a good idea to check the
connection.
This can be done using ``lpad report``, which will
return a quick description of the status of the LaunchPad.  If this step
does not work, consult the :ref:`launchpad_setup` instructions.

To submit the workflow to the LaunchPad we call::

  gcmcworkflow submit spec.yml -l my_launchpad.yaml

This reads the spec file we just created, translates this into a
Fireworks Workflow, and submits this to the Fireworks LaunchPad.
We can inspect the Workflow using Fireworks commands, such as
the web gui (``lpad webgui``).


Inspecting the Workflow
"""""""""""""""""""""""

By checking the webgui of the Workflow, we see a diagram of our Workflow
like this:


At the start of the Workflow we can see that that there are two tasks that
must be completed first, before we proceed to sampling different
temperatures and pressures.  These are copying the simulation template
onto the worker filesystem and creating the energy grid.
Fireworks has allowed to express dependencies between these, so that the
sampling simulations only run once the energy grid has been produced!


Running our Workflow
""""""""""""""""""""

The Workflow can now be executed!  This is done using the ``rlaunch``
commands from Fireworks.
For example to run the tasks within the Workflow in parallel on
4 cores, you could use::

  rlaunch multi 4

Remember that for this to work a connection to the LaunchPad is required,
ie there should be a ``launchpad.yaml`` file in the directory you run from.
  
It is worth remembering that the Workflow can be ran on a different
workstation than the one which submitted the Workflow.  This allows you to
define Workflow from your local workstation, then issue jobs on a HPC
cluster to pull these jobs annd push results back, then finally download
the results back to your local workstation.

Checking our results
""""""""""""""""""""

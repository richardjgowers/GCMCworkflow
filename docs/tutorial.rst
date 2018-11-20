GCMCWorkflow tutorial
=====================

In this tutorial we will run three isotherms of Argon in IRMOF-1 using
GCMCWorkflow.
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


Preparing the spec file
"""""""""""""""""""""""

With the Raspa input ready, we now create the input file for GCMCWorkflow,
know as the 'spec' file.
This file will have all the information on sampling we want to perform,
using the Raspa input we just prepared.

A template for this spec file can be generated using the
``gcmcworkflow genspec`` command.
Now edit the spec file to read as follows,
these settings will be explained below.

::
  
  name: IRMOF1_Ar_tutorial
  template: ./irmof/
  workdir: ./
  pressures: [10k, 20k, 40k]
  temperatures: [78.0, 98.0, 118.0]
  
Explaining the spec file lines:
 - **name** -- this is a unique identifier for this Workflow. It must be
   unique on the LaunchPad and will be used to refer to this Workflow
   in the future
 - **template** -- path to the simulation input we want to use
 - **workdir** -- path to where we want to run the simulations


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
the web gui (``lpad webgui``) or through some lighter inbuilt
GCMCWorkflow tools such as ``gcmcworkflow check``.


Running our Workflow
""""""""""""""""""""

- check Raspa installation

Checking our results
""""""""""""""""""""

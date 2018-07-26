Crash Recovery
--------------

When running simulations on a HPC cluster,
there is often a maximum wall time for your job,
typically 1 or 2 days.
However for some GCMC simulations,
especially at higher pressures,
this is not long enough to collect enough data.
GCMCWorkflow is able to work around this problem by allowing
the restart of terminated simulations.

After a RunSimulation task has been performed,
the PostProcess task checks if the simulation exited correctly.
If it finds that the simulation didn't exit correctly,
then it ascertains how long it should have ran for,
and how long the simulation actually ran for.
It then parses what data was generated (so this is not wasted),
then creates a new RunSimulation stage in the Workflow
which will complete the remaining number of steps.

If a job was killed due to walltime constraints,
the job will naturally not have been able to communicate that it was killed.
These jobs will therefore appear as if they are still running,
even after the job on the HPC cluster has terminated.
Manual intervention is required to find such jobs and mark them as finished;
the following Fireworks command can be used:

.. code:: bash

   ``lpad detect_lostruns --fizzle``

This finds jobs which are "lost", ie haven't reported their status
in a long time, and marks them as "FIZZLED", the Fireworks term for failure.



.. technical implementation

Automatic Runlength
-------------------

How automatic runlength works

 - once eq is found, we can measure how much data we have produced
 - use heuristic of g ~~ n_eq [from Mol. Sim paper]
 - sampling is defined in terms of number of g to collect
 - if enough g hasn't been collected, a restart is issued


.. image:: runlength.jpeg

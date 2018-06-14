# GCMCWorkflow

[![Build Status](https://travis-ci.org/richardjgowers/GCMCworkflow.svg?branch=master)](https://travis-ci.org/richardjgowers/GCMCworkflow)
[![codecov](https://codecov.io/gh/richardjgowers/GCMCworkflow/branch/master/graph/badge.svg)](https://codecov.io/gh/richardjgowers/GCMCworkflow)
[![DOI](https://zenodo.org/badge/104999008.svg)](https://zenodo.org/badge/latestdoi/104999008)

GCMCworkflow is a Python package for performing GCMC sampling of gas adsorption using [Fireworks](https://github.com/materialsproject/fireworks).

## Installation

GCMCWorkflow can be installed via the following steps:

```bash
git clone https://github.com/richardjgowers/hydraspa.git

cd hydraspa

pip install -r requirements.txt .

cd ../

git clone https://github.com/richardjgowers/GCMCworkflow.git

cd GCMCWorkflow

pip install -r requirements.txt

# for some pymongo connections
pip install dnspython

# for Raspa simulations
pip install raspa2

```

## Usage and basic tutorial

GCMCWorkflow relies on [Fireworks](https://github.com/materialsproject/fireworks) for managing the Workflow execution.  You should first [familiarise yourself with this package](https://materialsproject.github.io/fireworks/introduction.html), especially [how to use a MongoDB server](https://materialsproject.github.io/fireworks/quickstart.html?highlight=mongo)

A short example for how to set up a simulation of the GCMC sampling of Argon adsorption in IRMOF-1 using [Raspa](https://github.com/numat/RASPA2) is given: 

We will first use [hydraspa](https://github.com/richardjgowers/hydraspa) to prepare the simulation inputs:

```bash
hydraspa create -s IRMOF-1 -g Ar -f UFF -o IRMOF1_Argon

```

This creates a directory called ``IRMOF1_Argon`` containing a Raspa input template for our future simulations.

In order to define a sampling Workflow, a "spec file" must be given, an example workflow spec file is given below.
This contains information on the temperatures (78K) and pressures (100 to 201,000 Pa) we wish to sample, as well as providing the paths of the templates to be used.

```
# Example workflow_spec.yml file
name: ArIrmof1
pressures:
 - logspace(100, 125000.0, 10)
 - 0.15M
 - 0.201M  # saturation pressure
temperatures:
 - 78.0
template: IRMOF1_Argon/template/
workdir: IRMOF1_Argon/
nparallel: 1
ncycles: 5000

```

We can then add this Workflow to our LaunchPad via the ``submit`` command:

```bash
gcmcworkflow submit workflow_spec.yml -l my_launchpad.yaml
```

Once submitted, we can check what GCMC Workflows have been submitted using the ``list`` command, and query individual Workflows with the ``check`` command:

```
gcmcworkflow -l my_launchpad.yaml list
 
gcmcworkflow -l my_launchpad.yaml check ArIrmof1
```

The Workflow is executed as normal using Fireworks, using the ``rlaunch`` command.  For example to execute the Workflow using 4 parallel cores:

```
rlaunch multi 4
```

This will run Fireworks (compute tasks) from the Workflow until completion.  The progress of these can be viewed by looking inside the ``IRMOF1_Argon directory``.

Upon completion, a file called "results.csv" will be created in the working directory containing the results of our sampling.


## Citing

If you find this software useful for your research, consider citing the following publications:

[Jain, A., Ong, S. P., Chen, W., Medasani, B., Qu, X., Kocher, M., Brafman, M., Petretto, G., Rignanese, G.-M., Hautier, G., Gunter, D., and Persson, K. A. (2015) FireWorks: a dynamic workflow system designed for high-throughput applications. Concurrency Computat.: Pract. Exper., 27: 5037–5059. doi: 10.1002/cpe.3505.](http://onlinelibrary.wiley.com/doi/10.1002/cpe.3505/abstract)


## Contributing

GCMCWorkflow is being actively developed, drop me a line!

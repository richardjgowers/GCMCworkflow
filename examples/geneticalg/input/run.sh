#!/bin/bash

export RASPA_DIR=/home/rgowers/scratch/GNU_RASPA
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$RASPA_DIR/lib

$RASPA_DIR/bin/simulate

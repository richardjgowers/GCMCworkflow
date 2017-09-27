#!/bin/bash
#$ -V
#$ -cwd
#$ -l h_rt=12:00:00
#$ -l h_vmem=3G
#$ -N fw

. /etc/profile.d/modules.sh
ulimit -s unlimited

load_raspa

module load python

source activate GAargon

export CWD=$(pwd -P)
# copy over worker and launchpad settings
cp my_* $TMPDIR

cd $TMPDIR

# 10h timeout
rlaunch rapidfire --timeout 36000 > $CWD/status.$JOB_ID

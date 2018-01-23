import fireworks as fw
import gcmcworkflow as gcwf

import os

def test_already_existing(sample_input, launchpad):
    """Check that CopyTemplate correctly overwrites an existing Simulation"""
    T = 290.0
    P = 100.0
    gen = 1
    pid = 2

    # make something in the way
    newdir = gcwf.utils.gen_sim_path(T, P, gen, pid)
    os.makedirs(newdir)
    with open(os.path.join(newdir, 'thing.txt'), 'w') as out:
        out.write('hello!\n')

    # make and run CopyTemplate
    cp = fw.Firework([gcwf.firetasks.CopyTemplate(
        temperature=T, pressure=P,
        generation=gen, parallel_id=pid,
        fmt='raspa',
        workdir=os.path.abspath('.'),
    )],
                     spec={
                         'template': os.path.abspath('template'),
                     },
    )
    launchpad(cp)

    assert os.path.exists(newdir)
    assert not os.path.exists(os.path.join(newdir, 'thing.txt'))

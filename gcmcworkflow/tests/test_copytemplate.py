import fireworks as fw
import gcmcworkflow as gcwf

import os

def test_already_existing(sample_input, launchpad, template_contents):
    """Check that CopyTemplate correctly overwrites an existing Simulation"""
    T = 290.0
    P = 100.0
    gen = 1
    pid = 2

    # make something in the way
    newdir = gcwf.utils.gen_sim_path('hash123', T, P, gen, pid)
    os.makedirs(newdir)
    with open(os.path.join(newdir, 'thing.txt'), 'w') as out:
        out.write('hello!\n')

    # make and run CopyTemplate
    cp = fw.Firework([gcwf.firetasks.CopyTemplate(
        temperature=T, pressure=P,
        parallel_id=pid,
        fmt='raspa',
        workdir=os.path.abspath('.'),
    )],
                     spec={
                         'simhash': 'hash123',
                         'template': os.path.abspath('template'),
                     },
    )
    launchpad(cp)

    newdir2 = gcwf.utils.gen_sim_path('hash123', T, P, gen + 1, pid)

    assert os.path.exists(newdir)
    assert os.path.exists(newdir2)
    assert os.path.exists(os.path.join(newdir, 'thing.txt'))
    for fn in template_contents:
        assert os.path.exists(os.path.join(newdir2, fn))

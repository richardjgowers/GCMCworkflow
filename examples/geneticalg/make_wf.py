import fireworks as fw
import gcmcworkflow as gcwf
import os
import random


def updater(loc, candidate):
    """Modify the parameters in *loc* to match *candidate*"""
    import os

    ffloc = os.path.join(loc, 'force_field_mixing_rules.def')
    with open(ffloc, 'r') as fh:
        original = fh.readlines()
    with open(ffloc, 'w') as fh:
        for line in original:
            if not line.startswith('Ar'):
                fh.write(line)
            else:
                fh.write('Ar  lennard-jones {sig} {eps}\n'
                         ''.format(sig=candidate[0],
                                   eps=candidate[1]))


PRESSURES = [val * 100000. for val in (1, 3, 5, 10, 20, 30)]
RESULTS = [1.368, 4.080, 6.729, 13.126, 24.345, 35.533]
TEMPERATURES = [298.0] * len(PRESSURES)
CONDITIONS = list(zip(TEMPERATURES, PRESSURES, RESULTS))
BOUNDS = [
    (50.0, 200.0),
    (1.0, 5.0),
]
POPSIZE = 32
NGENS = 10


def generate_initial(ncandidates, boundaries):
    pop = []

    for _ in range(ncandidates):
        dude = []
        for lo, hi in boundaries:
            dude.append(random.uniform(lo, hi))
        pop.append(tuple(dude))

    return pop


if __name__ == '__main__':
    lp = fw.LaunchPad()

    wf = gcwf.make_genetics.make_genetic_workflow(
        ngens=NGENS,
        ncandidates=POPSIZE,
        template='input',
        initial_pop=generate_initial(POPSIZE, BOUNDS),
        conditions=CONDITIONS,
        ff_updater=updater,
        bounds=BOUNDS,
        wf_name='GAargon',
    )

    lp.add_wf(wf)

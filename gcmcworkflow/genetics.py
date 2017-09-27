"""FireWorks for Genetic Algorithms

Persistent Data structures(
parents:
  - list of parameters and fitness
    eg: ((0.5, 2.0, 1.5), 4.5)
candidates:
  - list of parameters, initially without fitness
    eg: ((0.5, 2.0, 1.5), None)
  - later gets given fitness values
candidate results:
  - assigns results to candidates
    eg: (0, (4.5, 4.6, 4.6))  # candidate 0 has results
  - can be converted into fitness later
simulation template:
 - contains the template for a simulation?
template:
  - path to where the template was saved to
)

VVVV
Simulation template
VVVV

Firstgen GA(
Firstgen Pre GA:
  Generate initial population
   - creates parents
  Copy template and pass along path to it
   - destroy simulation template
   - creates template

Firstgen Sampling:
  Identical to normal sampling stage

Firstgen Post GA:
  Identical to normal Post GA stage
)

VVVV
Parents, Template
VVVV

)

GA_process(

VVVV
Parents, Template
VVVV

PreGAFW: (one)
  Tournament
  - receive parents
  - create candidates from parents
VaryCandidates
  - replace candidates
PassAlong(parents, template)

VVVV
Parents, Candidates, Template
VVVV

SimFW: (for each condition and candidate)
  CopyTemplate
  - uses template
  ManipulateForcefield(candidate id)
  - receive candidates
  RunSimulation
  EvaluateResult(reference)
  - creates error
  - creates results_array

VVVV
error, results_array
VVVV

ResultsFW: (for each candidate)
  IsothermCreate
   - uses results_array
  AssignFitness(candidate_id)
   - uses error to create fitness

VVVV
Parents, Candidates, fitness, Template
VVVV

PostGAFW: (one)
  Replacement
  - uses candidates and fitness
  - replaces parents
  PassAlong(template)

VVVV
Parents, Template
VVVV
)

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import os
import random

from . import raspatools
from . import utils


@xs
class InitPopulation(fw.FiretaskBase):
    """Receieve the initial seeding for the GA"""
    required_params = ['initial_population']

    def run_task(self, fw_spec):
        return fw.FWAction(
            update_spec={
                'candidates': self['initial_population'],
                'parents': []  # no parents initially
            }
        )


@xs
class PassAlong(fw.FiretaskBase):
    """Pass along to next Firework"""
    required_params = ['keys']

    def run_task(self, fw_spec):
        return fw.FWAction(
            update_spec={k: fw_spec[k] for k in self['keys']}
        )


@xs
class Tournament(fw.FiretaskBase):
    """Return a list of candidates from parents"""
    @staticmethod
    def tournament(parents):
        """Return candidates from parents

        Parameters
        ----------
        parents : list of tuples
          current population of the GA

        Returns
        -------
        candidates : list of tuples
          parameter sets for the chosen solutions to propagate
        """
        popsize = len(parents)

        selected = []
        previous = None
        current = None
        while len(selected) < popsize:
            while previous == current:
                current = min(random.sample(parents, 2),
                              key=lambda x: x[1])  # .fitness
            selected.append(current[0])  # .parameters
            previous = current

        return selected

    def run_task(self, fw_spec):
        candidates = self.tournament(fw_spec['parents'])

        return fw.FWAction(
            update_spec={'candidates': candidates}
        )


@xs
class VaryCandidates(fw.FiretaskBase):
    """Vary the candidates"""
    required_params = [
        'blend_probability',
        # fraction to extrapolate from parent allele range
        'blend_alpha',
        'mutation_probability',
        # fudge factor to generate sigma for gassian noise
        # `sigma = (max - min) / sigma_factor`
        'sigma_factor',
        # bounds for candidate values
        'bounds',
    ]
    default_params = dict(
        blend_probability=0.9,
        blend_alpha=0.1,
        mutation_probability=0.1,
        sigma_factor=6.0,
    )

    @staticmethod
    def clamp(val, lower, upper):
        """He's champin' for a clampin'!"""
        val = max(val, lower)
        val = min(val, upper)
        return val

    def blend_crossover(self, candidates):
        # split candidates into pairs
        # vary each candidate in pairs
        # self['blend_probability']
        new_candidates = []

        for mother, father in zip(candidates[::2], candidates[1::2]):
            brother, sister = [], []
            for a, b, (min_bound, max_bound) in zip(mother, father,
                                                    self['bounds']):
                if random.random() < self['blend_probability']:
                    smallest, largest = min(a, b), max(a, b)
                    # range between parents
                    width = largest - smallest
                    # amount we go out of bounds from natural range
                    extra = width * self['blend_alpha']

                    # start point is (smallest - delta)
                    # we then move up to (width + 2 * extra) from this point
                    a = ((smallest - extra) +
                         random.random() * (width + 2 * extra))
                    b = ((smallest - extra) +
                         random.random() * (width + 2 * extra))
                    a = self.clamp(a, min_bound, max_bound)
                    b = self.clamp(b, min_bound, max_bound)

                brother.append(a)
                sister.append(b)

            new_candidates.append(tuple(brother))
            new_candidates.append(tuple(sister))

        return new_candidates

    def gaussian_mutation(self, candidates):
        # for each variable, calculate current range, then define sigma
        n_params = len(candidates[0])
        sigmas = []
        for i in range(n_params):
            maxval = max(c[i] for c in candidates)
            minval = min(c[i] for c in candidates)
            sigmas.append((maxval - minval) / self['sigma_factor'])

        # perform mutations using these sigmasx
        def mutate(candidate):
            new = []
            for sigma, val, (min_bound, max_bound) in zip(sigmas, candidate,
                                                          self['bounds']):
                if random.random() < self['mutation_probability']:
                    val += random.gauss(0, sigma)
                    val = self.clamp(val, min_bound, max_bound)

                new.append(val)
            return tuple(new)
        candidates = [mutate(c) for c in candidates]

        return candidates

    def run_task(self, fw_spec):
        candidates = self.blend_crossover(fw_spec['candidates'])
        candidates = self.gaussian_mutation(candidates)

        return fw.FWAction(
            update_spec={'candidates': candidates}
        )


@xs
class ManipulateForcefield(fw.FiretaskBase):
    """Change the forcefield parameters according to the candidate"""
    required_params = ['candidate_id', 'updater']

    def run_task(self, fw_spec):
        my_candidate = fw_spec['candidates'][self['candidate_id']]

        updater = utils.unpickle_func(self['updater'])
        updater(fw_spec['simtree'], my_candidate)

        return fw.FWAction()


@xs
class EvaluateResult(fw.FiretaskBase):
    """Calculate error of result"""
    required_params = ['reference']

    @staticmethod
    def grab_result(loc, fmt):
        """Grab the result from inside *loc*

        Parameters
        ----------
        loc : str
          path to where the simulation happened

        Returns
        -------
        result : float
          average result
        """
        if fmt == 'raspa':
            return raspatools.parse_results_simple(loc)
        else:
            raise NotImplementedError


    def run_task(self, fw_spec):
        result = self.grab_result(fw_spec['simtree'], fw_spec['format'])

        ref = self['reference']
        my_fitness = abs(result - ref) / ref

        return fw.FWAction(
            stored_data={'error': my_fitness},
            mod_spec=[{
                '_push': {
                    'error': my_fitness,
                    'results_array': (fw_spec['temperature'],
                                      fw_spec['pressure'],
                                      result, 1, 1),
                }
            }],
        )

@xs
class AssignFitness(fw.FiretaskBase):
    """After all Simulations of a candidate done, assign Fitness"""
    required_params = ['candidate_id']

    def run_task(self, fw_spec):
        my_id = self['candidate_id']
        # final fitness is sum of square of errors
        my_fitness = sum(v ** 2 for v in fw_spec['error'])

        f = (my_id, my_fitness)

        return fw.FWAction(
            stored_data={'fitness': f},
            mod_spec=[{
                '_push': {'fitness': f}
            }],

        )


@xs
class Replacement(fw.FiretaskBase):
    """Merge children and parents"""
    @staticmethod
    def collate(candidates, fitness):
        """Merge fitnesses and candidates into tuple Individuals

        Parameters
        ----------
        candidates : list of tuples
          list of candidates, in candidate_id order as they were provided
          to individual sims
        fitness : list of tuples
          tuples of (candidate_id, fitness)

        Returns
        -------
        individuals : list
          list of Individuals representing the results of the children for
          this generation
        """
        # sort according to candidate id
        fitnesses = sorted(fitness, key=lambda x: x[0])

        # then collatge the candidate results and fitnesses by zipping
        return [(c, f[1]) for c, f in zip(candidates, fitnesses)]

    @staticmethod
    def replace(parents, candidates):
        # final population size shouldn't change over time
        popsize = len(candidates)

        # parents is empty list in zeroth generation
        together = sorted(parents + candidates, key=lambda x: x[1])  # .fitness

        # just return the top half
        return together[:popsize]

    def run_task(self, fw_spec):
        # merge candidates and fitness
        children = self.collate(fw_spec['candidates'], fw_spec['fitness'])
        new_parents = self.replace(fw_spec['parents'], children)

        return fw.FWAction(
            stored_data={
                'candidates': children,
                'population': new_parents,
            },
            update_spec={'parents': new_parents},
        )

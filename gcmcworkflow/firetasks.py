"""Fireworks Firetasks that define workflows

Workflow diagram::

            InitTemplate
                 |
                 |
                 v  For each condition required, create SimFirework
     /-----------+-----------\
     |           |           |
     v           v           v
SimFirework SimFirework SimFirework
     |           |           |
     v           v           v
     \-----------+-----------/
                 |
                 v
            IsothermCreate


SimFirework layout::

                       from InitTemplate
                          (Tn, Pn)  # given one condition
                             |
                             | For each parallel task create an instance
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
    CopyTemplate        CopyTemplate        CopyTemplate
         |<-----------------)|(-----------------)|(-RestartSimulation-+
         |                   |<-----------------)|(-RestartSimulation-+
         |                   |                   |<-RestartSimulation-+
         v                   v                   v                    |
    RunSimulation       RunSimulation       RunSimulation             |
         |                   |                   |                    |
         v                   v                   v                    |
   AnalyseSimulation   AnalyseSimulation   AnalyseSimulation          |
         |                   |                   |                    |
         +-------------------+-------------------+                    |
                             |                                        |
                             v                                        |
                      PostProcess ------------------------------------+
                             |
                             v
                     to IsothermCreate

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import io
import numpy as np
import pandas as pd
import os
import shutil
import subprocess

# Import format specific tools
from . import NotEquilibratedError

from . import raspatools
from . import utils
from . import analysis
from . import postprocess


@xs
class InitTemplate(fw.FiretaskBase):
    """Prepare the template for future simulations

    Takes the simulation template from the MongoDB and creates a version
    on this worker machine.

    Takes:
     - dictionary of files - "contents"

    Does:
     - writes the template to the local work machine
     - detects the format of the simulation
     - creates a Treant in the new directory
       - tags this Treant as the template
     - adds path of template Treant to future Firework specs
    """
    required_params = ['contents']

    def run_task(self, fw_spec):
        # where the template can be found
        target = utils.dump_directory('template', self['contents'])

        return fw.FWAction(
            update_spec={
                # pass reference to this Treant to future Fireworks
                'template': target,
            }
        )


@xs
class CopyTemplate(fw.FiretaskBase):
    """Create a copy of the provided template

    From fw_spec:
     - template - path to the template to copy
     - temperature
     - pressure
     - parallel_id, optional
     - ncycles, optional

    Does:
     - creates new directory containing the Template
     - modifies the input files to this specification

    Provides: simtree - path to the customised version of the template
    """
    required_params = ['temperature', 'pressure', 'fmt']
    optional_params = ['parallel_id', 'ncycles']

    @staticmethod
    def update_input(target, fmt, T, P, n):
        if fmt == 'raspa':
            raspatools.update_input(target, T, P, n)
        else:
            raise NotImplementedError

    @staticmethod
    def copy_template(template, T, P, p_id):
        # where to place this simulation
        newdir = 'sim_{t}_{p}_v{i}'.format(t=T, p=P, i=p_id)
        # copy in the template to this newdir
        shutil.copytree(template, newdir)

        return newdir

    def run_task(self, fw_spec):
        sim_t = self.copy_template(
            fw_spec['template'],
            self['pressure'],
            self['temperature'],
            self.get('parallel_id', 0),
        )

        # Modify input to match the spec
        self.update_input(
            sim_t,
            self['fmt'],
            self['temperature'],
            self['pressure'],
            self.get('ncycles', None),
        )

        return fw.FWAction(
            update_spec={'simtree': os.path.abspath(sim_t)}
        )


@xs
class CreateRestart(fw.FiretaskBase):
    """Take a single simulation directory and prepare a continuation of it"""
    required_params = ['loc']

    def run_task(self, fw_spec):
        # self['loc'] is where to create restart from
        pass


@xs
class RunSimulation(fw.FiretaskBase):
    """Take a simulation directory and run it"""
    required_params = ['fmt']

    bin_name = {
        'raspa': 'simulate',
    }

    def run_task(self, fw_spec):
        old_dir = os.getcwd()
        os.chdir(fw_spec['simtree'])

        cmd = self.bin_name[self['fmt']]
        try:
            p = subprocess.run(cmd,
                               check=True,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            # CPE has following attributes:
            # - returncode
            # - cmd
            # - stdout
            # - stderr
            raise ValueError("RunSim failed with errorcode '{}' and stderr '{}'"
                             "".format(e.returncode, e.stderr))
        else:
            # write stdout and stderr to file?
            with open('stdout', 'wb') as outf:
                outf.write(p.stdout)
            with open('stderr', 'wb') as outf:
                outf.write(p.stderr)
        finally:
            os.chdir(old_dir)


@xs
class AnalyseSimulation(fw.FiretaskBase):
    """Analyse a single simulation into format agnostic form

    Takes:
     - path to simulation
    Does:
     - checks simulation finished correctly (ie output was written ok)
     - creates results file for this simulation
    """
    required_params = ['fmt']
    optional_params = ['parallel_id']

    @staticmethod
    def check_exit(fmt, simpath):
        """Check that the simulation finished OK

        Raises
        ------
        ValueError
          if simulation didn't finish
        """
        # format specific check exit
        if fmt == 'raspa':
            return raspatools.check_exit(simpath)
        else:
            raise NotImplementedError("Unrecognised format '{}' to parse"
                                      "".format(fmt))

    @staticmethod
    def parse_results(fmt, simpath):
        if fmt == 'raspa':
            return raspatools.parse_results(simpath)
        else:
            raise NotImplementedError("Unrecognised format '{}' to parse"
                                      "".format(fmt))

    def run_task(self, fw_spec):
        # check exit
        self.check_exit(self['fmt'], fw_spec['simtree'])

        # parse results
        results = self.parse_results(self['fmt'], fw_spec['simtree'])

        with open(os.path.join(fw_spec['simtree'], 'results.csv'), 'w') as out:
            results.to_csv(out)

        return fw.FWAction(
            stored_data={'result': results},
            mod_spec=[{
                '_push': {'results': (self.get('parallel_id', 0),
                                      results.to_csv())}
            }]
        )


@xs
class PostProcess(fw.FiretaskBase):
    """Gather results for a given condition and make decisions

    At this point, we are format agnostic:
     - AnalyseSimulation has created a generic timeseries for each individual
       sim
     - Make decisions based only on sim dirs irrespective of what format they
       are
    Does:
    - if not completed, create additional simulations
    - if finished, allow final step to happen

    # Can use estimates of neq and g to tailor remaining length
    # ie if g_completed = 10, and g=1e6, need additional 10e6 steps
    # can then create n_parallel extra sims each with 10e6/n_parallel additional
    # steps
    """
    required_params = ['temperature', 'pressure']

    def run_task(self, fw_spec):
        sims = dtr.discover(fw_spec['workdir'])
        # query the results database to pull out relevent simulations
        mysims = sims.categories.groupby(
            ['temperature', 'pressure'])[self['temperature'], self['pressure']]

        # Group together parallel ids across generations
        timeseries = postprocess.group_timeseries(mysims)

        # Find eq within each timeseries
        # Find g across all timeseries
        g_values = {}
        n_g = {}
        eq_points = {}
        for p_id, ts in timeseries.items():
            eq = analysis.find_eq(ts)
            # this is the total number of steps between samples?
            g = analysis.find_g(ts.loc[eq:])
            # can only take an integer number of samples
            n_g[p_id] = int((ts.index.max() - eq) / g)
            eq_points[p_id] = eq
            g_values[p_id] = g

        total_g = sum(n_g.values())

        # we're finished if the number of stat. decorrels. is larger
        # than the required amount
        # TODO: Make tau_criteria flexible
        tau_criteria = 20
        finished = total_g > tau_criteria

        if finished:
            # TODO: Maybe write down the final result I've calculated?
            # This way, the isotherm create step is simpler?
            # Result = (rho, stderr)
            # calculate stderr based on autocorrelation just calculated!
            # need to define somewhere what our criteria for "enough" is
            uncorr_series = []

            for p_id, ts in timeseries.items():
                eq = eq_points[p_id]
                g = g_values[p_id]
                # grab a few samples
                # reindex the original sample every *g* steps
                # starting at *eq*
                uncorr = ts.reindex(np.arange(n_g[p_id]) * g + eq,
                                    method='nearest')
                uncorr_series.append(uncorr)

            final_series = pd.concat(uncorr_series, ignore_index=True)
            mean = final_series.mean()
            std = final_series.std()
            # take mean and std from this
            return fw.FWAction(
                stored_data={'result': (mean, std)},
                mod_spec=[{
                    # push the results of this condition to the Create task
                    '_push': {'results_array': (self['temperature'],
                                                self['pressure'],
                                                mean, std, total_g)}
                }],
            )
        else:
            # find last generation number
            # grab reference to those simulations
            # add new batch of simulations
            last_generation = postprocess.find_latest_generation(mysims)
            new_fws = postprocess.gen_restart_sims(last_generation, T, P)

            # TODO: Look at how children are defined
            # only need the new PP task to inherit the child of this PP task
            return fw.FWAction(detours=new_fws)


@xs
class SimplePostProcess(fw.FiretaskBase):
    """Without recycle loop"""
    required_params = ['temperature', 'pressure']

    @staticmethod
    def make_series(ts):
        return pd.read_csv(
            io.StringIO(ts),
            header=None,
            index_col=0,
            squeeze=True,
        )

    def run_task(self, fw_spec):
        timeseries = {p_id: self.make_series(ts)
                      for (p_id, ts) in fw_spec['results']}

        means = []
        stds = []
        for p_id, ts in timeseries.items():
            eq = analysis.find_eq(ts)
            means.append(ts.loc[eq:].mean())
            stds.append(ts.loc[eq:].std())
        mean = np.mean(means)
        std = np.mean(stds)

        return fw.FWAction(
            stored_data={'result': (mean, std)},
            mod_spec=[{
                # push the results of this condition to the Create task
                '_push': {'results_array': (self['temperature'],
                                            self['pressure'],
                                            mean, std, 1)}
            }],
        )


@xs
class IsothermCreate(fw.FiretaskBase):
    """From all results, create final answer of the isotherm"""
    def run_task(self, fw_spec):
        # create sorted version
        results = sorted(fw_spec['results_array'],
                         key=lambda x: (x[0], x[1]))

        # write sorted version to file
        with open('results.out', 'w') as out:
            out.write('temperature,pressure,mean,std,g\n')
            for row in results:
                out.write(','.join(str(val) for val in row))
                out.write('\n')

        return fw.FWAction(
            stored_data={'final_result': results}
        )

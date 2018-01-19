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
         +-------------------+-------------------+ <------------------+
         |                   |                   |                    |
         v                   v                   v                    |
    CopyTemplate        CopyTemplate        CopyTemplate              |
         |                   |                   |                    |
   (CopyRestart?)      (CopyRestart?)      (CopyRestart?)             |
         |                   |                   |                    |
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

    Attributes:
     - template - path to the template to copy
     - temperature
     - pressure
     - generation, optional
     - parallel_id, optional
     - ncycles, optional

    Does:
     - creates new directory containing the Template
     - modifies the input files to this specification

    Provides: simtree - path to the customised version of the template
    """
    required_params = ['temperature', 'pressure', 'fmt']
    optional_params = ['workdir', 'generation', 'parallel_id', 'ncycles']

    @staticmethod
    def update_input(target, fmt, T, P, n):
        if fmt == 'raspa':
            raspatools.update_input(target, T, P, n)
        else:
            raise NotImplementedError

    @staticmethod
    def copy_template(workdir, template, T, P, gen_id, p_id):
        # where to place this simulation
        newdir = os.path.join(workdir, 'sim_{t}_{p}_gen{g}_v{i}'.format(
            t=T, p=P, g=gen_id, i=p_id)
        )
        # copy in the template to this newdir
        shutil.copytree(template, newdir)

        return newdir

    def run_task(self, fw_spec):
        sim_t = self.copy_template(
            self.get('workdir', ''),
            fw_spec['template'],
            self['pressure'],
            self['temperature'],
            self.get('generation', 1),
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
    required_params = ['previous_simtree']

    @staticmethod
    def set_as_restart(simtree):
        raspatools.set_restart(simtree)

    def run_task(self, fw_spec):
        # copy over Restart directory from previous simulation
        oldsim = self['previous_simtree']
        newsim = fw_spec['simtree']

        shutil.copytree(os.path.join(oldsim, 'Restart'),
                        os.path.join(newsim, 'RestartInitial'))

        # modify the simulation.input to use the restart file
        self.set_as_restart(fw_spec['simtree'])

        return fw.FWAction()


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
    optional_params = ['parallel_id', 'previous_results']

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

    @staticmethod
    def prepend_previous(previous, current):
        previous = utils.make_series(previous)

        # reindex the current timeseries to start after the last one
        dt = previous.index[1] - previous.index[0]
        current.index += previous.index.max() + dt

        return previous.append(current)

    def run_task(self, fw_spec):
        simtree = fw_spec['simtree']
        parallel_id = self.get('parallel_id', 0)

        # check exit
        self.check_exit(self['fmt'], simtree)

        # parse results
        results = self.parse_results(self['fmt'], simtree)
        # save csv of results from *this* simulation
        utils.save_csv(results, os.path.join(simtree, 'this_sim_results.csv'))

        if 'previous_results' in self:
            results = self.prepend_previous(self['previous_results'], results)
        # csv of results from all generations of this simulation
        utils.save_csv(results, os.path.join(simtree, 'total_results.csv'))

        return fw.FWAction(
            stored_data={'result': results},
            mod_spec=[{
                '_push': {
                    'results': (parallel_id, results.to_csv()),
                    'simpaths': (parallel_id, simtree),
                }
            }]
        )


@xs
class PostProcess(fw.FiretaskBase):
    """Gather results for a given condition and make decisions"""
    required_params = ['temperature', 'pressure']

    def run_task(self, fw_spec):
        timeseries = {p_id: utils.make_series(ts)
                      for (p_id, ts) in fw_spec['results']}

        # grab the production portion of each timeseries
        production = {}
        for p_id, ts in timeseries.items():
            eq = analysis.find_eq(ts)
            production[p_id] = ts.loc[eq:]

        # figure out the number of correlations in the production
        # period we've sampled
        # using all timeseries at once we can average between them to smooth
        g = analysis.find_g(production)

        total_g = 0.0
        for p_id, ts in production.items():
            total_g += int((ts.index.max() - ts.index.min()) / g)

        tau_criteria = 20
        if total_g < tau_criteria:
            # issue restarts
            return fw.FWAction(
            )
        else:
            # calculate and declare final answer
            return fw.FWAction(
            )

        if finished:
            # TODO: Maybe write down the final result I've calculated?
            # This way, the isotherm create step is simpler?
            # Result = (rho, stderr)
            # calculate stderr based on autocorrelation just calculated!
            # need to define somewhere what our criteria for "enough" is
            uncorr_series = []

            for p_id, ts in production.items():
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

    def run_task(self, fw_spec):
        timeseries = {p_id: utils.make_series(ts)
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
    optional_params = ['workdir']

    def run_task(self, fw_spec):
        # create sorted version
        results = sorted(fw_spec['results_array'],
                         key=lambda x: (x[0], x[1]))

        outfile = os.path.join(self.get('workdir', ''), results.out)
        with open(outfile, 'w') as out:
            out.write('temperature,pressure,mean,std,g\n')
            for row in results:
                out.write(','.join(str(val) for val in row))
                out.write('\n')

        return fw.FWAction(
            stored_data={'final_result': results}
        )

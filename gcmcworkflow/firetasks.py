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
         |                   |                   |                    |
         |                   |                   |                    |
         v                   v                   v                    |
    RunSimulation       RunSimulation       RunSimulation             |
         |                   |                   |                    |
         v                   v                   v                    |
    PostProcess         PostProcess         PostProcess               |
         |                   |                   |                    |
         +-------------------+-------------------+                    |
                             |                                        |
                             v                                        |
                          Analyse ------------------------------------+
                             |
                             v
                     to IsothermCreate

"""
import fireworks as fw
from fireworks.utilities.fw_utilities import explicit_serialize as xs
import hashlib
import numpy as np
import pandas as pd
import os
import shutil
import subprocess
import tarfile
try:
    import datreant as dtr
except:
    dtr = False

# Import format specific tools
from . import NotEquilibratedError

from . import formats
from . import raspatools
from . import utils
from . import analysis


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
    optional_params = ['contents', 'workdir']

    def run_task(self, fw_spec):
        if self.get('workdir', ''):
            os.makedirs(self.get('workdir'), exist_ok=True)

        if self.get('contents', None) is not None:
            # where the template can be found
            target = utils.dump_directory(
                os.path.join(self.get('workdir', ''), 'template'), self['contents'])

            return fw.FWAction(
                update_spec={
                    # pass reference to this Treant to future Fireworks
                    'template': target,
                }
            )
        else:
            return fw.FWAction()


@xs
class CreatePassport(fw.FiretaskBase):
    """Create a passport/fingerprint of a simulation setup"""
    optional_params = ['workdir']

    @staticmethod
    def calc_hash(tarname):
        """Returns leading 7 digits of SHA1 hash of tarfile"""
        hash = hashlib.sha1()

        with tarfile.open(tarname, 'r') as tar:
            for tarinfo in tar:
                if not tarinfo.isreg():
                    continue
                flo = tar.extractfile(tarinfo)
                while True:
                    # potentially can't hash the entire data
                    # so read it bit by bit
                    data = flo.read(2**20)
                    if not data:
                        break
                    hash.update(data)
                flo.close()

        return hash.hexdigest()[:7]

    @staticmethod
    def write_tarball(target, workdir):
        # create with initial name
        tarname = os.path.join(workdir, os.path.basename(target) + '.tar.gz')
        with tarfile.open(tarname, 'w:gz') as tar:
            tar.add(target, arcname=os.path.basename(target))

        return tarname

    def run_task(self, fw_spec):
        tarpath = self.write_tarball(fw_spec['template'].rstrip(os.path.sep),
                                     self.get('workdir', ''))

        # then rename tar according to hash of file
        sha1 = self.calc_hash(tarpath)
        os.rename(tarpath,
                  os.path.join(self.get('workdir', ''), '{}.tar.gz'.format(sha1)))

        return fw.FWAction(update_spec={'simhash': sha1})


@xs
class CopyTemplate(fw.FiretaskBase):
    """Create a copy of the provided template

    Attributes:
     - temperature
     - pressure
     - ncycles
    Optionally:
     - previous_simdir : for a restart
     - workdir : to control where simulation is done
     - parallel_id : to identify this sim, defaults to 0
     - use_grid : defaults to False

    Does:
     - creates new directory containing the Template
     - modifies the input files to this specification

    Provides: simtree - path to the customised version of the template
    """
    required_params = ['temperature', 'pressure', 'ncycles']
    optional_params = ['previous_simdir', 'workdir', 'parallel_id',
                       'use_grid']

    @staticmethod
    def update_input(target, fmt, T, P, n, use_grid=False):
        if fmt == 'raspa':
            raspatools.update_input(target, T, P, n, use_grid=use_grid)
        else:
            raise NotImplementedError

    @staticmethod
    def copy_template(workdir, simhash, template, T, P, p_id):
        """Copy template and prepare simulation run

        Parameters
        ----------
        workdir : str
          path to place template
        simhash : str
          7 digit hash of the simulation
        template : str
          template to copy
        T, P : float
          temperature and pressure to run
        p_id : int
          parallel id of this simulation
        """
        gen_id = utils.find_last_generation(workdir, simhash, T, P, p_id) + 1
        # where to place this simulation
        newdir = os.path.join(workdir,
                              utils.gen_sim_path(simhash, T, P, gen_id, p_id))

        # copy in the template to this newdir
        shutil.copytree(template, newdir)

        if dtr:
            t = dtr.Treant(
                newdir,
                categories={
                    'simhash': simhash,
                    'T': T,
                    'P': P,
                    'generation': gen_id,
                    'parallel_id': p_id,
                },
                tags=['sim'],
            )

        return newdir

    @staticmethod
    def set_as_restart(fmt, old, new):
        if fmt == 'raspa':
            # copy over Restart directory from previous simulation
            shutil.copytree(os.path.join(old, 'Restart'),
                            os.path.join(new, 'RestartInitial'))
            raspatools.set_restart(new)
        else:
            raise NotImplementedError

    def run_task(self, fw_spec):
        fmt = formats.detect_format(fw_spec['template'])

        is_restart = self.get('previous_simdir', None) is not None
        if is_restart:
            simhash = utils.parse_sim_path(self['previous_simdir']).simhash
        else:
            simhash = fw_spec['simhash']

        sim_t = self.copy_template(
            workdir=self.get('workdir', ''),
            simhash=simhash,
            template=fw_spec['template'],
            P=self['pressure'],
            T=self['temperature'],
            p_id=self.get('parallel_id', 0),
        )

        # Modify input to match the spec
        self.update_input(
            target=sim_t,
            fmt=fmt,
            T=self['temperature'],
            P=self['pressure'],
            n=self['ncycles'],
            use_grid=self.get('use_grid', False),
        )

        if is_restart:
            self.set_as_restart(
                fmt,
                old=self['previous_simdir'],
                new=sim_t,
            )

        return fw.FWAction(
            update_spec={
                'simtree': os.path.abspath(sim_t),
                'template': fw_spec['template'],
            }
        )


@xs
class RunSimulation(fw.FiretaskBase):
    """Take a simulation directory and run it"""
    bin_name = {
        'raspa': 'simulate simulation.input',
    }

    def run_task(self, fw_spec):
        fmt = formats.detect_format(fw_spec['simtree'])

        old_dir = os.getcwd()
        os.chdir(fw_spec['simtree'])

        cmd = self.bin_name[fmt]
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
class PostProcess(fw.FiretaskBase):
    """Analyse a single simulation into format agnostic form

    Takes:
     - path to simulation
    Does:
     - checks simulation finished correctly (ie output was written ok)
     - creates results file for this simulation
    """
    required_params = ['temperature', 'pressure', 'parallel_id',
                       'workdir']
    optional_params = ['previous_result', 'use_grid']

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
        current.index += (previous.index.max() + dt)

        return previous.append(current.iloc[:])

    @staticmethod
    def calc_remainder(simdir):
        """Calculate how many steps were left unfinished

        Parameters
        ----------
        simdir : str
          path to simulation

        Returns
        -------
        remaining : int
          number of steps still left to run
        """
        fmt = formats.detect_format(simdir)

        if fmt == 'raspa':
            return raspatools.calc_remainder(simdir)
        else:
            raise NotImplementedError("Unrecognised format '{}' to parse"
                                      "".format(fmt))

    def prepare_restart(self, template, previous_simdir,
                        current_result, wfname):
        """Prepare a continuation of the same sampling point

        Parameters
        ----------
        template : str
          path to template to use
        previous_simdir : str
          path to previous simulation
        current_result : pd.Series
          results gathered so far
        wfname : str
          unique name of Workflow

        Returns
        -------
        new_fws : list of fw
          contains Copy, Run and Analyse Fireworks
        """
        # make run FW
        ncycles_left = self.calc_remainder(previous_simdir)

        T = self['temperature']
        P = self['pressure']
        i = self['parallel_id']

        from .workflow_creator import make_runstage

        copy_fw, run_fw, analyse_fw = make_runstage(
            parent_fw=None,
            temperature=self['temperature'],
            pressure=self['pressure'],
            ncycles=ncycles_left,
            parallel_id=i,
            wfname=wfname,
            template=template,
            workdir=self['workdir'],
            previous_simdir=previous_simdir,
            previous_result=current_result.to_csv(),
            use_grid=self.get('use_grid', False),
        )

        return [copy_fw, run_fw, analyse_fw]

    def run_task(self, fw_spec):
        simtree = fw_spec['simtree']
        fmt = formats.detect_format(simtree)

        # check exit
        # will raise Error if simulation didn't finish
        finished = self.check_exit(fmt, simtree)

        # parse results
        results = self.parse_results(fmt, simtree)
        # save csv of results from *this* simulation
        utils.save_csv(results, os.path.join(simtree, 'this_sim_results.csv'))

        if self.get('previous_result', None) is not None:
            results = self.prepend_previous(self['previous_result'], results)
        # csv of results from all generations of this simulation
        utils.save_csv(results, os.path.join(simtree, 'total_results.csv'))

        if not finished:
            new_fws = self.prepare_restart(
                template=fw_spec['template'],
                previous_simdir=simtree,
                current_result=results,
                wfname=fw_spec['_category'],
            )

            return fw.FWAction(
                detours=fw.Workflow(new_fws)
            )
        else:
            parallel_id = self['parallel_id']

            return fw.FWAction(
                stored_data={'result': results.to_csv()},
                update_spec={
                    'template': fw_spec['template'],
                },
                mod_spec=[{
                    '_push': {
                        'results': (parallel_id, results.to_csv()),
                        'simpaths': (parallel_id, simtree),
                    }
                }]
            )


@xs
class Analyse(fw.FiretaskBase):
    """End of sampling stage

    Gathers together timeseries from all parallel runs

    Else:
      take off eq period
      estimate g based on eq time (g == eq)
      if enough g ran:
        finish
      else:
        issue more sampling
    """
    required_params = ['temperature', 'pressure', 'workdir', 'iteration',
                       'g_req', 'max_iterations']
    optional_params = ['use_grid']

    def prepare_resample(self, previous_simdirs, previous_results, ncycles,
                         wfname, template):
        """Prepare a new sampling stage

        Parameters
        ----------
        previous_simdirs, previous_results : dict
          mapping of parallel id to previous simulation path and results
        ncycles : int
          number of steps still required (in total across parallel jobs)
        wfname : str
          unique name for this Workflow
        template : str
          path to sim template

        Returns
        -------
        detour : fw.Workflow
          new sampling stages that must be done
        """
        from .workflow_creator import make_sampling_point

        nparallel = len(previous_simdirs)
        # adjust ncycles based on how many parallel runs we have
        ncycles = ncycles // nparallel

        runs, pps = make_sampling_point(
            parent_fw=None,
            temperature=self['temperature'],
            pressure=self['pressure'],
            ncycles=ncycles,
            nparallel=nparallel,
            wfname=wfname,
            template=template,
            workdir=self['workdir'],
            previous_results=previous_results,
            previous_simdirs=previous_simdirs,
            use_grid=self.get('use_grid', False),
            g_req=self['g_req'],
            iteration=self['iteration'] + 1,
            max_iterations=self['max_iterations'],
        )

        return fw.Workflow(runs + [pps])

    def run_task(self, fw_spec):
        timeseries = {p_id: utils.make_series(ts)
                      for (p_id, ts) in fw_spec['results']}

        g = 0.0
        g_req = self['g_req']

        means = []
        stds = []
        eqs = {}

        # starts True, turns false once a single sim wasn't equilibrated
        equilibrated = True

        for p_id, ts in timeseries.items():
            try:
                eq = analysis.find_eq(ts)
            except NotEquilibratedError:
                equilibrated &= False
            else:
                production = ts.loc[eq:]
                # how many eq periods have we sampled for?
                g += (production.index[-1] - production.index[0]) / eq
                means.append(production.mean())
                stds.append(production.std())
                eqs[p_id] = eq

        if equilibrated:
            mean = np.mean(means)
            std = np.mean(stds)
        else:
            mean, std = None, None

        # have we gathered enough data
        finished = (g > g_req)
        # Check if we've reached max iterations
        timeout = (not finished and
                   self['iteration'] + 1 >= self['max_iterations'])

        if finished or timeout:
            return fw.FWAction(
                stored_data={
                    'result': (mean, std),
                    'equilibrated': equilibrated,
                    'g': g,
                    'finished': finished,
                    'timed_out': timeout,
                },
                mod_spec=[{
                    # push the results of this condition to the Create task
                    '_push': {'results_array': (self['temperature'],
                                                self['pressure'],
                                                mean, std, g)}
                }],
            )
        else:
            # not finished, but more iterations allowed
            # perform more sampling
            if not equilibrated:
                # double previous length
                ts = list(timeseries.values())[0]
                nreq = ts.index[-1] + (ts.index[1] - ts.index[0])
                nreq *= 2
            else:
                # make educated guess
                total_steps_done = sum(timeseries[p_id].index[-1] - eqs[p_id]
                                       for p_id in timeseries)
                # how many steps for n+1 g?
                nreq = int(total_steps_done / g * (g_req + 1))

            return fw.FWAction(
                stored_data={
                    'equilibrated': equilibrated,
                    'g': g,
                    'finished': finished,
                    'timed_out': timeout,
                },
                detours=self.prepare_resample(
                    previous_simdirs={p_id: path
                                      for (p_id, path) in fw_spec['simpaths']},
                    previous_results={p_id: ts.to_csv()
                                      for (p_id, ts) in timeseries.items()},
                    ncycles=nreq,
                    wfname=fw_spec['_category'],
                    template=fw_spec['template'],
                ),
            )


@xs
class IsothermCreate(fw.FiretaskBase):
    """From all results, create final answer of the isotherm"""
    optional_params = ['workdir']

    def run_task(self, fw_spec):
        # create sorted version
        results = sorted(fw_spec['results_array'],
                         key=lambda x: (x[0], x[1]))

        outfile = os.path.join(self.get('workdir', ''), 'results.csv')
        with open(outfile, 'w') as out:
            out.write('temperature,pressure,mean,std,g\n')
            for row in results:
                out.write(','.join(str(val) for val in row))
                out.write('\n')

        return fw.FWAction(
            stored_data={'final_result': results}
        )

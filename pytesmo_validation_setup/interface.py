# Copyright (c) 2016, Vienna University of Technology (TU Wien), Department
# of Geodesy and Geoinformation (GEO).
# All rights reserved.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL VIENNA UNIVERSITY OF TECHNOLOGY,
# DEPARTMENT OF GEODESY AND GEOINFORMATION BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
This module represents the interface to the WARP processing functions.
"""

import time
import os
import imp

import numpy as np
import ipyparallel as p
from ipyparallel import interactive

from pytesmo.validation_framework.results_manager import netcdf_results_manager


def s_validation(path_setup=None):
    """
    Single processing interface for validation.

    Parameters
    ----------
    cfg_file : str
        File name of the config file.
    subset : str
        Process only a subset of WARP validation steps.
    """
    if path_setup is not None:
        # import validation setup
        fname = os.path.basename(path_setup)
        mname, ext = os.path.splitext(fname)
        val_module = imp.load_source(mname, path_setup)
        jobs, process = val_module.setup_process()
        results_path = '/data-write/RADAR/Validation_FFascetti/'
        for job in jobs:
            results = process.calc(job)
            netcdf_results_manager(results, results_path)

@interactive
def func(job):
    """
    Function which calls the start_processing method implemented in setup_code.
    """
    return start_process(job)

def create_index_list(n_engines, n_list):
    n_index = np.ceil(np.float64(n_list) / np.float64(n_engines))
    index = np.array_split(np.arange(n_index*n_engines, dtype=np.int32), n_engines)
    # index = np.vstack(index)
    # index = np.ravel(index, order='F')
    index = np.ma.masked_greater_equal(index, n_list)

    # return index.compressed()
    return index

def p_validation(path_setup=None):
    """
    Parallel processing interface for validation.

    Parameters
    ----------
    path_setup : str
        Path to setup file which needs to be executed for validation.
    """
    # get ipyparallel client
    c = p.Client()
    dv = c[:]
    n_engines = len(dv)

    # prevent numpy from multithreading
    dv.execute("import os")
    dv.execute("os.environ['MKL_NUM_THREADS']='1'")
    dv.execute("os.environ['OMP_NUM_THREADS']='1'")
    dv.execute("os.environ['MKL_DYNAMIC']='FALSE'")

    # lview = c.load_balanced_view()

    # Push  Validation setup to engines
    if path_setup is not None:
        dv.run(path_setup, block=True)
    else:
        raise ValueError('Validation setup file missing.')

    jobs = None
    try:
        jobs = dv.pull('jobs', targets=0, block=True)
    except p.CompositeError:
        print("Variable 'jobs' is not defined!")

    results_path = '/data-write/RADAR/Validation_FFascetti/'

    if (jobs is not None) and (results_path is not None):
        # re-arange job list to avoid cell reading conflicts
        n_jobs = len(jobs)
        job_index_list = create_index_list(n_engines, n_jobs)
        n_runs = job_index_list.shape[1]
        
        # start validation
        for runi in np.arange(n_runs):
            cur_jobs = jobs[job_index_list[:,runi].compressed()]
            amr = dv.map(func, cur_jobs)
            while amr.ready() is False:
                time.sleep(1)
            for i, result in enumerate(amr):
                netcdf_results_manager(result, results_path)

            print("Start Run {:}".format(runi))

            dv.results.clear()
            c.results.clear()
            c.purge_everything()

    c.purge_everything()
    dv.clear()
    c.close()

if __name__ == '__main__':
    setup_path = '/home/cre/myGit/pytesmo_validation_setup/pytesmo_validation_setup/lsm_abs_quad.py'
    #s_validation(path_setup=setup_path)
    p_validation(path_setup=setup_path)


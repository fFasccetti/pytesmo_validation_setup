from datetime import datetime
import os
import rsdata.root_path as root

from rsdata.SMOS.interface import Smudp2_620_Ts
from rsdata.ECMWF.interface import ERALAND_g2ze
from pynetcf.time_series import GriddedNcContiguousRaggedTs
from pygrids.warp5 import DGGv21CPv20_ind_ld

from pytesmo.validation_framework.temporal_matchers_ControloTimeERA import BasicTemporalMatching
from pytesmo.validation_framework.validation_Ini import Validation

# To analyze absolute soil moisture values
from pytesmo.validation_framework.lsm_preparation_ss import DataPreparationTC, BasicMetricsTC
# # To analyze anomaly soil mositure values
# # from pytesmo.validation_framework.lsm_preparation import DataPreparationTC, BasicMetricsTC

#from pytesmo.io.sat.ascat import AscatNetcdf as ascat_net
#from pytesmo.io.sat.ascat import AscatH25_SSM

def start_process(job):
    try:
        return process.calc(job)
    except RuntimeError:
        return process.calc(job)
    return job

def setup_process():

    global results_path
    global jobs
    global process

    smos_reader = Smudp2_620_Ts(path='/home/ffascett/shares/radar/Datapool_processed/SMOS/SMUDP2_620_2010_2011_v1/')

    path_data_era = os.path.join(root.r, 'Datapool_processed', 'ECMWF_reanalysis', 'ERA_Interim_Land', 'datasets', 'netcdf')
    path_grid_era_file = os.path.join(root.r, 'Datapool_processed', 'ECMWF_reanalysis', 'ERA_Interim_Land', 'ancillary', 'grid', 'eraArray_grid_subset.nc')
    era_reader = ERALAND_g2ze(path=path_data_era, parameter='sm_era', grid_info_path=path_grid_era_file)

    ers_folder = os.path.join(root.r, 'Datapool_processed', 'WARP', 'WARP5.6', 'IRE21_WARP56_P1', 'R1', '080_ssm','netcdf_new')
    #ers_grid_folder = os.path.join('/home','ffascett','shares','radar','Datapool_processed','WARP','ancillary','warp5_grid')
    #grid_ers = ascat_net(ers_folder,ers_grid_folder,grid_info_filename='TUW_WARP5_grid_info_2_1.nc')
    #grid_ers._load_grid_info()
    grid_ers = DGGv21CPv20_ind_ld()
    ers_reader = GriddedNcContiguousRaggedTs(parameters=['sm', 'proc_flag', 'corr_flag', 'ssf'], path=ers_folder, grid=grid_ers)


    datasets = {'SMOS': {'class':smos_reader,'columns':['Soil_Moisture'],'type':'reference','args':[],'kwargs':{}},
                'ERS': {'class':ers_reader,'columns':['sm'],'type': 'other', 'args':[],'kwargs':{},'grids_compatible':False,'use_lut': False,'lut_max_dist':15000},
                'ERA': {'class':era_reader,'columns':['sm_era'],'type':'other','args':[],'kwargs':{},'grids_compatible':False,'use_lut': False,'lut_max_dist':15000}}


    period = [datetime(2010,01,01),datetime(2011,12,31)]
    window = 8./24.
    scaling = None

    mc = BasicMetricsTC()
    dp = DataPreparationTC()

    tm = BasicTemporalMatching(window=window,reverse=False)

    process = Validation(datasets=datasets, data_prep=dp,temporal_matcher=tm,scaling=scaling,
                         scale_to_other=False,metrics_calculator=mc,period=period,cell_based_jobs=True,
                         triple=1,matching_together=1)

    jobs = process.get_processing_jobs()

    return jobs, process

if __name__ == '__main__':

    from pytesmo.validation_framework.results_manager import netcdf_results_manager
    import numpy as np
    setup_process()


    compact_results = start_process(jobs)



    print len(compact_results)

    save_path = '/home/ffascett/Desktop/provaTC/controlTime/'
    netcdf_results_manager(compact_results, save_path)

    print 'finish'


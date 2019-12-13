#!/usr/bin/env python2.7

"""
Script to analyse the observations that get integrated into the data assimilation process, for a suite run

Created by Elliott Warren - Wed 11th Dec 2019: elliott.warren@metoffice.gov.uk
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import subprocess
import datetime as dt

import ellUtils as eu


def find_obs_files(cycle, model_run='glu'):
    """
    Find the lsit of instruments used in the DA by looking to see which ODB2 files are present in MASS.
    Assume the cycle chosen represents all cycles, and extract the list of instruments from the filepaths from
    this cycle.

    Assumes file format in the style of: 'moose:/devfc/[suite-id]/adhoc.file/20190615T0600Z_glu_groundgps_odb2.gz'
    :param cycle: (datetime) cycle to get the instruments from
    :keyword model_run: ('glu' or 'glm')
    :return: instrument_list: (list of strings) instrument list that get used in the DA
    """

    # ensure model_run keyword is set properly to 'glu' or 'glm'
    if model_run not in ['glu', 'glm']:
        raise ValueError('model_run keyword argument set as {0}. Must be set as \'glu\' or'
                         ' \'glm\''.format(model_run))

    cycle_first_datestr = cycle.strftime('%Y%m%dT%H%MZ')
    s = 'moo ls moose:/devfc/u-bo798/adhoc.file/' + cycle_first_datestr + '_' + model_run + '*_odb2.gz'
    out = subprocess.check_output(s, shell=True)  # output all in one string
    # split filepaths by \n. End element is empty therefore do not keep it in the split
    files = out.split('\n')[:-1]

    return files

if __name__ == '__main__':

    # ==============================================================================
    # Setup
    # ==============================================================================

    # directories
    HOME = os.getenv('HOME')
    DATADIR = os.getenv('DATADIR')
    SCRATCH = os.getenv('SCRATCH')

    projectdir = DATADIR + '/R2O_projects/update_cutoff'
    datadir = projectdir + '/data'
    plotdir = projectdir + '/figures'
    scratchdir = SCRATCH + '/ODB2'
    numpysavedir = scratchdir + '/cycle_sql_stats'


    # suite dictionary
    # key = ID, value = short name
    suite_list = {'u-bo976': 'CTRL',  # Control, Update = 6 hours 15 mins
                  # 'u-bp725': 'U715',  # Update = 7 hours 15 mins (ran later, therefore less data than the others)
                  'u-bo895': 'U5',  # Update = 5 hours
                  'u-bo798': 'U4',  # Update = 4 hours
                  'u-bo862': 'U3',  # Update = 3 hours
                  #'u-bo857': 'M10'  # Main run = 2 hours 30 (-10 minutes) - needs to have glm not glu in mass file
                  }

    # date ranges to loop over

    start_date = dt.datetime(2019, 6, 15, 6, 0, 0)
    end_date = dt.datetime(2019, 9, 15, 18, 0, 0)
    cycle_range = eu.date_range(start_date, end_date, 6, 'hours')
    cycle_range_str = [i.strftime('%Y%m%d') for i in cycle_range]

    # ensure SCRATCH subdirectories are present for the ODB stats to be copied into, before further processing
    for d in [scratchdir, numpysavedir]:
        os.system('mkdir -p '+d)

    # setup statistics dictionary (suite => cycle)
    stats = {'tot_active':
                {suite_i:
                    {cycle_c: {} for cycle_c in cycle_range_str}
                 for suite_i in suite_list.iterkeys()
                }
            }

    # loop through all suite, then plot the cross-suite statistics after the looping
    for suite_id in suite_list.iterkeys():

        # Go through each cycle in turn
        for c, cycle_c in enumerate(cycle_range):

            # create cycle's stats array that will be numpy saved!
            # separate stats for suite and cycle encase more suites or cycles are added later
            suite_cycle_stats = {'active_per_obs_type': {}}

            # get obs filepaths for this cycle
            # ToDO - could be a waste of time to check each cycle. Option for 1 check and make file paths from then on?
            obs_filelist = find_obs_files(cycle_c, model_run='glu')

            # Instrument is the 2nd to last entry. Extract for all files at once as they follow the same naming convention
            obs_list = [f.split('_')[-2] for f in obs_filelist]

            ## is an entry waiting for the final value, in the dictionary/np.array?
            ## does this cycle exist
            #### has the last 4 or so cycles exist - if not assume the model hasn't gotten this far yet and 'break' loop

            ## is data there from mass?

            # get ODB data for each instrument in turn, as the files can be very large!
            # loop through its moose path and the paired observation name
            for obs_moosepath_i, obs_i in zip(obs_filelist, obs_list):

                # download ODB stats into the correct directory
                s = 'moo get '+obs_moosepath_i+' '+scratchdir
                os.system(s)

                # get the filepath after extraction from MASS
                filepath = scratchdir+'/'+obs_moosepath_i.split('/')[-1]

                ## assume all observation files are present with each cycle
                ## ungzip them
                os.system('gunzip '+filepath)

                # name of file without the .gz extension
                filepath_unzipped = filepath[:-3]


                # count number of observations that were included in the data assimilation,
                #   for this ob type, cycle, suite.
                s = 'odb sql \'select count(*) where datum_status.active \' -i '+filepath_unzipped
                out = subprocess.check_output(s, shell=True)

                # strip value from output string
                # remove leading spacing and end-of-line characters
                split = out.strip(' ').split('\n')
                value = float(split[1])

                # append data to stats dictionary
                suite_cycle_stats['active_per_obs_type'][obs_i] = value


                s = 'odb sql \'select count(*) where (datum_status.active) \' -i '+filepath_unzipped


                # remove file once its done with
                os.remove(filepath_unzipped)

            # summary stats (e.g. total active)
            suite_cycle_stats['total_active'] = np.sum(suite_cycle_stats['active_per_obs_type'].flatten())

            # numpy save this cycle's statistics
            cycle_c_str = cycle_range_str[c]
            numpysavepath = numpysavedir + '/' + cycle_c_str + '_stats.npy'
            np.save(numpysavepath, suite_cycle_stats)



        # summary stats
        #summary = np.nansum(stats[suite_id][cycle_i].flatten())
        #average_cross_cycle = np.nanmean(summary[suite_id])

        # plot all suite data
        # inc. total number of obs ingested vs update time
        # inc. total number of obs ingested vs update time by region (e.g. SH, NH, Europe)


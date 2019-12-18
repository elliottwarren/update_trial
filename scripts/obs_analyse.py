#!/usr/bin/env python2.7

"""
Script to analyse the observations that get integrated into the data assimilation process, for a suite run

Ensure PATH=$PATH:~odb/installs/odbapi/odbapi-0.10.3-ukmo-v2/gnu-4.4.7/bin is ran in the shell first!

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


def sql_count_all_query(s):
    """
    SQL count query on an SQL database, from a list of regions.

    :param s: sql count query statement
    :return: output (float): output value from the count query
    """

    # count number of observations that were included in the data assimilation,
    #   for this ob type, cycle, suite.
    # strip value from output string
    # remove leading spacing and end-of-line characters
    out = subprocess.check_output(s, shell=True)
    split = out.strip(' ').split('\n')

    return float(split[1])


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
    logdir = scratchdir + '/log'
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

    # # update trial start and end dates
    #start_date = dt.datetime(2019, 6, 15, 6, 0, 0)
    #end_date = dt.datetime(2019, 9, 15, 18, 0, 0)

    # date ranges to loop over if in a suite
    #start_date_in=$(rose date -c -f %Y%m%d%H%M)

    start_date_in = ['201906150600']
    end_date_in = ['201906151200']

    start_date = eu.dateList_to_datetime(start_date_in)[0]
    end_date = eu.dateList_to_datetime(end_date_in)[0]

    cycle_range = eu.date_range(start_date, end_date, 6, 'hours')
    cycle_range_str = [i.strftime('%Y%m%dT%H%M') for i in cycle_range]

    # ensure SCRATCH subdirectories are present for the ODB stats to be copied into, before further processing
    for d in [scratchdir, logdir, numpysavedir]:
        if not os.path.exists(d):
            os.system('mkdir -p '+d)

    # flag headers to check for and create statistics about
    flags = ['active', 'rejected']

    # regions to create statistic entries for
    regions = ['SH', 'NH', 'TR', 'global']

    # create empty log file that will be filled with filepaths of bad files, if any are present
    run_time_str = dt.datetime.now().strftime('%Y%m%dT%H%M')
    log_file_path = logdir + '/' + run_time_str + '_obs_anaylse_log.txt'
    with open(log_file_path, 'w') as log_file:
        log_file.write('log for obs_analyse - ran at '+run_time_str+'/n')

    # ==============================================================================
    # Process
    # ==============================================================================

    # loop through all suite, then plot the cross-suite statistics after the looping
    for suite_id in suite_list.iterkeys():

        print 'working suite-id: '+suite_id

        # Go through each cycle in turn
        for c, cycle_c in enumerate(cycle_range):

            # only continue if saves statistics do no exist already, or are to be overwritten

            print '... working cycle: '+cycle_range_str[c]

            # create cycle's stats array that will be numpy saved!
            # separate stats for suite and cycle encase more suites or cycles are added later
            # dictionary format will be: suite_cycle_stats[flag_i][region_i]
            #   and after sql queries for each obs type, will eventually be:
            #   suite_cycle_stats[flag_i][region_i][obs] = value
            suite_cycle_stats = {flag_i:
                                     {region_i: {} for region_i in regions}
                                 for flag_i in flags
                                 }

            # get obs filepaths for this cycle
            # use 'glu' (update run) as this is where the number of obs going in is varying, despite the impact being
            #   on 'glm' (main run).
            # ToDO - could be a waste of time to check each cycle. Option for 1 check and make file paths from then on?
            obs_filelist = find_obs_files(cycle_c, model_run='glu')

            # Instrument is the 2nd to last entry. Extract for all files at once as they follow the same naming convention
            obs_list = [f.split('_')[-2] for f in obs_filelist]

            ## is an entry waiting for the final value, in the dictionary/np.array?
            ## does this cycle exist
            #### has the last 4 or so cycles exist - if not assume the model hasn't gotten this far yet and 'break' loop

            # get ODB data for each instrument in turn, as the files can be very large!
            # loop through its moose path and the paired observation name
            for obs_moosepath_i, obs_i in zip(obs_filelist, obs_list):

                # create observation entries for all obs if they do not yet exist


                print '... ... working on obs: '+obs_i

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

                # try to do SQL queries but if the file is corrupt, the querries will fail.
                # If file is corrupt - catch exception, remove bad file and add it to a log of bad filenames
                try:

                    # header flags to check for in ODB databases
                    for flag_i in flags:

                        print '... ... ... working on flag: '+flag_i

                        # count number of observations that were included in the data assimilation,
                        #   for this ob type, cycle, suite.

                        # Southern hemisphere
                        statement = 'odb sql \'select count(*) where (datum_status.'+flag_i+') and (lat <= \'0\') \' -i '+filepath_unzipped
                        suite_cycle_stats[flag_i]['SH'][obs_i] = sql_count_all_query(statement)

                        # # test alternative for SH
                        # statement = 'odb sql \'select count(case (datum_status.'+flag_i+') and (lat <= \'0\')) \' -i '+filepath_unzipped
                        # suite_cycle_stats[flag_i]['SH'][obs_i] = sql_count_all_query(statement)

                        # save NH location for later?
                        statement = 'odb sql \'select @NH := where lat >= \'0\'\' -i ' + filepath_unzipped
                        out = subprocess.check_output(statement, shell=True)
                        split = out.strip(' ').split('\n')

                        # Northern hemisphere
                        statement = 'odb sql \'select count(*) where (datum_status.'+flag_i+') and (lat >= \'0\') \' -i '+filepath_unzipped
                        suite_cycle_stats[flag_i]['NH'][obs_i] = sql_count_all_query(statement)

                        # Tropics are 20 N to 20 S
                        statement = 'odb sql \'select count(*) where (datum_status.'+flag_i+') and (lat < \'20\' and lat > \'-20\') \' -i '+filepath_unzipped
                        suite_cycle_stats[flag_i]['TR'][obs_i] = sql_count_all_query(statement)

                        # global
                        suite_cycle_stats[flag_i]['global'][obs_i] = \
                            suite_cycle_stats[flag_i]['NH'][obs_i] + suite_cycle_stats[flag_i]['SH'][obs_i]

                        # delete from SQL the active flags?

                except:
                    print '/n/n!!!'+filepath_unzipped +' is a bad file!!!/n/n'
                    # add bad file to the log
                    with open(log_file_path, 'a') as log_file:
                        log_file.write(filepath_unzipped+'/n')

                # remove file once its done with (whether a good or bad file)
                os.remove(filepath_unzipped)

            print '... ... computing observation totals, across flags'

            # after all observation values have been acquired for all the flags.
            for flag_i in flags:
                for region_i in regions:
                    suite_cycle_stats[flag_i][region_i]['all_obs'] = \
                        np.sum([suite_cycle_stats[flag_i][region_i][obs_j] for obs_j in obs_list])

            print '... ... observation totals completed!'

            # numpy save this suite and cycle's statistics
            cycle_c_str = cycle_range_str[c]
            numpysavepath = numpysavedir + '/' + cycle_c_str + '_'+suite_id+'_stats.npy'
            np.save(numpysavepath, suite_cycle_stats)

            print '... ... '+numpysavepath+' saved!'
            print '/n/n/n'

    exit(0)



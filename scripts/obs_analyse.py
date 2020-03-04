#!/usr/bin/env python2.7

"""
Script to analyse the observations that get integrated into the data assimilation process, for a suite run

Ensure PATH=$PATH:~odb/installs/odbapi/odbapi-0.10.3-ukmo-v2/gnu-4.4.7/bin is ran in the shell first!

Created by Elliott Warren - Wed 11th Dec 2019: elliott.warren@metoffice.gov.uk
"""

import numpy as np
import os
import subprocess
import datetime as dt

# ==============================================================================
# Setup
# ==============================================================================

# directories
HOME = os.getenv('HOME')
DATADIR = os.getenv('DATADIR')
SCRATCH = os.getenv('SCRATCH')
THIS_CYCLE = os.getenv('THIS_CYCLE')
SUITE_I = os.getenv('SUITE_I')

THIS_CYCLE = os.getenv('CYLC_TASK_CYCLE_POINT')

# suite dictionary
# key = ID, value = short name
# offline
suite_list = {'u-bo796': 'CTRL',  # Control, Update = 6 hours 15 mins
              # 'u-bp725': 'U715',  # Update = 7 hours 15 mins (ran later, therefore less data than the others)
              'u-bo895': 'U5',  # Update = 5 hours
              'u-bo798': 'U4',  # Update = 4 hours
              'u-bo862': 'U3',  # Update = 3 hours
              # 'u-bo857': 'M10'  # Main run = 2 hours 30 (-10 minutes) - needs to have glm not glu in mass file
              }

# # update trial start and end dates
# start_date = dt.datetime(2019, 6, 15, 6, 0, 0)
# end_date = dt.datetime(2019, 9, 15, 18, 0, 0)

# date ranges to loop over if in a suite
# start_date_in=$(rose date -c -f %Y%m%d%H%M)

if THIS_CYCLE is None:

    # # offline 1
    # import ellUtils as eu
    # start_date_in = ['201906151200']
    # end_date_in = ['201906151200']
    # start_date = eu.dateList_to_datetime(start_date_in)[0]
    # end_date = eu.dateList_to_datetime(end_date_in)[0]
    # cycle_range = eu.date_range(start_date, end_date, 6, 'hours')
    # cycle_range_str = [i.strftime('%Y%m%dT%H%MZ') for i in cycle_range]

    # offline 2
    THIS_CYCLE = '20190615T1800Z'
    cycle_range = [dt.datetime.strptime(THIS_CYCLE, '%Y%m%dT%H%MZ')]
    cycle_range_str = [i.strftime('%Y%m%dT%H%MZ') for i in cycle_range]
    suite_iter_list = suite_list.keys()
else:

    # online
    #cycle_range = [dt.datetime.strptime(THIS_CYCLE, '%Y%m%d%H%M')]
    print 'THIS_CYCLE = '+THIS_CYCLE  #  20190615T0600Z
    cycle_range = [dt.datetime.strptime(THIS_CYCLE, '%Y%m%dT%H%MZ')]
    cycle_range_str = [i.strftime('%Y%m%dT%H%MZ') for i in cycle_range]
    suite_iter_list = [SUITE_I]
    print '\n\n\nscript ran in online mode!\n\n\n'

# flag headers to check for and create statistics about
# Note: needs to match the loop further down
# ToDo have loop inside linked to this list.
flags = ['active', 'rejected', 'thinned', 'thinned_but_active']

# regions to create statistic entries for
regions = ['SH', 'NH', 'TR', 'AUS', 'EUR']

# regional boundaries and the SQL query into its location
# SQL query entry NOT for global as this will be done as the sum of NH and SH, and added later!
region_bounds = {
           'NH': 'sum(lat > 0)',
           'SH': 'sum(lat < 0)',
           'TR': 'sum(20 > lat > -20)',
           'EUR': 'sum((70 > lat > 25) and (28 > lon > -10))',
           'AUS': 'sum((-8 > lat > -45) and (157 > lon > 106))'
}

# override the cycle statistics?
OVERRIDE_CYCLE_STATS = True


def find_obs_files(cycle_str, suite_id, model_run='glu'):
    """
    Find the lsit of instruments used in the DA by looking to see which ODB2 files are present in MASS.
    Assume the cycle chosen represents all cycles, and extract the list of instruments from the filepaths from
    this cycle.

    Assumes file format in the style of: 'moose:/devfc/[suite-id]/adhoc.file/20190615T0600Z_glu_groundgps_odb2.gz'
    :param cycle_str: (str: cycle.strftime('%Y%m%dT%H%MZ')) cycle to get the instruments from
    :keyword model_run: ('glu' or 'glm')
    :return: instrument_list: (list of strings) instrument list that get used in the DA
    """

    # ensure model_run keyword is set properly to 'glu' or 'glm'
    if model_run not in ['glu', 'glm']:
        raise ValueError('model_run keyword argument set as {0}. Must be set as \'glu\' or'
                         ' \'glm\''.format(model_run))
    #/opt/ukmo/mass/moose-client-wrapper/bin/
    s = 'moo ls moose:/devfc/'+suite_id+'/adhoc.file/' + cycle_str + '_' + model_run + '*_odb2.gz'
    out = subprocess.check_output(s, shell=True)  # output all in one string
    # split filepaths by \n. End element is empty therefore do not keep it in the split
    files = out.split('\n')[:-1]

    return files


def moo_ODB2_get_gunzip_file(moosepath, destdir):
    """
    moo get and gunzip an ODB2 file from MASS.
    :param moosepath: full path of ODB2 file on MASS
    :param destdir: where to put the file
    :return: filepath_unzipped: unzipped filepath
    """

    # download ODB stats into the correct directory
    s = 'moo get ' + moosepath + ' ' + destdir
    os.system(s)

    # get the filepath after extraction from MASS
    filepath = scratchdir + '/' + moosepath.split('/')[-1]

    ## assume all observation files are present with each cycle
    ## ungzip them
    os.system('gunzip ' + filepath)

    # name of file without the .gz extension
    filepath_unzipped = filepath[:-3]

    return filepath_unzipped


def sql_ODB2_select_query(region_bounds, regions, filepath):

    """
    Create and carry out SQL query on ODB dataase
    :param region_bounds: the SQL query part that has the boundaries of the region in it
    :param regions: the regions that match region_bounds
    :param filepath: ODB2 filepath
    :return: out_array: (numpy array, dtype=float) output from the SQL query
    """

    # construct statement from regions_boundaries, based on the list order of [regions],
    #  to ensure the SQL output and regions list match up
    loc_bound_query_part = ', '.join([region_bounds[loc] for loc in regions])
    # Add: where(entryno=1) for unique observations if you want to (some obs come in twice and get updated...)
    #   hopefully having entro=1 wont screw up the 'rejected' query by removing overlapping obs ahead of time...
    # statement = 'odb sql \'select datum_status.active, ops_report_flags.surplus, ' + loc_bound_query_part + ' where(entryno=1) \' -i ' + filepath
    #   do not use where(entryno=1) as later duplicate observations (entryno !=1), might become the active observation
    statement = 'odb sql \'select datum_status.active, ops_report_flags.surplus, ' + loc_bound_query_part + '\' -i ' + filepath
    out = subprocess.check_output(statement, shell=True)

    # ignore the input statement command and the empty string at the end
    out_split = out.split('\n')[1:-1]
    # in each row, remove leading spaces and split by tab to reveal the parts of each query combination
    #   e.g. datum_status.active=1 and ops_report_flags.surplus=1, where surplus is the same as being
    #   thinned
    out_array = np.array([n.replace(' ', '').split('\t') for n in out_split], dtype=np.float32)

    return out_array


def file_error_write(obs_file, log_file):

    """
    Exclaim error and write the filepath of the bad file, to a log for later
    :param obs_file:
    :param log_file:
    :return:
    """

    print '\n\n!!!' + obs_file + ' is a bad file!!!\n\n'
    # add bad file to the log
    with open(log_file, 'a') as log:
        log.write(obs_file + '\n')
    return


def extract_flag_data(suite_cycle_stats, out_array, regions, obs_i):

    """
    Extract the data from out_array
    :param suite_cycle_stats:
    :param regions:
    :param obs_i:
    :return:
    """

    # find correct row for the extraction - as sometimes some combinations do not exist and the number
    #   of rows reported changes!
    # check the variable [out_split] for human readable output and decide which indexing is needed
    active_col = out_array[:, 0]
    thinned_col = out_array[:, 1]

    # flag idx values
    # thinned but somehow active? (seems to be a thing for surface obs...)
    flag_idx = {'active': np.where((active_col == 1.0) & (thinned_col == 0.0))[0],
                'rejected': np.where(active_col == 0.0)[0],  # simply not active
                'thinned': np.where((active_col == 0.0) & (thinned_col == 1.0))[0],  # specific flag for data thinning
                'thinned_but_active': np.where((active_col == 1.0) & (thinned_col == 1.0))[0]}

    # extract and sum up all the relevent columns, for each region and flag where necessary.
    # Some flags combinations are missing from some files, therefore this will set them as np.nan
    for flag_i, flag_idx_i in flag_idx.iteritems():
        if flag_idx_i.size > 0:  # works if idx is length 1 or more
            for i, region_i in enumerate(regions):
                suite_cycle_stats[flag_i][region_i][obs_i] = np.sum(out_array[flag_idx_i, i + 2])
        else:  # if flag is not present for this ob
            for i, region_i in enumerate(regions):
                suite_cycle_stats[flag_i][region_i][obs_i] = 0.0

    # global total per flag
    for flag_i, flag_data in suite_cycle_stats.iteritems():
        suite_cycle_stats[flag_i]['GLOBAL'][obs_i] = \
            np.sum([flag_data['NH'][obs_i], flag_data['SH'][obs_i]])

    return


def create_metadata_num_files(obs_list, stats, flags, regions):
    """
    Create some simple metadata on the number of files used in the suite_cycle_stats, compared to the
    number of files on MASS. This is to help identify if some observation files were missing, alongside
    the log file.
    :param obs_list: all observation files that were present on MASS
    :param stats: statistics generated from the ODB2 files
    :param flags: things to look for in the ODB2 files, e.g. if active, if thinned
    :param regions: locations where to look for the flags (e.g. SH, NH)
    :return: meta: (dictionary) the metadata
    """

    meta = {}
    meta['number_obs_files_on_mass'] = len(obs_list)
    meta['number_obs_used_in_stats'] = len(stats[flags[0]][regions[0]].keys())

    # Flag for whether the 'total_stats' do include all the observations, from all the files, used in
    #   the DA.
    # If stats were made for all obs file ok, then set flag = 1
    # If some obs are missing, because the files were bad or missing, then set flag = 0
    # Note: if an obs type is missing, it will be missing in all flags and regions, therefore arbitrarily
    #   use the first flag and region to test this.
    if len(stats[flags[0]][regions[0]].keys()) == obs_list:
        meta['all_obs_files_ok'] = True
    else:
        meta['all_obs_files_ok'] = False

    return meta


if __name__ == '__main__':

    # ==============================================================================
    # Process
    # ==============================================================================

    # loop through all suite, then plot the cross-suite statistics after the looping
    # for suite_id in  ['u-bo976']: # suite_list.iterkeys():  # if running multiple suites in one script (offline)
    for suite_id in suite_iter_list:  # online

        print 'working suite-id: '+suite_id

        # suite id specific directories
        scratchdir = SCRATCH + '/ODB2/'+suite_id
        logdir = scratchdir + '/log'
        numpysavedir = DATADIR + '/R2O_projects/update_cutoff/data/cycle_sql_stats/'+suite_id

        # ensure scratch and save subdirectories are present for the ODB stats to be copied into, before further processing
        for d in [scratchdir, logdir, numpysavedir]:
            if not os.path.exists(d):
                os.system('mkdir -p '+d)

        # Go through each cycle in turn
        for c, cycle_c_str in enumerate(cycle_range_str):

            # create empty log file that will be filled with filepaths of bad files, if any are present
            run_time_str = dt.datetime.now().strftime('%Y%m%dT%H%M')
            log_file_path = logdir + '/' + suite_id + '_'+ cycle_c_str + '_obs_anaylse_log.txt'
            with open(log_file_path, 'w') as log_file:
                log_file.write('log for obs_analyse - ran at ' + run_time_str + '\n')

            # create numpy save path here to check whether it already exists. If so and OVERRIDE_CYCLE_STATS
            # is set to True, then skip this cycle.
            # only continue if saves statistics do no exist already, or are to be overwritten
            numpysavepath = numpysavedir + '/' + cycle_c_str + '_'+suite_id+'_stats.npy'
            if os.path.exists(numpysavepath) and (OVERRIDE_CYCLE_STATS == False):
                print numpysavepath + ' already exists! Skipping this cycle\n\n\n'
                exit(0)

            print '... working cycle: '+cycle_c_str

            # create cycle's stats array that will be numpy saved!
            # After sql queries for each obs type, will eventually be: suite_cycle_stats[flag_i][region_i][obs] = value
            # Add an extra entry for 'GLOBAL' on top of the regions, as although it doesn't get called in the SQL query,
            #   it is calculated at the end separately 
            suite_cycle_stats = {flag_i:
                                     {region_i: {} for region_i in regions + ['GLOBAL']}
                                 for flag_i in flags}

            # get obs filepaths for this cycle
            # use 'glu' (update run) as this is where the number of obs going in is varying, despite the impact being
            #   on 'glm' (main run).
            obs_filelist = find_obs_files(cycle_c_str, suite_id, model_run='glu')

            # are there any observations files for this cycle? Cycle may not have run yet
            if len(obs_filelist) == 0:
                print 'no observation files present for cycle: '+cycle_c_str+'\n\n\n'
                continue

            # Instrument is the 2nd to last entry. Extract for all files at once as they follow the same naming convention
            obs_list = [f.split('_')[-2] for f in obs_filelist]

            ##  does this cycle exist

            # get ODB data for each instrument in turn, as the files can be very large!
            # loop through its moose path and the paired observation name
            for obs_moosepath_i, obs_i in zip(obs_filelist, obs_list):

            # testing
            # for obs_moosepath_i, obs_i in zip(obs_filelist[:2], obs_list[:2]):
            #     obs_moosepath_i = obs_filelist[6]
            #     obs_i = obs_list[6]

                print '... ... ('+str(obs_list.index(obs_i)+1)+'/'+str(len(obs_list))+') working on obs: '+obs_i

                obd_odb2_filepath = moo_ODB2_get_gunzip_file(obs_moosepath_i, scratchdir)

                # try to do SQL queries but if the file is corrupt, the queries will fail.
                # If file is corrupt - catch exception, remove bad file and add it to a log of bad file names
                try:

                    print '... ... ... working on SQL queries'

                    # count number of observations that were 'active' and were'thinned' in the data assimilation,
                    #   for this ob type, cycle, suite.
                    # Pro-tip! Have as much as you can in a single query to save computation time
                    out_array = sql_ODB2_select_query(region_bounds, regions, obd_odb2_filepath)

                    print '... ... ... ODB2_select_query successful'

                    # extract out data based on the flags
                    #print suite_cycle_stats
                    extract_flag_data(suite_cycle_stats, out_array, regions, obs_i)
                    #print suite_cycle_stats

                    print '... ... ... extract_flag_data successful'

                except:

                    # write bad filename to the log
                    file_error_write(obd_odb2_filepath, log_file_path)

                # remove file once its done with (whether a good or bad file)
                if os.path.exists(obd_odb2_filepath):
                    os.remove(obd_odb2_filepath)

            print '... ... computing observation totals, across flags'

            # store number of obs files present from MASS and stats, and whether the two values are equal
            suite_cycle_meta = create_metadata_num_files(obs_list, suite_cycle_stats, flags, regions)

            # after all observation values have been acquired for all the flags, if present
            # This will make the number of keys in region_i, one more than the number of obs files
            for flag_i in suite_cycle_stats.iterkeys():
                for region_i, region_i_data in suite_cycle_stats[flag_i].iteritems():
                    suite_cycle_stats[flag_i][region_i]['all_obs'] = \
                        np.sum([region_i_data[obs_j] for obs_j in region_i_data.iterkeys()])

            print '... ... observation totals completed!'

            # numpy save this suite and cycle's statistics
            save_dict = {'suite_cycle_stats': suite_cycle_stats,
                         'suite_cycle_meta': suite_cycle_meta,
                         'cycle': cycle_c_str}
            np.save(numpysavepath, save_dict)

            print '... ... '+numpysavepath+' saved!'
            print '\n\n\n'

    exit(0)



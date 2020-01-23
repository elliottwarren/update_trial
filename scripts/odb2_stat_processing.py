#!/usr/bin/env python2.7

"""
Script to process, analyse and plot the ODB2 statstics created from the obs_analyse.py script.

Created by Elliott Warren - Wed 15th Jan 2020: elliott.warren@metoffice.gov.uk
"""

import numpy as np
import os
import subprocess
import datetime as dt
import ellUtils as eu
import matplotlib.pyplot as plt

# ==============================================================================
# Setup
# ==============================================================================

# directories
HOME = os.getenv('HOME')
DATADIR = os.getenv('DATADIR')

SAVEDIR = DATADIR + '/R2O_projects/update_cutoff/figures'

# suite dictionary
# key = ID, value = short name
# offline
SUITE_DICT = {'u-bo796': {'time_length': 6.25, 'colour': 'black'},  # Control, Update = 6 hours 15 mins
              # 'u-bp725': 'U715',  # Update = 7 hours 15 mins (ran later, therefore less data than the others)
              'u-bo895': {'time_length': 5.0, 'colour': 'red'},  # Update = 5 hours
              'u-bo798': {'time_length': 4.0, 'colour': 'blue'},  # Update = 4 hours
              'u-bo862': {'time_length': 3.0, 'colour': 'green'},  # Update = 3 hours
              # 'u-bo857': 'M10'  # Main run = 2 hours 30 (-10 minutes) - needs to have glm not glu in mass file
              }

# update trial start and end dates
start_date = dt.datetime(2019, 6, 15, 6, 0, 0)
end_date = dt.datetime(2019, 7, 30, 18, 0, 0)
# end_date = dt.datetime(2019, 9, 15, 18, 0, 0)

# each cycle

date_range = eu.date_range(start_date, end_date, 6, 'hours')

# date ranges to loop over if in a suite
# start_date_in=$(rose date -c -f %Y%m%d%H%M)

# ascending order for update time length
suite_list = ['u-bo862', 'u-bo798', 'u-bo895', 'u-bo796']

control_suite = 'u-bo796'

# flag headers to check for and create statistics about
flag_list = ['active', 'rejected', 'thinned', 'thinned_but_active']

# regions to create statistic entries for
region_list = ['SH', 'NH', 'TR', 'AUS', 'EUR', 'GLOBAL']

region_colours = {'SH': 'purple',
                  'NH': 'blue',
                  'TR': 'green',
                  'AUS':'red',
                  'EUR': 'gold',
                  'GLOBAL': 'black'}

# 'all_obs' is also calcualted...
obs_list = ['goesimclr',  'ssmis', 'mwri', 'surface', 'gmihigh', 'iasi', 'cris', 'sonde','ahiclr', 'atovs',
            'airs', 'gmilow', 'gpsro', 'amsr',  'aod', 'abiclr', 'scatwind', 'mwsfy3b', 'mwsfy3', 'atms',  'aircraft',
            'groundgps', 'seviriclr', 'saphir', 'satwind']



# catagorising observations into groups
obs_list_left = ['goesimclr', 'mwri', 'ahiclr', 'gpsro', 'aod', 'abiclr', 'mwsfy3b', 'mwsfy3', 'seviriclr', 'satwind']

obs_list_cats = {'hyperspectral_IR': ['airs', 'cris', 'iasi'], 'MW_sounder_imager': ['ssmis', 'atovs', 'atms', 'saphir', 'amsr', 'gmihigh', 'gmilow'],
                 'land_surface': ['surface'], 'sonde': ['sonde'], 'land_upper': ['groundgps', 'aircraft'], 'ocean_surface': ['scatwind']}



flag_colours = {'active': 'green',
                'rejected': 'red',
                'thinned': 'blue',
                'thinned_but_active': 'orange'}

if __name__ == '__main__':

    # ==============================================================================
    # Read
    # ==============================================================================

    # read in the data

    # initialise the dictionaries ready
    suite_meta = {key: {} for key in suite_list}

    # large nested loop: suite_cycle_stats => suite => flag => region => obs
    suite_data = {suite_id:{
                     flag_i: {
                         region_i: {
                            obs_i: [] for obs_i in obs_list}
                         for region_i in region_list}
                     for flag_i in flag_list}
                  for suite_id in suite_list}

    # sampling stats with respect to the observations
    cycle_summary_stats = {key: {} for key in suite_list}

    region_summary = {key: {} for key in suite_list}

    for date_i in date_range:

        print('working on: '+str(date_i))

        for suite_id in suite_list:

            # filename
            filepath = DATADIR+'/R2O_projects/update_cutoff/data/cycle_sql_stats/'+suite_id+'/' + \
                       date_i.strftime('%Y%m%dT%H%MZ')+'_'+suite_id+'_stats.npy'

            # extract statistics and metadata
            raw = np.load(filepath).flat[0]
            suite_cycle_meta = raw['suite_cycle_meta']
            suite_cycle_stats = raw['suite_cycle_stats']

            # append metadata to the dictionary

            #metadata
            # first handful of cases - initialise the lists ready for data if its the first entry
            if suite_meta[suite_id] == {}:
                for key in suite_cycle_meta.keys():
                    # just add the keys
                    suite_meta[suite_id][key] = []
            # add the data
            for key, item in suite_cycle_meta.items():
                suite_meta[suite_id][key] += [item]


            # # extract and append data to the dictionary
            # # set up dictionary for flag and region. Obs will be filled in later
            # if suite_data[suite_id] == {}:
            #     for flag, flag_dict in suite_cycle_stats.items():       # active, rejected, thinned
            #         suite_data[suite_id][flag] = {}
            #         for region in flag_dict.keys():
            #             suite_data[suite_id][flag][region] = {}

            # now fill the data in. The float values in [suite_cycle_stats] will be taken out and appended to lists
            for flag in flag_list:
                for region in region_list:
                    for obs in obs_list:
                        if obs in suite_cycle_stats[flag][region].keys():
                            suite_data[suite_id][flag][region][obs] += [suite_cycle_stats[flag][region][obs]]
                        else:
                            suite_data[suite_id][flag][region][obs] += [np.nan]

    # ==============================================================================
    # Process
    # ==============================================================================

    # after all cycles have been read in... calculate the SAMPLING statistics (mean.
    #    median etc through across the cycles)
    for suite_id in suite_list:
        # create mean stddev, med and IQR for each obs type, across all the cycles
        for flag in flag_list:
            cycle_summary_stats[suite_id][flag] = {}
            region_summary[suite_id][flag] = {}
            for region in region_list:
                cycle_summary_stats[suite_id][flag][region] = {}
                for obs in obs_list:
                    # if meta says all obs were present...
                    cycle_summary_stats[suite_id][flag][region][obs] = {
                        'mean': np.nanmean(suite_data[suite_id][flag][region][obs]),
                        'median': np.nanmedian(suite_data[suite_id][flag][region][obs]),
                        'stdev': np.nanstd(suite_data[suite_id][flag][region][obs]),
                        'IQR': np.nanpercentile(suite_data[suite_id][flag][region][obs], 75) -
                               np.nanpercentile(suite_data[suite_id][flag][region][obs], 25),
                        'total': np.nansum(suite_data[suite_id][flag][region][obs])
                    }

                # in the region loop, sum up the means across all the obs that were calculated in the dictionary
                #   above
                region_summary[suite_id][flag][region] = {
                    'total': np.nansum([cycle_summary_stats[suite_id][flag][region][obs]['mean'] for obs in obs_list]),
                    'stdev': np.nanstd([cycle_summary_stats[suite_id][flag][region][obs]['mean'] for obs in obs_list])}


    # plot mean number of obs vs update length (cycle_summary_stats[flag][region][obs]['mean'])

    # ...
    # plot num active vs update time length, for each region
    # plot num thinned vs update time ...
    # plot num rejected vs update time ...

    # update times in a list
    update_time_list = [SUITE_DICT[suite_id]['time_length'] for suite_id in suite_list]

    # 1. total mean number of observations, per flag, per region vs update time length
    total_mean_savedir = SAVEDIR + 'total_mean_obs'
    for flag in flag_list:

        print flag

        savedir_total_mean_obs = SAVEDIR + '/total_mean_obs_normed'
        if os.path.exists(savedir_total_mean_obs) == False:
            os.system('mkdir -p ' + savedir_total_mean_obs)

        fig = plt.figure(figsize=(7, 5))

        for region in region_list:

            #print region

            total_mean = np.array([region_summary[suite_id][flag][region]['total'] for suite_id in suite_list])/  \
                region_summary[control_suite][flag][region]['total']
            stdev_mean = np.array([region_summary[suite_id][flag][region]['stdev'] for suite_id in suite_list])/ \
                region_summary[control_suite][flag][region]['total']

            stdev_minus2 = (total_mean - (2.0*stdev_mean))
            stdev_plus2 = total_mean + (2.0*stdev_mean)

            ax = plt.plot(update_time_list, total_mean, color=region_colours[region], marker='o', label=region)  # total mean          # color=flag_colours[flag]
            plt.fill_between(update_time_list, stdev_minus2, stdev_plus2, color=region_colours[region], alpha=0.1)  # +/- 2 stdev
            plt.plot(update_time_list, stdev_plus2, color=region_colours[region], linestyle='--', alpha=0.4)  #
            plt.plot(update_time_list, stdev_minus2, color=region_colours[region], linestyle='--', alpha=0.4)  #

            # prettify
            plt.xlabel('update time [hours]')
            plt.ylabel('number of obs')
            plt.suptitle('total mean number of obs (normed to control): '+flag)
            plt.legend(loc=4)

            plt.savefig(savedir_total_mean_obs +'/'+flag+'.png')
            #plt.clf()

        plt.close(fig)

    # for suite_id in suite_list:
    #     suite_savedir = SAVEDIR + '/'+suite_id+'/'

























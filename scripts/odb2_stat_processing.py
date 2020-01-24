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
START_DATE = dt.datetime(2019, 6, 15, 6, 0, 0)
END_DATE = dt.datetime(2019, 7, 30, 18, 0, 0)
# end_date = dt.datetime(2019, 9, 15, 18, 0, 0)

# each cycle
DATE_RANGE = eu.date_range(START_DATE, END_DATE, 6, 'hours')

# date ranges to loop over if in a suite
# start_date_in=$(rose date -c -f %Y%m%d%H%M)

# ascending order for update time length
SUITE_LIST = ['u-bo862', 'u-bo798', 'u-bo895', 'u-bo796']

CONTROL_SUITE = 'u-bo796'

# flag headers to check for and create statistics about
FLAG_LIST = ['active', 'rejected', 'thinned', 'thinned_but_active']

# regions to create statistic entries for
REGION_LIST = ['SH', 'NH', 'TR', 'AUS', 'EUR', 'GLOBAL']

REGION_COLOURS = {'SH': 'purple',
                  'NH': 'blue',
                  'TR': 'green',
                  'AUS':'red',
                  'EUR': 'gold',
                  'GLOBAL': 'black'}

# 'all_obs' is also calcualted...
OBS_LIST = ['goesimclr',  'ssmis', 'mwri', 'surface', 'gmihigh', 'iasi', 'cris', 'sonde','ahiclr', 'atovs',
            'airs', 'gmilow', 'gpsro', 'amsr',  'aod', 'abiclr', 'scatwind', 'mwsfy3b', 'mwsfy3', 'atms',  'aircraft',
            'groundgps', 'seviriclr', 'saphir', 'satwind']

OBS_DICT_CATS = {'hyperspectral_IR': ['airs', 'cris', 'iasi'],
                 'MW_sounder_imager': ['ssmis', 'atovs', 'atms', 'saphir', 'amsr', 'gmihigh',
                                       'gmilow', 'mwsfy3b', 'mwsfy3', 'mwri'], 'amvs': ['satwind'], 'aircraft': ['aircraft'],
                 'surface': ['surface'], 'sonde': ['sonde'], 'scatwind': ['scatwind'], 'gnssro':['gpsro'],
                 'geo_csr':['seviriclr', 'abiclr', 'ahiclr', 'goesimclr'], 'ground_gnss': ['groundgps'], 'aod':['aod']}

FLAG_COLOURS = {'active': 'green',
                'rejected': 'red',
                'thinned': 'blue',
                'thinned_but_active': 'orange'}

# update times in a list
UPDATE_TIME_LIST = [SUITE_DICT[suite_id]['time_length'] for suite_id in SUITE_LIST]

# fixed list order to the obs catagories
OBS_LIST_CATS = OBS_DICT_CATS.keys()

# ==============================================================================
# Functions
# ==============================================================================

# processing


def create_cycle_summary_stats():
    """
    Calculate sampling statistics on the number of observations present across the cycles e.g. mean number of obs
    :return: cycle_summary_stats
    """

    # sampling stats with respect to the observations
    cycle_summary_stats = {suite_id: {
        flag_i: {
            region_i: {}
            for region_i in REGION_LIST}
        for flag_i in FLAG_LIST}
        for suite_id in SUITE_LIST}

    for suite_id in SUITE_LIST:
        # create mean stddev, med and IQR for each obs type, across all the cycles
        for flag in FLAG_LIST:
            cycle_summary_stats[suite_id][flag] = {}
            for region in REGION_LIST:
                cycle_summary_stats[suite_id][flag][region] = {}
                for obs in OBS_LIST:
                    # if meta says all obs were present...
                    cycle_summary_stats[suite_id][flag][region][obs] = {
                        'mean': np.nanmean(suite_data[suite_id][flag][region][obs]),
                        'median': np.nanmedian(suite_data[suite_id][flag][region][obs]),
                        'stdev': np.nanstd(suite_data[suite_id][flag][region][obs]),
                        'IQR': np.nanpercentile(suite_data[suite_id][flag][region][obs], 75) -
                               np.nanpercentile(suite_data[suite_id][flag][region][obs], 25),
                        'total': np.nansum(suite_data[suite_id][flag][region][obs])
                    }

    return cycle_summary_stats


# plotting


def plot_total_mean_obs(region_summary):

    """
    plot the total mean and stdev of all the observations, per region.

    :param region_summary: (dict) region summary statistics
    :return:
    """

    for flag in FLAG_LIST:

        print flag

        savedir_total_mean_obs = SAVEDIR + '/total_mean_obs_normed'
        if os.path.exists(savedir_total_mean_obs) == False:
            os.system('mkdir -p ' + savedir_total_mean_obs)

        fig = plt.figure(figsize=(7, 5))

        for region in REGION_LIST:

            #print region

            total_mean = np.array([region_summary[suite_id][flag][region]['total'] for suite_id in SUITE_LIST])/ \
                region_summary[CONTROL_SUITE][flag][region]['total']
            stdev_mean = np.array([region_summary[suite_id][flag][region]['stdev'] for suite_id in SUITE_LIST])/ \
                region_summary[CONTROL_SUITE][flag][region]['total']

            stdev_minus2 = (total_mean - (2.0*stdev_mean))
            stdev_plus2 = total_mean + (2.0*stdev_mean)

            ax = plt.plot(UPDATE_TIME_LIST, total_mean, color=REGION_COLOURS[region], marker='o', label=region)  # total mean          # color=flag_colours[flag]
            plt.fill_between(UPDATE_TIME_LIST, stdev_minus2, stdev_plus2, color=REGION_COLOURS[region], alpha=0.1)  # +/- 2 stdev
            plt.plot(UPDATE_TIME_LIST, stdev_plus2, color=REGION_COLOURS[region], linestyle='--', alpha=0.4)  #
            plt.plot(UPDATE_TIME_LIST, stdev_minus2, color=REGION_COLOURS[region], linestyle='--', alpha=0.4)  #

            # prettify
            plt.xlabel('update time [hours]')
            plt.ylabel('number of obs')
            plt.suptitle('total mean number of obs (normed to control): '+flag)
            plt.legend(loc=4)

            plt.savefig(savedir_total_mean_obs +'/'+flag+'.png')
            #plt.clf()

        plt.close(fig)

    return


if __name__ == '__main__':

    # ==============================================================================
    # Read
    # ==============================================================================

    # read in the data

    # initialise the dictionaries ready
    suite_meta = {key: {} for key in SUITE_LIST}

    # large nested loop: suite_cycle_stats => suite => flag => region => obs
    suite_data = {suite_id:{
                     flag_i: {
                         region_i: {
                            obs_i: [] for obs_i in OBS_LIST}
                         for region_i in REGION_LIST}
                     for flag_i in FLAG_LIST}
                  for suite_id in SUITE_LIST}

    region_summary = {key: {} for key in SUITE_LIST}

    for date_i in DATE_RANGE:

        print('working on: '+str(date_i))

        for suite_id in SUITE_LIST:

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
            for flag in FLAG_LIST:
                for region in REGION_LIST:
                    for obs in OBS_LIST:
                        if obs in suite_cycle_stats[flag][region].keys():
                            suite_data[suite_id][flag][region][obs] += [suite_cycle_stats[flag][region][obs]]
                        else:
                            suite_data[suite_id][flag][region][obs] += [np.nan]

    # ==============================================================================
    # Process
    # ==============================================================================

    # create the cycle summary statistics: mean stddev, med and IQR for each obs type, across all the cycles
    cycle_summary_stats = create_cycle_summary_stats()

    # after all cycles have been read in... calculate the SAMPLING statistics (mean.
    #    median etc through across the cycles)

    # --------------------
    # large nested loop: suite_cycle_stats => suite => flag => region => obs
    region_summary = {suite_id:{
                     flag_i: {
                         region_i: {}
                         for region_i in REGION_LIST}
                     for flag_i in FLAG_LIST}
                  for suite_id in SUITE_LIST}

    for suite_id in SUITE_LIST:
        for flag in FLAG_LIST:
            for region in REGION_LIST:

                # in the region loop, sum up the means across all the obs that were calculated in the dictionary
                #   above
                region_summary[suite_id][flag][region] = {
                    'total': np.nansum([cycle_summary_stats[suite_id][flag][region][obs]['mean'] for obs in OBS_LIST]),
                    'stdev': np.nanstd([cycle_summary_stats[suite_id][flag][region][obs]['mean'] for obs in OBS_LIST])}

                # sum up means across each obs catagory
                region_summary[suite_id][flag][region]['cat_total'] = {
                    cat_i:   np.nansum([cycle_summary_stats[suite_id][flag][region][obs]['mean'] for obs in OBS_DICT_CATS[cat_i]])
                        for cat_i in OBS_DICT_CATS.keys()}

                # total across all catagories


    # plot mean number of obs vs update length (cycle_summary_stats[flag][region][obs]['mean'])

    # 1. total mean number of observations, per flag, per region vs update time length
    plot_total_mean_obs(region_summary)

    # 2. plot mean number of obs split by category
    for flag in FLAG_LIST:

        print flag

        for region in REGION_LIST:

            savedir_total_mean_obs = SAVEDIR + '/total_cat_mean_normed_suite_id/'+region
            if os.path.exists(savedir_total_mean_obs) == False:
                os.system('mkdir -p ' + savedir_total_mean_obs)


            # normalise the data with respect to the total obs in each suite.
            # Dictionary becomes {cat_1:[suite1, suite2, suite3 ...], cat2: [suite1, suite2 ...] ...}
            norm_cat = {cat_i:[region_summary[suite_id][flag][region]['cat_total'][cat_i] /
                               region_summary[suite_id][flag][region]['total'] for suite_id in SUITE_LIST]
                        for cat_i in OBS_DICT_CATS.keys()}

            # CTRL vs suite. Change what it is normalised with respect to here AND change the save directory
            norm_cat_array = np.array([[region_summary[suite_id][flag][region]['cat_total'][cat_i] /
                               region_summary[suite_id][flag][region]['total'] for suite_id in SUITE_LIST]
                        for cat_i in OBS_LIST_CATS])

            fig = plt.figure(figsize=(7, 5))
            ax = plt.subplot(111)

            #for i, cat_i in enumerate(OBS_DICT_CATS):
            plt.stackplot(UPDATE_TIME_LIST, *norm_cat_array, labels=OBS_LIST_CATS)

            # pretify
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
            plt.legend(loc='center left', fontsize=8, bbox_to_anchor=(1, 0.5))
            ax.autoscale(enable=True, axis='x', tight=True)
            plt.axhline(1.0, color='black')
            plt.suptitle('total mean number of obs by type (normed to suite_id): '+flag+'; '+region )
            plt.xlabel('update time [hours]')
            plt.ylabel('number of obs')
            plt.savefig(savedir_total_mean_obs +'/total_by_cat_'+flag)

            plt.close()























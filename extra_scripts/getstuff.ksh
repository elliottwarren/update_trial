#!/bin/ksh
set -eu

# Set start/end dates
export ROSE_TASK_CYCLE_TIME=20190824T1200Z
end_date=2019082412

# Reset offset for each trial
offset=0
cdate=0
model=glu

while [[ $cdate -le $end_date ]]; do

  cdate=$(rose date -c -s +PT${offset}H --print-format=%Y%m%d%H)
  CDATE=$(rose date -c -s +PT${offset}H --print-format=%Y%m%dT%H00Z)

  # Loop through dates and trials to get rose-bush output
  #for trial in bo196 bo198 bo199; do
  for trial in bo613; do

    # Loop through obs types
    if [[ ! -d $trial ]]; then mkdir $trial; fi
    for obtype in abiclr ahiclr airs amsr aod atms atovs aircraft cris gmihigh gmilow goesimclr gpsro groundgps iasi mwri mwsfy3 mwsfy3b saphir seviriclr ssmis satwind scatwind sonde surface; do

      echo trial=$trial offset=$offset cdate=$cdate
      wget "http://fcm1/rose-bush/view/gltrials?&suite=u-${trial}&no_fuzzy_time=0&path=log/job-${CDATE}.tar.gz&path_in_tar=job/${CDATE}/${model}_ops_process_background_${obtype}/01/job.stats" -O $trial/${cdate}_${model}_ops_${obtype}.stats || wget "http://fcm1/rose-bush/view/gltrials?&suite=u-${trial}&no_fuzzy_time=0&path=log/job/${CDATE}/${model}_ops_process_background_${obtype}/01/job.stats" -O $trial/${cdate}_${model}_ops_${obtype}.stats

    done
  done

  offset=$((offset + 6))
done

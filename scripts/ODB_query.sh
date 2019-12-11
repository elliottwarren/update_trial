#!/bin/bash
set -eu
# Interrogate an ODB-2 file from glu cycles
# First scp remote file to desktop:
#  (sample) ~fpos1/cylc-run/mi-ai111/share/cycle/20160310T0000Z/glu_odb2/sonde.odb
#  (MASS-R) :/opfc/atm/global/rerun/psuite38.file/20161102T0000Z_glu_sonde_odb2.gz
#  (MASS-R) :/opfc/atm/global/rerun/201611.file/20161101T1200Z_glu_sonde_odb2.gz

# REMEMBER TO UNZIP THE FILES FIRST!
# gunzip file.gz

# Add odbapi exec to path
PATH=$PATH:~odb/installs/odbapi/odbapi-0.10.3-ukmo-v2/gnu-4.4.7/bin
ODB_FILE=$1

# List all wind profilers
#odb sql 'select distinct statid where ops_obstype=50400' -i $ODB_FILE

# List all data (hdr + first 5 lines)
#odb ls $ODB_FILE | head -5
#exit
odb sql 'select distinct date,time,statid,lat,lon,obsvalue where varno == 108' -i $ODB_FILE
exit

# Get all AMDAR/AIREP data
odb sql 'select max(initial_obsvalue-obsvalue), min(initial_obsvalue-obsvalue)' -i $ODB_FILE
odb sql 'select date,time,statid,lat,lon,ops_obstype,ops_subtype,initial_obsvalue,obsvalue where varno == 108' -i $ODB_FILE
exit
##odb sql 'select * where ops_obstype in (30100,30300)' -i $ODB_FILE
#odb sql 'select distinct date,time,statid,lat,lon,ops_obstype,aircraft_tail_number,aircraft_transponder_address,aircraft_airframe_code,aircraft_gnss_alt,aircraft_ind_air_speed,aircraft_true_air_speed,aircraft_ground_speed,aircraft_heading_bias,an_depar,fg_depar,bgvalue,final_obs_error,fg_error,pges_buddy,pges_final where ops_obstype in (30100,30300)' -i $ODB_FILE
odb sql 'select distinct date,time,statid,lat,lon,ops_obstype,aircraft_tail_number,an_depar,fg_depar,bgvalue,final_obs_error,obs_error,fg_error,pges_buddy,pges_final where ops_obstype in (30100,30300)' -i $ODB_FILE
exit

# Get all TEMPs
#odb sql 'select distinct date,time,statid,lat,lon,receipt_date,receipt_time,ops_obstype,station_type,ob_practice,obsvalue,an_depar,fg_depar,bgvalue,final_obs_error,fg_error,pges_buddy,pges_final where ops_obstype in (50101,50201)' -i $ODB_FILE
#odb sql 'select distinct date,time,statid,lat,lon,receipt_date,receipt_time,ops_obstype,station_type,ob_practice,obsvalue,an_depar,fg_depar,bgvalue,final_obs_error,fg_error,pges_buddy,pges_final where ops_obstype in (50500)' -i $ODB_FILE
odb sql 'select distinct date,time,statid,lat,lon where ops_obstype in (50101,50201)' -i $ODB_FILE
#odb sql 'select distinct date,time,statid,lat,lon where ops_obstype in (50500)' -i $ODB_FILE
exit

# Get all SHIP data
odb sql 'select distinct date,time,statid,lat,lon,receipt_date,receipt_time,ops_obstype,station_type,ob_practice,ship_speed,ship_direction,sst_measurement_method,obsvalue,an_depar,fg_depar,bgvalue,final_obs_error,fg_error,pges_buddy,pges_final where ops_obstype in (10201,10202)' -i $ODB_FILE
odb sql 'select * where ops_obstype in (10201,10202)' -i $ODB_FILE
exit

# Get SYNOP/METAR
odb sql 'select distinct date,time,statid,lat,lon where ops_obstype in (10101,10102,11101,11102)' -i $ODB_FILE
exit

###### ops_obstypes (see )
## AMDAR            30100
## AIREPS           30200
## TAMDAR           30300
## SONDE (BUFR)     50500
## TEMP (TAC)       50101, 50201
## WINDPRO          50400
## SHIPSYN          102nn
## SYNOP (man)      10101
## SYNOP (auto)     10102
## METAR (man)      11101
## METAR (auto)     11102

# List all TAC (50101) and BUFR (50201) sondes
cd /home/h06/fra21/localdata/
#odb ls $ODB_FILE -n 1
# list all data for specific station reports
##odb sql 'select * where ident=93112' -i $ODB_FILE
# List everything that is not WINPRO
#odb sql 'select distinct statid,lat,lon,date,time,ops_obstype,numlev where ops_obstype!=50100' -i $ODB_FILE
##odb sql 'select statid,lat,lon,ops_obstype,numlev,obsvalue where ident=61901' -i $ODB_FILE
##odb sql 'select distinct statid,lat,lon,ops_obstype,numlev,obsvalue where ops_obstype=50101' -i $ODB_FILE
# Everything but WINDPRO
#odb sql 'select distinct statid,lat,lon,ops_obstype where ops_obstype!=50400' -i $ODB_FILE
##exit

# List all columns
#odb ls $ODB_FILE | head -n 1
#odb ls $ODB_FILE | grep 30100
# Get tailnumber/statid
odb sql 'select distinct statid,lat,lon,ops_obstype,numlev,obsvalue where ops_obstype=30100' -i $ODB_FILE
#odb sql 'select aircraft_tail_number where ops_obstype=30100' -i $ODB_FILE

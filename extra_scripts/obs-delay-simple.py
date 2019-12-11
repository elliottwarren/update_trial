#!/usr/bin/env python2.7

"""
It retrieves some observations from MetDB and for each of them it determines whether or not it would have been used in
the global data assimilation (i.e. whether it arrived in time). That calculation is based on the "dataCutOff" value,
which is number of minutes after nominal analysis time.

In the example I attached, the value of 376 minutes roughly represents current global update cutoff time.

Created by Adam Maycock

requires module load scitools/experimental_legacy-current as interpreter
"""

#import obsmon.obsodb as odb
import metdb


def inAssimWindow(obTime=None, rcptTime=None, cycleLength=60, cutOff=0):
    """Round a datetime object to any time laps in seconds
    obTime : datetime.datetime object, default now.
    cycleLength : Closest number of seconds to round to, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
    """
    import datetime
    inTime = False
    if obTime == None: obTime = datetime.datetime.now()
    if rcptTime == None: rcptTime = datetime.datetime.now()
    seconds = (obTime.replace(tzinfo=None) - obTime.min).seconds
    rounding = (seconds + cycleLength / 2) // cycleLength * cycleLength
    assimWindow = obTime + datetime.timedelta(0, rounding - seconds, -obTime.microsecond)
    if rcptTime <= assimWindow + datetime.timedelta(seconds=cutOff):
        inTime = True
    return assimWindow, inTime


def list_dt_to_python_dt(intime):
    # Convert a [year, month, day, hour, minute, second] list to python datetime object

    import datetime

    year = int(intime[0])
    month = int(intime[1])
    day = int(intime[2])
    hour = int(intime[3])
    minute = max(int(intime[4]), 0)
    second = max(int(intime[5]), 0)

    return datetime.datetime(year, month, day, hour, minute, second)

# Initialise
assimWindowLength = 6 # hours
dataCutOff = 376 # minutes

start = 'START TIME 20191114/2100Z' # Start of assimilation window
end   = 'END TIME 20191115/0259Z'   # End of assimilation window
area = 'AREA 90.00N 90.00S 180.00W 180.00E' # Area

keywords = [start, end, area]
elements = ['WMO_BLCK_NMBR', 'WMO_STTN_NMBR', 'YEAR', 'MNTH', 'DAY', 'HOUR', 'MINT', 'RCPT_YEAR', 'RCPT_MNTH', 'RCPT_DAY', 'RCPT_HOUR', 'RCPT_MINT', 'LTTD', 'LNGD']
contact = 'adam.maycock@metoffice.gov.uk'
subtype = 'LNDSYN'
timediffs = []
numReceivedInTime = 0

# Retrieve observations from MetDB
obs = metdb.obs(contact, subtype, keywords, elements)

numObs = len(obs['YEAR'].data)

for ob in range(numObs):

    site_id = int(obs['WMO_BLCK_NMBR'].data[ob]) * 1000 + int(obs['WMO_STTN_NMBR'].data[ob])

    obtime = list_dt_to_python_dt([obs['YEAR'].data[ob], obs['MNTH'].data[ob], obs['DAY'].data[ob], obs['HOUR'].data[ob], obs['MINT'].data[ob], 0])
    rcpttime = list_dt_to_python_dt([obs['RCPT_YEAR'].data[ob], obs['RCPT_MNTH'].data[ob], obs['RCPT_DAY'].data[ob], obs['RCPT_HOUR'].data[ob], obs['RCPT_MINT'].data[ob], 0])
    timediff = (rcpttime - obtime).total_seconds()
    timediffs.append(timediff)
#    print obtime, rcpttime, inAssimWindow(obtime, rcpttime, cycleLength=assimWindowLength*60*60, cutOff = dataCutOff*60)

    inTime = inAssimWindow(obtime, rcpttime, cycleLength=assimWindowLength*60*60, cutOff = dataCutOff*60)[1]
    if inTime == True:
        numReceivedInTime += 1
        
print '{:d} / {:d} received in time'.format(numReceivedInTime, numObs)

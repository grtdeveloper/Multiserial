#! /usr/bin/python

from config import config
from common import *
from gps import *
import time
import sqlite3 as lite
import os
import logging


gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 

con = lite.connect(config['DB_NAME'])

workDir = os.getcwd()
fifoPath = workDir + "/" + "latlongFifo"
fPath=None

if os.path.isfile(fifoPath) is False:
    try:
        os.mkfifo(fifoPath)
    except OSError, e:
        logginf.info( "Failed to create FIFO: %s" % e)

try:
    fPath = open(fifoPath, "w")
except Exception as err:
    logginf.info("Error Opening FiFo ")


try:
    while True:
        logging.info('Working')
        report = gpsd.next()
        if report['class'] == 'TPV':
            logging.info("GPS signal received")
            with con:
                cur = con.cursor()
                lat = getattr(report,'lat',0.0)
                lon = getattr(report,'lon',0.0)
                gpstime = getattr(report,'gpstime',0.0)
                systime = getattr(report,'systime',0.0)
                alt = getattr(report,'alt',0.0)
                epv = getattr(report,'epv',0.0)
                ept = getattr(report,'ept',0.0)
                speed = getattr(report,'speed',0.0)
                climb = getattr(report,'climb',0.0)
                macaddr = getMAC()
                device_id = config["DEVICE_ID"]
                fPath.write(str(lat) + "," + str(lon))
                data = (lat, lon, gpstime, systime, alt, epv, ept, speed, climb, macaddr, device_id)
                cur.execute("insert into sensor_data (lat, lon, gpstime, systime, alt, epv, ept, speed, climb, macaddr, device_id) values (?,?,?,?,?,?,?,?,?,?,?)", data)
                logging.info("New DB record created")
        time.sleep(config['READ_INTERVAL']) 
except (KeyboardInterrupt, SystemExit): 
    logging.error("Done.\nExiting.")
    logging.info("Closing FiFo")
    fPath.close()

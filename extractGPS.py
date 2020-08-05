#! /usr/bin/python

from common import *
from gps import *
import sys
import stat,os
import logging
import serial
import time
from multiprocessing import Process, Queue
import sqlite3 as lite
from config import config

Iface="/dev/ttyUSB1"
BAUD_RATE=38400



gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 

con = lite.connect(config['DB_NAME'])

def writeData(lat,lon,cur,Q_PDLM1,Q_PDLMA):
    data_1 = []
    data_2 = []
    data = []
    tempStr = ""
    if Q_PDLM1.empty() is False:
        tempStr = Q_PDLM1.get()
        data_1 = (tempStr[9: len(tempStr) -8]).split(",")
        print("Got PDLM1 Buffer as :", data_1)
    if Q_PDLMA.empty() is False:
        tempStr = ""
        tempStr = Q_PDLMA.get()
        data_2 = (tempStr[9: len(tempStr) -8]).split(",")
        print("Got PDLMA Buffer as :", data_2)
 
    data  = data_1 + data_2

    netQry = "insert into sensorInfo (lat,lon,HHMMSS,hcpCon,hcpInphase,prpCond,prpInphase,Voltage,Temperature,Pitch,Roll) Values ('"
    netQry += str(round(lat,5))
    netQry += "','"
    netQry += str(round(lon,5))
    netQry += "','"
    print("len of data is :", len(data))
    print("netDAta is ", data)
    print("Storing data in database")
    i = 0
    while i < len(data) - 1:
	netQry += str(data[i])
        netQry += "','"
        i += 1
    netQry += str(data[8])
    netQry += "')"
    print("netQry is :", netQry)
    try:
        cur.execute(netQry)
    except Exception as err:
        print("Got Exception while inserting record :", str(err))
    return



def fetchlatlon(Q_LATLON,Q_PDLM1,Q_PDLMA):
    latlnData = ""
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
                    latlnData = str(round(lat,5)) +"," + str(round(lon,5))
                    data = (lat, lon, gpstime, systime, alt, epv, ept, speed, climb, macaddr, device_id)
                    cur.execute("insert into sensor_data (lat, lon, gpstime, systime, alt, epv, ept, speed, climb, macaddr, device_id) values (?,?,?,?,?,?,?,?,?,?,?)", d
ata)
                    writeData(lat,lon,cur,Q_PDLM1,Q_PDLMA)
                logging.info("New DB record created")
            time.sleep(config['READ_INTERVAL']) 
    except (KeyboardInterrupt, SystemExit): 
        logging.error("Done.\nExiting.")

def openPort(Iface,BAUD_RATE):
    global serPort
    try:
        serPort = serial.Serial(Iface,BAUD_RATE,timeout=1)
        print("Serial Port Opened Success : ", str(serPort))
	except Exception as err:
        print("Serial Port Could not be Opened :", str(err))
        sys.exit(0)
    return serPort


def collectData(serPort,Q_PDLM1,Q_PDLMA):
    BUF_PDLM1 = "$PDLM1"
    BUF_PDLMA = "$PDLMA"
    #BUF_PDLMB = "$PDLMB"
    pdlm1_data_available=0
    pdlma_data_available=0
    #pdlmb_data_available=0
    serPort.flushInput()  

    while True:
        received_data = str(serPort.readline())
        pdlm1_data_available = received_data.find(BUF_PDLM1)
        if pdlm1_data_available > 0:
            Q_PDLM1.put(received_data)
        pdlma_data_available = received_data.find(BUF_PDLMA)
        if pdlma_data_available > 0:
            Q_PDLMA.put(received_data)
        '''
        pdlmb_data_available = received_data.find(BUF_PDLMB)
        if pdlmb_data_available > 0:
            Q_PDLMB.put(received_data)
        '''
         
        time.sleep(0.15)


if __name__ == '__main__':
    
    Q_PDLM1 = Queue()
    Q_PDLMA = Queue()
    Q_LATLON = Queue()

    #Q_PDLMB = Queue()

    Port = openPort(Iface,BAUD_RATE)

    data_latlon = Process(name="GPS data Collect", target=fetchlatlon, args=(Q_LATLON,Q_PDLM1,Q_PDLMA,))
    coll_data = Process(name="Data Collection",target=collectData, args=(Port,Q_PDLM1,Q_PDLMA,))


    print("Staring the Processess....")
    data_latlon.start()
    coll_data.start()
     
    print("Joining the Processess....")
    data_latlon.join()
    coll_data.join()



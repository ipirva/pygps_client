#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

import serial
import time, datetime
import uuid
import sys, os, re, hashlib
import json
import math
import hashlib
# pip3 install pymemcache
from pymemcache.client.base import Client
# apt-get install python3-pika python3-pika-pool OR
# pip3 install pika
import pika

"""
Read serial
Validate serial read data
Detect movement between two consecutive reads
Publish data to queue
"""

fileName = "Main"
_fileName = os.path.splitext(fileName)[0]
_scriptDir = os.path.dirname(os.path.realpath(__file__))


def fMcdb():
    """
    connect to local memcachedb
    if it cannot connect, it returns None
    """

    fName = fMcdb.__name__
    callId = str(uuid.uuid1())
    # check if I can connect to memcachedb localhost port 21201
    try:
        mcdbClient = Client(('127.0.0.1', 21201), connect_timeout=3, timeout=3)
    except Exception as e:
        logM = "Errors memcachedb: %s" % str(e)
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        return None
    else:
        return mcdbClient


def fPublish(exchange = None, queue = None, routingKey = None, content = None):
    """
    publish a message to a specific RabbitMQ exchange / queue
    if the RabitMQ service is not available, no publishing - log file only and special field defined as a notice "error"
    the message to be published must be sent to the function JSON encoded
    """
    
    fName = fPublish.__name__
    callId = str(uuid.uuid1())

    result = {}
    # connection to AQMP
    result["conn"] = 0
    # publishing status
    result["publish"] = 0
    # any errors
    result["error"] = ""

    if content is not None:
        # encode the content as json
        try:
            # calculate a message id
            timeNow = datetime.datetime.now().isoformat()
            msgid = hashlib.md5(str(str(content)+timeNow).encode("utf-8")).hexdigest()
            content["msgid"] = msgid
            # JSON dump
            contentJSON = json.dumps(content, sort_keys=True)
        except Exception as e:
            logM = "Errors RabbitMQ body encoding: %s" % str(e)
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
            result["error"] = str(e)
            return result
    else:
        result["error"] = "No content specified to be published."
        logM = "Errors: %s" % str(result["error"])
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
        return result
            
    if routingKey is not None:
        try:
            # connect to RabbitMQ
            rbmqCredentials = pika.PlainCredentials(username=var["rbmqUsername"], password=var["rbmqPassword"])
            rbmqConn = pika.BlockingConnection(
                            pika.ConnectionParameters(
                                host='127.0.0.1',
                                credentials=rbmqCredentials
                            )
                        )
            rbmqChannel = rbmqConn.channel()
        except Exception as e:
            logM = "Errors RabbitMQ connect: %s" % str(e)
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
            result["error"] = logM
        else:
            result["conn"] = 1

        if result["conn"] == 1:
            if exchange is None:
                # publish to the default exchange
                # queue name = routingKey name
                try:

                    rbmqChannel.queue_declare(
                        queue=routingKey, 
                        durable=True,
                        arguments={'x-message-ttl' : var["rbmqQTTL"]}
                    )
                    publish = rbmqChannel.basic_publish(
                        exchange='',
                        routing_key=routingKey,
                        body=contentJSON,
                        properties=pika.BasicProperties(delivery_mode = var["rbmqDeliveryMode"])
                        )
                except Exception as e:
                    logM = "Errors RabbitMQ publish: %s" % str(e)
                    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
                    result["publish"] = 0
                    result["error"] = logM
                else:
                    if publish:
                        # publish returns TRUE
                        result["publish"] = 1
                    else:
                        # publish return FALSE
                        result["publish"] = 0
                finally:
                    rbmqConn.close()
            else:
                result["error"] = "The Exchange value is not correct."
                logM = "Errors: %s" % str(result["error"])
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
        else:
            return result
    else:
        result["error"] = "No routing key was specified."
        logM = "Errors: %s" % str(result["error"])
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
    
    return result


def fDistance(origin = None, destination = None):
    """
    get the Harvesine distance from the latitude and longitude coordinates
    origin & destination - tuple of float
    return distance in Km
    pay attention to receive lat and lon as FLOAT
    latitude - N/S (parralel)
    longitude - E/W (meridian)
    """

    fName = fDistance.__name__
    callId = str(uuid.uuid1())

    global lato, lono, timeUTCo, latd, lond, timeUTCd
    
    #  Earth radius in Km
    radius = 6371 
    # 1000 is used as default value when lato, lono and timeUTCo could not be retrieved from memcached
    if lato == lono == timeUTCo == 1000:
        return {"distance": 0.0, "cdistance": var["rDistanceCritical"], "units": "Km"}

    if destination == None:
        return None
    elif destination is not None:
        if type(destination) == tuple:
            if len(destination) == 3:
                latd, lond, timeUTCd  = destination
            else:
                return None
        else:
            return None
    # if origin is not None, use it
    # if origin is None, see if there are cached values
    if origin == None:
        # get the origin from memcachedb
        ## mcdbConnect = fMcdb()
        if mcdbConnect is not None:
            try:
                # return dict
                getCachedGPS = mcdbConnect.get_multi(["lat", "lon", "timeUTC"])
                if len(getCachedGPS) == 3:
                    origin = (float(getCachedGPS["lat"]), float(getCachedGPS["lon"]), int(getCachedGPS["timeUTC"]))
                    lato, lono, timeUTCo = origin
                else:
                    mcdbConnect.set_multi(
                        {"lat": var["lato"], "lon": var["lono"], "timeUTC": var["timeUTCo"]}
                    )
            except Exception as e:
                logM = "Errors memcachedb get: "+str(e)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
                return None
            else:
                origin = (float(lato), float(lono), int(timeUTCo))
                #now that we have lanx, lonx, update the cache with lond, latd
                try:
                    mcdbConnect.set_multi(
                        {"lat": latd, "lon": lond, "timeUTC": timeUTCd}
                    )
                except Exception as e:
                    logM = "Errors memcachedb set: %s" % str(e)
                    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
                    return None
        else:
            logM = "Cannot connect to memcachedb."
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
            return None

    if type(origin) == type(destination) == tuple:
        if len(origin) == len(destination) == 3:
            lato, lono, timeUTCo = origin
            latd, lond, timeUTCd = destination
            try:
                dlat = math.radians(latd - lato)
                dlon = math.radians(lond - lono)
                a = (math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lato)) * math.cos(math.radians(latd)) * math.sin(dlon / 2) * math.sin(dlon / 2))
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                d = radius * c
            except Exception as e:
                logM = "Errors: "+str(e)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
                return None
            else:
                return {"distance": d, "cdistance": var["rDistanceCritical"], "units": "Km"}
    return None
            

def fReadSerial(cmd = None):
    """
    write AT command to Serial and read the returned output
    """

    fName = fReadSerial.__name__
    callId = str(uuid.uuid1())

    if cmd is None:
        logM = "No cmd provided to write to Serial."
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        #sys.exit()
        return None
    else:
        commandToSend = cmd

    try:
        ser = serial.Serial(var["serialIF"], var["serialSpeed"], timeout = var["serialTimeout"])
    except Exception as e:
        logM = e
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        #sys.exit()
        return None

    if ser.isOpen():
        logM = "Serial is open. Send cmd: "+cmd
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
    else:
        logM = "Serial is NOT open. Cannot send cmd: "+cmd
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        #sys.exit()
        return None

    line = []
    jLine = None

    try:
        ser.write(str(commandToSend).encode())
        time.sleep(1)
    except Exception as e:
        logM = e
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        #sys.exit()
        return None
    else:
        for c in ser.read(1024):
            line.append(chr(c))
            jLine = ''.join(str(v) for v in line)
        ser.flush()
    return jLine


def fGetGPS():
    """
    write and read specific AT commands to serial
    use the results to get GPS data
    """

    fName = fGetGPS.__name__
    callId = str(uuid.uuid1())

    global lato, lono, timeUTCo, latd, lond, timeUTCd, rStatusGPS
    
    # get a list with matched values return by the serial read
    outputGPS = []
    statusGPS = []
    # build readable GPS data dict
    GPSValues = {}
    # GNSS navigation information parsed from NMEA sentences
    rSerial = fReadSerial(cmd = "AT+CGNSPWR=1 \r\n"+"AT+CGNSINF \r\n"+"AT+CGPSSTATUS? \r\n")
    if rSerial is not None:
        matchGPS1 = re.compile("\+CGNSINF: ([0-9,\.]+)", re.IGNORECASE)
        outputGPS = matchGPS1.findall(rSerial)
        # get GPS status for Location information
        matchGPS2 = re.compile("\+CGPSSTATUS: (.*)", re.IGNORECASE)
        statusGPS = matchGPS2.findall(rSerial)
        
    if len(statusGPS) == 1:
        statusGPS = statusGPS[0].strip()
    # the values for status GPS returned by the GPS module
    knownStatusGPS = ["Location Unknown","Location Not Fix","Location 2D Fix","Location 3D Fix"]
    if statusGPS in knownStatusGPS:
        rStatusGPS = statusGPS
    else:
        # if status not known, catch if any value
        rStatusGPS = "Unknown: %s" % str(statusGPS)

    logM = "rStatusGPS: "+rStatusGPS
    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
    
    GPSValues["rStatusGPSLocation"] = rStatusGPS
    # print(rStatusGPS)

    # check the serial output for specific characters
    # the outputGPS should be a list of size 1
    if len(outputGPS) == 1:
        # split by , should give us 21 fields
        '''    
        <GNSS run status>,<Fix status>,<UTC date & Time>,<Latitude>,<Longitude>,<MSL Altitude>,<Speed Over Ground>, 
        <Course Over Ground>,<Fix Mode>,<Reserved1>,<HDOP>,<PDOP>, <VDOP>,<Reserved2>,<GNSS Satellites in View>, 
        <GNSS Satellites Used>,<GLONASS Satellites Used>,<Reserved3>,<C/N0 max>,<HPA>,<VPA>
        '''
        GPSFields = {}
        GPSFields = {
            0: "runStatus", 
            1: "fixStatus",
            2: "UTCtimedate",
            3: "latitude",
            4: "longitude",
            5: "mslAltitude",
            6: "speed",
            7: "course",
            8: "fixMode",
            9: "reserved1",
            10: "hdop",
            11: "pdop",
            12: "vdop",
            13: "reserved2",
            14: "GNSSSsattelitesinView",
            15: "GNSSSsattelitesUsed",
            16: "GLONASSsattelitesUsed",
            17: "reserved3",
            18: "cn0Max",
            19: "hpa",
            20: "vpa"
        }
        outputGPSFields = outputGPS[0].split(",")
        # +CGNSINF: 1,0,20181124161605.000,,,,0.76,0.0,0,,,,,,4,0,,,38,,
        # +CGNSINF: 1,1,20181124162436.000,xxx,xxx,xxx,0.00,62.3,1,,2.3,2.5,0.9,,9,6,,,36
        if len(outputGPSFields) == 21:
        # at least runStatus and fixStatus
        # not sure about this one, == 21 ?
            for k, v in GPSFields.items():
                if k < len(outputGPSFields):
                    GPSValues[v] = outputGPSFields[k]
            # if the GPS runs and has a fix
            if GPSValues["runStatus"] == "1":
                if GPSValues["fixStatus"] == "1":
                    logM = json.dumps(GPSValues, sort_keys=True)
                    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "debug")
                    # set memcachedb values cache
                    destination = (GPSValues["latitude"], GPSValues["longitude"], str(int(float(GPSValues["UTCtimedate"]))))
                    latd, lond, timeUTCd = destination
                    ## mcdbConnect = fMcdb()
                    if mcdbConnect is not None:
                        try:
                            # return dict  
                            getCachedGPS = mcdbConnect.get_multi(["lat", "lon", "timeUTC"])
                            if len(getCachedGPS) == 3:
                                origin = (getCachedGPS["lat"],getCachedGPS["lon"],getCachedGPS["timeUTC"])
                                lato, lono, timeUTCo = origin
                            else:
                                lato, lono, timeUTCo = destination
                        except Exception as e:
                            logM = "Errors memcachedb get: %s" % str(e)
                            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
                            #return None
                    else:
                        logM = "Cannot connect to memcachedb."
                        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
                        #return None

                    return GPSValues
                else:
                    logM = "GPS does not have a fix status yet."
                    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "warning")
            else:
                logM = "GPS is not running."
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "debug")
    return None


def main():
    """
    get the GPS values GPSValues - it return a dict only if GPS is running and has a fix
    - if not None buid the result and calculate the distance between the present and the former coodonates
    - if the distance cannot be calculated the origin coordonates will be set to 1000 and the distance to 0.0
    publish message to queue
    """
    
    callId = str(uuid.uuid1())

    global iterate

    forcePublish = False
    deltaPlus = int(var["interExec"])
    # iterate = 0 -> first script's execution
    if iterate == 0:
        forcePublish = True
    # I publish the result independent of the critical distance
    # time epoch
    timeNow = time.time()
    deltaTime = 0
    mcdbConnect = fMcdb()
    try:
        getRunTime = mcdbConnect.get_multi(["runTime"])
    except Exception as e:
        runTime = timeNow
    else: 
        runTime = float(getRunTime["runTime"].decode('utf-8'))
        deltaTime =  abs(int(runTime - timeNow)) + deltaPlus
    if deltaTime >= int(var["publishInterval"]):
        try:
            #mcdbConnect = fMcdb()
            mcdbConnect.set_multi(
	            {"runTime": timeNow}
            )
        except Exception as e:
            deltaTime = 0
       
    # publish results
    publish = {}
    # publish based on criteria: distance, timer, forced (at start)
    # publish["publish"]                
    # publish = 0 not published, check if error
    # publish = 1 is done because of the mouvement
    # publish = 2 is done because of forced action
    # publish = 3 is done periodically, if no previous condition triggered
    
    rGPSValues = fGetGPS()
    if rGPSValues is not None:
        # return dictionary
        destination = (float(rGPSValues["latitude"]), float(rGPSValues["longitude"]), int(float(rGPSValues["UTCtimedate"])))
        
        rDistance = fDistance(None, destination)
        rOriginLat = float(lato)
        rOriginLon = float(lono)
        rOriginTimeUTC = int(timeUTCo)

        rDestinationLat, rDestinationLon, rTimeUTCd = destination
        rAltitude = float(rGPSValues["mslAltitude"])
        rSpeed = float(rGPSValues["speed"])
        rUTC = int(float(rGPSValues["UTCtimedate"]))
        
        if len(rGPSValues["GLONASSsattelitesUsed"]) == 0:
            rGLONASSsattelitesUsed = 0
        else:
            rGLONASSsattelitesUsed = int(rGPSValues["GLONASSsattelitesUsed"])
        
        if len(rGPSValues["GNSSSsattelitesUsed"]) == 0:
            rGNSSSsattelitesUsed = 0
        else:
            rGNSSSsattelitesUsed = int(rGPSValues["GNSSSsattelitesUsed"])

        if len(rGPSValues["GNSSSsattelitesinView"]) == 0:
            rGNSSSsattelitesinView = 0
        else:
            rGNSSSsattelitesinView = int(rGPSValues["GNSSSsattelitesinView"])

        rView = {
            "rOriginLat": rOriginLat,
            "rOriginLon": rOriginLon,
            "rOriginTimeUTC": rOriginTimeUTC,
            "rDestinationLat": rDestinationLat,
            "rDestinationLon": rDestinationLon,
            "rAltitude": rAltitude,
            "rUTC": rUTC,
            "rSpeed": rSpeed,
            "rDistance": rDistance,
            "rStatusGPS": rStatusGPS,
            "rGLONASSsattelitesUsed": rGLONASSsattelitesUsed,
            "rGNSSSsattelitesUsed": rGNSSSsattelitesUsed,
            "rGNSSSsattelitesinView": rGNSSSsattelitesinView
        }
    else:
        rView = None
    
    # default publish 
    publish = dict()
    publish["conn"] = -1
    publish["publish"] = 0
    publish["error"] = ""
    publish["exception"] = ""
    # the following allows to publish the id = 2 (at start) and 3 (periodic)
    # default values are used!
    # this happends when rStatusGPS is not "Location 2D Fix" or "Location 3D Fix"
    # {"publish": {}, "rAltitude": 0.0, "rDestinationLat": 1000, "rDestinationLon": 1000, "rDistance": {"distance": 0.0, "units": "Km"}, 
    # "rOriginLat": 1000, "rOriginLon": 1000, "rOriginTimeUTC": 20181202182023, "rSpeed": 0.0, "rStatusGPS": "Unknown[]", "rUTC": 20181202182023}
    # {"publish": {}, "rAltitude": 0.0, "rDestinationLat": 1000, "rDestinationLon": 1000, "rDistance": {"distance": 0.0, "units": "Km"}, 
    # "rOriginLat": 1000, "rOriginLon": 1000, "rOriginTimeUTC": 20181202182023, "rSpeed": 0.0, "rStatusGPS": "Location Not Fix", 
    # "rUTC": 20181202182023}
    # {"publish": {"conn": 1, "error": "", "publish": 3}, "rAltitude": 0.0, "rDestinationLat": 1000, "rDestinationLon": 1000, 
    # "rDistance": {"distance": 0.0, "units": "Km"}, "rOriginLat": 1000, "rOriginLon": 1000, "rOriginTimeUTC": 20181202182023, 
    # "rSpeed": 0.0, "rStatusGPS": "Location Unknown", "rUTC": 20181202182023}
    if rView is None:
        rView = dict()
        rDistance = {"distance": 0.0, "cdistance": var["rDistanceCritical"], "units": "Km"}
        # {"publish": {"conn": 1, "error": "", "publish": 3}, "rAltitude": 30.073, "rDestinationLat": xxx, "rDestinationLon": xxx, "rDistance": {"distance": 0.0, "units": "Km"}, "rOriginLat": xxx, "rOriginLon": xxx, "rOriginTimeUTC": 20181205214617, "rSpeed": 0.0, "rStatusGPS": "Location 3D Fix", "rUTC": 20181205214625}
        rView = {
            "rOriginLat": 1000,
            "rOriginLon": 1000,
            "rOriginTimeUTC": timeUTCo,
            "rDestinationLat": 1000,
            "rDestinationLon": 1000,
            "rAltitude": 0.0,
            "rUTC": timeUTCo,
            "rSpeed": 0.0,
            "rDistance": rDistance,
            "rStatusGPS": rStatusGPS,
            "rGLONASSsattelitesUsed": 0,
            "rGNSSSsattelitesUsed": 0,
            "rGNSSSsattelitesinView": 0
        }

    if float(rView["rDistance"]["distance"]) < float(var["rDistanceCritical"]):
        if (deltaTime >= int(var["publishInterval"])) or forcePublish:
            publish["publish"] = 3
            if forcePublish:
                publish["publish"] = 2
        else:
            # if the distance is less than the critical distance do not try to publish
            # {"publish": {"conn": -1, "error": "", "exception": "", "publish": 0}, "rAltitude": xxx, "rDestinationLat": xxx, 
            # "rDestinationLon": xxx, "rDistance": {"distance": 0.006118755639761127, "units": "Km"}, "rOriginLat": xxx, 
            # "rOriginLon": xxx, "rOriginTimeUTC": 20181205222003, "rSpeed": 0.0, "rStatusGPS": "Location 3D Fix", "rUTC": 20181205222010}
            publish["conn"] = -1
            publish["publish"] = 0
    elif (float(rView["rDistance"]["distance"]) >= float(var["rDistanceCritical"]) and float(rView["rDistance"]["distance"]) > 0)  or forcePublish:
        # the coordinates' change indicate a distance -ge than the critical distance 
        publish["publish"] = 1
        if forcePublish:
            publish["publish"] = 2
    # publish to the queue
    # publish = 0 not published
    # publish = 1 is done because of the mouvement
    # publish = 2 is done because of forced action
    # publish = 3 is done periodically, if no previous condition triggered
    if publish["publish"] > 0:
        rView["publish"] = dict()
        rView["publish"]["publish"] = publish["publish"]
        rPublish = fPublish(None, None, "GPSDetails", rView)
        try:
            publish["conn"] = rPublish["conn"]
            publish["error"] = rPublish["error"]
            publish["exception"] = ""
        except Exception as e:
            publish["exception"] = "Publish: %s" % str(e)
            rView["publish"] = publish
            logM = json.dumps(rView, sort_keys=True)
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  "Main", logM, "error")
        else:
            if publish["conn"] == 0:
                rView["publish"] = publish
                logM = json.dumps(rView, sort_keys=True)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  "Main", logM, "error")
    # publish in the logs for debugging
    rView["publish"] = publish
    logM = json.dumps(rView, sort_keys=True)
    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  "Main", logM, "debug")
    
if __name__ == "__main__":
    iterate = 0
    while True:
        from functions.functions import fLoadVars
        from functions.functions import fWriteLog
        #
        callId = str(uuid.uuid1())
        # epoch
        timeNow = time.time()
        # load variables
        # exit if any problems while loading
        _nameBase = os.path.splitext(os.path.basename(__file__))[0]
        _varFile = _nameBase+".yml"
        var = fLoadVars(file = _scriptDir+"/"+_varFile)
        try:
            var["loggingFilePath"]
        except Exception as e:
            var["loggingFilePath"] = _scriptDir+"/"+_nameBase+".log"

        try:
            fileHandle = open(var["loggingFilePath"], "a+")
        except IOError:
            sys.exit("Unable to write to log file: "+var["loggingFilePath"])        
        # we cannot publish at a rate lower than the execution interval
        # if the two values are equal, the script will publish at each execution cycle
        if int(var["publishInterval"]) < int(var["interExec"]):
            var["publishInterval"] = var["interExec"]

        # I publish the result independent of the critical distance when I start
        mcdbConnect = fMcdb()
        if iterate == 0:
            try:
                # if this is the 1st execution
                ## mcdbConnect = fMcdb()
                mcdbConnect.set_multi(
	                {"runTime": timeNow}
                )
            except Exception as e:
                logM = "Cannot connect to memcachedb."
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  "Main", logM, "critical")
        # measure main() execution in seconds 
        start = time.perf_counter()
        main()
        end = time.perf_counter()
        mainExecTime = end - start
        logM = "Time: main() execution time: %f seconds" % float(mainExecTime)
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  "Main", logM, "debug")
        # mark
        iterate = 1
        time.sleep(int(var["interExec"]))
        # log the time between two executions
        endExec = time.perf_counter()
        logM = "Time: consecutive executions: %f seconds" % float(endExec - end)
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  "Main", logM, "debug")

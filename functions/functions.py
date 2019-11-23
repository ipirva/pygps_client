#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-
import os, sys, yaml, time, datetime, requests, json, base64, zlib, ipaddress, uuid
from uptime import uptime


def fLoadVars(file: str = None) -> dict:
    """
    read YAML file with needed variables
    make this variable available in global
    """
    returnVar = dict()
    
    if file is None:
        return None

    setupFile = file
    try:
        fileHandle = open(setupFile, "r")
        variables = yaml.load(fileHandle, Loader=yaml.FullLoader)
    except Exception as e:
        sys.exit("Unable to read or/and load: "+setupFile+"Error: "+str(e))
    else:
        returnVar = variables
    
    return returnVar

def fWriteLog(callId: str = None, loggingFilePath: str = None, logLevelsShow: list = None, f: str = None, message: str = None, level: str = None) -> str:
    """
    write log message to a file on the disk
    use logging levels
    - logLevelsShow - to filter log levels to be stored
    - level - to be used for the specific log
    """

    fName = fWriteLog.__name__

    logLevels = ["info", "warning", "critical", "debug", "error"]

    try:
        logLevelsShow
    except NameError:
        logLevelsShow = logLevels

    timeNow = datetime.datetime.now().isoformat()
    
    if f is None:
        f = "Unknown function"
    if level is None:
        level = "INFO"
    else:
        level = level.upper()

    # check for defined log levels
    if level.lower() in logLevels:
        # check if the level indicated must be shown or not
        if level.lower() in logLevelsShow:
            if message is not None:
                message = str(callId)+" ::: "+str(f)+" ::: "+str(level)+" ::: "+str(timeNow)+" ::: "+str(message)
                try:
                    with open(loggingFilePath, "a+") as logFile:
                        logFile.write(message+"\n")
                except:
                    pass

def fJSONZip(msg: dict = None) -> dict:
    """
    Compress JSON message
    msg is dict()
    """
    fName = fJSONZip.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage["msgZip"] = ""

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    callId = str(uuid.uuid1())
    start = time.perf_counter()

    if type(msg) is not dict:
        return None

    if msg is not None:
        # key = "base64(zip(o))"
        try:
            #{'msgid': '', 'rAltitude': , 'publish': , 'rDestinationLat': , 'rGNSSSsattelitesinView': '', 
            # 'rGNSSSsattelitesUsed': '', 'rOriginLon': , 'rDistance': , 'rUTC': , 'rGLONASSsattelitesUsed': '', 'rOriginTimeUTC': , \
            #'rDestinationLon': , 'rStatusGPS': '', 'rSpeed': , 'rOriginLat': , 'uptime': , 'publicIPAddress': , 'hostname': }
            # map keys
            newKeys = {'msgid': 'a', 'rAltitude': 'b', 'publish': 'c', 'rDestinationLat': 'd', 'rGNSSSsattelitesinView': 'e', 'rGNSSSsattelitesUsed': 'f', 'rOriginLon': 'g', 'rDistance': 'h', 'rUTC': 'i', 'rGLONASSsattelitesUsed': 'k', 'rOriginTimeUTC': 'l', 'rDestinationLon': 'm', 'rStatusGPS': 'n', 'rSpeed': 'o', 'rOriginLat': 'p', 'uptime': 'r', 'publicIPAddress': 's', 'hostname': 't'}
            newMsg = dict([(newKeys.get(k), v) for k, v in msg.items()])
            msgZip = base64.b64encode(
                        zlib.compress(
                            json.dumps(newMsg,separators=(',',':')).encode('utf-8'), 9
                        )
                    ).decode('ascii')
            # decompress after
            # json.loads(zlib.decompress(b64decode(_['base64(zip(o))'])))
        except Exception as e:
            msgZip = None
            error[errId] = "Cannot compress the message: %s. The Error was: %s" %(str(msg), str(e))
            errId += 1
        else:
            returnMessage["msgZip"] = msgZip
    else:
        msgZip = None
        error[errId] = "Missing required variables."
        errId += 1

    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
    return returnMessage

def fGetPublicIP(ipAddressFilePath: str = None) -> str:
    """
    Get public IP from the local file
    """

    fName = fGetPublicIP.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage['ipAddress'] = None

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    callId = str(uuid.uuid1())
    start = time.perf_counter()

    if ipAddressFilePath is None:
        error[errId] = "The file path cannot be None."
        errId += 1
        elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
        return returnMessage

    try:
        fileHandle = open(ipAddressFilePath, "r")
        variables = yaml.load(fileHandle, Loader=yaml.FullLoader)
    except Exception as e:
        error[errId] = "Cannot open the file path %s or its content is not YAML: %s"%(str(ipAddressFilePath), str(e))
        errId += 1
    else:
        try:
            ipAddress = variables["ipAddress"]
        except Exception as e:
            error[errId] = "Cannot get the IP Address: %s"%(str(e))
            errId += 1
        else:
            try:
                ipaddress.ip_address(ipAddress)
            except Exception as e:
                error[errId] = "The IP address does not have a correct format: %s"%(str(e))
                errId += 1
            else:
                returnMessage['ipAddress'] = ipAddress
    
    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
    return returnMessage

def fGetUptime() -> int:
    """
    Get system uptime
    """
    rUptime = None
    try:
        rUptime = float(uptime())
    except Exception as e:
        rUptime = None
    
    return rUptime

def fGetHostname() -> str:
    """
    Get system hostname
    """
    try:
        hostname = os.uname()[1]
    except Exception as e:
        hostname = None
    
    return hostname
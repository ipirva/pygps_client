#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-
import os, sys, yaml, time, datetime, requests, json, base64, zlib, ipaddress, uuid
from uptime import uptime


def fCacheVars(vars: dict = None, cacheFilePath: str = None, action: str = None) -> dict:
    """
        Read / Write YAML data to file
        Return dict with the read data and statistics for read / write
    """
    fName = fCacheVars.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage["vars"] = dict()

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    callId = str(uuid.uuid1())
    start = time.perf_counter()

    if cacheFilePath is None or type(cacheFilePath) is not str:
        error[errId] = "The cache file path is not specified or its type is incorrect."
        errId += 1
        return returnMessage
    if action is None or type(action) is not str:
        error[errId] = "The action is not specified or its type is incorrect."
        errId += 1
        return returnMessage
    if action.lower() not in ["write", "read"]:
        error[errId] = "The action value is not valid"
        errId += 1
        return returnMessage

    if action.lower() != "read":
        if vars is None or type(vars) is not dict:
            error[errId] = "The variables are not specified or the type is incorrect."
            errId += 1
            return returnMessage
 
    if action.lower() == "read":
        try:
            fileHandle = open(cacheFilePath, "r")
        except Exception as e:
            error[errId] = "Cannot open %s for read." %str(cacheFilePath)
            errId += 1    
        else:
            success[successId] = "Could open %s for read." %str(cacheFilePath)
            successId += 1    

            try:
                variables = yaml.load(fileHandle, Loader=yaml.FullLoader)
            except Exception as e:
                error[errId] = "Cannot read YAML data from %s: %s." %(str(cacheFilePath), str(e))
                errId += 1
            else:
                success[successId] = "Could read YAML data from %s." %str(cacheFilePath)
                successId += 1
                try:
                    for k, v in variables.items():
                        returnMessage["vars"][k] = v
                except Exception as e:
                    error[errId] = "Cannot get data from YAML: %s." %(str(e))
                    errId += 1
            
            fileHandle.close()

    if action.lower() == "write":
        try:
            fileHandle = open(cacheFilePath, "w+")
        except Exception as e:
            error[errId] = "Cannot open %s for write." %str(cacheFilePath)
            errId += 1    
        else:
            success[successId] = "Could open %s for write." %str(cacheFilePath)
            successId += 1
            try:
                varsYAML = yaml.dump(vars)
            except Exception as e:
                error[errId] = "Cannot generate YAML data from %s: %s." %(str(vars), str(e))
                errId += 1
            else:
                try:
                    fileHandle.write(varsYAML)
                except Exception as e:
                    error[errId] = "Cannot write YAML data %s to file %s: %s." %(str(varsYAML), str(cacheFilePath), str(e))
                    errId += 1
                else:
                    success[successId] = "YAML wrote to file."
                    successId += 1
    
            fileHandle.close()

    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
    return returnMessage

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
            # 'rGNSSSsattelitesUsed': '', 'rOriginLon': , '_rDistance':, 'rDistance': , 'rUTC': , 'rGLONASSsattelitesUsed': '', 'rOriginTimeUTC': , \
            #'rDestinationLon': , 'rStatusGPS': '', 'rSpeed': , 'rOriginLat': , 'uptime': , 'publicIPAddress': , 'hostname': }
            # map keys
            newKeys = {'msgid': 'a', 'rAltitude': 'b', 'publish': 'c', 'rDestinationLat': 'd', 'rGNSSSsattelitesinView': 'e', 'rGNSSSsattelitesUsed': 'f', 'rOriginLon': 'g', '_rDistance': 'h', 'rDistance': 'i', 'rUTC': 'k', 'rGLONASSsattelitesUsed': 'l', 'rOriginTimeUTC': 'm', 'rDestinationLon': 'n', 'rStatusGPS': 'o', 'rLastGPSFix': 'p', 'rLastFixTimestampUTC': 'q', 'rSpeed': 'r', 'rOriginLat': 's', 'uptime': 't', 'publicIPAddress': 'u', 'hostname': 'v'}
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
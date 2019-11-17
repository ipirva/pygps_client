#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

def fLoadVars(file: str = None) -> dict:
    """
        read YAML file with needed variables
        make this variable available
    """
    returnVar = dict()
    
    if file is None:
        return None

    setupFile = file
    try:
        fileHandle = open(setupFile, "r")
        # deprecated https://msg.pyyaml.org/load
        # variables = yaml.load_all(fileHandle)
        variables = yaml.load(fileHandle, Loader=yaml.FullLoader)
    except Exception as e:
        sys.exit("Unable to read or/and load: "+setupFile+"Error: "+str(e))
    else:
        returnVar = variables

    return returnVar

def fWriteLog(callId: str = None, f: str = None, message: str = None, level: str = None) -> str:
    """
        write log message to a file on the disk
        use logging levels
        - logLevelsShow - to filter log levels to be stored
        - level - to be used for the specific log
    """

    fName = fWriteLog.__name__

    logLevels = ["info", "warning", "critical", "debug"]

    try:
        # vars defined in main
        myLogLevelsShow = logLevelsShow
        myLoggingFilePath = logPath
    except NameError:
        myLogLevelsShow = logLevels
        myLoggingFilePath = "/tmp/getipaddress.log"

    timeNow = datetime.datetime.now().isoformat()
    
    if f is None:
        f = "Unknown function"
    if level is None:
        level = "INFO"
    else:
        level = level.upper()

    # check for defined log levels
    if level.lower() in myLogLevelsShow:
        if message is not None:
            message = str(callId)+" ::: "+str(f)+" ::: "+str(level)+" ::: "+str(timeNow)+" ::: "+str(message)
            try:
                with open(myLoggingFilePath, "a+") as logFile:
                    logFile.write(message+"\n")
            except:
                pass
    
    return "OK"

def fRequestsRetrySession(retries=3, backoff_factor=0.3, status_forcelist=(400, 401, 403, 404, 405, 500, 501, 502, 504), session=None):
    """
        Request session retry
    """
    
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def fGetPublicIP(apiURL: str = None, offline: bool = False) -> dict:
    """
        Get public IP call
    """

    fName = fGetPublicIP.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    returnMessage['timestamp'] = int(time.time())

    returnMessage['ipAddress'] = None

    callId = str(uuid.uuid1())
    start = time.perf_counter()
    fWriteLog(callId, fName, f"START Call.", "info")

    # read local file
    if offline == True:
        fWriteLog(callId, fName, f"Offline lookup is True: {str(ipAddressFilePath)}", "info")
        try:
            fileHandle = open(ipAddressFilePath, "r")
            variables = yaml.load(fileHandle, Loader=yaml.FullLoader)
        except Exception as e:
            fWriteLog(callId, fName, f"Cannot open the file path or its content is not YAML: {str(e)}", "error")
            error[errId] = f"Cannot open the file path or its content is not YAML: {str(e)}"
            errId += 1
        else:
            try:
                ipAddress = variables["ipAddress"]
            except Exception as e:
                fWriteLog(callId, fName, f"Cannot get the IP Address: {str(e)}", "error")
                error[errId] = f"Cannot get the IP Address: {str(e)}"
                errId += 1
            else:
                try:
                    ipaddress.ip_address(ipAddress)
                except Exception as e:
                    fWriteLog(callId, fName, f"The IP address does not have a correct format: {str(e)}", "error")
                    error[errId] = f"The IP address does not have a correct format: {str(e)}"
                    errId += 1
                    ipAddress = None
                else:
                    returnMessage['ipAddress'] = ipAddress
    # call API
    if offline == False:
        fWriteLog(callId, fName, f"Offline lookup is False.", "info")
        if apiURL == None:
            fWriteLog(callId, fName, f"Key apiURL not defined, use the default: {str(apiURL)}", "info")
            apiURL = "https://api6.ipify.org?format=json"
    
        success[successId] = f"API call to be done to {str(apiURL)}."
        successId += 1
        
        apiGetHeaders = {'Content-Type': 'application/json'}

        try:
            apiGetResponse = fRequestsRetrySession().get(apiURL, headers=apiGetHeaders, timeout=(2,5))
        except Exception as e:
            error[errId] = f"IP API call failed: {str(e.__class__.__name__)}"
            errId += 1
        else:
            httpCode = apiGetResponse.status_code

            fWriteLog(callId, fName, f"API call HTTP response: {str(httpCode)}", "info")

            if httpCode == 200:
                try:
                    apiGetResponse = json.loads(apiGetResponse.content.decode('utf-8'))
                except Exception as e:
                    fWriteLog(callId, fName, f"API call response is not JSON formatted.", "error")
                    error[errId] = f"Cannot decode API response: {str(e)}"
                    errId += 1
                else:
                    success[successId] = f"API call returned response {str(httpCode)}."
                    successId += 1
            else:
                fWriteLog(callId, fName, f"API call HTTP response is not 200.", "error")
                error[errId] = f"API call returned response {str(httpCode)}."
                errId += 1

        
        try:
            ipAddress = apiGetResponse['ip']
        except Exception as e:
            fWriteLog(callId, fName, f"API call response does not contain key 'ip'.", "error")
            error[errId] = f"Cannot get the IP address: {str(e)}."
            errId += 1
        else:
            fWriteLog(callId, fName, f"API call response does contain key 'ip': {str(ipAddress)}.", "info")
            success[successId] = f"The IP address was retrieved."
            successId += 1

            returnMessage['ipAddress'] = ipAddress

    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
    fWriteLog(callId, fName, f"END Call. Duration: {str(elapsed)}", "info")

    return returnMessage

def fWriteFile(data: dict = None, filePath: str = None) -> dict:
    """
        Write to file
    """

    fName = fWriteFile.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage['successful'] = 0

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    callId = str(uuid.uuid1())
    start = time.perf_counter()
    fWriteLog(callId, fName, f"START Call.", "info")

    if filePath is None:
        fWriteLog(callId, fName, f"filePath cannot be None.", "error")

        error[errId] = f"Received filePath in None"
        errId += 1
    else:
        fWriteLog(callId, fName, f"Store IP address to file: {str(filePath)}.", "info")
        if data is not None:
            if type(data) is dict:
                try:
                    dataYML = yaml.dump(data)
                except Exception as e:
                    fWriteLog(callId, fName, f"Cannot dump YAML content for {str(data)}.", "error")
                    error[errId] = f"Cannot dump YAML content for {str(data)}: {str(e)}"
                    errId += 1
                else:
                    fWriteLog(callId, fName, f"Received correct data format: {str(data)}.", "info")
                    # compare w/ the existing stored data
                    responseIPAddress = fGetPublicIP(offline = True)
                    if "ipAddress" in responseIPAddress.keys():
                        if responseIPAddress["ipAddress"] is not None:
                            # ip address available
                            ipAddressOld = responseIPAddress["ipAddress"]
                            try:
                                ipAddressNew = data["ipAddress"]
                            except Exception as e:
                                pass
                            else:
                                if ipAddressOld == ipAddressNew:
                                    fWriteLog(callId, fName, f"IP did not change: {str(ipAddressOld)}", "info")
                                else:
                                    fWriteLog(callId, fName, f"IP did change: {str(ipAddressOld)} => {str(ipAddressNew)}", "info")
                        else:
                            fWriteLog(callId, fName, f"Saved ipAddress seems to be None.", "error")
                    else:
                        fWriteLog(callId, fName, f"Cannot get saved ipAddress.", "error")
                    # write data
                    try:
                        f = open(filePath,"w+")
                        f.write(dataYML)
                    except Exception as e:
                        fWriteLog(callId, fName, f"Cannot write data {str(data)} to file {str(filePath)}: {str(e)}.", "error")
                        error[errId] = f"Cannot write data {str(data)} to file {str(filePath)}: {str(e)}"
                        errId += 1
                    else:
                        fWriteLog(callId, fName, f"Data was written to file: {str(filePath)}.", "info")
                        success[successId] = "Data was written to file."
                        successId += 1
                        returnMessage['successful'] = 1
            else:
                fWriteLog(callId, fName, f"Received data is not a dictionary: {str(type(data))}.", "error")
                error[errId] = f"Received data is not a dictionary: {str(type(data))}"
                errId += 1
        else:
            fWriteLog(callId, fName, f"data cannot be None.", "error")
            error[errId] = f"Received data in None"
            errId += 1

    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
    fWriteLog(callId, fName, f"END Call. Duration: {str(elapsed)}", "info")

    return returnMessage

def main():
    
    fName = "Main"
    callId = str(uuid.uuid1())

    responseIPAddress = fGetPublicIP(apiURL = apiURL, offline = False)
    # debug
    fWriteLog(callId, fName, f"{str(responseIPAddress)}", "debug")

    if "ipAddress" in responseIPAddress.keys():
        if responseIPAddress["ipAddress"] is None:
            fWriteLog(callId, fName, f"Returned ipAddress is None.", "error")
        # ip address
        ipAddress = responseIPAddress["ipAddress"]
        try:
            ipTimestamp = responseIPAddress["timestamp"]
        except Exception as e:
            fWriteLog(callId, fName, f"Key ipTimestamp not present: {str(e)}. Use the current timestamp instead.", "warning")
        else:
            ipTimestamp = int(time.time())
        # write file
        data = dict()
        data["ipAddress"] = ipAddress
        data["ipTimestamp"] = ipTimestamp
        
        responsefWriteFile = fWriteFile(data = data, filePath = ipAddressFilePath)
        # debug
        fWriteLog(callId, fName, f"{str(responsefWriteFile)}", "debug")
    else:
        fWriteLog(callId, fName, f"No ipAddress was returned.", "error")


if __name__ == '__main__':
    
    import time
    import json, yaml
    import datetime
    import uuid
    import os, sys
    import ipaddress

    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

    _scriptDir = os.path.dirname(os.path.realpath(__file__))
    _nameBase = os.path.splitext(os.path.basename(__file__))[0]
    _varFile = _nameBase+".yml"
    var = fLoadVars(file = _scriptDir+"/"+_varFile)

    try:
        var["loggingFilePath"]
    except Exception as e:
        logPath = _scriptDir+"/"+_nameBase+".log"

    try:
        apiURL = var["apiGetIPURL"]
        ipAddressFilePath = var["filePath"]
        logLevelsShow = var["logLevelsShow"]
    except Exception as e:
        sys.exit("Check the default variables: "+str(e))

    main()

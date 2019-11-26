#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

import json, os, uuid, time, sys
import requests
import jwt
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from functions.functions import fJSONZip
from functions.functions import fLoadVars
from functions.functions import fGetPublicIP

"""
Compress the JSON Msg
Publish the compressed messaege
    - get JWT w/ mTLS authentication
    - prepare the HTTP headers
    - compress the message to be published
    - POST to the remote endpoint
"""


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

def fGetJWT() -> dict:
    """
    GET JWT token
    """
    fName = fGetJWT.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    returnMessage['token'] = None
    returnMessage['ipAddress'] = None

    returnMessage['cache'] = True

    callId = str(uuid.uuid1())
    start = time.perf_counter()
    
    try:
        _scriptDir = os.path.dirname(os.path.realpath(__file__))
        _nameBase = os.path.splitext(os.path.basename(__file__))[0]
        _varFile = _nameBase+".yml"
        var = fLoadVars(file = _scriptDir+"/"+_varFile)

        JWTEndpointURL = var["JWTEndpointURL"]
        
        APIRootCAPath =  _scriptDir+"/"+var["APIRootCAPath"]
        APICertificatePath = _scriptDir+"/"+var["APICertificatePath"]
        APIPrivateKeyPath = _scriptDir+"/"+var["APIPrivateKeyPath"]

        ipAddressFilePath = var["ipAddressFilePath"]
        
        jwtCacheFilePath = _scriptDir+"/"+var["jwtCacheFilePath"]
        jwtCacheBuffer = var["jwtCacheBuffer"]

    except Exception as e:
        error[errId] = "Cannot load the var files or a specific var is not defined: %s" %str(e)
        errId += 1
        elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)

        return returnMessage
    else:
        success[successId] = "Loaded the default variables"
        successId += 1
    
    responseGetIP = fGetPublicIP(ipAddressFilePath)
    if "ipAddress" in responseGetIP.keys():
        ipAddress = str(responseGetIP["ipAddress"])
        returnMessage['ipAddress'] = ipAddress
    else:
        ipAddress = None

    apiGETHeaders = {'X-IP-Address': ipAddress}

    # read jwt from cache
    cacheJWT = None
    timeDelta = 0
    try:
        with open(jwtCacheFilePath, 'r') as hdlCacheJWT:
            cacheJWT = str(hdlCacheJWT.read())
    except Exception as e:
        error[errId] = "Cannot read cached JWT from %s: %s" %(str(jwtCacheFilePath),str(e))
        errId += 1
    else:
        success[successId] = "Can read cached JWT from %s." %(str(jwtCacheFilePath))
        successId += 1
        try:
            # decode without verify it
            cacheJWTDecode = jwt.decode(cacheJWT, verify=False)
        except Exception as e:
            error[errId] = "Cannot decode cached JWT %s from %s: %s" %(str(cacheJWT),str(jwtCacheFilePath),str(e))
            errId += 1
        else:
            success[successId] = "Can decode cached JWT from %s." %(str(jwtCacheFilePath))
            successId += 1
            token = cacheJWT
            if type(cacheJWTDecode) == dict:
                if "exp" in cacheJWTDecode.keys():
                    try:
                        timeDelta = int(cacheJWTDecode["exp"]) - int(time.time())
                    except Exception as e:
                        error[errId] = "Cannot calculate cached JWT %s remaining lifetime: %s" %(str(cacheJWTDecode),str(e))
                        errId += 1
                    else:
                        success[successId] = "Cached JWT remaining lifetime %s." %(str(timeDelta))
                        successId += 1
                else:
                    error[errId] = "Cannot find exp key in the decoded cached JWT %s" %(str(cacheJWTDecode))
                    errId += 1
            else:
                error[errId] = "Decoded cached JWT %s does look mode like a %s than a dict." %(str(cacheJWTDecode),str(type(cacheJWTDecode)))
                errId += 1


    if timeDelta == 0 or timeDelta < jwtCacheBuffer or timeDelta < 0:
        # cached JWT is nearly expired
        cacheJWT = None
        error[errId] = "Cached JWT is expired"
        errId += 1


    if cacheJWT is None:
        returnMessage['cache'] = False
        # get HTTP
        try:
            apiGetResponse = fRequestsRetrySession().get(
                        JWTEndpointURL,
                        cert=(APICertificatePath, APIPrivateKeyPath),
                        verify=APIRootCAPath,
                        headers=apiGETHeaders, timeout=(2,5)
                    )
        except Exception as e:
            error[errId] = "HTTP GET JWT returned the following error: %s" %str(e)
            errId += 1
        else:
            success[successId] = "HTTP GET JWT API call completed successfully"
            successId += 1
            httpCode = apiGetResponse.status_code

            if httpCode == 200:
                try:
                    apiGetResponse = json.loads(apiGetResponse.content.decode('utf-8'))
                except Exception as e:
                    error[errId] = "Cannot decode HTTP GET JWT API response: %s" %str(e)
                    errId += 1
                else:
                    success[successId] = "HTTP GET JWT API call returned response: %s" %str(httpCode)
                    successId += 1
                    # get the token out of the response
                    try:
                        token = apiGetResponse["token"]
                    except Exception as e:
                        error[errId] = "Cannot get the token from the HTTP GET JWT API response: %s" %str(e)
                        errId += 1
                    else:
                        try:
                            jwt.decode(token, verify=False)
                        except Exception as e:
                            error[errId] = "Cannot decode received token %s: %s" %(str(token), str(e))
                            errId += 1
                        else:
                            success[successId] = "HTTP GET JWT API call returned an JWT token: %s" %str(token)
                            successId += 1
                            # write to cache
                            try:
                                with open(jwtCacheFilePath, 'w+') as hdlCacheJWT:
                                    hdlCacheJWT.write(token)
                            except Exception as e:
                                error[errId] = "Cannot write token to cache %s: %s" %(str(jwtCacheFilePath), str(e))
                                errId += 1
                            else:
                                success[successId] = "JWT token cached to: %s" %str(jwtCacheFilePath)
                                successId += 1
            else:
                # HTTP get JWT returned HTTP code other than 200
                error[errId] = "HTTP GET JWT API call returned response %s" %str(httpCode)
                errId += 1
    
    returnMessage['token'] = token

    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)

    return returnMessage

def fEndpointPublish(msg: dict = None, token: str = None) -> dict:

    """
    Compress the JSON Msg
    Publish the compressed messaege
        - get JWT w/ mTLS authentication
        - prepare the HTTP headers
        - compress the message to be published
        - POST to the remote endpoint
    """
    fName = fEndpointPublish.__name__

    returnMessage = dict()
    returnMessage['functionName'] = fName
    returnMessage['error'] = dict()
    returnMessage['success'] = dict()
    error = returnMessage['error']
    success = returnMessage['success']
    errId = 0; successId = 0

    returnMessage['published'] = False

    returnMessage['metrics'] = dict()
    metrics = returnMessage['metrics']

    callId = str(uuid.uuid1())
    start = time.perf_counter()

    try:
        _scriptDir = os.path.dirname(os.path.realpath(__file__))
        _nameBase = os.path.splitext(os.path.basename(__file__))[0]
        _varFile = _nameBase+".yml"
        
        var = fLoadVars(file = _scriptDir+"/"+_varFile)
        
        APIURL = var["APIURL"]
        APIEndpoint = var["APIEndpoint"]
    except Exception as e:
        error[errId] = "Cannot load the var files or a specific var is not defined: %s" %str(e)
        errId += 1
        elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
        return returnMessage
    else:
        success[successId] = "Loaded the default variables"
        successId += 1
    
    if msg is None:
        error[errId] = "Message msg variable cannot be None."
        errId += 1
        elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)
        return returnMessage
    
    APIEndpointURL = APIURL+APIEndpoint
    
    try:
        fJSONZipResult = fJSONZip(msg)
    except Exception as e:
        error[errId] = "Compress message action returned: %s" %str(e)
        errId += 1
    else:
        success[successId] = "JSON Zip function completed successfully."
        successId += 1
        if "msgZip" in fJSONZipResult.keys():
            msgCompress = fJSONZipResult["msgZip"]
            success[successId] = "JSON Zip function returned compressed message."
            successId += 1
        else:
            error[errId] = "Compress message function did not return the right key, value pairs."
            errId += 1

        if type(msgCompress) is not str:
            error[errId] = "Compress message type is not correct: %s" %str(type(msgCompress))
            errId += 1   
        
        if type(msgCompress) is str:
            success[successId] = "Compressed message is string."
            successId += 1
            # handle the publish action
            # get ip address
            responseGetIP = fGetPublicIP(var["ipAddressFilePath"])
            if "ipAddress" in responseGetIP.keys():
                ipAddress = responseGetIP["ipAddress"]
            else:
                ipAddress = None

            if token is not None:
                # valid token here
                # publish POST
                apiPOSTHeaders = {"Content-Type": "application/json", "Authorization": "Bearer "+token, "X-IP-Address": ipAddress}
                try:
                    apiPOSTResponse = fRequestsRetrySession().post(APIEndpointURL, data=json.dumps({"item": msgCompress}), headers=apiPOSTHeaders, timeout=(2,5))
                except Exception as e:
                    error[errId] = "Data POST was not successful: %s" %str(e)
                    errId += 1
                else:
                    success[successId] = "Data POST was successful."
                    successId += 1
                    httpResponseCode = apiPOSTResponse.status_code
                    httpResponseHeaders = apiPOSTResponse.headers
                    httpResponseContent = apiPOSTResponse.content
                    success[successId] = "POST Response Code: %d" %int(httpResponseCode)
                    successId += 1
                    success[successId] = "POST Response Headers: %s" %str(httpResponseHeaders)
                    successId += 1
                    success[successId] = "POST Response Content: %s" %str(httpResponseContent.decode('utf-8'))
                    successId += 1
                    try:
                        httpResponseContent = json.loads(httpResponseContent.decode('utf-8'))
                    except Exception as e:
                        error[errId] = "Data POST response content invalid: %s" %str(e)
                        errId += 1
                    else:
                        if "Success" in httpResponseContent.keys():
                            # message was correctly received and stored by the remote endpoint
                            returnMessage['published'] = True
                            success[successId] = "Data POST content validated by remote server."
                            successId += 1
                        else:
                            error[errId] = "Data POST content not validated by remote server."
                            errId += 1
                
            else:
                error[errId] = "JWT token not valid. Returned JWT token is: %s" %str(token)
                errId += 1
    elapsed = time.perf_counter() - start; metrics['elapsed'] = round(elapsed,5)

    return returnMessage
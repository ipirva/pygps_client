#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

import pika
import json
import sys, os, re, uuid
import time, datetime
# pip3 install jsonschema
from jsonschema import validate as fEXTJsonValidate
import hashlib
import zlib, base64

from endpointpublish.endpointpublish import fEndpointPublish, fGetJWT
from functions.functions import fGetUptime
from functions.functions import fGetPublicIP
from functions.functions import fGetHostname

"""
Read messages published to queue
Enrich message content
Call the function to publish the message to remote API endpoint
"""

fileName = "Main"
_scriptDir = os.path.dirname(os.path.realpath(__file__))

"""
fConsumeCallback ::: DEBUG ::: 2018-12-05T23:11:30.981483 ::: The consume callback function got the body message (str):
{"msgid": "89b5eefd51f530615f49758620c8cdcf", "publish": {"publish": 3}, "rAltitude": 38.773, "rDestinationLat": xxx, 
"rDestinationLon": xxx, "rDistance": {"cdistance": 0.01, "distance": 0.00039930959754097274, "units": "Km"}, "rGLONASSsattelitesUsed": 0, 
"rGNSSSsattelitesUsed": 11, "rGNSSSsattelitesinView": 12, "rOriginLat": xxx, "rOriginLon": xxx, "rOriginTimeUTC": 20191112211801, 
"rSpeed": 0.0, "rStatusGPS": "Location 3D Fix", "rUTC": 20191112211808}
fProcessMsg ::: DEBUG ::: 2018-12-05T23:11:30.991337 ::: Got a body message.
fProcessMsg ::: DEBUG ::: 2018-12-05T23:11:30.998031 ::: [0a9cdff290bdf991c30c11109a958e16] The body message has a valid JSON format.
fProcessMsg ::: DEBUG ::: 2018-12-05T23:11:31.102600 ::: JSON data schema validatation was successful.
"""

# the schema to validate the body data
msgJSONSchema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$ref": "#/definitions/GPSValues",
    "definitions": {
        "GPSValues": {
            "type": "object",
            "properties": {
                "rAltitude": {
                    "type": "number"
                },
                "rDestinationLat": {
                    "type": "number"
                },
                "rDestinationLon": {
                    "type": "number"
                },
                "_rDistance": {
                    "type": "number"
                },
                "rDistance": {
                    "$ref": "#/definitions/RDistance"
                },
                "rOriginLat": {
                    "type": "number"
                },
                "rOriginLon": {
                    "type": "number"
                },
                "rOriginTimeUTC": {
                    "type": "integer",
                    "minimum": 20181202182023
                },
                "rSpeed": {
                    "type": "number",
                    "minimum": 0
                },
                "rUTC": {
                    "type": "integer",
                    "minimum": 20181202182023
                },
                "rStatusGPS": {
                    "type": "string"
                },
                "rLastGPSFix": {
                    "type": "string"
                },
                "rLastFixTimestampUTC": {
                    "type": "integer",
                    "minimum": 20181202182023
                },
                "msgid": {
                    "type": "string"
                },
                "rGLONASSsattelitesUsed": {
                    "type": "integer",
                    "minimum": 0
                },
                "rGNSSSsattelitesUsed": {
                    "type": "integer",
                    "minimum": 0
                },
                "rGNSSSsattelitesinView": {
                    "type": "integer",
                    "minimum": 0
                }
            },
            "required": [
                "rAltitude",
                "rDestinationLat",
                "rDestinationLon",
                "_rDistance",
                "rDistance",
                "rOriginLat",
                "rOriginLon",
                "rOriginTimeUTC",
                "rSpeed",
                "rUTC", 
                "rStatusGPS",
                "rLastGPSFix",
                "rLastFixTimestampUTC",
                "msgid",
                "rGLONASSsattelitesUsed",
                "rGNSSSsattelitesUsed",
                "rGNSSSsattelitesinView"
            ],
            "title": "GPSValues"
        },
        "RDistance": {
            "type": "object",
            "properties": {
                "distance": {
                    "type": "number",
                    "minimum": 0
                },
                "cdistance": {
                    "type": "number",
                    "minimum": 0
                },
                "units": {
                    "type": "string",
                    "enum": [
                        "Km",
                        "m"
                    ]
                }
            },
            "required": [
                "distance",
                "cdistance",
                "units"
            ],
            "title": "RDistance"
        }
    }
}


def fConsumeCallback(ch, method, properties, body):
    fName = fConsumeCallback.__name__
    callId = str(uuid.uuid1())
    try:
        body = body.decode('utf-8')
    except Exception as e:
        logM = "Errors while decoding the body message: %s" % str(e)
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        fProcessMsg(None)
    else:
        logM = "The consume callback function got the body message (str): %s" % str(body)
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "debug")
        responseProcessMsg = fProcessMsg(body)
        if responseProcessMsg is not None:
            try:
                # ack message
                ch.basic_ack(delivery_tag = method.delivery_tag, multiple = False)
            except Exception as e:
                logM = "Cannot ACK message %s: %s" % (str(method.delivery_tag), str(e))
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "error")
            else:
                logM = "ACK message ok: %s" % str(method.delivery_tag)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
        else:
            logM = "The message is not to be published."
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "error")
            # requeue message
            try:
                ch.basic_nack(delivery_tag = method.delivery_tag, requeue=True)
            except Exception as e:
                logM = "Cannot requeue message %s: %s" % (str(method.delivery_tag), str(e))
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "error")
            else:
                logM = "The message is requeued %s." % str(method.delivery_tag)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "error")


def fCheckJSON(jstr = None, jschema = None):
    """
    Validate JSON against schema
    """
    fName = fCheckJSON.__name__
    callId = str(uuid.uuid1())
    try:
        fEXTJsonValidate(jstr, jschema)
    except Exception as e:
        logM = "Errors validating msg: "+str(e)
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        return None
    else:
        logM = "JSON data correctly validated against the schema."
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
        return True

def fProcessMsg(msg = None):
    """
    Get the msg read from the var["queue"]
    Check it and store it to influxdb
    """
    fName = fProcessMsg.__name__
    callId = str(uuid.uuid1())

    returnMessage = None

    # default message ID
    msgid = 0
    if msg is not None:
        logM = "Got a body message."
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
        # expects a json fomat message
        try:
            lMsg = json.loads(msg)
            if "msgid" in lMsg:
                msgid = lMsg["msgid"]
        except Exception as e:
            logM = "[%s] The body message has not a valid JSON format: %s. The error was: %s" % (str(msgid), str(lMsg), str(e))
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        else:
            logM = "[%s] The body message has a valid JSON format: %s" %(str(msgid), str(lMsg))
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
            # msg json valid, check its fields
            # {"rAltitude": xxx, "rDestinationLat": xxx, "rDestinationLon": xxx, "rDistance": {"distance": 0.0, "units": "Km"}, 
            # "rOriginLat": xxx, "rOriginLon": xxx, "rOriginTimeUTC": 20181202182023, "rSpeed": 0.0, "rUTC": "20181202182038"}
            # online schema gen https://app.quicktype.io/#l=schema
            try:
                rValidateJSON = fEXTJsonValidate(lMsg, msgJSONSchema)
            except Exception as e:
                logM = "[%s] JSON data schema validatation was not successful: %s" %(str(msgid), str(e))
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
                return None
            else:
                # data validation successful
                logM = "[%s] JSON data schema validatation was successful." % str(msgid)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")
                # message available - publish 1 (distance), 2 (forced - like when system re/starts) or 3 (beacon if no movement)
                # {'rGNSSSsattelitesinView': 11, 'rOriginLat': xxx, 'rOriginLon': xxx, 'msgid': 'd64cab02f56afe6750288e47cfa44245', 
                # 'rDistance': {'units': 'Km', 'distance': 0.0, 'cdistance': 0.01}, \
                # 'rAltitude': xxx, 'rStatusGPS': 'Location 3D Fix', 'publish': {'publish': 3}, 'rUTC': 20191010221837, 
                # 'rOriginTimeUTC': 20191010221830, 'rDestinationLat': xxx, 'rGLONASSsattelitesUsed': '', \
                # 'rGNSSSsattelitesUsed': '10', 'rSpeed': 0.0, 'rDestinationLon': xxx}
                #
                # {"msgid": "3ec64c23e72ff769f7bcc823f2e80dc6", "publish": {"publish": 3}, "rAltitude": 0.0, "rDestinationLat": 1000, 
                # "rDestinationLon": 1000, "rDistance": {"cdistance": 0.01, \
                # "distance": 0.0, "units": "Km"}, "rGLONASSsattelitesUsed": 0, "rGNSSSsattelitesUsed": 0, "rGNSSSsattelitesinView": 0, 
                # "rOriginLat": 1000, "rOriginLon": 1000, "rOriginTimeUTC": 20181202182023, "rSpeed": 0.0, \
                # "rStatusGPS": "Unknown: []", "rUTC": 20181202182023}
                # we got one message; what do we do with it?
                # call method
                # Get JWT Token
                responsefGetJWT = fGetJWT()
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, json.dumps(responsefGetJWT, sort_keys=True), "debug")
                #
                if "token" in responsefGetJWT.keys():
                    token = responsefGetJWT["token"]
                    if token is not None:
                        token = responsefGetJWT["token"]
                        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, "Did get JWT token.", "info")
                        # enrich the data
                        lMsg['uptime'] = fGetUptime()
                        lMsg['hostname'] = fGetHostname()
                        # get ip address
                        responseGetIP = fGetPublicIP(var["ipAddressFilePath"])
                        if "ipAddress" in responseGetIP.keys():
                            lMsg['publicIPAddress'] = responseGetIP["ipAddress"]
                        else:
                            lMsg['publicIPAddress'] = None
                        logM = "[%s] The message was enriched: %s." % (str(msgid), lMsg)
                        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "debug")
                        # Enpoint API publish
                        publishMsgResult = fEndpointPublish(msg=lMsg, token=token) 
                        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, json.dumps(publishMsgResult, sort_keys=True), "debug")
                        if "published" in publishMsgResult.keys():
                            if publishMsgResult["published"] is True:
                                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, "The message was published and ack by the remote endpoint.", "info")
                                # message published and ack by the API endpoint
                                returnMessage = "ok"
                            else:
                                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, "The message was not ack by the remote endpoint.", "error")
                        else:
                            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, "The message was not ack by the remote endpoint.", "error")
                                
                    else:
                        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, "Did not get JWT token.", "error")
                else:
                    fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, "Did not get JWT token.", "error")
    else:
        logM = "No message received."
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")

    return returnMessage

def fConsume(queue = None):
    """
    Consume a message from a specific RabbitMQ var["queue"]
    """    
    fName = fConsume.__name__
    callId = str(uuid.uuid1())

    if queue is not None:
        try:
            # connect to RabbitMQ
            rbmqCredentials = pika.PlainCredentials(username=var["rbmqUsername"], password=var["rbmqPassword"])
            rbmqConn = pika.BlockingConnection(
                            pika.ConnectionParameters(
                                host='127.0.0.1',
                                credentials=rbmqCredentials
                            )
                        )
        except Exception as e:
            logM = "Errors RabbitMQ connect: %s" % str(e)
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
            rbmqConn.close()
        else:
            logM = "Connected to queue %s!" % queue
            fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "debug")

            try:
                rbmqChannel = rbmqConn.channel()
                #rbmqChannel.basic_qos(prefetch_count=100)
                rbmqChannel.basic_consume(
                    queue,
                    fConsumeCallback,
                    auto_ack=False
                )
                rbmqChannel.start_consuming()
            except Exception as e:
                logM = "Error RabbitMQ consume: %s" % str(e)
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
                rbmqConn.close()
            else:
                logM = "Connected to queue %s and ready to consume!" % queue
                fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "info")

            # rbmqConn.close()
    else:
        logM = "Got no valid queue name!"
        fWriteLog(callId, var["loggingFilePath"], var["logLevelsShow"],  fName, logM, "critical")
        return None

def main():
    """
    Consume queue content
    """
    fConsume(var["queue"])
    
if __name__ == "__main__":
    from functions.functions import fLoadVars
    from functions.functions import fWriteLog
    # load variables
    _nameBase = os.path.splitext(os.path.basename(__file__))[0]
    _varFile = _nameBase+".yml"
    var = fLoadVars(file = _scriptDir+"/"+_varFile)
    try:
        var["loggingFilePath"]
    except Exception as e:
        var["loggingFilePath"] = _scriptDir+"/logs/"+_nameBase+".log"
    # check if I can write to logfile, if not, exit
    try:
        fileHandle = open(var["loggingFilePath"], "a+")
    except IOError:
        sys.exit("Unable to write to log file: "+var["loggingFilePath"])
    # run the main
    main()

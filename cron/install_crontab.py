#!/usr/local/bin/python3.7
# -*- coding: utf-8 -*-

# pip3 install python-crontab
from crontab import CronTab
import os, getpass

"""
Install crontab
"""
#
userName = getpass.getuser()
fileName = "getipaddress.py"
scriptDir = os.path.dirname(os.path.realpath(__file__))
filePath = scriptDir+"/"+fileName
# script user
cron = CronTab(user=userName)
job = cron.new(command="/usr/local/bin/python3.7 "+filePath)
job.minute.every(10)

cron.write()

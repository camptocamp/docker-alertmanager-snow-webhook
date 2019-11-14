#!/usr/bin/python3
# -*- coding: utf-8 -*-
import requests
import yaml
import json
import os
import sys

URL = os.environ['SNOW_API_URL']

PASSWORD_FILE = os.environ['SNOW_API_PASSWORD_FILE']

HEADERS = {"Content-Type":"application/json","Accept":"application/json"}
LABEL_SERVICE_ID = os.environ.get('ALERTMANAGER_LABEL_SNOW_ID', 'project')
LABEL_SERVICE_PRIORITY = os.environ.get('ALERTMANAGER_LABEL_SNOW_PRIORITY', 'snow_priority')
try:
    DEBUG = int(os.environ.get('DEBUG', '0'))
except ValueError:
    DEBUG = 0

def getPass(filename, service):
    username = None
    password = None
    with open(filename) as f:
        passdata = yaml.load(f)
        if service in passdata:
            username = passdata[service].get('username', None)
            password = passdata[service].get('password', None)
    if username == None or password == None:
        return None
    return ( username, password )

alertmanagerdata = json.loads(sys.argv[1])
if DEBUG:
    print("[DEBUG] alertmanagerdata : %s" % alertmanagerdata)

priority = 1
state = 'Down'
if LABEL_SERVICE_PRIORITY in alertmanagerdata['commonLabels'].keys():
    priority = alertmanagerdata['commonLabels'][LABEL_SERVICE_PRIORITY]
if alertmanagerdata['status'] == 'resolved':
    priority = 5
    state = 'Up'

if DEBUG:
    print("[DEBUG] priority : %s" %priority)
    print("[DEBUG] state : %s" %state)

description = 'Automatic Service {} via Camptocamp Monitoring.'.format(state)

if DEBUG:
    print("[DEBUG] description : %s" % description)

data = {
        "u_business_service" : alertmanagerdata['groupLabels'][LABEL_SERVICE_ID],
        "u_priority" : priority,
        "u_short_description" : description,
        "u_description" : description,
}
auth = getPass(PASSWORD_FILE, data['u_business_service'])
if auth == None:
    print('no entry in password file for service "' + data['u_business_service'] + '"')
    sys.exit(1)

response = requests.post(URL, auth=auth, headers=HEADERS, data=json.dumps(data).strip())
if DEBUG:
    print("[DEBUG] response : %s" % response)

print("ServiceNow returned %s" % response.status_code)

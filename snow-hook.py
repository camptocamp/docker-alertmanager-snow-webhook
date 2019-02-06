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
LABEL_NAME = os.environ.get('ALERTMANAGER_LABEL_SNOW_ID', 'project')

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

priority = 1
description = 'Automatic Service Down via Camptocamp Monitoring.'
if alertmanagerdata['status'] == 'resolved':
    priority = 5
    description = 'Automatic Service Up via Camptocamp Monitoring.'

data = {
        "u_business_service" : alertmanagerdata['groupLabels'][LABEL_NAME],
        "u_priority" : priority,
        "u_short_description" : description,
        "u_description" : description,
}
auth = getPass(PASSWORD_FILE, data['u_business_service'])
if auth == None:
    print('no entry in password file for service "' + data['u_business_service'] + '"')
    sys.exit(1)

response = requests.post(URL, auth=auth, headers=HEADERS, data=json.dumps(data).strip())

print("ServiceNow returned %s" % response.status_code)

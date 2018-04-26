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

data = {
        "u_business_service" : alertmanagerdata['groupLabels'][LABEL_NAME],
        "u_priority" : 5 if alertmanagerdata['status'] == "resolved" else 1,
        "u_short_description" : 'Automatic Service Down via Camptocamp Monitoring.',
        "u_description" : 'ToDo',
}
auth = getPass(PASSWORD_FILE, data['u_business_service'])
if auth == None:
    print('no entry in password file for service "' + data['u_business_service'] + '"')
    sys.exit(1)

response = requests.post(URL, auth=auth, headers=HEADERS, data=json.dumps(data).strip())

print("ServiceNow returned %s" % response.status_code)

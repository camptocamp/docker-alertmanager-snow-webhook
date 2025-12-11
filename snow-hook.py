#!/usr/bin/python3
# -*- coding: utf-8 -*-
import requests
import yaml
import json
import os
import sys
from datetime import datetime


def getPass(filename, service):
    username = None
    password = None
    with open(filename) as f:
        passdata = yaml.safe_load(f)
        if service in passdata:
            username = passdata[service].get('username', None).strip()
            password = passdata[service].get('password', None).strip()
    if username == None or password == None:
        return None
    return ( username, password )


def log_info(message):
    print('INFO : {}'.format(message), file=sys.stdout)


def log_error(message):
    print('ERROR : {}'.format(message), file=sys.stderr)


def log_debug(message):
    if DEBUG:
        print('DEBUG : {}'.format(message), file=sys.stdout)


try:
    DEBUG = int(os.environ.get('DEBUG', '0'))
except ValueError:
    DEBUG = 0

URL = os.environ['SNOW_API_URL']
STATUS_URL = os.environ['SNOW_API_STATUS_URL']
PASSWORD_FILE = os.environ['SNOW_API_PASSWORD_FILE']
LABEL_SERVICE_ID = os.environ.get('ALERTMANAGER_LABEL_SNOW_ID', 'service_id')
LABEL_SERVICE_COMPONENT = os.environ.get('ALERTMANAGER_LABEL_SNOW_COMPONENT', 'snow_component')

HEADERS = {'Content-Type': 'application/json',
           'Accept': 'application/json'}


alertmanagerdata = json.loads(sys.argv[1])

try:
    service_id = alertmanagerdata['groupLabels'][LABEL_SERVICE_ID]
except KeyError as e:
    log_error('Could not retrieve the service identifier : {}'.format(e))
    sys.exit(1)

service_id = service_id.upper()
auth = getPass(PASSWORD_FILE, service_id)
if auth == None:
    log_error('No entry in password file for service "{}"'.format(service_id))
    sys.exit(1)

nb_alerts = len(alertmanagerdata['alerts'])
log_debug('Handling {} alerts for service_id {}'.format(nb_alerts, service_id))

# Does we have firing alerts
url = '{}/{}'.format(STATUS_URL, service_id)
response = requests.get(url, auth=auth, headers=HEADERS)
log_debug('Retrieved ServiceNow firing alerts : {} : {}'.format(response.status_code, response.content))
if response.status_code != 200:
    log_error('Could not get status when requesting url "{}"'.format(url))
    sys.exit(1)

response_data = json.loads(response.text)
# Counts the number of alerts
existing_alerts = len(response_data['results'])
existing_incidents = 0
existing_degradations = 0
for existing_alert in response_data['results']:
    if existing_alert['outageType'] == 'Panne':
        existing_incidents += 1
    else :
        existing_degradations += 1
log_debug('There is/are {} ({} incidents, {} degradations) registered alerts in ServiceNow'.format(existing_alerts, existing_incidents, existing_degradations))

priority = 1
state = 'Down'
show_component = False
component = ''
nb_firing = 0

# Build the components string and determines the priority.
# The components is only shown in the outage description if the snow_component label exist.
#
# Snow Priorities
# 1 for new alerts
# 2 for degradation
# 6 to change description
# 5 to release an alert
#
# The priority can be superseded by the one specified in the 'snow_priority" label. We must be able
# to set it differently in case of a degradation.
#
# The alert description has to be modified when we want to specifiy the component(s) in the outage
# alert must not be released when we have firing alerts for multi-components outage.
#
component = ' ('
snow_priority = 9
for alert in alertmanagerdata['alerts']:
    if 'status' in alert and alert['status'] == 'firing':
        nb_firing += 1
        if 'snow_component' in alert['labels']:
            show_component = True
            if component.find(alert['labels']['snow_component']) == -1:
                component = component + alert['labels']['snow_component'] + ', '
        if 'snow_priority' in alert['labels']:
            tmp = int(alert['labels']['snow_priority'])
            if tmp < snow_priority :
                # keep the highest priority (smaller value)
                snow_priority = tmp

if 'snow_component' in alert['labels']:
    component = component[:-2] + ')'

if not show_component:
    component = ''

log_debug('Alertmanager have triggered {} alerts and {} is/are firing, global status is {}'.format(nb_alerts, nb_firing, alertmanagerdata["status"]))

if nb_firing >= 1:
    priority = 1
    state = 'Down'
    if snow_priority == 2:  # degraded
        priority = snow_priority
        state = 'Degraded'
    priority_changes = (snow_priority == 2 and existing_incidents != 0) or (snow_priority == 1 and existing_degradations != 0)
    if show_component and existing_alerts != 0 and not priority_changes:
        priority = 6
else:
    priority = 5
    state = 'Up'

description = 'Automatic Service{} {} via Camptocamp Monitoring.'.format(component, state)

data = {'u_business_service' : service_id,
        'u_priority' : priority,
        'u_short_description' : description,
        'u_description' : description}
log_info('Sending alert to ServiceNow for "{}" with priority "{}/{}" and description "{}"'.format(service_id, priority, state, description))
response = requests.post(URL, auth=auth, headers=HEADERS, data=json.dumps(data).strip())
log_debug("Sending alert done : {} : {}".format(response.status_code, response.content))

log_info("ServiceNow returned {}".format(response.status_code))

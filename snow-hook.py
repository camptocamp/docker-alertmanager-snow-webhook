#!/usr/bin/python3
# -*- coding: utf-8 -*-
import requests
import yaml
import json
import os
import sys
import logging
import json_logging
from datetime import datetime


class CustomJSONLog(logging.Formatter):
    # Customize JSON logs for ELK compatibility

    def get_exc_fields(self, record):
        if record.exc_info:
            exc_info = self.format_exception(record.exc_info)
        else:
            exc_info = record.exc_text
        return {'python.exc_info': exc_info}

    @classmethod
    def format_exception(cls, exc_info):
        return ''.join(traceback.format_exception(*exc_info)) if exc_info else ''

    def format(self, record):
        json_log_object = {'@timestamp': datetime.utcnow().isoformat(),
                           'level': record.levelname,
                           'message': record.getMessage(),
                           'env': os.environ['ENV']
                           }
        if hasattr(record, 'props'):
            json_log_object['data'].update(record.props)

        if record.exc_info or record.exc_text:
            json_log_object['data'].update(self.get_exc_fields(record))

        return json.dumps(json_log_object)


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


# Setup logging
json_logging.ENABLE_JSON_LOGGING = True
json_logging.__init(custom_formatter=CustomJSONLog)
# json_logging.init_non_web()
logger = logging.getLogger('json-logger')
try:
    DEBUG = int(os.environ.get('DEBUG', '0'))
except ValueError:
    DEBUG = 0
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


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
    logger.error('Could not retrieve the service identifier : {}'.format(e))
    sys.exit(1)

auth = getPass(PASSWORD_FILE, service_id.upper())
if auth == None:
    logger.error(f'No entry in password file for service "{service_id}"')
    sys.exit(1)

nb_alerts = len(alertmanagerdata['alerts'])
logger.debug(f'Handling {nb_alerts} alerts for service_id {service_id}')

# Does we have firing alerts
url = '{}/{}'.format(STATUS_URL, service_id)
response = requests.get(url, auth=auth, headers=HEADERS)
logger.debug(f'Retrieved ServiceNow firing alerts : {response.status_code} : {response.content}')
if response.status_code != 200:
    logger.error(f'Could not get status when requesting url "{url}"')
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
logger.debug(f'There is/are {existing_alerts} ({existing_incidents} incidents, {existing_degradations} degradations) registered alerts in ServiceNow')

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

logger.debug(f'Alertmanager have triggered {nb_alerts} alerts and {nb_firing} is/are firing, global status is {alertmanagerdata["status"]}')

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
logger.info(f'Sending alert to ServiceNow for "{service_id}" with priority "{priority}/{state}" and description "{description}"')
response = requests.post(URL, auth=auth, headers=HEADERS, data=json.dumps(data).strip())
logger.debug("Sending alert done : {} : {}".format(response.status_code, response.content))

logger.info("ServiceNow returned {}".format(response.status_code))

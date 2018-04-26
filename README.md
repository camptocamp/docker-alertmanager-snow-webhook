# alertmanager-snow-webhook

This repository container am AlertManager Webhook implementation for ServiceNow Status change.

# configuration

To configure the link to update the services in ServiceNow, you need the follwing:

* a ServiceNow API endpoint in the `SNOW_API_URL` environment variable
* a yaml file with a hash of services to username/password for the SNow API in the following format:
```yaml
<ServiceNow business_service identifier>:
  username: <username>
  password: <password>
```
* the path to the yaml credentials file in environment variable `SNOW_API_PASSWORD_FILE`
* alertmanager configured to send alerts with a "project" groupLabel (the label name is configurable with environment variale `ALERTMANAGER_LABEL_SNOW_ID`) and the ServiceNow `business_service` as value

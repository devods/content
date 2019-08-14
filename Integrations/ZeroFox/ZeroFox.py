import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

''' IMPORTS '''

import requests
from typing import Dict, List, Any, cast
# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' GLOBALS/PARAMS '''

USERNAME = None
PASSWORD = None
# Should we use SSL
USE_SSL = None
# Service base URL
BASE_URL = None
# default fetch time
FETCH_TIME_DEFAULT = '3 days'
FETCH_TIME = None

''' HELPER FUNCTIONS '''


# transforms severity number to string representation
def severity_num_to_string(severity_num):
    if severity_num == 1:
        return 'Info'
    elif severity_num == 2:
        return 'Low'
    elif severity_num == 3:
        return 'Medium'
    elif severity_num == 4:
        return 'High'
    elif severity_num == 5:
        return 'Critical'


# transforms an alert to incident convention
def alert_to_incident(alert):
    incident = {
        'rawJSON': json.dumps(alert),
        'name': 'ZeroFox Alert ' + str(alert.get('id')),  # not sure if it's the right name
        'occurred': alert.get('timestamp')  # not sure if it's the right field
    }
    return incident


# return updated contents of an alert
def get_updated_contents(alert_id):
    response_content = get_alert(alert_id)
    if not response_content or not isinstance(response_content, Dict):
        return {}
    alert = response_content.get('alert')
    if not alert or not isinstance(alert, Dict):
        return {}
    contents = get_alert_contents(alert)
    return contents


# removes all none values from a dict
def remove_none_dict(input_dict):
    return {key: value for key, value in input_dict.items() if value is not None}


# initialize all preset values
def initialize_preset():
    global USERNAME, PASSWORD, USE_SSL, BASE_URL
    USERNAME = demisto.params().get('credentials').get('identifier')
    PASSWORD = demisto.params().get('credentials').get('password')
    USE_SSL = not demisto.params().get('insecure', False)
    BASE_URL = demisto.params()['url'][:-1] if demisto.params()['url'].endswith('/') else demisto.params()['url']
    global FETCH_TIME
    FETCH_TIME = demisto.params().get('fetch_time', FETCH_TIME_DEFAULT)
    # Remove proxy if not set to true in params
    handle_proxy()


def get_alert_contents(alert):
    contents = {
        'AlertType': alert.get('alert_type'),
        'OffendingContentURL': alert.get('offending_content_url'),
        'AssetTermID': alert.get('asset_term').get('id') if alert.get('asset_term') else None,
        'AssetTermName': alert.get('asset_term').get('name') if alert.get('asset_term') else None,
        'AssetTermDeleted': alert.get('asset_term').get('deleted') if alert.get('asset_term') else None,
        'Assignee': alert.get('assignee'),
        'EntityID': alert.get('entity').get('id') if alert.get('entity') else None,
        'EntityName': alert.get('entity').get('name') if alert.get('entity') else None,
        'EntityImage': alert.get('entity').get('image') if alert.get('entity') else None,
        'EntityTermID': alert.get('entity_term').get('id') if alert.get('entity_term') else None,
        'EntityTermName': alert.get('entity_term').get('name') if alert.get('entity_term') else None,
        'EntityTermDeleted': alert.get('entity_term').get('deleted') if alert.get('entity_term') else None,
        'ContentCreatedAt': alert.get('content_created_at'),
        'ID': alert.get('id'),
        'ProtectedAccount': alert.get('protected_account'),
        'RiskRating': severity_num_to_string(alert.get('severity')),
        'PerpetratorName': alert.get('perpetrator').get('name') if alert.get('perpetrator') else None,
        'PerpetratorURL': alert.get('perpetrator').get('url') if alert.get('perpetrator') else None,
        'PerpetratorTimeStamp': alert.get('perpetrator').get('timestamp') if alert.get('perpetrator') else None,
        'PerpetratorType': alert.get('perpetrator').get('type') if alert.get('perpetrator') else None,
        'PerpetratorID': alert.get('perpetrator').get('id') if alert.get('perpetrator') else None,
        'PerpetratorNetwork': alert.get('perpetrator').get('network') if alert.get('perpetrator') else None,
        'RuleGroupID': alert.get('rule_group_id'),
        'AssetID': alert.get('asset').get('id') if alert.get('asset') else None,
        'AssetName': alert.get('asset').get('name') if alert.get('asset') else None,
        'AssetImage': alert.get('asset').get('image') if alert.get('asset') else None,
        'Status': alert.get('status'),
        'Timestamp': alert.get('timestamp'),
        'RuleName': alert.get('rule_name'),
        'LastModified': alert.get('last_modified'),
        'ProtectedLocations': alert.get('protected_locations'),
        'DarkwebTerm': alert.get('darkweb_term'),
        'Reviewed': alert.get('reviewed'),
        'Escalated': alert.get('escalated'),
        'Network': alert.get('network'),
        'ProtectedSocialObject': alert.get('protected_social_object'),
        'Notes': alert.get('notes'),
        'RuleID': alert.get('rule_id'),
        'EntityAccount': alert.get('entity_account'),
        'Tags': alert.get('tags')
    }
    return contents


# returns the convention for the war room
def get_alert_contents_war_room(contents):
    return {
        'ID': contents.get('ID'),
        'Protected Entity': contents.get('EntityName', '').title(),
        'Content Type': contents.get('AlertType', '').title(),
        'Alert Date': contents.get('Timestamp', ''),
        'Status': contents.get('Status', '').title(),
        'Source': contents.get('Network', '').title(),
        'Rule': contents.get('RuleName'),
        'Risk Rating': contents.get('RiskRating'),
        'Notes': contents.get('Notes') if contents.get('Notes') else None,
        'Tags': contents.get('Tags')
    }


def get_entity_contents(entity):
    return {
        'ID': entity.get('id'),
        'Name': entity.get('name'),
        'EmailAddress': entity.get('email_address'),
        'Organization': entity.get('organization'),
        'Labels': entity.get('labels'),
        'StrictNameMatching': entity.get('strict_name_matching'),
        'PolicyID': entity.get('policy_id'),
        'Profile': entity.get('profile'),
        'EntityGroupID': entity.get('entity_group').get('id') if entity.get('entity_group') else None,
        'EntityGroupName': entity.get('entity_group').get('name') if entity.get('entity_group') else None,
        'TypeID': entity.get('type').get('id') if entity.get('type') else None,
        'TypeName': entity.get('type').get('name') if entity.get('type') else None
    }


def get_entity_contents_war_room(contents):
    return {
        'Name': contents.get('Name'),
        'Type': contents.get('Type'),
        'Policy': contents.get('Policy'),
        'Email': contents.get('EmailAddress'),
        'Tags': contents.get('Labels'),
        'ID': contents.get('ID')
    }


def get_authorization_token():
    integration_context = demisto.getIntegrationContext()
    token = integration_context.get('token')
    if token:
        return token
    url_suffix: str = '/api-token-auth/'
    data_for_request: Dict = {
        'username': USERNAME,
        'password': PASSWORD
    }
    response_content = http_request('POST', url_suffix, data=data_for_request, continue_err=True, regular_request=False)
    if not response_content or not isinstance(response_content, Dict):
        raise Exception('Unexpected outputs from API call.')
    token = response_content.get('token')
    if not token:
        x = response_content.get('non_field_errors')
        if not x or not isinstance(x, List):
            raise Exception('Unexpected outputs from API call.')
        else:
            raise Exception(x[0])
    demisto.setIntegrationContext({'token': token})
    return token


def http_request(method: str, url_suffix: str, params=None, data=None, continue_err=False, regular_request=True):
    # A wrapper for requests lib to send our requests and handle requests and responses better
    try:
        token = get_authorization_token()
        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        res = requests.request(
            method,
            BASE_URL + url_suffix,
            verify=USE_SSL,
            params=params,
            data=data,
            headers=headers
        )
        # Handle error responses gracefully
        if res.status_code not in {200, 201} and not continue_err:
            err_msg: str = f'Error in ZeroFox Integration API call [{res.status_code}] - {res.reason}\n'
            try:
                res_json = res.json()
                if 'error' in res_json:
                    err_msg += res_json.get('error')
            except ValueError:
                err_msg += res.content
            finally:
                raise ValueError(err_msg)
        else:
            try:
                return res.json()
            except ValueError:
                return res.content
    except requests.exceptions.ConnectTimeout:
        err_msg = 'Connection Timeout Error - potential reasons may be that the Server URL parameter' \
                  ' is incorrect or that the Server is not accessible from your host.'
        raise Exception(err_msg)
    except requests.exceptions.SSLError:
        err_msg = 'SSL Certificate Verification Failed - try selecting \'Trust any certificate\' in' \
                  ' the integration configuration.'
        raise Exception(err_msg)
    except requests.exceptions.ProxyError:
        err_msg = 'Proxy Error - if \'Use system proxy\' in the integration configuration has been' \
                  ' selected, try deselecting it.'
        raise Exception(err_msg)
    except requests.exceptions.ConnectionError as e:
        # Get originating Exception in Exception chain
        while '__context__' in dir(e) and e.__context__:
            e = cast(Any, e.__context__)
        error_class = str(e.__class__)
        err_type = '<' + error_class[error_class.find('\'') + 1: error_class.rfind('\'')] + '>'
        err_msg = f'\nERRTYPE: {err_type}\nERRNO: [{e.errno}]\nMESSAGE: {e.strerror}\n' \
                  f'ADVICE: Check that the Server URL parameter is correct and that you' \
                  f' have access to the Server from your host.'
        return_error(err_msg)


''' COMMANDS + REQUESTS FUNCTIONS '''


def close_alert(alert_id):
    url_suffix: str = f'/alerts/{alert_id}/close/'
    response_content = http_request('POST', url_suffix)
    return response_content


def close_alert_command():
    alert_id: int = int(demisto.args().get('alert_id'))
    close_alert(alert_id)
    contents = get_updated_contents(alert_id)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': {'ID': alert_id, 'Status': 'Closed'}}
    return_outputs(
        f'Alert: {alert_id} has been closed successfully.',
        context,
        raw_response=contents
    )


def open_alert(alert_id):
    url_suffix: str = f'/alerts/{alert_id}/open/'
    response_content = http_request('POST', url_suffix)
    return response_content


def open_alert_command():
    alert_id: int = int(demisto.args().get('alert_id'))
    open_alert(alert_id)
    contents = get_updated_contents(alert_id)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': {'ID': alert_id, 'Status': 'Open'}}
    return_outputs(
        f'Alert: {alert_id} has been opened successfully.',
        context,
        raw_response=contents
    )


def alert_request_takedown(alert_id):
    url_suffix: str = f'/alerts/{alert_id}/request_takedown/'
    response_content = http_request('POST', url_suffix)
    return response_content


def alert_request_takedown_command():
    alert_id: int = int(demisto.args().get('alert_id'))
    alert_request_takedown(alert_id)
    contents = get_updated_contents(alert_id)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': {'ID': alert_id, 'Status': 'Takedown:Requested'}}
    return_outputs(
        f'Alert: {alert_id} has been requested to be taken down successfully.',
        context,
        raw_response=contents
    )


def alert_cancel_takedown(alert_id):
    url_suffix: str = f'/alerts/{alert_id}/cancel_takedown/'
    response_content = http_request('POST', url_suffix)
    return response_content


def alert_cancel_takedown_command():
    alert_id: int = int(demisto.args().get('alert_id'))
    alert_cancel_takedown(alert_id)
    contents = get_updated_contents(alert_id)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': {'ID': alert_id, 'Status': 'Open'}}
    return_outputs(
        f'Alert: {alert_id} has canceled takedown successfully.',
        context,
        raw_response=contents
    )


def alert_user_assignment(alert_id, username):
    url_suffix: str = f'/alerts/{alert_id}/assign/'
    request_body: Dict = {
        'subject': username
    }
    response_content = http_request('POST', url_suffix, data=json.dumps(request_body))
    return response_content


def alert_user_assignment_command():
    alert_id: int = int(demisto.args().get('alert_id'))
    username: str = demisto.args().get('username')
    alert_user_assignment(alert_id, username)
    contents = get_updated_contents(alert_id)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': {'ID': alert_id, 'Assignee': username}}
    return_outputs(
        f'{username} has been assigned to alert {alert_id} successfully.',
        context,
        raw_response=contents
    )


def modify_alert_tags(alert_id, action, tags_list_string):
    url_suffix: str = '/alerttagchangeset/'
    tags_list_name: str = 'added' if action else 'removed'
    tags_list: list = argToList(tags_list_string, separator=',')
    request_body: Dict = {
        'changes': [
            {
                f'{tags_list_name}': tags_list,
                'alert': alert_id
            }
        ]
    }
    response_content = http_request('POST', url_suffix, data=json.dumps(request_body))
    return response_content


def modify_alert_tags_command():
    alert_id = int(demisto.args().get('alert_id'))
    action_string = demisto.args().get('action')
    action = True if action_string == 'add' else False
    tags_list_string = demisto.args().get('tags')
    modify_alert_tags(alert_id, action, tags_list_string)
    contents = get_updated_contents(alert_id)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': contents}
    return_outputs(
        'Tags were modified successfully.',
        context,
        raw_response=contents
    )


def get_alert(alert_id):
    url_suffix: str = f'/alerts/{alert_id}/'
    response_content = http_request('GET', url_suffix, continue_err=True)
    return response_content


def get_alert_command():
    alert_id = demisto.args().get('alert_id')
    response_content = get_alert(alert_id)
    if not response_content or not isinstance(response_content, Dict):
        raise Exception('Unexpected outputs from API call.')
    alert = response_content.get('alert')
    if not alert or not isinstance(alert, Dict):
        raise Exception('No alert found.')
    contents = get_alert_contents(alert)
    contents_war_room = get_alert_contents_war_room(contents)
    context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': contents}
    return_outputs(
        tableToMarkdown(f'ZeroFox Alert {alert_id}', contents_war_room, removeNull=True),
        context,
        response_content
    )


def create_entity(name, strict_name_matching=None, image=None, labels=None, policy=None, organization=None):
    url_suffix: str = '/entities/'
    request_body = {
        'name': name,
        'strict_name_matching': strict_name_matching,
        'image': image,
        'labels': labels,
        'policy': policy,
        'organization': organization
    }
    request_body = remove_none_dict(request_body)
    response_content = http_request('POST', url_suffix, data=json.dumps(request_body))
    return response_content


def create_entity_command():
    name = demisto.args().get('name')
    strict_name_matching = demisto.args().get('strict_name_matching')
    image = demisto.args().get('image')
    labels = demisto.args().get('args')
    policy = demisto.args().get('policy')
    organization = demisto.args().get('organization')
    response_content = create_entity(name, strict_name_matching, image, labels, policy, organization)
    if not response_content or not isinstance(response_content, Dict):
        raise Exception('Unexpected outputs from API call.')
    entity_id = response_content.get('id')
    return_outputs(
        f'Entity has been created successfully. ID: {entity_id}',
        {'ZeroFox.Entity(val.ID && val.ID === obj.ID)': {'ID': entity_id}},
        response_content
    )


def list_alerts(params):  # not fully implemented
    url_suffix: str = '/alerts/'
    response_content = http_request('GET', url_suffix, params=params)
    return response_content


def list_alerts_command():  # not fully implemented
    params = remove_none_dict(demisto.args())
    response_content = list_alerts(params)
    if not response_content:
        return_outputs('No alerts found.', outputs={})
    elif isinstance(response_content, Dict):
        alerts = response_content.get('alerts')
        contents = [get_alert_contents(alert) for alert in alerts]
        contents_war_room = [get_alert_contents_war_room(content) for content in contents]
        context = {'ZeroFox.Alert(val.ID && val.ID === obj.ID)': contents}
        return_outputs(
            tableToMarkdown('ZeroFox Alerts', contents_war_room, removeNull=True),
            context,
            response_content
        )
    else:
        return_outputs('Unexpected outputs from API call.', outputs={})


def get_entities(params):
    url_suffix: str = '/entities/'
    response_content = http_request('GET', url_suffix, params=params)
    return response_content


def get_entities_command():
    params = remove_none_dict(demisto.args())
    response_content = get_entities(params)
    if not response_content:
        return_outputs('No entities found.', outputs={})
    elif isinstance(response_content, Dict):
        entities = response_content.get('entities')
        contents = [get_entity_contents(entity) for entity in entities]
        contents_war_room = [get_entity_contents_war_room(content) for content in contents]
        context = {'ZeroFox.Entity(val.ID && val.ID === obj.ID)': contents}
        return_outputs(
            tableToMarkdown('ZeroFox Entities', contents_war_room, removeNull=True),
            context,
            response_content
        )
    else:
        raise Exception('Unexpected outputs from API call.')


def fetch_incidents():
    last_run = demisto.getLastRun()
    if last_run and last_run.get('last_fetched_event_timestamp'):
        last_update_time = last_run['last_fetched_event_timestamp']
    else:
        last_update_time = parse_date_range(FETCH_TIME, date_format='%Y-%m-%dT%H:%M:%S')[0]
    incidents = []
    limit = demisto.params().get('fetch_limit')
    response_content = list_alerts({'sort_direction': 'asc', 'limit': limit, 'min_timestamp': last_update_time})
    alerts = response_content.get('alerts')
    # max_update_time is the timestamp of the last alert in alerts (because alerts is a sorted list)
    max_update_time = str(alerts[len(alerts)-1].get('timestamp')).split('+')[0]
    if not alerts:
        return
    for alert in alerts:
        incident = alert_to_incident(alert)
        incidents.append(incident)
    demisto.setLastRun({'last_fetched_event_timestamp': max_update_time})  # check whether max_update_time is a string?
    demisto.incidents(incidents)


def test_module():
    """
    Performs basic get request to get item samples
    """
    get_authorization_token()


''' COMMANDS MANAGER / SWITCH PANEL '''

''' EXECUTION '''


def main():
    LOG('Command being called is %s' % (demisto.command()))
    try:
        initialize_preset()
        if demisto.command() == 'test-module':
            test_module()
            demisto.results('ok')
        elif demisto.command() == 'zerofox-get-alert':
            get_alert_command()
        elif demisto.command() == 'zerofox-alert-user-assignment':
            alert_user_assignment_command()
        elif demisto.command() == 'zerofox-close-alert':
            close_alert_command()
        elif demisto.command() == 'zerofox-alert-request-takedown':
            alert_request_takedown_command()
        elif demisto.command() == 'zerofox-modify-alert-tags':
            modify_alert_tags_command()
        elif demisto.command() == 'zerofox-create-entity':
            create_entity_command()
        elif demisto.command() == 'zerofox-list-alerts':
            list_alerts_command()
        elif demisto.command() == 'zerofox-open-alert':
            open_alert_command()
        elif demisto.command() == 'zerofox-alert-cancel-takedown':
            alert_cancel_takedown_command()
        elif demisto.command() == 'zerofox-get-entities':
            get_entities_command()
        elif demisto.command() == 'fetch-incidents':
            fetch_incidents()

    # Log exceptions
    except Exception as e:
        error_msg = str(e)
        if demisto.command() == 'fetch-incidents':
            LOG(error_msg)
            LOG.print_log()
            raise
        else:
            return_error(error_msg)


if __name__ == 'builtins':
    main()
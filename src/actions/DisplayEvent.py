from bottle import Bottle, route, run, template, static_file, get, jinja2_template as template, post, request, response, redirect

import json
import requests
import runtime
import actions
import os
"""
DisplayEvent
"""

defaultInputParams = {}
defaultOutputParams = {}
sim_parameters = dict()

SAC_APP_SECRET = os.getenv('CRAFT_DEMO_SAC_APP_SECRET', '')
SAC_APP_ID     = os.getenv('CRAFT_DEMO_SAC_APP_ID', '')

HEADER_WITH_SECRETS = {'X-Craft-Ai-App-Id': SAC_APP_ID, 'X-Craft-Ai-App-Secret': SAC_APP_SECRET, 'Content-type': 'application/json', 'Accept': 'text/plain'}

# Register actions
def registerAction(user, project, version, sim_id):
	sim_parameters['user'] = user
	sim_parameters['project'] = project
	sim_parameters['version'] = version
	sim_parameters['sim_id'] = sim_id
	runtime.register_webActions(user, project, version, sim_id, 'DisplayEvent', '/home/actions/DisplayEvent/')

def start():
	inputParams = request.json['input']
	request_Id = request.json['requestId']
	runtime.eventQueue.put(json.dumps(inputParams['event']))
	success_url = '{}/v1/{}/{}/{}/{}/actions/{}/success'.format(runtime.CRAFT_RUNTIME_SERVER_URL, sim_parameters['user'],sim_parameters['project'],sim_parameters['version'],sim_parameters['sim_id'], request_Id)
	r = requests.post(success_url, headers=HEADER_WITH_SECRETS)
	return 

def cancel():
	request_Id = request.json['requestId']
	cancel_url = '{}/v1/{}/{}/{}/{}/actions/{}/cancelation'.format(runtime.CRAFT_RUNTIME_SERVER_URL, sim_parameters['user'],sim_parameters['project'],sim_parameters['version'],sim_parameters['sim_id'], request_Id)
	r = requests.post(cancel_url, headers=HEADER_WITH_SECRETS)
	return 

# -*- coding: utf8 -*-

import json
import requests
import os
import socket
import Queue

mainAgentId = -1
eventQueue = Queue.Queue()

status = {'created': 0, 'failed': 1, 'running': 2, 'succeeded': 3, 'canceled': 4, 'canceling': 5, 'destroyed': 6}

URL = os.getenv('CRAFT_DEMO_SAC_URL', '')
CRAFT_RUNTIME_SERVER_URL = os.getenv('CRAFT_RUNTIME_SERVER_URL', '')
CRAFT_RUNTIME_SERVER_API_BASE_ROUTE = os.getenv('CRAFT_RUNTIME_SERVER_API_BASE_ROUTE', '/v1')
HOSTIP = [(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
CRAFT_DEMO_SAC_ACTIONS_URL = os.getenv('CRAFT_DEMO_SAC_ACTIONS_URL', 'http://' + HOSTIP + ':' + os.getenv('CRAFT_DEMO_SAC_PORT', '8082'))
SAC_APP_SECRET = os.getenv('CRAFT_DEMO_SAC_APP_SECRET', '')
SAC_APP_ID     = os.getenv('CRAFT_DEMO_SAC_APP_ID', '')

HEADER_WITH_SECRETS = {'X-Craft-Ai-App-Id': SAC_APP_ID, 'X-Craft-Ai-App-Secret': SAC_APP_SECRET, 'Content-type': 'application/json', 'Accept': 'text/plain'}

def create_instance(user, project, version):
	print 'Creating instance...'
	r = requests.put(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version, headers = HEADER_WITH_SECRETS)
	return r.json()['instance']['instance_id']

def delete_instance(user, project, version, instance_id):
	print 'Deleting instance...'
	r = requests.delete(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id, headers = HEADER_WITH_SECRETS)
	print r.json()['message']

def update_instance(user, project, version, instance_id, time_t):
	r = requests.post(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id  + '/update', data='{"time":'+ str(time_t)+'}', headers = HEADER_WITH_SECRETS)
	return json.loads(r.text)['message']

def create_agent(user, project, version, instance_id, behavior, knowledgeJson = None ):
	url = CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id + '/agents'
	
	if not knowledgeJson :
		knowledgeJson = json.loads('{}')

	json_data = '{"behavior": "' + behavior +'", "knowledge":' + json.dumps(knowledgeJson) + '}'

	r = requests.put(url, data=json_data, headers = HEADER_WITH_SECRETS)

	agent_id = r.json()['agent']['id']
	print 'Agent id', agent_id

	return agent_id

def delete_agent(user, project, version, instance_id, id):
	r = requests.delete(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id +'/agents/' + str(id), headers = HEADER_WITH_SECRETS)

def getAgentKnowledge(user, project, version, instance_id, id):
	r = requests.get(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id + '/agents/'+ str(id) + '/knowledge', headers = HEADER_WITH_SECRETS)
	return r.json()['knowledge']

def putAgentKnowledge(user, project, version, instance_id, id, val, method = ''):
	r = requests.post(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id + '/agents/'+ str(id) + '/knowledge', data=json.dumps(val), headers = HEADER_WITH_SECRETS, params =  {'method': method})

def register_webActions(user, project, version, instance_id, actionName, requestName):
	print 'Registering web actions', actionName

	req = json.dumps({
		'name': actionName,
		'url': CRAFT_DEMO_SAC_ACTIONS_URL + requestName
	})
	r = requests.put(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id + '/actions', data=req, headers = HEADER_WITH_SECRETS)

def getInstanceKnowledge(user, project, version, instance_id):
	r = requests.get(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id +'/globalKnowledge', headers = HEADER_WITH_SECRETS)
	return r.json()['knowledge']

def setInstanceKnowledge(user, project, version, instance_id, val, method = ''):
	r = requests.post(CRAFT_RUNTIME_SERVER_URL + CRAFT_RUNTIME_SERVER_API_BASE_ROUTE + '/' + user + '/' + project + '/' + version + '/' + instance_id +'/globalKnowledge', data=json.dumps(val), headers = HEADER_WITH_SECRETS, params =  {'method': method})

# Websocket server between client and server
import threading
import gevent
from gevent.queue import Queue
from gevent.pywsgi import WSGIServer
import geventwebsocket
from geventwebsocket import WebSocketError
import requests
from gevent import monkey
from datetime import datetime
from dateutil import tz, parser, relativedelta
monkey.patch_all()

import bottle
from bottle import Bottle, route, run, template, static_file, get, jinja2_template as template, post, request, response, redirect

import runtime
import os
import sys
import glob
import imp
import json
import time
import stateVar

import httplib2
from apiclient.discovery import build

app = Bottle()

URL    = os.getenv('CRAFT_DEMO_SAC_URL', '')
WS_URL = os.getenv('CRAFT_DEMO_SAC_WS_URL', '')

GOOGLE_CLIENT_ID     = os.getenv('CRAFT_DEMO_SAC_GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('CRAFT_DEMO_SAC_GOOGLE_CLIENT_SECRET', '')

CRAFT_DEMO_SAC_USER    = os.getenv('CRAFT_DEMO_SAC_USER', '')
CRAFT_DEMO_SAC_PROJECT = os.getenv('CRAFT_DEMO_SAC_PROJECT', '')
CRAFT_DEMO_SAC_VERSION = os.getenv('CRAFT_DEMO_SAC_VERSION','')

SAC_APP_ID     = os.getenv('CRAFT_DEMO_SAC_APP_ID', '')
SAC_APP_SECRET = os.getenv('CRAFT_DEMO_SAC_APP_SECRET', '')

CRAFT_HUB_URL  = os.getenv('CRAFT_HUB_URL', '')

instance_step = 0.1
instance_id = -1
localTz = 'UTC'

working_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

### Google
auth_uri = CRAFT_HUB_URL + '/api/v1/auth/google?x-craft-ai-app-id=' + SAC_APP_ID + '&x-craft-ai-app-secret=' + SAC_APP_SECRET + '&success_uri=' + URL + '/run&failure_uri=' + URL + '?failure=true'

@app.route('/', method=['GET', 'POST'])
def google_authentification():
	result = request.json
	if result != None and 'type' in result and 'value' in result:
		global localTz
		param = request.json['type']
		val = request.json['value']
		if param == "tz":
			localTz = val
	
	return template(os.path.join(working_dir, 'html/index.html'), auth_uri = auth_uri)

### To load css, photo files. They have to be put in the static directory
@app.route('/static/<filename:path>')
def get_static_file(filename):
	return static_file(filename, root = os.path.join(working_dir, 'static/'))

@app.route('/alert')
def handle_websocket():
	ws = request.environ.get('wsgi.websocket')
	if not ws:
		bottle.abort(400, 'Expected WebSocket request.')

	try:
		while not ws.closed:
			try:
				event = runtime.eventQueue.get(True, 55)
				ws.send(event)
				if ws.receive() == None:
					runtime.eventQueue.put(event)
					ws.close()
			except Exception, ex:
				if ex.__class__.__name__ == 'Empty':
					ws.send('ping')
					ws.receive()
				else:
					print '%s: %s' % (ex.__class__.__name__, ex)
	except WebSocketError, ex:
		print '%s: %s' % (ex.__class__.__name__, ex)
		ws.close();

@app.route('/stop', method=['GET', 'POST'])
def stop_instance():
	with runtime.eventQueue.mutex:
		runtime.eventQueue.queue.clear()
	if not(stateVar.t_instance is None):
	    stateVar.t_instance.event.set()
	    stateVar.t_instance.join()
	    stateVar.t_instance = None
	return template(os.path.join(working_dir, 'html/index.html'), auth_uri = auth_uri, instance = stateVar.t_instance)

@app.route('/run', method=['GET', 'POST'])
def run_instance():
	if stateVar.t_instance is None:
		stateVar.currentTime = time.time()
		# Create life instance    
		global instance_id
		instance_id = runtime.create_instance(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION)

		# Init instance knowledge
		runtime.setInstanceKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, {'tz':localTz})
		runtime.setInstanceKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, {'time':stateVar.currentTime}, 'merge')

		# Register webActions
		get_and_register_webActions()

		# Start update instance in a thread
		stateVar.t_instance = UpdateLifeThreadClass()
		stateVar.t_instance.start()
		
		# Create life agent
		with open(os.path.join(working_dir, '../knowledge/ContextualAlerts.json')) as data_file:
			data = json.load(data_file)
		data['google_userId'] = request.query['user']

		stateVar.agentId = runtime.create_agent(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id,'src/decision/ContextualAlerts.bt', data)
	return update_data()

def update_data():
	result = request.json
	if result != None and 'type' in result and 'value' in result:
		param = request.json['type']
		val = request.json['value']
		if param == "snooze":
			if val == "You have to wake up, you have a metting.":
				runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'alert':{'snooze':{'0':True, '1':False}}}, 'merge')
			elif val == "It's time to go.":
				runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'alert':{'snooze':{'0':False, '1':True}}}, 'merge')
		elif param == "time":
			stateVar.currentTime = stateVar.currentTime + int(val)*60
		elif param == "transpMode":
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'transportationMode':val}, 'merge')
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'directions':{'found':False}}, 'merge')
		elif param == "location":
			location = str(val["latitude"]) + "," + str(val["longitude"])
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'origin':location}, 'merge')
		elif param == "origin":
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'origin':val}, 'merge')
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'directions':{'found':False}}, 'merge')
		elif param == "presence":
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'left': not val}, 'merge')
		elif param == "awake":
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'awake': not val}, 'merge')
		elif param == "workLocation":
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'workLocation':val}, 'merge')
			runtime.putAgentKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, stateVar.agentId, {'directions':{'found':False}}, 'merge')
		elif param == "speed":
			stateVar.speedFactor = int(val)
	return template(os.path.join(working_dir, 'html/index.html'),
		auth_uri = auth_uri,
		instance = stateVar.t_instance,
		url = URL,
		wsUrl = WS_URL)

def register_routes_webActions(app, actionName, startCallback, cancelCallback):
	actionRoute = '/home/actions/' + actionName
	app.route(actionRoute + '/start', ['POST'], startCallback)
	app.route(actionRoute + '/cancel', ['POST'], cancelCallback)

def get_and_register_webActions():
	actionsdir = os.path.abspath(__file__ + "/../../actions/")
	print 'Registering web actions located at ' + actionsdir
	for file in glob.glob(actionsdir + '/*.py'):
		name = os.path.splitext(os.path.basename(file))[0]
		module = imp.load_source(name, actionsdir +'/' + name + '.py')
		module.registerAction(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id)
		register_routes_webActions(app, name, module.start, module.cancel)
		print '- Registering web actions: ' + name

### LIFE update in a thread
class UpdateLifeThreadClass(gevent.Greenlet):
	def __init__(self):
		gevent.Greenlet.__init__(self)
		self.event = gevent.event.Event()
	def _run(self):
		previousTickTime = stateVar.currentTime
		while not self.event.isSet():
			try:
				success = runtime.update_instance(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, instance_step)
			except OSError, e:
				print e
				runtime.delete_instance(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id)

			gevent.sleep(instance_step)
			currentTickTime = time.time()
			stateVar.currentTime = stateVar.currentTime+stateVar.speedFactor*(currentTickTime-previousTickTime)
			previousTickTime = currentTickTime
			runtime.setInstanceKnowledge(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id, {'time':stateVar.currentTime}, 'merge')

		runtime.delete_instance(CRAFT_DEMO_SAC_USER, CRAFT_DEMO_SAC_PROJECT, CRAFT_DEMO_SAC_VERSION, instance_id)

	def __str__(self):
		return 'UpdateLifeThreadClass'

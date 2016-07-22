from flask import Flask, request, Blueprint
import json, subprocess, sys
app = Flask(__name__)

blueprint = Blueprint('out', __name__, static_url_path='/out', static_folder='out')
app.register_blueprint(blueprint)

new_states={}

@app.route('/get_updated_states/<client_id>')
def get_updated_states(client_id):
	if client_id not in new_states:
		new_states[client_id]=[]
	v= json.dumps(new_states[client_id])
	new_states[client_id]=[]
	return v

@app.route('/notify_updated_state/<state>')
def set_state_updated(state):
	if request.remote_addr=="127.0.0.1":
		for item in new_states.values():
			item.append(state)
		return "OK"
	else:
		return "Invalid URL"

if len(sys.argv)>1 and sys.argv[1]=="mt":
	for i in range(4):
		subprocess.Popen(["python3","constant_refresh.py", str(i)], stdout=open("log/constant_refresh_%d.log" % i, 'w'), stderr=open("log/constant_refresh_%d_err.log" % i, 'w'))
else:
	subprocess.Popen(["python3","constant_refresh.py", "-1"], stdout=open("log/constant_refresh.log", 'w'), stderr=open("log/constant_refresh_err.log", 'w'))
app.run('0.0.0.0',port=80)

from flask import Flask, request
import os, subprocess
app = Flask(__name__)

WORKER_DISTRIBUTION=[13,13,12,12]
worker_status=[0 for x in WORKER_DISTRIBUTION]
states_for_workers=[]

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/update_worker_progress/<worker_id>/<processed>')
def update_progress(worker_id, processed):
	worker_id=int(worker_id)
	processed=int(processed)
	worker_status[worker_id]=processed
	os.system("clear")
	print("Rendering state wordclouds with %d workers" % len(worker_status))
	i=0
	for item in worker_status:
		print(("Worker %d : [" % i)+"#"*item+" "*(WORKER_DISTRIBUTION[i]-item)+"] %d/%d -> %s" % (item, WORKER_DISTRIBUTION[i], (states_for_workers[i][item] if item<len(states_for_workers[i]) else "Done")))
		i+=1
	i=0
	for item in worker_status:
		if item!=WORKER_DISTRIBUTION[i]:
			break
		i+=1
		if i==len(worker_status):
			shutdown_server()
	return "OK"




STATES=[x.replace(".png","") for x in os.listdir("masks")]

i=0
state=0
for item in WORKER_DISTRIBUTION:
	cmd=["python3", "render_mt.py", str(i)]
	states_for_worker=STATES[state:state+WORKER_DISTRIBUTION[i]]
	states_for_workers.append(states_for_worker)
	cmd.extend(states_for_worker)
	print(cmd)
	subprocess.Popen(cmd, stdout=open("log/render_mt_%d.log"%i, 'w'), stderr=open("log/render_mt_err_%d.log"%i, 'w'))
	state+=WORKER_DISTRIBUTION[i]
	i+=1

update_progress(0,0)

app.run()
print("Integrating...")
os.system("python3 integrate.py")
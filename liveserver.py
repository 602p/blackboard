import flask
import argparse
import multiprocessing
import blackboard
import shutil

parser = argparse.ArgumentParser()

parser.add_argument('--address', default="127.0.0.1:5000")
parser.add_argument('--workers', default=4)
parser.add_argument('--states', default=4)
parser.add_argument('datasource', nargs="+")
parser.add_argument('--no-state-name', action='store_true')
parser.add_argument('-q', action='store_true')
parser.add_argument('--stopwords', default='')

args = parser.parse_args()

if __name__=="__main__":
	app = flask.Flask(__name__)
	app.register_blueprint(flask.Blueprint('server_viz', __name__, static_url_path='/sv', static_folder='server_viz'))
	addr=args.address
	if ":" not in addr:
		addr+=":5000"
	addr=addr.split(":")
	multiprocessing.Process(target=app.run, args=(addr[0], int(addr[1]))).start()
	statebuffer=[]
	statebuffer.extend(blackboard.STATES)
	stopwords=blackboard.process_stopwords(args.stopwords)
	while 1:
		i=0
		iterstates=[]
		while i<int(args.states):
			iterstates.append(statebuffer.pop())
			if len(statebuffer)==0:
				statebuffer.extend(blackboard.STATES)
			i+=1
		blackboard.CacheBuilder(iterstates, int(args.workers), args.datasource, True, args.no_state_name, stopwords, args.q).run()
		blackboard.MapBuilder(iterstates, 'dummy', False, "integrated.png", args.q).run()
		shutil.copy("integrated.png", "server_viz/integrated.png")
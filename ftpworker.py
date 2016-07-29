import ftplib
import argparse
import blackboard
import threading
import time

def _keep_alive(connection):
	while True:
		log("Sending keep-alive...")
		log("PWD reponse=%s"%connection.pwd())
		time.sleep(20)

parser = argparse.ArgumentParser()

parser.add_argument('--address', required=True)
parser.add_argument('--auth', required=True)
parser.add_argument('--workers', default=4)
parser.add_argument('--states', default=4)
parser.add_argument('datasource', nargs="+")
parser.add_argument('--no-state-name', action='store_true')
parser.add_argument('-q', action='store_true')
parser.add_argument('--stopwords', default='')

args = parser.parse_args()

def log(obj):
	if not args.q: print(obj)

if __name__=="__main__":
	stopwords=blackboard.process_stopwords(args.stopwords)
	if args.auth.startswith("%"):
		with open(args.auth, 'r') as fd:
			args.auth=fd.read()
	user, password=args.auth.split(":")
	log("Connecting: addr=%s, user=%s, pass=%s"%(args.address, user, password))
	connection=ftplib.FTP(args.address, user, password)
	log("Connected. welcome=%s"%connection.getwelcome())
	log("Spinning up keep-alive thread")
	threading.Thread(target=_keep_alive, args=(connection,)).start()
	statebuffer=[]
	statebuffer.extend(blackboard.STATES)
	while 1:
		i=0
		iterstates=[]
		while i<int(args.states):
			iterstates.append(statebuffer.pop())
			if len(statebuffer)==0:
				statebuffer.extend(blackboard.STATES)
			i+=1
		blackboard.CacheBuilder(iterstates, int(args.workers), args.datasource, True, False, args.no_state_name, stopwords, args.q).run()
		blackboard.MapBuilder(iterstates, 'dummy', False, "integrated.png", args.q).run()
		with open("integrated.png", 'rb') as fd:
			log("Uploading integrated.png...")
			connection.storbinary("STOR integrated.png", fd)

		for fn in ["%s.json"%state for state in iterstates]:
			with open("statecache/"+fn, 'rb') as fd:
				log("Uploading %s"%fn)
				connection.storlines("STOR sc/%s"%fn, fd)
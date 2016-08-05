import argparse
import blackboard
import json
import importlib

BASECONFIG={
	"states":"ALL",
	"omit":"NONE",
	"stopwords":"",
	"dispatcher":"local:4",
	"q":False,
	"datasource":[],
	"convert":False,
	"no_state_name":False,
	"state_data":False,
	"sdl_driver":"dummy",
	"start_from":"",
	"refresh_display":False,
	"use_cache":False,
	"address":"127.0.0.1:5000",
	"states_per_cycle":4,
	"simple_monitor":False
}

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")

config_parser = subparsers.add_parser('config')
config_parser.add_argument('file', nargs=1)

buildcache_parser = subparsers.add_parser('buildcache')
buildcache_parser.add_argument('--states', default='ALL')
buildcache_parser.add_argument('--omit', default='NONE')
buildcache_parser.add_argument('--stopwords', default='')
buildcache_parser.add_argument('--dispatcher', default="local:4")
buildcache_parser.add_argument('-q', action='store_true')
buildcache_parser.add_argument('datasource', nargs="*")
buildcache_parser.add_argument('--convert', action='store_true')
buildcache_parser.add_argument('--simple-monitor', action='store_true')
buildcache_parser.add_argument('--no-state-name', action='store_true')
buildcache_parser.add_argument('--state-data', action='store_true')

buildmap_parser = subparsers.add_parser('buildmap', parents=[buildcache_parser], add_help=False)
buildmap_parser.add_argument('--sdl-driver', default='dummy')
buildmap_parser.add_argument('--start-from', default='')
buildmap_parser.add_argument('--refresh-display', action='store_true')
buildmap_parser.add_argument('--use-cache', action='store_true')

liveserver_parser = subparsers.add_parser('liveserver', parents=[buildmap_parser], add_help=False)
liveserver_parser.add_argument('--address', default="127.0.0.1:5000")
liveserver_parser.add_argument('--states-per-cycle', default=4)

if __name__ == '__main__':
	args = parser.parse_args()
	if args.command=="config":
		args.__dict__.update(BASECONFIG)
		if args.file[0].startswith("%"):
			with open(args.file[0], 'r') as fd:
				args.__dict__.update(json.load(fd))
		else:
			args.__dict__.update(json.loads(args.file[0]))
	assert args.command, "No command specified"
	if args.command in ["buildcache", "buildmap", "liveserver"]:
		if args.states=="ALL":
			states=blackboard.STATES
		else:
			states=args.states.split(",") if type(args.states)!=list else args.states
		for item in args.omit.split(","):
			try:
				states.remove(item)
			except ValueError:pass
		stopwords=blackboard.process_stopwords(args.stopwords)

	if args.command in ["buildcache", "buildmap", "liveserver"]:
		if args.dispatcher.startswith("local"):
			dispatcher=blackboard.LocalWorkerDispatcher(int(args.dispatcher.split(":")[1]), args.q)
		if args.dispatcher.startswith("simparallel"):
			dispatcher=blackboard.SimparallelDispatcher(importlib.import_module(args.dispatcher.split(":")[1]).task, args.q)


	if args.command=="buildcache":
		blackboard.CacheBuilder(states, dispatcher, args.simple_monitor, args.datasource, args.state_data, not args.convert, args.no_state_name, stopwords, args.q).run()
	if args.command=="buildmap":
		if not args.use_cache:
			assert args.datasource, "No datasource provided, but --use-cache was not specified"
			blackboard.CacheBuilder(states, dispatcher, args.simple_monitor, args.datasource, args.state_data, not args.convert, args.no_state_name, stopwords, args.q).run()
		blackboard.MapBuilder(states, args.sdl_driver, args.refresh_display, args.start_from, args.simple_monitor, args.q).run()
	if args.command=="liveserver":
		import liveserver
		liveserver.run_liveserver(args, dispatcher)
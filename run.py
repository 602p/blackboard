import argparse
import blackboard

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")

test_parser = subparsers.add_parser('test')

buildcache_parser = subparsers.add_parser('buildcache')
buildcache_parser.add_argument('--states', default='ALL')
buildcache_parser.add_argument('--omit', default='NONE')
buildcache_parser.add_argument('--stopwords', default='')
buildcache_parser.add_argument('--workers', default=4, type=int)
buildcache_parser.add_argument('-q', action='store_true')
buildcache_parser.add_argument('datasource', nargs="+")
buildcache_parser.add_argument('--no-convert', action='store_true')
buildcache_parser.add_argument('--no-state-name', action='store_true')

buildmap_parser = subparsers.add_parser('buildmap')
buildmap_parser.add_argument('--states', default='ALL')
buildmap_parser.add_argument('--omit', default='NONE')
buildmap_parser.add_argument('--stopwords', default='')
buildmap_parser.add_argument('--workers', default=4, type=int)
buildmap_parser.add_argument('--sdl-driver', default='dummy')
buildmap_parser.add_argument('--start-from', default='')
buildmap_parser.add_argument('-q', action='store_true')
buildmap_parser.add_argument('--refresh-display', action='store_true')
buildmap_parser.add_argument('--convert', action='store_true')
buildmap_parser.add_argument('--use-cache', action='store_true')
buildmap_parser.add_argument('datasource', nargs="*")
buildmap_parser.add_argument('--no-state-name', action='store_true')

if __name__ == '__main__':
	args = parser.parse_args()
	assert args.command, "No command specified"
	if args.command in ["buildcache", "buildmap"]:
		if args.states=="ALL":
			states=blackboard.STATES
		else:
			states=args.states.split(",")
		for item in args.omit.split(","):
			try:
				states.remove(item)
			except ValueError:pass
		stopwords=blackboard.process_stopwords(args.stopwords)
	if args.command=="buildcache":
		blackboard.CacheBuilder(states, args.workers, args.datasource, args.no_convert, args.no_state_name, stopwords, args.q).run()
	if args.command=="buildmap":
		if not args.use_cache:
			assert args.datasource, "No datasource provided, but --use-cache was not specified"
			blackboard.CacheBuilder(states, args.workers, args.datasource, not args.convert, args.no_state_name, stopwords, args.q).run()
		blackboard.MapBuilder(states, args.sdl_driver, args.refresh_display, args.start_from, args.q).run()
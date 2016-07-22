import argparse
import blackboard

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")

test_parser = subparsers.add_parser('test')

buildcache_parser = subparsers.add_parser('buildcache')
buildcache_parser.add_argument('--states', default='ALL')
buildcache_parser.add_argument('--omit', default='NONE')
buildcache_parser.add_argument('--workers', default=4, type=int)
buildcache_parser.add_argument('-q', action='store_true')
buildcache_parser.add_argument('datasource', nargs="+")

buildmap_parser = subparsers.add_parser('buildmap')
buildmap_parser.add_argument('--states', default='ALL')
buildmap_parser.add_argument('--omit', default='NONE')
buildmap_parser.add_argument('--workers', default=4, type=int)
buildmap_parser.add_argument('--sdl-backend', default='dummy')
buildmap_parser.add_argument('-q', action='store_true')
buildmap_parser.add_argument('--use-cache', action='store_true')

liveserver_parser = subparsers.add_parser('liveserver')
liveserver_parser.add_argument('address', nargs='?', default="127.0.0.1:5000")
liveserver_parser.add_argument('--workers', default=4, type=int)
liveserver_parser.add_argument('datasource', nargs="+")

STATES=['nevada', 'rhodeisland', 'southdakota', 'illinois', 'newmexico',\
	'oregon', 'kentucky', 'maine', 'delaware', 'idaho', 'pennsylvania', \
	'arizona', 'nebraska', 'newjersey', 'indiana', 'washington', 'alabama',\
	'montana', 'hawaii', 'westvirginia', 'northdakota', 'northcarolina',\
	'louisiana', 'alaska', 'colorado', 'texas', 'newhampshire', 'utah',\
	'michigan', 'georgia', 'florida', 'tennessee', 'wisconsin', 'kansas',\
	'virginia', 'iowa', 'connecticut', 'newyork', 'minnesota', 'vermont',\
	'ohio', 'maryland', 'arkansas', 'southcarolina', 'massachusetts',\
	'missouri', 'wyoming', 'california', 'mississippi', 'oklahoma']

if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    assert args.command, "No command specified"
    if args.command=="buildcache":
    	blackboard.BuildCacheManager(STATES, args.workers, args.datasource, args.q).run()
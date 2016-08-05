import simparallel, json, collections, operator

with open("server_keys.json", 'r') as fd:
	data=json.load(fd)
	authdata=collections.OrderedDict()
	for k,v in sorted(data.items(), key=operator.itemgetter(0)):
		authdata[k]=v

task=simparallel.Task(
	"blackboard",
	servers=authdata,
	files=[
		"*",
		"masks/*",
		"out/.exists",
		"statecache/.exists",
		"log/.exists",
		"datasources/*",
		"stoplists/*"
	],
	command="python3 run.py config '{config}'",
	use_workers=max,
	delete="statecache/*",
	returns="statecache/*",
	returnto="statecache"
)


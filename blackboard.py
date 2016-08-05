import sys
import importlib
import datetime
import atexit
import multiprocessing
import os
import time
import numpy
import PIL
import wordcloud
import warnings
import json
import operator
import tqdm
import json
sys.path.append("datasources")

STATES=['nevada', 'rhodeisland', 'southdakota', 'illinois', 'newmexico',\
	'oregon', 'kentucky', 'maine', 'delaware', 'idaho', 'pennsylvania', \
	'arizona', 'nebraska', 'newjersey', 'indiana', 'washington', 'alabama',\
	'montana', 'hawaii', 'westvirginia', 'northdakota', 'northcarolina',\
	'louisiana', 'alaska', 'colorado', 'texas', 'newhampshire', 'utah',\
	'michigan', 'georgia', 'florida', 'tennessee', 'wisconsin', 'kansas',\
	'virginia', 'iowa', 'connecticut', 'newyork', 'minnesota', 'vermont',\
	'ohio', 'maryland', 'arkansas', 'southcarolina', 'massachusetts',\
	'missouri', 'wyoming', 'california', 'mississippi', 'oklahoma']

statemask_cache={}

CACHE_PATH="statecache/%s.png"
MASKS_PATH="masks/%s.png"
FINAL_PATH="out/%s.png"
DATA_PATH="statecache/%s.json"

def load_datasource(name):
	return importlib.import_module(name)

def process_stopwords(argtext):
	stopwords=argtext.split(",")
	remove=[]
	for item in stopwords:
		if item.startswith("%"):
			with open(item.replace("%",""),'rU') as fd:
				stopwords.extend(fd.read().split("\n"))
			remove.append(item)
	for item in remove:
		stopwords.remove(item)
	return stopwords

class LoggingThingy:
	def open_log(self, name=None):
		if name is None: name="log/"+type(self).__name__+".log"
		self.fd=open(name, 'w')
		atexit.register(self.fd.close)

	def log(self, text):
		ftext=str(datetime.datetime.now())+":\t"+str(text)
		self.fd.write(ftext+"\n")
		if not self.quiet:
			print(ftext)

def _save_metadata(state, data, datasources):
	with open(DATA_PATH%state, 'w') as fd:
		jdata=[]
		for k,v in reversed(sorted(data, key=operator.itemgetter(1))):
			jdata.append([k,v])
		json.dump({"words":jdata, "datasources":[item.get_embed_data() for item in datasources]}, fd)

def _build_state_worker(worker_id, no_convert, state_data, no_state_name, stoplist, states, datasources, connection):
	with open("log/worker_%d.log" % worker_id, 'w') as fd:
		def log(txt):
			fd.write(txt+"\n")
		log("Worker %d started, pid=%d" % (worker_id, os.getpid()))
		log("worker_id=%d, state_data=%s, no_convert=%s, no_state_name=%s, stoplist=%s, states=%s, datasources=%s, connection=%s" % (worker_id, state_data, str(no_convert), str(no_state_name), str(stoplist), str(states), str(datasources), str(connection)))
		log("Instansiating Datasources")
		sys.path.append("datasources")
		datasources_i=[ds.blackboard_datasource() for ds in [load_datasource(mod) for mod in datasources]]
		[ds.setup() for ds in datasources_i]
		warnings.simplefilter("ignore", ResourceWarning)
		s=0
		for item in states:
			log("Processing state %s"%item)
			log("Getting text from datasources->%s"%str(datasources_i))
			text=" ".join([ds.get_words(item) for ds in datasources_i])
			log("Loading mask...")
			with PIL.Image.open(MASKS_PATH%item) as img:
				mask = numpy.array(img)
			log("Setting STOPWORDS")
			stopwords = set(wordcloud.STOPWORDS)
			stopwords.add("said")
			stopwords.add("http")
			stopwords.add("https")
			[stopwords.add(x.lower()) for x in stoplist]
			if no_state_name:
				stopwords.add(item)
				for msn in ["new","north","south"]:
					if item.startswith(msn):
						stopwords.add(msn)
						stopwords.add(item.replace(msn,"",1))
			log("Creating WordCloud...")
			wc = wordcloud.WordCloud(background_color=None, mode="RGBA", max_words=2000, mask=mask, stopwords=stopwords)
			log("Generating WordCloud...")
			frequencies=wc.process_text(text)
			if state_data:
				_save_metadata(item, frequencies, datasources_i)
			wc.generate_from_frequencies(frequencies)
			#log("Coloring WordCloud...")
			#wc.recolor(color_func=grey_color_func, random_state=3)
			log("Saving...")
			wc.to_file(CACHE_PATH%item)
			if not no_convert:
				log("Colorkeying State")
				os.system("convert %s -transparent white %s" % (CACHE_PATH%item, FINAL_PATH%item))
			s+=1
			connection.send(s)

class WorkerDispatcher(LoggingThingy):
	def __init__(self):
		self.open_log()
		self.workers=0

	def get_workers(self):
		return self.workers

	def start_workers(self):
		pass

	def get_worker_status(self):
		pass

class LocalWorkerDispatcher(WorkerDispatcher):
	def __init__(self, workers, quiet=False):
		self.workers=workers
		self.open_log()
		self.quiet=quiet
		self.worker_status=[0 for _ in range(self.workers)]

	def get_worker_names(self):
		return ["Worker #%02d"%x for x in range(self.workers)]

	def start_workers(self, worker_queues, no_convert, state_data, no_state_name, stoplist, datasources):
		self.log("Starting workers!")
		self.worker_pipes=[i for i in range(self.workers)]
		for p_id in range(self.workers):
			self.log("STarting wroker %d"%p_id)
			self.log("Creating pipe")
			self.worker_pipes[p_id], child_pipe=multiprocessing.Pipe()
			self.log("Creating Process")
			multiprocessing.Process(target=_build_state_worker, args=(p_id, no_convert, state_data, no_state_name, stoplist, worker_queues[p_id], datasources, child_pipe)).start()
			self.log("Created")
		self.log("Done!")

	def get_worker_states(self):
		for wid in range(self.workers):
			if self.worker_pipes[wid].poll():
				self.worker_status[wid]=self.worker_pipes[wid].recv()
		return self.worker_status

class SimparallelDispatcher(WorkerDispatcher):
	def __init__(self, task, quiet=False):
		self.open_log()
		self.task=task
		self.quiet=quiet
		self.cumstate_count=[]
		self.workers=task.get_sum_nproc()
		self.worker_status=[0 for _ in range(self.workers)]
		self.host_task_count=[]

	def start_workers(self, worker_queues, no_convert, state_data, no_state_name, stoplist, datasources):
		configs=[]
		current_sid=0
		for server, nproc in self.task.nproc_count.items():
			self.host_task_count.append(nproc)
			self.log("SERVER=%s, NPROC=%s =============="%(server,nproc))
			self.log("current_sid=%s"%current_sid)
			cumstates=[]
			for item in worker_queues[current_sid:current_sid+nproc]:
				cumstates.extend(item)
			self.cumstate_count.append(len(cumstates))
			self.log("cumstates=%s, len=%d" % (str(cumstates), len(cumstates)))
			cfg={
					"command":"buildcache",
					"no_convert":no_convert,
					"state_data":state_data,
					"no_state_name":no_state_name,
					"stoplist":stoplist,
					"datasource":datasources,
					"states":cumstates,
					"simple_monitor":True,
					"dispatcher":"local:%d"%nproc
				}
			configs.append({"config":json.dumps(cfg)})
			current_sid+=nproc
			self.log(cfg)
		self.task.start_workers(configs)

	def get_worker_names(self):
		names=[]
		for server, num in self.task.nproc_count.items():
			[names.append("Worker #%02d @ %s" % (n, server)) for n in range(num)]
		return names

	def get_worker_states(self):
		for hostnum, item in enumerate(self.task.read_channels()):
			for line in item:
				if "\t" in line:
					line=line.split("\t")[-1]
				if line.startswith("["):
					status=eval(line)
					i=sum(self.host_task_count[:hostnum])
					# print(hostnum, i, status)
					for c, val in enumerate(status):
						self.worker_status[i+c]=val
		# print(self.worker_status)
		return self.worker_status

class CacheBuilder(LoggingThingy):
	def __init__(self, states, dispatcher, simple_monitor, datasources, state_data, no_convert, no_state_name, stoplist, quiet=False):
		self.open_log()
		self.datasources=datasources
		self.states=states
		self.stoplist=stoplist
		self.state_data=state_data
		self.quiet=quiet
		self.no_state_name=no_state_name
		self.no_convert=no_convert
		self.simple_monitor=simple_monitor
		self.dispatcher=dispatcher
		self.workers=dispatcher.get_workers()
		self.distribute_states()

	def distribute_states(self):
		self.log("Distributing %d states to %d workers" % (len(self.states), self.workers))
		self.worker_queues=[[] for _ in range(self.workers)]
		n=0
		while n<=len(self.states):
			n+=self.workers
		n-=self.workers
		n/=self.workers
		n=int(n)
		self.log("Smallest even distribution is %d/worker -> %d" % (n, n*self.workers))
		self.worker_sizes=[n for _ in range(self.workers)]
		i=0
		while sum(self.worker_sizes)!=len(self.states):
			self.worker_sizes[i]+=1
			i+=1
		self.log("Allocation complete: %s -> Total=%d" % (str(self.worker_sizes), sum(self.worker_sizes)))
		assert sum(self.worker_sizes)==len(self.states), "Allocating states failed"
		s=0
		w=0
		for num in self.worker_sizes:
			c=0
			while c<num:
				self.worker_queues[w].append(self.states[s])
				c+=1
				s+=1
			w+=1
		self.log("Distribution complete: %s -> %d"%(str(self.worker_queues), sum([len(wq) for wq in self.worker_queues])))
		assert sum([len(wq) for wq in self.worker_queues])==len(self.states), "Distributing states failed"

	def run(self, track=True):
		self.log("Starting dispatcher............")
		self.dispatcher.start_workers(self.worker_queues, self.no_convert, self.state_data, self.no_state_name, self.stoplist, self.datasources)
		self.log("Started!")
		if track:
			pbars=[]

			if not self.quiet and not self.simple_monitor:
				names=self.dispatcher.get_worker_names()
				longest=max([len(name) for name in names])
				for i, worker in enumerate(names):
					pbars.append(tqdm.tqdm(desc=worker+" "*(longest-len(worker)), unit="state", position=i, total=len(self.worker_queues[i])))
				overall=tqdm.tqdm(desc="Overall"+" "*(longest-len("Overall")), unit="state", position=len(pbars), total=len(self.states))

			run=1
			while run:
				ws=self.dispatcher.get_worker_states()
				run= sum(ws)!=len(self.states)
				time.sleep(1)
				if not self.quiet:
					if not self.simple_monitor:
						total_diff=0
						for i, item in enumerate(ws):
							diff=item-pbars[i].n
							if diff:
								if diff<1:
									print("***WOAH***")
									print(diff, i, pbars[i].n, ws)
								else:
									pbars[i].update(diff)
							total_diff+=diff
						if total_diff: overall.update(total_diff)
					else:
						self.log(ws)
			if pbars:overall.close()
			[x.close() for x in pbars]

		else:
			return self.dispatcher

class MapBuilder(LoggingThingy):
	def __init__(self, states, sdl_driver, refresh, start_from, simple_monitor, quiet):
		self.states=states
		self.quiet=quiet
		self.refresh=refresh
		self.start_from=start_from
		self.open_log()
		self.simple_monitor=simple_monitor
		if sdl_driver!="default":
			self.log("Setting SDL_VIDEODRIVER=%s"%sdl_driver)
			os.environ["SDL_VIDEODRIVER"]=sdl_driver
		else:
			self.log("Leaving SDL_VIDEODRIVER")
		self.log("Loading pygame")
		import pygame
		self.log("Initilizing")
		pygame.init()
		self.log("Setting up display -> 1x1")
		pygame.display.set_mode((1,1))
		self.log("Loading map for state %s to find size"%states[0])
		size=pygame.image.load(CACHE_PATH%states[0]).get_size()
		self.log("Size -> %s"%str(size))
		self.log("Resizing display...")
		self.surf=pygame.display.set_mode(size)
		if self.start_from:
			self.log("Setting start_from")
			self.surf.blit(pygame.image.load(self.start_from), (0,0))

	def run(self):
		import pygame
		self.log("Rendering map")
		self.log("Rendering %d states -> %s from base path %s"%(len(self.states), str(self.states), FINAL_PATH))
		if not self.quiet:print(".")
		i=1
		for item in tqdm.tqdm(self.states, unit="state", disable=self.quiet or self.simple_monitor):
			if not self.quiet and self.simple_monitor:
				print(i)
			i+=1
			img=pygame.image.load(CACHE_PATH%item).convert()
			img.set_colorkey((0,0,0))
			if self.start_from:
				if item not in statemask_cache:
					img_mask=pygame.image.load(MASKS_PATH%item).convert()
					img_mask.set_colorkey((255,255,255))
					statemask_cache[item]=img_mask
				else:
					img_mask=statemask_cache[item]
				self.surf.blit(img_mask, (0,0))
			self.surf.blit(img, (0,0))
			if self.refresh:
				pygame.display.flip()
		if not self.quiet:print("Done!")
		self.log("Saving to integrated.png")
		pygame.display.flip()
		pygame.image.save(self.surf, "integrated.png")
		self.log("Shutting down pygame")
		pygame.quit()
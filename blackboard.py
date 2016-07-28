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
		ftext=str(datetime.datetime.now())+":\t"+text
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
		datasources_i=[ds.blackboard_datasource() for ds in datasources]
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

class CacheBuilder(LoggingThingy):
	def __init__(self, states, workers, datasources, state_data, no_convert, no_state_name, stoplist, quiet=False):
		self.open_log()
		self.datasources=[load_datasource(ds) for ds in datasources]
		self.states=states
		self.stoplist=stoplist
		self.state_data=state_data
		self.workers=workers
		self.quiet=quiet
		self.no_state_name=no_state_name
		self.no_convert=no_convert
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
		self.log("Starting %d processes............" % self.workers)
		time.sleep(0.5)
		worker_pipes=[i for i in range(self.workers)]
		for p_id in range(self.workers):
			worker_pipes[p_id], child_pipe=multiprocessing.Pipe()
			multiprocessing.Process(target=_build_state_worker, args=(p_id, self.no_convert, self.state_data, self.no_state_name, self.stoplist, self.worker_queues[p_id], self.datasources, child_pipe)).start()
		if track:
			worker_state=[0 for _ in range(self.workers)]
			self.log("Communicate loop starting")
			while sum(worker_state)!=len(self.states):
				if not self.quiet:
					os.system("clear")
					print("Rendering %d states using %d processes"%(len(self.states), self.workers))
				w=0
				for conn in worker_pipes:
					if conn.poll():
						worker_state[w]=conn.recv()
					if not self.quiet:
						print(("Worker %02d: %02d/%02d ["%(w, worker_state[w], self.worker_sizes[w]))+"#"*worker_state[w]+\
							" "*(self.worker_sizes[w]-worker_state[w])+"] -> "\
							+(self.worker_queues[w][worker_state[w]] if worker_state[w]<self.worker_sizes[w] else "Done!"))
					w+=1
				if not self.quiet:
					print("Overall  : %02d/%02d ["%(sum(worker_state), len(self.states))+"#"*sum(worker_state)+" "*(len(self.states)-sum(worker_state))+"]")
				time.sleep(1)
			self.log("Finished!")
		else:
			return worker_pipes

class MapBuilder(LoggingThingy):
	def __init__(self, states, sdl_driver, refresh, start_from, quiet):
		self.states=states
		self.quiet=quiet
		self.refresh=refresh
		self.start_from=start_from
		self.open_log()
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
		for item in self.states:
			if not self.quiet:
				print("\rRendering state %02d/%02d ["%(i, len(self.states))+("#"*i)+(" "*(len(self.states)-i))+"] -> "+item+" "*10, end="")
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
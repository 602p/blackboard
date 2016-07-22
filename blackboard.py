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
sys.path.append("datasources")

MASKS_PATH="masks/%s.png"
CACHE_PATH="statecache/%s.png"
FINAL_PATH="out/%s.png"

def load_datasource(name):
	return importlib.import_module(name)

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

def _build_state_worker(worker_id, states, datasources, connection):
	with open("log/worker_%d.log" % worker_id, 'w') as fd:
		def log(txt):
			fd.write(txt+"\n")
		log("Worker %d started, pid=%d" % (worker_id, os.getpid()))
		log("worker_id=%d, states=%s, datasources=%s, connection=%s" % (worker_id, str(states), str(datasources), str(connection)))
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
			stopwords.add("RT")
			stopwords.add("RT@")
			log("Creating WordCloud...")
			wc = wordcloud.WordCloud(background_color=None, mode="RGBA", max_words=2000, mask=mask, stopwords=stopwords)
			log("Generating WordCloud...")
			wc.generate(text)
			#log("Coloring WordCloud...")
			#wc.recolor(color_func=grey_color_func, random_state=3)
			log("Saving...")
			wc.to_file(CACHE_PATH%item)
			log("Colorkeying State")
			os.system("convert %s -transparent white %s" % (CACHE_PATH%item, FINAL_PATH%item))
			s+=1
			connection.send(s)

class BuildCacheManager(LoggingThingy):
	def __init__(self, states, workers, datasources, quiet=False):
		self.open_log()
		self.datasources=[load_datasource(ds) for ds in datasources]
		self.states=states
		self.workers=workers
		self.quiet=quiet
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
		assert sum([len(wq) for wq in self.worker_queues])==50, "Distributing states failed"

	def run(self):
		self.log("Starting %d processes............" % self.workers)
		time.sleep(0.5)
		worker_pipes=[i for i in range(self.workers)]
		for p_id in range(self.workers):
			worker_pipes[p_id], child_pipe=multiprocessing.Pipe()
			multiprocessing.Process(target=_build_state_worker, args=(p_id, self.worker_queues[p_id], self.datasources, child_pipe)).start()
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
			time.sleep(1)
		self.log("Finished!")

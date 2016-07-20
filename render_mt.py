import warnings
warnings.simplefilter("ignore")

import praw
from os import path
import os, random, sys, urllib, time
from PIL import Image
import numpy as np
import wordcloud
warnings.simplefilter("ignore")

LOWBOUND=50
HIGHBOUND=200
CALLBACK="http://127.0.0.1:5000/update_worker_progress/%d/%d"

WORKER_ID=int(sys.argv[1])

def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return "rgb(%d, %d, %d)" % (random.randint(LOWBOUND, HIGHBOUND), 
    	random.randint(LOWBOUND, HIGHBOUND), 
    	random.randint(LOWBOUND, HIGHBOUND))


def render_state(state):
	print ("Connecting to reddit...")
	r=praw.Reddit("blackboard worker %d" % WORKER_ID)
	#r.set_oauth_app_info(client_id="OuF9NMxW2L5Bow",
	#	client_secret="reKtOR0dcRhlQEDHgfIwaKCZ2y0",
	#	redirect_uri="http://127.0.0.1:65010/authorize_callback")
	print("Reading Submissions...")
	submissions = r.get_subreddit(state).get_hot(limit=50)

	print("Building text...")
	text=""
	for submission in submissions:
		text+=submission.title

	print("Loading Mask...")
	mask = np.array(Image.open("masks/"+state+".png"))

	stopwords = set(wordcloud.STOPWORDS)
	stopwords.add("said")

	print("Creating WordCloud...")

	wc = wordcloud.WordCloud(background_color=None, mode="RGBA", max_words=2000, mask=mask,
	               stopwords=stopwords)
	print("Generating WordCloud...")
	wc.generate(text)
	print("Coloring WordCloud...")
	wc.recolor(color_func=grey_color_func, random_state=3)

	print("Saving...")
	wc.to_file("statecache/"+state+"_out.png")
	print("Done!")
	print("Colorkeying State")
	os.system("convert %s -transparent white %s" % ("statecache/"+state+"_out.png", "out/"+state+".png"))


if __name__=="__main__":

	i=0
	print("ARGS="+str(sys.argv))
	for item in sys.argv[2:]:
		print("Rendering State "+item+"...")
		render_state(item)
		i+=1
		urllib.request.urlopen(CALLBACK%(WORKER_ID, i))
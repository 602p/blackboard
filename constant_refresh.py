import urllib, render_mt, os

while 1:
	for item in [x.replace(".png","") for x in os.listdir("masks")]:
		print("Rendering "+item)
		render_mt.render_state(item)
		urllib.request.urlopen("http://localhost:5000/notify_updated_state/"+item)
import urllib, render_mt, os, sys

states=[x.replace(".png","") for x in sorted(os.listdir("masks"))]
print(states)
a=int(sys.argv[1])
print(a)

if a==-1:
	print("Taking all")
	my_states=states
elif a==0:
	print("Taking 0:13")
	my_states=states[0:13]
elif a==1:
	print("Taking 13:26")
	my_states=states[13:26]
elif a==2:
	print("Taking 26:38")
	my_states=states[26:38]
else:
	print("Taking 38:50")
	my_states=states[38:50]

print(sys.argv)
print(my_states)

while 1:
	for item in my_states:
		print("Rendering "+item)
		render_mt.render_state(item)
		urllib.request.urlopen("http://localhost:80/notify_updated_state/"+item)

import os

print("Colorkeying images...")
i=1
for item in [x.replace(".png","") for x in os.listdir("masks")]:
	f="statecache/%s_out.png"%item
	f2="out/%s.png"%item
	c="convert %s -transparent white %s" % (f, f2)
	print("\rKeying state %02d/50 : [%s] -> %s               " % (i, ("#"*i+" "*(50-i)), item), end="")
	os.system(c)
	i+=1
print("Done!")
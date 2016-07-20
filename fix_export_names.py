def fix(n):
	return n.replace(" ","").replace("(","").replace(")","").split(".")[0][:-2].lower()+".png"

import os

for item in os.listdir("masks"):
	cmd="mv \"masks/%s\" \"masks/%s\"" % (item, fix(item))
	print(cmd)
	os.system(cmd)
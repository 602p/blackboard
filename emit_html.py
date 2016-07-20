import os

STATES=[x.replace(".png","") for x in os.listdir("masks")]
IMAGE_SOURCE="out/%s.png"

with open("index.htm", 'w') as fd:
	fd.write("""<html>
<head>
<style>
img{
	position:absolute;
	top:0px;
	left:0px;
}
</style>
</head>
<body>""")
	for item in STATES:
		fd.write("<img src=\"%s\" ></img>"%(IMAGE_SOURCE%item))
	fd.write("</body></html>")
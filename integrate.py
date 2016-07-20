import os
 
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame, json, calendar, time

print(" (integrate using SDL_VIDEODRIVER=dummy) ")

pygame.init()
screen=pygame.display.set_mode((2000, 1379))

screen.fill((0,0,0))
# with open("save.json", 'r') as fd:
# 	i=1
# 	for item in json.load(fd):
# 		s=State.from_json(item)
# 		print("\rRendering state %02d/50 : [%s] -> %s                " % (i, ("#"*i+" "*(50-i)), s.state), end="")
# 		s.render(screen)
# 		i+=1

i=1
for item in os.listdir("masks"):
	item=item.replace(".png","")
	print("\rRendering state %02d/50 : [%s] -> %s                " % (i, ("#"*i+" "*(50-i)), item), end="")
	img=pygame.image.load("statecache/%s_out.png" % item).convert()
	img.set_colorkey((0,0,0))
	screen.blit(img, (0,0))
	i+=1

pygame.display.flip()

print("\nSaving snapshot...")
pygame.image.save(screen, "integrated.png")
os.system("cp integrated.png integrated/%d.png" % calendar.timegm(time.gmtime()))
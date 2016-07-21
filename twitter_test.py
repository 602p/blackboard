import twitter, json

with open("twitter_keys.json", 'r') as fd:
	keydata=json.load(fd)

api=twitter.Api(**keydata)
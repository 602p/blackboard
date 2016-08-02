class TwitterDatasource:
	def setup(self):
		import twitter, json

		with open("twitter_keys.json", 'r') as fd:
			keydata=json.load(fd)

		self.api=twitter.Api(**keydata)

	def get_words(self, state):
		search=self.api.GetSearch("#"+state)
		return " ".join([x.text for x in search])

	def get_embed_data(self):
		return {
			"name":"twitter",
			"desc":"Twitter trending for searching for each state's hashtag",
			"linkout":"https://twitter.com/search?q=#<STATE>%20<QUERY>"
		}

blackboard_datasource=TwitterDatasource
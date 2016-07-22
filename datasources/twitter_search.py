class TwitterDatasource:
	def setup(self):
		import twitter, json

		with open("twitter_keys.json", 'r') as fd:
			keydata=json.load(fd)

		self.api=twitter.Api(**keydata)

	def get_words(self, state):
		search=self.api.GetSearch(state)
		return " ".join([x.text for x in search])

blackboard_datasource=TwitterDatasource
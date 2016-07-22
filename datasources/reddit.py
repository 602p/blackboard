class RedditDatasource:
	def setup(self):
		import praw
		self.reddit=praw.Reddit("blackboard worker")
		self.reddit.get_subreddit("programming").get_hot(limit=1) #test

	def get_words(self, state):
		submissions = self.reddit.get_subreddit(state).get_hot(limit=50)
		text=""
		for submission in submissions:
			text+=submission.title
		return text

blackboard_datasource=RedditDatasource
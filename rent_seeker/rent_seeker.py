"""main class"""

import praw

class RentSeeker(object):
    """crossposts /new into discussion thread"""
    __slots__ = ["reddit", "subreddit"]

    def __init__(self, reddit: praw.Reddit, subreddit: str) -> None:
        """initialize rentseeker"""
        self.reddit: praw.Reddit = reddit
        self.subreddit: praw.models.Subreddit = self.reddit.subreddit(subreddit)

    def listen(self) -> None:
        """listens to subreddit's posts"""
        def start_time() -> int:
            """returns start time of function"""
            from calendar import timegm
            from datetime import datetime
            return int(timegm(datetime.utcnow().utctimetuple()))

        start: int = start_time()
        for post in self.subreddit.stream.submissions(pause_after=3):
            if  int(post.created_utc) > start:
                self.post_comment(post)
        return

    def post_comment(self, post: praw.models.Submission) -> None:
        """posts comment in discussion thread"""
        def get_discussion_thread() -> praw.models.Submission:
            """returns discussion thread"""
            for submission in self.subreddit.search("Discussion Thread", sort="new"):
                if submission.author == self.reddit.user.me():
                    return submission

        discussion_thread: praw.models.Submission = get_discussion_thread()
        body: str = f"New Post in [/new](/r/{self.subreddit}/new): [{post.title}]({post.permalink})"

        discussion_thread.reply(body)
        return

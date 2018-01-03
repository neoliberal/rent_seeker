"""main class"""

import praw

class Crosspost(object):
    def __init__(self, reddit: praw.Reddit, subreddit: str) -> None:
        self.reddit: praw.Reddit = reddit
        self.subreddit: praw.models.Subreddit = self.reddit.subreddit(subreddit)
        return

    def listen(self) -> None:
        return
    
    def comment(self, post: praw.models.Submission) -> None:
        def get_discussion_thread() -> praw.models.Submission:
            return

        discussion_thread: praw.models.Submission = get_discussion_thread()
        body: str = f"[{post.title}]({post.permalink})"
        discussion_thread.reply(body)
        return
            
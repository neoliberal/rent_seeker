"""main class"""
from typing import List

import praw

class RentSeeker(object):
    """crossposts /new into discussion thread"""
    __slots__ = ["reddit", "subreddit", "tracked"]

    def __init__(self, reddit: praw.Reddit, subreddit: str) -> None:
        """initialize rentseeker"""
        self.reddit: praw.Reddit = reddit
        self.subreddit: praw.models.Subreddit = self.reddit.subreddit(subreddit)
        self.tracked: List[praw.models.Comment] = list()

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

        for comment in self.tracked:
            if comment.replies:
                moderator: praw.models.reddit.submission.SubmissionModeration = (
                    self._get_discussion_thread().mod
                )
                for subcomment in comment.replies:
                    moderator.remove(subcomment)
        return

    def post_comment(self, post: praw.models.Submission) -> None:
        """posts comment in discussion thread"""
        discussion_thread: praw.models.Submission = self._get_discussion_thread()
        body: str = "\n".join([
            f"New Post in [/new](/r/{self.subreddit}/new): [{post.title}]({post.permalink})",
            "*Replies to this comment will be removed, please participate in the linked thread*"
        ])

        comment: praw.models.Comment = discussion_thread.reply(body)
        self.tracked.append(comment)
        return

    def _get_discussion_thread(self) -> praw.models.Submission:
        """returns discussion thread"""
        for submission in self.subreddit.search("Discussion Thread", sort="new"):
            if submission.author == self.reddit.user.me():
                return submission

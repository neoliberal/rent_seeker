"""main class"""
from typing import Dict
import logging

import praw
from slack_python_logging import slack_logger

class RentSeeker(object):
    """crossposts /new into discussion thread"""
    __slots__ = ["logger", "reddit", "subreddit", "init_time", "tracked"]

    def __init__(self, reddit: praw.Reddit, subreddit: str) -> None:
        """initialize rentseeker"""
        def start_time() -> int:
            """returns start time of function"""
            from calendar import timegm
            from datetime import datetime
            return int(timegm(datetime.utcnow().utctimetuple()))

        self.logger: logging.Logger = slack_logger.initialize("rent_seeker")
        self.reddit: praw.Reddit = reddit
        self.subreddit: praw.models.Subreddit = self.reddit.subreddit(subreddit)
        self.tracked: Dict[str, praw.models.Comment] = dict()
        self.init_time: int = start_time()
        self.logger.debug("Start time is \"%s\"", self.init_time)
        self.logger.info("Successfully initialized")

    def listen(self) -> None:
        """listens to subreddit's posts"""

        for post in self.subreddit.stream.submissions(pause_after=3):
            if post is None:
                self.logger.debug("None found, skipping")
                break
            if  int(post.created_utc) > self.init_time and str(post) not in self.tracked:
                self.post_comment(post)

        for comment in self.tracked.values():
            comment.refresh()
            if comment.replies.__len__() is not 0:
                self.logger.debug("Removing found comment replies")
                for subcomment in comment.replies.list():
                    self._get_moderator().remove(subcomment)
                self.logger.debug("Removed comment replies")
        return

    def post_comment(self, post: praw.models.Submission) -> None:
        """posts comment in discussion thread"""
        discussion_thread: praw.models.Submission = self._get_discussion_thread()
        body: str = "".join([
            f"New Post in [/new](/r/{self.subreddit}/new): [{post.title}]({post.permalink})",
            ""
            "*Replies to this comment will be removed, please participate in the linked thread*"
        ])

        self.logger.debug("Posting comment")
        comment: praw.models.Comment = discussion_thread.reply(body)
        self.logger.debug("Posted comment")

        self.tracked[str(post)] = comment
        self.logger.debug("Added \"%s\" to tracked comments", comment)
        return

    def _get_discussion_thread(self) -> praw.models.Submission:
        """returns discussion thread"""
        self.logger.debug("Finding discussion thread")
        for submission in self.subreddit.search("Discussion Thread", sort="new"):
            if submission.author == self.reddit.user.me():
                self.logger.debug("Found discussion thread")
                return submission
        self.logger.error("Could not find discussion thread")

    def _get_moderator(self) -> praw.models.reddit.submission.SubmissionModeration:
        """returns discussion thread moderator commands"""
        return self._get_discussion_thread().mod

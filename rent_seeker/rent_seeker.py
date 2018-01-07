"""main class"""
from pathlib import Path
import pickle
import logging
from typing import Dict
import signal

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
        self.tracked: Dict[str, praw.models.Comment] = self.load()
        self.init_time: int = start_time()
        signal.signal(signal.SIGTERM, self.exit)
        self.logger.debug("Start time is \"%s\"", self.init_time)
        self.logger.info("Successfully initialized")

    def exit(self, signum: int, frame) -> None:
        """defines exit function"""
        import os
        _ = frame
        self.save()
        self.logger.info("Exited gracefully with signal %s", signum)
        os._exit(os.EX_OK)
        return

    def load(self) -> Dict[str, praw.models.Comment]:
        """loads pickle if it exists"""
        self.logger.debug("Loading pickle file")
        tracked_file: Path = Path("tracked_comments.pkl")
        tracked_file.touch()
        with tracked_file.open('rb') as pickled_file:
            try:
                tracked: Dict[str, praw.models.Comment] = pickle.loads(pickled_file.read())
                self.logger.debug("Loaded pickle file")
                self.logger.debug("Contents: %s", str(tracked))
                return tracked
            except EOFError:
                self.logger.debug("No pickle found, returning blank dictionary")
                return {}

    def save(self) -> None:
        """pickles tracked comments after shutdown"""
        self.logger.debug("Saving pickle file")
        tracked_file: Path = Path("tracked_comments.pkl")
        with tracked_file.open('wb') as pickled_file:
            pickled_file.write(pickle.dumps(self.tracked))
            self.logger.debug("Saved pickle file")

    def listen(self) -> None:
        """listens to subreddit's posts"""
        def filter_post(post: praw.models.Submission) -> bool:
            """filters post based on criteria"""
            if post.title == "Discussion Thread":
                return False
            return True

        import prawcore
        from time import sleep
        try:
            for post in self.subreddit.stream.submissions(pause_after=3):
                if post is None:
                    break
                if  (int(post.created_utc) > self.init_time
                     and str(post) not in self.tracked and filter_post(post)
                    ):
                    self.post_comment(post)
        except prawcore.exceptions.ServerError:
            self.logger.error("Server error: Sleeping for 1 minute.")
            sleep(60)
        except prawcore.exceptions.ResponseException:
            self.logger.error("Response error: Sleeping for 1 minute.")
            sleep(60)
        except prawcore.exceptions.RequestException:
            self.logger.error("Request error: Sleeping for 1 minute.")
            sleep(60)

        from datetime import datetime, timedelta
        for post, comment in self.tracked.copy().items():
            comment.refresh()
            if len(comment.replies) is not 0:
                for subcomment in comment.replies.list():
                    if subcomment.banned_by == str(self.reddit.user.me()):
                        continue
                    subcomment.mod.remove()
                    self.logger.debug("Removed comment reply")
            delta: timedelta = datetime.utcnow() - datetime.utcfromtimestamp(comment.created_utc)
            if delta.days > 1:
                self.logger.debug("No longer tracking comment \"%s\", over a day old", str(comment))
                del self.tracked[post]

        return

    def post_comment(self, post: praw.models.Submission) -> None:
        """posts comment in discussion thread"""
        discussion_thread: praw.models.Submission = self._get_discussion_thread()
        body: str = "\n\n".join([
            f"New Post in [/new](/r/{self.subreddit}/new): [{post.title}]({post.permalink})",
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

"""main class"""
import pickle
import logging
from typing import Deque, NamedTuple
import os
import signal

import praw
from slack_python_logging import slack_logger

# pylint: disable=R0903
class Holder(NamedTuple):
    """holds comment and post objects"""
    post: str
    comment: str

class RentSeeker(object):
    """crossposts /new into discussion thread"""
    __slots__ = ["logger", "reddit", "subreddit", "init_time", "tracked", "bot_name"]

    def __init__(self, reddit: praw.Reddit, subreddit: str) -> None:
        """initialize rentseeker"""
        def start_time() -> int:
            """returns start time of function"""
            from calendar import timegm
            from datetime import datetime
            return int(timegm(datetime.utcnow().utctimetuple()))

        def register_signals() -> None:
            """registers signals for systemd"""
            signal.signal(signal.SIGTERM, self.exit)

        self.logger: logging.Logger = slack_logger.initialize(
            app_name = "rent_seeker",
            stream_loglevel = "INFO",
            slack_loglevel = "CRITICAL",
        )
        self.reddit: praw.Reddit = reddit
        self.bot_name = os.environ['dt_bot_username']
        self.subreddit: praw.models.Subreddit = self.reddit.subreddit(subreddit)
        self.tracked: Deque[Holder] = self.load()
        self.init_time: int = start_time()
        register_signals()
        self.logger.debug("Start time is \"%s\"", self.init_time)
        self.logger.info("Successfully initialized")

    def exit(self, signum: int, frame) -> None:
        """defines exit function"""
        import os
        _ = frame
        self.save()
        self.logger.info("Exited gracefully with signal %s", signum)
        os._exit(os.EX_OK) #pylint: disable=W0212
        return

    def load(self) -> Deque[Holder]:
        """loads pickle if it exists"""
        self.logger.debug("Loading pickle file")
        try:
            with open("tracked_comments.pkl", 'rb') as pickled_file:
                try:
                    tracked: Deque[Holder] = pickle.loads(pickled_file.read())
                    self.logger.debug("Loaded pickle file")
                    self.logger.debug("Current length: %s", len(tracked))
                    if tracked.maxlen != 250:
                        self.logger.warning("Deque has invalid max length, returning new one")
                        return Deque(tracked, maxlen=250)
                    self.logger.debug("Contents: %s", str(tracked))
                    return tracked
                except EOFError:
                    self.logger.debug("No pickle found, returning blank dictionary")
                    return Deque(maxlen=250)
                except pickle.UnpicklingError:
                    self.logger.warning("Could not unpickle file, returning blank deque")
                    return Deque(maxlen=250)
        except FileNotFoundError:
            self.logger.debug("Comment not found, returning empty deque")
            return Deque(maxlen=250)

    def save(self) -> None:
        """pickles tracked comments after shutdown"""
        self.logger.debug("Saving pickle file")
        with open("tracked_comments.pkl", 'wb') as pickled_file:
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
                     and not any(item for item in self.tracked if item.post == str(post))
                     and filter_post(post)
                    ):
                    self.post_comment(post)
            for reply in self.reddit.inbox.unread():
                if (isinstance(reply, praw.models.Comment)
                        and any(item for item in self.tracked if item.comment == str(reply.parent()))
                   ):
                    reply.mod.remove()
                    self.logger.debug("Removed comment reply")
                    reply.mark_unread()
        except prawcore.exceptions.ServerError:
            self.logger.error("Server error: Sleeping for 15 minutes.")
            sleep(60 * 15)
        except prawcore.exceptions.ResponseException:
            self.logger.error("Response error: Sleeping for 1 minute.")
            sleep(60)
        except prawcore.exceptions.RequestException:
            self.logger.error("Request error: Sleeping for 1 minute.")
            sleep(60)
        # Started hitting rate limits in Feb 2022, added this to hopefully help
        sleep(2)

    def post_comment(self, post: praw.models.Submission) -> None:
        """posts comment in discussion thread"""
        discussion_thread: praw.models.Submission = self._get_discussion_thread()
        if discussion_thread is None:
            # This tends to happen when Reddit is running slow.
            # We haven't added the submission to tracked yet, and we've logged
            # the error. So just exit and try again later.
            return
        body: str = "\n\n".join([
            f"[/new](/r/{self.subreddit}/new): [{post.title}]({post.permalink})",
            "*Replies to this comment will be removed, please participate in the linked thread*"
        ])

        self.logger.debug("Posting comment")
        comment: praw.models.Comment = discussion_thread.reply(body)
        self.logger.info("Posted comment %s linking to submission %s", comment, post)

        self.tracked.append(Holder(str(post), str(comment)))
        self.logger.debug("Added \"%s\" to tracked comments", comment)
        return

    def _get_discussion_thread(self) -> praw.models.Submission:
        """returns discussion thread"""
        self.logger.debug("Finding discussion thread")
        return next(self.reddit.redditor(self.bot_name).submissions.new(limit=1))
        self.logger.error("Could not find discussion thread")

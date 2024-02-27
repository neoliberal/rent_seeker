"""service file"""
import os

import praw

try:
    from rent_seeker import RentSeeker
except ModuleNotFoundError:
    from .rent_seeker import RentSeeker

def main() -> None:
    """main service function"""

    reddit: praw.Reddit = praw.Reddit(
        client_id=os.environ["client_id"],
        client_secret=os.environ["client_secret"],
        refresh_token=os.environ["refresh_token"],
        user_agent="linux:rent_seeker:v1.0 (by /u/CactusChocolate)"
    )

    bot: RentSeeker = RentSeeker(
        reddit,
        "neoliberal+metaNL"
    )

    while True:
        bot.listen()

    return

if __name__ == "__main__":
    main()

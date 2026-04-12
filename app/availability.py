"""
Availability tagger — marks each game based on your work schedule.

Tags:
  "can_watch"  — game is outside work hours, you're free
  "will_miss"  — game falls entirely within work hours
"""

from datetime import datetime
import pytz

import config


def tag_availability(games):
    """
    Set the 'availability' field on each game.
    Modifies games in place and returns them.
    """
    tz = pytz.timezone(config.TIMEZONE)
    work = config.WORK_SCHEDULE

    for game in games:
        try:
            # Parse the UTC date string into a timezone-aware local datetime
            game_dt = datetime.fromisoformat(game["date"].replace("Z", "+00:00"))
            local_dt = game_dt.astimezone(tz)

            weekday = local_dt.weekday()  # 0=Monday, 6=Sunday
            hour = local_dt.hour

            # Check if the game falls during work hours
            is_work_day = weekday in work["days"]
            is_work_hours = work["start_hour"] <= hour < work["end_hour"]

            if is_work_day and is_work_hours:
                game["availability"] = "will_miss"
            else:
                game["availability"] = "can_watch"

        except (ValueError, KeyError):
            # If we can't parse the date, assume available
            game["availability"] = "can_watch"

    return games

import pickle
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable

import requests
from pywikibot import Site
from pywikibot.logentries import RightsEntry
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.tools import itergroup


class Right(Enum):
    GOOD_EDITOR = "goodeditor"
    PATROLLER = "patroller"
    HONORED_MAINTAINER = "honoredmaintainer"
    ADMIN = "admin"
    USER = "user"

    def __str__(self):
        return self.value

    def to_chinese(self):
        if self == self.GOOD_EDITOR:
            return "优质编辑者"
        if self == self.PATROLLER:
            return "巡查姬"
        if self == self.HONORED_MAINTAINER:
            return "荣誉维护人员"
        if self == self.USER:
            return "用户"
        return "？？？"



@dataclass
class RightChange:
    actor: str
    rights_added: list[str]
    rights_removed: list[str]
    timestamp: datetime
    reason: str


@dataclass
class UserRight:
    username: str
    events: list[RightChange]
    registration_date: datetime = datetime.fromtimestamp(0)
    earliest_event: datetime = datetime.fromtimestamp(0)


def parse_date(d: str) -> datetime:
    # auto CST
    return datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)


def get_user_right_history() -> dict[str, UserRight]:
    site = Site()
    data_path = Path("data")
    data_path.mkdir(exist_ok=True)
    cache_path = data_path.joinpath("user_rights_logs.txt")
    if not cache_path.exists():
        user_rights: dict[str, UserRight] = dict()
        events = list(site.logevents(logtype="rights"))
        for event in events:
            event: RightsEntry
            data = event.data
            username = data['title'].replace('User:', '')
            if username not in user_rights:
                user_rights[username] = UserRight(username, [])
            user_rights[username].events.append(
                RightChange(
                    actor=data['user'],
                    rights_added=event.newgroups,
                    rights_removed=event.oldgroups,
                    timestamp=parse_date(data['timestamp']),
                    reason=data['comment'] if 'comment' in data else ''
                ))
        for usernames in itergroup(user_rights.keys(), 50):
            time.sleep(3)
            print("Retrieving registration dates for " + ", ".join(usernames))
            response = requests.get("https://mzh.moegirl.org.cn/api.php", params={
                'action': 'query',
                'list': 'users',
                'usprop': 'registration',
                'ususers': "|".join(usernames),
                'format': 'json'
            }).json()
            for r in response['query']['users']:
                if 'registration' in r:
                    user_rights[r['name']].registration_date = parse_date(r['registration'])
        with open(cache_path, "wb") as f:
            pickle.dump(user_rights, f)
    else:
        with open(cache_path, "rb") as f:
            user_rights = pickle.load(f)
    return user_rights


def process_users(users: Iterable[UserRight]) -> list[UserRight]:
    target_user_rights = {r.value for r in Right}
    resulting_users = []
    for user in users:
        resulting_events = []
        for event in user.events:
            added = [Right(right)
                     for right in event.rights_added
                     if right in target_user_rights and right not in event.rights_removed]
            removed = [Right(right)
                       for right in event.rights_removed
                       if right in target_user_rights and right not in event.rights_added]
            event.rights_removed = removed
            event.rights_added = added
            if len(added) > 0 or len(removed) > 0:
                resulting_events.append(event)
        user.events = resulting_events
        if len(user.events) > 0:
            user.events.sort(key=lambda e: e.timestamp)
            user.earliest_event = user.events[0].timestamp
            resulting_users.append(user)
    resulting_users.sort(key=lambda u: u.earliest_event)
    return resulting_users


def date_to_str(d: datetime) -> str:
    return d.strftime("%Y.%m.%d")


def get_extras(events: list[RightChange]) -> str:
    """
    Convert events to extra string.
    1. goodeditor to nothing
    2. goodeditor to patroller
    3. patroller to goodeditor
    4. anything to honoredmaintainer
    :param events: List of events
    :return: A string
    """
    res = ""
    for e in events:
        # lose goodeditor
        date = e.timestamp
        date_str = f'{date.year}年{date.month}月{date.day}日'
        if len(e.rights_added) == 0:
            res += f'{date_str}因"{e.reason}"被{e.actor}除权。'
        elif e.rights_added[0] == Right.PATROLLER:
            if len(e.rights_removed) > 0 and e.rights_removed[0] == Right.GOOD_EDITOR:
                res += f'{date_str}因"{e.reason}"被提权为巡查姬。'
            # else:
            #     res += f'{date_str}因"{e.reason}"从？？？成为巡查姬。'
        elif e.rights_added[0] == Right.GOOD_EDITOR and len(e.rights_removed) > 0:
            res += f'{date_str}因"{e.reason}"被降权为优质编辑者。'
        elif e.rights_added[0] == Right.HONORED_MAINTAINER:
            res += f'{date_str}因"{e.reason}"成为荣誉维护人员。'
    return res


def user_to_table_row(user: UserRight) -> str:
    periods = []
    current_status = []
    for e in user.events:
        if Right.GOOD_EDITOR in e.rights_added:
            periods.append((e.timestamp, None, e.actor, e.reason if e.reason.strip() != "" else "（无理由）"))
        if Right.GOOD_EDITOR in e.rights_removed:
            periods[-1] = (periods[-1][0], e.timestamp, periods[-1][2], periods[-1][3])
        current_status = e.rights_added if len(e.rights_added) > 0 else current_status
        if len(e.rights_removed) > 0 and e.rights_removed[0] == current_status:
            current_status = "user"
    extras = get_extras(user.events)
    row_span = len(periods)
    if row_span == 0:
        return ""
    row_span_string = "" if row_span == 1 else "rowspan=" + str(row_span) + "|"
    periods_strings = [(date_to_str(p[0]) + " - " + (date_to_str(p[1]) if p[1] else "") + "||" + p[2],
                        p[3])
                       for p in periods]
    res = "|-\n|" + row_span_string + " -{[[U:" + user.username + "]]}- || " + row_span_string + \
        date_to_str(user.registration_date) + " || " + periods_strings[0][0] + "||" + \
          row_span_string + Right(current_status[0]).to_chinese() + "||" + periods_strings[0][1] + "||" + \
          row_span_string + extras + "\n"
    if row_span > 1:
        res += "".join("|-\n| " + s[0] + "||" + s[1] + "\n" for s in periods_strings[1:])
    return res


def good_editor_history():
    user_rights = get_user_right_history()
    users = process_users(user_rights.values())
    users = [user for user in users if user.earliest_event >= datetime.fromisoformat("2018-11-02")]
    print("".join(user_to_table_row(u) for u in users))


if __name__ == "__main__":
    good_editor_history()

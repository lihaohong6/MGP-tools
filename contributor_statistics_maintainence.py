import pickle
from datetime import  datetime, timedelta
from pathlib import Path

from pywikibot import Site, APISite, User, Timestamp

mgp: APISite = Site(fam="mgp")


def get_good_editors():
    return mgp.allusers(group="goodeditor")


CUR_DATE = datetime.now()
MAINTENANCE_START = datetime(year=2022, month=10, day=11)
DAY_COUNT = 7


def in_prev_range(ts: Timestamp):
    return MAINTENANCE_START > ts > MAINTENANCE_START + timedelta(days=-DAY_COUNT)


def in_cur_range(ts: Timestamp):
    return ts > CUR_DATE + timedelta(days=-DAY_COUNT)


def before_acceptable_range(ts: Timestamp):
    return ts <= MAINTENANCE_START + timedelta(days=-DAY_COUNT)


def main():
    data_path = Path("data")
    data_path.mkdir(exist_ok=True)
    good_editor_file = data_path.joinpath("good_editors.pickle")
    if good_editor_file.exists():
        good_editors = pickle.load(open(good_editor_file, "rb"))
    else:
        good_editors = list(get_good_editors())
        with open(good_editor_file, "wb") as f:
            pickle.dump(good_editors, f)
    for editor in good_editors:
        username = editor['name']
        user = User(source=mgp, title=username)
        prev_contrib, cur_contrib = 0, 0
        for c in user.contributions():
            _, _, timestamp, _ = c
            if in_prev_range(timestamp):
                prev_contrib += 1
            elif in_cur_range(timestamp):
                cur_contrib += 1
            elif before_acceptable_range(timestamp):
                break
        print("|-")
        print(f"|-{{{username}}}- || {prev_contrib} || {cur_contrib}")


if __name__ == "__main__":
    main()

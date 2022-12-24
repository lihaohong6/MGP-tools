import collections
import re
from dataclasses import dataclass
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Generator, Iterable

import bilibili_api.video
from bilibili_api import sync
from bilibili_api.user import ChannelSeries, ChannelSeriesType, User


# from https://github.com/ShiSheng233/bili_BV/blob/master/biliBV/__init__.py
def av_to_bv(av):
    key = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
    dic = {}
    for num in range(58):
        dic[key[num]] = num
    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608
    av = (int(str(av).lstrip('av')) ^ xor) + add
    r = list('BV1  4 1 7  ')
    for a in range(6):
        r[s[a]] = key[av // 58 ** a % 58]
    return ''.join(r)


def bv_to_av(BV):
    key = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
    dic = {}
    for num in range(58):
        dic[key[num]] = num
    s = [11, 10, 3, 8, 4, 6]
    xor = 177451812
    add = 8728348608
    r = 0
    for a in range(6):
        r += dic[BV[s[a]]] * 58 ** a
    return (r - add) ^ xor


@dataclass
class Video:
    bv: str
    title: str
    pubdate: int
    image_link: str


def timestamp_to_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone(offset=timedelta(hours=8))).strftime("%y/%m/%d")


def get_videos_in_channel(s: ChannelSeries) -> list[Video]:
    videos = []
    page = 1
    page_size = 100
    while True:
        v = sync(s.get_videos(pn=page, ps=page_size))['archives']
        videos.extend(v)
        if len(v) < page_size:
            break
        page += 1
    return [parse_video(v) for v in videos]


def has_tags(bv: str, tags: list[str]) -> bool:
    video_tags = [tag['tag_name'] for tag in sync(bilibili_api.video.Video(bvid=bv).get_tags())]
    return any(tag in video_tags for tag in tags)


def filter_videos(videos: Iterable[Video], keywords: list[str] = None, exclude: list[str] = None,
                  tags: list[str] = None) -> Generator:
    for v in videos:
        if (keywords is None or any(keyword in v.title for keyword in keywords)) and \
                (exclude is None or all(e not in v.title for e in exclude)) and \
                (tags is None or has_tags(v.bv, tags)):
            yield v


def write_videos_to_file(videos) -> None:
    videos = list(videos)
    result = []
    videos = sorted(videos, key=lambda vid: vid.pubdate)
    for index, v in enumerate(videos):
        s = ("{{Temple Song\n"
             "|color = transparent\n"
             "|bb_id = " + v.bv + "\n" +
             "|曲目 = " + v.title + "\n" +
             "|投稿日期 = " + timestamp_to_date(v.pubdate) + "\n" +
             "|再生数量 = " + "{{BilibiliCount|id=" + v.bv + "}}\n" +
             "|image link = " + v.image_link + " }}"
             )
        result.append(s)
    open("data/vtuber_songs.txt", "w").write("\n\n".join(result))


def parse_video(source) -> Video:
    pubdate = None
    if 'pubdate' in source:
        pubdate = source['pubdate']
    if 'created' in source:
        pubdate = source['created']
    return Video(source['bvid'], source['title'], pubdate, source['pic'])


def get_user_videos(uid: int, search: str = "", tid: int = 0) -> Generator:
    page = 1
    page_size = 30
    user = User(uid=uid)
    while True:
        videos = sync(user.get_videos(pn=page, tid=tid, ps=page_size, keyword=search))['list']['vlist']
        for v in videos:
            yield parse_video(v)
        if len(videos) < page_size:
            break
        page += 1


def merge_video_lists(*args):
    bvs = set()
    result = []
    for arg in args:
        for v in arg:
            if v.bv not in bvs:
                result.append(v)
                bvs.add(v.bv)
    return result


def video_list_subtract(a: list[Video], b: list[Video]) -> list[Video]:
    s = set(v.bv for v in b)
    return [v for v in a if v.bv not in s]


def get_bv_in_file(filename: str) -> Generator:
    with open(filename, "r") as f:
        file = f.read()
        matches = re.findall("BV[a-zA-Z0-9]{10}", file)
        av_list = re.findall("av[0-9]+", file)
    for match in matches:
        yield str(match)
    for av in av_list:
        yield av_to_bv(str(av))


def duplicate_bv(filename: str, repetitions: int):
    bv = get_bv_in_file(filename)
    d = dict(collections.Counter(bv))
    for k, v in d.items():
        if v != repetitions:
            print(k)


def bv_subtract(f1: str, f2: str):
    s1 = set(get_bv_in_file(f1))
    s2 = set(get_bv_in_file(f2))
    res = list(s1.difference(s2))
    print(len(res))
    print(res)
    print([bv_to_av(b) for b in res])


def main():
    # s = ChannelSeries(uid=63231, type_=ChannelSeriesType.SERIES, id_=899123)
    # videos = get_videos_in_channel(s)
    # videos2 = filter_videos(get_user_videos(140378), ["翻唱", "V家", "中文版"])
    # videos = merge_video_lists(videos2, videos1)
    videos = list(get_user_videos(uid=386900246, search="原创"))
    write_videos_to_file(videos)


if __name__ == "__main__":
    main()

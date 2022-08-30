from textwrap import indent
from typing import List, Optional

import requests
from mgp_common.config import get_cache_path
from mgp_common.japanese import is_japanese
from mgp_common.string_utils import auto_lj
from mgp_common.video import VideoSite
from mgp_common.vocadb import get_producer_songs, get_producer_albums, Song
from requests import Session


def song_to_link(s: Song) -> str:
    name_ja = s.name_ja
    if s.name_chs is not None:
        trans = s.name_chs
    elif len(s.name_other) == 1:
        trans = s.name_other[0]
    elif name_ja.isascii():
        return name_ja
    else:
        trans = name_ja
    return trans + "{{!}}" + auto_lj(name_ja)


def get_original_songs_template(songs: List[Song]):
    year_to_songs = dict()
    for index, s in enumerate(songs):
        prev = year_to_songs.get(s.publish_date.year, [])
        prev.append(s)
        year_to_songs[s.publish_date.year] = prev
    year_strings = []
    for year in sorted(year_to_songs.keys()):
        s = "|" + str(year) + "年\n" + \
            "|{{links|" + "|".join(song_to_link(s) for s in year_to_songs[year]) + "}}"
        year_strings.append(s)
    return "\n".join(year_strings)


def get_album_template(producer_id: str) -> str:
    albums = get_producer_albums(producer_id, only_main=True)
    if len(albums) == 0:
        return ""
    return "|专辑\n" + \
           "|{{lj|{{links|" + "|".join(albums) + "}}}}\n"


def search_bb_keyword(session: Session, keyword: str):
    try:
        response = session.get("http://api.bilibili.com/x/web-interface/search/type",
                               params={
                                   'keyword': keyword,
                                   'search_type': 'video',
                                   'duration': 1,
                                   'tids': 3,
                               }).json()
        res = []
        for result in response['data']['result'][:5]:
            res.append(result['title'])
        return res
    except Exception as e:
        return []


def search_bb_for_titles(session: Session, s: Song) -> List[str]:
    result = []
    for v in s.videos:
        if v.site == VideoSite.NICO_NICO:
            result.extend(search_bb_keyword(session, v.url[v.url.rfind('/') + 1:]))
    result.extend(search_bb_keyword(session, s.name_ja))
    return [t.replace('<em class="keyword">', '\033[1m')
                .replace('</em>', '\033[0m')
                .replace('&quot;', '"')
                .replace('&amp;', '&')
                .replace('&#39;', "'")
            for t in set(result)]


def make_template(producer_id: str):
    songs = get_producer_songs(producer_id)
    songs = [s for s in songs if len(s.videos) > 0 and s.original]
    sorted(songs, key=lambda s: s.publish_date)
    album_template = get_album_template(producer_id)

    def make_string():
        original_songs = get_original_songs_template(songs)
        return "{{大家族\n|name=\n|title=\n" + \
               "|state={{#ifeq:{{{1}}}|collapsed|mw-collapsible mw-collapsed|mw-uncollapsed}}\n" + \
               "|原创投稿曲目\n" + \
               "|{{大家族模板子项\n" + indent(original_songs + "}}", prefix="  ") + "\n" + \
               album_template + \
               "}}"

    p = get_cache_path().joinpath("vocaloid_producer_template.txt")
    session = requests.Session()
    # get cookies, see bilibili-API-collect for more information
    session.get("https://bilibili.com")
    for s in songs:
        with open(p, "w", encoding="utf-8") as f:
            f.write(make_string())
        titles = search_bb_for_titles(session, s)
        print("====== " + s.name_ja + " ======")
        print("\n".join(titles))
        options = ["Keep original.", *s.name_other,
                   "Enter your translation (input directly, don't use the number)."]
        print("\n".join(f"{index + 1}. {text}" for index, text in enumerate(options)))
        while True:
            response = input()
            if response.strip() == "":
                s.name_chs = s.name_ja
                break
            try:
                int_option = int(response)
                if int_option == 1:
                    s.name_chs = s.name_ja
                elif 1 < int_option < len(options):
                    s.name_chs = options[int_option - 1]
                else:
                    print("Invalid option number. Redo...")
                    continue
            except ValueError:
                s.name_chs = response.strip()
            break


def main():
    p = get_cache_path()
    p.mkdir(exist_ok=True)
    target = input("Vocadb id?\n").strip()
    print(make_template(target))


if __name__ == "__main__":
    main()

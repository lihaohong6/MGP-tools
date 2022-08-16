from textwrap import indent

from mgp_common.japanese import is_japanese
from mgp_common.string_utils import auto_lj
from mgp_common.vocadb import get_producer_songs, get_producer_albums, Song


def song_to_link(s: Song) -> str:
    name_ja = auto_lj(s.name_ja)
    if len(s.name_other) == 1:
        return s.name_other[0] + "{{!}}" + name_ja
    if is_japanese(name_ja):
        return s.name_ja + "{{!}}" + name_ja
    return name_ja


def get_original_songs_template(songs: list[Song]):
    year_to_songs = dict()
    for s in songs:
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
    albums = get_producer_albums(producer_id)
    if len(albums) == 0:
        return ""
    return "|专辑\n" + \
           "|{{lj|{{links|" + "|".join(albums) + "}}}}\n"


def make_template(producer_id: str):
    songs = get_producer_songs(producer_id)
    songs = [s for s in songs if len(s.videos) > 0 and s.original]
    sorted(songs, key=lambda s: s.publish_date)
    original_songs = get_original_songs_template(songs)
    return "{{大家族\n|name=\n|title=\n" + \
           "|state={{#ifeq:{{{1}}}|collapsed|mw-collapsible mw-collapsed|mw-uncollapsed}}\n" + \
           "|原创投稿曲目\n" + \
           "|{{大家族模板子项\n" + indent(original_songs + "}}", prefix="  ") + "\n" + \
           get_album_template(producer_id) + \
           "}}"


if __name__ == "__main__":
    target = input("Vocadb id?").strip()
    print(make_template(target))

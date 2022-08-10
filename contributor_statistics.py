import pickle
from pathlib import Path

import pywikibot as pwb
from pywikibot import Page, User
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.tools import itergroup
import pywikibot.data.api as api

special_user_groups = ['sysop', 'patroller', 'goodeditor', 'honoredmaintainer', 'autoconfirmed', 'user']
contributions: dict = {}
FILE_NAME = "data/contributor_statistics_{}.pickle"


def handle_user(byte_diff: int, groups: list[str]):
    for group in special_user_groups:
        if group in groups:
            contributions[group] += byte_diff
            return
    raise RuntimeError("User with undefined rights: " + str(groups))


def handle_page(page: Page, user_contributions: dict):
    prev_bytes = 0
    for revision in page.revisions(reverse=True):
        user = revision['user']
        byte_count = revision['size']
        byte_diff = max(0, byte_count - prev_bytes)
        if "mw-undo" in revision['tags']:
            byte_diff = 0
        user_contributions[user] = user_contributions.get(user, 0) + byte_diff
        prev_bytes = byte_count


def get_rand_pages(page_count: int):
    gen = GeneratorFactory()
    gen.handle_arg("-ns:0")
    gen.handle_arg("-random:" + str(page_count))
    return gen.getCombinedGenerator(preload=True)


def handle_user_contributions(user_contributions: dict):
    print(len(user_contributions), "users total.", (len(user_contributions) + 49) // 50, "tries required.")
    for users in itergroup(user_contributions.keys(), 50):
        r = api.Request(site=pwb.Site(),
                        parameters={'action': 'query',
                                    'list': 'users',
                                    'usprop': 'groups',
                                    'ususers': '|'.join(users)})
        response = r.submit()['query']['users']
        for user in response:
            if 'groups' not in user:
                # ip editor
                user['groups'] = ['user']
            handle_user(user_contributions[user['name']], user['groups'])
        print(contributions)


def visualize(data: dict[str, int]):
    s = sum(data.values())
    print(s, "bytes total.")
    left_length = max(map(len, data.keys()))
    for k, v in data.items():
        print(f"{k.ljust(left_length)}: {'%.2f' % (v / s * 100) : >5}%")
    print()


def get_user_contributions(page_count: int):
    user_contributions_file = Path(FILE_NAME.format("user_contributions_" + str(page_count)))
    if user_contributions_file.exists():
        print("Loading existing user contributions.")
        user_contributions = pickle.load(open(user_contributions_file, 'rb'))
    else:
        progress_file = Path(FILE_NAME.format("user_contributions_progress_" + str(page_count)))
        if progress_file.exists():
            page_gen, user_contributions = pickle.load(open(progress_file, 'rb'))
            print(len(page_gen), "pages remaining.")
        else:
            page_gen, user_contributions = list(map(lambda p: p.title(), get_rand_pages(page_count))), {}
        print("Processing these pages", page_gen)
        for page_title in page_gen:
            page = pwb.Page(pwb.Site(), page_title)
            print("Processing " + page.title())
            handle_page(page, user_contributions)
            page_gen.pop(0)
            pickle.dump((page_gen, user_contributions), open(progress_file, 'wb'))
        progress_file.unlink(missing_ok=True)
        pickle.dump(user_contributions, open(user_contributions_file, 'wb'))
    return user_contributions


def main():
    user_contributions = get_user_contributions(500)
    print(sorted(user_contributions.items(), key=lambda t: t[1], reverse=True))
    for right in special_user_groups:
        contributions[right] = 0
    handle_user_contributions(user_contributions)
    print(contributions)
    visualize(contributions)
    s = sum(contributions.values())
    common = contributions[special_user_groups[-1]] + contributions[special_user_groups[-2]]
    simplified = {'special': s - common,
                  'common': common}
    visualize(simplified)


if __name__ == "__main__":
    main()

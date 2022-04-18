import collections
import json
import urllib
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import requests
from matplotlib.patches import Wedge
from typing import List

namespace_dict = {
    0: "主", 1: "讨论",
    2: "用户", 3: "用户讨论",
    4: "萌娘百科", 5: "萌百讨论",
    6: "文件", 7: "文件讨论",
    8: "MW", 9: "MW讨论",
    10: "模板", 11: "模板讨论",
    12: "帮助", 13: "帮助讨论",
    14: "分类", 15: "分类讨论",
    274: "小部件", 275: "小部件讨论",
    828: "模块", 829: "模块讨论"
}


def get_contributions_on_mgp(user: str) -> list:
    url = "https://mzh.moegirl.org.cn/api.php?action=query&list=usercontribs&format=json" \
          "&ucuser={}&uclimit=500&ucprop=title".format(urllib.parse.quote(user))
    cont = ""
    result = []
    index = 1
    while True:
        cur = url + cont
        print("Fetching page", index)
        index += 1
        while True:
            try:
                response = json.loads(requests.get(cur).text)
                break
            except Exception as e:
                print(e, ", retrying...")
        if "query" not in response or 'usercontribs' not in response['query']:
            print("Something went wrong and no query response was received.")
            print(response)
            break
        result.extend(response['query']['usercontribs'])
        if "continue" not in response:
            break
        cont = "&uccontinue=" + response['continue']['uccontinue']
    return result


def get_contributions(username: str) -> list:
    path = Path("cache/{}.json".format(username))
    if not path.exists():
        contributions = get_contributions_on_mgp(username)
        path.touch(exist_ok=True)
        json.dump(contributions, open(path, "w"))
    else:
        contributions = json.load(open(path, "r"))
    return contributions


def process_contributions(username: str):
    Path("cache").mkdir(exist_ok=True)
    contributions = get_contributions(username)
    if len(contributions) == 0:
        print("用户无贡献")
        return
    counter = collections.Counter([namespace_dict.get(c['ns'], c['ns'])
                                   for c in contributions])
    t = sorted(list(counter.items()), key=lambda p: p[1], reverse=True)
    print(t)
    plot_contributions(t)


def plot_contributions(t: list):
    matplotlib.rcParams['font.family'] = "Heiti TC"
    matplotlib.rcParams['axes.unicode_minus'] = False

    namespaces, edits = zip(*t)
    plt.figure(1, [10, 6])
    patches: List[Wedge]
    patches, texts = plt.pie(edits, labels=namespaces)
    plt.legend(patches, [f"{p[0]}: {p[1]}" for p in t], loc='center right',
               bbox_to_anchor=(0, 0.5), fontsize=15)
    plt.savefig("cache/pie.png")
    plt.show()
    plt.figure(2, [len(namespaces), 6])
    bar_plot = plt.bar(namespaces, edits, color=[p.get_facecolor() for p in patches])
    plt.bar_label(bar_plot)
    plt.savefig("cache/bar.png")
    plt.show()


def main():
    username = input("Username?\n")
    process_contributions(username)


if __name__ == '__main__':
    main()

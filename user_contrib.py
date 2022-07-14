import collections
import json
import platform
import urllib
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import requests
from matplotlib.patches import Wedge
from typing import List, Callable, Any, Generator

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


def get_contributions_on_mgp(user: str, create_only: bool) -> list:
    url = "https://mzh.moegirl.org.cn/api.php?action=query" \
          "&list=usercontribs" \
          "&format=json" + ("&ucshow=new" if create_only else "") + \
          "&ucuser={}&uclimit=500&ucprop=title|tags|flags".format(urllib.parse.quote(user))
    # 一开始不需要uccontinue参数
    cont = ""
    # 用列表（数组）存储所有贡献
    contributions = []
    index = 1
    while True:
        # 默认url加上continue参数
        cur = url + cont
        print("Fetching page", index)
        index += 1
        # 重试直到成功
        while True:
            try:
                response = json.loads(requests.get(cur).text)
                break
            except Exception as e:
                print(e, ", retrying...")
        # 请求失败，json数据不包含query
        if "query" not in response or 'usercontribs' not in response['query']:
            print("Something went wrong and no query response was received.")
            print(response)
            break
        contributions.extend(response['query']['usercontribs'])
        # 如果api返回的数据中不含continue，表明所有贡献已获取完成
        if "continue" not in response:
            break
        # # 如果包含continue，继续获取贡献
        cont = "&uccontinue=" + response['continue']['uccontinue']
    return contributions


def get_contributions(username: str, create_only: bool = False) -> list:
    path = Path("cache/{}.json".format(username))
    # 缓存机制：将获取的贡献数据在本地存储
    # 如果没有本地数据，从萌百获取并写入文件系统
    if not path.exists():
        contributions = get_contributions_on_mgp(username, create_only)
        path.touch(exist_ok=True)
        json.dump(contributions, open(path, "w", encoding="utf-8"))
    else:  # 如果有本地数据，直接读取
        contributions = json.load(open(path, "r", encoding="utf-8"))
        print("Loading data from ", str(path))
    return contributions


def plot_pie(t: list, username: str):
    # 把名字空间和编辑次数放入两个不同的列表。
    namespaces, edits = zip(*t)
    plt.figure(figsize=[10, 6])
    patches: List[Wedge]
    patches, texts = plt.pie(edits, labels=namespaces)
    plt.legend(patches, [f"{p[0]}: {p[1]}" for p in t], loc='center right',
               bbox_to_anchor=(0, 0.5), fontsize=15)
    plt.title(f"用户 {username} 的贡献", fontsize=24)
    plt.savefig("cache/pie.png")
    return patches


def plot_bar(t: list, patches: list, username: str, y_label: str):
    plt.figure(figsize=[len(t), 6])
    namespaces, edits = zip(*t)
    bar_plot = plt.bar(x=namespaces, height=edits, color=[p.get_facecolor() for p in patches])
    plt.bar_label(bar_plot)
    plt.title(f"用户 {username} 的贡献", fontsize=24)
    plt.xlabel("名字空间")
    plt.ylabel(y_label)
    plt.savefig("cache/bar.png")


def init_plotting():
    # 部分操作系统中，matplotlib的默认字体不支持中文，因此需要手动指定字体。
    if "Windows" in platform.platform():
        matplotlib.rcParams['font.family'] = "Microsoft YaHei"
    else:
        matplotlib.rcParams['font.family'] = "Heiti TC"
    matplotlib.rcParams['axes.unicode_minus'] = False


def plot_contributions(t: list, username: str, y_label: str):
    # 第一张图：饼状图
    patches = plot_pie(t, username)
    # 第二张图：柱状图
    plot_bar(t, patches, username, y_label)


def filter_contributions(contributions: list, predicate: Callable[[Any], bool]) -> Generator:
    for c in contributions:
        if predicate(c):
            yield c


def count_contributions(contributions: list) -> list[tuple[str, int]]:
    # 获取每次编辑的名字空间，并将其转换为文字（如果namespace_dict没有对应的文字，则保留数字）。
    # 最后用Counter统计每个名字空间出现了多少次。
    counter = collections.Counter([namespace_dict.get(c['ns'], c['ns'])
                                   for c in contributions])
    # 按照编辑次数给所有名字空间排序
    return sorted(list(counter.items()), key=lambda p: p[1], reverse=True)


def process_contributions(username: str):
    # 创建缓存文件夹
    Path("cache").mkdir(exist_ok=True)
    # 获取贡献
    contributions = get_contributions(username)
    if len(contributions) == 0:
        print("用户无贡献")
        return
    print(len(contributions), "次编辑")
    t = count_contributions(contributions)
    # 输出数据
    print("\n".join([f"{p[0]}: {p[1]}" for p in t]))
    # 画图
    init_plotting()
    plot_contributions(t, username, "编辑数")
    page_creations = list(filter_contributions(contributions,
                                               lambda c: 'new' in c and "mw-new-redirect" not in c['tags']))
    t = count_contributions(page_creations)
    print("创建了", len(page_creations), "个页面")
    print("\n".join([f"{p[0]}: {p[1]}" for p in t]))
    plot_contributions(t, username, "创建页面数")
    plt.show()


def main():
    username = input("Username?\n")
    process_contributions(username)


if __name__ == '__main__':
    main()

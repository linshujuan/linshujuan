#!/usr/bin/env python3
"""抓取指定用户最近 star 的仓库，注入 README 的 RECENT_STARS 区块。

同时更新中文（README.md）与英文（README.en.md）两个文件，表头与时间
按各自语言本地化。仅使用 GitHub 公开接口 /users/{user}/starred，配合
Actions 内置的 GITHUB_TOKEN 即可（用于提高速率限制），无需任何 PAT。
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("STAR_USER", "linshujuan")
COUNT = int(os.environ.get("STAR_COUNT", "8"))
START = "<!-- RECENT_STARS:START -->"
END = "<!-- RECENT_STARS:END -->"

# 每个目标文件对应一种语言
TARGETS = [
    {"path": "README.md", "lang": "zh"},
    {"path": "README.en.md", "lang": "en"},
]

# 语言 -> 小色块 emoji，找不到就用 ⬜
LANG_DOT = {
    "JavaScript": "🟨", "TypeScript": "🟦", "Python": "🐍", "Vue": "🟩",
    "HTML": "🟧", "CSS": "🟪", "Go": "🩵", "Rust": "🦀", "Java": "☕",
    "C": "⬛", "C++": "🟦", "C#": "🟩", "Shell": "🐚", "Ruby": "🟥",
    "Kotlin": "🟪", "Swift": "🟧", "Dart": "🩵", "PHP": "🟦", "Jupyter Notebook": "🟧",
}

I18N = {
    "zh": {
        "header": "| 项目 | 语言 | 简介 | Star 于 |",
        "empty": "_最近还没有新的 star，去逛逛开源世界吧～_",
        "none_desc": "—",
    },
    "en": {
        "header": "| Repo | Language | Description | Starred |",
        "empty": "_No recent stars yet — time to explore some open source!_",
        "none_desc": "—",
    },
}


def api(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.star+json")
    req.add_header("User-Agent", f"{USER}-profile-bot")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def humanize(iso, lang):
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - dt).days
    if lang == "en":
        if days <= 0:
            return "today"
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days} days ago"
        if days < 365:
            return f"{days // 30} mo ago"
        return f"{days // 365} yr ago"
    # zh
    if days <= 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days < 30:
        return f"{days} 天前"
    if days < 365:
        return f"{days // 30} 个月前"
    return f"{days // 365} 年前"


def truncate(text, n=70):
    text = (text or "").strip().replace("\r", " ").replace("\n", " ").replace("|", "·")
    return text if len(text) <= n else text[: n - 1] + "…"


def build_table(items, lang):
    t = I18N[lang]
    rows = [t["header"], "| :-- | :-- | :-- | :-- |"]
    for it in items:
        repo = it["repo"]
        name = repo["full_name"]
        url = repo["html_url"]
        lang_name = repo.get("language")
        dot = LANG_DOT.get(lang_name, "⬜")
        lang_txt = f"{dot} {lang_name}" if lang_name else "⬜ —"
        desc = truncate(repo.get("description")) or t["none_desc"]
        when = humanize(it.get("starred_at"), lang)
        rows.append(f"| **[{name}]({url})** | {lang_txt} | {desc} | {when} |")
    return "\n".join(rows)


def inject(path, block):
    if not os.path.exists(path):
        print(f"跳过（不存在）：{path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(content):
        print(f"WARN: {path} 中未找到 RECENT_STARS 标记，跳过", file=sys.stderr)
        return False
    updated = pattern.sub(f"{START}\n{block}\n{END}", content)
    if updated == content:
        print(f"{path} 无变化")
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"已更新 {path}")
    return True


def main():
    url = f"https://api.github.com/users/{USER}/starred?per_page={COUNT}&sort=created&direction=desc"
    items = api(url)
    items = items[:COUNT] if isinstance(items, list) else []
    changed = False
    for tgt in TARGETS:
        lang = tgt["lang"]
        block = build_table(items, lang) if items else I18N[lang]["empty"]
        if inject(tgt["path"], block):
            changed = True
    if not changed:
        print("所有文件均无变化")


if __name__ == "__main__":
    main()

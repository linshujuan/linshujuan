#!/usr/bin/env python3
"""抓取指定用户最近 star 的仓库，注入 README.md 的 RECENT_STARS 区块。

仅使用 GitHub 公开接口 /users/{user}/starred，配合 Actions 内置的
GITHUB_TOKEN 即可（用于提高速率限制），无需任何手动配置的 PAT。
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("STAR_USER", "linshujuan")
COUNT = int(os.environ.get("STAR_COUNT", "8"))
README = os.environ.get("README_PATH", "README.md")
START = "<!-- RECENT_STARS:START -->"
END = "<!-- RECENT_STARS:END -->"

# 语言 -> 小色块 emoji，找不到就用 ⬜
LANG_DOT = {
    "JavaScript": "🟨", "TypeScript": "🟦", "Python": "🐍", "Vue": "🟩",
    "HTML": "🟧", "CSS": "🟪", "Go": "🩵", "Rust": "🦀", "Java": "☕",
    "C": "⬛", "C++": "🟦", "C#": "🟩", "Shell": "🐚", "Ruby": "🟥",
    "Kotlin": "🟪", "Swift": "🟧", "Dart": "🩵", "PHP": "🟦", "Jupyter Notebook": "🟧",
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


def humanize(iso):
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - dt).days
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
    if not text:
        return "—"
    return text if len(text) <= n else text[: n - 1] + "…"


def build_table(items):
    rows = [
        "| 项目 | 语言 | 简介 | Star 于 |",
        "| :-- | :-- | :-- | :-- |",
    ]
    for it in items:
        repo = it["repo"]
        name = repo["full_name"]
        url = repo["html_url"]
        lang = repo.get("language")
        dot = LANG_DOT.get(lang, "⬜")
        lang_txt = f"{dot} {lang}" if lang else "⬜ —"
        desc = truncate(repo.get("description"))
        when = humanize(it.get("starred_at"))
        rows.append(f"| **[{name}]({url})** | {lang_txt} | {desc} | {when} |")
    return "\n".join(rows)


def main():
    url = f"https://api.github.com/users/{USER}/starred?per_page={COUNT}&sort=created&direction=desc"
    items = api(url)
    if not isinstance(items, list) or not items:
        block = "_最近还没有新的 star，去逛逛开源世界吧～_"
    else:
        block = build_table(items[:COUNT])

    with open(README, "r", encoding="utf-8") as f:
        content = f.read()

    new_section = f"{START}\n{block}\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(content):
        print("ERROR: 未在 README 中找到 RECENT_STARS 标记", file=sys.stderr)
        sys.exit(1)
    updated = pattern.sub(new_section, content)

    if updated == content:
        print("README 无变化")
        return
    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"已更新 {len(items[:COUNT])} 个 star")


if __name__ == "__main__":
    main()

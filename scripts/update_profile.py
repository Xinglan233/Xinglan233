#!/usr/bin/env python3
"""Render one coordinated GitHub profile panel using Python's standard library.

Live mode is intended for the profile repository's automatic GITHUB_TOKEN.
No API token, raw API response, private repository name or source code is saved.
The grade formula is adapted from github-readme-stats; see THIRD_PARTY_LICENSES.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- PROFILE:START -->', '<!-- PROFILE:END -->'
PALETTES = {
    False: {'bg': '#f6f7f9', 'text': '#1d1d1f', 'muted': '#62666d',
            'line': '#dfe2e7', 'track': '#e0e4ea', 'accent': '#0969da',
            'series': ['#2463a8', '#5086b9', '#759fbd', '#91adb9', '#b0bfc9', '#d1d8df']},
    True: {'bg': '#161b22', 'text': '#f0f3f6', 'muted': '#a4acb7',
           'line': '#30363d', 'track': '#303a47', 'accent': '#79b8ff',
           'series': ['#79b8ff', '#699cc9', '#7b9fb4', '#899fa7', '#a0afb5', '#c0c9d0']},
}
REPO_FIELDS = '''repositories(first:100, after:$after, ownerAffiliations:[OWNER],
  privacy:PUBLIC, isFork:false, orderBy:{field:NAME,direction:ASC}) {
  nodes {
    name isPrivate isFork isArchived stargazerCount owner { login }
    languages(first:100, orderBy:{field:SIZE,direction:DESC}) {
      edges { size node { name } } pageInfo { hasNextPage }
    }
  }
  pageInfo { hasNextPage endCursor }
}'''
INITIAL_QUERY = '''query($login:String!, $after:String, $from:DateTime!, $to:DateTime!,
  $prQuery:String!, $issueQuery:String!) {
  user(login:$login) {
    login followers { totalCount }
    contributionsCollection(from:$from,to:$to) {
      totalCommitContributions totalPullRequestReviewContributions
    }
    ''' + REPO_FIELDS + '''
  }
  prs: search(query:$prQuery,type:ISSUE,first:1) { issueCount }
  issues: search(query:$issueQuery,type:ISSUE,first:1) { issueCount }
}'''
PAGE_QUERY = 'query($login:String!, $after:String) { user(login:$login) { ' + REPO_FIELDS + ' } }'


def calculate_rank(commits: int, prs: int, issues: int, reviews: int,
                   stars: int, followers: int) -> tuple[str, float]:
    """GRS's default annual-commit formula; a heuristic, not a measured global rank."""
    values = (commits, prs, issues, reviews, stars, followers)
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Rank inputs must be finite, nonnegative numbers.')
    medians, weights = (250, 50, 25, 2, 50, 10), (2, 3, 1, 1, 4, 1)
    scores = [1 - 2 ** (-v / m) if i < 4 else (v / m) / (1 + v / m)
              for i, (v, m) in enumerate(zip(values, medians))]
    percentile = max(0.0, min(100.0, 100 * (1 - sum(w * s for w, s in zip(weights, scores)) / 12)))
    for threshold, level in zip((1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100),
                                ('S', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C')):
        if percentile <= threshold:
            return level, percentile
    raise AssertionError('Unreachable rank threshold.')


def graphql(query: str, variables: dict, token: str) -> dict:
    """Fetch from GitHub only; fail on partial GraphQL responses instead of displaying zero."""
    payload = json.dumps({'query': query, 'variables': variables}).encode('utf-8')
    for attempt in range(3):
        req = urllib.request.Request('https://api.github.com/graphql', data=payload, headers={
            'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
            'Accept': 'application/vnd.github+json', 'User-Agent': 'Xinglan233-profile',
        })
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                result = json.load(response)
            if result.get('errors') or not result.get('data'):
                # Avoid putting raw response contents or credentials in logs.
                raise RuntimeError('GitHub GraphQL returned errors or incomplete data; previous assets kept.')
            return result['data']
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f'GitHub HTTP {error.code}; previous assets kept.') from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 2:
                raise RuntimeError('Could not obtain valid GitHub data; previous assets kept.') from None
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError('GitHub data request failed.')


def aggregate_repositories(repositories: list[dict], username: str) -> dict:
    """Public, owned, nonfork repos; profile repo excluded to avoid stats-code feedback."""
    stars, languages = 0, {}
    for repo in repositories:
        if (not repo or repo['isPrivate'] or repo['isFork'] or
            repo['owner']['login'].lower() != username.lower() or
            repo['name'].lower() == username.lower()):
            continue
        stars += int(repo['stargazerCount'])
        if repo['isArchived']:
            continue
        if repo['languages']['pageInfo']['hasNextPage']:
            raise ValueError('A repository has more than 100 languages; refusing a truncated language chart.')
        for edge in repo['languages']['edges']:
            name, size = edge['node']['name'], int(edge['size'])
            if size > 0:
                languages[name] = languages.get(name, 0) + size
    return {'stars': stars, 'languages': languages}


def fetch_stats(username: str, token: str) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username):
        raise ValueError('Invalid GitHub username.')
    now = datetime.now(timezone.utc)
    variables = {'login': username, 'after': None,
                 'from': f'{now.year}-01-01T00:00:00Z', 'to': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'prQuery': f'author:{username} is:pr is:public',
                 'issueQuery': f'author:{username} is:issue is:public'}
    data = graphql(INITIAL_QUERY, variables, token)
    user = data.get('user')
    if not user:
        raise ValueError('The requested GitHub user was not found.')
    stats = {'commits': int(user['contributionsCollection']['totalCommitContributions']),
             'reviews': int(user['contributionsCollection']['totalPullRequestReviewContributions']),
             'followers': int(user['followers']['totalCount']),
             'prs': int(data['prs']['issueCount']), 'issues': int(data['issues']['issueCount']),
             'date': now.date().isoformat(), 'year': now.year}
    repositories, seen_cursors = [], set()
    connection = user['repositories']
    while True:
        repositories.extend(connection['nodes'])
        page = connection['pageInfo']
        if not page['hasNextPage']:
            break
        cursor = page['endCursor']
        if not cursor or cursor in seen_cursors:
            raise RuntimeError('Invalid GitHub pagination; refusing partial statistics.')
        seen_cursors.add(cursor)
        data = graphql(PAGE_QUERY, {'login': username, 'after': cursor}, token)
        connection = data['user']['repositories']
    stats.update(aggregate_repositories(repositories, username))
    return stats


def language_rows(languages: dict[str, int]) -> list[dict]:
    items = sorted(((name, count) for name, count in languages.items() if count > 0),
                   key=lambda item: (-item[1], item[0]))
    total = sum(size for _, size in items)
    if not total:
        return []
    visible = items[:5]
    if len(items) > 5:
        visible.append(('Other', sum(size for _, size in items[5:])))
    raw = [size / total * 1000 for _, size in visible]
    tenths = [math.floor(number) for number in raw]
    for i in sorted(range(len(raw)), key=lambda i: (-(raw[i] - tenths[i]), i))[:1000 - sum(tenths)]:
        tenths[i] += 1
    return [{'name': name, 'bytes': size, 'tenths': tenth}
            for (name, size), tenth in zip(visible, tenths)]


def short_number(value: int | None) -> str:
    if value is None:
        return '—'
    if value >= 1_000_000:
        return f'{value / 1_000_000:.1f}m'
    if value >= 10_000:
        return f'{value / 1000:.1f}k'
    return f'{value:,}'


def render_svg(stats: dict | None, *, dark: bool, mobile: bool) -> str:
    p = PALETTES[dark]
    width, height = (400, 468) if mobile else (800, 332)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
           '<title id="title">GitHub activity and language distribution</title>',
           '<desc id="description">Public GitHub statistics. Rank uses the GitHub Readme Stats formula; languages are source-code byte shares, not proficiency. Exact figures appear in the README text table.</desc>',
           f'<rect x="0" y="0" width="{width}" height="{height}" rx="18" fill="{p["bg"]}"/>',
           '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">']

    def text(x, y, value, size=14, weight=400, muted=False, anchor='start', color=None):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                   f'fill="{color or p["muted" if muted else "text"]}" text-anchor="{anchor}">{escape(str(value))}</text>')

    def line(x1, y1, x2, y2):
        out.append(f'<path d="M{x1} {y1}H{x2}" stroke="{p["line"]}"/>' if y1 == y2 else
                   f'<path d="M{x1} {y1}V{y2}" stroke="{p["line"]}"/>')

    pad = 24 if mobile else 28
    text(pad, 32 if mobile else 35, 'GitHub activity', 16, 600)
    updated = f'Updated {stats["date"]} · UTC' if stats else 'Awaiting first sync'
    text(pad if mobile else 772, 55 if mobile else 35, updated, 11, muted=True,
         anchor='start' if mobile else 'end')
    coordinates = [(pad, 111), (146 if mobile else 180, 111),
                   (pad, 196), (146 if mobile else 180, 196)]
    labels = [('commits', f'Commits · {stats["year"]}' if stats else 'Commits · this year'),
              ('stars', 'Stars received'), ('prs', 'Pull requests'), ('issues', 'Issues opened')]
    for (x, y), (key, label) in zip(coordinates, labels):
        text(x, y, short_number(stats[key] if stats else None), 31 if mobile else 36, 600)
        text(x, y + 24, label, 11 if mobile else 12, muted=True)
    cx, cy, radius = (328, 147, 35) if mobile else (352, 147, 43)
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{p["track"]}" stroke-width="4"/>')
    grade = '—'
    if stats is not None:
        grade, percentile = calculate_rank(*(stats[key] for key in ('commits','prs','issues','reviews','stars','followers')))
        circumference = 2 * math.pi * radius
        length = circumference * (100 - percentile) / 100
        if length > 0:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{p["accent"]}" stroke-width="4" stroke-linecap="round" stroke-dasharray="{length:.3f} {circumference:.3f}" transform="rotate(-90 {cx} {cy})"/>')
    text(cx, cy + 10, grade, 27, 600, anchor='middle')
    text(cx, 219 if mobile else 219, 'GRS rank', 11, muted=True, anchor='middle')
    if mobile:
        line(24, 247, 376, 247)
        text(24, 283, 'Languages', 16, 600)
        bx, by, bw = 24, 300, 352
    else:
        line(420, 70, 420, 276)
        text(452, 83, 'Languages', 16, 600)
        bx, by, bw = 452, 102, 320
    rows = language_rows(stats['languages']) if stats else []
    out.append(f'<defs><clipPath id="language-bar"><rect x="{bx}" y="{by}" width="{bw}" height="8" rx="4"/></clipPath></defs>')
    out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="8" rx="4" fill="{p["track"]}"/>')
    if rows:
        cursor = bx
        total_bytes = sum(row['bytes'] for row in rows)
        for i, row in enumerate(rows):
            segment = bw * row['bytes'] / total_bytes
            color = p['series'][i]
            out.append(f'<rect x="{cursor:.3f}" y="{by}" width="{segment:.3f}" height="8" fill="{color}" clip-path="url(#language-bar)"/>')
            cursor += segment
            if mobile:
                x, y = (24 if i % 2 == 0 else 212), 344 + (i // 2) * 35
                right = 188 if i % 2 == 0 else 376
                max_name = 13
            else:
                x, y, right, max_name = 452, 145 + i * 25, 772, 30
            out.append(f'<circle cx="{x + 3}" cy="{y - 5}" r="3" fill="{color}"/>')
            name = row['name'] if len(row['name']) <= max_name else row['name'][:max_name - 1] + '…'
            label_width = right - (x + 14) - 52
            out.append(f'<defs><clipPath id="language-label-{i}"><rect x="{x + 14}" y="{y - 17}" width="{label_width}" height="23"/></clipPath></defs>')
            out.append(f'<g clip-path="url(#language-label-{i})">')
            text(x + 14, y, name, 12 if mobile else 13)
            out.append('</g>')
            text(right, y, f'{row["tenths"] / 10:.1f}%', 12 if mobile else 13, muted=True, anchor='end')
    else:
        text(bx, 352 if mobile else 160, 'No language data yet', 13, muted=True)
        text(bx, 377 if mobile else 185, 'Updated after the first sync.' if stats is None else 'No eligible source files found.', 11, muted=True)
    text(pad, 448 if mobile else 311, 'Public code · language share by bytes', 11, muted=True)
    out.extend(['</g>', '</svg>'])
    result = '\n'.join(out) + '\n'
    ET.fromstring(result)
    return result


def render_details(stats: dict | None) -> str:
    if stats is None:
        return '<details>\n<summary>统计口径</summary>\n\n首次运行 Actions 后填入真实数据；当前的「—」不是零分。\n\n语言占比按代码字节统计，不代表熟练度。评分采用 GitHub Readme Stats 公式，不是 GitHub 官方能力评分。\n\n</details>'
    grade, _ = calculate_rank(*(stats[key] for key in ('commits','prs','issues','reviews','stars','followers')))
    rows = ['<details>', '<summary>统计明细与口径</summary>', '',
            f'数据日期：{stats["date"]}（UTC）。', '', '| 指标 | 数值 |', '| --- | ---: |',
            f'| {stats["year"]} 年提交 | {stats["commits"]:,} |',
            f'| 收到的 Star | {stats["stars"]:,} |', f'| 公开 Pull requests | {stats["prs"]:,} |',
            f'| 公开 Issues | {stats["issues"]:,} |', f'| {stats["year"]} 年评审贡献 | {stats["reviews"]:,} |',
            f'| Followers | {stats["followers"]:,} |', f'| GRS 活动评级 | {grade} |', '',
            '| 语言 | 代码占比 |', '| --- | ---: |']
    for item in language_rows(stats['languages']):
        name = escape(item['name']).replace('|', '&#124;').replace('\n', ' ')
        rows.append(f'| {name} | {item["tenths"] / 10:.1f}% |')
    rows.extend(['', '语言按本人公开、非 fork、未归档仓库的代码字节统计，排除同名主页仓库。',
                 'Star 汇总保留归档仓库；提交和评审按当年统计，PR、Issue、Star 为累计值。',
                 'GRS 采用 GitHub Readme Stats 的活动评级公式，不是 GitHub 官方评分，也不代表技术水平或实测全球排名。',
                 '原生贡献图还会计入其他类型的贡献，不能把绿点总数直接当成 commit 数。', '', '</details>'])
    return '\n'.join(rows)


def replace_details(readme: str, details: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) >= readme.index(END):
        raise ValueError('README must contain exactly one ordered PROFILE marker pair.')
    return readme[:readme.index(START) + len(START)] + '\n' + details + '\n' + readme[readme.index(END):]


def asset_texts(stats: dict | None) -> dict[str, str]:
    return {f'activity-{theme}{"-mobile" if mobile else ""}.svg':
            render_svg(stats, dark=(theme == 'dark'), mobile=mobile)
            for theme in ('light', 'dark') for mobile in (False, True)}


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as temp:
        name = temp.name
        temp.write(content)
    try:
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_assets(directory: Path, stats: dict | None) -> None:
    texts = asset_texts(stats)  # Finish and validate every SVG before touching existing assets.
    for name, content in texts.items():
        atomic_write(directory / name, content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='Xinglan233')
    parser.add_argument('--init', action='store_true', help='Create honest empty-state SVGs without an API request.')
    parser.add_argument('--output', type=Path, default=ROOT / 'assets')
    parser.add_argument('--readme', type=Path, default=ROOT / 'README.md')
    args = parser.parse_args()
    try:
        token = os.environ.get('GITHUB_TOKEN', '')
        if not args.init and not token:
            raise ValueError('GITHUB_TOKEN is missing. Use the supplied GitHub Actions workflow; do not paste a token into README.')
        stats = None if args.init else fetch_stats(args.username, token)
        # Validate the full publication before writing; a failed API request never erases old data.
        texts = asset_texts(stats)
        readme = replace_details(args.readme.read_text(encoding='utf-8'), render_details(stats))
        for name, content in texts.items():
            atomic_write(args.output / name, content)
        atomic_write(args.readme, readme)
        print('Prepared four theme/layout variants and the accessible text summary.')
        return 0
    except (ValueError, RuntimeError, KeyError, TypeError, OSError) as error:
        print(f'Profile update failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

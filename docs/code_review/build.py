#!/usr/bin/env python3
"""CODE_REVIEW_REPORT.md → index.html 변환기.

사용법:  python3 docs/code_review/build.py
결과:    docs/code_review/index.html, docs/code_review/report.md (원본 복사)
"""
import html
import re
import shutil
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / 'CODE_REVIEW_REPORT.md'
OUT = HERE / 'index.html'

SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low']
SEVERITY_SUB = {
    'Critical': '관측 중단·무한 대기·장비 오판·설정 손실·자격증명 노출',
    'High': '특정 조건에서 확실히 오동작하거나 자원을 크게 낭비',
    'Medium': '잠재 버그, 조용히 기록되는 잘못된 결과, 유지보수 위험',
    'Low': '저장소 정리, 스타일, 죽은 코드',
}
FIELD_CLASS = {
    '파일': 'files', '파일/위치': 'files',
    '위치·의도': 'intent',
    '문제 요소': 'risk', '추가 문제': 'risk',
    '개선 제안': 'fix',
}
ID_RE = re.compile(r'(?<![\w/])([A-D]\d{1,2})(?![\w])')


# ---------- inline markdown ----------
def _plain(seg: str) -> str:
    seg = html.escape(seg, quote=False)
    seg = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', seg)
    seg = ID_RE.sub(r'<a class="xref" href="#\1">\1</a>', seg)
    return seg


def inline(s: str, autolink: bool = True) -> str:
    parts = re.split(r'(`[^`]+`)', s)
    out = []
    for p in parts:
        if p.startswith('`') and p.endswith('`') and len(p) > 1:
            out.append('<code>' + html.escape(p[1:-1], quote=False) + '</code>')
        else:
            out.append(_plain(p) if autolink else re.sub(
                r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html.escape(p, quote=False)))
    return ''.join(out)


# ---------- block markdown (prose sections) ----------
LIST_RE = re.compile(r'^(\s*)([-*]|\d+\.) (.*)$')


def render_table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    head, body = cells[0], [r for r in cells[2:]]
    h = ['<div class="tablewrap"><table><thead><tr>']
    h += [f'<th>{inline(c)}</th>' for c in head]
    h.append('</tr></thead><tbody>')
    for r in body:
        h.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
    h.append('</tbody></table></div>')
    return ''.join(h)


def render_list(block):
    items = []
    for ln in block:
        m = LIST_RE.match(ln)
        if m:
            items.append([len(m.group(1)), m.group(2)[0].isdigit(), m.group(3)])
        elif items:
            items[-1][2] += ' ' + ln.strip()

    def build(start, indent):
        tag = 'ol' if items[start][1] else 'ul'
        parts = [f'<{tag}>']
        i = start
        while i < len(items) and items[i][0] >= indent:
            if items[i][0] > indent:
                break
            parts.append(f'<li>{inline(items[i][2])}')
            if i + 1 < len(items) and items[i + 1][0] > indent:
                sub, i = build(i + 1, items[i + 1][0])
                parts.append(sub)
            else:
                i += 1
            parts.append('</li>')
        parts.append(f'</{tag}>')
        return ''.join(parts), i

    out, _ = build(0, items[0][0])
    return out


def render_blocks(lines):
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            out.append(render_table(rows))
            continue
        if re.match(r'^-{3,}$', ln.strip()):
            out.append('<hr>')
            i += 1
            continue
        m = re.match(r'^(#{3,4}) (.*)', ln)
        if m:
            lvl = len(m.group(1))
            out.append(f'<h{lvl}>{inline(m.group(2))}</h{lvl}>')
            i += 1
            continue
        if LIST_RE.match(ln):
            block = []
            while i < len(lines) and (LIST_RE.match(lines[i]) or (lines[i].startswith('  ') and lines[i].strip())):
                block.append(lines[i])
                i += 1
            out.append(render_list(block))
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('|') \
                and not LIST_RE.match(lines[i]) and not lines[i].startswith('#'):
            para.append(lines[i].strip())
            i += 1
        out.append(f'<p>{inline(" ".join(para))}</p>')
    return '\n'.join(out)


# ---------- findings ----------
def parse_findings(lines):
    items, cur = [], None
    for ln in lines:
        m = re.match(r'^### ([A-D]\d+)\. (.*)$', ln)
        if m:
            cur = {'id': m.group(1), 'title': m.group(2), 'fields': [], 'body': []}
            items.append(cur)
            continue
        if cur is None or not ln.strip():
            continue
        m = re.match(r'^- \*\*(.+?)\*\*:\s*(.*)$', ln)
        if m:
            cur['fields'].append({'label': m.group(1), 'text': m.group(2), 'items': []})
            continue
        m = re.match(r'^  - (.*)$', ln)
        if m:
            (cur['fields'][-1]['items'] if cur['fields'] else cur['body']).append(m.group(1))
            continue
        m = re.match(r'^- (.*)$', ln)
        if m:
            cur['body'].append(m.group(1))
            continue
        if cur['fields']:
            cur['fields'][-1]['text'] += ' ' + ln.strip()
        else:
            cur['body'].append(ln.strip())
    for it in items:
        cats = []
        for f in it['fields']:
            if f['label'] == '분류':
                cats = [c.strip() for c in re.split(r'\s*/\s*', f['text']) if c.strip()]
        it['categories'] = cats
        it['fields'] = [f for f in it['fields'] if f['label'] != '분류']
    return items


def render_finding(it, severity):
    sev = severity.lower()
    cats = ''.join(f'<span class="chip cat" data-cat="{html.escape(c)}">{html.escape(c)}</span>' for c in it['categories'])
    rows = []
    if it['body']:
        rows.append('<div class="row"><div class="k">내용</div><div class="v">'
                    + ''.join(f'<p>{inline(b)}</p>' for b in it['body']) + '</div></div>')
    for f in it['fields']:
        cls = FIELD_CLASS.get(f['label'], 'other')
        v = f'<p>{inline(f["text"])}</p>' if f['text'] else ''
        if f['items']:
            v += '<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in f['items']) + '</ul>'
        rows.append(f'<div class="row {cls}"><div class="k">{html.escape(f["label"])}</div><div class="v">{v}</div></div>')
    cat_attr = html.escape('|'.join(it['categories']))
    return (
        f'<details class="finding" id="{it["id"]}" data-sev="{severity}" data-cats="{cat_attr}" open>'
        f'<summary><span class="fid sev-{sev}">{it["id"]}</span>'
        f'<span class="ftitle">{inline(it["title"], autolink=False)}</span>'
        f'<span class="chips"><span class="chip sev sev-{sev}">{severity}</span>{cats}</span></summary>'
        f'<div class="fbody">{"".join(rows)}</div></details>'
    )


# ---------- document ----------
def split_sections(text):
    lines = text.split('\n')
    pre, sections, cur = [], [], None
    for ln in lines:
        m = re.match(r'^## (.*)$', ln)
        if m:
            cur = {'title': m.group(1), 'lines': []}
            sections.append(cur)
        elif cur is None:
            pre.append(ln)
        else:
            cur['lines'].append(ln)
    return pre, sections


def main():
    text = SRC.read_text(encoding='utf-8')
    pre, sections = split_sections(text)

    meta = [ln[2:] for ln in pre if ln.startswith('- ')]
    date = next((m.split(':', 1)[1].strip() for m in meta if m.startswith('작성일')), '')

    prose, findings = [], {}
    for s in sections:
        num = s['title'].split('.')[0].strip()
        sev = next((sv for sv in SEVERITY_ORDER if s['title'].split('.', 1)[1].strip().startswith(sv)), None)
        if sev:
            findings[sev] = parse_findings(s['lines'])
        else:
            prose.append((num, s['title'].split('.', 1)[1].strip(), render_blocks(s['lines'])))

    all_items = [(sev, it) for sev in SEVERITY_ORDER for it in findings.get(sev, [])]
    counts = {sev: len(findings.get(sev, [])) for sev in SEVERITY_ORDER}
    total = sum(counts.values())
    cats = sorted({c for _, it in all_items for c in it['categories']})

    # sidebar
    toc_prose = ''.join(f'<a href="#sec-{n}">{html.escape(t)}</a>' for n, t, _ in prose)
    toc_sev = ''
    for sev in SEVERITY_ORDER:
        ids = ''.join(f'<a class="idchip sev-{sev.lower()}" href="#{it["id"]}">{it["id"]}</a>' for it in findings.get(sev, []))
        toc_sev += (f'<div class="tocsev"><a class="toclink" href="#sev-{sev}">{sev}'
                    f'<span class="cnt">{counts[sev]}</span></a><div class="idrow">{ids}</div></div>')
    sev_filters = ''.join(
        f'<label class="sevopt"><input type="checkbox" id="sev-{sev}-cb" data-sev="{sev}" checked>'
        f'<span class="dot sev-{sev.lower()}"></span>{sev}<span class="cnt">{counts[sev]}</span></label>'
        for sev in SEVERITY_ORDER)
    cat_filters = ''.join(
        f'<button type="button" class="catbtn" id="cat-{re.sub(r"[^A-Za-z]", "", c)}" data-cat="{html.escape(c)}" aria-pressed="false">{html.escape(c)}</button>'
        for c in cats)

    # main
    header_counts = ''.join(
        f'<a class="sevcount sev-{sev.lower()}" href="#sev-{sev}"><b>{counts[sev]}</b><span>{sev}</span></a>'
        for sev in SEVERITY_ORDER)
    prose_html = ''
    for n, t, body in prose:
        if n == '6':
            continue
        prose_html += f'<section class="prose" id="sec-{n}"><h2><span class="num">{n}</span>{html.escape(t)}</h2>{body}</section>'
    sev_html = ''
    for sev in SEVERITY_ORDER:
        cards = ''.join(render_finding(it, sev) for it in findings.get(sev, []))
        sev_html += (f'<section class="sevsec" id="sev-{sev}" data-sev="{sev}">'
                     f'<h2><span class="sevmark sev-{sev.lower()}"></span>{sev}'
                     f'<span class="secmeta"><span class="shown">{counts[sev]}</span> / {counts[sev]}건</span></h2>'
                     f'<p class="sevsub">{SEVERITY_SUB[sev]}</p>{cards}</section>')
    tail_html = ''
    for n, t, body in prose:
        if n == '6':
            tail_html = f'<section class="prose" id="sec-{n}"><h2><span class="num">{n}</span>{html.escape(t)}</h2>{body}</section>'

    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    meta_html = ''.join(f'<li>{inline(m)}</li>' for m in meta)

    page = TEMPLATE
    for k, v in {
        '{{DATE}}': html.escape(date), '{{TOTAL}}': str(total), '{{META}}': meta_html,
        '{{HEADER_COUNTS}}': header_counts, '{{TOC_PROSE}}': toc_prose, '{{TOC_SEV}}': toc_sev,
        '{{SEV_FILTERS}}': sev_filters, '{{CAT_FILTERS}}': cat_filters,
        '{{PROSE}}': prose_html, '{{SEVERITY_SECTIONS}}': sev_html, '{{TAIL}}': tail_html,
        '{{BUILT}}': built,
    }.items():
        page = page.replace(k, v)
    OUT.write_text(page, encoding='utf-8')
    shutil.copy(SRC, HERE / 'report.md')
    print(f'{OUT}  findings={total}  ' + ' '.join(f'{k}={v}' for k, v in counts.items()))


TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>TCSpy 코드 리뷰</title>
<style>
:root{
  --bg:#f3f5f8; --surface:#ffffff; --surface-2:#eaeef3; --text:#1a2231; --muted:#5b6676;
  --border:#d9dfe7; --accent:#2c5f8a; --accent-ink:#ffffff; --code-bg:#eef2f6; --code-ink:#243447;
  --sev-critical:#b42318; --sev-critical-bg:#fbe9e7;
  --sev-high:#c4621a;     --sev-high-bg:#fdf0e4;
  --sev-medium:#9a7b0a;   --sev-medium-bg:#fbf5dc;
  --sev-low:#3b7a57;      --sev-low-bg:#e6f3ea;
  --shadow:0 1px 2px rgba(20,30,45,.06), 0 6px 20px -12px rgba(20,30,45,.25);
  color-scheme:light;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#12161c; --surface:#1a2028; --surface-2:#222a34; --text:#e5e9ef; --muted:#96a1b1;
    --border:#2c3540; --accent:#7fb0da; --accent-ink:#0f1720; --code-bg:#242d38; --code-ink:#d6e2f0;
    --sev-critical:#f28b82; --sev-critical-bg:#3a1f1c;
    --sev-high:#f0a35a;     --sev-high-bg:#3a2a18;
    --sev-medium:#e2c34a;   --sev-medium-bg:#35301a;
    --sev-low:#7fc49a;      --sev-low-bg:#1e332a;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 6px 20px -12px rgba(0,0,0,.6);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#12161c; --surface:#1a2028; --surface-2:#222a34; --text:#e5e9ef; --muted:#96a1b1;
  --border:#2c3540; --accent:#7fb0da; --accent-ink:#0f1720; --code-bg:#242d38; --code-ink:#d6e2f0;
  --sev-critical:#f28b82; --sev-critical-bg:#3a1f1c;
  --sev-high:#f0a35a;     --sev-high-bg:#3a2a18;
  --sev-medium:#e2c34a;   --sev-medium-bg:#35301a;
  --sev-low:#7fc49a;      --sev-low-bg:#1e332a;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 6px 20px -12px rgba(0,0,0,.6);
  color-scheme:dark;
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:var(--bg); color:var(--text);
  font-family:"Pretendard Variable",Pretendard,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.6; -webkit-font-smoothing:antialiased;
  padding-inline:16px; padding-block:0 48px;
}
code{
  font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,"Noto Sans Mono CJK KR",monospace;
  font-size:.86em; background:var(--code-bg); color:var(--code-ink); padding:.08em .38em; border-radius:4px;
  word-break:break-all;
}
a{color:var(--accent)}
a.xref{font-weight:600; text-decoration:none; border-bottom:1px dotted var(--accent)}
h1,h2,h3{text-wrap:balance; line-height:1.3; margin:0}
.wrap{max-width:1240px; margin-inline:auto}

/* header */
.top{display:flex; flex-wrap:wrap; gap:18px 32px; align-items:flex-end; justify-content:space-between; padding-block:36px 20px; border-bottom:1px solid var(--border)}
.eyebrow{font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); font-weight:600}
h1{font-size:30px; font-weight:750; letter-spacing:-.01em; margin-top:4px}
.top .meta{color:var(--muted); font-size:13.5px; margin:10px 0 0; padding:0; list-style:none; display:grid; gap:2px; max-width:70ch}
.top .meta code{font-size:.9em}
.counts{display:flex; gap:10px; flex-wrap:wrap}
.sevcount{display:flex; flex-direction:column; align-items:flex-start; min-width:92px; padding:10px 14px; border-radius:8px; text-decoration:none; color:var(--text); background:var(--surface); border:1px solid var(--border); border-left:4px solid currentColor}
.sevcount b{font-size:24px; font-weight:750; font-variant-numeric:tabular-nums; line-height:1.1}
.sevcount span{font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); font-weight:600}
.sevcount.sev-critical{color:var(--sev-critical)} .sevcount.sev-high{color:var(--sev-high)}
.sevcount.sev-medium{color:var(--sev-medium)} .sevcount.sev-low{color:var(--sev-low)}

/* layout */
.grid{display:grid; grid-template-columns:272px minmax(0,1fr); gap:32px; align-items:start; padding-top:24px}
aside{position:sticky; top:env(safe-area-inset-top,0px); max-height:calc(100vh - env(safe-area-inset-top,0px)); overflow:auto; padding-block:8px 24px; font-size:13.5px}
aside .box{display:grid; gap:8px; padding:12px 0 16px; border-bottom:1px solid var(--border)}
aside .box:last-child{border-bottom:0}
aside .label{font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); font-weight:700}
aside a{text-decoration:none; color:var(--text)}
aside a:hover{color:var(--accent)}
.toclink{display:flex; justify-content:space-between; align-items:center; font-weight:600; padding:2px 0}
.cnt{font-variant-numeric:tabular-nums; color:var(--muted); font-weight:600; font-size:12px; margin-left:8px}
.idrow{display:flex; flex-wrap:wrap; gap:4px; margin:4px 0 6px}
.idchip{font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,monospace; font-size:11px; font-weight:600; padding:1px 6px; border-radius:4px; border:1px solid var(--border); background:var(--surface); color:var(--text)}
.idchip.sev-critical{border-color:var(--sev-critical)} .idchip.sev-high{border-color:var(--sev-high)}
.idchip.sev-medium{border-color:var(--sev-medium)} .idchip.sev-low{border-color:var(--sev-low)}
.idchip.dim{opacity:.35}
#search{width:100%; padding:8px 10px; border:1px solid var(--border); border-radius:6px; background:var(--surface); color:var(--text); font:inherit; font-size:13.5px}
#search:focus-visible,.catbtn:focus-visible,summary:focus-visible,button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
.sevopt{display:flex; align-items:center; gap:8px; cursor:pointer; padding:2px 0}
.sevopt input{margin:0; accent-color:var(--accent)}
.dot{width:10px; height:10px; border-radius:50%; background:currentColor; flex:none}
.dot.sev-critical{color:var(--sev-critical)} .dot.sev-high{color:var(--sev-high)}
.dot.sev-medium{color:var(--sev-medium)} .dot.sev-low{color:var(--sev-low)}
.catrow{display:flex; flex-wrap:wrap; gap:6px}
.catbtn{font:inherit; font-size:12.5px; padding:3px 9px; border-radius:999px; border:1px solid var(--border); background:var(--surface); color:var(--text); cursor:pointer}
.catbtn[aria-pressed="true"]{background:var(--accent); color:var(--accent-ink); border-color:var(--accent)}
.tools{display:flex; gap:6px; flex-wrap:wrap}
.tools button{font:inherit; font-size:12.5px; padding:4px 10px; border-radius:6px; border:1px solid var(--border); background:var(--surface); color:var(--text); cursor:pointer}
.status{color:var(--muted); font-size:12.5px; font-variant-numeric:tabular-nums}

/* prose */
main{min-width:0; display:grid; gap:40px}
section.prose h2, section.sevsec h2{font-size:22px; font-weight:720; display:flex; align-items:center; gap:12px; padding-bottom:10px; border-bottom:1px solid var(--border); margin-bottom:16px}
h2 .num{font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,monospace; font-size:13px; font-weight:600; color:var(--muted); border:1px solid var(--border); border-radius:4px; padding:0 6px}
section.prose{max-width:78ch}
section.prose p, section.prose li{max-width:72ch}
section.prose h3{font-size:16px; margin:20px 0 6px}
section.prose ul, section.prose ol{padding-left:1.3em; margin:8px 0}
section.prose li{margin:3px 0}
section.prose hr{border:0; border-top:1px solid var(--border); margin:20px 0}
.tablewrap{overflow-x:auto; margin:12px 0}
table{border-collapse:collapse; font-size:14px; min-width:320px}
th,td{padding:7px 12px; border-bottom:1px solid var(--border); text-align:left; vertical-align:top}
th{font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); font-weight:700; background:var(--surface-2)}
td:nth-child(2){font-variant-numeric:tabular-nums}

/* severity sections + cards */
.sevmark{width:12px; height:12px; border-radius:3px; background:currentColor; flex:none}
.sevmark.sev-critical{color:var(--sev-critical)} .sevmark.sev-high{color:var(--sev-high)}
.sevmark.sev-medium{color:var(--sev-medium)} .sevmark.sev-low{color:var(--sev-low)}
.secmeta{margin-left:auto; font-size:13px; color:var(--muted); font-weight:600; font-variant-numeric:tabular-nums}
.sevsub{color:var(--muted); font-size:13.5px; margin:-6px 0 16px}
.sevsec{display:grid; gap:12px}
.finding{background:var(--surface); border:1px solid var(--border); border-left-width:4px; border-radius:8px; box-shadow:var(--shadow)}
.finding[data-sev="Critical"]{border-left-color:var(--sev-critical)} .finding[data-sev="High"]{border-left-color:var(--sev-high)}
.finding[data-sev="Medium"]{border-left-color:var(--sev-medium)} .finding[data-sev="Low"]{border-left-color:var(--sev-low)}
.finding:target{outline:2px solid var(--accent); outline-offset:2px}
summary{list-style:none; cursor:pointer; display:flex; flex-wrap:wrap; align-items:center; gap:8px 12px; padding:12px 16px}
summary::-webkit-details-marker{display:none}
summary::before{content:""; width:7px; height:7px; border-right:1.6px solid var(--muted); border-bottom:1.6px solid var(--muted); transform:rotate(-45deg); transition:transform .15s; flex:none; margin-left:2px}
.finding[open] summary::before{transform:rotate(45deg)}
.fid{font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,monospace; font-weight:700; font-size:13px; padding:2px 7px; border-radius:4px; color:var(--surface); flex:none}
.fid.sev-critical{background:var(--sev-critical)} .fid.sev-high{background:var(--sev-high)}
.fid.sev-medium{background:var(--sev-medium)} .fid.sev-low{background:var(--sev-low)}
.ftitle{font-weight:650; font-size:15.5px; flex:1 1 320px; min-width:0}
.ftitle code{font-size:.85em}
.chips{display:flex; flex-wrap:wrap; gap:6px; margin-left:auto}
.chip{font-size:11.5px; font-weight:650; letter-spacing:.02em; padding:2px 8px; border-radius:999px; border:1px solid var(--border); color:var(--muted); background:var(--surface-2)}
.chip.sev.sev-critical{color:var(--sev-critical); background:var(--sev-critical-bg); border-color:transparent}
.chip.sev.sev-high{color:var(--sev-high); background:var(--sev-high-bg); border-color:transparent}
.chip.sev.sev-medium{color:var(--sev-medium); background:var(--sev-medium-bg); border-color:transparent}
.chip.sev.sev-low{color:var(--sev-low); background:var(--sev-low-bg); border-color:transparent}
.fbody{border-top:1px solid var(--border); padding:6px 16px 14px; display:grid}
.row{display:grid; grid-template-columns:88px minmax(0,1fr); gap:6px 16px; padding:9px 0; border-bottom:1px dashed var(--border)}
.row:last-child{border-bottom:0}
.row .k{font-size:11.5px; letter-spacing:.06em; text-transform:uppercase; font-weight:700; color:var(--muted); padding-top:3px}
.row.risk .k{color:var(--sev-critical)}
.row.fix .k{color:var(--sev-low)}
.row .v{min-width:0; font-size:14.5px}
.row .v p{margin:0 0 6px} .row .v p:last-child{margin-bottom:0}
.row .v ul{margin:4px 0 0; padding-left:1.2em} .row .v li{margin:3px 0}
.row.files .v{font-size:14px}
.finding.hidden{display:none}
.sevsec.hidden{display:none}
footer{color:var(--muted); font-size:12.5px; padding-top:32px; border-top:1px solid var(--border); margin-top:8px; display:flex; flex-wrap:wrap; gap:6px 20px}

@media (max-width:860px){
  .grid{grid-template-columns:1fr; gap:16px}
  aside{position:static; max-height:none; border:1px solid var(--border); border-radius:8px; padding:4px 14px 8px; background:var(--surface)}
  .idrow{display:none}
  h1{font-size:24px}
  .row{grid-template-columns:1fr; gap:2px 0}
  summary{padding:10px 12px} .fbody{padding:4px 12px 12px}
}
@media (prefers-reduced-motion:reduce){ *{transition:none!important} }
@media print{
  aside,.counts,footer .tools{display:none}
  .grid{grid-template-columns:1fr}
  .finding{break-inside:avoid; box-shadow:none}
  body{font-size:12px}
}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <div>
    <div class="eyebrow">Code review · TCSpy · {{DATE}}</div>
    <h1>TCSpy 코드 리뷰</h1>
    <ul class="meta">{{META}}</ul>
  </div>
  <div class="counts" aria-label="심각도별 건수">{{HEADER_COUNTS}}</div>
</header>

<div class="grid">
<aside aria-label="목차와 필터">
  <div class="box">
    <div class="label">검색</div>
    <input id="search" type="search" placeholder="파일명, 함수, 키워드…" aria-label="항목 검색" autocomplete="off">
    <div class="status" id="status">전체 {{TOTAL}}건 표시</div>
  </div>
  <div class="box">
    <div class="label">심각도</div>
    {{SEV_FILTERS}}
  </div>
  <div class="box">
    <div class="label">분류</div>
    <div class="catrow">{{CAT_FILTERS}}</div>
  </div>
  <div class="box">
    <div class="label">보기</div>
    <div class="tools">
      <button type="button" id="expand">모두 펼치기</button>
      <button type="button" id="collapse">모두 접기</button>
      <button type="button" id="reset">필터 초기화</button>
    </div>
  </div>
  <div class="box">
    <div class="label">목차</div>
    {{TOC_PROSE}}
    {{TOC_SEV}}
    <a href="#sec-6">구조적 개선 제안</a>
  </div>
</aside>

<main>
  {{PROSE}}
  {{SEVERITY_SECTIONS}}
  {{TAIL}}
  <footer>
    <span>빌드 {{BUILT}}</span>
    <span><a href="report.md">마크다운 원본</a></span>
    <span>다시 만들기: <code>python3 docs/code_review/build.py</code></span>
  </footer>
</main>
</div>
</div>

<script>
(function(){
  var $ = function(s, r){ return (r||document).querySelector(s); };
  var $$ = function(s, r){ return Array.prototype.slice.call((r||document).querySelectorAll(s)); };
  var cards = $$('.finding');
  var sevBoxes = $$('input[data-sev]');
  var catBtns = $$('.catbtn');
  var search = $('#search');
  var status = $('#status');
  var KEY = 'tcspy-review-filters';

  function state(){
    return {
      sev: sevBoxes.filter(function(b){return b.checked;}).map(function(b){return b.dataset.sev;}),
      cats: catBtns.filter(function(b){return b.getAttribute('aria-pressed')==='true';}).map(function(b){return b.dataset.cat;}),
      q: (search.value||'').trim().toLowerCase()
    };
  }
  function apply(){
    var s = state(), shown = 0, perSev = {};
    cards.forEach(function(c){
      var cats = (c.dataset.cats||'').split('|').filter(Boolean);
      var ok = s.sev.indexOf(c.dataset.sev) >= 0
        && (s.cats.length === 0 || s.cats.some(function(x){return cats.indexOf(x)>=0;}))
        && (!s.q || c.textContent.toLowerCase().indexOf(s.q) >= 0);
      c.classList.toggle('hidden', !ok);
      if (ok){ shown++; perSev[c.dataset.sev] = (perSev[c.dataset.sev]||0)+1; }
      var chip = $('.idchip[href="#'+c.id+'"]');
      if (chip) chip.classList.toggle('dim', !ok);
    });
    $$('.sevsec').forEach(function(sec){
      var n = perSev[sec.dataset.sev]||0;
      $('.shown', sec).textContent = n;
      sec.classList.toggle('hidden', n === 0);
    });
    status.textContent = shown === cards.length ? '전체 '+cards.length+'건 표시' : cards.length+'건 중 '+shown+'건 표시';
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch(e){}
  }
  function restore(){
    try {
      var s = JSON.parse(localStorage.getItem(KEY)||'null');
      if (!s) return;
      sevBoxes.forEach(function(b){ b.checked = s.sev.indexOf(b.dataset.sev) >= 0; });
      catBtns.forEach(function(b){ b.setAttribute('aria-pressed', s.cats.indexOf(b.dataset.cat) >= 0 ? 'true':'false'); });
      search.value = s.q || '';
    } catch(e){}
  }
  sevBoxes.forEach(function(b){ b.addEventListener('change', apply); });
  catBtns.forEach(function(b){ b.addEventListener('click', function(){
    b.setAttribute('aria-pressed', b.getAttribute('aria-pressed')==='true' ? 'false':'true'); apply();
  }); });
  search.addEventListener('input', apply);
  $('#expand').addEventListener('click', function(){ cards.forEach(function(c){ c.open = true; }); });
  $('#collapse').addEventListener('click', function(){ cards.forEach(function(c){ c.open = false; }); });
  $('#reset').addEventListener('click', function(){
    sevBoxes.forEach(function(b){ b.checked = true; });
    catBtns.forEach(function(b){ b.setAttribute('aria-pressed','false'); });
    search.value = ''; apply();
  });
  function openTarget(){
    var id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === 'DETAILS'){ el.open = true; el.classList.remove('hidden'); }
  }
  window.addEventListener('hashchange', openTarget);
  document.addEventListener('keydown', function(e){
    if (e.key === '/' && document.activeElement !== search){ e.preventDefault(); search.focus(); }
  });
  restore(); apply(); openTarget();
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()

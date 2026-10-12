#!/usr/bin/env python3
"""Build the offline reading copy from this kit's Markdown subset; no dependencies or network."""
import argparse
import html
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/westman2000/pixel-xl-recovery'
ONLINE = False
DOCUMENTS = [
    ('README.md', 'Overview'),
    ('docs/CASE-STUDY.md', 'Case study'),
    ('docs/RECOVERY-RUNBOOK.md', 'Recovery runbook'),
    ('docs/IMPLEMENTATION.md', 'Image implementation'),
    ('docs/VALIDATION.md', 'Validation and evidence'),
    ('docs/TOOLS.md', 'Tool reference'),
    ('docs/RESEARCH-PLAN.md', 'Research and porting plan'),
    ('docs/REFERENCES.md', 'References'),
    ('CONTRIBUTING.md', 'Contributing'),
    ('templates/DEVICE-REPORT.md', 'Device report template'),
    ('PUBLIC-POST.md', 'Prepared public post'),
    ('CHANGELOG.md', 'Release history'),
]
IDS = {(ROOT / name).resolve(): 'chapter-' + str(i + 1)
       for i, (name, _) in enumerate(DOCUMENTS)}


def link_target(target, source):
    parts = urlsplit(target)
    if parts.scheme or target.startswith('#'):
        return target
    resolved = (source.parent / parts.path).resolve()
    if resolved in IDS:
        return '#' + IDS[resolved]
    path = resolved.relative_to(ROOT).as_posix()
    return (REPOSITORY + '/blob/main/' if ONLINE else '') + path + (('#' + parts.fragment) if parts.fragment else '')


def inline(text, source):
    """Escape all HTML; render only code spans, links, and bold used by these documents."""
    tokens = re.compile(r'`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*')
    out, end = [], 0
    for match in tokens.finditer(text):
        out.append(html.escape(text[end:match.start()]))
        code, label, target, bold = match.groups()
        if code is not None:
            out.append('<code>' + html.escape(code) + '</code>')
        elif label is not None:
            href = html.escape(link_target(target, source), quote=True)
            out.append('<a href="' + href + '">' + inline(label, source) + '</a>')
        else:
            out.append('<strong>' + html.escape(bold) + '</strong>')
        end = match.end()
    out.append(html.escape(text[end:]))
    return ''.join(out)


def render(source):
    lines = source.read_text().splitlines()
    out, headings, i = [], [], 0
    prefix = IDS[source.resolve()]
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            if i == len(lines):
                raise ValueError('Unclosed code fence: ' + source.name)
            out.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
            i += 1
            continue
        heading = re.match(r'^(#{1,6}) (.+)$', line)
        if heading:
            level, text = len(heading[1]), heading[2]
            anchor = prefix + '-heading-' + str(len(headings) + 1)
            headings.append((level, anchor, text))
            out.append(f'<h{level} id="{anchor}">' + inline(text, source) + f'</h{level}>')
            i += 1
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', x) for x in cells):
                    rows.append(cells)
                i += 1
            width = len(rows[0])
            if any(len(row) != width for row in rows):
                raise ValueError('Unsupported table cell: ' + source.name)
            out.append('<div class="table-wrap"><table><thead><tr>')
            out.extend('<th scope="col">' + inline(x, source) + '</th>' for x in rows[0])
            out.append('</tr></thead><tbody>')
            for row in rows[1:]:
                out.append('<tr>' + ''.join('<td>' + inline(x, source) + '</td>' for x in row) + '</tr>')
            out.append('</tbody></table></div>')
            continue
        item = re.match(r'^(- |\d+\. )(.+)$', line)
        if item:
            ordered = item[1] != '- '
            tag = 'ol' if ordered else 'ul'
            out.append('<' + tag + '>')
            while i < len(lines):
                m = re.match(r'^(\d+\. )(.+)$' if ordered else r'^(- )(.+)$', lines[i])
                if not m:
                    break
                out.append('<li>' + inline(m[2], source) + '</li>'); i += 1
            out.append('</' + tag + '>')
            continue
        paragraph = []
        while i < len(lines) and lines[i].strip():
            if re.match(r'^(?:#{1,6} |```|\||- |\d+\. )', lines[i]):
                break
            paragraph.append(lines[i]); i += 1
        if not paragraph:
            raise ValueError('Unsupported Markdown block: ' + line)
        out.append('<p>' + inline(' '.join(paragraph), source) + '</p>')
    # Place an optional local contents list immediately after the chapter title.
    subsections = [(anchor, title) for level, anchor, title in headings if level == 2]
    if len(subsections) > 3:
        local = '<details class="local-toc"><summary>In this chapter</summary><ul>'
        local += ''.join('<li><a href="#' + a + '">' + inline(t, source) + '</a></li>' for a, t in subsections)
        local += '</ul></details>'
        out.insert(1, local)
    return '\n'.join(out)


STYLE = '''
:root{color-scheme:light;--ink:#18303d;--muted:#526570;--line:#d9e3e8;--blue:#005b80;--paper:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:#f3f6f7;font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--blue);text-underline-offset:3px}a:hover{color:#002f47}a:focus-visible{outline:3px solid #eeb744;outline-offset:3px}
.cover{background:#123345;color:#fff;padding:56px max(6vw,24px) 42px}.cover-inner{max-width:1120px;margin:auto}.eyebrow{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#9ed2df}.cover h1{font-size:clamp(32px,4vw,52px);line-height:1.12;max-width:850px;letter-spacing:-.03em;margin:18px 0}.cover p{max-width:820px;color:#d6e4ea;font-size:19px}.facts{display:flex;gap:48px;flex-wrap:wrap;margin-top:32px}.fact strong{font-size:30px;display:block;line-height:1.2}.fact span{font-size:13px;color:#b8d3df}.cover .edition{font-size:13px;margin-top:24px}
.cover-actions{display:flex;gap:12px;flex-wrap:wrap;margin:26px 0 10px}.cover-actions a{display:inline-block;padding:10px 18px;border:1px solid #8cb6c6;border-radius:6px;color:#eaf7fb;text-decoration:none;font-size:14px;font-weight:600}.cover-actions a:first-child{background:#d8f0df;color:#143b2a;border-color:#d8f0df}.cover-actions a:hover{background:#244c60}.cover-actions a:first-child:hover{background:#bfdfc8}.skip-link{position:absolute;top:-80px;left:20px;background:white;color:#123345;padding:10px 16px;z-index:5}.skip-link:focus{top:12px}.chapter-meta a:focus-visible{outline-offset:2px}
.layout{max-width:1340px;margin:auto;display:grid;grid-template-columns:250px minmax(0,1fr);gap:38px;padding:40px 28px}.navigation{align-self:start;position:sticky;top:22px;max-height:calc(100vh - 44px);overflow:auto;font-size:14px}.navigation h2{font-size:13px;text-transform:uppercase;letter-spacing:.09em;margin:0 0 14px}.navigation ol{padding-left:20px;margin:0}.navigation li{padding:5px 0}.navigation a{text-decoration:none}.navigation p{color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px;margin-right:10px}
main{min-width:0}section{background:var(--paper);border:1px solid var(--line);border-radius:9px;padding:38px 42px;margin-bottom:32px;scroll-margin-top:20px}section h1{font-size:30px;line-height:1.2;letter-spacing:-.02em;margin:0 0 24px}h2{font-size:23px;line-height:1.3;margin:38px 0 14px;scroll-margin-top:24px}h3{font-size:19px;margin:28px 0 12px}p{margin:14px 0}li{margin:7px 0}ul,ol{padding-left:25px}.chapter-meta{font-size:12px;color:var(--muted);border-bottom:1px solid var(--line);padding-bottom:12px;margin:0 0 24px}.chapter-meta a{text-decoration:none}.local-toc{font-size:14px;background:#f4f8fa;border:1px solid var(--line);border-radius:5px;padding:10px 14px;margin:18px 0 28px}.local-toc summary{cursor:pointer;color:var(--blue)}.local-toc li{margin:3px 0}
code{font: .87em/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;background:#edf3f6;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{background:#132d3c;color:#e4f0f5;padding:18px 20px;border-radius:6px;overflow:auto;font-size:14px;line-height:1.65;max-width:100%}pre code{font-size:inherit;background:none;padding:0;color:inherit;overflow-wrap:normal;white-space:pre}.table-wrap{overflow-x:auto;margin:20px 0;border:1px solid var(--line);border-radius:5px}table{border-collapse:collapse;font-size:14px;width:100%;line-height:1.5}th,td{text-align:left;vertical-align:top;padding:12px 13px;border-bottom:1px solid var(--line);min-width:110px}th{background:#eaf1f5;font-weight:650}tbody tr:last-child td{border-bottom:0}tbody tr:nth-child(even){background:#fafcfd}.footer{max-width:1120px;margin:0 auto 40px;padding:0 24px;color:var(--muted);font-size:13px}
@media(max-width:1000px){.layout{grid-template-columns:1fr;gap:22px;max-width:950px}.navigation{position:static;max-height:none}.navigation ol{columns:2}.navigation p{display:none}}
@media(max-width:600px){body{font-size:16px}.cover{padding:34px 20px}.cover p{font-size:17px}.facts{gap:24px}.fact strong{font-size:25px}.layout{padding:22px 12px}.navigation{padding:0 12px}.navigation ol{columns:1}section{padding:26px 20px;border-radius:5px}section h1{font-size:26px}h2{font-size:21px}pre{font-size:12px;padding:14px}.table-wrap{margin-left:-4px;margin-right:-4px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{background:white;font-size:10pt}.cover{background:white;color:black;padding:0 0 20px}.cover p,.cover .eyebrow,.cover .edition,.fact span{color:#333}.cover h1{font-size:26pt}.layout{display:block;padding:0}.navigation,.local-toc,.chapter-meta{display:none}section{border:0;padding:0;margin:0;break-before:page}h1,h2,h3{break-after:avoid}pre{white-space:pre-wrap;background:#f2f2f2;color:black;overflow:visible;font-size:8pt}pre code{white-space:pre-wrap;overflow-wrap:anywhere}.table-wrap{overflow:visible}table{font-size:8pt}tr{break-inside:avoid}a{color:inherit}.footer{padding:0}}
'''


def main():
    global ONLINE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', action='store_true', help='Generate index.html for GitHub Pages; evidence/source links point to GitHub')
    args = parser.parse_args()
    ONLINE = args.site
    nav = ''.join('<li><a href="#' + IDS[(ROOT / name).resolve()] + '">' + html.escape(label) + '</a></li>'
                  for name, label in DOCUMENTS)
    chapters = []
    for i, (name, label) in enumerate(DOCUMENTS, 1):
        source = ROOT / name
        source_url = REPOSITORY + '/blob/main/' + name if ONLINE else name
        meta = f'<p class="chapter-meta">{i:02d} / {len(DOCUMENTS):02d} &nbsp; · &nbsp; <a href="{html.escape(source_url)}">Markdown source</a> &nbsp; · &nbsp; <a href="#contents">Contents</a></p>'
        chapters.append('<section id="' + IDS[source.resolve()] + '">' + meta + render(source) + '</section>')
    document = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pixel XL Clock Recovery — Case Study and Toolkit</title>
<meta name="description" content="A single-device Pixel XL bootloop investigation, exact-image toolkit, evidence and reproduction plan.">
<style>''' + STYLE + '''</style></head><body><a class="skip-link" href="#main">Skip to documentation</a>
<header class="cover"><div class="cover-inner"><div class="eyebrow">Independent investigation · Pixel XL / marlin</div>
<h1>From a bootloop to four working cores</h1>
<p>A complete case study, recovery runbook, exact-image toolkit, and plan for independent reproduction.</p>
<div class="cover-actions"><a href="#chapter-2">Read the case study</a><a href="#chapter-3">Recovery guide</a><a href="https://github.com/westman2000/pixel-xl-recovery/releases/latest">Download toolkit ↗</a></div>
<div class="facts"><div class="fact"><strong>1 device</strong><span>Scope of the hardware evidence</span></div><div class="fact"><strong>4 cores</strong><span>Working in the retained configuration</span></div><div class="fact"><strong>7,252</strong><span>Recorded final-image correctness checks</span></div></div>
<p class="edition">Release 0.1.0 · October 12, 2026 · English reference edition · No trackers or external scripts</p></div></header>
<div class="layout"><nav class="navigation" id="contents" aria-label="Chapters"><h2>Contents</h2><ol>''' + nav + '''</ol>
<p>The source files and evidence are included alongside this reader. No firmware binaries are distributed. <a href="https://github.com/westman2000/pixel-xl-recovery">Project on GitHub</a> · <a href="https://github.com/westman2000/pixel-xl-recovery/releases">Releases</a></p></nav>
<main id="main">''' + '\n'.join(chapters) + '''</main></div>
<footer class="footer">One device and one exact source image. This is a documented workaround with bounded evidence, not a universal repair or a proven physical diagnosis. <a href="LICENSE">License</a> · <a href="NOTICE">Upstream notices</a></footer>
</body></html>
'''
    if ONLINE:
        document = document.replace('href="LICENSE"', 'href="' + REPOSITORY + '/blob/main/LICENSE"')
        document = document.replace('href="NOTICE"', 'href="' + REPOSITORY + '/blob/main/NOTICE"')
        document = document.replace('</head>', '<link rel="canonical" href="https://westman2000.github.io/pixel-xl-recovery/"></head>')
    output = ROOT / ('index.html' if ONLINE else 'READ-ME.html')
    output.write_text(document)
    print('Wrote', output.name, 'with', len(DOCUMENTS), 'chapters')


if __name__ == '__main__':
    main()

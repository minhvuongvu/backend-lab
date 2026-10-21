"""Order ROADMAP.html for learning while keeping every topic independently learnable.

What it does (idempotent — run it after adding or editing topics):
  1. Validates the prerequisite graph (unknown slugs, cycles).
  2. Computes a suggested global learning order with a topological sort: every topic comes after
     all of its prerequisites; ties are broken by stage/track order, then priority, then table order.
     The number is written to tr[data-order] and shown as "#n" in the first cell.
  3. Regroups the topic table by stage → track (group header rows), topics inside a group by #n.
  4. Regenerates the "Giai đoạn học" section between <!-- stages:start --> / <!-- stages:end -->.
  5. Reorders the per-track diagrams to follow the stage order.

The order is a suggestion only: /research lets you start any topic; missing prerequisites are
summarised inside that topic's 01-research.html (§6 "Tóm tắt tiền đề").

Usage: python3 scripts/roadmap_order.py [--check]
"""
import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROADMAP = ROOT / "ROADMAP.html"

STAGES = [
    (1, "Nền tảng một node", "Dữ liệu đúng trong một database, container, JVM, Spring và mạng: mọi topic sau đều dựng trên đây.",
     ["correctness", "postgres", "containers", "jvm", "spring", "networking"]),
    (2, "Chịu tải & dữ liệu nóng", "Giữ hệ thống sống khi tải tăng hoặc phụ thuộc chậm, tăng tốc đọc bằng cache, và phục vụ kết nối real-time.",
     ["resilience", "caching", "redis", "realtime"]),
    (3, "Hệ phân tán & messaging", "Nhất quán, đồng thuận, giao nhận message, giao dịch trải nhiều service và các mẫu nghiệp vụ dựng trên chúng.",
     ["foundations", "kafka", "rabbitmq", "distributed", "business"]),
    (4, "Thiết kế & tiến hoá hệ thống", "Thay đổi API, dữ liệu và ranh giới kiến trúc mà không phá hệ thống đang chạy.",
     ["api", "architecture"]),
    (5, "Kho dữ liệu chuyên dụng & AI", "Document store, tìm kiếm, lưu trữ object, phân tích (OLAP) và tích hợp AI.",
     ["mongodb", "search-storage", "analytics", "ai"]),
    (6, "Nền tảng chạy hệ thống", "Kubernetes, tìm service, cấu hình, cổng vào và chạy trên nhiều vùng.",
     ["kubernetes", "platform", "gateway", "multiregion"]),
    (7, "Bảo mật & vận hành", "Danh tính, phân quyền, bí mật, quan sát, cảnh báo và đưa thay đổi lên production.",
     ["security", "sre", "cicd"]),
]

ROW_RE = re.compile(r'[ \t]*<tr id="([^"]+)" data-slug="[^"]*"[^>]*>.*?</tr>\n', re.S)
GROUP_RE = re.compile(r'[ \t]*<tr class="track-group"[^>]*>.*?</tr>\n', re.S)
ORDER_SPAN_RE = re.compile(r'<span class="order-no"[^>]*>#\d+</span> ?')
LATER_SPAN_RE = re.compile(r' ?<span class="after-stage"[^>]*>[^<]*</span>')


def attr(tag, name):
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="validate only, do not write")
    args = ap.parse_args()

    s = ROADMAP.read_text(encoding="utf-8")
    tb_start = s.index("<tbody>", s.index('<table class="roadmap"')) + len("<tbody>\n")
    tb_end = s.index("      </tbody>", tb_start)
    body = GROUP_RE.sub("", s[tb_start:tb_end])

    rows = []
    for idx, m in enumerate(ROW_RE.finditer(body)):
        block = m.group(0)
        tag = block[: block.index(">") + 1]
        rows.append({
            "slug": m.group(1), "block": block, "idx": idx,
            "track": attr(tag, "data-track"),
            "prereq": [p for p in attr(tag, "data-prereq").split(",") if p],
            "priority": int(attr(tag, "data-priority") or 3),
            "name": html.unescape(re.search(r"<strong>(.*?)</strong>", block, re.S).group(1)),
        })
    by_slug = {r["slug"]: r for r in rows}
    assert len(by_slug) == len(rows), "duplicate slugs in table"

    problems = []
    for r in rows:
        for p in r["prereq"]:
            if p not in by_slug:
                problems.append(f"{r['slug']}: unknown prerequisite {p}")
    track_rank = {t: i for i, (_, _, _, ts) in enumerate(STAGES) for t in ts}
    track_seq = [t for _, _, _, ts in STAGES for t in ts]
    unknown_tracks = sorted({r["track"] for r in rows} - set(track_rank))
    for t in unknown_tracks:
        problems.append(f"track '{t}' is not assigned to a stage in STAGES (it will be listed last)")
        track_rank[t] = len(STAGES)
        track_seq.append(t)

    # Kahn's algorithm with a deterministic priority key.
    key = lambda r: (track_rank[r["track"]], track_seq.index(r["track"]), r["priority"], r["idx"])
    indeg = {r["slug"]: sum(1 for p in r["prereq"] if p in by_slug) for r in rows}
    children = {r["slug"]: [] for r in rows}
    for r in rows:
        for p in r["prereq"]:
            if p in by_slug:
                children[p].append(r["slug"])
    ready = sorted([by_slug[k] for k, d in indeg.items() if d == 0], key=key)
    order = []
    while ready:
        r = ready.pop(0)
        order.append(r)
        for c in children[r["slug"]]:
            indeg[c] -= 1
            if indeg[c] == 0:
                ready.append(by_slug[c])
                ready.sort(key=key)
    if len(order) != len(rows):
        stuck = sorted(k for k, d in indeg.items() if d > 0)
        problems.append(f"cycle among: {', '.join(stuck)}")
    for n, r in enumerate(order, 1):
        r["order"] = n

    for msg in problems:
        print("WARN" if "not assigned" in msg else "ERROR", msg)
    if any(not m.startswith("track") for m in problems if "not assigned" not in m):
        sys.exit(1)

    # Cross-group "forward" prerequisites: prerequisite lives in a later group of the table.
    group_pos = {t: i for i, t in enumerate(track_seq)}
    forward = [(r["slug"], p) for r in rows for p in r["prereq"]
               if p in by_slug and group_pos[by_slug[p]["track"]] > group_pos[r["track"]]]

    # Learning paths (ol.learning-path under h3[id^=path-]): every prerequisite of a step must appear
    # earlier in the same path, otherwise the path asks the reader to learn something out of order.
    path_problems = []
    for pm in re.finditer(r'<h3 id="(path-[^"]+)">.*?<ol class="learning-path">(.*?)</ol>', s, re.S):
        steps = re.findall(r'<li><a href="#([^"]+)">', pm.group(2))
        seen = set()
        for st in steps:
            if st not in by_slug:
                path_problems.append(f"{pm.group(1)}: unknown topic {st}")
                continue
            missing = [p for p in by_slug[st]["prereq"] if p not in seen]
            if missing:
                path_problems.append(f"{pm.group(1)}: {st} comes before its prerequisites {missing}")
            seen.add(st)
    for msg in path_problems:
        print("WARN", msg)

    if args.check:
        print(f"ok: {len(rows)} topics, {len(track_seq)} tracks; prerequisites in a later group: {len(forward)}; "
              f"learning-path order problems: {len(path_problems)}")
        return

    # Latest stage among all (transitive) prerequisites: a topic placed in an early stage whose
    # prerequisites live in a later stage is an "advanced" topic of its group — learn it after that stage.
    stage_idx = {t: n for n, _, _, ts in STAGES for t in ts}
    memo = {}

    def max_prereq_stage(slug):
        if slug not in memo:
            memo[slug] = 0
            for p in by_slug[slug]["prereq"]:
                if p in by_slug:
                    memo[slug] = max(memo[slug], stage_idx.get(by_slug[p]["track"], len(STAGES) + 1), max_prereq_stage(p))
        return memo[slug]

    # Rewrite rows: data-order attribute + "#n" badge (+ "learn after stage N") in the first cell.
    def render(r):
        b = r["block"]
        tag_end = b.index(">")
        tag = re.sub(r' data-(order|after-stage)="\d+"', "", b[:tag_end])
        later = max_prereq_stage(r["slug"])
        own = stage_idx.get(r["track"], len(STAGES) + 1)
        extra = f' data-after-stage="{later}"' if later > own else ""
        b = tag + f' data-order="{r["order"]}"{extra}' + b[tag_end:]
        b = ORDER_SPAN_RE.sub("", b)
        b = LATER_SPAN_RE.sub("", b)
        b = re.sub(r"<td>\s*<strong>", "<td><strong>", b, count=1)  # leftovers of removed badges
        badge = (f' <span class="after-stage" title="Có tiền đề ở giai đoạn {later}; topic nâng cao của nhóm này">'
                 f'Học sau giai đoạn {later}</span>') if later > own else ""
        return b.replace("<td><strong>", f'<td><span class="order-no" title="Thứ tự gợi ý">#{r["order"]}</span>{badge} <strong>', 1)

    track_names = dict(re.findall(r'data-roadmap="([^"]+)" data-track-name="([^"]+)"', s))
    stage_of = {t: (n, title) for n, title, _, ts in STAGES for t in ts}
    out = []
    for t in track_seq:
        members = sorted((r for r in rows if r["track"] == t), key=lambda r: r["order"])
        if not members:
            continue
        sn, stitle = stage_of.get(t, (len(STAGES) + 1, "Khác"))
        first, last = members[0]["order"], members[-1]["order"]
        out.append(f'        <tr class="track-group" data-group="{t}"><td colspan="5">'
                   f'<span class="stage-no">Giai đoạn {sn}</span> {html.escape(stitle, quote=False)} · '
                   f'<strong>{track_names.get(t, html.escape(t))}</strong>'
                   f' <span class="group-count">{len(members)} topic · #{first}–#{last}</span></td></tr>\n')
        out.extend(render(r) for r in members)
    s = s[:tb_start] + "".join(out) + s[tb_end:]

    # Stage overview section.
    stage_html = ['    <h2 id="stages">Giai đoạn học</h2>',
                  '    <p>Nhóm topic được xếp theo thứ tự nên học; số <span class="order-no">#n</span> ở mỗi topic là thứ tự gợi ý, '
                  'luôn đứng sau mọi tiền đề của nó. <strong>Thứ tự chỉ là gợi ý:</strong> có thể bắt đầu bất kỳ topic nào bằng '
                  '<code>/research &lt;slug&gt;</code>; tiền đề chưa học sẽ được tóm tắt ngay trong tài liệu research của topic đó '
                  '(mục "Tóm tắt tiền đề") để đủ hiểu mà không phải học trọn topic tiền đề trước.</p>',
                  '    <ol class="stage-list">']
    for n, title, intro, ts in STAGES:
        links = ", ".join(f'<a href="#group-{t}">{track_names.get(t, t)}</a>' for t in ts
                          if any(r["track"] == t for r in rows))
        count = sum(1 for r in rows if r["track"] in ts)
        stage_html.append(f'      <li><strong>Giai đoạn {n} — {html.escape(title, quote=False)}</strong> '
                          f'<span class="group-count">{count} topic</span><br>{html.escape(intro, quote=False)}<br>{links}</li>')
    stage_html.append("    </ol>")
    if forward:
        stage_html.append(f'    <p class="note">{len(forward)} quan hệ tiền đề trỏ sang nhóm xếp sau (ví dụ topic Kubernetes cần service discovery). '
                          'Số #n đã tính cả các quan hệ này, nên đi theo #n vẫn luôn gặp tiền đề trước.</p>')
    block = "<!-- stages:start -->\n" + "\n".join(stage_html) + "\n    <!-- stages:end -->"
    if "<!-- stages:start -->" in s:
        s = re.sub(r"<!-- stages:start -->.*?<!-- stages:end -->", lambda _: block, s, flags=re.S)
    else:
        anchor = s.index('<h2 id="paths">')
        sec_start = s.rindex("<section", 0, anchor)
        s = s[:sec_start] + "<section>\n    " + block + "\n  </section>\n\n  " + s[sec_start:]

    # Group anchors for the stage links: id on the group header row.
    s = re.sub(r'<tr class="track-group" data-group="([^"]+)">', r'<tr class="track-group" data-group="\1" id="group-\1">', s)

    # Reorder per-track diagrams (overview stays first).
    fig_re = re.compile(r'\n    <h3 id="graph-([^"]+)">[^<]*</h3>\n    <figure class="diagram" data-roadmap="\1"[^>]*>.*?</figure>', re.S)
    figs = {m.group(1): m.group(0) for m in fig_re.finditer(s) if m.group(1) != "overview"}
    first = min(m.start() for m in fig_re.finditer(s) if m.group(1) != "overview")
    last = max(m.end() for m in fig_re.finditer(s) if m.group(1) != "overview")
    ordered = "".join(figs[t] for t in track_seq if t in figs) + "".join(v for k, v in figs.items() if k not in track_seq)
    s = s[:first] + ordered + s[last:]

    ROADMAP.write_text(s, encoding="utf-8", newline="\n")
    print(f"ordered {len(rows)} topics in {len([t for t in track_seq if any(r['track'] == t for r in rows)])} groups / "
          f"{len(STAGES)} stages; prerequisites pointing to a later group: {len(forward)}")


if __name__ == "__main__":
    main()

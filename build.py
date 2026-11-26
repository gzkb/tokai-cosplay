#!/usr/bin/env python3
"""東海コスプレイベントカレンダー（静的サイト）を docs/ に生成する。
使い方: python3 build.py [--base https://<user>.github.io/<repo>] [--today YYYY-MM-DD]
入力: data/events.json  {asof, events:[{date,end,name,pref,place,time,fee,note,url,status}]}
"""
import argparse, datetime, hashlib, html, json, os, re, shutil
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs")
TAG = "gzkbamazon-22"
SITE = "東海コスプレイベントカレンダー"
NOTE = "https://note.com/gzkb"
W = "月火水木金土日"

# 会場の名寄せ：(キーワード, 会場名, スラッグ, 地域)
VENUES = [
    ("鶴舞公園", "鶴舞公園（名古屋市）", "tsurumai", "名古屋市昭和区"),
    ("大須", "大須周辺（名古屋市中区）", "osu", "名古屋市中区"),
    ("大曽根", "大曽根商店街（名古屋市北区）", "ozone", "名古屋市北区"),
    ("吹上ホール", "吹上ホール（名古屋市千種区）", "fukiage", "名古屋市千種区"),
    ("護國神社", "愛知縣護國神社（名古屋市中区）", "gokoku", "名古屋市中区"),
    ("シートレインランド", "名古屋港シートレインランド", "seatrain", "名古屋市港区"),
    ("セントレア", "中部国際空港セントレア（常滑市）", "centrair", "常滑市"),
    ("ラグーナ", "ラグーナテンボス（蒲郡市）", "laguna", "蒲郡市"),
    ("デンパーク", "デンパーク（安城市）", "denpark", "安城市"),
    ("アンフォーレ", "アンフォーレ（安城市）", "anforet", "安城市"),
    ("イオンモール豊川", "イオンモール豊川（豊川市）", "aeon-toyokawa", "豊川市"),
    ("津島市文化会館", "津島市文化会館", "tsushima", "津島市"),
    ("リトルワールド", "リトルワールド（犬山市）", "littleworld", "犬山市"),
    ("ながはら小学校", "ながはら小学校", "nagahara", ""),
    ("パルパル", "浜名湖パルパル（浜松市）", "palpal", "浜松市"),
    ("神明宮", "濱名惣社神明宮（浜松市）", "shinmei", "浜松市"),
    ("二岡神社", "二岡神社（御殿場市）", "futaoka", "御殿場市"),
    ("ソラナ", "ソラナスタジオ（小山町須走）", "solana", "小山町"),
    ("清水港", "清水港（静岡市）", "shimizu", "静岡市"),
    ("富士宮", "富士宮市", "fujinomiya", "富士宮市"),
    ("郡上八幡", "郡上八幡城下町（郡上市）", "gujo", "郡上市"),
    ("笠松競馬場", "笠松競馬場（笠松町）", "kasamatsu", "笠松町"),
    ("マリーナ河芸", "マリーナ河芸（津市）", "kawage", "津市"),
    ("ナガシマスパーランド", "ナガシマスパーランド（桑名市）", "nagashima", "桑名市"),
]


def esc(s):
    return html.escape(s or "", quote=True)


def d(s):
    return datetime.date.fromisoformat(s)


def fmt(e):
    a, b = d(e["date"]), d(e["end"] or e["date"])
    s = f"{a.month}/{a.day}（{W[a.weekday()]}）"
    if b != a:
        s += f"〜{b.month}/{b.day}（{W[b.weekday()]}）"
    return s


def venue_of(e):
    for kw, name, slug, area in VENUES:
        if kw in e["place"] or kw in e["name"]:
            return slug
    return None


def amz(q):
    return f"https://www.amazon.co.jp/s?k={quote(q)}&tag={TAG}"


def badge(status):
    if "公式確認済み" in status:
        return '<span class="b ok">公式で確認済み</span>'
    if "主催" in status or "公式Xで確認" in status:
        return '<span class="b mid">主催の告知で確認</span>'
    return '<span class="b ng">公式で未確認</span>'


CSS = """
:root{--bg:#fffafc;--fg:#3a2f3d;--mut:#7d6f82;--pk:#e85a9a;--pk2:#ffe3ef;--bd:#f0d5e2;--ok:#1f9d6b;--mid:#c28a00;--ng:#c0392b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 -apple-system,"Hiragino Sans","Yu Gothic",sans-serif}
a{color:#c2307a}header,main,footer{max-width:860px;margin:0 auto;padding:0 16px}
header{padding-top:20px;padding-bottom:8px}header .t{font-size:1.35rem;font-weight:700;color:var(--pk);text-decoration:none}
nav{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px;font-size:.95rem}
h1{font-size:1.5rem;margin:18px 0 6px}h2{font-size:1.2rem;margin:28px 0 8px;border-left:6px solid var(--pk);padding-left:10px}
.lead{color:var(--mut)}.card{background:#fff;border:1px solid var(--bd);border-radius:14px;padding:12px 14px;margin:10px 0}
.card .n{font-weight:700}.card .m{color:var(--mut);font-size:.92rem}.b{font-size:.78rem;border-radius:99px;padding:1px 9px;color:#fff;margin-left:6px;white-space:nowrap}
.ok{background:var(--ok)}.mid{background:var(--mid)}.ng{background:var(--ng)}
.filter{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.filter button{border:1px solid var(--pk);background:#fff;color:var(--pk);border-radius:99px;padding:5px 14px;font-size:.95rem;cursor:pointer}
.filter button.on{background:var(--pk);color:#fff}.btn{display:inline-block;background:var(--pk);color:#fff;border-radius:99px;padding:8px 18px;text-decoration:none;font-weight:700}
.pr{background:var(--pk2);border-radius:10px;padding:8px 12px;font-size:.88rem;margin:14px 0}footer{color:var(--mut);font-size:.88rem;padding-top:30px;padding-bottom:40px}
ul.l{padding-left:1.2em}.hide{display:none}
"""


def page(title, body, desc, path, base, head_extra=""):
    canon = f'<link rel="canonical" href="{base}/{path}">' if base else ""
    rel = "../" * path.count("/")
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{canon}
<meta property="og:title" content="{esc(title)}"><meta property="og:type" content="website"><meta property="og:locale" content="ja_JP">
<style>{CSS}</style>{head_extra}</head><body>
<header><a class="t" href="{rel}index.html">✿ {SITE}</a>
<nav><a href="{rel}index.html">イベント一覧</a><a href="{rel}venues/index.html">会場から探す</a><a href="{rel}facilities/index.html">撮影できる施設</a><a href="{rel}about.html">このサイトについて</a></nav></header>
<main>{body}</main>
<footer>
<p>イベントの日程・場所・参加条件は変更されることがあります。お出かけの前に、必ず各イベントの公式ページ・主催者の告知をご確認ください。</p>
<p>運営：ずっちー（東海のコスプレカメラマン）／ <a href="{NOTE}">note</a></p>
<p>Amazonのアソシエイトとして、ずっちーは適格販売により収入を得ています。</p></footer></body></html>"""


def card(e, show_venue=True):
    meta = [fmt(e)]
    if e["pref"]:
        meta.append(e["pref"] + "県")
    if e["place"] and show_venue:
        meta.append(e["place"])
    if e["time"]:
        meta.append(e["time"])
    if e["fee"]:
        meta.append("参加費：" + e["fee"])
    link = f' <a href="{esc(e["url"])}" rel="noopener" target="_blank">公式・主催ページ</a>' if e["url"] else ""
    note = f'<div class="m">{esc(e["note"])}</div>' if e["note"] else ""
    return (f'<div class="card" data-pref="{esc(e["pref"])}"><div class="n">{esc(e["name"])}{badge(e["status"])}</div>'
            f'<div class="m">{esc("｜".join(meta))}{link}</div>{note}</div>')


def ics(events):
    now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//tokai-cosplay-calendar//JP", "CALSCALE:GREGORIAN",
         "X-WR-CALNAME:東海コスプレイベント", "X-WR-TIMEZONE:Asia/Tokyo"]
    for e in events:
        a, b = d(e["date"]), d(e["end"] or e["date"])
        uid = hashlib.md5((e["date"] + e["name"]).encode()).hexdigest() + "@tokai-cosplay"
        desc = e["status"] + ("\\n" + e["url"] if e["url"] else "") + "\\n日程・場所は公式でご確認ください"
        L += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}", f"DTSTART;VALUE=DATE:{a:%Y%m%d}",
              f"DTEND;VALUE=DATE:{(b + datetime.timedelta(days=1)):%Y%m%d}",
              "SUMMARY:" + e["name"].replace(",", "\\,"), "LOCATION:" + (e["place"] or "").replace(",", "\\,"),
              "DESCRIPTION:" + desc.replace(",", "\\,"), "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    base = a.base.rstrip("/")
    data = json.load(open(os.path.join(HERE, "data/events.json")))
    today = d(a.today)
    evs = [e for e in data["events"] if d(e["end"] or e["date"]) >= today]
    evs.sort(key=lambda e: (e["date"], e["name"]))
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT + "/venues")
    open(OUT + "/.nojekyll", "w").close()
    sd = os.path.join(HERE, "static")
    if os.path.isdir(sd):
        for f in os.listdir(sd):
            shutil.copy(os.path.join(sd, f), os.path.join(OUT, f))
    open(OUT + "/events.ics", "w", newline="").write(ics(evs))
    PSLUG = {"愛知": "aichi", "静岡": "shizuoka", "岐阜": "gifu", "三重": "mie"}
    prefs = [p for p in PSLUG if any(e["pref"] == p for e in evs)] + sorted({e["pref"] for e in evs} - set(PSLUG))
    icsmap = {"": "events.ics"}
    for pf in prefs:
        fn = f"events-{PSLUG.get(pf, hashlib.md5(pf.encode()).hexdigest()[:6])}.ics"
        open(OUT + "/" + fn, "w", newline="").write(ics([e for e in evs if e["pref"] == pf]).replace("X-WR-CALNAME:東海コスプレイベント", f"X-WR-CALNAME:東海コスプレイベント（{pf}県）"))
        icsmap[pf] = fn
    # --- index
    months = {}
    for e in evs:
        months.setdefault(e["date"][:7], []).append(e)
    body = f"""<h1>東海のコスプレイベント予定</h1>
<p class="lead">愛知・静岡・岐阜・三重の東海4県で、これから開催されるコスプレイベントを日付順にまとめています（{data['asof']}時点／約3か月先まで）。岐阜・三重は一覧に載る数が少なめなので、見つけ次第追加します。</p>
<p><a class="btn" id="ics" href="events.ics">全イベントをカレンダーに登録（.ics）</a></p>
<p class="lead" style="font-size:.9rem">下の県ボタンで絞り込むと、その県のイベントだけの .ics をダウンロードできます。ダウンロードした .ics を、iPhoneのカレンダー・Googleカレンダーなどで開くと、一度にまとめて登録できます。</p>
<div class="filter" id="f"><button class="on" data-p="">すべて</button>{''.join(f'<button data-p="{esc(p)}">{esc(p)}県</button>' for p in prefs)}</div>"""
    for m, items in months.items():
        y, mo = m.split("-")
        body += f'<section class="mon"><h2>{y}年{int(mo)}月</h2>' + "".join(card(e) for e in items) + "</section>"
    body += f"""<div class="pr">※このページにはアフィリエイトリンク（PR）を含みます。</div>
<h2>イベントに行く前の準備</h2><p class="lead">Amazonの検索結果へのリンクです。</p><ul class="l">
<li><a href="{amz('貼るカイロ')}" rel="sponsored noopener">貼るカイロ</a></li>
<li><a href="{amz('ウィッグネット')}" rel="sponsored noopener">ウィッグネット</a></li>
<li><a href="{amz('モバイルバッテリー')}" rel="sponsored noopener">モバイルバッテリー</a></li>
<li><a href="{amz('レジャーシート 大判')}" rel="sponsored noopener">レジャーシート</a></li></ul>
<h2>「公式で確認済み」の見方</h2><ul class="l"><li><span class="b ok">公式で確認済み</span> 公式サイトで日程を確認できたもの</li>
<li><span class="b mid">主催の告知で確認</span> 主催者のSNSなどで告知を確認したもの</li>
<li><span class="b ng">公式で未確認</span> 一覧サイトにだけ載っていて、公式でまだ確認できていないもの</li></ul>
<script>
const ICS=__ICSMAP__;
const bs=document.querySelectorAll('#f button');bs.forEach(b=>b.onclick=()=>{{bs.forEach(x=>x.classList.remove('on'));b.classList.add('on');const p=b.dataset.p;const a=document.getElementById('ics');a.href=ICS[p];a.textContent=p?(p+'県のイベントをカレンダーに登録（.ics）'):'全イベントをカレンダーに登録（.ics）';
document.querySelectorAll('.card').forEach(c=>c.classList.toggle('hide',p&&c.dataset.pref!==p));
document.querySelectorAll('.mon').forEach(s=>s.classList.toggle('hide',![...s.querySelectorAll('.card')].some(c=>!c.classList.contains('hide'))));}});
</script>"""
    body = body.replace("__ICSMAP__", json.dumps(icsmap, ensure_ascii=False))
    open(OUT + "/index.html", "w").write(page(f"{SITE}｜愛知・静岡・岐阜・三重のイベント予定", body,
        "愛知・静岡・岐阜・三重など東海地方のコスプレイベントの予定を、日付順にまとめたカレンダーです。公式で確認できた情報かどうかも表示しています。", "index.html", base))
    # --- venues
    by = {}
    for e in evs:
        by.setdefault(venue_of(e) or "other", []).append(e)
    vi = {slug: (name, area) for _, name, slug, area in VENUES}
    items = ""
    for slug, es in sorted(by.items(), key=lambda kv: kv[1][0]["date"]):
        if slug == "other":
            continue
        name, area = vi[slug]
        items += f'<div class="card"><div class="n"><a href="{slug}.html">{esc(name)}</a></div><div class="m">{len(es)}件｜次回：{esc(fmt(es[0]))} {esc(es[0]["name"])}</div></div>'
        q = quote(name.split("（")[0])
        vb = f"""<h1>{esc(name)}のコスプレイベント</h1><p class="lead">{esc(name)}で開催が予定されているイベントです（{data['asof']}時点）。</p>
{''.join(card(e, False) for e in es)}
<p><a href="https://www.google.com/maps/search/?api=1&query={q}" rel="noopener" target="_blank">地図で場所を見る（Googleマップ）</a></p>
<p>撮影のルール・更衣室・入場方法はイベントごとに違います。必ず各イベントの公式ページで確認してください。</p>
<p><a href="../index.html">← イベント一覧へ戻る</a></p>"""
        open(f"{OUT}/venues/{slug}.html", "w").write(page(f"{name}のコスプレイベント｜{SITE}", vb,
            f"{name}で開催予定のコスプレイベントの一覧です。", f"venues/{slug}.html", base))
    open(OUT + "/venues/index.html", "w").write(page(f"会場から探す｜{SITE}",
        "<h1>会場から探す</h1><p class=\"lead\">これからイベントが予定されている会場です。</p>" + items, "コスプレイベントの会場ごとの予定一覧です。", "venues/index.html", base))

    # --- facilities
    fp = os.path.join(HERE, "data/facilities.json")
    fac_urls = []
    if os.path.exists(fp):
        fd = json.load(open(fp)); F = fd["facilities"]
        os.makedirs(OUT + "/facilities", exist_ok=True)
        def conf(f):
            return '<span class="b ok">公式で確認</span>' if f["confidence"] == "公式で確認" else '<span class="b ng">一覧サイトのみ</span>'
        def row(k, v):
            return f'<li><b>{k}</b>：{esc(v)}</li>' if v else ""
        cards = ""
        for f in F:
            cards += (f'<div class="card" data-pref="{esc(f["pref"])}" data-type="{esc(f["type"])}"><div class="n"><a href="{f["id"]}.html">{esc(f["name"])}</a>{conf(f)}</div>'
                      f'<div class="m">{esc(f["pref"])}県 {esc(f["city"])}｜{esc(f["type"])}</div><div class="m">{esc(f["features"])}</div></div>')
            ul = "".join([row("住所", f["address"]), row("アクセス", f["access"]), row("営業時間", f["hours"]), row("駐車場", f["parking"]),
                          row("コスプレのルール", f["cosplay_rule"] if f["cosplay_rule"] != "公式で確認" else "公式サイトで確認してください")])
            off = f'<p><a href="{esc(f["official_url"])}" rel="noopener" target="_blank">公式サイト</a></p>' if f["official_url"] else ""
            note = "" if f["confidence"] == "公式で確認" else '<p class="pr">この施設は、一覧サイトの情報をもとにしています。コスプレ撮影の可否や条件は、公式サイトまたは問い合わせで必ず確認してください。</p>'
            q = quote(f["name"])
            vb = (f'<h1>{esc(f["name"])}</h1><p class="lead">{esc(f["pref"])}県 {esc(f["city"])}｜{esc(f["type"])}（{conf(f)}）</p><p>{esc(f["features"])}</p>{note}'
                  f'<ul class="l">{ul}</ul>{off}<p><a href="https://www.google.com/maps/search/?api=1&query={q}" rel="noopener" target="_blank">地図で場所を見る（Googleマップ）</a></p>'
                  f'<p class="lead" style="font-size:.9rem">確認日：{esc(f["checked"])}。料金・営業時間・ルールは変わることがあります。</p><p><a href="index.html">← 施設の一覧へ戻る</a></p>')
            open(f"{OUT}/facilities/{f['id']}.html", "w").write(page(f"{f['name']}｜コスプレ撮影｜{SITE}", vb,
                f"{f['name']}（{f['pref']}県{f['city']}）のコスプレ撮影ルールとアクセス。", f"facilities/{f['id']}.html", base))
            fac_urls.append(f"facilities/{f['id']}.html")
        pb = "".join(f'<button data-p="{pf}">{pf}県</button>' for pf in ["愛知", "静岡", "岐阜", "三重"])
        tb = "".join(f'<button data-t="{t}">{t}</button>' for t in sorted({f["type"] for f in F}))
        ib = (f'<h1>東海でコスプレ撮影できる施設</h1><p class="lead">愛知・静岡・岐阜・三重で、コスプレ撮影ができるスタジオ・公園・施設をまとめています（{fd["asof"]}時点／{len(F)}件）。'
              f'「公式で確認」は公式サイトで可否や条件を確認できたもの、「一覧サイトのみ」は一覧サイトの情報だけのものです。三重は確認できた施設が少なめです。</p>'
              f'<div class="filter" id="fp"><button class="on" data-p="">すべて</button>{pb}</div><div class="filter" id="ft"><button class="on" data-t="">すべての種類</button>{tb}</div>'
              f'<div id="cards">{cards}</div><script>let P="",T="";function ap(){{document.querySelectorAll("#cards .card").forEach(c=>c.classList.toggle("hide",(P&&c.dataset.pref!==P)||(T&&c.dataset.type!==T)))}}'
              f'document.querySelectorAll("#fp button").forEach(b=>b.onclick=()=>{{document.querySelectorAll("#fp button").forEach(x=>x.classList.remove("on"));b.classList.add("on");P=b.dataset.p;ap()}});'
              f'document.querySelectorAll("#ft button").forEach(b=>b.onclick=()=>{{document.querySelectorAll("#ft button").forEach(x=>x.classList.remove("on"));b.classList.add("on");T=b.dataset.t;ap()}});</script>'
              f'<p class="lead">掲載してほしい施設・間違いは、<a href="{NOTE}">note</a> のコメントからお知らせください。</p>')
        open(OUT + "/facilities/index.html", "w").write(page(f"東海でコスプレ撮影できる施設｜{SITE}", ib,
            "愛知・静岡・岐阜・三重のコスプレ撮影スタジオ・公園・施設の一覧。公式で確認できた情報かどうかも表示。", "facilities/index.html", base))
        fac_urls.append("facilities/index.html")
    # --- about
    ab = f"""<h1>このサイトについて</h1>
<p>愛知・静岡・岐阜・三重の東海4県で開催されるコスプレイベントの予定をまとめています。運営しているのは、東海のイベントで撮影している、コスプレカメラマンのずっちーです。</p>
<h2>情報の集め方</h2><ul class="l"><li>イベントの一覧サイトと、主催者の公式サイト・告知で、日程や場所を確認しています。</li>
<li>公式で確認できたかどうかを、各イベントに表示しています。</li><li>情報は変わることがあります。お出かけの前に、必ず公式ページをご確認ください。</li></ul>
<h2>個人情報について</h2><p>このサイトには、参加者・個人のアカウントの情報は載せていません。</p>
<h2>広告・アフィリエイト</h2><p>このサイトには、Amazonアソシエイトのリンク（PR）が含まれます。Amazonのアソシエイトとして、ずっちーは適格販売により収入を得ています。</p>
<h2>連絡先・ほかの発信</h2><p>情報の間違いなどは、<a href="{NOTE}">note</a> のコメントからお知らせください。</p>"""
    open(OUT + "/about.html", "w").write(page(f"このサイトについて｜{SITE}", ab, "サイトの運営者、情報の集め方、広告について。", "about.html", base))
    # --- sitemap / robots
    if base:
        urls = ["index.html", "about.html", "venues/index.html"] + fac_urls + [f"venues/{s}.html" for s in by if s != "other"]
        open(OUT + "/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
            "".join(f"<url><loc>{base}/{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>")
        open(OUT + "/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    print(f"events={len(evs)} venues={len([s for s in by if s!='other'])} other={len(by.get('other',[]))} -> {OUT}")
    if "other" in by:
        for e in by["other"]:
            print("  会場未分類:", e["name"], e["place"])


if __name__ == "__main__":
    main()

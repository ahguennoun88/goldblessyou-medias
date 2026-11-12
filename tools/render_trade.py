#!/usr/bin/env python3
"""
render_trade.py - GOLDBLESSYOU
Carrousel Instagram (4 slides JPEG 1080x1350) pour un trade du bot, a partir du JSON trade_*.json
et (optionnel) du JSON daily pour le graphique H1 et le contexte.

Exemple :
  python3 render_trade.py --trade snapshots/trade_2026-11-12_trade24.json \
      --daily snapshots/0900/daily_2026-11-12.json --context snapshots/daily_2026-11-12.json --out posts/2026-11-12_trade24

Aucune donnee inventee : tout vient des JSON du bot ; un champ absent est omis.
Slides : 1 couverture · 2 plan (entree / stop / objectif / R:R) · 3 graphique H1 · 4 contexte du bot + suite.
Necessite Playwright (python) avec Chromium.
"""
import argparse
import html
import json
from datetime import date
from pathlib import Path

HANDLE = "@goldblessyou.xau"
GOLD, BULL, BEAR, MUTED, INK = "#D9B44A", "#5FD38D", "#FF7A5C", "#A69F90", "#F5F1E8"
e = html.escape


def money(x):
    return f"${x:,.2f}"


def page(n, total, body, last=False):
    foot = (f'<div style="font-size:20px;color:{MUTED};text-align:center;line-height:1.4">Personal view — not financial advice. '
            f'Trading involves risk of loss.<br>Every trade of the bot is published, wins and losses.</div>'
            f'<div style="font-family:\'Space Grotesk\';font-size:30px;font-weight:600;text-align:center">{HANDLE}</div>'
            if last else
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="font-family:\'Space Grotesk\';font-size:28px;font-weight:600">{HANDLE}</span>'
            f'<span style="font-size:26px;color:{GOLD};font-weight:600">Swipe →</span></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=block" rel="stylesheet">
<style>body{{margin:0;background:#0F0E0C}} .card{{background:#1A1815;border:1px solid #2E2A22;border-radius:28px}}
.lbl{{font-size:20px;letter-spacing:.16em;text-transform:uppercase;color:{MUTED};font-weight:600}}
.num{{font-family:'Space Grotesk',sans-serif;font-weight:700;font-variant-numeric:tabular-nums}}</style></head><body>
<div style="width:1080px;height:1350px;box-sizing:border-box;padding:72px 72px 64px;background:#0F0E0C;color:{INK};
font-family:Inter,sans-serif;display:flex;flex-direction:column;justify-content:space-between">
<div style="display:flex;justify-content:space-between;font-size:22px;letter-spacing:.2em;font-weight:600">
<span style="color:{GOLD}">GOLDBLESSYOU · TRADE</span><span style="color:{MUTED}">{n} / {total}</span></div>
<div style="display:flex;flex-direction:column;gap:28px">{body}</div>
<div style="display:flex;flex-direction:column;gap:14px">{foot}</div></div></body></html>"""


def chart_svg(candles, lines, W=936, H=640):
    cs = [c for c in candles if None not in (c.get("o"), c.get("h"), c.get("l"), c.get("c"))]
    L, R, T, B = 4, 150, 14, 40
    vals = [c["h"] for c in cs] + [c["l"] for c in cs] + [v for _, v, _, _ in lines]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.05 or 1
    lo, hi = lo - pad, hi + pad
    step = (W - L - R) / len(cs)
    X = lambda i: L + step * (i + 0.5)
    Y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)
    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" font-family="Inter, sans-serif">']
    for i, c in enumerate(cs):
        hh = c["t"][11:16]
        if hh.endswith(":00") and int(hh[:2]) % 6 == 0 and X(i) > 30:
            s.append(f'<line x1="{X(i):.1f}" y1="{T}" x2="{X(i):.1f}" y2="{H-B}" stroke="#2E2A22"/>')
            s.append(f'<text x="{X(i):.1f}" y="{H-10}" fill="#7D776B" font-size="20" text-anchor="middle">{hh}</text>')
    used = []
    for name, v, col, dash in sorted(lines, key=lambda x: -x[1]):
        y = ly = Y(v)
        for u in used:
            if abs(ly - u) < 52:
                ly = u + 52
        used.append(ly)
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R+4}" y2="{y:.1f}" stroke="{col}" stroke-width="2.5" stroke-dasharray="{dash}"/>')
        s.append(f'<rect x="{W-R+12}" y="{ly-21:.1f}" width="6" height="42" rx="3" fill="{col}"/>')
        s.append(f'<text x="{W-R+26}" y="{ly-3:.1f}" fill="{MUTED}" font-size="19">{e(name)}</text>')
        s.append(f'<text x="{W-R+26}" y="{ly+21:.1f}" fill="{INK}" font-size="23" font-weight="700" '
                 f'font-family="Space Grotesk, sans-serif">{v:,.2f}</text>')
    bw = step * 0.62
    for i, c in enumerate(cs):
        col = BULL if c["c"] >= c["o"] else BEAR
        x = X(i)
        s.append(f'<line x1="{x:.1f}" y1="{Y(c["h"]):.1f}" x2="{x:.1f}" y2="{Y(c["l"]):.1f}" stroke="{col}" stroke-width="2"/>')
        top, bot = Y(max(c["o"], c["c"])), Y(min(c["o"], c["c"]))
        s.append(f'<rect x="{x-bw/2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(bot-top, 2):.1f}" rx="2" fill="{col}"/>')
    s.append("</svg>")
    return "".join(s)


def build(t, daily, ctx):
    side = t["side"]
    scol = BEAR if side == "SELL" else BULL
    d = date.fromisoformat(t["opened_at"][:10])
    when = d.strftime("%a, %b ") + str(d.day) + d.strftime(", %Y") + f" · {t['opened_at'][-5:]} CET"
    tags = " · ".join(x for x in (t.get("strategy") and t["strategy"].capitalize(),
                                   t.get("setup") and f"setup {t['setup']}",
                                   t.get("session") and f"{t['session'].capitalize()} session") if x)
    status = {"open": ("OPEN", GOLD), "win": ("WIN", BULL), "loss": ("LOSS", BEAR),
              "breakeven": ("BREAK-EVEN", MUTED)}.get(t.get("outcome"), ("", MUTED))
    verb = "Selling" if side == "SELL" else "Buying"
    s1 = f"""<div class="lbl">{e(when)}</div>
<div style="font-family:'Space Grotesk';font-size:150px;line-height:.95;font-weight:700;letter-spacing:-.03em">Trade<br>#{t['trade_no']}</div>
<div style="font-family:'Space Grotesk';font-size:96px;line-height:1;font-weight:700;color:{scol}">{verb} gold.</div>
<div style="font-size:30px;color:{MUTED}">XAU/USD · {e(tags)}</div>
<div><span style="display:inline-block;padding:12px 26px;border:2px solid {status[1]};border-radius:999px;color:{status[1]};
font-size:26px;font-weight:600;letter-spacing:.14em">{status[0]}</span></div>"""

    tile = lambda lbl, v, sub, col: (f'<div class="card" style="padding:26px 30px;display:flex;justify-content:space-between;align-items:center">'
                                     f'<div style="display:flex;flex-direction:column;gap:8px"><span class="lbl">{lbl}</span>'
                                     f'<span class="num" style="font-size:58px;color:{col}">{money(v)}</span></div>'
                                     f'<span style="font-size:26px;color:{MUTED};text-align:right">{sub}</span></div>')
    sd, td = t.get("sl_distance_usd"), t.get("tp_distance_usd")
    rows = [tile("Entry", t["entry"], f"{side} · {t['opened_at'][-5:]} CET", INK)]
    if t.get("stop_loss") is not None:
        rows.append(tile("Stop loss", t["stop_loss"], f"risk {money(sd)}" if sd else "", BEAR))
    if t.get("take_profit") is not None:
        rows.append(tile("Target", t["take_profit"], f"reward {money(td)}" if td else "", BULL))
    rr = t.get("rr_planned")
    s2 = (f'<div style="font-family:\'Space Grotesk\';font-size:72px;font-weight:700">The plan</div>' + "".join(rows) +
          (f'<div style="display:flex;align-items:baseline;gap:24px"><span class="lbl">Reward / risk</span>'
           f'<span class="num" style="font-size:84px;color:{GOLD}">1 : {rr:g}</span></div>' if rr else "") +
          f'<div style="font-size:26px;color:{MUTED}">Distances in USD per ounce of gold. Stop and target are set by the bot at entry.</div>')

    s3 = ""
    if daily and daily.get("candles_h1"):
        lines = [("Entry", t["entry"], GOLD, "3 7")]
        if t.get("stop_loss") is not None:
            lines.append(("Stop loss", t["stop_loss"], BEAR, "10 8"))
        if t.get("take_profit") is not None:
            lines.append(("Target", t["take_profit"], BULL, "10 8"))
        cl = (ctx or {}).get("levels") or {}
        if cl.get("key_support_src") == "swing_low" and cl.get("key_support") is not None and cl["key_support"] > t["entry"]:
            lines.append(("Broken low", cl["key_support"], MUTED, "14 8"))
        s3 = (f'<div style="font-family:\'Space Grotesk\';font-size:72px;font-weight:700">The chart</div>'
              f'<div class="card" style="padding:26px 22px 14px 26px"><div class="lbl" style="margin-bottom:12px">H1 · last '
              f'{len(daily["candles_h1"])} candles · last one {daily["candles_h1"][-1]["t"][-5:]} CET · bot data</div>'
              f'{chart_svg(daily["candles_h1"], lines)}</div>')

    a = (ctx or {}).get("analysis") or {}
    lv = (ctx or {}).get("levels") or {}
    pts = []
    if a.get("h4_bias"):
        pts.append(("H4 trend", f"{a['h4_bias'].capitalize()}", f"bot bias at {a['analysis_at'][-5:]} CET",
                    BEAR if a["h4_bias"] == "bearish" else BULL))
    if a.get("adx") is not None:
        pts.append(("Trend strength", f"ADX {a['adx']:.1f}", f"H1 at {a['analysis_at'][-5:]} CET · above 25 = trending market", INK))
    if lv.get("ema50") is not None and a.get("price") is not None:
        pos = "below" if a["price"] < lv["ema50"] else "above"
        pts.append(("Price vs EMA 50", f"{pos.capitalize()} {money(lv['ema50'])}", f"H1 · price {money(a['price'])} at {a['analysis_at'][-5:]} CET", INK))
    brk = None
    if daily and lv.get("key_support_src") == "swing_low" and lv.get("key_support") is not None:
        before = [c for c in daily.get("candles_h1") or [] if c["t"] < t["opened_at"]]
        if before and before[-1]["c"] < lv["key_support"]:
            brk = (f"The {before[-1]['t'][-5:]} candle closed at {money(before[-1]['c'])}, "
                   f"below the {money(lv['key_support'])} swing low.")
    if brk:
        pts.append(("Trigger", "Breakout", brk, GOLD))
    cards = "".join(f'<div class="card" style="padding:24px 30px;display:flex;flex-direction:column;gap:6px">'
                    f'<span class="lbl">{e(l)}</span><span class="num" style="font-size:44px;color:{c}">{e(v)}</span>'
                    f'<span style="font-size:24px;color:{MUTED}">{e(sub)}</span></div>' for l, v, sub, c in pts)
    s4 = (f'<div style="font-family:\'Space Grotesk\';font-size:72px;font-weight:700">Why the bot {side.lower()}s</div>{cards}'
          f'<div class="card" style="padding:24px 30px;border-color:{GOLD}"><span style="font-size:28px">Result posted when the '
          f'trade closes — <span style="color:{GOLD}">win or loss</span>.</span></div>')
    slides = [s1, s2] + ([s3] if s3 else []) + [s4]
    return [page(i + 1, len(slides), b, last=(i == len(slides) - 1)) for i, b in enumerate(slides)]


def render(pages, outdir):
    from playwright.sync_api import sync_playwright
    outdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for i, h in enumerate(pages, 1):
            tmp = outdir / f"_slide{i}.html"
            tmp.write_text(h, encoding="utf-8")
            pg.goto(tmp.resolve().as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.screenshot(path=str(outdir / f"slide{i}.jpg"), type="jpeg", quality=92,
                          clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            tmp.unlink()
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade", required=True, help="trade_YYYY-MM-DD_tradeN.json")
    ap.add_argument("--daily", help="daily JSON dont les bougies H1 servent au graphique")
    ap.add_argument("--context", help="daily JSON de l'analyse avant l'entree (biais, ADX, EMA, swing low) ; defaut = --daily")
    ap.add_argument("--out", required=True, help="dossier de sortie (slide1.jpg ...)")
    a = ap.parse_args()
    t = json.loads(Path(a.trade).read_text(encoding="utf-8"))["trade"]
    daily = json.loads(Path(a.daily).read_text(encoding="utf-8")) if a.daily else None
    ctx = json.loads(Path(a.context).read_text(encoding="utf-8")) if a.context else daily
    pages = build(t, daily, ctx)
    render(pages, Path(a.out))
    print(f"OK {a.out} ({len(pages)} slides)")


if __name__ == "__main__":
    main()

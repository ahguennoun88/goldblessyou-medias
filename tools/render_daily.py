#!/usr/bin/env python3
"""
render_daily.py - GOLDBLESSYOU
Genere la story Daily (JPEG 1080x1920) a partir du JSON daily du bot et des infos du Daily Market Watch.

Exemple :
  python3 render_daily.py --json daily_2026-11-09.json --out 2026-11-09_daily.jpg \
      --prev-close 4070.10 --prev-close-pct -0.42 --prev-day Fri \
      --catalyst-title "US CPI · Tue 14:30 CET" --catalyst-desc "October US inflation report — tier-1 release"

Aucune donnee inventee : sans --prev-close la pastille est omise, sans --catalyst-title le bloc catalyseur est omis.
Le biais affiche est UNIQUEMENT celui du bot (H4).
Graphique : si candles_h1 est present, chandeliers H1 + resistance / pivot / cloture veille / support
(remplace les tuiles de niveaux) ; cloture veille lue dans prev_close du JSON si --prev-close absent.
Niveaux cles : lus dans levels du JSON (key_resistance|resistance_vwap_daily, ema50 (H1, ou ema50_tf), key_support) ; nuls -> omis.
Necessite Playwright (python) avec Chromium.
"""
import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path
from string import Template

HANDLE = "@goldblessyou.xau"
GOLD, BULL, BEAR, NEUTRAL = "#D9B44A", "#5FD38D", "#FF7A5C", "#C9C2B3"
REGIMES = {"trend": "Trend", "weak_trend": "Weak trend", "range": "Range", "compression": "Compression"}
ICON_UP = '<path d="M3 17l6-6 4 4 8-8"></path><path d="M21 13V7h-6"></path>'
ICON_DOWN = '<path d="M3 7l6 6 4-4 8 8"></path><path d="M21 11v6h-6"></path>'
ICON_FLAT = '<path d="M3 12h18"></path>'

PAGE = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Daily $date_iso</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Space+Grotesk:wght@500;600;700&amp;display=block" rel="stylesheet">
<style>body{margin:0;background:#0F0E0C}</style></head><body>
<div style="width: 1080px; height: 1920px; box-sizing: border-box; background: #0F0E0C; color: #F5F1E8; font-family: Inter, system-ui, sans-serif; padding: $pad_top 88px $pad_bottom; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden">
<div style="display: flex; flex-direction: column; gap: $gap">
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 26px; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 600">
<span style="color: #D9B44A">Daily · Gold</span><span style="color: #A69F90">$date_label</span></div>
<div style="display: flex; flex-direction: column; gap: 8px">
<div style="font-family: 'Space Grotesk', sans-serif; font-size: 52px; font-weight: 600; letter-spacing: 0.02em">XAU/USD</div>
<div style="font-family: 'Space Grotesk', sans-serif; font-size: $price_size; line-height: 1; font-weight: 700; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; color: #D9B44A">$price</div>
<div style="font-size: 28px; color: #A69F90">Personal Analysis · $time CET</div>
<div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px">$pills</div></div>
<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 36px; padding: $bias_pad; display: flex; flex-direction: column; gap: $bias_gap">
<span style="font-size: 26px; letter-spacing: 0.16em; text-transform: uppercase; color: #A69F90; font-weight: 600">H4 bias</span>
<div style="display: flex; align-items: center; gap: 20px; font-family: 'Space Grotesk', sans-serif; font-size: $bias_size; line-height: 1; font-weight: 700; color: $bias_color">
<svg width="$bias_icon" height="$bias_icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">$bias_paths</svg>$bias_label</div>
<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px">$tiles</div></div>
<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 28px; padding: 26px 36px; display: flex; align-items: center; justify-content: space-between; gap: 24px">
<span style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 22px; letter-spacing: 0.16em; text-transform: uppercase; color: #A69F90; font-weight: 600">Bot decision · $time CET</span><span style="font-size: 26px">$decision_text</span></span>
<span style="font-family: 'Space Grotesk', sans-serif; font-size: 56px; line-height: 1; font-weight: 700; color: $decision_color">$decision</span></div>
$levels
$catalyst
</div>
<div style="display: flex; flex-direction: column; gap: 12px; align-items: center; text-align: center">
<span style="font-family: 'Space Grotesk', sans-serif; font-size: 34px; font-weight: 600">$handle</span>
<span style="font-size: 24px; color: #A69F90">Personal view — Not financial advice (NFA)</span></div>
</div></body></html>""")

PILL = ('<span style="display: inline-flex; align-items: center; padding: 12px 22px; border-radius: 999px; '
        'background: #1A1815; color: #C9C2B3; font-size: 26px; font-variant-numeric: tabular-nums">{}</span>')
TILE = ('<div style="background: #0F0E0C; border-radius: 24px; padding: 22px 26px; display: flex; flex-direction: column; gap: 6px">'
        '<span style="font-size: 22px; color: #A69F90">{}</span><span style="font-family: \'Space Grotesk\', sans-serif; '
        'font-size: {}px; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums">{}</span></div>')
CATALYST = Template("""<div style="border: 2px solid #D9B44A; border-radius: 36px; padding: 30px 40px; display: flex; align-items: center; gap: 32px">
<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#D9B44A" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>
<div style="display: flex; flex-direction: column; gap: 6px">
<span style="font-size: 24px; letter-spacing: 0.16em; text-transform: uppercase; color: #A69F90; font-weight: 600">Next catalyst</span>
<span style="font-family: 'Space Grotesk', sans-serif; font-size: $size; line-height: 1; font-weight: 700; color: #D9B44A">$title</span>
<span style="font-size: 26px">$desc</span></div></div>""")
LEVELS = Template("""<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 36px; padding: 30px 40px; display: flex; flex-direction: column; gap: 20px">
<span style="font-size: 24px; letter-spacing: 0.16em; text-transform: uppercase; color: #A69F90; font-weight: 600">Key levels · bot</span>
<div style="display: grid; grid-template-columns: repeat($n, minmax(0, 1fr)); gap: 20px">$tiles</div></div>""")
LEVEL_TILE = ('<div style="background: #0F0E0C; border-radius: 24px; padding: 20px 24px; display: flex; flex-direction: column; gap: 6px">'
              '<span style="font-size: 22px; color: {}">{}</span><span style="font-family: \'Space Grotesk\', sans-serif; '
              'font-size: 36px; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums">{}</span></div>')


def first(d, *keys):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


def build_levels(levels):
    """Bloc niveaux cles, lu UNIQUEMENT dans levels du JSON du bot. Valeur nulle -> tuile omise ; tout nul -> bloc omis."""
    levels = levels or {}
    ema_tf = levels.get("ema50_tf") or "H1"  # EMA 50 du bot = H1 par defaut
    items = [("Resistance", BEAR, first(levels, "key_resistance", "resistance", "resistance_vwap_daily")),
             (f"EMA 50 ({ema_tf})" if ema_tf else "EMA 50", GOLD, first(levels, "ema50", "ema_50")),
             ("Support", BULL, first(levels, "key_support", "support"))]
    tiles = [LEVEL_TILE.format(c, html.escape(lbl), money(float(v))) for lbl, c, v in items if v is not None]
    if not tiles:
        return ""
    return LEVELS.substitute(n=len(tiles), tiles="".join(tiles))


def build_chart(candles, levels, prev_close):
    """Graphique H1 en chandeliers (candles_h1 du JSON) + resistance / pivot du jour / cloture veille / support.
    Toutes les valeurs viennent du JSON du bot ; un niveau nul n'est pas trace. Aucune bougie -> chaine vide."""
    cs = [c for c in (candles or []) if None not in (c.get("o"), c.get("h"), c.get("l"), c.get("c"))]
    if len(cs) < 2:
        return ""
    levels = levels or {}
    src = lambda base, k: {"swing_high": "Swing high", "swing_low": "Swing low"}.get(
        levels.get(k), f"{base} {levels[k]}" if levels.get(k) else base)
    lines = [(src("Resistance", "key_resistance_src"), first(levels, "key_resistance", "resistance"), BEAR, "8 8"),
             ("Daily pivot", (levels.get("pivots") or {}).get("pivot"), GOLD, "3 7"),
             (f"{prev_close['day']} close" if prev_close and prev_close.get("day") else "Prev. close",
              (prev_close or {}).get("value"), "#A69F90", "14 8"),
             (src("Support", "key_support_src"), first(levels, "key_support", "support"), BULL, "8 8")]
    lines = [x for x in lines if x[1] is not None]
    W, H, L, R, T, B = 900, 470, 4, 132, 16, 40
    vals = [c["h"] for c in cs] + [c["l"] for c in cs] + [v for _, v, _, _ in lines]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    n = len(cs)
    step = (W - L - R) / n
    X = lambda i: L + step * (i + 0.5)
    Y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)
    svg = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block" font-family="Inter, sans-serif">']
    for i, c in enumerate(cs):
        hh = c["t"][11:16]
        if hh.endswith(":00") and int(hh[:2]) % 6 == 0 and X(i) > 30:
            svg.append(f'<line x1="{X(i):.1f}" y1="{T}" x2="{X(i):.1f}" y2="{H-B}" stroke="#2E2A22" stroke-width="1"/>')
            svg.append(f'<text x="{X(i):.1f}" y="{H-12}" fill="#7D776B" font-size="20" text-anchor="middle">{hh}</text>')
    used = []
    for name, v, col, dash in sorted(lines, key=lambda x: -x[1]):
        y = ly = Y(v)
        for u in used:                       # etiquettes sans chevauchement
            if abs(ly - u) < 52:
                ly = u + 52
        used.append(ly)
        svg.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R+4}" y2="{y:.1f}" stroke="{col}" stroke-width="2" stroke-dasharray="{dash}"/>')
        svg.append(f'<rect x="{W-R+12}" y="{ly-19:.1f}" width="6" height="38" rx="3" fill="{col}"/>')
        svg.append(f'<text x="{W-R+24}" y="{ly-3:.1f}" fill="#A69F90" font-size="18">{html.escape(name)}</text>')
        svg.append(f'<text x="{W-R+24}" y="{ly+19:.1f}" fill="#F4EFE6" font-size="22" font-weight="700" '
                   f'font-family="Space Grotesk, sans-serif">{v:,.2f}</text>')
    bw = step * 0.62
    for i, c in enumerate(cs):
        col = BULL if c["c"] >= c["o"] else BEAR
        x = X(i)
        svg.append(f'<line x1="{x:.1f}" y1="{Y(c["h"]):.1f}" x2="{x:.1f}" y2="{Y(c["l"]):.1f}" stroke="{col}" stroke-width="2"/>')
        top, bot = Y(max(c["o"], c["c"])), Y(min(c["o"], c["c"]))
        svg.append(f'<rect x="{x-bw/2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(bot-top, 2):.1f}" rx="2" fill="{col}"/>')
    svg.append("</svg>")
    chg = (cs[-1]["c"] - cs[0]["o"]) / cs[0]["o"] * 100
    return (f'<div style="background:#1A1815;border:1px solid #2E2A22;border-radius:36px;padding:28px 30px 18px 34px;'
            f'display:flex;flex-direction:column;gap:14px"><div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<span style="font-size:24px;letter-spacing:.16em;text-transform:uppercase;color:#A69F90;font-weight:600">'
            f'H1 · last {n}h · bot</span><span style="font-size:26px;font-weight:700;color:{BULL if chg >= 0 else BEAR};'
            f'font-variant-numeric:tabular-nums">{"+" if chg >= 0 else "−"}{abs(chg):.2f}%</span></div>{"".join(svg)}</div>')


def money(x):
    return f"${x:,.2f}"


def build_html(a, ref, prev_close, prev_pct, prev_day, cat_title, cat_desc, levels=None, candles=None, prev_obj=None):
    e = html.escape
    bias = (a.get("h4_bias") or "").lower()
    if bias == "bullish":
        bias_label, bias_color, bias_icon = "Bullish", BULL, ICON_UP
    elif bias == "bearish":
        bias_label, bias_color, bias_icon = "Bearish", BEAR, ICON_DOWN
    else:
        bias_label, bias_color, bias_icon = "Neutral", NEUTRAL, ICON_FLAT

    decision = (a.get("decision") or "HOLD").upper()
    decision_text = {"HOLD": "No entry signal — waiting for a setup",
                     "BUY": "Long entry signal — see trade story",
                     "SELL": "Short entry signal — see trade story"}.get(decision, "See trade story")
    decision_color = {"BUY": BULL, "SELL": BEAR}.get(decision, GOLD)

    chart = build_chart(candles, levels, prev_obj or ({'value': prev_close, 'day': prev_day} if prev_close is not None else None))
    pills = []
    if prev_close is not None and not chart:  # avec le graphique, la cloture veille est tracee dessus
        txt = f"{e(prev_day)} close: {money(prev_close)}"
        if prev_pct is not None:
            txt += f" ({'+' if prev_pct >= 0 else '−'}{abs(prev_pct):.2f}%)"
        pills.append(PILL.format(txt))
    if a.get("atr") is not None:
        pills.append(PILL.format(f"ATR (H1): {a['atr']:.2f}"))

    regime = REGIMES.get(a.get("regime") or "", (a.get("regime") or "—").replace("_", " ").capitalize())
    big = 34 if chart else 40
    tile = TILE.replace("padding: 22px 26px", "padding: 14px 22px") if chart else TILE
    tiles = [tile.format("ADX (H1)", big, "—" if a.get("adx") is None else f"{a['adx']:.1f}"),
             tile.format("RSI (H1)", big, "—" if a.get("rsi") is None else f"{a['rsi']:.1f}"),
             tile.format("Regime", (30 if chart else 34) if len(regime) > 6 else big, e(regime))]

    catalyst = ""
    if cat_title:
        size = "56px" if len(cat_title) <= 24 else "44px"
        catalyst = CATALYST.substitute(size=size, title=e(cat_title), desc=e(cat_desc or ""))

    lv = chart or build_levels(levels)  # graphique si bougies, sinon tuiles ; bloc niveaux : mise en page resserree pour garder la zone basse libre
    time_txt = (a.get("analysis_at") or "07:00")[-5:]
    return PAGE.substitute(
        date_iso=ref.isoformat(), date_label=ref.strftime("%a, %b ") + str(ref.day) + ref.strftime(", %Y"),
        price=money(a["price"]), time=time_txt, pills="".join(pills),
        bias_color=bias_color, bias_paths=bias_icon, bias_label=bias_label, tiles="".join(tiles),
        decision=e(decision), decision_text=e(decision_text), decision_color=decision_color,
        levels=lv, catalyst=catalyst, handle=HANDLE,
        pad_top="170px" if chart else ("180px" if lv else "250px"), pad_bottom="250px" if chart else ("290px" if lv else "340px"),
        gap="20px" if chart else ("22px" if lv else "30px"),
        bias_pad="22px 36px" if chart else ("30px 40px" if lv else "40px"),
        bias_gap="14px" if chart else "24px", bias_size="56px" if chart else "80px", bias_icon=44 if chart else 64,
        price_size="112px" if chart else ("124px" if lv else "150px"))


def render(html_text, out_path):
    from playwright.sync_api import sync_playwright
    tmp = Path(out_path).with_suffix(".html")
    tmp.write_text(html_text, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        pg.goto(tmp.resolve().as_uri(), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(out_path), type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
        b.close()
    tmp.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="snapshots/daily_YYYY-MM-DD.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prev-close", type=float)
    ap.add_argument("--prev-close-pct", type=float)
    ap.add_argument("--prev-day", default="Prev.")
    ap.add_argument("--catalyst-title")
    ap.add_argument("--catalyst-desc")
    a = ap.parse_args()
    doc = json.loads(Path(a.json).read_text(encoding="utf-8"))
    analysis = doc.get("analysis")
    if not analysis or analysis.get("price") is None:
        sys.exit(f"Pas d'analyse exploitable dans {a.json} : {doc.get('warnings')}")
    ref = date.fromisoformat(doc["reference_date"])
    pc = doc.get("prev_close") or {}
    if a.prev_close is None and pc.get("value") is not None:   # cloture veille du bot (bougies_h1) par defaut
        a.prev_close, a.prev_close_pct, a.prev_day = pc["value"], pc.get("pct"), pc.get("day") or a.prev_day
    prev_obj = {"value": a.prev_close, "pct": a.prev_close_pct, "day": a.prev_day} if a.prev_close is not None else None
    render(build_html(analysis, ref, a.prev_close, a.prev_close_pct, a.prev_day, a.catalyst_title, a.catalyst_desc,
                      doc.get("levels"), doc.get("candles_h1"), prev_obj), a.out)
    print(f"OK {a.out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
render_trade_story.py - GOLDBLESSYOU
Stories 1080x1920 « Trade of the day » (ouverture) et « Trade closed » (cloture), reprises des templates valides
du canvas « Story XAUUSD 6 nov » (Trade.dc.html, Close.dc.html).

Exemples :
  python3 render_trade_story.py --trade snapshots/trade_2026-11-12_trade24.json \
      --context snapshots/daily_2026-11-12.json --out stories/2026-11-12_trade24_open.jpg
  python3 render_trade_story.py --trade snapshots/trade_2026-11-13_trade24.json --close \
      --lesson "..." --out stories/2026-11-13_trade24_close.jpg

Aucune donnee inventee : tout vient des JSON du bot (trade + daily de contexte) ; un champ absent est omis.
--why / --risk / --lesson remplacent ou completent les lignes de texte (validees par Ahmed).
"""
import argparse
import html
import json
from datetime import date, datetime
from pathlib import Path

HANDLE = "@goldblessyou.xau"
ACCENT, BULL, BEAR, MUTED, INK = "#D9B44A", "#5FD38D", "#FF7A5C", "#A69F90", "#F5F1E8"
e = html.escape
CHECK = (f'<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="2.5" '
         f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg>')
WARN = ('<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l10 18H2z"></path>'
        '<path d="M12 10v5"></path><path d="M12 18h.01"></path></svg>')


def px(v):
    return f"{v:,.2f}"


def day_label(s):
    d = date.fromisoformat(s[:10])
    return d.strftime("%a, %b ") + str(d.day) + d.strftime(", %Y")


FMT = {"h": 1920, "pad": "250px 88px 340px", "gap": "32px", "tall": "180px"}


def shell(body, header_left, header_right):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Space+Grotesk:wght@500;600;700&amp;display=block" rel="stylesheet">
<style>body{{margin:0;background:#0F0E0C}}</style></head><body>
<div style="width: 1080px; height: {FMT['h']}px; box-sizing: border-box; background: #0F0E0C; color: {INK}; font-family: Inter, system-ui, sans-serif; padding: {FMT['pad']}; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden">
<div style="display: flex; flex-direction: column; gap: {FMT['gap']}">
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 26px; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 600">
<span style="color: {ACCENT}">{e(header_left)}</span><span style="color: {MUTED}">{e(header_right)}</span></div>
{body}
</div>
<div style="display: flex; flex-direction: column; gap: 12px; align-items: center; text-align: center">
<span style="font-family: 'Space Grotesk', sans-serif; font-size: 34px; font-weight: 600; color: {INK}">{HANDLE}</span>
<span style="font-size: 24px; color: {MUTED}">Personal view — Not financial advice (NFA)</span></div>
</div></body></html>"""


def pill(text, fg, bg, dot=False, upper=False):
    d = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle></svg>'
         if dot else "")
    up = "font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;" if upper else ""
    return (f'<span style="display: inline-flex; align-items: center; gap: 10px; padding: 12px 22px; border-radius: 999px; '
            f'background: {bg}; color: {fg}; font-size: 26px; {up} font-variant-numeric: tabular-nums">{d}{e(text)}</span>')


def setup_line(t):
    parts = [f"{t['strategy'].capitalize()} setup" if t.get("strategy") else None, "H1"]
    return " · ".join(p for p in parts if p)


# ------------------------------------------------------------------ contexte (daily du bot)
def context_lines(t, ctx):
    """Raisons et risque tires du daily d'analyse le plus proche AVANT l'entree. Rien d'invente."""
    why, risk = [], []
    if not ctx:
        return why, risk
    a, lv = ctx.get("analysis") or {}, ctx.get("levels") or {}
    sell = t["side"] == "SELL"
    if a.get("h4_bias"):
        aligned = (a["h4_bias"] == "bearish") == sell
        why.append(f"H4 bias {a['h4_bias']}" + (" — trade with the trend" if aligned else " — counter-trend"))
    cs = [c for c in (ctx.get("candles_h1") or []) if c["t"] < t["opened_at"]]
    sup, res = lv.get("key_support"), lv.get("key_resistance")
    if sell and cs and lv.get("key_support_src") == "swing_low" and sup and cs[-1]["c"] < sup:
        why.append(f"Breakout: {cs[-1]['t'][-5:]} candle closed below the {px(sup)} swing low")
    if not sell and cs and lv.get("key_resistance_src") == "swing_high" and res and cs[-1]["c"] > res:
        why.append(f"Breakout: {cs[-1]['t'][-5:]} candle closed above the {px(res)} swing high")
    if a.get("adx") is not None:
        trend = "Strong" if a["adx"] >= 25 else "Weak"
        ema = lv.get("ema50")
        side = ""
        if ema is not None and a.get("price") is not None:
            side = f" · price {'below' if a['price'] < ema else 'above'} EMA 50 H1 ({px(ema)})"
        why.append(f"{trend} H1 trend (ADX {a['adx']:.1f}){side}")
    rsi = a.get("rsi")
    if rsi is not None and ((sell and rsi < 35) or (not sell and rsi > 65)):
        risk.append(f"RSI H1 {rsi:.1f} — {'near oversold' if sell else 'near overbought'}")
    piv = lv.get("pivots") or {}
    nxt = piv.get("pivot_s1") if sell else piv.get("pivot_r1")
    if nxt is not None and ((sell and nxt < t["entry"]) or (not sell and nxt > t["entry"])):
        risk.append(f"{'S1' if sell else 'R1'} pivot {px(nxt)} {'below' if sell else 'above'} entry")
    return why, risk


# ------------------------------------------------------------------ story ouverture
def story_open(t, ctx, why_extra, risk_extra, account):
    sell = t["side"] == "SELL"
    scol = BEAR if sell else BULL
    when = f"Opened {t['opened_at'][-5:]} CET"
    pills = pill("Open", scol, "#2A1A15" if sell else "#15281D", dot=True, upper=True)
    if account:
        pills += pill(f"Account: {account}", "#C9C2B3", "#1A1815")
    tp, sl, entry = t.get("take_profit"), t.get("stop_loss"), t["entry"]
    td, sd, rr = t.get("tp_distance_usd"), t.get("sl_distance_usd"), t.get("rr_planned")

    def lvl(label, val, col, delta=None):
        dd = (f'<span style="font-size: 24px; color: {col}; font-variant-numeric: tabular-nums">{e(delta)}</span>'
              if delta else "")
        return (f'<div style="display: flex; align-items: center; justify-content: space-between; gap: 16px">'
                f'<span style="font-size: 22px; letter-spacing: 0.14em; text-transform: uppercase; color: {MUTED}; font-weight: 600">{label}</span>'
                f'<span style="display: flex; align-items: baseline; gap: 16px"><span style="font-family: \'Space Grotesk\', sans-serif; '
                f'font-size: 44px; line-height: 1; font-weight: 700; color: {col}; font-variant-numeric: tabular-nums">{px(val)}</span>{dd}</span></div>')

    dot = lambda c: f'<div style="display: flex; align-items: center; justify-content: center"><span style="width: 24px; height: 24px; border-radius: 999px; background: {c}"></span></div>'
    bar = lambda c: f'<div style="display: flex; justify-content: center"><span style="width: 6px; height: 100%; background: {c}; opacity: 0.55"></span></div>'
    tp_row = lvl("Take profit", tp, BULL, f"+${td:,.2f}" if td else None) if tp is not None else ""
    sl_row = lvl("Stop loss", sl, BEAR, f"−${sd:,.2f}" if sd else None) if sl is not None else ""
    rr_cell = (f'<div style="display: flex; align-items: center"><span style="display: inline-flex; align-items: center; gap: 12px; '
               f'padding: 14px 24px; border-radius: 18px; background: #0F0E0C; font-size: 28px; color: {INK}; font-weight: 600">R:R '
               f'<span style="font-family: \'Space Grotesk\', sans-serif; font-size: 40px; color: {ACCENT}">1 : {rr:g}</span></span></div>'
               if rr else "<div></div>")
    # ordre par prix, de haut en bas : BUY = TP / entree / SL ; SELL = SL / entree / TP
    top, top_c, bottom, bottom_c = (sl_row, BEAR, tp_row, BULL) if sell else (tp_row, BULL, sl_row, BEAR)
    ladder = (f'<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 36px; padding: 36px 40px; display: grid; '
              f'grid-template-columns: 28px minmax(0, 1fr); grid-template-rows: 48px {"60px" if sell else FMT["tall"]} 48px {FMT["tall"] if sell else "60px"} 48px; column-gap: 28px">'
              f'{dot(top_c)}{top}'
              f'{bar(top_c)}{"<div></div>" if sell else rr_cell}'
              f'{dot(ACCENT)}{lvl("Entry", entry, ACCENT)}'
              f'{bar(bottom_c)}{rr_cell if sell else "<div></div>"}'
              f'{dot(bottom_c)}{bottom}</div>')
    why, risk = context_lines(t, ctx)
    why = (why + why_extra)[:3] if why_extra else why[:3]
    risk = risk_extra or risk
    rows = "".join(f'<div style="display: flex; align-items: center; gap: 16px; font-size: 28px; line-height: 1.3">{CHECK}<span>{e(w)}</span></div>'
                   for w in why)
    if risk:
        rows += (f'<div style="display: flex; align-items: center; gap: 16px; font-size: 26px; line-height: 1.3; color: {BEAR}; margin-top: 6px">'
                 f'{WARN}<span>Risk: {e(" · ".join(risk))}</span></div>')
    why_card = (f'<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 36px; padding: 40px; display: flex; '
                f'flex-direction: column; gap: 18px"><span style="font-size: 26px; letter-spacing: 0.16em; text-transform: uppercase; '
                f'color: {MUTED}; font-weight: 600">Why this trade</span>{rows}</div>') if rows else ""
    body = f"""<div style="display: flex; flex-direction: column; gap: 8px">
<div style="display: flex; align-items: baseline; gap: 24px; font-family: 'Space Grotesk', sans-serif; line-height: 1">
<span style="font-size: 120px; font-weight: 700; letter-spacing: -0.02em; color: {scol}">{t['side']}</span>
<span style="font-size: 52px; font-weight: 600; color: {INK}">XAU/USD</span></div>
<div style="font-size: 28px; color: {MUTED}">{e(setup_line(t))} · {e(when)}</div>
<div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px">{pills}</div></div>
{ladder}
{why_card}"""
    return shell(body, "Trade of the day · Gold", day_label(t["opened_at"]))


# ------------------------------------------------------------------ story cloture
def story_close(t, lesson, account_balance):
    r, pnl = t.get("r"), t.get("pnl_eur")
    win = (pnl or 0) > 0
    col = BULL if t.get("outcome") == "win" else (MUTED if t.get("outcome") == "breakeven" else BEAR)
    reason = {"tp": "Take profit hit", "sl": "Stop loss hit"}.get(t.get("exit_reason"), "Closed")
    r_txt = f"{'+' if (r or 0) >= 0 else '−'}{abs(r):.2f}R" if r is not None else "—"
    span = f"{t['opened_at'][-5:]} → {t['closed_at'][-5:]} CET" if t.get("closed_at") else ""
    if t.get("closed_at") and t["closed_at"][:10] != t["opened_at"][:10]:
        span = f"{day_label(t['opened_at'])[:3]} {t['opened_at'][-5:]} → {day_label(t['closed_at'])[:3]} {t['closed_at'][-5:]} CET"
    pills = (pill(span, "#C9C2B3", "#1A1815") if span else "") + (
        pill(f"Balance: €{account_balance:,.2f}", "#C9C2B3", "#1A1815") if account_balance is not None else "")
    dur = t.get("duration_min")
    dur_txt = (f"{int(dur // 60)}h{int(dur % 60):02d}" if dur >= 60 else f"{int(dur)} min") if dur is not None else "—"
    third = None
    if r is not None and t.get("exit_reason") == "sl":
        third = ("Slippage", f"{r + 1:+.2f}R", BEAR if r < -1 else BULL)
    elif t.get("exit_reason") == "tp" and t.get("rr_planned") and r is not None:
        third = ("Planned R", f"{t['rr_planned']:g}R", ACCENT)
    tile = lambda l, v, c: (f'<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 28px; padding: 26px 28px; '
                            f'display: flex; flex-direction: column; gap: 8px"><span style="font-size: 22px; color: {MUTED}">{e(l)}</span>'
                            f'<span style="font-family: \'Space Grotesk\', sans-serif; font-size: 40px; font-weight: 700; color: {c}; '
                            f'font-variant-numeric: tabular-nums">{e(v)}</span></div>')
    tiles = [tile("P&L", f"{'+' if win else '−'}€{abs(pnl):,.2f}" if pnl is not None else "—", col), tile("Duration", dur_txt, INK)]
    if third:
        tiles.append(tile(*third))
    row = lambda mark, label, val, c, lc=INK: (f'<div style="display: flex; justify-content: space-between; align-items: baseline; gap: 16px">'
                                               f'<span style="display: flex; align-items: center; gap: 16px; font-size: 28px; color: {lc}">{mark}{e(label)}</span>'
                                               f'<span style="font-family: \'Space Grotesk\', sans-serif; font-size: 38px; font-weight: 700; color: {c}; '
                                               f'font-variant-numeric: tabular-nums">{px(val)}</span></div>')
    circle = lambda c, fill: (f'<span style="width: 18px; height: 18px; border-radius: 999px; box-sizing: border-box; '
                              + (f'background: {c}"></span>' if fill else f'border: 3px solid {c}"></span>'))
    lv = []
    tp_hit = t.get("exit_reason") == "tp"
    if t.get("take_profit") is not None:
        lv.append(row(circle(BULL, tp_hit), "Take profit" + ("" if tp_hit else " · not reached"), t["take_profit"],
                      BULL if tp_hit else MUTED, INK if tp_hit else MUTED))
    lv.append(row(circle(ACCENT, True), "Entry", t["entry"], ACCENT))
    if t.get("stop_loss") is not None:
        sl_hit = t.get("exit_reason") == "sl"
        lv.append(row(circle(BEAR, sl_hit), "Stop loss" + ("" if sl_hit else " · not hit"), t["stop_loss"],
                      BEAR if sl_hit else MUTED, INK if sl_hit else MUTED))
    if t.get("exit") is not None:
        lv.append(row(f'<span style="width: 18px; height: 18px; border-radius: 4px; background: {col}"></span>', "Exit", t["exit"], col))
    take = (f'<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 36px; padding: 36px 40px; display: flex; '
            f'flex-direction: column; gap: 16px"><span style="font-size: 26px; letter-spacing: 0.16em; text-transform: uppercase; '
            f'color: {MUTED}; font-weight: 600">Takeaway</span><span style="font-size: 28px; line-height: 1.35; color: {ACCENT}">'
            f'{e(lesson)}</span></div>') if lesson else ""
    badge_bg = "#15281D" if col == BULL else ("#2A1A15" if col == BEAR else "#1A1815")
    body = f"""<div style="display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; align-items: center; gap: 28px; flex-wrap: wrap">
<span style="font-family: 'Space Grotesk', sans-serif; font-size: 150px; line-height: 1; font-weight: 700; letter-spacing: -0.03em; color: {col}; font-variant-numeric: tabular-nums">{r_txt}</span>
{pill(reason, col, badge_bg, upper=True)}</div>
<div style="font-size: 30px; color: {INK}; font-weight: 500">{t['side']} XAU/USD · {e(setup_line(t))}</div>
<div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px">{pills}</div></div>
<div style="display: grid; grid-template-columns: repeat({len(tiles)}, minmax(0, 1fr)); gap: 20px">{"".join(tiles)}</div>
<div style="background: #1A1815; border: 1px solid #2E2A22; border-radius: 36px; padding: 36px 40px; display: flex; flex-direction: column; gap: 22px">
<span style="font-size: 26px; letter-spacing: 0.16em; text-transform: uppercase; color: {MUTED}; font-weight: 600">Levels</span>{"".join(lv)}</div>
{take}"""
    return shell(body, "Trade closed · Gold", day_label(t["closed_at"] or t["opened_at"]))


def render(html_text, out):
    from playwright.sync_api import sync_playwright
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".html")
    tmp.write_text(html_text, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": FMT["h"]}, device_scale_factor=1)
        pg.goto(tmp.resolve().as_uri(), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(out), type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 1080, "height": FMT["h"]})
        b.close()
    tmp.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade", required=True, help="trade_YYYY-MM-DD_tradeN.json")
    ap.add_argument("--context", help="daily JSON de l'analyse juste avant l'entree (biais, ADX, niveaux, bougies)")
    ap.add_argument("--candles", help="daily JSON plus recent dont seules les bougies H1 sont reprises (entree incluse)")
    ap.add_argument("--close", action="store_true", help="story de cloture (sinon : ouverture)")
    ap.add_argument("--why", action="append", default=[], help="ligne « Why this trade » supplementaire (repetable)")
    ap.add_argument("--risk", action="append", default=[], help="remplace les lignes de risque (repetable)")
    ap.add_argument("--lesson", help="lecon (story de cloture) ; sans elle, le bloc Takeaway est omis")
    ap.add_argument("--account", default=None, help="libelle du compte (defaut : setup.account du challenge si fourni)")
    ap.add_argument("--challenge", help="challenge_*.json (compte Live)")
    ap.add_argument("--format", choices=["story", "post"], default="story", help="story 1080x1920 ou post 1080x1350 (4:5)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.format == "post":
        FMT.update(h=1350, pad="64px 72px 56px", gap="24px", tall="120px")
    t = json.loads(Path(a.trade).read_text(encoding="utf-8"))["trade"]
    ctx = json.loads(Path(a.context).read_text(encoding="utf-8")) if a.context else None
    if ctx is not None and a.candles:
        ctx["candles_h1"] = json.loads(Path(a.candles).read_text(encoding="utf-8")).get("candles_h1")
    account = a.account
    if account is None and a.challenge:
        account = (json.loads(Path(a.challenge).read_text(encoding="utf-8")).get("setup") or {}).get("account")
    if a.close:
        if t.get("status") != "closed":
            raise SystemExit(f"Trade #{t.get('trade_no')} pas encore cloture (status={t.get('status')}).")
        html_text = story_close(t, a.lesson, t.get("balance_after"))
    else:
        html_text = story_open(t, ctx, a.why, a.risk, account)
    render(html_text, a.out)
    print(f"OK {a.out}")


if __name__ == "__main__":
    main()

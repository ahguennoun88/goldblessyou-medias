#!/usr/bin/env python3
"""
render_trade_carousel.py - GOLDBLESSYOU
Carrousel de CLOTURE d'un trade (post de fil, 2 slides JPEG 1080x1350) valide par Ahmed le 12/11/2026 (trade #1) :
  slide1.jpg : carte « Trades · fond noir » (TRADE #N / CLOSED, SELL XAU/USD, R en grand, grille P&L · Balance ·
               Strategy · Date, pied GOLDBLESSYOU / @goldblessyou.xau)
  slide2.jpg : detail « Trade closed » (R, horaires, balance, P&L, duree, frais, niveaux avec motif de sortie),
               en-tete aligne sur la slide 1.

Exemple :
  python3 tools/render_trade_carousel.py --trade trade_2026-11-12_trade24.json --out posts/2026-11-12_trade24_close

Numero affiche : --display-no, sinon trade_no du bot - posts/trades_state.json["_numbering"]["offset"]
(offset 23 : le trade 24 du bot = Trade #1). Si l'export recoit un vrai --challenge-start, remettre l'offset a 0.
Balance : balance_after_broker du JSON (solde reel) ; a defaut balance_before_broker + pnl_eur (calcule, signale).
Frais : fees_eur (commission + swap) s'il est renseigne, sinon la tuile est omise.
Motif de sortie : --exit-label, sinon deduit (stop touche en gain = « Trailing stop », a ~0R = « Break-even stop »).
Aucune donnee inventee : tout vient du JSON du bot ; un champ absent est omis.
"""
import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_trade_story as rts  # noqa: E402  (helpers et rendu Playwright du template valide)

ROOT = Path(__file__).resolve().parent.parent
GOLD, BULL, BEAR, MUTED, INK = rts.ACCENT, rts.BULL, rts.BEAR, rts.MUTED, rts.INK
LINE = "#2E2A22"
e = html.escape
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;'
         'family=Space+Grotesk:wght@500;600;700&amp;display=block" rel="stylesheet">')
PAD = "96px 82px 84px"          # marges communes aux deux slides (en-tetes alignes)
HEAD = ("display:flex;justify-content:space-between;font-family:'Space Grotesk',sans-serif;font-size:36px;"
        "font-weight:600;letter-spacing:0.16em;text-transform:uppercase")


def money(x, signed=False):
    s = "+" if signed and x >= 0 else ("−" if x < 0 else "")
    return f"{s}€{abs(x):,.2f}"


def display_no(t, forced):
    if forced is not None:
        return forced
    try:
        off = json.loads((ROOT / "posts/trades_state.json").read_text(encoding="utf-8"))["_numbering"]["offset"]
    except (OSError, KeyError, ValueError):
        off = 0
    return t["trade_no"] - off


def balance(t):
    """(valeur, source) : solde broker reel si exporte, sinon solde avant + P&L (calcule)."""
    if t.get("balance_after_broker") is not None:
        return t["balance_after_broker"], "broker (balance_after_broker)"
    if t.get("balance_before_broker") is not None and t.get("pnl_eur") is not None:
        return round(t["balance_before_broker"] + t["pnl_eur"], 2), "calcule (balance_before_broker + pnl_eur)"
    return None, "absent"


def exit_label(t, forced):
    if forced is not None:
        return forced or None
    if t.get("exit_reason") == "other" and t.get("exit_reason_raw") == "sl":
        if t.get("outcome") == "win":
            return "Trailing stop"
        if t.get("outcome") == "breakeven":
            return "Break-even stop"
    return None


def colour(t):
    return BULL if t.get("outcome") == "win" else (MUTED if t.get("outcome") == "breakeven" else BEAR)


def r_text(r):
    return f"{'+' if r >= 0 else '−'}{abs(r):.2f}R"


def page(inner, footer, pad=PAD):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">{FONTS}'
            f'<style>body{{margin:0;background:#0F0E0C}}</style></head><body>'
            f'<div style="width:1080px;height:1350px;box-sizing:border-box;background:#0F0E0C;color:{INK};'
            f'font-family:Inter,system-ui,sans-serif;padding:{pad};display:flex;flex-direction:column;'
            f'justify-content:space-between;overflow:hidden">{inner}{footer}</div></body></html>')


# ------------------------------------------------------------------ slide 1 : carte fond noir
def slide1(t, no, bal):
    col = colour(t)
    stats = [("P&L", money(t["pnl_eur"], True) if t.get("pnl_eur") is not None else None, col),
             ("Balance", money(bal) if bal is not None else None, INK),
             ("Strategy", (t.get("strategy") or "").capitalize() or None, GOLD),
             ("Date", datetime.strptime(t["closed_at"], "%Y-%m-%d %H:%M").strftime("%a, %b %-d"), INK)]
    stats = [s for s in stats if s[1]]
    cells = "".join(
        f'<div style="display:flex;flex-direction:column;gap:12px;padding:30px 0;'
        f'{f"border-left:1px solid {LINE};padding-left:40px;" if i % 2 else ""}'
        f'{f"border-top:1px solid {LINE};" if i > 1 else ""}">'
        f'<span style="font-size:24px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:{MUTED}">{l}</span>'
        f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:52px;font-weight:700;line-height:1;color:{c};'
        f'font-variant-numeric:tabular-nums">{e(v)}</span></div>' for i, (l, v, c) in enumerate(stats))
    inner = (f'<div style="{HEAD}"><span style="color:{GOLD}">Trade #{no}</span><span style="color:{MUTED}">Closed</span></div>'
             f'<div style="display:flex;flex-direction:column">'
             f'<div style="font-family:\'Space Grotesk\',sans-serif;font-size:96px;font-weight:700;line-height:1;'
             f'letter-spacing:-0.01em">{e(t["side"])} XAU/USD</div>'
             f'<div style="font-family:\'Space Grotesk\',sans-serif;font-size:250px;font-weight:700;line-height:1;'
             f'letter-spacing:-0.03em;color:{col};margin:22px 0 22px -10px">{r_text(t["r"])}</div>'
             f'<div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid {LINE};margin-top:8px">{cells}</div></div>')
    footer = (f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
              f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:32px;font-weight:600;letter-spacing:0.16em;'
              f'color:{GOLD}">GOLDBLESSYOU</span><span style="font-size:32px;color:{MUTED}">{rts.HANDLE}</span></div>')
    return page(inner, footer)


# ------------------------------------------------------------------ slide 2 : detail
def slide2(t, bal, xlabel, lesson):
    col = colour(t)
    r, pnl = t.get("r"), t.get("pnl_eur")
    reason = {"tp": "Take profit hit", "sl": "Stop loss hit"}.get(t.get("exit_reason"), "Closed")
    span = f"{t['opened_at'][-5:]} → {t['closed_at'][-5:]} CET"
    if t["closed_at"][:10] != t["opened_at"][:10]:
        span = (f"{rts.day_label(t['opened_at'])[:3]} {t['opened_at'][-5:]} → "
                f"{rts.day_label(t['closed_at'])[:3]} {t['closed_at'][-5:]} CET")
    pills = rts.pill(span, "#C9C2B3", "#1A1815") + (rts.pill(f"Balance: {money(bal)}", "#C9C2B3", "#1A1815") if bal is not None else "")
    dur = t.get("duration_min")
    dur_txt = (f"{int(dur // 60)}h{int(dur % 60):02d}" if dur >= 60 else f"{int(dur)} min") if dur is not None else "—"
    tile = lambda l, v, c: (f'<div style="background:#1A1815;border:1px solid {LINE};border-radius:28px;padding:26px 28px;'
                            f'display:flex;flex-direction:column;gap:8px"><span style="font-size:22px;color:{MUTED}">{e(l)}</span>'
                            f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:40px;font-weight:700;color:{c};'
                            f'font-variant-numeric:tabular-nums">{e(v)}</span></div>')
    tiles = [tile("P&L", money(pnl, True) if pnl is not None else "—", col), tile("Duration", dur_txt, INK)]
    if t.get("fees_eur") is not None:
        tiles.append(tile("Fees", money(t["fees_eur"]), MUTED))
    if r is not None and t.get("exit_reason") == "sl":
        tiles.append(tile("Slippage", f"{r + 1:+.2f}R", BEAR if r < -1 else BULL))
    elif t.get("exit_reason") == "tp" and t.get("rr_planned") and r is not None:
        tiles.append(tile("Planned R", f"{t['rr_planned']:g}R", GOLD))
    row = lambda mark, label, val, c, lc=INK: (
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:16px">'
        f'<span style="display:flex;align-items:center;gap:16px;font-size:28px;color:{lc}">{mark}{e(label)}</span>'
        f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:38px;font-weight:700;color:{c};'
        f'font-variant-numeric:tabular-nums">{rts.px(val)}</span></div>')
    circle = lambda c, fill: (f'<span style="width:18px;height:18px;border-radius:999px;box-sizing:border-box;'
                              + (f'background:{c}"></span>' if fill else f'border:3px solid {c}"></span>'))
    tp_hit, sl_hit = t.get("exit_reason") == "tp", t.get("exit_reason") == "sl"
    lv = []
    if t.get("take_profit") is not None:
        lv.append(row(circle(BULL, tp_hit), "Take profit" + ("" if tp_hit else " · not reached"), t["take_profit"],
                      BULL if tp_hit else MUTED, INK if tp_hit else MUTED))
    lv.append(row(circle(GOLD, True), "Entry", t["entry"], GOLD))
    if t.get("stop_loss") is not None:
        lv.append(row(circle(BEAR, sl_hit), "Stop loss" + ("" if sl_hit else " · not hit"), t["stop_loss"],
                      BEAR if sl_hit else MUTED, INK if sl_hit else MUTED))
    lv.append(row(f'<span style="width:18px;height:18px;border-radius:4px;background:{col}"></span>',
                  "Exit" + (f" · {xlabel}" if xlabel else ""), t["exit"], col))
    take = (f'<div style="background:#1A1815;border:1px solid {LINE};border-radius:36px;padding:36px 40px;display:flex;'
            f'flex-direction:column;gap:16px"><span style="font-size:26px;letter-spacing:0.16em;text-transform:uppercase;'
            f'color:{MUTED};font-weight:600">Takeaway</span><span style="font-size:28px;line-height:1.35;color:{GOLD}">'
            f'{e(lesson)}</span></div>') if lesson else ""
    badge_bg = "#15281D" if col == BULL else ("#2A1A15" if col == BEAR else "#1A1815")
    date_txt = rts.day_label(t["closed_at"]).rsplit(",", 1)[0]
    inner = (f'<div style="display:flex;flex-direction:column;gap:24px">'
             f'<div style="{HEAD}"><span style="color:{GOLD}">Trade closed · Gold</span><span style="color:{MUTED}">{e(date_txt)}</span></div>'
             f'<div style="display:flex;flex-direction:column;gap:10px">'
             f'<div style="display:flex;align-items:center;gap:28px;flex-wrap:wrap">'
             f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:150px;line-height:1;font-weight:700;'
             f'letter-spacing:-0.03em;color:{col};font-variant-numeric:tabular-nums">{r_text(r) if r is not None else "—"}</span>'
             f'{rts.pill(reason, col, badge_bg, upper=True)}</div>'
             f'<div style="font-size:30px;color:{INK};font-weight:500">{t["side"]} XAU/USD · {e(rts.setup_line(t))}</div>'
             f'<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:12px">{pills}</div></div>'
             f'<div style="display:grid;grid-template-columns:repeat({len(tiles)},minmax(0,1fr));gap:20px">{"".join(tiles)}</div>'
             f'<div style="background:#1A1815;border:1px solid {LINE};border-radius:36px;padding:36px 40px;display:flex;'
             f'flex-direction:column;gap:22px"><span style="font-size:26px;letter-spacing:0.16em;text-transform:uppercase;'
             f'color:{MUTED};font-weight:600">Levels</span>{"".join(lv)}</div>{take}</div>')
    footer = (f'<div style="display:flex;flex-direction:column;gap:12px;align-items:center;text-align:center">'
              f'<span style="font-family:\'Space Grotesk\',sans-serif;font-size:34px;font-weight:600">{rts.HANDLE}</span>'
              f'<span style="font-size:24px;color:{MUTED}">Personal view — Not financial advice (NFA)</span></div>')
    return page(inner, footer, "96px 82px 56px")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trade", required=True, help="trade_YYYY-MM-DD_tradeN.json (trade cloture)")
    ap.add_argument("--out", required=True, help="dossier de sortie (slide1.jpg, slide2.jpg)")
    ap.add_argument("--display-no", type=int, help="numero affiche (defaut : trade_no - offset de trades_state.json)")
    ap.add_argument("--exit-label", help="motif de sortie affiche apres « Exit » (\"\" pour aucun ; defaut : deduit)")
    ap.add_argument("--lesson", help="lecon (bloc Takeaway de la slide 2) ; sans elle, bloc omis")
    a = ap.parse_args()
    t = json.loads(Path(a.trade).read_text(encoding="utf-8"))["trade"]
    if t.get("status") != "closed":
        raise SystemExit(f"Trade {t.get('trade_no')} pas encore cloture (status={t.get('status')}).")
    rts.FMT.update(h=1350)
    no = display_no(t, a.display_no)
    bal, src = balance(t)
    xl = exit_label(t, a.exit_label)
    out = Path(a.out)
    rts.render(slide1(t, no, bal), out / "slide1.jpg")
    rts.render(slide2(t, bal, xl, a.lesson), out / "slide2.jpg")
    print(f"OK {out}/slide1.jpg {out}/slide2.jpg | Trade #{no} | balance {bal} ({src}) | "
          f"fees {t.get('fees_eur')} | exit label {xl!r}")


if __name__ == "__main__":
    main()

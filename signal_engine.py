"""Candle-based technical analysis and historical signal evaluation.

Confidence is a rule-strength score, NOT a proven probability or guaranteed win rate.
"""
from __future__ import annotations
from math import sqrt
from typing import Any


def _ema(values: list[float], period: int) -> list[float]:
    alpha = 2 / (period + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1 - alpha) * out[-1])
    return out


def _patterns(opens, highs, lows, closes) -> list[dict[str, str]]:
    """Detect common single-, two-, and three-candle patterns at the latest bar."""
    n = len(closes)
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    rng = max(h - l, 1e-12)
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    out: list[dict[str, str]] = []

    def add(name: str, direction: str, strength: str = "normal"):
        out.append({"name": name, "direction": direction, "strength": strength})

    # One-candle patterns
    if body <= rng * 0.10:
        add("Doji", "neutral")
    if body > 0 and lower >= body * 2 and upper <= body * 0.7 and (max(o, c) >= l + rng * 0.55):
        add("Hammer", "bullish", "strong")
    if body > 0 and upper >= body * 2 and lower <= body * 0.7 and (min(o, c) <= l + rng * 0.45):
        add("Shooting Star", "bearish", "strong")
    if body > 0 and lower >= body * 2.2 and upper <= body:
        add("Bullish Pin Bar", "bullish")
    if body > 0 and upper >= body * 2.2 and lower <= body:
        add("Bearish Pin Bar", "bearish")

    # Two-candle engulfing patterns
    if n >= 2:
        po, pc = opens[-2], closes[-2]
        prev_body = abs(pc - po)
        if pc < po and c > o and o <= pc and c >= po and body >= prev_body * 0.9:
            add("Bullish Engulfing", "bullish", "strong")
        elif pc > po and c < o and o >= pc and c <= po and body >= prev_body * 0.9:
            add("Bearish Engulfing", "bearish", "strong")

    # Three-candle reversal patterns
    if n >= 3:
        o1, c1 = opens[-3], closes[-3]
        o2, c2 = opens[-2], closes[-2]
        b1, b2 = abs(c1-o1), abs(c2-o2)
        mid1 = (o1+c1)/2
        if c1 < o1 and b1 > 0 and b2 <= b1*0.55 and c > o and c >= mid1:
            add("Morning Star", "bullish", "strong")
        elif c1 > o1 and b1 > 0 and b2 <= b1*0.55 and c < o and c <= mid1:
            add("Evening Star", "bearish", "strong")
        if closes[-3] < opens[-3] and closes[-2] > opens[-2] and c > o and c > closes[-2] and closes[-2] > closes[-3]:
            add("Three White Soldiers", "bullish", "strong")
        elif closes[-3] > opens[-3] and closes[-2] < opens[-2] and c < o and c < closes[-2] and closes[-2] < closes[-3]:
            add("Three Black Crows", "bearish", "strong")
    return out


def analyze(candles: list[dict[str, Any]], timeframe: int) -> dict[str, Any]:
    if len(candles) < 60:
        raise ValueError(f"At least 60 real candles are required; received {len(candles)}.")
    closes = [float(c['close']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]
    opens = [float(c['open']) for c in candles]
    if not all(x > 0 for x in closes + highs + lows + opens):
        raise ValueError("Candle feed contains invalid prices.")
    if any(h < max(o, c) or l > min(o, c) or h < l for o,h,l,c in zip(opens,highs,lows,closes)):
        raise ValueError("Candle feed contains inconsistent OHLC values.")

    e9, e21, e50 = _ema(closes, 9), _ema(closes, 21), _ema(closes, 50)
    changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]
    avg_gain, avg_loss = sum(gains[-14:])/14, sum(losses[-14:])/14
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else (50.0 if avg_loss == 0 else 100 - 100/(1+avg_gain/avg_loss))

    ema12, ema26 = _ema(closes,12), _ema(closes,26)
    macd_series = [a-b for a,b in zip(ema12,ema26)]
    macd_hist = macd_series[-1] - _ema(macd_series,9)[-1]

    sample = closes[-20:]
    mean = sum(sample)/20
    sd = sqrt(sum((v-mean)**2 for v in sample)/20)
    upper, lower = mean+2*sd, mean-2*sd
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1,len(candles))]
    atr = sum(trs[-14:])/14

    score, reasons = 0.0, []
    if e9[-1] > e21[-1] > e50[-1]: score += 2; reasons.append("EMA 9/21/50 bullish alignment")
    elif e9[-1] < e21[-1] < e50[-1]: score -= 2; reasons.append("EMA 9/21/50 bearish alignment")
    if rsi >= 55: score += 1; reasons.append(f"RSI bullish ({rsi:.1f})")
    elif rsi <= 45: score -= 1; reasons.append(f"RSI bearish ({rsi:.1f})")
    if macd_hist > 0: score += 1; reasons.append("MACD histogram positive")
    elif macd_hist < 0: score -= 1; reasons.append("MACD histogram negative")
    if closes[-1] > upper: score += 1; reasons.append("Close above Bollinger upper band")
    elif closes[-1] < lower: score -= 1; reasons.append("Close below Bollinger lower band")
    recent_high, recent_low = max(highs[-20:-1]), min(lows[-20:-1])
    if closes[-1] > recent_high: score += 1.5; reasons.append("20-candle resistance breakout")
    elif closes[-1] < recent_low: score -= 1.5; reasons.append("20-candle support breakdown")
    body = closes[-1]-opens[-1]
    if atr and body > atr*.25: score += .5; reasons.append("Bullish candle momentum")
    elif atr and body < -atr*.25: score -= .5; reasons.append("Bearish candle momentum")

    patterns = _patterns(opens, highs, lows, closes)
    for p in patterns:
        if p["direction"] == "bullish":
            weight = 1.5 if p["strength"] == "strong" else 0.75
            score += weight
            reasons.append(f'{p["name"]} (bullish candlestick pattern)')
        elif p["direction"] == "bearish":
            weight = 1.5 if p["strength"] == "strong" else 0.75
            score -= weight
            reasons.append(f'{p["name"]} (bearish candlestick pattern)')

    direction = "CALL" if score >= 0 else "PUT"
    confidence = min(88, 52 + round(abs(score)*5))
    return {
        "signal": direction, "confidence": confidence, "score": round(score,2),
        "entry_price": closes[-1], "expiry_seconds": timeframe,
        "indicators": {"ema9":e9[-1],"ema21":e21[-1],"ema50":e50[-1],"rsi14":round(rsi,2),
                       "macd_histogram":macd_hist,"bollinger_upper":upper,"bollinger_lower":lower,"atr14":atr},
        "patterns": patterns, "reasons": reasons, "candles_used":len(candles),
        "confidence_note":"Rule-strength estimate only; not a proven win probability.",
    }


def evaluate_accuracy(candles: list[dict[str, Any]], timeframe: int, max_samples: int = 200) -> dict[str, Any]:
    """Simple walk-forward historical check: each signal uses only prior candles.

    Outcome is next candle close vs signal entry close. This is a rough historical
    directional check, not broker settlement data and not a guaranteed live win rate.
    """
    if len(candles) < 65:
        raise ValueError(f"At least 65 candles are required for historical accuracy check; received {len(candles)}.")
    start = max(60, len(candles)-max_samples-1)
    wins = losses = ties = 0
    for idx in range(start, len(candles)-1):
        hist = candles[:idx+1]
        try:
            signal = analyze(hist, timeframe)["signal"]
        except (ValueError, IndexError, ZeroDivisionError):
            continue
        entry = float(candles[idx]["close"])
        outcome = float(candles[idx+1]["close"])
        if outcome == entry:
            ties += 1
        elif (signal == "CALL" and outcome > entry) or (signal == "PUT" and outcome < entry):
            wins += 1
        else:
            losses += 1
    total = wins+losses
    if total == 0:
        raise ValueError("Not enough non-flat next-candle outcomes to calculate historical accuracy.")
    return {
        "wins": wins, "losses": losses, "ties": ties, "samples": total,
        "accuracy": round(wins/total*100, 1),
        "method": "Walk-forward next-candle direction check on historical candles; excludes ties.",
        "warning": "Historical result only. Not a guaranteed future win rate; broker payout, spread, latency and execution are not modeled."
    }

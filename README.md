# APEX SIGNAL AI — Complete Signal-Only Build

APEX SIGNAL AI is a FastAPI web app with a dark animated dashboard, dynamic TradoWix instrument lists, a candle chart, and a technical-analysis signal endpoint. It does **not** place trades.

## Included

- Live and OTC tabs are populated from the authenticated TradoWix instrument feed; no fixed pair list is hardcoded.
- Search filters the loaded pairs by symbol/name. Open/closed and active/inactive status is shown; closed/inactive pairs remain visible but are disabled for signal selection.
- Animated pair-selection highlight.
- 30-second and 1-minute historical candles, requesting up to 1,000 bars where the provider makes that history available.
- Live tick subscription and in-browser candle updates.
- Signal engine based on returned OHLC candles: EMA 9/21/50, RSI 14, MACD histogram, Bollinger Bands, ATR, recent support/resistance breakout, and candle momentum.
- CALL/PUT output only when enough real candles are received. If the feed is disconnected, pair is closed, or fewer than 60 candles are available, the API returns an error instead of fabricating a signal.
- Signal confidence is a heuristic rule-strength score, **not** a verified probability or win rate.
- The app displays a TradoWix email/password form. Credentials are submitted to the backend only when the user presses Connect; the password is not written into the project files or returned to the browser. Use HTTPS hosting only. The SDK caches a session token on the server in `~/.pytradowix/session.json`.
- No trade execution route is included.

## Deploy

Use Python 3.11+ and a Python web-service host that supports outbound WebSockets.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Set private environment variables on the host:
  - `TRADOWIX_EMAIL` = TradoWix account email
  - `TRADOWIX_PASSWORD` = TradoWix account password

Do not add `.env` or real credentials to GitHub. Keep the repository private where possible. `.env.example` is only a blank template.

After deployment, open the app, open **Chart & API Diagnostics**, enter your TradoWix email/password, and click **Connect TradoWix API**. Once the instrument feed arrives, the selected Live/OTC pair list populates automatically. If login succeeds before the instruments arrive, wait briefly and press **Refresh Pairs**. Then search/select a pair, load the chart, and return to the signal panel to generate a signal.

## Endpoints

- `GET /api/health`
- `POST /api/connect` — accepts `{ "email": "...", "password": "..." }` over HTTPS and authenticates with TradoWix
- `GET /api/status`
- `GET /api/assets?market=live|otc|all`
- `GET /api/chart?symbol=...&timeframe=30|60&limit=1000`
- `GET /api/signal?symbol=...&timeframe=30|60`
- `GET /api/ticks/{symbol}`
- `POST /api/disconnect`

## Important integration limits

This package has been compile-checked and smoke-tested with the backend disconnected, and the analysis engine has been tested with synthetic OHLC data. The actual TradoWix account login, current instrument feed, broker candle history, and live tick stream cannot be verified in this build environment because no account credentials are available here. Their availability depends on the account, broker service, SDK compatibility, and deployment host's outbound WebSocket support. The app reports provider errors rather than substituting fake prices or signals.

The included PyTradoWix library is an unofficial SDK copy. Confirm its current compatibility with TradoWix before relying on the service.


## Candlestick patterns and historical accuracy

The signal engine detects Doji, Hammer, Shooting Star, bullish/bearish Pin Bar,
Bullish/Bearish Engulfing, Morning/Evening Star, Three White Soldiers and
Three Black Crows when the latest candle sequence meets its rule conditions.
Detected directional patterns contribute to the rule score and are shown in
the signal explanation.

`GET /api/accuracy?symbol=...&timeframe=30|60&samples=200` runs a simple
walk-forward historical next-candle direction check. Its percentage is a
historical sample result, not a guaranteed future win rate or broker-settled
binary-options result. It does not model payout, spread, latency or execution.

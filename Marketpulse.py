"""
Market Pulse — Streamlit Dashboard
====================================
Live / last-closed prices for Global & Indian markets.
Indian data: Upstox API V2  |  Global data: yfinance + CoinGecko

Usage:
    pip install -r requirements.txt
    streamlit run market_pulse.py

Optionally set token in .streamlit/secrets.toml:
    UPSTOX_TOKEN = "your_access_token_here"
"""

import streamlit as st
import requests
import time
from datetime import datetime
import pytz

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ═══════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(page_title="Market Pulse", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# ═══════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');
.stApp{background:#0a0e17}
header[data-testid="stHeader"]{background:rgba(10,14,23,0.9);backdrop-filter:blur(12px);border-bottom:1px solid #1e2a3a}
#MainMenu,footer,.stDeployButton{display:none!important}

.main-title{font-family:'Outfit',sans-serif;font-size:32px;font-weight:800;background:linear-gradient(135deg,#e8ecf1,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0;letter-spacing:-.5px}
.sub-info{font-family:'JetBrains Mono',monospace;font-size:12px;color:#4a5568;margin-top:2px}
.section-label{font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;color:#4a5568;margin:24px 0 12px;padding-bottom:8px;border-bottom:1px solid #1e2a3a}

.ticker-card{background:#111827;border:1px solid #1e2a3a;border-radius:12px;padding:18px 20px;transition:all .25s;position:relative;overflow:hidden;height:100%}
.ticker-card:hover{border-color:rgba(59,130,246,0.3);background:#1a2332;transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,0.3)}
.ticker-card.up{border-left:3px solid #10b981}
.ticker-card.down{border-left:3px solid #ef4444}
.ticker-card.neutral{border-left:3px solid #4a5568}
.ticker-card.error{border-left:3px solid #f59e0b}

.ticker-header{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.ticker-icon{width:22px;height:22px;border-radius:5px;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;flex-shrink:0}
.ticker-label{font-family:'Outfit',sans-serif;font-size:12px;font-weight:600;color:#7a8ba3;text-transform:uppercase;letter-spacing:.8px}
.ticker-price{font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:#e8ecf1;margin-bottom:6px;letter-spacing:-.5px}
.ticker-change{display:flex;align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;font-size:13px}
.chg-abs{color:#7a8ba3}
.chg-pct{padding:2px 8px;border-radius:6px;font-weight:600;font-size:12px}
.up .chg-pct{background:rgba(16,185,129,0.1);color:#10b981}
.down .chg-pct{background:rgba(239,68,68,0.1);color:#ef4444}
.neutral .chg-pct{background:rgba(74,85,104,0.15);color:#4a5568}
.ticker-error-msg{font-family:'JetBrains Mono',monospace;font-size:12px;color:#f59e0b;margin-top:8px;line-height:1.4}

.dot{width:8px;height:8px;border-radius:50%;display:inline-block;animation:pulse 2s infinite}
.dot.green{background:#10b981;box-shadow:0 0 8px rgba(16,185,129,0.4)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

.login-container{max-width:420px;margin:60px auto;background:#111827;border:1px solid #1e2a3a;border-radius:16px;padding:40px 32px;text-align:center}
.login-title{font-family:'Outfit',sans-serif;font-size:28px;font-weight:700;background:linear-gradient(135deg,#e8ecf1,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}
.login-sub{color:#7a8ba3;font-size:14px;margin-bottom:24px}

.stTextInput>div>div>input{background:#0d1321!important;border:1px solid #1e2a3a!important;color:#e8ecf1!important;font-family:'JetBrains Mono',monospace!important;border-radius:10px!important}
.stTextInput>div>div>input:focus{border-color:#3b82f6!important;box-shadow:none!important}
.stButton>button{background:linear-gradient(135deg,#2563eb,#3b82f6)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-family:'Outfit',sans-serif!important;font-weight:600!important;padding:10px 24px!important}
.stButton>button:hover{box-shadow:0 6px 24px rgba(59,130,246,0.3)!important}
[data-testid="stHorizontalBlock"]{gap:12px!important}

.stApp::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;background-image:linear-gradient(rgba(59,130,246,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,0.03) 1px,transparent 1px);background-size:60px 60px}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# INSTRUMENTS
# ═══════════════════════════════════════════════════════

# Upstox V2 confirmed instrument keys (pipe format for request)
# IMPORTANT: Response keys use COLON instead of PIPE
#   Request:  NSE_INDEX|Nifty 50
#   Response: NSE_INDEX:Nifty 50
INDIAN_INSTRUMENTS = [
    {
        "id": "gift_nifty", "label": "GIFT Nifty", "icon": "🎁", "bg": "#8b5cf6",
        "keys": ["NSE_INDEX|Nifty 50"],  # GIFT Nifty not available separately via REST, uses Nifty 50
        "note": "Nifty 50 proxy"
    },
    {
        "id": "nifty50", "label": "Nifty 50", "icon": "N", "bg": "#3b82f6",
        "keys": ["NSE_INDEX|Nifty 50"],
    },
    {
        "id": "banknifty", "label": "Bank Nifty", "icon": "B", "bg": "#10b981",
        "keys": ["NSE_INDEX|Nifty Bank"],
    },
    {
        "id": "finnifty", "label": "FinNifty", "icon": "F", "bg": "#f59e0b",
        "keys": ["NSE_INDEX|Nifty Fin Service"],
    },
    {
        "id": "sensex", "label": "Sensex", "icon": "S", "bg": "#ef4444",
        "keys": ["BSE_INDEX|SENSEX"],
    },
]

GLOBAL_INSTRUMENTS = [
    {"id": "gold",   "label": "Gold",          "icon": "🥇", "bg": "#f59e0b", "sym": "GC=F"},
    {"id": "dji",    "label": "Dow Jones Fut", "icon": "DJ", "bg": "#3b82f6", "sym": "YM=F"},
    {"id": "nasdaq", "label": "Nasdaq",        "icon": "NQ", "bg": "#8b5cf6", "sym": "NQ=F"},
    {"id": "sp500",  "label": "S&P 500",       "icon": "SP", "bg": "#10b981", "sym": "ES=F"},
    {"id": "btc",    "label": "Bitcoin",        "icon": "₿",  "bg": "#f97316", "sym": "BTC-USD"},
]


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def fmt_price(val):
    if val is None: return "—"
    return f"{val:,.2f}"

def fmt_change(val):
    if val is None: return "—"
    return f"{'+' if val > 0 else ''}{val:,.2f}"

def fmt_pct(val):
    if val is None: return "—"
    return f"{'+' if val > 0 else ''}{val:.2f}%"

def direction(val):
    if val is None or val == 0: return "neutral"
    return "up" if val > 0 else "down"

def pipe_to_colon(key):
    """Convert instrument key from request format (pipe) to response format (colon).
    Upstox V2 quirk: request uses NSE_INDEX|Nifty 50 but response uses NSE_INDEX:Nifty 50
    """
    return key.replace("|", ":")

def render_card(label, icon, bg_color, price, change, pct, error=None):
    if error:
        return f"""<div class="ticker-card error">
            <div class="ticker-header">
                <span class="ticker-icon" style="background:{bg_color}">{icon}</span>
                <span class="ticker-label">{label}</span>
            </div>
            <div class="ticker-error-msg">{error}</div>
        </div>"""
    d = direction(pct)
    return f"""<div class="ticker-card {d}">
        <div class="ticker-header">
            <span class="ticker-icon" style="background:{bg_color}">{icon}</span>
            <span class="ticker-label">{label}</span>
        </div>
        <div class="ticker-price">{fmt_price(price)}</div>
        <div class="ticker-change">
            <span class="chg-abs">{fmt_change(change)}</span>
            <span class="chg-pct">{fmt_pct(pct)}</span>
        </div>
    </div>"""


# ═══════════════════════════════════════════════════════
# DATA: INDIAN MARKETS (Upstox V2)
# ═══════════════════════════════════════════════════════
@st.cache_data(ttl=25)
def fetch_indian_data(token):
    results = {}
    all_keys = list(set(k for inst in INDIAN_INSTRUMENTS for k in inst["keys"]))
    param = ",".join(all_keys)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    api_error_msg = None

    # ── Try full quotes endpoint ──
    try:
        r = requests.get(
            "https://api.upstox.com/v2/market-quote/quotes",
            params={"instrument_key": param},
            headers=headers,
            timeout=10,
        )
        j = r.json()

        if r.status_code != 200 or j.get("status") != "success":
            api_error_msg = (
                j.get("message")
                or (j.get("errors") or [{}])[0].get("message")
                or f"HTTP {r.status_code}"
            )
        elif j.get("data"):
            data = j["data"]
            for inst in INDIAN_INSTRUMENTS:
                d = None
                for k in inst["keys"]:
                    # Try both pipe and colon format lookups
                    colon_key = pipe_to_colon(k)
                    if k in data:
                        d = data[k]
                        break
                    elif colon_key in data:
                        d = data[colon_key]
                        break
                if d:
                    ltp = d.get("last_price") or (d.get("ohlc") or {}).get("close") or 0
                    chg = d.get("net_change") or 0
                    pct = d.get("percentage_change")
                    if pct is None and ltp and chg:
                        denom = ltp - chg
                        pct = (chg / denom) * 100 if denom != 0 else 0
                    results[inst["id"]] = {"price": ltp, "change": chg, "pct": pct or 0}
                else:
                    results[inst["id"]] = {"error": f"Key not in response. Tried: {inst['keys']}"}
            return results
        else:
            api_error_msg = "API returned success but empty data"
    except requests.exceptions.RequestException as e:
        api_error_msg = f"Network: {e}"
    except Exception as e:
        api_error_msg = str(e)

    # ── Fallback: LTP endpoint (lighter, may work when quotes doesn't) ──
    try:
        r_ltp = requests.get(
            "https://api.upstox.com/v2/market-quote/ltp",
            params={"instrument_key": param},
            headers=headers,
            timeout=10,
        )
        j_ltp = r_ltp.json()

        if r_ltp.status_code == 200 and j_ltp.get("status") == "success" and j_ltp.get("data"):
            data = j_ltp["data"]
            for inst in INDIAN_INSTRUMENTS:
                d = None
                for k in inst["keys"]:
                    colon_key = pipe_to_colon(k)
                    if k in data:
                        d = data[k]
                        break
                    elif colon_key in data:
                        d = data[colon_key]
                        break
                if d:
                    ltp = d.get("last_price") or 0
                    # LTP endpoint doesn't have change info, show price only
                    results[inst["id"]] = {"price": ltp, "change": 0, "pct": 0}
                else:
                    results[inst["id"]] = {"error": api_error_msg or "No data"}
            return results
    except Exception:
        pass

    # ── Fallback: OHLC endpoint ──
    try:
        r2 = requests.get(
            "https://api.upstox.com/v2/market-quote/ohlc",
            params={"instrument_key": param, "interval": "1d"},
            headers=headers,
            timeout=10,
        )
        j2 = r2.json()

        if r2.status_code == 200 and j2.get("status") == "success" and j2.get("data"):
            data = j2["data"]
            for inst in INDIAN_INSTRUMENTS:
                d = None
                for k in inst["keys"]:
                    colon_key = pipe_to_colon(k)
                    if k in data:
                        d = data[k]
                        break
                    elif colon_key in data:
                        d = data[colon_key]
                        break
                if d:
                    ltp = d.get("last_price") or (d.get("ohlc") or {}).get("close") or 0
                    op = (d.get("ohlc") or {}).get("open") or ltp
                    chg = ltp - op
                    pct = (chg / op) * 100 if op else 0
                    results[inst["id"]] = {"price": ltp, "change": chg, "pct": pct}
                else:
                    results[inst["id"]] = {"error": api_error_msg or "No data"}
            return results
        else:
            ohlc_err = (
                j2.get("message")
                or (j2.get("errors") or [{}])[0].get("message")
                or f"HTTP {r2.status_code}"
            )
            api_error_msg = api_error_msg or ohlc_err
    except Exception as e2:
        api_error_msg = api_error_msg or str(e2)

    # All failed
    err = api_error_msg or "Unknown error"
    for inst in INDIAN_INSTRUMENTS:
        results[inst["id"]] = {"error": err}
    return results


# ═══════════════════════════════════════════════════════
# DATA: GLOBAL MARKETS (yfinance → Yahoo HTTP → CoinGecko)
# ═══════════════════════════════════════════════════════
@st.cache_data(ttl=25)
def fetch_global_data():
    results = {}

    if HAS_YF:
        syms = [inst["sym"] for inst in GLOBAL_INSTRUMENTS]
        try:
            tickers = yf.Tickers(" ".join(syms))
            for inst in GLOBAL_INSTRUMENTS:
                try:
                    t = tickers.tickers[inst["sym"]]
                    info = t.fast_info
                    price = info.last_price
                    prev = info.previous_close
                    if price and prev:
                        chg = price - prev
                        pct = (chg / prev) * 100
                        results[inst["id"]] = {"price": price, "change": chg, "pct": pct}
                    else:
                        raise ValueError("No price")
                except Exception:
                    try:
                        t = yf.Ticker(inst["sym"])
                        hist = t.history(period="2d")
                        if len(hist) >= 2:
                            prev = hist["Close"].iloc[-2]
                            price = hist["Close"].iloc[-1]
                        elif len(hist) == 1:
                            price = hist["Close"].iloc[-1]
                            prev = price
                        else:
                            raise ValueError("No history")
                        chg = price - prev
                        pct = (chg / prev) * 100 if prev else 0
                        results[inst["id"]] = {"price": float(price), "change": float(chg), "pct": float(pct)}
                    except Exception as e:
                        results[inst["id"]] = {"error": f"yfinance: {e}"}
            return results
        except Exception:
            pass

    # Fallback: raw Yahoo HTTP
    for inst in GLOBAL_INSTRUMENTS:
        if inst["id"] in results:
            continue
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{inst['sym']}?range=2d&interval=1d"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            j = r.json()
            meta = j.get("chart", {}).get("result", [{}])[0].get("meta", {})
            if not meta: raise ValueError("No data")
            price = meta.get("regularMarketPrice") or meta.get("previousClose")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price
            chg = price - prev if price and prev else 0
            pct = (chg / prev) * 100 if prev else 0
            results[inst["id"]] = {"price": price, "change": chg, "pct": pct}
        except Exception:
            if inst["id"] == "btc":
                try:
                    r2 = requests.get(
                        "https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                        timeout=10,
                    )
                    j2 = r2.json()
                    p = j2.get("bitcoin", {}).get("usd")
                    pc = j2.get("bitcoin", {}).get("usd_24h_change") or 0
                    results["btc"] = {"price": p, "change": p * (pc / 100) if p else 0, "pct": pc}
                except Exception:
                    results["btc"] = {"error": "All sources failed"}
            else:
                results[inst["id"]] = {"error": "Yahoo Finance unavailable"}
    return results


# ═══════════════════════════════════════════════════════
# TOKEN VALIDATION
# ═══════════════════════════════════════════════════════
def validate_token(token):
    try:
        r = requests.get(
            "https://api.upstox.com/v2/user/profile",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=8,
        )
        if r.status_code == 200:
            j = r.json()
            if j.get("status") == "success":
                return True, j.get("data", {}).get("user_name", "User")
        j = r.json() if "json" in r.headers.get("content-type", "") else {}
        msg = (
            j.get("message")
            or (j.get("errors") or [{}])[0].get("message")
            or f"Auth failed ({r.status_code})"
        )
        return False, msg
    except Exception as e:
        return False, f"Connection error: {e}"


# ═══════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════
if "token" not in st.session_state:
    try:
        st.session_state.token = st.secrets.get("UPSTOX_TOKEN", "")
    except Exception:
        st.session_state.token = ""
if "connected" not in st.session_state:
    st.session_state.connected = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""


# ═══════════════════════════════════════════════════════
# LOGIN SCREEN
# ═══════════════════════════════════════════════════════
if not st.session_state.connected:
    st.markdown("""
    <div class="login-container">
        <div class="login-title">Market Pulse</div>
        <div class="login-sub">Real-time market dashboard via Upstox</div>
    </div>
    """, unsafe_allow_html=True)

    _, col_form, _ = st.columns([1.5, 2, 1.5])
    with col_form:
        token_input = st.text_input(
            "Access Token", type="password",
            placeholder="Paste your Upstox access token",
            value=st.session_state.token, label_visibility="collapsed",
        )
        if st.button("Connect & Launch", use_container_width=True):
            if not token_input.strip():
                st.error("Please enter your access token.")
            else:
                with st.spinner("Validating token…"):
                    ok, msg = validate_token(token_input.strip())
                if ok:
                    st.session_state.token = token_input.strip()
                    st.session_state.connected = True
                    st.session_state.user_name = msg
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        st.markdown(
            '<p style="text-align:center;margin-top:16px;font-size:12px;color:#4a5568;">'
            'Generate your daily token from '
            '<a href="https://login.upstox.com" target="_blank" style="color:#3b82f6;">Upstox Developer Console</a>'
            '</p>', unsafe_allow_html=True,
        )
    st.stop()


# ═══════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════
token = st.session_state.token
ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)
time_str = now_ist.strftime("%I:%M:%S %p IST")

# Header
h_left, h_right = st.columns([3, 2])
with h_left:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:14px;">
        <span class="main-title">MARKET PULSE</span>
        <span class="dot green"></span>
    </div>
    <div class="sub-info">Updated {time_str} &nbsp;·&nbsp; Welcome, {st.session_state.user_name}</div>
    """, unsafe_allow_html=True)
with h_right:
    _, rc2, rc3 = st.columns([2, 1, 1])
    with rc2:
        if st.button("↻ Refresh"):
            st.cache_data.clear()
            st.rerun()
    with rc3:
        if st.button("Disconnect"):
            st.session_state.connected = False
            st.session_state.token = ""
            st.cache_data.clear()
            st.rerun()

# Fetch data
global_data = fetch_global_data()
indian_data = fetch_indian_data(token)

# Global row
st.markdown('<div class="section-label">Global Markets</div>', unsafe_allow_html=True)
g_cols = st.columns(len(GLOBAL_INSTRUMENTS))
for i, inst in enumerate(GLOBAL_INSTRUMENTS):
    d = global_data.get(inst["id"], {})
    with g_cols[i]:
        if "error" in d:
            st.markdown(render_card(inst["label"], inst["icon"], inst["bg"], None, None, None, d["error"]), unsafe_allow_html=True)
        else:
            st.markdown(render_card(inst["label"], inst["icon"], inst["bg"], d.get("price"), d.get("change"), d.get("pct")), unsafe_allow_html=True)

# Indian row
st.markdown('<div class="section-label">Indian Markets</div>', unsafe_allow_html=True)
i_cols = st.columns(len(INDIAN_INSTRUMENTS))
for i, inst in enumerate(INDIAN_INSTRUMENTS):
    d = indian_data.get(inst["id"], {})
    with i_cols[i]:
        if "error" in d:
            st.markdown(render_card(inst["label"], inst["icon"], inst["bg"], None, None, None, d["error"]), unsafe_allow_html=True)
        else:
            st.markdown(render_card(inst["label"], inst["icon"], inst["bg"], d.get("price"), d.get("change"), d.get("pct")), unsafe_allow_html=True)

# Footer
st.markdown(
    '<div style="text-align:center;padding:24px 0 8px;color:#4a5568;font-size:11px;'
    'border-top:1px solid #1e2a3a;margin-top:32px;">'
    'Data via Upstox V2 API · yfinance · CoinGecko &nbsp;·&nbsp; Auto-refreshes every 30s</div>',
    unsafe_allow_html=True,
)

# Auto-refresh
time.sleep(30)
st.cache_data.clear()
st.rerun()

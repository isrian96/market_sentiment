import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import ta
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

st.title("📈 AI NIFTY 200 Trader")
st.write("News sentiment + RSI + volume based signals")

analyzer = SentimentIntensityAnalyzer()


# =========================
# Load NIFTY 200
# =========================
@st.cache_data
def load_nifty200():
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
    df = pd.read_csv(url)
    return [s + ".NS" for s in df["Symbol"].tolist()]


# =========================
# News sentiment
# =========================
def news_sentiment(symbol):

    try:
        name = symbol.replace(".NS","")

        url = f"https://news.google.com/rss/search?q={name}%20NSE%20India"
        feed = feedparser.parse(url)

        scores = []

        for entry in feed.entries[:5]:
            score = analyzer.polarity_scores(entry.title)["compound"]
            scores.append(score)

        if len(scores) == 0:
            return 0

        return np.mean(scores)

    except:
        return 0


# =========================
# Technical indicators
# =========================
def technicals(symbol):

    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)

        if df is None or len(df) < 30:
            return None

        df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
        df["MA20"] = df["Close"].rolling(20).mean()
        df["vol_avg"] = df["Volume"].rolling(10).mean()

        last = df.iloc[-1]

        return {
            "price": float(last["Close"]),
            "rsi": float(last["RSI"]),
            "vol": float(last["Volume"]),
            "vol_avg": float(last["vol_avg"]),
            "ma20": float(last["MA20"])
        }

    except:
        return None


# =========================
# Decision engine
# =========================
def decision(symbol):

    sent = news_sentiment(symbol)
    tech = technicals(symbol)

    if tech is None:
        return None, sent, None

    price = tech["price"]
    rsi = tech["rsi"]
    vol = tech["vol"]
    vol_avg = tech["vol_avg"]
    ma20 = tech["ma20"]

    # Intraday BUY
    if sent > 0.25 and rsi < 70 and vol > 1.5*vol_avg and price > ma20:
        return "INTRADAY BUY", sent, rsi

    # Long term BUY
    if sent > 0.15 and price > ma20 and rsi < 60:
        return "LONG TERM BUY", sent, rsi

    # SELL
    if sent < -0.25:
        return "SELL", sent, rsi

    return None, sent, rsi


# =========================
# UI
# =========================

if st.button("Scan NIFTY 200"):

    stocks = load_nifty200()

    progress = st.progress(0)
    status = st.empty()

    results = []

    for i, s in enumerate(stocks):

        status.text(f"Scanning {i+1}/{len(stocks)} : {s}")

        signal, sent, rsi = decision(s)

        if signal:
            results.append({
                "Stock": s,
                "Signal": signal,
                "Sentiment": round(sent,3),
                "RSI": round(rsi,1) if rsi else None
            })

        progress.progress((i+1)/len(stocks))

    df = pd.DataFrame(results)

    st.success("Scan complete")

    # show all
    if len(df) == 0:
        st.warning("No trading signals found right now")
    else:
        st.dataframe(df, use_container_width=True)

        # intraday
        st.subheader("🔥 Intraday Buys")

        intraday = df[df["Signal"]=="INTRADAY BUY"]

        if len(intraday) == 0:
            st.write("No intraday signals")
        else:
            st.dataframe(intraday, use_container_width=True)

        # long term
        st.subheader("📈 Long Term Buys")

        longterm = df[df["Signal"]=="LONG TERM BUY"]

        if len(longterm) == 0:
            st.write("No long term signals")
        else:
            st.dataframe(longterm, use_container_width=True)
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
st.write("Relaxed signals + confidence score")

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

        last = df.iloc[-1]

        return {
            "price": float(last["Close"]),
            "rsi": float(last["RSI"]),
            "ma20": float(last["MA20"])
        }

    except:
        return None


# =========================
# Confidence score
# =========================
def confidence_score(sent, rsi, price, ma20):

    score = 0

    # sentiment strength
    score += abs(sent) * 50

    # RSI zone
    if 40 < rsi < 65:
        score += 20
    elif 30 < rsi < 70:
        score += 10

    # trend
    if price > ma20:
        score += 20

    return min(round(score), 100)


# =========================
# Decision engine (RELAXED)
# =========================
def decision(symbol):

    sent = news_sentiment(symbol)
    tech = technicals(symbol)

    if tech is None:
        return None, sent, None, None

    price = tech["price"]
    rsi = tech["rsi"]
    ma20 = tech["ma20"]

    conf = confidence_score(sent, rsi, price, ma20)

    # intraday
    if sent > 0.15 and price > ma20:
        return "INTRADAY BUY", sent, rsi, conf

    # long term
    if sent > 0.05 and price > ma20:
        return "LONG TERM BUY", sent, rsi, conf

    # sell
    if sent < -0.15:
        return "SELL", sent, rsi, conf

    return None, sent, rsi, conf


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

        signal, sent, rsi, conf = decision(s)

        if signal:
            strength = "WEAK"

            if conf > 75:
                strength = "STRONG"
            elif conf > 55:
                strength = "MEDIUM"

            results.append({
                "Stock": s,
                "Signal": signal,
                "Strength": strength,
                "Confidence %": conf,
                "Sentiment": round(sent,3),
                "RSI": round(rsi,1) if rsi else None
            })

        progress.progress((i+1)/len(stocks))

    df = pd.DataFrame(results)

    st.success("Scan complete")

    if len(df) == 0:
        st.warning("No signals right now")
    else:

        st.subheader("All Signals")
        st.dataframe(
            df.sort_values("Confidence %", ascending=False),
            use_container_width=True
        )

        st.subheader("🔥 Strong Buys")
        strong = df[df["Strength"]=="STRONG"]

        if len(strong) > 0:
            st.dataframe(strong, use_container_width=True)

        st.subheader("⚡ Intraday")
        intraday = df[df["Signal"]=="INTRADAY BUY"]

        if len(intraday) > 0:
            st.dataframe(intraday, use_container_width=True)

        st.subheader("📈 Long Term")
        longterm = df[df["Signal"]=="LONG TERM BUY"]

        if len(longterm) > 0:
            st.dataframe(longterm, use_container_width=True)
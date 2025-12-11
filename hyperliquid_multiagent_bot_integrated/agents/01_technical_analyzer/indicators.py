import pandas as pd
import ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    atr = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    )
    df["atr"] = atr.average_true_range()

    # Pivot point semplice sugli ultimi N periodi
    lookback = 10
    high = df["high"].tail(lookback).max()
    low = df["low"].tail(lookback).min()
    close = df["close"].iloc[-1]
    pivot = (high + low + close) / 3
    df["pivot"] = pivot

    return df

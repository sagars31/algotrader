import pandas as pd
import numpy as np


def calculate_ema(data: pd.Series, period: int, adjust: bool = False) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA) of a price series.

    Parameters
    ----------
    data : pd.Series
        Historic price data (e.g., closing prices), indexed by date.
    period : int
        The EMA lookback period (e.g., 12, 26, 50, 200).
    adjust : bool, default False
        If False, uses the recursive formula (standard for trading/finance).
        If True, uses pandas' weighted-average formula (better for stats work).

    Returns
    -------
    pd.Series
        EMA values aligned with the input index.
    """
    return data.ewm(span=period, adjust=adjust).mean()


def calculate_ema_manual(data: pd.Series, period: int) -> pd.Series:
    """
    Manual EMA calculation (no pandas .ewm), useful if you want to see
    exactly how each value is derived.

    Formula:
        multiplier = 2 / (period + 1)
        EMA_today = (Price_today - EMA_yesterday) * multiplier + EMA_yesterday

    The first EMA value is seeded using the SMA of the first `period` values.
    """
    prices = data.values
    ema = np.full(len(prices), np.nan)

    multiplier = 2 / (period + 1)

    # Seed with SMA of the first `period` prices
    ema[period - 1] = prices[:period].mean()

    for i in range(period, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]

    return pd.Series(ema, index=data.index)


if __name__ == "__main__":
    # ---- Example usage ----
    # Simulate historic closing price data
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    np.random.seed(42)
    prices = pd.Series(100 + np.random.randn(30).cumsum(), index=dates)

    period = 10

    df = pd.DataFrame({
        "Close": prices,
        "EMA_pandas": calculate_ema(prices, period),
        "EMA_manual": calculate_ema_manual(prices, period),
    })

    print(df.round(2))
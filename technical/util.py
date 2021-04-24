"""
    defines utility functions to be used
"""
from pandas import DataFrame, DatetimeIndex, merge, to_datetime

TICKER_INTERVAL_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "60m": 60,
    "2h": 120,
    "4h": 240,
    "6h": 360,
    "12h": 720,
    "1d": 1440,
    "1w": 10080,
}


def ticker_history_to_dataframe(ticker: list) -> DataFrame:
    """
    builds a dataframe based on the given ticker history

    :param ticker: See exchange.get_ticker_history
    :return: DataFrame
    """
    cols = ["date", "open", "high", "low", "close", "volume"]
    frame = DataFrame(ticker, columns=cols)

    frame["date"] = to_datetime(frame["date"], unit="ms", utc=True, infer_datetime_format=True)

    # group by index and aggregate results to eliminate duplicate ticks
    frame = frame.groupby(by="date", as_index=False, sort=True).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "max",
        }
    )
    frame.drop(frame.tail(1).index, inplace=True)  # eliminate partial candle
    return frame


def resample_to_interval(dataframe, interval):
    """
        resamples the given dataframe to the desired interval.
        Please be aware you need to upscale this to join the results
        with the other dataframe

    :param dataframe: dataframe containing close/high/low/open/volume
    :param interval: to which ticker value in minutes would you like to resample it
    :return:
    """
    if isinstance(interval, str):
        interval = TICKER_INTERVAL_MINUTES[interval]
    
    df = dataframe.copy()
    df = df.set_index(DatetimeIndex(df["date"]))
    ohlc_dict = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    df = df.resample(str(interval) + "min", label="left").agg(ohlc_dict).dropna()
    df.reset_index(inplace=True)

    return df


def resampled_merge(original, resampled, fill_na=True):
    """
    this method merges a resampled dataset back into the orignal data set

    :param original: the original non resampled dataset
    :param resampled:  the resampled dataset
    :return: the merged dataset
    """

    resampled_interval = compute_interval(resampled)

    # rename all the columns to the correct interval
    resampled.columns = [f"resample_{resampled_interval}_{col}" for col in resampled.columns]

    dataframe = merge(original, resampled, left_on='date', right_on=f'resample_{resampled_interval}_date', how="left")

    if fill_na:
        dataframe.fillna(method="ffill", inplace=True)

    return dataframe


def compute_interval(dataframe: DataFrame, exchange_interval=False):
    """
        calculates the interval of the given dataframe for us
    :param dataframe:
    :param exchange_interval: should we convert the result to an exchange interval or just a number
    :return:
    """
    res_interval = int((dataframe["date"] - dataframe["date"].shift()).min().total_seconds() // 60)

    if exchange_interval:
        # convert to our allowed ticker values
        converted = list(TICKER_INTERVAL_MINUTES.keys())[
            list(TICKER_INTERVAL_MINUTES.values()).index(exchange_interval)
        ]
        if len(converted) > 0:
            return converted
        else:
            raise Exception(
                f"sorry, your interval of {res_interval} is not "
                f"supported in {TICKER_INTERVAL_MINUTES}"
            )

    return res_interval

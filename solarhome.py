#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" Module to read Ausgrid's "Solar Home Electricity" dataset

Pierre Haessig — May 2017
"""

import os.path
import numpy as np
import pandas as pd

csv_fpath = {
    '2010-2011': os.path.join('data', 'Solar home 2010-2011.csv'),
    '2011-2012': os.path.join('data', 'Solar home 2011-2012.csv'),
    '2012-2013': os.path.join('data', 'Solar home 2012-2013.csv'),
}

def read_csv(year):
    """Read original CSV files of the Solar Home Electricity dataset.

    Returns a raw DataFrame, that is with same shape as in the CSV file.
    It can be further processed by `reshape`.

    Notice: due to non ISO timestamp format + dataset reshaping,
    it takes about 1 min to read the file.
    """
    fpath = csv_fpath[year]
    df_raw = pd.read_csv(fpath, skiprows=1,
                parse_dates=['date'], dayfirst=True,
                na_filter=False, dtype={'Row Quality': str})
    return df_raw


def reshape(df_raw):
    """Reshape the raw DataFrame to a nicer "timeseries-friendly" format:
      * columns are customer/channel (using `pandas.MultiIndex`)
      * rows are the records for each datetime (regular sampling every 30 minutes)

    Returns reshaped DataFrame, missing_records list
    """
    # Rows: clean periodic time index
    d0, d1 = df_raw.date.min(), df_raw.date.max()
    from pandas.tseries.offsets import Day
    index = pd.date_range(d0, d1 + Day(1), freq='30T', closed='left')

    # Columns
    customers = sorted(df_raw.Customer.unique())
    channels = ['GC', 'GG', 'CL']
    columns = pd.MultiIndex.from_product(
        (customers, channels),
        names=['Customer', 'Channel'])

    # Empty DataFrame with proper MultiIndex structure
    empty_cols = pd.MultiIndex(
        levels=[customers, channels],
        labels=[[],[]],
        names=['Customer', 'Channel'])
    df = pd.DataFrame(index=index, columns=empty_cols)

    # Fill the DataFrame:
    missing_records = []
    for c in customers:
        d_c = df_raw[df_raw.Customer == c]
        # TODO: save the row quality
        for ch in channels:
            d_c_ch = d_c[d_c['Consumption Category'] == ch]
            ts = d_c_ch.iloc[:,5:-1].values.ravel()
            if len(ts) != len(index):
                # TODO: account for incomplete records.
                # Especially in 2010-2011: len(ts) is almost often 17155 = 48*357.4 !!
                missing_records.append((c,ch, len(ts)))
            else:
                df[c, ch] = ts
    # unit conversion (kWh on 30 min) → kW
    df *= 2
    return df, missing_records


def pv_capacity(df_raw):
    """PV generator capacity of each customer"""
    gen_cap_gby = df_raw.groupby('Customer')['Generator Capacity']
    assert np.all(gen_cap_gby.nunique() == 1)
    return gen_cap_gby.mean()


def postcode(df_raw):
    """Postcode of each customer"""
    postcode_gby = df_raw.groupby('Customer')['Postcode']
    return postcode_gby.min()

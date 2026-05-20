"""
crawler_to_db_template.py

用途：
你的正式股票爬蟲程式最後可以呼叫 insert_dataframe_to_db(df)，
把爬蟲結果寫入 stock_platform.db 的 stocks 資料表。

df 建議欄位：
date, market, code, name, item12, open_price, high_price, close_price, low_price,
volume, multiple, amplitude, change_range, rise_range, fall_range, signal
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "stock_platform.db"

def insert_dataframe_to_db(df: pd.DataFrame, replace_same_date: bool = False):
    conn = sqlite3.connect(DB_PATH)

    if replace_same_date and "date" in df.columns:
        dates = df["date"].dropna().unique().tolist()
        for d in dates:
            conn.execute("DELETE FROM stocks WHERE date = ?", (d,))

    df.to_sql("stocks", conn, if_exists="append", index=False)

    conn.execute(
        "INSERT INTO crawler_logs (run_time, source, status, rows_count, message) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Crawler", "成功", len(df), "爬蟲資料已寫入資料庫")
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    # 這裡只是測試範例，你之後可改成接你的正式爬蟲結果
    sample = pd.DataFrame([{
        "date": "2026/1/27",
        "market": "TWSE",
        "code": "2330",
        "name": "台積電",
        "item12": 0,
        "open_price": 1000,
        "high_price": 1010,
        "close_price": 1005,
        "low_price": 995,
        "volume": 50000,
        "multiple": 1.2,
        "amplitude": 1.5,
        "change_range": 0.8,
        "rise_range": 1.0,
        "fall_range": -0.5,
        "signal": "測試訊號"
    }])

    insert_dataframe_to_db(sample, replace_same_date=False)
    print("測試資料已寫入資料庫")

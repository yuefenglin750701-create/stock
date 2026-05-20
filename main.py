from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stock_platform.db"

app = FastAPI(title="Stock Intelligence Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def rows_to_dict(rows):
    return [dict(r) for r in rows]

class RequestCreate(BaseModel):
    name: str
    email: str
    message: str

class StockCreate(BaseModel):
    date: str
    market: str
    code: str
    name: str
    item12: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    close_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[int] = None
    multiple: Optional[float] = None
    amplitude: Optional[float] = None
    change_range: Optional[float] = None
    rise_range: Optional[float] = None
    fall_range: Optional[float] = None
    signal: Optional[str] = None

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        market TEXT NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        item12 REAL,
        open_price REAL,
        high_price REAL,
        close_price REAL,
        low_price REAL,
        volume INTEGER,
        multiple REAL,
        amplitude REAL,
        change_range REAL,
        rise_range REAL,
        fall_range REAL,
        signal TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        plan TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS crawler_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_time TEXT,
        source TEXT,
        status TEXT,
        rows_count INTEGER,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

@app.get("/api/summary")
def summary():
    conn = get_conn()
    cur = conn.cursor()
    stock_count = cur.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    strategy_count = cur.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    request_count = cur.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    latest_date = cur.execute("SELECT MAX(date) FROM stocks").fetchone()[0]
    twse_count = cur.execute("SELECT COUNT(*) FROM stocks WHERE market='TWSE'").fetchone()[0]
    otc_count = cur.execute("SELECT COUNT(*) FROM stocks WHERE market='OTC'").fetchone()[0]
    signal_count = cur.execute("SELECT COUNT(*) FROM stocks WHERE signal IS NOT NULL AND signal!=''").fetchone()[0]
    conn.close()
    return {
        "stock_count": stock_count,
        "strategy_count": strategy_count,
        "user_count": user_count,
        "request_count": request_count,
        "latest_date": latest_date,
        "twse_count": twse_count,
        "otc_count": otc_count,
        "signal_count": signal_count
    }

@app.get("/api/options")
def options():
    conn = get_conn()
    dates = [r[0] for r in conn.execute("SELECT DISTINCT date FROM stocks ORDER BY date DESC").fetchall()]
    months = sorted(list(set([d[:7] for d in dates if d and len(d) >= 7])), reverse=True)
    markets = [r[0] for r in conn.execute("SELECT DISTINCT market FROM stocks ORDER BY market").fetchall()]
    conn.close()
    return {"dates": dates, "months": months, "markets": markets}

@app.get("/api/stocks")
def list_stocks(
    code: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    min_volume: Optional[int] = Query(None),
    signal_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=2000)
):
    query = "SELECT * FROM stocks WHERE 1=1"
    params = []

    if code:
        query += " AND code LIKE ?"
        params.append(f"%{code.strip()}%")
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name.strip()}%")
    if date:
        query += " AND date = ?"
        params.append(date)
    if month:
        query += " AND substr(date, 1, 7) = ?"
        params.append(month)
    if market and market != "ALL":
        query += " AND market = ?"
        params.append(market)
    if min_volume is not None:
        query += " AND volume >= ?"
        params.append(min_volume)
    if signal_only:
        query += " AND signal IS NOT NULL AND signal != ''"

    query += " ORDER BY date DESC, volume DESC LIMIT ?"
    params.append(limit)

    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows_to_dict(rows)

@app.get("/api/chart/signals")
def chart_signals():
    conn = get_conn()
    rows = conn.execute("""
        SELECT date, COUNT(*) AS count
        FROM stocks
        WHERE signal IS NOT NULL AND signal != ''
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """).fetchall()
    conn.close()
    data = rows_to_dict(rows)
    data.reverse()
    return data

@app.get("/api/chart/market")
def chart_market():
    conn = get_conn()
    rows = conn.execute("""
        SELECT market, COUNT(*) AS count
        FROM stocks
        GROUP BY market
        ORDER BY market
    """).fetchall()
    conn.close()
    return rows_to_dict(rows)

@app.get("/api/chart/top-volume")
def chart_top_volume(limit: int = 10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT code, name, volume
        FROM stocks
        ORDER BY volume DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows_to_dict(rows)

@app.post("/api/stocks")
def create_stock(stock: StockCreate):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO stocks (
            date, market, code, name, item12, open_price, high_price, close_price, low_price,
            volume, multiple, amplitude, change_range, rise_range, fall_range, signal
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        stock.date, stock.market, stock.code, stock.name, stock.item12, stock.open_price, stock.high_price,
        stock.close_price, stock.low_price, stock.volume, stock.multiple, stock.amplitude,
        stock.change_range, stock.rise_range, stock.fall_range, stock.signal
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": new_id}

@app.get("/api/strategies")
def list_strategies():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM strategies ORDER BY id DESC").fetchall()
    conn.close()
    data = rows_to_dict(rows)
    for item in data:
        item["active"] = bool(item["active"])
    return data

@app.get("/api/users")
def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    return rows_to_dict(rows)

@app.get("/api/requests")
def list_requests():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM requests ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return rows_to_dict(rows)

@app.post("/api/requests")
def create_request(payload: RequestCreate):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO requests (name, email, message) VALUES (?, ?, ?)",
        (payload.name, payload.email, payload.message)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"ok": True, "id": new_id}

@app.get("/api/logs")
def list_logs():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM crawler_logs ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return rows_to_dict(rows)

@app.post("/api/seed")
def seed_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM stocks")
    cur.execute("DELETE FROM strategies")
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM crawler_logs")

    stocks = [
        ("2026/1/26","OTC","1815","富喬",15.11,94.00,96.40,95.80,93.30,44923,0.62,3.31,2.24,2.88,-0.43,"紫燈條件"),
        ("2026/1/26","OTC","5351","鈺創",14.16,60.80,63.80,61.10,59.50,21209,0.84,7.21,2.52,7.05,-0.17,"量價突破"),
        ("2026/1/26","OTC","5498","凱崴",24.59,62.00,63.10,61.20,59.10,15339,0.84,6.43,-1.61,1.45,-4.98,""),
        ("2026/1/26","OTC","6265","方土昶",17.34,49.00,49.55,47.30,45.05,15903,0.74,9.34,-1.87,2.80,-6.54,""),
        ("2026/1/26","OTC","8088","品安",10.11,61.80,65.10,63.80,61.50,10690,1.09,5.91,4.76,6.90,0.99,"均線轉強"),
        ("2026/1/26","TWSE","1717","長興",9.82,64.00,64.60,62.90,61.50,27263,0.65,4.86,-1.41,1.25,-3.61,""),
        ("2026/1/26","TWSE","2409","友達",1.30,15.20,15.50,15.25,15.10,104980,0.52,2.66,1.33,2.99,0.33,"量價突破"),
        ("2026/1/26","TWSE","3481","群創",5.36,24.55,25.35,24.55,24.05,451933,0.61,5.42,2.29,5.63,0.21,"量價突破"),
        ("2026/1/26","TWSE","6116","彩晶",1.32,9.18,9.70,9.16,9.06,32897,1.50,7.09,1.44,7.42,0.33,"均線轉強"),
        ("2026/1/26","TWSE","8422","可寧衛*", -92.73,40.70,41.50,40.10,39.25,82363,0.92,5.57,-0.74,2.72,-2.85,""),
        ("2026/1/23","OTC","1815","富喬",14.61,100.00,101.00,93.70,93.60,72577,0.60,7.08,-10.33,-3.35,-10.43,""),
        ("2026/1/23","OTC","3624","光頡",12.51,68.20,69.00,62.00,61.60,14018,2.66,12.03,0.81,12.20,0.16,"KD金叉"),
        ("2026/1/23","OTC","5351","鈺創",13.36,61.90,64.20,59.60,58.00,25278,0.77,9.92,-4.64,2.72,-7.20,""),
        ("2026/1/23","OTC","5498","凱崴",23.57,66.30,66.80,62.20,61.80,18206,1.15,7.41,-7.85,-1.04,-8.44,""),
        ("2026/1/23","TWSE","1605","華新",7.00,39.40,39.75,38.85,38.25,66987,0.42,3.78,-2.02,0.25,-3.53,""),
        ("2026/1/23","TWSE","1717","長興",8.82,67.80,68.00,63.80,63.00,42216,0.93,7.50,-4.35,1.95,-5.55,"")
    ]
    cur.executemany("""
        INSERT INTO stocks (
            date, market, code, name, item12, open_price, high_price, close_price, low_price,
            volume, multiple, amplitude, change_range, rise_range, fall_range, signal
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, stocks)

    strategies = [
        ("量價突破", "成交張數大於 5,000，並觀察漲幅、振幅與突破條件。", 1),
        ("均線轉強", "短期均線向上，搭配成交量放大。", 1),
        ("KD金叉", "K 值向上突破 D 值，搭配量能過濾。", 1),
        ("紫燈條件", "多條件同日成立後，隔日依指定價格進場。", 1)
    ]
    cur.executemany("INSERT INTO strategies (name, description, active) VALUES (?, ?, ?)", strategies)

    users = [
        ("王先生", "wang@example.com", "進階版", "啟用"),
        ("陳小姐", "chen@example.com", "基礎版", "啟用"),
        ("林先生", "lin@example.com", "客製版", "建置中")
    ]
    cur.executemany("INSERT INTO users (name, email, plan, status) VALUES (?, ?, ?, ?)", users)

    logs = [
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "TWSE", "成功", 1045, "上市資料更新完成"),
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "OTC", "成功", 839, "上櫃資料更新完成"),
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Signal", "成功", 16, "策略訊號計算完成")
    ]
    cur.executemany("INSERT INTO crawler_logs (run_time, source, status, rows_count, message) VALUES (?, ?, ?, ?, ?)", logs)

    conn.commit()
    conn.close()
    return {"ok": True, "message": "sample data inserted"}

# Must be last
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

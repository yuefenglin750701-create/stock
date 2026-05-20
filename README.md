# Stock Intelligence Platform 即時版（含前台 + 後台 + API + 篩選）

## 啟動方式

在此資料夾開啟 Anaconda Prompt 或命令提示字元：

```bash
pip install -r requirements.txt
python main.py
```

打開前台：

```text
http://127.0.0.1:8000/
```

打開後台：

```text
http://127.0.0.1:8000/admin.html
```

## 第一次使用

1. 先啟動 `python main.py`
2. 進入後台
3. 點「匯入範例資料」
4. 回前台即可看到即時資料與篩選功能

## 前台已支援

- 證券代號篩選
- 證券名稱篩選
- 日期篩選
- 月份篩選
- 市場 TWSE / OTC 篩選
- 成交張數門檻
- 只看策略訊號
- 每 30 秒自動更新
- 深色 / 淺色模式
- 即時圖表
- 客製化需求寫入資料庫

## 後台已支援

- 資料庫狀態
- 股票資料管理
- 策略管理
- 用戶管理
- 客製化需求
- 爬蟲執行紀錄
- 匯入範例資料

## 如何接你的正式爬蟲？

請看：

```text
crawler_to_db_template.py
```

你的爬蟲產生 DataFrame 後，呼叫：

```python
insert_dataframe_to_db(df, replace_same_date=True)
```

即可讓前台與後台自動讀到最新資料。

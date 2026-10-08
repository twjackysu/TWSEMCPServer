# 🚀 TWStockMCPServer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![API Tests](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml/badge.svg)](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml)

一個全面的**模型上下文協議 (MCP) 伺服器**，專為台灣證券交易所 (TWSE) 數據分析設計，提供即時股票資訊、財務報表、ESG 數據和趨勢分析功能。


## 🌏 語言版本

- [English](README_en-us.md) | **繁體中文**

## 🎬 示範影片

### VSCode Copilot demo
![VSCode Copilot demo](./staticFiles/sample-ezgif.com-resize.gif)

### Gemini CLI demo
![Gemini CLI demo](./staticFiles/gemini-cli-demo.gif)

*觀看 TWStockMCPServer 功能展示*

## ✨ 五大投資分析情境

### 📊 **個股趨勢研判**
短中長期技術面、基本面、籌碼面綜合分析
> *"分析台積電(2330)最近的走勢" / "鴻海(2317)適合長期投資嗎？"*

### 💰 **外資投資解讀**
外資持股、產業流向、個股進出追蹤
> *"外資最近在買什麼股票？" / "半導體業外資投資趨勢如何？"*

### 🔥 **市場熱點捕捉**
重大訊息、異常成交、權證活躍度監控
> *"今天有什麼重大消息？" / "哪些股票交易量異常活躍？"*

### 💎 **股利投資規劃**
高殖利率篩選、除權息行事曆、配息穩定性分析
> *"推薦一些高殖利率股票" / "下個月有哪些公司要除權息？"*

### 🎯 **投資標的篩選**
價值股/成長股篩選、ESG風險評估
> *"幫我找一些被低估的價值股" / "ESG表現好的公司有哪些？"*

## 🧮 進階功能

### 期貨籌碼與選擇權分析
Put/Call Ratio、大額交易人未沖銷部位、三大法人期貨/選擇權部位
> *"台指期籌碼現在偏多還是偏空？" / "選擇權大額交易人在哪個價位布局？"*

### 三大法人籌碼流向
上市/上櫃三大法人買賣超、外資產業配置
> *"三大法人今天買超哪些股票？" / "外資在哪個產業加碼？"*

### 個股財報體檢
獲利能力、成長性、財務結構、配息政策、公司治理五面向分析
> *"幫我做台積電的財報體檢" / "這家公司的財務體質健不健康？"*

### 買前風險掃描
處置股、注意股、當沖限制、停資停券名單比對
> *"這檔股票買進前有沒有被列處置或注意？"*

### 期貨/三大法人歷史回溯查詢
openapi.taifex.com.tw 僅提供最新一個交易日，本專案改用期交所網站下載頁面
（`www.taifex.com.tw`）：預設查最新交易日，也可回溯查詢期貨/選擇權每日行情、三大法人部位、大額交易人部位
> *"幫我拉台指期最近一個月的每日OHLC" / "外資期貨部位過去三個月怎麼變化？"*

### 財報／營收／股利多期歷史
財報、月營收、股利改由公開資訊觀測站（MOPS）提供（上市、上櫃、興櫃、公發公司皆可）：預設最新一期，
也可查任意過去季度的綜合損益表、資產負債表、**現金流量表**，多個月份的月營收，多年度股利分派，以及法說會行事曆；
另有重大訊息全文、董監持股與設質、內部人每月持股異動、庫藏股買回、背書保證與資金貸與
> *"比較台積電過去四季的毛利率和自由現金流" / "鴻海近五年配息穩定嗎？" / "這個月有哪些公司開法說會？" / "最近有哪些公司在買庫藏股？"*

### 籌碼集中度與上櫃歷史
集保戶股權分散表（千張大戶、散戶持股比例），上櫃個股日K、三大法人、融資融券可回溯任意過去日期；
上市當沖統計、除權息結果、類股指數歷史
> *"環球晶的大戶持股比例是多少？" / "半導體類指數上個月表現如何？"*

### 總體經濟
國發會景氣對策信號（景氣燈號）與領先/同時/落後指標、臺灣 PMI/NMI、中央銀行每日匯率
> *"現在景氣燈號是什麼顏色？" / "新台幣最近一個月升還是貶？"*

## ⚙️ 快速開始

### 🚀 線上使用（由 [Prefect Horizon](https://horizon.prefect.io/) 提供支援）

本專案由 **Prefect Horizon** 提供支援，免費託管線上 remote MCP Server：
```json
{
  "twstockmcpserver": {
    "transport": "streamable_http",
    "url": "https://TW-Stock-MCP-Server.fastmcp.app/mcp"
  }
}
```

> ⚠️ **使用限制**：為維持服務永續，此線上服務設有合理使用量上限（非無限制）。若需**商業使用**或較高呼叫量，強烈建議改用下方 Docker／本機方式自行架設伺服器，或使用 [Prefect Horizon](https://horizon.prefect.io/) 的付費方案。
>
> 🙏 感謝 [Prefect Horizon](https://horizon.prefect.io/) 支援本開源專案，讓社群能免費輕鬆試用。

### 🐳 Docker 使用（stdio）
```json
{
  "twstockmcpserver": {
    "command": "docker",
    "args": [
      "run",
      "-i",
      "--rm",
      "--pull=always",
      "-e",
      "MCP_STDIO=1",
      "ghcr.io/twjackysu/twsemcpserver:latest"
    ]
  }
}
```

### 🔧 本地安裝
```bash
git clone https://github.com/twjackysu/TWStockMCPServer.git
cd TWStockMCPServer
uv sync && uv run fastmcp dev server.py
```

## 📡 資料來源

| 來源 | 說明 | Tools |
|------|------|-------|
| [TWSE OpenAPI](https://openapi.twse.com.tw) | 台灣證交所官方 API — 公司治理、ESG、財務比率、公告名單、權證、券商等 | 106 個 |
| [TWSE Web API](https://www.twse.com.tw) | 證交所網頁 API（皆預設最新交易日，可查任意過去日期）— 個股日K、月均價、估值、融資融券、上市三大法人買賣超（金額/股數）、全市場收盤行情、加權指數歷史、外資持股歷史、個股月/年成交彙總、鉅額交易明細、融券借券餘額/成交、除權除息計算結果、當日沖銷交易標的與統計、全部指數（含類股指數）收盤（皆可查最新或任意過去日期） | 19 個 |
| [MIS 即時報價](https://mis.twse.com.tw) | 盤中即時多股報價（上市+上櫃） | 1 個 |
| [TPEx OpenAPI](https://www.tpex.org.tw/openapi) | 櫃買中心 — 上櫃日收盤（最新一日；指定日期改用網站資料）、三大法人彙總、注意/處置股、零股、指數 | 6 個 |
| [TAIFEX OpenAPI](https://openapi.taifex.com.tw) | 期交所 — 選擇權分析（Delta/未平倉增減）、保證金、年月統計 | 6 個 |
| [TAIFEX 網站下載](https://www.taifex.com.tw) | 期交所網站資料下載頁面 — 期貨／選擇權每日行情、三大法人（期貨/選擇權分計、總表、各契約、買賣權分計）、期貨與選擇權大額交易人部位、Put/Call Ratio（預設最新交易日，可回溯查詢；openapi.taifex.com.tw 僅提供最新一日） | 10 個 |
| [公開資訊觀測站 MOPS](https://mops.twse.com.tw) | 綜合損益表／資產負債表／現金流量表、月營收、股利分派（皆預設最新一期，可查任意過去期間；上市櫃、興櫃、公發公司皆可）、重大訊息（含全文）、董監持股與設質、內部人持股異動、庫藏股、背書保證與資金貸與、法人說明會 | 11 個 |
| [TPEx 網站](https://www.tpex.org.tw) | 櫃買中心網站 API — 上櫃個股日K、三大法人買賣超、融資融券、本益比/殖利率/淨值比、外資持股排行、除權除息計算結果（預設最新交易日，可回溯任意過去日期） | 6 個 |
| [集保結算所開放資料](https://opendata.tdcc.com.tw) | 集保戶股權分散表（最新一週，含大戶／散戶持股比例） | 1 個 |
| [國發會](https://data.gov.tw/dataset/6099) | 景氣對策信號與景氣指標（1982 起）、臺灣採購經理人指數 PMI/NMI | 2 個 |
| [中央銀行](https://cpx.cbc.gov.tw) | 新台幣及主要貿易對手通貨對美元每日匯率（1993 起） | 1 個 |
| 衍生分析（由上述資料計算） | 還原權息日K、技術指標（MA、KD、RSI、MACD、布林通道）、估值選股 screener、同業比較（上市+上櫃） | 4 個 |

## 🤝 參與貢獻
歡迎PR！

## 📄 授權 & 免責聲明
MIT授權 | 僅供參考，不構成投資建議


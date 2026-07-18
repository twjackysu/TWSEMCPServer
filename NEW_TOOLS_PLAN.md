# 新增 Tools 計畫

現況（截至 v1.5.0）：165 tools。缺口集中在**歷史回溯查詢**——TWSE/TAIFEX 的 OpenAPI
大多只回傳最新一日快照，但兩個交易所官網自己的 rwd JSON / HTML表單下載端點支援任意日期區間。
本文件盤點這些缺口，所有端點皆已用 `requests` 實際打過確認可用（非猜測）。

## 🔴 Tier 1 — 高價值缺口（優先實作）

### TWSE（`www.twse.com.tw/rwd/zh/...`，GET + JSON，與現有 `get_twse_institutional_investors_summary`／T86 同模式）

| # | 新 tool | 端點 | 內容 | 實測 |
|---|--------|------|------|------|
| 1 | `get_market_institutional_amounts_history` | `fund/BFI82U` | 市場層級三大法人買賣金額統計（日/週/月，`type` 參數） | ✅ stat=OK |
| 2 | `get_all_stocks_daily_close` | `afterTrading/MI_INDEX` | 指定日期全部上市個股收盤行情（開高低收/量/漲跌） | ✅ stat=OK |
| 3 | `get_market_turnover_history` | `afterTrading/FMTQIK` | 每日市場成交量值＋加權指數收盤，一次回整月 | ✅ 21筆/月 |
| 4 | `get_taiex_index_history` | `TAIEX/MI_5MINS_HIST` | 加權指數日 OHLC 歷史（整月），大盤 K 棒 | ✅ 21筆/月 |
| 5 | `get_foreign_holdings_history` | `fund/MI_QFIIS` | 指定日期全個股外資持股比率歷史（openapi 只有最新） | ✅ 1347筆 |

### TAIFEX（`www.taifex.com.tw/cht/3/...Down`，POST + Big5 CSV，重用 PR #49 的 `fetch_bytes` + `decode_and_parse_csv`）

| # | 新 tool | 端點 | 內容 | 實測 |
|---|--------|------|------|------|
| 6 | `get_put_call_ratio_history` | `pcRatioDown` | P/C ratio 任意區間（openapi 只給滾動 21 天） | ✅ 8天=8筆 |
| 7 | `get_options_institutional_calls_puts_history` | `callsAndPutsDateDown` | 三大法人 CALL/PUT 分計歷史 | ✅ 48筆 |
| 8 | `get_large_traders_futures_history` | `largeTraderFutDown` | 大額交易人期貨未平倉歷史（⚠️量大：8天10964筆，須強制 contract 篩選＋限區間） | ✅ |
| 9 | `get_options_daily_history` | `optDataDown` | 選擇權每日 OHLC 歷史（⚠️超大：5天33332筆，須強制指定契約/月份＋限區間） | ✅ |

## 🟡 Tier 2 — 次批

| # | 新 tool | 端點 | 內容 |
|---|--------|------|------|
| 10 | `get_stock_monthly_history` / `get_stock_yearly_history` | TWSE `FMSRFK` / `FMNPTK` | 個股月/年成交彙總（長期趨勢不用逐月拉） |
| 11 | `get_institutional_total_history` | TAIFEX `totalTableDateDown` | 三大法人期＋權總表歷史 |
| 12 | `get_institutional_fut_opt_split_history` | TAIFEX `futAndOptDateDown` | 期貨/選擇權二類分計歷史 |
| 13 | `get_options_institutional_by_contract_history` | TAIFEX `optContractsDateDown` | 法人各選擇權契約歷史 |
| 14 | `get_block_trades_detail` | TWSE `block/BFIAUU`（+個股版） | 鉅額交易逐筆明細 by date（現有 openapi 只有量值統計） |
| 15 | `get_sbl_balance_history` | TWSE `TWT93U` / `TWTASU` | 融券＋借券賣出餘額/成交 by date（補 MI_MARGN 沒有的借券面） |

## ⚪ Tier 3 — 低優先（暫不做）

- TWT38U/43U/44U 單法人買賣超（T86 已含三法人明細，重複）
- TWT47U/54U 週報月報（可由 T86 聚合）
- 盤後定價 BFT41U、零股 TWT53U/TWTC7U、成交前20 MI_STOCK20 歷史版
- TAIFEX 夜盤系列（`...AhDown`）、最後結算價、逐筆 tick（`TimeAndSalesData`，單日幾十萬筆，MCP text 輸出不現實，不做）

## 實作備註

1. **TWSE rwd** 與現有 T86 完全同模式：`fetch_json(url, params={"response":"json","date":...})`，ROC 日期用 `utils/date_helper.py`。零新基礎設施。
2. **TAIFEX Down** 重用 PR #49 建立的 `fetch_bytes` + `decode_and_parse_csv`（`tools/taifex/futures_daily_history.py`）。零新基礎設施。
3. 量大端點（#8/#9）tool 內強制篩選參數＋span 上限，照 `institutional_futures_history` 的 92 天 client-side cap 慣例。
4. 每個都補 `tests/e2e/` 欄位順序測試（CSV 類）或 `test_hardcoded_fields_exist`（JSON 類）。
5. PR 切分：**PR-A** = TWSE Tier1（5個）、**PR-B** = TAIFEX Tier1（4個）、**PR-C** = Tier2。

## 進度

- [x] PR-A：TWSE Tier 1（#1–#5）— #53
- [x] PR-B：TAIFEX Tier 1（#6–#9）— #54
- [x] PR-C1：TWSE Tier 2（#10, #14, #15）— #56
- [x] PR-C2：TAIFEX Tier 2（#11–#13）— 本 PR

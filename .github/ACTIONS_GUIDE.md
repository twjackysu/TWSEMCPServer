# GitHub Actions 設定說明

## 自動化測試工作流程

`.github/workflows/api-tests.yml`（「TWSE API E2E Tests」）每天定時、也可手動執行完整的 live 測試，
用來偵測 TWSE／TPEx／TAIFEX／MOPS 等第三方 API 的介面是否有變化。它不會在 push 或 Pull Request 時觸發。

測試分兩類（細節見 `CLAUDE.md` 的 Testing 章節）：
- **Live contract tests**（`tests/e2e/`、`tests/test_api_schemas.py`）：打真實的第三方 API，只驗證介面契約。
- **Offline unit tests**（其餘 `tests/test_*.py`）：用假資料測我們自己的邏輯，不打網路。

## 觸發方式

### 1. 定時執行
每天早上 9:00（台灣時間）自動執行完整測試：

```yaml
schedule:
  - cron: '0 1 * * *'  # UTC 1:00 = 台灣時間 9:00
```

### 2. 手動觸發

1. 進入 GitHub 專案頁面的 "Actions" 標籤
2. 選擇 "TWSE API E2E Tests" workflow
3. 點擊右側的 "Run workflow"
4. 選擇測試範圍，再點 "Run workflow" 確認

## 測試範圍選項

| 選項 | 執行的測試 |
|------|-----------|
| all（預設） | `pytest tests/`（全部，含 `--cov` 終端機覆蓋率報告、失敗自動重跑 2 次） |
| history | `tests/e2e/test_history_api.py` |
| realtime | `tests/e2e/test_realtime_api.py` |
| otc | `tests/e2e/test_otc_api.py` |
| taifex | `tests/e2e/test_taifex_api.py`、`test_taifex_new_api.py`、`test_taifex_batch2_api.py` |

## 測試結果處理

### ✅ 測試成功
- 顯示綠色勾勾
- 若是定時執行，且有之前自動建立的失敗 issue，會留言並關閉
- 覆蓋率只輸出在執行日誌中，沒有上傳到 Codecov 等外部服務

### ❌ 測試失敗

定時或手動執行失敗時，會：

1. **自動建立 Issue**
   - 標題：⚠️ TWSE API Schema Change Detected
   - 標籤：`api-change`、`bug`、`automated`
   - 內容：失敗原因的可能方向、測試日誌連結、建議的處理步驟
2. **避免重複 Issue**：如果已有相同的開啟中 issue，改為新增評論

> 注意：自動關閉依賴 GitHub 的 issue 列表 API。曾經有一個 issue（#23）在測試恢復後沒被自動關閉，
> 直接以編號查詢仍是 open，但列表與搜尋 API 都找不到它。遇到這種情況手動關閉即可。

失敗通知的處理步驟：
1. 檢查來源網站的 API 或頁面是否有更新
2. 查看測試日誌中的錯誤訊息
3. 更新相關的工具函數和測試
4. 更新 `CLAUDE.md` 的「External API Notes」（若是來源行為改變）

## 在 README 中加入 Badge

```markdown
[![TWSE API Tests](https://github.com/twjackysu/TWSEMCPServer/actions/workflows/api-tests.yml/badge.svg)](https://github.com/twjackysu/TWSEMCPServer/actions/workflows/api-tests.yml)
```

## 本地測試

在推送到 GitHub 之前，建議先在本地執行測試：

```bash
# 只跑 offline 測試（快，不打網路）
uv run pytest -m offline

# 快速測試（遇到第一個失敗就停）
python run_tests.py quick

# 執行所有測試
python run_tests.py all

# 依類別執行 live 測試（history、realtime、otc、taifex、institutional、mops、macro、e2e）
python run_tests.py taifex

# 產生 HTML 覆蓋率報告
python run_tests.py cov
```

## 疑難排解

### Q: 手動觸發按鈕找不到？
A: 確認 workflow 檔案已經合併到主分支，並且重新整理頁面。

### Q: 測試在 GitHub 失敗但本地成功？
A: 可能是環境差異，檢查：
- Python 版本是否一致
- 依賴套件版本
- 網路連線問題（來源網站可能擋 GitHub Actions 的 IP，或暫時性斷線；暫時性狀況的測試會 skip 而不是失敗）

### Q: 如何停用定時測試？
A: 編輯 `.github/workflows/api-tests.yml`，註解掉 `schedule` 部分：

```yaml
# schedule:
#   - cron: '0 1 * * *'
```

### Q: 如何修改測試執行時間？
A: 修改 cron 表達式。例如改為每天下午 2:00：

```yaml
schedule:
  - cron: '0 6 * * *'  # UTC 6:00 = 台灣時間 14:00
```

Cron 表達式格式：`分 時 日 月 週`

## 維護建議

1. **定期檢查測試結果**：至少每週看一次定時測試的結果
2. **及時處理失敗的 issue**：API 變化時盡快更新程式碼
3. **新增功能時同時新增測試**：做法見 `CLAUDE.md` 的「Adding New Tools」
4. **更新文件**：修改資料來源時更新 `CLAUDE.md`（資料來源、External API Notes）與 README

## 參考資源

- [GitHub Actions 文件](https://docs.github.com/en/actions)
- [pytest 文件](https://docs.pytest.org/)

# GitHub Actions 設定說明

## 自動化測試工作流程

本專案設定了完整的 E2E 測試自動化流程，可以：
- 在每次 push/PR 時自動執行測試
- 每天定時檢查 TWSE API 是否有變化
- 支援手動觸發測試

## 檔案位置

`.github/workflows/api-tests.yml`

## 觸發方式

### 1. 自動觸發

#### Push/Pull Request
當程式碼推送到 `main` 或 `develop` 分支時，或建立 Pull Request 時自動執行。

#### 定時執行
每天早上 9:00 (台灣時間) 自動執行，用於偵測 TWSE API 的變化。

```yaml
schedule:
  - cron: '0 1 * * *'  # UTC 1:00 = 台灣時間 9:00
```

### 2. 手動觸發

前往 GitHub Actions 頁面手動執行測試：

1. 進入 GitHub 專案頁面
2. 點擊 "Actions" 標籤
3. 選擇 "TWSE API E2E Tests" workflow
4. 點擊右側的 "Run workflow" 按鈕
5. 選擇測試範圍：
   - **all** - 執行所有測試（預設）
   - **esg** - 只執行 ESG API 測試
   - **api_client** - 只執行 API Client 測試
6. 點擊 "Run workflow" 確認執行

## 測試範圍選項

| 選項 | 說明 | 執行的測試 |
|------|------|-----------|
| all | 執行所有測試（含覆蓋率報告） | `pytest tests/ -v --cov` |
| esg | 只執行 ESG API 測試 | `pytest tests/e2e/test_esg_api.py` |
| api_client | 只執行 API Client 測試 | `pytest tests/test_api_client.py` |

## 測試結果處理

### ✅ 測試成功
- 顯示綠色勾勾 ✅
- 產生覆蓋率報告並上傳到 Codecov
- 如果之前有失敗的 issue，自動關閉並留言

### ❌ 測試失敗

當定時測試或手動測試失敗時，GitHub Actions 會：

1. **自動建立 Issue**
   - 標題：⚠️ TWSE API Schema Change Detected
   - 標籤：`api-change`, `bug`, `automated`
   - 內容包含：
     - 失敗原因分析
     - 測試日誌連結
     - 建議的修復步驟

2. **避免重複 Issue**
   - 如果已有相同的開啟 issue，則新增評論
   - 不會建立重複的 issue

3. **通知資訊**
   ```
   ## 測試失敗通知
   
   E2E 測試失敗，可能原因：
   - 證交所 API schema 已變更
   - API 端點無法訪問
   - 資料格式不符合預期
   
   ### 測試詳情
   - 觸發方式: schedule
   - 分支: main
   - 提交: abc123...
   - 執行時間: 2025-10-15T01:00:00Z
   
   ### 建議行動
   1. 檢查證交所 API 文件是否有更新
   2. 查看測試日誌中的錯誤訊息
   3. 更新相關的工具函數和測試
   4. 更新 API_TODO.md 文件
   ```

## 在 README 中加入 Badge

可以在 `README.md` 中加入以下 badge：

```markdown
[![TWSE API Tests](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml/badge.svg)](https://github.com/twjackysu/TWStockMCPServer/actions/workflows/api-tests.yml)
```

顯示效果：
![Badge Example](https://img.shields.io/badge/tests-passing-brightgreen)

## 覆蓋率報告

測試完成後會自動上傳覆蓋率報告到 Codecov。

要在 README 中顯示覆蓋率 badge：

```markdown
[![codecov](https://codecov.io/gh/twjackysu/TWStockMCPServer/branch/main/graph/badge.svg)](https://codecov.io/gh/twjackysu/TWStockMCPServer)
```

## 本地測試

在推送到 GitHub 之前，建議先在本地執行測試：

```powershell
# 快速測試
python run_tests.py quick

# 執行所有測試
python run_tests.py all

# 只測試 ESG API
python run_tests.py esg

# 產生覆蓋率報告
python run_tests.py cov
```

## 疑難排解

### Q: 手動觸發按鈕找不到？
A: 確認 workflow 檔案已經合併到主分支，並且重新整理頁面。

### Q: 測試在 GitHub 失敗但本地成功？
A: 可能是環境差異，檢查：
- Python 版本是否一致
- 依賴套件版本
- 網路連線問題（GitHub Actions 可能被證交所阻擋）

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

1. **定期檢查測試結果**：至少每週檢查一次自動測試的結果
2. **及時處理失敗的 issue**：API 變化時盡快更新程式碼
3. **保持測試覆蓋率**：新增功能時同時新增測試
4. **更新文件**：修改 API 時更新 `TESTING.md` 和 `API_TODO.md`

## 參考資源

- [GitHub Actions 文件](https://docs.github.com/en/actions)
- [pytest 文件](https://docs.pytest.org/)
- [Codecov 整合指南](https://docs.codecov.com/docs)

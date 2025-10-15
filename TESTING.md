# TWSE MCP Server Testing Guide

## 測試架構

本專案使用 pytest 進行 E2E 測試，確保 TWSE API 的穩定性和資料格式正確性。

## 安裝測試依賴

使用 uv：
```bash
uv sync --extra dev
```

或使用 pip：
```bash
pip install -r requirements-dev.txt
```

## 執行測試

### 執行所有測試
```bash
# 使用 uv (推薦)
uv run pytest

# 或直接使用 pytest
pytest
```

### 執行特定測試檔案
```bash
# ESG API 測試
uv run pytest tests/e2e/test_esg_api.py

# API Client 測試
uv run pytest tests/test_api_client.py
```

### 執行特定測試類別
```bash
uv run pytest tests/e2e/test_esg_api.py::TestAnticompetitiveLitigationAPI
```

### 執行特定測試函數
```bash
uv run pytest tests/e2e/test_esg_api.py::TestAnticompetitiveLitigationAPI::test_api_endpoint_is_accessible
```

### 顯示詳細輸出
```bash
uv run pytest -v -s
```

### 產生覆蓋率報告
```bash
uv run pytest --cov=tools --cov=utils --cov-report=html
```

覆蓋率報告會產生在 `htmlcov/index.html`

## 測試說明

### E2E 測試 (tests/e2e/)

#### test_esg_api.py
測試所有 ESG 相關的 API：
- ✅ API 端點可訪問性
- ✅ 回應 schema 驗證
- ✅ 資料格式檢查
- ✅ 過濾邏輯驗證
- ✅ 公司代號查詢功能

**測試的 API：**
- `/opendata/t187ap46_L_20` - 反競爭行為法律訴訟
- `/opendata/t187ap46_L_9` - 功能性委員會
- `/opendata/t187ap46_L_8` - 氣候相關議題管理
- `/opendata/t187ap46_L_19` - 風險管理政策
- `/opendata/t187ap46_L_13` - 供應鏈管理
- `/opendata/t187ap46_L_16` - 資訊安全

### API Client 測試 (tests/test_api_client.py)

測試 `TWSEAPIClient` 的基礎功能：
- ✅ `get_data()` 回傳格式
- ✅ `get_company_data()` 過濾功能
- ✅ 錯誤處理

## GitHub Actions CI/CD

### 自動執行
- **Push/PR**: 推送到 main 或 develop 分支時自動執行
- **定時執行**: 每天早上 9:00 (台灣時間) 自動執行

### 手動觸發

1. 前往 GitHub Actions 頁面
2. 選擇 "TWSE API E2E Tests" workflow
3. 點擊 "Run workflow"
4. 選擇測試範圍：
   - `all` - 執行所有測試
   - `esg` - 只執行 ESG API 測試
   - `api_client` - 只執行 API Client 測試

### 失敗通知

當定時測試或手動測試失敗時，GitHub Actions 會：
1. 自動建立一個 issue，標記為 `api-change` 和 `bug`
2. 包含失敗的詳細資訊和測試日誌連結
3. 如果已有相同的開啟 issue，則新增評論而不是建立新 issue

當測試恢復正常時，會自動關閉相關的 issue。

## 新增測試

### 新增 ESG API 測試

在 `tests/e2e/test_esg_api.py` 中新增：

```python
def test_new_esg_api(self):
    """測試新的 ESG API."""
    data = TWSEAPIClient.get_data("/opendata/新的端點")
    assert data is not None
    # 加入更多驗證...
```

### 新增參數化測試

```python
@pytest.mark.parametrize("endpoint,expected_field", [
    ("/opendata/t187ap46_L_20", "公司代號"),
    ("/opendata/t187ap46_L_9", "公司名稱"),
])
def test_api_has_field(self, endpoint, expected_field):
    data = TWSEAPIClient.get_data(endpoint)
    assert expected_field in data[0]
```

## 測試最佳實踐

1. **每個 API 至少要有基礎測試**：確保端點可訪問和 schema 正確
2. **測試邊界情況**：空資料、無效代號、格式錯誤等
3. **保持測試獨立**：每個測試應該能獨立執行
4. **使用有意義的斷言訊息**：幫助快速定位問題
5. **定期更新測試資料**：如果已知資料變化，更新測試中的預期值

## 常見問題

### Q: 測試失敗但 API 實際可用？
A: 可能是證交所的資料格式變更，檢查測試日誌中的具體錯誤，更新測試的預期值。

### Q: 如何跳過特定測試？
A: 使用 `@pytest.mark.skip` 裝飾器：
```python
@pytest.mark.skip(reason="API 暫時維護中")
def test_something(self):
    pass
```

### Q: 如何只執行特定標記的測試？
A: 
```bash
pytest -m e2e  # 只執行標記為 e2e 的測試
pytest -m "not slow"  # 跳過慢速測試
```

## 貢獻

新增 API 工具時，請同時新增對應的 E2E 測試，確保：
- [ ] API 端點可訪問性測試
- [ ] Schema 驗證測試
- [ ] 資料格式測試
- [ ] 過濾/查詢邏輯測試

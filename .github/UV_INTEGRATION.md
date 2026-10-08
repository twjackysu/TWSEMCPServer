# GitHub Actions 與 UV 整合總結

## 已完成的改進

### 1. 依賴管理統一化
✅ 將測試依賴整合到 `pyproject.toml` 中
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.1",
    "pytest-asyncio>=0.21.0",
]
```

### 2. GitHub Actions 使用 UV
✅ 完整的 UV 整合流程：

```yaml
- name: 📦 Install uv
  uses: astral-sh/setup-uv@v5
  with:
    enable-cache: true

- name: 📦 Install dependencies
  run: |
    uv sync --extra dev

- name: 🧪 Run all tests
  run: |
    uv run pytest tests/ -v --tb=short --cov=tools --cov=utils
```

### 3. 所有測試命令都使用 UV

✅ 三種測試模式都已更新：
- `uv run pytest` - 執行所有測試
- `uv run pytest tests/e2e/test_esg_api.py` - ESG API 測試
- `uv run pytest tests/test_api_client.py` - API Client 測試

## 優勢

### 🚀 速度提升
- UV 比 pip 快 10-100 倍
- GitHub Actions 啟用了 UV cache，第二次執行更快

### 📦 依賴管理
- 單一來源（`pyproject.toml`）管理所有依賴
- 自動鎖定版本（`uv.lock`）
- 開發依賴與生產依賴分離

### 🔒 可重現性
- `uv.lock` 確保所有環境使用相同版本
- 本地開發環境與 CI/CD 完全一致

### 🛠️ 簡化流程
- 不需要分別管理 `requirements.txt` 和 `requirements-dev.txt`
- 一個命令安裝所有依賴：`uv sync --extra dev`

## 本地開發工作流程

### 初次設定
```bash
# 安裝 UV (如果尚未安裝)
pip install uv

# 同步專案依賴（包含開發依賴）
uv sync --extra dev
```

### 日常開發
```bash
# 執行測試
uv run pytest

# 執行特定測試
uv run pytest tests/e2e/test_esg_api.py -v

# 產生覆蓋率報告
uv run pytest --cov=tools --cov=utils --cov-report=html

# 執行快速測試腳本
uv run python run_tests.py quick
```

### 新增依賴
```bash
# 新增生產依賴
uv add requests

# 新增開發依賴
uv add --dev pytest-timeout

# 同步依賴
uv sync
```

## CI/CD 工作流程

### 自動觸發
- Push 到 main/develop → 自動執行完整測試
- Pull Request → 自動執行完整測試
- 每天早上 9:00 → 自動執行完整測試（偵測 API 變化）

### 手動觸發
1. 前往 GitHub Actions 頁面
2. 選擇 "TWSE API E2E Tests"
3. 點擊 "Run workflow"
4. 選擇測試範圍（all/esg/api_client）
5. 執行

## 檔案清單

### 核心設定檔
- ✅ `pyproject.toml` - 專案依賴與元資料
- ✅ `uv.lock` - 鎖定版本（由 uv 自動生成）
- ✅ `.github/workflows/api-tests.yml` - CI/CD 設定

### 測試相關
- ✅ `pytest.ini` - Pytest 設定
- ✅ `tests/` - 測試程式碼目錄
- ✅ `tests/conftest.py` - Pytest fixtures
- ✅ `tests/e2e/test_esg_api.py` - ESG API E2E 測試
- ✅ `tests/test_api_client.py` - API Client 測試

### 文件
- ✅ `CLAUDE.md` - 測試與開發指南（Testing 章節）
- ✅ `.github/ACTIONS_GUIDE.md` - GitHub Actions 使用指南
- ✅ `run_tests.py` - 快速測試腳本

## 相容性說明

### 保留 requirements-dev.txt
為了相容不使用 UV 的環境，我們仍保留 `requirements-dev.txt`：
```bash
# 傳統方式（不推薦）
pip install -r requirements-dev.txt
pytest
```

### 推薦方式
```bash
# UV 方式（推薦）
uv sync --extra dev
uv run pytest
```

## 疑難排解

### Q: UV 找不到？
```bash
pip install uv
```

### Q: 依賴安裝失敗？
```bash
# 清除快取重新安裝
uv cache clean
uv sync --extra dev
```

### Q: GitHub Actions 失敗？
檢查日誌中的 "Install dependencies" 步驟，確認：
1. UV 是否成功安裝
2. `uv sync --extra dev` 是否執行成功
3. 所有測試命令是否都使用 `uv run pytest`

## 檢查清單

在推送之前，確認：
- [ ] `pyproject.toml` 包含所有必要依賴
- [ ] 本地執行 `uv run pytest` 成功
- [ ] `.github/workflows/api-tests.yml` 所有命令都使用 `uv run`
- [ ] 文件已更新（CLAUDE.md、ACTIONS_GUIDE.md）

## 下一步

1. ✅ 推送到 GitHub
2. ✅ 觀察 GitHub Actions 執行結果
3. ✅ 手動觸發一次測試驗證
4. ✅ 檢查測試覆蓋率報告
5. ✅ 如果成功，在 README 加入測試 badge

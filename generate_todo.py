import json
import os
import re

# 讀取 swagger 文件
with open('staticFiles/swagger_decoded.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

paths = data['paths']
result = {}

# 掃描所有 tools 目錄中的 Python 文件，查找已實作的 API endpoints
implemented_apis = set()

def scan_directory(directory):
    """遞迴掃描目錄，找出所有已實作的 API endpoints"""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 使用更精確的正則表達式
                        # 匹配雙引號中的路徑
                        matches = re.findall(r'"(/[^"]+)"', content)
                        # 匹配單引號中的路徑
                        matches += re.findall(r"'(/[^']+)'", content)
                        
                        for match in matches:
                            # 只保留以特定前綴開頭的 API 路徑
                            if any(match.startswith(f'/{prefix}/') for prefix in 
                                   ['opendata', 'exchangeReport', 'indicesReport', 'news', 
                                    'company', 'fund', 'block', 'ETFReport', 'brokerService', 
                                    'Announcement', 'SBL', 'holidaySchedule', 'static']):
                                # 忽略包含 {suffix} 或 f-string 標記的路徑
                                if '{' not in match and '}' not in match:
                                    implemented_apis.add(match)
                except Exception as e:
                    print(f'Warning: 無法讀取 {filepath}: {e}')

# 掃描 tools 目錄
print('正在掃描已實作的 API...')
scan_directory('tools')

# 處理動態生成的 endpoints（如 t187ap06_L, t187ap07_L 等）
# 這些是通過程式碼動態選擇的 API endpoints
dynamic_patterns = {
    '/opendata/t187ap06_L': ['_X_ci', '_X_basi', '_X_bd', '_X_fh', '_X_ins', '_X_mim'],  # 綜合損益表
    '/opendata/t187ap07_L': ['_X_ci', '_X_mim'],  # 資產負債表
}

# 添加動態生成的 endpoints
for base, suffixes in dynamic_patterns.items():
    for suffix in suffixes:
        endpoint = base.replace('_L', suffix)
        implemented_apis.add(endpoint)

print(f'找到 {len(implemented_apis)} 個已實作的 API endpoints')

# 按 tag 分類所有 API
for path in paths:
    if 'get' in paths[path] and 'tags' in paths[path]['get']:
        tag = paths[path]['get']['tags'][0]
        summary = paths[path]['get']['summary']
        if tag not in result:
            result[tag] = []
        result[tag].append({'path': path, 'summary': summary})

# 生成 Markdown 內容
total_apis = sum(len(items) for items in result.values())
implemented_count = sum(1 for tag_items in result.values() for item in tag_items if item['path'] in implemented_apis)

output = '# TWSE API 實作進度\n\n'
output += f'總計: {total_apis} 個 API\n'
output += f'已完成: {implemented_count} 個 ({implemented_count/total_apis*100:.1f}%)\n'
output += f'未完成: {total_apis - implemented_count} 個\n\n'
output += '---\n\n'

for tag, items in result.items():
    tag_implemented = sum(1 for item in items if item['path'] in implemented_apis)
    output += f'## {tag} ({len(items)} 個，已完成 {tag_implemented} 個)\n\n'
    for item in items:
        # 如果 API 已實作，就打勾
        checkbox = '[x]' if item['path'] in implemented_apis else '[ ]'
        output += f'- {checkbox} {item["summary"]} - `{item["path"]}`\n'
    output += '\n'

# 寫入文件
with open('API_TODO.md', 'w', encoding='utf-8') as f:
    f.write(output)

print(f'✓ 已生成 API_TODO.md')
print(f'  總計: {total_apis} 個 API')
print(f'  已完成: {implemented_count} 個 ({implemented_count/total_apis*100:.1f}%)')
print(f'  未完成: {total_apis - implemented_count} 個')

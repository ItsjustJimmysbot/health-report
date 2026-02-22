# PERMANENT POLICY - AI Analysis Generation
# Version: 1.0
# Effective: Immediately
# Violation: Terminate generation, alert user

## STRICT RULES (不可违反)

### 1. 禁止的生成方式 (FORBIDDEN)
- ❌ inline f-string 模板填充 (如: f"心率今日为{v}ms...")
- ❌ 代码内硬编码分析文本
- ❌ 复用旧分析文本
- ❌ /tmp 缓存文件
- ❌ 任何非 AI 对话生成的分析

### 2. 唯一允许的流程 (REQUIRED)
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 1. 提取数据  │ → │ 2. AI对话分析 │ → │ 3. 保存JSON  │ → │ 4. 生成报告  │
│  (脚本)      │    │  (当前对话)   │    │  (workspace) │    │  (脚本)      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 3. 验证检查点 (CHECKPOINTS)
每个报告生成前必须确认：
- [ ] 分析文本来自当前对话 (有 message history)
- [ ] 分析中引用的数字与源数据一致
- [ ] 无 f-string / format 模板痕迹
- [ ] 无 /tmp 路径访问

### 4. 违规处理 (VIOLATION HANDLING)
如果检测到违规生成方式：
1. 立即停止
2. 报告给用户
3. 删除违规输出
4. 重新按正确流程执行

---

## 技术实现

### 预生成检查脚本
位置: `scripts/validate_analysis_source.py`
功能: 验证 AI 分析是否来自当前对话

### 钩子机制
在 `generate_report_v5_ai.py` 开头插入:
```python
import sys
if not os.environ.get('AI_ANALYSIS_VALIDATED'):
    print("ERROR: 必须经过AI对话分析才能生成报告")
    print("正确流程: 提取数据 → AI分析 → 保存JSON → 生成报告")
    sys.exit(1)
```

---

## 正确流程示例

### Step 1: 提取数据 (脚本执行)
```bash
python3 scripts/extract_health_data.py 2026-02-19 > workspace/data_2026-02-19.json
```

### Step 2: AI 分析 (当前对话)
我读取数据，逐条分析，写出完整的 AI 分析文本。

### Step 3: 保存 JSON (用户确认后)
```bash
cat > workspace/ai_analysis_2026-02-19.json << 'EOF'
{ [我写的分析] }
EOF
```

### Step 4: 生成报告 (脚本执行，带验证)
```bash
export AI_ANALYSIS_VALIDATED=1
python3 scripts/generate_report_v5_ai.py 2026-02-19 < workspace/ai_analysis_2026-02-19.json
```

---

## 违规检测关键词

如果代码或命令中包含以下模式，视为违规:
- `f"...{var}..."` 在分析文本生成中
- `"..." + var + "..."` 字符串拼接分析
- `/tmp/ai_analysis` 路径
- `build_data_from_source` 直接生成分析字段

---

**签署**: health agent
**日期**: 2026-02-23
**承诺**: 永远不再使用 f-string 模板生成 AI 分析

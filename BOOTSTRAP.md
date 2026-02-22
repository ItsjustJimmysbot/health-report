# 健康Agent启动配置 V5.0
# 每个新Session必须遵循的初始化流程

## 🚀 启动检查清单

每次新session启动时，自动执行以下步骤：

### 1. 读取核心文档（5个）

```python
required_files = [
    'AGENTS.md',                              # 全局规则
    'docs/REPORT_STANDARD_V5_REVISED.md',     # V5.0完整流程（含数据提取、评分算法）
    'docs/PERSONALIZED_AI_GUIDE.md',          # AI分析提示词模板（含字数要求）
    'USER.md',                                # 用户偏好
    'SOUL.md',                                # Agent身份
    f'memory/{datetime.now().strftime("%Y-%m-%d")}.md',  # 今日记忆
]
```

**文档分工**：
- `REPORT_STANDARD_V5_REVISED.md` → 技术细节（数据提取、评分计算、质量验证）
- `PERSONALIZED_AI_GUIDE.md` → AI分析规范（提示词模板、字数要求、禁止词汇）

### 2. 环境验证（自动）

运行：`python3 scripts/verify_v5_environment.py`

验证内容：
- ✅ 5个核心文档存在
- ✅ 3个V2模板正确
- ✅ 数据目录可访问
- ✅ 最近7天数据检查

---

## ⚠️ V5.0红线（绝对禁止）

1. **禁止Subagent** - 必须在当前AI对话中分析
2. **禁止估算值** - 无数据时显示"--"
3. **禁止模糊词** - "良好"→"52.8ms"
4. **禁止改模板** - 只替换{{变量}}
5. **禁止跳验证** - 每项数据必须验证

---

## 📋 快速参考（生成报告时查看）

### 步骤流程
```
1. 提取数据 → 2. AI分析 → 3. 填充模板 → 4. 生成PDF → 5. 质量验证
```

### AI分析提示词（详见PERSONALIZED_AI_GUIDE.md）

```
【HRV分析】150-200字
结构：数值→历史对比→生理机制→关联分析→建议

【睡眠分析】150-200字  
结构：时长→标准对比→阶段分析→关联分析→建议

【运动分析】150-200字
结构：类型/时长→心率区间→恢复评估→关联分析→建议

【最高优先级】250-300字
结构：问题(80-100字)→行动(100-120字)→效果(70-80字)
```

### 字数验证（必须执行）

```python
def verify_ai_analysis(text: str, min_len: int, max_len: int) -> bool:
    if not (min_len <= len(text) <= max_len):
        raise ValueError(f"字数不符: {len(text)}字")
    
    # 检查模糊词
    forbidden = ['良好', '注意', '适当', '一般']
    for word in forbidden:
        if word in text:
            raise ValueError(f"禁止模糊词: {word}")
    
    return True
```

### 评分计算（固定算法）

```python
# 恢复度：基础70 + HRV>50(+10) + 静息<65(+10) + 睡眠>7h(+10)
# 睡眠：<6h=30, 6-7h=50, 7-8h=70, >8h=80 + 深睡/REM bonus
# 运动：基础50 + 步数bonus + 有运动(+15) + 能量>500(+10)
```

---

## 🔄 自我检查（8项）

生成报告后必须确认：

1. ✅ 在当前对话AI分析？（非脚本模板）
2. ✅ 引用具体数据点？（如"HRV 52.8ms"）
3. ✅ 字数达标？（150-200/250-300字）
4. ✅ 指标间关联？（睡眠↔HRV↔运动）
5. ✅ 建议具体？（如"22:30前入睡"）
6. ✅ HTML格式优化？（彩色标题、表情符号）
7. ✅ 图表显示？（Chart.js正常渲染）
8. ✅ 变量替换完整？（无{{XXX}}残留）

---

**版本**: V5.0-BOOTSTRAP  
**配套文档**: 
- REPORT_STANDARD_V5_REVISED.md（技术流程）
- PERSONALIZED_AI_GUIDE.md（AI分析规范）

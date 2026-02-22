# 标准化流程更新总结（2026-02-22）

## 🎯 目标
解决用户提出的4个关键问题：
1. 确保中文字体不会出错
2. 确保SubAgent使用模板生成，不自编HTML/CSS
3. 确保新Session自动读取QUICK_START.md
4. 精确定义睡眠数据时间窗口（当日20:00至次日12:00）

---

## 📁 修改的文件

### 1. `QUICK_START.md`（全面重写）
**主要更新：**
- ✅ 添加「强制步骤」章节，新Session必须执行初始化流程
- ✅ 添加「中文字体保障方案」章节，3种保障方案（系统字体/wkhtmltopdf/Docker）
- ✅ 明确字体声明：`'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC'`
- ✅ 精确定义睡眠数据时间窗口：当日20:00至次日12:00
- ✅ 添加PDF生成完整代码示例（复制即用）
- ✅ 添加「强制检查清单」生成前验证

**关键约束：**
```python
# 强制验证模板
assert '667eea' in template, "模板错误：必须是紫色V2模板"
assert 'PingFang SC' in template or 'Microsoft YaHei' in template, "模板错误：缺少中文字体"
```

---

### 2. `AGENT_ROLES.md`（健康Agent部分）
**主要更新：**
- ✅ 添加「新Session强制初始化流程」章节
- ✅ 添加中文字体验证函数 `verify_chinese_in_pdf()`
- ✅ 更新模板使用规范，强调必须使用V2模板
- ✅ 添加模板验证函数 `verify_template_v2()`
- ✅ 明确模板文件路径（V2版本）

**强制初始化代码：**
```python
def session_initialization():
    # 1. 读取标准化文档
    docs = [
        '~/.openclaw/workspace-health/docs/REPORT_STANDARD.md',
        '~/.openclaw/workspace-health/AGENT_ROLES.md',
        '~/.openclaw/workspace-health/QUICK_START.md',
    ]
    # 2. 验证模板存在
    # 3. 验证模板关键特征
```

---

### 3. `REPORT_STANDARD.md`（UI模板和睡眠数据部分）
**主要更新：**
- ✅ 版本升级到v3.5
- ✅ 添加「中文字体强制保障」章节
- ✅ 更新为必须使用V2模板（旧模板废弃）
- ✅ **精确定义睡眠数据时间窗口**：当日20:00至次日12:00
- ✅ 添加完整实现代码示例
- ✅ 明确说明需要检查当日文件（午睡）+ 次日文件（夜间睡眠）

**睡眠数据时间窗口精确定义：**
```
时间窗口：YYYY-MM-DD 20:00 至 YYYY-MM-DD+1 12:00 (UTC+8)

示例（2026-02-18）：
- 2月18日 13:00-13:30 午睡 → 归属于2月18日
- 2月18日 23:30入睡 → 2月19日 07:30醒来 → 归属于2月18日
- 2月19日 03:47入睡 → 2月19日 11:26醒来 → 归属于2月18日
- 2月19日 13:00-14:00 午睡 → 归属于2月19日
```

---

### 4. `AGENTS.md`（Channel Agent Bootstrap部分）
**主要更新：**
- ✅ 在必须读取列表中添加 `QUICK_START.md`
- ✅ 添加「Health Agent 特别提醒」章节
- ✅ 明确列出5项必须执行的步骤
- ✅ 列出禁止行为和模板文件路径

**Health Agent 特别提醒：**
1. 读取 `QUICK_START.md`
2. 验证模板存在
3. 使用中文字体
4. 使用模板生成（禁止自编HTML/CSS）
5. 睡眠数据时间窗口

---

## 🔒 强制执行机制

### 对于新Session：
1. **自动读取** `QUICK_START.md`（在AGENTS.md中强制要求）
2. **验证模板** 存在性和正确性
3. **执行检查清单** 生成前验证

### 对于SubAgent：
1. **必须使用V2模板**（在AGENT_ROLES.md中强制要求）
2. **只能替换`{{VARIABLE}}`**，禁止修改CSS
3. **必须验证中文显示**

### 对于睡眠数据：
1. **时间窗口精确定义**：当日20:00至次日12:00
2. **必须检查两个文件**：当日文件（午睡）+ 次日文件（夜间睡眠）
3. **代码实现示例**已提供

---

## ✅ 验证清单

新Session生成报告前必须确认：

- [ ] 已读取 `QUICK_START.md`
- [ ] 已读取 `AGENT_ROLES.md`
- [ ] 已读取 `REPORT_STANDARD.md`
- [ ] V2模板存在且验证通过（紫色主题 `#667eea`）
- [ ] 模板包含中文字体声明（PingFang SC / Microsoft YaHei）
- [ ] 睡眠数据时间窗口正确（当日20:00至次日12:00）
- [ ] 仅替换 `{{VARIABLE}}`，未修改模板结构
- [ ] 生成PDF后验证中文显示正常

---

## 📚 相关文件路径

```
~/.openclaw/workspace-health/
├── QUICK_START.md                    # ← 必须读取
├── AGENT_ROLES.md                    # ← 必须读取
├── docs/REPORT_STANDARD.md           # ← 必须读取
├── AGENTS.md                         # ← Health Agent引导
├── templates/
│   ├── DAILY_TEMPLATE_V2.html       # ← 必须使用
│   ├── WEEKLY_TEMPLATE_V2.html      # ← 必须使用
│   └── MONTHLY_TEMPLATE_V2.html     # ← 必须使用
└── cache/daily/                      # ← 每日缓存
```

---

## 🚀 生效时间

**立即生效** - 所有新Session和SubAgent都必须遵守以上规范。

**版本**: 2026-02-22  
**更新者**: health agent  
**审核状态**: 已实施

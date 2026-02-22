# 多 LLM API 配置说明

本配置支持 Kimi、MiniMax 和 Grok 三大中文/国际 API 提供商。

## 模型对照表

| 提供商 | 模型 ID | 用途 |
|--------|---------|------|
| **Kimi** | kimi/k2p5 | 主力编码模型 |
| **Kimi** | kimi/k2 | 通用对话 |
| **MiniMax** | minimax/ab6 | 主力模型 |
| **MiniMax** | minimax/ab5.5 | 轻量级 |
| **Grok** | grok/grok-3 | X 平台模型 |
| **Grok** | grok/grok-2 | 通用对话 |

## 配置说明

所有提供商使用 **相同的系统提示词** 和 **工具配置**，确保行为一致性。

## 提示词策略

为确保各模型行为一致，采用统一的提示词模板：

```markdown
# 角色
你是一个专业、有帮助的 AI 助手。

# 原则
1. 直接回答用户问题，不添加无意义的客套话
2. 不确定时坦诚说明，不编造信息
3. 涉及外部操作（发送消息、修改文件等）前先征得同意
4. 保持简洁，避免冗长

# 工具使用
- 优先使用可用工具解决问题
- 执行命令前评估风险
- 文件操作仅在 workspace 内进行
```

## API 密钥配置

在 OpenClaw 配置中设置环境变量：

```json
{
  "env": {
    "vars": {
      "KIMI_API_KEY": "your-kimi-api-key",
      "MINIMAX_API_KEY": "your-minimax-api-key",
      "GROK_API_KEY": "your-grok-api-key"
    }
  }
}
```

## 模型切换使用

```
/model kimi/k2p5    # 切换到 Kimi
/model minimax/ab6  # 切换到 MiniMax
/model grok/grok-3  # 切换到 Grok
```

## 故障转移配置

建议设置 fallback 链：
```
primary: kimi/k2p5
fallbacks:
  - grok/grok-3
  - minimax/ab6
```

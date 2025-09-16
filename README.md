# 大模型API压力测试系统

一个专业的大模型API压力测试工具，支持多种API配置、自动化压力测试、实时监控和专业报告生成。

## 🚀 系统特性

### 核心功能
- **多API支持**: 支持 OpenAI、Azure OpenAI、Claude 等主流大模型API
- **灵活配置**: 可配置的API参数、测试强度和报告格式
- **压力测试**: 支持负载测试和压力测试两种模式
- **实时监控**: 网络延时和可用性实时观测
- **专业报告**: HTML、Excel、PDF 多格式专业测试报告
- **数据分析**: 深度性能分析和历史对比

### 技术特点
- **异步架构**: 基于 asyncio 的高性能异步处理
- **智能重试**: 自动重试机制和错误处理
- **数据持久化**: SQLite 数据库存储测试结果
- **可视化**: 丰富的图表和统计分析
- **命令行界面**: 简单易用的CLI工具

## 📦 安装和依赖

### 系统要求
- Python 3.8+
- 网络连接（用于API测试）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 主要依赖
- `aiohttp`: 异步HTTP客户端
- `click`: 命令行界面
- `rich`: 终端美化
- `matplotlib/plotly`: 图表生成
- `pandas`: 数据分析
- `pydantic`: 数据验证

## ⚙️ 配置说明

### API配置 (config/config.yaml)

系统支持多种大模型API，配置示例：

```yaml
api_configs:
  openai:
    name: "OpenAI API"
    base_url: "https://api.openai.com/v1"
    endpoints:
      chat: "/chat/completions"
    headers:
      Authorization: "Bearer {api_key}"
      Content-Type: "application/json"
    request_format:
      model: "gpt-3.5-turbo"
      messages:
        - role: "user"
          content: "{prompt}"
      max_tokens: 1000

  azure_openai:
    name: "Azure OpenAI"
    base_url: "https://{resource_name}.openai.azure.com"
    endpoints:
      chat: "/openai/deployments/{deployment_name}/chat/completions?api-version=2023-12-01-preview"
    headers:
      api-key: "{api_key}"
      Content-Type: "application/json"
```

### 测试配置

```yaml
test_configs:
  default:
    name: "默认压力测试配置"
    concurrent_levels: [1, 5, 10, 20, 50]  # 并发级别
    requests_per_level: 100                # 每级别请求数
    timeout: 30                           # 超时时间
    retry_count: 3                        # 重试次数
    ramp_up_time: 5                       # 预热时间
    cool_down_time: 10                    # 冷却时间
```

### 提示词文件 (data/prompts.jsonl)

每行一个JSON对象，包含 `question` 字段：

```jsonl
{"question": "解释一下深度学习中的反向传播算法原理"}
{"question": "什么是transformer架构，它有哪些优势？"}
{"question": "请介绍一下大语言模型的训练过程"}
```

## 🎯 使用方法

### 1. 基础命令

查看帮助：
```bash
python main.py --help
```

列出可用配置：
```bash
python main.py list-configs
```

### 2. 负载测试

基础负载测试：
```bash
python main.py test \
  --api openai \
  --api-key your_api_key_here \
  --test-config default
```

自定义测试参数：
```bash
python main.py test \
  --api openai \
  --api-key your_api_key_here \
  --concurrent-levels "1,5,10,25,50" \
  --requests-per-level 200 \
  --timeout 60 \
  --report-formats "html,excel,pdf"
```

Azure OpenAI测试：
```bash
python main.py test \
  --api azure_openai \
  --api-key your_api_key \
  --resource-name your_resource \
  --deployment-name your_deployment
```

### 3. 压力测试

运行持续压力测试：
```bash
python main.py stress \
  --api openai \
  --api-key your_api_key \
  --max-concurrent 100 \
  --duration 600
```

### 4. 报告生成

为历史测试生成报告：
```bash
python main.py report test_1703123456_abc12345 --formats html,pdf
```

查看测试历史：
```bash
python main.py history --limit 20
```

### 5. 运行示例

快速体验系统功能：
```bash
python example.py
```

## 📊 测试报告

### HTML报告特性
- **交互式图表**: 基于 Plotly 的动态图表
- **响应式设计**: 支持各种屏幕尺寸
- **专业外观**: 现代化的UI设计
- **详细统计**: 完整的性能指标和分析

### 报告内容
1. **测试概览**: 总体性能指标
2. **响应时间分析**: 平均、P95、P99响应时间
3. **吞吐量分析**: 请求和Token吞吐量
4. **错误率分析**: 错误分布和失败原因
5. **并发性能建议**: 最优并发数配置
6. **网络质量监控**: 延时和可用性统计

### Excel报告
- **多工作表**: 摘要、详细结果、错误分布
- **数据透视**: 便于进一步分析
- **格式化**: 专业的表格样式

## 🔧 高级功能

### 1. 自定义API配置

添加新的API提供商配置到 `config/config.yaml`：

```yaml
api_configs:
  custom_api:
    name: "自定义API"
    base_url: "https://your-api.com"
    endpoints:
      chat: "/v1/chat"
    headers:
      Authorization: "Bearer {api_key}"
    request_format:
      prompt: "{prompt}"
      max_tokens: 1000
```

### 2. 网络监控

系统会自动监控API的网络质量：
- **TCP/HTTP连接测试**
- **延时统计** (平均、最小、最大、抖动)
- **可用性监控** (成功率、丢包率)
- **实时图表** 显示网络状态变化

### 3. 性能分析

#### 并发性能分析
- 自动识别最优并发数
- 性能拐点检测
- 效率评分计算

#### 错误分析
- 错误类型分类统计
- 失败模式识别
- 重试策略优化建议

#### 历史对比
- 多次测试结果对比
- 性能趋势分析
- 基准测试功能

## 🐛 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 验证API密钥
   - 调整超时时间

2. **API限流**
   - 降低并发数
   - 增加预热时间
   - 检查API配额

3. **内存不足**
   - 减少请求总数
   - 降低并发级别
   - 启用结果批量处理

4. **权限错误**
   - 验证API密钥权限
   - 检查资源访问权限
   - 确认模型可用性

### 调试模式

启用详细日志：
```bash
export PYTHONPATH=.
python -m logging.config.dictConfig '{"version": 1, "handlers": {"console": {"class": "logging.StreamHandler", "level": "DEBUG"}}, "root": {"handlers": ["console"], "level": "DEBUG"}}'
python main.py test --api openai --api-key xxx
```

## 📈 性能优化

### 系统调优建议

1. **并发设置**
   - 从低并发开始测试
   - 观察错误率变化
   - 寻找性能拐点

2. **网络优化**
   - 使用就近的API节点
   - 优化网络连接池
   - 启用连接复用

3. **资源管理**
   - 监控系统资源使用
   - 合理设置超时时间
   - 避免内存泄漏

## 🔒 安全注意事项

1. **API密钥管理**
   - 不要在代码中硬编码密钥
   - 使用环境变量存储密钥
   - 定期轮换API密钥

2. **数据隐私**
   - 注意测试数据的隐私性
   - 避免在提示词中包含敏感信息
   - 定期清理测试日志

3. **访问控制**
   - 限制测试系统的访问权限
   - 监控异常的测试活动
   - 实施审计日志

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码更改
4. 创建 Pull Request

## 📝 更新日志

### v1.0.0
- ✨ 初始版本发布
- 🚀 支持多种大模型API
- 📊 专业测试报告生成
- 🌐 网络质量监控
- 📈 性能分析和优化建议

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 📞 支持

如有问题或建议，请提交 Issue 或联系开发团队。

---

**注意**: 本工具仅用于性能测试目的，请遵守相关API的使用条款和限制。
# 快速开始指南

本指南将帮助你快速上手大模型API压力测试系统。

## 🏃‍♂️ 5分钟快速体验

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行示例
```bash
python example.py
```

这将运行一个模拟测试，生成示例报告，帮助你了解系统功能。

## 🔧 第一次真实测试

### 1. 准备API密钥
- OpenAI: https://platform.openai.com/api-keys
- Azure OpenAI: 在Azure门户获取
- Claude: https://console.anthropic.com/

### 2. 测试OpenAI API
```bash
python main.py test \
  --api openai \
  --api-key sk-your-openai-key-here \
  --concurrent-levels "1,5,10" \
  --requests-per-level 20
```

### 3. 查看结果
测试完成后，系统会：
- 显示性能摘要表格
- 自动打开HTML报告
- 保存Excel格式数据

## 🎯 测试不同并发级别

```bash
# 轻量测试
python main.py test --api openai --api-key xxx --concurrent-levels "1,2,5"

# 中等强度测试
python main.py test --api openai --api-key xxx --concurrent-levels "5,10,20,50"

# 高强度测试
python main.py test --api openai --api-key xxx --concurrent-levels "10,25,50,100,200"
```

## 📊 理解测试结果

### 关键指标
- **RPS**: 每秒请求数（越高越好）
- **响应时间**: 平均/P95/P99响应时间（越低越好）
- **成功率**: 请求成功比例（应接近100%）
- **Token/s**: Token吞吐量

### 性能评估
1. **成功率 > 95%**: 系统稳定
2. **P95响应时间 < 5s**: 用户体验良好
3. **RPS持续增长**: 系统有扩展能力
4. **错误率突增点**: 性能瓶颈

## 🚨 常见问题

### Q: 测试时出现大量超时
A: 降低并发数，增加超时时间：
```bash
python main.py test --api openai --api-key xxx --timeout 60 --concurrent-levels "1,5,10"
```

### Q: API返回429错误
A: 触发了限流，降低测试强度：
```bash
python main.py test --api openai --api-key xxx --requests-per-level 10
```

### Q: 想要更详细的错误信息
A: 查看生成的Excel报告中的"错误分布"工作表

## 🎛️ 高级配置

### 自定义测试配置
编辑 `config/config.yaml`，添加新的测试配置：

```yaml
test_configs:
  my_test:
    name: "我的测试配置"
    concurrent_levels: [1, 3, 6, 12, 25]
    requests_per_level: 50
    timeout: 45
```

使用自定义配置：
```bash
python main.py test --api openai --api-key xxx --test-config my_test
```

## 📈 下一步

1. **查看完整文档**: README.md
2. **自定义API配置**: 添加更多API提供商
3. **定期性能测试**: 建立基准线和监控
4. **报告分享**: 导出专业报告给团队

开始你的AI性能测试之旅吧！ 🚀
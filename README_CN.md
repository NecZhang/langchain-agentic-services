# 🚀 企业级智能代理服务 API

专为企业文档处理、分析和知识管理设计的专业中文优先AI助手服务。具备先进的分块策略、多用户会话管理和全面的文件格式支持。

## ✨ 核心特性

- **🌐 中文优先**: 智能语言检测，原生中文支持
- **📄 多格式支持**: PDF、Word、PowerPoint、Excel、JSON、图片OCR
- **🎯 六种AI模式**: 翻译、问答、总结、分析、提取、对比
- **👥 多用户管理**: 会话管理，持久聊天历史
- **🔒 企业级安全**: API密钥认证、CORS、文件大小限制
- **⚡ 高级处理**: 语义分块、流式响应、文档缓存

## 🛠 快速开始

1. **安装依赖**
   ```bash
   uv sync  # 或者 pip install -r requirements.txt
   ```

2. **配置环境**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置你的 vLLM 服务器设置
   ```

3. **启动服务**
   ```bash
   python start_server.py
   ```

4. **测试API**
   ```bash
   curl -X POST http://localhost:9510/chat \
     -F query='你好，测试服务' \
     -F user='测试用户'
   ```

## ⚙️ 环境配置 (.env)

```bash
# vLLM 服务器配置
VLLM_ENDPOINT=http://192.168.6.10:8002
VLLM_MODEL=Qwen/Qwen3-32B-FP8

# API 服务器配置
API_HOST=0.0.0.0
API_PORT=9510

# 语言配置（中文优先）
DEFAULT_LANGUAGE=Chinese
AUTO_DETECT_LANGUAGE=true

# 安全配置（可选）
API_KEY=你的密钥
MAX_FILE_SIZE_MB=50
```

## 📚 API 接口文档

### 基础URL: `http://localhost:9510`

### 🔗 接口端点

#### **健康检查**
```http
GET /health
```

#### **统一聊天API** ⭐ **主要接口**
```http
POST /chat
```

**参数说明:**
- `query` (必需): 你的问题/指令
- `user` (可选): 用户ID，用于会话管理
- `session` (可选): 会话ID，用于对话历史
- `stream` (可选): 启用流式响应 (true/false)
- `files` (可选): 上传文件（单个或多个）
- `api_key` (可选): 认证密钥

#### **配置信息**
```http
GET /config
```

## 🚀 使用示例

### **纯文本聊天**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='什么是人工智能？' \
  -F user='张三'
```

### **文档分析**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='请分析这个财务报告的关键发现' \
  -F user='分析师' \
  -F files=@财务报告.pdf
```

### **多文档对比**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='对比这些方案并突出关键差异' \
  -F user='项目经理' \
  -F files=@方案A.pdf \
  -F files=@方案B.docx
```

### **流式响应**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='详细分析市场趋势' \
  -F stream=true \
  -F files=@市场数据.xlsx
```

## 🎯 AI处理模式

AI会自动从你的查询中检测任务类型：

| 模式 | 触发词 | 示例 |
|------|--------|------|
| **🌐 翻译** | 翻译, translate | `"翻译这个文档为英文"` |
| **💬 问答/RAG** | 什么, 如何, 为什么 | `"这个报告的主要观点是什么？"` |
| **📊 总结** | 总结, 摘要, 概述 | `"总结这个会议纪要"` |
| **🔍 分析** | 分析, 洞察, 趋势 | `"分析销售数据的趋势"` |
| **📋 提取** | 提取, 找出, 列出 | `"提取关键发现和建议"` |
| **⚖️ 对比** | 比较, 对比, 差异 | `"对比这些文档的差异"` |

## 📁 支持的文件格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| **文本** | `.txt`, `.md` | 纯文本、Markdown |
| **PDF** | `.pdf` | 便携式文档格式 |
| **Word** | `.docx` | Microsoft Word（不支持.doc） |
| **PowerPoint** | `.pptx` | Microsoft PowerPoint |
| **JSON** | `.json` | 结构化数据 |
| **图片** | `.jpg`, `.png`, `.bmp` | OCR文字提取 |

## 🌐 语言支持

### **自动检测**
```bash
# 中文查询 → 中文回答
curl -F query='分析这个合同的风险点'

# 英文查询 → 英文回答  
curl -F query='Analyze the contract risks'
```

### **支持的语言**
- **中文**（主要）：完整的原生支持和企业级提示
- **英文**（次要）：完整功能支持

## 👥 多用户功能

### **会话管理**
每个用户/会话组合维护：
- **聊天历史**: 对话上下文
- **文档缓存**: 上传文件记忆
- **RAG索引**: 快速查询处理

### **示例：团队工作流程**
```bash
# 市场团队上传研究报告
curl -X POST http://localhost:9510/chat \
  -F query='上传市场调研报告' \
  -F user='市场部' \
  -F session='Q4规划' \
  -F files=@市场调研.pdf

# 稍后，询问后续问题
curl -X POST http://localhost:9510/chat \
  -F query='基于之前的报告，制定营销策略建议' \
  -F user='市场部' \
  -F session='Q4规划'
```

## 🔒 安全功能

### **API密钥认证**
```bash
# 在 .env 中设置
API_KEY=你的安全密钥

# 在请求中使用
curl -F api_key='你的安全密钥' ...
```

### **文件安全**
- **大小限制**: 可配置的最大文件大小
- **格式验证**: 仅接受支持的格式
- **会话隔离**: 用户数据分离

## 🛡️ 企业级功能

### **可靠性保证**
- **信息来源标注**: 区分文档内容与通用知识
- **不确定性处理**: 对不确定信息明确标注需要确认
- **专业建议**: 对重要决策建议咨询相关专家

### **质量保证**
- **杜绝幻觉**: 仅使用可靠信息来源
- **结构化回答**: 执行摘要格式
- **风险提示**: 突出决策关键因素

## 🐍 Python客户端示例

```python
import requests

def query_agent(query, files=None, user="默认用户", session="默认会话"):
    url = "http://localhost:9510/chat"
    data = {"query": query, "user": user, "session": session}
    
    files_data = []
    if files:
        for file_path in files:
            files_data.append(('files', open(file_path, 'rb')))
    
    response = requests.post(url, data=data, files=files_data)
    return response.json()

# 使用示例
result = query_agent(
    query="分析这个财务报告",
    files=["财务报告.pdf"],
    user="财务团队",
    session="Q3审查"
)
print(result["answer"])
```

## 🚨 错误处理

### **常见错误**
- **413**: 文件过大
- **401**: API密钥无效
- **415**: 不支持的文件格式
- **500**: 处理错误

### **错误响应格式**
```json
{
  "detail": "❌ 文件过大，超过最大限制 50MB"
}
```

## 📊 性能优化

### **优化功能**
- **智能缓存**: 文档分块和RAG索引
- **流式传输**: 实时响应交付
- **批处理**: 多文档处理
- **高级分块**: 任务优化的文本分段

### **扩展考虑**
- **并发用户**: 设计支持多用户访问
- **内存管理**: 高效的缓存策略
- **负载均衡**: 可运行多个实例

## 🔧 高级配置

### **自定义模型设置**
```bash
# 针对不同需求的不同模型
VLLM_MODEL=Qwen/Qwen3-32B-FP8      # 中文优化
# VLLM_MODEL=meta-llama/Llama-2-70b  # 替代方案
```

### **分块策略**
服务会根据以下因素自动优化分块：
- **文件类型**: PDF页面、PowerPoint幻灯片等
- **任务类型**: 翻译（大块）、RAG（小块）、分析（中块）
- **内容结构**: 尊重段落和句子边界

## 📈 监控

### **健康检查**
```bash
# 服务状态
curl http://localhost:9510/health

# 配置信息
curl http://localhost:9510/config
```

### **日志记录**
- **启动**: 服务配置和模型加载
- **处理**: 文件解析和分块进度
- **错误**: 详细的错误信息用于调试

## ❓ 故障排除

### **服务无法启动**
1. 检查vLLM服务器连接: `curl http://your-vllm:8002/v1/models`
2. 验证环境变量: `cat .env`
3. 检查依赖: `uv sync` 或 `pip install -r requirements.txt`

### **文件处理问题**
1. 验证Tesseract: `tesseract --version`
2. 检查文件权限和格式
3. 确保文件大小在限制范围内

### **内存问题**
1. 监控使用情况: `htop`
2. 减少 `MAX_FILE_SIZE_MB`
3. 调整分块参数

## 🎯 最佳实践

### **企业使用**
1. **使用API密钥**: 生产环境启用认证
2. **设置CORS**: 配置允许的来源
3. **监控使用**: 跟踪API调用和性能
4. **会话管理**: 使用有意义的用户/会话ID

### **开发者指南**
1. **错误处理**: 始终检查响应状态
2. **文件验证**: 上传前验证格式
3. **流式传输**: 对长响应使用流式传输
4. **缓存利用**: 利用会话持久性

## 🤝 集成示例

### **Web应用程序**
```javascript
// 前端集成
const formData = new FormData();
formData.append('query', '分析这个文档');
formData.append('files', fileInput.files[0]);
formData.append('user', currentUser.id);

fetch('http://localhost:9510/chat', {
    method: 'POST',
    body: formData
}).then(response => response.json());
```

### **工作流自动化**
```python
# 自动化文档处理流水线
import os
from pathlib import Path

def process_documents_batch(folder_path, query_template):
    results = []
    for file_path in Path(folder_path).glob('*.pdf'):
        query = query_template.format(filename=file_path.name)
        result = query_agent(query, [str(file_path)])
        results.append({
            'file': file_path.name,
            'analysis': result['answer']
        })
    return results

# 使用示例
results = process_documents_batch(
    '/path/to/contracts', 
    '分析合同 {filename} 的关键条款和风险点'
)
```

## 🏢 企业应用场景

### **财务分析**
```bash
# 财务报告分析
curl -X POST http://localhost:9510/chat \
  -F query='分析Q3财务报告，重点关注收入增长和成本控制' \
  -F user='财务总监' \
  -F session='Q3财务审查' \
  -F files=@Q3财务报告.pdf
```

### **合同审查**
```bash
# 合同风险评估
curl -X POST http://localhost:9510/chat \
  -F query='审查这个供应商合同，识别潜在风险和不利条款' \
  -F user='法务部' \
  -F session='供应商合同审查' \
  -F files=@供应商合同.docx
```

### **市场研究**
```bash
# 竞争对手分析
curl -X POST http://localhost:9510/chat \
  -F query='对比分析这三个竞争对手的产品策略' \
  -F user='产品经理' \
  -F session='竞品分析' \
  -F files=@竞争对手A.pdf \
  -F files=@竞争对手B.pdf \
  -F files=@竞争对手C.pdf
```

### **政策解读**
```bash
# 政策影响分析
curl -X POST http://localhost:9510/chat \
  -F query='解读新政策对我们业务的潜在影响和应对策略' \
  -F user='战略规划部' \
  -F session='政策分析' \
  -F files=@新政策文件.pdf
```

## 🔍 高级查询示例

### **结构化分析**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='请按照以下结构分析这个商业计划书：
1. 市场机会评估
2. 竞争优势分析  
3. 财务预测合理性
4. 风险因素识别
5. 投资建议' \
  -F files=@商业计划书.pptx
```

### **多维度对比**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='从技术可行性、成本效益、实施难度、风险程度四个维度对比这些技术方案' \
  -F files=@方案1.docx \
  -F files=@方案2.docx \
  -F files=@方案3.docx
```

### **趋势预测**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='基于历史数据分析销售趋势，并预测未来6个月的发展方向' \
  -F files=@销售数据.xlsx
```

## 📞 技术支持

### **文档资源**
- 上述API端点和参数说明
- `.env.example`中的配置选项
- 错误代码和故障排除指南

### **企业级支持**
生产环境部署考虑：
- 负载均衡设置
- 数据库持久化
- 高级安全配置
- 自定义模型集成

### **社区支持**
- GitHub Issues: 报告问题和功能请求
- 技术文档: 详细的API参考和最佳实践
- 示例代码: 各种语言的集成示例

---

## 🎉 开始使用

1. **按照快速开始指南**进行安装配置
2. **使用`.env`配置你的环境**
3. **用curl或Python测试示例查询**
4. **集成到你的应用程序中**

你的企业AI助手已准备好处理中英文文档并回答问题！🚀

**需要帮助？** 查看故障排除部分或参考上述配置指南。

## 📋 常见问题 (FAQ)

### **Q: 支持哪些中文方言？**
A: 目前主要支持简体中文，对繁体中文也有良好的理解能力。

### **Q: 可以处理扫描版PDF吗？**
A: 是的，通过OCR技术可以提取扫描版PDF中的文字内容。

### **Q: 如何确保数据安全？**
A: 服务提供会话隔离、API密钥认证、文件大小限制等多重安全保障。

### **Q: 支持批量处理吗？**
A: 支持，可以一次上传多个文件进行对比分析，也可以通过API进行批量自动化处理。

### **Q: 响应速度如何？**
A: 通过智能缓存、流式响应和高级分块策略，确保快速响应。首次处理会建立缓存，后续查询会更快。

---

**企业级智能文档处理，从这里开始！** 🌟

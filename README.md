# 🚀 Enterprise Agentic Service API

A professional, Chinese-first AI assistant service designed for enterprise document processing, analysis, and knowledge management.

## ✨ Key Features

- **🌐 Chinese-First**: Intelligent language detection with native Chinese support
- **📄 Multi-Format**: PDF, Word, PowerPoint, Excel, JSON, images with OCR
- **🎯 Six AI Modes**: Translation, Q&A, Summarization, Analysis, Extraction, Comparison
- **👥 Multi-User**: Session management with persistent chat history
- **🔒 Enterprise Security**: API key authentication, CORS, file size limits
- **⚡ Advanced Processing**: Semantic chunking, streaming responses, document caching

## 🛠 Quick Start

1. **Install dependencies**
   ```bash
   uv sync  # Install all dependencies from pyproject.toml
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your vLLM server settings
   ```

3. **Start the service**
   ```bash
   python start_server.py
   ```

4. **Test the API**
   ```bash
   curl -X POST http://localhost:9510/chat \
     -F query='Hello, test the service' \
     -F user='test_user'
   ```

## ⚙️ Configuration (.env)

```bash
# vLLM Server
VLLM_ENDPOINT=http://192.168.6.10:8002
VLLM_MODEL=Qwen/Qwen3-32B-FP8

# API Server
API_HOST=0.0.0.0
API_PORT=9510

# Language (Chinese-first)
DEFAULT_LANGUAGE=Chinese
AUTO_DETECT_LANGUAGE=true

# Security (Optional)
API_KEY=your_secret_key
MAX_FILE_SIZE_MB=50
```

## 📚 API Reference

### Base URL: `http://localhost:9510`

### 🔗 Endpoints

#### **Health Check**
```http
GET /health
```

#### **Unified Chat API** ⭐ **Main Endpoint**
```http
POST /chat
```

**Parameters:**
- `query` (required): Your question/instruction
- `user` (optional): User ID for session management
- `session` (optional): Session ID for conversation history
- `stream` (optional): Enable streaming (true/false)
- `files` (optional): Upload files (single or multiple)
- `api_key` (optional): Authentication key

#### **Configuration Info**
```http
GET /config
```

## 🚀 Usage Examples

### **Text-Only Chat**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='什么是人工智能?' \
  -F user='john_doe'
```

### **Document Analysis**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='请分析这个报告的关键发现' \
  -F user='analyst' \
  -F files=@report.pdf
```

### **Multiple Document Comparison**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='Compare these proposals' \
  -F user='manager' \
  -F files=@proposal1.pdf \
  -F files=@proposal2.docx
```

### **Streaming Response**
```bash
curl -X POST http://localhost:9510/chat \
  -F query='详细分析市场趋势' \
  -F stream=true \
  -F files=@market_data.xlsx
```

## 🎯 AI Processing Modes

The AI automatically detects task type from your query:

| Mode | Trigger Words | Example |
|------|---------------|---------|
| **🌐 Translation** | 翻译, translate | `"Translate this to English"` |
| **💬 Q&A/RAG** | 什么, what, how | `"What are the main points?"` |
| **📊 Summarization** | 总结, summarize | `"Summarize this report"` |
| **🔍 Analysis** | 分析, analyze | `"Analyze the trends"` |
| **📋 Extraction** | 提取, extract | `"Extract key findings"` |
| **⚖️ Comparison** | 比较, compare | `"Compare these documents"` |

## 📁 Supported Formats

| Format | Extensions | Description |
|--------|------------|-------------|
| **Text** | `.txt`, `.md` | Plain text, Markdown |
| **PDF** | `.pdf` | Portable Document Format |
| **Word** | `.docx` | Microsoft Word (not .doc) |
| **PowerPoint** | `.pptx` | Microsoft PowerPoint |
| **JSON** | `.json` | Structured data |
| **Images** | `.jpg`, `.png`, `.bmp` | OCR text extraction |

## 🌐 Language Support

### **Automatic Detection**
```bash
# Chinese query → Chinese response
curl -F query='分析这个合同的风险点'

# English query → English response  
curl -F query='Analyze the contract risks'
```

### **Supported Languages**
- **Chinese** (Primary): Full native support with enterprise prompts
- **English** (Secondary): Complete functionality

## 👥 Multi-User Features

### **Session Management**
Each user/session combination maintains:
- **Chat History**: Conversation context
- **Document Cache**: Uploaded file memory
- **RAG Indexes**: Fast query processing

### **Example: Team Workflow**
```bash
# Marketing team uploads research
curl -X POST http://localhost:9510/chat \
  -F query='上传市场调研报告' \
  -F user='marketing' \
  -F session='q4_planning' \
  -F files=@research.pdf

# Later, ask follow-up questions
curl -X POST http://localhost:9510/chat \
  -F query='基于之前的报告，制定营销策略' \
  -F user='marketing' \
  -F session='q4_planning'
```

## 🔒 Security Features

### **API Key Authentication**
```bash
# Set in .env
API_KEY=your_secure_key

# Use in requests
curl -F api_key='your_secure_key' ...
```

### **File Security**
- **Size Limits**: Configurable max file size
- **Format Validation**: Only supported formats accepted
- **Session Isolation**: User data separation

## 🛡️ Enterprise Features

### **Reliability**
- **Source Attribution**: Distinguishes document vs. general knowledge
- **Uncertainty Handling**: States when information needs confirmation
- **Professional Advice**: Recommends expert consultation for critical decisions

### **Quality Assurance**
- **No Hallucination**: Only reliable information sources
- **Structured Responses**: Executive summary format
- **Risk Alerts**: Highlights decision-critical factors

## 🐍 Python Client Example

```python
import requests

def query_agent(query, files=None, user="default", session="default"):
    url = "http://localhost:9510/chat"
    data = {"query": query, "user": user, "session": session}
    
    files_data = []
    if files:
        for file_path in files:
            files_data.append(('files', open(file_path, 'rb')))
    
    response = requests.post(url, data=data, files=files_data)
    return response.json()

# Example usage
result = query_agent(
    query="分析这个财务报告",
    files=["report.pdf"],
    user="finance_team",
    session="q3_review"
)
print(result["answer"])
```

## 🚨 Error Handling

### **Common Errors**
- **413**: File too large
- **401**: Invalid API key
- **415**: Unsupported file format
- **500**: Processing error

### **Error Response Format**
```json
{
  "detail": "❌ 文件过大，超过最大限制 50MB"
}
```

## 📊 Performance

### **Optimization Features**
- **Smart Caching**: Document chunks and RAG indexes
- **Streaming**: Real-time response delivery
- **Batch Processing**: Multiple document handling
- **Advanced Chunking**: Task-optimized text segmentation

### **Scaling Considerations**
- **Concurrent Users**: Designed for multi-user access
- **Memory Management**: Efficient caching strategies
- **Load Balancing**: Can run multiple instances

## 🔧 Advanced Configuration

### **Custom Model Settings**
```bash
# Different models for different needs
VLLM_MODEL=Qwen/Qwen3-32B-FP8      # Chinese-optimized
# VLLM_MODEL=meta-llama/Llama-2-70b  # Alternative
```

### **Chunking Strategy**
The service automatically optimizes chunking based on:
- **File Type**: PDF pages, PowerPoint slides, etc.
- **Task Type**: Translation (large), RAG (small), Analysis (medium)
- **Content Structure**: Respects paragraphs and sentences

## 📈 Monitoring

### **Health Checks**
```bash
# Service status
curl http://localhost:9510/health

# Configuration info
curl http://localhost:9510/config
```

### **Logging**
- **Startup**: Service configuration and model loading
- **Processing**: File parsing and chunking progress
- **Errors**: Detailed error information for debugging

## ❓ Troubleshooting

### **Service Won't Start**
1. Check vLLM server connectivity: `curl http://your-vllm:8002/v1/models`
2. Verify environment variables: `cat .env`
3. Check dependencies: `uv sync` or `uv sync --extra dev` for development

### **File Processing Issues**
1. Verify Tesseract: `tesseract --version`
2. Check file permissions and formats
3. Ensure file size within limits

### **Memory Problems**
1. Monitor usage: `htop`
2. Reduce `MAX_FILE_SIZE_MB`
3. Adjust chunking parameters

## 🎯 Best Practices

### **For Enterprises**
1. **Use API Keys**: Enable authentication for production
2. **Set CORS**: Configure allowed origins
3. **Monitor Usage**: Track API calls and performance
4. **Session Management**: Use meaningful user/session IDs

### **For Developers**
1. **Error Handling**: Always check response status
2. **File Validation**: Verify formats before upload
3. **Streaming**: Use streaming for long responses
4. **Caching**: Leverage session persistence

## 🤝 Integration Examples

### **Web Application**
```javascript
// Frontend integration
const formData = new FormData();
formData.append('query', '分析这个文档');
formData.append('files', fileInput.files[0]);
formData.append('user', currentUser.id);

fetch('http://localhost:9510/chat', {
    method: 'POST',
    body: formData
}).then(response => response.json());
```

### **Workflow Automation**
```python
# Automated document processing pipeline
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
```

## 📞 Support

### **Documentation**
- API endpoints and parameters above
- Configuration options in `.env.example`
- Error codes and troubleshooting guide

### **Enterprise Support**
For production deployments:
- Load balancing setup
- Database persistence
- Advanced security configurations
- Custom model integration

---

## 🎉 Ready to Start?

1. **Follow the Quick Start** guide above
2. **Configure your environment** with `.env`
3. **Test with sample queries** using curl or Python
4. **Integrate with your applications** using the API

Your enterprise AI assistant is ready to process documents and answer questions in both Chinese and English! 🚀

**Need help?** Check the troubleshooting section or review the configuration guide above.

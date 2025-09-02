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
   curl -X POST http://localhost:9211/chat \
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
API_PORT=9211

# Language (Chinese-first)
DEFAULT_LANGUAGE=Chinese
AUTO_DETECT_LANGUAGE=true

# Security (Optional)
API_KEY=your_secret_key
MAX_FILE_SIZE_MB=50
```

## 📚 API Reference

### Base URL: `http://localhost:9211`

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

## 🔧 Complete API Parameters Reference

### **📝 Main Chat Endpoint: `/chat`**

#### **Required Parameters:**
- **`query`** (string, required)
  - **Description**: The user's input message or request
  - **Examples**: 
    - `"translate this document to English"`
    - `"What is artificial intelligence?"`
    - `"Please analyze this document"`
    - `"Summarize the key points"`

#### **Optional Parameters:**

##### **File Upload:**
- **`files`** (file, optional)
  - **Description**: Document file to be processed (PDF, Word, PowerPoint, images, text)
  - **Supported Formats**: 
    - **Documents**: `.pdf`, `.docx`, `.doc`, `.pptx`, `.ppt`
    - **Images**: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff` (with OCR)
    - **Text**: `.txt`, `.md`
    - **Spreadsheets**: `.xlsx`, `.xls`
  - **Max Size**: Configurable (default: 50MB)
  - **Usage**: `-F files=@document.pdf`

##### **User & Session Management:**
- **`user`** (string, optional)
  - **Description**: Unique identifier for the user
  - **Purpose**: Enables per-user storage, chat history, and document caching
  - **Examples**: `"john_doe"`, `"translator"`, `"analyst_001"`
  - **Default**: Anonymous user (no persistent storage)

- **`session`** (string, optional)
  - **Description**: Chat session identifier
  - **Purpose**: Groups conversations and maintains context across multiple requests
  - **Examples**: `"meeting_2024"`, `"project_alpha"`, `"daily_chat"`
  - **Default**: Single session per user

##### **Translation Control:**
- **`target_language`** (string, optional)
  - **Description**: Target language for translation tasks
  - **Supported Languages**: 
    - **English**: `"english"`, `"en"`, `"英文"`
    - **Chinese**: `"chinese"`, `"zh"`, `"中文"`
    - **Japanese**: `"japanese"`, `"ja"`, `"日语"`
    - **Korean**: `"korean"`, `"ko"`, `"韩语"`
    - **French**: `"french"`, `"fr"`
    - **German**: `"german"`, `"de"`
    - **Spanish**: `"spanish"`, `"es"`
    - **Russian**: `"russian"`, `"ru"`
  - **Default**: `"English"`
  - **Auto-Detection**: System automatically detects source language and determines translation direction

##### **Streaming Control:**
- **`stream`** (boolean, optional)
  - **Description**: Enable real-time streaming response
  - **Values**: `true` or `false`
  - **Default**: `false`
  - **Benefits**: 
    - Character-by-character output
    - Real-time response
    - Better user experience
  - **Network Optimization**: Includes special headers for smooth streaming over networks

### **⚙️ Configuration Endpoint: `/config`**

#### **Response Parameters:**
- **`server_info`**
  - **`host`**: Server host address
  - **`port`**: Server port number
  - **`version`**: API version

- **`vllm_config`**
  - **`endpoint`**: vLLM server URL
  - **`model`**: Active LLM model name
  - **`status`**: Connection status

- **`streaming`**
  - **`enabled`**: Whether streaming is available
  - **`char_by_char`**: Character-level streaming mode
  - **`small_chunks`**: Force small chunk processing
  - **`network_optimized`**: Network streaming optimization
  - **`debug_logging`**: Debug information control

- **`storage`**
  - **`data_directory`**: Main data storage location
  - **`temp_directory`**: Temporary upload location
  - **`user_isolation`**: User data separation status

### **🔧 Environment Configuration Parameters**

#### **Server Configuration:**
```bash
# Server settings
HOST=0.0.0.0                    # Server host (default: 0.0.0.0)
PORT=9211                        # Server port (default: 9211)

# vLLM connection
VLLM_ENDPOINT=http://192.168.6.10:8002  # vLLM server URL
VLLM_MODEL=Qwen/Qwen3-32B-FP8   # LLM model name
AGENTIC_REQUEST_TIMEOUT=30       # Request timeout in seconds
```

#### **Streaming Configuration:**
```bash
# Streaming behavior
STREAM_CHAR_BY_CHAR=true         # Enable character-by-character streaming
FORCE_SMALL_CHUNKS=true          # Force small chunk processing
NETWORK_STREAMING_OPTIMIZED=true # Optimize for network streaming
DEBUG_STREAMING=false            # Control debug logging
```

#### **Storage Configuration:**
```bash
# Data storage paths
AGENTIC_DATA_DIR=.data           # Main data directory (development)
AGENTIC_TEMP_DIR=.tmp_uploads    # Temporary upload directory
```

### **📊 API Response Parameters**

#### **Success Response:**
- **`status`**: `"success"`
- **`data`**: Response content (varies by task type)
- **`metadata`**: Task information and processing details

#### **Streaming Response:**
- **Content-Type**: `text/plain; charset=utf-8`
- **Headers**: 
  - `Cache-Control: no-cache, no-store, must-revalidate`
  - `X-Accel-Buffering: no` (disables nginx buffering)
  - `Transfer-Encoding: chunked`

#### **Error Response:**
- **`status`**: `"error"`
- **`error`**: Error message
- **`details`**: Additional error information

### **🎯 Task-Specific Parameters**

#### **Translation Tasks:**
- **Intent Detection**: Automatically detected from query
- **Language Detection**: Automatic source language detection
- **Direction Logic**: Intelligent translation direction determination
- **Format Preservation**: Maintains original document structure

#### **Q&A Tasks:**
- **Context Retrieval**: Uses RAG (Retrieval-Augmented Generation)
- **Document Chunking**: Intelligent text segmentation
- **Source Attribution**: References source documents
- **History Context**: Includes chat history when available

#### **Analysis Tasks:**
- **Document Processing**: Supports multiple file formats
- **Chunking Strategy**: Task-optimized text segmentation
- **Caching**: Intelligent result caching for performance

### ** Advanced Usage Examples**

#### **Network Streaming (Remote Client):**
```bash
# For smooth streaming over network, use --no-buffer
curl -X POST http://192.168.6.19:9211/chat \
  -F query='translate this document to English' \
  -F user='translator' \
  -F files=@document.pdf \
  -F stream=true \
  --no-buffer
```

#### **Multi-Language Translation:**
```bash
# Chinese to English
curl -X POST http://localhost:9211/chat \
  -F query='translate to English' \
  -F user='translator' \
  -F files=@chinese_doc.pdf

# English to Chinese
curl -X POST http://localhost:9211/chat \
  -F query='translate to Chinese' \
  -F user='translator' \
  -F files=@english_doc.pdf
```

#### **Session-Based Workflow:**
```bash
# Step 1: Upload document
curl -X POST http://localhost:9211/chat \
  -F query='Upload this research paper' \
  -F user='researcher' \
  -F session='paper_analysis' \
  -F files=@research.pdf

# Step 2: Ask questions about the document
curl -X POST http://localhost:9211/chat \
  -F query='What are the main findings?' \
  -F user='researcher' \
  -F session='paper_analysis'

# Step 3: Translate the conversation
curl -X POST http://localhost:9211/chat \
  -F query='translate our conversation to Chinese' \
  -F user='researcher' \
  -F session='paper_analysis'
```

## 🚀 Usage Examples

### **Text-Only Chat**
```bash
curl -X POST http://localhost:9211/chat \
  -F query='什么是人工智能?' \
  -F user='john_doe'
```

### **Document Analysis**
```bash
curl -X POST http://localhost:9211/chat \
  -F query='请分析这个报告的关键发现' \
  -F user='analyst' \
  -F files=@report.pdf
```

### **Text Translation (Multiple Ways)**
```bash
# Method 1: Direct text in query
curl -X POST http://localhost:9211/chat \
  -F query='translate: Hello, how are you today?' \
  -F user='translator'

# Method 2: Text in quotes
curl -X POST http://localhost:9211/chat \
  -F query='translate "What is artificial intelligence?" to Chinese' \
  -F user='translator'

# Method 3: With chat history (translate conversation)
curl -X POST http://localhost:9211/chat \
  -F query='translate our conversation to English' \
  -F user='user123' \
  -F session='conversation_001'

# Method 4: Document translation
curl -X POST http://localhost:9211/chat \
  -F query='translate this document to English' \
  -F user='translator' \
  -F files=@document.pdf
```

### **Multiple Document Comparison**
```bash
curl -X POST http://localhost:9211/chat \
  -F query='Compare these proposals' \
  -F user='manager' \
  -F files=@proposal1.pdf \
  -F files=@proposal2.docx
```

### **Streaming Response**
```bash
curl -X POST http://localhost:9211/chat \
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
curl -X POST http://localhost:9211/chat \
  -F query='上传市场调研报告' \
  -F user='marketing' \
  -F session='q4_planning' \
  -F files=@research.pdf

# Later, ask follow-up questions
curl -X POST http://localhost:9211/chat \
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
    url = "http://localhost:9211/chat"
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
curl http://localhost:9211/health

# Configuration info
curl http://localhost:9211/config
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

fetch('http://localhost:9211/chat', {
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

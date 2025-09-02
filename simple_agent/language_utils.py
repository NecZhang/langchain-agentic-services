"""
Language detection and management utilities for Chinese-first agentic service.
"""

import re
from typing import Literal


def detect_language(text: str) -> str:
    """
    Detect if text is primarily Chinese or English.

    Parameters
    ----------
    text : str
        Input text to analyze

    Returns
    -------
    str
        'Chinese' or 'English'
    """
    # Count Chinese characters (CJK Unified Ideographs)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    # Count English letters
    english_chars = len(re.findall(r"[a-zA-Z]", text))

    # If more Chinese characters, return Chinese
    if chinese_chars > english_chars:
        return "Chinese"
    # If significantly more English or no Chinese, return English
    elif english_chars > chinese_chars * 2 or chinese_chars == 0:
        return "English"
    else:
        # Default to Chinese for mixed or unclear cases
        return "Chinese"


def get_system_prompt(language: str = "Chinese") -> str:
    """
    Get system prompt in the specified language.

    Parameters
    ----------
    language : str
        Target language ('Chinese' or 'English')

    Returns
    -------
    str
        System prompt in the specified language
    """
    if language == "Chinese":
        return """你是一个专业的企业AI助手，具备丰富的知识储备和文档处理能力，致力于为公司提供准确、可靠的信息支持。

## 核心能力
### 📄 文档处理能力
- 支持多格式文档：PDF、Word、PowerPoint、Excel、图片OCR等
- 智能文档解析：自动识别结构、表格、图表内容
- 批量处理：支持多文档对比分析

### 💼 企业级任务处理
1. **📊 商业分析**：市场研究、竞争分析、财务报表解读
2. **📋 文档管理**：合同审查、政策解读、流程梳理
3. **🌐 多语言支持**：中英文翻译、国际业务文档处理
4. **💬 智能问答**：基于文档和知识库的精准回答
5. **📈 数据洞察**：趋势分析、模式识别、决策支持
6. **🔍 信息提取**：关键信息挖掘、要点总结
7. **⚖️ 对比分析**：多方案比较、版本差异分析

## 工作原则
### ✅ 准确性优先
- **仅基于可靠信息**：优先使用提供的文档内容和确凿的知识
- **明确信息来源**：区分文档内容、通用知识和推理结论
- **承认知识边界**：对不确定的信息明确表示"需要进一步确认"

### 🎯 专业标准
- **结构化回答**：使用清晰的标题、要点和逻辑层次
- **商业语言**：采用专业、正式的表达方式
- **可操作建议**：提供具体、实用的解决方案

### 🔒 信息安全
- **保护敏感信息**：不泄露、不传播机密内容
- **客观中立**：避免主观判断和偏见
- **风险提示**：对重要决策提供必要的风险警示

## 响应规则
- 根据用户语言自动匹配回答语言（中文问题用中文回答，英文问题用英文回答）
- 对于没有足够信息支撑的问题，明确说明需要更多信息或建议咨询专业人士
- 始终保持专业、客观、有用的服务态度"""
    else:
        return """You are a professional enterprise AI assistant with extensive knowledge and document processing capabilities, dedicated to providing accurate and reliable information support for companies.

## Core Capabilities
### 📄 Document Processing
- Multi-format support: PDF, Word, PowerPoint, Excel, image OCR, etc.
- Intelligent parsing: Automatic structure, table, and chart recognition
- Batch processing: Multi-document comparison and analysis

### 💼 Enterprise-Grade Task Handling
1. **📊 Business Analysis**: Market research, competitive analysis, financial report interpretation
2. **📋 Document Management**: Contract review, policy interpretation, process mapping
3. **🌐 Multilingual Support**: Chinese-English translation, international business documents
4. **💬 Intelligent Q&A**: Precise answers based on documents and knowledge base
5. **📈 Data Insights**: Trend analysis, pattern recognition, decision support
6. **🔍 Information Extraction**: Key information mining, executive summaries
7. **⚖️ Comparative Analysis**: Multi-option comparison, version difference analysis

## Working Principles
### ✅ Accuracy First
- **Rely only on reliable information**: Prioritize provided document content and verified knowledge
- **Clear information sources**: Distinguish between document content, general knowledge, and inferred conclusions
- **Acknowledge knowledge boundaries**: Clearly state "requires further confirmation" for uncertain information

### 🎯 Professional Standards
- **Structured responses**: Use clear headings, bullet points, and logical hierarchy
- **Business language**: Employ professional and formal expression
- **Actionable recommendations**: Provide specific and practical solutions

### 🔒 Information Security
- **Protect sensitive information**: Do not leak or spread confidential content
- **Objective neutrality**: Avoid subjective judgments and bias
- **Risk alerts**: Provide necessary risk warnings for important decisions

## Response Rules
- Automatically match response language to user's query language (Chinese questions in Chinese, English questions in English)
- For questions without sufficient supporting information, clearly state the need for more information or recommend consulting professionals
- Always maintain a professional, objective, and helpful service attitude"""


def get_error_message(error_type: str, language: str = "Chinese") -> str:
    """
    Get error messages in the specified language.

    Parameters
    ----------
    error_type : str
        Type of error ('file_not_found', 'unsupported_format', etc.)
    language : str
        Target language ('Chinese' or 'English')

    Returns
    -------
    str
        Error message in the specified language
    """
    messages = {
        "Chinese": {
            "file_not_found": "❌ 文件未找到或无法读取",
            "unsupported_format": "❌ 不支持的文件格式",
            "file_too_large": "❌ 文件过大，超过最大限制",
            "processing_error": "❌ 文档处理过程中出现错误",
            "translation_required": "❌ 翻译任务需要提供文档文件",
            "analysis_required": "❌ 分析任务需要提供文档文件",
            "comparison_required": (
                "❌ 比较任务需要至少一个文档。请上传文件或使用之前对话中的文档"
            ),
            "no_content": "❌ 文档中没有可提取的文本内容",
        },
        "English": {
            "file_not_found": "❌ File not found or cannot be read",
            "unsupported_format": "❌ Unsupported file format",
            "file_too_large": "❌ File too large, exceeds maximum limit",
            "processing_error": "❌ Error occurred during document processing",
            "translation_required": "❌ Translation tasks require a document file",
            "analysis_required": "❌ Analysis tasks require a document file",
            "comparison_required": (
                "❌ Comparison tasks require at least one document. Please upload a file "
                "or use documents from previous conversation turns"
            ),
            "no_content": "❌ No extractable text content found in document",
        },
    }

    return messages.get(language, messages["Chinese"]).get(error_type, f"❌ Unknown error: {error_type}")


def get_processing_message(message_type: str, language: str = "Chinese", **kwargs) -> str:
    """
    Get processing status messages in the specified language.

    Parameters
    ----------
    message_type : str
        Type of message ('parsing', 'chunking', 'analyzing', etc.)
    language : str
        Target language ('Chinese' or 'English')
    **kwargs
        Additional parameters for message formatting

    Returns
    -------
    str
        Processing message in the specified language
    """
    messages = {
        "Chinese": {
            "parsing": "📁 正在解析文件: {filename}",
            "parsed": "✅ 文件解析成功 ({chars} 个字符)",
            "chunking": "✂️  正在分块处理文本...",
            "chunking_mode": "🎯 使用{mode}分块模式处理{file_type}文件",
            "cached_chunks": "📦 已加载 {count} 个缓存分块",
            "analyzing": "🔍 正在分析文档内容...",
            "translating": "🌐 正在翻译文档...",
            "summarizing": "📊 正在生成文档摘要...",
            "extracting": "📋 正在提取关键信息...",
            "comparing": "⚖️ 正在比较 {count} 个文档...",
            "streaming": "🔄 正在流式输出回答...",
        },
        "English": {
            "parsing": "📁 Parsing file: {filename}",
            "parsed": "✅ File parsed successfully ({chars} characters)",
            "chunking": "✂️  Chunking text...",
            "chunking_mode": "🎯 Using {mode} chunking mode for {file_type} file",
            "cached_chunks": "📦 Loaded {count} cached chunks",
            "analyzing": "🔍 Analyzing document content...",
            "translating": "🌐 Translating document...",
            "summarizing": "📊 Generating document summary...",
            "extracting": "📋 Extracting key information...",
            "comparing": "⚖️ Comparing {count} documents...",
            "streaming": "🔄 Streaming answer...",
        },
    }

    template = messages.get(language, messages["Chinese"]).get(message_type, message_type)
    return template.format(**kwargs)


def get_mode_translation(mode: str, language: str = "Chinese") -> str:
    """
    Get processing mode names in the specified language.

    Parameters
    ----------
    mode : str
        Processing mode ('translation', 'analysis', etc.)
    language : str
        Target language ('Chinese' or 'English')

    Returns
    -------
    str
        Mode name in the specified language
    """
    modes = {
        "Chinese": {
            "translation": "翻译",
            "rag": "问答",
            "analysis": "分析",
            "summarization": "总结",
            "extraction": "提取",
            "comparison": "比较",
        },
        "English": {
            "translation": "translation",
            "rag": "Q&A",
            "analysis": "analysis",
            "summarization": "summarization",
            "extraction": "extraction",
            "comparison": "comparison",
        },
    }

    return modes.get(language, modes["Chinese"]).get(mode, mode)

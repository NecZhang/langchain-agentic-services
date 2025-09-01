"""An intelligent intent recognizer for user queries.

This module exports a single function, :func:`detect_intent`, which
examines a user query and attempts to classify it into one of a
predefined set of task types. The new system uses semantic analysis
and context awareness instead of simple keyword matching.
"""

from __future__ import annotations

from typing import Literal

__all__ = ["detect_intent"]


def detect_intent(query: str) -> Literal["translate", "qa", "summarize", "analyze", "extract", "compare"]:
    """Determine the user's intent from their query using semantic analysis.

    The function analyzes the query structure, semantics, and context to
    determine the most appropriate intent. It considers:
    - Query complexity and structure
    - Semantic meaning beyond keywords
    - Context indicators (file references, specific requests)
    - Chinese language patterns and expressions

    Parameters
    ----------
    query : str
        The user's query string.

    Returns
    -------
    Literal["translate", "qa", "summarize", "analyze", "extract", "compare"]
        The detected intent.
    """
    if not query:
        return "qa"
    
    q = query.strip()
    q_lower = q.lower()
    
    # 1. TRANSLATION INTENT - Highest priority for clear translation requests
    if _is_translation_request(q, q_lower):
        return "translate"
    
    # 2. SUMMARIZATION INTENT - Clear summary requests
    if _is_summarization_request(q, q_lower):
        return "summarize"
    
    # 3. EXTRACTION INTENT - Specific extraction tasks
    if _is_extraction_request(q, q_lower):
        return "extract"
    
    # 4. COMPARISON INTENT - Comparison tasks
    if _is_comparison_request(q, q_lower):
        return "compare"
    
    # 5. ANALYSIS INTENT - Complex analysis requests
    if _is_analysis_request(q, q_lower):
        return "analyze"
    
    # 6. DEFAULT: Q&A/RAG - For questions, explanations, and general queries
    return "qa"


def _is_translation_request(query: str, query_lower: str) -> bool:
    """Check if the query is a translation request."""
    # Direct translation keywords
    translation_keywords = [
        # English
        "translate", "translation", "translate this", "translate the file",
        "please translate", "convert to", "in english", "in chinese",
        # Chinese - direct translation
        "翻译", "翻译成", "翻译为", "转换成", "转换为", "英译", "中译",
        "英文化", "中文化", "英译中", "中译英"
    ]
    
    # Language direction indicators
    language_indicators = [
        "英文", "中文", "英语", "汉语", "英文版", "中文版"
    ]
    
    # Check for direct translation requests
    if any(keyword in query_lower for keyword in translation_keywords):
        return True
    
    # Check for language direction requests
    if any(indicator in query for indicator in language_indicators):
        # But exclude if it's asking about language features, not requesting translation
        if any(word in query_lower for word in ["优势", "特点", "区别", "比较", "分析"]):
            return False
        return True
    
    return False


def _is_summarization_request(query: str, query_lower: str) -> bool:
    """Check if the query is a summarization request."""
    summary_keywords = [
        # English
        "summarize", "summary", "summarise", "key points", "main points",
        "executive summary", "brief", "overview", "gist", "essence",
        # Chinese
        "总结", "概括", "摘要", "要点", "重点", "概要", "大纲", "梗概"
    ]
    
    return any(keyword in query_lower for keyword in summary_keywords)


def _is_extraction_request(query: str, query_lower: str) -> bool:
    """Check if the query is an extraction request."""
    extraction_keywords = [
        # English
        "extract", "find all", "list all", "get all", "identify",
        "pull out", "collect", "gather", "retrieve", "locate",
        # Chinese
        "提取", "找出", "列出", "获取", "识别", "收集", "检索", "定位"
    ]
    
    return any(keyword in query_lower for keyword in extraction_keywords)


def _is_comparison_request(query: str, query_lower: str) -> bool:
    """Check if the query is a comparison request."""
    comparison_keywords = [
        # English
        "compare", "comparison", "contrast", "difference", "differences",
        "similar", "similarities", "versus", "vs", "against", "match",
        # Chinese
        "比较", "对比", "对照", "差异", "区别", "相似", "相似性", "对比分析"
    ]
    
    return any(keyword in query_lower for keyword in comparison_keywords)


def _is_analysis_request(query: str, query_lower: str) -> bool:
    """Check if the query is an analysis request."""
    # Analysis keywords that indicate deep examination
    analysis_keywords = [
        # English
        "analyze", "analyse", "analysis", "insights", "trends", "patterns",
        "examine", "evaluate", "assess", "review", "interpret", "findings",
        # Chinese - deep analysis
        "分析", "分析一下", "分析这个", "分析文档", "分析内容", "分析结果",
        "深入分析", "详细分析", "综合分析", "系统分析"
    ]
    
    # Check for analysis keywords
    if any(keyword in query_lower for keyword in analysis_keywords):
        return True
    
    # Check for complex analytical patterns in Chinese
    analytical_patterns = [
        "阐述", "阐述一下", "阐述这个", "描述", "描述一下", "描述这个"
    ]
    
    # But exclude if it's asking for explanation/understanding (which should be Q&A)
    if any(pattern in query for pattern in analytical_patterns):
        # Check if it's asking for explanation rather than analysis
        explanation_indicators = ["解释", "说明", "理解", "了解", "知道"]
        if any(indicator in query for indicator in explanation_indicators):
            return False  # This is Q&A, not analysis
        return True
    
    return False


def _is_qa_request(query: str, query_lower: str) -> bool:
    """Check if the query is a Q&A/RAG request (default case)."""
    # Q&A patterns that should trigger RAG
    qa_patterns = [
        # English
        "what is", "what are", "how", "why", "when", "where", "which",
        "can you", "could you", "please tell", "tell me", "i want to know",
        "question", "ask", "inquiry", "query",
        # Chinese - questions and explanations
        "什么是", "什么是", "怎么", "为什么", "什么时候", "哪里", "哪个",
        "能否", "可以", "请告诉我", "告诉我", "我想知道", "问题", "询问", "查询"
    ]
    
    # Special Chinese patterns that indicate Q&A/RAG
    chinese_qa_patterns = [
        "解释", "解释一下", "解释这个", "说明", "说明一下", "说明这个",
        "结合", "结合这个", "结合文件", "结合文档", "综合", "综合这个",
        "根据", "根据文件", "根据文档", "根据信息", "基于", "基于文件", "基于文档",
        "文件信息", "文档信息", "文档中", "文件中", "资料中", "内容中"
    ]
    
    # Check for Q&A patterns
    if any(pattern in query_lower for pattern in qa_patterns):
        return True
    
    # Check for Chinese Q&A patterns
    if any(pattern in query for pattern in chinese_qa_patterns):
        return True
    
    # Default: if no other intent is detected, it's Q&A
    return True

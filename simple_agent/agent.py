"""Implementation of a simple agent for interacting with a local LLM.

This module defines :class:`SimpleAgent`, a lightweight helper that
assembles the various components defined in this package to perform
file parsing, intent detection, retrieval‑augmented question answering,
and translation.  It assumes the presence of a vLLM server exposing
an OpenAI‑compatible API (e.g., ``/v1/chat/completions`` endpoint).
"""

from __future__ import annotations

import json
import os
from typing import Optional, List

import requests
from tqdm import tqdm

from .file_parser import parse_file
from .intent_recognizer import detect_intent
from .rag_utils import RAGRetriever
from .enhanced_chunking import chunk_document, ChunkingMode, ChunkingConfig, get_file_type
from .storage_factory import (
    ensure_session_dirs,
    append_chat_message,
    load_chat_history,
    compute_file_hash,
    copy_upload,
    cache_key,
    save_chunks,
    load_chunks,
    save_retriever,
    load_retriever,
    set_last_doc_key,
    get_last_doc_key,
    get_all_cached_documents,
    get_all_cached_documents_with_names,
)
from .language_utils import detect_language, get_system_prompt, get_processing_message

# Configuration constant *after* imports
DEFAULT_REQUEST_TIMEOUT = int(os.environ.get("AGENTIC_REQUEST_TIMEOUT", "30"))
STREAM_CHAR_BY_CHAR = os.environ.get("STREAM_CHAR_BY_CHAR", "true").lower() == "true"
FORCE_SMALL_CHUNKS = os.getenv("FORCE_SMALL_CHUNKS", "true").lower() == "true"
NETWORK_STREAMING_OPTIMIZED = os.getenv("NETWORK_STREAMING_OPTIMIZED", "true").lower() == "true"
DEBUG_STREAMING = os.getenv("DEBUG_STREAMING", "false").lower() == "true"

__all__ = ["SimpleAgent"]


class SimpleAgent:
    """A tiny agent capable of translation and question answering.

    The agent operates in two modes based on the user's intent.  When
    the intent is ``"translate"``, it will translate the entirety of an
    attached document (respecting the model's context window by
    chunking if necessary).  When the intent is ``"qa"``, it will use
    retrieval‑augmented generation to answer the user's question from
    the attached document if provided.  If no file is attached, it
    attempts to answer the question directly using the LLM.

    A running vLLM server is required.  You must supply the base
    endpoint of the server (e.g., ``http://localhost:8000``) and the
    model name you wish to use.  The class uses synchronous HTTP
    requests to communicate with the server.

    Parameters
    ----------
    llm_endpoint : str
        Base URL of the vLLM server (without trailing slash).  The
        expected chat completions endpoint is ``{llm_endpoint}/v1/chat/completions``.
    model : str, optional
        Name of the model to use.  Defaults to ``"gpt-3.5-turbo"``.  The
        model must be available on your vLLM server.
    max_context_tokens : int, optional
        Maximum number of tokens supported by the model.  This value
        influences how large a chunk the agent feeds into the LLM.  As
        we do not have access to a tokenizer in this environment, the
        value is converted to characters by multiplying by four (a
        rough approximation).
    """

    def __init__(self, llm_endpoint: str, model: str = "gpt-3.5-turbo", max_context_tokens: int = 128_000) -> None:
        self.llm_endpoint = llm_endpoint.rstrip("/")
        self.model = model
        self.max_context_tokens = max_context_tokens

    # -----------------------------------------------------------------
    # LLM interaction
    #
    def _call_llm(self, messages: List[dict], stream: bool = False):
        """Invoke the chat completions endpoint.

        A minimal wrapper around ``requests.post`` that sends a JSON
        payload and returns the assistant's reply.  If the LLM
        returns an error response, an exception is raised.

        Parameters
        ----------
        messages : List[dict]
            A list of message objects formatted for an OpenAI‑style
            chat completion request.
        stream : bool, optional
            Whether to stream the response. If True, returns a generator
            that yields response chunks. If False, returns the complete response.

        Returns
        -------
        Union[str, Generator[str, None, None]]
            If stream=False: The complete response content.
            If stream=True: A generator yielding response chunks.
        """
        url = f"{self.llm_endpoint}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }

        if stream:
            return self._stream_response(url, headers, payload)
        else:
            return self._get_complete_response(url, headers, payload)

    def _get_complete_response(self, url: str, headers: dict, payload: dict) -> str:
        """Get the complete response from the LLM."""
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=DEFAULT_REQUEST_TIMEOUT)
        try:
            response.raise_for_status()
        except Exception:
            # propagate the error with more context
            raise RuntimeError(f"LLM request failed with status {response.status_code}: {response.text}")
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("LLM did not return any choices")
        return choices[0]["message"]["content"]

    def _stream_response(self, url: str, headers: dict, payload: dict):
        """Stream the response from the LLM with improved granularity control."""
        response = requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=DEFAULT_REQUEST_TIMEOUT)
        try:
            response.raise_for_status()
        except Exception:
            # propagate the error with more context
            raise RuntimeError(f"LLM request failed with status {response.status_code}: {response.text}")

        buffer = ""
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == "[DONE]":
                        # Yield any remaining buffered content
                        if buffer:
                            if STREAM_CHAR_BY_CHAR:
                                for char in buffer:
                                    yield char
                            else:
                                yield buffer
                        print("✅ LLM streaming completed")
                        break
                    try:
                        json_data = json.loads(data)
                        choices = json_data.get("choices") or []
                        if choices and choices[0].get("delta", {}).get("content"):
                            content = choices[0]["delta"]["content"]
                            if DEBUG_STREAMING and FORCE_SMALL_CHUNKS and STREAM_CHAR_BY_CHAR:
                                print(f"🔍 Debug: Received chunk of size {len(content)} characters")
                            buffer += content
                            
                            # Control streaming granularity
                            if STREAM_CHAR_BY_CHAR:
                                if FORCE_SMALL_CHUNKS:
                                    # Force ultra-smooth streaming by yielding immediately
                                    # Don't buffer - yield each character as it comes
                                    # For network streaming, add small delays to prevent buffering
                                    import time
                                    for char in content:
                                        yield char
                                        # Small delay to prevent network buffering (configurable)
                                        if NETWORK_STREAMING_OPTIMIZED:
                                            time.sleep(0.001)  # 1ms delay
                                    buffer = ""  # Clear buffer since we're not using it
                                else:
                                    # Smart chunking with natural break points
                                    buffer += content
                                    if len(buffer) >= 3:  # Buffer at least 3 characters
                                        # Find a good break point
                                        break_point = self._find_break_point(buffer)
                                        if break_point > 0:
                                            # Yield the content up to the break point
                                            for char in buffer[:break_point]:
                                                yield char
                                            # Keep the rest in buffer
                                            buffer = buffer[break_point:]
                            else:
                                # For chunk-level streaming, yield the entire content
                                yield content
                                buffer = ""
                    except json.JSONDecodeError:
                        continue

    def _find_break_point(self, text: str) -> int:
        """Find a good break point in text for streaming."""
        # Prefer breaking at spaces, then at punctuation, then at character boundaries
        if len(text) < 3:
            return 0  # Not enough text to break
        
        # Look for spaces first (preferred)
        space_pos = text.rfind(' ')
        if space_pos > 0:
            return space_pos + 1
        
        # Look for punctuation marks
        punctuation = ',.!?;:'
        for i in range(len(text) - 1, 0, -1):
            if text[i] in punctuation:
                return i + 1
        
        # If no good break point, break at 2/3 of the text length
        return max(1, len(text) * 2 // 3)

    def _extract_conversation_text(self, history: List[dict]) -> str:
        """Extract conversation text from chat history for translation."""
        conversation_lines = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                # Format: "User: [content]" or "Assistant: [content]"
                conversation_lines.append(f"{role.title()}: {content}")
        
        return "\n\n".join(conversation_lines)
    
    def _parse_file_selection(self, selection: str, cached_docs: List[tuple]) -> List[tuple]:
        """Parse user's file selection and return selected documents."""
        selection = selection.strip().lower()
        
        if selection == "all":
            return cached_docs
        elif selection == "latest":
            # Get the most recent document
            last_doc_key = get_last_doc_key(self.storage_paths) if hasattr(self, 'storage_paths') else None
            if last_doc_key:
                for doc_key, chunks in cached_docs:
                    if doc_key == last_doc_key:
                        return [(doc_key, chunks)]
            # If no last doc key, return the last document in the list
            return [cached_docs[-1]] if cached_docs else []
        else:
            # Parse numeric selections (e.g., "1", "1,3", "1,2,3")
            try:
                indices = []
                for part in selection.split(','):
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part) - 1  # Convert to 0-based index
                        if 0 <= idx < len(cached_docs):
                            indices.append(idx)
                
                if indices:
                    return [cached_docs[i] for i in indices]
                else:
                    return []
            except (ValueError, IndexError):
                return []
    
    def _is_file_selection_response(self, query: str) -> bool:
        """Check if the query is a response to a file selection confirmation."""
        query_lower = query.strip().lower()
        
        # Check for numeric responses
        if query_lower.isdigit():
            return True
        
        # Check for comma-separated numbers
        if ',' in query_lower:
            parts = query_lower.split(',')
            return all(part.strip().isdigit() for part in parts)
        
        # Check for keywords
        if query_lower in ['all', 'latest']:
            return True
        
        # More flexible pattern matching for remote API calls
        # Check if it looks like a file selection (numbers, commas, spaces, dashes)
        import re
        if re.match(r'^[\d\s,.-]+$', query_lower) and len(query_lower) <= 20:
            # Further validate it contains at least one digit
            return bool(re.search(r'\d', query_lower))
        
        return False
    
    def _should_auto_select_all_files(self, intent: str) -> bool:
        """Determine if the agent should automatically select all files for this intent."""
        # Tasks that typically benefit from multiple files
        auto_select_intents = ["compare"]
        return intent in auto_select_intents
    
    def _should_ask_for_file_confirmation(self, intent: str, num_files: int) -> bool:
        """Determine if the agent should ask for file confirmation for this intent."""
        # Only ask for confirmation if there are multiple files and it's a single-file task
        single_file_intents = ["translate", "summarize", "analyze", "extract"]
        return intent in single_file_intents and num_files > 1

    # -----------------------------------------------------------------
    # High level tasks
    #
    def _detect_translation_direction(self, query: str, file_text: str) -> tuple[str, str]:
        """Analyze user's intention and determine translation direction.
        
        Returns:
            tuple: (source_language, target_language)
        """
        # First, detect the language of the file content
        source_language = self._detect_content_language(file_text)
        
        # Then analyze the user's query to determine target language
        target_language = self._extract_target_language_from_query(query)
        
        # If we can't determine from query, use intelligent defaults
        if not target_language:
            if source_language == "Chinese":
                target_language = "English"  # Most common: Chinese -> English
            elif source_language == "English":
                target_language = "Chinese"  # Common: English -> Chinese
            else:
                target_language = "English"  # Default fallback
        
        print(f"🔍 Translation direction: {source_language} → {target_language}")
        return source_language, target_language
    
    def _detect_content_language(self, text: str) -> str:
        """Detect the language of the content to be translated."""
        if not text:
            return "Unknown"
        
        # Simple language detection based on character sets
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len([c for c in text if c.isalpha() and ord(c) < 128])
        
        # Calculate ratios
        total_chars = len([c for c in text if c.isalpha()])
        if total_chars == 0:
            return "Unknown"
        
        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars
        
        if chinese_ratio > 0.3:  # If more than 30% are Chinese characters
            return "Chinese"
        elif english_ratio > 0.7:  # If more than 70% are English characters
            return "English"
        else:
            # Mixed or other language, try to detect from common patterns
            if any(word in text.lower() for word in ['what', 'is', 'the', 'and', 'of', 'in', 'to']):
                return "English"
            elif any(word in text for word in ['什么', '是', '的', '和', '在', '到']):
                return "Chinese"
            else:
                return "Unknown"
    
    def _extract_target_language_from_query(self, query: str) -> str:
        """Extract target language from user's query using pattern matching."""
        query_lower = query.lower()
        
        # Common patterns for target language specification
        patterns = {
            "english": ["to english", "into english", "translate to english", "english", "en"],
            "chinese": ["to chinese", "into chinese", "translate to chinese", "chinese", "zh", "中文"],
            "japanese": ["to japanese", "into japanese", "translate to japanese", "japanese", "ja", "日语"],
            "korean": ["to korean", "into korean", "translate to korean", "korean", "ko", "韩语"],
            "french": ["to french", "into french", "translate to french", "french", "fr"],
            "german": ["to german", "into german", "translate to german", "german", "de"],
            "spanish": ["to spanish", "into spanish", "translate to spanish", "spanish", "es"],
            "russian": ["to russian", "into russian", "translate to russian", "russian", "ru"]
        }
        
        for target_lang, patterns_list in patterns.items():
            if any(pattern in query_lower for pattern in patterns_list):
                return target_lang
        
        return None

    def _translate(
        self, text: str, target_language: str = "English", stream: bool = False, detected_language: str = "Chinese"
    ):
        """Translate a block of text into the target language.

        The request is made in a single call to the LLM.  A system
        prompt instructs the model to act as a translation assistant.

        Parameters
        ----------
        text : str
            The text to be translated.
        target_language : str, optional
            The language into which the text should be translated.  Defaults
            to English.
        stream : bool, optional
            Whether to stream the response. If True, returns a generator
            that yields response chunks. If False, returns the complete response.

        Returns
        -------
        Union[str, Generator[str, None, None]]
            If stream=False: The translated text.
            If stream=True: A generator yielding translation chunks.
        """
        # Determine source language from the text content, not from detected_language parameter
        # If target_language is English, assume source is Chinese (most common case)
        # If target_language is Chinese, assume source is English
        if target_language.lower() in ["english", "en", "英文"]:
            # Translating TO English, so source is likely Chinese
            system_prompt = """You are a professional translator. Your task is to translate Chinese text to English.

CRITICAL REQUIREMENTS:
1. The input text is in CHINESE language
2. You MUST translate it to ENGLISH language
3. DO NOT output Chinese characters in your response
4. Preserve the meaning, formatting, and structure where possible
5. If you see Chinese characters like '超声波', '专业补给站', etc., translate them to English
6. Output ONLY English text

Example: If input is '超声波是什么?', output should be 'What is ultrasound?' NOT '超声波是什么?'"""
            user_content = f"TRANSLATE THIS CHINESE TEXT TO ENGLISH (output only English):\n\n{text}"
        elif target_language.lower() in ["chinese", "zh", "中文"]:
            # Translating TO Chinese, so source is likely English
            system_prompt = """你是一个专业的翻译专家。你的任务是将英文文本翻译成中文。

重要要求：
1. 输入文本是英文语言
2. 你必须将其翻译成中文语言
3. 不要在回复中输出英文字符
4. 保持原有的格式和结构
5. 如果看到英文单词，请翻译成中文
6. 只输出中文文本"""
            user_content = f"请将以下英文文本翻译成中文（只输出中文）：\n\n{text}"
        else:
            # Generic translation prompt
            system_prompt = f"""You are a professional translator. Translate the following text to {target_language}.

IMPORTANT: Output ONLY in {target_language} language. Do not include the original text."""
            user_content = f"Please translate this text to {target_language} (output only in {target_language}):\n\n{text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self._call_llm(messages, stream=stream)

    def _qa(
        self,
        question: str,
        docs: List[str],
        stream: bool = False,
        history: Optional[List[dict]] = None,
        detected_language: str = "Chinese",
    ):
        """Answer a question given a list of context documents.

        This method concatenates the provided documents into a single
        context and asks the model to answer the question based solely
        on that context.  If the list of documents is empty, it asks
        the model to answer without additional context.

        Parameters
        ----------
        question : str
            The user's question.
        docs : List[str]
            A list of contextual documents retrieved from the user's
            uploaded file.
        stream : bool, optional
            Whether to stream the response. If True, returns a generator
            that yields response chunks. If False, returns the complete response.

        Returns
        -------
        Union[str, Generator[str, None, None]]
            If stream=False: The LLM's answer.
            If stream=True: A generator yielding answer chunks.
        """
        context = "\n\n".join(docs) if docs else ""
        # Use Chinese-first system prompt
        system_prompt = get_system_prompt(detected_language)
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # Include brief chat history if provided
        if history:
            # take last few turns (limit tokens naïvely by message count)
            for h in history[-6:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        # Add the enhanced RAG prompt with source attribution
        if context:
            if detected_language == "Chinese":
                prompt = f"""基于提供的文档内容，请回答以下问题：{question}

## 文档内容：
{context}

## 回答要求：
1. **优先使用文档内容**：主要基于上述文档内容回答
2. **标明信息来源**：明确区分文档中的信息和通用知识
3. **承认限制**：如果文档中没有足够信息，请明确说明
4. **结构化回答**：使用清晰的标题和要点组织答案
5. **风险提示**：对重要决策相关问题提供必要提醒"""
            else:
                prompt = f"""Based on the provided document content, please answer the following question: {question}

## Document Content:
{context}

## Response Requirements:
1. **Prioritize document content**: Base your answer primarily on the above document content
2. **Indicate information sources**: Clearly distinguish between document information and general knowledge
3. **Acknowledge limitations**: If there isn't sufficient information in the documents, clearly state this
4. **Structured response**: Use clear headings and bullet points to organize your answer
5. **Risk alerts**: Provide necessary warnings for decision-related questions"""
        else:
            if detected_language == "Chinese":
                prompt = f"""请基于你的知识回答以下问题：{question}

## 回答要求：
1. **知识边界**：仅提供确信的、可靠的信息
2. **不确定性说明**：对不确定的信息明确标注"需要进一步确认"
3. **专业建议**：涉及重要决策时建议咨询相关专业人士
4. **结构化回答**：使用清晰的逻辑结构组织答案"""
            else:
                prompt = f"""Please answer the following question based on your knowledge: {question}

## Response Requirements:
1. **Knowledge boundaries**: Only provide information you are confident and reliable about
2. **Uncertainty indication**: Clearly mark uncertain information as "requires further confirmation"
3. **Professional advice**: For important decisions, recommend consulting relevant professionals
4. **Structured response**: Use clear logical structure to organize your answer"""

        messages.append({"role": "user", "content": prompt})
        return self._call_llm(messages, stream=stream)

    def _summarize(self, text: str, stream: bool = False, detected_language: str = "Chinese"):
        """Summarize a document or text block with enterprise focus."""
        if detected_language == "Chinese":
            system_prompt = """你是一个专业的企业文档总结专家。请创建结构化、全面的文档摘要，突出关键要点、主要观点和重要细节。

总结要求：
- 使用执行摘要格式，包含核心结论
- 识别关键业务信息、数据和建议
- 保持客观中立，避免主观解读
- 标注重要的风险点或决策要素
- 使用专业商业语言"""
            user_content = f"请对以下文档内容进行专业总结：\n\n{text}"
        else:
            system_prompt = (
                "You are a professional enterprise document summarization expert. "
                "Create structured, comprehensive document summaries highlighting key "
                "points, main ideas, and important details.\n\n"
                "Summary requirements:\n"
                "- Use executive summary format with core conclusions\n"
                "- Identify key business information, data, and recommendations\n"
                "- Maintain objectivity and avoid subjective interpretations\n"
                "- Mark important risk factors or decision elements\n"
                "- Use professional business language"
            )
            user_content = f"Please provide a professional summary of the following document:\n\n{text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self._call_llm(messages, stream=stream)

    def _analyze(self, text: str, stream: bool = False):
        """Analyze a document for insights, patterns, and key findings."""
        system_prompt = (
            "You are an expert analyst. Analyze the provided text for key insights, "
            "patterns, trends, and important findings. Provide a structured analysis "
            "with clear observations and implications."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please analyze the following text:\n\n{text}"},
        ]
        return self._call_llm(messages, stream=stream)

    def _extract(self, text: str, query: str, stream: bool = False):
        """Extract specific information from the text based on the query."""
        system_prompt = (
            "You are an expert information extractor. Extract the specific information "
            "requested from the provided text. Be precise and comprehensive. "
            "Format your response clearly with the extracted information."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract the following from the text: {query}\n\nText:\n{text}"},
        ]
        return self._call_llm(messages, stream=stream)

    def _compare(self, texts: List[str], query: str, stream: bool = False):
        """Compare multiple documents and highlight differences/similarities."""
        system_prompt = (
            "You are an expert document comparator. Compare the provided documents "
            "and highlight key similarities, differences, and unique aspects. "
            "Structure your comparison clearly with specific examples."
        )

        # Combine texts with clear separators
        combined_text = ""
        for i, text in enumerate(texts, 1):
            combined_text += f"\n\n--- Document {i} ---\n{text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Compare these documents focusing on: {query}\n{combined_text}"},
        ]
        return self._call_llm(messages, stream=stream)

    # -----------------------------------------------------------------
    # Public interface
    #
    def run(
        self,
        query: str,
        file_path: Optional[str] = None,
        target_language: str = "Chinese",
        stream: bool = False,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Process a user query with an optional attached file.

        This is the main entry point for the agent.  It determines the
        user's intent, parses the file if provided, chunks the content
        appropriately, and delegates to translation or question
        answering logic.

        Parameters
        ----------
        query : str
            The user's input message.
        file_path : Optional[str], optional
            Path to an attached file.  If provided, it will be parsed
            into text for use by the LLM.  Defaults to ``None``.
        target_language : str, optional
            Desired output language for translation tasks.  Defaults to
            English.
        stream : bool, optional
            Whether to stream the response. If True, returns a generator
            that yields response chunks. If False, returns the complete response.
        user_id : Optional[str]
            Identifier for the user to enable per-user storage.
        session_id : Optional[str]
            Identifier for the chat session to group history and caches.

        Returns
        -------
        Union[str, Generator[str, None, None]]
            If stream=False: The complete response.
            If stream=True: A generator yielding response chunks.

        Raises
        ------
        ValueError
            If translation is requested but no file is attached.
        """
        # Detect language from query for appropriate messaging
        detected_language = detect_language(query)

        # Parse the file if one is supplied
        file_text = None
        file_ext = "txt"
        storage_paths = None
        if user_id and session_id:
            storage_paths = ensure_session_dirs(user_id=user_id, session_id=session_id)
            # append user message to history early
            append_chat_message(storage_paths, role="user", content=query)
        # Load recent chat history for prompt context
        recent_history = load_chat_history(storage_paths, max_messages=12) if storage_paths else None
        if file_path:
            print(get_processing_message("parsing", detected_language, filename=file_path))
            if storage_paths:
                # Copy upload to session folder
                uploaded_path = copy_upload(storage_paths, file_path)
                file_path = str(uploaded_path)
                print(f"📁 File uploaded to session: {uploaded_path}")
            file_text = parse_file(file_path)
            print(get_processing_message("parsed", detected_language, chars=len(file_text)))
            file_ext = get_file_type(file_path)
            
            # Check if we have previous context in this session
            if storage_paths:
                cached_docs = get_all_cached_documents_with_names(storage_paths)
                if cached_docs:
                    print(f"📚 Session has {len(cached_docs)} cached documents from previous uploads")
                    for doc_key, filename, chunks in cached_docs:
                        print(f"   - {filename}: {len(chunks)} chunks")
                else:
                    print("📚 No previous documents in this session")

        # Determine intent from the query first
        intent = detect_intent(query)
        print(f"🎯 Detected intent: {intent}")
        
        # Check if this is a response to a file selection confirmation
        if storage_paths and recent_history:
            # Check if the last assistant message was a file selection confirmation
            last_assistant_msg = None
            for msg in reversed(recent_history):
                if msg.get("role") == "assistant":
                    last_assistant_msg = msg.get("content", "")
                    break
            
            # More robust detection of file selection responses
            is_file_selection_response = False
            original_query_context = None
            
            if last_assistant_msg and "Multiple files found in this session" in last_assistant_msg:
                is_file_selection_response = True
                # Extract the original query from the previous user message
                for msg in reversed(recent_history):
                    if msg.get("role") == "user":
                        original_query_context = msg.get("content", "")
                        break
            elif self._is_file_selection_response(query) and storage_paths:
                # Even without clear context, if the query looks like a file selection
                # and we have multiple cached documents, treat it as a file selection
                cached_docs = get_all_cached_documents_with_names(storage_paths)
                if len(cached_docs) > 1:
                    is_file_selection_response = True
                    print(f"🔍 Detected potential file selection response: '{query}'")
                    # Try to find the original query from recent history
                    for msg in reversed(recent_history):
                        if msg.get("role") == "user" and not self._is_file_selection_response(msg.get("content", "")):
                            original_query_context = msg.get("content", "")
                            break
            
            if is_file_selection_response:
                # This is a response to file selection, parse it
                cached_docs = get_all_cached_documents_with_names(storage_paths)
                if cached_docs and self._is_file_selection_response(query):
                    selected_docs = self._parse_file_selection(query, cached_docs)
                    if selected_docs:
                        print(f"📋 User selected {len(selected_docs)} file(s) for processing")
                        
                        # Determine the task type from context or query
                        task_type = "compare"  # Default to compare for file selection
                        if last_assistant_msg:
                            if "translate" in last_assistant_msg.lower():
                                task_type = "translate"
                            elif "summarize" in last_assistant_msg.lower():
                                task_type = "summarize"
                            elif "analyze" in last_assistant_msg.lower():
                                task_type = "analyze"
                            elif "extract" in last_assistant_msg.lower():
                                task_type = "extract"
                        
                        if task_type == "compare":
                            # For comparison, we need to prepare multiple texts
                            self._selected_docs_for_comparison = selected_docs
                            # Store the original query context for the comparison
                            if original_query_context:
                                self._original_comparison_query = original_query_context
                                print(f"📄 Prepared {len(selected_docs)} selected files for comparison with original query: '{original_query_context}'")
                            else:
                                print(f"📄 Prepared {len(selected_docs)} selected files for comparison")
                            # Force the intent to be comparison since we're handling a comparison request
                            intent = "compare"
                        else:
                            # For other tasks, combine selected documents
                            combined_text = []
                            for doc_key, filename, chunks in selected_docs:
                                combined_text.append("\n\n".join(chunks))
                            file_text = "\n\n--- FILE SEPARATOR ---\n\n".join(combined_text)
                            print(f"📄 Combined {len(selected_docs)} selected files for processing")
                            # Force the intent based on the detected task type
                            intent = task_type
                    else:
                        error_msg = "❌ Invalid file selection. Please try again with a valid number, 'all', or 'latest'."
                        if stream:
                            def _error_stream():
                                for char in error_msg:
                                    yield char
                            return _error_stream()
                        else:
                            return error_msg
        
        if intent == "translate":
            # Translation can work with files, chat history, or direct text
            if not file_text:
                # First, check if we have cached documents from previous uploads in this session
                if storage_paths:
                    cached_docs = get_all_cached_documents_with_names(storage_paths)
                    if cached_docs:
                        print(f"📚 Found {len(cached_docs)} cached documents from previous uploads in this session")
                        
                        # Intelligent file selection for translation
                        if self._should_ask_for_file_confirmation("translate", len(cached_docs)):
                            # Create a confirmation message listing all available files
                            file_list = []
                            for i, (doc_key, filename, chunks) in enumerate(cached_docs, 1):
                                file_size = sum(len(chunk) for chunk in chunks)
                                file_list.append(f"{i}. {filename} ({file_size:,} characters)")
                            
                            confirmation_message = (
                                f"📋 Multiple files found in this session. Please specify which file(s) you want to translate:\n\n"
                                f"{chr(10).join(file_list)}\n\n"
                                f"Please respond with:\n"
                                f"- A single number (e.g., '1') to translate that specific file\n"
                                f"- Multiple numbers (e.g., '1,3') to translate multiple files\n"
                                f"- 'all' to translate all files\n"
                                f"- 'latest' to translate the most recent file"
                            )
                            
                            # Return the confirmation message instead of proceeding
                            if stream:
                                def _confirmation_stream():
                                    for char in confirmation_message:
                                        yield char
                                return _confirmation_stream()
                            else:
                                return confirmation_message
                        
                        # If only one document, use it directly
                        else:
                            doc_key, filename, chunks = cached_docs[0]
                            file_text = "\n\n".join(chunks)
                            print(f"📄 Using the uploaded file for translation: {filename}")
                
                # If still no file_text, check if the query itself contains text to translate
                if not file_text:
                    import re
                    translation_patterns = [
                        r'translate\s*:\s*(.+)',
                        r'translate\s+this\s*:\s*(.+)',
                        r'translate\s+"([^"]+)"',
                        r'translate\s+([^:]+?)(?:\s+to\s+\w+)?$'
                    ]
                    
                    text_to_translate = None
                    for pattern in translation_patterns:
                        match = re.search(pattern, query, re.IGNORECASE)
                        if match:
                            text_to_translate = match.group(1).strip()
                            break
                    
                    if text_to_translate:
                        # Use the extracted text for translation
                        file_text = text_to_translate
                        print(f"📝 Extracted text to translate: {text_to_translate[:100]}...")
                    elif recent_history:
                        # If we have chat history but no file, translate the conversation
                        print("💬 Translating chat history...")
                        # Extract the conversation text from history
                        conversation_text = self._extract_conversation_text(recent_history)
                        file_text = conversation_text
                        print(f"📝 Extracted conversation text: {conversation_text[:100]}...")
                    else:
                        raise ValueError(
                            "Translation tasks require one of the following:\n"
                            "1. An attached file with content\n"
                            "2. A previously uploaded file in this session\n"
                            "3. Text in the query (e.g., 'translate: Hello world' or 'translate this: How are you?')\n"
                            "4. Text in quotes (e.g., 'translate \"How are you?\" to Chinese')\n"
                            "5. Chat history (previous conversation)"
                        )

            # Get file extension for file-type aware chunking

            # Create translation-optimized chunking config
            translation_config = ChunkingConfig(
                mode=ChunkingMode.TRANSLATION,
                max_chars=self.max_context_tokens * 4,  # Large chunks for translation
                overlap=200,
                respect_sentences=True,
                respect_paragraphs=True,
            )
            
            print(f"🔧 Translation chunking config: mode={translation_config.mode.value}, max_chars={translation_config.max_chars}")

            print(f"✂️  Chunking text using {file_ext.upper()} optimized strategy...")
            # Cache by file hash + mode
            doc_hash = compute_file_hash(file_path) if file_path else "nofile"
            key = cache_key(doc_hash, "translation")
            cached_chunks = load_chunks(storage_paths, key) if storage_paths else None
            if cached_chunks is not None:
                print(f"📦 Loaded {len(cached_chunks)} cached chunks")
                chunks = cached_chunks
            else:
                chunks = chunk_document(
                    file_text, file_type=file_ext, mode=ChunkingMode.TRANSLATION, config=translation_config
                )
                if storage_paths:
                    save_chunks(storage_paths, key, chunks)
            print(f"📊 Created {len(chunks)} semantic chunks for translation")

            # Determine translation direction using intelligent language detection
            source_lang, target_lang = self._detect_translation_direction(query, file_text)
            
            if stream:
                # For streaming, we need to handle chunked translation differently
                # Since we can't easily stream multiple chunks, we'll concatenate and stream
                # the entire translation as one response
                print("🔄 Streaming translation...")
                all_text = "\n\n".join(chunks)
                
                def _wrap_translation_stream():
                    for chunk in self._translate(all_text, target_language=target_lang, stream=True, detected_language=source_lang):
                        yield chunk
                    print("✅ Translation streaming completed")
                
                return _wrap_translation_stream()
            else:
                translations = []
                for chunk in tqdm(chunks, desc="Translating chunks"):
                    translations.append(self._translate(chunk, target_language=target_lang, detected_language=source_lang))
                return "\n".join(translations)
        elif intent == "summarize":
            if not file_text:
                # Check if we have cached documents from previous uploads in this session
                if storage_paths:
                    cached_docs = get_all_cached_documents_with_names(storage_paths)
                    if cached_docs:
                        print(f"📚 Found {len(cached_docs)} cached documents from previous uploads in this session")
                        
                        # Intelligent file selection for summarization
                        if self._should_ask_for_file_confirmation("summarize", len(cached_docs)):
                            # Create a confirmation message listing all available files
                            file_list = []
                            for i, (doc_key, filename, chunks) in enumerate(cached_docs, 1):
                                file_size = sum(len(chunk) for chunk in chunks)
                                file_list.append(f"{i}. {filename} ({file_size:,} characters)")
                            
                            confirmation_message = (
                                f"📋 Multiple files found in this session. Please specify which file(s) you want to summarize:\n\n"
                                f"{chr(10).join(file_list)}\n\n"
                                f"Please respond with:\n"
                                f"- A single number (e.g., '1') to summarize that specific file\n"
                                f"- Multiple numbers (e.g., '1,3') to summarize multiple files\n"
                                f"- 'all' to summarize all files\n"
                                f"- 'latest' to summarize the most recent file"
                            )
                            
                            if stream:
                                def _confirmation_stream():
                                    for char in confirmation_message:
                                        yield char
                                return _confirmation_stream()
                            else:
                                return confirmation_message
                        
                        # If only one document, use it directly
                        else:
                            doc_key, filename, chunks = cached_docs[0]
                            file_text = "\n\n".join(chunks)
                            print(f"📄 Using the uploaded file for summarization: {filename}")
                
                if not file_text:
                    raise ValueError("Summarization tasks require an attached file with content.")

            # Create summarization-optimized chunking config
            summary_config = ChunkingConfig(
                mode=ChunkingMode.SUMMARIZATION,
                max_chars=30_000,  # Large chunks for better context
                overlap=200,
                respect_sentences=True,
                respect_paragraphs=True,
            )

            print("✂️  Chunking text for summarization...")
            doc_hash = compute_file_hash(file_path) if file_path else "nofile"
            key = cache_key(doc_hash, "summarization")
            cached_chunks = load_chunks(storage_paths, key) if storage_paths else None
            if cached_chunks is not None:
                print(f"📦 Loaded {len(cached_chunks)} cached chunks")
                chunks = cached_chunks
            else:
                chunks = chunk_document(file_text, file_type=file_ext, mode=ChunkingMode.SUMMARIZATION, config=summary_config)
                if storage_paths:
                    save_chunks(storage_paths, key, chunks)

            # Summarize each chunk and combine
            all_text = "\n\n".join(chunks)
            return self._summarize(all_text, stream=stream)

        elif intent == "analyze":
            # Check if this is actually a RAG request disguised as analysis
            # Queries like "结合这个文件，再解释下单晶探头的优势" should use RAG
            if file_text and _should_use_rag_instead_of_analysis(query):
                print("🔄 Detected explanation request with file - switching to RAG mode for better context handling")
                # Fall through to the RAG section below
                intent = "qa"  # This will trigger the RAG workflow
            elif not file_text:
                # Check if we have cached documents from previous uploads in this session
                if storage_paths:
                    cached_docs = get_all_cached_documents_with_names(storage_paths)
                    if cached_docs:
                        print(f"📚 Found {len(cached_docs)} cached documents from previous uploads in this session")
                        
                        # Intelligent file selection for analysis
                        if self._should_ask_for_file_confirmation("analyze", len(cached_docs)):
                            # Create a confirmation message listing all available files
                            file_list = []
                            for i, (doc_key, filename, chunks) in enumerate(cached_docs, 1):
                                file_size = sum(len(chunk) for chunk in chunks)
                                file_list.append(f"{i}. {filename} ({file_size:,} characters)")
                            
                            confirmation_message = (
                                f"📋 Multiple files found in this session. Please specify which file(s) you want to analyze:\n\n"
                                f"{chr(10).join(file_list)}\n\n"
                                f"Please respond with:\n"
                                f"- A single number (e.g., '1') to analyze that specific file\n"
                                f"- Multiple numbers (e.g., '1,3') to analyze multiple files\n"
                                f"- 'all' to analyze all files\n"
                                f"- 'latest' to analyze the most recent file"
                            )
                            
                            if stream:
                                def _confirmation_stream():
                                    for char in confirmation_message:
                                        yield char
                                return _confirmation_stream()
                            else:
                                return confirmation_message
                        
                        # If only one document, use it directly
                        else:
                            doc_key, filename, chunks = cached_docs[0]
                            file_text = "\n\n".join(chunks)
                            print(f"📄 Using the uploaded file for analysis: {filename}")
                
                if not file_text:
                    raise ValueError("Analysis tasks require an attached file with content.")

            # Create analysis-optimized chunking config
            analysis_config = ChunkingConfig(
                mode=ChunkingMode.ANALYSIS,
                max_chars=25_000,  # Medium chunks for balanced analysis
                overlap=200,
                respect_sentences=True,
                respect_paragraphs=True,
            )

            print("✂️  Chunking text for analysis...")
            doc_hash = compute_file_hash(file_path) if file_path else "nofile"
            key = cache_key(doc_hash, "analysis")
            cached_chunks = load_chunks(storage_paths, key) if storage_paths else None
            if cached_chunks is not None:
                print(f"📦 Loaded {len(cached_chunks)} cached chunks")
                chunks = cached_chunks
            else:
                chunks = chunk_document(file_text, file_type=file_ext, mode=ChunkingMode.ANALYSIS, config=analysis_config)
                if storage_paths:
                    save_chunks(storage_paths, key, chunks)

            # Analyze the combined text
            all_text = "\n\n".join(chunks)
            
            # Check if we have additional session context to enhance the analysis
            if storage_paths:
                cached_docs = get_all_cached_documents_with_names(storage_paths)
                if cached_docs:
                    print(f"🔗 Enhancing analysis with {len(cached_docs)} cached documents from session...")
                    # Create enhanced context for analysis
                    enhanced_context = []
                    enhanced_context.append(f"📄 **Current File Analysis:**\n{all_text}")
                    
                    # Add relevant context from previous uploads
                    for doc_key, filename, doc_chunks in cached_docs:
                        if doc_key != key:  # Skip current file
                            doc_text = "\n\n".join(doc_chunks)
                            enhanced_context.append(f"📚 **Additional Context from {filename}:**\n{doc_text}")
                    
                    enhanced_text = "\n\n---\n\n".join(enhanced_context)
                    print(f"✅ Enhanced analysis context with session knowledge")
                    return self._analyze(enhanced_text, stream=stream)
            
            return self._analyze(all_text, stream=stream)

        elif intent == "extract":
            if not file_text:
                # Check if we have cached documents from previous uploads in this session
                if storage_paths:
                    cached_docs = get_all_cached_documents_with_names(storage_paths)
                    if cached_docs:
                        print(f"📚 Found {len(cached_docs)} cached documents from previous uploads in this session")
                        
                        # Intelligent file selection for extraction
                        if self._should_ask_for_file_confirmation("extract", len(cached_docs)):
                            # Create a confirmation message listing all available files
                            file_list = []
                            for i, (doc_key, filename, chunks) in enumerate(cached_docs, 1):
                                file_size = sum(len(chunk) for chunk in chunks)
                                file_list.append(f"{i}. {filename} ({file_size:,} characters)")
                            
                            confirmation_message = (
                                f"📋 Multiple files found in this session. Please specify which file(s) you want to extract from:\n\n"
                                f"{chr(10).join(file_list)}\n\n"
                                f"Please respond with:\n"
                                f"- A single number (e.g., '1') to extract from that specific file\n"
                                f"- Multiple numbers (e.g., '1,3') to extract from multiple files\n"
                                f"- 'all' to extract from all files\n"
                                f"- 'latest' to extract from the most recent file"
                            )
                            
                            if stream:
                                def _confirmation_stream():
                                    for char in confirmation_message:
                                        yield char
                                return _confirmation_stream()
                            else:
                                return confirmation_message
                        
                        # If only one document, use it directly
                        else:
                            doc_key, filename, chunks = cached_docs[0]
                            file_text = "\n\n".join(chunks)
                            print(f"📄 Using the uploaded file for extraction: {filename}")
                
                if not file_text:
                    raise ValueError("Extraction tasks require an attached file with content.")

            # Create extraction-optimized chunking config
            extract_config = ChunkingConfig(
                mode=ChunkingMode.EXTRACTION,
                max_chars=15_000,  # Small chunks for precise extraction
                overlap=100,
                respect_sentences=True,
                respect_paragraphs=True,
            )

            print("✂️  Chunking text for extraction...")
            doc_hash = compute_file_hash(file_path) if file_path else "nofile"
            key = cache_key(doc_hash, "extraction")
            cached_chunks = load_chunks(storage_paths, key) if storage_paths else None
            if cached_chunks is not None:
                print(f"📦 Loaded {len(cached_chunks)} cached chunks")
                chunks = cached_chunks
            else:
                chunks = chunk_document(file_text, file_type=file_ext, mode=ChunkingMode.EXTRACTION, config=extract_config)
                if storage_paths:
                    save_chunks(storage_paths, key, chunks)

            # Extract from the combined text
            all_text = "\n\n".join(chunks)
            return self._extract(all_text, query, stream=stream)

        elif intent == "compare":
            # For comparison, we can use current file + cached documents, or just cached documents
            texts = []

            # Check if we have pre-selected documents for comparison
            if hasattr(self, '_selected_docs_for_comparison') and self._selected_docs_for_comparison:
                print(f"📋 Using {len(self._selected_docs_for_comparison)} pre-selected files for comparison")
                
                # Use original query context if available
                comparison_query = query
                if hasattr(self, '_original_comparison_query') and self._original_comparison_query:
                    comparison_query = self._original_comparison_query
                    print(f"📝 Using original comparison query: '{comparison_query}'")
                    # Clear the stored query after use
                    delattr(self, '_original_comparison_query')
                
                for doc_key, filename, chunks in self._selected_docs_for_comparison:
                    texts.append("\n\n".join(chunks))
                # Clear the selection after use
                delattr(self, '_selected_docs_for_comparison')
                
                # Use the original query for the comparison
                query = comparison_query
            else:
                # Add current file if provided
                if file_text:
                    texts.append(file_text)

                # Add all cached documents from the session
                if storage_paths:
                    cached_docs = get_all_cached_documents_with_names(storage_paths)
                    if cached_docs:
                        print(f"📚 Found {len(cached_docs)} cached documents from previous uploads in this session")
                        
                        # For comparison tasks, intelligently handle multiple files
                        if len(cached_docs) > 1 and not file_text:
                            # Auto-select all files for comparison (intelligent behavior)
                            print(f"🤖 Intelligent selection: Auto-selecting all {len(cached_docs)} files for comparison")
                            for doc_key, filename, chunks in cached_docs:
                                texts.append("\n\n".join(chunks))
                            print(f"📄 Using all {len(cached_docs)} cached documents for comparison")
                        
                        # If only one cached document and no current file, use it
                        elif len(cached_docs) == 1 and not file_text:
                            doc_key, filename, chunks = cached_docs[0]
                            texts.append("\n\n".join(chunks))
                            print(f"📄 Using the uploaded file for comparison: {filename}")
                        
                        # If we have current file and cached documents, add all cached documents
                        elif file_text:
                            for doc_key, filename, chunks in cached_docs:
                                cached_text = "\n\n".join(chunks)
                                texts.append(cached_text)
                            print(f"📄 Adding {len(cached_docs)} cached documents to comparison with current file")

            # Need at least one document to compare
            if not texts:
                raise ValueError(
                    "Comparison tasks require at least one document. Please upload a file "
                    "or use documents from previous conversation turns."
                )

            # If only one document, inform the user but still proceed
            if len(texts) == 1:
                print("📄 Only one document available for comparison. Proceeding with analysis of this single document.")
            else:
                print(f"📊 Comparing {len(texts)} documents from current upload and session history.")

            return self._compare(texts, query, stream=stream)

        else:
            # For QA tasks, build a small corpus from the file (if present).
            context_docs: List[str] = []
            if file_text:
                # Get file extension for file-type aware chunking
                file_ext = get_file_type(file_path)

                # Create RAG-optimized chunking config
                rag_config = ChunkingConfig(
                    mode=ChunkingMode.RAG,
                    max_chars=20_000,  # Small chunks for retrieval
                    overlap=200,
                    respect_sentences=True,
                    respect_paragraphs=True,
                )

                print(f"✂️  Preparing {file_ext.upper()} chunks for question answering...")
                doc_hash = compute_file_hash(file_path)
                key = cache_key(doc_hash, "rag")
                cached_chunks = load_chunks(storage_paths, key) if storage_paths else None
                if cached_chunks is not None:
                    print(f"📦 Loaded {len(cached_chunks)} cached chunks")
                    docs = cached_chunks
                else:
                    docs = chunk_document(file_text, file_type=file_ext, mode=ChunkingMode.RAG, config=rag_config)
                    if storage_paths:
                        save_chunks(storage_paths, key, docs)
                        set_last_doc_key(storage_paths, key)
                print(f"📊 Created {len(docs)} semantic chunks for RAG")
                # Build a simple retriever over the docs
                print("🔍 Building search index...")
                retriever_loaded = load_retriever(storage_paths, key) if storage_paths else None
                if retriever_loaded:
                    vectorizer, doc_vectors, nn = retriever_loaded
                    retriever = RAGRetriever(docs, vectorizer=vectorizer, doc_vectors=doc_vectors, nn=nn)
                else:
                    retriever = RAGRetriever(docs)
                    if storage_paths:
                        save_retriever(storage_paths, key, retriever.vectorizer, retriever.doc_vectors, retriever.nn)
                # Retrieve top few chunks relevant to the question
                print("🔎 Searching for relevant content...")
                results = retriever.query(query, k=3)
                for idx, dist in results:
                    context_docs.append(docs[idx])
                print(f"✅ Found {len(context_docs)} relevant document sections")
            
            # Always check for accumulated session context, even when no file is uploaded
            if storage_paths:
                cached_docs = get_all_cached_documents_with_names(storage_paths)
                if cached_docs:
                    print(f"📖 Checking {len(cached_docs)} cached documents from previous uploads in this session...")
                    # Track which documents we've already processed to avoid duplicates
                    processed_docs = set()
                    
                    for doc_key, filename, chunks in cached_docs:
                        # Skip if we already have this document from current upload
                        if not file_text or doc_key != cache_key(compute_file_hash(file_path), "rag") if file_path else None:
                            # Skip if we've already processed this document
                            if doc_key in processed_docs:
                                continue
                            processed_docs.add(doc_key)
                            # Use RAG to find relevant content from cached documents
                            if "rag" in doc_key:
                                # This is already RAG-optimized, use it directly
                                context_docs.extend(chunks[:2])  # Add top 2 chunks from each cached doc
                                print(f"📚 Added {len(chunks[:2])} chunks from cached RAG document: {doc_key}")
                            else:
                                # This is from other modes (translation, analysis, etc.), create RAG chunks
                                print(f"🔄 Converting cached document to RAG format: {doc_key}")
                                rag_chunks = chunk_document("\n\n".join(chunks), mode=ChunkingMode.RAG, config=ChunkingConfig(mode=ChunkingMode.RAG))
                                context_docs.extend(rag_chunks[:2])  # Add top 2 chunks
                                print(f"📚 Added {len(rag_chunks[:2])} RAG chunks from cached document: {doc_key}")
            
            # If we have both current file and session context, enhance the answer with comprehensive context
            if file_text and context_docs:
                print(f"🔗 Combining current file content with {len(context_docs)} context sections from session...")
                # Create a comprehensive context that includes both current file and session knowledge
                comprehensive_context = []
                
                # Add current file content first (higher priority)
                if file_text:
                    comprehensive_context.append(f"📄 **Current Uploaded File Content:**\n{file_text}")
                
                # Add relevant session context
                if context_docs:
                    comprehensive_context.append(f"📚 **Relevant Session Context:**\n{chr(10).join(context_docs)}")
                
                # Update context_docs to include the comprehensive context
                context_docs = comprehensive_context
                print(f"✅ Created comprehensive context combining current file and session knowledge")
            
            if not context_docs:
                # Check if user is asking about file content but no file is attached
                if _is_asking_about_file_content(query):
                    print("📄 User is asking about file content but no file attached. Checking session cache...")
                    if storage_paths:
                        cached_docs = get_all_cached_documents_with_names(storage_paths)
                        if cached_docs:
                            print(f"📚 Found {len(cached_docs)} cached documents in session. Using them for RAG...")
                            # Use all cached documents for comprehensive RAG
                            # Track which documents we've already processed to avoid duplicates
                            processed_docs = set()
                            
                            for doc_key, filename, chunks in cached_docs:
                                # Skip if we've already processed this document
                                if doc_key in processed_docs:
                                    continue
                                processed_docs.add(doc_key)
                                
                                if "rag" in doc_key:
                                    context_docs.extend(chunks)
                                else:
                                    # Convert other modes to RAG chunks
                                    rag_chunks = chunk_document("\n\n".join(chunks), mode=ChunkingMode.RAG, config=ChunkingConfig(mode=ChunkingMode.RAG))
                                    context_docs.extend(rag_chunks)
                            print(f"✅ Created RAG context from {len(cached_docs)} cached documents")
                        else:
                            print("💡 No cached documents in session. Providing knowledge-based answer...")
                            guidance = (
                                "\n\n💡 **Note**: This answer is based on general knowledge. "
                                "For more specific and accurate answers, consider uploading relevant documents. "
                                "You can also ask follow-up questions about specific aspects."
                            )
                            
                            if stream:
                                def _wrap_knowledge_stream():
                                    for chunk in self._qa(query, [], stream=True, history=recent_history):
                                        yield chunk
                                    yield guidance
                                return _wrap_knowledge_stream()
                            else:
                                answer = self._qa(query, [], stream=False, history=recent_history)
                                return answer + guidance
                    else:
                        print("💡 No storage paths available. Providing knowledge-based answer...")
                        guidance = (
                            "\n\n💡 **Note**: This answer is based on general knowledge. "
                            "For more specific and accurate answers, consider uploading relevant documents. "
                            "You can also ask follow-up questions about specific aspects."
                        )
                        
                        if stream:
                            def _wrap_knowledge_stream():
                                for chunk in self._qa(query, [], stream=True, history=recent_history):
                                    yield chunk
                                yield guidance
                            return _wrap_knowledge_stream()
                        else:
                            answer = self._qa(query, [], stream=False, history=recent_history)
                            return answer + guidance
                else:
                    print("💡 No document context available. Providing knowledge-based answer...")
                    guidance = (
                        "\n\n💡 **Note**: This answer is based on general knowledge. "
                        "For more specific and accurate answers, consider uploading relevant documents. "
                        "You can also ask follow-up questions about specific aspects."
                    )
                    
                    if stream:
                        def _wrap_knowledge_stream():
                            for chunk in self._qa(query, [], stream=True, history=recent_history):
                                yield chunk
                            yield guidance
                        return _wrap_knowledge_stream()
                    else:
                        answer = self._qa(query, [], stream=False, history=recent_history)
                        return answer + guidance
            # Ask the model to answer using the retrieved context
            if stream:
                print("🔄 Streaming answer...")
            stream_iter = self._qa(query, context_docs, stream=stream, history=recent_history)
            if storage_paths:

                def _wrap_stream_and_persist():
                    buffer_parts: List[str] = []
                    for chunk in stream_iter:
                        buffer_parts.append(chunk)
                        yield chunk
                    full_answer = "".join(buffer_parts)
                    append_chat_message(storage_paths, role="assistant", content=full_answer)
                    print("✅ Streaming completed")

                return _wrap_stream_and_persist()
            else:
                return stream_iter


def _should_use_rag_instead_of_analysis(query: str) -> bool:
    """Determine if a query should use RAG instead of analysis mode.
    
    This function identifies queries that are asking for explanations or information
    based on file content, which are better handled by RAG than pure analysis.
    """
    query_lower = query.lower()
    
    # Chinese patterns that indicate explanation requests
    explanation_patterns = [
        "解释", "解释一下", "解释这个", "说明", "说明一下", "说明这个",
        "结合", "结合这个", "结合文件", "结合文档", "综合", "综合这个",
        "再解释", "再说明", "再阐述"
    ]
    
    # Check if the query contains explanation patterns
    if any(pattern in query for pattern in explanation_patterns):
        return True
    
    # English patterns that indicate explanation requests
    english_explanation_patterns = [
        "explain", "explanation", "tell me about", "what is", "what are",
        "how does", "why is", "describe", "elaborate", "clarify"
    ]
    
    if any(pattern in query_lower for pattern in english_explanation_patterns):
        return True
    
    return False


def _is_asking_about_file_content(query: str) -> bool:
    """Determine if a user is asking about file content even when no file is attached.
    
    This function identifies queries that are requesting information that should come
    from documents, indicating the user expects file-based answers.
    """
    query_lower = query.lower()
    
    # Chinese patterns that indicate file content requests
    chinese_file_patterns = [
        "根据", "根据文件", "根据文档", "根据信息", "基于", "基于文件", "基于文档",
        "文件信息", "文档信息", "文档中", "文件中", "资料中", "内容中"
    ]
    
    # English patterns that indicate file content requests
    english_file_patterns = [
        "based on", "according to", "from the", "in the", "document", "file",
        "information", "content", "data", "text"
    ]
    
    # Check for Chinese patterns
    if any(pattern in query for pattern in chinese_file_patterns):
        return True
    
    # Check for English patterns
    if any(pattern in query_lower for pattern in english_file_patterns):
        return True
    
    return False

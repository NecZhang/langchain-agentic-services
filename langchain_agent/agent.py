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

# Configuration constants
DEFAULT_REQUEST_TIMEOUT = int(os.environ.get("AGENTIC_REQUEST_TIMEOUT", "30"))

from .file_parser import parse_file
from .intent_recognizer import detect_intent
from .rag_utils import RAGRetriever
from .enhanced_chunking import chunk_document, ChunkingMode, ChunkingConfig, get_file_type
from .storage import (
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
)
from .language_utils import (
    detect_language,
    get_system_prompt,
    get_processing_message,
)

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
        """Stream the response from the LLM."""
        response = requests.post(url, headers=headers, data=json.dumps(payload), stream=True, timeout=DEFAULT_REQUEST_TIMEOUT)
        try:
            response.raise_for_status()
        except Exception:
            # propagate the error with more context
            raise RuntimeError(f"LLM request failed with status {response.status_code}: {response.text}")

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == "[DONE]":
                        break
                    try:
                        json_data = json.loads(data)
                        choices = json_data.get("choices") or []
                        if choices and choices[0].get("delta", {}).get("content"):
                            yield choices[0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue

    # -----------------------------------------------------------------
    # High level tasks
    #
    def _translate(
        self, text: str, target_language: str = "Chinese", stream: bool = False, detected_language: str = "Chinese"
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
        # Use bilingual system prompt based on detected language
        if detected_language == "Chinese":
            system_prompt = f"你是一个专业的翻译专家。请将以下文本翻译成{target_language}。保持原有的格式和结构。"
            user_content = f"请翻译以下文本：\n\n{text}"
        else:
            system_prompt = (
                f"You are a professional translator. Translate the following text to "
                f"{target_language}. Preserve the meaning and formatting where possible."
            )
            user_content = text

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
            file_text = parse_file(file_path)
            print(get_processing_message("parsed", detected_language, chars=len(file_text)))
            file_ext = get_file_type(file_path)

        # Determine intent from the query
        intent = detect_intent(query)
        if intent == "translate":
            if not file_text:
                raise ValueError("Translation tasks require an attached file with content.")

            # Get file extension for file-type aware chunking

            # Create translation-optimized chunking config
            translation_config = ChunkingConfig(
                mode=ChunkingMode.TRANSLATION,
                max_chars=self.max_context_tokens * 4,  # Large chunks for translation
                overlap=200,
                respect_sentences=True,
                respect_paragraphs=True,
            )

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

            if stream:
                # For streaming, we need to handle chunked translation differently
                # Since we can't easily stream multiple chunks, we'll concatenate and stream
                # the entire translation as one response
                print("🔄 Streaming translation...")
                all_text = "\n\n".join(chunks)
                return self._translate(all_text, target_language=target_language, stream=True)
            else:
                translations = []
                for chunk in tqdm(chunks, desc="Translating chunks"):
                    translations.append(self._translate(chunk, target_language=target_language))
                return "\n".join(translations)
        elif intent == "summarize":
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
            return self._analyze(all_text, stream=stream)

        elif intent == "extract":
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

            # Add current file if provided
            if file_text:
                texts.append(file_text)

            # Add all cached documents from the session
            if storage_paths:
                cached_docs = get_all_cached_documents(storage_paths)
                for doc_key, chunks in cached_docs:
                    cached_text = "\n\n".join(chunks)
                    texts.append(cached_text)

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
            elif storage_paths:
                # No file this time; try to reuse last document for this session
                key = get_last_doc_key(storage_paths)
                if key:
                    print(f"♻️  Reusing last document cache: {key}")
                    cached_chunks = load_chunks(storage_paths, key)
                    if cached_chunks:
                        docs = cached_chunks
                        retriever_loaded = load_retriever(storage_paths, key)
                        if retriever_loaded:
                            vectorizer, doc_vectors, nn = retriever_loaded
                            retriever = RAGRetriever(docs, vectorizer=vectorizer, doc_vectors=doc_vectors, nn=nn)
                        else:
                            retriever = RAGRetriever(docs)
                        results = retriever.query(query, k=3)
                        for idx, dist in results:
                            context_docs.append(docs[idx])
                        print(f"✅ Reused {len(context_docs)} context sections from cache")
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

                return _wrap_stream_and_persist()
            else:
                return stream_iter

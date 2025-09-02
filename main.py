"""Command line interface for the simple LLM agent.

This script provides a minimal wrapper around :class:`simple_agent.agent.SimpleAgent`
for demonstration purposes.  It allows you to pass a query and an
optional file via command line arguments and prints the agent's
response to standard output.  See the README for usage examples.
"""

from __future__ import annotations

import argparse
import os
from simple_agent.agent import SimpleAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the simple LLM agent.")
    parser.add_argument(
        "query",
        type=str,
        help="The user's query.  Include keywords like 'translate' to trigger translation mode."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to an optional file to attach to the query.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=os.environ.get("VLLM_ENDPOINT", "http://localhost:8000"),
        help="Base URL of the vLLM server (default: http://localhost:8000 or $VLLM_ENDPOINT).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("VLLM_MODEL", "gpt-3.5-turbo"),
        help="Name of the model to use on the vLLM server (default: gpt-3.5-turbo or $VLLM_MODEL).",
    )
    parser.add_argument(
        "--target-language",
        type=str,
        default="Chinese",
        help="Target language for translation tasks (default: Chinese).",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming output (responses will be printed as they arrive).",
    )
    parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="User identifier to enable per-user storage (uploads, caches, chat history).",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session identifier to group chat messages and caches.",
    )
    args = parser.parse_args()

    agent = SimpleAgent(llm_endpoint=args.endpoint, model=args.model)
    response = agent.run(
        query=args.query,
        file_path=args.file,
        target_language=args.target_language,
        stream=args.stream,
        user_id=args.user,
        session_id=args.session,
    )
    
    if args.stream:
        # Handle streaming response
        for chunk in response:
            print(chunk, end="", flush=True)
        print()  # New line at the end
    else:
        # Handle non-streaming response
        print(response)


if __name__ == "__main__":
    main()
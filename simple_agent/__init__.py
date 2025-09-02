"""Top-level package for the simple agent.

This package provides a minimal implementation of an agent that can
interact with a local language model server, parse various file types
into text, detect user intent (e.g., translation versus question
answering), and perform a rudimentary retrieval‑augmented generation
task.  It does not depend on the upstream ``langchain`` library and
works within environments without internet access or external Python
packages.  You can import :class:`simple_agent.agent.SimpleAgent`
to construct and run the agent in your own application.
"""

from .agent import SimpleAgent  # noqa: F401

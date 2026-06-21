"""
CHAREDIT - A Python library for highlighting character dialogue in text.

This library provides core functionality for:
- Character dialogue detection and highlighting
- Character color management
- Text pagination
- Story structure management
"""

from .core import DialogueHighlighter, CharacterManager, TextPaginator
from .models import Character, StoryStructure

__version__ = "1.0.0"
__all__ = [
    "DialogueHighlighter",
    "CharacterManager", 
    "TextPaginator",
    "Character",
    "StoryStructure"
]

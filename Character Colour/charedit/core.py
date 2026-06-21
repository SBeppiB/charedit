"""
Core functionality for the Dialogue Colorizer library.

This module provides the main logic for dialogue highlighting, character management,
and text pagination without GUI dependencies.
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from .models import Character, StoryStructure


class DialogueHighlighter:
    """Core dialogue detection and highlighting logic."""
    
    def __init__(self):
        self.character_data: Dict[str, Dict] = {}
        self.prefix_regex = re.compile(r'^([^:]+):')
        self.quote_regex = re.compile(r'["""][^""\\]*(?:\\.[^""\\]*)*["""]')
    
    def set_characters(self, characters: Dict[str, Dict]):
        """Set character data for highlighting."""
        self.character_data = characters
    
    def detect_character(self, text: str) -> Optional[str]:
        """Detect which character is speaking in a line of text."""
        prefix_match = self.prefix_regex.match(text)
        if prefix_match:
            detected_name = prefix_match.group(1).strip()
            
            for main_name, attributes in self.character_data.items():
                if detected_name == main_name or detected_name in attributes.get("aliases", []):
                    return attributes.get("color")
        return None
    
    def find_dialogue_lines(self, text: str) -> List[Tuple[int, str, Optional[str]]]:
        """Find all dialogue lines with their character colors."""
        lines = text.split('\n')
        results = []
        
        for idx, line in enumerate(lines):
            color = self.detect_character(line)
            if color:
                results.append((idx, line, color))
        
        return results
    
    def apply_highlighting(self, text: str) -> str:
        """Apply HTML highlighting to dialogue lines."""
        lines = text.split('\n')
        highlighted_lines = []
        
        for line in lines:
            color = self.detect_character(line)
            if color:
                # Wrap character name and quotes in colored spans
                prefix_match = self.prefix_regex.match(line)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    prefix_end = prefix_match.end()
                    highlighted = f'<span style="color:{color}">{prefix}</span>{line[prefix_end:]}'
                    highlighted_lines.append(highlighted)
                else:
                    highlighted_lines.append(line)
            else:
                highlighted_lines.append(line)
        
        return '\n'.join(highlighted_lines)


class CharacterManager:
    """Manages character data and persistence."""
    
    def __init__(self, library_path: str = "characters.json"):
        self.library_path = library_path
        self.characters: Dict[str, Character] = {}
        self.load()
    
    def add_character(self, name: str, color: str = "#FFFFFF", aliases: List[str] = None) -> Character:
        """Add a new character."""
        if aliases is None:
            aliases = []
        
        if ":" in name:
            raise ValueError("Character names cannot contain colons")
        
        character = Character(name=name, color=color, aliases=aliases)
        self.characters[name] = character
        self.save()
        return character
    
    def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name."""
        return self.characters.get(name)
    
    def remove_character(self, name: str) -> bool:
        """Remove a character."""
        if name in self.characters:
            del self.characters[name]
            self.save()
            return True
        return False
    
    def update_character(self, name: str, color: str = None, aliases: List[str] = None) -> bool:
        """Update an existing character."""
        if name not in self.characters:
            return False
        
        character = self.characters[name]
        if color is not None:
            character.color = color
        if aliases is not None:
            character.aliases = aliases
        
        self.save()
        return True
    
    def get_all_characters(self) -> Dict[str, Character]:
        """Get all characters."""
        return self.characters
    
    def to_highlighter_dict(self) -> Dict[str, Dict]:
        """Convert character data to format expected by highlighter."""
        return {
            name: {
                "color": char.color,
                "aliases": char.aliases
            }
            for name, char in self.characters.items()
        }
    
    def save(self):
        """Save character data to file."""
        try:
            data = {name: char.to_dict() for name, char in self.characters.items()}
            with open(self.library_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            raise IOError(f"Failed to save character data: {e}")
    
    def load(self):
        """Load character data from file."""
        try:
            with open(self.library_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.characters = {
                name: Character.from_dict(char_data)
                for name, char_data in data.items()
            }
        except (IOError, json.JSONDecodeError):
            self.characters = {}


class TextPaginator:
    """Handles text pagination with configurable words per page."""
    
    def __init__(self, words_per_page: int = 600):
        self.words_per_page = words_per_page
    
    def paginate(self, text: str, add_spacing: bool = True) -> Tuple[str, int]:
        """
        Paginate text and return paginated text with page count.
        
        Args:
            text: The text to paginate
            add_spacing: Whether to add spacing between dialogue lines
            
        Returns:
            Tuple of (paginated_text, total_pages)
        """
        lines = text.split('\n')
        
        # Remove existing page markers
        cleaned_lines = [
            line for line in lines
            if not re.match(r'^--- PAGE \d+ ---$', line)
        ]
        
        # Add spacing between dialogue lines if requested
        if add_spacing:
            spaced_lines = self._add_dialogue_spacing(cleaned_lines)
        else:
            spaced_lines = cleaned_lines
        
        # Remove consecutive empty lines
        final_lines = self._remove_consecutive_empty(spaced_lines)
        
        # Add page markers
        paginated_lines = []
        word_counter = 0
        page_number = 1
        
        for line in final_lines:
            line_words = len(re.findall(r'\b\w+\b', line))
            if word_counter + line_words > self.words_per_page:
                paginated_lines.append(f"--- PAGE {page_number} ---")
                page_number += 1
                word_counter = line_words
            else:
                word_counter += line_words
            paginated_lines.append(line)
        
        paginated_text = '\n'.join(paginated_lines)
        return paginated_text, page_number
    
    def _add_dialogue_spacing(self, lines: List[str]) -> List[str]:
        """Add blank lines between dialogue lines."""
        spaced_lines = []
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            is_dialogue = (stripped and ':' in stripped and not stripped.startswith('#'))
            
            if is_dialogue and len(spaced_lines) > 0:
                if spaced_lines[-1].strip() != "":
                    spaced_lines.append("")
            
            spaced_lines.append(line)
            
            if is_dialogue:
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    if next_line:
                        is_next_dialogue = (':' in next_line and not next_line.startswith('#'))
                        if not is_next_dialogue:
                            spaced_lines.append("")
        
        return spaced_lines
    
    def _remove_consecutive_empty(self, lines: List[str]) -> List[str]:
        """Remove consecutive empty lines."""
        final_lines = []
        for line in lines:
            if len(final_lines) > 0 and final_lines[-1] == "" and line == "":
                continue
            final_lines.append(line)
        return final_lines
    
    def parse_pages(self, text: str) -> List[Tuple[int, str]]:
        """
        Parse paginated text into individual pages.
        
        Returns:
            List of tuples (page_number, page_content)
        """
        pages = []
        lines = text.split('\n')
        current_page_lines = []
        current_page_num = 1
        
        for line in lines:
            page_match = re.match(r'^--- PAGE (\d+) ---$', line)
            if page_match:
                if current_page_lines:
                    pages.append((current_page_num, '\n'.join(current_page_lines)))
                current_page_num = int(page_match.group(1))
                current_page_lines = []
            else:
                current_page_lines.append(line)
        
        if current_page_lines:
            pages.append((current_page_num, '\n'.join(current_page_lines)))
        
        return pages
    
    def get_page(self, text: str, page_number: int) -> Optional[str]:
        """Get a specific page from paginated text."""
        pages = self.parse_pages(text)
        for page_num, content in pages:
            if page_num == page_number:
                return content
        return None
    
    def get_page_count(self, text: str) -> int:
        """Get the total number of pages in paginated text."""
        pages = self.parse_pages(text)
        return len(pages)


class StoryManager:
    """Manages story structure (arcs and chapters)."""
    
    def __init__(self, structure_path: str = "story_structure.json"):
        self.structure_path = structure_path
        self.story_structure = StoryStructure()
        self.trash_bin: List[Dict] = []
        self.load()
    
    def add_arc(self, arc_name: str) -> Arc:
        """Add a new narrative arc."""
        return self.story_structure.add_arc(arc_name)
    
    def add_chapter(self, arc_index: int, chapter_name: str, color: str = None) -> Chapter:
        """Add a new chapter to an arc."""
        return self.story_structure.add_chapter(arc_index, chapter_name, color)
    
    def remove_arc(self, arc_index: int) -> bool:
        """Remove an arc and move it to trash."""
        if 0 <= arc_index < len(self.story_structure.arcs):
            arc = self.story_structure.arcs.pop(arc_index)
            self.trash_bin.append(arc.to_dict())
            self.save()
            return True
        return False
    
    def remove_chapter(self, arc_index: int, chapter_index: int) -> bool:
        """Remove a chapter and move it to trash."""
        if 0 <= arc_index < len(self.story_structure.arcs):
            arc = self.story_structure.arcs[arc_index]
            if 0 <= chapter_index < len(arc.chapters):
                chapter = arc.chapters.pop(chapter_index)
                self.trash_bin.append({
                    "name": chapter.name,
                    "color": chapter.color,
                    "parent_arc_name": arc.arc_name
                })
                self.save()
                return True
        return False
    
    def get_structure(self) -> StoryStructure:
        """Get the current story structure."""
        return self.story_structure
    
    def save(self):
        """Save story structure to file."""
        try:
            with open(self.structure_path, "w", encoding="utf-8") as f:
                json.dump(self.story_structure.to_dict(), f, indent=4)
        except IOError as e:
            raise IOError(f"Failed to save story structure: {e}")
    
    def load(self):
        """Load story structure from file."""
        try:
            with open(self.structure_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.story_structure = StoryStructure.from_dict(data)
        except (IOError, json.JSONDecodeError):
            self.story_structure = StoryStructure()

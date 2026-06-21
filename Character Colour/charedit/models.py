"""
Data models for the Dialogue Colorizer library.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class Character:
    """Represents a character with color and aliases."""
    name: str
    color: str = "#FFFFFF"
    aliases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert character to dictionary."""
        return {
            "name": self.name,
            "color": self.color,
            "aliases": self.aliases
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        """Create character from dictionary."""
        return cls(
            name=data.get("name", ""),
            color=data.get("color", "#FFFFFF"),
            aliases=data.get("aliases", [])
        )


@dataclass
class Chapter:
    """Represents a chapter in the story structure."""
    name: str
    color: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert chapter to dictionary."""
        return {
            "name": self.name,
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Chapter':
        """Create chapter from dictionary."""
        return cls(
            name=data.get("name", ""),
            color=data.get("color")
        )


@dataclass
class Arc:
    """Represents a narrative arc containing chapters."""
    arc_name: str
    chapters: List[Chapter] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert arc to dictionary."""
        return {
            "arc_name": self.arc_name,
            "chapters": [ch.to_dict() for ch in self.chapters]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Arc':
        """Create arc from dictionary."""
        return cls(
            arc_name=data.get("arc_name", ""),
            chapters=[Chapter.from_dict(ch) for ch in data.get("chapters", [])]
        )


@dataclass
class StoryStructure:
    """Represents the overall story structure with arcs and chapters."""
    arcs: List[Arc] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert story structure to dictionary."""
        return [arc.to_dict() for arc in self.arcs]
    
    @classmethod
    def from_dict(cls, data: List[Dict]) -> 'StoryStructure':
        """Create story structure from dictionary."""
        return cls(
            arcs=[Arc.from_dict(arc) for arc in data]
        )
    
    def add_arc(self, arc_name: str) -> Arc:
        """Add a new arc to the story structure."""
        arc = Arc(arc_name=arc_name)
        self.arcs.append(arc)
        return arc
    
    def add_chapter(self, arc_index: int, chapter_name: str, color: str = None) -> Chapter:
        """Add a new chapter to an arc."""
        if 0 <= arc_index < len(self.arcs):
            chapter = Chapter(name=chapter_name, color=color)
            self.arcs[arc_index].chapters.append(chapter)
            return chapter
        raise IndexError("Arc index out of range")

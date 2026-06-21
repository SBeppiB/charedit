# CHAREDIT

A Python library for highlighting character dialogue in text with support for character management, text pagination, and story structure organization.

## Features

- **Dialogue Detection**: Automatically detect character dialogue lines
- **Character Management**: Manage characters with custom colors and aliases
- **Text Highlighting**: Apply color highlighting to dialogue
- **Text Pagination**: Split text into pages with configurable word count
- **Story Structure**: Organize content into arcs and chapters
- **GUI Support**: Optional PyQt6 integration for visual editing

## Installation

### Core Library (No GUI dependencies)

```bash
pip install charedit
```

### With GUI Support

```bash
pip install charedit[gui]
```

### Development Installation

```bash
pip install charedit[dev]
```

## Quick Start

### Basic Dialogue Highlighting

```python
from charedit import DialogueHighlighter

# Create highlighter
highlighter = DialogueHighlighter()

# Set character colors
highlighter.set_characters({
    "Hero": {"color": "#FF0000", "aliases": ["Protagonist", "Main"]},
    "Villain": {"color": "#0000FF", "aliases": ["Antagonist"]}
})

# Detect character in dialogue
text = "Hero: Hello world!"
color = highlighter.detect_character(text)
print(color)  # "#FF0000"

# Apply HTML highlighting
highlighted = highlighter.apply_highlighting(text)
print(highlighted)  # '<span style="color:#FF0000">Hero</span>: Hello world!'
```

### Character Management

```python
from dialogue_colorizer import CharacterManager

# Create manager with custom file path
manager = CharacterManager("my_characters.json")

# Add characters
manager.add_character("Alice", color="#FF5733", aliases=["Al", "Chief"])
manager.add_character("Bob", color="#33FF57")

# Get character
alice = manager.get_character("Alice")
print(alice.color)  # "#FF5733"

# Update character
manager.update_character("Alice", color="#FF0000")

# Remove character
manager.remove_character("Bob")

# Get all characters
all_chars = manager.get_all_characters()
```

### Text Pagination

```python
from dialogue_colorizer import TextPaginator

# Create paginator with custom words per page
paginator = TextPaginator(words_per_page=500)

# Paginate text
text = "Your long text here..."
paginated_text, page_count = paginator.paginate(text, add_spacing=True)
print(f"Total pages: {page_count}")

# Parse pages into individual pages
pages = paginator.parse_pages(paginated_text)
for page_num, content in pages:
    print(f"Page {page_num}: {len(content)} characters")

# Get specific page
page_1 = paginator.get_page(paginated_text, 1)
```

### Story Structure Management

```python
from dialogue_colorizer import StoryManager

# Create story manager
story = StoryManager("my_story.json")

# Add arcs
arc1 = story.add_arc("Act 1: The Beginning")
arc2 = story.add_arc("Act 2: The Conflict")

# Add chapters
story.add_chapter(0, "Chapter 1: Introduction", color="#FF0000")
story.add_chapter(0, "Chapter 2: The Journey")
story.add_chapter(1, "Chapter 3: The Climax")

# Get structure
structure = story.get_structure()
for arc in structure.arcs:
    print(f"Arc: {arc.arc_name}")
    for chapter in arc.chapters:
        print(f"  Chapter: {chapter.name}")
```

### Complete Workflow Example

```python
from dialogue_colorizer import DialogueHighlighter, CharacterManager, TextPaginator

# Setup character management
char_manager = CharacterManager()
char_manager.add_character("John", color="#FF0000")
char_manager.add_character("Jane", color="#0000FF")

# Setup dialogue highlighting
highlighter = DialogueHighlighter()
highlighter.set_characters(char_manager.to_highlighter_dict())

# Process dialogue text
dialogue = """
John: Hello Jane!
Jane: Hi John, how are you?
John: I'm doing great!
"""

# Find all dialogue lines
dialogue_lines = highlighter.find_dialogue_lines(dialogue)
for line_num, text, color in dialogue_lines:
    print(f"Line {line_num}: {text} (Color: {color})")

# Paginate the dialogue
paginator = TextPaginator(words_per_page=100)
paginated, pages = paginator.paginate(dialogue, add_spacing=True)
print(f"Paginated into {pages} pages")
```

## Library Structure

```
dialogue_colorizer/
├── __init__.py          # Package initialization
├── core.py              # Core functionality (highlighting, pagination, etc.)
├── models.py            # Data models (Character, Chapter, Arc, etc.)
└── gui.py               # Optional PyQt6 GUI components
```

## API Reference

### DialogueHighlighter

Main class for dialogue detection and highlighting.

- `set_characters(characters: Dict)` - Set character data
- `detect_character(text: str) -> Optional[str]` - Detect character color in text
- `find_dialogue_lines(text: str) -> List[Tuple]` - Find all dialogue lines
- `apply_highlighting(text: str) -> str` - Apply HTML highlighting

### CharacterManager

Manage character data with persistence.

- `add_character(name, color, aliases)` - Add new character
- `get_character(name) -> Character` - Get character by name
- `remove_character(name) -> bool` - Remove character
- `update_character(name, color, aliases) -> bool` - Update character
- `get_all_characters() -> Dict` - Get all characters
- `to_highlighter_dict() -> Dict` - Convert for highlighter use
- `save()` - Save to file
- `load()` - Load from file

### TextPaginator

Handle text pagination with configurable word count.

- `paginate(text, add_spacing) -> Tuple[str, int]` - Paginate text
- `parse_pages(text) -> List[Tuple]` - Parse into individual pages
- `get_page(text, page_number) -> Optional[str]` - Get specific page
- `get_page_count(text) -> int` - Get total page count

### StoryManager

Manage story structure (arcs and chapters).

- `add_arc(arc_name) -> Arc` - Add narrative arc
- `add_chapter(arc_index, chapter_name, color) -> Chapter` - Add chapter
- `remove_arc(arc_index) -> bool` - Remove arc
- `remove_chapter(arc_index, chapter_index) -> bool` - Remove chapter
- `get_structure() -> StoryStructure` - Get current structure
- `save()` - Save to file
- `load()` - Load from file

## GUI Integration

For PyQt6 GUI integration, install with the gui extra:

```bash
pip install dialogue-colorizer[gui]
```

Then use the GUI components:

```python
from dialogue_colorizer.gui import ColorEditorApp
import sys
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
editor = ColorEditorApp()
editor.show()
sys.exit(app.exec())
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

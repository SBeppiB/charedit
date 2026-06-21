"""
Example usage of the CHAREDIT library.
"""

from charedit import DialogueHighlighter, CharacterManager, TextPaginator, StoryManager


def example_basic_highlighting():
    """Basic dialogue highlighting example."""
    print("=== Basic Dialogue Highlighting ===")
    
    highlighter = DialogueHighlighter()
    
    # Set character colors
    highlighter.set_characters({
        "Hero": {"color": "#FF0000", "aliases": ["Protagonist"]},
        "Villain": {"color": "#0000FF", "aliases": ["Antagonist"]}
    })
    
    # Test dialogue
    dialogue = """
Hero: Hello world!
Villain: I will defeat you!
Protagonist: Never!
"""
    
    # Find dialogue lines
    lines = highlighter.find_dialogue_lines(dialogue)
    for line_num, text, color in lines:
        print(f"Line {line_num}: {text.strip()} -> Color: {color}")
    
    # Apply highlighting
    highlighted = highlighter.apply_highlighting(dialogue)
    print(f"\nHighlighted text:\n{highlighted}")


def example_character_management():
    """Character management example."""
    print("\n=== Character Management ===")
    
    manager = CharacterManager("example_characters.json")
    
    # Add characters
    manager.add_character("Alice", color="#FF5733", aliases=["Al", "Chief"])
    manager.add_character("Bob", color="#33FF57")
    manager.add_character("Charlie", color="#3357FF")
    
    # Get and display characters
    all_chars = manager.get_all_characters()
    for name, char in all_chars.items():
        print(f"{name}: {char.color} (Aliases: {', '.join(char.aliases)})")
    
    # Update a character
    manager.update_character("Alice", color="#FF0000")
    
    # Convert for highlighter use
    highlighter_dict = manager.to_highlighter_dict()
    print(f"\nHighlighter dict: {highlighter_dict}")


def example_pagination():
    """Text pagination example."""
    print("\n=== Text Pagination ===")
    
    paginator = TextPaginator(words_per_page=50)
    
    # Sample text
    text = """
This is a sample text that will be paginated. 
It contains multiple lines of dialogue and prose.
Hero: This is the first line of dialogue.
Villain: This is the second line of dialogue.
The story continues with more narrative text.
Hero: Another dialogue line here.
More prose to fill up the pages.
"""
    
    # Paginate
    paginated, page_count = paginator.paginate(text, add_spacing=True)
    print(f"Paginated into {page_count} pages")
    print(f"\nPaginated text:\n{paginated}")
    
    # Parse pages
    pages = paginator.parse_pages(paginated)
    for page_num, content in pages:
        print(f"\n--- Page {page_num} ---")
        print(content)


def example_story_structure():
    """Story structure management example."""
    print("\n=== Story Structure ===")
    
    story = StoryManager("example_story.json")
    
    # Add arcs
    story.add_arc("Act 1: The Beginning")
    story.add_arc("Act 2: The Conflict")
    story.add_arc("Act 3: The Resolution")
    
    # Add chapters
    story.add_chapter(0, "Chapter 1: Introduction", color="#FF0000")
    story.add_chapter(0, "Chapter 2: The Journey")
    story.add_chapter(1, "Chapter 3: The Climax")
    story.add_chapter(2, "Chapter 4: Conclusion")
    
    # Display structure
    structure = story.get_structure()
    for arc in structure.arcs:
        print(f"Arc: {arc.arc_name}")
        for chapter in arc.chapters:
            print(f"  Chapter: {chapter.name} (Color: {chapter.color})")


def example_complete_workflow():
    """Complete workflow example."""
    print("\n=== Complete Workflow ===")
    
    # Setup character management
    char_manager = CharacterManager("workflow_characters.json")
    char_manager.add_character("John", color="#FF0000")
    char_manager.add_character("Jane", color="#0000FF")
    
    # Setup dialogue highlighting
    highlighter = DialogueHighlighter()
    highlighter.set_characters(char_manager.to_highlighter_dict())
    
    # Process dialogue
    dialogue = """
John: Hello Jane!
Jane: Hi John, how are you?
John: I'm doing great, thanks for asking.
Jane: That's wonderful to hear.
"""
    
    # Find dialogue lines
    dialogue_lines = highlighter.find_dialogue_lines(dialogue)
    print(f"Found {len(dialogue_lines)} dialogue lines")
    
    # Paginate
    paginator = TextPaginator(words_per_page=30)
    paginated, pages = paginator.paginate(dialogue, add_spacing=True)
    print(f"Paginated into {pages} pages")
    
    # Display pages
    for page_num, content in paginator.parse_pages(paginated):
        print(f"\n--- Page {page_num} ---")
        print(content)


if __name__ == "__main__":
    example_basic_highlighting()
    example_character_management()
    example_pagination()
    example_story_structure()
    example_complete_workflow()
    
    print("\n=== Examples Complete ===")
    print("Check the generated JSON files: example_characters.json, example_story.json, workflow_characters.json")

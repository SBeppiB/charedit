import sys
import json
import re
import csv
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QFileDialog, 
                             QMenu, QVBoxLayout, QHBoxLayout, QWidget, QColorDialog, 
                             QDialog, QLabel, QLineEdit, QPushButton, QListWidget, 
                             QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QAbstractItemView)
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QAction, QTextCursor, QKeySequence
from PyQt6.QtCore import Qt, QTimer

VERSION = "1.0.7"
CONFIG_FILE = "config.json"
DEFAULT_LIBRARY = "CHARACTER.json"
DEFAULT_SCRIPT_FILE = "current_script.md"
STRUCTURE_FILE = "story_structure.json"
TRASH_FILE = "trash_bin.json"

class AdvancedDialogueHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.character_data = {}  
        self.manual_overrides = {} 
        
        self.prefix_regex = re.compile(r'^([^:]+):')
        self.quote_regex = re.compile(r'["“][^"”\\]*(?:\\.[^"”\\]*)*["”]')
        
        self.md_rules = [
            (re.compile(r'^# .+$'), self.get_md_format("#00E5FF", bold=True, size=16)),     
            (re.compile(r'^## .+$'), self.get_md_format("#00B0FF", bold=True, size=14)),    
            (re.compile(r'^### .+$'), self.get_md_format("#40C4FF", bold=True, size=13)),   
            (re.compile(r'\*\*([^*]+)\*\*'), self.get_md_format(None, bold=True)),          
            (re.compile(r'\*([^*]+)\*'), self.get_md_format(None, italic=True)),            
            (re.compile(r'^--- PAGE \d+ ---$'), self.get_md_format("#FFB300", bold=True)),  
        ]

    def get_md_format(self, hex_color=None, bold=False, italic=False, size=None):
        fmt = QTextCharFormat()
        if hex_color:
            fmt.setForeground(QColor(hex_color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        if size:
            fmt.setFontPointSize(size)
        return fmt

    def set_colors(self, data_dict):
        self.character_data = data_dict
        self.rehighlight()

    def add_manual_override(self, block_index, start, length, hex_color):
        if block_index not in self.manual_overrides:
            self.manual_overrides[block_index] = []
        self.manual_overrides[block_index].append((start, length, hex_color))
        self.rehighlight()

    def highlightBlock(self, text):
        block_idx = self.currentBlock().blockNumber()
        cleaned_text = text.strip()

        if not cleaned_text:
            self.setCurrentBlockState(-1)
            return

        prefix_match = self.prefix_regex.match(text)
        target_color = None
        prefix_length = 0

        if prefix_match:
            detected_name = prefix_match.group(1).strip()
            prefix_length = prefix_match.end()

            for main_name, attributes in self.character_data.items():
                if detected_name == main_name or detected_name in attributes.get("aliases", []):
                    target_color = attributes.get("color")
                    break

            if target_color:
                state_id = abs(hash(target_color)) & 0x7FFFFFFF
                self.setCurrentBlockState(state_id)
            else:
                self.setCurrentBlockState(-1)
        else:
            prev_state = self.previousBlockState()
            if prev_state > 0 and (cleaned_text.startswith('"') or cleaned_text.startswith('“')):
                for main_name, attributes in self.character_data.items():
                    c = attributes.get("color")
                    if c and (abs(hash(c)) & 0x7FFFFFFF) == prev_state:
                        target_color = c
                        self.setCurrentBlockState(prev_state)  
                        break
            else:
                self.setCurrentBlockState(-1)

        if target_color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(target_color))
            if prefix_length > 0:
                self.setFormat(0, prefix_length, fmt)

            has_quotes = False
            for quote_match in self.quote_regex.finditer(text):
                has_quotes = True
                start, end = quote_match.span()
                self.setFormat(start, end - start, fmt)

            if not has_quotes and prefix_length == 0 and (cleaned_text.startswith('"') or cleaned_text.startswith('“')):
                self.setFormat(0, len(text), fmt)

        for regex, fmt in self.md_rules:
            for match in regex.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

        if block_idx in self.manual_overrides:
            for start, length, hex_color in self.manual_overrides[block_idx]:
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(hex_color))
                self.setFormat(start, length, fmt)


class CharacterManagerDialog(QDialog):
    def __init__(self, parent=None, character_data=None, library_path=DEFAULT_LIBRARY):
        super().__init__(parent)
        self.setWindowTitle("Manage Characters & Subnames")
        self.setMinimumSize(500, 450)
        self.character_data = character_data if character_data is not None else {}
        self.library_path = library_path
        self.selected_color = QColor("#ffffff")
        self.editing_character_name = None 
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Existing Characters & Subnames:"))
        self.char_list = QListWidget()
        self.refresh_list()
        self.char_list.itemSelectionChanged.connect(self.load_selected_character)
        left_layout.addWidget(self.char_list)
        
        self.btn_delete = QPushButton("🗑️ Delete Character")
        self.btn_delete.clicked.connect(self.delete_character)
        left_layout.addWidget(self.btn_delete)
        main_layout.addLayout(left_layout, stretch=2)

        right_layout = QVBoxLayout()
        self.form_label = QLabel("Create Character:")
        right_layout.addWidget(self.form_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Primary Name (e.g., Hero #1)...")
        right_layout.addWidget(self.name_input)

        self.aliases_input = QLineEdit()
        self.aliases_input.setPlaceholderText("Subnames/Aliases (comma-separated)...")
        right_layout.addWidget(self.aliases_input)

        self.color_preview = QLabel("Color Preview")
        self.color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_preview()
        right_layout.addWidget(self.color_preview)

        self.btn_pick_color = QPushButton("🎨 Choose Color...")
        self.btn_pick_color.clicked.connect(self.pick_color)
        right_layout.addWidget(self.btn_pick_color)

        self.btn_clear = QPushButton("❌ Clear / New Character")
        self.btn_clear.clicked.connect(self.reset_form)
        self.btn_clear.hide()
        right_layout.addWidget(self.btn_clear)
        right_layout.addStretch()

        self.btn_save = QPushButton("✅ Save Character Profile")
        self.btn_save.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white; padding: 6px;")
        self.btn_save.clicked.connect(self.save_character)
        right_layout.addWidget(self.btn_save)
        main_layout.addLayout(right_layout, stretch=3)

    def refresh_list(self):
        self.char_list.blockSignals(True)
        self.char_list.clear()
        for char, attribs in self.character_data.items():
            hex_color = attribs.get("color", "#FFFFFF")
            aliases = attribs.get("aliases", [])
            alias_str = f" [{', '.join(aliases)}]" if aliases else ""
            
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(f"{char}{alias_str} ({hex_color})")
            item.setData(Qt.ItemDataRole.UserRole, char)
            self.char_list.addItem(item)
        self.char_list.blockSignals(False)

    def load_selected_character(self):
        selected_item = self.char_list.currentItem()
        if not selected_item:
            return
        name = selected_item.data(Qt.ItemDataRole.UserRole)
        if name and name in self.character_data:
            self.editing_character_name = name
            attribs = self.character_data[name]
            self.name_input.setText(name)
            self.aliases_input.setText(", ".join(attribs.get("aliases", [])))
            self.selected_color = QColor(attribs.get("color", "#FFFFFF"))
            self.update_preview()
            self.form_label.setText("Edit Character:")
            self.btn_save.setText("🔄 Update Character Profile")
            self.btn_save.setStyleSheet("font-weight: bold; background-color: #1976d2; color: white; padding: 6px;")
            self.btn_clear.show()

    def reset_form(self):
        self.editing_character_name = None
        self.name_input.clear()
        self.aliases_input.clear()
        self.selected_color = QColor("#ffffff")
        self.update_preview()
        self.form_label.setText("Create Character:")
        self.btn_save.setText("✅ Save Character Profile")
        self.btn_save.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white; padding: 6px;")
        self.btn_clear.hide()
        self.char_list.clearSelection()

    def pick_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Select Dialogue Color")
        if color.isValid():
            self.selected_color = color
            self.update_preview()

    def update_preview(self):
        hex_name = self.selected_color.name()
        rgb = self.selected_color.getRgb()
        self.color_preview.setText(f"Hex: {hex_name}\nRGB: ({rgb[0]}, {rgb[1]}, {rgb[2]})")
        luminance = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
        text_color = "#000000" if luminance > 0.5 else "#FFFFFF"
        self.color_preview.setStyleSheet(f"background-color: {hex_name}; color: {text_color}; border: 1px solid #555; border-radius: 4px; padding: 8px;")

    def save_character(self):
        name = self.name_input.text().strip()
        if not name or ":" in name:
            QMessageBox.warning(self, "Validation Error", "Invalid name. Avoid colons (':').")
            return

        raw_aliases = self.aliases_input.text().split(",")
        aliases = [a.strip() for a in raw_aliases if a.strip() and ":" not in a]

        hex_color = self.selected_color.name()
        if self.editing_character_name and self.editing_character_name != name:
            if self.editing_character_name in self.character_data:
                del self.character_data[self.editing_character_name]

        self.character_data[name] = {"color": hex_color, "aliases": aliases}
        self.save_to_json()
        self.refresh_list()
        self.reset_form()
        if self.parent():
            self.parent().update_loaded_library(self.character_data, self.library_path)

    def delete_character(self):
        selected_item = self.char_list.currentItem()
        if not selected_item:
            return
        name = selected_item.data(Qt.ItemDataRole.UserRole)
        if name and name in self.character_data:
            del self.character_data[name]
            self.save_to_json()
            self.refresh_list()
            self.reset_form()
            if self.parent():
                self.parent().update_loaded_library(self.character_data, self.library_path)

    def save_to_json(self):
        try:
            with open(self.library_path, "w", encoding="utf-8") as f:
                json.dump(self.character_data, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error Saving", f"Failed to update file:\n{e}")


class TrashBinDialog(QDialog):
    def __init__(self, parent=None, trash_data=None):
        super().__init__(parent)
        self.setWindowTitle("Story Structure Trash Bin")
        self.setMinimumSize(550, 400)
        self.trash_data = trash_data if trash_data is not None else []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Deleted Items Inventory:</b>"))

        self.trash_list = QListWidget()
        self.trash_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.refresh_list()
        layout.addWidget(self.trash_list)

        btn_layout = QHBoxLayout()
        self.btn_restore = QPushButton("↩️ Restore Selected")
        self.btn_restore.clicked.connect(self.restore_selected)
        
        self.btn_multi_restore = QPushButton("⚡ Multi-Restore All")
        self.btn_multi_restore.setStyleSheet("background-color: #1565c0; color: white;")
        self.btn_multi_restore.clicked.connect(self.restore_all)

        self.btn_clear = QPushButton("🗑️ Clear Trash Bin")
        self.btn_clear.setStyleSheet("background-color: #c62828; color: white;")
        self.btn_clear.clicked.connect(self.clear_trash)

        btn_layout.addWidget(self.btn_restore)
        btn_layout.addWidget(self.btn_multi_restore)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

    def refresh_list(self):
        self.trash_list.clear()
        for idx, item in enumerate(self.trash_data):
            type_lbl = "[ARC]" if "chapters" in item else "[CHAPTER]"
            name = item.get("arc_name") if "chapters" in item else item.get("name")
            
            from PyQt6.QtWidgets import QListWidgetItem
            list_item = QListWidgetItem(f"{type_lbl} {name}")
            list_item.setData(Qt.ItemDataRole.UserRole, idx)
            self.trash_list.addItem(list_item)

    def restore_selected(self):
        selected_items = self.trash_list.selectedItems()
        if not selected_items: return
        indices = sorted([item.data(Qt.ItemDataRole.UserRole) for item in selected_items], reverse=True)
        for idx in indices:
            restored_item = self.trash_data.pop(idx)
            self.parent().execute_structural_restoration(restored_item)
        self.parent().save_trash_bin()
        self.refresh_list()

    def restore_all(self):
        if not self.trash_data: return
        while self.trash_data:
            restored_item = self.trash_data.pop(0)
            self.parent().execute_structural_restoration(restored_item)
        self.parent().save_trash_bin()
        self.refresh_list()

    def clear_trash(self):
        if not self.trash_data: return
        confirm = QMessageBox.question(self, "Confirm Permanent Purge", "Empty the entire trash bin permanently?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.trash_data.clear()
            self.parent().save_trash_bin()
            self.refresh_list()


class BookManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📚 Book Structure Manager")
        self.setMinimumSize(700, 500)
        self.parent_window = parent
        self.init_ui()
        self.load_book_structure()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>📖 Book Overview:</b>"))
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self.book_tree = QTreeWidget()
        self.book_tree.setHeaderLabels(["Arc / Chapter", "Pages"])
        self.book_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.book_tree.customContextMenuRequested.connect(self.show_book_context_menu)
        self.book_tree.itemDoubleClicked.connect(self.navigate_to_chapter)
        layout.addWidget(self.book_tree)
        
        nav_layout = QHBoxLayout()
        self.btn_prev_chapter = QPushButton("◀ Previous Chapter")
        self.btn_prev_chapter.clicked.connect(self.go_to_previous_chapter)
        
        self.btn_next_chapter = QPushButton("Next Chapter ▶")
        self.btn_next_chapter.clicked.connect(self.go_to_next_chapter)
        
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.load_book_structure)
        
        nav_layout.addWidget(self.btn_prev_chapter)
        nav_layout.addWidget(self.btn_next_chapter)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_refresh)
        layout.addLayout(nav_layout)
        
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Total Arcs: 0 | Total Chapters: 0")
        stats_layout.addWidget(self.stats_label)
        layout.addLayout(stats_layout)

    def load_book_structure(self):
        self.book_tree.clear()
        if not self.parent_window:
            return
            
        tree = self.parent_window.tree_widget
        total_arcs = tree.topLevelItemCount()
        total_chapters = 0
        
        for arc_idx in range(total_arcs):
            arc_item = tree.topLevelItem(arc_idx)
            arc_name = arc_item.text(0)
            chapter_count = arc_item.childCount()
            total_chapters += chapter_count
            
            arc_tree_item = QTreeWidgetItem(self.book_tree)
            arc_tree_item.setText(0, f"📚 {arc_name}")
            arc_tree_item.setText(1, f"{chapter_count} chapters")
            arc_tree_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "arc", "tree_item": arc_item})
            
            for ch_idx in range(chapter_count):
                chapter_item = arc_item.child(ch_idx)
                chapter_name = chapter_item.text(0)
                
                ch_tree_item = QTreeWidgetItem(arc_tree_item)
                ch_tree_item.setText(0, f"📄 {chapter_name}")
                
                # Calculate pages for this chapter
                safe_name = "".join([c if (c.isalnum() or c in (' ', '_', '-')) else '_' for c in chapter_name]).strip()
                safe_name = safe_name.replace(' ', '_')
                script_path = f"{safe_name}.md"
                
                page_count = 0
                if os.path.exists(script_path):
                    try:
                        with open(script_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        clean_text = re.sub(r'--- PAGE \d+ ---', '', content)
                        words = len(re.findall(r'\b\w+\b', clean_text))
                        page_count = int(words / 600) + 1
                    except:
                        pass
                
                ch_tree_item.setText(1, f"{page_count} pages")
                ch_tree_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "chapter", "tree_item": chapter_item})
        
        self.book_tree.expandAll()
        self.stats_label.setText(f"Total Arcs: {total_arcs} | Total Chapters: {total_chapters}")

    def show_book_context_menu(self, pos):
        item = self.book_tree.itemAt(pos)
        if not item: return
        
        menu = QMenu()
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "chapter":
            nav_action = QAction("📖 Open Chapter", self)
            nav_action.triggered.connect(lambda: self.navigate_to_chapter(item))
            menu.addAction(nav_action)
        
        refresh_action = QAction("🔄 Refresh Structure", self)
        refresh_action.triggered.connect(self.load_book_structure)
        menu.addAction(refresh_action)
        
        menu.exec(self.book_tree.viewport().mapToGlobal(pos))

    def navigate_to_chapter(self, item=None):
        if item is None:
            item = self.book_tree.currentItem()
        if not item: return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "chapter":
            tree_item = data.get("tree_item")
            if tree_item and self.parent_window:
                self.parent_window.tree_widget.setCurrentItem(tree_item)
                self.parent_window.on_tree_selection_changed()
                self.close()

    def go_to_previous_chapter(self):
        if not self.parent_window: return
        current = self.parent_window.tree_widget.currentItem()
        if not current or current.parent() is None: return
        
        parent = current.parent()
        idx = parent.indexOfChild(current)
        
        if idx > 0:
            prev_chapter = parent.child(idx - 1)
            self.parent_window.tree_widget.setCurrentItem(prev_chapter)
            self.parent_window.on_tree_selection_changed()
        elif parent.parent() is None:
            # Try to go to previous arc's last chapter
            arc_idx = self.parent_window.tree_widget.indexOfTopLevelItem(parent)
            if arc_idx > 0:
                prev_arc = self.parent_window.tree_widget.topLevelItem(arc_idx - 1)
                if prev_arc.childCount() > 0:
                    last_chapter = prev_arc.child(prev_arc.childCount() - 1)
                    self.parent_window.tree_widget.setCurrentItem(last_chapter)
                    self.parent_window.on_tree_selection_changed()

    def go_to_next_chapter(self):
        if not self.parent_window: return
        current = self.parent_window.tree_widget.currentItem()
        if not current or current.parent() is None: return
        
        parent = current.parent()
        idx = parent.indexOfChild(current)
        
        if idx < parent.childCount() - 1:
            next_chapter = parent.child(idx + 1)
            self.parent_window.tree_widget.setCurrentItem(next_chapter)
            self.parent_window.on_tree_selection_changed()
        elif parent.parent() is None:
            # Try to go to next arc's first chapter
            arc_idx = self.parent_window.tree_widget.indexOfTopLevelItem(parent)
            if arc_idx < self.parent_window.tree_widget.topLevelItemCount() - 1:
                next_arc = self.parent_window.tree_widget.topLevelItem(arc_idx + 1)
                if next_arc.childCount() > 0:
                    first_chapter = next_arc.child(0)
                    self.parent_window.tree_widget.setCurrentItem(first_chapter)
                    self.parent_window.on_tree_selection_changed()


class StoryTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def dropEvent(self, event):
        target_item = self.itemAt(event.position().toPoint())
        selected_item = self.currentItem()

        if not selected_item:
            event.ignore()
            return

        if selected_item.parent() is not None:
            if target_item and target_item.parent() is not None:
                parent_arc = target_item.parent()
                index = parent_arc.indexOfChild(target_item)
                selected_item.parent().removeChild(selected_item)
                parent_arc.insertChild(index, selected_item)
                self.setCurrentItem(selected_item)
                event.accept()
                self.window().save_story_structure()
                return
            elif target_item and target_item.parent() is None:
                selected_item.parent().removeChild(selected_item)
                target_item.addChild(selected_item)
                event.accept()
                self.window().save_story_structure()
                return
            else:
                event.ignore()
                return
        else:
            if target_item and target_item.parent() is not None:
                event.ignore()
                return
            
        super().dropEvent(event)
        self.window().save_story_structure()


class ColorEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Character Dialogue Colorizer - V{VERSION}")
        self.setGeometry(100, 100, 1300, 700) 
        self.character_data = {}
        self.trash_bin = []
        self.current_library_path = DEFAULT_LIBRARY
        self.current_script_path = DEFAULT_SCRIPT_FILE
        self._is_paginating = False
        self.current_page = 1
        self.total_pages = 1
        self.full_text = ""
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(400)
        self.debounce_timer.timeout.connect(self.trigger_rehighlight)
        
        self.init_ui()
        self.load_persisted_library()
        self.load_saved_script()
        self.load_story_structure()
        self.load_trash_bin()

    def init_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Panel: Outline View ---
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(5, 5, 5, 5)
        
        nav_layout.addWidget(QLabel("<b>Story Structure Outline:</b>"))
        self.tree_widget = StoryTreeWidget(self)
        self.tree_widget.setHeaderLabels(["Timeline Elements"])
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.tree_widget.itemChanged.connect(self.on_tree_item_changed)
        self.tree_widget.itemSelectionChanged.connect(self.on_tree_selection_changed)
        nav_layout.addWidget(self.tree_widget)
        
        btn_layout = QHBoxLayout()
        self.btn_add_arc = QPushButton("+ Arc")
        self.btn_add_arc.clicked.connect(self.add_arc_item)
        self.btn_add_chapter = QPushButton("+ Chapter")
        self.btn_add_chapter.clicked.connect(self.add_chapter_item)
        self.btn_trash = QPushButton("🗑️ Trash")
        self.btn_trash.clicked.connect(self.open_trash_bin)
        btn_layout.addWidget(self.btn_add_arc)
        btn_layout.addWidget(self.btn_add_chapter)
        btn_layout.addWidget(self.btn_trash)
        nav_layout.addLayout(btn_layout)
        
        self.btn_book_manager = QPushButton("📚 Book Manager")
        self.btn_book_manager.clicked.connect(self.open_book_manager)
        nav_layout.addWidget(self.btn_book_manager)
        
        # --- Center Panel: Workspace Editor Panel ---
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(5, 5, 5, 5)
        editor_layout.addWidget(QLabel("<b>Dialogue Editor Script Workspace (.md):</b>"))
        
        self.text_edit = QTextEdit()
        self.text_edit.setUndoRedoEnabled(True)
        
        lora_font = QFont("Lora", 12)
        lora_font.setStyleHint(QFont.StyleHint.Serif)
        self.text_edit.setFont(lora_font)
        self.text_edit.setStyleSheet("QTextEdit { background-color: #121212; color: #FFFFFF; border: 1px solid #333333; padding: 10px; line-height: 150%; }")
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.show_context_menu)
        self.text_edit.textChanged.connect(self.on_text_changed)
        
        self.highlighter = AdvancedDialogueHighlighter(self.text_edit.document())
        editor_layout.addWidget(self.text_edit)
        
        # Page Navigation Controls
        page_nav_layout = QHBoxLayout()
        
        self.btn_prev_page = QPushButton("◀ Previous")
        self.btn_prev_page.clicked.connect(self.go_to_previous_page)
        self.btn_prev_page.setEnabled(False)
        
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; padding: 5px;")
        
        self.btn_next_page = QPushButton("Next ▶")
        self.btn_next_page.clicked.connect(self.go_to_next_page)
        self.btn_next_page.setEnabled(False)
        
        page_nav_layout.addWidget(self.btn_prev_page)
        page_nav_layout.addWidget(self.page_label)
        page_nav_layout.addWidget(self.btn_next_page)
        editor_layout.addLayout(page_nav_layout)
        
        self.metrics_label = QLabel("Words: 0 | Pages: 0.0 (600 wpp)")
        self.metrics_label.setStyleSheet("color: #AAAAAA; font-size: 11px; padding: 2px;")
        editor_layout.addWidget(self.metrics_label)
        
        # --- Right Panel: Database Viewer ---
        json_widget = QWidget()
        json_layout = QVBoxLayout(json_widget)
        json_layout.setContentsMargins(5, 5, 5, 5)
        
        self.json_label = QLabel("<b>Active Library (.json Content):</b>")
        json_layout.addWidget(self.json_label)
        
        self.json_viewer = QTextEdit()
        self.json_viewer.setReadOnly(True)
        mono_font = QFont("Consolas", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.json_viewer.setFont(mono_font)
        self.json_viewer.setStyleSheet("QTextEdit { background-color: #1E1E1E; color: #A9CDA1; border: 1px solid #444444; padding: 8px; }")
        json_layout.addWidget(self.json_viewer)
        
        main_splitter.addWidget(nav_widget)
        main_splitter.addWidget(editor_widget)
        main_splitter.addWidget(json_widget)
        main_splitter.setSizes([275, 625, 400]) 
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(main_splitter)
        
        text_container = QWidget()
        text_container.setLayout(main_layout)
        self.setCentralWidget(text_container)

        self.setup_menu_actions()

    def setup_menu_actions(self):
        menubar = self.menuBar()
        
        edit_menu = menubar.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.text_edit.undo)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.text_edit.redo)
        
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)

        file_menu = menubar.addMenu("File")
        open_script_action = QAction("Open Script (.md)...", self)
        open_script_action.triggered.connect(self.import_md_file)
        file_menu.addAction(open_script_action)
        
        save_script_action = QAction("Save Script As...", self)
        save_script_action.triggered.connect(self.export_md_file)
        file_menu.addAction(save_script_action)

        library_menu = menubar.addMenu("Library")
        import_json_action = QAction("Open CHARACTER.json...", self)
        import_json_action.triggered.connect(self.import_json)
        library_menu.addAction(import_json_action)

        import_sheets_action = QAction("Import from Sheets/Excel (CSV)...", self)
        import_sheets_action.triggered.connect(self.import_from_sheets)
        library_menu.addAction(import_sheets_action)
        
        export_sheets_action = QAction("Export to Sheets/Excel (CSV)...", self)
        export_sheets_action.triggered.connect(self.export_to_sheets)
        library_menu.addAction(export_sheets_action)
        library_menu.addSeparator()
        
        manage_chars_action = QAction("⚙️ Manage Characters...", self)
        manage_chars_action.triggered.connect(self.open_character_manager)
        library_menu.addAction(manage_chars_action)

    def on_text_changed(self):
        if self._is_paginating:
            return
        self.update_word_and_page_count()
        self.reset_debounce_timer()
        self.autosave_script()

    def update_word_and_page_count(self):
        text = self.full_text if self.full_text else self.text_edit.toPlainText()
        clean_text = re.sub(r'--- PAGE \d+ ---', '', text)
        words = len(re.findall(r'\b\w+\b', clean_text))
        pages = words / 600.0
        self.metrics_label.setText(f"Words: {words} | Pages: {pages:.2f} (Calculated at 600 words per page)")

    def go_to_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.display_current_page()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.display_current_page()

    def parse_pages(self):
        text = self.full_text if self.full_text else ""
        if not text:
            return []
        
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

    def display_current_page(self):
        self.text_edit.blockSignals(True)
        pages = self.parse_pages()
        if not pages:
            self.text_edit.setPlainText(self.full_text if self.full_text else "")
            self.total_pages = 1
        else:
            self.total_pages = len(pages)
            if self.current_page <= self.total_pages:
                page_num, page_content = pages[self.current_page - 1]
                self.text_edit.setPlainText(page_content)
            else:
                self.current_page = 1
                page_num, page_content = pages[0]
                self.text_edit.setPlainText(page_content)
        
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < self.total_pages)
        self.text_edit.blockSignals(False)

    def repaginate_workspace(self):
        if self._is_paginating:
            return
        self._is_paginating = True
        
        raw_text = self.full_text if self.full_text else self.text_edit.toPlainText()
        lines = raw_text.split('\n')
        
        cleaned_lines = []
        for line in lines:
            if not re.match(r'^--- PAGE \d+ ---$', line):
                cleaned_lines.append(line)
        
        spaced_lines = []
        for idx, line in enumerate(cleaned_lines):
            stripped = line.strip()
            
            # Identify if current line is character dialogue
            is_current_dialogue = (stripped and ':' in stripped and not stripped.startswith('#'))
            
            # Look behind to inject space before dialogue
            if is_current_dialogue and len(spaced_lines) > 0:
                if spaced_lines[-1].strip() != "":
                    spaced_lines.append("")
                        
            spaced_lines.append(line)
            
            # Look ahead to inject space after dialogue if transitioning to prose
            if is_current_dialogue:
                if idx + 1 < len(cleaned_lines):
                    next_line = cleaned_lines[idx + 1].strip()
                    if next_line:
                        is_next_dialogue = (':' in next_line and not next_line.startswith('#'))
                        if not is_next_dialogue:
                            spaced_lines.append("")

        final_cleaned = []
        for l in spaced_lines:
            if len(final_cleaned) > 0 and final_cleaned[-1] == "" and l == "":
                continue
            final_cleaned.append(l)

        paginated_lines = []
        word_counter = 0
        page_number = 1
        
        for line in final_cleaned:
            line_words = len(re.findall(r'\b\w+\b', line))
            if word_counter + line_words > 600:
                paginated_lines.append(f"--- PAGE {page_number} ---")
                page_number += 1
                word_counter = line_words
            else:
                word_counter += line_words
            paginated_lines.append(line)
            
        new_text = '\n'.join(paginated_lines)
        self.full_text = new_text
        # Don't reset current_page - preserve it during repagination
        self.display_current_page()
            
        self._is_paginating = False

    def autosave_script(self):
        if not self.current_script_path: return
        try:
            text = self.full_text if self.full_text else self.text_edit.toPlainText()
            clean_text = re.sub(r'--- PAGE \d+ ---\n?', '', text)
            with open(self.current_script_path, "w", encoding="utf-8") as f:
                f.write(clean_text)
        except IOError:
            pass

    def load_saved_script(self):
        if os.path.exists(self.current_script_path):
            try:
                with open(self.current_script_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.full_text = content
                self.text_edit.blockSignals(True)
                self.repaginate_workspace()
                self.text_edit.blockSignals(False)
                self.update_word_and_page_count()
            except Exception:
                pass

    def on_tree_selection_changed(self):
        selected_item = self.tree_widget.currentItem()
        if selected_item and selected_item.parent() is not None:
            self.autosave_script()
            
            raw_text = selected_item.text(0)
            safe_name = "".join([c if (c.isalnum() or c in (' ', '_', '-')) else '_' for c in raw_text]).strip()
            safe_name = safe_name.replace(' ', '_')
            
            self.current_script_path = f"{safe_name}.md"
            self.highlighter.manual_overrides.clear()
            self.current_page = 1
            self.full_text = ""
            
            if os.path.exists(self.current_script_path):
                self.load_saved_script()
            else:
                self.text_edit.blockSignals(True)
                self.text_edit.clear()
                self.text_edit.blockSignals(False)
                self.highlighter.rehighlight()
                self.update_word_and_page_count()
                self.page_label.setText("Page 1 of 1")
                self.btn_prev_page.setEnabled(False)
                self.btn_next_page.setEnabled(False)

    def add_arc_item(self):
        item = QTreeWidgetItem(self.tree_widget)
        item.setText(0, "New Narrative Arc")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        self.tree_widget.expandItem(item)
        self.save_story_structure()

    def add_chapter_item(self):
        selected = self.tree_widget.currentItem()
        if selected and selected.parent() is None:
            parent_item = selected
        else:
            parent_item = self.tree_widget.topLevelItem(0)
            
        if not parent_item:
            parent_item = QTreeWidgetItem(self.tree_widget)
            parent_item.setText(0, "Default Arc Framework")
            parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            
        child = QTreeWidgetItem(parent_item)
        child.setText(0, f"Chapter {parent_item.childCount() + 1}: New Chapter")
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled)
        self.tree_widget.expandItem(parent_item)
        self.save_story_structure()

    def show_tree_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        if not item: return
        
        menu = QMenu()
        rename_action = QAction("✏️ Rename Element", self)
        rename_action.triggered.connect(lambda: self.tree_widget.editItem(item, 0))
        menu.addAction(rename_action)

        if item.parent() is not None:
            color_action = QAction("🎨 Edit Chapter Color...", self)
            color_action.triggered.connect(lambda: self.change_tree_item_color(item))
            menu.addAction(color_action)

        delete_action = QAction("🗑️ Delete Element to Trash", self)
        delete_action.triggered.connect(lambda: self.send_tree_item_to_trash(item))
        menu.addAction(delete_action)
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))

    def change_tree_item_color(self, item):
        current_color = item.foreground(0).color()
        if not current_color.isValid():
            current_color = QColor("#FFFFFF")
            
        color = QColorDialog.getColor(current_color, self, "Select Chapter Node Color")
        if color.isValid():
            item.setForeground(0, color)
            self.save_story_structure()

    def send_tree_item_to_trash(self, item):
        parent = item.parent()
        if parent:
            color_hex = item.foreground(0).color().name() if item.foreground(0).color().isValid() else None
            self.trash_bin.append({
                "name": item.text(0),
                "color": color_hex,
                "parent_arc_name": parent.text(0)
            })
            parent.removeChild(item)
        else:
            arc_packet = {"arc_name": item.text(0), "chapters": []}
            for j in range(item.childCount()):
                child = item.child(j)
                c_hex = child.foreground(0).color().name() if child.foreground(0).color().isValid() else None
                arc_packet["chapters"].append({"name": child.text(0), "color": c_hex})
            self.trash_bin.append(arc_packet)
            
            idx = self.tree_widget.indexOfTopLevelItem(item)
            self.tree_widget.takeTopLevelItem(idx)

        self.save_story_structure()
        self.save_trash_bin()

    def execute_structural_restoration(self, trash_item):
        self.tree_widget.blockSignals(True)
        if "chapters" in trash_item:
            arc_item = QTreeWidgetItem(self.tree_widget)
            arc_item.setText(0, trash_item.get("arc_name", "Restored Arc"))
            arc_item.setFlags(arc_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            for ch in trash_item.get("chapters", []):
                ch_item = QTreeWidgetItem(arc_item)
                ch_item.setText(0, ch.get("name"))
                ch_item.setFlags(ch_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled)
                if ch.get("color"):
                    ch_item.setForeground(0, QColor(ch["color"]))
        else:
            target_parent_name = trash_item.get("parent_arc_name")
            parent_arc_item = None
            for i in range(self.tree_widget.topLevelItemCount()):
                t_item = self.tree_widget.topLevelItem(i)
                if t_item.text(0) == target_parent_name:
                    parent_arc_item = t_item
                    break
            
            if not parent_arc_item:
                parent_arc_item = QTreeWidgetItem(self.tree_widget)
                parent_arc_item.setText(0, target_parent_name if target_parent_name else "Restored Assets Arc")
                parent_arc_item.setFlags(parent_arc_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)

            ch_item = QTreeWidgetItem(parent_arc_item)
            ch_item.setText(0, trash_item.get("name", "Restored Chapter"))
            ch_item.setFlags(ch_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled)
            if trash_item.get("color"):
                ch_item.setForeground(0, QColor(trash_item["color"]))
                
        self.tree_widget.blockSignals(False)
        self.save_story_structure()

    def open_trash_bin(self):
        dialog = TrashBinDialog(self, self.trash_bin)
        dialog.exec()

    def open_book_manager(self):
        dialog = BookManagerDialog(self)
        dialog.exec()

    def on_tree_item_changed(self, item, column):
        self.save_story_structure()

    def save_story_structure(self):
        self.tree_widget.blockSignals(True)
        structure = []
        for i in range(self.tree_widget.topLevelItemCount()):
            arc_item = self.tree_widget.topLevelItem(i)
            arc_data = {"arc_name": arc_item.text(0), "chapters": []}
            for j in range(arc_item.childCount()):
                child = arc_item.child(j)
                color_hex = child.foreground(0).color().name() if child.foreground(0).color().isValid() else None
                arc_data["chapters"].append({
                    "name": child.text(0),
                    "color": color_hex
                })
            structure.append(arc_data)
        self.tree_widget.blockSignals(False)
        try:
            with open(STRUCTURE_FILE, "w", encoding="utf-8") as f:
                json.dump(structure, f, indent=4)
        except IOError:
            pass

    def load_story_structure(self):
        if not os.path.exists(STRUCTURE_FILE): return
        try:
            with open(STRUCTURE_FILE, "r", encoding="utf-8") as f:
                structure = json.load(f)
            
            self.tree_widget.blockSignals(True)
            self.tree_widget.clear()
            for arc in structure:
                arc_item = QTreeWidgetItem(self.tree_widget)
                arc_item.setText(0, arc.get("arc_name", "Unnamed Arc"))
                arc_item.setFlags(arc_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
                for ch in arc.get("chapters", []):
                    ch_item = QTreeWidgetItem(arc_item)
                    ch_item.setFlags(ch_item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled)
                    if isinstance(ch, dict):
                        ch_item.setText(0, ch.get("name", "Unnamed Chapter"))
                        if ch.get("color"):
                            ch_item.setForeground(0, QColor(ch["color"]))
                    else:
                        ch_item.setText(0, str(ch))
            self.tree_widget.blockSignals(False)
        except Exception:
            self.tree_widget.blockSignals(False)

    def save_trash_bin(self):
        try:
            with open(TRASH_FILE, "w", encoding="utf-8") as f:
                json.dump(self.trash_bin, f, indent=4)
        except IOError:
            pass

    def load_trash_bin(self):
        if os.path.exists(TRASH_FILE):
            try:
                with open(TRASH_FILE, "r", encoding="utf-8") as f:
                    self.trash_bin = json.load(f)
            except Exception:
                self.trash_bin = []

    def import_md_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Script Markdown File", "", "Markdown Files (*.md *.txt)")
        if file_path:
            self.current_script_path = file_path
            self.load_saved_script()

    def export_md_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Script Framework As...", "", "Markdown Files (*.md)")
        if file_path:
            self.current_script_path = file_path
            self.autosave_script()

    def update_json_display(self):
        if self.character_data:
            formatted_json = json.dumps(self.character_data, indent=4, ensure_ascii=False)
            self.json_viewer.setPlainText(formatted_json)
        else:
            self.json_viewer.setPlainText("{\n    // No character assets loaded.\n}")
        filename = os.path.basename(self.current_library_path)
        self.json_label.setText(f"<b>Active Library ({filename}):</b>")

    def reset_debounce_timer(self):
        self.debounce_timer.start()

    def trigger_rehighlight(self):
        self.repaginate_workspace()
        self.text_edit.blockSignals(True)
        self.highlighter.rehighlight()
        self.text_edit.blockSignals(False)

    def save_config(self, library_path):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_library": library_path}, f)
        except IOError:
            pass

    def load_persisted_library(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    saved_path = config.get("last_library", DEFAULT_LIBRARY)
                    if os.path.exists(saved_path):
                        self.current_library_path = saved_path
            except Exception:
                self.current_library_path = DEFAULT_LIBRARY

        if os.path.exists(self.current_library_path):
            try:
                with open(self.current_library_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                self.character_data = {}
                for k, v in raw_data.items():
                    self.character_data[k] = v if isinstance(v, dict) else {"color": v, "aliases": []}
                self.highlighter.set_colors(self.character_data)
            except Exception:
                pass
        
        self.update_json_display()

    def update_loaded_library(self, data_dict, library_path):
        self.character_data = data_dict
        self.current_library_path = library_path
        self.highlighter.set_colors(self.character_data)
        self.save_config(library_path)
        self.update_json_display()

    def open_character_manager(self):
        dialog = CharacterManagerDialog(self, self.character_data, self.current_library_path)
        dialog.exec()

    def import_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open JSON Library", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            normalized = {k: (v if isinstance(v, dict) else {"color": v, "aliases": []}) for k, v in raw_data.items()}
            self.update_loaded_library(normalized, file_path)

    def import_from_sheets(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Sheets Export", "", "CSV Files (*.csv)")
        if file_path:
            new_data = {}
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        name = row[0].strip()
                        hex_color = row[1].strip() if row[1].strip().startswith('#') else f"#{row[1].strip()}"
                        aliases = [a.strip() for a in row[2].split(";")] if len(row) >= 3 and row[2] else []
                        if name and len(hex_color) == 7:
                            new_data[name] = {"color": hex_color, "aliases": aliases}
            self.update_loaded_library(new_data, self.current_library_path)

    def export_to_sheets(self):
        if not self.character_data:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Sheets CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    for name, attribs in self.character_data.items():
                        writer.writerow([name, attribs.get("color"), ";".join(attribs.get("aliases", []))])
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def show_context_menu(self, position):
        menu = self.text_edit.createStandardContextMenu()
        menu.addSeparator()
        custom_color_action = QAction("🎨 Select Custom Color...", self)
        custom_color_action.triggered.connect(self.apply_custom_picker_color)
        menu.addAction(custom_color_action)
        
        color_submenu = QMenu("Apply Character Color", self)
        if self.character_data:
            for char, attribs in self.character_data.items():
                hex_color = attribs.get("color")
                action = QAction(f"{char} ({hex_color})", self)
                action.triggered.connect(lambda checked, c=hex_color: self.apply_manual_override_color(c))
                color_submenu.addAction(action)
        else:
            color_submenu.addAction("No Characters Loaded").setEnabled(False)
            
        menu.addMenu(color_submenu)
        menu.exec(self.text_edit.viewport().mapToGlobal(position))

    def apply_manual_override_color(self, hex_color):
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        current_cursor = QTextCursor(cursor)
        current_cursor.setPosition(start_pos)
        
        while current_cursor.position() < end_pos:
            block = current_cursor.block()
            block_start = block.position()
            block_end = block_start + block.length() - 1

            actual_start = max(start_pos, block_start)
            actual_end = min(end_pos, block_end)
            
            if actual_start < actual_end:
                relative_start = actual_start - block_start
                length = actual_end - actual_start
                self.highlighter.add_manual_override(block.blockNumber(), relative_start, length, hex_color)
            
            current_cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            if current_cursor.atEnd() and current_cursor.position() <= end_pos:
                break

    def apply_custom_picker_color(self):
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            color = QColorDialog.getColor()
            if color.isValid():
                self.apply_manual_override_color(color.name())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ColorEditor()
    editor.show()
    sys.exit(app.exec())
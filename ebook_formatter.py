import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import re
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import fonts
import pdfplumber
from PIL import Image as PILImage
import nltk
from nltk.tokenize import sent_tokenize
from textblob import TextBlob
import ebooklib
from ebooklib import epub
import docx
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import json
import os
from datetime import datetime
import threading
from queue import Queue
import concurrent.futures

def process_text(text):
    """Process text to detect chapters and their content"""
    chapters = []
    current_chapter = None
    current_content = []
    
    # Split text into lines
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for chapter markers
        if re.match(r'^Chapter\s+\d+', line, re.IGNORECASE) or \
           re.match(r'^CHAPTER\s+\d+', line) or \
           re.match(r'^\d+\.', line):
            # Save previous chapter if exists
            if current_chapter:
                chapters.append({
                    'title': current_chapter,
                    'content': current_content
                })
            
            # Start new chapter
            current_chapter = line
            current_content = []
        else:
            # Add line to current chapter content
            if current_chapter:
                current_content.append(line)
            else:
                # If no chapter title found yet, create a default chapter
                current_chapter = "Chapter 1"
                current_content.append(line)
    
    # Add the last chapter
    if current_chapter:
        chapters.append({
            'title': current_chapter,
            'content': current_content
        })
    
    return chapters

def clean_text(text):
    """Clean and normalize text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common punctuation issues
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    text = re.sub(r'"\s*"', '" "', text)
    
    # Fix common formatting issues
    text = text.replace('--', '—')
    text = text.replace('...', '…')
    
    return text.strip()

# Create a thread pool for background tasks
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

# Initialize NLTK in a background thread
def init_nltk():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)

# Start NLTK initialization in background
threading.Thread(target=init_nltk, daemon=True).start()

# Define themes with modern colors
THEMES = {
    "Light": {
        "bg": "#ffffff",
        "fg": "#2d2d2d",
        "select_bg": "#e1e1e1",
        "select_fg": "#2d2d2d",
        "button_bg": "#f0f0f0",
        "button_fg": "#2d2d2d",
        "frame_bg": "#f5f5f5",
        "text_bg": "#ffffff",
        "text_fg": "#2d2d2d",
        "listbox_bg": "#ffffff",
        "listbox_fg": "#2d2d2d",
        "listbox_select_bg": "#0078d7",
        "listbox_select_fg": "#ffffff",
        "status_bg": "#f0f0f0",
        "status_fg": "#2d2d2d",
        "accent_color": "#0078d7",
        "accent_hover": "#106ebe",
        "error_color": "#d83b01",
        "success_color": "#107c10",
        "warning_color": "#797673"
    },
    "Dark": {
        "bg": "#2d2d2d",
        "fg": "#ffffff",
        "select_bg": "#3d3d3d",
        "select_fg": "#ffffff",
        "button_bg": "#3d3d3d",
        "button_fg": "#ffffff",
        "frame_bg": "#2d2d2d",
        "text_bg": "#1e1e1e",
        "text_fg": "#ffffff",
        "listbox_bg": "#1e1e1e",
        "listbox_fg": "#ffffff",
        "listbox_select_bg": "#0078d7",
        "listbox_select_fg": "#ffffff",
        "status_bg": "#1e1e1e",
        "status_fg": "#ffffff",
        "accent_color": "#0078d7",
        "accent_hover": "#106ebe",
        "error_color": "#d83b01",
        "success_color": "#107c10",
        "warning_color": "#797673"
    }
}

# Define formatting presets with modern defaults
FORMATTING_PRESETS = {
    "Kindle": {
        "page_size": letter,
        "font_name": "Times-Roman",
        "font_size": 16,
        "line_spacing": 1.5,
        "paragraph_spacing": 12,
        "first_line_indent": 32,
        "chapter_title_size": 24,
        "chapter_title_spacing": 30,
        "margins": (72, 72, 72, 72),
        "header_footer": False,
        "drop_cap": True,
        "smart_quotes": True
    },
    "Google Books": {
        "page_size": letter,
        "font_name": "Times-Roman",
        "font_size": 16,
        "line_spacing": 1.5,
        "paragraph_spacing": 12,
        "first_line_indent": 32,
        "chapter_title_size": 24,
        "chapter_title_spacing": 30,
        "margins": (72, 72, 72, 72),
        "header_footer": False,
        "drop_cap": True,
        "smart_quotes": True
    },
    "Print": {
        "page_size": letter,
        "font_name": "Times-Roman",
        "font_size": 12,
        "line_spacing": 1.15,
        "paragraph_spacing": 8,
        "first_line_indent": 24,
        "chapter_title_size": 20,
        "chapter_title_spacing": 24,
        "margins": (72, 72, 72, 72),
        "header_footer": True,
        "drop_cap": True,
        "smart_quotes": True
    }
}

class ModernButton(ttk.Button):
    """Custom button with hover effect and modern styling"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.default_style = self.cget('style')
        self.configure(padding=5)

    def on_enter(self, e):
        self.configure(style='Accent.TButton')

    def on_leave(self, e):
        self.configure(style=self.default_style)

class ModernToolbar(ttk.Frame):
    """Modern toolbar with icons and tooltips"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.buttons = {}
        self.create_toolbar()

    def create_toolbar(self):
        # File operations
        self.add_button("new", "New", "Create a new document")
        self.add_button("open", "Open", "Open a text file")
        self.add_button("save", "Save", "Save current document")
        self.add_separator()
        
        # Edit operations
        self.add_button("undo", "Undo", "Undo last action")
        self.add_button("redo", "Redo", "Redo last action")
        self.add_separator()
        self.add_button("cut", "Cut", "Cut selected text")
        self.add_button("copy", "Copy", "Copy selected text")
        self.add_button("paste", "Paste", "Paste text")
        self.add_separator()
        
        # Format operations
        self.add_button("format_kindle", "Kindle", "Format for Kindle")
        self.add_button("format_google", "Google Books", "Format for Google Books")
        self.add_button("format_print", "Print", "Format for Print")
        self.add_separator()
        
        # View operations
        self.add_button("zoom_in", "Zoom In", "Increase text size")
        self.add_button("zoom_out", "Zoom Out", "Decrease text size")
        self.add_button("theme", "Theme", "Toggle theme")

    def add_button(self, name, text, tooltip):
        btn = ModernButton(self, text=text)
        btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(btn, tooltip)
        self.buttons[name] = btn

    def add_separator(self):
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

    def create_tooltip(self, widget, text):
        def show_tooltip(event=None):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background=THEMES["Light"]["accent_color"], foreground="white", padding=5)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
        
        widget.bind('<Enter>', show_tooltip)

class ModernProgressBar(ttk.Frame):
    """Modern progress bar with status message"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        
        self.progress = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress.pack(fill=tk.X, padx=5, pady=2)
        
        self.status = ttk.Label(
            self,
            textvariable=self.status_var,
            anchor=tk.W
        )
        self.status.pack(fill=tk.X, padx=5, pady=2)

    def start(self, message="Processing..."):
        self.progress_var.set(0)
        self.status_var.set(message)
        self.progress.start(10)

    def stop(self, message="Ready"):
        self.progress.stop()
        self.progress_var.set(100)
        self.status_var.set(message)

class SearchDialog(tk.Toplevel):
    """Modern search and replace dialog"""
    def __init__(self, parent, text_widget):
        super().__init__(parent)
        self.title("Search and Replace")
        self.text_widget = text_widget
        self.current_search = None
        self.create_widgets()
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        # Center dialog
        self.geometry("400x150")
        self.center()

    def create_widgets(self):
        # Search frame
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Find:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Replace frame
        replace_frame = ttk.Frame(self)
        replace_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(replace_frame, text="Replace:").pack(side=tk.LEFT)
        self.replace_var = tk.StringVar()
        self.replace_entry = ttk.Entry(replace_frame, textvariable=self.replace_var)
        self.replace_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Options frame
        options_frame = ttk.Frame(self)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.case_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Match case", variable=self.case_var).pack(side=tk.LEFT)
        
        self.whole_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Whole word", variable=self.whole_var).pack(side=tk.LEFT, padx=5)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(buttons_frame, text="Find", command=self.find).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Replace", command=self.replace).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Replace All", command=self.replace_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=2)

    def center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def find(self):
        search_text = self.search_var.get()
        if not search_text:
            return
            
        flags = 0
        if self.case_var.get():
            flags |= tk.END
            
        if self.whole_var.get():
            flags |= tk.END
            
        # Start search from current position
        start_pos = self.text_widget.index(tk.INSERT)
        pos = self.text_widget.search(search_text, start_pos, flags=flags)
        
        if pos:
            self.text_widget.tag_remove('search', '1.0', tk.END)
            self.text_widget.tag_add('search', pos, f"{pos}+{len(search_text)}c")
            self.text_widget.tag_configure('search', background='yellow')
            self.text_widget.see(pos)
            self.current_search = (pos, search_text)
        else:
            messagebox.showinfo("Search", "Text not found")

    def replace(self):
        if not self.current_search:
            self.find()
            
        if self.current_search:
            pos, search_text = self.current_search
            replace_text = self.replace_var.get()
            self.text_widget.delete(pos, f"{pos}+{len(search_text)}c")
            self.text_widget.insert(pos, replace_text)
            self.find()

    def replace_all(self):
        search_text = self.search_var.get()
        replace_text = self.replace_var.get()
        if not search_text:
            return
            
        flags = 0
        if self.case_var.get():
            flags |= tk.END
            
        if self.whole_var.get():
            flags |= tk.END
            
        content = self.text_widget.get('1.0', tk.END)
        new_content = content.replace(search_text, replace_text)
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.insert('1.0', new_content)

class ModernTitleBar(tk.Frame):
    """Modern title bar with gradient background and format indicators"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(height=50)  # Increased height
        self.pack(fill=tk.X, side=tk.TOP)
        
        # Create gradient background
        self.canvas = tk.Canvas(self, height=50, highlightthickness=0)  # Increased height
        self.canvas.pack(fill=tk.X)
        self.create_gradient()
        
        # Title label with larger font and enhanced styling
        self.title_label = tk.Label(
            self.canvas,
            text="Ebook Formatter Pro",
            font=("Segoe UI", 16, "bold"),  # Larger font
            bg="#0078d7",
            fg="white",
            pady=10  # Added padding
        )
        self.title_label.pack(side=tk.LEFT, padx=20)  # Increased padding
        
        # Format indicators with enhanced styling
        self.format_frame = tk.Frame(self.canvas, bg="#0078d7")
        self.format_frame.pack(side=tk.RIGHT, padx=20)  # Increased padding
        
        self.format_indicators = {}
        for format_name in ["Kindle", "Google Books", "Print"]:
            indicator = tk.Label(
                self.format_frame,
                text=format_name,
                font=("Segoe UI", 10),  # Larger font
                bg="#0078d7",
                fg="#ffffff",
                padx=10,  # Increased padding
                pady=5
            )
            indicator.pack(side=tk.LEFT, padx=5)
            self.format_indicators[format_name] = indicator
        
        # Bind window resize
        self.bind('<Configure>', self.on_resize)
    
    def create_gradient(self):
        """Create enhanced gradient background"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Create a more vibrant gradient with three colors
        start_color = "#0078d7"  # Microsoft blue
        mid_color = "#00a4ef"    # Lighter blue
        end_color = "#106ebe"    # Darker blue
        
        for i in range(height):
            # Calculate position in gradient (0 to 1)
            pos = i / height
            
            # Create three-color gradient
            if pos < 0.5:
                # Blend from start to mid color
                blend = pos * 2
                color = self.blend_colors(start_color, mid_color, blend)
            else:
                # Blend from mid to end color
                blend = (pos - 0.5) * 2
                color = self.blend_colors(mid_color, end_color, blend)
            
            self.canvas.create_line(0, i, width, i, fill=color)
    
    def blend_colors(self, color1, color2, blend_factor):
        """Blend two colors based on blend factor (0 to 1)"""
        # Convert hex to RGB
        r1, g1, b1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
        r2, g2, b2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]
        
        # Blend colors
        r = int(r1 + (r2 - r1) * blend_factor)
        g = int(g1 + (g2 - g1) * blend_factor)
        b = int(b1 + (b2 - b1) * blend_factor)
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def on_resize(self, event):
        """Handle window resize"""
        self.create_gradient()
    
    def update_format_indicator(self, format_name):
        """Update the active format indicator with enhanced visual feedback"""
        for name, indicator in self.format_indicators.items():
            if name == format_name:
                indicator.configure(
                    bg="#ffffff",
                    fg="#0078d7",
                    font=("Segoe UI", 10, "bold")  # Bold for active format
                )
            else:
                indicator.configure(
                    bg="#0078d7",
                    fg="#ffffff",
                    font=("Segoe UI", 10)  # Normal for inactive formats
                )

class ModernSearchBar(ttk.Frame):
    """Modern search bar with real-time filtering"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Create search frame with icon
        self.search_frame = ttk.Frame(self)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Search icon (using Unicode magnifying glass)
        self.icon_label = ttk.Label(
            self.search_frame,
            text="🔍",
            font=("Segoe UI", 10)
        )
        self.icon_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Search entry
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        
        self.search_entry = ttk.Entry(
            self.search_frame,
            textvariable=self.search_var,
            font=("Segoe UI", 10)
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Match count label
        self.match_count_var = tk.StringVar(value="")
        self.match_count_label = ttk.Label(
            self.search_frame,
            textvariable=self.match_count_var,
            font=("Segoe UI", 9)
        )
        self.match_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Navigation buttons
        self.nav_frame = ttk.Frame(self)
        self.nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.prev_button = ttk.Button(
            self.nav_frame,
            text="↑ Previous",
            command=self.find_previous
        )
        self.prev_button.pack(side=tk.LEFT, padx=2)
        
        self.next_button = ttk.Button(
            self.nav_frame,
            text="↓ Next",
            command=self.find_next
        )
        self.next_button.pack(side=tk.LEFT, padx=2)
        
        self.clear_button = ttk.Button(
            self.nav_frame,
            text="Clear",
            command=self.clear_search
        )
        self.clear_button.pack(side=tk.RIGHT, padx=2)
        
        self.current_match = 0
        self.matches = []
        self.text_widget = None
    
    def set_text_widget(self, text_widget):
        """Set the text widget to search in"""
        self.text_widget = text_widget
    
    def on_search_change(self, *args):
        """Handle search text changes"""
        if not self.text_widget:
            return
            
        search_text = self.search_var.get()
        if not search_text:
            self.clear_search()
            return
        
        # Remove existing tags
        self.text_widget.tag_remove('search', '1.0', tk.END)
        
        # Find all matches
        self.matches = []
        start_pos = '1.0'
        while True:
            pos = self.text_widget.search(search_text, start_pos, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_text)}c"
            self.matches.append((pos, end_pos))
            start_pos = end_pos
        
        # Update match count
        count = len(self.matches)
        self.match_count_var.set(f"{count} match{'es' if count != 1 else ''}")
        
        # Highlight all matches
        for start, end in self.matches:
            self.text_widget.tag_add('search', start, end)
        
        # Configure search tag
        self.text_widget.tag_configure('search', background='yellow')
        
        # Go to first match
        if self.matches:
            self.current_match = 0
            self.go_to_match(0)
    
    def find_next(self):
        """Go to next match"""
        if not self.matches:
            return
        self.current_match = (self.current_match + 1) % len(self.matches)
        self.go_to_match(self.current_match)
    
    def find_previous(self):
        """Go to previous match"""
        if not self.matches:
            return
        self.current_match = (self.current_match - 1) % len(self.matches)
        self.go_to_match(self.current_match)
    
    def go_to_match(self, index):
        """Go to specific match"""
        if not self.matches or not self.text_widget:
            return
        
        start, end = self.matches[index]
        self.text_widget.see(start)
        self.text_widget.mark_set(tk.INSERT, start)
        self.text_widget.see(tk.INSERT)
    
    def clear_search(self):
        """Clear search and remove highlights"""
        self.search_var.set("")
        if self.text_widget:
            self.text_widget.tag_remove('search', '1.0', tk.END)
        self.match_count_var.set("")
        self.matches = []
        self.current_match = 0

class StatsBar(ttk.Frame):
    """Statistics bar showing word, character, and line counts"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Create labels for statistics
        self.word_count_var = tk.StringVar(value="Words: 0")
        self.char_count_var = tk.StringVar(value="Characters: 0")
        self.line_count_var = tk.StringVar(value="Lines: 0")
        
        # Create and pack labels
        ttk.Label(self, textvariable=self.word_count_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(self, textvariable=self.char_count_var).pack(side=tk.LEFT, padx=5)
        ttk.Label(self, textvariable=self.line_count_var).pack(side=tk.LEFT, padx=5)
    
    def update_stats(self, text):
        """Update statistics based on text content"""
        # Count words
        words = len(text.split())
        self.word_count_var.set(f"Words: {words}")
        
        # Count characters
        chars = len(text)
        self.char_count_var.set(f"Characters: {chars}")
        
        # Count lines
        lines = len(text.splitlines())
        self.line_count_var.set(f"Lines: {lines}")

class SplashScreen(tk.Toplevel):
    """Splash screen with loading indicator"""
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)  # Remove window decorations
        
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Set window size and position
        width = 400
        height = 200
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create gradient background
        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.create_gradient()
        
        # Title
        self.canvas.create_text(
            width/2, 60,
            text="Ebook Formatter Pro",
            font=("Segoe UI", 20, "bold"),
            fill="white"
        )
        
        # Loading text
        self.loading_text = self.canvas.create_text(
            width/2, 100,
            text="Loading...",
            font=("Segoe UI", 12),
            fill="white"
        )
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress.pack(fill=tk.X, padx=40, pady=20)
        
        # Status text
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            foreground="white",
            background="#0078d7"
        )
        self.status_label.pack(fill=tk.X, padx=40, pady=5)
        
        # Start progress animation
        self.animate_progress()
    
    def create_gradient(self):
        """Create gradient background"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Create gradient colors
        start_color = "#0078d7"
        end_color = "#106ebe"
        
        for i in range(height):
            pos = i / height
            color = self.blend_colors(start_color, end_color, pos)
            self.canvas.create_line(0, i, width, i, fill=color)
    
    def blend_colors(self, color1, color2, blend_factor):
        """Blend two colors based on blend factor (0 to 1)"""
        r1, g1, b1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
        r2, g2, b2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]
        
        r = int(r1 + (r2 - r1) * blend_factor)
        g = int(g1 + (g2 - g1) * blend_factor)
        b = int(b1 + (b2 - b1) * blend_factor)
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def animate_progress(self):
        """Animate the progress bar"""
        current = self.progress_var.get()
        if current < 100:
            self.progress_var.set(current + 1)
            self.after(20, self.animate_progress)
    
    def update_status(self, message):
        """Update the status message"""
        self.status_var.set(message)

class DocumentMiniMap(tk.Canvas):
    """Modern mini-map for document navigation"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(width=100, highlightthickness=0)
        self.bind('<Configure>', self.on_resize)
        self.bind('<Button-1>', self.on_click)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.on_release)
        
        # Variables
        self.text_widget = None
        self.viewport_height = 0
        self.document_height = 0
        self.scroll_ratio = 0
        self.dragging = False
        
        # Colors
        self.bg_color = THEMES["Light"]["frame_bg"]
        self.viewport_color = THEMES["Light"]["accent_color"]
        self.text_color = THEMES["Light"]["text_fg"]
        self.highlight_color = THEMES["Light"]["accent_hover"]
    
    def set_text_widget(self, text_widget):
        """Set the text widget to monitor"""
        self.text_widget = text_widget
        self.text_widget.bind('<Configure>', self.update_minimap)
        self.text_widget.bind('<Key>', self.update_minimap)
        self.text_widget.bind('<MouseWheel>', self.update_minimap)
    
    def on_resize(self, event):
        """Handle resize events"""
        self.update_minimap()
    
    def update_minimap(self, event=None):
        """Update the mini-map display"""
        if not self.text_widget:
            return
            
        # Get dimensions
        self.viewport_height = self.text_widget.winfo_height()
        self.document_height = int(self.text_widget.index('end-1c').split('.')[0])
        
        # Calculate scroll ratio
        first_visible = float(self.text_widget.index('@0,0').split('.')[0])
        self.scroll_ratio = first_visible / self.document_height
        
        # Redraw
        self.delete('all')
        self.draw_minimap()
    
    def draw_minimap(self):
        """Draw the mini-map visualization"""
        # Draw background
        self.configure(bg=self.bg_color)
        
        # Calculate dimensions
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Draw document representation
        line_height = height / self.document_height
        for i in range(self.document_height):
            y = i * line_height
            # Draw a line for each paragraph
            if self.text_widget.get(f"{i+1}.0", f"{i+1}.end").strip():
                self.create_line(0, y, width, y, fill=self.text_color, width=1)
        
        # Draw viewport indicator
        viewport_height = (self.viewport_height / self.document_height) * height
        viewport_y = self.scroll_ratio * height
        self.create_rectangle(
            0, viewport_y,
            width, viewport_y + viewport_height,
            fill=self.viewport_color,
            outline=self.highlight_color,
            width=2
        )
    
    def on_click(self, event):
        """Handle click events"""
        self.dragging = True
        self.scroll_to_position(event.y)
    
    def on_drag(self, event):
        """Handle drag events"""
        if self.dragging:
            self.scroll_to_position(event.y)
    
    def on_release(self, event):
        """Handle release events"""
        self.dragging = False
    
    def scroll_to_position(self, y):
        """Scroll text widget to clicked position"""
        if not self.text_widget:
            return
            
        # Calculate scroll position
        scroll_ratio = y / self.winfo_height()
        line = int(scroll_ratio * self.document_height)
        
        # Scroll text widget
        self.text_widget.see(f"{line}.0")

class CodeHighlighter:
    """Modern syntax highlighter for code blocks"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.patterns = {
            'keywords': r'\b(if|else|elif|for|while|def|class|import|from|return|try|except|finally|with|as|in|is|not|and|or|True|False|None)\b',
            'strings': r'"[^"\\]*(\\.[^"\\]*)*"|\'[^\'\\]*(\\.[^\'\\]*)*\'',
            'comments': r'#.*$',
            'numbers': r'\b\d+\b',
            'functions': r'\b\w+(?=\()',
            'operators': r'[+\-*/=<>!&|^~%]',
            'decorators': r'@\w+'
        }
        self.colors = {
            'keywords': '#FF6B6B',
            'strings': '#98C379',
            'comments': '#5C6370',
            'numbers': '#D19A66',
            'functions': '#61AFEF',
            'operators': '#56B6C2',
            'decorators': '#E5C07B'
        }
        
        # Configure tags
        for name, color in self.colors.items():
            self.text_widget.tag_configure(name, foreground=color)
    
    def highlight(self, start='1.0', end='end-1c'):
        """Apply syntax highlighting to the specified range"""
        content = self.text_widget.get(start, end)
        
        # Remove existing tags
        for tag in self.colors.keys():
            self.text_widget.tag_remove(tag, start, end)
        
        # Apply highlighting
        for name, pattern in self.patterns.items():
            for match in re.finditer(pattern, content, re.MULTILINE):
                start_index = f"{start}+{match.start()}c"
                end_index = f"{start}+{match.end()}c"
                self.text_widget.tag_add(name, start_index, end_index)

class EbookFormatterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ebook Formatter Pro")
        self.root.geometry("1200x800")
        
        # Initialize variables
        self.default_font = ("Segoe UI", 10)
        self.chapters = []
        self.cover_image_path = None
        self.current_preset = "Kindle"
        self.original_text = ""
        self.current_theme = "Light"
        self.auto_save_timer = None
        self.last_save = None
        self.operation_queue = Queue()
        self.processing = False
        self.debounce_timer = None
        
        # Create UI elements first
        self.create_basic_ui()
        
        # Start background initialization
        self.root.after(100, self.initialize_background)
    
    def create_basic_ui(self):
        """Create basic UI elements that don't require heavy processing"""
        # Add modern title bar
        self.title_bar = ModernTitleBar(self.root)
        
        # Configure styles
        self.setup_styles()
        
        # Create modern toolbar
        self.create_toolbar()
        
        # Create menu bar
        self.create_menu()
        
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create left panel (input and preview)
        self.left_panel = ttk.Frame(self.main_container)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create right panel (settings and chapters)
        self.right_panel = ttk.Frame(self.main_container)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Create input area
        self.create_input_area()
        
        # Create preview area
        self.create_preview_area()
        
        # Create settings panel
        self.create_settings_panel()
        
        # Create chapters panel
        self.create_chapters_panel()
        
        # Create progress bar
        self.progress = ModernProgressBar(self.root)
        self.progress.pack(fill=tk.X, padx=10, pady=5)
        
        # Create status bar
        self.create_status_bar()
        
        # Create statistics bar
        self.create_stats_bar()
        
        # Create mini-map
        self.mini_map = DocumentMiniMap(self.left_panel)
        self.mini_map.pack(fill=tk.X, padx=5, pady=5)
        
        # Apply theme
        self.apply_theme()
    
    def initialize_background(self):
        """Initialize heavy components in the background"""
        try:
            # Update title bar with initial format
            self.title_bar.update_format_indicator(self.current_preset)
            
            # Bind keyboard shortcuts
            self.bind_shortcuts()
            
            # Start background task processor
            self.process_background_tasks()
            
            # Start auto-save timer in background
            self.start_auto_save()
            
            # Update status
            self.update_status("Application ready", "success")
        except Exception as e:
            self.update_status(f"Error during initialization: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to initialize application: {str(e)}")

    def process_background_tasks(self):
        """Process background tasks from the queue"""
        try:
            while not self.operation_queue.empty():
                task = self.operation_queue.get_nowait()
                if task:
                    func, args, callback = task
                    future = thread_pool.submit(func, *args)
                    if callback:
                        self.root.after(100, lambda: self.check_future(future, callback))
        except Exception as e:
            print(f"Error processing background tasks: {e}")
        
        # Schedule next check
        self.root.after(100, self.process_background_tasks)

    def check_future(self, future, callback):
        """Check if a future is done and call the callback"""
        if future.done():
            try:
                result = future.result()
                callback(result)
            except Exception as e:
                print(f"Error in background task: {e}")
        else:
            self.root.after(100, lambda: self.check_future(future, callback))

    def run_in_background(self, func, *args, callback=None):
        """Run a function in the background thread pool"""
        self.operation_queue.put((func, args, callback))

    def start_auto_save(self):
        """Start auto-save timer in background"""
        def auto_save_task():
            if self.original_text:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"autosave_{timestamp}.txt"
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(self.original_text)
                    self.last_save = filename
                    self.root.after(0, lambda: self.update_status(f"Auto-saved to {filename}"))
                except Exception as e:
                    self.root.after(0, lambda: self.update_status(f"Auto-save failed: {str(e)}"))
        
        # Schedule next auto-save
        self.auto_save_timer = threading.Timer(300, self.start_auto_save)
        self.auto_save_timer.daemon = True
        self.auto_save_timer.start()
        
        # Run auto-save in background
        self.run_in_background(auto_save_task)

    def __del__(self):
        """Cleanup when the application is closed"""
        if self.auto_save_timer:
            self.auto_save_timer.cancel()
        thread_pool.shutdown(wait=False)

    def create_toolbar(self):
        """Create the modern toolbar"""
        self.toolbar = ModernToolbar(self.root)
        self.toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        # Connect toolbar buttons to actions
        self.toolbar.buttons["new"].configure(command=self.new_document)
        self.toolbar.buttons["open"].configure(command=self.import_text_file)
        self.toolbar.buttons["save"].configure(command=self.export_chapters_text)
        self.toolbar.buttons["undo"].configure(command=lambda: self.input_text.event_generate("<<Undo>>"))
        self.toolbar.buttons["redo"].configure(command=lambda: self.input_text.event_generate("<<Redo>>"))
        self.toolbar.buttons["cut"].configure(command=lambda: self.input_text.event_generate("<<Cut>>"))
        self.toolbar.buttons["copy"].configure(command=lambda: self.input_text.event_generate("<<Copy>>"))
        self.toolbar.buttons["paste"].configure(command=lambda: self.input_text.event_generate("<<Paste>>"))
        self.toolbar.buttons["format_kindle"].configure(command=lambda: self.format_for_platform("Kindle"))
        self.toolbar.buttons["format_google"].configure(command=lambda: self.format_for_platform("Google Books"))
        self.toolbar.buttons["format_print"].configure(command=lambda: self.format_for_platform("Print"))
        self.toolbar.buttons["zoom_in"].configure(command=self.zoom_in)
        self.toolbar.buttons["zoom_out"].configure(command=self.zoom_out)
        self.toolbar.buttons["theme"].configure(command=self.toggle_theme)

    def new_document(self):
        """Create a new document"""
        if messagebox.askyesno("New Document", "Do you want to save the current document?"):
            self.export_chapters_text()
        
        self.input_text.delete("1.0", tk.END)
        self.original_text = ""
        self.chapters = []
        self.chapter_listbox.delete(0, tk.END)
        self.update_status("New document created")

    def zoom_in(self):
        """Increase text size"""
        current_size = self.default_font[1]
        self.default_font = (self.default_font[0], current_size + 1)
        self.update_fonts()

    def zoom_out(self):
        """Decrease text size"""
        current_size = self.default_font[1]
        if current_size > 8:
            self.default_font = (self.default_font[0], current_size - 1)
            self.update_fonts()

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = "Dark" if self.current_theme == "Light" else "Light"
        self.change_theme(new_theme)

    def update_fonts(self):
        """Update fonts for all text widgets"""
        self.input_text.configure(font=self.default_font)
        self.preview_text.configure(font=self.default_font)
        self.chapter_listbox.configure(font=self.default_font)
        self.setup_styles()

    def update_status(self, message, status_type="info"):
        """Update the status bar message with type-based coloring"""
        theme = THEMES[self.current_theme]
        color = theme.get(f"{status_type}_color", theme["text_fg"])
        self.status_bar.configure(text=message, foreground=color)

    def bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.root.bind('<Control-n>', lambda e: self.new_document())
        self.root.bind('<Control-o>', lambda e: self.import_text_file())
        self.root.bind('<Control-s>', lambda e: self.export_chapters_text())
        self.root.bind('<Control-p>', lambda e: self.import_pdf_file())
        self.root.bind('<Control-i>', lambda e: self.import_cover_image())
        self.root.bind('<Control-e>', lambda e: self.export_chapters_pdf_editable())
        self.root.bind('<Control-k>', lambda e: self.format_for_platform("Kindle"))
        self.root.bind('<Control-g>', lambda e: self.format_for_platform("Google Books"))
        self.root.bind('<Control-r>', lambda e: self.format_for_platform("Print"))
        self.root.bind('<Control-f>', lambda e: self.show_search_dialog())
        self.root.bind('<Control-plus>', lambda e: self.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.zoom_out())
        self.root.bind('<Control-t>', lambda e: self.toggle_theme())

    def show_search_dialog(self):
        """Show the search and replace dialog"""
        SearchDialog(self.root, self.input_text)

    def detect_chapters(self):
        """Detect chapters from input text and populate listbox."""
        print("Detect chapters called")  # Debug output
        self.progress.start("Detecting chapters...")
        
        input_text = self.input_text.get("1.0", tk.END).strip()
        print(f"Input text length: {len(input_text)}")  # Debug output
        
        if not input_text:
            messagebox.showwarning("Warning", "Please enter some text to process.")
            self.progress.stop("Ready")
            return

        try:
            # Process chapters synchronously
            print("Processing chapters...")  # Debug output
            chapters = process_text(input_text)
            print(f"Processed chapters: {len(chapters)}")  # Debug output
            
            if chapters:
                self.chapters = chapters
                self.chapter_listbox.delete(0, tk.END)
                for chapter in self.chapters:
                    self.chapter_listbox.insert(tk.END, chapter["title"].strip())
                self.progress.stop(f"Found {len(self.chapters)} chapters")
                self.update_status(f"Detected {len(self.chapters)} chapters", "success")
            else:
                self.progress.stop("No chapters detected")
                self.update_status("No chapters detected", "warning")
        except Exception as e:
            print(f"Error in detect_chapters: {str(e)}")  # Debug output
            self.progress.stop("Error detecting chapters")
            self.update_status(f"Error detecting chapters: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to detect chapters: {str(e)}")

    def format_for_platform(self, platform):
        """Format text specifically for the selected platform."""
        self.progress.start(f"Formatting for {platform}...")
        
        if not self.original_text:
            self.original_text = self.input_text.get("1.0", tk.END).strip()
        
        if not self.original_text:
            messagebox.showwarning("Warning", "Please enter some text to format.")
            self.progress.stop("Ready")
            return

        try:
            # Get the preset for the platform
            preset = FORMATTING_PRESETS[platform]
            
            # Format the text based on platform-specific rules
            formatted_text = self.format_text_for_platform(self.original_text, platform, preset)
            
            # Update the input text with formatted content
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", formatted_text)
            
            # Update the current preset
            self.current_preset = platform
            self.platform_var.set(platform)
            
            # Update title bar format indicator if it exists
            if hasattr(self, 'title_bar'):
                self.title_bar.update_format_indicator(platform)
            
            # Clear existing chapters and listbox
            self.chapters = []
            self.chapter_listbox.delete(0, tk.END)
            
            # Process chapters in the main thread
            try:
                print("Detecting chapters after formatting...")  # Debug output
                chapters = process_text(formatted_text)
                if chapters:
                    self.chapters = chapters
                    for chapter in self.chapters:
                        self.chapter_listbox.insert(tk.END, chapter["title"].strip())
                    self.update_status(f"Detected {len(self.chapters)} chapters", "success")
                else:
                    self.update_status("No chapters detected", "warning")
            except Exception as e:
                print(f"Error detecting chapters: {str(e)}")  # Debug output
                self.update_status(f"Error detecting chapters: {str(e)}", "error")
            
            # Update preview after chapter detection
            self.update_preview()
            
            self.progress.stop("Formatting complete")
            self.update_status(f"Formatted for {platform}", "success")
        except Exception as e:
            self.progress.stop("Error formatting text")
            self.update_status(f"Error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to format text: {str(e)}")

    def format_text_for_platform(self, text, platform, preset):
        """Format text according to platform-specific rules"""
        try:
            # Split text into paragraphs
            paragraphs = text.split('\n\n')
            formatted_paragraphs = []
            
            for paragraph in paragraphs:
                # Clean up the paragraph
                paragraph = clean_text(paragraph)
                
                # Apply platform-specific formatting
                if platform in ["Kindle", "Google Books"]:
                    # Add proper spacing for e-readers
                    paragraph = paragraph.replace('. ', '.\n\n')
                    paragraph = paragraph.replace('! ', '!\n\n')
                    paragraph = paragraph.replace('? ', '?\n\n')
                    # Ensure proper dialogue formatting
                    paragraph = paragraph.replace('" "', '" "')
                elif platform == "Print":
                    # Add proper spacing for print
                    paragraph = paragraph.replace('. ', '. ')
                    paragraph = paragraph.replace('! ', '! ')
                    paragraph = paragraph.replace('? ', '? ')
                    # Ensure proper paragraph indentation
                    paragraph = "    " + paragraph
                
                formatted_paragraphs.append(paragraph)
            
            # Join paragraphs with appropriate spacing
            return '\n\n'.join(formatted_paragraphs)
        except Exception as e:
            print(f"Error in format_text_for_platform: {str(e)}")
            return text  # Return original text if formatting fails

    def export_chapters_text(self):
        """Export detected chapters to a plain text file."""
        if not self.chapters:
            messagebox.showwarning("Warning", "No chapters detected to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Chapters As",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if file_path:
            self.progress.start("Exporting chapters...")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for chapter in self.chapters:
                        f.write(f"{chapter['title']}\n\n")
                        f.write("\n".join(chapter['content']) + "\n\n")
                        f.write("-" * 50 + "\n\n")
                
                self.progress.stop("Export complete")
                self.update_status(f"Exported to {file_path}", "success")
                messagebox.showinfo("Success", f"Chapters exported to {file_path}")
            except Exception as e:
                self.progress.stop("Export failed")
                self.update_status(f"Error: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to export text file: {str(e)}")

    def export_chapters_pdf_editable(self):
        """Export detected chapters to a PDF with editable text, cover image, and basic TOC."""
        if not self.chapters:
            messagebox.showwarning("Warning", "No chapters detected to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Editable PDF As",
            defaultextension=".pdf",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if file_path:
            self.progress.start("Exporting PDF...")
            try:
                preset = FORMATTING_PRESETS[self.current_preset]
                doc = SimpleDocTemplate(
                    file_path,
                    pagesize=preset['page_size'],
                    leftMargin=preset['margins'][0],
                    rightMargin=preset['margins'][1],
                    topMargin=preset['margins'][2],
                    bottomMargin=preset['margins'][3]
                )
                
                # Create styles
                styles = self.create_pdf_styles(preset)
                
                # Build document
                story = self.build_pdf_story(styles)
                
                # Generate PDF
                doc.build(story)
                
                self.progress.stop("PDF export complete")
                self.update_status(f"Exported PDF to {file_path}", "success")
                messagebox.showinfo("Success", f"Editable PDF exported to {file_path}")
            except Exception as e:
                self.progress.stop("PDF export failed")
                self.update_status(f"Error: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")

    def create_pdf_styles(self, preset):
        """Create PDF styles based on preset"""
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='CustomHeading',
            fontName=preset['font_name'],
            fontSize=preset['chapter_title_size'],
            leading=preset['chapter_title_size'] * 1.2,
            spaceAfter=preset['chapter_title_spacing'],
            spaceBefore=preset['chapter_title_spacing']
        ))
        
        styles.add(ParagraphStyle(
            name='CustomBody',
            fontName=preset['font_name'],
            fontSize=preset['font_size'],
            leading=preset['font_size'] * preset['line_spacing'],
            spaceAfter=preset['paragraph_spacing'],
            spaceBefore=0,
            firstLineIndent=preset['first_line_indent'],
            leftIndent=0,
            rightIndent=0,
            wordWrap='CJK'
        ))
        
        styles.add(ParagraphStyle(
            name='TOCHeading1',
            fontName=preset['font_name'],
            fontSize=preset['font_size'] + 2,
            leading=preset['font_size'] * preset['line_spacing'],
            spaceAfter=preset['paragraph_spacing'],
            spaceBefore=0
        ))
        
        return styles

    def build_pdf_story(self, styles):
        """Build the PDF story with all content"""
        story = []
        
        # Cover image
        if self.cover_image_path:
            story.extend(self.add_cover_image(styles))
        
        # Table of Contents
        story.extend(self.add_table_of_contents(styles))
        
        # Chapters
        story.extend(self.add_chapters(styles))
        
        return story

    def add_cover_image(self, styles):
        """Add cover image to PDF"""
        with PILImage.open(self.cover_image_path) as img:
            img_width, img_height = img.size
        
        page_width, page_height = FORMATTING_PRESETS[self.current_preset]['page_size']
        scale = min(page_width / img_width, page_height / img_height)
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        
        return [
            Image(self.cover_image_path, width=scaled_width, height=scaled_height),
            PageBreak()
        ]

    def add_table_of_contents(self, styles):
        """Add table of contents to PDF"""
        return [
            Paragraph("Table of Contents", styles['CustomHeading']),
            Spacer(1, 24),
            *[Paragraph(chapter["title"], styles['TOCHeading1']) for chapter in self.chapters],
            PageBreak()
        ]

    def add_chapters(self, styles):
        """Add chapters to PDF"""
        story = []
        for chapter in self.chapters:
            story.append(Paragraph(chapter["title"], styles["CustomHeading"]))
            story.append(Spacer(1, 12))
            
            for paragraph in chapter["content"]:
                # Clean up paragraph text
                paragraph = clean_text(paragraph)
                # Ensure proper spacing around dialogue
                paragraph = re.sub(r'"\s*"', '" "', paragraph)
                # Add proper spacing after punctuation
                paragraph = re.sub(r'([.!?])([A-Z])', r'\1 \2', paragraph)
                story.append(Paragraph(paragraph, styles["CustomBody"]))
            story.append(Spacer(1, 24))
        
        return story

    def setup_styles(self):
        """Configure ttk styles for the application"""
        style = ttk.Style()
        
        # Configure default style
        style.configure("TFrame", background=THEMES[self.current_theme]["frame_bg"])
        style.configure("TLabel", 
                       background=THEMES[self.current_theme]["frame_bg"],
                       foreground=THEMES[self.current_theme]["text_fg"])
        style.configure("TButton",
                       background=THEMES[self.current_theme]["button_bg"],
                       foreground=THEMES[self.current_theme]["button_fg"],
                       padding=5)
        
        # Configure accent button style
        style.configure("Accent.TButton",
                       background=THEMES[self.current_theme]["accent_color"],
                       foreground="white")
        
        # Configure listbox style
        style.configure("TListbox",
                       background=THEMES[self.current_theme]["listbox_bg"],
                       foreground=THEMES[self.current_theme]["listbox_fg"],
                       selectbackground=THEMES[self.current_theme]["listbox_select_bg"],
                       selectforeground=THEMES[self.current_theme]["listbox_select_fg"])
        
        # Configure progress bar style
        style.configure("Horizontal.TProgressbar",
                       background=THEMES[self.current_theme]["accent_color"],
                       troughcolor=THEMES[self.current_theme]["frame_bg"])
        
        # Configure separator style
        style.configure("TSeparator",
                       background=THEMES[self.current_theme]["frame_bg"])

    def create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_document, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self.import_text_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.export_chapters_text, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Import PDF", command=self.import_pdf_file, accelerator="Ctrl+P")
        file_menu.add_command(label="Import Cover Image", command=self.import_cover_image, accelerator="Ctrl+I")
        file_menu.add_command(label="Export PDF", command=self.export_chapters_pdf_editable, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=lambda: self.input_text.event_generate("<<Undo>>"), accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=lambda: self.input_text.event_generate("<<Redo>>"), accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.input_text.event_generate("<<Cut>>"), accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=lambda: self.input_text.event_generate("<<Copy>>"), accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=lambda: self.input_text.event_generate("<<Paste>>"), accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find/Replace", command=self.show_search_dialog, accelerator="Ctrl+F")
        
        # Format menu
        format_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Format", menu=format_menu)
        format_menu.add_command(label="Format for Kindle", command=lambda: self.format_for_platform("Kindle"), accelerator="Ctrl+K")
        format_menu.add_command(label="Format for Google Books", command=lambda: self.format_for_platform("Google Books"), accelerator="Ctrl+G")
        format_menu.add_command(label="Format for Print", command=lambda: self.format_for_platform("Print"), accelerator="Ctrl+R")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme, accelerator="Ctrl+T")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)

    def import_text_file(self):
        """Import text from a file"""
        file_path = filedialog.askopenfilename(
            title="Import Text File",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if file_path:
            self.progress.start("Importing text file...")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", text)
                self.original_text = text
                
                # Automatically detect chapters after import
                self.detect_chapters()
                
                self.progress.stop("Import complete")
                self.update_status(f"Imported text from {file_path}", "success")
            except Exception as e:
                self.progress.stop("Import failed")
                self.update_status(f"Error: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to import text file: {str(e)}")

    def import_pdf_file(self):
        """Import text from a PDF file"""
        file_path = filedialog.askopenfilename(
            title="Import PDF File",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if file_path:
            self.progress.start("Importing PDF file...")
            try:
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", text)
                self.original_text = text
                self.progress.stop("Import complete")
                self.update_status(f"Imported PDF from {file_path}", "success")
            except Exception as e:
                self.progress.stop("Import failed")
                self.update_status(f"Error: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to import PDF file: {str(e)}")

    def import_cover_image(self):
        """Import a cover image for the ebook"""
        file_path = filedialog.askopenfilename(
            title="Import Cover Image",
            filetypes=(("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*"))
        )
        if file_path:
            try:
                self.cover_image_path = file_path
                self.update_status(f"Cover image imported from {file_path}", "success")
            except Exception as e:
                self.update_status(f"Error: {str(e)}", "error")
                messagebox.showerror("Error", f"Failed to import cover image: {str(e)}")

    def show_about_dialog(self):
        """Show the about dialog"""
        messagebox.showinfo(
            "About Ebook Formatter Pro",
            "Ebook Formatter Pro\nVersion 1.0\n\n"
            "A modern application for formatting and preparing ebooks "
            "for various platforms including Kindle, Google Books, and print.\n\n"
            "© 2024 All rights reserved."
        )

    def create_input_area(self):
        """Create the input text area"""
        input_frame = ttk.LabelFrame(self.left_panel, text="Input Text")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            font=self.default_font,
            bg=THEMES[self.current_theme]["text_bg"],
            fg=THEMES[self.current_theme]["text_fg"]
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create search bar
        self.search_bar = ModernSearchBar(input_frame)
        self.search_bar.pack(fill=tk.X, padx=5, pady=5)
        self.search_bar.set_text_widget(self.input_text)
        
        # Create button frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Import buttons
        import_frame = ttk.Frame(button_frame)
        import_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="Import Text", command=self.import_text_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(import_frame, text="Import PDF", command=self.import_pdf_file).pack(side=tk.LEFT, padx=2)
        
        # Auto-preview toggle
        self.auto_preview = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="Auto-preview", variable=self.auto_preview).pack(side=tk.RIGHT, padx=2)
        
        # Bind text change event
        self.input_text.bind('<<Modified>>', self.on_text_change)
        
    def create_preview_area(self):
        """Create the preview text area"""
        preview_frame = ttk.LabelFrame(self.left_panel, text="Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            wrap=tk.WORD,
            font=self.default_font,
            bg=THEMES[self.current_theme]["text_bg"],
            fg=THEMES[self.current_theme]["text_fg"]
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create button frame
        button_frame = ttk.Frame(preview_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Preview buttons
        ttk.Button(button_frame, text="Update Preview", command=self.update_preview).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear Preview", command=lambda: self.preview_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=2)

    def create_settings_panel(self):
        """Create the settings panel"""
        settings_frame = ttk.LabelFrame(self.right_panel, text="Settings")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Platform selection
        platform_frame = ttk.Frame(settings_frame)
        platform_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(platform_frame, text="Format Platform:").pack(side=tk.LEFT)
        self.platform_var = tk.StringVar(value=self.current_preset)
        platform_combo = ttk.Combobox(
            platform_frame,
            textvariable=self.platform_var,
            values=list(FORMATTING_PRESETS.keys()),
            state="readonly"
        )
        platform_combo.pack(side=tk.LEFT, padx=5)
        platform_combo.bind('<<ComboboxSelected>>', lambda e: self.format_for_platform(self.platform_var.get()))

    def create_chapters_panel(self):
        """Create the chapters panel"""
        chapters_frame = ttk.LabelFrame(self.right_panel, text="Chapters")
        chapters_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create listbox
        self.chapter_listbox = tk.Listbox(
            chapters_frame,
            font=self.default_font,
            bg=THEMES[self.current_theme]["listbox_bg"],
            fg=THEMES[self.current_theme]["listbox_fg"],
            selectbackground=THEMES[self.current_theme]["listbox_select_bg"],
            selectforeground=THEMES[self.current_theme]["listbox_select_fg"]
        )
        self.chapter_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.chapter_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
        # Create button frame
        button_frame = ttk.Frame(chapters_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Chapter buttons
        ttk.Button(button_frame, text="Detect Chapters", command=self.detect_chapters).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear Chapters", command=lambda: self.chapter_listbox.delete(0, tk.END)).pack(side=tk.LEFT, padx=2)

    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = ttk.Label(
            self.root,
            text="Ready",
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_bar.pack(fill=tk.X, padx=10, pady=2)

    def create_stats_bar(self):
        """Create the statistics bar"""
        self.stats_bar = StatsBar(self.root)
        self.stats_bar.pack(fill=tk.X, padx=10, pady=2)

    def apply_theme(self):
        """Apply the current theme to the application"""
        style = ttk.Style()
        style.configure("TFrame", background=THEMES[self.current_theme]["frame_bg"])
        style.configure("TLabel", 
                       background=THEMES[self.current_theme]["frame_bg"],
                       foreground=THEMES[self.current_theme]["text_fg"])
        style.configure("TButton",
                       background=THEMES[self.current_theme]["button_bg"],
                       foreground=THEMES[self.current_theme]["button_fg"],
                       padding=5)
        
        style.configure("Accent.TButton",
                       background=THEMES[self.current_theme]["accent_color"],
                       foreground="white")
        
        style.configure("TListbox",
                       background=THEMES[self.current_theme]["listbox_bg"],
                       foreground=THEMES[self.current_theme]["listbox_fg"],
                       selectbackground=THEMES[self.current_theme]["listbox_select_bg"],
                       selectforeground=THEMES[self.current_theme]["listbox_select_fg"])
        
        style.configure("Horizontal.TProgressbar",
                       background=THEMES[self.current_theme]["accent_color"],
                       troughcolor=THEMES[self.current_theme]["frame_bg"])
        
        style.configure("TSeparator",
                       background=THEMES[self.current_theme]["frame_bg"])

    def update_preview(self):
        """Update the preview area with formatted text"""
        try:
            # Get current text
            text = self.input_text.get("1.0", tk.END).strip()
            if not text:
                self.preview_text.delete("1.0", tk.END)
                return
            
            # Process chapters
            chapters = process_text(text)
            
            # Update preview
            self.preview_text.delete("1.0", tk.END)
            for chapter in chapters:
                self.preview_text.insert(tk.END, f"{chapter['title']}\n\n")
                self.preview_text.insert(tk.END, "\n".join(chapter['content']) + "\n\n")
                self.preview_text.insert(tk.END, "-" * 50 + "\n\n")
            
            # Update status
            self.update_status(f"Preview updated with {len(chapters)} chapters")
        except Exception as e:
            self.update_status(f"Error updating preview: {str(e)}", "error")

    def on_chapter_select(self, event):
        """Handle chapter selection from listbox"""
        selection = self.chapter_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if 0 <= index < len(self.chapters):
            chapter = self.chapters[index]
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.insert("1.0", f"{chapter['title']}\n\n")
            self.preview_text.insert(tk.END, "\n".join(chapter['content']))
            self.update_status(f"Selected chapter: {chapter['title']}")

    def on_text_change(self, event):
        """Handle text changes in input area"""
        if self.auto_preview.get():
            self.update_preview()
        
        # Update statistics
        text = self.input_text.get("1.0", tk.END)
        self.stats_bar.update_stats(text)
        
        # Reset modified flag
        self.input_text.edit_modified(False)

    def change_theme(self, new_theme):
        """Change the application theme"""
        if new_theme not in THEMES:
            return
            
        self.current_theme = new_theme
        
        # Update text widgets
        self.input_text.configure(
            bg=THEMES[new_theme]["text_bg"],
            fg=THEMES[new_theme]["text_fg"]
        )
        self.preview_text.configure(
            bg=THEMES[new_theme]["text_bg"],
            fg=THEMES[new_theme]["text_fg"]
        )
        
        # Update chapter listbox
        self.chapter_listbox.configure(
            bg=THEMES[new_theme]["listbox_bg"],
            fg=THEMES[new_theme]["listbox_fg"],
            selectbackground=THEMES[new_theme]["listbox_select_bg"],
            selectforeground=THEMES[new_theme]["listbox_select_fg"]
        )
        
        # Update status bar
        self.status_bar.configure(
            bg=THEMES[new_theme]["status_bg"],
            fg=THEMES[new_theme]["status_fg"]
        )
        
        # Apply theme to all widgets
        self.apply_theme()
        
        # Update status
        self.update_status(f"Theme changed to {new_theme}")

def main():
    print("Starting Ebook Formatter...")
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Create and show splash screen
    splash = SplashScreen(root)
    
    def initialize_app():
        try:
            # Initialize NLTK in background
            splash.update_status("Initializing text processing...")
            init_nltk()
            
            # Create the main application
            splash.update_status("Creating application interface...")
            app = EbookFormatterApp(root)
            
            # Hide splash screen and show main window
            splash.destroy()
            root.deiconify()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize application: {str(e)}")
            root.quit()
    
    # Start initialization in background
    root.after(100, initialize_app)
    root.mainloop()

if __name__ == "__main__":
    main()
        
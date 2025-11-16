import sys
# Add to top of your main script

# Exclude heavy packages you don't use
excluded_packages = [
    'matplotlib', 'scipy', 'sklearn', 'pandas', 'numpy',  # Only if you don't use them
    'PIL.ImageQt', 'PIL.ImageTk',  # Unused Pillow components
    'pyautogui._pyautogui_osx', 'pyautogui._pyautogui_x11',  # Platform-specific
]
for package in excluded_packages:
    if package in sys.modules:
        del sys.modules[package]

from pathlib import Path
# Import the ETailPlugin class
try:
    from plugins.etail_plugin import ETailPlugin
except ImportError:
    # Fallback: define it here if not found
    from abc import ABC, abstractmethod
    import json  # ADD THIS IMPORT
    import sys   # ADD THIS IMPORT
    from pathlib import Path  # ADD THIS IMPORT

    class ETailPlugin(ABC):
        def __init__(self, app):
            self.app = app
            # Only set default name if not already set by subclass
            if not hasattr(self, 'name') or getattr(self, 'name', None) == "Unnamed Plugin":
                self.name = "Unnamed Plugin"
            if not hasattr(self, 'version'):
                self.version = "1.0" 
            if not hasattr(self, 'description'):
                self.description = "No description provided"
            
            # Instance identification
            self.instance_id = getattr(app, 'instance_id', 'standalone')
            print(f"DEBUG: Plugin {self.name} loaded for instance: {self.instance_id}")
            
            # Instance-specific configuration
            self.config = self.load_config()
            
        def load_config(self):
            """Load instance-specific configuration - FIXED with better error handling"""
            config_path = self.get_config_path()
            print(f"DEBUG: Attempting to load config from: {config_path}")
            print(f"DEBUG: Config file exists: {config_path.exists()}")
            
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        print(f"DEBUG: Config file content length: {len(content)}")
                        
                        if not content:
                            print(f"DEBUG: Config file is empty")
                            default_config = self.get_default_config()
                            print(f"DEBUG: Using default config for {self.name} in instance {self.instance_id}")
                            return default_config
                        
                        config = json.loads(content)
                        print(f"DEBUG: Successfully loaded config for {self.name} from {config_path}")
                        print(f"DEBUG: Config keys: {list(config.keys()) if config else 'None'}")
                        return config
                        
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error in config for {self.name}: {e}")
                    print(f"DEBUG: Problematic content: '{content}'")
                except Exception as e:
                    print(f"DEBUG: Error loading config for {self.name}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Return default config if no instance-specific config exists or there was an error
            default_config = self.get_default_config()
            print(f"DEBUG: Using default config for {self.name} in instance {self.instance_id}")
            return default_config

        def save_config(self):
            """Save instance-specific configuration"""
            config_path = self.get_config_path()
            try:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                print(f"DEBUG: Saved config for {self.name} to {config_path}")
                return True
            except Exception as e:
                print(f"DEBUG: Error saving config for {self.name}: {e}")
                return False
        
        def get_config_path(self):
            """Get instance-specific config file path"""
            # Use the plugin manager's config directory
            if hasattr(self.app, 'plugin_manager') and hasattr(self.app.plugin_manager, 'plugin_config_dir'):
                return self.app.plugin_manager.plugin_config_dir / f"{self.name}.json"
            else:
                # Fallback
                if getattr(sys, 'frozen', False):
                    base_dir = Path(sys.executable).parent
                else:
                    base_dir = Path(__file__).parent
                
                if hasattr(self.app, 'instance_id'):
                    config_dir = base_dir / "instances" / self.app.instance_id / "plugins"
                    config_dir.mkdir(parents=True, exist_ok=True)
                    return config_dir / f"{self.name}.json"
                else:
                    config_dir = base_dir / "plugins" / "config"
                    config_dir.mkdir(parents=True, exist_ok=True)
                    return config_dir / f"{self.name}.json"
        
        def get_default_config(self):
            """Override this to provide default configuration"""
            return {}
        
        @abstractmethod
        def setup(self): 
            pass
                    
        @abstractmethod 
        def teardown(self): 
            pass

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from tkinter.colorchooser import askcolor


import pyautogui #needed by OCR
from PIL import Image, ImageTk, ImageEnhance, ImageFilter #needed by OCR
import win32gui #needed by OCR
import win32ui #needed by OCR
import win32con #needed by OCR
import win32process #needed by OCR
import pytesseract #needed by OCR
import ctypes #needed by OCR
from ctypes import wintypes #needed by OCR
from enum import Enum #needed by OCR
import numpy as np #needed by OCR
import psutil  # needed by OCR
import mss #needed by OCR
import mss.tools #needed by OCR

import os
import chardet
import threading
from threading import Thread, Event
import time
import re
import json
import pygame
import pyttsx3
import importlib
import importlib.util
import inspect
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import socket
import ssl
import hashlib

try:
    from plyer import notification
    HAS_SYSTEM_NOTIFICATIONS = True
    print("Plyer available for system notifications")
except ImportError:
    HAS_SYSTEM_NOTIFICATIONS = False
    print("Plyer not available for system notifications")

from abc import ABC, abstractmethod

"""A Tuple of fixed messages coded by index.
Set as global to be used anywhere.
index   string
0       Running
1       Stopped
2       Ready
3       Error
4       Paused
5       Detected file encoding:
6       Filter added.
7       Filter removed.
8       Index out of bonds.
9       Sucess.
"""
mssgs = ("Running",
"Stopped",
"Ready",
"Error",
"Paused",
"Detected file encoding: ",
"Filter added.",
"Filter removed.",
"Index out of bonds.",
"Success")


# ****************************************************************************
# *************************** Style Manager **********************************
# ****************************************************************************

class StyleManager:
    """Centralized styling management for ETail application"""
    
    def __init__(self, root=None):
        self.root = root
        self.style = ttk.Style()
        
        # Default style settings
        self.style_settings = {
            'primary_color': '#2c3e50',
            'secondary_color': '#3498db',
            'success_color': '#27ae60',
            'warning_color': '#f39c12',
            'danger_color': '#e74c3c',
            'light_bg': '#ecf0f1',
            'dark_bg': '#34495e',
            'text_primary': '#2c3e50',
            'text_light': '#ffffff',
            'text_dark': '#000000',
            'font_family': 'Arial',
            'font_size': 9,
            'theme': 'classic',
            'disabled_color': '#c0c0c0',
            'window_styles': {}  # Add window styles to defaults
        }
        
        # Initialize required attributes for compatibility
        self._setup_attributes()

    def _setup_attributes(self):
        """Setup instance attributes for backward compatibility"""
        for key, value in self.style_settings.items():
            setattr(self, key, value)

    def update_style_settings(self, new_settings):
        """Update style settings and refresh attributes"""
        self.style_settings.update(new_settings)
        self._setup_attributes()

    def get_style_settings(self):
        """Get current style settings"""
        return self.style_settings.copy()

    def configure_styles(self):
        """Configure comprehensive granular styling for ALL widget types"""
        
        # Use the style_settings dictionary directly instead of individual variables
        primary = self.style_settings['primary_color']
        secondary = self.style_settings['secondary_color']
        success = self.style_settings['success_color']
        warning = self.style_settings['warning_color']
        danger = self.style_settings['danger_color']
        light_bg = self.style_settings['light_bg']
        dark_bg = self.style_settings['dark_bg']
        disabled = self.style_settings['disabled_color']
        text_primary = self.style_settings['text_primary']
        text_light = self.style_settings['text_light']
        text_dark = self.style_settings['text_dark']
        font_family = self.style_settings['font_family']
        font_size = self.style_settings['font_size']
        
        # WIDGET-SPECIFIC STYLE CONFIGURATIONS
        style_configs = {
            # ========== BASE STYLES ==========
            '.': {
                'background': light_bg,
                'foreground': text_primary,
                'font': (font_family, font_size)
            },
            
            # ========== FRAME STYLES ==========
            'TFrame': {
                'background': light_bg
            },
            'Primary.TFrame': {
                'background': light_bg
            },
            'Secondary.TFrame': {
                'background': dark_bg
            },
            
            # ========== LABEL STYLES ==========
            'TLabel': {
                'background': light_bg,
                'foreground': text_primary,
                'font': (font_family, font_size)
            },
            'Title.TLabel': {
                'font': (font_family, 12, 'bold'),
                'foreground': text_primary,
                'background': light_bg
            },
            'Subtitle.TLabel': {
                'font': (font_family, 10, 'bold'), 
                'foreground': secondary,
                'background': light_bg
            },
            'Success.TLabel': {
                'foreground': success,
                'background': light_bg,
                'font': (font_family, font_size)
            },
            'Warning.TLabel': {
                'foreground': warning,
                'background': light_bg,
                'font': (font_family, font_size)
            },
            'Error.TLabel': {
                'foreground': danger,
                'background': light_bg,
                'font': (font_family, font_size)
            },
            
            # ========== BUTTON STYLES ==========
            'TButton': {
                'font': (font_family, font_size),
                'background': secondary,
                'foreground': text_light,
                'focuscolor': 'none',
                'padding': (10, 5)
            },
            'Primary.TButton': {
                'background': secondary,
                'foreground': text_light
            },
            'Secondary.TButton': {
                'background': primary,
                'foreground': text_light
            },
            'Success.TButton': {
                'background': success,
                'foreground': text_light
            },
            'Warning.TButton': {
                'background': warning,
                'foreground': text_dark
            },
            'Danger.TButton': {
                'background': danger, 
                'foreground': text_light
            },
            
            # ========== ENTRY STYLES ==========
            'TEntry': {
                'fieldbackground': 'white',
                'foreground': text_dark,
                'font': (font_family, font_size),
                'borderwidth': 1,
                'relief': 'solid',
                'padding': (5, 2)
            },
            'Modern.TEntry': {
                'fieldbackground': 'white',
                'foreground': text_dark,
                'font': (font_family, font_size),
                'padding': (5, 2)
            },
            
            # ========== COMBOBOX STYLES ==========
            'TCombobox': {
                'fieldbackground': 'white',
                'background': 'white',
                'foreground': text_dark,
                'font': (font_family, font_size),
                'arrowcolor': primary,
                'padding': (5, 2)
            },
            
            # ========== NOTEBOOK STYLES ==========
            'TNotebook': {
                'background': light_bg,
                'tabmargins': [2, 5, 2, 0]
            },
            'TNotebook.Tab': {
                'padding': [15, 5],
                'background': light_bg,
                'foreground': text_primary,
                'font': (font_family, font_size, 'bold')
            },
            'Custom.TNotebook': {
                'background': light_bg
            },
            'Custom.TNotebook.Tab': {
                'padding': [15, 5],
                'font': (font_family, font_size, 'bold'),
                'background': light_bg,
                'foreground': text_primary
            },
            
            # ========== TREEVIEW STYLES ==========
            'Treeview': {
                'background': 'white',
                'foreground': text_dark,
                'fieldbackground': 'white',
                'font': (font_family, font_size),
                'rowheight': 25
            },
            'Treeview.Heading': {
                'background': primary,
                'foreground': text_light,
                'font': (font_family, font_size, 'bold'),
                'padding': (5, 2)
            },
            
            # ========== SCROLLBAR STYLES ==========
            'Vertical.TScrollbar': {
                'background': light_bg,
                'troughcolor': dark_bg,
                'arrowcolor': primary
            },
            'Horizontal.TScrollbar': {
                'background': light_bg,
                'troughcolor': dark_bg,
                'arrowcolor': primary
            },
            
            # ========== LABELFRAME STYLES ==========
            'TLabelframe': {
                'background': light_bg,
                'foreground': text_primary,
                'borderwidth': 2
            },
            'TLabelframe.Label': {
                'font': (font_family, font_size, 'bold'),
                'foreground': text_primary,
                'background': light_bg
            },
            'Custom.TLabelframe': {
                'background': light_bg,
                'relief': 'solid',
                'borderwidth': 1
            },
            'Custom.TLabelframe.Label': {
                'font': (font_family, font_size, 'bold'),
                'foreground': text_primary,
                'background': light_bg
            },
            
            # ========== CHECKBUTTON & RADIOBUTTON STYLES ==========
            'TCheckbutton': {
                'background': light_bg,
                'foreground': text_primary,
                'font': (font_family, font_size)
            },
            'TRadiobutton': {
                'background': light_bg,
                'foreground': text_primary,
                'font': (font_family, font_size)
            },
            
            # ========== SEPARATOR STYLES ==========
            'TSeparator': {
                'background': dark_bg
            },
            
            # ========== STATUS STYLES ==========
            'Status.Running.TLabel': {
                'foreground': success,
                'font': (font_family, font_size, 'bold'),
                'background': light_bg
            },
            'Status.Stopped.TLabel': {
                'foreground': danger,
                'font': (font_family, font_size, 'bold'),
                'background': light_bg
            },
            'Status.Paused.TLabel': {
                'foreground': warning,
                'font': (font_family, font_size, 'bold'),
                'background': light_bg
            }
        }
        
        # Apply all style configurations
        for style_name, config in style_configs.items():
            try:
                self.style.configure(style_name, **config)
            except tk.TclError as e:
                print(f"DEBUG: Style configuration failed for {style_name}: {e}")
        
        # Configure style maps for interactive states
        self._configure_style_maps(primary, secondary, success, warning, danger, light_bg, dark_bg, disabled, text_light, text_dark)

        # Apply button styles AFTER base styles and maps
        button_styles = self.style_settings.get('button_styles')
        if button_styles:
            self.configure_button_styles(button_styles)
        else:
            print("DEBUG: No button styles found in settings")
            
        # Apply text input styles
        text_input_styles = self.style_settings.get('text_input_styles')
        if text_input_styles:
            self.configure_text_input_styles(text_input_styles)
        else:
            print("DEBUG: No text input styles found in settings")

        # Apply treeview styles - ADD THIS
        treeview_styles = self.style_settings.get('treeview_styles')
        if treeview_styles:
            self.configure_treeview_styles(treeview_styles)
        else:
            print("DEBUG: No treeview styles found in settings")

        # Apply window styles - ADD THIS
        window_styles = self.style_settings.get('window_styles')
        if window_styles:
            self.configure_window_styles(window_styles)
        else:
            print("DEBUG: No window styles found in settings")

        # APPLY COMBOBOX POPDOWN STYLES - ADD THIS
        self.configure_enhanced_combobox_styles()
        self.configure_scrollbar_styles()

    def configure_scrollbar_styles(self):
        """Configure scrollbar styles using correct ttk options"""
        try:
            # Get colors from your style settings
            bg_color = self.style_settings.get('bg_color', '#f0f0f0')
            trough_color = self.style_settings.get('bg_color', '#e0e0e0')
            thumb_color = self.style_settings.get('dark_bg', '#0078d4')
            thumb_hover = self.style_settings.get('light_bg', '#005a9e')
            
            # Configure VERTICAL scrollbar with correct options
            self.style.configure("Vertical.TScrollbar",
                background=thumb_color,
                troughcolor=trough_color,
                bordercolor=bg_color,
                relief="flat",
                borderwidth=1)
            # Remove the width option - ttk Scrollbar doesn't support it
                
            # Configure HORIZONTAL scrollbar with correct options
            self.style.configure("Horizontal.TScrollbar",
                background=thumb_color, 
                troughcolor=trough_color,
                bordercolor=bg_color,
                relief="flat", 
                borderwidth=1)
            # Remove the width option - ttk Scrollbar doesn't support it
            
            # Map states for both
            self.style.map("Vertical.TScrollbar",
                background=[('active', thumb_hover), ('pressed', thumb_hover)],
                troughcolor=[('active', trough_color)])
                
            self.style.map("Horizontal.TScrollbar", 
                background=[('active', thumb_hover), ('pressed', thumb_hover)],
                troughcolor=[('active', trough_color)])
                
            print("Scrollbar styles configured successfully")
            
        except Exception as e:
            print(f"Scrollbar style error: {e}")

    def _configure_style_maps(self, primary, secondary, success, warning, danger, light_bg, dark_bg, disabled, text_light, text_dark):
        """Configure comprehensive style maps for all widget states"""
        
        # ========== BUTTON STATE MAPPINGS ==========
        button_states = {
            'background': [
                ('active', primary), 
                ('pressed', dark_bg), 
                ('disabled', disabled)
            ],
            'foreground': [
                ('active', text_light), 
                ('pressed', text_light), 
                ('disabled', disabled)
            ]
        }
        
        self.style.map('TButton', **button_states)
        self.style.map('Primary.TButton', **button_states)
        self.style.map('Secondary.TButton', **button_states)
        self.style.map('Success.TButton', **button_states)
        
        # Warning button has different text colors
        self.style.map('Warning.TButton',
            background=[
                ('active', warning), 
                ('pressed', '#e67e22'), 
                ('disabled', disabled)
            ],
            foreground=[
                ('active', text_dark), 
                ('pressed', text_dark), 
                ('disabled', disabled)
            ]
        )
        
        self.style.map('Danger.TButton', **button_states)
        
        # ========== NOTEBOOK TAB STATE MAPPINGS ==========
        self.style.map('TNotebook.Tab',
            background=[
                ('selected', secondary), 
                ('active', secondary)
            ],
            foreground=[
                ('selected', text_light), 
                ('active', text_light)
            ]
        )
        
        # ========== ENTRY STATE MAPPINGS ==========
        self.style.map('TEntry',
            fieldbackground=[
                ('disabled', light_bg),
                ('readonly', light_bg),
                ('focus', 'white')
            ],
            foreground=[
                ('disabled', disabled),
                ('readonly', self.style_settings['text_primary'])  # Use text_primary from settings
            ],
            bordercolor=[
                ('focus', secondary),
                ('hover', primary)
            ]
        )
        
        # ========== ENHANCED COMBOBOX STATE MAPPINGS ==========
        self.style.map('TCombobox',
            fieldbackground=[
                ('disabled', light_bg),
                ('readonly', 'white'),
                ('focus', 'white'),
                ('hover', 'white')
            ],
            background=[
                ('disabled', light_bg),
                ('readonly', 'white'),
                ('focus', 'white')
            ],
            foreground=[
                ('disabled', disabled),
                ('readonly', text_dark),
                ('focus', text_dark)
            ],
            selectbackground=[
                ('focus', secondary),
                ('readonly', secondary)
            ],
            selectforeground=[
                ('focus', text_light),
                ('readonly', text_light)
            ],
            arrowcolor=[
                ('disabled', disabled),
                ('pressed', text_light),
                ('active', secondary),
                ('hover', secondary)
            ],
            bordercolor=[
                ('focus', secondary),
                ('hover', primary),
                ('active', secondary),
                ('disabled', disabled)
            ]
        )        
        # ========== TREEVIEW STATE MAPPINGS ==========
        self.style.map('Treeview',
            background=[
                ('selected', secondary)
            ],
            foreground=[
                ('selected', text_light)
            ]
        )

    def apply_theme(self, theme_name):
        """Apply a ttk theme"""
        try:
            available_themes = self.style.theme_names()
            if theme_name in available_themes:
                self.style.theme_use(theme_name)
                self.style_settings['theme'] = theme_name
                return True
            else:
                print(f"DEBUG: Theme '{theme_name}' not available. Available: {available_themes}")
                return False
        except Exception as e:
            print(f"DEBUG: Error applying theme: {e}")
            return False

    def apply_styles_to_widgets(self, parent):
        """Apply styles to all widgets in a parent container"""
        self.style_ttk_widgets(parent)
        self.style_text_widgets(parent)

    def style_ttk_widgets(self, parent):
        """Recursively apply ttk styles to all ttk widgets"""
        try:
            for child in parent.winfo_children():
                widget_class = child.winfo_class()
                
                # Apply appropriate style based on widget type
                if isinstance(child, ttk.Button):
                    current_style = str(child.cget('style') or '')
                    if 'success' in current_style or 'Success' in current_style:
                        child.configure(style='Success.TButton')
                    elif 'danger' in current_style or 'Danger' in current_style:
                        child.configure(style='Danger.TButton')
                    elif 'warning' in current_style or 'Warning' in current_style:
                        child.configure(style='Warning.TButton')
                    elif 'secondary' in current_style or 'Secondary' in current_style:
                        child.configure(style='Secondary.TButton')
                    else:
                        child.configure(style='Primary.TButton')
                        
                elif isinstance(child, ttk.Entry):
                    child.configure(style='Modern.TEntry')
                    
                elif isinstance(child, ttk.Combobox):
                    child.configure(style='TCombobox')
                    # Additional configuration for combobox
                    try:
                        # Set the state to readonly if it's a dropdown (common case)
                        current_state = str(child.cget('state'))
                        if current_state == 'readonly':
                            # Ensure readonly state gets proper styling
                            child.configure(state='readonly')
                    except:
                        pass
                elif isinstance(child, ttk.Treeview):
                    child.configure(style='Treeview')
                    self._configure_treeview_style(child)
                    
                elif isinstance(child, ttk.Label):
                    current_text = child.cget('text') if hasattr(child, 'cget') else ''
                    if 'Running' in str(current_text):
                        child.configure(style='Status.Running.TLabel')
                    elif 'Stopped' in str(current_text):
                        child.configure(style='Status.Stopped.TLabel')
                    elif 'Paused' in str(current_text):
                        child.configure(style='Status.Paused.TLabel')
                    elif any(x in str(child.cget('style') or '') for x in ['Title', 'Subtitle', 'Success', 'Warning', 'Error']):
                        pass  # Keep existing special styles
                    else:
                        child.configure(style='TLabel')
                        
                elif isinstance(child, ttk.Frame):
                    frame_style = 'Primary.TFrame'
                    current_style = str(child.cget('style') or '')
                    if 'secondary' in current_style.lower() or 'dark' in current_style.lower():
                        frame_style = 'Secondary.TFrame'
                    child.configure(style=frame_style)
                    
                elif isinstance(child, ttk.Notebook):
                    child.configure(style='Custom.TNotebook')
                    
                elif isinstance(child, ttk.LabelFrame):
                    child.configure(style='Custom.TLabelframe')
                    
                elif isinstance(child, ttk.Scrollbar):
                    orient = child.cget('orient')
                    if orient == 'vertical':
                        child.configure(style='Vertical.TScrollbar')
                    else:
                        child.configure(style='Horizontal.TScrollbar')
                        
                elif isinstance(child, (ttk.Checkbutton, ttk.Radiobutton)):
                    if isinstance(child, ttk.Checkbutton):
                        child.configure(style='TCheckbutton')
                    else:
                        child.configure(style='TRadiobutton')
                
                # Recursively style children
                if hasattr(child, 'winfo_children'):
                    self.style_ttk_widgets(child)
                    
        except Exception as e:
            print(f"DEBUG: Error styling ttk widgets: {e}")

    def style_text_widgets(self, parent):
        """Style all tkinter Text widgets - FIXED TO USE TEXT INPUT STYLES"""
        try:
            # Get text input styles if available
            text_input_styles = self.style_settings.get('text_input_styles', {})
            
            for child in parent.winfo_children():
                if isinstance(child, tk.Text):
                    # Get Text widget specific styles
                    text_styles = text_input_styles.get('Text', {})
                    
                    child.configure(
                        background=text_styles.get('background', 'white'),
                        foreground=text_styles.get('foreground', self.style_settings['text_dark']),
                        font=(
                            text_styles.get('font_family', self.style_settings['font_family']),
                            int(text_styles.get('font_size', self.style_settings['font_size']))
                        ),
                        insertbackground=text_styles.get('insertbackground', self.style_settings['text_dark']),
                        selectbackground=text_styles.get('selectbackground', self.style_settings['secondary_color']),
                        selectforeground=text_styles.get('selectforeground', self.style_settings['text_light']),
                        padx=int(text_styles.get('padding_x', 5)),
                        pady=int(text_styles.get('padding_y', 5)),
                        wrap=tk.WORD,
                        relief=text_styles.get('relief', 'solid'),
                        borderwidth=int(text_styles.get('borderwidth', 1))
                    )
                        
                elif isinstance(child, tk.Listbox):
                    # Get Listbox specific styles
                    listbox_styles = text_input_styles.get('Listbox', {})
                    
                    child.configure(
                        background=listbox_styles.get('background', 'white'),
                        foreground=listbox_styles.get('foreground', self.style_settings['text_dark']),
                        font=(
                            listbox_styles.get('font_family', self.style_settings['font_family']),
                            int(listbox_styles.get('font_size', self.style_settings['font_size']))
                        ),
                        selectbackground=listbox_styles.get('selectbackground', self.style_settings['secondary_color']),
                        selectforeground=listbox_styles.get('selectforeground', self.style_settings['text_light']),
                        relief=listbox_styles.get('relief', 'solid'),
                        borderwidth=int(listbox_styles.get('borderwidth', 1))
                    )
                        
                elif isinstance(child, tk.Scrollbar):
                    try:
                        child.configure(
                            background=self.style_settings['light_bg'],
                            troughcolor=self.style_settings['dark_bg'],
                            activebackground=self.style_settings['primary_color']
                        )
                    except tk.TclError:
                        pass  # Some scrollbar versions don't support all options
                
                # Recursively style children
                if hasattr(child, 'winfo_children'):
                    self.style_text_widgets(child)
                    
        except Exception as e:
            print(f"DEBUG: Error styling text widgets: {e}")

    def update_dynamic_widgets(self, parent):
        """Update dynamic widgets that can't be styled recursively"""
        try:
            for child in parent.winfo_children():
                if isinstance(child, ttk.Label):
                    current_text = child.cget('text')
                    if 'Running' in current_text:
                        child.configure(style='Status.Running.TLabel')
                    elif 'Stopped' in current_text:
                        child.configure(style='Status.Stopped.TLabel')
                    elif 'Paused' in current_text:
                        child.configure(style='Status.Paused.TLabel')
                
                if hasattr(child, 'winfo_children'):
                    self.update_dynamic_widgets(child)
                    
        except Exception as e:
            print(f"DEBUG: Error updating dynamic widgets: {e}")

    def configure_button_styles(self, button_styles_settings=None):
        """Configure button styles with fine-tuned settings"""
        if not button_styles_settings:
            print("DEBUG: No button styles settings to configure")
            return
            
        for style_name, state_settings in button_styles_settings.items():
            try:
                # Configure normal state
                normal_bg = state_settings.get('normal', {}).get('background')
                normal_fg = state_settings.get('normal', {}).get('foreground')
                
                if normal_bg and normal_fg:
                    self.style.configure(style_name, background=normal_bg, foreground=normal_fg)
                
                # Configure state mappings
                background_map = []
                foreground_map = []
                
                for state in ['active', 'pressed', 'disabled']:
                    if state in state_settings:
                        bg = state_settings[state].get('background')
                        fg = state_settings[state].get('foreground')
                        
                        if bg:
                            background_map.append((state, bg))
                        if fg:
                            foreground_map.append((state, fg))
                
                # Apply state mappings
                if background_map:
                    self.style.map(style_name, background=background_map)
                if foreground_map:
                    self.style.map(style_name, foreground=foreground_map)
                    
            except Exception as e:
                print(f"DEBUG: Error configuring button style {style_name}: {e}")

    def configure_text_input_styles(self, text_input_styles=None):
        """Configure text input styles with fine-tuned settings - UPDATED FOR COMBOBOX"""
        if not text_input_styles:
            print("DEBUG: No text input styles to configure")
            return

        # Configure ttk styles
        for widget_type, style_settings in text_input_styles.items():
            if widget_type in ["TEntry", "Modern.TEntry", "TCombobox"]:
                try:
                    
                    # Convert string values to appropriate types
                    config_args = {}
                    for key, value in style_settings.items():
                        if key in ["padding_x", "padding_y", "borderwidth"]:
                            try:
                                config_args[key] = int(value)
                            except:
                                config_args[key] = value
                        elif key == "padding":
                            try:
                                x_pad = int(style_settings.get('padding_x', 5))
                                y_pad = int(style_settings.get('padding_y', 2))
                                config_args['padding'] = (x_pad, y_pad)
                            except:
                                pass
                        elif key == "font_family" and "font_size" in style_settings:
                            try:
                                font_size = int(style_settings.get("font_size", 9))
                                config_args["font"] = (value, font_size)
                            except:
                                config_args["font"] = (value, 9)
                        elif key == "font_size" and "font_family" in style_settings:
                            # Font is handled with font_family
                            continue
                        elif key.startswith(("focus_", "hover_")):
                            # State colors are handled in map, not configure
                            continue
                        else:
                            config_args[key] = value
                    
                    # SPECIAL HANDLING FOR COMBOBOX
                    if widget_type == "TCombobox":
                        # Ensure selection colors are explicitly set
                        if 'selectbackground' not in config_args:
                            config_args['selectbackground'] = self.style_settings['secondary_color']
                        if 'selectforeground' not in config_args:
                            config_args['selectforeground'] = self.style_settings['text_light']
                        # Force white background for consistency
                        if 'fieldbackground' not in config_args:
                            config_args['fieldbackground'] = self.style_settings['secondary_color']
                        if 'background' not in config_args:
                            config_args['background'] = self.style_settings['secondary_color']
                    # Configure the style
                    self.style.configure(widget_type, **config_args)
                    
                    # CONFIGURE STATE MAPS FOR FOCUS AND HOVER
                    state_maps = {}
                    
                    # Focus state
                    focus_border = style_settings.get('focus_bordercolor')
                    focus_bg = style_settings.get('focus_fieldbackground')
                    
                    if focus_border or focus_bg:
                        if 'bordercolor' not in state_maps:
                            state_maps['bordercolor'] = []
                        if 'fieldbackground' not in state_maps:
                            state_maps['fieldbackground'] = []
                        
                        if focus_border:
                            state_maps['bordercolor'].append(('focus', focus_border))
                        if focus_bg:
                            state_maps['fieldbackground'].append(('focus', focus_bg))
                    
                    # Hover state
                    hover_border = style_settings.get('hover_bordercolor')
                    if hover_border:
                        if 'bordercolor' not in state_maps:
                            state_maps['bordercolor'] = []
                        state_maps['bordercolor'].append(('hover', hover_border))
                    
                    # Apply state maps if we have any
                    if state_maps:
                        self.style.map(widget_type, **state_maps)
                                        
                except Exception as e:
                    print(f"DEBUG: Error configuring text input style {widget_type}: {e}")
        
        # APPLY ENHANCED COMBOBOX STYLING FOR POPDOWN
        self.configure_enhanced_combobox_styles()

    def configure_treeview_styles(self, treeview_styles=None):
        """Configure treeview styles with fine-tuned settings"""
        if not treeview_styles:
            print("DEBUG: No treeview styles to configure")
            return
            
        # Configure main Treeview styles
        for component, style_settings in treeview_styles.items():
            try:
                # Convert string values to appropriate types
                config_args = {}
                for key, value in style_settings.items():
                    if key in ["rowheight", "borderwidth", "padding_x", "padding_y"]:
                        try:
                            config_args[key] = int(value)
                        except:
                            config_args[key] = value
                    elif key == "padding":
                        try:
                            x_pad = int(style_settings.get('padding_x', 5))
                            y_pad = int(style_settings.get('padding_y', 2))
                            config_args['padding'] = (x_pad, y_pad)
                        except:
                            pass
                    elif key == "font_family" and "font_size" in style_settings:
                        try:
                            font_size = int(style_settings.get("font_size", 9))
                            config_args["font"] = (value, font_size)
                        except:
                            config_args["font"] = (value, 9)
                    elif key == "font_size" and "font_family" in style_settings:
                        # Font is handled with font_family
                        continue
                    else:
                        config_args[key] = value
                
                # Configure the style
                self.style.configure(component, **config_args)
                
            except Exception as e:
                print(f"DEBUG: Error configuring treeview style {component}: {e}")
        
        # Configure treeview tags for row coloring
        self._configure_treeview_tags(treeview_styles)
    
    def _configure_treeview_tags(self, treeview_styles):
        """Configure treeview tags for alternating row colors and selection"""
        try:
            # Get item styles
            item_styles = treeview_styles.get('Treeview.Item', {})
            
            # Configure tags for alternating row colors
            even_color = item_styles.get('even_color', '#f8f9fa')
            odd_color = item_styles.get('odd_color', '#ffffff')
            
            # These will be applied when styling individual treeviews
            self.treeview_even_color = even_color
            self.treeview_odd_color = odd_color
            self.treeview_selected_color = item_styles.get('selected_color', '#3498db')
            self.treeview_selected_text = item_styles.get('selected_text', '#ffffff')
            self.treeview_hover_color = item_styles.get('hover_color', '#e3f2fd')
            
            print(f"DEBUG: Configured treeview tags - even: {even_color}, odd: {odd_color}")
            
        except Exception as e:
            print(f"DEBUG: Error configuring treeview tags: {e}")

    def _configure_treeview_style(self, treeview):
        """Configure treeview with custom tags and styling - ENHANCED VERSION"""
        try:
            # Use configured colors if available, otherwise defaults
            even_color = getattr(self, 'treeview_even_color', self.style_settings['light_bg'])
            odd_color = getattr(self, 'treeview_odd_color', 'white')
            selected_color = getattr(self, 'treeview_selected_color', self.style_settings['secondary_color'])
            selected_text = getattr(self, 'treeview_selected_text', self.style_settings['text_light'])
            hover_color = getattr(self, 'treeview_hover_color', '#e3f2fd')
            
            treeview.tag_configure('even', background=even_color)
            treeview.tag_configure('odd', background=odd_color)
            treeview.tag_configure('selected', background=selected_color, foreground=selected_text)
            treeview.tag_configure('hover', background=hover_color)
            
            treeview.configure(selectmode='extended')
            
            # Apply alternating row colors
            self._apply_treeview_row_colors(treeview)
            
        except Exception as e:
            print(f"DEBUG: Error configuring treeview: {e}")

    def _apply_treeview_row_colors(self, treeview):
        """Apply alternating row colors to treeview"""
        try:
            children = treeview.get_children()
            for i, item in enumerate(children):
                tag = 'even' if i % 2 == 0 else 'odd'
                current_tags = list(treeview.item(item, 'tags'))
                
                # Remove existing color tags
                color_tags = [t for t in current_tags if t in ['even', 'odd', 'selected', 'hover']]
                for color_tag in color_tags:
                    current_tags.remove(color_tag)
                
                # Add new color tag
                current_tags.append(tag)
                treeview.item(item, tags=current_tags)
                
        except Exception as e:
            print(f"DEBUG: Error applying treeview row colors: {e}")

    def configure_window_styles(self, window_styles=None):
        """Configure window styles with fine-tuned settings - ENHANCED"""
        if not window_styles:
            print("DEBUG: No window styles to configure")
            return

        # Store window styles for later application
        self.window_styles = window_styles
        self.style_settings['window_styles'] = window_styles

        # Apply window styling to root window if available
        if self.root:
            try:
                self._apply_window_styling(self.root)
                # Try multiple times to ensure it applies
                if hasattr(self.root, 'after'):
                    self.root.after(100, lambda: self._apply_window_styling(self.root))
                    self.root.after(500, lambda: self._apply_window_styling(self.root))
            except Exception as e:
                print(f"DEBUG: Error applying window styling: {e}")

    def _apply_window_styling(self, window):
        """Apply window styling to a specific window - IMPROVED"""
        try:
            if not hasattr(self, 'window_styles') or not self.window_styles:
                print("DEBUG: No window styles to apply")
                return

            # Apply basic window attributes
            self._apply_basic_window_attributes(window)
            
            # Get platform-specific implementation
            platform = self._get_platform()
            
            if platform == "windows":
                self._apply_windows_styling(window)
            elif platform == "darwin":  # macOS
                self._apply_macos_styling(window)
            else:  # Linux and other
                self._apply_linux_styling(window)
                
        except Exception as e:
            print(f"DEBUG: Error in _apply_window_styling: {e}")

    def _apply_basic_window_attributes(self, window):
        """Apply basic window attributes that work on all platforms - IMPROVED"""
        try:
            # Apply window background
            bg_styles = self.window_styles.get('WindowBackground', {})
            if bg_styles:
                bg_color = bg_styles.get('background')
                if bg_color:
                    try:
                        window.configure(background=bg_color)
                    except Exception as e:
                        print(f"DEBUG: Error setting window background: {e}")
            
            # Apply window opacity
            opacity = bg_styles.get('opacity', '1.0')
            try:
                window.attributes('-alpha', float(opacity))
            except Exception as e:
                print(f"DEBUG: Opacity not supported on this platform: {e}")
            
            # Apply border styling
            border_styles = self.window_styles.get('WindowBorder', {})
            if border_styles:
                border_color = border_styles.get('border_color')
                if border_color:
                    try:
                        # Try to set border color through tkinter
                        window.configure(highlightbackground=border_color)
                        window.configure(highlightcolor=border_color)
                    except:
                        pass
        except Exception as e:
            print(f"DEBUG: Error applying basic window attributes: {e}")

    def _get_platform(self):
        """Get the current platform"""
        import platform
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "darwin"
        else:
            return "linux"

    def _apply_windows_styling(self, window):
        """Apply window styling on Windows - ENHANCED"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get window handle
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            
            # Apply advanced Windows styling
            self._apply_windows_dwm_styling(hwnd)
                        
        except Exception as e:
            print(f"DEBUG: Windows window styling not available: {e}")

    def _apply_windows_dwm_styling(self, hwnd):
        """Apply Windows DWM (Desktop Window Manager) styling - ENHANCED"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Get window styles
            title_bar_styles = self.window_styles.get('TitleBar', {})
            border_styles = self.window_styles.get('WindowBorder', {})
            
            # Windows DWM attributes
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWA_BORDER_COLOR = 34
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            
            # Set dark mode if title bar is dark
            title_bg = title_bar_styles.get('background', '#2c3e50')
            if self._is_dark_color(title_bg):
                attribute_value = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 
                    ctypes.byref(attribute_value), ctypes.sizeof(attribute_value)
                )
            
            # Set border color if available
            border_color = border_styles.get('border_color')
            if border_color:
                color_rgb = self._hex_to_rgb(border_color)
                color_dword = self._rgb_to_dword(color_rgb)
                attribute_value = wintypes.DWORD(color_dword)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_BORDER_COLOR, 
                    ctypes.byref(attribute_value), ctypes.sizeof(attribute_value)
                )
            
            # Set caption color
            caption_color = title_bar_styles.get('background')
            if caption_color:
                color_rgb = self._hex_to_rgb(caption_color)
                color_dword = self._rgb_to_dword(color_rgb)
                attribute_value = wintypes.DWORD(color_dword)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_CAPTION_COLOR, 
                    ctypes.byref(attribute_value), ctypes.sizeof(attribute_value)
                )
            
            # Set text color
            text_color = title_bar_styles.get('foreground')
            if text_color:
                color_rgb = self._hex_to_rgb(text_color)
                color_dword = self._rgb_to_dword(color_rgb)
                attribute_value = wintypes.DWORD(color_dword)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_TEXT_COLOR, 
                    ctypes.byref(attribute_value), ctypes.sizeof(attribute_value)
                )
            

        except Exception as e:
            print(f"DEBUG: Windows DWM styling failed: {e}")

    def _apply_macos_styling(self, window):
        """Apply window styling on macOS"""
        try:
            # macOS-specific window styling
            # Note: Limited styling options on macOS without additional dependencies
            print("DEBUG: macOS window styling - using basic attributes only")
            
        except Exception as e:
            print(f"DEBUG: macOS window styling not available: {e}")

    def _apply_linux_styling(self, window):
        """Apply window styling on Linux"""
        try:
            # Linux window styling (varies by window manager)
            # This is more complex and would require X11 or Wayland specific code
            print("DEBUG: Linux window styling - using basic attributes only")
            
        except Exception as e:
            print(f"DEBUG: Linux window styling not available: {e}")

    def _is_dark_color(self, hex_color):
        """Check if a color is dark"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        except:
            return False

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_dword(self, rgb):
        """Convert RGB tuple to Windows DWORD color"""
        r, g, b = rgb
        return (r << 16) | (g << 8) | b

    def configure_combobox_popdown_styles(self):
        """Configure the combobox popdown listbox and scrollbar styles"""
        try:
            # Get current colors from settings
            primary = self.style_settings['primary_color']
            secondary = self.style_settings['secondary_color']
            light_bg = self.style_settings['light_bg']
            dark_bg = self.style_settings['dark_bg']
            text_dark = self.style_settings['text_dark']
            text_light = self.style_settings['text_light']
            
            # Configure the combobox popdown listbox
            # This requires accessing the internal popdown window
            self._configure_combobox_popdown(primary, secondary, light_bg, dark_bg, text_dark, text_light)
            
        except Exception as e:
            print(f"DEBUG: Error configuring combobox popdown styles: {e}")

    def _configure_combobox_popdown(self, primary, secondary, light_bg, dark_bg, text_dark, text_light):
        """Configure the internal combobox popdown window"""
        try:
            # Get the style
            style = ttk.Style()
            
            # Configure the combobox to use our colors
            style.configure('TCombobox',
                           background='white',
                           foreground=text_dark,
                           fieldbackground='white',
                           selectbackground=secondary,
                           selectforeground=text_light)
            
            # For the popdown listbox, we need to use option_add to set global listbox options
            if hasattr(self, 'root') and self.root:
                # Set global listbox options that will affect the combobox popdown
                self.root.option_add('*TCombobox*Listbox.background', 'white')
                self.root.option_add('*TCombobox*Listbox.foreground', text_dark)
                self.root.option_add('*TCombobox*Listbox.selectBackground', secondary)
                self.root.option_add('*TCombobox*Listbox.selectForeground', text_light)
                self.root.option_add('*TCombobox*Listbox.font', (self.style_settings['font_family'], self.style_settings['font_size']))
                
                # Set scrollbar options for the combobox popdown
                self.root.option_add('*TCombobox*Scrollbar.background', light_bg)
                self.root.option_add('*TCombobox*Scrollbar.troughColor', dark_bg)
                self.root.option_add('*TCombobox*Scrollbar.activeBackground', primary)
                
                print("DEBUG: Configured combobox popdown styles")
                
        except Exception as e:
            print(f"DEBUG: Error configuring combobox popdown: {e}")

    def configure_enhanced_combobox_styles(self):
        """Enhanced combobox styling with complete popdown control"""
        try:
            # Get current colors
            primary = self.style_settings['primary_color']
            secondary = self.style_settings['secondary_color']
            light_bg = self.style_settings['light_bg']
            dark_bg = self.style_settings['dark_bg']
            text_dark = self.style_settings['text_dark']
            text_light = self.style_settings['text_light']
            font_family = self.style_settings['font_family']
            font_size = self.style_settings['font_size']
            disabled = self.style_settings['disabled_color']
            
            style = ttk.Style()
            
            # Configure the main combobox
            style.configure('TCombobox',
                background='white',
                foreground=text_dark,
                fieldbackground='white',
                selectbackground=secondary,
                selectforeground=text_light,
                arrowcolor=primary,
                bordercolor=dark_bg,
                focuscolor=secondary,
                padding=(5, 2),
                relief='solid',
                borderwidth=1
            )
            
            # Enhanced state mappings for combobox
            style.map('TCombobox',
                background=[
                    ('readonly', 'white'),
                    ('disabled', light_bg),
                    ('active', 'white')
                ],
                foreground=[
                    ('readonly', text_dark),
                    ('disabled', disabled),
                    ('active', text_dark)
                ],
                fieldbackground=[
                    ('readonly', 'white'),
                    ('disabled', light_bg),
                    ('focus', 'white'),
                    ('active', 'white')
                ],
                selectbackground=[
                    ('readonly', secondary),
                    ('focus', secondary)
                ],
                selectforeground=[
                    ('readonly', text_light),
                    ('focus', text_light)
                ],
                arrowcolor=[
                    ('disabled', disabled),
                    ('pressed', text_light),
                    ('active', secondary)
                ],
                bordercolor=[
                    ('focus', secondary),
                    ('hover', primary),
                    ('active', secondary)
                ]
            )
            
            # CRITICAL: Configure the popdown listbox using option_add
            if hasattr(self, 'root') and self.root:
                self._configure_combobox_popdown_listbox()
                
            # Platform-specific enhancements
            self._apply_platform_specific_combobox_styling()
            
            print("DEBUG: Applied enhanced combobox styling with popdown support")
            
        except Exception as e:
            print(f"DEBUG: Error in enhanced combobox styling: {e}")
    
    def _configure_combobox_popdown_listbox(self):
        """Configure the combobox popdown listbox and scrollbar"""
        try:
            secondary = self.style_settings['secondary_color']
            text_dark = self.style_settings['text_dark']
            text_light = self.style_settings['text_light']
            font_family = self.style_settings['font_family']
            font_size = self.style_settings['font_size']
            light_bg = self.style_settings['light_bg']
            dark_bg = self.style_settings['dark_bg']
            primary = self.style_settings['primary_color']
            
            # Multiple patterns to catch different combobox implementations
            listbox_patterns = [
                '*TCombobox*Listbox',
                '*TkDDMenu*Listbox', 
                '*Listbox',
                '*.combobox*Listbox'
            ]
            
            for pattern in listbox_patterns:
                self.root.option_add(f'{pattern}.background', 'white')
                self.root.option_add(f'{pattern}.foreground', text_dark)
                self.root.option_add(f'{pattern}.selectBackground', secondary)
                self.root.option_add(f'{pattern}.selectForeground', text_light)
                self.root.option_add(f'{pattern}.font', (font_family, int(font_size)))
                self.root.option_add(f'{pattern}.highlightThickness', 0)
                self.root.option_add(f'{pattern}.borderWidth', 1)
                self.root.option_add(f'{pattern}.relief', 'solid')
                self.root.option_add(f'{pattern}.activestyle', 'dotbox')
                self.root.option_add(f'{pattern}.selectborderwidth', 0)
            
            # Configure popdown window
            popdown_patterns = ['*TkDDMenu', '*TCombobox*Toplevel']
            for pattern in popdown_patterns:
                self.root.option_add(f'{pattern}.background', 'white')
                self.root.option_add(f'{pattern}.highlightBackground', dark_bg)
                self.root.option_add(f'{pattern}.highlightColor', primary)
                self.root.option_add(f'{pattern}.borderWidth', 1)
                self.root.option_add(f'{pattern}.relief', 'solid')
            
            # Scrollbar styling for combobox popdown
            scrollbar_patterns = ['*TCombobox*Scrollbar', '*TkDDMenu*Scrollbar']
            for pattern in scrollbar_patterns:
                self.root.option_add(f'{pattern}.background', light_bg)
                self.root.option_add(f'{pattern}.troughColor', dark_bg)
                self.root.option_add(f'{pattern}.activeBackground', primary)
                self.root.option_add(f'{pattern}.borderWidth', 0)
                self.root.option_add(f'{pattern}.highlightThickness', 0)
                self.root.option_add(f'{pattern}.arrowColor', primary)
                self.root.option_add(f'{pattern}.width', 12)
                
        except Exception as e:
            print(f"DEBUG: Error configuring combobox popdown listbox: {e}")
    
    def _apply_platform_specific_combobox_styling(self):
        """Apply platform-specific combobox styling enhancements"""
        platform = self._get_platform()
        
        if platform == "windows":
            self._apply_windows_combobox_styling()
        elif platform == "darwin":
            self._apply_macos_combobox_styling()
        else:
            self._apply_linux_combobox_styling()
    
    def _apply_windows_combobox_styling(self):
        """Windows-specific combobox styling"""
        try:
            if hasattr(self, 'root') and self.root:
                # Windows-specific combobox options
                self.root.option_add('*TCombobox*Listbox.Jump', 1)
                self.root.tk_setPalette(background='white', foreground=self.style_settings['text_dark'])
        except Exception as e:
            print(f"DEBUG: Windows combobox styling failed: {e}")
    
    def _apply_macos_combobox_styling(self):
        """macOS-specific combobox styling"""
        try:
            if hasattr(self, 'root') and self.root:
                # macOS usually respects system themes more, focus on basic styling
                self.root.option_add('*TCombobox*Listbox.background', 'systemWindowBackgroundColor')
                self.root.option_add('*TCombobox*Listbox.foreground', 'systemTextColor')
        except Exception as e:
            print(f"DEBUG: macOS combobox styling failed: {e}")
    
    def _apply_linux_combobox_styling(self):
        """Linux-specific combobox styling"""
        try:
            if hasattr(self, 'root') and self.root:
                # Linux combobox styling
                self.root.option_add('*TCombobox*Listbox.background', 'white')
                self.root.option_add('*TCombobox*Listbox.foreground', self.style_settings['text_dark'])
                # Try to force the theme
                self.root.tk.call('tk', 'scaling', 1.0)
        except Exception as e:
            print(f"DEBUG: Linux combobox styling failed: {e}")

# ****************************************************************************
# ****************************************************************************
# *************************** STYLING ****************************************

class UnifiedStyleDialog(tk.Toplevel):
    """Unified styling dialog - COMPLETE AND UNIFIED VERSION"""
    
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.app = app_instance
        self.title("ETail Styling Configuration")
        self.geometry("900x700")
        
        # Check if we have a browser or LogTailApp instance
        self.is_browser_instance = hasattr(app_instance, 'instances')
        
        # Use the app's StyleManager
        self.style_manager = app_instance.style_manager
        self.current_styles = self.style_manager.get_style_settings()
        
        # Get current styles
        if self.is_browser_instance:
            self.current_styles = app_instance.style_manager.get_style_settings()
        else:
            self.current_styles = app_instance.get_current_style_settings()
            
        self.original_styles = self.current_styles.copy()
        self.style_presets = {}
        
        # Initialize button style management
        self.setup_button_style_management()
        self.setup_text_input_style_management()
        self.initialize_button_color_vars()
        self.initialize_text_input_vars()
        self.setup_treeview_style_management()
        self.setup_window_style_management()  # ADD THIS
        
        self.setup_dialog()
        self.load_current_styles()
        self.load_style_presets()
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()

    def setup_dialog(self):
        """Setup the unified dialog layout with proper tab filling"""
        # Main container
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="ETail Unified Styling", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Main notebook for different styling aspects - THIS MUST EXPAND
        self.main_notebook = ttk.Notebook(main_frame)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create all tabs
        self._create_all_tabs()
        
        # Preview area (common to all)
        self.setup_preview_area(main_frame)
        
        # Control buttons
        self.setup_control_buttons(main_frame)

    def _create_all_tabs(self):
        """Create all notebook tabs with proper configuration"""
        # Theme and Colors tab
        self.theme_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.theme_tab, text="Theme & Colors")
        self.setup_theme_tab()
        
        # Button Tuning tab
        self.button_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.button_tab, text="Button Styles")
        self.setup_button_tuning_tab()
        
        # Text & Inputs tab
        self.text_inputs_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.text_inputs_tab, text="Text & Inputs")
        self.setup_text_inputs_tab()
        
        # Treeview & Grid tab
        self.treeview_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.treeview_tab, text="Tree & Grid")
        self.setup_treeview_grid_tab()
        
        # Window Decorations tab
        self.window_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.window_tab, text="Window Decorations")
        self.setup_window_decorations_tab()
        
        # Review tab
        self.review_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.review_tab, text="Review")
        self.setup_review_tab()

    def _setup_tab_layout(self, tab):
        """Setup consistent layout for a tab to ensure proper filling"""
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

    def initialize_button_color_vars(self):
        """Properly initialize the button color variables dictionary"""
        if not hasattr(self, 'button_color_vars'):
            self.button_color_vars = {}
        
        # Initialize variables for all button styles and states
        button_styles = ["TButton", "Primary.TButton", "Success.TButton", "Warning.TButton", "Danger.TButton"]
        states = ["normal", "active", "pressed", "disabled"]
        
        for style in button_styles:
            default_colors = self.get_current_button_colors(style)
            for state in states:
                bg_key = (style, state, 'background')
                fg_key = (style, state, 'foreground')
                
                # Only create if it doesn't exist
                if bg_key not in self.button_color_vars:
                    self.button_color_vars[bg_key] = tk.StringVar(value=default_colors[state]["background"])
                if fg_key not in self.button_color_vars:
                    self.button_color_vars[fg_key] = tk.StringVar(value=default_colors[state]["foreground"])

    def setup_theme_tab(self):
        """Setup unified theme and styling controls"""
        # REPLACE THE FIRST FEW LINES OF YOUR EXISTING METHOD WITH THIS:
        
        # Main container using grid for proper expansion
        container = ttk.Frame(self.theme_tab)
        container.pack(fill=tk.BOTH, expand=True)  # This ensures the container fills the tab
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar to fill container
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure canvas to update scrollable frame width
        def configure_canvas_width(event):
            canvas.itemconfig("all", width=event.width)
        canvas.bind("<Configure>", configure_canvas_width)

        # Presets section
        preset_frame = ttk.LabelFrame(scrollable_frame, text="Style Presets", padding="5")
        preset_frame.pack(fill=tk.X, pady=(0, 10))
        
        preset_subframe = ttk.Frame(preset_frame)
        preset_subframe.pack(fill=tk.X)
        
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_subframe, textvariable=self.preset_var, 
                                        state="readonly", width=30)
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_selected)
        
        btn_frame = ttk.Frame(preset_subframe)
        btn_frame.pack(side=tk.RIGHT)
        
        ttk.Button(btn_frame, text="Save Preset", command=self.save_preset, width=10).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(btn_frame, text="Delete Preset", command=self.delete_preset, width=10).pack(side=tk.LEFT)
        
        # Theme section
        theme_frame = ttk.LabelFrame(scrollable_frame, text="Theme", padding="5")
        theme_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(theme_frame, text="Theme:").pack(side=tk.LEFT)
        
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                       state="readonly", width=20)
        self.theme_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # Get available themes
        self.style = ttk.Style()
        available_themes = self.style.theme_names()
        self.theme_combo['values'] = available_themes
        
        ttk.Button(theme_frame, text="Apply Theme", command=self.apply_theme).pack(side=tk.LEFT)
        
        # Color scheme section
        colors_frame = ttk.LabelFrame(scrollable_frame, text="Color Scheme", padding="5")
        colors_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a grid for colors
        color_grid = ttk.Frame(colors_frame)
        color_grid.pack(fill=tk.X)
        
        # Row 1
        row1 = ttk.Frame(color_grid)
        row1.pack(fill=tk.X, pady=2)
        
        # Primary color
        ttk.Label(row1, text="Primary:", width=12).pack(side=tk.LEFT)
        self.primary_color_var = tk.StringVar(value="#2c3e50")
        primary_entry = ttk.Entry(row1, textvariable=self.primary_color_var, width=10)
        primary_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row1, text="Choose", command=lambda: self.choose_color('primary'), width=8).pack(side=tk.LEFT, padx=(0, 20))
        
        # Secondary color
        ttk.Label(row1, text="Secondary:", width=12).pack(side=tk.LEFT)
        self.secondary_color_var = tk.StringVar(value="#3498db")
        secondary_entry = ttk.Entry(row1, textvariable=self.secondary_color_var, width=10)
        secondary_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row1, text="Choose", command=lambda: self.choose_color('secondary'), width=8).pack(side=tk.LEFT)
        
        # Row 2
        row2 = ttk.Frame(color_grid)
        row2.pack(fill=tk.X, pady=2)
        
        # Success color
        ttk.Label(row2, text="Success:", width=12).pack(side=tk.LEFT)
        self.success_color_var = tk.StringVar(value="#27ae60")
        success_entry = ttk.Entry(row2, textvariable=self.success_color_var, width=10)
        success_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row2, text="Choose", command=lambda: self.choose_color('success'), width=8).pack(side=tk.LEFT, padx=(0, 20))
        
        # Warning color
        ttk.Label(row2, text="Warning:", width=12).pack(side=tk.LEFT)
        self.warning_color_var = tk.StringVar(value="#f39c12")
        warning_entry = ttk.Entry(row2, textvariable=self.warning_color_var, width=10)
        warning_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row2, text="Choose", command=lambda: self.choose_color('warning'), width=8).pack(side=tk.LEFT)
        
        # Row 3
        row3 = ttk.Frame(color_grid)
        row3.pack(fill=tk.X, pady=2)
        
        # Danger color
        ttk.Label(row3, text="Danger:", width=12).pack(side=tk.LEFT)
        self.danger_color_var = tk.StringVar(value="#e74c3c")
        danger_entry = ttk.Entry(row3, textvariable=self.danger_color_var, width=10)
        danger_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row3, text="Choose", command=lambda: self.choose_color('danger'), width=8).pack(side=tk.LEFT, padx=(0, 20))
        
        # Disabled color
        ttk.Label(row3, text="Disabled:", width=12).pack(side=tk.LEFT)
        self.disabled_color_var = tk.StringVar(value="#c0c0c0")
        disabled_entry = ttk.Entry(row3, textvariable=self.disabled_color_var, width=10)
        disabled_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row3, text="Choose", command=lambda: self.choose_color('disabled'), width=8).pack(side=tk.LEFT)
        
        # Background colors section
        bg_frame = ttk.LabelFrame(scrollable_frame, text="Background Colors", padding="5")
        bg_frame.pack(fill=tk.X, pady=(0, 10))
        
        bg_row = ttk.Frame(bg_frame)
        bg_row.pack(fill=tk.X, pady=2)
        
        # Light background
        ttk.Label(bg_row, text="Light BG:", width=12).pack(side=tk.LEFT)
        self.light_bg_var = tk.StringVar(value="#ecf0f1")
        light_bg_entry = ttk.Entry(bg_row, textvariable=self.light_bg_var, width=10)
        light_bg_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(bg_row, text="Choose", command=lambda: self.choose_color('light_bg'), width=8).pack(side=tk.LEFT, padx=(0, 20))
        
        # Dark background
        ttk.Label(bg_row, text="Dark BG:", width=12).pack(side=tk.LEFT)
        self.dark_bg_var = tk.StringVar(value="#34495e")
        dark_bg_entry = ttk.Entry(bg_row, textvariable=self.dark_bg_var, width=10)
        dark_bg_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(bg_row, text="Choose", command=lambda: self.choose_color('dark_bg'), width=8).pack(side=tk.LEFT)
        
        # Text colors section
        text_frame = ttk.LabelFrame(scrollable_frame, text="Text Colors", padding="5")
        text_frame.pack(fill=tk.X, pady=(0, 10))
        
        text_row = ttk.Frame(text_frame)
        text_row.pack(fill=tk.X, pady=2)
        
        # Primary text
        ttk.Label(text_row, text="Primary Text:", width=12).pack(side=tk.LEFT)
        self.text_primary_var = tk.StringVar(value="#2c3e50")
        text_primary_entry = ttk.Entry(text_row, textvariable=self.text_primary_var, width=10)
        text_primary_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(text_row, text="Choose", command=lambda: self.choose_color('text_primary'), width=8).pack(side=tk.LEFT, padx=(0, 20))
        
        # Light text
        ttk.Label(text_row, text="Light Text:", width=12).pack(side=tk.LEFT)
        self.text_light_var = tk.StringVar(value="#ffffff")
        text_light_entry = ttk.Entry(text_row, textvariable=self.text_light_var, width=10)
        text_light_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(text_row, text="Choose", command=lambda: self.choose_color('text_light'), width=8).pack(side=tk.LEFT, padx=(0, 20))
        
        # Dark text
        ttk.Label(text_row, text="Dark Text:", width=12).pack(side=tk.LEFT)
        self.text_dark_var = tk.StringVar(value="#000000")
        text_dark_entry = ttk.Entry(text_row, textvariable=self.text_dark_var, width=10)
        text_dark_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(text_row, text="Choose", command=lambda: self.choose_color('text_dark'), width=8).pack(side=tk.LEFT)
        
        # Font settings
        font_frame = ttk.LabelFrame(scrollable_frame, text="Font Settings", padding="5")
        font_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Font family
        font_family_frame = ttk.Frame(font_frame)
        font_family_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(font_family_frame, text="Family:", width=12).pack(side=tk.LEFT)
        self.font_family_var = tk.StringVar(value="Arial")
        font_family_combo = ttk.Combobox(font_family_frame, textvariable=self.font_family_var,
                                        values=["Arial", "Helvetica", "Times New Roman", "IBM Plex Mono Text", "IBM Plex Mono Medium", "Courier New", 
                                               "Verdana", "Tahoma", "Segoe UI", "System"])
        font_family_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Font size
        font_size_frame = ttk.Frame(font_frame)
        font_size_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(font_size_frame, text="Size:", width=12).pack(side=tk.LEFT)
        self.font_size_var = tk.StringVar(value="9")
        font_size_combo = ttk.Combobox(font_size_frame, textvariable=self.font_size_var,
                                      values=["8", "9", "10", "11", "12", "14", "16", "18"])
        font_size_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Add bindings for auto-preview
        color_vars = [
            self.primary_color_var, self.secondary_color_var, self.success_color_var,
            self.warning_color_var, self.danger_color_var, self.disabled_color_var,
            self.light_bg_var, self.dark_bg_var, self.text_primary_var,
            self.text_light_var, self.text_dark_var, self.font_family_var,
            self.font_size_var
        ]
        
        for var in color_vars:
            var.trace('w', lambda *args: self.apply_to_preview())

    def setup_button_tuning_tab(self):
        """Setup the button fine-tuning tab with proper filling"""
        # Create scrollable frame for button tab
        self._create_scrollable_frame(self.button_tab)
        
        # Now build your existing button tuning content using self.scrollable_frame as parent
        # File management section
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="Button Style Files", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        file_subframe = ttk.Frame(file_frame)
        file_subframe.pack(fill=tk.X)
        
        ttk.Label(file_subframe, text="Style Files:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.button_file_var = tk.StringVar()
        self.button_file_combo = ttk.Combobox(
            file_subframe, 
            textvariable=self.button_file_var,
            state="readonly",
            width=20
        )
        self.button_file_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.button_file_combo.bind('<<ComboboxSelected>>', self.on_button_file_selected)
        
        file_btn_frame = ttk.Frame(file_subframe)
        file_btn_frame.pack(side=tk.LEFT)
        
        ttk.Button(file_btn_frame, text="Load", 
                  command=self.load_current_button_file, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Save As", 
                  command=self.save_button_style_as, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Delete", 
                  command=self.delete_current_button_file, width=8).pack(side=tk.LEFT)
        
        # Button style selection
        style_selection_frame = ttk.LabelFrame(self.scrollable_frame, text="Button Style Selection", padding="5")
        style_selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(style_selection_frame, text="Select Button Style:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.button_style_var = tk.StringVar(value="TButton")
        self.button_style_combo = ttk.Combobox(
            style_selection_frame, 
            textvariable=self.button_style_var,
            values=["TButton", "Primary.TButton", "Success.TButton", "Warning.TButton", "Danger.TButton"],
            state="readonly",
            width=20
        )
        self.button_style_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.button_style_combo.bind('<<ComboboxSelected>>', self.on_button_style_selected)
        
        # Button states explanation
        states_frame = ttk.Frame(style_selection_frame)
        states_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        states_label = ttk.Label(states_frame, text="States: normal, active (hover), pressed, disabled", 
                               font=("Arial", 8), foreground="gray")
        states_label.pack(side=tk.LEFT)
        
        # Color controls frame - will be populated dynamically
        self.color_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Color Controls", padding="5")
        self.color_controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Quick actions frame
        quick_actions_frame = ttk.LabelFrame(self.scrollable_frame, text="Quick Actions", padding="5")
        quick_actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        action_subframe = ttk.Frame(quick_actions_frame)
        action_subframe.pack(fill=tk.X)
        
        ttk.Button(action_subframe, text="Reset All to Defaults", 
                  command=self.reset_all_button_styles, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Copy to Other Styles", 
                  command=self.copy_button_styles, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Apply to Theme", 
                  command=self.apply_button_styles_to_theme, width=15).pack(side=tk.LEFT)
        
        # Initialize with default button style
        self.setup_button_color_controls("TButton")
        self.update_button_file_combo()

    def setup_button_color_controls(self, button_style):
        """Setup color controls for the selected button style"""
        # Clear existing controls
        for widget in self.color_controls_frame.winfo_children():
            widget.destroy()
        
        # Get current colors for this button style
        current_colors = self.get_current_button_colors(button_style)
        
        # Initialize the dictionary if it doesn't exist
        if not hasattr(self, 'button_color_vars'):
            self.button_color_vars = {}
        
        # Create color controls for each state
        states = [
            ("normal", "Normal State"),
            ("active", "Active (Hover)"), 
            ("pressed", "Pressed State"),
            ("disabled", "Disabled State")
        ]
        
        for i, (state_key, state_label) in enumerate(states):
            state_frame = ttk.Frame(self.color_controls_frame)
            state_frame.pack(fill=tk.X, pady=2)
            
            # State label
            ttk.Label(state_frame, text=state_label, width=15).pack(side=tk.LEFT)
            
            # Background color
            bg_frame = ttk.Frame(state_frame)
            bg_frame.pack(side=tk.LEFT, padx=(0, 10))
            
            ttk.Label(bg_frame, text="Background:").pack(side=tk.LEFT)
            
            # Create StringVar and store in dictionary
            bg_key = (button_style, state_key, 'background')
            bg_var = tk.StringVar(value=current_colors[state_key]["background"])
            self.button_color_vars[bg_key] = bg_var
            
            bg_entry = ttk.Entry(bg_frame, textvariable=bg_var, width=10)
            bg_entry.pack(side=tk.LEFT, padx=(5, 5))
            
            ttk.Button(bg_frame, text="Choose", 
                      command=lambda bs=button_style, sk=state_key, var=bg_var: 
                      self.choose_button_color(bs, sk, 'background', var),
                      width=8).pack(side=tk.LEFT)
            
            # Foreground color
            fg_frame = ttk.Frame(state_frame)
            fg_frame.pack(side=tk.LEFT)
            
            ttk.Label(fg_frame, text="Text:").pack(side=tk.LEFT)
            
            # Create StringVar and store in dictionary
            fg_key = (button_style, state_key, 'foreground')
            fg_var = tk.StringVar(value=current_colors[state_key]["foreground"])
            self.button_color_vars[fg_key] = fg_var
            
            fg_entry = ttk.Entry(fg_frame, textvariable=fg_var, width=10)
            fg_entry.pack(side=tk.LEFT, padx=(5, 5))
            
            ttk.Button(fg_frame, text="Choose", 
                      command=lambda bs=button_style, sk=state_key, var=fg_var: 
                      self.choose_button_color(bs, sk, 'foreground', var),
                      width=8).pack(side=tk.LEFT)
            
            # Add trace to auto-update preview - BUT WITH DEBOUNCE
            bg_var.trace('w', self.schedule_preview_update)
            fg_var.trace('w', self.schedule_preview_update)

    def schedule_preview_update(self, *args):
        """Schedule a preview update with debounce to prevent multiple rapid updates"""
        if hasattr(self, '_preview_job'):
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(300, self.apply_to_preview)

    def setup_preview_area(self, parent):
        """Setup common preview area"""
        preview_frame = ttk.LabelFrame(parent, text="Live Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 5))
        
        # Create notebook for preview tabs
        self.preview_notebook = ttk.Notebook(preview_frame)
        self.preview_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Log View Preview
        log_tab = ttk.Frame(self.preview_notebook, padding="10")
        self.preview_notebook.add(log_tab, text="Log View")
        self.build_log_preview(log_tab)
        
        # Tab 2: Controls Preview
        controls_tab = ttk.Frame(self.preview_notebook, padding="10")
        self.preview_notebook.add(controls_tab, text="UI Controls")
        self.build_controls_preview(controls_tab)

    def setup_control_buttons(self, parent):
        """Setup control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame, text="Apply to Preview", 
                  command=self.apply_to_preview).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_frame, text="Reset", 
                  command=self.reset_styles).pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame, text="Cancel", 
                  command=self.cancel_changes).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(right_frame, text="Save & Apply", 
                  command=self.save_and_apply, style='Success.TButton').pack(side=tk.RIGHT, padx=(5, 0))

    def build_log_preview(self, parent):
        """Build log view preview"""
        log_preview_frame = ttk.LabelFrame(parent, text="Log Display")
        log_preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_preview = scrolledtext.ScrolledText(log_preview_frame, height=8, wrap=tk.WORD)
        self.log_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add sample log content
        sample_log = """[INFO] Application started
                [DEBUG] Loading configuration
                [WARNING] Default settings applied
                [ERROR] File not found: config.json
                [SUCCESS] Configuration loaded"""
        
        self.log_preview.insert(1.0, sample_log)
        self.log_preview.config(state=tk.DISABLED)

    def build_controls_preview(self, parent):
        """Build controls preview with proper widget references"""
        self._create_scrollable_frame(parent)
        # Sample buttons
        # Now build your controls preview content using self.scrollable_frame as parent
        # Sample buttons
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Label(button_frame, text="Buttons:").pack(anchor=tk.W)
        btn_subframe = ttk.Frame(button_frame)
        btn_subframe.pack(fill=tk.X, pady=5)
        
        # STORE REFERENCES AS INSTANCE ATTRIBUTES
        self.preview_btn_default = ttk.Button(btn_subframe, text="Default Button")
        self.preview_btn_default.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_primary = ttk.Button(btn_subframe, text="Primary Button", style='Primary.TButton')
        self.preview_btn_primary.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_success = ttk.Button(btn_subframe, text="Success Button", style='Success.TButton')
        self.preview_btn_success.pack(side=tk.LEFT, padx=(0, 5))

        self.preview_btn_warning = ttk.Button(btn_subframe, text="Warning Button", style='Warning.TButton')
        self.preview_btn_warning.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_danger = ttk.Button(btn_subframe, text="Danger Button", style='Danger.TButton')
        self.preview_btn_danger.pack(side=tk.LEFT)
        
        # Add disabled versions in a second row
        disabled_frame = ttk.Frame(button_frame)
        disabled_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(disabled_frame, text="Disabled States:").pack(anchor=tk.W)
        disabled_btn_subframe = ttk.Frame(disabled_frame)
        disabled_btn_subframe.pack(fill=tk.X, pady=5)
        
        self.preview_btn_default_disabled = ttk.Button(disabled_btn_subframe, text="Default Disabled", state="disabled")
        self.preview_btn_default_disabled.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_primary_disabled = ttk.Button(disabled_btn_subframe, text="Primary Disabled", style='Primary.TButton', state="disabled")
        self.preview_btn_primary_disabled.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_success_disabled = ttk.Button(disabled_btn_subframe, text="Success Disabled", style='Success.TButton', state="disabled")
        self.preview_btn_success_disabled.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_warning_disabled = ttk.Button(disabled_btn_subframe, text="Warning Disabled", style='Warning.TButton', state="disabled")
        self.preview_btn_warning_disabled.pack(side=tk.LEFT, padx=(0, 5))
        
        self.preview_btn_danger_disabled = ttk.Button(disabled_btn_subframe, text="Danger Disabled", style='Danger.TButton', state="disabled")
        self.preview_btn_danger_disabled.pack(side=tk.LEFT)
        
        # Sample entries and combos - ENHANCED              
        input_frame = ttk.Frame(self.scrollable_frame)
        input_frame.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(input_frame, text="Input Fields:").pack(anchor=tk.W)
        
        self.preview_entry = ttk.Entry(input_frame, width=30)
        self.preview_entry.pack(fill=tk.X, pady=2)
        self.preview_entry.insert(0, "Sample text entry")
        
        # Enhanced combobox with more options to demonstrate styling
        self.preview_combo = ttk.Combobox(input_frame, 
                                         values=["Option 1 - Selected", "Option 2", "Option 3", "Option 4", "Option 5"],
                                         state="readonly",
                                         width=30)
        self.preview_combo.pack(fill=tk.X, pady=2)
        self.preview_combo.set("Option 1 - Selected")
        
        # Add a note about combobox styling
        note_frame = ttk.Frame(input_frame)
        note_frame.pack(fill=tk.X, pady=2)
        
        note_label = ttk.Label(note_frame, 
                              text="Note: Combobox dropdown styling may vary by platform",
                              font=("Arial", 8),
                              foreground="gray")
        note_label.pack(anchor=tk.W)
        
        # Sample listbox

        list_frame = ttk.Frame(self.scrollable_frame)
        list_frame.pack(fill=tk.X, pady=5, padx=5)
       
        ttk.Label(list_frame, text="ListBox:").pack(anchor=tk.W)
        self.preview_listbox = tk.Listbox(list_frame, height=3)
        self.preview_listbox.pack(fill=tk.X, pady=2)       
        
        for i in range(1, 3):
            self.preview_listbox.insert(tk.END, f"List item {i}")

        
        # Add Treeview preview section
        treeview_frame = ttk.Frame(self.scrollable_frame)
        treeview_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(treeview_frame, text="Treeview Preview:").pack(anchor=tk.W)
        
        # Create treeview with sample data
        tree_subframe = ttk.Frame(treeview_frame)
        tree_subframe.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create treeview
        self.preview_treeview = ttk.Treeview(tree_subframe, columns=("Name", "Value", "Status"), show="headings", height=2)
        self.preview_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_subframe, orient="vertical", command=self.preview_treeview.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_treeview.configure(yscrollcommand=tree_scrollbar.set)
        
        # Configure columns
        self.preview_treeview.heading("Name", text="Name")
        self.preview_treeview.heading("Value", text="Value") 
        self.preview_treeview.heading("Status", text="Status")
        
        self.preview_treeview.column("Name", width=100)
        self.preview_treeview.column("Value", width=80)
        self.preview_treeview.column("Status", width=80)
        
        # Add sample data
        sample_data = [
            ("Item 1", "100", "Active"),
            ("Item 2", "200", "Inactive"),
            ("Item 3", "150", "Pending"),
        ]
        
        for i, (name, value, status) in enumerate(sample_data):
            self.preview_treeview.insert("", "end", values=(name, value, status))

        # Add Window Decorations preview section - IMPROVED VERSION
        window_frame = ttk.Frame(self.scrollable_frame)
        window_frame.pack(fill=tk.X, pady=5, padx=5)
                
        # Create a simulated window frame using tk.Frame for direct color control
        sim_window = tk.Frame(window_frame, relief='solid', borderwidth=1, background='#34495e')
        sim_window.pack(fill=tk.X, padx=5, pady=5)
        
        # Simulated title bar using tk.Frame for direct color control
        self.preview_titlebar = tk.Frame(sim_window, height=25, background='#2c3e50')
        self.preview_titlebar.pack(fill=tk.X)
        self.preview_titlebar.pack_propagate(False)  # Keep height
        
        # Title bar content
        title_content = tk.Frame(self.preview_titlebar, background='#2c3e50')
        title_content.pack(fill=tk.X, padx=5, pady=2)
        
        # Window title using tk.Label for direct color control
        self.preview_window_title = tk.Label(title_content, 
                                           text="Window Title Preview",
                                           background='#2c3e50',
                                           foreground='#ffffff',
                                           font=('Arial', 9))
        self.preview_window_title.pack(side=tk.LEFT)
        
        # Window buttons frame
        button_frame = tk.Frame(title_content, background='#2c3e50')
        button_frame.pack(side=tk.RIGHT)
        
        # Simulated window buttons using tk.Label for direct color control
        self.preview_minimize_btn = tk.Label(button_frame, 
                                           text="—", 
                                           width=2, 
                                           background='#3498db',
                                           foreground='#ffffff',
                                           relief='raised', 
                                           borderwidth=1,
                                           anchor='center',
                                           font=('Arial', 10, 'bold'))
        self.preview_minimize_btn.pack(side=tk.LEFT, padx=1)
        
        self.preview_maximize_btn = tk.Label(button_frame, 
                                           text="□", 
                                           width=2,
                                           background='#f39c12',
                                           foreground='#ffffff',
                                           relief='raised', 
                                           borderwidth=1,
                                           anchor='center',
                                           font=('Arial', 10, 'bold'))
        self.preview_maximize_btn.pack(side=tk.LEFT, padx=1)
        
        self.preview_close_btn = tk.Label(button_frame, 
                                        text="×", 
                                        width=2,
                                        background='#e74c3c',
                                        foreground='#ffffff',
                                        relief='raised', 
                                        borderwidth=1,
                                        anchor='center',
                                        font=('Arial', 10, 'bold'))
        self.preview_close_btn.pack(side=tk.LEFT, padx=1)
        
        # Window content area using tk.Frame for direct color control
        content_frame = tk.Frame(sim_window, height=20, background='#ecf0f1')
        content_frame.pack(fill=tk.X)
        content_frame.pack_propagate(False)
        
        # Content label using tk.Label for direct color control
        content_label = tk.Label(content_frame, 
                               text="Window Content Area", 
                               background='#ecf0f1',
                               foreground='#000000',
                               justify='center')
        content_label.pack(expand=True, fill=tk.BOTH)

    def choose_color(self, color_type):
        """Choose color for specified type"""
        color_vars = {
            'primary': self.primary_color_var,
            'secondary': self.secondary_color_var,
            'success': self.success_color_var,
            'warning': self.warning_color_var,
            'danger': self.danger_color_var,
            'disabled': self.disabled_color_var,
            'light_bg': self.light_bg_var,
            'dark_bg': self.dark_bg_var,
            'text_primary': self.text_primary_var,
            'text_light': self.text_light_var,
            'text_dark': self.text_dark_var,
        }
        
        if color_type in color_vars:
            color = askcolor(title=f"Choose {color_type.replace('_', ' ').title()} Color", 
                           initialcolor=color_vars[color_type].get())
            if color[1]:
                color_vars[color_type].set(color[1])
                # AUTO-APPLY TO PREVIEW
                self.apply_to_preview()

    def apply_theme(self):
        """Apply the selected theme"""
        try:
            selected_theme = self.theme_var.get()
            if selected_theme:
                self.style.theme_use(selected_theme)
                self.apply_to_preview()
                self.app.messages(2, 9, f"Theme changed to: {selected_theme}")
        except Exception as e:
            self.app.messages(2, 3, f"Error applying theme: {e}")

    def apply_to_preview(self):
        """Apply current styles to preview - FIXED TO PREVENT RESETTING"""
        try:
            # Collect current settings
            style_settings = self.collect_all_settings()

            # Update the StyleManager with current settings
            if hasattr(self.app, 'style_manager'):
                # Create a copy of current styles to avoid modifying the original during preview
                preview_settings = style_settings.copy()
                self.app.style_manager.update_style_settings(preview_settings)
                self.app.style_manager.configure_styles()
            
            # Apply to log preview
            self.log_preview.config(state=tk.NORMAL)
            self.log_preview.configure(
                background=style_settings.get('light_bg', '#ecf0f1'),
                foreground=style_settings.get('text_dark', '#000000'),
                font=(style_settings['font_family'], int(style_settings['font_size']))
            )
            self.log_preview.config(state=tk.DISABLED)
            
            # Apply to other preview widgets
            self._update_controls_preview(style_settings)
            
        except Exception as e:
            print(f"DEBUG: Error in apply_to_preview: {e}")

    def _update_controls_preview(self, style_settings):
        """Update the controls preview with current styles - FIXED FOR TEXT INPUTS"""
        try:
            # Get colors from settings
            primary_color = style_settings['primary_color']
            secondary_color = style_settings['secondary_color']
            success_color = style_settings['success_color']
            danger_color = style_settings['danger_color']
            warning_color = style_settings['warning_color']
            light_bg = style_settings['light_bg']
            text_dark = style_settings.get('text_dark', '#000000')
            
            # Create temporary styles for preview widgets
            preview_style = ttk.Style()
            
            # Configure base button styles from theme
            preview_style.configure('Preview.TButton', background=secondary_color, foreground='white')
            preview_style.configure('Preview.Primary.TButton', background=secondary_color, foreground='white')
            preview_style.configure('Preview.Success.TButton', background=success_color, foreground='white')
            preview_style.configure('Preview.Warning.TButton', background=warning_color, foreground=text_dark)
            preview_style.configure('Preview.Danger.TButton', background=danger_color, foreground='white')
            
            # Apply text input styles to preview - NEW SECTION
            text_input_styles = style_settings.get('text_input_styles', {})
            if text_input_styles:
                self._apply_text_input_styles_to_preview(text_input_styles)
            else:
                # Fallback to basic styles if no custom text input styles
                preview_style.configure('Preview.TEntry',
                                       fieldbackground='white',
                                       foreground=text_dark)
                preview_style.configure('Preview.TCombobox',
                                       fieldbackground='white', 
                                       foreground=text_dark)
                
                # Update entry and combobox if they exist
                if hasattr(self, 'preview_entry'):
                    self.preview_entry.configure(style='Preview.TEntry')
                if hasattr(self, 'preview_combo'):
                    self.preview_combo.configure(style='Preview.TCombobox')
            
            # Update button styles if they exist
            if hasattr(self, 'preview_btn_default'):
                self.preview_btn_default.configure(style='Preview.TButton')
            if hasattr(self, 'preview_btn_primary'):
                self.preview_btn_primary.configure(style='Preview.Primary.TButton')
            if hasattr(self, 'preview_btn_success'):
                self.preview_btn_success.configure(style='Preview.Success.TButton')
            if hasattr(self, 'preview_btn_warning'):
                self.preview_btn_warning.configure(style='Preview.Warning.TButton')
            if hasattr(self, 'preview_btn_danger'):
                self.preview_btn_danger.configure(style='Preview.Danger.TButton')
    
            # Update disabled buttons
            disabled_buttons = [
                'preview_btn_default_disabled', 'preview_btn_primary_disabled',
                'preview_btn_success_disabled', 'preview_btn_warning_disabled',
                'preview_btn_danger_disabled'
            ]
            for btn_attr in disabled_buttons:
                if hasattr(self, btn_attr):
                    getattr(self, btn_attr).configure(style='Preview.TButton')
            
            # Get button styles if any and apply them
            button_styles = style_settings.get('button_styles', {})
            for style_name in ["TButton", "Primary.TButton", "Success.TButton", "Warning.TButton", "Danger.TButton"]:
                if style_name in button_styles:
                    self._apply_button_style_to_preview(style_name, button_styles[style_name])

            # Apply treeview styles to preview - NEW SECTION
            treeview_styles = style_settings.get('treeview_styles', {})
            if treeview_styles and hasattr(self, 'preview_treeview'):
                self._apply_treeview_styles_to_preview(treeview_styles)

            # Update tkinter widgets (Text, Listbox) - FIXED
            self._update_tkinter_widgets_preview(style_settings, text_input_styles)

            # Apply window styles to preview - NEW SECTION
            window_styles = style_settings.get('window_styles', {})
            if window_styles:
                self._apply_window_styles_to_preview(window_styles)

        except Exception as e:
            print(f"DEBUG: Error updating controls preview: {e}")

    def save_and_apply(self):
        """Save and apply styles to application - FIXED VERSION"""
        try:
            print("DEBUG: Starting save_and_apply")
            
            # Collect all style settings
            style_settings = self.collect_all_settings()
            print(f"DEBUG: Collected {len(style_settings)} basic settings")
            
            # Collect button styles
            button_settings = self.collect_button_tuning_settings()
            if button_settings:
                style_settings['button_styles'] = button_settings
                print(f"DEBUG: Added {len(button_settings)} button styles to settings")
            else:
                print("DEBUG: No button styles collected")
                # Ensure we remove any existing button styles if none are collected
                if 'button_styles' in style_settings:
                    del style_settings['button_styles']
            
            # Apply based on instance type
            if self.is_browser_instance:
                print("DEBUG: Applying to browser instance")
                self.apply_to_browser(style_settings)
            else:
                print("DEBUG: Applying to standalone instance")
                self.apply_to_standalone(style_settings)
            
            self.app.messages(2, 9, "Styles saved and applied successfully")
            self.destroy()
              
        except Exception as e:
            print(f"DEBUG: Error in save_and_apply: {e}")
            self.app.messages(2, 3, f"Error saving styles: {e}")

    def debug_current_state(self):
        """Debug method to show current state"""
        print("=== CURRENT STATE DEBUG ===")
        print(f"Has button_color_vars: {hasattr(self, 'button_color_vars')}")
        if hasattr(self, 'button_color_vars'):
            print(f"Number of button color vars: {len(self.button_color_vars)}")
        
        current_settings = self.collect_all_settings()
        print(f"Basic settings count: {len(current_settings)}")
        
        button_settings = self.collect_button_tuning_settings()
        print(f"Button settings count: {len(button_settings)}")
        
        if button_settings:
            for style_name, states in button_settings.items():
                print(f"  {style_name}: {len(states)} states")

    def collect_all_settings(self):
        """Collect all style settings from all tabs - UPDATED"""
        settings = {
            # Basic theme settings
            'primary_color': self.primary_color_var.get(),
            'secondary_color': self.secondary_color_var.get(),
            'success_color': self.success_color_var.get(),
            'warning_color': self.warning_color_var.get(),
            'danger_color': self.danger_color_var.get(),
            'disabled_color': self.disabled_color_var.get(),
            'light_bg': self.light_bg_var.get(),
            'dark_bg': self.dark_bg_var.get(),
            'text_primary': self.text_primary_var.get(),
            'text_light': self.text_light_var.get(),
            'text_dark': self.text_dark_var.get(),
            'font_family': self.font_family_var.get(),
            'font_size': self.font_size_var.get(),
            'theme': self.theme_var.get(),
        }
        
        # Include button tuning settings
        button_settings = self.collect_button_tuning_settings()
        if button_settings:
            settings['button_styles'] = button_settings
        
        # Include text input settings
        text_input_settings = self.collect_text_input_settings()
        settings['text_input_styles'] = text_input_settings
        
        # Include treeview settings
        treeview_settings = self.collect_treeview_settings()
        settings['treeview_styles'] = treeview_settings
        
        # Include window settings - ADD THIS
        window_settings = self.collect_window_settings()
        settings['window_styles'] = window_settings
        
        return settings

    def apply_to_browser(self, style_settings):
        """Apply styles to browser instance - UPDATED FOR WINDOW STYLES"""
        try:
            print("DEBUG: Applying styles to browser")
            
            # Update global style manager
            self.app.style_manager.update_style_settings(style_settings)
            self.app.global_styles = style_settings.copy()
            
            # Save window styles separately
            window_styles = style_settings.get('window_styles')
            if window_styles:
                print(f"DEBUG: Saving {len(window_styles)} window styles")
                self.app.save_window_styles(window_styles)
            
            # Configure styles first
            self.app.style_manager.configure_styles()
            
            # Then apply to browser and instances
            self.app.apply_global_style_to_browser()
            self.app.apply_global_style_to_all_instances()
            
            # Save instances
            self.app.save_instances()
            print("DEBUG: Successfully applied styles to browser")
            
        except Exception as e:
            print(f"DEBUG: Error in apply_to_browser: {e}")
            raise

    def apply_to_standalone(self, style_settings):
        """Apply styles to standalone instance"""
        # Update instance attributes
        for key, value in style_settings.items():
            if hasattr(self.app, key):
                setattr(self.app, key, value)
        
        # Reconfigure styles
        self.app.configure_styles()
        self.app.apply_style_to_widgets(style_settings)
        
        # Save to config
        self.app.config_manager.set("style_settings", style_settings)
        self.app.config_manager.save_config()
        
        # Update browser if exists
        if hasattr(self.app, 'browser') and self.app.browser:
            self.app.browser.style_manager.update_style_settings(style_settings)
            self.app.browser.save_instances()
    
    def reset_styles(self):
        """Reset to default styles"""
        try:
            # Reset basic settings
            self.primary_color_var.set("#2c3e50")
            self.secondary_color_var.set("#3498db")
            self.success_color_var.set("#27ae60")
            self.warning_color_var.set("#f39c12")
            self.danger_color_var.set("#e74c3c")
            self.disabled_color_var.set("#c0c0c0")
            self.light_bg_var.set("#ecf0f1")
            self.dark_bg_var.set("#34495e")
            self.text_primary_var.set("#2c3e50")
            self.text_light_var.set("#ffffff")
            self.text_dark_var.set("#000000")
            self.font_family_var.set("Arial")
            self.font_size_var.set("9")
            
            # Reset button styles
            self.reset_all_button_styles()
            
            self.apply_to_preview()
            self.app.messages(2, 9, "Styles reset to defaults")
            
        except Exception as e:
            self.app.messages(2, 3, f"Error resetting styles: {e}")
    
    def cancel_changes(self):
        """Cancel changes and close dialog"""
        self.destroy()

    def load_current_styles(self):
        """Load current style settings - FIXED VERSION"""
        try:
            # Load all theme settings
            self.primary_color_var.set(self.current_styles.get('primary_color', '#2c3e50'))
            self.secondary_color_var.set(self.current_styles.get('secondary_color', '#3498db'))
            self.success_color_var.set(self.current_styles.get('success_color', '#27ae60'))
            self.warning_color_var.set(self.current_styles.get('warning_color', '#f39c12'))
            self.danger_color_var.set(self.current_styles.get('danger_color', '#e74c3c'))
            self.disabled_color_var.set(self.current_styles.get('disabled_color', '#c0c0c0'))
            self.light_bg_var.set(self.current_styles.get('light_bg', '#ecf0f1'))
            self.dark_bg_var.set(self.current_styles.get('dark_bg', '#34495e'))
            self.text_primary_var.set(self.current_styles.get('text_primary', '#2c3e50'))
            self.text_light_var.set(self.current_styles.get('text_light', '#ffffff'))
            self.text_dark_var.set(self.current_styles.get('text_dark', '#000000'))
            self.font_family_var.set(self.current_styles.get('font_family', 'Arial'))
            self.font_size_var.set(str(self.current_styles.get('font_size', 9)))
            
            # Load theme
            current_theme = self.style.theme_use()
            self.theme_var.set(self.current_styles.get('theme', current_theme))
            
            # Load button tuning settings
            button_styles = self.current_styles.get('button_styles', {})
            if button_styles:
                print(f"DEBUG: Loading {len(button_styles)} button styles")
                if not hasattr(self, 'button_color_vars'):
                    self.button_color_vars = {}
                
                for style_name, states in button_styles.items():
                    for state, colors in states.items():
                        bg_key = (style_name, state, 'background')
                        fg_key = (style_name, state, 'foreground')
                        
                        if bg_key not in self.button_color_vars:
                            self.button_color_vars[bg_key] = tk.StringVar(value=colors.get('background', ''))
                        else:
                            self.button_color_vars[bg_key].set(colors.get('background', ''))
                        
                        if fg_key not in self.button_color_vars:
                            self.button_color_vars[fg_key] = tk.StringVar(value=colors.get('foreground', ''))
                        else:
                            self.button_color_vars[fg_key].set(colors.get('foreground', ''))
            
            # Load text input settings - FIXED: Always try to load
            text_input_styles = self.current_styles.get('text_input_styles', {})
            print(f"DEBUG: Loading {len(text_input_styles)} text input styles")
            
            # Ensure text_input_vars is initialized
            if not hasattr(self, 'text_input_vars'):
                self.text_input_vars = {}
            
            # Populate the dictionary with saved text input styles
            for widget_type, properties in text_input_styles.items():
                for prop_name, prop_value in properties.items():
                    var_key = (widget_type, prop_name)
                    
                    if var_key not in self.text_input_vars:
                        self.text_input_vars[var_key] = tk.StringVar(value=prop_value)
                    else:
                        self.text_input_vars[var_key].set(prop_value)
            
            # Load treeview settings - ADD THIS
                treeview_styles = self.current_styles.get('treeview_styles', {})
                print(f"DEBUG: Loading {len(treeview_styles)} treeview styles")
            
                # Ensure treeview_vars is initialized
                if not hasattr(self, 'treeview_vars'):
                    self.treeview_vars = {}
            
            # Load window settings - ADD THIS
            window_styles = self.current_styles.get('window_styles', {})
            print(f"DEBUG: Loading {len(window_styles)} window styles")
            
            # Ensure window_vars is initialized
            if not hasattr(self, 'window_vars'):
                self.window_vars = {}
            
            # Populate the dictionary with saved window styles
            for component, properties in window_styles.items():
                for prop_name, prop_value in properties.items():
                    var_key = (component, prop_name)
                    
                    if var_key not in self.window_vars:
                        self.window_vars[var_key] = tk.StringVar(value=prop_value)
                    else:
                        self.window_vars[var_key].set(prop_value)
            
            # Update all current controls
            current_button_style = self.button_style_var.get()
            self.setup_button_color_controls(current_button_style)
            
            current_text_type = self.text_widget_type_var.get()
            self.setup_text_widget_controls(current_text_type)
            
            current_treeview_component = self.treeview_component_var.get()
            self.setup_treeview_component_controls(current_treeview_component)
            
            current_window_component = self.window_component_var.get()
            self.setup_window_component_controls(current_window_component)
                
        except Exception as e:
            print(f"DEBUG: Error loading current styles: {e}")
            self.app.messages(2, 3, f"Error loading current styles: {e}")

    def load_style_presets(self):
        """Load style presets"""
        try:
            # Try to load from config manager
            if hasattr(self.app, 'config_manager'):
                presets = self.app.config_manager.get("style_presets", {})
                self.style_presets = presets
            else:
                # Try to load from browser
                if hasattr(self.app, 'style_presets'):
                    self.style_presets = self.app.style_presets
                else:
                    self.style_presets = {}
            
            # Update preset combo
            preset_names = list(self.style_presets.keys())
            self.preset_combo['values'] = preset_names
            
            if preset_names:
                self.preset_combo.set(preset_names[0])
                print(f"DEBUG: Loaded {len(preset_names)} style presets")
            else:
                print("DEBUG: No style presets found")
                
            # Add default presets if none exist
            if not self.style_presets:
                self._create_default_presets()
                
        except Exception as e:
            print(f"DEBUG: Error loading style presets: {e}")
            self.style_presets = {}
            self._create_default_presets()

    def on_preset_selected(self, event=None):
        """Handle preset selection"""
        preset_name = self.preset_var.get()
        if preset_name and preset_name in self.style_presets:
            try:
                preset = self.style_presets[preset_name]
                
                # Update current styles
                self.current_styles.update(preset)
                
                # Load the preset into the UI controls
                self._load_preset_to_ui(preset)
                
                # IMPORTANT: Apply to preview after a short delay to ensure UI is updated
                self.after(100, self.apply_to_preview)
                
                self.app.messages(2, 9, f"Loaded preset: {preset_name}")
                
            except Exception as e:
                self.app.messages(2, 3, f"Error loading preset: {e}")

    def save_preset(self):
        """Save current style as preset"""
        preset_name = tk.simpledialog.askstring("Save Preset", "Enter preset name:")
        if preset_name:
            # Collect current settings
            preset_data = self.collect_all_settings()
            
            # Save to presets
            self.style_presets[preset_name] = preset_data
            
            # Update UI
            self.preset_combo['values'] = list(self.style_presets.keys())
            self.preset_var.set(preset_name)
            
            # Save to appropriate location
            self._save_presets_to_config()
            
            self.app.messages(2, 9, f"Preset saved: {preset_name}")
            print(f"DEBUG: Saved preset '{preset_name}'")

    def _save_presets_to_config(self):
        """Save presets to the appropriate configuration - FIXED FOR APP DIR"""
        try:
            # Save to config manager if available
            if hasattr(self.app, 'config_manager'):
                self.app.config_manager.set("style_presets", self.style_presets)
                self.app.config_manager.save_config()
                print("DEBUG: Saved presets to config manager")
            
            # Save to browser if available
            elif hasattr(self.app, 'style_presets'):
                self.app.style_presets = self.style_presets
                if hasattr(self.app, 'save_instances'):
                    self.app.save_instances()
                print("DEBUG: Saved presets to browser")
            
            # Save to file in app directory as backup
            if hasattr(self.app, 'app_dir'):
                presets_file = os.path.join(self.app.app_dir, "style_presets.json")
                try:
                    with open(presets_file, 'w') as f:
                        json.dump(self.style_presets, f, indent=2)
                    print(f"DEBUG: Saved presets backup to: {presets_file}")
                except Exception as e:
                    print(f"DEBUG: Error saving presets backup: {e}")
                    
        except Exception as e:
            print(f"DEBUG: Error saving presets to config: {e}")
 
    def delete_preset(self):
        """Delete selected preset"""
        preset_name = self.preset_var.get()
        if preset_name and preset_name in self.style_presets:
            if messagebox.askyesno("Delete Preset", f"Delete preset '{preset_name}'?"):
                # Delete from presets
                del self.style_presets[preset_name]
                
                # Update UI
                preset_names = list(self.style_presets.keys())
                self.preset_combo['values'] = preset_names
                if preset_names:
                    self.preset_combo.set(preset_names[0])
                else:
                    self.preset_var.set('')
                    
                # Save changes
                self._save_presets_to_config()
                
                self.app.messages(2, 9, f"Preset deleted: {preset_name}")
                print(f"DEBUG: Deleted preset '{preset_name}'")

    def _create_default_presets(self):
        """Create default style presets"""
        self.style_presets = {
            "Default Dark": {
                'primary_color': '#2c3e50',
                'secondary_color': '#3498db', 
                'success_color': '#27ae60',
                'warning_color': '#f39c12',
                'danger_color': '#e74c3c',
                'disabled_color': '#c0c0c0',
                'light_bg': '#34495e',
                'dark_bg': '#2c3e50',
                'text_primary': '#ffffff',
                'text_light': '#ffffff',
                'text_dark': '#000000',
                'font_family': 'Arial',
                'font_size': '9',
                'theme': 'classic'
            },
            "Blue Theme": {
                'primary_color': '#2980b9',
                'secondary_color': '#3498db',
                'success_color': '#27ae60', 
                'warning_color': '#f39c12',
                'danger_color': '#e74c3c',
                'disabled_color': '#c0c0c0',
                'light_bg': '#ecf0f1',
                'dark_bg': '#34495e',
                'text_primary': '#2c3e50',
                'text_light': '#ffffff',
                'text_dark': '#000000',
                'font_family': 'Segoe UI',
                'font_size': '9',
                'theme': 'classic'
            },
            "Green Theme": {
                'primary_color': '#27ae60',
                'secondary_color': '#2ecc71',
                'success_color': '#16a085', 
                'warning_color': '#f39c12',
                'danger_color': '#e74c3c',
                'disabled_color': '#c0c0c0',
                'light_bg': '#ecf0f1',
                'dark_bg': '#2c3e50',
                'text_primary': '#2c3e50',
                'text_light': '#ffffff',
                'text_dark': '#000000',
                'font_family': 'Verdana',
                'font_size': '9',
                'theme': 'classic'
            }
        }
        
        # Update preset combo
        preset_names = list(self.style_presets.keys())
        self.preset_combo['values'] = preset_names
        if preset_names:
            self.preset_combo.set(preset_names[0])
        
        print("DEBUG: Created default style presets")

    def _load_preset_to_ui(self, preset):
        """Load preset data into UI controls"""
        # Basic settings
        self.primary_color_var.set(preset.get('primary_color', '#2c3e50'))
        self.secondary_color_var.set(preset.get('secondary_color', '#3498db'))
        self.success_color_var.set(preset.get('success_color', '#27ae60'))
        self.warning_color_var.set(preset.get('warning_color', '#f39c12'))
        self.danger_color_var.set(preset.get('danger_color', '#e74c3c'))
        self.disabled_color_var.set(preset.get('disabled_color', '#c0c0c0'))
        self.light_bg_var.set(preset.get('light_bg', '#ecf0f1'))
        self.dark_bg_var.set(preset.get('dark_bg', '#34495e'))
        self.text_primary_var.set(preset.get('text_primary', '#2c3e50'))
        self.text_light_var.set(preset.get('text_light', '#ffffff'))
        self.text_dark_var.set(preset.get('text_dark', '#000000'))
        self.font_family_var.set(preset.get('font_family', 'Arial'))
        self.font_size_var.set(str(preset.get('font_size', 9)))
        
        # Theme
        if 'theme' in preset:
            self.theme_var.set(preset['theme'])
        
        # Button styles
        button_styles = preset.get('button_styles', {})
        if button_styles:
            # Initialize the button_color_vars dictionary
            if not hasattr(self, 'button_color_vars'):
                self.button_color_vars = {}
            
            # Populate the dictionary with saved button styles
            for style_name, states in button_styles.items():
                for state, colors in states.items():
                    bg_key = (style_name, state, 'background')
                    fg_key = (style_name, state, 'foreground')
                    
                    if bg_key not in self.button_color_vars:
                        self.button_color_vars[bg_key] = tk.StringVar(value=colors.get('background'))
                    else:
                        self.button_color_vars[bg_key].set(colors.get('background'))
                    
                    if fg_key not in self.button_color_vars:
                        self.button_color_vars[fg_key] = tk.StringVar(value=colors.get('foreground'))
                    else:
                        self.button_color_vars[fg_key].set(colors.get('foreground'))

    # ==================== BUTTON STYLE MANAGEMENT ====================

    def setup_button_style_management(self):
        """Setup button style file management system - FIXED FOR APP DIR"""
        # Use application directory instead of user home directory
        if hasattr(self.app, 'app_dir'):
            # Browser instance
            self.button_styles_dir = os.path.join(self.app.app_dir, "button_styles")
        elif hasattr(self.app, 'config_manager') and hasattr(self.app.config_manager, 'config_dir'):
            # Standalone instance
            self.button_styles_dir = os.path.join(self.app.config_manager.config_dir, "button_styles")
        else:
            # Fallback to current directory
            self.button_styles_dir = os.path.join(os.getcwd(), "config", "button_styles")
        
        # Create directory if it doesn't exist
        if not os.path.exists(self.button_styles_dir):
            os.makedirs(self.button_styles_dir)
            print(f"DEBUG: Created button styles directory: {self.button_styles_dir}")
        
        # Load available button style files
        self.load_button_style_files()
        print(f"DEBUG: Button styles directory: {self.button_styles_dir}")

    def load_button_style_files(self):
        """Load all available button style files"""
        self.button_style_files = {}
        
        if not os.path.exists(self.button_styles_dir):
            return
        
        for filename in os.listdir(self.button_styles_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.button_styles_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        style_data = json.load(f)
                        style_name = filename[:-5]  # Remove .json extension
                        self.button_style_files[style_name] = style_data
                except Exception as e:
                    print(f"DEBUG: Error loading button style file {filename}: {e}")

    def update_button_file_combo(self):
        """Update the button file combo with available files"""
        file_names = list(self.button_style_files.keys())
        self.button_file_combo['values'] = file_names
        if file_names:
            self.button_file_combo.set(file_names[0])

    def on_button_file_selected(self, event=None):
        """Handle button file selection"""
        file_name = self.button_file_var.get()
        if file_name:
            self.load_button_style_file(file_name)

    def load_current_button_file(self):
        """Load the currently selected button file"""
        file_name = self.button_file_var.get()
        if file_name:
            self.load_button_style_file(file_name)

    def save_button_style_as(self):
        """Save current button styles with a new name"""
        style_name = tk.simpledialog.askstring("Save Button Styles", "Enter style name:")
        if style_name:
            if self.save_button_style_file(style_name):
                self.update_button_file_combo()
                self.button_file_var.set(style_name)

    def delete_current_button_file(self):
        """Delete the currently selected button file"""
        file_name = self.button_file_var.get()
        if file_name:
            if messagebox.askyesno("Delete Button Styles", f"Delete button style '{file_name}'?"):
                if self.delete_button_style_file(file_name):
                    self.update_button_file_combo()

    def save_button_style_file(self, style_name):
        """Save current button styles to a file"""
        try:
            button_settings = self.collect_button_tuning_settings()
            if not button_settings:
                self.app.messages(2, 3, "No button styles to save")
                return False
            
            filename = f"{style_name}.json"
            filepath = os.path.join(self.button_styles_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(button_settings, f, indent=2)
            
            # Reload the files
            self.load_button_style_files()
            self.app.messages(2, 9, f"Button styles saved: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error saving button styles: {e}")
            return False

    def load_button_style_file(self, style_name):
        """Load button styles from a file"""
        try:
            if style_name not in self.button_style_files:
                self.app.messages(2, 3, f"Button style file not found: {style_name}")
                return False
            
            button_settings = self.button_style_files[style_name]
            self.apply_button_style_settings(button_settings)
            self.app.messages(2, 9, f"Button styles loaded: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error loading button styles: {e}")
            return False

    def delete_button_style_file(self, style_name):
        """Delete a button style file"""
        try:
            filename = f"{style_name}.json"
            filepath = os.path.join(self.button_styles_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                # Reload the files
                self.load_button_style_files()
                self.app.messages(2, 9, f"Button styles deleted: {style_name}")
                return True
            else:
                self.app.messages(2, 3, f"Button style file not found: {style_name}")
                return False
                
        except Exception as e:
            self.app.messages(2, 3, f"Error deleting button styles: {e}")
            return False

    def apply_button_style_settings(self, button_settings):
        """Apply button style settings to the UI controls"""
        try:
            # Initialize button_color_vars if it doesn't exist
            if not hasattr(self, 'button_color_vars'):
                self.button_color_vars = {}
            
            # Apply settings to all button styles
            for style_name, states in button_settings.items():
                for state, colors in states.items():
                    bg_key = (style_name, state, 'background')
                    fg_key = (style_name, state, 'foreground')
                    
                    # Create or update the variables
                    if bg_key not in self.button_color_vars:
                        self.button_color_vars[bg_key] = tk.StringVar(value=colors['background'])
                    else:
                        self.button_color_vars[bg_key].set(colors['background'])
                    
                    if fg_key not in self.button_color_vars:
                        self.button_color_vars[fg_key] = tk.StringVar(value=colors['foreground'])
                    else:
                        self.button_color_vars[fg_key].set(colors['foreground'])
            
            # Update the current button style controls if they're visible
            current_style = self.button_style_var.get()
            self.setup_button_color_controls(current_style)
            
            # Update preview
            self.apply_to_preview()
            
        except Exception as e:
            print(f"DEBUG: Error applying button style settings: {e}")

    def reset_all_button_styles(self):
        """Reset all button styles to defaults"""
        if messagebox.askyesno("Reset Button Styles", "Reset all button styles to defaults?"):
            try:
                # Clear all button color variables
                if hasattr(self, 'button_color_vars'):
                    self.button_color_vars.clear()
                
                # Reset current controls
                current_style = self.button_style_var.get()
                self.setup_button_color_controls(current_style)
                
                # Update preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "All button styles reset to defaults")
                
            except Exception as e:
                self.app.messages(2, 3, f"Error resetting button styles: {e}")

    def apply_button_styles_to_theme(self):
        """Apply current button styles to the main theme"""
        try:
            button_settings = self.collect_button_tuning_settings()
            if button_settings:
                # Update the current styles with button settings
                self.current_styles['button_styles'] = button_settings
                
                # Apply to preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "Button styles applied to current theme")
            else:
                self.app.messages(2, 3, "No button styles to apply")
                
        except Exception as e:
            self.app.messages(2, 3, f"Error applying button styles: {e}")

    def copy_button_styles(self):
        """Copy current button style settings to other styles"""
        current_style = self.button_style_var.get()
        if not hasattr(self, 'button_color_vars'):
            return
            
        # Get current style settings
        source_settings = {}
        for state in ["normal", "active", "pressed", "disabled"]:
            bg_key = (current_style, state, 'background')
            fg_key = (current_style, state, 'foreground')
            
            if bg_key in self.button_color_vars and fg_key in self.button_color_vars:
                source_settings[state] = {
                    'background': self.button_color_vars[bg_key].get(),
                    'foreground': self.button_color_vars[fg_key].get()
                }
        
        # Copy to other styles
        target_styles = ["TButton", "Primary.TButton", "Success.TButton", "Warning.TButton", "Danger.TButton"]
        target_styles.remove(current_style)  # Don't copy to self
        
        for target_style in target_styles:
            for state, colors in source_settings.items():
                bg_key = (target_style, state, 'background')
                fg_key = (target_style, state, 'foreground')
                
                if bg_key in self.button_color_vars:
                    self.button_color_vars[bg_key].set(colors['background'])
                if fg_key in self.button_color_vars:
                    self.button_color_vars[fg_key].set(colors['foreground'])
        
        self.apply_to_preview()
        self.app.messages(2, 9, f"Copied {current_style} settings to other button styles")

    # ==================== BUTTON TUNING METHODS ====================

    def on_button_style_selected(self, event=None):
        """Handle button style selection change"""
        selected_style = self.button_style_var.get()
        self.setup_button_color_controls(selected_style)
        self.app.messages(2, 9, f"Now editing: {selected_style}")
    
    def choose_button_color(self, button_style, state_key, color_type, color_var):
        """Simplified color chooser that directly updates the StringVar"""
        try:
            current_color = color_var.get()
            
            color = askcolor(
                title=f"Choose {button_style} {state_key} {color_type}",
                initialcolor=current_color
            )
            
            if color[1]:  # color[1] is the hex code
                color_var.set(color[1])
                # No need to manually call update_button_style_preview 
                # because the trace on the StringVar will handle it automatically
                
        except Exception as e:
            print(f"DEBUG: Error in choose_button_color_simple: {e}")
            self.app.messages(2, 3, f"Error choosing color: {e}")
    
    def get_current_button_colors(self, button_style):
        """Get current colors for a button style from style manager"""
        # Default colors based on button style
        default_colors = {
            "TButton": {
                "normal": {"background": "#3498db", "foreground": "#ffffff"},
                "active": {"background": "#2980b9", "foreground": "#ffffff"},
                "pressed": {"background": "#21618c", "foreground": "#ffffff"},
                "disabled": {"background": "#bdc3c7", "foreground": "#7f8c8d"}
            },
            "Primary.TButton": {
                "normal": {"background": "#3498db", "foreground": "#ffffff"},
                "active": {"background": "#2980b9", "foreground": "#ffffff"},
                "pressed": {"background": "#21618c", "foreground": "#ffffff"},
                "disabled": {"background": "#bdc3c7", "foreground": "#7f8c8d"}
            },
            "Success.TButton": {
                "normal": {"background": "#27ae60", "foreground": "#ffffff"},
                "active": {"background": "#229954", "foreground": "#ffffff"},
                "pressed": {"background": "#1e8449", "foreground": "#ffffff"},
                "disabled": {"background": "#bdc3c7", "foreground": "#7f8c8d"}
            },
            "Warning.TButton": {
                "normal": {"background": "#f39c12", "foreground": "#000000"},
                "active": {"background": "#e67e22", "foreground": "#000000"},
                "pressed": {"background": "#d68910", "foreground": "#000000"},
                "disabled": {"background": "#bdc3c7", "foreground": "#7f8c8d"}
            },
            "Danger.TButton": {
                "normal": {"background": "#e74c3c", "foreground": "#ffffff"},
                "active": {"background": "#c0392b", "foreground": "#ffffff"},
                "pressed": {"background": "#a93226", "foreground": "#ffffff"},
                "disabled": {"background": "#bdc3c7", "foreground": "#7f8c8d"}
            }
        }
        
        # Try to get actual current colors from style manager
        try:
            style = ttk.Style()
            actual_colors = {}
            
            for state in ["normal", "active", "pressed", "disabled"]:
                # Try to get actual configured colors
                try:
                    bg = style.lookup(button_style, "background", [state])
                    fg = style.lookup(button_style, "foreground", [state])
                    actual_colors[state] = {
                        "background": bg if bg else default_colors[button_style][state]["background"],
                        "foreground": fg if fg else default_colors[button_style][state]["foreground"]
                    }
                except:
                    actual_colors[state] = default_colors[button_style][state]
            
            return actual_colors
        except:
            return default_colors.get(button_style, default_colors["TButton"])
    
    def collect_button_tuning_settings(self):
        """Collect all button tuning settings - FIXED VERSION"""
        button_settings = {}
        
        if not hasattr(self, 'button_color_vars') or not self.button_color_vars:
            print("DEBUG: No button color variables found")
            return button_settings
        
        button_styles = ["TButton", "Primary.TButton", "Success.TButton", "Warning.TButton", "Danger.TButton"]
        
        for style in button_styles:
            style_settings = {}
            has_settings = False
            
            for state in ["normal", "active", "pressed", "disabled"]:
                bg_key = (style, state, 'background')
                fg_key = (style, state, 'foreground')
                
                if bg_key in self.button_color_vars and fg_key in self.button_color_vars:
                    bg_value = self.button_color_vars[bg_key].get().strip()
                    fg_value = self.button_color_vars[fg_key].get().strip()
                    
                    # Validate colors are not empty
                    if bg_value and fg_value:
                        style_settings[state] = {
                            "background": bg_value,
                            "foreground": fg_value
                        }
                        has_settings = True
                        print(f"DEBUG: Collected {style}.{state}: bg={bg_value}, fg={fg_value}")
            
            if has_settings:
                button_settings[style] = style_settings
        
        print(f"DEBUG: Collected {len(button_settings)} button styles")
        return button_settings

    def _apply_button_style_to_preview(self, style_name, style_settings):
        """Apply specific button style to preview buttons"""
        try:
            preview_style = ttk.Style()
            temp_style_name = f"Preview.{style_name}"
            
            # Configure normal state
            if 'normal' in style_settings:
                preview_style.configure(
                    temp_style_name,
                    background=style_settings['normal'].get('background'),
                    foreground=style_settings['normal'].get('foreground')
                )
            
            # Configure state mappings
            background_map = []
            foreground_map = []
            
            for state in ['active', 'pressed', 'disabled']:
                if state in style_settings:
                    bg = style_settings[state].get('background')
                    fg = style_settings[state].get('foreground')
                    
                    if bg:
                        background_map.append((state, bg))
                    if fg:
                        foreground_map.append((state, fg))
            
            if background_map:
                preview_style.map(temp_style_name, background=background_map)
            if foreground_map:
                preview_style.map(temp_style_name, foreground=foreground_map)
            
            # Update the corresponding preview button
            button_attr_map = {
                "TButton": "preview_btn_default",
                "Primary.TButton": "preview_btn_primary", 
                "Success.TButton": "preview_btn_success",
                "Warning.TButton": "preview_btn_warning",
                "Danger.TButton": "preview_btn_danger"
            }
            
            if style_name in button_attr_map:
                button_attr = button_attr_map[style_name]
                if hasattr(self, button_attr):
                    button = getattr(self, button_attr)
                    button.configure(style=temp_style_name)
                    
        except Exception as e:
            print(f"DEBUG: Error applying button style {style_name}: {e}")

    # ==================== TEXT TUNING METHODS ====================

    def setup_text_inputs_tab(self):
        """Setup the text and input fields styling tab"""
        # Create the new tab
        self._create_scrollable_frame(self.text_inputs_tab)
        
        # File management section
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="Text Input Style Files", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_subframe = ttk.Frame(file_frame)
        file_subframe.pack(fill=tk.X)
        
        ttk.Label(file_subframe, text="Style Files:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.text_input_file_var = tk.StringVar()
        self.text_input_file_combo = ttk.Combobox(
            file_subframe, 
            textvariable=self.text_input_file_var,
            state="readonly",
            width=20
        )
        self.text_input_file_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.text_input_file_combo.bind('<<ComboboxSelected>>', self.on_text_input_file_selected)
        
        file_btn_frame = ttk.Frame(file_subframe)
        file_btn_frame.pack(side=tk.LEFT)
        
        ttk.Button(file_btn_frame, text="Load", 
                  command=self.load_current_text_input_file, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Save As", 
                  command=self.save_text_input_style_as, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Delete", 
                  command=self.delete_current_text_input_file, width=8).pack(side=tk.LEFT)
        
        # Widget type selection
        widget_selection_frame = ttk.LabelFrame(self.scrollable_frame, text="Widget Type Selection", padding="5")
        widget_selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(widget_selection_frame, text="Select Widget Type:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.text_widget_type_var = tk.StringVar(value="TEntry")
        self.text_widget_type_combo = ttk.Combobox(
            widget_selection_frame, 
            textvariable=self.text_widget_type_var,
            values=["TEntry", "Modern.TEntry", "TCombobox", "Text", "Listbox"],
            state="readonly",
            width=20
        )
        self.text_widget_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.text_widget_type_combo.bind('<<ComboboxSelected>>', self.on_text_widget_type_selected)
        
        # Style controls frame - will be populated dynamically
        self.text_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Style Controls", padding="5")
        self.text_controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Quick actions frame
        quick_actions_frame = ttk.LabelFrame(self.scrollable_frame, text="Quick Actions", padding="5")
        quick_actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        action_subframe = ttk.Frame(quick_actions_frame)
        action_subframe.pack(fill=tk.X)
        
        ttk.Button(action_subframe, text="Reset All to Defaults", 
                  command=self.reset_all_text_input_styles, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Copy to Other Widgets", 
                  command=self.copy_text_input_styles, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Apply to Theme", 
                  command=self.apply_text_input_styles_to_theme, width=15).pack(side=tk.LEFT)
        
        # Initialize with default widget type
        self.setup_text_widget_controls("TEntry")
        self.update_text_input_file_combo()

    def setup_text_input_style_management(self):
        """Setup text input style file management system - FIXED FOR APP DIR"""
        # Use application directory instead of user home directory
        if hasattr(self.app, 'app_dir'):
            # Browser instance
            self.text_input_styles_dir = os.path.join(self.app.app_dir, "text_input_styles")
        elif hasattr(self.app, 'config_manager') and hasattr(self.app.config_manager, 'config_dir'):
            # Standalone instance
            self.text_input_styles_dir = os.path.join(self.app.config_manager.config_dir, "text_input_styles")
        else:
            # Fallback to current directory
            self.text_input_styles_dir = os.path.join(os.getcwd(), "config", "text_input_styles")
        
        # Create directory if it doesn't exist
        if not os.path.exists(self.text_input_styles_dir):
            os.makedirs(self.text_input_styles_dir)
            print(f"DEBUG: Created text input styles directory: {self.text_input_styles_dir}")
        
        # Load available text input style files
        self.load_text_input_style_files()
        print(f"DEBUG: Text input styles directory: {self.text_input_styles_dir}")

    def load_text_input_style_files(self):
        """Load all available text input style files"""
        self.text_input_style_files = {}
        
        if not os.path.exists(self.text_input_styles_dir):
            return
        
        for filename in os.listdir(self.text_input_styles_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.text_input_styles_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        style_data = json.load(f)
                        style_name = filename[:-5]  # Remove .json extension
                        self.text_input_style_files[style_name] = style_data
                except Exception as e:
                    print(f"DEBUG: Error loading text input style file {filename}: {e}")
    
    def update_text_input_file_combo(self):
        """Update the text input file combo with available files"""
        file_names = list(self.text_input_style_files.keys())
        self.text_input_file_combo['values'] = file_names
        if file_names:
            self.text_input_file_combo.set(file_names[0])

    def setup_text_widget_controls(self, widget_type):
        """Setup controls for the selected text widget type - WITH FOCUS STATES"""
        # Clear existing controls
        for widget in self.text_controls_frame.winfo_children():
            widget.destroy()
        
        # Get current styles for this widget type
        current_styles = self.get_current_text_widget_styles(widget_type)
        
        # Initialize the dictionary if it doesn't exist
        if not hasattr(self, 'text_input_vars'):
            self.text_input_vars = {}
        
        # Common properties for all widget types
        common_properties = [
            ("background", "Background"),
            ("foreground", "Text Color"),
            ("font_family", "Font Family"),
            ("font_size", "Font Size"),
            ("padding_x", "Padding X"),
            ("padding_y", "Padding Y")
        ]
        
        # Widget-specific properties
        widget_specific_properties = {
            "TEntry": [
                ("fieldbackground", "Field Background"),
                ("bordercolor", "Border Color"),
                ("focuscolor", "Focus Color")
            ],
            "Modern.TEntry": [
                ("fieldbackground", "Field Background"),
                ("bordercolor", "Border Color"),
                ("focuscolor", "Focus Color")
            ],
            "TCombobox": [
                ("fieldbackground", "Field Background"),
                ("arrowcolor", "Arrow Color"),
                ("bordercolor", "Border Color")
            ],
            "Text": [
                ("selectbackground", "Selection Background"),
                ("selectforeground", "Selection Text"),
                ("insertbackground", "Cursor Color"),
                ("relief", "Border Style"),
                ("borderwidth", "Border Width")
            ],
            "Listbox": [
                ("selectbackground", "Selection Background"),
                ("selectforeground", "Selection Text"),
                ("relief", "Border Style"),
                ("borderwidth", "Border Width")
            ]
        }
        
        # Create controls for common properties
        for prop_key, prop_label in common_properties:
            prop_frame = ttk.Frame(self.text_controls_frame)
            prop_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(prop_frame, text=prop_label, width=15).pack(side=tk.LEFT)
            
            # Create StringVar and store in dictionary
            var_key = (widget_type, prop_key)
            current_value = current_styles.get(prop_key, "")
            
            if var_key not in self.text_input_vars:
                self.text_input_vars[var_key] = tk.StringVar(value=current_value)
            
            # Special handling for font family and font size
            if prop_key == "font_family":
                font_combo = ttk.Combobox(prop_frame, textvariable=self.text_input_vars[var_key],
                                        values=["Arial", "Helvetica", "Times New Roman", "IBM Plex Mono Text", "IBM Plex Mono Medium", "Courier New", 
                                               "Verdana", "Tahoma", "Segoe UI", "System"])
                font_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
            elif prop_key == "font_size":
                size_combo = ttk.Combobox(prop_frame, textvariable=self.text_input_vars[var_key],
                                        values=["8", "9", "10", "11", "12", "14", "16", "18"])
                size_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
            else:
                entry = ttk.Entry(prop_frame, textvariable=self.text_input_vars[var_key], width=15)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                
                if prop_key in ["background", "foreground", "fieldbackground", "selectbackground"]:
                    ttk.Button(prop_frame, text="Choose", 
                              command=lambda wk=widget_type, pk=prop_key, var=self.text_input_vars[var_key]: 
                              self.choose_text_input_color(wk, pk, var),
                              width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Create controls for widget-specific properties
        if widget_type in widget_specific_properties:
            separator = ttk.Separator(self.text_controls_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=10)
            
            specific_label = ttk.Label(self.text_controls_frame, text=f"{widget_type} Specific:", 
                                     font=("Arial", 9, "bold"))
            specific_label.pack(anchor=tk.W, pady=(5, 10))
            
            for prop_key, prop_label in widget_specific_properties[widget_type]:
                prop_frame = ttk.Frame(self.text_controls_frame)
                prop_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(prop_frame, text=prop_label, width=15).pack(side=tk.LEFT)
                
                # Create StringVar and store in dictionary
                var_key = (widget_type, prop_key)
                current_value = current_styles.get(prop_key, "")
                
                if var_key not in self.text_input_vars:
                    self.text_input_vars[var_key] = tk.StringVar(value=current_value)
                
                entry = ttk.Entry(prop_frame, textvariable=self.text_input_vars[var_key], width=15)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                
                if "color" in prop_key or "background" in prop_key:
                    ttk.Button(prop_frame, text="Choose", 
                              command=lambda wk=widget_type, pk=prop_key, var=self.text_input_vars[var_key]: 
                              self.choose_text_input_color(wk, pk, var),
                              width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # ADD STATE CONTROLS FOR TTK WIDGETS - NEW SECTION
        if widget_type in ["TEntry", "Modern.TEntry", "TCombobox"]:
            separator = ttk.Separator(self.text_controls_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=10)
            
            state_label = ttk.Label(self.text_controls_frame, text="State Colors:", 
                                   font=("Arial", 9, "bold"))
            state_label.pack(anchor=tk.W, pady=(5, 10))
            
            # Focus state
            focus_frame = ttk.Frame(self.text_controls_frame)
            focus_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(focus_frame, text="Focus Border:", width=15).pack(side=tk.LEFT)
            
            focus_border_key = (widget_type, "focus_bordercolor")
            focus_border_value = current_styles.get("focus_bordercolor", current_styles.get("bordercolor", "#3498db"))
            
            if focus_border_key not in self.text_input_vars:
                self.text_input_vars[focus_border_key] = tk.StringVar(value=focus_border_value)
            
            focus_border_entry = ttk.Entry(focus_frame, textvariable=self.text_input_vars[focus_border_key], width=15)
            focus_border_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
            
            ttk.Button(focus_frame, text="Choose", 
                      command=lambda wk=widget_type, var=self.text_input_vars[focus_border_key]: 
                      self.choose_text_input_color(wk, "focus_bordercolor", var),
                      width=8).pack(side=tk.LEFT, padx=(5, 0))
            
            # Focus background
            focus_bg_frame = ttk.Frame(self.text_controls_frame)
            focus_bg_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(focus_bg_frame, text="Focus BG:", width=15).pack(side=tk.LEFT)
            
            focus_bg_key = (widget_type, "focus_fieldbackground")
            focus_bg_value = current_styles.get("focus_fieldbackground", current_styles.get("fieldbackground", "#ffffff"))
            
            if focus_bg_key not in self.text_input_vars:
                self.text_input_vars[focus_bg_key] = tk.StringVar(value=focus_bg_value)
            
            focus_bg_entry = ttk.Entry(focus_bg_frame, textvariable=self.text_input_vars[focus_bg_key], width=15)
            focus_bg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
            
            ttk.Button(focus_bg_frame, text="Choose", 
                      command=lambda wk=widget_type, var=self.text_input_vars[focus_bg_key]: 
                      self.choose_text_input_color(wk, "focus_fieldbackground", var),
                      width=8).pack(side=tk.LEFT, padx=(5, 0))
            
            # Hover state
            hover_frame = ttk.Frame(self.text_controls_frame)
            hover_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(hover_frame, text="Hover Border:", width=15).pack(side=tk.LEFT)
            
            hover_border_key = (widget_type, "hover_bordercolor")
            hover_border_value = current_styles.get("hover_bordercolor", current_styles.get("bordercolor", "#2c3e50"))
            
            if hover_border_key not in self.text_input_vars:
                self.text_input_vars[hover_border_key] = tk.StringVar(value=hover_border_value)
            
            hover_border_entry = ttk.Entry(hover_frame, textvariable=self.text_input_vars[hover_border_key], width=15)
            hover_border_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
            
            ttk.Button(hover_frame, text="Choose", 
                      command=lambda wk=widget_type, var=self.text_input_vars[hover_border_key]: 
                      self.choose_text_input_color(wk, "hover_bordercolor", var),
                      width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Add trace to auto-update preview
        for var_key, var in self.text_input_vars.items():
            if var_key[0] == widget_type:  # Only trace variables for current widget type
                var.trace('w', self.schedule_preview_update)

    def get_current_text_widget_styles(self, widget_type):
        """Get current styles for a text widget type - WITH STATE COLORS"""
        # Default styles based on widget type
        default_styles = {
            "TEntry": {
                "background": "#ffffff",
                "foreground": "#000000",
                "fieldbackground": "#ffffff",
                "font_family": "Arial",
                "font_size": "9",
                "padding_x": "5",
                "padding_y": "2",
                "bordercolor": "#cccccc",
                "focuscolor": "#3498db",
                "focus_bordercolor": "#3498db",
                "focus_fieldbackground": "#ffffff",
                "hover_bordercolor": "#2c3e50"
            },
            "Modern.TEntry": {
                "background": "#ffffff",
                "foreground": "#000000",
                "fieldbackground": "#ffffff",
                "font_family": "Arial",
                "font_size": "9",
                "padding_x": "5",
                "padding_y": "2",
                "bordercolor": "#3498db",
                "focuscolor": "#2980b9",
                "focus_bordercolor": "#2980b9",
                "focus_fieldbackground": "#ffffff",
                "hover_bordercolor": "#2c3e50"
            },
            "TCombobox": {
                "background": "#ffffff",
                "foreground": "#000000",
                "fieldbackground": "#ffffff",
                "font_family": "Arial",
                "font_size": "9",
                "padding_x": "5",
                "padding_y": "2",
                "arrowcolor": "#3498db",
                "bordercolor": "#cccccc",
                "focus_bordercolor": "#3498db",
                "focus_fieldbackground": "#ffffff",
                "hover_bordercolor": "#2c3e50"
            },
            "Text": {
                "background": "#ffffff",
                "foreground": "#000000",
                "font_family": "Arial",
                "font_size": "9",
                "padding_x": "5",
                "padding_y": "5",
                "selectbackground": "#3498db",
                "selectforeground": "#ffffff",
                "insertbackground": "#000000",
                "relief": "solid",
                "borderwidth": "1"
            },
            "Listbox": {
                "background": "#ffffff",
                "foreground": "#000000",
                "font_family": "Arial",
                "font_size": "9",
                "selectbackground": "#3498db",
                "selectforeground": "#ffffff",
                "relief": "solid",
                "borderwidth": "1"
            }
        }
        
        # Try to get actual current styles
        try:
            style = ttk.Style()
            actual_styles = default_styles[widget_type].copy()
            
            if widget_type in ["TEntry", "Modern.TEntry", "TCombobox"]:
                # For ttk widgets, try to get actual configured styles
                try:
                    bg = style.lookup(widget_type, "background")
                    if bg:
                        actual_styles["background"] = bg
                except:
                    pass
                    
                try:
                    fg = style.lookup(widget_type, "foreground")
                    if fg:
                        actual_styles["foreground"] = fg
                except:
                    pass
                    
                try:
                    field_bg = style.lookup(widget_type, "fieldbackground")
                    if field_bg:
                        actual_styles["fieldbackground"] = field_bg
                except:
                    pass
            
            return actual_styles
        except:
            return default_styles.get(widget_type, default_styles["TEntry"])

    def choose_text_input_color(self, widget_type, property_key, color_var):
        """Color chooser for text input properties"""
        try:
            current_color = color_var.get()
            
            color = askcolor(
                title=f"Choose {widget_type} {property_key}",
                initialcolor=current_color
            )
            
            if color[1]:  # color[1] is the hex code
                color_var.set(color[1])
                
        except Exception as e:
            print(f"DEBUG: Error in choose_text_input_color: {e}")
            self.app.messages(2, 3, f"Error choosing color: {e}")
    
    def on_text_widget_type_selected(self, event=None):
        """Handle text widget type selection change"""
        selected_type = self.text_widget_type_var.get()
        self.setup_text_widget_controls(selected_type)
        self.app.messages(2, 9, f"Now editing: {selected_type}")

    def on_text_input_file_selected(self, event=None):
        """Handle text input file selection"""
        file_name = self.text_input_file_var.get()
        if file_name:
            self.load_text_input_style_file(file_name)
    
    def load_current_text_input_file(self):
        """Load the currently selected text input file"""
        file_name = self.text_input_file_var.get()
        if file_name:
            self.load_text_input_style_file(file_name)
    
    def save_text_input_style_as(self):
        """Save current text input styles with a new name"""
        style_name = tk.simpledialog.askstring("Save Text Input Styles", "Enter style name:")
        if style_name:
            if self.save_text_input_style_file(style_name):
                self.update_text_input_file_combo()
                self.text_input_file_var.set(style_name)
    
    def delete_current_text_input_file(self):
        """Delete the currently selected text input file"""
        file_name = self.text_input_file_var.get()
        if file_name:
            if messagebox.askyesno("Delete Text Input Styles", f"Delete text input style '{file_name}'?"):
                if self.delete_text_input_style_file(file_name):
                    self.update_text_input_file_combo()
    
    def save_text_input_style_file(self, style_name):
        """Save current text input styles to a file"""
        try:
            text_input_settings = self.collect_text_input_settings()
            if not text_input_settings:
                self.app.messages(2, 3, "No text input styles to save")
                return False
            
            filename = f"{style_name}.json"
            filepath = os.path.join(self.text_input_styles_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(text_input_settings, f, indent=2)
            
            # Reload the files
            self.load_text_input_style_files()
            self.app.messages(2, 9, f"Text input styles saved: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error saving text input styles: {e}")
            return False
    
    def load_text_input_style_file(self, style_name):
        """Load text input styles from a file"""
        try:
            if style_name not in self.text_input_style_files:
                self.app.messages(2, 3, f"Text input style file not found: {style_name}")
                return False
            
            text_input_settings = self.text_input_style_files[style_name]
            self.apply_text_input_style_settings(text_input_settings)
            self.app.messages(2, 9, f"Text input styles loaded: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error loading text input styles: {e}")
            return False
    
    def delete_text_input_style_file(self, style_name):
        """Delete a text input style file"""
        try:
            filename = f"{style_name}.json"
            filepath = os.path.join(self.text_input_styles_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                # Reload the files
                self.load_text_input_style_files()
                self.app.messages(2, 9, f"Text input styles deleted: {style_name}")
                return True
            else:
                self.app.messages(2, 3, f"Text input style file not found: {style_name}")
                return False
                
        except Exception as e:
            self.app.messages(2, 3, f"Error deleting text input styles: {e}")
            return False

    def collect_text_input_settings(self):
        """Collect all text input settings - FIXED VERSION"""
        text_input_settings = {}
        
        if not hasattr(self, 'text_input_vars') or not self.text_input_vars:
            print("DEBUG: No text_input_vars dictionary found or empty")
            return text_input_settings
        
        widget_types = ["TEntry", "Modern.TEntry", "TCombobox", "Text", "Listbox"]
        
        for widget_type in widget_types:
            widget_settings = {}
            has_settings = False
            
            # Get all properties for this widget type
            for var_key, var in self.text_input_vars.items():
                if var_key[0] == widget_type:
                    property_name = var_key[1]
                    value = var.get().strip()
                    
                    # Only include if we have a non-empty value
                    if value:
                        widget_settings[property_name] = value
                        has_settings = True
                        print(f"DEBUG: Collected {widget_type}.{property_name}: {value}")
            
            if has_settings:
                text_input_settings[widget_type] = widget_settings
        
        print(f"DEBUG: Collected {len(text_input_settings)} text input widget styles")
        return text_input_settings

    def apply_text_input_style_settings(self, text_input_settings):
        """Apply text input style settings to the UI controls"""
        try:
            # Initialize text_input_vars if it doesn't exist
            if not hasattr(self, 'text_input_vars'):
                self.text_input_vars = {}
            
            # Apply settings to all widget types
            for widget_type, properties in text_input_settings.items():
                for prop_name, prop_value in properties.items():
                    var_key = (widget_type, prop_name)
                    
                    # Create or update the variables
                    if var_key not in self.text_input_vars:
                        self.text_input_vars[var_key] = tk.StringVar(value=prop_value)
                    else:
                        self.text_input_vars[var_key].set(prop_value)
            
            # Update the current widget type controls if they're visible
            current_type = self.text_widget_type_var.get()
            self.setup_text_widget_controls(current_type)
            
            # Update preview
            self.apply_to_preview()
            
        except Exception as e:
            print(f"DEBUG: Error applying text input style settings: {e}")
    
    def reset_all_text_input_styles(self):
        """Reset all text input styles to defaults"""
        if messagebox.askyesno("Reset Text Input Styles", "Reset all text input styles to defaults?"):
            try:
                # Clear all text input variables
                if hasattr(self, 'text_input_vars'):
                    self.text_input_vars.clear()
                
                # Reset current controls
                current_type = self.text_widget_type_var.get()
                self.setup_text_widget_controls(current_type)
                
                # Update preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "All text input styles reset to defaults")
                
            except Exception as e:
                self.app.messages(2, 3, f"Error resetting text input styles: {e}")
    
    def apply_text_input_styles_to_theme(self):
        """Apply current text input styles to the main theme"""
        try:
            text_input_settings = self.collect_text_input_settings()
            if text_input_settings:
                # Update the current styles with text input settings
                self.current_styles['text_input_styles'] = text_input_settings
                
                # Apply to preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "Text input styles applied to current theme")
            else:
                self.app.messages(2, 3, "No text input styles to apply")
                
        except Exception as e:
            self.app.messages(2, 3, f"Error applying text input styles: {e}")
    
    def copy_text_input_styles(self):
        """Copy current text input style settings to other widgets"""
        current_type = self.text_widget_type_var.get()
        if not hasattr(self, 'text_input_vars'):
            return
            
        # Get current widget settings
        source_settings = {}
        for var_key, var in self.text_input_vars.items():
            if var_key[0] == current_type:
                source_settings[var_key[1]] = var.get()
        
        # Copy to other widget types
        target_types = ["TEntry", "Modern.TEntry", "TCombobox", "Text", "Listbox"]
        target_types.remove(current_type)  # Don't copy to self
        
        for target_type in target_types:
            for prop_name, prop_value in source_settings.items():
                var_key = (target_type, prop_name)
                
                if var_key in self.text_input_vars:
                    self.text_input_vars[var_key].set(prop_value)
        
        self.apply_to_preview()
        self.app.messages(2, 9, f"Copied {current_type} settings to other text input widgets")

    def _apply_text_input_styles_to_preview(self, text_input_styles):
        """Apply text input styles to preview widgets - UPDATED FOR COMBOBOX POPDOWN"""
        try:
            preview_style = ttk.Style()
            
            # Apply styles to ttk widgets
            for widget_type, styles in text_input_styles.items():
                if widget_type in ["TEntry", "Modern.TEntry", "TCombobox"]:
                    temp_style_name = f"Preview.{widget_type}"
                    
                    # Configure the style
                    config_args = {}
                    state_maps = {}
                    
                    for prop, value in styles.items():
                        if prop in ["background", "foreground", "fieldbackground", 
                                   "arrowcolor", "bordercolor", "focuscolor"]:
                            config_args[prop] = value
                        elif prop == "font_family" and "font_size" in styles:
                            font_size = styles.get("font_size", "9")
                            config_args["font"] = (value, int(font_size))
                        elif prop == "font_size" and "font_family" in styles:
                            # Font is handled with font_family
                            continue
                        elif prop == "padding_x" and "padding_y" in styles:
                            padding_y = styles.get("padding_y", "2")
                            config_args["padding"] = (int(value), int(padding_y))
                        elif prop == "padding_y" and "padding_x" in styles:
                            # Padding is handled with padding_x
                            continue
                        # Handle state colors for maps
                        elif prop == "focus_bordercolor":
                            if 'bordercolor' not in state_maps:
                                state_maps['bordercolor'] = []
                            state_maps['bordercolor'].append(('focus', value))
                        elif prop == "focus_fieldbackground":
                            if 'fieldbackground' not in state_maps:
                                state_maps['fieldbackground'] = []
                            state_maps['fieldbackground'].append(('focus', value))
                        elif prop == "hover_bordercolor":
                            if 'bordercolor' not in state_maps:
                                state_maps['bordercolor'] = []
                            state_maps['bordercolor'].append(('hover', value))
                    
                    # Special handling for combobox to show selection colors
                    if widget_type == "TCombobox":
                        if 'selectbackground' not in config_args:
                            config_args['selectbackground'] = self.current_styles.get('secondary_color', '#3498db')
                        if 'selectforeground' not in config_args:
                            config_args['selectforeground'] = self.current_styles.get('text_light', '#ffffff')
                    
                    # Apply configuration
                    if config_args:
                        preview_style.configure(temp_style_name, **config_args)
                    
                    # Apply state maps
                    if state_maps:
                        preview_style.map(temp_style_name, **state_maps)
                    
                    # Update the corresponding preview widget
                    if widget_type in ["TEntry", "Modern.TEntry"] and hasattr(self, 'preview_entry'):
                        self.preview_entry.configure(style=temp_style_name)
                    elif widget_type == "TCombobox" and hasattr(self, 'preview_combo'):
                        self.preview_combo.configure(style=temp_style_name)
                        
        except Exception as e:
            print(f"DEBUG: Error applying text input styles to preview: {e}")

    def _update_tkinter_widgets_preview(self, style_settings, text_input_styles):
        """Update tkinter widgets (Text, Listbox) in preview"""
        try:
            # Update Text widget preview
            if hasattr(self, 'log_preview'):
                text_styles = text_input_styles.get('Text', {})
                self.log_preview.config(state=tk.NORMAL)
                self.log_preview.configure(
                    background=text_styles.get('background', 'white'),
                    foreground=text_styles.get('foreground', style_settings.get('text_dark', '#000000')),
                    font=(
                        text_styles.get('font_family', style_settings['font_family']),
                        int(text_styles.get('font_size', style_settings['font_size']))
                    ),
                    insertbackground=text_styles.get('insertbackground', style_settings.get('text_dark', '#000000')),
                    selectbackground=text_styles.get('selectbackground', style_settings['secondary_color']),
                    selectforeground=text_styles.get('selectforeground', style_settings['text_light']),
                    padx=int(text_styles.get('padding_x', 5)),
                    pady=int(text_styles.get('padding_y', 5)),
                    relief=text_styles.get('relief', 'solid'),
                    borderwidth=int(text_styles.get('borderwidth', 1))
                )
                self.log_preview.config(state=tk.DISABLED)
            
            # Update Listbox preview
            if hasattr(self, 'preview_listbox'):
                listbox_styles = text_input_styles.get('Listbox', {})
                self.preview_listbox.configure(
                    background=listbox_styles.get('background', 'white'),
                    foreground=listbox_styles.get('foreground', style_settings.get('text_dark', '#000000')),
                    font=(
                        listbox_styles.get('font_family', style_settings['font_family']),
                        int(listbox_styles.get('font_size', style_settings['font_size']))
                    ),
                    selectbackground=listbox_styles.get('selectbackground', style_settings['secondary_color']),
                    selectforeground=listbox_styles.get('selectforeground', style_settings['text_light']),
                    relief=listbox_styles.get('relief', 'solid'),
                    borderwidth=int(listbox_styles.get('borderwidth', 1))
                )
                
        except Exception as e:
            print(f"DEBUG: Error updating tkinter widgets preview: {e}")

    def initialize_text_input_vars(self):
        """Properly initialize the text input variables dictionary"""
        if not hasattr(self, 'text_input_vars'):
            self.text_input_vars = {}
        
        # Initialize variables for all text widget types and properties
        widget_types = ["TEntry", "Modern.TEntry", "TCombobox", "Text", "Listbox"]
        
        for widget_type in widget_types:
            default_styles = self.get_current_text_widget_styles(widget_type)
            for prop_name, prop_value in default_styles.items():
                var_key = (widget_type, prop_name)
                
                # Only create if it doesn't exist
                if var_key not in self.text_input_vars:
                    self.text_input_vars[var_key] = tk.StringVar(value=prop_value)

    def debug_text_input_state(self):
        """Debug method to show current text input state"""
        print("=== TEXT INPUT STATE DEBUG ===")
        print(f"Has text_input_vars: {hasattr(self, 'text_input_vars')}")
        if hasattr(self, 'text_input_vars'):
            print(f"Number of text input vars: {len(self.text_input_vars)}")
            for key, var in list(self.text_input_vars.items())[:10]:  # Show first 10
                print(f"  {key}: {var.get()}")
        
        current_settings = self.collect_all_settings()
        text_input_settings = current_settings.get('text_input_styles', {})
        print(f"Text input settings count: {len(text_input_settings)}")
        
        for widget_type, styles in text_input_settings.items():
            print(f"  {widget_type}: {len(styles)} properties")

    # ==================== TREEVIEW METHODS ====================

    def setup_treeview_grid_tab(self):
        """Setup the Treeview and Data Grid styling tab"""
        # Create the new tab
        self._create_scrollable_frame(self.treeview_tab)

        # File management section
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="Treeview Style Files", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_subframe = ttk.Frame(file_frame)
        file_subframe.pack(fill=tk.X)
        
        ttk.Label(file_subframe, text="Style Files:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.treeview_file_var = tk.StringVar()
        self.treeview_file_combo = ttk.Combobox(
            file_subframe, 
            textvariable=self.treeview_file_var,
            state="readonly",
            width=20
        )
        self.treeview_file_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.treeview_file_combo.bind('<<ComboboxSelected>>', self.on_treeview_file_selected)
        
        file_btn_frame = ttk.Frame(file_subframe)
        file_btn_frame.pack(side=tk.LEFT)
        
        ttk.Button(file_btn_frame, text="Load", 
                  command=self.load_current_treeview_file, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Save As", 
                  command=self.save_treeview_style_as, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Delete", 
                  command=self.delete_current_treeview_file, width=8).pack(side=tk.LEFT)
        
        # Component selection
        component_frame = ttk.LabelFrame(self.scrollable_frame, text="Component Selection", padding="5")
        component_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(component_frame, text="Select Component:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.treeview_component_var = tk.StringVar(value="Treeview")
        self.treeview_component_combo = ttk.Combobox(
            component_frame, 
            textvariable=self.treeview_component_var,
            values=["Treeview", "Treeview.Heading", "Treeview.Item", "Treeview.Cell"],
            state="readonly",
            width=20
        )
        self.treeview_component_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.treeview_component_combo.bind('<<ComboboxSelected>>', self.on_treeview_component_selected)
        
        # Style controls frame - will be populated dynamically
        self.treeview_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Style Controls", padding="5")
        self.treeview_controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Quick actions frame
        quick_actions_frame = ttk.LabelFrame(self.scrollable_frame, text="Quick Actions", padding="5")
        quick_actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        action_subframe = ttk.Frame(quick_actions_frame)
        action_subframe.pack(fill=tk.X)
        
        ttk.Button(action_subframe, text="Reset All to Defaults", 
                  command=self.reset_all_treeview_styles, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Copy to Other Components", 
                  command=self.copy_treeview_styles, width=18).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Apply to Theme", 
                  command=self.apply_treeview_styles_to_theme, width=15).pack(side=tk.LEFT)
        
        # Initialize with default component
        self.setup_treeview_component_controls("Treeview")
        self.update_treeview_file_combo()

    def setup_treeview_style_management(self):
        """Setup treeview style file management system"""
        # Use application directory
        if hasattr(self.app, 'app_dir'):
            self.treeview_styles_dir = os.path.join(self.app.app_dir, "treeview_styles")
        elif hasattr(self.app, 'config_manager') and hasattr(self.app.config_manager, 'config_dir'):
            self.treeview_styles_dir = os.path.join(self.app.config_manager.config_dir, "treeview_styles")
        else:
            self.treeview_styles_dir = os.path.join(os.getcwd(), "config", "treeview_styles")
        
        # Create directory if it doesn't exist
        if not os.path.exists(self.treeview_styles_dir):
            os.makedirs(self.treeview_styles_dir)
            print(f"DEBUG: Created treeview styles directory: {self.treeview_styles_dir}")
        
        # Load available treeview style files
        self.load_treeview_style_files()
        print(f"DEBUG: Treeview styles directory: {self.treeview_styles_dir}")
    
    def load_treeview_style_files(self):
        """Load all available treeview style files"""
        self.treeview_style_files = {}
        
        if not os.path.exists(self.treeview_styles_dir):
            return
        
        for filename in os.listdir(self.treeview_styles_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.treeview_styles_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        style_data = json.load(f)
                        style_name = filename[:-5]  # Remove .json extension
                        self.treeview_style_files[style_name] = style_data
                except Exception as e:
                    print(f"DEBUG: Error loading treeview style file {filename}: {e}")
    
    def update_treeview_file_combo(self):
        """Update the treeview file combo with available files"""
        file_names = list(self.treeview_style_files.keys())
        self.treeview_file_combo['values'] = file_names
        if file_names:
            self.treeview_file_combo.set(file_names[0])

    def setup_treeview_component_controls(self, component):
        """Setup controls for the selected treeview component"""
        # Clear existing controls
        for widget in self.treeview_controls_frame.winfo_children():
            widget.destroy()
        
        # Get current styles for this component
        current_styles = self.get_current_treeview_styles(component)
        
        # Initialize the dictionary if it doesn't exist
        if not hasattr(self, 'treeview_vars'):
            self.treeview_vars = {}
        
        # Define properties for each component
        component_properties = {
            "Treeview": [
                ("background", "Background"),
                ("foreground", "Text Color"),
                ("fieldbackground", "Field Background"),
                ("font_family", "Font Family"),
                ("font_size", "Font Size"),
                ("rowheight", "Row Height"),
                ("borderwidth", "Border Width"),
                ("relief", "Border Style"),
                ("padding_x", "Padding X"),
                ("padding_y", "Padding Y")
            ],
            "Treeview.Heading": [
                ("background", "Background"),
                ("foreground", "Text Color"),
                ("font_family", "Font Family"),
                ("font_size", "Font Size"),
                ("padding_x", "Padding X"),
                ("padding_y", "Padding Y"),
                ("relief", "Border Style"),
                ("borderwidth", "Border Width")
            ],
            "Treeview.Item": [
                ("even_color", "Even Row Color"),
                ("odd_color", "Odd Row Color"),
                ("hover_color", "Hover Color"),
                ("selected_color", "Selected Background"),
                ("selected_text", "Selected Text Color")
            ],
            "Treeview.Cell": [
                ("focus_color", "Focus Color"),
                ("disabled_color", "Disabled Color"),
                ("readonly_color", "Readonly Background")
            ]
        }
        
        # Create controls for the selected component
        if component in component_properties:
            for prop_key, prop_label in component_properties[component]:
                prop_frame = ttk.Frame(self.treeview_controls_frame)
                prop_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(prop_frame, text=prop_label, width=20).pack(side=tk.LEFT)
                
                # Create StringVar and store in dictionary
                var_key = (component, prop_key)
                current_value = current_styles.get(prop_key, "")
                
                if var_key not in self.treeview_vars:
                    self.treeview_vars[var_key] = tk.StringVar(value=current_value)
                
                # Special handling for different property types
                if prop_key in ["font_family"]:
                    font_combo = ttk.Combobox(prop_frame, textvariable=self.treeview_vars[var_key],
                                            values=["Arial", "Helvetica", "Times New Roman", "IBM Plex Mono Text", "IBM Plex Mono Medium", "Courier New", 
                                                   "Verdana", "Tahoma", "Segoe UI", "System"])
                    font_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                elif prop_key in ["font_size", "rowheight", "borderwidth"]:
                    size_combo = ttk.Combobox(prop_frame, textvariable=self.treeview_vars[var_key],
                                            values=["8", "9", "10", "11", "12", "14", "16", "18", "20", "24"])
                    size_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                elif prop_key == "relief":
                    relief_combo = ttk.Combobox(prop_frame, textvariable=self.treeview_vars[var_key],
                                              values=["flat", "raised", "sunken", "solid", "ridge", "groove"])
                    relief_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                else:
                    entry = ttk.Entry(prop_frame, textvariable=self.treeview_vars[var_key], width=15)
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                    
                    # Add color picker for color properties
                    if any(color_term in prop_key for color_term in ["color", "background", "foreground"]):
                        ttk.Button(prop_frame, text="Choose", 
                                  command=lambda c=component, p=prop_key, var=self.treeview_vars[var_key]: 
                                  self.choose_treeview_color(c, p, var),
                                  width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Add trace to auto-update preview
        for var_key, var in self.treeview_vars.items():
            if var_key[0] == component:  # Only trace variables for current component
                var.trace('w', self.schedule_preview_update)

    def get_current_treeview_styles(self, component):
        """Get current styles for a treeview component"""
        # Default styles based on component
        default_styles = {
            "Treeview": {
                "background": "#ffffff",
                "foreground": "#000000",
                "fieldbackground": "#ffffff",
                "font_family": "Arial",
                "font_size": "9",
                "rowheight": "25",
                "borderwidth": "1",
                "relief": "solid",
                "padding_x": "5",
                "padding_y": "2"
            },
            "Treeview.Heading": {
                "background": "#2c3e50",
                "foreground": "#ffffff",
                "font_family": "Arial",
                "font_size": "9",
                "padding_x": "5",
                "padding_y": "2",
                "relief": "raised",
                "borderwidth": "1"
            },
            "Treeview.Item": {
                "even_color": "#f8f9fa",
                "odd_color": "#ffffff",
                "hover_color": "#e3f2fd",
                "selected_color": "#3498db",
                "selected_text": "#ffffff"
            },
            "Treeview.Cell": {
                "focus_color": "#2980b9",
                "disabled_color": "#f5f5f5",
                "readonly_color": "#f9f9f9"
            }
        }
        
        # Try to get actual current styles
        try:
            style = ttk.Style()
            actual_styles = default_styles[component].copy()
            
            # Try to get actual configured styles
            try:
                bg = style.lookup(component, "background")
                if bg:
                    actual_styles["background"] = bg
            except:
                pass
                
            try:
                fg = style.lookup(component, "foreground")
                if fg:
                    actual_styles["foreground"] = fg
            except:
                pass
                
            try:
                field_bg = style.lookup(component, "fieldbackground")
                if field_bg:
                    actual_styles["fieldbackground"] = field_bg
            except:
                pass
                
            try:
                font = style.lookup(component, "font")
                if font:
                    # Parse font tuple
                    if isinstance(font, tuple):
                        actual_styles["font_family"] = font[0]
                        actual_styles["font_size"] = str(font[1])
            except:
                pass
            
            return actual_styles
        except:
            return default_styles.get(component, default_styles["Treeview"])
    
    def choose_treeview_color(self, component, property_key, color_var):
        """Color chooser for treeview properties"""
        try:
            current_color = color_var.get()
            
            color = askcolor(
                title=f"Choose {component} {property_key}",
                initialcolor=current_color
            )
            
            if color[1]:  # color[1] is the hex code
                color_var.set(color[1])
                
        except Exception as e:
            print(f"DEBUG: Error in choose_treeview_color: {e}")
            self.app.messages(2, 3, f"Error choosing color: {e}")
    
    def on_treeview_component_selected(self, event=None):
        """Handle treeview component selection change"""
        selected_component = self.treeview_component_var.get()
        self.setup_treeview_component_controls(selected_component)
        self.app.messages(2, 9, f"Now editing: {selected_component}")

    def on_treeview_file_selected(self, event=None):
        """Handle treeview file selection"""
        file_name = self.treeview_file_var.get()
        if file_name:
            self.load_treeview_style_file(file_name)
    
    def load_current_treeview_file(self):
        """Load the currently selected treeview file"""
        file_name = self.treeview_file_var.get()
        if file_name:
            self.load_treeview_style_file(file_name)
    
    def save_treeview_style_as(self):
        """Save current treeview styles with a new name"""
        style_name = tk.simpledialog.askstring("Save Treeview Styles", "Enter style name:")
        if style_name:
            if self.save_treeview_style_file(style_name):
                self.update_treeview_file_combo()
                self.treeview_file_var.set(style_name)
    
    def delete_current_treeview_file(self):
        """Delete the currently selected treeview file"""
        file_name = self.treeview_file_var.get()
        if file_name:
            if messagebox.askyesno("Delete Treeview Styles", f"Delete treeview style '{file_name}'?"):
                if self.delete_treeview_style_file(file_name):
                    self.update_treeview_file_combo()
    
    def save_treeview_style_file(self, style_name):
        """Save current treeview styles to a file"""
        try:
            treeview_settings = self.collect_treeview_settings()
            if not treeview_settings:
                self.app.messages(2, 3, "No treeview styles to save")
                return False
            
            filename = f"{style_name}.json"
            filepath = os.path.join(self.treeview_styles_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(treeview_settings, f, indent=2)
            
            # Reload the files
            self.load_treeview_style_files()
            self.app.messages(2, 9, f"Treeview styles saved: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error saving treeview styles: {e}")
            return False
    
    def load_treeview_style_file(self, style_name):
        """Load treeview styles from a file"""
        try:
            if style_name not in self.treeview_style_files:
                self.app.messages(2, 3, f"Treeview style file not found: {style_name}")
                return False
            
            treeview_settings = self.treeview_style_files[style_name]
            self.apply_treeview_style_settings(treeview_settings)
            self.app.messages(2, 9, f"Treeview styles loaded: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error loading treeview styles: {e}")
            return False
    
    def delete_treeview_style_file(self, style_name):
        """Delete a treeview style file"""
        try:
            filename = f"{style_name}.json"
            filepath = os.path.join(self.treeview_styles_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                # Reload the files
                self.load_treeview_style_files()
                self.app.messages(2, 9, f"Treeview styles deleted: {style_name}")
                return True
            else:
                self.app.messages(2, 3, f"Treeview style file not found: {style_name}")
                return False
                
        except Exception as e:
            self.app.messages(2, 3, f"Error deleting treeview styles: {e}")
            return False

    def collect_treeview_settings(self):
        """Collect all treeview settings"""
        treeview_settings = {}
        
        if not hasattr(self, 'treeview_vars') or not self.treeview_vars:
            print("DEBUG: No treeview_vars dictionary found or empty")
            return treeview_settings
        
        components = ["Treeview", "Treeview.Heading", "Treeview.Item", "Treeview.Cell"]
        
        for component in components:
            component_settings = {}
            has_settings = False
            
            # Get all properties for this component
            for var_key, var in self.treeview_vars.items():
                if var_key[0] == component:
                    property_name = var_key[1]
                    value = var.get().strip()
                    
                    # Only include if we have a non-empty value
                    if value:
                        component_settings[property_name] = value
                        has_settings = True
                        print(f"DEBUG: Collected {component}.{property_name}: {value}")
            
            if has_settings:
                treeview_settings[component] = component_settings
        
        print(f"DEBUG: Collected {len(treeview_settings)} treeview component styles")
        return treeview_settings
    
    def apply_treeview_style_settings(self, treeview_settings):
        """Apply treeview style settings to the UI controls"""
        try:
            # Initialize treeview_vars if it doesn't exist
            if not hasattr(self, 'treeview_vars'):
                self.treeview_vars = {}
            
            # Apply settings to all components
            for component, properties in treeview_settings.items():
                for prop_name, prop_value in properties.items():
                    var_key = (component, prop_name)
                    
                    # Create or update the variables
                    if var_key not in self.treeview_vars:
                        self.treeview_vars[var_key] = tk.StringVar(value=prop_value)
                    else:
                        self.treeview_vars[var_key].set(prop_value)
            
            # Update the current component controls if they're visible
            current_component = self.treeview_component_var.get()
            self.setup_treeview_component_controls(current_component)
            
            # Update preview
            self.apply_to_preview()
            
        except Exception as e:
            print(f"DEBUG: Error applying treeview style settings: {e}")
    
    def reset_all_treeview_styles(self):
        """Reset all treeview styles to defaults"""
        if messagebox.askyesno("Reset Treeview Styles", "Reset all treeview styles to defaults?"):
            try:
                # Clear all treeview variables
                if hasattr(self, 'treeview_vars'):
                    self.treeview_vars.clear()
                
                # Reset current controls
                current_component = self.treeview_component_var.get()
                self.setup_treeview_component_controls(current_component)
                
                # Update preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "All treeview styles reset to defaults")
                
            except Exception as e:
                self.app.messages(2, 3, f"Error resetting treeview styles: {e}")
    
    def apply_treeview_styles_to_theme(self):
        """Apply current treeview styles to the main theme"""
        try:
            treeview_settings = self.collect_treeview_settings()
            if treeview_settings:
                # Update the current styles with treeview settings
                self.current_styles['treeview_styles'] = treeview_settings
                
                # Apply to preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "Treeview styles applied to current theme")
            else:
                self.app.messages(2, 3, "No treeview styles to apply")
                
        except Exception as e:
            self.app.messages(2, 3, f"Error applying treeview styles: {e}")
    
    def copy_treeview_styles(self):
        """Copy current treeview style settings to other components"""
        current_component = self.treeview_component_var.get()
        if not hasattr(self, 'treeview_vars'):
            return
            
        # Get current component settings
        source_settings = {}
        for var_key, var in self.treeview_vars.items():
            if var_key[0] == current_component:
                source_settings[var_key[1]] = var.get()
        
        # Copy to other components (only meaningful for similar components)
        target_components = ["Treeview", "Treeview.Heading"]
        if current_component in target_components:
            target_components.remove(current_component)
            
            for target_component in target_components:
                for prop_name, prop_value in source_settings.items():
                    # Only copy properties that make sense for the target
                    if prop_name in ["font_family", "font_size", "padding_x", "padding_y"]:
                        var_key = (target_component, prop_name)
                        
                        if var_key in self.treeview_vars:
                            self.treeview_vars[var_key].set(prop_value)
        
        self.apply_to_preview()
        self.app.messages(2, 9, f"Copied {current_component} settings to other components")

    def _apply_treeview_styles_to_preview(self, treeview_styles):
        """Apply treeview styles to preview treeview"""
        try:
            preview_style = ttk.Style()
            
            # Apply styles to treeview components
            for component, styles in treeview_styles.items():
                temp_style_name = f"Preview.{component}"
                
                # Configure the style
                config_args = {}
                for prop, value in styles.items():
                    if prop in ["background", "foreground", "fieldbackground"]:
                        config_args[prop] = value
                    elif prop == "font_family" and "font_size" in styles:
                        font_size = styles.get("font_size", "9")
                        config_args["font"] = (value, int(font_size))
                    elif prop == "font_size" and "font_family" in styles:
                        # Font is handled with font_family
                        continue
                    elif prop in ["rowheight", "borderwidth"]:
                        try:
                            config_args[prop] = int(value)
                        except:
                            config_args[prop] = value
                    elif prop == "relief":
                        config_args[prop] = value
                
                # Apply configuration
                if config_args:
                    preview_style.configure(temp_style_name, **config_args)
                
                # Update the preview treeview
                if component == "Treeview" and hasattr(self, 'preview_treeview'):
                    self.preview_treeview.configure(style=temp_style_name)
                    
        except Exception as e:
            print(f"DEBUG: Error applying treeview styles to preview: {e}")

    def setup_review_tab(self):
        """Setup the review tab to see all styles together"""
        # Create the new tab
        # Create scrollable frame for button tab
        self._create_scrollable_frame(self.review_tab)
        
        
        # Title
        title_label = ttk.Label(self.scrollable_frame, text="Style Configuration Summary", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Current Settings Summary
        summary_frame = ttk.LabelFrame(self.scrollable_frame, text="Current Style Settings", padding="10")
        summary_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create summary text widget
        self.summary_text = scrolledtext.ScrolledText(summary_frame, height=15, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Update summary button
        ttk.Button(summary_frame, text="Refresh Summary", 
                  command=self.update_summary).pack(pady=(10, 0))
        
        # Style Validation
        validation_frame = ttk.LabelFrame(self.scrollable_frame, text="Style Validation", padding="10")
        validation_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.validation_text = scrolledtext.ScrolledText(validation_frame, height=8, wrap=tk.WORD)
        self.validation_text.pack(fill=tk.BOTH, expand=True)
        
        # Validation buttons
        validation_btn_frame = ttk.Frame(validation_frame)
        validation_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(validation_btn_frame, text="Validate Styles", 
                  command=self.validate_styles).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(validation_btn_frame, text="Export Summary", 
                  command=self.export_summary).pack(side=tk.LEFT)
        
        # Initial update
        self.update_summary()

    def update_summary(self):
        """Update the style summary"""
        try:
            # Collect all current settings
            all_settings = self.collect_all_settings()
            
            # Format the summary
            summary = "=== STYLE CONFIGURATION SUMMARY ===\n\n"
            
            # Basic theme settings
            summary += "BASIC THEME SETTINGS:\n"
            summary += f"  Primary Color: {all_settings.get('primary_color', 'Not set')}\n"
            summary += f"  Secondary Color: {all_settings.get('secondary_color', 'Not set')}\n"
            summary += f"  Background: {all_settings.get('light_bg', 'Not set')} / {all_settings.get('dark_bg', 'Not set')}\n"
            summary += f"  Font: {all_settings.get('font_family', 'Not set')} {all_settings.get('font_size', 'Not set')}\n"
            summary += f"  Theme: {all_settings.get('theme', 'Not set')}\n\n"
            
            # Button styles summary
            button_styles = all_settings.get('button_styles', {})
            summary += f"BUTTON STYLES: {len(button_styles)} configured\n"
            for style_name in button_styles:
                summary += f"  {style_name}: {len(button_styles[style_name])} states\n"
            summary += "\n"
            
            # Text input styles summary
            text_styles = all_settings.get('text_input_styles', {})
            summary += f"TEXT INPUT STYLES: {len(text_styles)} configured\n"
            for widget_type in text_styles:
                summary += f"  {widget_type}: {len(text_styles[widget_type])} properties\n"
            summary += "\n"
            
            # Treeview styles summary
            treeview_styles = all_settings.get('treeview_styles', {})
            summary += f"TREEVIEW STYLES: {len(treeview_styles)} configured\n"
            for component in treeview_styles:
                summary += f"  {component}: {len(treeview_styles[component])} properties\n"
            summary += "\n"
            
            # File info
            summary += "STYLE FILES:\n"
            summary += f"  Button styles: {len(self.button_style_files)} files\n"
            summary += f"  Text input styles: {len(self.text_input_style_files)} files\n"
            summary += f"  Treeview styles: {len(self.treeview_style_files)} files\n"
            summary += f"  Presets: {len(self.style_presets)} presets\n"
            
            # Update the text widget
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(1.0, summary)
            self.summary_text.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"DEBUG: Error updating summary: {e}")
    
    def validate_styles(self):
        """Validate current style settings"""
        try:
            all_settings = self.collect_all_settings()
            validation_results = []
            
            # Basic validation
            validation_results.append("=== STYLE VALIDATION ===\n")
            
            # Check required colors
            required_colors = ['primary_color', 'secondary_color', 'light_bg', 'dark_bg']
            for color in required_colors:
                if color in all_settings and all_settings[color]:
                    validation_results.append(f"✓ {color}: {all_settings[color]}")
                else:
                    validation_results.append(f"✗ {color}: MISSING")
            
            validation_results.append("")
            
            # Check font settings
            if all_settings.get('font_family') and all_settings.get('font_size'):
                validation_results.append(f"✓ Font: {all_settings['font_family']} {all_settings['font_size']}")
            else:
                validation_results.append("✗ Font: INCOMPLETE")
            
            validation_results.append("")
            
            # Check style consistency
            button_styles = all_settings.get('button_styles', {})
            if button_styles:
                validation_results.append(f"✓ Button styles: {len(button_styles)} configured")
            else:
                validation_results.append("⚠ Button styles: None configured")
            
            text_styles = all_settings.get('text_input_styles', {})
            if text_styles:
                validation_results.append(f"✓ Text input styles: {len(text_styles)} configured")
            else:
                validation_results.append("⚠ Text input styles: None configured")
            
            treeview_styles = all_settings.get('treeview_styles', {})
            if treeview_styles:
                validation_results.append(f"✓ Treeview styles: {len(treeview_styles)} configured")
            else:
                validation_results.append("⚠ Treeview styles: None configured")
            
            validation_results.append("\n=== VALIDATION COMPLETE ===")
            
            # Update validation text
            validation_text = "\n".join(validation_results)
            self.validation_text.delete(1.0, tk.END)
            self.validation_text.insert(1.0, validation_text)
            self.validation_text.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"DEBUG: Error validating styles: {e}")
    
    def export_summary(self):
        """Export style summary to file"""
        try:
            # Get export filename
            filename = filedialog.asksaveasfilename(
                title="Export Style Summary",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                # Get current summary
                summary = self.summary_text.get(1.0, tk.END)
                validation = self.validation_text.get(1.0, tk.END)
                
                with open(filename, 'w') as f:
                    f.write("ETail Style Configuration Export\n")
                    f.write("=" * 40 + "\n\n")
                    f.write(summary)
                    f.write("\n" + "=" * 40 + "\n\n")
                    f.write(validation)
                
                self.app.messages(2, 9, f"Style summary exported to: {filename}")
                
        except Exception as e:
            self.app.messages(2, 3, f"Error exporting summary: {e}")

    # ==================== WINDOW METHODS ====================

    def setup_window_decorations_tab(self):
        """Setup the window decorations styling tab"""
        # Create the new tab
        self._create_scrollable_frame(self.window_tab)
        
        # File management section
        file_frame = ttk.LabelFrame(self.scrollable_frame, text="Window Style Files", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_subframe = ttk.Frame(file_frame)
        file_subframe.pack(fill=tk.X)
        
        ttk.Label(file_subframe, text="Style Files:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.window_file_var = tk.StringVar()
        self.window_file_combo = ttk.Combobox(
            file_subframe, 
            textvariable=self.window_file_var,
            state="readonly",
            width=20
        )
        self.window_file_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.window_file_combo.bind('<<ComboboxSelected>>', self.on_window_file_selected)
        
        file_btn_frame = ttk.Frame(file_subframe)
        file_btn_frame.pack(side=tk.LEFT)
        
        ttk.Button(file_btn_frame, text="Load", 
                  command=self.load_current_window_file, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Save As", 
                  command=self.save_window_style_as, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(file_btn_frame, text="Delete", 
                  command=self.delete_current_window_file, width=8).pack(side=tk.LEFT)
        
        # Window component selection
        component_frame = ttk.LabelFrame(self.scrollable_frame, text="Window Components", padding="5")
        component_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(component_frame, text="Select Component:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.window_component_var = tk.StringVar(value="TitleBar")
        self.window_component_combo = ttk.Combobox(
            component_frame, 
            textvariable=self.window_component_var,
            values=["TitleBar", "WindowButtons", "WindowBorder", "WindowBackground"],
            state="readonly",
            width=20
        )
        self.window_component_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.window_component_combo.bind('<<ComboboxSelected>>', self.on_window_component_selected)
        
        # Style controls frame - will be populated dynamically
        self.window_controls_frame = ttk.LabelFrame(self.scrollable_frame, text="Style Controls", padding="5")
        self.window_controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Quick actions frame
        quick_actions_frame = ttk.LabelFrame(self.scrollable_frame, text="Quick Actions", padding="5")
        quick_actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        action_subframe = ttk.Frame(quick_actions_frame)
        action_subframe.pack(fill=tk.X)
        
        ttk.Button(action_subframe, text="Reset All to Defaults", 
                  command=self.reset_all_window_styles, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Copy to Other Windows", 
                  command=self.copy_window_styles, width=18).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_subframe, text="Apply to Theme", 
                  command=self.apply_window_styles_to_theme, width=15).pack(side=tk.LEFT)
        
        # Platform-specific warning
        platform_frame = ttk.Frame(self.scrollable_frame)
        platform_frame.pack(fill=tk.X, pady=(10, 0))
        
        warning_text = "Note: Window decorations are applied to new windows. Some features may be platform-dependent."
        warning_label = ttk.Label(platform_frame, text=warning_text, 
                                font=("Arial", 8), foreground="orange")
        warning_label.pack(anchor=tk.W)
        
        # Initialize with default component
        self.setup_window_component_controls("TitleBar")
        self.update_window_file_combo()

    def setup_window_style_management(self):
        """Setup window style file management system"""
        # Use application directory
        if hasattr(self.app, 'app_dir'):
            self.window_styles_dir = os.path.join(self.app.app_dir, "window_styles")
        elif hasattr(self.app, 'config_manager') and hasattr(self.app.config_manager, 'config_dir'):
            self.window_styles_dir = os.path.join(self.app.config_manager.config_dir, "window_styles")
        else:
            self.window_styles_dir = os.path.join(os.getcwd(), "config", "window_styles")
        
        # Create directory if it doesn't exist
        if not os.path.exists(self.window_styles_dir):
            os.makedirs(self.window_styles_dir)
            print(f"DEBUG: Created window styles directory: {self.window_styles_dir}")
        
        # Load available window style files
        self.load_window_style_files()
        print(f"DEBUG: Window styles directory: {self.window_styles_dir}")
    
    def load_window_style_files(self):
        """Load all available window style files"""
        self.window_style_files = {}
        
        if not os.path.exists(self.window_styles_dir):
            return
        
        for filename in os.listdir(self.window_styles_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.window_styles_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        style_data = json.load(f)
                        style_name = filename[:-5]  # Remove .json extension
                        self.window_style_files[style_name] = style_data
                except Exception as e:
                    print(f"DEBUG: Error loading window style file {filename}: {e}")
    
    def update_window_file_combo(self):
        """Update the window file combo with available files"""
        file_names = list(self.window_style_files.keys())
        self.window_file_combo['values'] = file_names
        if file_names:
            self.window_file_combo.set(file_names[0])

    def setup_window_component_controls(self, component):
        """Setup controls for the selected window component"""
        # Clear existing controls
        for widget in self.window_controls_frame.winfo_children():
            widget.destroy()
        
        # Get current styles for this component
        current_styles = self.get_current_window_styles(component)
        
        # Initialize the dictionary if it doesn't exist
        if not hasattr(self, 'window_vars'):
            self.window_vars = {}
        
        # Define properties for each component
        component_properties = {
            "TitleBar": [
                ("background", "Background Color"),
                ("foreground", "Text Color"),
                ("font_family", "Font Family"),
                ("font_size", "Font Size"),
                ("height", "Height"),
                ("active_background", "Active Background"),
                ("inactive_background", "Inactive Background"),
                ("gradient_start", "Gradient Start"),
                ("gradient_end", "Gradient End")
            ],
            "WindowButtons": [
                ("close_color", "Close Button Color"),
                ("close_hover", "Close Hover Color"),
                ("maximize_color", "Maximize Button Color"),
                ("maximize_hover", "Maximize Hover Color"),
                ("minimize_color", "Minimize Button Color"),
                ("minimize_hover", "Minimize Hover Color"),
                ("button_size", "Button Size"),
                ("button_spacing", "Button Spacing"),
                ("symbol_color", "Symbol Color"),
                ("symbol_size", "Symbol Size")
            ],
            "WindowBorder": [
                ("border_color", "Border Color"),
                ("border_width", "Border Width"),
                ("active_border", "Active Border Color"),
                ("inactive_border", "Inactive Border Color"),
                ("border_radius", "Border Radius"),
                ("resize_handle_color", "Resize Handle Color"),
                ("resize_handle_size", "Resize Handle Size")
            ],
            "WindowBackground": [
                ("background", "Background Color"),
                ("gradient_start", "Gradient Start"),
                ("gradient_end", "Gradient End"),
                ("pattern", "Background Pattern"),
                ("opacity", "Window Opacity"),
                ("shadow_color", "Shadow Color"),
                ("shadow_blur", "Shadow Blur")
            ]
        }
        
        # Create controls for the selected component
        if component in component_properties:
            for prop_key, prop_label in component_properties[component]:
                prop_frame = ttk.Frame(self.window_controls_frame)
                prop_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(prop_frame, text=prop_label, width=20).pack(side=tk.LEFT)
                
                # Create StringVar and store in dictionary
                var_key = (component, prop_key)
                current_value = current_styles.get(prop_key, "")
                
                if var_key not in self.window_vars:
                    self.window_vars[var_key] = tk.StringVar(value=current_value)
                
                # Special handling for different property types
                if prop_key in ["font_family"]:
                    font_combo = ttk.Combobox(prop_frame, textvariable=self.window_vars[var_key],
                                            values=["Arial", "Helvetica", "Times New Roman", "IBM Plex Mono Text", "IBM Plex Mono Medium", "Courier New", 
                                                   "Verdana", "Tahoma", "Segoe UI", "System"])
                    font_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                elif prop_key in ["font_size", "height", "button_size", "border_width", "border_radius", 
                                "resize_handle_size", "shadow_blur"]:
                    size_combo = ttk.Combobox(prop_frame, textvariable=self.window_vars[var_key],
                                            values=["1", "2", "3", "4", "5", "6", "8", "10", "12", "14", "16"])
                    size_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                elif prop_key == "pattern":
                    pattern_combo = ttk.Combobox(prop_frame, textvariable=self.window_vars[var_key],
                                               values=["solid", "gradient", "diagonal", "grid", "dots", "none"])
                    pattern_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                elif prop_key == "opacity":
                    opacity_scale = ttk.Scale(prop_frame, from_=0.1, to=1.0, 
                                            variable=self.window_vars[var_key], orient=tk.HORIZONTAL)
                    opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                    # Show current value
                    value_label = ttk.Label(prop_frame, textvariable=self.window_vars[var_key], width=5)
                    value_label.pack(side=tk.LEFT, padx=(5, 0))
                else:
                    entry = ttk.Entry(prop_frame, textvariable=self.window_vars[var_key], width=15)
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
                    
                    # Add color picker for color properties
                    if any(color_term in prop_key for color_term in ["color", "background", "foreground"]):
                        ttk.Button(prop_frame, text="Choose", 
                                  command=lambda c=component, p=prop_key, var=self.window_vars[var_key]: 
                                  self.choose_window_color(c, p, var),
                                  width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # Add trace to auto-update preview
        for var_key, var in self.window_vars.items():
            if var_key[0] == component:  # Only trace variables for current component
                var.trace('w', self.schedule_preview_update)

    def get_current_window_styles(self, component):
        """Get current styles for a window component"""
        # Default styles based on component
        default_styles = {
            "TitleBar": {
                "background": "#2c3e50",
                "foreground": "#ffffff",
                "font_family": "Arial",
                "font_size": "9",
                "height": "25",
                "active_background": "#2c3e50",
                "inactive_background": "#95a5a6",
                "gradient_start": "#2c3e50",
                "gradient_end": "#34495e"
            },
            "WindowButtons": {
                "close_color": "#e74c3c",
                "close_hover": "#c0392b",
                "maximize_color": "#f39c12",
                "maximize_hover": "#e67e22",
                "minimize_color": "#3498db",
                "minimize_hover": "#2980b9",
                "button_size": "12",
                "button_spacing": "2",
                "symbol_color": "#ffffff",
                "symbol_size": "8"
            },
            "WindowBorder": {
                "border_color": "#34495e",
                "border_width": "1",
                "active_border": "#3498db",
                "inactive_border": "#bdc3c7",
                "border_radius": "0",
                "resize_handle_color": "#3498db",
                "resize_handle_size": "4"
            },
            "WindowBackground": {
                "background": "#ecf0f1",
                "gradient_start": "#ecf0f1",
                "gradient_end": "#bdc3c7",
                "pattern": "solid",
                "opacity": "1.0",
                "shadow_color": "#000000",
                "shadow_blur": "10"
            }
        }
        
        return default_styles.get(component, default_styles["TitleBar"])
    
    def choose_window_color(self, component, property_key, color_var):
        """Color chooser for window properties"""
        try:
            current_color = color_var.get()
            
            color = askcolor(
                title=f"Choose {component} {property_key}",
                initialcolor=current_color
            )
            
            if color[1]:  # color[1] is the hex code
                color_var.set(color[1])
                
        except Exception as e:
            print(f"DEBUG: Error in choose_window_color: {e}")
            self.app.messages(2, 3, f"Error choosing color: {e}")
    
    def on_window_component_selected(self, event=None):
        """Handle window component selection change"""
        selected_component = self.window_component_var.get()
        self.setup_window_component_controls(selected_component)
        self.app.messages(2, 9, f"Now editing: {selected_component}")

    def on_window_file_selected(self, event=None):
        """Handle window file selection"""
        file_name = self.window_file_var.get()
        if file_name:
            self.load_window_style_file(file_name)
    
    def load_current_window_file(self):
        """Load the currently selected window file"""
        file_name = self.window_file_var.get()
        if file_name:
            self.load_window_style_file(file_name)
    
    def save_window_style_as(self):
        """Save current window styles with a new name"""
        style_name = tk.simpledialog.askstring("Save Window Styles", "Enter style name:")
        if style_name:
            if self.save_window_style_file(style_name):
                self.update_window_file_combo()
                self.window_file_var.set(style_name)
    
    def delete_current_window_file(self):
        """Delete the currently selected window file"""
        file_name = self.window_file_var.get()
        if file_name:
            if messagebox.askyesno("Delete Window Styles", f"Delete window style '{file_name}'?"):
                if self.delete_window_style_file(file_name):
                    self.update_window_file_combo()
    
    def save_window_style_file(self, style_name):
        """Save current window styles to a file"""
        try:
            window_settings = self.collect_window_settings()
            if not window_settings:
                self.app.messages(2, 3, "No window styles to save")
                return False
            
            filename = f"{style_name}.json"
            filepath = os.path.join(self.window_styles_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(window_settings, f, indent=2)
            
            # Reload the files
            self.load_window_style_files()
            self.app.messages(2, 9, f"Window styles saved: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error saving window styles: {e}")
            return False
    
    def load_window_style_file(self, style_name):
        """Load window styles from a file"""
        try:
            if style_name not in self.window_style_files:
                self.app.messages(2, 3, f"Window style file not found: {style_name}")
                return False
            
            window_settings = self.window_style_files[style_name]
            self.apply_window_style_settings(window_settings)
            self.app.messages(2, 9, f"Window styles loaded: {style_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error loading window styles: {e}")
            return False
    
    def delete_window_style_file(self, style_name):
        """Delete a window style file"""
        try:
            filename = f"{style_name}.json"
            filepath = os.path.join(self.window_styles_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                # Reload the files
                self.load_window_style_files()
                self.app.messages(2, 9, f"Window styles deleted: {style_name}")
                return True
            else:
                self.app.messages(2, 3, f"Window style file not found: {style_name}")
                return False
                
        except Exception as e:
            self.app.messages(2, 3, f"Error deleting window styles: {e}")
            return False

    def collect_window_settings(self):
        """Collect all window settings"""
        window_settings = {}
        
        if not hasattr(self, 'window_vars') or not self.window_vars:
            print("DEBUG: No window_vars dictionary found or empty")
            return window_settings
        
        components = ["TitleBar", "WindowButtons", "WindowBorder", "WindowBackground"]
        
        for component in components:
            component_settings = {}
            has_settings = False
            
            # Get all properties for this component
            for var_key, var in self.window_vars.items():
                if var_key[0] == component:
                    property_name = var_key[1]
                    value = var.get().strip()
                    
                    # Only include if we have a non-empty value
                    if value:
                        component_settings[property_name] = value
                        has_settings = True
                        print(f"DEBUG: Collected {component}.{property_name}: {value}")
            
            if has_settings:
                window_settings[component] = component_settings
        
        print(f"DEBUG: Collected {len(window_settings)} window component styles")
        return window_settings
    
    def apply_window_style_settings(self, window_settings):
        """Apply window style settings to the UI controls"""
        try:
            # Initialize window_vars if it doesn't exist
            if not hasattr(self, 'window_vars'):
                self.window_vars = {}
            
            # Apply settings to all components
            for component, properties in window_settings.items():
                for prop_name, prop_value in properties.items():
                    var_key = (component, prop_name)
                    
                    # Create or update the variables
                    if var_key not in self.window_vars:
                        self.window_vars[var_key] = tk.StringVar(value=prop_value)
                    else:
                        self.window_vars[var_key].set(prop_value)
            
            # Update the current component controls if they're visible
            current_component = self.window_component_var.get()
            self.setup_window_component_controls(current_component)
            
            # Update preview
            self.apply_to_preview()
            
        except Exception as e:
            print(f"DEBUG: Error applying window style settings: {e}")
    
    def reset_all_window_styles(self):
        """Reset all window styles to defaults"""
        if messagebox.askyesno("Reset Window Styles", "Reset all window styles to defaults?"):
            try:
                # Clear all window variables
                if hasattr(self, 'window_vars'):
                    self.window_vars.clear()
                
                # Reset current controls
                current_component = self.window_component_var.get()
                self.setup_window_component_controls(current_component)
                
                # Update preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "All window styles reset to defaults")
                
            except Exception as e:
                self.app.messages(2, 3, f"Error resetting window styles: {e}")
    
    def apply_window_styles_to_theme(self):
        """Apply current window styles to the main theme"""
        try:
            window_settings = self.collect_window_settings()
            if window_settings:
                # Update the current styles with window settings
                self.current_styles['window_styles'] = window_settings
                
                # Apply to preview
                self.apply_to_preview()
                
                self.app.messages(2, 9, "Window styles applied to current theme")
            else:
                self.app.messages(2, 3, "No window styles to apply")
                
        except Exception as e:
            self.app.messages(2, 3, f"Error applying window styles: {e}")
    
    def copy_window_styles(self):
        """Copy current window style settings to other components"""
        current_component = self.window_component_var.get()
        if not hasattr(self, 'window_vars'):
            return
            
        # Get current component settings
        source_settings = {}
        for var_key, var in self.window_vars.items():
            if var_key[0] == current_component:
                source_settings[var_key[1]] = var.get()
        
        # Copy to other components where it makes sense
        if current_component == "TitleBar":
            target_components = ["WindowBackground"]
            for target_component in target_components:
                for prop_name, prop_value in source_settings.items():
                    if prop_name in ["background", "foreground", "font_family", "font_size"]:
                        var_key = (target_component, prop_name)
                        if var_key in self.window_vars:
                            self.window_vars[var_key].set(prop_value)
        
        self.apply_to_preview()
        self.app.messages(2, 9, f"Copied {current_component} settings to related components")

    def _apply_window_styles_to_preview(self, window_styles):
        """Apply window styles to preview window decorations - SIMPLIFIED VERSION"""
        try:
            # Extract styles for each component
            title_styles = window_styles.get('TitleBar', {})
            button_styles = window_styles.get('WindowButtons', {})
            border_styles = window_styles.get('WindowBorder', {})
            bg_styles = window_styles.get('WindowBackground', {})
            
            # Update all window preview widgets
            self.update_window_preview_widgets(title_styles, button_styles, border_styles, bg_styles)
            
            print("DEBUG: Successfully applied window styles to preview")
            
        except Exception as e:
            print(f"DEBUG: Error applying window styles to preview: {e}")
            import traceback
            traceback.print_exc()

    def update_window_preview_widgets(self, title_styles, button_styles, border_styles, bg_styles):
        """Update window preview widgets with new styles"""
        try:
            # Update title bar
            if hasattr(self, 'preview_titlebar'):
                bg_color = title_styles.get('background', '#2c3e50')
                fg_color = title_styles.get('foreground', '#ffffff')
                
                self.preview_titlebar.configure(background=bg_color)
                
                # Update all children frames in title bar
                for child in self.preview_titlebar.winfo_children():
                    if isinstance(child, tk.Frame):
                        child.configure(background=bg_color)
                        
                        # Update labels in the title content
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, tk.Label):
                                grandchild.configure(
                                    background=bg_color,
                                    foreground=fg_color
                                )
                            elif isinstance(grandchild, tk.Frame):
                                # Button frame
                                grandchild.configure(background=bg_color)
            
            # Update window buttons
            button_attrs = [
                ('preview_minimize_btn', button_styles.get('minimize_color', '#3498db')),
                ('preview_maximize_btn', button_styles.get('maximize_color', '#f39c12')),
                ('preview_close_btn', button_styles.get('close_color', '#e74c3c'))
            ]
            
            symbol_color = button_styles.get('symbol_color', '#ffffff')
            
            for btn_attr, bg_color in button_attrs:
                if hasattr(self, btn_attr):
                    btn = getattr(self, btn_attr)
                    btn.configure(
                        background=bg_color,
                        foreground=symbol_color
                    )
            
            # Update window border
            if hasattr(self, 'preview_titlebar'):
                parent = self.preview_titlebar.master
                if parent:
                    border_color = border_styles.get('border_color', '#34495e')
                    parent.configure(background=border_color)
            
            # Update content background
            if hasattr(self, 'preview_titlebar'):
                parent = self.preview_titlebar.master
                if parent:
                    for child in parent.winfo_children():
                        if child != self.preview_titlebar and isinstance(child, tk.Frame):
                            bg_color = bg_styles.get('background', '#ecf0f1')
                            child.configure(background=bg_color)
                            
                            # Update content label
                            for content_child in child.winfo_children():
                                if isinstance(content_child, tk.Label):
                                    content_child.configure(background=bg_color)
                            
        except Exception as e:
            print(f"DEBUG: Error updating window preview widgets: {e}")

    def collect_all_settings(self):
        """Collect all style settings from all tabs - UPDATED"""
        settings = {
            # Basic theme settings
            'primary_color': self.primary_color_var.get(),
            'secondary_color': self.secondary_color_var.get(),
            'success_color': self.success_color_var.get(),
            'warning_color': self.warning_color_var.get(),
            'danger_color': self.danger_color_var.get(),
            'disabled_color': self.disabled_color_var.get(),
            'light_bg': self.light_bg_var.get(),
            'dark_bg': self.dark_bg_var.get(),
            'text_primary': self.text_primary_var.get(),
            'text_light': self.text_light_var.get(),
            'text_dark': self.text_dark_var.get(),
            'font_family': self.font_family_var.get(),
            'font_size': self.font_size_var.get(),
            'theme': self.theme_var.get(),
        }
        
        # Include button tuning settings
        button_settings = self.collect_button_tuning_settings()
        if button_settings:
            settings['button_styles'] = button_settings
        
        # Include text input settings
        text_input_settings = self.collect_text_input_settings()
        settings['text_input_styles'] = text_input_settings
        
        # Include treeview settings
        treeview_settings = self.collect_treeview_settings()
        settings['treeview_styles'] = treeview_settings
        
        # Include window settings - MAKE SURE THIS IS INCLUDED
        window_settings = self.collect_window_settings()
        settings['window_styles'] = window_settings
        
        print(f"DEBUG: Collected settings - Window: {len(window_settings) if window_settings else 0} components")
        
        return settings

    def _create_scrollable_frame(self, parent):
        """Create a scrollable frame in the given parent and store it as self.scrollable_frame"""
        # Create container
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update the scrollable frame width when canvas is resized
        def configure_canvas(event):
            canvas.itemconfig("all", width=event.width)
        canvas.bind("<Configure>", configure_canvas)

# ****************************************************************************
# *************************** Plugin Manager ********************************
# ****************************************************************************

class PluginDependencyLoader:
    """
    Handles loading of compiled plugins and their dependencies
    for the main compiled executable
    """
    def __init__(self, app):
        self.app = app
        self.loaded_dependencies = set()
        
        # Use main app directory for dependencies (shared)
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
            
        # Dependencies are shared across instances
        self.plugin_base_path = base_dir / "plugins"

    def get_plugin_base_path(self) -> Path:
        """Get the base path for plugins based on executable location"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_dir = Path(sys.executable).parent
        else:
            # Running from script
            base_dir = Path(__file__).parent
        
        return base_dir / "plugins"

    def discover_compiled_plugins(self) -> Dict[str, Dict]:
        """Discover compiled plugins with platform information - REPLACES OLD METHOD"""
        plugins_info = {}
        
        if not self.plugin_base_path.exists():
            self.app.messages(2, 3, f"Plugin directory not found: {self.plugin_base_path}")
            return plugins_info
        
        pyd_files = list(self.plugin_base_path.glob("*.pyd"))
        
        print(f"DEBUG: Found {len(pyd_files)} .pyd files: {[f.name for f in pyd_files]}")
        
        for pyd_file in pyd_files:
            full_stem = pyd_file.stem
            parts = full_stem.split('.')
            base_name = parts[0]
            
            platform_info = "unknown"
            if len(parts) > 1:
                platform_info = parts[1]  # e.g., "cp313-win_amd64"
            
            plugins_info[base_name] = {
                'base_name': base_name,
                'full_stem': full_stem,
                'filename': pyd_file.name,
                'path': pyd_file,
                'platform': platform_info,
                'is_current_platform': self.is_compatible_platform(platform_info)
            }
            
            status = "✓" if plugins_info[base_name]['is_current_platform'] else "⚠"
            print(f"DEBUG: {status} {base_name} [{platform_info}]")
        
        self.app.messages(2, 9, f"Found {len(plugins_info)} compiled plugins")
        return plugins_info
    
    def is_compatible_platform(self, platform_str: str) -> bool:
        """Check if the plugin platform matches current environment"""
        # Basic compatibility check
        current_python = f"cp{sys.version_info.major}{sys.version_info.minor}"
        
        if platform_str == "unknown":
            return True  # Assume compatible if we don't know
        
        # Check if it's for current Python version
        if current_python in platform_str:
            return True
        
        # Check if it's platform-agnostic
        if platform_str in ["any", "none", ""]:
            return True
        
        return False

    def load_compiled_plugin(self, plugin_name: str) -> Optional[Any]:
        """Load a compiled plugin - USES PLATFORM INFO"""
        try:
            # Get plugin info to find the exact filename
            plugins_info = self.discover_compiled_plugins()
            
            if plugin_name not in plugins_info:
                self.app.messages(2, 3, f"Plugin not found: {plugin_name}")
                return None
            
            plugin_info = plugins_info[plugin_name]
            plugin_path = plugin_info['path']
            
            print(f"DEBUG: Loading compiled plugin: {plugin_name} from {plugin_info['filename']}")
            
            # Warn about platform compatibility
            if not plugin_info['is_current_platform']:
                self.app.messages(2, 3, 
                                 f"Plugin {plugin_name} may not be compatible. "
                                 f"Plugin: {plugin_info['platform']}, "
                                 f"Current: cp{sys.version_info.major}{sys.version_info.minor}")
            
            # Load dependencies
            if not self.load_plugin_dependencies(plugin_name):
                self.app.messages(2, 9, f"Note: No dependencies found for {plugin_name}")
            
            # Load the plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None:
                self.app.messages(2, 3, f"Failed to create spec for {plugin_name}")
                return None
            
            plugin_module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = plugin_module
            spec.loader.exec_module(plugin_module)
            
            # Find the plugin class
            plugin_class = self.find_plugin_class(plugin_module, plugin_name)
            if plugin_class:
                self.app.messages(2, 9, f"Successfully loaded compiled plugin: {plugin_name}")
                return plugin_class
            else:
                self.app.messages(2, 3, f"No valid plugin class found in {plugin_name}")
                return None
                
        except Exception as e:
            self.app.messages(2, 3, f"Error loading compiled plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def find_plugin_class(self, module, plugin_name: str) -> Optional[Any]:
        """Find the plugin class in a module using duck typing"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a class with the required methods
            if (isinstance(attr, type) and 
                hasattr(attr, 'setup') and 
                hasattr(attr, 'teardown') and
                callable(attr.setup) and 
                callable(attr.teardown) and
                attr.__module__ == module.__name__):
                
                # Create test instance to verify it has required attributes
                try:
                    test_instance = attr(self.app)
                    if (hasattr(test_instance, 'name') and 
                        hasattr(test_instance, 'version') and 
                        hasattr(test_instance, 'description')):
                        return attr
                except Exception as e:
                    self.app.messages(2, 3, f"Error testing plugin class {attr_name}: {e}")
                    continue
        
        return None
    
    def load_plugin_dependencies(self, plugin_name: str) -> bool:
        """Load dependencies for a specific plugin"""
        try:
            print(f"DEBUG: Loading dependencies for: {plugin_name}")
            
            # Look for dependencies directory
            deps_dir = self.plugin_base_path / "dependencies"
            if not deps_dir.exists():
                print(f"DEBUG: No dependencies directory found")
                return True  # No dependencies needed
            
            print(f"DEBUG: Using dependencies directory: {deps_dir}")
    
            # Add dependencies directory to Python path
            if str(deps_dir) not in sys.path:
                sys.path.insert(0, str(deps_dir))
                self.loaded_dependencies.add(str(deps_dir))
                print(f"DEBUG: ✓ Added main dependency path: {deps_dir}")
    
            # Load extracted packages
            extracted_dir = deps_dir / "extracted"
            if extracted_dir.exists():
                self.load_extracted_packages(extracted_dir)
    
            # Load direct packages
            direct_packages_dir = deps_dir / "direct_packages"
            if direct_packages_dir.exists():
                self.load_direct_packages(direct_packages_dir)
                
                # Special handling for PyAutoGUI
                if (direct_packages_dir / "pyautogui").exists():
                    print("DEBUG: PyAutoGUI found in direct_packages, applying fix...")
                    self.fix_pyautogui_import()
    
            return True
            
        except Exception as e:
            print(f"DEBUG: Error loading dependencies: {e}")
            return False

    def extract_and_load_wheel(self, wheel_path: Path):
        """Extract and load a wheel package"""
        try:
            # Create extraction directory
            extract_dir = wheel_path.parent / "extracted" / wheel_path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract wheel
            with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the actual package directory
            package_dir = self.find_package_directory(extract_dir)
            if package_dir and str(package_dir) not in sys.path:
                sys.path.insert(0, str(package_dir))
                self.loaded_dependencies.add(str(package_dir))
                self.app.messages(2, 9, f"Loaded wheel package: {wheel_path.name}")
            
        except Exception as e:
            self.app.messages(2, 3, f"Error extracting wheel {wheel_path}: {e}")
    
    def find_package_directory(self, extract_dir: Path) -> Optional[Path]:
        """Find the actual package directory in extracted wheel contents"""
        # Common wheel structures
        possible_paths = [
            extract_dir,
            extract_dir / "src",
            extract_dir / "lib",
        ]
        
        # Look for directories containing Python files
        for path in possible_paths:
            if path.exists():
                # Check for Python files or packages
                python_files = list(path.rglob("*.py"))
                python_packages = list(path.rglob("*/__init__.py"))
                
                if python_files or python_packages:
                    return path
        
        # If no clear structure, return the main extract directory
        return extract_dir
    
    def load_extracted_packages(self, extracted_dir: Path):
        """Load packages from extracted dependencies"""
        for package_dir in extracted_dir.iterdir():
            if package_dir.is_dir():
                if str(package_dir) not in sys.path:
                    sys.path.insert(0, str(package_dir))
                    self.loaded_dependencies.add(str(package_dir))
                    self.app.messages(2, 9, f"Loaded extracted package: {package_dir.name}")
    
    def debug_pyautogui_structure(self):
        """Quick debug of PyAutoGUI package structure"""
        deps_dir = self.plugin_base_path / "dependencies" / "direct_packages" / "pyautogui"
        
        if not deps_dir.exists():
            print(f"DEBUG: PyAutoGUI not found at: {deps_dir}")
            return
        
        print(f"DEBUG: PyAutoGUI package structure at: {deps_dir}")
        
        # List all files in the package
        for file_path in deps_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(deps_dir)
                print(f"DEBUG:   {rel_path}")
        
        # Check for critical files
        critical_files = [
            "__init__.py",
            "__main__.py", 
            "pyautogui.py",
        ]
        
        for file_name in critical_files:
            file_path = deps_dir / file_name
            if file_path.exists():
                print(f"DEBUG: ✓ Found critical file: {file_name}")
            else:
                print(f"DEBUG: ✗ Missing critical file: {file_name}")

    def fix_pyautogui_import(self) -> bool:
        """Fix PyAutoGUI import without importing it at module level"""
        try:
            print("DEBUG: === FIXING PYAUTOGUI PATH (LAZY) ===")
            
            # Path where PyAutoGUI should be
            pyautogui_path = self.plugin_base_path / "dependencies" / "direct_packages" / "pyautogui"
            
            if not pyautogui_path.exists():
                print(f"DEBUG: PyAutoGUI not found at: {pyautogui_path}")
                return False
            
            print(f"DEBUG: Found PyAutoGUI at: {pyautogui_path}")
            
            # Add to sys.path if not already there
            if str(pyautogui_path) not in sys.path:
                sys.path.insert(0, str(pyautogui_path))
                print(f"DEBUG: ✓ Added PyAutoGUI to sys.path: {pyautogui_path}")
            
            # DON'T test import here - that would bundle it!
            print("DEBUG: ✓ PyAutoGUI path setup complete (lazy import)")
            return True
                
        except Exception as e:
            print(f"DEBUG: Error in fix_pyautogui_import: {e}")
            return False

    def fix_pillow_import(self) -> bool:
        """Fix Pillow imports without importing at module level"""
        try:
            print("DEBUG: === FIXING PILLOW PATH (LAZY) ===")
            
            # Find the Pillow package
            pillow_paths = [
                self.plugin_base_path / "dependencies" / "extracted" / "pillow-12.0.0-cp313-cp313-win_amd64",
                self.plugin_base_path / "dependencies" / "extracted" / "Pillow-12.0.0-cp313-cp313-win_amd64",
            ]
            
            pillow_path = None
            for path in pillow_paths:
                if path.exists():
                    pillow_path = path
                    break
            
            if not pillow_path:
                print("DEBUG: ✗ Pillow package not found")
                return False
            
            print(f"DEBUG: Found Pillow at: {pillow_path}")
            
            # Add to sys.path if not already there
            if str(pillow_path) not in sys.path:
                sys.path.insert(0, str(pillow_path))
                print(f"DEBUG: ✓ Added Pillow to sys.path: {pillow_path}")
            
            print("DEBUG: ✓ Pillow path setup complete (lazy import)")
            return True
                
        except Exception as e:
            print(f"DEBUG: Error in fix_pillow_import: {e}")
            return False

    def load_direct_packages(self, direct_packages_dir: Path):
        """Load directly copied packages with better debugging"""
        if not direct_packages_dir.exists():
            return
        
        print(f"DEBUG: Loading direct packages from: {direct_packages_dir}")
        
        for package_dir in direct_packages_dir.iterdir():
            if package_dir.is_dir():
                package_name = package_dir.name
                print(f"DEBUG: Processing direct package: {package_name} at {package_dir}")
                
                # Check if the package structure is correct
                init_file = package_dir / "__init__.py"
                if init_file.exists():
                    print(f"DEBUG: ✓ Package {package_name} has __init__.py")
                else:
                    print(f"DEBUG: ⚠ Package {package_name} missing __init__.py")
                    # Look for Python files anyway
                    py_files = list(package_dir.glob("*.py"))
                    if py_files:
                        print(f"DEBUG:   But has {len(py_files)} Python files")
                
                if str(package_dir) not in sys.path:
                    sys.path.insert(0, str(package_dir))
                    self.loaded_dependencies.add(str(package_dir))
                    print(f"DEBUG: ✓ Added to sys.path: {package_dir}")
                else:
                    print(f"DEBUG: ⚠ Already in sys.path: {package_dir}")
        
        # Debug: Show current sys.path to verify
        print("DEBUG: Current sys.path for direct packages:")
        for i, path in enumerate(sys.path[:5]):  # Show first 5 paths
            print(f"DEBUG:   {i}: {path}")

    # REMOVE THESE METHODS - they cause PyInstaller to bundle dependencies
    def test_pyautogui_import(self):
        """REMOVE THIS - it imports pyautogui and bundles it"""
        # This method imports pyautogui, causing PyInstaller to include it
        pass

    def test_dependency_loading(self):
        """REMOVE THIS - it imports dependencies"""
        # This imports various dependencies
        pass

    def cleanup_dependencies(self):
        """Clean up loaded dependencies (optional)"""
        for dep_path in self.loaded_dependencies:
            if dep_path in sys.path:
                sys.path.remove(dep_path)
        self.loaded_dependencies.clear()

# Plugin Manager
class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins = {}
        self.loaded_plugins = {}
        
        # Use main app directory for plugin CODE (shared)
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
        
        # Plugin CODE directory (shared across all instances)
        self.plugins_dir = base_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Plugin CONFIG directory (instance-specific)
        if hasattr(app, 'instance_id'):
            self.plugin_config_dir = base_dir / "instances" / app.instance_id / "plugins"
        else:
            self.plugin_config_dir = base_dir / "plugins" / "config"
        
        self.plugin_config_dir.mkdir(parents=True, exist_ok=True)
        
        self.dependency_loader = PluginDependencyLoader(app)
        

    def discover_plugins(self):
        """Discover available plugins from SHARED plugins directory"""
        self.plugins.clear()
    
    
        if not self.plugins_dir.exists():
            print(f"DEBUG: Plugin directory doesn't exist: {self.plugins_dir}")
            return
    
        # Add SHARED plugins directory to Python path
        plugins_path = str(self.plugins_dir.absolute())
        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)
            print(f"DEBUG: Added to Python path: {plugins_path}")
    
        # Discover source plugins (.py files) from SHARED directory
        python_files = list(self.plugins_dir.glob("*.py"))
        source_plugins = [f for f in python_files 
                         if not f.name.startswith("_") and f.stem != "etail_plugin"]
        
        # Discover compiled plugins from SHARED directory
        compiled_plugins_info = self.dependency_loader.discover_compiled_plugins()
        compiled_plugins = list(compiled_plugins_info.keys())
        
        print(f"DEBUG: Found {len(source_plugins)} source plugins in shared directory")
        print(f"DEBUG: Found {len(compiled_plugins)} compiled plugins in shared directory")
        
        # Load source plugins (only if no compiled version exists)
        for file_path in source_plugins:
            plugin_name = file_path.stem
            if plugin_name not in compiled_plugins:
                self.load_source_plugin(plugin_name, file_path)
            else:
                print(f"DEBUG: Skipping source plugin {plugin_name} - compiled version available")
    
        # Load compiled plugins from SHARED directory
        for plugin_name in compiled_plugins:
            self.load_compiled_plugin(plugin_name)
    
        print(f"DEBUG: Total plugins loaded from shared directory: {len(self.plugins)}")

    def load_source_plugin(self, plugin_name: str, file_path: Path):
        """Load a source plugin from .py file"""
        try:

            # Use import_module for proper import resolution
            module = importlib.import_module(plugin_name)

            # Find plugin classes using duck typing
            found_class = False
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if this class looks like a plugin (has required methods)
                if (hasattr(obj, 'setup') and 
                    hasattr(obj, 'teardown') and 
                    callable(obj.setup) and 
                    callable(obj.teardown) and
                    obj.__module__ == module.__name__):

                    # Create a test instance to verify it has plugin attributes
                    try:
                        test_instance = obj(self.app)
                        if (hasattr(test_instance, 'name') and 
                            hasattr(test_instance, 'version') and 
                            hasattr(test_instance, 'description')):

                            self.plugins[plugin_name] = {
                                'class': obj,
                                'module': module,
                                'file': file_path,
                                'enabled': False,
                                'type': 'source'
                            }
                            found_class = True
                            break
                    except Exception as e:
                        print(f"DEBUG: Failed to instantiate {name}: {e}")
                        continue

            if not found_class:
                print(f"DEBUG: No valid plugin class found in {plugin_name}")

        except Exception as e:
            print(f"DEBUG: ERROR loading {plugin_name}: {e}")
            import traceback
            traceback.print_exc()

    def load_compiled_plugin(self, plugin_name: str):
        """Load a compiled plugin using the dependency loader"""
        print(f"DEBUG: TRY TO LOAD COMPILED")
        try:
            plugin_class = self.dependency_loader.load_compiled_plugin(plugin_name)
            if plugin_class:
                self.plugins[plugin_name] = {
                    'class': plugin_class,
                    'module': None,  # Compiled modules don't have source module
                    'file': self.plugins_dir / f"{plugin_name}.pyd",
                    'enabled': False,
                    'type': 'compiled'
                }
                print(f"DEBUG: SUCCESS - Loaded compiled plugin: {plugin_name}")
            else:
                print(f"DEBUG: Failed to load compiled plugin: {plugin_name}")

        except Exception as e:
            print(f"DEBUG: ERROR loading compiled plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()

    def load_plugin(self, plugin_filename):
        """Load and enable a plugin - supports both source and compiled"""
        if plugin_filename not in self.plugins:
            return False
    
        try:
            # Get plugin info
            plugin_info = self.plugins[plugin_filename]
            plugin_class = plugin_info['class']
    
            # Create instance and set up
            plugin_instance = plugin_class(self.app)
            plugin_instance.setup()
    
            # Update state - use the filename as the key in loaded_plugins
            self.loaded_plugins[plugin_filename] = plugin_instance
            self.plugins[plugin_filename]['enabled'] = True
            self.app.messages(2, 9, f"Plugin loaded: {plugin_filename}")
    
            return True
    
        except Exception as e:
            self.app.messages(2, 3, f"Error loading plugin {plugin_filename}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def unload_plugin(self, plugin_name):
        """Unload and disable a plugin"""
        if plugin_name not in self.loaded_plugins:
            return False
            
        try:
            plugin_instance = self.loaded_plugins[plugin_name]
            plugin_instance.teardown()
            del self.loaded_plugins[plugin_name]
            self.plugins[plugin_name]['enabled'] = False
            self.app.messages(2, 9, f"Plugin unloaded: {plugin_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error unloading plugin {plugin_name}: {e}")
            return False

    def call_plugin_method(self, method_name, *args, **kwargs):
        """Call a method on all loaded plugins"""
        print(f"DEBUG calling {method_name}")
        results = []
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                method = getattr(plugin, method_name, None)
                if method and callable(method):
                    result = method(*args, **kwargs)
                    results.append((plugin_name, result))
                    print(f"DEBUG calling {method_name} on {plugin_name}")
            except Exception as e:
                print(f"Error calling {method_name} on {plugin_name}: {e}")
        return results

    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Get information about a plugin"""
        if plugin_name in self.plugins:
            plugin_info = self.plugins[plugin_name]
            if plugin_info['enabled'] and plugin_name in self.loaded_plugins:
                instance = self.loaded_plugins[plugin_name]
                return {
                    'name': getattr(instance, 'name', 'Unknown'),
                    'version': getattr(instance, 'version', 'Unknown'),
                    'description': getattr(instance, 'description', 'No description'),
                    'type': plugin_info['type'],
                    'enabled': True
                }
            else:
                return {
                    'name': plugin_name,
                    'type': plugin_info['type'],
                    'enabled': False
                }
        return {}

# ****************************************************************************
# *************************** Collapsible frame******************************
# ****************************************************************************

class CollapsibleFrame(ttk.Frame):
    def __init__(self, parent, text="", *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        
        self.is_expanded = True
        self.text = text
        
        # Create header frame with better styling
        self.header_frame = ttk.Frame(self, relief="raised", borderwidth=1)
        self.header_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Toggle button with better styling
        self.toggle_btn = ttk.Button(
            self.header_frame, 
            text=f"▼ {text}",
            command=self.toggle,
            style="Accordion.TButton"
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Content frame
        self.content_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        if self.is_expanded:
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0), padx=2)
    
    def toggle(self):
        """Toggle the visibility of the content"""
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text=f"► {self.text}")
        else:
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0), padx=2)
            self.toggle_btn.config(text=f"▼ {self.text}")
        
        self.is_expanded = not self.is_expanded
    
    def get_content_frame(self):
        """Get the content frame to add widgets"""
        return self.content_frame


# ****************************************************************************
# *************************** Config******************************************
# ****************************************************************************

class ConfigManager:

    def __init__(self, config_file):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove last_config_tracker references
        self.config = self.load_default_config()
        self.load_config()
        
    def __getitem__(self, key):
        """Allow dictionary-style access: config_manager['log_file']"""
        return self.config.get(key)

    def __setitem__(self, key, value):
        """Allow dictionary-style assignment: config_manager['log_file'] = 'path'"""
        self.config[key] = value

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value

    def load_default_config(self):
        """Return default configuration values with proper paths"""
        # Determine app base directory for default paths
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
            
        return {
            "log_file": "",
            "initial_lines": 50,
            "refresh_interval": 100,
            "auto_load_config": True,
            "last_directory": str(Path.home()),
            "filters_file": "",  # Empty by default
            "advanced_filters_file": "",  # Empty by default
            "recent_filters": [],
            "recent_advanced_filters": [],
            "verbose": True
        }
    
    def load_config(self):
        """Load configuration from file with validation"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                # Validate and fix paths in loaded config
                loaded_config = self.validate_config_paths(loaded_config)
                    
                # Update default config with loaded values
                self.config.update(loaded_config)
                print(f"Configuration loaded successfully from {self.config_file}")
            else:
                print("No existing config file, using defaults")
                
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")

    def save_config(self, config_path=None):
        """Save current configuration to file"""
        try:
            # Use provided path or current config file
            save_path = Path(config_path) if config_path else self.config_file
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # Update current config file reference if we're saving to a new path
            if config_path:
                self.config_file = save_path
                
            print(f"Configuration saved to: {save_path}")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def update_recent_list(self, list_name, file_path, max_entries=5):
        if file_path and os.path.exists(file_path):
            if list_name not in self.config:
                self.config[list_name] = []
            
            # Remove if already exists
            if file_path in self.config[list_name]:
                self.config[list_name].remove(file_path)
            
            # Add to beginning
            self.config[list_name].insert(0, file_path)
            
            # Trim to max entries
            self.config[list_name] = self.config[list_name][:max_entries]

    def get_default_filters_path(self):
        """Get the path for the default filters file"""
        return self.config_file.parent / "default_filters.json"
    
    def should_auto_load_filters(self):
        """Check if we should auto-load filters based on config"""
        return self.get("auto_load_config", True)
    
    def set_auto_load_filters(self, value):
        """Set whether to auto-load filters on startup"""
        self.set("auto_load_filters", value)

    def validate_config_paths(self, config):
        """Validate and fix file paths in configuration"""
        # Fix filters file path if it's invalid
        if 'filters_file' in config and config['filters_file']:
            filters_path = Path(config['filters_file'])
            if not filters_path.is_file() or not filters_path.exists():
                print(f"Invalid filters file path: {config['filters_file']}, resetting to empty")
                config['filters_file'] = ""
        
        # Fix advanced filters file path if it's invalid        
        if 'advanced_filters_file' in config and config['advanced_filters_file']:
            adv_filters_path = Path(config['advanced_filters_file'])
            if not adv_filters_path.is_file() or not adv_filters_path.exists():
                print(f"Invalid advanced filters file path: {config['advanced_filters_file']}, resetting to empty")
                config['advanced_filters_file'] = ""
                
        return config

# ****************************************************************************
# *************************** Action Handler *********************************
# ****************************************************************************

def get_root_window(self):
    """Safe method to get the root window for dialogs and after() calls"""
    # Try different methods to get the root window
    if hasattr(self, 'master') and self.master:
        return self.master
    elif hasattr(self, '_root') and self._root:
        return self._root
    else:
        # Fallback to winfo_toplevel
        return self.winfo_toplevel()

class ActionHandler:
    def __init__(self, root):
        self.root = root
        self.tts_engine = None
        self.pygame_initialized = False
        self.init_tts()
        self.init_sound()
    
    def init_tts(self):
        """Initialize text-to-speech engine with better error handling"""
        try:
            self.tts_engine = pyttsx3.init()
            if self.tts_engine:
                # Set speech properties
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            else:
                print("TTS engine initialization returned None")
        except Exception as e:
            print(f"TTS initialization failed: {e}")
            self.tts_engine = None

    def get_available_voices(self):
        """Get available voices from pyttsx3 and return formatted list"""
        #"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\MSTTS_V110_enGB_SusanM" not listed
        try:
            if not self.tts_engine:
                print(f"Error init the engine:")
                self.init_tts()
            voices = self.tts_engine.getProperty('voices')
            if not voices:
                self.messages(2, 3, "No TTS voices available")

            voice_list = []
            for i, voice in enumerate(voices):
                # Extract voice name - format varies by platform
                try:
                    voice_name = voice.name
                except AttributeError:
                    voice_name = f"Voice {i+1}"

                voice_info = {
                    'id': voice.id,
                    'name': voice_name,
                    'index': i
                }
                voice_list.append(voice_info)     
            return voice_list
        except Exception as e:
            print(f"Error getting voices: {e}")
            return []

    def init_sound(self):
        """Initialize pygame mixer for sound playback"""
        try:
            pygame.mixer.init()
            self.pygame_initialized = True
        except Exception as e:
            print(f"Sound initialization failed: {e}")
            self.pygame_initialized = False
    
    def execute_action(self, action, modifier, line_content=""):
        """Execute the specified action with the modifier"""
        try:
            if action == "sound" and modifier:
                self.play_sound(modifier)
            elif action == "tts":
                self.speak_text(modifier[0],modifier[1])
            elif action == "skip":
                return True  # Signal to skip this line
            elif action == "notification" and modifier:
                self.show_notification(modifier)
            elif action == "dialog" and modifier:
                self.show_dialog(modifier)
            return False
        except Exception as e:
            print(f"Action execution error: {e}")
            return False
    
    def play_sound(self, sound_file):
        """Play a sound file in a separate thread"""
        def _play_sound():
            try:
                if self.pygame_initialized and os.path.exists(sound_file):
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()
                else:
                    print(f"Sound file not found or sound system not available: {sound_file}")
            except Exception as e:
                print(f"Error playing sound: {e}")
        
        sound_thread = threading.Thread(target=_play_sound, daemon=True)
        sound_thread.start()
    
    def speak_text(self, text, voice):
        """Speak text using TTS in a separate thread"""
        def _speak():
            try:
                if self.tts_engine:
                    self.tts_engine.startLoop(False)
                    if self.tts_engine._inLoop:
                        self.tts_engine.endLoop()
                    self.tts_engine.setProperty('voice', voice)
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS error: {e} filter: {text}")
        tts_thread = threading.Thread(target=_speak, daemon=True)
        tts_thread.start()
    
    def show_notification(self, message):
        """Show a system notification using plyer"""
        try:
            if HAS_SYSTEM_NOTIFICATIONS:
                notification.notify(
                    title="ETail Alert",
                    message=message,
                    timeout=10,  # seconds
                    app_name="ETail Log Monitor"
                )
            else:
                # Fallback to tkinter messagebox - ensure we have a root window
                root_window = self.root
                if hasattr(root_window, 'after'):
                    root_window.after(0, lambda: messagebox.showinfo("ETail Notification", message))
                else:
                    # If it's not a tkinter widget, try to get the root
                    if hasattr(root_window, 'get_root_window'):
                        root_window = root_window.get_root_window()
                        root_window.after(0, lambda: messagebox.showinfo("ETail Notification", message))
                    else:
                        # Last resort
                        messagebox.showinfo("ETail Notification", message)
        except Exception as e:
            print(f"Etail Says - System notification failed: {e}")
            # Fallback
            try:
                messagebox.showinfo("ETail Notification", message)
            except:
                pass
    
    def show_dialog(self, message):
        """Show a dialog window"""
        try:
            root_window = self.root
            if hasattr(root_window, 'after'):
                root_window.after(0, lambda: messagebox.showwarning("ETail Alert", message))
            else:
                messagebox.showwarning("ETail Alert", message)
        except Exception as e:
            print(f"Error showing dialog: {e}")

# ****************************************************************************
# *************************** SERVER *****************************************
# ****************************************************************************

class LogServer:
    def __init__(self, config_manager, instance_id: str):
        self.config_manager = config_manager
        self.instance_id = instance_id
        self.server_socket = None
        self.is_running = False
        self.connected_clients = {}
        
        # Server configuration
        self.port = int(self.config_manager.get("server_port", 21327))
        self.ssl_sw = None
        self.password_hash = self.config_manager.get("server_password_hash", "")
        self.server_log_file = Path(self.config_manager.get("server_log_file", "temp_mon.log"))
        self.ssl_certfile = Path(self.config_manager.get("ssl_certfile", "server.crt"))
        self.ssl_keyfile = Path(self.config_manager.get("ssl_keyfile", "server.key"))
        
        # Ensure instance directory exists
        self.instance_dir = Path(self.config_manager.config_file).parent
        self.server_log_file = self.instance_dir / self.server_log_file
        
        # Simple print-based status tracking
        self._print(f"LogServer initialized for instance {instance_id}")
        
    def _print(self, message: str):
        """Simple print-based status output"""
        print(f"[LogServer] {time.strftime('%H:%M:%S')} - {message}")
        
    def start_server(self):
        """Start the log server in a separate thread"""
        if self.is_running:
            self._print("Server is already running")
            return False
            
        try:
            # Check if SSL certificates exist
            ssl_enabled = self.ssl_certfile.exists() and self.ssl_keyfile.exists()
            
            # Create SSL context if certificates exist
            context = None
            if ssl_enabled:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=str(self.ssl_certfile), keyfile=str(self.ssl_keyfile))
                self._print("SSL/TLS enabled - using encrypted connections")
            else:
                self._print("SSL/TLS disabled - using plaintext connections")
            
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            
            if ssl_enabled and context:
                self.server_socket = context.wrap_socket(self.server_socket, server_side=True)
                self.ssl_enabled = True
                self.ssl_sw = " SSL"
            else:
                self.ssl_enabled = False
                self.ssl_sw = " NO Encryption"
            
            self.is_running = True
            server_thread = threading.Thread(target=self._server_loop, daemon=True)
            server_thread.start()
            
            self._print(f"Server started on port {self.port}")
            self._print(f"SSL: {'ENABLED' if self.ssl_enabled else 'DISABLED'}")
            return True
            
        except Exception as e:
            self._print(f"Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the log server"""
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        # Close all client connections
        for client_info in self.connected_clients.values():
            try:
                client_info['socket'].close()
            except:
                pass
        self.connected_clients.clear()
        self._print("Server stopped")
    
    def _server_loop(self):
        """Main server loop to accept client connections"""
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.is_running:  # Only log if we're supposed to be running
                    self._print(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle individual client connection"""
        client_id = f"{client_address[0]}:{client_address[1]}"
        self._print(f"Client connected: {client_id}")
        
        try:
            # Authenticate client
            if not self._authenticate_client(client_socket, client_address):
                self._print(f"Authentication failed for client {client_id}")
                client_socket.close()
                return
            
            self.connected_clients[client_id] = {
                'socket': client_socket,
                'address': client_address,
                'connected_at': time.time()
            }
            
            # Process log lines from client
            self._process_client_logs(client_socket, client_id)
            
        except Exception as e:
            self._print(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            try:
                client_socket.close()
            except:
                pass
            self._print(f"Client disconnected: {client_id}")
    
    def _authenticate_client(self, client_socket: socket.socket, client_address: tuple) -> bool:
        """Authenticate client using password"""
        try:
            # Receive authentication data
            auth_data = client_socket.recv(1024).decode('utf-8').strip()
            
            # Simple password authentication
            if self.password_hash and auth_data != self.password_hash:
                client_socket.send(b"AUTH_FAILED")
                return False
            
            client_socket.send(b"AUTH_SUCCESS")
            return True
            
        except Exception as e:
            self._print(f"Authentication error: {e}")
            return False
    
    def _process_client_logs(self, client_socket: socket.socket, client_id: str):
        """Process log lines from authenticated client"""
        try:
            while self.is_running:
                # Receive log line
                log_line = client_socket.recv(4096).decode('utf-8').strip()
                if not log_line:
                    break
                
                # Write to server log file
                self._write_log_line(log_line, client_id)
                
                # Send confirmation
                client_socket.send(log_line.encode('utf-8'))
                
        except Exception as e:
            self._print(f"Error processing logs from {client_id}: {e}")
    
    def _write_log_line(self, log_line: str, client_id: str):
        """Write log line to server log file with timestamp"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_line = f"[{timestamp}] [{client_id}] {log_line}\n"
            
            with open(self.server_log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_line)
                
        except Exception as e:
            self._print(f"Error writing log line: {e}")

    def generate_ssl_certificates(self):
        """Generate self-signed SSL certificates for testing"""
        try:
            # Try to import cryptography
            try:
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
                from datetime import datetime, timezone, timedelta
            except ImportError:
                self._print("cryptography module not available, SSL certificates not generated")
                return False
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"Log Monitor Server"),
            ])
            
            # Use timezone-aware datetime objects
            current_time = datetime.now(timezone.utc)
            
            certificate = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                current_time
            ).not_valid_after(
                current_time + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(u"localhost"),
                    x509.DNSName(u"127.0.0.1"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Write private key
            with open(self.ssl_keyfile, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                ))
            
            # Write certificate
            with open(self.ssl_certfile, "wb") as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
            self._print("SSL certificates generated successfully")
            return True
            
        except Exception as e:
            self._print(f"Error generating SSL certificates: {e}")
            return False
    
    def get_server_status(self) -> Dict:
        """Get server status information"""
        ssl_status = "Enabled" if hasattr(self, 'ssl_enabled') and self.ssl_enabled else "Disabled"
    
        return {
            'is_running': self.is_running,
            'port': self.port,
            'ssl_enabled': ssl_status,
            'connected_clients': len(self.connected_clients),
            'log_file': str(self.server_log_file),
            'clients': list(self.connected_clients.keys())
        }


class ServerConfigDialog(tk.Toplevel):
    def __init__(self, parent, config_manager, instance_id):
        super().__init__(parent)
        self.config_manager = config_manager
        self.instance_id = instance_id
        self.result = None
        
        self.title("Log Server Configuration")
        self.geometry("500x400")
        self.resizable(False, False)
        
        self.create_widgets()
        self.load_configuration()
        
    def create_widgets(self):
        """Create configuration dialog widgets"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Port configuration
        ttk.Label(main_frame, text="Server Port:").grid(row=0, column=0, sticky="w", pady=5)
        self.port_var = tk.StringVar()
        self.port_entry = ttk.Entry(main_frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=1, sticky="w", pady=5)
        ttk.Label(main_frame, text="(Default: 21327)").grid(row=0, column=2, sticky="w", pady=5)
        
        # Password configuration
        ttk.Label(main_frame, text="Password:").grid(row=1, column=0, sticky="w", pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(main_frame, textvariable=self.password_var, show="*", width=20)
        self.password_entry.grid(row=1, column=1, sticky="w", pady=5)
        ttk.Label(main_frame, text="(Leave empty for no authentication)").grid(row=1, column=2, sticky="w", pady=5)
        
        # Log file configuration
        ttk.Label(main_frame, text="Server Log File:").grid(row=2, column=0, sticky="w", pady=5)
        self.log_file_var = tk.StringVar()
        self.log_file_entry = ttk.Entry(main_frame, textvariable=self.log_file_var, width=40)
        self.log_file_entry.grid(row=2, column=1, columnspan=2, sticky="we", pady=5)
        
        ttk.Button(main_frame, text="Browse", command=self.browse_log_file).grid(row=2, column=3, pady=5)
        
        # SSL certificate section
        ssl_frame = ttk.LabelFrame(main_frame, text="SSL/TLS Configuration", padding="5")
        ssl_frame.grid(row=3, column=0, columnspan=4, sticky="we", pady=10)
        
        ttk.Button(ssl_frame, text="Generate SSL Certificates", 
                  command=self.generate_ssl_certificates).pack(pady=5)
        
        ttk.Label(ssl_frame, text="SSL certificates will be generated in the instance directory").pack()
        
        # Test server section
        test_frame = ttk.LabelFrame(main_frame, text="Test Server", padding="5")
        test_frame.grid(row=4, column=0, columnspan=4, sticky="we", pady=10)
        
        ttk.Button(test_frame, text="Start Test Server", 
                  command=self.test_server).pack(side=tk.LEFT, padx=(0, 5))
        
        self.test_status_label = ttk.Label(test_frame, text="Not running")
        self.test_status_label.pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=4, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        
    def load_configuration(self):
        """Load current server configuration"""
        self.port_var.set(self.config_manager.get("server_port", 21327))
        
        # Don't load password for security
        self.log_file_var.set(self.config_manager.get("server_log_file", "temp_mon.log"))
        
        # Initialize server log file
        self.initialize_server_log()
    
    def initialize_server_log(self):
        """Initialize the server log file with a test entry"""
        log_file_path = Path(self.config_manager.config_file).parent / self.log_file_var.get()
        
        try:
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            test_entry = f"[{timestamp}] [SERVER] Server log initialized for instance: {self.instance_id}\n"
            
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(test_entry)
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not initialize server log file: {e}")
    
    def browse_log_file(self):
        """Browse for server log file location"""
        initial_dir = Path(self.config_manager.config_file).parent
        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            title="Select Server Log File",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        
        if filename:
            self.log_file_var.set(str(Path(filename)))
            
            self.initialize_server_log()
    
            self.config_manager.set("last_directory", str(Path(filename).parent))
            
            # SYNC STATE: Update config immediately when file is selected
            self.config_manager.set("log_file", str(Path(filename)))
    
    def generate_ssl_certificates(self):
        """Generate SSL certificates for the server"""
        try:
            # Create a temporary server instance to generate certificates
            temp_server = LogServer(self.config_manager, self.instance_id)
            if temp_server.generate_ssl_certificates():
                messagebox.showinfo("Success", "SSL certificates generated successfully")
            else:
                messagebox.showwarning("Warning", "Could not generate SSL certificates")
        except Exception as e:
            messagebox.showerror("Error", f"Error generating SSL certificates: {e}")
    
    def test_server(self):
        """Start a test server instance"""
        try:
            if not hasattr(self, 'test_server'):
                self.test_server = LogServer(self.config_manager, self.instance_id)
                # Update with current dialog values
                self.test_server.port = int(self.port_var.get())
                self.test_server.password_hash = self._hash_password(self.password_var.get())
                self.test_server.server_log_file = Path(self.log_file_var.get())
            
            if self.test_server.start_server():
                self.test_status_label.config(text=f"Running on port {self.test_server.port}")
            else:
                self.test_status_label.config(text="Failed to start")
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not start test server: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password for storage (simple SHA256 for now)"""
        if not password:
            return ""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def save_configuration(self):
        """Save server configuration"""
        try:
            # Validate port
            port = int(self.port_var.get())
            if not (1024 <= port <= 65535):
                raise ValueError("Port must be between 1024 and 65535")
            
            # Save configuration
            self.config_manager.set("server_port", port)
            self.config_manager.set("server_password_hash", self._hash_password(self.password_var.get()))
            self.config_manager.set("server_log_file", self.log_file_var.get())
            
            self.config_manager.save_config()
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid configuration: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save configuration: {e}")


# ****************************************************************************
# *************************** Inits*******************************************
# ****************************************************************************

class LogTailApp(ttk.Frame):
    """
    Refactored version that works as a Frame for browser integration
    Maintains all original functionality but can be embedded in tabs
    """
    def __init__(self, parent, instance_id=None, config_file=None, browser_reference=None):
        super().__init__(parent)

        # Initialize StyleManager - FIX: Use parent (which is the frame)
        self.style_manager = StyleManager(parent)  # This should work since parent exists
        
        # Copy style attributes for backward compatibility
        self._copy_style_attributes()
        
        # Instance identification for browser
        self.instance_id = instance_id or f"instance_{id(self)}"
        self.browser = browser_reference

        # Add these font attributes
        self.font_family = 'Arial'
        self.font_size = 9
        self.text_primary = "#2c3e50"
        self.text_light = "#ffffff" 
        self.text_dark = "#000000"

        # Use app directory for instance configuration
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
        
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Default to instance directory within app directory
            instances_dir = base_dir / "instances"
            instances_dir.mkdir(exist_ok=True)
            self.config_file = instances_dir / f"{self.instance_id}.json"
        
        # Initialize core components
        self.config_manager = ConfigManager(str(self.config_file))
        self.action_handler = ActionHandler(parent)        

        # Control variables
        self.stop_event = Event()
        self.tail_thread = None
        self.last_position = 0  # Track file position
        self.filters = {}

        # Regex builder components
        self.regex_fields = []  # Store field widgets
        self.regex_operators = []  # Store operator widgets between fields
        self.max_fields = 10
               
        # Filter editing state
        self.editing_filter_key = None  # Track which filter we're editing
        self.original_filter_key = None  # Store original key in case pattern changes

        self.advanced_filters = {}
        self.editing_advanced_filter_key = None

        # Predefined regex patterns
        self.predefined_patterns = {
            "Date (YYYY-MM-DD)": r"\d{4}-\d{2}-\d{2}",
            "Date (MM/DD/YYYY)": r"\d{2}/\d{2}/\d{4}",
            "Time (HH:MM:SS)": r"\d{2}:\d{2}:\d{2}",
            "IPv4 Address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "IPv6 Address": r"\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b",
            "Email Address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "Phone Number": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "URL": r"https?://[^\s]+",
            "Hex Color": r"#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b",
            "MAC Address": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})",
            "Credit Card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            "UUID": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            "Log Level": r"\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\b",
            "Number": r"\b\d+\b",
            "Word": r"\b\w+\b"
        }

        # Initialize UI and components
        self.detect_encoding = self.simple_encoding_detect
        self.setup_styling()
        self.create_widgets()
        self.messages(2, 2, f"Instance {self.instance_id} initialized")
        
        # Auto-load if enabled
        if self.config_manager.get("auto_load_config", True):
            self.load_configuration()
            # Load instance identity
            self.load_instance_identity()
            # Auto-load simple filters
            self.auto_load_filters()
        self.after(200, self.load_style_settings)

        # Initialize plugin manager AFTER everything else is set up
        self.plugin_manager = None
        self.plugin_filters = {}  # plugin_name -> list of filters
        self.plugin_filter_callbacks = {}  # plugin_name -> callback function
        self.after(100, self.initialize_plugin_system)  # Delay plugin init

    def apply_window_styling(self):
        """Apply window styling to this window"""
        try:
            if hasattr(self, 'style_manager') and hasattr(self.style_manager, 'window_styles'):
                self.style_manager._apply_window_styling(self.root)
        except Exception as e:
            print(f"DEBUG: Error applying window styling: {e}")
    # ========== BROWSER INTEGRATION METHODS ==========

    @property
    def root(self):
        """Backward compatibility property for plugins that expect self.root"""
        return self.get_root_window()

    def get_root(self):
        """Safe method to get the root window"""
        return self.master if hasattr(self, 'master') else self

    def get_root_window(self):
        """Safe method to get the root window for dialogs"""
        # Try different methods to get the root window
        if hasattr(self, 'master') and self.master:
            return self.master
        elif hasattr(self, '_root') and self._root:
            return self._root
        else:
            # Fallback to winfo_toplevel
            return self.winfo_toplevel()

    def get_instance_info(self):
        """Return information about this instance for the browser"""
        return {
            'instance_id': self.instance_id,
            'config_file': str(self.config_file),
            'status': getattr(self, 'status_var', tk.StringVar()).get(),
            'log_file': self.config_manager.get("log_file", ""),
            'filters_count': len(self.filters),
            'advanced_filters_count': len(self.advanced_filters),
            'plugins_loaded': len(self.plugin_manager.loaded_plugins) if self.plugin_manager else 0
        }

    def share_data_with_browser(self, data_type, data):
        """Share data with the browser and other instances"""
        if self.browser and hasattr(self.browser, 'receive_instance_data'):
            self.browser.receive_instance_data(self.instance_id, data_type, data)

    def receive_shared_data(self, from_instance_id, data_type, data):
        """Receive shared data from browser/other instances"""
        if data_type == "filter":
            self.import_filter_data(data)
        elif data_type == "performance_tweak":
            self.apply_performance_tweak(data)

    def import_filter_data(self, filter_data):
        """Import filter data from another instance"""
        try:
            if 'simple_filters' in filter_data:
                for filter_key, filter_info in filter_data['simple_filters'].items():
                    if filter_key not in self.filters:
                        self.filters[filter_key] = filter_info
                        self.refresh_filter_listbox()
            
            if 'advanced_filters' in filter_data:
                for filter_key, filter_info in filter_data['advanced_filters'].items():
                    if filter_key not in self.advanced_filters:
                        self.advanced_filters[filter_key] = filter_info
                        self.refresh_advanced_filters_listbox()
            
            self.messages(2, 9, f"Imported filters from {filter_data.get('source_instance', 'another instance')}")
            
        except Exception as e:
            self.messages(2, 3, f"Error importing filters: {e}")

    def apply_performance_tweak(self, tweak_data):
        """Apply performance tweaks from browser"""
        try:
            if 'refresh_interval' in tweak_data:
                new_interval = tweak_data['refresh_interval']
                self.config_manager.set("refresh_interval", new_interval)
                if hasattr(self, 'refresh_interval_var'):
                    self.refresh_interval_var.set(str(new_interval))
                
            if 'initial_lines' in tweak_data:
                new_lines = tweak_data['initial_lines']
                self.config_manager.set("initial_lines", new_lines)
                if hasattr(self, 'initial_lines_var'):
                    self.initial_lines_var.set(str(new_lines))
                
            self.messages(2, 9, "Performance tweaks applied")
            
        except Exception as e:
            self.messages(2, 3, f"Error applying performance tweaks: {e}")

    def export_configuration(self):
        """Export current configuration for sharing or backup - CAPTURES RUNTIME STATE"""
        # FIRST: Update the config manager with current UI state
        self.save_configuration()  # This ensures all current settings are saved
        
        # NOW: Export the current state including runtime data
        config_data = {
            'instance_id': self.instance_id,
            'timestamp': time.time(),
            'config': dict(self.config_manager.config),  # This now has current values
            
            # Include current UI state that might not be in config yet
            'runtime_state': {
                'current_log_file': self.log_file_var.get(),
                'verbose': self.verbose_var.get(),
                'filters_loaded': len(self.filters) > 0,
                'advanced_filters_loaded': len(self.advanced_filters) > 0,
                'tail_running': self.tail_thread and self.tail_thread.is_alive() if hasattr(self, 'tail_thread') else False
            },
            
            'simple_filters': self.filters,
            'advanced_filters': self.advanced_filters,
            'plugin_states': self.get_plugin_states()
        }
        return config_data

    def import_configuration(self, config_data):
        """Import configuration from another instance or backup"""
        try:
            if 'config' in config_data:
                self.config_manager.config.update(config_data['config'])
                self.load_configuration()
            
            if 'simple_filters' in config_data:
                self.filters = config_data['simple_filters'].copy()
                self.refresh_filter_listbox()
            
            if 'advanced_filters' in config_data:
                self.advanced_filters = config_data['advanced_filters'].copy()
                self.refresh_advanced_filters_listbox()
            
            self.messages(2, 9, "Configuration imported successfully")
            
        except Exception as e:
            self.messages(2, 3, f"Error importing configuration: {e}")

    def get_plugin_states(self):
        """Get current plugin states for export"""
        if not self.plugin_manager:
            return {}
        
        plugin_states = {}
        for plugin_name, plugin_info in self.plugin_manager.plugins.items():
            plugin_states[plugin_name] = {
                'enabled': plugin_info['enabled'],
                'type': plugin_info['type']
            }
        return plugin_states

    def cleanup(self):
        """Clean up resources when instance is closed - FIXED VERSION"""
        try:
            # Stop tailing if running
            self.stop_tail()
    
            # SYNC AND SAVE: Ensure all UI state is captured
            self.sync_ui_to_config()
            
            # Save filters state
            if self.filters:
                self.save_filters(False)  # Don't show dialog
                
            if self.advanced_filters:
                self.save_advanced_filters(False)  # Don't show dialog
                
            # Save main configuration
            self.config_manager.save_config()
            print(f"DEBUG: Instance {self.instance_id} cleanup completed")
            
            # Clean up plugin manager
            if hasattr(self, 'plugin_manager') and self.plugin_manager:
                for plugin_name in list(self.plugin_manager.loaded_plugins.keys()):
                    try:
                        self.plugin_manager.unload_plugin(plugin_name)
                    except Exception as e:
                        print(f"Error unloading plugin {plugin_name}: {e}")
            
            # Clean up action handler
            if hasattr(self, 'action_handler') and self.action_handler:
                if self.action_handler.tts_engine:
                    try:
                        self.action_handler.tts_engine.stop()
                    except:
                        pass
                
                if self.action_handler.pygame_initialized:
                    try:
                        pygame.mixer.quit()
                    except:
                        pass
                        
        except Exception as e:
            print(f"Error during instance cleanup: {e}")

    # ========== BROWSER INTEGRATION METHODS ==========

    def load_instance_identity(self):
        """Load instance identity from config to maintain consistency"""
        try:
            # Try to load instance name from config
            instance_name = self.config_manager.get("instance_name")
            instance_id = self.config_manager.get("instance_id")
            
            if instance_name and instance_name != self.instance_id:
                print(f"DEBUG: Updating instance name from config: {self.instance_id} -> {instance_name}")
                self.instance_id = instance_id or self.instance_id
                
            # Update the instance info in browser if available
            if hasattr(self, 'browser') and self.browser:
                if self.instance_id in self.browser.instances:
                    self.browser.instances[self.instance_id]['name'] = instance_name
                    # Update tab name
                    tab_index = self.browser.notebook.index(self.browser.instances[self.instance_id]['frame'])
                    self.browser.notebook.tab(tab_index, text=instance_name)
                    
        except Exception as e:
            print(f"DEBUG: Error loading instance identity: {e}")

    def save_instance_state(self):
        """Save instance state and update instances file"""
        try:
            self.sync_ui_to_config()
            
            # Save main configuration
            success = self.config_manager.save_config()
            
            # Save filters if they exist
            if self.filters:
                self.save_filters(False)
            if self.advanced_filters:
                self.save_advanced_filters(False)
            
            # Update instances file
            if hasattr(self, 'browser') and self.browser:
                self.browser.save_instances()
            
            return success
            
        except Exception as e:
            print(f"DEBUG: Error in save_instance_state: {e}")
            return False

    def broadcast_regex_match(self, field_data, original_line, filter_pattern):
        """Broadcast regex match data to all loaded plugins"""
        match_data = {
            'fields': field_data,  # Array of extracted fields
            'line': original_line,  # Complete log line
            'pattern': filter_pattern,  # Regex pattern used
            'timestamp': time.time()  # When the match occurred
        }
        print(f"DEBUG: broadcast  {field_data} - {filter_pattern}")
    
    # Send to all loaded plugins
        if hasattr(self, 'plugin_manager'):
            self.plugin_manager.call_plugin_method('on_regex_data', match_data)
            print(f"DEBUG: SEND  {match_data}")
            # Plugin filter system

    def test_dependency_loading(self):
        """Test if dependency loading is working"""
        try:
            # Try to import common dependencies to verify they're available
            test_imports = ['PIL', 'psutil', 'pyautogui', 'pytesseract']
            
            for import_name in test_imports:
                try:
                    __import__(import_name)
                    self.messages(2, 9, f"Dependency available: {import_name}")
                except ImportError:
                    self.messages(2, 3, f"Dependency missing: {import_name}")
                    
        except Exception as e:
            self.messages(2, 3, f"Dependency test failed: {e}")
    
    def load_specific_compiled_plugin(self, plugin_name: str) -> bool:
        """Load a specific compiled plugin by name"""
        try:
            if not hasattr(self, 'plugin_manager'):
                self.messages(2, 3, "Plugin manager not initialized")
                return False
            
            return self.plugin_manager.load_plugin(plugin_name)
            
        except Exception as e:
            self.messages(2, 3, f"Error loading compiled plugin {plugin_name}: {e}")
            return False

    def initialize_plugin_system(self):
        """Initialize plugin system WITHOUT importing dependencies"""
        try:
            self.plugin_manager = PluginManager(self)
        
            # Only setup paths, don't test imports
            if hasattr(self.plugin_manager, 'dependency_loader'):
                loader = self.plugin_manager.dependency_loader
                # Just setup paths, don't test imports
                loader.fix_pyautogui_import()    # Sets up path only
                loader.fix_pillow_import()       # Sets up path only
        
            self.messages(2, 9, "Plugin system initialized (lazy loading)")
        except Exception as e:
            self.messages(2, 3, f"Plugin system failed: {e}")

    def register_plugin_filter(self, plugin_filename, filter_pattern, filter_id, callback):
        """Register a plugin-specific filter"""
        # Check if the plugin filename exists in loaded_plugins
        if plugin_filename in self.plugin_manager.loaded_plugins:
            self.messages(2, 9, f"Plugin filter is ALREADY loaded: {plugin_filename} - {filter_id}")
   
        if plugin_filename not in self.plugin_filters:
            self.plugin_filters[plugin_filename] = []
            self.plugin_filter_callbacks[plugin_filename] = callback
            
        plugin_filter = {
            'id': filter_id,
            'pattern': filter_pattern,
            'plugin': plugin_filename,  # Store the filename identifier
            'regex': re.compile(filter_pattern) if filter_pattern else None
        }
        self.plugin_filters[plugin_filename].append(plugin_filter)


        self.messages(2, 9, f"Plugin filter registered(main): {plugin_filename} - {filter_id}")
        return True

    def process_plugin_filters(self, line):
        """Process all plugin filters against a line - instance specific"""
        if not hasattr(self, 'plugin_manager') or not self.plugin_manager:
            print(f"DEBUG: not self.plugin_manager:  {plugin_filename}")
            return

        for plugin_filename, filters in self.plugin_filters.items():
            # Only process plugins loaded in this instance
            if plugin_filename in self.plugin_manager.loaded_plugins:
                for filter_obj in filters:
                    if filter_obj['regex']:
                        matches = filter_obj['regex'].findall(line)
                        if matches:
                            callback = self.plugin_filter_callbacks.get(plugin_filename)
                            if callback:
                                # Pass instance context to callback
                                callback(filter_obj['id'], matches, line, self.instance_id)

    def remove_plugin_filter(self, plugin_name, filter_id):
        """Remove a specific plugin filter"""
        if plugin_name in self.plugin_filters:
            self.plugin_filters[plugin_name] = [
                f for f in self.plugin_filters[plugin_name] 
                if f['id'] != filter_id
            ]           
            # Remove plugin entry if no filters left
            if not self.plugin_filters[plugin_name]:
                del self.plugin_filters[plugin_name]
                del self.plugin_filter_callbacks[plugin_name]
        return True  # ← ADD THIS LINE                

    def test_plugin_integration(self):
        """Test if plugins are receiving data"""
        test_line = "2025-10-04 12:04:53 [System] [] You received Test Item x (1) Value: 0.0100 PED"
        print("DEBUG: Testing plugin integration...")
        self.process_plugin_filters(test_line)
        print("Test completed")

    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def auto_load_filters(self):
        """Automatically load filters file if it exists and auto-load is enabled"""
        try:
            # Auto-load simple filters
            filters_path = self.config_manager.get("filters_file", "")
            if filters_path:
                filters_path = Path(filters_path)
                
            if (self.config_manager.should_auto_load_filters() and 
                filters_path and filters_path.exists() and filters_path.is_file()):
            
                self.messages(2, 2, f"Auto-loading filters from {filters_path}")
                self.filters_file_var.set(str(filters_path))
                self.load_filters()
            else:
                # Don't show error for auto-load - it's normal for file not to exist initially
                if filters_path and filters_path.exists() and not filters_path.is_file():
                    print(f"DEBUG: Filters path is not a file: {filters_path}")
        
            # AUTO-LOAD ADVANCED FILTERS
            advanced_filters_path = self.config_manager.get("advanced_filters_file", "")
            if advanced_filters_path:
                advanced_filters_path = Path(advanced_filters_path)
                
            if (self.config_manager.should_auto_load_filters() and 
                advanced_filters_path and advanced_filters_path.exists() and advanced_filters_path.is_file()):
            
                self.messages(2, 2, f"Auto-loading advanced filters from {advanced_filters_path}")
                self.advanced_filters_file_var.set(str(advanced_filters_path))
                self.load_advanced_filters_auto()
            else:
                if advanced_filters_path and advanced_filters_path.exists() and not advanced_filters_path.is_file():
                    print(f"DEBUG: Advanced filters path is not a file: {advanced_filters_path}")
                
        except Exception as e:
            # Silent fail for auto-load - don't bother user with errors on startup
            print(f"Auto-load filters error: {e}")

    def load_filters(self):
        """Load filters from the configured filters file (auto-load version)"""
        filters_file = self.filters_file_var.get()
        if not filters_file:
            # Don't show error for auto-load - it's normal for file not to exist initially
            return
            
        try:
            filters_path = Path(filters_file)
            if not filters_path.exists() or not filters_path.is_file():
                print(f"DEBUG: Filters file doesn't exist or is not a file: {filters_file}")
                return
        
            with open(filters_path, 'r', encoding='utf-8') as f:
                filters_data = json.load(f)
        
            # Clear current filters
            self.filters.clear()
            self.filter_listbox.delete(0, tk.END)
        
            # Load new filters
            for filter_data in filters_data.get("filters", []):
                filter_key = f"{filter_data['pattern']}|{filter_data['action']}|{filter_data.get('action_modifier', '')}"
                self.filters[filter_key] = filter_data
            
                # Add to listbox
                action_display = filter_data['action'] if filter_data['action'] != "none" else "color only"
                modifier_display = f" ({filter_data['action_modifier']})" if filter_data.get('action_modifier') else ""
                display_text = f"{filter_data['pattern']} → {action_display}{modifier_display}"
                self.filter_listbox.insert(tk.END, display_text)
            
                # Configure text tag
                self.log_text.tag_configure(filter_key, 
                                      foreground=filter_data['fg_color'], 
                                      background=filter_data['bg_color'])
        
            # Update recent filters list
            self.config_manager.update_recent_list("recent_filters", str(filters_path))
            self.update_recent_combos()
        
            self.messages(2, 9, f"Loaded {len(self.filters)} filters automatically")
        
        except Exception as e:
            # Silent fail for auto-load - don't bother user with errors on startup
            print(f"Auto-load filters error: {e}")

    def save_filters_default(self):
        """Save current filters to the default filters file"""
        try:
            default_filters_path = self.config_manager.get_default_filters_path()
        
            filters_data = {
                "version": "1.1",
                "filters": list(self.filters.values())
            }
        
            with open(default_filters_path, 'w', encoding='utf-8') as f:
                json.dump(filters_data, f, indent=2, ensure_ascii=False)
        
            self.messages(2, 9, f"Filters saved to default location: {default_filters_path}")
            return True
        
        except Exception as e:
            self.messages(2, 3, f"Error saving default filters: {e}")
            return False
    
    def save_json(self, what_to_save, file_to_save, list_to_save, dialog):
        """Save current filters to the configured filters file - SIMPLIFIED"""
        file_types = [
            ('JSON files', '*.json'),
            ('All Files', '*.*')
        ]
    
        # Get current directory from config manager if available
        initial_dir = self.config_manager.get("last_directory", "")
    
        if dialog:
            # Open save file dialog
            file_to_save = filedialog.asksaveasfilename(
                title="Save Configuration As",
                defaultextension=".json",
                filetypes=file_types,
                initialdir=initial_dir,
            )
    
        if not file_to_save:
            return False
    
        try:
            with open(file_to_save, 'w', encoding='utf-8') as f:
                json.dump(list_to_save, f, indent=2, ensure_ascii=False)
    
            # Update recent filters list (no last config tracker)
            match what_to_save:
                case "simple":
                    self.config_manager.update_recent_list("recent_filters", file_to_save)
                    self.filters_file_var.set(Path(file_to_save))
                case "advanced":
                    self.config_manager.update_recent_list("recent_advanced_filters", file_to_save)
                    self.advanced_filters_file_var.set(Path(file_to_save))
    
            self.update_recent_combos()
            self.messages(2, 9, "Filters saved successfully")
            
            return True
        
        except Exception as e:
            self.messages(2, 3, f"Error saving filters: {e}")
            return False

    # *********************************************************************

    def messages(self, par_1, par_2, par_3):
        """Enhanced messaging that can communicate with browser"""
        self.str_out = f"{mssgs[par_2]} {par_3}"
        
        # Share important messages with browser
        if par_1 in [1, 2] and par_2 in [0, 1, 3]:  # Running, Stopped, Error states
            self.share_data_with_browser("status_update", {
                'instance_id': self.instance_id,
                'status': mssgs[par_2],
                'message': par_3
            })
        
        # Original message handling
        match par_1:
            case 0:
                print(f"[{self.instance_id}] {self.str_out}")
            case 1:
                self.update_status(self.str_out)
            case 2:
                print(f"[{self.instance_id}] {self.str_out}")
                self.update_status(self.str_out)

    def simple_encoding_detect(self, file_path):
        """Detects file encoding efficiently."""
        try:
            # Only read first 10KB for encoding detection
            with open(file_path, 'rb') as file:
                raw_data = file.read(10240)  # Read only first 10KB
            
            if not raw_data:
                return 'utf-8'
            
            detected = chardet.detect(raw_data)
            encoding = detected.get('encoding')
            confidence = detected.get('confidence', 0)
            return encoding if encoding and confidence > 0.8 else 'utf-8'
        except Exception as e:
            self.messages(2,3,f"Encoding detection failed: {e}. Using fallback 'utf-8'.")
            return 'utf-8'

    def get_last_lines(self, filepath, num_lines=50, encoding='utf-8'):
        """Efficiently get only the last N lines of a file."""
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as file:
                # Move to end of file
                file.seek(0, os.SEEK_END)
                file_size = file.tell()

                # Start reading backwards from the end
                buffer_size = 8192
                buffer = bytearray()
                lines_found = 0
                position = file_size
                
                while position > 0 and lines_found < num_lines + 1:
                    # Read chunk from current position
                    chunk_size = min(buffer_size, position)
                    position -= chunk_size
                    file.seek(position)
                    chunk = file.read(chunk_size)
                    # Add chunk to buffer and count lines
                    buffer = bytearray(chunk.encode(encoding) if isinstance(chunk, str) else chunk) + buffer
                    lines_found = buffer.count(b'\n') if isinstance(buffer, bytearray) else chunk.count('\n')
                
                # Convert to string and get last N lines
                if isinstance(buffer, bytearray):
                    content = buffer.decode(encoding, errors='replace')
                else:
                    content = buffer
                
                lines = content.splitlines()
                return lines[-num_lines:] if len(lines) > num_lines else lines              
        except Exception as e:
            self.messages(2,3,f"Error reading last lines: {e}")
            return []


    # *************************************************************************
    # *************************** Screen  *************************************
    # *************************************************************************   

    def create_widgets(self):
        """Create and arrange the GUI components within the frame"""
        # Main container
        main_container = ttk.Frame(self, style='Primary.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        # Top frame with instance info and status
        top_frame = ttk.Frame(main_container)
        top_frame.pack(fill=tk.X, pady=(0, 5))
    
        # Instance info
        instance_info = ttk.Label(top_frame, text=f"Instance: {self.instance_id}", 
                                style='Subtitle.TLabel')
        instance_info.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(top_frame, text="Ready", style='Status.Stopped.TLabel')
        self.status_label.pack(side=tk.RIGHT)
    
        # Create notebook (same as before)
        notebook = ttk.Notebook(main_container, style='Custom.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs (same as before)
        self.log_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.config_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.simple_filters_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.advanced_filters_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.plugins_tab = ttk.Frame(notebook, style='Primary.TFrame')

        notebook.add(self.log_tab, text="Log View")
        notebook.add(self.config_tab, text="Configuration") 
        notebook.add(self.simple_filters_tab, text="Simple Filters")
        notebook.add(self.advanced_filters_tab, text="Advanced Filters")
        notebook.add(self.plugins_tab, text="Plugins")

        # Create tab contents using your existing methods
        self.create_log_tab()
        self.create_config_tab()
        self.create_simple_filters_tab()
        self.create_advanced_filters_tab()
        self.create_plugins_tab()
        self.create_status_bar()

    # *************************************************************************

    def create_status_bar(self):
        """Create status bar at bottom of frame"""
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # *************************************************************************

    def update_status(self, message):
        """Update status with instance awareness"""
        self.status_var.set(message)
        
        if "Running" in message:
            self.status_label.config(style='Status.Running.TLabel')
        elif "Stopped" in message:
            self.status_label.config(style='Status.Stopped.TLabel') 
        elif "Paused" in message:
            self.status_label.config(style='Status.Paused.TLabel')
        else:
            self.status_label.config(style='')
        
        self.update_idletasks()

    # ========== NEW BROWSER-RELATED DIALOGS ==========

    def export_config_dialog(self):
        """Dialog to export configuration"""
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"etail_config_{self.instance_id}.json"
        )
        
        if filename:
            try:
                config_data = self.export_configuration()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                self.messages(2, 9, f"Configuration exported to {filename}")
            except Exception as e:
                self.messages(2, 3, f"Error exporting configuration: {e}")

    def share_filters_dialog(self):
        """Dialog to share filters with other instances"""
        if not self.browser:
            messagebox.showinfo("Sharing", "Sharing requires browser mode")
            return
            
        share_window = tk.Toplevel(self)
        share_window.title("Share Filters")
        share_window.geometry("400x300")
        
        main_frame = ttk.Frame(share_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Select filters to share:", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Filter selection
        selection_frame = ttk.Frame(main_frame)
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.share_simple_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(selection_frame, text=f"Simple Filters ({len(self.filters)})", 
                       variable=self.share_simple_var).pack(anchor=tk.W)
        
        self.share_advanced_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(selection_frame, text=f"Advanced Filters ({len(self.advanced_filters)})", 
                       variable=self.share_advanced_var).pack(anchor=tk.W)
        
        # Share button
        def share_filters():
            filter_data = {
                'source_instance': self.instance_id,
                'timestamp': time.time()
            }
            
            if self.share_simple_var.get():
                filter_data['simple_filters'] = self.filters
            if self.share_advanced_var.get():
                filter_data['advanced_filters'] = self.advanced_filters
                
            self.share_data_with_browser("filters", filter_data)
            share_window.destroy()
            self.messages(2, 9, "Filters shared with browser")
        
        ttk.Button(main_frame, text="Share Filters", 
                  command=share_filters).pack(pady=(10, 0))

    # ****************************************************************************

    def create_log_tab(self):
        """Create log viewing tab with modern styling"""
        # Main frame
        main_frame = ttk.Frame(self.log_tab, style='Primary.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Controls frame with modern styling
        controls_frame = ttk.LabelFrame(main_frame, text="Log Controls", style='Custom.TLabelframe')
        controls_frame.pack(fill=tk.X, pady=(0, 5))

        # Left controls
        left_controls = ttk.Frame(controls_frame)
        left_controls.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.start_button = ttk.Button(left_controls, text="Start Tail", state="normal", command=self.start_tail, style='Success.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(left_controls, text="Stop Tail", state="disabled", command=self.stop_tail, style='Danger.TButton')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(left_controls, text="Clear Display", command=self.clear_display).pack(side=tk.LEFT, padx=(0, 5))

        self.pause_var = tk.BooleanVar(value=False)
        self.pause_button = ttk.Button(left_controls, text="Pause", state="disabled", command=self.toggle_pause, style='Primary.TButton')
        self.pause_button.pack(side=tk.LEFT, padx=(20, 5))

        # Right controls - search
        right_controls = ttk.Frame(controls_frame)
        right_controls.pack(side=tk.RIGHT)

        # Encoding indicator
        self.encoding_label = ttk.Label(right_controls, text="")
        self.encoding_label.pack(side=tk.RIGHT)

        ttk.Label(right_controls, text="Search:").pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(right_controls, textvariable=self.search_var, width=25, style='Modern.TEntry')
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self.search_log())

        ttk.Button(right_controls, text="Find", command=self.search_log, style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_controls, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=(0, 5))

        # Search navigation buttons
        self.prev_button = ttk.Button(right_controls, text="▲ Prev", command=self.search_previous, state="disabled", style='Primary.TButton')
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))
        self.next_button = ttk.Button(right_controls, text="▼ Next", command=self.search_next, state="disabled", style='Primary.TButton')
        self.next_button.pack(side=tk.LEFT, padx=(0, 5))
  
        # Initialize search state
        self.search_matches = []
        self.current_match_index = -1

        # Log display area
        log_display_frame = ttk.LabelFrame(main_frame, text="Log Content", style='Custom.TLabelframe')
        log_display_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.log_text = scrolledtext.ScrolledText(log_display_frame, wrap=tk.WORD, width=80, height=25,
                                            font=('IBM Plex Mono Text', 10))  # Monospace font for logs
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Configure text tags with modern colors
        self.log_text.tag_configure("default", foreground="#2c3e50")
        self.log_text.tag_configure("search_highlight", background="#f39c12", foreground="black")
        self.log_text.tag_configure("search_current", background="#e74c3c", foreground="white")

        # Configure text tags for search highlighting
        self.log_text.tag_configure("search_highlight", background="yellow", foreground="black")
        self.log_text.tag_configure("search_current", background="orange", foreground="black")
    
        # Configure default text tag
        self.log_text.tag_configure("default", foreground="black")

    # ****************************************************************************

    def create_simple_filters_tab(self):
        #Create simple filters tab content.
        main_frame = ttk.Frame(self.simple_filters_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # ENHANCED FILTER CONFIGURATION SECTION
        filter_frame = ttk.LabelFrame(main_frame, text="Filter Configuration", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Filter pattern
        ttk.Label(filter_frame, text="Filter Pattern:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_string = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_string, width=40).grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")
        
        # Regex checkbox
        self.filter_regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Use Regex", variable=self.filter_regex_var).grid(row=0, column=2, pady=2, sticky="w")
        
        # Colors
        ttk.Label(filter_frame, text="Text Color:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        self.fg_color = tk.StringVar(value="black")
        ttk.Entry(filter_frame, textvariable=self.fg_color, width=10).grid(row=1, column=1, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(filter_frame, text='Select a Color', command=lambda: self.change_color('fg')).grid(row=1, column=1, padx=(100, 10), pady=2, sticky="w")

        ttk.Label(filter_frame, text="Background:").grid(row=1, column=3, sticky="w", padx=(0, 5), pady=2)
        self.bg_color = tk.StringVar(value="yellow")
        ttk.Entry(filter_frame, textvariable=self.bg_color, width=10).grid(row=1, column=4, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(filter_frame, text='Select a Color', command=lambda: self.change_color('bg')).grid(row=1, column=5, padx=(0, 10), pady=2, sticky="w")

        # Action type selection
        ttk.Label(filter_frame, text="Action:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_action_var = tk.StringVar(value="none")
        action_combo = ttk.Combobox(filter_frame, textvariable=self.filter_action_var, 
                                   values=["none", "sound", "tts", "skip", "notification", "dialog"],
                                   state="readonly", width=12)
        action_combo.grid(row=2, column=1, padx=(0, 10), pady=2, sticky="w")
        action_combo.bind('<<ComboboxSelected>>', self.on_action_changed)

        # Add filter button
        ttk.Button(filter_frame, text="Add Filter", command=self.add_enhanced_filter).grid(row=4, column=0, pady=10, sticky="w")
        
        # Update filter button (initially disabled)
        self.update_filter_btn = ttk.Button(filter_frame, text="Update Filter", command=self.update_enhanced_filter, state="disabled")
        self.update_filter_btn.grid(row=4, column=1, pady=10, sticky="w")
        
        # Action modifier
        ttk.Label(filter_frame, text="Action Modifier:").grid(row=3, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_action_modifier = tk.StringVar()
        self.action_modifier_entry = ttk.Entry(filter_frame, textvariable=self.filter_action_modifier, width=40)
        self.action_modifier_entry.grid(row=3, column=1, columnspan=2, padx=(0, 10), pady=2, sticky="w")
        
        # Sound file browser (initially hidden)
        self.browse_sound_btn = ttk.Button(filter_frame, text="Browse Sound", command=self.browse_sound_file)
        self.browse_sound_btn.grid(row=3, column=3, padx=(5, 0), pady=2)
        self.browse_sound_btn.grid_remove()  # Hide initially
 
        # Voice selection for TTS actions (using Combobox instead of Listbox)
        ttk.Label(filter_frame, text="TTS Voice:").grid(row=4, column=0, sticky="w", padx=(0, 5), pady=2)
    
        # Combobox for voice selection
        self.voice_combobox = ttk.Combobox(filter_frame, state="readonly", width=40)
        self.voice_combobox.grid(row=3, column=3, columnspan=2, sticky="w", pady=2)
        self.voice_combobox.grid_remove()  # Hide initially
        
        # Load available voices
        self.refresh_voices()
    
        # Test voice button
        self.test_voice_btn = ttk.Button(filter_frame, text="Test Voice", command=self.test_selected_voice)
        self.test_voice_btn.grid(row=3, column=5, padx=(5, 0), pady=2)
        self.test_voice_btn.grid_remove()  # Hide initially
        
        # Add filter button
        ttk.Button(filter_frame, text="Add Filter", command=self.add_enhanced_filter).grid(row=4, column=0, pady=10, sticky="w")
        
        # Filter list display
        listbox_frame = ttk.Frame(filter_frame)
        listbox_frame.grid(row=5, column=0, columnspan=6, sticky="nsew", pady=(10, 0))        

        # Force the listbox frame to expand vertically
        filter_frame.rowconfigure(5, weight=1)
        filter_frame.columnconfigure(0, weight=1)
        
        # Add scrollbar to listbox
        self.filter_listbox = tk.Listbox(listbox_frame, width=80, height=6) 
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.filter_listbox.yview)

        scrollbar.grid(row=0, column=1, sticky="ns")
        self.filter_listbox.configure(yscrollcommand=scrollbar.set)

        self.filter_listbox.bind('<<ListboxSelect>>', self.on_filter_select)
        self.filter_listbox.bind('<<ListboxSelect>>', self.on_filter_selection_change)
       
        # Make the listbox frame expand properly
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
              
        # Use grid geometry manager instead of pack for better control
        self.filter_listbox.grid(row=0, column=0, sticky="nsew")       
        
        # Remove filter button
        ttk.Button(filter_frame, text="Remove Selected Filter", command=self.remove_enhanced_filter).grid(row=6, column=0, pady=5, sticky="w")
    
        button_frame = ttk.Frame(filter_frame)
        button_frame.grid(row=4, column=0, columnspan=6, pady=10, sticky="w")
    
        ttk.Button(button_frame, text="Add Filter", command=self.add_enhanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        self.edit_filter_btn = ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_filter, state="disabled")
        self.edit_filter_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.update_filter_btn = ttk.Button(button_frame, text="Update Filter", command=self.update_filter, state="disabled")
        self.update_filter_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel Edit", command=self.cancel_edit).pack(side=tk.LEFT)
    
        # Make filter frame grid responsive
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.rowconfigure(5, weight=1)  # This makes the listbox row expandable

    # ****************************************************************************

    def create_advanced_filters_tab(self):
        """Create advanced filters tab with collapsible sections - ENHANCED"""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.advanced_filters_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create collapsible sections
        self.builder_section = CollapsibleFrame(main_frame, text="Regex Builder")
        self.builder_section.pack(fill=tk.X, pady=(0, 5))

        self.actions_section = CollapsibleFrame(main_frame, text="Actions")
        self.actions_section.pack(fill=tk.X, pady=(0, 5))

        self.saved_section = CollapsibleFrame(main_frame, text="Saved Advanced Filters")
        self.saved_section.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Build each section
        self.build_regex_builder_section()
        self.build_actions_section()
        self.actions_section.toggle()
        self.build_saved_filters_section()
        self.saved_section.toggle()

        # Control buttons at bottom (always visible)
        self.build_control_buttons(main_frame)
        # Initialize with one empty field
        self.after(100, self.initialize_advanced_filters)  # Small delay to ensure UI is built

    def initialize_advanced_filters(self):
        """Initialize advanced filters tab with default state"""
        # Add one empty field to start
        if not self.regex_fields:
            self.add_regex_field()
    
        # Load advanced filters if auto-load is enabled
        if self.config_manager.get("auto_load_config", True):
            self.auto_load_advanced_filters()

    def auto_load_advanced_filters(self):
        """Auto-load advanced filters on startup"""
        try:
            advanced_filters_file = self.config_manager.get("advanced_filters_file", "")
            if advanced_filters_file and os.path.exists(advanced_filters_file):
                self.advanced_filters_file_var.set(advanced_filters_file)
                self.load_advanced_filters_auto()
        except Exception as e:
            print(f"Auto-load advanced filters error: {e}")

    def build_regex_builder_section(self):
    
        """Build the regex builder section with common patterns combobox"""
        builder_frame = self.builder_section.get_content_frame()

        # TOP BAR: Common patterns combobox and controls
        top_bar_frame = ttk.Frame(builder_frame)
        top_bar_frame.pack(fill=tk.X, pady=(0, 10))

        # Common patterns combobox on the right
        ttk.Label(top_bar_frame, text="Common Patterns:").pack(side=tk.LEFT, padx=(0, 5))

        self.common_patterns_var = tk.StringVar()
        self.common_patterns_combo = ttk.Combobox(
            top_bar_frame, 
            textvariable=self.common_patterns_var,
            values=list(self.predefined_patterns.keys()),
            state="readonly",
            width=20
        )
        self.common_patterns_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.common_patterns_combo.set("Select a pattern")  # Default text
    
        # Insert pattern button
        ttk.Button(
            top_bar_frame, 
            text="Insert Pattern", 
            command=self.insert_common_pattern
        ).pack(side=tk.LEFT, padx=(0, 10))
    
        # Preview pattern button
        ttk.Button(
            top_bar_frame, 
            text="Preview", 
            command=self.preview_common_pattern
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Help text on the left
        help_text = "Tip: Use commas to separate multiple terms in 'as string' and 'as word' modifiers"
        help_label = ttk.Label(top_bar_frame, text=help_text, font=("Arial", 8), foreground="blue")
        help_label.pack(side=tk.RIGHT)

        # Rest of your existing builder section code...
        name_frame = ttk.Frame(builder_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        """Build the regex builder section"""
        builder_frame = self.builder_section.get_content_frame()

        # Filter name and enabled
        name_frame = ttk.Frame(builder_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="Filter Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.advanced_filter_name = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.advanced_filter_name, width=30).pack(side=tk.LEFT, padx=(0, 15))

        self.advanced_filter_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(name_frame, text="Enabled", variable=self.advanced_filter_enabled).pack(side=tk.LEFT)

        # Regex fields container with scrollbar
        fields_container = ttk.Frame(builder_frame)
        fields_container.pack(fill=tk.BOTH, expand=True)

        # Create scrollable canvas for fields
        self.fields_canvas = tk.Canvas(fields_container, height=150)
        fields_scrollbar = tk.Scrollbar(fields_container, orient="vertical", command=self.fields_canvas.yview)
        self.fields_scrollable_frame = ttk.Frame(self.fields_canvas)

        self.fields_scrollable_frame.bind("<Configure>", lambda e: self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all")))

        self.fields_canvas.create_window((0, 0), window=self.fields_scrollable_frame, anchor="nw")
        self.fields_canvas.configure(yscrollcommand=fields_scrollbar.set)

        self.fields_canvas.pack(side="left", fill="both", expand=True)
        fields_scrollbar.pack(side="right", fill="y")

        # Add field button
        ttk.Button(builder_frame, text="Add Field", command=self.add_regex_field).pack(pady=(10, 0))
    
        # Generated Regex Display
        regex_display_frame = ttk.LabelFrame(builder_frame, text="Generated Regex", padding="5")
        regex_display_frame.pack(fill=tk.X, pady=(10, 0))

        self.generated_regex = tk.StringVar()
        regex_entry = ttk.Entry(regex_display_frame, textvariable=self.generated_regex, font=("Courier", 9), state="readonly")
        regex_entry.pack(fill=tk.X, padx=5, pady=2)

        # Test regex button - ENHANCED
        test_button_frame = ttk.Frame(regex_display_frame)
        test_button_frame.pack(fill=tk.X, pady=(5, 2))
    
        ttk.Button(test_button_frame, text="Test Regex Pattern", command=self.test_generated_regex).pack(side=tk.LEFT)

        # Add a button to copy regex to clipboard
        ttk.Button(test_button_frame, text="Copy to Clipboard", command=lambda: self.copy_to_clipboard(self.generated_regex.get())).pack(side=tk.LEFT, padx=(10, 0))

    def build_actions_section(self):
        """Build the actions section"""
        actions_frame = self.actions_section.get_content_frame()
    
        # Use grid for better alignment in actions section
        # Colors
        ttk.Label(actions_frame, text="Text Color:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_fg_color = tk.StringVar(value="black")
        ttk.Entry(actions_frame, textvariable=self.advanced_fg_color, width=10).grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(actions_frame, text='Select', command=lambda: self.change_color('advanced_fg')).grid(row=0, column=2, pady=2, sticky="w")

        ttk.Label(actions_frame, text="Background:").grid(row=0, column=3, sticky="w", padx=(20, 5), pady=2)
        self.advanced_bg_color = tk.StringVar(value="yellow")
        ttk.Entry(actions_frame, textvariable=self.advanced_bg_color, width=10).grid(row=0, column=4, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(actions_frame, text='Select', command=lambda: self.change_color('advanced_bg')).grid(row=0, column=5, pady=2, sticky="w")
    
        # Action type selection
        ttk.Label(actions_frame, text="Additional Action:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_action_var = tk.StringVar(value="none")
        action_combo = ttk.Combobox(actions_frame, textvariable=self.advanced_action_var,
                               values=["none", "sound", "tts", "notification", "dialog"],
                               state="readonly", width=12)
        action_combo.grid(row=1, column=1, padx=(0, 10), pady=2, sticky="w")
        action_combo.bind('<<ComboboxSelected>>', self.on_advanced_action_changed)

        # Action modifier
        ttk.Label(actions_frame, text="Action Details:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_action_modifier = tk.StringVar()
        self.advanced_action_modifier_entry = ttk.Entry(actions_frame, textvariable=self.advanced_action_modifier, width=40)
        self.advanced_action_modifier_entry.grid(row=2, column=1, columnspan=3, padx=(0, 10), pady=2, sticky="w")

        # Advanced TTS voice selection
        ttk.Label(actions_frame, text="TTS Voice:").grid(row=3, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_voice_combobox = ttk.Combobox(actions_frame, state="readonly", width=30)
        self.advanced_voice_combobox.grid(row=3, column=1, columnspan=2, padx=(0, 10), pady=2, sticky="w")
        self.advanced_voice_combobox.grid_remove()  # Hide initially

    def build_saved_filters_section(self):
        """Build the saved filters section"""
        saved_frame = self.saved_section.get_content_frame()

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(saved_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        self.advanced_filters_listbox = tk.Listbox(listbox_frame, height=6)
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.advanced_filters_listbox.yview)
        self.advanced_filters_listbox.configure(yscrollcommand=scrollbar.set)

        self.advanced_filters_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Filter management buttons
        mgmt_frame = ttk.Frame(saved_frame)
        mgmt_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(mgmt_frame, text="Load Selected", command=self.load_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(mgmt_frame, text="Delete Selected", command=self.delete_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(mgmt_frame, text="Toggle Enabled", command=self.toggle_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))

    def build_control_buttons(self, parent_frame):
        """Build the control buttons (always visible)"""
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Store Advanced Filter", command=self.store_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear Form", command=self.clear_advanced_form).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Collapse All", command=self.collapse_all_sections).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Expand All", command=self.expand_all_sections).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(button_frame, text="Test", command=self.debug_advanced_filters).pack(side=tk.RIGHT, padx=(0, 5))

    def collapse_all_sections(self):
        """Collapse all collapsible sections"""
        if hasattr(self, 'builder_section') and self.builder_section.is_expanded:
            self.builder_section.toggle()
        if hasattr(self, 'actions_section') and self.actions_section.is_expanded:
            self.actions_section.toggle()
        if hasattr(self, 'saved_section') and self.saved_section.is_expanded:
            self.saved_section.toggle()

    def expand_all_sections(self):
        """Expand all collapsible sections"""
        if hasattr(self, 'builder_section') and not self.builder_section.is_expanded:
            self.builder_section.toggle()
        if hasattr(self, 'actions_section') and not self.actions_section.is_expanded:
            self.actions_section.toggle()
        if hasattr(self, 'saved_section') and not self.saved_section.is_expanded:
            self.saved_section.toggle()

    def insert_common_pattern(self):
        """Insert the selected common pattern into the currently focused field"""
        pattern_name = self.common_patterns_var.get()
        if not pattern_name or pattern_name == "Select a pattern":
            self.messages(2, 3, "Please select a pattern first")
            return

        pattern = self.predefined_patterns.get(pattern_name)
        if not pattern:
            self.messages(2, 3, "Selected pattern not found")
            return

        # Find the currently focused field
        focused_widget = self.root.focus_get()
    
        # Search through all regex fields to find the focused entry
        for field_frame in self.regex_fields:
            for widget in field_frame.winfo_children():
                if widget == focused_widget and isinstance(widget, ttk.Entry):
                    # Found the focused entry widget
                    current_text = widget.get()
                    if current_text:
                        # Insert at cursor position or replace selection
                        try:
                            # Get selection range
                            sel_range = widget.selection_get()
                            if sel_range:
                                # Replace selection
                                start = widget.index(tk.SEL_FIRST)
                                end = widget.index(tk.SEL_LAST)
                                widget.delete(start, end)
                                widget.insert(start, pattern)
                            else:
                                # Insert at cursor
                                cursor_pos = widget.index(tk.INSERT)
                                widget.insert(cursor_pos, pattern)
                        except tk.TclError:
                            # No selection, insert at end
                            widget.insert(tk.END, pattern)
                    else:
                        # Field is empty, just set the pattern
                        widget.delete(0, tk.END)
                        widget.insert(0, pattern)
                
                    # Update the generated regex
                    self.update_generated_regex()
                    self.messages(2, 9, f"Pattern '{pattern_name}' inserted")
                    return
    
        # If no focused field found, insert into the first field
        if self.regex_fields:
            first_field = self.regex_fields[0]
            field_entry = None
            for widget in first_field.winfo_children():
                if isinstance(widget, ttk.Entry):
                    field_entry = widget
                    break
        
            if field_entry:
                field_entry.delete(0, tk.END)
                field_entry.insert(0, pattern)
                self.update_generated_regex()
                self.messages(2, 9, f"Pattern '{pattern_name}' inserted into first field")
            else:
                self.messages(2, 3, "No field found to insert pattern")
        else:
            self.messages(2, 3, "No regex fields available")

    def preview_common_pattern(self):
        """Show a preview of the selected common pattern"""
        pattern_name = self.common_patterns_var.get()
        if not pattern_name or pattern_name == "Select a pattern":
            self.messages(2, 3, "Please select a pattern first")
            return

        pattern = self.predefined_patterns.get(pattern_name)
        if not pattern:
            self.messages(2, 3, "Selected pattern not found")
            return

        # Create preview dialog
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"Pattern Preview: {pattern_name}")
        preview_window.geometry("500x300")
        preview_window.transient(self.root)

        main_frame = ttk.Frame(preview_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Pattern display
        ttk.Label(main_frame, text="Pattern:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        pattern_text = tk.Text(main_frame, height=3, wrap=tk.WORD, font=("Courier", 9))
        pattern_text.pack(fill=tk.X, pady=(0, 10))
        pattern_text.insert(1.0, pattern)
        pattern_text.config(state=tk.DISABLED)

        # Description
        ttk.Label(main_frame, text="Description:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 10))
    
        descriptions = {
            "Date (YYYY-MM-DD)": "Matches dates in YYYY-MM-DD format",
            "Date (MM/DD/YYYY)": "Matches dates in MM/DD/YYYY format", 
            "Time (HH:MM:SS)": "Matches times in HH:MM:SS format",
            "IPv4 Address": "Matches IPv4 addresses",
            "IPv6 Address": "Matches IPv6 addresses",
            "Email Address": "Matches email addresses",
            "Phone Number": "Matches phone numbers",
            "URL": "Matches URLs starting with http/https",
            "Hex Color": "Matches hexadecimal color codes",
            "MAC Address": "Matches MAC addresses",
            "Credit Card": "Matches credit card numbers",
            "UUID": "Matches UUIDs",
            "Log Level": "Matches common log levels (DEBUG, INFO, WARN, etc.)",
            "Number": "Matches numbers",
            "Word": "Matches words"
        }
    
        desc_text = tk.Text(desc_frame, height=2, wrap=tk.WORD)
        desc_text.pack(fill=tk.X)
        desc_text.insert(1.0, descriptions.get(pattern_name, "No description available"))
        desc_text.config(state=tk.DISABLED)

        # Example matches
        ttk.Label(main_frame, text="Example Matches:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        examples_frame = ttk.Frame(main_frame)
        examples_frame.pack(fill=tk.BOTH, expand=True)
    
        examples_text = tk.Text(examples_frame, wrap=tk.WORD)
        examples_text.pack(fill=tk.BOTH, expand=True)
    
        # Generate examples based on pattern type
        examples = self.generate_pattern_examples(pattern_name, pattern)
        examples_text.insert(1.0, "\n".join(examples))
        examples_text.config(state=tk.DISABLED)

        ttk.Button(main_frame, text="Close", command=preview_window.destroy).pack(pady=(10, 0))

    def generate_pattern_examples(self, pattern_name, pattern):
        """Generate example matches for common patterns"""
        examples = {
            "Date (YYYY-MM-DD)": ["2024-01-15", "1999-12-31", "2023-03-08"],
            "Date (MM/DD/YYYY)": ["12/31/2023", "01/15/2024", "03/08/2023"],
            "Time (HH:MM:SS)": ["14:30:25", "09:15:00", "23:59:59"],
            "IPv4 Address": ["192.168.1.1", "10.0.0.1", "172.16.254.1"],
            "IPv6 Address": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334", "::1", "2001:db8::1"],
            "Email Address": ["user@example.com", "test.email+tag@domain.co.uk", "name@company.org"],
            "Phone Number": ["555-123-4567", "555.123.4567", "5551234567"],
            "URL": ["https://example.com", "http://sub.domain.co.uk/path", "https://www.google.com"],
            "Hex Color": ["#ff0000", "#abc", "#123456", "#f0f0f0"],
            "MAC Address": ["00:1B:44:11:3A:B7", "00-1B-44-11-3A-B7", "001B44113AB7"],
            "Credit Card": ["4111-1111-1111-1111", "5500 0000 0000 0004", "340000000000009"],
            "UUID": ["123e4567-e89b-12d3-a456-426614174000", "00000000-0000-0000-0000-000000000000"],
            "Log Level": ["DEBUG: Starting process", "ERROR: File not found", "INFO: Operation completed"],
            "Number": ["123", "0", "999999", "42"],
            "Word": ["hello", "test", "example", "word"]
        }
    
        return examples.get(pattern_name, ["No examples available"])

    # ****************************************************************************


    def create_config_tab(self):
        """Enhanced config tab with instance info"""
        main_frame = ttk.Frame(self.config_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Instance Info Section
        instance_frame = ttk.LabelFrame(main_frame, text="Instance Information", padding="10")
        instance_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(instance_frame, text="Instance ID:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(instance_frame, text=self.instance_id, font=("Arial", 9, "bold")).grid(row=0, column=1, sticky="w", pady=2)
        
        ttk.Label(instance_frame, text="Config File:").grid(row=1, column=0, sticky="w", pady=2)
        config_label = ttk.Label(instance_frame, text=str(self.config_file), font=("Courier", 8))
        config_label.grid(row=1, column=1, sticky="w", pady=2)
        
        # Browser integration buttons
        browser_frame = ttk.Frame(instance_frame)
        browser_frame.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        
        ttk.Button(browser_frame, text="Export Config", 
                  command=self.export_config_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(browser_frame, text="Share Filters", 
                  command=self.share_filters_dialog).pack(side=tk.LEFT, padx=(0, 5))
    
        # File Settings Section
        file_frame = ttk.LabelFrame(main_frame, text="File Settings", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        # Log file selection - SINGLE SOURCE OF TRUTH
        ttk.Label(file_frame, text="Default Log File:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        
        # Initialize the StringVar
        if not hasattr(self, 'log_file_var'):
            self.log_file_var = tk.StringVar(value=self.config_manager.get("log_file", ""))
        
        # Create the Entry widget - store it in a way that prevents overwriting
        self._config_log_file_entry = ttk.Entry(file_frame, textvariable=self.log_file_var, width=50)
        self._config_log_file_entry.grid(row=0, column=1, padx=(0, 5), pady=2)
        
        # Create the browse button
        self._config_browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_log_file)
        self._config_browse_button.grid(row=0, column=2, pady=2)
        
        # Create aliases that point to the protected widgets
        self.log_file_entry = self._config_log_file_entry
        self.browse_button = self._config_browse_button
        
        print(f"Config tab created - log_file_entry: {self.log_file_entry}")
       
        # Server checkbox
        self.server_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(file_frame, text="Enable Remote Log Server",variable=self.server_enabled_var,command=self.toggle_server).grid(row=0, column=3, sticky="w", pady=10)
        
        # Server configure button
        ttk.Button(file_frame, text="Configure Server",command=self.configure_server).grid(row=0, column=4, pady=2)
        
        # Server status label
        self.server_status_label = ttk.Label(file_frame, text="Server: Stopped",style='Status.Stopped.TLabel').grid(row=0, column=5, sticky="w", padx=(0, 5), pady=2)   
        
        # Filters file selection - FIXED: Initialize with empty if invalid
        ttk.Label(file_frame, text="Filters File:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        filters_file = self.config_manager.get("filters_file", "")
        if filters_file:
            filters_path = Path(filters_file)
            if not filters_path.exists() or not filters_path.is_file():
                filters_file = ""  # Reset if invalid
        # Load filters button
        
        self.filters_file_var = tk.StringVar(value=filters_file)
        ttk.Entry(file_frame, textvariable=self.filters_file_var, width=50).grid(row=1, column=1, padx=(0, 5), pady=2)
        ttk.Button(file_frame, text="Load", command=lambda: self.browse_filter_file("filters_file")).grid(row=1, column=2, pady=2)
        # Save as default filters button
        ttk.Button(file_frame, text="Save", command=lambda: self.save_filters(True)).grid(row=1, column=3, sticky="e", pady=2)
      
        # Advanced filters file selection - FIXED: Initialize with empty if invalid
        ttk.Label(file_frame, text="Advanced Filters File:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        advanced_filters_file = self.config_manager.get("advanced_filters_file", "")
        if advanced_filters_file:
            adv_filters_path = Path(advanced_filters_file)
            if not adv_filters_path.exists() or not adv_filters_path.is_file():
                advanced_filters_file = ""  # Reset if invalid
    
        self.advanced_filters_file_var = tk.StringVar(value=advanced_filters_file)
        ttk.Entry(file_frame, textvariable=self.advanced_filters_file_var, width=50).grid(row=2, column=1, padx=(0, 5), pady=2)
        ttk.Button(file_frame, text="Load", command=lambda: self.browse_filter_file("advanced_filters_file")).grid(row=2, column=2, pady=2)
        ttk.Button(file_frame, text="Save", command=lambda: self.save_advanced_filters(True)).grid(row=2, column=3, sticky="e", pady=2)

        # Application Settings Section
        app_frame = ttk.LabelFrame(main_frame, text="Application Settings", padding="10")
        app_frame.pack(fill=tk.X, pady=(0, 10))

        # Initial lines
        ttk.Label(app_frame, text="Initial Lines:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.initial_lines_var = tk.StringVar(value=str(self.config_manager.get("initial_lines", 50)))
        ttk.Entry(app_frame, textvariable=self.initial_lines_var, width=10).grid(row=0, column=1, sticky="w", pady=2)
        
        # Refresh interval
        ttk.Label(app_frame, text="Refresh Interval (ms):").grid(row=0, column=2, sticky="w", padx=(20, 10), pady=2)
        self.refresh_interval_var = tk.StringVar(value=str(self.config_manager.get("refresh_interval", 100)))
        ttk.Entry(app_frame, textvariable=self.refresh_interval_var, width=10).grid(row=0, column=3, sticky="w", pady=2)

      
        # Auto-load checkbox
        self.auto_load_var = tk.BooleanVar(value=self.config_manager.get("auto_load_config", True))
        ttk.Checkbutton(app_frame, text="Auto-load last configuration and filters on startup", variable=self.auto_load_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=10)
       
        # Verbosity checkbox
        self.verbose_var = tk.BooleanVar(value=self.config_manager.get("verbose", True))
        ttk.Checkbutton(app_frame, text="Verbosity", variable=self.verbose_var).grid(row=1, column=2, columnspan=4, sticky="w", pady=10)


        # Styling
        #self.auto_style_var = tk.BooleanVar(value=self.config_manager.get("auto_style", True))
        self.auto_style_var = tk.BooleanVar(value=self.config_manager.get("auto_style", False))
        #ttk.Checkbutton(app_frame, text="Apply custom styling", variable=self.auto_style_var).grid(row=2, column=0, columnspan=1, sticky="w", pady=10)
       
        self.style = ttk.Style()
        available_themes = self.style.theme_names()

        self.style_list_combo = ttk.Combobox(app_frame, values=available_themes, width=50)
        self.style_list_combo.grid(row=2, column=1, padx=(10, 5), pady=2)
        self.style_list_combo.current(0)
        
        ttk.Button(app_frame, text="Change theme", command=lambda: self.change_theme(self.style_list_combo.get(),self.auto_style_var), style='Danger.TButton').grid(row=2, column=2, pady=2)
       
        # Recent Files Section
        recent_frame = ttk.LabelFrame(main_frame, text="Recent Files", padding="10")
        recent_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Recent filters
        ttk.Label(recent_frame, text="Recent Filters:").grid(row=0, column=0, sticky="w", pady=2)
        self.recent_filters_combo = ttk.Combobox(recent_frame, values=self.config_manager.get("recent_filters", []), width=50)
        self.recent_filters_combo.grid(row=0, column=1, padx=(10, 5), pady=2)
        ttk.Button(recent_frame, text="Load", command=lambda: self.on_recent_filters_selected(self.recent_filters_combo.get())).grid(row=0, column=3, pady=2)

        # Recent advanced filters
        ttk.Label(recent_frame, text="Recent Advanced Filters:").grid(row=1, column=0, sticky="w", pady=2)
        self.recent_adv_filters_combo = ttk.Combobox(recent_frame, values=self.config_manager.get("recent_advanced_filters", []), width=50)
        self.recent_adv_filters_combo.grid(row=1, column=1, padx=(10, 5), pady=2)
        ttk.Button(recent_frame, text="Load", command=lambda: self.on_recent_adv_filters_selected(self.recent_adv_filters_combo.get())).grid(row=1, column=3, pady=2)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Save Configuration", command=self.save_configuration_dialog).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Load Configuration", command=self.load_configuration_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_configuration).pack(side=tk.LEFT)

    # *************************************************************************

    def toggle_server(self):
        """Toggle server on/off"""
        print(f"toggle_server called - server_enabled: {self.server_enabled_var.get()}")
        
        if self.server_enabled_var.get():
            # Start server
            if not hasattr(self, 'log_server'):
                self.log_server = LogServer(self.config_manager, self.instance_id)
            
            if self.log_server.start_server():
                # Update GUI status
                client_count = len(self.log_server.connected_clients)
                status_text = f"Server: Running on port {self.log_server.port}{self.log_server.ssl_sw}"
                if client_count > 0:
                    status_text += f" ({client_count} clients)"
                
                self.status_label.config(text=status_text)
                self.status_label.configure(style='Status.Running.TLabel')
                
                # Disable local log file selection in config tab
                self._safe_widget_config(self._config_log_file_entry, 'state', 'disabled')
                self._safe_widget_config(self._config_browse_button, 'state', 'disabled')
                
                # Update log file to use server log file
                server_log_path = str(self.log_server.server_log_file)
                self.log_file_var.set(server_log_path)
                print(f"Server enabled - log file set to: {server_log_path}")
            else:
                self.server_enabled_var.set(False)
                self.server_status_label.config(text="Server: Failed to start")
        else:
            # Stop server
            if hasattr(self, 'log_server'):
                self.log_server.stop_server()
            
            self.status_label.config(text="Server: Stopped")
            self.status_label.configure(style='Status.Stopped.TLabel')
            
            # Enable local log file selection in config tab
            self._safe_widget_config(self._config_log_file_entry, 'state', 'normal')
            self._safe_widget_config(self._config_browse_button, 'state', 'normal')
            
            print("Server disabled - log file widgets enabled")
    
    def _safe_widget_config(self, widget, option, value):
        """Safely configure a widget with error handling"""
        try:
            if widget is not None:
                widget.config(**{option: value})
            else:
                print(f"Warning: Attempted to configure None widget with {option}={value}")
        except Exception as e:
            print(f"Error configuring widget: {e}")

    def track_widget_changes(self):
        """Track when log_file_entry changes"""
        import inspect
        current_frame = inspect.currentframe()
        
        # Set up a property to track assignments
        original_value = getattr(self, 'log_file_entry', None)
        print(f"Initial log_file_entry value: {original_value}")
        
        # This will help us find where it's being set to None
        def log_setattr(name, value):
            if name == 'log_file_entry' and value != original_value:
                print(f"log_file_entry CHANGED from {original_value} to {value}")
                print("Stack trace:")
                for frame_info in inspect.stack()[1:6]:
                    print(f"  {frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
            return value
        
        # We can't easily override __setattr__ dynamically, so let's use a different approach
        # Instead, let's check periodically
        self.after(100, self._check_widget_state)
    
    def _check_widget_state(self):
        """Periodically check the widget state"""
        if hasattr(self, 'log_file_entry') and self.log_file_entry is None:
            print("ALERT: log_file_entry is None during periodic check!")
        self.after(100, self._check_widget_state)
    
    def configure_server(self):
        """Open server configuration dialog"""
        dialog = ServerConfigDialog(self, self.config_manager, self.instance_id)
        self.wait_window(dialog)
        
        # Restart server if it was running
        if hasattr(self, 'log_server') and self.log_server.is_running:
            self.log_server.stop_server()
            self.toggle_server()

    def create_plugins_tab(self):
        """Create the plugins management tab"""
        main_frame = ttk.Frame(self.plugins_tab, style='Primary.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="Plugin Manager", style='Title.TLabel').pack(anchor=tk.W)
        ttk.Label(title_frame, text="Extend ETail functionality with plugins", 
                 style='Subtitle.TLabel').pack(anchor=tk.W)
        
        # Plugin discovery and controls
        controls_frame = ttk.LabelFrame(main_frame, text="Plugin Controls", style='Custom.TLabelframe')
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        control_buttons = ttk.Frame(controls_frame)
        control_buttons.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_buttons, text="Discover Plugins", 
                  command=self.discover_plugins, style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_buttons, text="Reload All", 
                  command=self.reload_plugins).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_buttons, text="Open Plugins Folder", 
                  command=self.open_plugins_folder).pack(side=tk.LEFT)
        
        # Plugins list
        list_frame = ttk.LabelFrame(main_frame, text="Available Plugins", style='Custom.TLabelframe')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create treeview for plugins
        columns = ('name', 'version', 'description', 'status')
        self.plugins_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        self.plugins_tree.heading('name', text='Plugin Name')
        self.plugins_tree.heading('version', text='Version')
        self.plugins_tree.heading('description', text='Description')
        self.plugins_tree.heading('status', text='Status')
        
        self.plugins_tree.column('name', width=150)
        self.plugins_tree.column('version', width=80)
        self.plugins_tree.column('description', width=300)
        self.plugins_tree.column('status', width=100)
        
        # Scrollbar for treeview
        tree_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.plugins_tree.yview)
        self.plugins_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.plugins_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Plugin actions frame
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.enable_button = ttk.Button(actions_frame, text="Enable Plugin", 
                                       command=self.enable_selected_plugin, 
                                       style='Success.TButton', state='disabled')
        self.enable_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disable_button = ttk.Button(actions_frame, text="Disable Plugin", 
                                        command=self.disable_selected_plugin, 
                                        style='Danger.TButton', state='disabled')
        self.disable_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.settings_button = ttk.Button(actions_frame, text="Settings", 
                                         command=self.show_plugin_settings, 
                                         state='disabled')
        self.settings_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Plugin info frame
        self.info_frame = ttk.LabelFrame(main_frame, text="Plugin Information", style='Custom.TLabelframe')
        self.info_frame.pack(fill=tk.X)
        
        self.plugin_info_text = scrolledtext.ScrolledText(self.info_frame, height=4, wrap=tk.WORD)
        self.plugin_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.plugin_info_text.config(state=tk.DISABLED)
        
        # Bind selection event
        self.plugins_tree.bind('<<TreeviewSelect>>', self.on_plugin_selection_changed)
        
        # Initial plugin discovery
        self.after(1000, self.discover_plugins)  # Delay to let UI load first

    def discover_plugins(self):
        """Discover and list available plugins"""
        self.plugin_manager.discover_plugins()
        
        # DEBUG: Check what the plugin manager actually found
        print(f"DEBUG: Plugin manager found {len(self.plugin_manager.plugins)} plugins")

        self.refresh_plugins_list()
        self.messages(2, 9, f"Found {len(self.plugin_manager.plugins)} plugins")

    def refresh_plugins_list(self):
        """Refresh the plugins treeview"""
        # Clear existing items
        for item in self.plugins_tree.get_children():
            self.plugins_tree.delete(item)
        
        # Add plugins to treeview
        for plugin_name, plugin_info in self.plugin_manager.plugins.items():
            plugin_class = plugin_info['class']
            plugin_instance = plugin_class(self)  # Temporary instance for info
            
            status = "Enabled" if plugin_info['enabled'] else "Disabled"
            
            self.plugins_tree.insert('', tk.END, values=(
                plugin_instance.name,
                plugin_instance.version,
                plugin_instance.description,
                status
            ), tags=(plugin_name,))

    def on_plugin_selection_changed(self, event):
        """Handle plugin selection change"""
        selection = self.plugins_tree.selection()
        if not selection:
            self.enable_button.config(state='disabled')
            self.disable_button.config(state='disabled')
            self.settings_button.config(state='disabled')
            return
        
        item = selection[0]
        plugin_name = self.plugins_tree.item(item, 'tags')[0]
        plugin_info = self.plugin_manager.plugins.get(plugin_name)
        
        if plugin_info:
            # Update action buttons
            if plugin_info['enabled']:
                self.enable_button.config(state='disabled')
                self.disable_button.config(state='normal')
            else:
                self.enable_button.config(state='normal')
                self.disable_button.config(state='disabled')
            
            self.settings_button.config(state='normal')
            
            # Update info text
            plugin_class = plugin_info['class']
            plugin_instance = plugin_class(self)
            
            info_text = f"Name: {plugin_instance.name}\n"
            info_text += f"Version: {plugin_instance.version}\n"
            info_text += f"Description: {plugin_instance.description}\n"
            info_text += f"File: {plugin_info['file'].name}\n"
            info_text += f"Status: {'Enabled' if plugin_info['enabled'] else 'Disabled'}"
            
            self.plugin_info_text.config(state=tk.NORMAL)
            self.plugin_info_text.delete(1.0, tk.END)
            self.plugin_info_text.insert(1.0, info_text)
            self.plugin_info_text.config(state=tk.DISABLED)

    def enable_selected_plugin(self):
        """Enable the selected plugin"""
        selection = self.plugins_tree.selection()
        if selection:
            item = selection[0]
            plugin_name = self.plugins_tree.item(item, 'tags')[0]
            if self.plugin_manager.load_plugin(plugin_name):
                self.refresh_plugins_list()

    def disable_selected_plugin(self):
        """Disable the selected plugin"""
        selection = self.plugins_tree.selection()
        if selection:
            item = selection[0]
            plugin_name = self.plugins_tree.item(item, 'tags')[0]
            if self.plugin_manager.unload_plugin(plugin_name):
                self.refresh_plugins_list()

    def show_plugin_settings(self):
        """Show settings for selected plugin"""
        selection = self.plugins_tree.selection()
        if selection:
            item = selection[0]
            plugin_name = self.plugins_tree.item(item, 'tags')[0]
            plugin_instance = self.plugin_manager.loaded_plugins.get(plugin_name)
            
            if plugin_instance:
                settings_widget = plugin_instance.get_settings_widget(self.plugins_tab)
                if settings_widget:
                    # Create settings dialog
                    root_window = self.get_root_window()
                    settings_window = tk.Toplevel(root_window)
                    settings_window.title(f"Settings - {plugin_instance.name}")
                    settings_window.geometry("400x300")
                    settings_window.transient(root_window)
                    
                    settings_widget(settings_window).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                else:
                    self.messages(2, 3, "This plugin has no settings")

    def open_plugins_folder(self):
        """Open the plugins folder in file explorer"""
        try:
            os.startfile(str(self.plugin_manager.plugins_dir))  # Windows
        except:
            try:
                import subprocess
                subprocess.run(['open', str(self.plugin_manager.plugins_dir)])  # macOS
            except:
                try:
                    subprocess.run(['xdg-open', str(self.plugin_manager.plugins_dir)])  # Linux
                except:
                    self.messages(2, 3, "Could not open plugins folder")

    def reload_plugins(self):
        """Reload all plugins"""
        # Unload all currently loaded plugins
        for plugin_name in list(self.plugin_manager.loaded_plugins.keys()):
            self.plugin_manager.unload_plugin(plugin_name)
        
        # Rediscover and reload enabled plugins
        self.discover_plugins()
        self.messages(2, 9, "All plugins reloaded")

    # *************************************************************************
    # *************************** Button Actions*******************************
    # *************************************************************************

    def change_color(self,wich):
        colors = askcolor(title="Tkinter Color Chooser")
        match wich:
            case "fg":
                self.fg_color.set(colors[1])
            case "bg":
                self.bg_color.set(colors[1])
            case "advanced_fg":
                self.advanced_fg_color.set(colors[1])
            case "advanced_bg":
                self.advanced_bg_color.set(colors[1])

        print(f"Colors {wich}{colors}{colors[1]}")
    
    def clear_display(self):
        """Clear the log display area."""
        self.log_text.delete(1.0, tk.END)

    def search_log(self):
        """Search for text in the log display and highlight matches"""
        search_text = self.search_var.get().strip()
        if not search_text:
            self.clear_search()
            return

        # Remove previous search highlights
        self.log_text.tag_remove("search_highlight", "1.0", tk.END)
        self.log_text.tag_remove("search_current", "1.0", tk.END)
    
        # Reset search state
        self.search_matches = []
        self.current_match_index = -1

        # Search for matches (case-insensitive)
        content = self.log_text.get("1.0", tk.END).lower()
        search_lower = search_text.lower()
    
        start_pos = "1.0"
        while True:
            start_pos = self.log_text.search(search_text, start_pos, tk.END, nocase=1)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(search_text)}c"

            # Add to matches list
            self.search_matches.append(start_pos)

            # Apply highlight tag
            self.log_text.tag_add("search_highlight", start_pos, end_pos)
        
            start_pos = end_pos

        # Update UI based on results
        match_count = len(self.search_matches)
        if match_count > 0:
            self.messages(2, 9, f"Found {match_count} match(es)")
            self.prev_button.config(state="normal")
            self.next_button.config(state="normal")
            self.jump_to_match(0)  # Jump to first match
        else:
            self.messages(2, 3, "No matches found")
            self.prev_button.config(state="disabled")
            self.next_button.config(state="disabled")

    def search_next(self):
        """Jump to the next search match"""
        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        self.jump_to_match(self.current_match_index)

    def search_previous(self):
        """Jump to the previous search match"""
        if not self.search_matches:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        self.jump_to_match(self.current_match_index)

    def jump_to_match(self, index):
        """Jump to a specific match and highlight it"""
        if not self.search_matches or index < 0 or index >= len(self.search_matches):
            return
        
        # Remove current match highlighting
        self.log_text.tag_remove("search_current", "1.0", tk.END)
    
        # Get match position
        match_pos = self.search_matches[index]
        end_pos = f"{match_pos}+{len(self.search_var.get())}c"
    
        # Highlight current match
        self.log_text.tag_add("search_current", match_pos, end_pos)
    
        # Scroll to make the match visible
        self.log_text.see(match_pos)
    
        # Update status
        self.current_match_index = index
        self.messages(2, 2, f"Match {index + 1} of {len(self.search_matches)}")

    def clear_search(self):
        """Clear search highlights and reset search state"""
        self.log_text.tag_remove("search_highlight", "1.0", tk.END)
        self.log_text.tag_remove("search_current", "1.0", tk.END)
        self.search_var.set("")
        self.search_matches = []
        self.current_match_index = -1
        self.prev_button.config(state="disabled")
        self.next_button.config(state="disabled")
        self.messages(2, 2, "Search cleared")
    
    # ****************************************************************************
    # *************************** Filter Actions**********************************
    # ****************************************************************************

    def on_filter_select(self, event):
        """When a filter is selected from the listbox, load its data into the form."""
        selection = self.filter_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        # Get the filter key from the index
        filter_keys = list(self.filters.keys())
        if index >= len(filter_keys):
            return
        
        filter_key = filter_keys[index]
        filter_data = self.filters[filter_key]
        
        # Store the current edit filter key
        self.current_edit_filter_key = filter_key
        
        # Load the filter data into the form
        self.filter_string.set(filter_data['pattern'])
        self.filter_regex_var.set(filter_data.get('is_regex', False))
        self.fg_color.set(filter_data['fg_color'])
        self.bg_color.set(filter_data['bg_color'])
        self.filter_action_var.set(filter_data['action'])
        
        # For the action modifier, we need to set the modifier and also handle the voice if TTS
        action_modifier = filter_data.get('action_modifier', '')
        self.filter_action_modifier.set(action_modifier)
        
        # If the action is TTS, we also have a voice_id, so we need to set the voice combobox
        if filter_data['action'] == 'tts':
            voice_id = filter_data.get('voice_id')
            if voice_id:
                # Find the voice name by id and set the combobox
                for voice_info in self.available_voices:
                    if voice_info['id'] == voice_id:
                        self.voice_combobox.set(voice_info['name'])
                        break
            else:
                self.voice_combobox.set('')
        else:
            self.voice_combobox.set('')
        
        # Trigger the action changed to update the UI
        self.on_action_changed()
        
        # Enable the update button
        self.update_filter_btn.config(state="normal")

    def update_enhanced_filter(self):
        """Update the currently selected filter with the form data."""
        if not self.current_edit_filter_key:
            self.messages(2, 3, "No filter selected for editing")
            return

        # Get the current form data
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()

        if not filter_pattern:
            self.messages(2, 3, "Filter pattern cannot be empty")
            return

        # Create the new filter key from the current form data
        new_filter_key = f"{filter_pattern}|{action}|{action_modifier}"

        # Prepare filter data
        filter_data = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }

        # Add voice ID for TTS actions
        if action == "tts":
            voice_id = self.get_selected_voice_id()
            if voice_id:
                filter_data['voice_id'] = voice_id

        # Remove the old filter (by the old key)
        old_filter_key = self.current_edit_filter_key
        if old_filter_key in self.filters:
            del self.filters[old_filter_key]

        # Remove the old filter from the listbox
        # We don't know the index of the old one, so we will refresh the entire listbox
        self.filter_listbox.delete(0, tk.END)
        for key, data in self.filters.items():
            action_display = data['action'] if data['action'] != "none" else "color only"
            modifier_display = f" ({data['action_modifier']})" if data.get('action_modifier') else ""
            if data['action'] == 'tts' and data.get('voice_id'):
                voice_name = self.get_voice_name_by_id(data['voice_id'])
                modifier_display += f" [Voice: {voice_name}]"
            display_text = f"{data['pattern']} → {action_display}{modifier_display}"
            self.filter_listbox.insert(tk.END, display_text)

        # Now add the new filter
        self.filters[new_filter_key] = filter_data

        # Also add the new filter to the listbox (we just refreshed, so we can add the new one)
        action_display = action if action != "none" else "color only"
        modifier_display = f" ({action_modifier})" if action_modifier else ""
        if action == "tts" and voice_id:
            voice_name = self.get_voice_name_by_id(voice_id)
            modifier_display += f" [Voice: {voice_name}]"
        display_text = f"{filter_pattern} → {action_display}{modifier_display}"
        self.filter_listbox.insert(tk.END, display_text)

        # Update the text widget tags: remove the old tag and add the new one
        self.log_text.tag_delete(old_filter_key)
        self.log_text.tag_configure(new_filter_key, foreground=fg, background=bg)

        # Save the filters to disk
        self.save_filters()

        # Clear the form and reset the edit state
        self.clear_filter_form()
        self.current_edit_filter_key = None
        self.update_filter_btn.config(state="disabled")

        self.messages(2, 9, "Filter updated successfully")

    def clear_filter_form(self):
        """Clear the filter form fields."""
        self.filter_string.set("")
        self.filter_regex_var.set(False)
        self.fg_color.set("black")
        self.bg_color.set("yellow")
        self.filter_action_var.set("none")
        self.filter_action_modifier.set("")
        self.voice_combobox.set("")
        self.on_action_changed()

    def refresh_voices(self):
        """Populate the voice combobox with available voices"""
        self.available_voices = self.action_handler.get_available_voices()
        if not self.available_voices:
            self.messages(2, 3, "No TTS voices available")
            return
            # Create display names for the combobox
        voice_names = []
        for voice_info in self.available_voices:
            voice_names.append(voice_info['name'])

        # Update combobox values
        self.voice_combobox['values'] = voice_names

        # Auto-select first voice if available
        if voice_names:
            self.voice_combobox.set(voice_names[0])

    def get_selected_voice_id(self):
        """Get the voice ID of the currently selected voice from combobox"""
        selected_name = self.voice_combobox.get()
        self.messages(2,2,f"Voice selected: {selected_name}")
        if selected_name and self.available_voices:
            for voice_info in self.available_voices:
                if voice_info['name'] == selected_name:
                    return voice_info['id']
        return None

    def get_voice_name_by_id(self, voice_id):
        """Get voice display name by voice ID"""
        for voice_info in self.available_voices:
            if voice_info['id'] == voice_id:
                return voice_info['name']
        return "Unknown Voice"

    def test_selected_voice(self):
        """Test the selected voice with sample text"""
        voice_id = self.get_selected_voice_id()
        if not self.action_handler.tts_engine:
            self.messages(2, 3, "TTS engine not initialized")
            return
        if voice_id and self.action_handler.tts_engine:
            # Use threading to prevent GUI freezing :cite[9]
            import threading
            def speak_test():
                try:
                    if self.action_handler.tts_engine:
                        self.action_handler.tts_engine.startLoop(False)
                        if self.action_handler.tts_engine._inLoop:
                            self.action_handler.tts_engine.endLoop()
                        self.original_voice = self.action_handler.tts_engine.getProperty('voice')
                        self.action_handler.tts_engine.setProperty('voice', voice_id)
                        self.action_handler.tts_engine.say("This is a test of the selected voice")
                        self.action_handler.tts_engine.runAndWait()                 
                        self.action_handler.tts_engine.setProperty('voice', self.original_voice)
                except Exception as e:
                    self.messages(2,3,f"TTS: {e} voice: {voice_id}")
            thread = threading.Thread(target=speak_test)
            thread.daemon = True
            thread.start()

    def on_action_changed(self, event=None):
        """Show/hide relevant controls based on selected action"""
        action = self.filter_action_var.get()
        
        # Hide sound, tts and other by default
        self.browse_sound_btn.grid_remove()
        self.voice_combobox.grid_remove()
        self.test_voice_btn.grid_remove()
        
        # Clear modifier field
        self.filter_action_modifier.set("")
        
        # Show sound browser only for sound action
        if action == "sound":
            self.browse_sound_btn.grid()
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Click 'Browse Sound' or enter file path")
        elif action == "tts":
            self.voice_combobox.grid()  # Show voice selection for TTS
            self.test_voice_btn.grid()
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Text to speak when filter matches")
        elif action == "notification":
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Notification message")
        elif action == "dialog":
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Dialog message")
        elif action == "skip":
            self.action_modifier_entry.config(state="disabled")
            self.filter_action_modifier.set("")  # No modifier needed for skip
        else:  # "none"
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("")  # No action modifier
    
    def browse_sound_file(self):
        """Browse for sound files"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title="Select Sound File",
            initialdir=initial_dir,
            filetypes=[("Sound files", "*.wav *.mp3 *.ogg"), ("All files", "*.*")]
        )
        if filename:
            self.filter_action_modifier.set(filename)

    def edit_selected_filter(self):
        """Load the selected filter into the form for editing"""
        try:
            selection = self.filter_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No filter selected for editing")
                return
            
            index = selection[0]
            filter_keys = list(self.filters.keys())
            if index >= len(filter_keys):
                self.messages(2, 3, "Invalid filter selection")
                return
            
            # Get the filter key and data
            self.original_filter_key = filter_keys[index]
            filter_data = self.filters[self.original_filter_key]
        
            # Store the key we're editing
            self.editing_filter_key = self.original_filter_key
        
            # Load filter data into form fields
            self.filter_string.set(filter_data['pattern'])
            self.filter_regex_var.set(filter_data.get('is_regex', False))
            self.fg_color.set(filter_data['fg_color'])
            self.bg_color.set(filter_data['bg_color'])
            self.filter_action_var.set(filter_data['action'])
            self.on_action_changed()
            # Refresh UI based on action type
            action_modifier = filter_data.get('action_modifier', '')
            print(f"action_modifier {filter_data.get('action_modifier', '')}")
            self.filter_action_modifier.set(filter_data['action_modifier'])
            # Load voice if it's a TTS filter
            if filter_data['action'] == 'tts' and 'voice_id' in filter_data:
                voice_id = filter_data['voice_id']
                # Find and select the voice in combobox
                for voice_info in self.available_voices:
                    if voice_info['id'] == voice_id:
                        self.voice_combobox.set(voice_info['name'])
                        break
        
            # Update UI state
            self.update_filter_btn.config(state="normal")
            self.edit_filter_btn.config(state="disabled")
        
            self.messages(2, 2, f"Editing filter: {filter_data['pattern']}")
        
        except Exception as e:
            self.messages(2, 3, f"Error loading filter for editing: {e}")

    def update_filter(self):
        """Update the currently edited filter with form values"""
        if not self.editing_filter_key:
            self.messages(2, 3, "No filter being edited")
            return
        
        # Get current form values
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()
    
        if not filter_pattern:
            self.messages(2, 3, "Filter pattern cannot be empty")
            return
    
        # Create new filter key (might be different if pattern changed)
        new_filter_key = f"{filter_pattern}|{action}|{action_modifier}"
    
        # Prepare updated filter data
        updated_filter_data = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }
    
        # Add voice ID for TTS actions
        if action == "tts":
            voice_id = self.get_selected_voice_id()
            if voice_id:
                updated_filter_data['voice_id'] = voice_id
    
        # Remove the old filter and add the updated one
        if self.original_filter_key in self.filters:
            del self.filters[self.original_filter_key]
    
        # Add the updated filter (with potentially new key)
        self.filters[new_filter_key] = updated_filter_data
    
        # Refresh the listbox display
        self.refresh_filter_listbox()
    
        # Update text widget tags
        self.log_text.tag_delete(self.original_filter_key)  # Remove old tag
        self.log_text.tag_configure(new_filter_key, foreground=fg, background=bg)
    
        # Save to file
        self.save_filters(None)
    
        # Reset editing state
        self.cancel_edit()
    
        self.messages(2, 9, f"Filter updated: {filter_pattern}")

    def cancel_edit(self):
        """Cancel the current edit operation and clear the form"""
        self.editing_filter_key = None
        self.original_filter_key = None
    
        # Clear form fields
        self.filter_string.set("")
        self.filter_regex_var.set(False)
        self.fg_color.set("black")
        self.bg_color.set("yellow")
        self.filter_action_var.set("none")
        self.filter_action_modifier.set("")
        self.voice_combobox.set("")
    
        # Reset UI state
        self.on_action_changed()
        self.update_filter_btn.config(state="disabled")
        self.edit_filter_btn.config(state="normal")
    
        # Clear listbox selection
        self.filter_listbox.selection_clear(0, tk.END)
    
        self.messages(2, 2, "Edit cancelled")
    
    def add_enhanced_filter(self):
        # If we're in edit mode, cancel it first
        if self.editing_filter_key:
            self.cancel_edit()    
        """Add a new enhanced filter with actions"""
        self.current_edit_filter_key = None
        self.update_filter_btn.config(state="disabled")
        
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()
    
        if not filter_pattern:
            self.messages(2,3,f"Filter pattern cannot be empty")
            return
    
        # Create unique key for the filter
        filter_key = f"{filter_pattern}|{action}|{action_modifier}"
    
        # Prepare filter data
        filter_data = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }
    
        # Add voice ID for TTS actions
        if action == "tts":
            voice_id = self.get_selected_voice_id()
            if voice_id:
                filter_data['voice_id'] = voice_id
    
        # Store the enhanced filter
        self.filters[filter_key] = filter_data
    
        # Update the listbox display
        action_display = action if action != "none" else "color only"
        modifier_display = f" ({action_modifier})" if action_modifier else ""
    
        # Add voice info to display for TTS filters
        if action == "tts" and voice_id:
            voice_name = self.voice_combobox.get()
            modifier_display += f" [Voice: {voice_name}]"
    
        display_text = f"{filter_pattern} → {action_display}{modifier_display}"
        self.filter_listbox.insert(tk.END, display_text)
    
        # Configure text widget tag for coloring
        self.log_text.tag_configure(filter_key, foreground=fg, background=bg)
    
        # Save filters to file
        self.save_filters(False)
    
        # Clear input fields
        self.filter_string.set("")
        self.filter_action_var.set("none")
        self.filter_action_modifier.set("")
        self.on_action_changed()  # Reset UI state
    
        self.messages(2,9,f"Filter added: {filter_pattern}")
 
    def remove_enhanced_filter(self):
        """Remove the selected enhanced filter"""
        try:
            selection = self.filter_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No filter selected")
                return
                
            index = selection[0]
            filter_key = list(self.filters.keys())[index]
            
            # Remove from filters dict
            del self.filters[filter_key]
            
            # Remove from listbox
            self.filter_listbox.delete(index)
            
            # Remove tag from text widget
            self.log_text.tag_delete(filter_key)
            
            # Save changes
            self.save_filters(False)
            self.messages(2,9,"Filter removed")

        except IndexError:
            self.messages(2,3,"No filter selected or invalid selection")
        except Exception as e:
            self.messages(2,3,f"Error removing filter: {e}")

    def on_filter_selection_change(self, event):
        """Enable edit button when a filter is selected"""
        selection = self.filter_listbox.curselection()
        if selection and not self.editing_filter_key:
            self.edit_filter_btn.config(state="normal")
        else:
            self.edit_filter_btn.config(state="disabled")

    def refresh_filter_listbox(self):
        """Refresh the filter listbox with current filters"""
        self.filter_listbox.delete(0, tk.END)

        for filter_key, filter_data in self.filters.items():
            action_display = filter_data['action'] if filter_data['action'] != "none" else "color only"
            modifier_display = f" ({filter_data['action_modifier']})" if filter_data.get('action_modifier') else ""

            # Add voice info for TTS filters
            if filter_data['action'] == "tts" and filter_data.get('voice_id'):
                voice_name = self.get_voice_name_by_id(filter_data['voice_id'])
                modifier_display += f" [Voice: {voice_name}]"

            display_text = f"{filter_data['pattern']} → {action_display}{modifier_display}"
            self.filter_listbox.insert(tk.END, display_text)

    def save_filters(self, dialog=False):
        """Save current filters to the configured filters file"""
        filters_file = self.filters_file_var.get()
        # If no filters file is configured but we want to save, use default
        if not filters_file and not dialog:
            self.messages(2, 3, "No filters file configured")
            return False
        if not filters_file:
            if dialog:
                # Let the save_json handle the dialog
                pass         
        try:
            filters_data = {
                "version": "1.1",
                "filters": list(self.filters.values())

            }
            # Update recent filters list
            self.save_json("simple", filters_file, filters_data, dialog)
            self.config_manager.update_recent_list("recent_filters", filters_file)
            self.update_recent_combos()          
            self.messages(2, 9, "Filters saved successfully")
            
            return True
        
        except Exception as e:
            self.messages(2, 3, f"Error saving filters: {e}")
            return False

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.messages(2, 9, "Regex copied to clipboard")
        except Exception as e:
            self.messages(2, 3, f"Failed to copy to clipboard: {e}")

    # ****************************************************************************
    # *****************Advanced   Filter Actions**********************************
    # ****************************************************************************

    def add_regex_field(self, field_data=None):
        """Add a new regex field row - FIXED to properly load saved data"""
        if len(self.regex_fields) >= self.max_fields:
            self.messages(2, 3, f"Maximum {self.max_fields} fields allowed")
            return

        field_frame = ttk.Frame(self.fields_scrollable_frame)
        field_frame.pack(fill=tk.X, pady=2)

        # Field number label
        field_num = len(self.regex_fields) + 1
        ttk.Label(field_frame, text=f"Field {field_num}:").pack(side=tk.LEFT, padx=(0, 5))

        # Input field - FIXED: Use field_data if provided
        field_text = tk.StringVar(value=field_data.get("text", "") if field_data else "")
        field_entry = ttk.Entry(field_frame, textvariable=field_text, width=25)
        field_entry.pack(side=tk.LEFT, padx=(0, 5))

        # Modifier combobox - FIXED: Use field_data if provided
        modifier_var = tk.StringVar(value=field_data.get("modifier", "as_string") if field_data else "as_string")
        modifier_combo = ttk.Combobox(field_frame, textvariable=modifier_var,
                                values=["as_string", "as_word", "as_regex", "predefined"],
                                state="readonly", width=12)
        modifier_combo.pack(side=tk.LEFT, padx=(0, 5))
        modifier_combo.bind('<<ComboboxSelected>>', lambda e, f=field_frame: self.on_modifier_changed(f))

        # Predefined patterns combobox - FIXED: Use field_data if provided
        predefined_var = tk.StringVar(value=field_data.get("predefined_type", "") if field_data else "")
        predefined_combo = ttk.Combobox(field_frame, textvariable=predefined_var,
                                values=list(self.predefined_patterns.keys()),
                                state="readonly", width=15)
        predefined_combo.pack(side=tk.LEFT, padx=(0, 5))
        predefined_combo.pack_forget()

        # Predefined pattern insert button
        insert_btn = ttk.Button(field_frame, text="Insert", 
                        command=lambda: self.insert_predefined_pattern(field_entry, predefined_var))
        insert_btn.pack(side=tk.LEFT, padx=(0, 5))
        insert_btn.pack_forget()

        # Scope combobox (for between fields) - FIXED: Use field_data if provided
        if len(self.regex_fields) > 0:  # Only add scope for fields after the first one
            scope_var = tk.StringVar(value=field_data.get("scope", "anything_between") if field_data else "anything_between")
            scope_combo = ttk.Combobox(field_frame, textvariable=scope_var,
                                values=["anything_between", "immediate_after", "word_boundary_between", 
                                        "whitespace_between", "specific_separator"],
                                state="readonly", width=18)
            scope_combo.pack(side=tk.LEFT, padx=(20, 5))
        
            # Store scope reference
            field_frame.scope_var = scope_var

            # Separator entry for specific_separator scope - FIXED: Use field_data if provided
            separator_var = tk.StringVar(value=field_data.get("separator", "") if field_data else "")
            separator_entry = ttk.Entry(field_frame, textvariable=separator_var, width=8)
            separator_entry.pack(side=tk.LEFT, padx=(5, 0))
            separator_entry.pack_forget()

            field_frame.separator_var = separator_var
            field_frame.separator_entry = separator_entry

            # Show/hide separator based on scope
            scope_combo.bind('<<ComboboxSelected>>', 
                        lambda e, f=field_frame: self.on_scope_changed(f))

            # Set initial scope state
            self.on_scope_changed(field_frame)
        else:
            field_frame.scope_var = None

        # Remove button
        remove_btn = ttk.Button(field_frame, text="Remove", 
                        command=lambda: self.remove_regex_field(field_frame))
        remove_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Store references
        field_frame.field_text = field_text
        field_frame.modifier_var = modifier_var
        field_frame.predefined_var = predefined_var
        field_frame.predefined_combo = predefined_combo
        field_frame.insert_btn = insert_btn

        # Set initial modifier state
        self.on_modifier_changed(field_frame)

        # Add to tracking list
        self.regex_fields.append(field_frame)

        # Update regex display
        self.update_generated_regex()

        # Update scroll region
        self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all"))

    def remove_regex_field(self, field_frame):
        """Remove a regex field"""
        if field_frame in self.regex_fields:
            self.regex_fields.remove(field_frame)
            field_frame.destroy()
            self.renumber_fields()
            self.update_generated_regex()

    def renumber_fields(self):
        """Renumber fields after removal"""
        for i, field_frame in enumerate(self.regex_fields):
            # Update the field number label
            for widget in field_frame.winfo_children():
                if isinstance(widget, ttk.Label) and "Field" in widget.cget("text"):
                    widget.config(text=f"Field {i + 1}:")
                    break

    def on_modifier_changed(self, field_frame):
        """Show/hide predefined pattern controls based on modifier"""
        modifier = field_frame.modifier_var.get()
    
        if modifier == "predefined":
            field_frame.predefined_combo.pack(side=tk.LEFT, padx=(0, 5))
            field_frame.insert_btn.pack(side=tk.LEFT, padx=(0, 5))
        else:
            field_frame.predefined_combo.pack_forget()
            field_frame.insert_btn.pack_forget()
    
        # Update regex when modifier changes
        self.update_generated_regex()

    def insert_predefined_pattern(self, field_entry, predefined_var):
        """Insert predefined pattern into field"""
        pattern_type = predefined_var.get()
        if pattern_type in self.predefined_patterns:
            field_entry.delete(0, tk.END)
            field_entry.insert(0, self.predefined_patterns[pattern_type])
            self.update_generated_regex()

    def update_generated_regex(self):
        """Generate the final regex from all fields with positional enforcement"""
        if not self.regex_fields:
            self.generated_regex.set("")
            return
    
        regex_parts = []
        first_field = True
    
        for i, field_frame in enumerate(self.regex_fields):
            field_text = field_frame.field_text.get().strip()
            modifier = field_frame.modifier_var.get()
        
            if not field_text:
                continue
        
            processed_field = self.apply_modifier(field_text, modifier)
        
            if first_field:
                regex_parts.append(processed_field)
                first_field = False
            else:
                scope = field_frame.scope_var.get() if field_frame.scope_var else "anything_between"
                previous_pattern = regex_parts[-1]
                combined_pattern = self.apply_positional_scope(previous_pattern, processed_field, scope)
                regex_parts[-1] = combined_pattern
    
        # Add final .* to match anything after the last field
        if regex_parts:
            final_regex = regex_parts[-1] + ".*"
            self.generated_regex.set(final_regex)
        else:
            self.generated_regex.set("")

    def apply_positional_scope(self, previous_pattern, current_pattern, scope):
        """Apply positional scope between fields to enforce order"""
        if scope == "anything_between":
            # Field1 followed by anything, then Field2 (your example pattern)
            return f"{previous_pattern}.*{current_pattern}"
        elif scope == "immediate_after":
            # Field2 immediately after Field1
            return f"{previous_pattern}{current_pattern}"
        elif scope == "word_boundary_between":
            # Field1 followed by Field2 with word boundaries in between
            return f"{previous_pattern}\\b.*\\b{current_pattern}"
        elif scope == "whitespace_between":
            # Field1 followed by Field2 with whitespace in between
            return f"{previous_pattern}\\s+{current_pattern}"
        elif scope == "specific_separator":
            # Field1 followed by Field2 with a specific separator
            # We'll need to add a separator input field for this
            separator = getattr(self, 'separator_var', tk.StringVar(value="")).get()
            return f"{previous_pattern}{re.escape(separator)}{current_pattern}"
        
        return f"{previous_pattern}.*{current_pattern}"  # Default

    def on_scope_changed(self, field_frame):
        """Show/hide separator entry based on scope selection"""
        scope = field_frame.scope_var.get()
    
        if scope == "specific_separator":
            field_frame.separator_entry.pack(side=tk.LEFT, padx=(5, 0))
        else:
            field_frame.separator_entry.pack_forget()
    
        # Update regex when scope changes
        self.update_generated_regex()

    def apply_modifier(self, text, modifier):
        """Apply modifier to field text to create regex pattern, now with multi-term support"""
        if not text:
            return ""

        try:
            if modifier == "as_string":
                # Check if text contains commas for multiple terms
                if ',' in text:
                    terms = [term.strip() for term in text.split(',') if term.strip()]
                    if terms:
                        escaped_terms = [re.escape(term) for term in terms]
                        return '(' + '|'.join(escaped_terms) + ')'
                # Single term (original behavior)
                return re.escape(text)

            elif modifier == "as_word":
                # Check if text contains commas for multiple terms
                if ',' in text:
                    terms = [term.strip() for term in text.split(',') if term.strip()]
                    if terms:
                        escaped_terms = [re.escape(term) for term in terms]
                        return r'\b(' + '|'.join(escaped_terms) + r')\b'
                # Single term (original behavior)
                return r'\b' + re.escape(text) + r'\b'

            elif modifier == "as_word_start":
                # Word boundary at start only (single term only for now)
                return r'\b' + re.escape(text)

            elif modifier == "as_word_end":
                # Word boundary at end only (single term only for now)  
                return re.escape(text) + r'\b'

            elif modifier == "as_regex":
                # Use as raw regex - validate it first
                try:
                    re.compile(text)
                    return text
                except re.error:
                    # Fall back to escaped version if invalid regex
                    return re.escape(text)

            elif modifier == "predefined":
                # Already a regex pattern from predefined
                try:
                    re.compile(text)
                    return text
                except re.error:
                    return re.escape(text)

            else:
                # Default to string escaping
                return re.escape(text)

        except Exception as e:
            self.messages(2, 3, f"Error applying modifier '{modifier}' to '{text}': {e}")
            return re.escape(text)  # Fallback

    def apply_scope(self, current_pattern, scope, previous_pattern):
        """Apply scope between fields"""
        if scope == "search_all":
            # Just concatenate (implicit AND)
            return current_pattern
        elif scope == "search_between":
            # Match anything between previous and current
            return r".*?" + current_pattern
        elif scope == "search_after":
            # Match current pattern after previous
            return r"(?<=" + previous_pattern + r")" + current_pattern
        elif scope == "search_before":
            # Match current pattern before previous
            return current_pattern + r"(?=" + previous_pattern + r")"
        return current_pattern

    def store_advanced_filter(self):
        """Store the current advanced filter with TTS voice support"""
        filter_name = self.advanced_filter_name.get().strip()
        if not filter_name:
            self.messages(2, 3, "Advanced filter name cannot be empty")
            return

        # Collect field data
        fields_data = []
        for field_frame in self.regex_fields:
            field_data = {
                "text": field_frame.field_text.get(),
                "modifier": field_frame.modifier_var.get(),
                "predefined_type": field_frame.predefined_var.get(),
            }

            if field_frame.scope_var:
                field_data["scope"] = field_frame.scope_var.get()
                if hasattr(field_frame, 'separator_var'):
                    field_data["separator"] = field_frame.separator_var.get()

            fields_data.append(field_data)

        # Build actions with TTS voice support
        actions = {
            "bg_color": self.advanced_bg_color.get(),
            "fg_color": self.advanced_fg_color.get(),
            "action": self.advanced_action_var.get(),
            "action_modifier": self.advanced_action_modifier.get(),
        }

        # Add TTS voice ID if available and action is TTS
        if self.advanced_action_var.get() == "tts" and hasattr(self, 'advanced_voice_combobox'):
            selected_voice_name = self.advanced_voice_combobox.get()
            if selected_voice_name and hasattr(self, 'advanced_available_voices'):
                for voice_info in self.advanced_available_voices:
                    if voice_info['name'] == selected_voice_name:
                        actions["voice_id"] = voice_info['id']
                        actions["voice_name"] = voice_info['name']
                        break

        # Create filter
        filter_key = f"advanced_{filter_name}"
        self.advanced_filters[filter_key] = {
            "name": filter_name,
            "enabled": self.advanced_filter_enabled.get(),
            "fields": fields_data,
            "generated_regex": self.generated_regex.get(),
            "actions": actions
        }

        self.refresh_advanced_filters_listbox()
        self.save_advanced_filters(False)
        self.messages(2, 9, f"Advanced filter stored: {filter_name}")

    def save_advanced_filters(self, dialog=False):
        """Save advanced filters to the configured file - FIXED VERSION"""
        advanced_filters_file = self.advanced_filters_file_var.get()

        # If no file is set but we're not using dialog, try to get from config
        if not advanced_filters_file and not dialog:
            advanced_filters_file = self.config_manager.get("advanced_filters_file", "")
            if advanced_filters_file:
                self.advanced_filters_file_var.set(advanced_filters_file)

        # If still no file and we're not using dialog, show error
        if not advanced_filters_file:
            if dialog:
                # Let the save_json handle the dialog
                pass
            else:
                self.messages(2, 3, "No advanced filters file configured")
                return False

        try:
            filters_data = {
                "version": "1.0",
                "advanced_filters": self.advanced_filters  # Direct assignment
            }

            print(f"DEBUG: Saving {len(self.advanced_filters)} advanced filters")  # Debug

            # Use the existing save_json method
            return self.save_json("advanced", advanced_filters_file, filters_data, dialog)

        except Exception as e:
            self.messages(2, 3, f"Error saving advanced filters: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_advanced_filters_auto(self):
        """Load advanced filters from the configured file - FIXED VERSION"""
        advanced_filters_file = self.advanced_filters_file_var.get()
        if not advanced_filters_file:
            return
            
        try:
            filters_path = Path(advanced_filters_file)
            if not filters_path.exists() or not filters_path.is_file():
                print(f"DEBUG: Advanced filters file doesn't exist or is not a file: {advanced_filters_file}")
                return
    
            with open(filters_path, 'r', encoding='utf-8') as f:
                filters_data = json.load(f)
    
            # Clear current advanced filters
            self.advanced_filters.clear()
        
            # Load new advanced filters - FIXED: Proper access to nested structure
            advanced_filters_data = filters_data.get("advanced_filters", {})
            print(f"DEBUG: Found {len(advanced_filters_data)} advanced filters in file")
    
            for filter_key, filter_data in advanced_filters_data.items():
                self.advanced_filters[filter_key] = filter_data
                print(f"DEBUG: Loaded filter: {filter_data.get('name', 'Unnamed')}")
    
            # Refresh listbox
            self.refresh_advanced_filters_listbox()
    
            # Update recent filters list
            self.config_manager.update_recent_list("recent_advanced_filters", str(filters_path))
            self.update_recent_combos()
    
            self.messages(2, 9, f"Loaded {len(self.advanced_filters)} advanced filters")
    
        except Exception as e:
            print(f"Error loading advanced filters: {e}")

    def load_advanced_filter(self):
        """Load selected advanced filter into form with TTS voice support"""
        selection = self.advanced_filters_listbox.curselection()
        if not selection:
            self.messages(2, 3, "No advanced filter selected")
            return

        index = selection[0]
        filter_keys = list(self.advanced_filters.keys())
        if index >= len(filter_keys):
            self.messages(2, 3, "Invalid filter selection")
            return

        filter_key = filter_keys[index]
        filter_data = self.advanced_filters[filter_key]

        # Clear current form
        self.clear_advanced_form()

        # Load basic info
        self.advanced_filter_name.set(filter_data.get("name", ""))
        self.advanced_filter_enabled.set(filter_data.get("enabled", True))

        # Load fields
        fields_data = filter_data.get("fields", [])
        self.clear_all_regex_fields()
    
        for field_data in fields_data:
            self.add_regex_field(field_data)

        # Load actions with TTS voice support
        actions = filter_data.get("actions", {})
        self.advanced_bg_color.set(actions.get("bg_color", "yellow"))
        self.advanced_fg_color.set(actions.get("fg_color", "black"))
        self.advanced_action_var.set(actions.get("action", "none"))
        self.advanced_action_modifier.set(actions.get("action_modifier", ""))

        # Load TTS voice if available
        if actions.get("action") == "tts" and "voice_id" in actions:
            voice_id = actions["voice_id"]
            # Set the voice in the combobox
            if hasattr(self, 'advanced_voice_combobox') and hasattr(self, 'advanced_available_voices'):
                for voice_info in self.advanced_available_voices:
                    if voice_info['id'] == voice_id:
                        self.advanced_voice_combobox.set(voice_info['name'])
                        break

        # Load generated regex
        if "generated_regex" in filter_data:
            self.generated_regex.set(filter_data["generated_regex"])

        # Update UI for action type
        self.on_advanced_action_changed()

        self.editing_advanced_filter_key = filter_key
        self.messages(2, 2, f"Editing advanced filter: {filter_data.get('name', 'Unnamed')}")

    def perform_test():
        text = test_text.get(1.0, tk.END).strip()
        try:
            matches = re.findall(regex_pattern, text)
            if matches:
                result_var.set(f"✓ Found {len(matches)} match(es)")
                result_label.config(foreground="green")
            else:
                result_var.set("✗ No matches found")
                result_label.config(foreground="red")
        except re.error as e:
            result_var.set(f"✗ Regex error: {e}")
            result_label.config(foreground="red")
    
        ttk.Button(test_window, text="Test", command=perform_test).pack(pady=5)

    def clear_advanced_form(self):
        """Clear the advanced filter form - FIXED to properly reset state"""
        try:
            # Clear basic form fields
            self.advanced_filter_name.set("")
            self.advanced_filter_enabled.set(True)

            # Clear action fields
            self.advanced_fg_color.set("black")
            self.advanced_bg_color.set("yellow")
            self.advanced_action_var.set("none")
            self.advanced_action_modifier.set("")

            # Hide TTS voice selection
            if hasattr(self, 'advanced_voice_combobox'):
                self.advanced_voice_combobox.grid_remove()
                self.advanced_voice_combobox.set("")

            # Clear all regex fields
            self.clear_all_regex_fields()

            # Reset editing state
            self.editing_advanced_filter_key = None

            # Clear generated regex display
            self.generated_regex.set("")

            # Add one empty field to start fresh
            self.add_regex_field()

            # Reset UI state for actions
            self.on_advanced_action_changed()

            # Clear listbox selection
            if hasattr(self, 'advanced_filters_listbox'):
                self.advanced_filters_listbox.selection_clear(0, tk.END)

            self.messages(2, 2, "Advanced form cleared")

        except Exception as e:
            self.messages(2, 3, f"Error clearing advanced form: {e}")

    def clear_all_regex_fields(self):
        """Remove all regex field widgets from the form"""
        if hasattr(self, 'regex_fields'):
            # Destroy all field frames
            for field_frame in self.regex_fields:
                try:
                    field_frame.destroy()
                except:
                    pass  # Widget might already be destroyed
        
            # Clear the list
            self.regex_fields.clear()
    
        # Also clear the scrollable frame children
        if hasattr(self, 'fields_scrollable_frame'):
            for widget in self.fields_scrollable_frame.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
    
        # Update scroll region
        if hasattr(self, 'fields_canvas'):
            self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all"))

    def delete_advanced_filter(self):
        """Delete the selected advanced filter"""
        try:
            selection = self.advanced_filters_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No advanced filter selected for deletion")
                return
            
            index = selection[0]
            filter_keys = list(self.advanced_filters.keys())
            if index >= len(filter_keys):
                self.messages(2, 3, "Invalid filter selection")
                return
        
            filter_key = filter_keys[index]
            filter_name = self.advanced_filters[filter_key]["name"]
        
            # Confirm deletion
            confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the advanced filter '{filter_name}'?")
        
            if confirm:
                # Remove from dictionary
                del self.advanced_filters[filter_key]
                
                # Update listbox
                self.refresh_advanced_filters_listbox()
                
                # Save changes
                self.save_advanced_filters()
                
                # Clear form if we were editing this filter
                if self.editing_advanced_filter_key == filter_key:
                    self.clear_advanced_form()
            
                self.messages(2, 9, f"Advanced filter deleted: {filter_name}")
            
        except Exception as e:
            self.messages(2, 3, f"Error deleting advanced filter: {e}")

    def toggle_advanced_filter(self):
        """Toggle enabled/disabled state of selected advanced filter"""
        try:
            selection = self.advanced_filters_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No advanced filter selected")
                return
            
            index = selection[0]
            filter_keys = list(self.advanced_filters.keys())
            if index >= len(filter_keys):
                self.messages(2, 3, "Invalid filter selection")
                return
        
            filter_key = filter_keys[index]
            filter_data = self.advanced_filters[filter_key]
        
            # Toggle enabled state
            filter_data["enabled"] = not filter_data["enabled"]
            new_state = "enabled" if filter_data["enabled"] else "disabled"
        
            # Update listbox display
            self.refresh_advanced_filters_listbox()
        
            # Save changes
            self.save_advanced_filters()
        
            self.messages(2, 9, f"Advanced filter {new_state}: {filter_data['name']}")
        
        except Exception as e:
            self.messages(2, 3, f"Error toggling advanced filter: {e}")

    def refresh_advanced_filters_listbox(self):
        """Refresh the advanced filters listbox display - FIXED VERSION"""
        if not hasattr(self, 'advanced_filters_listbox'):
            return

        self.advanced_filters_listbox.delete(0, tk.END)

        for filter_key, filter_data in self.advanced_filters.items():
            status = "✓" if filter_data.get("enabled", True) else "✗"
            filter_name = filter_data.get("name", "Unnamed Filter")
            display_text = f"{status} {filter_name}"
            self.advanced_filters_listbox.insert(tk.END, display_text)

        print(f"DEBUG: Listbox refreshed with {len(self.advanced_filters)} filters")  # Debug

    def on_advanced_action_changed(self, event=None):
        """Show/hide relevant controls based on selected advanced action - IMPROVED"""
        action = self.advanced_action_var.get()

        # Hide TTS controls by default
        if hasattr(self, 'advanced_voice_combobox'):
            self.advanced_voice_combobox.grid_remove()

        # Show voice selection for TTS actions
        if action == "tts":
            if hasattr(self, 'advanced_voice_combobox'):
                self.advanced_voice_combobox.grid()
                # Load voices if not already loaded
                if not hasattr(self, 'advanced_available_voices') or not self.advanced_available_voices:
                    self.refresh_advanced_voices()

    def refresh_advanced_voices(self):
        """Refresh available voices for advanced filters with better error handling"""
        try:
            self.advanced_available_voices = self.action_handler.get_available_voices()
            if self.advanced_available_voices:
                voice_names = [voice['name'] for voice in self.advanced_available_voices]
                self.advanced_voice_combobox['values'] = voice_names
                # Don't auto-select, preserve current selection if any
            else:
                self.messages(2, 3, "No TTS voices available")
        except Exception as e:
            self.messages(2, 3, f"Error loading voices: {e}")

    def test_generated_regex(self):
        """Test the generated regex with sample input - COMPLETE IMPLEMENTATION"""
        regex_pattern = self.generated_regex.get()
        if not regex_pattern:
            self.messages(2, 3, "No regex generated to test")
            return

        # Create test dialog
        test_window = tk.Toplevel(self.root)
        test_window.title("Test Regex Pattern")
        test_window.geometry("600x400")
        test_window.transient(self.root)
        test_window.grab_set()

        # Main content frame
        main_frame = ttk.Frame(test_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Regex pattern display
        ttk.Label(main_frame, text="Regex Pattern to Test:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        pattern_frame = ttk.Frame(main_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 10))
    
        pattern_text = tk.Text(pattern_frame, height=2, wrap=tk.WORD, font=("Courier", 9))
        pattern_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        pattern_text.insert(1.0, regex_pattern)
        pattern_text.config(state=tk.DISABLED)  # Make it read-only
    
        # Test input area
        ttk.Label(main_frame, text="Enter text to test against the regex:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
    
        test_text = tk.Text(main_frame, height=8, wrap=tk.WORD)
        test_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
        # Add some sample text for quick testing
        sample_text = "This is sample text. You can enter your own text here to test the regex pattern.\nExample: This line contains uno and dos"
        test_text.insert(1.0, sample_text)

        # Results area
        result_frame = ttk.LabelFrame(main_frame, text="Test Results", padding="5")
        result_frame.pack(fill=tk.X, pady=(0, 10))

        self.test_result_var = tk.StringVar(value="Click 'Run Test' to see results")
        result_label = ttk.Label(result_frame, textvariable=self.test_result_var, wraplength=550)
        result_label.pack(fill=tk.X)

        # Match details
        self.match_details_var = tk.StringVar(value="")
        match_details_label = ttk.Label(result_frame, textvariable=self.match_details_var, 
                                    foreground="blue", wraplength=550)
        match_details_label.pack(fill=tk.X)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        def perform_test():
            """Execute the regex test and display results"""
            text = test_text.get(1.0, tk.END).strip()
            if not text:
                self.test_result_var.set("Please enter some text to test")
                result_label.config(foreground="red")
                return

            try:
                # Test the regex
                pattern = self.generated_regex.get()
                matches = list(re.finditer(pattern, text, re.MULTILINE | re.DOTALL))

                if matches:
                    # Show successful results
                    self.test_result_var.set(f"✓ SUCCESS: Found {len(matches)} match(es)")
                    result_label.config(foreground="green")
                
                    # Show match details
                    match_info = []
                    for i, match in enumerate(matches, 1):
                        match_text = match.group(0)
                        # Truncate long matches for display
                        if len(match_text) > 100:
                            match_text = match_text[:100] + "..."
                        match_info.append(f"Match {i}: '{match_text}' (position {match.start()}-{match.end()})")

                    self.match_details_var.set("\n".join(match_info))

                else:
                    # No matches found
                    self.test_result_var.set("✗ NO MATCHES: The regex pattern did not match any text")
                    result_label.config(foreground="red")
                    self.match_details_var.set("")

            except re.error as e:
                # Regex syntax error
                self.test_result_var.set(f"✗ REGEX ERROR: {e}")
                result_label.config(foreground="red")
                self.match_details_var.set("")
            except Exception as e:
                # Other errors
                self.test_result_var.set(f"✗ TEST ERROR: {e}")
                result_label.config(foreground="red")
                self.match_details_var.set("")

        def clear_input():
            """Clear the test input area"""
            test_text.delete(1.0, tk.END)

        def use_current_log_line():
            """Use the currently selected line from the log as test input"""
            try:
                # Try to get selected text from log display
                selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if selected_text:
                    test_text.delete(1.0, tk.END)
                    test_text.insert(1.0, selected_text)
                else:
                    # If no selection, get the last line from log
                    last_line = self.log_text.get("end-2l linestart", "end-1l lineend")
                    if last_line.strip():
                        test_text.delete(1.0, tk.END)
                        test_text.insert(1.0, last_line)
                    else:
                        self.messages(2, 3, "No text available in log")
            except tk.TclError:
                # No text selected
                self.messages(2, 3, "No text selected in log")


    # ****************************************************************************
    # *************************** Config Actions  ********************************
    # ****************************************************************************

    def browse_log_file(self):
        """Browse for log file and update last directory - UPDATED TO SYNC STATE"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title="Select Log File",
            initialdir=initial_dir
        )
        if filename:
            self.log_file_var.set(str(Path(filename)))
            self.config_manager.set("last_directory", str(Path(filename).parent))
            
            # SYNC STATE: Update config immediately when file is selected
            self.config_manager.set("log_file", str(Path(filename)))
            self.auto_save_config()  # Auto-save the new state
    
    def browse_filter_file(self, config_type):
        """Browse for configuration files - UPDATED TO SYNC STATE"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title=f"Select {config_type.replace('_', ' ').title()}",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.config_manager.set("last_directory", str(Path(filename).parent))
    
            if config_type == "filters_file":
                self.filters_file_var.set(filename)
                self.config_manager.set("filters_file", filename)  # SYNC STATE
                self.load_filters()
                self.config_manager.update_recent_list("recent_filters", filename)
    
            elif config_type == "advanced_filters_file":
                self.advanced_filters_file_var.set(filename)
                self.config_manager.set("advanced_filters_file", filename)  # SYNC STATE
                self.load_advanced_filters_auto()
                self.config_manager.update_recent_list("recent_advanced_filters", filename)
    
            self.update_recent_combos()
            self.auto_save_config()  # Auto-save the new state

    def update_recent_combos(self):
        """Update the recent files comboboxes"""
        self.recent_filters_combo['values'] = self.config_manager.get("recent_filters", [])
        self.recent_adv_filters_combo['values'] = self.config_manager.get("recent_advanced_filters", [])
    
    def on_recent_filters_selected(self, event=None):
        """When a recent filters file is selected - FIXED"""
        selected_file = self.recent_filters_combo.get()
        if selected_file and os.path.exists(selected_file):
            self.filters_file_var.set(selected_file)
            self.load_filters()
        else:
            self.messages(2, 3, "Selected file does not exist")

    def on_recent_adv_filters_selected(self, event=None):
        """When a recent advanced filters file is selected - FIXED"""
        selected_file = self.recent_adv_filters_combo.get()
        if selected_file and os.path.exists(selected_file):
            self.advanced_filters_file_var.set(selected_file)
            self.load_advanced_filters_auto()
        else:
            self.messages(2, 3, "Selected file does not exist")

    def save_configuration_dialog(self):
        """Save configuration with instance file update"""
        try:
            # Sync UI state first
            self.sync_ui_to_config()
            
            file_types = [
                ('JSON files', '*.json'),
                ('All Files', '*.*')
            ]
        
            initial_dir = self.config_manager.get("last_directory", "")
            
            filename = filedialog.asksaveasfilename(
                title="Save Configuration As",
                defaultextension=".json",
                filetypes=file_types,
                initialdir=initial_dir,
                initialfile=f"etail_config_{self.instance_id}.json"
            )
        
            if filename:
                # Update config file reference
                old_config_file = self.config_file
                self.config_file = Path(filename)
                self.config_manager.config_file = self.config_file
                
                # Save configuration
                if self.config_manager.save_config():
                    # Update browser's instances file
                    if hasattr(self, 'browser') and self.browser:
                        self.browser.update_instance_config_file(self.instance_id, self.config_file)
                    
                    self.messages(2, 9, f"Configuration saved to {filename}")
                else:
                    # Restore old config file on failure
                    self.config_file = old_config_file
                    self.config_manager.config_file = old_config_file
                    self.messages(2, 3, "Failed to save configuration")
                        
        except Exception as e:
            self.messages(2, 3, f"Error saving file: {e}")

    def save_configuration(self, config_path=None):
        """Save current configuration to file - CAPTURES CURRENT STATE"""
        # Update config manager with CURRENT UI values, not just initial ones
        self.config_manager.set("log_file", self.log_file_var.get())
        self.config_manager.set("filters_file", self.filters_file_var.get())
        self.config_manager.set("advanced_filters_file", self.advanced_filters_file_var.get())
    
        try:
            self.config_manager.set("initial_lines", int(self.initial_lines_var.get()))
        except ValueError:
            self.messages(2, 3, "Invalid initial lines value, using default")
            self.config_manager.set("initial_lines", 50)
    
        try:
            self.config_manager.set("refresh_interval", int(self.refresh_interval_var.get()))
        except ValueError:
            self.messages(2, 3, "Invalid refresh interval, using default")
            self.config_manager.set("refresh_interval", 100)
        
        self.config_manager.set("auto_load_config", self.auto_load_var.get())
        
        self.config_manager.set("verbose", self.verbose_var.get())
    
        # Also capture any other runtime state that should be persisted
        if hasattr(self, 'last_directory'):
            self.config_manager.set("last_directory", self.last_directory)
    
        # Simply save the config
        if self.config_manager.save_config(config_path):
            self.messages(2, 9, "Configuration saved successfully with current state")
            return True
        else:
            self.messages(2, 3, "Failed to save configuration")
            return False

    def load_configuration_file(self):
        """Browse for configuration files"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title="Load configuration",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                a_config = json.load(f)
            # Update default config with loaded values
            self.config_manager.config_file = Path(filename)
            self.config_manager.config.update(a_config)
            self.load_configuration()

    def load_configuration(self):
        """Load configuration from file and update UI - ROBUST VERSION"""
        try:
            # Ensure all expected keys exist with defaults
            default_config = self.config_manager.load_default_config()
            for key, value in default_config.items():
                if key not in self.config_manager.config:
                    self.config_manager.config[key] = value
            
            # Update UI with loaded values
            self.log_file_var.set(self.config_manager.get("log_file", ""))
            
            # Validate and set filters file paths
            filters_file = self.config_manager.get("filters_file", "")
            if filters_file:
                filters_path = Path(filters_file)
                if not filters_path.exists() or not filters_path.is_file():
                    filters_file = ""  # Reset if invalid
            self.filters_file_var.set(filters_file)
            
            advanced_filters_file = self.config_manager.get("advanced_filters_file", "")
            if advanced_filters_file:
                adv_filters_path = Path(advanced_filters_file)
                if not adv_filters_path.exists() or not adv_filters_path.is_file():
                    advanced_filters_file = ""  # Reset if invalid
            self.advanced_filters_file_var.set(advanced_filters_file)
            
            # Application settings with validation
            self.initial_lines_var.set(str(self.config_manager.get("initial_lines", 50)))
            self.refresh_interval_var.set(str(self.config_manager.get("refresh_interval", 100)))
            self.auto_load_var.set(self.config_manager.get("auto_load_config", True))
            self.verbose_var.set(self.config_manager.get("verbose", True))          
            
            self.update_recent_combos()
            self.messages(2, 9, f"Configuration loaded for instance {self.instance_id}")
            
        except Exception as e:
            print(f"DEBUG: Error loading configuration: {e}")
            # Load defaults on error
            self.config_manager.config = self.config_manager.load_default_config()

    def reset_configuration(self):
        """Reset configuration to defaults"""
        self.config_manager.config = self.config_manager.load_default_config()
        self.load_configuration()
        self.messages(2,9,f"Configuration reset to defaults")

    def create_empty_default_filters(self):
        """Create an empty default filters file"""
        try:
            default_filters_path = self.config_manager.get_default_filters_path()

            empty_filters = {
                "version": "1.1",
                "filters": []
            }
        
            with open(default_filters_path, 'w', encoding='utf-8') as f:
                json.dump(empty_filters, f, indent=2, ensure_ascii=False)
        
            self.messages(2, 9, "Created empty default filters file")
            return True

        except Exception as e:
            self.messages(2, 3, f"Error creating default filters: {e}")
            return False

    def debug_advanced_filters(self):
        """Debug method to check what's happening with advanced filters"""
        print("\n=== ADVANCED FILTERS DEBUG ===")
        print(f"Total advanced filters: {len(self.advanced_filters)}")
        print(f"Listbox items: {self.advanced_filters_listbox.size() if hasattr(self, 'advanced_filters_listbox') else 'No listbox'}")
    
        for key, data in self.advanced_filters.items():
            print(f"Filter Key: {key}")
            print(f"  Name: {data.get('name', 'Unnamed')}")
            print(f"  Enabled: {data.get('enabled', 'Unknown')}")
            print(f"  Fields: {len(data.get('fields', []))}")
            print(f"  Regex: {data.get('generated_regex', 'None')}")
            print(f"  Actions: {data.get('actions', {})}")
        print("==============================\n")
        
    def test_advanced_filter_loading(self):
        """Test method to verify advanced filters are working"""
        print("\n=== ADVANCED FILTERS TEST ===")
        print(f"Filters in memory: {len(self.advanced_filters)}")

        # Test if filters are being applied to log lines
        test_line = "This line contains uno and dos"
        for filter_key, filter_data in self.advanced_filters.items():
            if filter_data.get('enabled', True):
                regex = filter_data.get('generated_regex', '')
                if regex:
                    try:
                        match = re.search(regex, test_line)
                        if match:
                            print(f"✓ Filter '{filter_data.get('name')}' matches test line")
                        else:
                            print(f"✗ Filter '{filter_data.get('name')}' does NOT match test line")
                    except Exception as e:
                        print(f"✗ Filter '{filter_data.get('name')}' has invalid regex: {e}")

        print("=============================\n")

    # ****************************************************************************
    # *************************** Tail Actions  **********************************
    # ****************************************************************************

    def start_tail(self):
        """Start tailing the log file in a separate thread."""
        #self.config_manager.get("log_file", "") #Get from config file
        filepath = Path(self.log_file_var.get()) #Get from UI var
        if not filepath or not filepath.exists():
            self.messages(2,3,f"File {filepath} can't be accessed.")
            return
        
        # Get number of initial lines to display
        try:
            num_initial_lines = int(self.initial_lines_var.get())
        except:
            num_initial_lines = 50
        
        # Display last N lines instead of entire file
        encoding = self.simple_encoding_detect(filepath)
        last_lines = self.get_last_lines(filepath, num_initial_lines, encoding)
        if last_lines == []:
            print("Falling back to utf-8")
            encoding = "utf-8"
            last_lines = self.get_last_lines(filepath, num_initial_lines, "utf-8")
        self.encoding_label.config(text=f"Encoding: {encoding} ")
        
        self.log_text.delete(1.0, tk.END)  # Clear display
        for line in last_lines:
            self.update_display(line)
        
        # Start tailing from current end of file
        self.last_position = os.path.getsize(filepath)
        self.stop_event.clear()
        self.tail_thread = Thread(target=self.tail_loop, daemon=True)
        self.tail_thread.start()
        self.pause_button['state']="normal"
        self.stop_button['state']="normal"
        self.start_button['state']="disabled"
        self.status_label.config(text="Running", foreground="green")
        self.messages(2,0,f"Started tailing: {filepath} (showing last {num_initial_lines} lines)")

    def toggle_pause(self):
        """Pause or resume log updates."""
        self.pause_var.set(not self.pause_var.get())
        if self.pause_var.get():
            self.status_label.config(text="PAUSED", foreground="orange")
            self.messages(2,4,"")
            self.stop_button['state']="disabled"
            self.pause_button.config(text="Resume")
        else:
            self.pause_button.config(text="Pause")
            self.stop_button['state']="normal"
            self.status_label.config(text="Resumed", foreground="orange")
            self.messages(2,0,"")
            
    def stop_tail(self):
        """Stop the tailing process."""
        self.pause_button['state']="disabled"
        self.stop_button['state']="disabled"
        self.start_button['state']="normal"
        self.stop_event.set()
        if self.tail_thread and self.tail_thread.is_alive():
            self.tail_thread.join(timeout=2.0)
        self.messages(2,1,"Stopped tailing")
        self.status_label.config(text=mssgs[1], foreground="red")
    
    def tail_loop(self):
        """Efficient tailing loop that only reads new content."""
        filepath = Path(self.log_file_var.get()) #Get from UI var
        if not filepath or not os.path.exists(filepath):
            self.messages(2, 3, f"Log file not found: {filepath}")
            return

        encoding = self.simple_encoding_detect(filepath)
        error_count = 0
        max_errors = 5
        file_rotation_detected = False

        while not self.stop_event.is_set():
            try:
                if not os.path.exists(filepath):
                    self.messages(2, 3, f"Log file disappeared: {filepath}")
                    time.sleep(2)
                    continue

                current_size = os.path.getsize(filepath)

            # Handle file rotation or truncation
                if current_size < self.last_position:
                    self.messages(2, 2, "Log file was rotated/truncated, resetting position")
                    self.last_position = 0
                    file_rotation_detected = True

                # Read new content
                if current_size > self.last_position or file_rotation_detected:
                    self.status_label.config(text="Running", foreground="green")
                    with open(filepath, 'r', encoding=encoding, errors='replace') as file:
                        file.seek(self.last_position)
                        new_lines = file.readlines()

                        for line in new_lines:
                            if self.stop_event.is_set():
                                break
                            # Only process if not paused
                            if not self.pause_var.get():
                                self.after(0, self.update_display, line.rstrip())

                        self.last_position = file.tell()
                        file_rotation_detected = False
                    error_count = 0  # Reset error count on success

                time.sleep(0.1)  # Small sleep to prevent CPU overload

            except PermissionError:
                self.messages(2, 3, f"Permission denied accessing: {filepath}")
                time.sleep(2)

            except Exception as e:
                error_count += 1
                if error_count >= max_errors:
                    self.messages(2, 3, f"Multiple errors in tail loop, stopping: {e}")
                    break
                print(f"Error in tail loop (attempt {error_count}): {e}")
                time.sleep(1)
  
    def update_display(self, line):
        """Update the log display with highlighting and execute actions"""
        if not line:
            return

        # Call plugin on_log_line method
        self.plugin_manager.call_plugin_method('on_log_line', line)

        # Check if any filter matches and should skip the line
        should_skip = self.apply_filters_and_actions(line)
        if should_skip:       
            return

        # Insert the line at the end
        self.log_text.insert(tk.END, line + "\n")

        # Auto-scroll to the bottom
        self.log_text.see(tk.END)
        self.log_text.update()        

        # Optional: Limit total lines to prevent memory bloat
        lines_count = int(self.log_text.index('end-1c').split('.')[0])
        if lines_count > 10000:  # Keep last 10,000 lines
            self.log_text.delete(1.0, "1000.0")  # Remove first 5,000 lines

    def apply_filters_and_actions(self, line):
        sw_skip = False
        ac_skip = True

        # Apply simple filters
        self.process_plugin_filters(line)
        for filter_str, filter_data in self.filters.items():
            if self.line_matches_filter(line, filter_data):
                action = filter_data.get('action', 'none') 
                modifier = filter_data.get('action_modifier', '')
                match action:
                    case "skip":
                        sw_skip = True
                        ac_skip = True
                    case "tts":
                        voice = filter_data.get('voice_id', '')
                        modifier = (filter_data.get('action_modifier', ''), filter_data.get('voice_id', ''))

                # Execute action (if not skip, since we already handled that)
                if sw_skip != True and action != 'none':
                    ac_skip = False
                    # Apply coloring
                    tag_name = filter_str
                    bg_color = filter_data.get('bg_color', 'yellow')
                    fg_color = filter_data.get('fg_color', 'black')
                    
                    self.action_handler.execute_action(action, modifier, line)
                # Call plugin on_filter_match method
                self.plugin_manager.call_plugin_method('on_filter_match', filter_data, line)

        # Apply advanced filters
        for filter_key, filter_data in self.advanced_filters.items():
            if filter_data.get('enabled', True):  # Only process enabled advanced filters
                if self.line_matches_advanced_filter(line, filter_data):
                    # Apply advanced filter coloring and actions
                    actions = filter_data.get('actions', {})
                    # Execute advanced filter actions
                    action = actions.get('action', 'none')
                    if action != 'none':
                        modifier = actions.get('action_modifier', '')
                        match action:
                            case "skip":
                                sw_skip = True
                                ac_skip = True
                            case "tts":
                                voice = actions.get('voice_id', '')
                                modifier = (actions.get('action_modifier', ''), actions.get('voice_id', ''))
                        # Execute action (if not skip, since we already handled that)
                        if sw_skip != True and action != 'none':
                            ac_skip = False
                            self.action_handler.execute_action(action, modifier, line)
                            # Apply coloring
                            # Create a unique tag for this advanced filter
                            tag_name = f"advanced_{filter_key}"
    
                            # Configure the tag if not already configured
                            bg_color = actions.get('bg_color', 'yellow')
                            fg_color = actions.get('fg_color', 'black')

        if self.verbose_var.get() != True:
            sw_skip = True
        if ac_skip == False: #Print and colour if matched line
            self.messages(2, 2, f"ACTION PRINTED")
            self.log_text.insert(tk.END, line + "\n")
           
            # Auto-scroll to the bottom
            self.log_text.see(tk.END)
            self.log_text.update()        

            start_index = self.log_text.index("end-2l")
            end_index = self.log_text.index("end-1c")

            #self.log_text.tag_configure(tag_name, foreground=fg_color, background=bg_color)
            self.log_text.tag_add(tag_name, start_index, end_index)

            sw_skip = True # Skip the line since we already printed it.
        return sw_skip

    def line_matches_advanced_filter(self, line, filter_data):
        """Check if a line matches an advanced filter pattern"""
        regex_pattern = filter_data.get('generated_regex', '')
        if not regex_pattern:
            return False
        try:
            return bool(re.findall(regex_pattern, line))
        except re.error as e:
            self.messages(2, 3, f"Advanced filter regex error: {e}")
            return False

    def line_matches_filter(self, line, filter_data):
        """Check if a line matches a filter pattern"""
        pattern = filter_data['pattern']
        is_regex = filter_data.get('is_regex', False)
        if is_regex:
            try:
                #if hasattr(self, 'plugin_manager'):
                    #self.broadcast_regex_match(re.findall(pattern, line), line, pattern)
                return bool(re.findall(pattern, line))
            except re.error:
                return pattern in line
        else:
            return pattern in line

    def detect_log_rotation(self, filepath):
        """Detect if log file has been rotated"""
        try:
            current_inode = os.stat(filepath).st_ino
            if hasattr(self, 'last_inode'):
                if current_inode != self.last_inode:
                    self.last_inode = current_inode
                    return True
            else:
                self.last_inode = current_inode
            return False
        except:
            return False


    # ****************************************************************************
    # *************************** Style Actions  *********************************
    # ****************************************************************************

    def load_style_settings(self):
        """Load style settings from browser only - instances don't store styles"""
        try:
            if hasattr(self, 'browser') and self.browser:
                # Use browser's global styles
                self.apply_global_style(self.browser.global_styles)
                self.messages(2, 9, "Browser style settings applied")
            else:
                # Standalone mode: use defaults
                self.apply_global_style(GlobalStyleManager.get_style_settings())
                self.messages(2, 9, "Default style settings applied")
        except Exception as e:
            self.messages(2, 3, f"Error loading style settings: {e}")

    def ensure_style_attributes(self, style_settings):
        """Ensure all required style attributes exist with proper defaults"""
        required_attrs = {
            'font_family': 'Arial',
            'font_size': 9,
            'text_primary': '#2c3e50',
            'text_light': '#ffffff',
            'text_dark': '#000000',
            'primary_color': '#2c3e50',
            'secondary_color': '#3498db',
            'success_color': '#27ae60', 
            'warning_color': '#f39c12',
            'danger_color': '#e74c3c',
            'light_bg': '#ecf0f1',
            'dark_bg': '#34495e'
        }
        
        for attr, default in required_attrs.items():
            if not hasattr(self, attr):
                setattr(self, attr, default)
            
            # Also update from style_settings if provided
            if style_settings and attr in style_settings:
                setattr(self, attr, style_settings[attr])

    def sync_ui_to_config(self):
        """Sync current UI state to configuration manager"""
        # Log file
        current_log_file = self.log_file_var.get()
        if current_log_file and current_log_file != self.config_manager.get("log_file", ""):
            self.config_manager.set("log_file", current_log_file)
        
        # Filters files
        current_filters_file = self.filters_file_var.get()
        if current_filters_file and current_filters_file != self.config_manager.get("filters_file", ""):
            self.config_manager.set("filters_file", current_filters_file)
        
        current_advanced_filters_file = self.advanced_filters_file_var.get()
        if (current_advanced_filters_file and 
            current_advanced_filters_file != self.config_manager.get("advanced_filters_file", "")):
            self.config_manager.set("advanced_filters_file", current_advanced_filters_file)
        
        # Other settings
        try:
            self.config_manager.set("initial_lines", int(self.initial_lines_var.get()))
        except ValueError:
            pass
            
        try:
            self.config_manager.set("refresh_interval", int(self.refresh_interval_var.get()))
        except ValueError:
            pass
        
        self.config_manager.set("auto_load_config", self.auto_load_var.get())
        
        # Verbose setting
        self.config_manager.set("verbose", self.verbose_var.get())
    
    def auto_save_config(self):
        """Automatically save configuration with current state"""
        try:
            self.sync_ui_to_config()
            self.config_manager.save_config()
            print(f"DEBUG: Auto-saved configuration for {self.instance_id}")
        except Exception as e:
            print(f"DEBUG: Auto-save failed: {e}")

    def _copy_style_attributes(self):
        """Copy style attributes for backward compatibility"""
        for key, value in self.style_manager.style_settings.items():
            setattr(self, key, value)
    
    def setup_styling(self):
        """Setup modern styling using StyleManager"""
        self.style_manager.configure_styles()
    
    def configure_styles(self):
        """Delegate to StyleManager"""
        self.style_manager.configure_styles()
    
    def apply_style_to_widgets(self, style_settings=None):
        """Apply styles to all widgets using StyleManager"""
        if style_settings:
            self.style_manager.update_style_settings(style_settings)
            self._copy_style_attributes()
        
        self.style_manager.configure_styles()
        self.style_manager.apply_styles_to_widgets(self)
    
    def get_current_style_settings(self):
        """Get current style settings from StyleManager"""
        return self.style_manager.get_style_settings()
    
    def apply_global_style(self, style_settings=None):
        """Apply global style using StyleManager"""
        if style_settings:
            self.style_manager.update_style_settings(style_settings)
            self._copy_style_attributes()
        
        # Apply theme if specified
        if 'theme' in self.style_manager.style_settings:
            self.style_manager.apply_theme(self.style_manager.style_settings['theme'])
        
        self.style_manager.configure_styles()
        self.style_manager.apply_styles_to_widgets(self)

    # ****************************************************************************
    # *************************** Main          **********************************
    # ****************************************************************************    
class ETailBrowser:

    def __init__(self):
        try:
            self.root = tk.Tk()
            self.root.title("ETail - Multi-instance Log Monitor")
            self.root.geometry("1200x800")
            icon_path = resource_path("Etail.ico")
            self.root.wm_iconbitmap(icon_path)
            self.root.title("Etail 0.3")
            
            # Instance management
            self.instances = {}
            self.instance_counter = 0
            self.active_instance = None
            self.is_closing = False  # Track if we're shutting down            
            
            # Recent instances tracking
            self.recent_instances = []
            self.max_recent_instances = 5

            # Unified instances file in app directory
            if getattr(sys, 'frozen', False):
                self.app_dir = Path(sys.executable).parent
            else:
                self.app_dir = Path(__file__).parent
            
            # Initialize style manager with root reference
            self.style_manager = StyleManager(root=self.root)
            self.global_styles = self.style_manager.get_style_settings()
        
            # Initialize window styling - LOAD BEFORE SETUP
            self.setup_window_styling()
            
            self.instances_file = self.app_dir / "instances.json"
           
            # Ensure window styles directory exists
            self.window_styles_dir = self.app_dir / "window_styles"
            self.window_styles_dir.mkdir(exist_ok=True)
            self.apply_window_styling()

            # Add style presets storage
            self.style_presets = {}

           
            self.setup_ui()

            self.debug_window_styling_status()
            
            self.load_instances()
     
            # Apply initial window styling
            self.apply_initial_window_styling()
           
            print(f"DEBUG: Browser initialized with {len(self.instances)} instances")
    
            # Handle window closing properly
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
        except Exception as e:
            print(f"DEBUG: Browser initialization failed: {e}")
            raise
       
    #=========================WINDOWS======================================

    def debug_window_styling_status(self):
        """Debug method to check window styling status"""
        print("=== WINDOW STYLING STATUS ===")
        
        # Check if we have window styles
        if hasattr(self, 'global_styles'):
            window_styles = self.global_styles.get('window_styles', {})
            print(f"Window styles configured: {len(window_styles)} components")
            for component, styles in window_styles.items():
                print(f"  {component}: {len(styles)} properties")
        else:
            print("No global styles found")
        
        # Check platform
        import platform
        print(f"Platform: {platform.system()} {platform.release()}")
        
        # Check if root window exists
        if hasattr(self, 'root'):
            print(f"Root window: {self.root}")
            try:
                bg_color = self.root.cget('background')
                print(f"Root background: {bg_color}")
            except:
                print("Root background: Unknown")
        else:
            print("No root window found")
        
        print("=============================")
    
    
    def apply_window_styling(self):
        """Apply window styling to this window"""
        try:
            print(f"DEBUG: Applying window styling....................................")
            if hasattr(self, 'style_manager') and hasattr(self.style_manager, 'window_styles'):
                self.style_manager._apply_window_styling(self.root)
        except Exception as e:
            print(f"DEBUG: Error applying window styling: {e}")

    def setup_window_styling(self):
        """Setup window styling system"""
        # Ensure window styles directory exists
        self.window_styles_dir = self.app_dir / "window_styles"
        self.window_styles_dir.mkdir(exist_ok=True)
        
        # Load window styles if they exist
        self.load_window_styles()

    def load_window_styles(self):
        """Load saved window styles"""
        try:
            window_styles_file = self.app_dir / "window_styles" / "current.json"
            if window_styles_file.exists():
                with open(window_styles_file, 'r') as f:
                    window_styles = json.load(f)
                    self.global_styles['window_styles'] = window_styles
                    print("DEBUG: Loaded window styles from file")
        except Exception as e:
            print(f"DEBUG: Error loading window styles: {e}")

    def apply_initial_window_styling(self):
        """Apply window styling to the main browser window - IMPROVED"""
        try:
            # Apply immediately and then again after window is fully created
            self._apply_browser_window_styling()
            self.root.after(100, self._apply_browser_window_styling)
            self.root.after(500, self._apply_browser_window_styling)
            self.root.after(1000, self._apply_browser_window_styling)
        except Exception as e:
            print(f"DEBUG: Error in initial window styling: {e}")

    def _apply_browser_window_styling(self):
        """Apply window styling to browser window"""
        try:
            window_styles = self.global_styles.get('window_styles', {})
            if window_styles:
                self.style_manager.configure_window_styles(window_styles)
                
                # Apply specific window attributes
                self._apply_window_attributes(window_styles)
        except Exception as e:
            print(f"DEBUG: Error applying browser window styling: {e}")

    def _apply_window_attributes(self, window_styles):
        """Apply specific window attributes"""
        try:
            # Apply window background
            bg_styles = window_styles.get('WindowBackground', {})
            if bg_styles:
                bg_color = bg_styles.get('background')
                if bg_color:
                    self.root.configure(background=bg_color)
            
            # Apply window opacity if supported
            opacity = bg_styles.get('opacity', '1.0')
            try:
                self.root.attributes('-alpha', float(opacity))
            except:
                pass  # Opacity not supported on all platforms
                
        except Exception as e:
            print(f"DEBUG: Error applying window attributes: {e}")
    
    
    def apply_global_style_to_browser(self):
        """Apply global style to browser using StyleManager - UPDATED"""
        try:
            # Update StyleManager with current global styles
            self.style_manager.update_style_settings(self.global_styles)
            
            # Apply theme if specified
            if 'theme' in self.global_styles:
                self.style_manager.apply_theme(self.global_styles['theme'])
            
            # Configure and apply styles
            self.style_manager.configure_styles()
            self.style_manager.apply_styles_to_widgets(self.main_frame)
            
            # Apply window styling
            window_styles = self.global_styles.get('window_styles')
            if window_styles:
                self.style_manager.configure_window_styles(window_styles)
                self._apply_window_attributes(window_styles)
            
            print("DEBUG: Global style applied to browser using StyleManager")
            
        except Exception as e:
            print(f"DEBUG: Browser global style error: {e}")

    def save_window_styles(self, window_styles):
        """Save window styles to file"""
        try:
            window_styles_file = self.app_dir / "window_styles" / "current.json"
            with open(window_styles_file, 'w') as f:
                json.dump(window_styles, f, indent=2)
            print("DEBUG: Window styles saved to file")
        except Exception as e:
            print(f"DEBUG: Error saving window styles: {e}")

    #=========================WINDOWS======================================

    def on_closing(self):
        """Handle browser window closing - PROPER SAVE SEQUENCE"""
        self.is_closing = True
        
        print("DEBUG: Browser closing started")
        
        # Save all instance configurations first
        self.save_all_configs()
        
        # Then save the instances file
        self.save_instances()
        
        # Finally cleanup instances
        self.cleanup_all_instances()
        
        print("DEBUG: Browser closing completed")
        self.root.destroy()

    def apply_global_style(self, style_settings):
        """Apply styling to all instances and browser"""
        # Apply to browser itself
        print(f"***************************************************************************")
        print(f"**************************** Line 7956 ************************************")
        print(f"************************** Clas EtailBrowser*******************************")
        print(f"configure_styles(self, style_settings) {self}, {style_settings}")
        print(f"***************************************************************************")
        print(f"***************************************************************************")  
        
        self.configure_browser_styles(style_settings)
        
        # Apply to all instances
        for instance_id, instance_info in self.instances.items():
            if instance_info['app']:
                try:
                    instance_info['app'].apply_unified_style(style_settings)
                except Exception as e:
                    print(f"Error applying style to instance {instance_id}: {e}")

    def apply_global_style_to_all_instances(self):
        """Apply global style to all instances using StyleManager"""  
        for instance_id, instance_info in self.instances.items():
            if instance_info and instance_info.get('app'):
                try:
                    instance_info['app'].apply_global_style(self.global_styles)
                    print(f"DEBUG: Applied global style to existing instance {instance_id}")
                except Exception as e:
                    print(f"DEBUG: Error applying style to instance {instance_id}: {e}")

    def _copy_style_attributes(self):
        """Copy style attributes for backward compatibility"""
        for key, value in self.style_manager.style_settings.items():
            setattr(self, key, value)

    def close_active_instance(self):
        """Close the currently active instance - FIXED AUTO-CREATION"""
        if self.is_closing:
            return
            
        current_tab = self.safe_notebook_select()
        if not current_tab:
            return
            
        tab_index = self.safe_notebook_index(current_tab)
        if tab_index == -1:
            return
            
        instance_id = self.find_instance_by_tab_index(tab_index)
        
        if instance_id and instance_id in self.instances:
            instance = self.instances[instance_id]
            
            # Confirm closure
            if messagebox.askyesno("Confirm", f"Close instance '{instance['name']}'?"):
                # Save instance state before cleanup
                if instance['app']:
                    instance['app'].save_instance_state()
                
                # Clean up the instance
                if instance['app']:
                    instance['app'].cleanup()
                
                # Remove from notebook
                self.safe_notebook_forget(instance['frame'])
                
                # Remove from instances and save
                del self.instances[instance_id]
                self.save_instances()
                
                self.status_var.set(f"Closed instance: {instance['name']}")
                
                # Only create new instance if this was the last one AND we're not closing
                if not self.instances and not self.is_closing:
                    print("DEBUG: Last instance closed, creating new one")
                    self.create_instance()
                else:
                    print(f"DEBUG: Instance closed, {len(self.instances)} instances remaining")

    def find_instance_by_tab_index(self, index):
        """Find instance ID by notebook tab index - SAFE VERSION"""
        try:
            for instance_id, info in self.instances.items():
                if self.notebook.index(info['frame']) == index:
                    return instance_id
        except tk.TclError:
            # Notebook might be destroyed
            pass
        return None
        
    def on_tab_changed(self, event):
        """Handle tab changes"""
        current_tab = self.notebook.select()
        if current_tab:
            tab_index = self.notebook.index(current_tab)
            instance_id = self.find_instance_by_tab_index(tab_index)
            if instance_id:
                self.active_instance = instance_id
                instance_name = self.instances[instance_id]['name']
                self.status_var.set(f"Active: {instance_name}")
                
    def receive_instance_data(self, instance_id, data_type, data):
        """Receive data from instances for sharing"""
        if data_type == "filters":
            # Store for sharing with other instances
            self.shared_data['common_filters'][instance_id] = data
            # Optionally auto-share with other instances
            self.broadcast_to_other_instances(instance_id, "filter", data)
            
        elif data_type == "status_update":
            # Update browser status if needed
            pass
            
    def broadcast_to_other_instances(self, from_instance_id, data_type, data):
        """Broadcast data to all other instances"""
        for instance_id, instance_info in self.instances.items():
            if instance_id != from_instance_id and instance_info['app']:
                instance_info['app'].receive_shared_data(from_instance_id, data_type, data)
                
    def show_performance_dialog(self):
        """Show performance tuning dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Performance Settings")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="Global Performance Settings", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Refresh interval
        interval_frame = ttk.Frame(dialog)
        interval_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(interval_frame, text="Default Refresh Interval (ms):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="100")
        ttk.Entry(interval_frame, textvariable=self.interval_var, width=10).pack(side=tk.RIGHT)
        
        # Apply to all button
        ttk.Button(dialog, text="Apply to All Instances", 
                  command=self.apply_performance_to_all).pack(pady=20)
                  
    def apply_performance_to_all(self):
        """Apply performance settings to all instances"""
        try:
            interval = int(self.interval_var.get())
            
            for instance_id, instance_info in self.instances.items():
                if instance_info['app']:
                    instance_info['app'].apply_performance_tweak({
                        'refresh_interval': interval
                    })
                    
            self.status_var.set("Performance settings applied to all instances")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def save_all_configs(self):
        """Save all configurations - ENHANCED"""
        print(f"DEBUG: Saving configurations for {len(self.instances)} instances")
        
        success_count = 0
        for instance_id, instance in self.instances.items():
            if instance['app']:
                try:
                    if instance['app'].save_instance_state():
                        success_count += 1
                        print(f"DEBUG: ✓ Saved instance {instance_id}")
                    else:
                        print(f"DEBUG: ✗ Failed to save instance {instance_id}")
                except Exception as e:
                    print(f"DEBUG: ✗ Error saving instance {instance_id}: {e}")
        
        self.status_var.set(f"Saved {success_count}/{len(self.instances)} instances")
        print(f"DEBUG: Configuration save completed: {success_count}/{len(self.instances)} successful")

    def run(self):
        """Run the browser - SIMPLIFIED"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"DEBUG: Browser mainloop error: {e}")
        finally:
            if not self.is_closing:
                self.cleanup_all_instances()

    def share_plugin_data(self, from_instance_id, plugin_name, data_type, data):
        """Coordinate plugin data sharing between instances"""
        # Allow plugins to share data if needed, but keep config separate
        if data_type == "config_request":
            # One instance can request config from another
            pass
        elif data_type == "data_broadcast":
            # Broadcast data to same plugin in other instances
            self.broadcast_plugin_data(from_instance_id, plugin_name, data)

    def broadcast_plugin_data(self, from_instance_id, plugin_name, data):
        """Broadcast data to same plugin in other instances"""
        for instance_id, instance_info in self.instances.items():
            if instance_id != from_instance_id:
                plugin_instance = self.get_plugin_instance(instance_id, plugin_name)
                if plugin_instance and hasattr(plugin_instance, 'receive_broadcast'):
                    plugin_instance.receive_broadcast(data, from_instance_id)

    def get_plugin_instance(self, instance_id, plugin_name):
        """Get a specific plugin instance from an app instance"""
        if instance_id in self.instances:
            app = self.instances[instance_id]['app']
            if (hasattr(app, 'plugin_manager') and 
                app.plugin_manager and 
                plugin_name in app.plugin_manager.loaded_plugins):
                return app.plugin_manager.loaded_plugins[plugin_name]
        return None

    def cleanup_all_instances(self):
        """Clean up all instances without using the notebook"""
        for instance_id, instance_info in list(self.instances.items()):
            if instance_info['app']:
                try:
                    instance_info['app'].cleanup()
                except Exception as e:
                    print(f"Error cleaning up instance {instance_id}: {e}")
            # Remove from instances dict
            del self.instances[instance_id]

    def safe_notebook_select(self):
        """Safely get current notebook selection"""
        try:
            if (hasattr(self, 'notebook') and 
                self.notebook and 
                self.notebook.winfo_exists()):
                return self.notebook.select()
        except tk.TclError:
            pass
        return None
    
    def safe_notebook_index(self, widget):
        """Safely get notebook index for widget"""
        try:
            if (hasattr(self, 'notebook') and 
                self.notebook and 
                self.notebook.winfo_exists()):
                return self.notebook.index(widget)
        except tk.TclError:
            pass
        return -1
    
    def safe_notebook_forget(self, widget):
        """Safely remove widget from notebook"""
        try:
            if (hasattr(self, 'notebook') and 
                self.notebook and 
                self.notebook.winfo_exists()):
                self.notebook.forget(widget)
        except tk.TclError:
            pass

    def create_instance_from_data(self, instance_data):
        """Create instance from saved data using the new naming system"""
        try:
            instance_id = instance_data['id']
            instance_name = instance_data.get('name', instance_id)
            tab_name = instance_data.get('tab_name', instance_name)
            config_path = Path(instance_data['config_file'])
            
            # CHECK FOR DUPLICATE FIRST
            if instance_id in self.instances:
                print(f"DEBUG: Instance {instance_id} already exists, skipping")
                return False
                
            print(f"DEBUG: Creating instance {instance_id} ({instance_name}) from {config_path}")
            
            # Verify config file exists
            if not config_path.exists():
                print(f"DEBUG: Config file {config_path} not found, skipping instance {instance_name}")
                return False
            
            # Create frame for this instance
            instance_frame = ttk.Frame(self.notebook)
            
            # Add to notebook with stored tab name
            self.notebook.add(instance_frame, text=tab_name)
            
            # Create the LogTailApp instance
            app_instance = LogTailApp(
                parent=instance_frame,
                instance_id=instance_id,
                config_file=str(config_path),
                browser_reference=self
            )
            app_instance.pack(fill=tk.BOTH, expand=True)
            
            # Store instance info with proper naming
            self.instances[instance_id] = {
                'frame': instance_frame,
                'id': instance_id,
                'app': app_instance,
                'name': instance_name,
                'config_path': config_path,
                'tab_name': tab_name
            }
            
            print(f"DEBUG: Successfully created instance from data: {instance_name}")
            return True
            
        except Exception as e:
            print(f"DEBUG: Error creating instance from data: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_instances(self):
        """Save all instances to unified instances file - COMPLETE VERSION"""
        try:
            instances_data = {
                'browser': {
                    'window_geometry': self.root.geometry(),
                    'last_saved': time.time(),
                    'instance_counter': self.instance_counter,
                    'total_instances': len(self.instances),
                    'global_style': self.style_manager.get_style_settings(),
                    'recent_instances': self.recent_instances  # Add this line
                },
                'instances': [],
                'style_presets': self.style_presets  # ADD THIS LINE
            }
            #print(f"DEBUG: Saving browser global styles: {self.style_manager.get_style_settings()}")
            #print(f"DEBUG: Saving browser style presets: {len(self.style_presets)} presets")
            
            # Add each instance
            for instance_id, instance_info in self.instances.items():
                instance_data = {
                    'id': instance_id,
                    'name': instance_info['name'],  # Store the friendly name
                    'tab_name': instance_info['tab_name'],
                    'config_file': str(instance_info['config_path']),
                    'last_updated': time.time()
                }
                instances_data['instances'].append(instance_data)
            
            # Ensure directory exists
            self.instances_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(self.instances_file, 'w', encoding='utf-8') as f:
                json.dump(instances_data, f, indent=2, ensure_ascii=False)
            
            #self.after(200, lambda: instance_info['app'].apply_global_style())
            return True


        except Exception as e:
            print(f"DEBUG: Error saving instances: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_instance(self, config_path=None, instance_name=None):
        """Create a new ETail instance with proper naming and directory management - FIXED"""
        try:
            # If no name provided, ask for one
            if instance_name is None:
                instance_name = tk.simpledialog.askstring(
                    "Instance Name", 
                    "Enter a name for this instance:",
                    initialvalue=f"Instance {self.instance_counter + 1}"
                )
                if not instance_name:  # User cancelled or empty name
                    return
            
            # Check if instance name already exists
            for existing_id, existing_info in self.instances.items():
                if existing_info['name'] == instance_name:
                    messagebox.showwarning("Duplicate Name", 
                                         f"Instance name '{instance_name}' already exists.")
                    return
            
            # Generate instance ID based on name (sanitized)
            instance_id = "".join(c for c in instance_name.lower() if c.isalnum() or c == '_')
            
            # Ensure unique instance ID
            original_id = instance_id
            counter = 1
            while instance_id in self.instances:
                instance_id = f"{original_id}_{counter}"
                counter += 1
            
            # Use provided config path or create one based on instance name
            if config_path is None:
                # Create a sanitized directory name
                safe_name = "".join(c for c in instance_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                instances_dir = self.app_dir / "instances"
                instances_dir.mkdir(parents=True, exist_ok=True)
                config_path = instances_dir / f"{safe_name}.json"
            else:
                config_path = Path(config_path)
            
            print(f"DEBUG: Creating instance - ID: {instance_id}, Name: {instance_name}, Config: {config_path}")
            
            # Create frame for this instance
            instance_frame = ttk.Frame(self.notebook)
            
            # Use the provided name for the tab
            tab_name = instance_name
            self.notebook.add(instance_frame, text=tab_name)
            
            # Create and store the LogTailApp instance
            app_instance = LogTailApp(
                parent=instance_frame,
                instance_id=instance_id,
                config_file=str(config_path),
                browser_reference=self
            )
            app_instance.pack(fill=tk.BOTH, expand=True)
            
            # Store instance info with proper naming
            self.instances[instance_id] = {
                'frame': instance_frame,
                'id': instance_id,
                'app': app_instance,
                'name': instance_name,  # Store the friendly name
                'config_path': config_path,
                'tab_name': tab_name
            }
            
            # Save instance name in the instance config
            app_instance.config_manager.set("instance_name", instance_name)
            app_instance.config_manager.set("instance_id", instance_id)  # Also save instance_id
            app_instance.config_manager.save_config()
            
            # Update instance counter
            self.instance_counter += 1
            
            # Save to instances file
            self.save_instances()
            
            # Apply global style to the new instance IMMEDIATELY
            self.apply_style_to_new_instance(instance_id)
            
            # Switch to new instance
            self.notebook.select(instance_frame)
            self.status_var.set(f"Created instance: {instance_name}")
            
            print(f"DEBUG: Created new instance: {instance_id} ({instance_name})")
            
        except Exception as e:
            print(f"DEBUG: Error creating instance: {e}")
            messagebox.showerror("Error", f"Failed to create instance: {e}")

    def update_instance_config_file(self, instance_id, new_config_file):
        """Update the config file path for an instance"""
        if instance_id in self.instances:
            self.instances[instance_id]['config_path'] = new_config_file
            self.save_instances()
            print(f"DEBUG: Updated config file for {instance_id} to {new_config_file}")

    def load_instances(self):
        """Load all instances from unified instances file - FIXED VERSION"""
        try:
            # Clear any existing instances first
            self.instances.clear()
            self.instance_counter = 0
            
            # Remove all existing tabs
            for tab_id in self.notebook.tabs():
                self.notebook.forget(tab_id)
            
            # Check if instances file exists
            if not self.instances_file.exists():
                print("DEBUG: No instances file found, creating first instance")
                self.create_instance()
                return
    
            # Load instances file
            with open(self.instances_file, 'r', encoding='utf-8') as f:
                instances_data = json.load(f)
            
            print(f"DEBUG: Found instances data with {len(instances_data.get('instances', []))} instances")
            
            # Initialize browser_config with empty dict as default
            browser_config = instances_data.get('browser', {})
            
            # Load recent instances FIRST (before other browser config)
            if 'recent_instances' in browser_config:
                self.recent_instances = browser_config['recent_instances']
                print(f"DEBUG: Loaded {len(self.recent_instances)} recent instances")
            
            # Load style presets
            if 'style_presets' in instances_data:
                self.style_presets = instances_data['style_presets']
                print(f"DEBUG: Loaded {len(self.style_presets)} style presets from instances file")
            else:
                self.style_presets = {}
                print("DEBUG: No style presets found in instances file")
            
            # Load browser window state
            if browser_config:  # Only if we have browser config
                if 'window_geometry' in browser_config:
                    self.root.geometry(browser_config['window_geometry'])
                if 'instance_counter' in browser_config:
                    self.instance_counter = browser_config['instance_counter']
                
                # Load global style settings
                if 'global_style' in browser_config:
                    self.style_manager.update_style_settings(browser_config['global_style'])
                    self.global_styles = self.style_manager.get_style_settings()
                    print(f"DEBUG: Loaded browser global styles: {self.global_styles}")
                    
                    # Apply theme if specified
                    if 'theme' in self.global_styles:
                        try:
                            self.style = ttk.Style()
                            self.style.theme_use(self.global_styles['theme'])
                            print(f"DEBUG: Applied theme: {self.global_styles['theme']}")
                        except Exception as e:
                            print(f"DEBUG: Error applying theme: {e}")
                else:
                    # Initialize with defaults if not found
                    self.global_styles = self.style_manager.get_style_settings()
                    print("DEBUG: Using default browser styles")
                
                # Always apply browser styles after loading
                self.apply_global_style_to_browser()
            
            # Load all instances
            loaded_count = 0
            if 'instances' in instances_data and instances_data['instances']:
                print(f"DEBUG: Attempting to load {len(instances_data['instances'])} instances")
                
                for instance_data in instances_data['instances']:
                    try:
                        # Use the stored name and tab_name
                        instance_id = instance_data['id']
                        instance_name = instance_data.get('name', instance_id)
                        tab_name = instance_data.get('tab_name', instance_name)
                        config_file = instance_data['config_file']
                        
                        # Check if config file still exists
                        if not Path(config_file).exists():
                            print(f"DEBUG: Config file not found: {config_file}, skipping instance {instance_name}")
                            continue
                        
                        # Check for duplicates
                        if instance_id in self.instances:
                            print(f"DEBUG: Instance {instance_id} already loaded, skipping")
                            continue
                        
                        # Create instance with stored information
                        success = self.create_instance_from_data(instance_data)
                        if success:
                            loaded_count += 1
                            print(f"DEBUG: Successfully loaded instance: {instance_name}")
                        else:
                            print(f"DEBUG: Failed to load instance: {instance_name}")
                    except Exception as e:
                        print(f"DEBUG: Error loading instance {instance_data}: {e}")
                        continue
    
            # Update instance counter to highest loaded instance
            if loaded_count > 0:
                max_instance_num = 0
                for instance_id in self.instances.keys():
                    try:
                        # Extract number from "instance_X" if present
                        if '_' in instance_id:
                            instance_num = int(instance_id.split('_')[-1])
                            if instance_num > max_instance_num:
                                max_instance_num = instance_num
                    except (IndexError, ValueError):
                        pass
                self.instance_counter = max_instance_num
                print(f"DEBUG: Set instance_counter to {self.instance_counter} based on loaded instances")
            
            # ONLY create default instance if NO instances were loaded
            if loaded_count == 0:
                print("DEBUG: No instances loaded, creating default instance")
                self.create_instance()
            else:
                print(f"DEBUG: Successfully loaded {loaded_count} instances")
                
            # Select first tab if any exist
            if self.notebook.tabs():
                self.notebook.select(0)
    
            # Apply global styling to all loaded instances
            self.apply_global_style_to_all_instances()
            
        except Exception as e:
            print(f"DEBUG: Error loading instances: {e}")
            import traceback
            traceback.print_exc()
            # Only create default instance on error if no instances exist
            if not self.instances:
                self.create_instance()

    def debug_instances_file(self):
        """Debug method to check instances file content"""
        if self.instances_file.exists():
            try:
                with open(self.instances_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                print(f"\n=== INSTANCES FILE CONTENT ===")
                print(f"Total instances in file: {len(content.get('instances', []))}")
                for instance in content.get('instances', []):
                    print(f"  - {instance['id']}: {instance['tab_name']} -> {instance['config_file']}")
                print(f"Instance counter in file: {content.get('browser', {}).get('instance_counter', 'N/A')}")
                print("==============================\n")
            except Exception as e:
                print(f"DEBUG: Error reading instances file: {e}")
        else:
            print("DEBUG: Instances file does not exist")

    def open_unified_style_dialog(self):
            """Open unified styling dialog"""
            if not self.instances:
                messagebox.showinfo("Styling", "Please create an instance first")
                return
                
            unified_dialog = UnifiedStyleDialog(self.root, self)

    def setup_ui(self):
        """Setup the main browser interface - FIXED VERSION"""
        # Remove this line: self.setup_global_styling() - DELETE IT
        
        # Create main frame - use existing styles instead of Browser.TFrame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top toolbar - use existing styles
        toolbar = ttk.Frame(self.main_frame)  # Remove style='Browser.TFrame'
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # All buttons use existing styles
        ttk.Button(toolbar, text="New Instance", command=self.create_instance).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Close Instance", command=self.close_active_instance).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Save All Configs", command=self.save_all_configs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Load Instance", command=self.load_instance_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Rename Instance", command=self.rename_active_instance).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Styling", command=self.open_unified_style_dialog).pack(side=tk.LEFT, padx=(0, 5))

        #label = EditableLabel(toolbar, text="double-click to edit me")
        #text = tk.Text(toolbar)
        #label.pack(side="top", fill="x", padx=2, pady=2)
        
        # Notebook - use existing styles
        self.notebook = ttk.Notebook(self.main_frame)  # Remove style='Browser.TNotebook'
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Status bar - use existing styles
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)  # Remove style='Browser.TLabel'
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Apply global styling - KEEP THIS but it will use the new StyleManager
        self.root.after(100, self.apply_global_style_to_browser)

    def apply_style_to_new_instance(self, instance_id):
        """Apply global style to a newly created instance"""
        try:
            if instance_id in self.instances:
                instance_info = self.instances[instance_id]
                if instance_info and instance_info.get('app'):
                    instance_info['app'].apply_global_style(self.global_styles)
                    print(f"DEBUG: Applied global style to new instance {instance_id}")
        except Exception as e:
            print(f"DEBUG: Error applying style to new instance {instance_id}: {e}")

    def load_instance_dialog(self):
        """Open dialog to load an instance from a configuration file"""
        initial_dir = self.app_dir / "instances"
        filename = filedialog.askopenfilename(
            title="Load Instance Configuration",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="*.json"
        )
        
        if filename:
            self.load_instance_from_config(filename)

    def load_instance_from_config(self, config_file):
        """Load an instance from a configuration file with proper naming"""
        try:
            config_path = Path(config_file)
            
            # Check if this instance is already loaded
            for instance_id, instance_info in self.instances.items():
                if instance_info['config_path'] == config_path:
                    # Switch to this instance
                    self.notebook.select(instance_info['frame'])
                    self.status_var.set(f"Instance already loaded: {instance_info['name']}")
                    return
            
            # Try to get instance name from the config file
            instance_name = config_path.stem  # Default to filename
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if 'instance_name' in config_data:
                        instance_name = config_data['instance_name']
            except:
                pass  # Use default name if we can't read the config
            
            # Check for duplicate names
            original_name = instance_name
            counter = 1
            while any(info['name'] == instance_name for info in self.instances.values()):
                instance_name = f"{original_name} ({counter})"
                counter += 1
            
            # Generate instance ID from name
            instance_id = "".join(c for c in instance_name.lower() if c.isalnum() or c == '_')
            
            # Ensure unique instance ID
            original_id = instance_id
            counter = 1
            while instance_id in self.instances:
                instance_id = f"{original_id}_{counter}"
                counter += 1
            
            # Create frame for this instance
            instance_frame = ttk.Frame(self.notebook)
            
            # Use the instance name for the tab
            tab_name = instance_name
            self.notebook.add(instance_frame, text=tab_name)
            
            # Create the LogTailApp instance
            app_instance = LogTailApp(
                parent=instance_frame,
                instance_id=instance_id,
                config_file=str(config_path),
                browser_reference=self
            )
            app_instance.pack(fill=tk.BOTH, expand=True)
            
            # Store instance info
            self.instances[instance_id] = {
                'frame': instance_frame,
                'id': instance_id,
                'app': app_instance,
                'name': instance_name,
                'config_path': config_path,
                'tab_name': tab_name
            }
            
            # Add to recent instances
            self.add_to_recent_instances(config_path)
            
            # Save to instances file
            self.save_instances()
            
            # Apply global style to the new instance
            self.root.after(2000, lambda instance_id=instance_id: self.apply_style_to_new_instance(instance_id))
            
            # Switch to new instance
            self.notebook.select(instance_frame)
            self.status_var.set(f"Loaded instance: {instance_name}")
            
            print(f"DEBUG: Loaded instance from config: {instance_name}")
            
        except Exception as e:
            print(f"DEBUG: Error loading instance from config: {e}")
            messagebox.showerror("Error", f"Failed to load instance: {e}")

    def add_to_recent_instances(self, config_path):
        """Add a config file to recent instances list"""
        config_str = str(config_path)
        if config_str in self.recent_instances:
            self.recent_instances.remove(config_str)
        
        self.recent_instances.insert(0, config_str)
        self.recent_instances = self.recent_instances[:self.max_recent_instances]
        
        # Save recent instances to browser config
        self.save_instances()

    def load_recent_instances_menu(self):
        """Create a recent instances submenu"""
        if hasattr(self, 'recent_menu'):
            self.recent_menu.delete(0, tk.END)
        else:
            self.recent_menu = tk.Menu(self.root, tearoff=0)
        
        if not self.recent_instances:
            self.recent_menu.add_command(label="No recent instances", state="disabled")
        else:
            for config_path in self.recent_instances:
                path = Path(config_path)
                self.recent_menu.add_command(
                    label=path.name,
                    command=lambda p=config_path: self.load_instance_from_config(p)
                )
        
        return self.recent_menu

    def rename_instance(self, instance_id):
        """Rename an existing instance"""
        if instance_id not in self.instances:
            return
        
        current_name = self.instances[instance_id]['name']
        new_name = tk.simpledialog.askstring("Rename Instance", 
                                        "Enter new name for this instance:",
                                        initialvalue=current_name)
        
        if new_name and new_name != current_name:
            # Check for duplicate names
            if any(info['name'] == new_name for info in self.instances.values()):
                messagebox.showwarning("Duplicate Name", 
                                     f"Instance name '{new_name}' already exists.")
                return
            
            # Update instance info
            self.instances[instance_id]['name'] = new_name
            self.instances[instance_id]['tab_name'] = new_name
            
            # Update tab text
            tab_index = self.notebook.index(self.instances[instance_id]['frame'])
            self.notebook.tab(tab_index, text=new_name)
            
            # Save instance name in instance config
            if self.instances[instance_id]['app']:
                self.instances[instance_id]['app'].config_manager.set("instance_name", new_name)
                self.instances[instance_id]['app'].config_manager.save_config()
            
            # Save browser config
            self.save_instances()
            
            self.status_var.set(f"Renamed instance to: {new_name}")

    def rename_active_instance(self):
        """Rename the currently active instance"""
        current_tab = self.safe_notebook_select()
        if not current_tab:
            messagebox.showinfo("Rename", "No instance selected")
            return
            
        tab_index = self.safe_notebook_index(current_tab)
        if tab_index == -1:
            return
            
        instance_id = self.find_instance_by_tab_index(tab_index)
        if instance_id:
            self.rename_instance(instance_id)

    def messages(self, par_1, par_2, par_3):
        """Simple messaging method for browser compatibility"""
        # Just update the status bar and print to console
        if hasattr(self, 'status_var'):
            self.status_var.set(par_3)
        print(f"[Browser] {par_3}")

    # ****************************************************************************
    # *************************** EDITABLE LABEL *********************************
    # ****************************************************************************    


class EditableLabel(tk.Label):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.entry = tk.Entry(self)
        self.bind("<Double-1>", self.edit_start)
        self.entry.bind("<Return>", self.edit_stop)
        self.entry.bind("<FocusOut>", self.edit_stop)
        self.entry.bind("<Escape>", self.edit_cancel)

    def edit_start(self, event=None):
        self.entry.place(relx=.5, rely=.5, relwidth=1.0, relheight=1.0, anchor="center")
        self.entry.focus_set()

    def edit_stop(self, event=None):
        self.configure(text=self.entry.get())
        self.entry.place_forget()

    def edit_cancel(self, event=None):
        self.entry.delete(0, "end")
        self.entry.place_forget()

def main_browser():
    debug_startup()  # Add this line
    try:
        browser = ETailBrowser()
        browser.run()
    except Exception as e:
        print(f"Error starting browser: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Browser Error", f"Failed to start ETail Browser: {e}")
        sys.exit(1)

def resource_path(relative_path):
    """Get absolute path to resource - unchanged"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def debug_startup():
    """Debug startup sequence"""
    print("=== DEBUG STARTUP ===")
    print(f"frozen: {getattr(sys, 'frozen', False)}")
    print(f"__name__: {__name__}")
    print(f"argv: {sys.argv}")
    
    # Check if we're accidentally calling standalone
    import inspect
    for frame in inspect.stack():
        if 'main_standalone' in str(frame):
            print("FOUND MAIN_STANDALONE IN STACK!")
            break
    
    print("=====================")

    # ****************************************************************************
    # *************************** Main          **********************************
    # ****************************************************************************    


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    # Always use browser mode - no fallback to standalone
    main_browser()
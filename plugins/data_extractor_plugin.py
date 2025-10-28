try:
    # Try to import from plugins package (source mode)
    from plugins.etail_plugin import ETailPlugin
except ImportError:
    try:
        # Try direct import (compiled mode)
        from etail_plugin import ETailPlugin
    except ImportError:
        # Fallback: define it here
        from abc import ABC, abstractmethod
        class ETailPlugin(ABC):
            def __init__(self, app):
                self.app = app
                self.name = "Unnamed Plugin"
                self.version = "1.0" 
                self.description = "No description provided"
                self.enabled = False
                
            @abstractmethod
            def setup(self): pass
                
            @abstractmethod 
            def teardown(self): pass

import tkinter as tk
from tkinter import ttk, filedialog
import re
from datetime import datetime
import csv
import json
import os

def add_tooltip(widget, text):
    """Helper function to easily add tooltips"""
    ToolTip(widget, text)

# =============================================================================
# FILTER MANAGER
# =============================================================================

class FilterManager:
    """Manages filter persistence and multiple filter support"""
    
    def __init__(self, plugin):
        self.plugin = plugin
        self.filters_file = "data_extractor_filters.json"
        self.active_filters = {}
        self.saved_filters = self.load_filters()
    
    def get_filters_path(self):
        """Get the path to the filters file"""
        # Try to use plugin directory or current directory
        if hasattr(self.plugin, 'plugin_dir'):
            return os.path.join(self.plugin.plugin_dir, self.filters_file)
        return self.filters_file
    
    def load_filters(self):
        """Load saved filters from file"""
        try:
            filters_path = self.get_filters_path()
            if os.path.exists(filters_path):
                with open(filters_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading filters: {e}")
            return {}
    
    def save_filters(self):
        """Save all filters to file"""
        try:
            # Combine active and saved filters
            all_filters = self.saved_filters.copy()
            
            for filter_id, filter_config in self.active_filters.items():
                # Don't save temporary test filters
                if not filter_id.startswith('test_'):
                    all_filters[filter_id] = filter_config
            
            filters_path = self.get_filters_path()
            with open(filters_path, 'w', encoding='utf-8') as f:
                json.dump(all_filters, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving filters: {e}")
            return False
    
    def save_filter(self, filter_id, filter_config):
        """Save a specific filter"""
        self.active_filters[filter_id] = filter_config
        return self.save_filters()
    
    def delete_filter(self, filter_id):
        """Delete a filter"""
        if filter_id in self.active_filters:
            del self.active_filters[filter_id]
        if filter_id in self.saved_filters:
            del self.saved_filters[filter_id]
        return self.save_filters()
    
    def get_all_filters(self):
        """Get all filters (active + saved)"""
        all_filters = self.saved_filters.copy()
        all_filters.update(self.active_filters)
        return all_filters
    
    def load_filter_to_ui(self, filter_id):
        """Load a saved filter into the UI"""
        if filter_id in self.saved_filters:
            return self.saved_filters[filter_id]
        return None

# =============================================================================
# PATTERN GENERATORS - Fixed with proper delimiters and wildcards
# =============================================================================

class PatternGenerator:
    @staticmethod
    def should_use_boundaries(field_content):
        """Determine if word boundaries are appropriate for this content"""
        # Word boundaries only work with word characters at start/end
        if not field_content:
            return False
        
        # Check if content starts and ends with word characters
        starts_with_word = field_content[0].isalnum() or field_content[0] == '_'
        ends_with_word = field_content[-1].isalnum() or field_content[-1] == '_'
        
        return starts_with_word and ends_with_word
    
    @staticmethod
    def wrap_with_boundaries(pattern, use_boundaries, field_content):
        r"""Wrap pattern with boundaries if appropriate"""
        if use_boundaries and PatternGenerator.should_use_boundaries(field_content):
            return f"\\b{pattern}\\b"
        else:
            return pattern
    
    @staticmethod
    def generate_date_pattern(field_content, use_boundary=True):
        r"""Generate date pattern like (\d{4}-\d{2}-\d{2}) with smart boundaries"""
        pattern = r"(\d{4}-\d{2}-\d{2})"
        return PatternGenerator.wrap_with_boundaries(pattern, use_boundary, field_content)
    
    @staticmethod
    def generate_time_pattern(field_content, use_boundary=True):
        r"""Generate time pattern like (\d{2}:\d{2}:\d{2}) with smart boundaries"""
        pattern = r"(\d{2}:\d{2}:\d{2})"
        return PatternGenerator.wrap_with_boundaries(pattern, use_boundary, field_content)
    
    @staticmethod
    def generate_integer_pattern(field_content, use_boundary=True):
        r"""Generate integer pattern like (\d+) with smart boundaries"""
        pattern = r"(\d+)"
        return PatternGenerator.wrap_with_boundaries(pattern, use_boundary, field_content)
    
    @staticmethod
    def generate_float_pattern(field_content, use_boundary=True):
        r"""Generate float pattern like (\d+\.\d+) with smart boundaries"""
        pattern = r"(\d+\.\d+)"
        return PatternGenerator.wrap_with_boundaries(pattern, use_boundary, field_content)
    
    @staticmethod
    def generate_text_pattern(field_content, use_boundary=True):
        """Generate text pattern with smart boundaries"""
        escaped = re.escape(field_content)
        pattern = f"({escaped})"
        return PatternGenerator.wrap_with_boundaries(pattern, use_boundary, field_content)
    
    @staticmethod
    def generate_smart_pattern(field_content, use_boundary=True):
        """Generate pattern with intelligent handling of special characters"""
        # For fields with parentheses, colons, etc., we need special handling
        if '(' in field_content or ')' in field_content:
            # For parentheses, we need to escape them and handle spaces
            escaped = re.escape(field_content)
            # Ensure spaces around parentheses for better matching
            escaped = escaped.replace(r'\(', r'\s*\(').replace(r'\)', r'\)\s*')
            return f"({escaped})"
        
        elif ':' in field_content and field_content.endswith(':'):
            # For labels ending with colon, ensure space after
            escaped = re.escape(field_content)
            return f"({escaped}\\s*)"
        
        else:
            # Default text pattern with smart boundaries
            return PatternGenerator.generate_text_pattern(field_content, use_boundary)

# =============================================================================
# FIELD CONFIGURATION - Enhanced with better ignore handling
# =============================================================================

class FieldConfig:

    def __init__(self, index, original_content):
        self.index = index
        self.original = original_content
        self.name_var = tk.StringVar(value=f"field_{index+1}")
        self.type_var = tk.StringVar(value="text")
        self.category_var = tk.StringVar(value="label")
        self.boundary_var = tk.BooleanVar(value=self._auto_detect_boundaries(original_content))
        self.ignore_var = tk.BooleanVar(value=False)
        self.include_in_data_var = tk.BooleanVar(value=True)       

    def _auto_detect_boundaries(self, content):
        """Auto-detect whether boundaries should be used for this field"""
        # Don't use boundaries for fields with special characters
        if any(char in content for char in '()[]{}:;,!?'):
            return False
        # Use boundaries for clean alphanumeric fields
        return content.replace(' ', '').isalnum()
        
    def get_pattern(self):
        """Get the regex pattern for this field - return None if ignored"""
        if self.ignore_var.get():
            # Return None for ignored fields so they don't contribute to the pattern
            return None
        
        field_type = self.type_var.get()
        use_boundary = self.boundary_var.get()
        
        # Use smart pattern for text fields with special characters
        if field_type == "text" and self._has_special_chars():
            return PatternGenerator.generate_smart_pattern(self.original, use_boundary)
        
        pattern_methods = {
            "date": PatternGenerator.generate_date_pattern,
            "time": PatternGenerator.generate_time_pattern, 
            "integer": PatternGenerator.generate_integer_pattern,
            "float": PatternGenerator.generate_float_pattern,
            "currency": PatternGenerator.generate_float_pattern,
            "text": PatternGenerator.generate_text_pattern,
        }
        
        if field_type in pattern_methods:
            return pattern_methods[field_type](self.original, use_boundary)
        else:
            return PatternGenerator.generate_smart_pattern(self.original, use_boundary)

    def _has_special_chars(self):
        """Check if field contains characters that need special handling"""
        special_chars = '()[]{}:;,!?'
        return any(char in self.original for char in special_chars)

    def _generate_ignore_pattern(self):
        """Generate pattern for ignored fields with proper escaping"""
        # For ignored fields, we need to match the content but not capture it
        escaped = re.escape(self.original)
        
        # Special handling for common patterns
        if self.original == '(':
            return r'\('
        elif self.original == ')':
            return r'\)'
        elif self.original == ':' and self._is_value_label():
            return r':\s*'
        else:
            return escaped
    
    def _is_value_label(self):
        """Check if this field is likely a value label like 'Value:'"""
        return self.original.strip().endswith(':') and any(word in self.original.lower() 
                                                          for word in ['value', 'amount', 'total'])
    
    def should_capture(self):
        """Whether this field should be in the capture group"""
        return not self.ignore_var.get() and self.include_in_data_var.get()

# =============================================================================
# FIELD MANAGER - Enhanced with boundary detection feedback
# =============================================================================

class FieldManager:

    def __init__(self, plugin):
        self.plugin = plugin
        self.field_configs = []

    def add_tooltip(widget, text):
        """Helper function to easily add tooltips"""
        ToolTip(widget, text)

    def create_field_ui(self, parent, parts):
        """Create field configuration UI"""
        for widget in parent.winfo_children():
            widget.destroy()
            
        self.field_configs = []
        
        for i, part in enumerate(parts):
            self._create_single_field_ui(parent, i, part)

    def _create_single_field_ui(self, parent, index, content):
        """Create UI for a single field with boundary feedback"""
        field_frame = ttk.Frame(parent)
        field_frame.pack(fill=tk.X, pady=1)
        
        # Field position
        ttk.Label(field_frame, text=f"{index+1}", width=2).pack(side=tk.LEFT)
        
        # Field content preview with boundary indicator
        display_text = content if len(content) <= 15 else content[:12] + "..."
        
        # Color code based on boundary suitability
        bg_color = "#e8f5e8" if self._is_good_for_boundaries(content) else "#fff0f0"
        content_label = ttk.Label(field_frame, text=display_text, width=15, relief="sunken", 
                                 background=bg_color)
        content_label.pack(side=tk.LEFT, padx=(2, 5))
        
        if len(content) > 15:
            add_tooltip(content_label, content)
        
        # Field name
        name_var = tk.StringVar(value=self._suggest_field_name(content, index))
        name_entry = ttk.Entry(field_frame, textvariable=name_var, width=12)
        name_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Field type with auto-detection
        detected_type = self.plugin.type_detector.detect_field_type(content)
        type_var = tk.StringVar(value=detected_type)
        type_combo = ttk.Combobox(field_frame, textvariable=type_var, 
                                 values=["text", "date", "time", "integer", "float", "currency"], 
                                 state="readonly", width=8)
        type_combo.pack(side=tk.LEFT, padx=(0, 5))
        type_combo.bind('<<ComboboxSelected>>', lambda e: self.plugin.generate_regex())
        
        # Auto-set category based on type
        category_var = tk.StringVar()
        if detected_type in ["integer", "float", "currency"]:
            category_var.set("numeric")
        else:
            category_var.set("label")
        
        # Field category
        category_combo = ttk.Combobox(field_frame, textvariable=category_var,
                                     values=["label", "numeric"], 
                                     state="readonly", width=8)
        category_combo.pack(side=tk.LEFT, padx=(0, 5))
        category_combo.bind('<<ComboboxSelected>>', lambda e: self.plugin.generate_regex())
        
        # Boundary checkbox with intelligent default
        use_boundary = self._is_good_for_boundaries(content)
        boundary_var = tk.BooleanVar(value=use_boundary)
        boundary_cb = ttk.Checkbutton(field_frame, text="Bound", 
                                     variable=boundary_var, width=6)
        boundary_cb.pack(side=tk.LEFT, padx=(0, 5))
        boundary_cb.configure(command=self.plugin.generate_regex)
        
        # Tooltip for boundary checkbox
        boundary_tip = "Use word boundaries" if use_boundary else "Word boundaries not recommended (special characters)"
        add_tooltip(boundary_cb, boundary_tip)
        
        # Include in data checkbox
        include_var = tk.BooleanVar(value=True)
        include_cb = ttk.Checkbutton(field_frame, text="Extract", 
                                    variable=include_var, width=6)
        include_cb.pack(side=tk.LEFT, padx=(0, 5))
        include_cb.configure(command=self.plugin.generate_regex)
        
        # Ignore checkbox
        ignore_var = tk.BooleanVar(value=False)
        ignore_cb = ttk.Checkbutton(field_frame, text="Ignore", 
                                   variable=ignore_var, width=6)
        ignore_cb.pack(side=tk.LEFT, padx=(0, 5))
        ignore_cb.configure(command=self.plugin.generate_regex)
        
        # Store configuration
        field_config = FieldConfig(index, content)
        field_config.name_var = name_var
        field_config.type_var = type_var
        field_config.category_var = category_var
        field_config.boundary_var = boundary_var
        field_config.include_in_data_var = include_var
        field_config.ignore_var = ignore_var
        
        self.field_configs.append(field_config)
    
    def _is_good_for_boundaries(self, content):
        """Check if this content is suitable for word boundaries"""
        return PatternGenerator.should_use_boundaries(content)

    def _suggest_field_name(self, content, index):
        """Suggest meaningful field names based on content"""
        content_lower = content.lower()
        
        # Date/time patterns
        if re.match(r'\d{4}-\d{2}-\d{2}', content):
            return "date"
        elif re.match(r'\d{2}:\d{2}:\d{2}', content):
            return "time"
        elif content_lower in ['system', 'local', 'global']:
            return "source"
        elif 'received' in content_lower:
            return "action"
        elif any(word in content_lower for word in ['shrapnel', 'scrap', 'component', 'crap']):
            return "item_name"
        elif content.isdigit():
            return "quantity"
        elif re.match(r'\d+\.\d+', content):
            return "value"
        elif content == 'PED':
            return "currency"
        else:
            return f"field_{index+1}"

    def toggle_field_selection(self, index):
        """Toggle field selection for grouping"""
        if index in self.selected_fields:
            self.selected_fields.remove(index)
        else:
            self.selected_fields.add(index)
        
        # Update visual feedback
        for i, config in enumerate(self.field_configs):
            if i in self.selected_fields:
                # Highlight selected fields (you could change background color)
                pass

    def group_selected_fields(self):
        """Group selected fields into a single field"""
        if len(self.selected_fields) < 2:
            return
            
        selected_indices = sorted(self.selected_fields)
        
        # Create combined pattern for grouped fields
        combined_patterns = []
        for idx in selected_indices:
            config = self.field_configs[idx]
            pattern = config['pattern_var'].get()
            combined_patterns.append(pattern)
        
        # Join with delimiter (non-capturing group for flexibility)
        delimiter = re.escape(self.current_delimiter)
        combined_pattern = delimiter.join(combined_patterns)
        
        # Update the first field in the group with combined pattern
        first_config = self.field_configs[selected_indices[0]]
        first_config['pattern_var'].set(combined_pattern)
        
        # Mark other fields in the group as ignored
        for idx in selected_indices[1:]:
            self.field_configs[idx]['ignore_var'].set(True)
        
        # Clear selection
        self.selected_fields.clear()
        
        # Regenerate UI
        self.plugin.refresh_field_display()

    def get_field_names(self):
        """Get list of field names for capture groups"""
        return [cfg['name_var'].get() for cfg in self.field_configs 
                if not cfg['ignore_var'].get()]
    
    def get_field_types(self):
        """Get list of field types for capture groups"""
        return [cfg['type_var'].get() for cfg in self.field_configs 
                if not cfg['ignore_var'].get()]
    
    def get_field_categories(self):
        """Get list of field categories for analytics"""
        return [cfg['category_var'].get() for cfg in self.field_configs 
                if not cfg['ignore_var'].get()]

# =============================================================================
# TYPE DETECTOR - Handles field type detection
# =============================================================================

class TypeDetector:
    def __init__(self):
        pass
        
    def get_available_types(self):
        """Return all available field types"""
        return [
            "text", "integer", "float", "currency",
            "date", "time", "datetime", 
            "ip_address", "email", "url",
            "hex", "boolean", "uuid", "file_path", "ignore"
        ]
    
    def detect_field_type(self, field_content):
        """Automatically detect the field type based on content patterns"""
        if not field_content:
            return "text"
        
        content = field_content.strip()
        
        # Check for numeric types first
        if self.is_integer(content):
            return "integer"
        elif self.is_float(content):
            return "float"
        elif self.is_currency(content):
            return "currency"
        
        # Check for date/time patterns
        elif self.is_date(content):
            return "date"
        elif self.is_time(content):
            return "time"
        elif self.is_datetime(content):
            return "datetime"
        
        # Check for network patterns
        elif self.is_ip_address(content):
            return "ip_address"
        elif self.is_email(content):
            return "email"
        elif self.is_url(content):
            return "url"
        
        # Check for other common patterns
        elif self.is_hexadecimal(content):
            return "hex"
        elif self.is_boolean(content):
            return "boolean"
        elif self.is_uuid(content):
            return "uuid"
        elif self.is_file_path(content):
            return "file_path"
        
        # Default to text
        return "text"

    def convert_value_by_type(self, value, data_type):
        """Convert value to appropriate type based on user selection"""
        if value is None or str(value).strip() == '':
            return None
        
        try:
            if data_type == 'integer':
                return int(str(value).strip('()'))
            elif data_type == 'float':
                return float(str(value).strip('()'))
            elif data_type == 'currency':
                # Remove currency symbols and convert to float
                cleaned = re.sub(r'[^\d.-]', '', str(value))
                return float(cleaned)
            elif data_type == 'boolean':
                val_lower = str(value).lower().strip()
                return val_lower in ['true', 'yes', '1', 'on', 'enabled']
            elif data_type in ['date', 'time', 'datetime']:
                # Keep as string for now, could be converted to datetime objects later
                return str(value).strip()
            else:  # text
                return str(value).strip()
        except (ValueError, TypeError):
            # If conversion fails, return original value as string
            return str(value).strip()

    def is_integer(self, content):
        """Check if content is an integer"""
        try:
            int(content)
            return True
        except ValueError:
            return False

    def is_float(self, content):
        """Check if content is a float"""
        try:
            float(content)
            return True
        except ValueError:
            return False

    def is_currency(self, content):
        """Check if content is a currency value"""
        currency_patterns = [
            r'^\$?\-?\(?\d{1,3}(,\d{3})*(\.\d+)?\)?$',
            r'^\$?\-?\d+(\.\d+)?$',
            r'^\-?\$?\d+(\.\d+)?$',
            r'^\$?\-?\d{1,3}(\.\d{3})*(,\d+)?$',
        ]
        return any(re.match(pattern, content.strip()) for pattern in currency_patterns)

    def is_date(self, content):
        """Check if content is a date"""
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{2}/\d{2}/\d{4}$',
            r'^\d{2}-\d{2}-\d{4}$',
            r'^\d{2}\.\d{2}\.\d{4}$',
            r'^\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}$',
        ]
        return any(re.match(pattern, content, re.IGNORECASE) for pattern in date_patterns)

    def is_time(self, content):
        """Check if content is a time"""
        time_patterns = [
            r'^\d{2}:\d{2}:\d{2}$',
            r'^\d{2}:\d{2}:\d{2}\.\d+$',
            r'^\d{2}:\d{2}$',
            r'^\d{1,2}:\d{2}\s*(AM|PM)$',
        ]
        return any(re.match(pattern, content, re.IGNORECASE) for pattern in time_patterns)

    def is_datetime(self, content):
        """Check if content is a datetime"""
        datetime_patterns = [
            r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',
            r'^\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}',
            r'^\w{3}\s+\w{3}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}',
        ]
        return any(re.match(pattern, content) for pattern in datetime_patterns)

    def is_ip_address(self, content):
        """Check if content is an IP address"""
        ip_patterns = [
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
            r'^[0-9a-fA-F:]+$',
        ]
        return any(re.match(pattern, content) for pattern in ip_patterns)

    def is_email(self, content):
        """Check if content is an email address"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, content) is not None

    def is_url(self, content):
        """Check if content is a URL"""
        url_patterns = [
            r'^https?://[^\s/$.?#].[^\s]*$',
            r'^www\.[^\s/$.?#].[^\s]*$',
            r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/\S*)?$',
        ]
        return any(re.match(pattern, content, re.IGNORECASE) for pattern in url_patterns)

    def is_hexadecimal(self, content):
        """Check if content is hexadecimal"""
        hex_pattern = r'^[0-9a-fA-F]+$'
        return re.match(hex_pattern, content) is not None

    def is_boolean(self, content):
        """Check if content is boolean"""
        boolean_values = ['true', 'false', 'yes', 'no', '1', '0', 'on', 'off']
        return content.lower() in boolean_values

    def is_uuid(self, content):
        """Check if content is a UUID"""
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return re.match(uuid_pattern, content) is not None

    def is_file_path(self, content):
        """Check if content is a file path"""
        path_patterns = [
            r'^[a-zA-Z]:\\[\\\S|*\S]?.*$',
            r'^[/~][^\s]*$',
            r'^\.{1,2}[/\\][^\s]*$',
        ]
        return any(re.match(pattern, content) for pattern in path_patterns)

# =============================================================================
# REGEX BUILDER - Complete rewrite with proper empty pattern handling
# =============================================================================

class RegexBuilder:

    def __init__(self, field_manager):
        self.field_manager = field_manager
        self.generated_regex = ""
        self.current_capture_groups = []
        
# =============================================================================
# ANALYTICS ENGINE - Enhanced with variable assignment
# =============================================================================

class AnalyticsEngine:
    def __init__(self, app):  # ADDED: app parameter
        self.app = app
        self.extracted_data = []
        self.real_time_stats = {}
        self.analytics_variables = {}  # Store computed values for export
        
    def process_match_data(self, filter_id, matches, original_line, capture_groups):
        """Process data with variable assignment for analytics"""
        try:
            for match in matches:
                if isinstance(match, tuple):
                    field_values = list(match)
                else:
                    field_values = [match]
                
                record = self._create_data_record(filter_id, original_line, field_values, capture_groups)
                self.extracted_data.append(record)
                self._update_analytics_variables(record, capture_groups)
                
        except Exception as e:
            print(f"Error processing extracted data: {e}")
    
    def _create_data_record(self, filter_id, original_line, field_values, capture_groups):
        """Create a data record with proper typing"""
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'filter_id': filter_id,
            'original_line': original_line
        }
        
        # Add extracted fields using capture group info
        if capture_groups:
            for i, group_info in enumerate(capture_groups):
                if i < len(field_values):
                    field_name = group_info['name']
                    field_value = field_values[i]
                    record[field_name] = self._convert_field_value(field_value, group_info['type'])
                    
                    # Add category info for easy filtering
                    record[f'{field_name}_category'] = group_info['category']
                
        return record
    
    def _update_analytics_variables(self, record, capture_groups):
        """Update computed variables for analytics"""
        # Reset variables for this record
        record_variables = {}
        
        # Calculate numeric aggregates
        numeric_fields = {}
        for group in capture_groups:
            if (group['category'] == 'numeric' and 
                record.get(group['name']) is not None):
                try:
                    numeric_fields[group['name']] = float(record[group['name']])
                except (ValueError, TypeError):
                    continue
        
        if numeric_fields:
            record_variables['numeric_field_count'] = len(numeric_fields)
            record_variables['numeric_sum'] = sum(numeric_fields.values())
            record_variables['numeric_avg'] = record_variables['numeric_sum'] / len(numeric_fields)
            
            # Add field-specific variables
            for field_name, value in numeric_fields.items():
                record_variables[f'{field_name}_value'] = value
        
        # Count label occurrences
        label_fields = {}
        for group in capture_groups:
            if (group['category'] == 'label' and 
                record.get(group['name']) is not None):
                label_fields[group['name']] = record[group['name']]
        
        for field_name, value in label_fields.items():
            # Create a safe key for the label
            safe_value = str(value).replace(' ', '_').lower()
            key = f"{field_name}_{safe_value}"
            record_variables[key] = record_variables.get(key, 0) + 1
        
        # Store variables in record
        record['analytics_variables'] = record_variables
        
        # Update global statistics
        self._update_global_stats(record_variables)
    
    def _update_global_stats(self, variables):
        """Update global statistics across all records"""
        for key, value in variables.items():
            if key not in self.real_time_stats:
                self.real_time_stats[key] = []
            self.real_time_stats[key].append(value)
    
    def get_analytics_summary(self):
        """Get summary of analytics variables"""
        summary = {}
        
        for key, values in self.real_time_stats.items():
            if values:
                if all(isinstance(v, (int, float)) for v in values):
                    summary[f'{key}_count'] = len(values)
                    summary[f'{key}_sum'] = sum(values)
                    summary[f'{key}_avg'] = sum(values) / len(values)
                    if values:  # Check if list is not empty
                        summary[f'{key}_min'] = min(values)
                        summary[f'{key}_max'] = max(values)
                else:
                    summary[f'{key}_count'] = len(values)
        
        return summary

    def _convert_field_value(self, value, field_type):
        """Convert field value to appropriate Python type"""
        if not value:
            return value
            
        try:
            if field_type == "integer":
                return int(value)
            elif field_type in ["float", "currency"]:
                cleaned_value = re.sub(r'[^\d.-]', '', value)
                return float(cleaned_value)
            elif field_type == "boolean":
                return value.lower() in ['true', 'yes', '1', 'on']
            else:
                return value.strip()
        except (ValueError, TypeError):
            return value

    def clear_data(self):
        """Clear all collected data"""
        self.extracted_data.clear()
        self.real_time_stats = {}
        self.analytics_variables = {}

    def export_to_csv(self, filename):
        """Export extracted data to CSV file"""
        if not self.extracted_data:
            return False
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if self.extracted_data:
                    all_fields = set()
                    for record in self.extracted_data:
                        all_fields.update(record.keys())
                    
                    fieldnames = sorted(all_fields)
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.extracted_data)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
            

# =============================================================================
# MAIN PLUGIN CLASS - Enhanced with better empty state handling
# =============================================================================

class DataExtractorPlugin(ETailPlugin):

    def __init__(self, app):
        super().__init__(app)
        self.name = "Data Extractor"
        self.version = "1.6"
        self.description = "Pattern-based data extraction system"
        self.is_etail_plugin = True
        
        # Initialize components
        self.field_manager = FieldManager(self)
        self.type_detector = TypeDetector()
        self.regex_builder = RegexBuilder(self.field_manager)
        self.analytics_engine = AnalyticsEngine(self.app)
        self.filter_manager = FilterManager(self)  # REPLACES active_filters
        
        # Plugin state
        self.sample_line = ""
        
        # UI references
        self.sample_text = None
        self.delimiter_var = None
        self.regex_text = None
        self.explanation_text = None
        self.fields_container = None
        self.test_button = None
        self.register_button = None

    def setup(self):
        """Setup the plugin - load saved filters"""
        self.app.messages(2, 9, "Data Extractor plugin enabled")

        # Initialize filter name mapping
        self.filter_name_to_id = {}
    
        # Load and register saved filters
        self.load_saved_filters()
        
        # Update all selectors
        if hasattr(self, 'update_filter_selectors'):
            self.update_filter_selectors()

    def check_gui_initialization(self):
        """Check if all GUI elements are properly initialized"""
        print(f"🔍 DEBUG: Checking GUI Initialization")
        
        elements_to_check = [
            ('summary_label', 'Summary Label'),
            ('raw_text', 'Raw Text Widget'),
            ('pl_summary_text', 'Profit/Loss Summary Text'),
            ('pl_details_tree', 'Profit/Loss Details Tree'),
            ('group_filter_selector', 'Group Filter Selector'),
            ('group_field_selector', 'Group Field Selector'),
            ('grouped_tree', 'Grouped Tree View'),
            ('data_table', 'Data Table'),
            ('filters_tree', 'Filters Tree'),
            ('variables_text', 'Variables Text')
        ]
        
        for attr, description in elements_to_check:
            exists = hasattr(self, attr)
            if exists:
                value = getattr(self, attr)
                is_none = value is None
                print(f"   {description}: {'✅ EXISTS' if not is_none else '❌ EXISTS BUT NONE'}")
            else:
                print(f"   {description}: ❌ NOT FOUND")
        
        # Check analytics structure
        if hasattr(self, 'analytics_structure'):
            if self.analytics_structure:
                record_count = len(self.analytics_structure.get('data', []))
                print(f"   Analytics Structure: ✅ EXISTS with {record_count} records")
            else:
                print(f"   Analytics Structure: ❌ EXISTS BUT EMPTY")
        else:
            print(f"   Analytics Structure: ❌ NOT FOUND")

    def load_saved_filters(self):
        """Load and register all saved filters"""
        loaded_count = 0
    
        for filter_id, filter_config in self.filter_manager.saved_filters.items():
            try:

                # DEBUG: Check what we're loading
                print(f"=== LOADING FILTER {filter_id} ===")
                field_definitions = filter_config.get('field_definitions', {})
                for field_name, field_info in field_definitions.items():
                    print(f"  {field_name}: index={field_info.get('index', 'MISSING')}, type={field_info.get('data_type')}")
            
                # Register with main app
                success = self.app.register_plugin_filter(
                    self.name,
                    filter_config['regex'],
                    filter_id,
                    self.on_plugin_filter_match
                )
            
                if success:
                    self.filter_manager.active_filters[filter_id] = filter_config
                    loaded_count += 1
                
            except Exception as e:
                print(f"Error loading filter {filter_id}: {e}")
    
        if loaded_count > 0:
            self.app.messages(2, 9, f"Loaded {loaded_count} saved filters")

    def teardown(self):
        """Teardown the plugin - cleanup filters and widgets"""
        try:
            # Try to remove all active filters from main app
            for filter_id in list(self.filter_manager.active_filters.keys()):
                try:
                    self.app.remove_plugin_filter(self.name, filter_id)
                except AttributeError:
                    # Main app might not have remove_plugin_filter method
                    print(f"Note: Main app doesn't support remove_plugin_filter for {filter_id}")
                except Exception as e:
                    print(f"Error removing filter {filter_id}: {e}")
    
            # Save filters before shutdown
            self.filter_manager.save_filters()
        
            # Clear widget references to prevent TclError
            self._clear_widget_references()
    
        except Exception as e:
            print(f"Error during plugin teardown: {e}")
    
        self.app.messages(2, 9, "Data Extractor disabled")

    def register_filter(self):
        """Register the generated regex as a plugin filter with persistence"""
        if (not hasattr(self.regex_builder, 'generated_regex') or 
            not self.regex_builder.generated_regex or
            self.regex_builder.generated_regex.startswith("#")):
            self.app.messages(2, 3, "Cannot register filter: No valid pattern configured")
            return
            
        # Ask user for filter name
        filter_name = self.ask_filter_name()
        if not filter_name:
            return  # User canceled
            
        filter_id = f"data_extractor_{datetime.now().strftime('%H%M%S')}"
        
        # Get current field configuration
        field_definitions = {}
        if hasattr(self, 'analytics_structure'):
            field_definitions = self.analytics_structure.get('fields', {})
        
        # UPDATED: Enhanced filter configuration with NEW profit/loss structure
        filter_config = {
            'name': filter_name,  # User-friendly name
            'regex': self.regex_builder.generated_regex,
            'field_definitions': field_definitions,
            'field_names': list(field_definitions.keys()),
            'sample_line': getattr(self, 'sample_line', ''),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'last_used': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'match_count': 0,
            'description': self.ask_filter_description(),  # Optional description
            
            # COMPLETELY UPDATED: New profit/loss structure with multiple concepts
            'profit_loss': {
                'enabled': False,  # Master switch - turns all concepts on/off
                
                # Array of up to 3 concepts
                'concepts': [
                    # Concept 1
                    {
                        'enabled': False,      # Whether this specific concept is active
                        'name': 'Concept 1',   # User-friendly name (e.g., "Sale Amount")
                        'value_type': 'fixed', # 'fixed' or 'field'
                        'fixed_value': 0.0,    # Used when value_type = 'fixed'
                        'value_field': None,   # Field name when value_type = 'field'
                        'multiplier': 1.0,     # Multiply the value by this
                        'is_profit': True,     # True = profit, False = loss
                        'description': ''      # User description
                    },
                    # Concept 2  
                    {
                        'enabled': False,
                        'name': 'Concept 2',
                        'value_type': 'fixed',
                        'fixed_value': 0.0,
                        'value_field': None,
                        'multiplier': 1.0,
                        'is_profit': True,
                        'description': ''
                    },
                    # Concept 3
                    {
                        'enabled': False,
                        'name': 'Concept 3',
                        'value_type': 'fixed',
                        'fixed_value': 0.0,
                        'value_field': None,
                        'multiplier': 1.0,
                        'is_profit': True,
                        'description': ''
                    }
                ]
            }
        }
        
        # Register with main app
        success = self.app.register_plugin_filter(
            self.name, 
            self.regex_builder.generated_regex, 
            filter_id,
            self.on_plugin_filter_match
        )
        
        if success:
            # Save to filter manager
            self.filter_manager.save_filter(filter_id, filter_config)
            
            self.app.messages(2, 9, f"Filter '{filter_name}' registered and saved")
            
            # Update filter management UI if it exists
            if hasattr(self, 'update_filters_display'):
                self.update_filters_display()
        else:
            self.app.messages(2, 3, "Failed to register filter with main application")

    def ask_filter_name(self):
        """Ask user for a descriptive filter name"""
        dialog = tk.Toplevel()
        dialog.title("Name Your Filter")
        dialog.geometry("400x200")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (200 // 2)
        dialog.geometry(f"400x200+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Suggest a name based on fields
        suggested_name = self.suggest_filter_name()
        
        ttk.Label(main_frame, text="Enter a descriptive name for this filter:", 
                  font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        name_var = tk.StringVar(value=suggested_name)
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40, font=('Arial', 10))
        name_entry.pack(fill=tk.X, pady=(0, 20))
        name_entry.select_range(0, tk.END)
        name_entry.focus()
        
        ttk.Label(main_frame, text="Description (optional):", 
                  font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 5))
        
        desc_text = tk.Text(main_frame, height=3, width=40)
        desc_text.pack(fill=tk.BOTH, expand=True)
        
        result = [None]  # Store result in list to modify in closure
        
        def on_ok():
            name = name_var.get().strip()
            if name:
                result[0] = name
                dialog.destroy()
            else:
                tk.messagebox.showwarning("Invalid Name", "Please enter a filter name")
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key to OK
        dialog.bind('<Return>', lambda e: on_ok())
        
        # Wait for dialog to close
        self.app.root.wait_window(dialog)
        
        return result[0]
    
    def ask_filter_description(self):
        """Ask user for filter description (optional)"""
        dialog = tk.Toplevel()
        dialog.title("Filter Description")
        dialog.geometry("400x200")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Filter Description (optional):", 
                  font=('Arial', 10)).pack(anchor=tk.W, pady=(0, 10))
        
        desc_text = tk.Text(main_frame, height=6, width=40)
        desc_text.pack(fill=tk.BOTH, expand=True)
        
        result = [""]  # Store result in list
        
        def on_ok():
            result[0] = desc_text.get(1.0, tk.END).strip()
            dialog.destroy()
        
        def on_skip():
            dialog.destroy()
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Skip", command=on_skip).pack(side=tk.RIGHT)
        
        # Wait for dialog to close
        self.app.root.wait_window(dialog)
        
        return result[0]
    
    def suggest_filter_name(self):
        """Suggest a meaningful filter name based on field content"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure.get('fields'):
            return f"Data Filter {datetime.now().strftime('%H:%M')}"
        
        fields = self.analytics_structure['fields']
        field_names = list(fields.keys())
        
        # Look for common patterns to suggest names
        name_parts = []
        
        # Check for specific field types
        for field_name, field_info in fields.items():
            data_type = field_info.get('data_type', 'text')
            if data_type == 'date':
                name_parts.append("Date")
            elif data_type == 'time':
                name_parts.append("Time")
            elif data_type in ['integer', 'float', 'currency']:
                if 'value' in field_name.lower() or 'amount' in field_name.lower():
                    name_parts.append("Value")
            elif 'item' in field_name.lower():
                name_parts.append("Item")
            elif 'action' in field_name.lower():
                name_parts.append("Action")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_parts = []
        for part in name_parts:
            if part not in seen:
                seen.add(part)
                unique_parts.append(part)
        
        if unique_parts:
            return " ".join(unique_parts) + " Extractor"
        else:
            # Use field names to create name
            if field_names:
                main_fields = field_names[:2]  # Use first 2 fields
                return " ".join(main_fields) + " Extractor"
            else:
                return f"Data Filter {datetime.now().strftime('%H:%M')}"

    def check_main_app_integration(self):
        """Check if the plugin is properly integrated with the main application"""
        integration_status = {
            'plugin_registered': hasattr(self.app, 'plugins') and self.name in getattr(self.app, 'plugins', {}),
            'active_filters_count': len(self.filter_manager.active_filters),
            'analytics_data_count': len(getattr(self, 'analytics_structure', {}).get('data', [])),
            'last_data_update': getattr(self, 'last_update_time', 'Never')
        }
    
        print("=== MAIN APP INTEGRATION STATUS ===")
        for key, value in integration_status.items():
            print(f"{key}: {value}")
    
        # Check if main app has our filter registration method
        has_register_method = hasattr(self.app, 'register_plugin_filter')
        print(f"Main app has register_plugin_filter: {has_register_method}")
    
        return integration_status

    def test_main_app_integration(self):
        """Test if main app can send data to our plugin"""
        test_filter_id = "test_integration"
        test_matches = [('2025-10-04', '12:04:53', '[System]', 'You received', 'Test Item', 'x', '1', '0.0100')]
        test_line = "2025-10-04 12:04:53 [System] [] You received Test Item x (1) Value: 0.0100 PED"
    
        print("=== TESTING MAIN APP INTEGRATION ===")
    
        # Simulate receiving data from main app
        self.on_plugin_filter_match(test_filter_id, test_matches, test_line)
    
        # Check if data was processed
        if hasattr(self, 'analytics_structure') and self.analytics_structure.get('data'):
            print("✅ SUCCESS: Plugin can receive and process data from main app")
            print(f"Processed {len(self.analytics_structure['data'])} test records")
        else:
            print("❌ FAILED: Plugin did not process test data")

    def on_plugin_filter_match(self, filter_id, matches, original_line):
        """Handle matches from multiple plugin filters - FIXED ANALYTICS STRUCTURE"""
        print(f"🚀 DEBUG: on_plugin_filter_match CALLED")
        print(f"   Filter: {filter_id}")
        print(f"   Matches: {matches}")
        print(f"   Line: {original_line[:80]}...")
        
        if filter_id not in self.filter_manager.active_filters:
            if filter_id in self.filter_manager.saved_filters:
                self.filter_manager.active_filters[filter_id] = self.filter_manager.saved_filters[filter_id]
                print(f"   DEBUG: Loaded filter from saved filters")
            else:
                print(f"   DEBUG: Unknown filter ID: {filter_id}")
                return
        
        try:
            filter_config = self.filter_manager.active_filters[filter_id]
            field_definitions = filter_config.get('field_definitions', {})

            
            filter_config['match_count'] = filter_config.get('match_count', 0) + 1
            filter_config['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
            print(f"   DEBUG: Updated match count to: {filter_config['match_count']}")
            
            # PROPERLY INITIALIZE analytics structure
            if not hasattr(self, 'analytics_structure'):
                print(f"   🔧 DEBUG: Creating new analytics_structure")
                self.analytics_structure = {
                    'fields': {},
                    'data': [],
                    'summary': {
                        'total_records': 0,
                        'selected_fields': 0,
                        'field_types': {}
                    }
                }
            
            # Ensure the structure has the required keys
            if 'data' not in self.analytics_structure:
                self.analytics_structure['data'] = []
            if 'fields' not in self.analytics_structure:
                self.analytics_structure['fields'] = {}
            if 'summary' not in self.analytics_structure:
                self.analytics_structure['summary'] = {
                    'total_records': 0,
                    'selected_fields': 0,
                    'field_types': {}
                }
                
            print(f"   ✅ DEBUG: Analytics structure ready: {len(self.analytics_structure['data'])} records")
            
            # Process the match data
            processed_records = self.process_realtime_match(filter_id, matches, original_line, field_definitions)
            print(f"   ✅ DEBUG: Processed {len(processed_records)} records")
            
            # Save updated statistics
            self.filter_manager.save_filters()
            
            # DEBUG: Check analytics structure after processing
            if hasattr(self, 'analytics_structure') and self.analytics_structure:
                record_count = len(self.analytics_structure['data'])
                print(f"   📊 DEBUG: Analytics structure now has {record_count} records")
            else:
                print(f"   ❌ DEBUG: Analytics structure missing after processing!")

            # UPDATE FILTERS DISPLAY
            if hasattr(self, 'update_filters_display'):
                try:
                    self.app.root.after(0, self.update_filters_display)
                    print(f"   ✅ DEBUG: Scheduled filters display update with new match count")
                except Exception as e:
                    print(f"   ❌ DEBUG: Failed to schedule filters display update: {e}")
            
            # Update analytics display - ENHANCED TO INCLUDE P&L
            print(f"   🔄 DEBUG: Attempting to update analytics display...")
            if hasattr(self, 'update_analytics_display'):
                try:
                    self.app.root.after(0, self.safe_update_analytics)  # Now calls both analytics and P&L
                    print(f"   ✅ DEBUG: Scheduled analytics and P&L update in main thread")
                except Exception as e:
                    print(f"   ❌ DEBUG: Failed to schedule analytics update: {e}")
            else:
                print(f"   ❌ DEBUG: update_analytics_display method not found!")
                    
        except Exception as e:
            print(f"   ❌ DEBUG: Error in on_plugin_filter_match: {e}")
            import traceback
            traceback.print_exc()

    def safe_update_analytics(self):
        """Safe method to update analytics in main thread - FIXED VARIABLE REFERENCE"""
        print(f"🔄 DEBUG: safe_update_analytics called")
        try:
            # Update all analytics displays
            if hasattr(self, 'update_analytics_display'):
                self.update_analytics_display()
            
            # Auto-refresh profit/loss display if it exists
            if hasattr(self, 'update_profit_loss_display'):
                self.update_profit_loss_display()
                print(f"✅ DEBUG: Auto-refreshed profit/loss display")
            else:
                print(f"❌ DEBUG: update_profit_loss_display method not found!")
                
        except Exception as e:
            print(f"DEBUG: Error in safe_update_analytics: {e}")
            import traceback
            traceback.print_exc()

    def get_settings_widget(self, parent):
        """Create the regex builder and analytics interface - WITH PROPER WIDGET MANAGEMENT"""
        def create_widget(master):
            # Clear any existing widget references to prevent TclError
            self._clear_widget_references()
            
            notebook = ttk.Notebook(master)
        
            # Tab 1: Pattern Wizard (NEW)
            wizard_tab = ttk.Frame(notebook, padding=10)
            self.pattern_wizard = PatternWizard(self)
            wizard_content = self.pattern_wizard.create_wizard_ui(wizard_tab)
            wizard_content.pack(fill=tk.BOTH, expand=True)
            notebook.add(wizard_tab, text="Pattern Wizard")
        
            # Tab 2: Regex Builder (existing)
            regex_tab = ttk.Frame(notebook, padding=10)
            self.create_regex_builder(regex_tab)
            notebook.add(regex_tab, text="Regex Builder")
        
            # Tab 3: Filter Management (NEW)
            filters_tab = ttk.Frame(notebook, padding=10)
            self.create_filters_tab(filters_tab)
            notebook.add(filters_tab, text="Filter Management")
    
            notebook.pack(fill=tk.BOTH, expand=True)
    
            # Tab 4: Enhanced Analytics (REPLACE THE OLD ANALYTICS TAB)
            analytics_tab = ttk.Frame(notebook, padding=10)
            self.create_enhanced_analytics_tab(analytics_tab)
            notebook.add(analytics_tab, text="Analytics")
              
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # Store the notebook reference for cleanup
            self._current_notebook = notebook
            
            # DEBUG: Check if GUI elements were created
            self.check_gui_initialization()
    
            
            return notebook
        
        return create_widget
    
    def _clear_widget_references(self):
        """Clear widget references to prevent TclError when reopening GUI"""
        # List of widget attributes that should be cleared
        widget_attributes = [
            'summary_label', 'raw_text', 'pl_summary_text', 'pl_details_tree',
            'group_filter_selector', 'group_field_selector', 'grouped_tree',
            'data_table', 'filters_tree', 'variables_text', 'data_filter_selector',
            'stats_filter_selector', 'export_filter_selector', 'stats_group_selector',
            'filter_data_tree', 'summary_stats_text', 'grouped_stats_tree', 
            'time_series_text', 'export_log_text', 'regex_input', 'sample_input',
            'results_text', 'field_selection_btn', '_current_notebook'
        ]
        
        for attr in widget_attributes:
            if hasattr(self, attr):
                try:
                    # Check if widget still exists before trying to clear reference
                    widget = getattr(self, attr)
                    if widget and hasattr(widget, 'winfo_exists') and not widget.winfo_exists():
                        setattr(self, attr, None)
                except (tk.TclError, AttributeError):
                    # Widget is already destroyed, clear the reference
                    setattr(self, attr, None)

    def create_regex_builder(self, parent):
        """Create simplified regex builder interface"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Advanced Regex Editor", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Instructions
        instr_text = """Paste your regex pattern and sample text to test. When you get the desired results, 
    you can proceed to field selection using the same interface as the Pattern Wizard."""
        
        ttk.Label(main_frame, text=instr_text, justify=tk.LEFT, wraplength=600).pack(anchor=tk.W, pady=(0, 10))
        
        # Regex input section
        regex_frame = ttk.LabelFrame(main_frame, text="Regular Expression", padding=10)
        regex_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grab from main app button (if available)
        grab_frame = ttk.Frame(regex_frame)
        grab_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(grab_frame, text="Grab Current Filter", 
                  command=self.grab_current_filter).pack(side=tk.LEFT)
        
        # Regex text area
        self.regex_input = tk.Text(regex_frame, height=4, width=80, wrap=tk.WORD)
        self.regex_input.pack(fill=tk.X)
        
        # Sample text section
        sample_frame = ttk.LabelFrame(main_frame, text="Sample Text to Test Against", padding=10)
        sample_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.sample_input = tk.Text(sample_frame, height=6, width=80, wrap=tk.WORD)
        self.sample_input.pack(fill=tk.X)
        
        # Test button and results
        test_frame = ttk.Frame(main_frame)
        test_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(test_frame, text="Test Regex", 
                  command=self.test_advanced_regex).pack(side=tk.LEFT)
        
        # Results display
        results_frame = ttk.LabelFrame(main_frame, text="Test Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.results_text = tk.Text(results_frame, height=8, width=80)
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        
        self.field_selection_btn = ttk.Button(action_frame, text="Proceed to Field Selection", 
                                             command=self.proceed_to_field_selection,
                                             state=tk.DISABLED)
        self.field_selection_btn.pack(side=tk.RIGHT)
        
        return main_frame
    
    def grab_current_filter(self):
        """Grab the current filter from the main application"""
        try:
            # This would depend on your main app's API
            # For now, we'll just show a message
            current_filter = "# Grab filter functionality would be implemented here"
            self.regex_input.delete(1.0, tk.END)
            self.regex_input.insert(1.0, current_filter)
            self.app.messages(2, 9, "Filter grabbed from main app (placeholder)")
        except Exception as e:
            self.app.messages(2, 3, f"Could not grab filter: {e}")
    
    def test_advanced_regex(self):
        """Test the user-provided regex against sample text"""
        try:
            regex_pattern = self.regex_input.get(1.0, tk.END).strip()
            sample_text = self.sample_input.get(1.0, tk.END).strip()
            
            if not regex_pattern:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(1.0, "Please enter a regex pattern")
                return
                
            if not sample_text:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(1.0, "Please enter sample text to test against")
                return
            
            # Test the regex
            compiled_pattern = re.compile(regex_pattern)
            matches = compiled_pattern.findall(sample_text)
            
            # Display results
            self.results_text.delete(1.0, tk.END)
            
            if matches:
                result_text = f"✅ SUCCESS: Found {len(matches)} match(es)\n\n"
                
                # Store matches for field selection
                self.current_matches = matches
                self.current_sample_text = sample_text
                self.current_regex_pattern = regex_pattern
                
                # Show detailed results
                for i, match in enumerate(matches):
                    result_text += f"Match {i+1}:\n"
                    if isinstance(match, tuple):
                        for j, group in enumerate(match):
                            result_text += f"  Group {j+1}: '{group}'\n"
                    else:
                        result_text += f"  Full match: '{match}'\n"
                    result_text += "\n"
                
                # Enable field selection button
                self.field_selection_btn.config(state=tk.NORMAL)
                
            else:
                result_text = "❌ NO MATCHES FOUND\n\n"
                result_text += "The regex pattern did not match any part of the sample text.\n"
                result_text += "Please check your pattern and try again."
                
                # Disable field selection button
                self.field_selection_btn.config(state=tk.DISABLED)
            
            self.results_text.insert(1.0, result_text)
            
        except Exception as e:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(1.0, f"❌ REGEX ERROR: {e}")
            self.field_selection_btn.config(state=tk.DISABLED)
    
    def proceed_to_field_selection(self):
        """Proceed to field selection using the wizard's interface"""
        if not hasattr(self, 'current_matches') or not self.current_matches:
            tk.messagebox.showerror("Error", "No matches available for field selection")
            return
        
        # Get the first match to determine field structure
        first_match = self.current_matches[0]
        
        if isinstance(first_match, tuple):
            # Multiple capture groups
            field_count = len(first_match)
            columns = [f"field_{i+1}" for i in range(field_count)]
            data_rows = [list(match) for match in self.current_matches if isinstance(match, tuple)]
        else:
            # Single capture group
            columns = ["full_match"]
            data_rows = [[match] for match in self.current_matches]
        
        # Create field selection dialog
        self.show_field_selection_dialog(columns, data_rows)
    
    def show_field_selection_dialog(self, columns, data_rows):
        """Show the field selection dialog (reusing wizard logic)"""
        dialog = tk.Toplevel()
        dialog.title("Field Selection & Data Structure")
        dialog.geometry("800x600")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"800x600+{x}+{y}")
        
        # Create a temporary wizard instance to reuse its field selection logic
        temp_wizard = PatternWizard(self)
        temp_wizard.extracted_columns = columns
        temp_wizard.extracted_data = data_rows
        
        # Create the field selection interface
        selection_frame = ttk.Frame(dialog)
        selection_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(selection_frame, text="Select Fields for Analytics", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Create field selection interface using wizard methods
        temp_wizard.create_field_selection_interface(selection_frame, columns, data_rows)
        
        # Action buttons
        button_frame = ttk.Frame(selection_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def on_apply():
            # Get selected fields and their new names
            selected_fields = {}
            for original_name, use_var in temp_wizard.field_selection_vars.items():
                if use_var.get():
                    new_name = temp_wizard.field_name_vars[original_name].get()
                    selected_fields[original_name] = new_name
            
            if not selected_fields:
                tk.messagebox.showwarning("No Fields Selected", "Please select at least one field for analytics.")
                return
            
            # Prepare the data structure
            analytics_structure = temp_wizard.prepare_analytics_structure(selected_fields)
            
            # Store for use in analytics tab
            self.analytics_engine.extracted_data = analytics_structure['data']
            self.analytics_structure = analytics_structure
            
            regex_pattern = self.regex_input.get(1.0, tk.END).strip()
            PatternWizard.auto_register_filter_from_wizard(self, analytics_structure, selected_fields, regex_pattern)
            # Update analytics display
            if hasattr(self, 'update_analytics_display'):
                self.update_analytics_display()
            
            tk.messagebox.showinfo("Success", 
                                  f"Data structure applied to Analytics tab!\n\n"
                                  f"Selected {len(selected_fields)} fields.\n"
                                  f"Total records: {len(analytics_structure['data'])}")
            
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Apply to Analytics", 
                  command=on_apply).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", 
                  command=on_cancel).pack(side=tk.RIGHT)

    def create_analytics_tab(self, parent):
        """Create enhanced analytics display with the new data structure"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Advanced Analytics Dashboard", 
                              font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10), anchor=tk.W)
        
        # Real-time Status Frame
        status_frame = ttk.LabelFrame(main_frame, text="Real-time Monitoring", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
    
        # Status indicators
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X)
    
        self.status_labels = {}
    
        # Active filters status
        ttk.Label(status_grid, text="Active Filters:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_labels['filters'] = ttk.Label(status_grid, text="0", foreground="red")
        self.status_labels['filters'].grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
    
        # Data records status
        ttk.Label(status_grid, text="Data Records:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.status_labels['records'] = ttk.Label(status_grid, text="0", foreground="red")
        self.status_labels['records'].grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
    
        # Last update status
        ttk.Label(status_grid, text="Last Update:").grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        self.status_labels['last_update'] = ttk.Label(status_grid, text="Never", foreground="gray")
        self.status_labels['last_update'].grid(row=0, column=5, sticky=tk.W)
    
        # Control buttons for monitoring
        monitor_frame = ttk.Frame(status_frame)
        monitor_frame.pack(fill=tk.X, pady=(10, 0))
    
        ttk.Button(monitor_frame, text="Check Integration", 
                command=self.check_integration).pack(side=tk.LEFT, padx=(0, 10))
    
        ttk.Button(monitor_frame, text="Force Update", 
                command=self.force_update_display).pack(side=tk.LEFT, padx=(0, 10))
    
        ttk.Button(monitor_frame, text="View Active Filters", 
                command=self.show_active_filters).pack(side=tk.LEFT)
        
        # Data Summary Frame
        summary_frame = ttk.LabelFrame(main_frame, text="Data Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.summary_label = ttk.Label(summary_frame, text="No data loaded")
        self.summary_label.pack(anchor=tk.W)
        
        # Analytics Variables Frame
        variables_frame = ttk.LabelFrame(main_frame, text="Analytics Variables", padding=10)
        variables_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.variables_text = tk.Text(variables_frame, height=6, width=80)
        scrollbar = ttk.Scrollbar(variables_frame, orient=tk.VERTICAL, command=self.variables_text.yview)
        self.variables_text.configure(yscrollcommand=scrollbar.set)
        
        self.variables_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="Update Analytics", 
                  command=self.update_analytics_display).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Export to CSV", 
                  command=self.export_data).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Clear Data", 
                  command=self.clear_data).pack(side=tk.LEFT)
        
        # Replace the table view with a raw text view
        raw_frame = ttk.LabelFrame(main_frame, text="Extracted Data", padding=10)
        raw_frame.pack(fill=tk.BOTH, expand=True)
    
        # Create raw text widget
        self.raw_text = tk.Text(raw_frame, wrap=tk.WORD, height=20)
        scrollbar = ttk.Scrollbar(raw_frame, orient=tk.VERTICAL, command=self.raw_text.yview)
        self.raw_text.configure(yscrollcommand=scrollbar.set)
    
        self.raw_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Store reference for easy access
        self.analytics_tab = main_frame
        
        return main_frame

    def check_integration(self):
        """Check and display integration status"""
        status = self.check_main_app_integration()
    
        # Update status labels
        self.status_labels['filters'].config(
            text=str(status['active_filters_count']),
            foreground="green" if status['active_filters_count'] > 0 else "red"
        )
    
        self.status_labels['records'].config(
            text=str(status['analytics_data_count']),
            foreground="green" if status['analytics_data_count'] > 0 else "red"
        )
    
        self.status_labels['last_update'].config(
            text=status['last_data_update']
        )
    
        self.app.messages(2, 9, "Integration status updated")

    def force_update_display(self):
        """Force update the analytics display"""
        self.last_update_time = datetime.now().strftime("%H:%M:%S")
        self.update_analytics_display()
        self.check_integration()
    
    def show_active_filters(self):
        """Show dialog with active filters information"""
        dialog = tk.Toplevel()
        dialog.title("Active Filters")
        dialog.geometry("500x300")
        
        text_widget = tk.Text(dialog, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        if self.filter_manager.active_filters:
            text_widget.insert(1.0, "ACTIVE FILTERS:\n\n")
            for filter_id, config in self.filter_manager.active_filters.items():
                text_widget.insert(tk.END, f"Filter: {filter_id}\n")
                text_widget.insert(tk.END, f"Pattern: {config['regex']}\n")
                text_widget.insert(tk.END, f"Registered: {config.get('registered_at', 'Unknown')}\n")
                text_widget.insert(tk.END, f"Fields: {list(config.get('field_definitions', {}).keys())}\n")
                text_widget.insert(tk.END, "-" * 50 + "\n")
        else:
            text_widget.insert(1.0, "No active filters registered.")
        
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def update_analytics_display(self):
        """Simple update that works with minimal GUI"""
        print("🔄 DEBUG: update_analytics_display called")
        
        # Update summary if it exists
        if hasattr(self, 'summary_label') and self.summary_label:
            if hasattr(self, 'analytics_structure') and self.analytics_structure and self.analytics_structure['data']:
                record_count = len(self.analytics_structure['data'])
                active_filters = len(self.filter_manager.active_filters)
            
                # Calculate total matches across all filters
                total_matches = sum(
                    config.get('match_count', 0) 
                    for config in self.filter_manager.active_filters.values()
                )
            
                self.summary_label.config(
                    text=f"Records: {record_count} | Active Filters: {active_filters} | Total Matches: {total_matches} | Last: {datetime.now().strftime('%H:%M:%S')}"
                )
                print(f"✅ DEBUG: Updated summary label with {record_count} records and {total_matches} total matches")
            else:
                self.summary_label.config(text="No data available")
    
        # Update filter selectors
        self.update_filter_selectors()
    
        # Update current views if they exist - FIXED: Only call if we have a selected filter
        if hasattr(self, 'data_filter_selector') and self.data_filter_selector.get():
            selected_name = self.data_filter_selector.get()
            if hasattr(self, 'filter_name_to_id') and selected_name in self.filter_name_to_id:
                filter_id = self.filter_name_to_id[selected_name]
                self.update_filter_data_view(filter_id)
        
        if hasattr(self, 'stats_filter_selector') and self.stats_filter_selector.get():
            selected_name = self.stats_filter_selector.get()
            if hasattr(self, 'filter_name_to_id') and selected_name in self.filter_name_to_id:
                filter_id = self.filter_name_to_id[selected_name]
                self.update_statistics_view(filter_id)
    
        # Update raw text if it exists
        if hasattr(self, 'raw_text') and self.raw_text:
            self.update_raw_data_display()
        else:
            print("❌ DEBUG: raw_text not available in update_analytics_display")
        
        print("✅ DEBUG: update_analytics_display completed")
    
    def update_raw_data_display(self):
        """Enhanced raw data display that shows profit/loss information"""
        if not hasattr(self, 'raw_text') or not self.raw_text:
            return
            
        self.raw_text.delete(1.0, tk.END)
        
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure.get('data'):
            self.raw_text.insert(1.0, "No data available")
            return
        
        data = self.analytics_structure['data']
        total_records = len(data)
        
        # Header with profit/loss summary
        self.raw_text.insert(1.0, f"=== REAL-TIME DATA EXTRACTION ===\n\n")
        self.raw_text.insert(tk.END, f"Total Records: {total_records}\n")
        
        # Calculate overall profit/loss if available
        pl_data = self.calculate_enhanced_profit_loss_summary()
        if pl_data['by_filter']:
            total_net = pl_data['net']
            self.raw_text.insert(tk.END, f"Overall P&L: {total_net:.4f}\n")
        
        self.raw_text.insert(tk.END, f"Last Update: {datetime.now().strftime('%H:%M:%S')}\n\n")
        
        # Group by filter
        filters_data = {}
        for record in data:
            filter_id = record.get('filter_id', 'unknown')
            if filter_id not in filters_data:
                filters_data[filter_id] = []
            filters_data[filter_id].append(record)
        
        # Display data for each filter with profit/loss
        for filter_id, records in filters_data.items():
            # Get friendly filter name
            filter_config = self.filter_manager.active_filters.get(filter_id) or self.filter_manager.saved_filters.get(filter_id)
            filter_name = filter_config.get('name', filter_id) if filter_config else filter_id
        
            self.raw_text.insert(tk.END, f"🔍 FILTER: {filter_name}\n")
            self.raw_text.insert(tk.END, f"Records: {len(records)}\n")
            
            # Show filter match count if available
            filter_config = self.filter_manager.active_filters.get(filter_id, {})
            match_count = filter_config.get('match_count', 0)
            self.raw_text.insert(tk.END, f"Total Matches: {match_count}\n")
            
            # Show profit/loss for this filter if enabled
            pl_config = filter_config.get('profit_loss', {})
            if pl_config.get('enabled', False):
                filter_pl = self.calculate_filter_profit_loss(records)
                self.raw_text.insert(tk.END, f"P&L: {filter_pl:.4f}\n")
            
            self.raw_text.insert(tk.END, "\n")
            
            # Show field names for this filter
            if records:
                field_names = [key for key in records[0].keys() 
                              if key not in ['timestamp', 'filter_id', 'original_line']]
                self.raw_text.insert(tk.END, f"Extracted Fields: {', '.join(field_names)}\n")
                
                # Show profit/loss fields if they exist
                pl_fields = [key for key in records[0].keys() if key.startswith('profit_loss_')]
                if pl_fields:
                    self.raw_text.insert(tk.END, f"P&L Fields: {', '.join(pl_fields)}\n")
                
                self.raw_text.insert(tk.END, "\n")
                
                # Show recent records (last 3)
                recent_records = records[-3:]
                for i, record in enumerate(recent_records):
                    self.raw_text.insert(tk.END, f"Record {i+1}:\n")
                    self.raw_text.insert(tk.END, f"  Time: {record.get('timestamp', 'N/A')}\n")
                    
                    # Show extracted fields
                    for field_name in field_names:
                        if field_name in record:
                            value = record[field_name]
                            self.raw_text.insert(tk.END, f"  {field_name}: {value}\n")
                    
                    # Show profit/loss if available
                    if 'profit_loss_total' in record:
                        self.raw_text.insert(tk.END, f"  P&L Total: {record['profit_loss_total']:.4f}\n")
                    
                    self.raw_text.insert(tk.END, f"  Original: {record.get('original_line', 'N/A')[:60]}...\n")
                    self.raw_text.insert(tk.END, "\n")
                
                if len(records) > 3:
                    self.raw_text.insert(tk.END, f"... and {len(records) - 3} more records\n")
            
            self.raw_text.insert(tk.END, "\n" + "="*50 + "\n\n")

    def group_data_by_filter(self):
        """Group data by filter and prepare display information"""
        data_by_filter = {}
        
        for record in self.analytics_structure['data']:
            filter_id = record.get('filter_id', 'unknown')
            
            if filter_id not in data_by_filter:
                # Get filter configuration for this filter
                filter_config = self.filter_manager.active_filters.get(filter_id, {})
                field_definitions = filter_config.get('field_definitions', {})
                
                data_by_filter[filter_id] = {
                    'records': [],
                    'field_definitions': field_definitions,
                    'field_names': list(field_definitions.keys()),
                    'record_count': 0
                }
            
            data_by_filter[filter_id]['records'].append(record)
            data_by_filter[filter_id]['record_count'] += 1
        
        return data_by_filter
    
    def display_filter_data(self, filter_id, filter_info):
        """Display data for a specific filter"""
        records = filter_info['records']
        field_definitions = filter_info['field_definitions']
        field_names = filter_info['field_names']
        
        # Filter header
        self.raw_text.insert(tk.END, f"🔍 FILTER: {filter_id}\n")
        self.raw_text.insert(tk.END, f"Records: {len(records)} | Fields: {len(field_names)}\n")
        
        # Show field information
        if field_definitions:
            self.raw_text.insert(tk.END, "Fields: ")
            field_descriptions = []
            for field_name in field_names:
                field_info = field_definitions.get(field_name, {})
                data_type = field_info.get('data_type', 'text')
                field_descriptions.append(f"{field_name}({data_type})")
            self.raw_text.insert(tk.END, ", ".join(field_descriptions) + "\n")
        
        self.raw_text.insert(tk.END, "\n")
        
        # Show recent records (last 5)
        recent_records = records[-5:]  # Show last 5 records
        for i, record in enumerate(recent_records):
            self.raw_text.insert(tk.END, f"Record {i+1}:\n")
            
            # Display timestamp and original line first
            timestamp = record.get('timestamp', 'N/A')
            original_line = record.get('original_line', 'N/A')
            self.raw_text.insert(tk.END, f"  Time: {timestamp}\n")
            self.raw_text.insert(tk.END, f"  Line: {original_line[:80]}...\n")
            
            # Display extracted fields
            for field_name in field_names:
                if field_name in record and field_name not in ['timestamp', 'original_line']:
                    value = record[field_name]
                    field_info = field_definitions.get(field_name, {})
                    data_type = field_info.get('data_type', 'text')
                    
                    # Format based on data type
                    if data_type in ['integer', 'float', 'currency']:
                        self.raw_text.insert(tk.END, f"  📊 {field_name}: {value} ({data_type})\n")
                    else:
                        self.raw_text.insert(tk.END, f"  📝 {field_name}: {value}\n")
            
            self.raw_text.insert(tk.END, "\n")
        
        if len(records) > 5:
            self.raw_text.insert(tk.END, f"... and {len(records) - 5} more records\n")
        
        # Add filter-specific analytics
        self.display_filter_analytics(filter_id, records, field_definitions)
        
        self.raw_text.insert(tk.END, "\n" + "-"*50 + "\n\n")
    
    def display_filter_analytics(self, filter_id, records, field_definitions):
        """Display analytics for a specific filter"""
        numeric_fields = {}
        
        # Find numeric fields and their values
        for record in records:
            for field_name, field_info in field_definitions.items():
                if field_info.get('data_type') in ['integer', 'float', 'currency']:
                    if field_name in record and record[field_name] is not None:
                        if field_name not in numeric_fields:
                            numeric_fields[field_name] = []
                        try:
                            numeric_fields[field_name].append(float(record[field_name]))
                        except (ValueError, TypeError):
                            pass
        
        # Display numeric analytics
        if numeric_fields:
            self.raw_text.insert(tk.END, "📈 Numeric Analytics:\n")
            for field_name, values in numeric_fields.items():
                if values:
                    self.raw_text.insert(tk.END, f"  {field_name}:\n")
                    self.raw_text.insert(tk.END, f"    Count: {len(values)}\n")
                    self.raw_text.insert(tk.END, f"    Sum: {sum(values):.4f}\n")
                    self.raw_text.insert(tk.END, f"    Avg: {sum(values)/len(values):.4f}\n")
                    self.raw_text.insert(tk.END, f"    Min: {min(values):.4f}\n")
                    self.raw_text.insert(tk.END, f"    Max: {max(values):.4f}\n")
    
    def display_overall_analytics(self):
        """Display overall analytics across all filters"""
        total_records = len(self.analytics_structure['data'])
        active_filters = len(self.filter_manager.active_filters)
        
        self.raw_text.insert(tk.END, f"Total Records: {total_records}\n")
        self.raw_text.insert(tk.END, f"Active Filters: {active_filters}\n")
        
        # Show filters and their record counts
        filter_counts = {}
        for record in self.analytics_structure['data']:
            filter_id = record.get('filter_id', 'unknown')
            filter_counts[filter_id] = filter_counts.get(filter_id, 0) + 1
        
        self.raw_text.insert(tk.END, "\nFilter Distribution:\n")
        for filter_id, count in filter_counts.items():
            percentage = (count / total_records) * 100 if total_records > 0 else 0
            self.raw_text.insert(tk.END, f"  {filter_id}: {count} records ({percentage:.1f}%)\n")
    
    def compute_simple_analytics(self):
        """Compute simple analytics that work with any data structure"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure['data']:
            return {}
        
        data = self.analytics_structure['data']
        summary = {
            'Total Records': len(data),
            'Active Filters': len(self.filter_manager.active_filters),
            'Data Sources': len(set(record.get('filter_id', 'unknown') for record in data))
        }
        
        # Find numeric fields and compute basic stats
        numeric_fields = {}
        for record in data:
            for field, value in record.items():
                if field not in ['timestamp', 'filter_id', 'original_line']:
                    try:
                        num_val = float(value)
                        if field not in numeric_fields:
                            numeric_fields[field] = []
                        numeric_fields[field].append(num_val)
                    except (ValueError, TypeError):
                        continue
        
        for field, values in numeric_fields.items():
            if values:
                summary[f"{field} (count)"] = len(values)
                summary[f"{field} (sum)"] = sum(values)
                summary[f"{field} (avg)"] = sum(values) / len(values)
                summary[f"{field} (min)"] = min(values)
                summary[f"{field} (max)"] = max(values)
        
        return summary
    
        def update_data_table(self):
            """Update the data table with current extracted data"""
            # Clear existing table
            for item in self.data_table.get_children():
                self.data_table.delete(item)
            
            # Clear existing columns
            for column in self.data_table['columns']:
                self.data_table.heading(column, text="")
            
            self.data_table['columns'] = []
            
            if (hasattr(self, 'analytics_structure') and 
                self.analytics_structure and 
                self.analytics_structure['data']):
                
                # Get column names from first data row
                if self.analytics_structure['data']:
                    columns = list(self.analytics_structure['data'][0].keys())
                    self.data_table['columns'] = columns
                    
                    # Configure columns
                    for col in columns:
                        self.data_table.heading(col, text=col)
                        self.data_table.column(col, width=100)
                    
                    # Add data rows
                    for row in self.analytics_structure['data']:
                        values = [row.get(col, '') for col in columns]
                        self.data_table.insert('', tk.END, values=values)
    
    def update_analytics_variables(self):
        """Update analytics variables display with computed statistics"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure:
            return
        
        self.variables_text.delete(1.0, tk.END)
        
        # Compute basic statistics
        stats = self.compute_basic_statistics()
        
        if stats:
            self.variables_text.insert(1.0, "Computed Analytics:\n\n")
            
            for field_name, field_stats in stats.items():
                self.variables_text.insert(tk.END, f"📊 {field_name}:\n")
                
                for stat_name, value in field_stats.items():
                    if isinstance(value, float):
                        self.variables_text.insert(tk.END, f"  {stat_name}: {value:.4f}\n")
                    else:
                        self.variables_text.insert(tk.END, f"  {stat_name}: {value}\n")
                
                self.variables_text.insert(tk.END, "\n")
        else:
            self.variables_text.insert(1.0, "No numeric fields available for analytics")
    
    def compute_basic_statistics(self):
        """Compute basic statistics for numeric fields"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure:
            return {}
        
        stats = {}
        data = self.analytics_structure['data']
        field_types = self.analytics_structure['summary']['field_types']
        
        for field_name, field_type in field_types.items():
            if field_type in ['integer', 'float', 'currency']:
                # Extract numeric values
                values = []
                for row in data:
                    value = row.get(field_name)
                    if value is not None and isinstance(value, (int, float)):
                        values.append(value)
                
                if values:
                    stats[field_name] = {
                        'count': len(values),
                        'sum': sum(values),
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'range': max(values) - min(values)
                    }
        
        return stats

    def export_data(self):
        """Export extracted data to CSV file - UPDATED FOR NEW STRUCTURE"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure['data']:
            self.app.messages(2, 3, "No data to export")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
        
            if filename:
                success = self.export_structured_data_to_csv(filename)
                if success:
                    record_count = len(self.analytics_structure['data'])
                    self.app.messages(2, 9, f"Exported {record_count} records to {filename}")
                else:
                    self.app.messages(2, 3, "Export failed")
                
        except Exception as e:
            self.app.messages(2, 3, f"Export failed: {e}")

    def export_structured_data_to_csv(self, filename):
        """Export the structured data to CSV"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if self.analytics_structure['data']:
                    # Get all field names
                    fieldnames = list(self.analytics_structure['data'][0].keys())
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.analytics_structure['data'])
                return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def clear_data(self):
        """Clear all collected data - UPDATED FOR NEW STRUCTURE"""
        if hasattr(self, 'analytics_structure'):
            self.analytics_structure = {
                'fields': {},
                'data': [],
                'summary': {
                    'total_records': 0,
                    'selected_fields': 0,
                    'field_types': {}
                }
            }
        
        self.analytics_engine.clear_data()
        self.update_analytics_display()
        self.app.messages(2, 9, "Data cleared")

    def create_filters_tab(self, parent):
        """Create filter management tab with match counts"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Filter Management", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="Reload All Filters", 
                    command=self.reload_all_filters).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Save All Filters", 
                  command=self.save_all_filters).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Export Filters", 
                  command=self.export_filters).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="Import Filters", 
                  command=self.import_filters).pack(side=tk.LEFT)
        
        # Status indicator for monitoring
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        total_matches = sum(config.get('match_count', 0) for config in self.filter_manager.get_all_filters().values())
        active_filters = len(self.filter_manager.active_filters)
        
        status_text = f"Active Filters: {active_filters} | Total Matches: {total_matches}"
        status_label = ttk.Label(status_frame, text=status_text, foreground="blue")
        status_label.pack(anchor=tk.W)
        
        # Filters list
        list_frame = ttk.LabelFrame(main_frame, text="Saved Filters", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for filters - UPDATED COLUMNS
        columns = ('ID', 'Name', 'Description', 'Fields', 'Created', 'Last Used', 'Matches', 'P&L')
        self.filters_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # Configure columns with match count
        col_widths = {
            'ID': 120, 'Name': 150, 'Description': 150, 'Fields': 100, 
            'Created': 120, 'Last Used': 120, 'Matches': 80, 'P&L': 60
        }
        for col in columns:
            self.filters_tree.heading(col, text=col)
            self.filters_tree.column(col, width=col_widths.get(col, 100))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.filters_tree.yview)
        self.filters_tree.configure(yscrollcommand=scrollbar.set)
        
        self.filters_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons for selected filter
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(action_frame, text="Load Filter", 
                  command=self.load_selected_filter).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(action_frame, text="Activate Filter", 
                  command=self.activate_selected_filter).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(action_frame, text="Delete Filter", 
                  command=self.delete_selected_filter).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(action_frame, text="View Details", 
                  command=self.view_filter_details).pack(side=tk.LEFT, padx=(0, 10))
    
        # Add profit/loss editing button
        ttk.Button(action_frame, text="Edit P&L", 
                command=self.edit_profit_loss).pack(side=tk.LEFT, padx=(0, 10))
        
        # Add edit name button
        ttk.Button(action_frame, text="Edit Name", 
                  command=self.edit_filter_name).pack(side=tk.LEFT)
        
        # Bind double-click to load filter
        self.filters_tree.bind('<Double-1>', lambda e: self.load_selected_filter())
        
        # Initial load
        self.update_filters_display()
        
        return main_frame

    def edit_profit_loss(self):
        """Edit profit/loss settings for selected filter"""
        selection = self.filters_tree.selection()
        if not selection:
            tk.messagebox.showwarning("No Selection", "Please select a filter to edit")
            return
        
        item = selection[0]
        filter_id = self.filters_tree.item(item, 'values')[0]
        
        filter_config = self.filter_manager.get_all_filters().get(filter_id)
        if not filter_config:
            tk.messagebox.showerror("Error", f"Filter {filter_id} not found")
            return
        
        # Create editing dialog
        self.show_profit_loss_dialog(filter_id, filter_config)

    def show_profit_loss_dialog(self, filter_id, filter_config):
        """Show enhanced profit/loss configuration dialog with multiple concepts"""
        dialog = tk.Toplevel()
        dialog.title(f"Profit/Loss Settings - {filter_id}")
        dialog.geometry("600x600")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text=f"Profit/Loss Configuration for {filter_id}", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        # Enable/disable profit loss tracking
        pl_enabled = tk.BooleanVar(value=filter_config.get('profit_loss', {}).get('enabled', False))
        enable_cb = ttk.Checkbutton(main_frame, text="Enable Profit/Loss Tracking", 
                                   variable=pl_enabled)
        enable_cb.pack(anchor=tk.W, pady=(0, 10))
        
        # Concepts Notebook for multiple concepts
        concepts_notebook = ttk.Notebook(main_frame)
        concepts_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Get available numeric fields
        field_definitions = filter_config.get('field_definitions', {})
        numeric_fields = [name for name, info in field_definitions.items() 
                         if info.get('data_type') in ['integer', 'float', 'currency']]
        
        # Initialize concepts data
        concepts_data = filter_config.get('profit_loss', {}).get('concepts', [])
        if not concepts_data:
            # Initialize with empty concepts
            concepts_data = [{} for _ in range(3)]
        
        self.concept_vars = []
        
        # Create tabs for up to 3 concepts
        for i in range(3):
            concept_frame = ttk.Frame(concepts_notebook, padding=10)
            concepts_notebook.add(concept_frame, text=f"Concept {i+1}")
            
            concept_vars = self.create_concept_tab(concept_frame, concepts_data[i], numeric_fields, i)
            self.concept_vars.append(concept_vars)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def on_save():
            # Collect all concepts data
            concepts = []
            for concept_vars in self.concept_vars:
                if concept_vars['enabled'].get():
                    concept_config = {
                        'enabled': True,
                        'name': concept_vars['name'].get(),
                        'value_type': concept_vars['value_type'].get(),
                        'fixed_value': concept_vars['fixed_value'].get(),
                        'value_field': concept_vars['field_var'].get() if concept_vars['value_type'].get() == "field" else None,
                        'multiplier': concept_vars['multiplier'].get(),
                        'is_profit': concept_vars['is_profit'].get(),
                        'description': concept_vars['description'].get(1.0, tk.END).strip()
                    }
                    concepts.append(concept_config)
                else:
                    # Add disabled concept placeholder
                    concepts.append({'enabled': False})
            
            # Update filter configuration
            if 'profit_loss' not in filter_config:
                filter_config['profit_loss'] = {}
            
            filter_config['profit_loss'].update({
                'enabled': pl_enabled.get(),
                'concepts': concepts
            })
            
            # Save changes
            self.filter_manager.save_filters()
            self.update_filters_display()
            
            dialog.destroy()
            self.app.messages(2, 9, f"Profit/Loss settings updated for {filter_id}")
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=on_save).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

    def create_concept_tab(self, parent, concept_config, numeric_fields, concept_index):
        """Create configuration UI for a single profit/loss concept"""
        concept_vars = {}
        
        # Concept enabled
        concept_vars['enabled'] = tk.BooleanVar(value=concept_config.get('enabled', True))
        enable_cb = ttk.Checkbutton(parent, text=f"Enable Concept {concept_index + 1}", 
                                   variable=concept_vars['enabled'])
        enable_cb.pack(anchor=tk.W, pady=(0, 10))
        
        # Configuration frame
        config_frame = ttk.LabelFrame(parent, text=f"Concept {concept_index + 1} Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        # Concept name
        name_frame = ttk.Frame(config_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Concept Name:").pack(side=tk.LEFT)
        concept_vars['name'] = tk.StringVar(value=concept_config.get('name', f"Concept {concept_index + 1}"))
        name_entry = ttk.Entry(name_frame, textvariable=concept_vars['name'], width=20)
        name_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Value type (fixed vs field-based)
        value_type_frame = ttk.Frame(config_frame)
        value_type_frame.pack(fill=tk.X, pady=5)
        
        concept_vars['value_type'] = tk.StringVar(value=concept_config.get('value_type', 'fixed'))
        ttk.Radiobutton(value_type_frame, text="Fixed Value", 
                       variable=concept_vars['value_type'], value="fixed").pack(anchor=tk.W)
        ttk.Radiobutton(value_type_frame, text="Use Extracted Field", 
                       variable=concept_vars['value_type'], value="field").pack(anchor=tk.W)
        
        # Fixed value entry
        fixed_frame = ttk.Frame(config_frame)
        fixed_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fixed_frame, text="Fixed Amount:").pack(side=tk.LEFT)
        concept_vars['fixed_value'] = tk.DoubleVar(value=concept_config.get('fixed_value', 0.0))
        fixed_entry = ttk.Entry(fixed_frame, textvariable=concept_vars['fixed_value'], width=10)
        fixed_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Field selection
        field_frame = ttk.Frame(config_frame)
        field_frame.pack(fill=tk.X, pady=5)
        ttk.Label(field_frame, text="Use Field:").pack(side=tk.LEFT)
        concept_vars['field_var'] = tk.StringVar(value=concept_config.get('value_field', ''))
        field_combo = ttk.Combobox(field_frame, textvariable=concept_vars['field_var'], 
                                  values=numeric_fields, state="readonly")
        field_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Multiplier
        multiplier_frame = ttk.Frame(config_frame)
        multiplier_frame.pack(fill=tk.X, pady=5)
        ttk.Label(multiplier_frame, text="Multiplier:").pack(side=tk.LEFT)
        concept_vars['multiplier'] = tk.DoubleVar(value=concept_config.get('multiplier', 1.0))
        multiplier_entry = ttk.Entry(multiplier_frame, textvariable=concept_vars['multiplier'], width=10)
        multiplier_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Profit/Loss type
        type_frame = ttk.Frame(config_frame)
        type_frame.pack(fill=tk.X, pady=5)
        concept_vars['is_profit'] = tk.BooleanVar(value=concept_config.get('is_profit', True))
        ttk.Radiobutton(type_frame, text="Profit (Positive)", 
                       variable=concept_vars['is_profit'], value=True).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Loss (Negative)", 
                       variable=concept_vars['is_profit'], value=False).pack(side=tk.LEFT, padx=(10, 0))
        
        # Description
        desc_frame = ttk.Frame(config_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(desc_frame, text="Description:").pack(anchor=tk.W)
        desc_text = tk.Text(desc_frame, height=3, width=50)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        desc_text.insert(1.0, concept_config.get('description', ''))
        concept_vars['description'] = desc_text
        
        # Update field visibility based on value type
        def update_concept_visibility():
            if concept_vars['value_type'].get() == "fixed":
                fixed_entry.config(state=tk.NORMAL)
                field_combo.config(state=tk.DISABLED)
                multiplier_entry.config(state=tk.DISABLED)
            else:
                fixed_entry.config(state=tk.DISABLED)
                field_combo.config(state=tk.NORMAL)
                multiplier_entry.config(state=tk.NORMAL)
        
        concept_vars['value_type'].trace('w', lambda *args: update_concept_visibility())
        update_concept_visibility()
        
        return concept_vars

    def load_selected_filter(self):
        """Load selected filter into the regex builder"""
        selection = self.filters_tree.selection()
        if not selection:
            tk.messagebox.showwarning("No Selection", "Please select a filter to load")
            return
        
        item = selection[0]
        filter_id = self.filters_tree.item(item, 'values')[0]
        
        filter_config = self.filter_manager.load_filter_to_ui(filter_id)
        if filter_config:
            # Load into regex builder
            self.load_filter_to_regex_builder(filter_config)
            self.app.messages(2, 9, f"Filter {filter_id} loaded into Regex Builder")
        else:
            tk.messagebox.showerror("Error", f"Could not load filter {filter_id}")
    
    def load_filter_to_regex_builder(self, filter_config):
        """Load a filter configuration into the regex builder tab"""
        # Set the regex pattern
        if hasattr(self, 'regex_input'):
            self.regex_input.delete(1.0, tk.END)
            self.regex_input.insert(1.0, filter_config.get('regex', ''))
        
        # Set sample line if available
        sample_line = filter_config.get('sample_line', '')
        if sample_line and hasattr(self, 'sample_input'):
            self.sample_input.delete(1.0, tk.END)
            self.sample_input.insert(1.0, sample_line)
        
        # Store field definitions for later use
        self.current_field_definitions = filter_config.get('field_definitions', {})
    
    def activate_selected_filter(self):
        """Activate the selected filter (register with main app)"""
        selection = self.filters_tree.selection()
        if not selection:
            tk.messagebox.showwarning("No Selection", "Please select a filter to activate")
            return

        item = selection[0]
        filter_id = self.filters_tree.item(item, 'values')[0]
    
        # Check if filter is already active
        if filter_id in self.filter_manager.active_filters:
            tk.messagebox.showinfo("Already Active", f"Filter {filter_id} is already active")
            return
    
        filter_config = self.filter_manager.saved_filters.get(filter_id)
        if not filter_config:
            tk.messagebox.showerror("Error", f"Filter {filter_id} not found in saved filters")
            return
    
        try:
            # Register with main app
            success = self.app.register_plugin_filter(
                self.name,
                filter_config['regex'],
                filter_id,
                self.on_plugin_filter_match
            )
        
            if success:
                self.filter_manager.active_filters[filter_id] = filter_config
                self.app.messages(2, 9, f"Filter {filter_id} activated")
                self.update_filters_display()
            else:
                tk.messagebox.showerror("Error", f"Failed to activate filter {filter_id}")
            
        except Exception as e:
            tk.messagebox.showerror("Error", f"Error activating filter: {e}")

    def reload_all_filters(self):
        """Reload all filters from disk"""
        self.filter_manager.saved_filters = self.filter_manager.load_filters()
        self.update_filters_display()
        self.app.messages(2, 9, "Filters reloaded from disk")
    
    def save_all_filters(self):
        """Save all active filters to disk"""
        if self.filter_manager.save_filters():
            self.app.messages(2, 9, "All filters saved successfully")
        else:
            self.app.messages(2, 3, "Failed to save filters")
    
    def export_filters(self):
        """Export filters to a file"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Filters To"
            )
            
            if filename:
                all_filters = self.filter_manager.get_all_filters()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(all_filters, f, indent=2, ensure_ascii=False)
                
                self.app.messages(2, 9, f"Filters exported to {filename}")
                
        except Exception as e:
            self.app.messages(2, 3, f"Export failed: {e}")
    
    def import_filters(self):
        """Import filters from a file"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Filters From"
            )
            
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported_filters = json.load(f)
                
                # Merge with existing filters
                for filter_id, filter_config in imported_filters.items():
                    # Avoid overwriting existing filters with same ID
                    if filter_id not in self.filter_manager.saved_filters:
                        self.filter_manager.saved_filters[filter_id] = filter_config
                
                # Save the merged filters
                self.filter_manager.save_filters()
                self.update_filters_display()
                
                self.app.messages(2, 9, f"Imported {len(imported_filters)} filters")
                
        except Exception as e:
            self.app.messages(2, 3, f"Import failed: {e}")
    
    def delete_selected_filter(self):
        """Delete the selected filter"""
        selection = self.filters_tree.selection()
        if not selection:
            tk.messagebox.showwarning("No Selection", "Please select a filter to delete")
            return
        
        item = selection[0]
        filter_id = self.filters_tree.item(item, 'values')[0]
        
        # Confirm deletion
        if not tk.messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete filter '{filter_id}'?"):
            return
        
        # Remove from main app if active
        if filter_id in self.filter_manager.active_filters:
            try:
                self.app.remove_plugin_filter(self.name, filter_id)
            except:
                pass  # Main app might not have remove_plugin_filter method
        
        # Delete from filter manager
        if self.filter_manager.delete_filter(filter_id):
            self.filters_tree.delete(item)
            self.app.messages(2, 9, f"Filter {filter_id} deleted")
        else:
            self.app.messages(2, 3, f"Failed to delete filter {filter_id}")
    
    def view_filter_details(self):
        """Show detailed view of selected filter"""
        selection = self.filters_tree.selection()
        if not selection:
            tk.messagebox.showwarning("No Selection", "Please select a filter to view")
            return
        
        item = selection[0]
        filter_id = self.filters_tree.item(item, 'values')[0]
        
        filter_config = self.filter_manager.get_all_filters().get(filter_id)
        if not filter_config:
            tk.messagebox.showerror("Error", f"Filter {filter_id} not found")
            return
        
        # Create details dialog
        dialog = tk.Toplevel()
        dialog.title(f"Filter Details: {filter_id}")
        dialog.geometry("600x500")
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Format and display filter details
        details = self.format_filter_details(filter_id, filter_config)
        text_widget.insert(1.0, details)
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def format_filter_details(self, filter_id, filter_config):
        """Format filter details for display"""
        details = f"FILTER DETAILS: {filter_id}\n"
        details += "=" * 50 + "\n\n"
        
        # Basic info
        details += "BASIC INFORMATION:\n"
        details += f"  Created: {filter_config.get('created_at', 'Unknown')}\n"
        details += f"  Last Used: {filter_config.get('last_used', 'Never')}\n"
        details += f"  Match Count: {filter_config.get('match_count', 0)}\n"
        details += f"  Status: {'ACTIVE' if filter_id in self.filter_manager.active_filters else 'INACTIVE'}\n\n"
        
        # Regex pattern
        details += "REGEX PATTERN:\n"
        details += f"  {filter_config.get('regex', 'No pattern')}\n\n"
        
        # Sample line
        sample_line = filter_config.get('sample_line', '')
        if sample_line:
            details += "SAMPLE LINE:\n"
            details += f"  {sample_line}\n\n"
        
        # Field definitions
        field_definitions = filter_config.get('field_definitions', {})
        if field_definitions:
            details += "FIELD DEFINITIONS:\n"
            for field_name, field_info in field_definitions.items():
                details += f"  {field_name}:\n"
                details += f"    Type: {field_info.get('data_type', 'unknown')}\n"
                details += f"    Original: {field_info.get('original_name', 'unknown')}\n"
                details += f"    Index: {field_info.get('index', 'unknown')}\n"
            details += "\n"
        else:
            details += "FIELD DEFINITIONS: None\n\n"
        
        # Field names
        field_names = filter_config.get('field_names', [])
        if field_names:
            details += f"FIELD NAMES: {', '.join(field_names)}\n"
        
        return details

    def process_realtime_match(self, filter_id, matches, original_line, field_definitions):
        """Process real-time match data - WITH PROFIT/LOSS CALCULATION"""
        print(f"   🔧 DEBUG: process_realtime_match called for {len(matches)} matches")
        processed_records = []
        
        for i, match in enumerate(matches):
            print(f"      Processing match {i+1}/{len(matches)}: {match}")
            
            record = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'filter_id': filter_id,
                'original_line': original_line
            }
            
            # Process match data
            if isinstance(match, tuple):
                print(f"      Match is tuple with {len(match)} elements")
                
                for field_name, field_info in field_definitions.items():
                    field_index = field_info.get('index')
                    
                    if field_index is not None and field_index < len(match):
                        value = match[field_index]
                        data_type = field_info.get('data_type', 'text')
                        
                        # Convert the value
                        try:
                            converted_value = TypeDetector.convert_value_by_type(self, value, data_type)
                            record[field_name] = converted_value
                            print(f"      ✅ Extracted {field_name}[{field_index}] = '{value}' -> {converted_value}")
                        except Exception as e:
                            record[field_name] = value
                            print(f"      ⚠️  Conversion failed for {field_name}: {e}")
                    else:
                        print(f"      ❌ Cannot extract {field_name} - index: {field_index}, match length: {len(match)}")
            
            # CRITICAL: CALCULATE PROFIT/LOSS FOR THIS RECORD
            self.calculate_profit_loss_concept(filter_id, record, field_definitions)
            
            # In process_realtime_match, after processing the record:
            self.debug_profit_loss_calculation(filter_id, record)            
            
            # ALWAYS add to analytics data - no conditions
            if hasattr(self, 'analytics_structure'):
                self.analytics_structure['data'].append(record)
                current_count = len(self.analytics_structure['data'])
                print(f"      ✅ Added record to analytics. Total records: {current_count}")
                
                # DEBUG: Check if profit/loss was calculated
                if 'profit_loss_total' in record:
                    print(f"      💰 P&L Calculated: {record['profit_loss_total']:.4f}")
                else:
                    print(f"      ❌ No P&L calculated for record")
                    
                processed_records.append(record)
            else:
                print(f"      ❌ analytics_structure not available for storing record!")
        
        return processed_records

    def edit_filter_name(self):
        """Edit the name and description of an existing filter"""
        selection = self.filters_tree.selection()
        if not selection:
            tk.messagebox.showwarning("No Selection", "Please select a filter to edit")
            return
        
        item = selection[0]
        filter_id = self.filters_tree.item(item, 'values')[0]
        
        filter_config = self.filter_manager.get_all_filters().get(filter_id)
        if not filter_config:
            tk.messagebox.showerror("Error", f"Filter {filter_id} not found")
            return
        
        # Create editing dialog
        dialog = tk.Toplevel()
        dialog.title(f"Edit Filter: {filter_config.get('name', filter_id)}")
        dialog.geometry("500x300")
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Filter name
        ttk.Label(main_frame, text="Filter Name:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        name_var = tk.StringVar(value=filter_config.get('name', filter_id))
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40, font=('Arial', 10))
        name_entry.pack(fill=tk.X, pady=(5, 15))
        name_entry.select_range(0, tk.END)
        name_entry.focus()
        
        # Description
        ttk.Label(main_frame, text="Description:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        desc_text = tk.Text(main_frame, height=4, width=40)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        desc_text.insert(1.0, filter_config.get('description', ''))
        
        # Field names editing
        ttk.Label(main_frame, text="Field Names:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        field_frame = ttk.Frame(main_frame)
        field_frame.pack(fill=tk.X, pady=(5, 15))
        
        field_vars = {}
        field_definitions = filter_config.get('field_definitions', {})
        
        for field_name, field_info in field_definitions.items():
            field_row = ttk.Frame(field_frame)
            field_row.pack(fill=tk.X, pady=2)
            
            ttk.Label(field_row, text=f"{field_info.get('original_name', field_name)}:", 
                     width=20, anchor=tk.W).pack(side=tk.LEFT)
            
            field_var = tk.StringVar(value=field_name)
            field_entry = ttk.Entry(field_row, textvariable=field_var, width=20)
            field_entry.pack(side=tk.LEFT, padx=(5, 0))
            
            field_vars[field_name] = field_var
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def on_save():
            # Update filter configuration
            filter_config['name'] = name_var.get()
            filter_config['description'] = desc_text.get(1.0, tk.END).strip()
            
            # Update field names
            new_field_definitions = {}
            for old_name, field_info in field_definitions.items():
                new_name = field_vars[old_name].get()
                field_info['original_name'] = old_name  # Keep track of original
                new_field_definitions[new_name] = field_info
            
            filter_config['field_definitions'] = new_field_definitions
            filter_config['field_names'] = list(new_field_definitions.keys())
            
            # Save changes
            self.filter_manager.save_filters()
            self.update_filters_display()
            
            dialog.destroy()
            self.app.messages(2, 9, f"Filter '{name_var.get()}' updated")
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=on_save).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

    #**************************************************************************

    def create_enhanced_analytics_tab(self, parent):
        """Create enhanced analytics tab with filter-specific features"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for different views
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Filter Data View
        filter_tab = ttk.Frame(notebook, padding=10)
        self.create_filter_data_tab(filter_tab)
        notebook.add(filter_tab, text="Filter Data")
        
        # Tab 2: Statistics & Analytics
        stats_tab = ttk.Frame(notebook, padding=10)
        self.create_statistics_tab(stats_tab)
        notebook.add(stats_tab, text="Statistics")
        
        # Tab 3: Profit/Loss Analytics (NEW)
        pl_tab = ttk.Frame(notebook, padding=10)
        self.create_profit_loss_tab(pl_tab)
        notebook.add(pl_tab, text="Profit/Loss")
        
        # Tab 4: Export Data
        export_tab = ttk.Frame(notebook, padding=10)
        self.create_export_tab(export_tab)
        notebook.add(export_tab, text="Export")

        # Tab 5: Raw
        export_tab = ttk.Frame(notebook, padding=10)
        self.create_raw_data_tab(export_tab)
        notebook.add(export_tab, text="Raw Data")

        # Tab 6: Grouped
        export_tab = ttk.Frame(notebook, padding=10)
        self.create_grouped_view_tab(export_tab)
        notebook.add(export_tab, text="Grouped")
        
        return main_frame
    
    def create_filter_data_tab(self, parent):
        """Create filter-specific data view"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="View data for filter:").pack(side=tk.LEFT)
        
        # Filter selector
        self.data_filter_selector = ttk.Combobox(control_frame, state="readonly", width=30)
        self.data_filter_selector.pack(side=tk.LEFT, padx=(5, 10))
        self.data_filter_selector.bind('<<ComboboxSelected>>', self.on_data_filter_selected)
        
        # Refresh button
        ttk.Button(control_frame, text="Refresh", 
                  command=self.update_filter_data_view).pack(side=tk.LEFT, padx=(0, 10))
        
        # Record count
        self.record_count_label = ttk.Label(control_frame, text="Records: 0")
        self.record_count_label.pack(side=tk.RIGHT)
        
        # Data table frame
        table_frame = ttk.LabelFrame(main_frame, text="Extracted Data", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for data
        self.filter_data_tree = ttk.Treeview(table_frame, show='headings', height=15)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.filter_data_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.filter_data_tree.xview)
        self.filter_data_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and treeview
        self.filter_data_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return main_frame

    def create_profit_loss_tab(self, parent):
        """Create profit/loss summary tab with enhanced columns"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(main_frame, text="Profit/Loss Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.pl_summary_text = tk.Text(summary_frame, height=10, wrap=tk.WORD)  # Increased height
        scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.pl_summary_text.yview)
        self.pl_summary_text.configure(yscrollcommand=scrollbar.set)
        
        self.pl_summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Details frame
        details_frame = ttk.LabelFrame(main_frame, text="Detailed Breakdown by Concept", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for detailed breakdown with concept column
        columns = ('Filter', 'Concept', 'Description', 'Count', 'Total', 'Average', 'Min', 'Max')
        self.pl_details_tree = ttk.Treeview(details_frame, columns=columns, show='headings', height=12)  # Increased height
        
        # Configure columns
        col_widths = {
            'Filter': 120, 'Concept': 100, 'Description': 150, 
            'Count': 60, 'Total': 80, 'Average': 80, 'Min': 80, 'Max': 80
        }
        
        for col in columns:
            self.pl_details_tree.heading(col, text=col)
            self.pl_details_tree.column(col, width=col_widths.get(col, 100))
        
        scrollbar_details = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.pl_details_tree.yview)
        self.pl_details_tree.configure(yscrollcommand=scrollbar_details.set)
        
        self.pl_details_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_details.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Refresh button
        refresh_frame = ttk.Frame(main_frame)
        refresh_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(refresh_frame, text="Refresh P&L", 
                  command=self.update_profit_loss_display).pack(side=tk.RIGHT)
    
        return main_frame

    def create_grouped_view_tab(self, parent):
        """Create grouped view tab - WITH AUTO-UPDATE ON FIELD SELECTION"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="Group by:").pack(side=tk.LEFT)
        
        # Filter selector
        self.group_filter_selector = ttk.Combobox(control_frame, state="readonly", width=20)
        self.group_filter_selector.pack(side=tk.LEFT, padx=(5, 10))
        self.group_filter_selector.bind('<<ComboboxSelected>>', self.on_group_filter_selected)
        
        # Field selector - WITH AUTO-UPDATE BINDING
        self.group_field_selector = ttk.Combobox(control_frame, state="readonly", width=15)
        self.group_field_selector.pack(side=tk.LEFT, padx=(0, 10))
        # AUTO-UPDATE: Bind field selection changes to update the treeview
        self.group_field_selector.bind('<<ComboboxSelected>>', lambda e: self.update_grouped_view())
        
        ttk.Button(control_frame, text="Refresh", 
                  command=lambda: self.update_grouped_view()).pack(side=tk.LEFT)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Grouped Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for grouped results
        self.grouped_tree = ttk.Treeview(results_frame, show='headings', height=15)
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.grouped_tree.yview)
        self.grouped_tree.configure(yscrollcommand=scrollbar.set)
        
        self.grouped_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return main_frame

    def on_group_field_selected(self, event=None):
        """Handle field selection in grouped view"""
        self.update_grouped_view()

    def create_raw_data_tab(self, parent):
        """Create raw data tab (replaces the old analytics tab)"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Real-time Data Extraction", 
                              font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10), anchor=tk.W)
        
        # Real-time Status Frame
        status_frame = ttk.LabelFrame(main_frame, text="Real-time Monitoring", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status indicators (keep your existing status display)
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X)
        
        self.status_labels = {}
        
        # Active filters status
        ttk.Label(status_grid, text="Active Filters:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_labels['filters'] = ttk.Label(status_grid, text="0", foreground="red")
        self.status_labels['filters'].grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Data records status
        ttk.Label(status_grid, text="Data Records:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.status_labels['records'] = ttk.Label(status_grid, text="0", foreground="red")
        self.status_labels['records'].grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Last update status
        ttk.Label(status_grid, text="Last Update:").grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        self.status_labels['last_update'] = ttk.Label(status_grid, text="Never", foreground="gray")
        self.status_labels['last_update'].grid(row=0, column=5, sticky=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="Check Integration", 
                  command=self.check_integration).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Force Update", 
                  command=self.force_update_display).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Clear Data", 
                  command=self.clear_data).pack(side=tk.LEFT)
        
        # Raw data display area
        raw_frame = ttk.LabelFrame(main_frame, text="Extracted Data", padding=10)
        raw_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create raw text widget
        self.raw_text = tk.Text(raw_frame, wrap=tk.WORD, height=20)
        scrollbar = ttk.Scrollbar(raw_frame, orient=tk.VERTICAL, command=self.raw_text.yview)
        self.raw_text.configure(yscrollcommand=scrollbar.set)
        
        self.raw_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return main_frame

    def create_export_tab(self, parent):
        """Create data export tab"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Export controls
        control_frame = ttk.LabelFrame(main_frame, text="Export Options", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Filter selection for export
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Export data for filter:").pack(side=tk.LEFT)
        self.export_filter_selector = ttk.Combobox(filter_frame, state="readonly", width=30)
        self.export_filter_selector.pack(side=tk.LEFT, padx=(5, 10))
        
        # Export options
        options_frame = ttk.Frame(control_frame)
        options_frame.pack(fill=tk.X)
        
        self.export_include_timestamp = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include timestamp", 
                       variable=self.export_include_timestamp).pack(side=tk.LEFT, padx=(0, 10))
        
        self.export_include_original = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Include original line", 
                       variable=self.export_include_original).pack(side=tk.LEFT, padx=(0, 10))
        
        # Export buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Export to CSV", 
                  command=self.export_filter_to_csv).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Export All Filters", 
                  command=self.export_all_filters_to_csv).pack(side=tk.LEFT)
        
        # Export log
        log_frame = ttk.LabelFrame(main_frame, text="Export Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.export_log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.export_log_text.yview)
        self.export_log_text.configure(yscrollcommand=scrollbar.set)
        
        self.export_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return main_frame
    
    #**************************************************************************

    def calculate_profit_loss_concept(self, filter_id, record, field_definitions):
        """Calculate multiple profit/loss concepts for a record"""
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        pl_config = filter_config.get('profit_loss', {})
        
        if not pl_config.get('enabled', False):
            return
        
        concepts = pl_config.get('concepts', [])
        total_profit_loss = 0.0
        
        for i, concept in enumerate(concepts):
            if not concept.get('enabled', False):
                continue
                
            amount = 0.0
            concept_name = concept.get('name', f'concept_{i+1}')
            
            if concept.get('value_type') == 'field' and concept.get('value_field'):
                # Use extracted field value
                field_name = concept['value_field']
                if field_name in record and record[field_name] is not None:
                    try:
                        amount = float(record[field_name]) * concept.get('multiplier', 1.0)
                    except (ValueError, TypeError):
                        amount = 0.0
            else:
                # Use fixed value
                amount = concept.get('fixed_value', 0.0)
            
            # Apply profit/loss sign
            if not concept.get('is_profit', True):
                amount = -amount
            
            # Store individual concept amount
            record[f'profit_loss_{concept_name}'] = amount
            record[f'profit_loss_{concept_name}_description'] = concept.get('description', '')
            
            total_profit_loss += amount
        
        # Store total
        record['profit_loss_total'] = total_profit_loss
        record['profit_loss_concept_count'] = len([c for c in concepts if c.get('enabled', False)])

    def calculate_filter_profit_loss(self, records):
        """Calculate total profit/loss for a set of records"""
        total = 0.0
        for record in records:
            if 'profit_loss_total' in record:
                total += record['profit_loss_total']
        return total

    def update_profit_loss_display(self):
        """Update the profit/loss display with multiple concepts and overall total"""
        if not hasattr(self, 'pl_summary_text') or not hasattr(self, 'pl_details_tree'):
            return
        
        # Clear existing data
        self.pl_summary_text.delete(1.0, tk.END)
        for item in self.pl_details_tree.get_children():
            self.pl_details_tree.delete(item)
        
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure['data']:
            self.pl_summary_text.insert(1.0, "No data available")
            return
        
        # Calculate enhanced profit/loss summary with multiple concepts
        pl_data = self.calculate_enhanced_profit_loss_summary()
        
        # NEW: Calculate overall totals across all filters
        overall_totals = self.calculate_overall_profit_loss_totals()
        
        # Update summary text with overall totals
        self.pl_summary_text.insert(1.0, self.format_enhanced_profit_loss_summary(pl_data, overall_totals))
        
        # Update details tree with multiple concepts
        for filter_id, data in pl_data['by_filter'].items():
            if data['total_count'] > 0:
                # Get friendly filter name
                filter_config = self.filter_manager.active_filters.get(filter_id) or self.filter_manager.saved_filters.get(filter_id)
                filter_name = filter_config.get('name', filter_id) if filter_config else filter_id            
                
                # Add row for each concept
                for concept_name, concept_data in data['concepts'].items():
                    if concept_data['count'] > 0:
                        self.pl_details_tree.insert('', tk.END, values=(
                            filter_name,  # Use friendly name instead of ID
                            concept_name,
                            f"{concept_data['description']}",
                            concept_data['count'],
                            f"{concept_data['total']:.4f}",
                            f"{concept_data['average']:.4f}",
                            f"{concept_data['min']:.4f}",
                            f"{concept_data['max']:.4f}"
                        ))
                
                # Add filter total row
                self.pl_details_tree.insert('', tk.END, values=(
                    filter_name,  # Use friendly name instead of ID
                    "FILTER TOTAL",
                    "Sum of all concepts for this filter",
                    data['total_count'],
                    f"{data['total_sum']:.4f}",
                    f"{data['total_average']:.4f}",
                    f"{data['total_min']:.4f}",
                    f"{data['total_max']:.4f}"
                ), tags=('filter_total',))
        
        # NEW: Add overall grand total row
        if overall_totals['total_count'] > 0:
            self.pl_details_tree.insert('', tk.END, values=(
                "ALL FILTERS",
                "GRAND TOTAL",
                "Sum of all filters and concepts",
                overall_totals['total_count'],
                f"{overall_totals['total_sum']:.4f}",
                f"{overall_totals['total_average']:.4f}",
                f"{overall_totals['total_min']:.4f}",
                f"{overall_totals['total_max']:.4f}"
            ), tags=('grand_total',))
    
        # Configure tags for different row types
        self.pl_details_tree.tag_configure('filter_total', background='#e0e0e0', font=('Arial', 9, 'bold'))
        self.pl_details_tree.tag_configure('grand_total', background='#a0d0ff', font=('Arial', 10, 'bold'))

    def calculate_profit_loss_summary(self):
        """Calculate comprehensive profit/loss summary"""
        data = self.analytics_structure['data']
        summary = {
            'total_profit': 0.0,
            'total_loss': 0.0,
            'net': 0.0,
            'by_filter': {}
        }
        
        # Group by filter and calculate
        amount = 0
        for record in data:
            if 'profit_loss_total' in record:
                filter_id = record['filter_id']
                total_amount = record['profit_loss_total']
                
                if filter_id not in summary['by_filter']:
                    filter_config = self.filter_manager.active_filters.get(filter_id) or self.filter_manager.saved_filters.get(filter_id)
                    filter_name = filter_config.get('name', filter_id) if filter_config else filter_id
                    
                    pl_config = filter_config.get('profit_loss', {}) if filter_config else {}
                    concepts_config = pl_config.get('concepts', [])
                    
                    summary['by_filter'][filter_id] = {
                        'name': filter_name,  # Store friendly name
                        'description': filter_config.get('description', filter_id) if filter_config else filter_id,
                        'concepts': {},
                        'total_values': [],
                        'total_count': 0,
                        'total_sum': 0.0,
                        'total_average': 0.0,
                        'total_min': 0.0,
                        'total_max': 0.0
                    }
                    
                    # Initialize concepts
                    for concept in concepts_config:
                        if concept.get('enabled', False):
                            concept_name = concept.get('name', 'unknown')
                            summary['by_filter'][filter_id]['concepts'][concept_name] = {
                                'description': concept.get('description', ''),
                                'values': [],
                                'count': 0,
                                'total': 0.0,
                                'average': 0.0,
                                'min': 0.0,
                                'max': 0.0
                            }
                filter_data = summary['by_filter'][filter_id]
                filter_data['values'].append(amount)
                filter_data['count'] += 1
                filter_data['total'] += amount
                
                # Update overall totals
                if amount >= 0:
                    summary['total_profit'] += amount
                else:
                    summary['total_loss'] += amount
                summary['net'] += amount
        
        # Calculate averages and min/max
        for filter_data in summary['by_filter'].values():
            if filter_data['count'] > 0:
                values = filter_data['values']
                filter_data['average'] = sum(values) / len(values)
                filter_data['min'] = min(values)
                filter_data['max'] = max(values)
        
        return summary
    
    def format_profit_loss_summary(self, pl_data):
        """Format profit/loss summary for display"""
        text = "=== PROFIT/LOSS SUMMARY ===\n\n"
        text += f"Total Profit: {pl_data['total_profit']:.4f}\n"
        text += f"Total Loss: {pl_data['total_loss']:.4f}\n"
        text += f"Net: {pl_data['net']:.4f}\n\n"
        
        text += f"Filters with P&L tracking: {len(pl_data['by_filter'])}\n"
        text += f"Total records with P&L: {sum(data['count'] for data in pl_data['by_filter'].values())}\n"
        
        return text

    def calculate_overall_profit_loss_totals(self):
        """Calculate overall profit/loss totals across all filters"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure['data']:
            return {
                'total_count': 0,
                'total_sum': 0.0,
                'total_average': 0.0,
                'total_min': 0.0,
                'total_max': 0.0,
                'filter_count': 0
            }
        
        data = self.analytics_structure['data']
        
        # Extract all profit/loss values
        pl_values = []
        for record in data:
            if 'profit_loss_total' in record:
                pl_values.append(record['profit_loss_total'])
        
        if not pl_values:
            return {
                'total_count': 0,
                'total_sum': 0.0,
                'total_average': 0.0,
                'total_min': 0.0,
                'total_max': 0.0,
                'filter_count': 0
            }
        
        # Count unique filters with P&L data
        filters_with_pl = set()
        for record in data:
            if 'profit_loss_total' in record:
                filters_with_pl.add(record.get('filter_id', 'unknown'))
        
        return {
            'total_count': len(pl_values),
            'total_sum': sum(pl_values),
            'total_average': sum(pl_values) / len(pl_values),
            'total_min': min(pl_values),
            'total_max': max(pl_values),
            'filter_count': len(filters_with_pl)
        }

    def on_group_filter_selected(self, event=None):
        """When a filter is selected for grouping - OPTIMIZED TO PREVENT DOUBLE UPDATES"""
        if not hasattr(self, 'group_filter_selector') or not self.group_filter_selector.get():
            return
            
        selected_name = self.group_filter_selector.get()
        
        # Safety check for mapping
        if not hasattr(self, 'filter_name_to_id') or not self.filter_name_to_id:
            return
            
        # Try to find the filter ID
        filter_id = None
        
        # First try exact match
        if selected_name in self.filter_name_to_id:
            filter_id = self.filter_name_to_id[selected_name]
        else:
            # Try to extract the base filter ID
            import re
            match = re.match(r'^(\w+_\d+_\d+)\s+\d+', selected_name)
            if match:
                potential_id = match.group(1)
                if potential_id in self.filter_manager.active_filters:
                    filter_id = potential_id
                else:
                    # Try to find by partial match
                    for fid in self.filter_manager.active_filters.keys():
                        if fid in selected_name:
                            filter_id = fid
                            break
            
        if not filter_id:
            return
        
        # Update available fields for this filter
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        if not filter_config:
            return
            
        field_definitions = filter_config.get('field_definitions', {})
        field_names = list(field_definitions.keys())
        
        if hasattr(self, 'group_field_selector'):
            # PRESERVE CURRENT SELECTION if it exists in the new field list
            current_selection = self.group_field_selector.get()
            
            self.group_field_selector['values'] = field_names
            
            if field_names:
                # Only auto-select if there's no current selection OR if current selection is no longer valid
                if not current_selection or current_selection not in field_names:
                    self.group_field_selector.set(field_names[0])
                    # The field selection change will automatically trigger update_grouped_view via the binding
                else:
                    # Field selection is preserved, but we need to update the treeview for the new filter
                    self.app.root.after(50, lambda: self.update_grouped_view())
            else:
                # Clear the treeview if no fields
                if hasattr(self, 'grouped_tree'):
                    for item in self.grouped_tree.get_children():
                        self.grouped_tree.delete(item)
                    self.grouped_tree['columns'] = []

    def update_grouped_view(self, event=None):
        """Update the grouped view based on selected filter and field - ENHANCED"""
        # Safety check - don't run if GUI elements don't exist
        if not hasattr(self, 'group_filter_selector') or not self.group_filter_selector:
            print(f"❌ DEBUG: Group filter selector not available")
            return        
        
        selected_filter = self.group_filter_selector.get()
        selected_field = self.group_field_selector.get() if hasattr(self, 'group_field_selector') else None
        
        print(f"🔍 DEBUG: update_grouped_view called - Filter: '{selected_filter}', Field: '{selected_field}'")
        
        if not selected_filter or not selected_field:
            print(f"❌ DEBUG: Missing filter or field selection")
            return
        
        # Clear existing tree
        if hasattr(self, 'grouped_tree'):
            for item in self.grouped_tree.get_children():
                self.grouped_tree.delete(item)
            
            # Clear columns
            self.grouped_tree['columns'] = []
        else:
            print(f"❌ DEBUG: grouped_tree not available")
            return
        
        # Get data for selected filter
        filter_data = self.get_filter_data(selected_filter)
        
        if not filter_data:
            print(f"❌ DEBUG: No data found for filter: {selected_filter}")
            return
        
        print(f"✅ DEBUG: Processing {len(filter_data)} records for grouped view")
        
        # Group by selected field
        grouped_data = {}
        for record in filter_data:
            group_key = record.get(selected_field, 'N/A')
            if group_key not in grouped_data:
                grouped_data[group_key] = []
            grouped_data[group_key].append(record)
        
        # Get numeric fields for calculations
        filter_config = self.filter_manager.active_filters.get(selected_filter, {})
        field_definitions = filter_config.get('field_definitions', {})
        numeric_fields = [name for name, info in field_definitions.items() 
                         if info.get('data_type') in ['integer', 'float', 'currency']]
        
        # Create dynamic columns based on available numeric fields
        columns = ['Group', 'Count'] + numeric_fields
        
        # Check if profit/loss is enabled for this filter
        pl_config = filter_config.get('profit_loss', {})
        if pl_config.get('enabled', False):
            # Add individual concept columns and total
            concepts = pl_config.get('concepts', [])
            for concept in concepts:
                if concept.get('enabled', False):
                    concept_name = concept.get('name', 'Unknown')
                    columns.append(f'P&L {concept_name}')
            columns.append('P&L Total')
        
        self.grouped_tree['columns'] = columns
        
        for col in columns:
            self.grouped_tree.heading(col, text=col)
            self.grouped_tree.column(col, width=100)
        
        # Add grouped data
        for group_key, records in grouped_data.items():
            values = [group_key, len(records)]
            
            # Add sums for numeric fields
            for field in numeric_fields:
                field_sum = sum(float(r.get(field, 0)) for r in records if r.get(field) is not None)
                values.append(f"{field_sum:.4f}")
            
            # Add profit/loss if available
            if pl_config.get('enabled', False):
                # Calculate sums for each concept
                concepts = pl_config.get('concepts', [])
                for concept in concepts:
                    if concept.get('enabled', False):
                        concept_name = concept.get('name', 'Unknown')
                        concept_key = f'profit_loss_{concept_name}'
                        concept_sum = sum(r.get(concept_key, 0) for r in records if concept_key in r)
                        values.append(f"{concept_sum:.4f}")
                
                # Add total profit/loss
                total_pl_sum = sum(r.get('profit_loss_total', 0) for r in records if 'profit_loss_total' in r)
                values.append(f"{total_pl_sum:.4f}")
            
            self.grouped_tree.insert('', tk.END, values=values)
        
        print(f"✅ DEBUG: Grouped view updated with {len(grouped_data)} groups")

    def create_statistics_tab(self, parent):
        """Create statistics and analytics tab - WITH AUTO-UPDATE ON FIELD SELECTION"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="Statistics for filter:").pack(side=tk.LEFT)
        
        # Filter selector for statistics
        self.stats_filter_selector = ttk.Combobox(control_frame, state="readonly", width=30)
        self.stats_filter_selector.pack(side=tk.LEFT, padx=(5, 10))
        self.stats_filter_selector.bind('<<ComboboxSelected>>', self.on_stats_filter_selected)
        
        # Field selector for grouping - WITH AUTO-UPDATE BINDING
        ttk.Label(control_frame, text="Group by:").pack(side=tk.LEFT, padx=(20, 5))
        self.stats_group_selector = ttk.Combobox(control_frame, state="readonly", width=15)
        self.stats_group_selector.pack(side=tk.LEFT, padx=(0, 10))
        # AUTO-UPDATE: Bind field selection changes to update the statistics
        self.stats_group_selector.bind('<<ComboboxSelected>>', lambda e: self.update_statistics_view())
        
        ttk.Button(control_frame, text="Refresh Stats", 
                  command=self.update_statistics_view).pack(side=tk.LEFT)
        
        # Statistics display
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for different stat views
        stats_notebook = ttk.Notebook(stats_frame)
        stats_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Summary Statistics
        summary_tab = ttk.Frame(stats_notebook, padding=10)
        self.create_summary_stats_tab(summary_tab)
        stats_notebook.add(summary_tab, text="Summary")
        
        # Tab 2: Grouped Statistics
        grouped_tab = ttk.Frame(stats_notebook, padding=10)
        self.create_grouped_stats_tab(grouped_tab)
        stats_notebook.add(grouped_tab, text="Grouped")
        
        # Tab 3: Time Series
        time_tab = ttk.Frame(stats_notebook, padding=10)
        self.create_time_series_tab(time_tab)
        stats_notebook.add(time_tab, text="Time Series")
        
        return main_frame

    def update_filters_display(self):
        """Update the filters treeview with match counts and friendly names - WITH WIDGET EXISTENCE CHECK"""
        # Check if widgets exist before trying to update them
        if not hasattr(self, 'filters_tree') or not self.filters_tree:
            print("❌ DEBUG: filters_tree not available for update")
            return
        
        try:
            # Clear existing items
            for item in self.filters_tree.get_children():
                self.filters_tree.delete(item)
            
            # Update group filter selector if it exists
            if hasattr(self, 'group_filter_selector') and self.group_filter_selector:
                try:
                    filters = list(self.filter_manager.active_filters.keys())
                    self.group_filter_selector['values'] = filters
                    if filters and not self.group_filter_selector.get():
                        self.group_filter_selector.set(filters[0])
                except tk.TclError:
                    print("❌ DEBUG: group_filter_selector widget destroyed, skipping update")
                    return
            else:
                print("❌ DEBUG: group_filter_selector not available")
            
            # Add all filters
            all_filters = self.filter_manager.get_all_filters()
            
            for filter_id, config in all_filters.items():
                # Determine if filter has profit/loss enabled
                pl_enabled = config.get('profit_loss', {}).get('enabled', False)
                is_active = filter_id in self.filter_manager.active_filters
                
                tags = ()
                if is_active:
                    tags = ('active',)
                if pl_enabled:
                    tags = tags + ('profit_loss',)
                
                # Use friendly name instead of technical ID
                filter_name = config.get('name', filter_id)
                description = config.get('description', '')[:50] + '...' if len(config.get('description', '')) > 50 else config.get('description', '')
                match_count = config.get('match_count', 0)
                
                # Color code based on activity
                if match_count == 0:
                    match_display = "0"
                    match_tags = tags + ('inactive',)
                elif match_count < 10:
                    match_display = f"{match_count}"
                    match_tags = tags + ('low_activity',)
                else:
                    match_display = f"{match_count}"
                    match_tags = tags + ('active',)
                
                # Add to treeview
                self.filters_tree.insert('', tk.END, values=(
                    filter_id,  # Hidden technical ID
                    filter_name,  # Friendly name
                    description,
                    ', '.join(config.get('field_names', [])[:3]),
                    config.get('created_at', 'Unknown'),
                    config.get('last_used', 'Never'),
                    match_display,  # Match count with formatting
                    "Yes" if pl_enabled else "No"
                ), tags=match_tags)
            
            # Configure tags for visual feedback
            self.filters_tree.tag_configure('active', background='#e0f0e0')
            self.filters_tree.tag_configure('profit_loss', foreground='blue')
            self.filters_tree.tag_configure('inactive', foreground='red')
            self.filters_tree.tag_configure('low_activity', foreground='orange')
        
        except tk.TclError as e:
            print(f"❌ DEBUG: TclError in update_filters_display: {e}")
            # Clear the broken widget reference
            if hasattr(self, 'filters_tree'):
                self.filters_tree = None

    def safe_update_ui(self):
        """Safely update all UI elements with proper error handling"""
        try:
            if hasattr(self, 'update_filters_display'):
                self.update_filters_display()

            if hasattr(self, 'update_analytics_display'):
                self.update_analytics_display()

            if hasattr(self, 'update_profit_loss_display'):
                self.update_profit_loss_display()

        except tk.TclError as e:
            print(f"❌ DEBUG: TclError in safe_update_ui: {e}")
            # Reinitialize the GUI if widgets are destroyed
            self._clear_widget_references()

    def calculate_enhanced_profit_loss_summary(self):
        """Calculate comprehensive profit/loss summary with multiple concepts"""
        data = self.analytics_structure['data']
        
        summary = {
            'total_profit': 0.0,
            'total_loss': 0.0,
            'net': 0.0,
            'concept_breakdown': {},
            'by_filter': {}
        }
        
        # Group by filter and calculate
        for record in data:
            if 'profit_loss_total' in record:
                filter_id = record['filter_id']
                total_amount = record['profit_loss_total']
                
                if filter_id not in summary['by_filter']:
                    filter_config = self.filter_manager.active_filters.get(filter_id, {})
                    pl_config = filter_config.get('profit_loss', {})
                    concepts_config = pl_config.get('concepts', [])
                    
                    summary['by_filter'][filter_id] = {
                        'description': filter_config.get('name', filter_id),
                        'concepts': {},
                        'total_values': [],
                        'total_count': 0,
                        'total_sum': 0.0,
                        'total_average': 0.0,
                        'total_min': 0.0,
                        'total_max': 0.0
                    }
                    
                    # Initialize concepts
                    for concept in concepts_config:
                        if concept.get('enabled', False):
                            concept_name = concept.get('name', 'unknown')
                            summary['by_filter'][filter_id]['concepts'][concept_name] = {
                                'description': concept.get('description', ''),
                                'values': [],
                                'count': 0,
                                'total': 0.0,
                                'average': 0.0,
                                'min': 0.0,
                                'max': 0.0
                            }
                
                filter_data = summary['by_filter'][filter_id]
                filter_data['total_values'].append(total_amount)
                filter_data['total_count'] += 1
                filter_data['total_sum'] += total_amount
                
                # Update concept-level data
                for concept_name in filter_data['concepts'].keys():
                    concept_key = f'profit_loss_{concept_name}'
                    if concept_key in record and record[concept_key] is not None:
                        concept_amount = record[concept_key]
                        filter_data['concepts'][concept_name]['values'].append(concept_amount)
                        filter_data['concepts'][concept_name]['count'] += 1
                        filter_data['concepts'][concept_name]['total'] += concept_amount
                
                # Update overall totals
                if total_amount >= 0:
                    summary['total_profit'] += total_amount
                else:
                    summary['total_loss'] += total_amount
                summary['net'] += total_amount
        
        # Calculate averages and min/max
        for filter_data in summary['by_filter'].values():
            if filter_data['total_count'] > 0:
                # Total values
                total_values = filter_data['total_values']
                filter_data['total_average'] = sum(total_values) / len(total_values)
                filter_data['total_min'] = min(total_values)
                filter_data['total_max'] = max(total_values)
                
                # Concept values
                for concept_data in filter_data['concepts'].values():
                    if concept_data['count'] > 0:
                        values = concept_data['values']
                        concept_data['average'] = sum(values) / len(values)
                        concept_data['min'] = min(values)
                        concept_data['max'] = max(values)
            
            # Build concept breakdown for overall summary
            for concept_name, concept_data in filter_data['concepts'].items():
                if concept_name not in summary['concept_breakdown']:
                    summary['concept_breakdown'][concept_name] = {
                        'total': 0.0,
                        'count': 0,
                        'filters': []
                    }
                summary['concept_breakdown'][concept_name]['total'] += concept_data['total']
                summary['concept_breakdown'][concept_name]['count'] += concept_data['count']
                summary['concept_breakdown'][concept_name]['filters'].append(filter_data['description'])
        
        return summary

    #**************************************************************************
    
    def update_filter_selectors(self):
        """Update all filter selectors with current active filters - PRESERVE SELECTIONS"""
        active_filters = self.filter_manager.active_filters
        
        # Create list of friendly names for display
        friendly_names = []
        
        # Initialize the mapping dictionary if it doesn't exist
        if not hasattr(self, 'filter_name_to_id'):
            self.filter_name_to_id = {}
        
        # Clear the existing mapping
        self.filter_name_to_id.clear()
        
        for filter_id, config in active_filters.items():
            friendly_name = config.get('name', filter_id)
            friendly_names.append(friendly_name)
            self.filter_name_to_id[friendly_name] = filter_id
        
        print(f"🔍 DEBUG: Built filter mapping with {len(friendly_names)} filters:")
        
        # Update all selector widgets if they exist - PRESERVE CURRENT SELECTIONS
        selectors = ['data_filter_selector', 'stats_filter_selector', 'export_filter_selector', 'group_filter_selector']
        for selector_name in selectors:
            if hasattr(self, selector_name):
                selector = getattr(self, selector_name)
                current_value = selector.get()
                selector['values'] = friendly_names
                
                # Only set to first filter if nothing selected AND we have filters
                # Otherwise preserve the current selection if it's still valid
                if friendly_names:
                    if not current_value:
                        selector.set(friendly_names[0])
                        print(f"✅ DEBUG: Initialized {selector_name} to '{friendly_names[0]}'")
                    elif current_value not in friendly_names:
                        # Current selection is no longer valid, set to first available
                        selector.set(friendly_names[0])
                        print(f"✅ DEBUG: Reset {selector_name} to '{friendly_names[0]}' (previous selection invalid)")
                    else:
                        # Selection is still valid, preserve it
                        print(f"✅ DEBUG: Preserved {selector_name} selection: '{current_value}'")
                else:
                    selector.set('')
        
        # AUTO-INITIALIZE: Only trigger updates if the selection changed
        if hasattr(self, 'group_filter_selector') and self.group_filter_selector.get():
            current_selection = self.group_filter_selector.get()
            # Only trigger if we don't have a field selected yet
            if not hasattr(self, 'group_field_selector') or not self.group_field_selector.get():
                print(f"🔍 DEBUG: Auto-initializing group view for: '{current_selection}'")
                self.app.root.after(200, lambda: self.on_group_filter_selected())
        
        # AUTO-INITIALIZE: Only trigger updates if the selection changed  
        if hasattr(self, 'stats_filter_selector') and self.stats_filter_selector.get():
            current_selection = self.stats_filter_selector.get()
            # Only trigger if we don't have a field selected yet
            if not hasattr(self, 'stats_group_selector') or not self.stats_group_selector.get():
                print(f"🔍 DEBUG: Auto-initializing stats view for: '{current_selection}'")
                self.app.root.after(200, lambda: self.on_stats_filter_selected())
        
        print(f"✅ DEBUG: Updated {len(friendly_names)} filter selectors (selections preserved)")

    def on_data_filter_selected(self, event=None):
        """When a filter is selected in the data view - USING FRIENDLY NAMES"""
        if not hasattr(self, 'data_filter_selector') or not self.data_filter_selector.get():
            return
            
        selected_name = self.data_filter_selector.get()
        
        # Safety check for mapping
        if not hasattr(self, 'filter_name_to_id') or not self.filter_name_to_id:
            print("❌ DEBUG: filter_name_to_id mapping not available")
            return
            
        filter_id = self.filter_name_to_id.get(selected_name)
        if filter_id:
            self.update_filter_data_view(filter_id)
        else:
            print(f"❌ DEBUG: Could not find filter ID for: {selected_name} 3823")

    def on_stats_filter_selected(self, event=None):
        """When a filter is selected in the statistics view - PRESERVE FIELD SELECTION"""
        if not hasattr(self, 'stats_filter_selector') or not self.stats_filter_selector.get():
            return
            
        selected_name = self.stats_filter_selector.get()
        
        # Safety check for mapping
        if not hasattr(self, 'filter_name_to_id') or not self.filter_name_to_id:
            print("❌ DEBUG: filter_name_to_id mapping not available")
            return
            
        filter_id = self.filter_name_to_id.get(selected_name)
        if filter_id:
            # Update available fields for grouping
            filter_config = self.filter_manager.active_filters.get(filter_id, {})
            field_definitions = filter_config.get('field_definitions', {})
            field_names = list(field_definitions.keys())
            
            if hasattr(self, 'stats_group_selector'):
                # PRESERVE CURRENT SELECTION
                current_selection = self.stats_group_selector.get()
                
                self.stats_group_selector['values'] = field_names
                if field_names:
                    # Only auto-select if there's no current selection OR if current selection is no longer valid
                    if not current_selection or current_selection not in field_names:
                        self.stats_group_selector.set(field_names[0])
                    # Trigger automatic update after a short delay
                    self.app.root.after(100, self.update_statistics_view)
            
        else:
            print(f"❌ DEBUG: Could not find filter ID for: {selected_name}")

    def update_filter_data_view(self, filter_id=None):
        """Update the filter data view with selected filter's data - ADDED DEFAULT"""
        if filter_id is None:
            # Try to get from selector if available
            if hasattr(self, 'data_filter_selector') and self.data_filter_selector.get():
                selected_name = self.data_filter_selector.get()
                if hasattr(self, 'filter_name_to_id') and selected_name in self.filter_name_to_id:
                    filter_id = self.filter_name_to_id[selected_name]
                else:
                    print("❌ DEBUG: Cannot update filter data view - no filter selected")
                    return
            else:
                print("❌ DEBUG: Cannot update filter data view - no filter_id provided and no selector available")
                return
        
        # Clear existing tree
        for item in self.filter_data_tree.get_children():
            self.filter_data_tree.delete(item)
        
        # Clear columns
        self.filter_data_tree['columns'] = []
        
        # Get data for selected filter
        filter_data = self.get_filter_data(filter_id)
        
        if not filter_data:
            self.record_count_label.config(text="Records: 0")
            return
        
        # Get field definitions for this filter
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        field_definitions = filter_config.get('field_definitions', {})
        
        # Create columns based on field definitions
        columns = ['timestamp'] + list(field_definitions.keys()) + ['original_line']
        self.filter_data_tree['columns'] = columns
        
        # Configure columns
        for col in columns:
            self.filter_data_tree.heading(col, text=col)
            self.filter_data_tree.column(col, width=100, stretch=False)
        
        # Add data rows
        for record in filter_data:
            values = [record.get(col, '') for col in columns]
            self.filter_data_tree.insert('', tk.END, values=values)
        
        # Update record count
        self.record_count_label.config(text=f"Records: {len(filter_data)}")
    
    def get_filter_data(self, filter_id):
        """Get all data for a specific filter - WORKS WITH FRIENDLY NAMES"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure['data']:
            return []
        
        # If it's a friendly name, convert to filter ID
        if hasattr(self, 'filter_name_to_id') and filter_id in self.filter_name_to_id.values():
            # It's already a filter ID
            pass
        elif hasattr(self, 'filter_name_to_id'):
            # It might be a friendly name, try to convert
            filter_id = self.filter_name_to_id.get(filter_id, filter_id)
        
        return [record for record in self.analytics_structure['data'] 
                if record.get('filter_id') == filter_id]

    #**************************************************************************

    def create_summary_stats_tab(self, parent):
        """Create summary statistics tab"""
        self.summary_stats_text = tk.Text(parent, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.summary_stats_text.yview)
        self.summary_stats_text.configure(yscrollcommand=scrollbar.set)
        
        self.summary_stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_grouped_stats_tab(self, parent):
        """Create grouped statistics tab"""
        self.grouped_stats_tree = ttk.Treeview(parent, show='headings', height=15)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.grouped_stats_tree.yview)
        self.grouped_stats_tree.configure(yscrollcommand=scrollbar.set)
        
        self.grouped_stats_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_time_series_tab(self, parent):
        """Create time series statistics tab"""
        self.time_series_text = tk.Text(parent, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.time_series_text.yview)
        self.time_series_text.configure(yscrollcommand=scrollbar.set)
        
        self.time_series_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_statistics_view(self, filter_id=None):
        """Update the statistics view - USING FRIENDLY NAMES"""
        if filter_id is None:
            if not hasattr(self, 'stats_filter_selector') or not self.stats_filter_selector.get():
                return
            
            selected_name = self.stats_filter_selector.get()
            
            # Safety check for mapping
            if not hasattr(self, 'filter_name_to_id') or not self.filter_name_to_id:
                print("❌ DEBUG: filter_name_to_id mapping not available")
                return
                
            filter_id = self.filter_name_to_id.get(selected_name)
            if not filter_id:
                print(f"❌ DEBUG: Could not find filter ID for: {selected_name} 3965")
                return
        
        filter_data = self.get_filter_data(filter_id)
        if not filter_data:
            return
        
        # Get friendly name for display
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        filter_name = filter_config.get('name', filter_id)
        
        # Update summary statistics
        self.update_summary_statistics(filter_id, filter_name, filter_data)
        
        # Update grouped statistics
        if hasattr(self, 'stats_group_selector') and self.stats_group_selector.get():
            selected_field = self.stats_group_selector.get()
            self.update_grouped_statistics(filter_id, filter_name, filter_data, selected_field)
        
        # Update time series statistics
        self.update_time_series_statistics(filter_id, filter_name, filter_data)

    def update_summary_statistics(self, filter_id, filter_name, data):
        """Update summary statistics display with friendly names - FIXED PARAMETERS"""
        if not hasattr(self, 'summary_stats_text'):
            return
        
        self.summary_stats_text.delete(1.0, tk.END)
        
        # Basic statistics - using friendly name
        stats_text = f"=== SUMMARY STATISTICS: {filter_name} ===\n\n"
        stats_text += f"Total Records: {len(data)}\n"
        stats_text += f"Date Range: {self.get_date_range(data)}\n\n"
        
        # Check for profit/loss data
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        pl_config = filter_config.get('profit_loss', {})
        if pl_config.get('enabled', False):
            pl_data = self.calculate_filter_profit_loss_summary(data)
            stats_text += "PROFIT/LOSS SUMMARY:\n"
            stats_text += f"  Total P&L: {pl_data['total']:.4f}\n"
            stats_text += f"  Average per record: {pl_data['average']:.4f}\n"
            stats_text += f"  Records with P&L: {pl_data['count']}\n\n"
        
        # Field-specific statistics
        field_definitions = filter_config.get('field_definitions', {})
        
        numeric_fields = {}
        for field_name, field_info in field_definitions.items():
            if field_info.get('data_type') in ['integer', 'float', 'currency']:
                values = []
                for record in data:
                    if field_name in record and record[field_name] is not None:
                        try:
                            values.append(float(record[field_name]))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    numeric_fields[field_name] = values
        
        if numeric_fields:
            stats_text += "NUMERIC FIELD STATISTICS:\n\n"
            for field_name, values in numeric_fields.items():
                stats_text += f"📊 {field_name}:\n"
                stats_text += f"   Count: {len(values)}\n"
                stats_text += f"   Sum: {sum(values):.4f}\n"
                stats_text += f"   Average: {sum(values)/len(values):.4f}\n"
                stats_text += f"   Min: {min(values):.4f}\n"
                stats_text += f"   Max: {max(values):.4f}\n"
                stats_text += f"   Range: {max(values)-min(values):.4f}\n\n"
        
        self.summary_stats_text.insert(1.0, stats_text)

    def calculate_filter_profit_loss_summary(self, data):
        """Calculate profit/loss summary for a specific filter's data"""
        total = 0.0
        count = 0
        
        for record in data:
            if 'profit_loss_total' in record:
                total += record['profit_loss_total']
                count += 1
        
        return {
            'total': total,
            'count': count,
            'average': total / count if count > 0 else 0.0
        }

    def update_grouped_statistics(self, filter_id, filter_name, data, group_field):
        """Update grouped statistics display - FIXED PARAMETERS"""
        if not hasattr(self, 'grouped_stats_tree'):
            return
        
        # Clear existing tree
        for item in self.grouped_stats_tree.get_children():
            self.grouped_stats_tree.delete(item)
        
        # Clear columns
        self.grouped_stats_tree['columns'] = []
        
        # Get data for selected filter
        filter_data = data  # Using the data parameter that was passed in
        
        if not filter_data:
            return
        
        # Group by selected field
        grouped_data = {}
        for record in filter_data:
            group_key = record.get(group_field, 'N/A')
            if group_key not in grouped_data:
                grouped_data[group_key] = []
            grouped_data[group_key].append(record)
        
        # Get numeric fields for calculations
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        field_definitions = filter_config.get('field_definitions', {})
        numeric_fields = [name for name, info in field_definitions.items() 
                         if info.get('data_type') in ['integer', 'float', 'currency']]
        
        # Create dynamic columns based on available numeric fields
        columns = ['Group', 'Count'] + numeric_fields
        
        # Check if profit/loss is enabled for this filter
        pl_config = filter_config.get('profit_loss', {})
        if pl_config.get('enabled', False):
            # Add individual concept columns and total
            concepts = pl_config.get('concepts', [])
            for concept in concepts:
                if concept.get('enabled', False):
                    concept_name = concept.get('name', 'Unknown')
                    columns.append(f'P&L {concept_name}')
            columns.append('P&L Total')
        
        self.grouped_stats_tree['columns'] = columns
        
        for col in columns:
            self.grouped_stats_tree.heading(col, text=col)
            self.grouped_stats_tree.column(col, width=100)
        
        # Add grouped data
        for group_key, records in grouped_data.items():
            values = [group_key, len(records)]
            
            # Add sums for numeric fields
            for field in numeric_fields:
                field_sum = sum(float(r.get(field, 0)) for r in records if r.get(field) is not None)
                values.append(f"{field_sum:.4f}")
            
            # Add profit/loss if available
            if pl_config.get('enabled', False):
                # Calculate sums for each concept
                concepts = pl_config.get('concepts', [])
                for concept in concepts:
                    if concept.get('enabled', False):
                        concept_name = concept.get('name', 'Unknown')
                        concept_key = f'profit_loss_{concept_name}'
                        concept_sum = sum(r.get(concept_key, 0) for r in records if concept_key in r)
                        values.append(f"{concept_sum:.4f}")
                
                # Add total profit/loss
                total_pl_sum = sum(r.get('profit_loss_total', 0) for r in records if 'profit_loss_total' in r)
                values.append(f"{total_pl_sum:.4f}")
            
            self.grouped_stats_tree.insert('', tk.END, values=values)

    def update_time_series_statistics(self, filter_id, filter_name, data):
        """Update time series statistics display - FIXED PARAMETERS"""
        if not hasattr(self, 'time_series_text'):
            return
        
        self.time_series_text.delete(1.0, tk.END)
        
        if not data:
            self.time_series_text.insert(1.0, "No data available")
            return
        
        # Basic time series analysis - using friendly name
        stats_text = f"=== TIME SERIES ANALYSIS: {filter_name} ===\n\n"
        
        # Extract timestamps and group by time intervals
        time_data = {}
        for record in data:
            timestamp_str = record.get('timestamp')
            if timestamp_str:
                # Extract just the date part for daily grouping
                date_part = timestamp_str.split()[0]  # Get YYYY-MM-DD part
                if date_part not in time_data:
                    time_data[date_part] = 0
                time_data[date_part] += 1
        
        if time_data:
            stats_text += "Records by Date:\n"
            for date, count in sorted(time_data.items()):
                stats_text += f"  {date}: {count} records\n"
            
            # Add simple trend analysis
            dates = sorted(time_data.keys())
            if len(dates) > 1:
                stats_text += f"\nDate Range: {dates[0]} to {dates[-1]}\n"
                stats_text += f"Total Days: {len(dates)}\n"
                stats_text += f"Average records per day: {len(data)/len(dates):.1f}\n"
        else:
            stats_text += "No timestamp data available for time series analysis.\n"
        
        self.time_series_text.insert(1.0, stats_text)

    #**************************************************************************

    def get_date_range(self, data):
        """Get the date range from the data for display in statistics"""
        if not data:
            return "N/A"
        
        # Extract all timestamps
        timestamps = []
        for record in data:
            timestamp_str = record.get('timestamp')
            if timestamp_str:
                try:
                    # Parse the timestamp string to datetime object
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    timestamps.append(dt)
                except (ValueError, TypeError):
                    continue
        
        if not timestamps:
            return "No timestamps found"
        
        # Find min and max dates
        min_date = min(timestamps)
        max_date = max(timestamps)
        
        # Format for display
        if min_date.date() == max_date.date():
            # Same day, just show time range
            return f"{min_date.strftime('%Y-%m-%d')} ({min_date.strftime('%H:%M')} - {max_date.strftime('%H:%M')})"
        else:
            # Different days
            return f"{min_date.strftime('%Y-%m-%d %H:%M')} to {max_date.strftime('%Y-%m-%d %H:%M')}"
    
    #**************************************************************************

    def export_filter_to_csv(self):
        """Export data for selected filter to CSV - USING FRIENDLY NAMES"""
        if not hasattr(self, 'export_filter_selector') or not self.export_filter_selector.get():
            self.log_export_message("❌ Please select a filter to export")
            return
        
        selected_name = self.export_filter_selector.get()
        
        # Safety check for mapping
        if not hasattr(self, 'filter_name_to_id') or not self.filter_name_to_id:
            self.log_export_message("❌ Filter mapping not available")
            return
            
        filter_id = self.filter_name_to_id.get(selected_name)
        if not filter_id:
            self.log_export_message(f"❌ Could not find filter ID for: {selected_name} 4225")
            return
        
        filter_data = self.get_filter_data(filter_id)
        if not filter_data:
            self.log_export_message(f"❌ No data available for filter: {selected_name}")
            return
        
        # Create filename with friendly name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in selected_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')  # Replace spaces with underscores
        default_filename = f"{safe_name}_{timestamp}.csv"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title=f"Export data for {selected_name}",
            initialfile=default_filename  # Suggest friendly filename
        )
        
        if not filename:
            return
        
        try:
            success = self.export_data_to_csv(filter_data, selected_name, filename)
            if success:
                self.log_export_message(f"✅ Successfully exported {len(filter_data)} records to: {filename}")
            else:
                self.log_export_message(f"❌ Failed to export data to: {filename}")
        except Exception as e:
            self.log_export_message(f"❌ Export error: {e}")
    
    def export_all_filters_to_csv(self):
        """Export data for all filters to separate CSV files with friendly names"""
        if not hasattr(self, 'analytics_structure') or not self.analytics_structure['data']:
            self.log_export_message("❌ No data available to export")
            return
        
        # Safety check for mapping
        if not hasattr(self, 'filter_name_to_id') or not self.filter_name_to_id:
            self.log_export_message("❌ Filter mapping not available")
            return
        
        # Get directory for export
        export_dir = filedialog.askdirectory(title="Select directory for CSV exports")
        if not export_dir:
            return
        
        try:
            exported_count = 0
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for filter_id, filter_config in self.filter_manager.active_filters.items():
                filter_data = self.get_filter_data(filter_id)
                if filter_data:
                    # Use friendly name for filename
                    filter_name = filter_config.get('name', filter_id)
                    safe_name = "".join(c for c in filter_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    safe_name = safe_name.replace(' ', '_')  # Replace spaces with underscores
                    filename = os.path.join(export_dir, f"{safe_name}_{timestamp}.csv")
                    
                    success = self.export_data_to_csv(filter_data, filter_name, filename)
                    if success:
                        self.log_export_message(f"✅ Exported {filter_name}: {len(filter_data)} records")
                        exported_count += 1
                    else:
                        self.log_export_message(f"❌ Failed to export {filter_name}")
            
            self.log_export_message(f"🎉 Export completed: {exported_count} filters exported to {export_dir}")
            
        except Exception as e:
            self.log_export_message(f"❌ Export error: {e}")

    def log_export_message(self, message):
        """Add message to export log"""
        if hasattr(self, 'export_log_text'):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.export_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.export_log_text.see(tk.END)

    def format_enhanced_profit_loss_summary(self, pl_data, overall_totals):
        """Format enhanced profit/loss summary for display with overall totals"""
        text = "=== ENHANCED PROFIT/LOSS SUMMARY ===\n\n"
        
        # Overall summary with new totals
        text += "OVERALL SUMMARY (All Filters):\n"
        text += f"Grand Total P&L: {overall_totals['total_sum']:.4f}\n"
        text += f"Total Profit: {pl_data['total_profit']:.4f}\n"
        text += f"Total Loss: {pl_data['total_loss']:.4f}\n"
        text += f"Net: {pl_data['net']:.4f}\n"
        text += f"Records with P&L: {overall_totals['total_count']}\n"
        text += f"Average per record: {overall_totals['total_average']:.4f}\n"
        text += f"Range: {overall_totals['total_min']:.4f} to {overall_totals['total_max']:.4f}\n"
        text += f"Filters with P&L: {overall_totals['filter_count']}\n\n"
        
        # Concept breakdown
        if pl_data['concept_breakdown']:
            text += "CONCEPT BREAKDOWN:\n"
            for concept_name, concept_data in pl_data['concept_breakdown'].items():
                text += f"• {concept_name}:\n"
                text += f"  Total: {concept_data['total']:.4f}\n"
                text += f"  Records: {concept_data['count']}\n"
                if concept_data['count'] > 0:
                    text += f"  Avg per record: {concept_data['total']/concept_data['count']:.4f}\n"
                text += f"  Filters: {', '.join(concept_data['filters'][:3])}"
                if len(concept_data['filters']) > 3:
                    text += f" and {len(concept_data['filters']) - 3} more"
                text += "\n\n"
        
        text += f"Total filters with P&L tracking: {len(pl_data['by_filter'])}\n"
        text += f"Total concepts tracked: {sum(len(data['concepts']) for data in pl_data['by_filter'].values())}\n"
        
        return text

    def debug_profit_loss_calculation(self, filter_id, record):
        """Debug method to check why profit/loss isn't being calculated"""
        filter_config = self.filter_manager.active_filters.get(filter_id, {})
        pl_config = filter_config.get('profit_loss', {})
        
        print(f"🔍 DEBUG P&L for filter {filter_id}:")
        print(f"   P&L enabled: {pl_config.get('enabled', False)}")
        
        if pl_config.get('enabled', False):
            concepts = pl_config.get('concepts', [])
            print(f"   Concepts count: {len(concepts)}")
            
            for i, concept in enumerate(concepts):
                print(f"   Concept {i+1}:")
                print(f"     Enabled: {concept.get('enabled', False)}")
                print(f"     Name: {concept.get('name', 'Unknown')}")
                print(f"     Value type: {concept.get('value_type', 'fixed')}")
                
                if concept.get('enabled', False):
                    if concept.get('value_type') == 'field':
                        field_name = concept.get('value_field')
                        field_value = record.get(field_name) if field_name else None
                        print(f"     Field: {field_name}, Value: {field_value}")
                    else:
                        print(f"     Fixed value: {concept.get('fixed_value', 0.0)}")
                    
                    print(f"     Multiplier: {concept.get('multiplier', 1.0)}")
                    print(f"     Is profit: {concept.get('is_profit', True)}")
        else:
            print(f"   ❌ Profit/Loss not enabled for this filter")

# =============================================================================
# TOOLTIP AND HELPER FUNCTIONS
# =============================================================================

class ToolTip:
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<Motion>', self.motion)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def motion(self, event=None):
        self.x, self.y = event.x, event.y

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + self.x + 25
        y = self.widget.winfo_rooty() + self.y + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 10))
        label.pack()

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# =============================================================================
# PATTERN WIZARD - Step-by-step pattern creation for non-technical users
# =============================================================================

class PatternWizard:

    def __init__(self, plugin):
        self.plugin = plugin
        self.current_step = 0
        self.sample_lines = []
        self.selected_line = ""
        self.delimiter = " "
        self.field_configs = []
        self.current_field_index = 0
        
    def create_wizard_ui(self, parent):
        self.wizard_frame = ttk.Frame(parent)
        
        # Title
        title_label = ttk.Label(self.wizard_frame, text="Pattern Creation Wizard", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Progress indicator
        self.progress_frame = ttk.Frame(self.wizard_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Content area
        self.content_frame = ttk.Frame(self.wizard_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Navigation buttons
        self.nav_frame = ttk.Frame(self.wizard_frame)
        self.nav_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.back_button = ttk.Button(self.nav_frame, text="← Back", 
                                     command=self.previous_step, state=tk.DISABLED)
        self.back_button.pack(side=tk.LEFT)
        
        self.next_button = ttk.Button(self.nav_frame, text="Next →", 
                                     command=self.next_step)
        self.next_button.pack(side=tk.RIGHT)
        
        # Initialize first step
        self.show_step(0)
        
        return self.wizard_frame
    
    def show_step(self, step_index):
        """Show the specified wizard step"""
        self.current_step = step_index
        
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Update progress
        self.update_progress()
        
        # Show appropriate step
        steps = [
            self.step_input_line,
            self.step_select_delimiter,
            self.step_configure_fields,
            self.step_review_pattern
        ]
        
        if step_index < len(steps):
            steps[step_index]()
        
        # Update navigation buttons
        self.update_navigation()
    
    def update_progress(self):
        """Update the progress indicator"""
        for widget in self.progress_frame.winfo_children():
            widget.destroy()
            
        steps = ["1. Input", "2. Delimiter", "3. Fields", "4. Review"]
        
        for i, step_name in enumerate(steps):
            # Create step indicator
            if i == self.current_step:
                # Current step - highlighted
                step_label = ttk.Label(self.progress_frame, text=step_name, 
                                      foreground="blue", font=('Arial', 10, 'bold'))
            elif i < self.current_step:
                # Completed step
                step_label = ttk.Label(self.progress_frame, text=f"✓ {step_name}", 
                                      foreground="green")
            else:
                # Future step
                step_label = ttk.Label(self.progress_frame, text=step_name, 
                                      foreground="gray")
            
            step_label.pack(side=tk.LEFT, padx=10)
            
            # Add separator between steps (except last one)
            if i < len(steps) - 1:
                ttk.Label(self.progress_frame, text="→").pack(side=tk.LEFT, padx=5)

    def update_navigation(self):
        """Update navigation button states"""
        if self.current_step == 0:
            self.back_button.config(state=tk.DISABLED)
        else:
            self.back_button.config(state=tk.NORMAL)
        
        if self.current_step == 2:  # Field configuration step
            # Enable Next button only if we've configured all fields
            all_configured = (hasattr(self, 'field_configs') and 
                            len(self.field_configs) > 0 and
                            self.current_field_index == len(self.field_configs) - 1)
            self.next_button.config(state=tk.NORMAL if all_configured else tk.DISABLED)
        elif self.current_step == 3:  # Last step
            self.next_button.config(text="Finish", state=tk.NORMAL)
        else:
            self.next_button.config(text="Next →")

    # =============================================================================
    # =============================================================================
    
    def step_input_line(self):
        """Step 1: Input log line"""
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Instructions
        instr_text = """Please paste one or more sample log lines below. 
                        If you paste multiple lines, you'll be asked to select one for pattern creation."""
        
        ttk.Label(frame, text=instr_text, justify=tk.LEFT, wraplength=500).pack(anchor=tk.W, pady=(0, 10))
        
        # Text area for log lines
        ttk.Label(frame, text="Log lines:").pack(anchor=tk.W)
        self.input_text = tk.Text(frame, height=8, width=80)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Example
        example_frame = ttk.LabelFrame(frame, text="Example", padding=5)
        example_frame.pack(fill=tk.X, pady=(10, 0))
        
        example_text = "2025-10-04 12:04:53 [System] [] You received Shrapnel x (1) Value: 0.0001 PED"
        ttk.Label(example_frame, text=example_text, foreground="gray", font=('Arial', 9)).pack(anchor=tk.W)
    
    def show_line_selection_dialog(self, lines):
        """Show a dialog for user to select which line to process"""
        dialog = tk.Toplevel()
        dialog.title("Select Log Line")
        dialog.geometry("600x400")
        dialog.transient(self.wizard_frame)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"600x400+{x}+{y}")
        
        # Instructions
        ttk.Label(dialog, text="Multiple log lines detected. Please select the line you want to use for pattern creation:", 
                  wraplength=550, justify=tk.LEFT).pack(padx=20, pady=(20, 10), anchor=tk.W)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.line_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                      selectmode=tk.SINGLE, font=('Courier', 9))
        self.line_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.line_listbox.yview)
        
        # Add lines to listbox
        for i, line in enumerate(lines):
            # Truncate very long lines for display
            display_line = line if len(line) <= 80 else line[:77] + "..."
            self.line_listbox.insert(tk.END, f"Line {i+1}: {display_line}")
        
        # Select first line by default
        self.line_listbox.selection_set(0)
        
        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        def on_select():
            selection = self.line_listbox.curselection()
            if selection:
                self.selected_line = lines[selection[0]]
                dialog.destroy()
            else:
                tk.messagebox.showwarning("No Selection", "Please select a line to continue")
        
        def on_cancel():
            self.selected_line = None
            dialog.destroy()
        
        ttk.Button(button_frame, text="Select", command=on_select).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)
        
        # Double-click to select
        self.line_listbox.bind('<Double-Button-1>', lambda e: on_select())
        
        # Wait for dialog to close
        self.wizard_frame.wait_window(dialog)
    
    # =============================================================================

    def get_delimiter(self):
        """Get the current delimiter string"""
        delimiter = self.delimiter_var.get()
        if delimiter == "custom":
            delimiter = self.custom_delimiter.get().strip()
        elif delimiter == "\\t":
            delimiter = "\t"
        return delimiter

    def step_select_delimiter(self):
        """Step 2: Select delimiter"""
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Instructions
        instr_text = """How would you like to split the log line? 
                        The wizard will break the line into fields using your chosen delimiter."""
        
        ttk.Label(frame, text=instr_text, justify=tk.LEFT, wraplength=500).pack(anchor=tk.W, pady=(0, 20))
        
        # Delimiter selection
        delim_frame = ttk.Frame(frame)
        delim_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.delimiter_var = tk.StringVar(value=" ")
        
        delimiters = [
            ("Space ( )", " "),
            ("Tab", "\\t"),
            ("Comma (,)", ","),
            ("Pipe (|)", "|"),
            ("Custom", "custom")
        ]
        
        for text, value in delimiters:
            ttk.Radiobutton(delim_frame, text=text, variable=self.delimiter_var, 
                           value=value).pack(anchor=tk.W, pady=2)
        
        # Custom delimiter entry
        self.custom_delimiter = ttk.Entry(delim_frame, width=10)
        self.custom_delimiter.pack(anchor=tk.W, pady=5)
        self.custom_delimiter.config(state=tk.DISABLED)
        
        # Bind custom delimiter selection
        self.delimiter_var.trace('w', self.on_delimiter_change)
        
        # Preview
        preview_frame = ttk.LabelFrame(frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_text = tk.Text(preview_frame, height=6, width=80)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Update preview
        self.update_preview()
    
    def on_delimiter_change(self, *args):
        """Handle delimiter selection change"""
        if self.delimiter_var.get() == "custom":
            self.custom_delimiter.config(state=tk.NORMAL)
        else:
            self.custom_delimiter.config(state=tk.DISABLED)
        self.update_preview()
    
    def update_preview(self):
        """Update the delimiter preview"""
        if not hasattr(self, 'preview_text'):
            return
            
        self.preview_text.delete(1.0, tk.END)
        
        if not self.selected_line:
            self.preview_text.insert(1.0, "No line selected. Please go back to Step 1 and select a log line.")
            return
        
        # Get delimiter
        delimiter = self.delimiter_var.get()
        if delimiter == "custom":
            delimiter = self.custom_delimiter.get().strip()
            if not delimiter:
                self.preview_text.insert(1.0, "Please enter a custom delimiter")
                return
        elif delimiter == "\\t":
            delimiter = "\t"
        
        # Split and show preview
        try:
            parts = self.selected_line.split(delimiter)
            
            self.preview_text.insert(1.0, f"Selected line:\n{self.selected_line}\n\n")
            self.preview_text.insert(tk.END, f"Using delimiter: '{repr(delimiter)}'\n")
            self.preview_text.insert(tk.END, f"Split into {len(parts)} fields:\n\n")
            
            for i, part in enumerate(parts):
                self.preview_text.insert(tk.END, f"Field {i+1:2d}: '{part}'\n")
                
            # Store the parts for the next step
            self.field_parts = parts
            
        except Exception as e:
            self.preview_text.insert(1.0, f"Error splitting line: {e}")

    # =============================================================================
    
    def step_configure_fields(self):
        """Step 3: Configure fields one by one"""
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        if not hasattr(self, 'field_parts') or not self.field_parts:
            ttk.Label(frame, text="Please complete Steps 1 and 2 first.", justify=tk.CENTER).pack(expand=True)
            return
        
        # Initialize field configurations if not done yet
        if not hasattr(self, 'field_configs') or not self.field_configs:
            self.field_configs = []
            for i, part in enumerate(self.field_parts):
                detected_type = self.plugin.type_detector.detect_field_type(part)
                # Map detected type to our pattern types
                pattern_type_map = {
                    "integer": "integer",
                    "float": "float", 
                    "currency": "currency",
                    "date": "date",
                    "time": "time",
                    "text": "text"
                }
                pattern_type = pattern_type_map.get(detected_type, "text")

                self.field_configs.append({
                    'index': i,
                    'content': part,
                    'group_with_next': True,
                    'include_in_search': True,
                    'pattern_type': pattern_type,  # Use the mapped type
                    'field_name': self._suggest_field_name(part, i)
                })

        # Current field navigation
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.current_field_index = getattr(self, 'current_field_index', 0)
        
        ttk.Label(nav_frame, text=f"Field {self.current_field_index + 1} of {len(self.field_configs)}", 
                 font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        
        # Navigation buttons for fields
        field_nav_frame = ttk.Frame(nav_frame)
        field_nav_frame.pack(side=tk.RIGHT)
        
        ttk.Button(field_nav_frame, text="← Previous", 
                  command=self.previous_field, 
                  state=tk.NORMAL if self.current_field_index > 0 else tk.DISABLED).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(field_nav_frame, text="Next →", 
                  command=self.next_field,
                  state=tk.NORMAL if self.current_field_index < len(self.field_configs) - 1 else tk.DISABLED).pack(side=tk.LEFT)
        
        # Field content display
        content_frame = ttk.LabelFrame(frame, text="Field Content", padding=10)
        content_frame.pack(fill=tk.X, pady=(0, 20))
        
        field_content = self.field_configs[self.current_field_index]['content']
        content_text = tk.Text(content_frame, height=3, width=80, wrap=tk.WORD)
        content_text.pack(fill=tk.X)
        content_text.insert(1.0, field_content)
        content_text.config(state=tk.DISABLED)  # Read-only
        
        # Configuration options
        config_frame = ttk.LabelFrame(frame, text="Configuration Options", padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 20))
        
        config = self.field_configs[self.current_field_index]
        
        # Option 1: Group with next field
        self.group_var = tk.BooleanVar(value=config['group_with_next'])
        group_cb = ttk.Checkbutton(config_frame, text="Group with next field", 
                                variable=self.group_var,
                                command=self.on_config_change)
        group_cb.pack(anchor=tk.W, pady=2)
        add_tooltip(group_cb, "When checked, this field will be combined with the next field in the pattern")
        
        # Option 2: Include in search
        self.include_var = tk.BooleanVar(value=config['include_in_search'])
        include_cb = ttk.Checkbutton(config_frame, text="Include in search pattern", 
                                    variable=self.include_var,
                                    command=self.on_config_change)
        include_cb.pack(anchor=tk.W, pady=2)
        add_tooltip(include_cb, "When checked, this field will be part of the search pattern")
        
        # Option 3: Pattern type selection (REPLACED the checkbox with combobox)
        pattern_frame = ttk.Frame(config_frame)
        pattern_frame.pack(fill=tk.X, pady=5)
        ttk.Label(pattern_frame, text="Pattern type:").pack(side=tk.LEFT)
        
        
        # Pattern type combobox
        pattern_types = [
            ("literal", "Exact text (literal)"),
            ("word", "A Single Word"),
            ("text", "Any text (.+?)"),
            ("integer", "Whole number (\\d+)"),
            ("float", "Decimal number (\\d+\\.\\d+)"),
            ("currency", "Currency value (\\d+\\.\\d+)"),
            ("date", "Date (\\d{4}-\\d{2}-\\d{2})"),
            ("time", "Time (\\d{2}:\\d{2}:\\d{2})")
        ]
    
        self.pattern_type_var = tk.StringVar(value=config['pattern_type'])
        self.pattern_combo = ttk.Combobox(pattern_frame, 
                                        textvariable=self.pattern_type_var,
                                        values=[desc for _, desc in pattern_types],
                                        state="readonly", width=20)
        self.pattern_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.pattern_combo.bind('<<ComboboxSelected>>', lambda e: self.on_config_change())

        # Map display names to internal pattern types
        self.pattern_type_map = {desc: internal for internal, desc in pattern_types}
    
        # Set the display value based on internal type
        current_display = next((desc for internal, desc in pattern_types 
                            if internal == config['pattern_type']), "Any text (.+?)")
        self.pattern_type_var.set(current_display)

        add_tooltip(self.pattern_combo, "Choose how to match this field in the pattern")

        # Field name suggestion
        name_frame = ttk.Frame(config_frame)
        name_frame.pack(fill=tk.X, pady=5)
    
        ttk.Label(name_frame, text="Field name:").pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=config['field_name'])
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=20)
        name_entry.pack(side=tk.LEFT, padx=(5, 0))
        name_entry.bind('<KeyRelease>', lambda e: self.on_config_change())
        
        # Pattern preview
        preview_frame = ttk.LabelFrame(frame, text="Pattern Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.pattern_preview = tk.Text(preview_frame, height=4, width=80)
        self.pattern_preview.pack(fill=tk.BOTH, expand=True)
        
        # Update the preview
        self.update_pattern_preview()

    def _suggest_field_name(self, content, index):
        """Suggest meaningful field names based on content"""
        content_lower = content.lower()
        
        # Date/time patterns
        if re.match(r'\d{4}-\d{2}-\d{2}', content):
            return "date"
        elif re.match(r'\d{2}:\d{2}:\d{2}', content):
            return "time"
        elif content_lower in ['system', 'local', 'global']:
            return "channel"
        elif 'received' in content_lower:
            return "action"
        elif any(word in content_lower for word in ['shrapnel', 'scrap', 'component', 'crap']):
            return "item_name"
        elif content.isdigit():
            return "quantity"
        elif re.match(r'\d+\.\d+', content):
            return "value"
        elif content == 'PED':
            return "currency"
        elif content == 'x':
            return "multiplier"
        elif content.startswith('(') and content.endswith(')'):
            return "parentheses_content"
        else:
            return f"field_{index+1}"
    
    def previous_field(self):
        """Navigate to previous field"""
        if self.current_field_index > 0:
            self.save_current_field_config()
            self.current_field_index -= 1
            self.show_step(2)  # Refresh step 3 with new field
    
    def next_field(self):
        """Navigate to next field"""
        if self.current_field_index < len(self.field_configs) - 1:
            self.save_current_field_config()
            self.current_field_index += 1
            self.show_step(2)  # Refresh step 3 with new field

    def save_current_field_config(self):
        """Save current field configuration"""
        if hasattr(self, 'group_var'):
            # Convert pattern type display to internal type
            pattern_display = self.pattern_type_var.get()
            internal_pattern_type = self.pattern_type_map.get(pattern_display, "text")

            self.field_configs[self.current_field_index].update({
                'group_with_next': self.group_var.get(),
                'include_in_search': self.include_var.get(),
                'pattern_type': internal_pattern_type,
                'field_name': self.name_var.get()
            })

    def on_config_change(self):
        """Handle configuration changes"""
        self.save_current_field_config()
        self.update_pattern_preview()

    def update_pattern_preview(self):
        """Update the pattern preview with current configuration"""
        if not hasattr(self, 'pattern_preview'):
            return
            
        self.pattern_preview.delete(1.0, tk.END)
        
        # Generate the regex pattern based on current configurations
        regex_pattern = self.generate_regex_pattern()
        explanation = self.generate_pattern_explanation()
        
        self.pattern_preview.insert(1.0, f"Generated Pattern:\n{regex_pattern}\n\n")
        self.pattern_preview.insert(tk.END, f"Explanation:\n{explanation}")
        
        # Add debug info (temporary)
        debug_info = self.debug_field_configs()
        self.pattern_preview.insert(tk.END, f"\n\nDebug Info:\n{debug_info}")
        
        # Test the pattern against the sample line
        test_result = self.test_pattern(regex_pattern)
        if test_result:
            self.pattern_preview.insert(tk.END, f"\n\nTest Result: ✅ SUCCESS\n{test_result}")
        else:
            self.pattern_preview.insert(tk.END, f"\n\nTest Result: ❌ NO MATCH")

    def generate_regex_pattern(self):
        """Generate regex pattern - SIMPLIFIED APPROACH"""
        if not hasattr(self, 'field_configs'):
            return "No fields configured"
        
        try:
            groups = self._build_field_groups()
            pattern_parts = []
            
            for i, group in enumerate(groups):
                group_pattern = self._process_group_pattern(group)
                pattern_parts.append(group_pattern)
                
                # Add .*? between all groups by default
                if i < len(groups) - 1:
                    pattern_parts.append(r'.*?')
            
            # Now, specifically remove .*? around the pattern groups that capture variable content
            pattern_string = ''.join(pattern_parts)
            
            # Find pattern groups (.+?) that are between literal groups and remove the .*? around them
            # We're looking for: .*?(.+?).*? and want to replace with (.+?)
            # But only when both sides have literal groups
            
            # This is a simplified approach - we'll identify the pattern group for item names
            # and manually adjust the quantifiers around it
            for i, group in enumerate(groups):
                if (any(cfg['pattern_type'] != 'literal' for cfg in group) and 
                    i > 0 and i < len(groups) - 1 and
                    not any(cfg['pattern_type'] != 'literal' for cfg in groups[i-1]) and
                    not any(cfg['pattern_type'] != 'literal' for cfg in groups[i+1])):
                    # This is a pattern group between two literal groups
                    # Replace .*?(.+?).*? with (.+?)
                    before_pattern = self._process_group_pattern(groups[i-1])
                    pattern_group = self._process_group_pattern(group)
                    after_pattern = self._process_group_pattern(groups[i+1])
                    
                    old_sequence = before_pattern + r'.*?' + pattern_group + r'.*?' + after_pattern
                    new_sequence = before_pattern + pattern_group + after_pattern
                    
                    pattern_string = pattern_string.replace(old_sequence, new_sequence)
            
            return pattern_string
        except Exception as e:
            return f"Error generating pattern: {e}"

    def _get_group_type(self, group):
        """Return the type of the group: 'literal' if all fields are literal, otherwise the pattern type of the first non-literal field."""
        if any(cfg['pattern_type'] != 'literal' for cfg in group):
            # It's a pattern group, now check if it's text pattern
            # We consider it a text pattern group if any field in the group is of type "text"
            if any(cfg['pattern_type'] == 'text' for cfg in group):
                return 'text'
            else:
                return 'other_pattern'
        else:
            return 'literal'

    def _get_separator_between_groups(self, current_index, previous_group_configs):
        """Get the appropriate separator between two groups of fields"""
        # Look at the content of the previous group and next field to determine separator
        previous_group_ends_with_space = False
        if previous_group_configs:
            last_config = previous_group_configs[-1]
            previous_group_ends_with_space = last_config['content'].endswith(' ')
    
        # Look at next field
        next_index = current_index + 1
        while next_index < len(self.field_configs) and not self.field_configs[next_index]['include_in_search']:
            next_index += 1
    
        if next_index < len(self.field_configs):
            next_config = self.field_configs[next_index]
            next_starts_with_space = next_config['content'].startswith(' ')
        else:
            next_starts_with_space = False
    
        # Determine separator based on context
        if previous_group_ends_with_space or next_starts_with_space:
            return r'\s*'  # Allow optional whitespace
        else:
            # For general content between fields, use a more permissive pattern
            # that captures everything up to the next fixed pattern
            return r'.*?'

    def _get_smart_separator(self, current_index, previous_group_configs):
        """Get smart separator based on context - PREVENTS CONSECUTIVE PATTERN ISSUES"""
        # Check what type of group we just processed
        previous_uses_pattern = any(cfg['pattern_type'] != 'literal' for cfg in previous_group_configs)
        
        # Find next included field
        next_index = current_index + 1
        while next_index < len(self.field_configs) and not self.field_configs[next_index]['include_in_search']:
            next_index += 1
        
        if next_index >= len(self.field_configs):
            return r'.*?'  # No next field, use normal wildcard
        
        next_config = self.field_configs[next_index]
        next_uses_pattern = next_config['pattern_type'] != 'literal'
        
        # STRATEGY: Remove quantifiers between pattern groups and literal fields
        # This prevents the "capture only spaces" issue
        if previous_uses_pattern and not next_uses_pattern:
            # Pattern group followed by literal field - NO SEPARATOR
            # This forces the pattern to capture everything up to the literal
            return ''
        elif not previous_uses_pattern and next_uses_pattern:
            # Literal field followed by pattern group - NO SEPARATOR  
            # This allows the pattern to start immediately after the literal
            return ''
        else:
            # Both same type - use normal wildcard
            return r'.*?'

    def _process_current_group(self, pattern_parts, current_group, current_group_configs, delimiter_escaped, current_index):
        """Process a group of fields and add the appropriate pattern - IMPROVED"""
        if len(current_group) == 1:
            # Single field
            config = current_group[0]
            if config['pattern_type'] == 'literal':
                pattern_parts.append(f"({re.escape(config['content'])})")
            else:
                pattern_parts.append(f"({self.get_pattern_for_type(config['pattern_type'], config['content'])})")
        else:
            # Multiple grouped fields
            any_uses_pattern = any(cfg['pattern_type'] != 'literal' for cfg in current_group_configs)
            
            if any_uses_pattern:
                # Use a single pattern for the entire grouped content
                pattern_parts.append(r"(.+?)")
            else:
                # All fields are literal - join them with the delimiter
                literal_patterns = [re.escape(cfg['content']) for cfg in current_group]
                grouped_pattern = delimiter_escaped.join(literal_patterns)
                pattern_parts.append(f"({grouped_pattern})")

    def get_pattern_for_type(self, pattern_type, content):
        """Get regex pattern for the selected pattern type - FIXED"""
        # pattern_type should be the internal type, not display name
        patterns = {
            "literal": re.escape(content),  # Exact match
            "word": r"\w+",  # A word
            "text": r".+?",  # Any text (non-greedy)
            "integer": r"\d+",
            "float": r"\d+\.\d+",
            "currency": r"\d+\.\d+",
            "date": r"\d{4}-\d{2}-\d{2}",
            "time": r"\d{2}:\d{2}:\d{2}",
        }
        return patterns.get(pattern_type, r".+?")

    def generate_pattern_explanation(self):
        """Generate explanation - PATTERN GROUP QUANTIFIER STRATEGY"""
        if not hasattr(self, 'field_configs'):
            return "No fields configured"

        explanation = "This pattern will capture:\n"

        groups = self._build_field_groups()

        for i, group in enumerate(groups):
            if len(group) == 1:
                config = group[0]
                pattern_desc = self.get_pattern_description(config['pattern_type'])
                explanation += f"{i+1}. '{config['content']}' as {config['field_name']} ({pattern_desc})\n"
            else:
                fields_list = " + ".join([f"'{cfg['content']}'" for cfg in group])
                any_pattern = any(cfg['pattern_type'] != 'literal' for cfg in group)
                pattern_desc = "flexible text pattern" if any_pattern else "exact text"
                explanation += f"{i+1}. Group: {fields_list} as {group[0]['field_name']} ({pattern_desc})\n"

        if not groups:
            return "No fields are included in the search pattern."
    
        # Add strategy explanation
        explanation += "\nQuantifier strategy:\n"
        explanation += "• Pattern groups connect directly to literals (no .*?)\n"
        explanation += "• This forces pattern groups to capture all content between fixed markers\n"
        explanation += "• Only literal→literal connections use .*? wildcards\n"

        return explanation

    def get_pattern_description(self, pattern_type):
        """Get human-readable description of pattern type"""
        descriptions = {
            "literal": "exact text",
            "word": "single word",  # A word
            "text": "any text",
            "integer": "whole number", 
            "float": "decimal number",
            "currency": "currency value",
            "date": "date",
            "time": "time"
        }
        return descriptions.get(pattern_type, "any text")

    def _explain_current_group(self, explanation, current_group, current_group_configs):
        """Explain the current group of fields and return the count of groups added"""
        if len(current_group) == 1:
            # Single field
            config = current_group_configs[0]
            pattern_desc = self.get_pattern_description(config['pattern_type'])
            explanation += f"• '{config['content']}' as {config['field_name']} ({pattern_desc})\n"
            return 1
        else:
            # Multiple grouped fields
            any_pattern = any(cfg['pattern_type'] != 'literal' for cfg in current_group_configs)
            fields_list = " + ".join([f"'{content}'" for content in current_group])
            
            if any_pattern:
                explanation += f"• Grouped fields {fields_list} as {current_group_configs[0]['field_name']} (flexible text pattern)\n"
            else:
                explanation += f"• Grouped fields {fields_list} as {current_group_configs[0]['field_name']} (exact text)\n"
            return 1

    def debug_field_configs(self):
        """Debug method to see current field configurations"""
        if not hasattr(self, 'field_configs'):
            return "No field configs"
    
        debug_info = "Field Configurations:\n"
        for i, config in enumerate(self.field_configs):
            debug_info += f"Field {i+1}: '{config['content']}'\n"
            debug_info += f"  - Group with next: {config['group_with_next']}\n"
            debug_info += f"  - Include in search: {config['include_in_search']}\n"
            debug_info += f"  - Pattern type: {config['pattern_type']}\n"
            debug_info += f"  - Field name: {config['field_name']}\n"
        return debug_info

    def test_pattern(self, pattern):
        """Test the pattern against the selected line - IMPROVED"""
        try:
            # Don't test if pattern is empty
            if not pattern or pattern == "No fields configured":
                return None
                
            matches = re.findall(pattern, self.selected_line)
            if matches:
                result = f"✅ SUCCESS: Found {len(matches)} match(es)\n"
                for i, match in enumerate(matches):
                    if isinstance(match, tuple):
                        result += f"  Group {i+1}: {match}\n"
                        # Show what each capture group captured
                        for j, capture in enumerate(match):
                            result += f"    - Field {j+1}: '{capture}'\n"
                    else:
                        result += f"  Match {i+1}: '{match}'\n"
                return result
            else:
                # Show why it might have failed
                result = "❌ NO MATCH - Possible issues:\n"
                result += "  • Grouping might be incorrect\n"
                result += "  • Delimiters between grouped fields might be missing\n"
                result += "  • Special characters might need escaping\n"
                
                # Try to show what part of the pattern might be problematic
                try:
                    # Test if the pattern compiles
                    re.compile(pattern)
                    result += f"  • Pattern compiles but doesn't match the sample line\n"
                except Exception as e:
                    result += f"  • Pattern error: {e}\n"
                    
                return result
        except Exception as e:
            return f"❌ PATTERN ERROR: {e}"

    def _process_group_pattern(self, group):
        """Generate pattern for a single group of fields"""
        if len(group) == 1:
            # Single field
            config = group[0]
            if config['pattern_type'] == 'literal':
                return f"({re.escape(config['content'])})"
            else:
                return f"({self.get_pattern_for_type(config['pattern_type'], config['content'])})"
        else:
            # Multiple fields in one group
            any_uses_pattern = any(cfg['pattern_type'] != 'literal' for cfg in group)

            if any_uses_pattern:
                # Use a single pattern for the entire grouped content
                return r"(.+?)"
            else:
                # All fields are literal - join them with the delimiter
                delimiter = self.get_delimiter()
                delimiter_escaped = re.escape(delimiter)
                literal_patterns = [re.escape(cfg['content']) for cfg in group]
                grouped_pattern = delimiter_escaped.join(literal_patterns)
                return f"({grouped_pattern})"

    def _build_field_groups(self):
        """Build field groups based on group_with_next settings"""
        groups = []
        current_group = []
    
        for i, config in enumerate(self.field_configs):
            if not config['include_in_search']:
                # If we have a current group, save it before skipping
                if current_group:
                    groups.append(current_group)
                    current_group = []
                continue
            
            # If current group is empty, start a new group
            if not current_group:
                current_group.append(config)
            else:
                # Check if previous field in current group wants to group with next
                if current_group[-1]['group_with_next']:
                    current_group.append(config)
                else:
                    # Previous field doesn't want to group, so start new group
                    groups.append(current_group)
                    current_group = [config]
        # Don't forget the last group
        if current_group:
            groups.append(current_group)
    
        return groups

    # =============================================================================

    def step_review_pattern(self):
        """Step 4: Use the field selection interface"""
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Generate the final pattern and test it
        final_pattern = self.generate_regex_pattern()
        test_results = self.test_pattern_on_all_lines(final_pattern)
        
        # Get extracted data
        columns, data_rows = self.prepare_data_preview(final_pattern)
        
        if not columns or not data_rows:
            ttk.Label(frame, text="Pattern didn't extract any data. Please go back and adjust your configuration.").pack(expand=True)
            return
        
        # Title
        title_label = ttk.Label(frame, text="Field Selection & Data Structure", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(anchor=tk.W, pady=(0, 20))
        
        # Pattern and test results (collapsible?)
        pattern_frame = ttk.LabelFrame(frame, text="Generated Pattern & Test Results", padding=10)
        pattern_frame.pack(fill=tk.X, pady=(0, 20))
        
        pattern_text = tk.Text(pattern_frame, height=3, width=80, wrap=tk.WORD)
        pattern_text.pack(fill=tk.X)
        pattern_text.insert(1.0, f"Pattern: {final_pattern}\n\nTest: {test_results}")
        pattern_text.config(state=tk.DISABLED)
        
        # Field selection interface
        selection_frame = ttk.LabelFrame(frame, text="Select Fields for Analytics", padding=10)
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.create_field_selection_interface(selection_frame, columns, data_rows)

        # Add register filter button
        register_frame = ttk.Frame(frame)
        register_frame.pack(fill=tk.X, pady=(10, 0))
    
        ttk.Button(register_frame, text="Register Filter for Real-time Processing", 
                command=self.manual_register_filter).pack(side=tk.LEFT, padx=(0, 10))

        
        # Finish button
        finish_frame = ttk.Frame(frame)
        finish_frame.pack(fill=tk.X)
        
        ttk.Button(finish_frame, text="Finish & Apply to Analytics", 
                  command=self.finish_and_apply).pack(side=tk.RIGHT)

    def create_field_selection_interface(self, parent, columns, data_rows):
        """Create interface for selecting and naming fields with better defaults"""
        # Instructions
        instr_text = """Select which fields to include in analytics, assign meaningful names, and set data types.
                        Checked fields will be available for calculations and reporting."""
        
        ttk.Label(parent, text=instr_text, justify=tk.LEFT, wraplength=600).pack(anchor=tk.W, pady=(0, 10))
        
        # Create a canvas with scrollbar for the field selection
        canvas = tk.Canvas(parent, height=200)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store field selection variables
        self.field_selection_vars = {}
        self.field_name_vars = {}
        self.field_type_vars = {}
        
        # Available data types
        self.available_types = [
            "text", "integer", "float", "currency", 
            "date", "time", "datetime", "boolean"
        ]
        
        # Header
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="Use", width=5).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Field Name", width=20).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(header_frame, text="Sample Data", width=30).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(header_frame, text="Data Type", width=15).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(header_frame, text="Original", width=15).pack(side=tk.LEFT, padx=(10, 0))
        
        # Field rows
        for i, col_name in enumerate(columns):
            field_frame = ttk.Frame(scrollable_frame)
            field_frame.pack(fill=tk.X, pady=2)
            
            # Use checkbox
            use_var = tk.BooleanVar(value=True)
            use_cb = ttk.Checkbutton(field_frame, variable=use_var)
            use_cb.pack(side=tk.LEFT)
            self.field_selection_vars[col_name] = use_var
            
            # Field name entry with better default names
            default_name = self.suggest_meaningful_field_name(col_name, data_rows, i)
            name_var = tk.StringVar(value=default_name)
            name_entry = ttk.Entry(field_frame, textvariable=name_var, width=20)
            name_entry.pack(side=tk.LEFT, padx=(10, 0))
            self.field_name_vars[col_name] = name_var
            
            # Sample data (first row)
            sample_data = data_rows[0][i] if i < len(data_rows[0]) else "N/A"
            sample_label = ttk.Label(field_frame, text=str(sample_data)[:25], width=25, 
                                    relief="sunken", background="white")
            sample_label.pack(side=tk.LEFT, padx=(10, 0))
            
            # Data type selection
            detected_type = self.detect_data_type([row[i] for row in data_rows if i < len(row)])
            type_var = tk.StringVar(value=detected_type)
            type_combo = ttk.Combobox(field_frame, textvariable=type_var, 
                                     values=self.available_types, state="readonly", width=12)
            type_combo.pack(side=tk.LEFT, padx=(10, 0))
            self.field_type_vars[col_name] = type_var
            
            # Original column name (read-only)
            orig_label = ttk.Label(field_frame, text=col_name, width=15, 
                                  relief="sunken", background="#f0f0f0", foreground="gray")
            orig_label.pack(side=tk.LEFT, padx=(10, 0))
            
            # Tooltip with full sample data
            if len(str(sample_data)) > 25:
                add_tooltip(sample_label, str(sample_data))
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Select All / None buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Select All", 
                  command=lambda: self.set_all_fields(True)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Select None", 
                  command=lambda: self.set_all_fields(False)).pack(side=tk.LEFT)
        
        # Store the data for later use
        self.extracted_columns = columns
        self.extracted_data = data_rows

    def suggest_meaningful_field_name(self, original_name, data_rows, index):
        """Suggest meaningful field names based on content analysis"""
        # Get sample values for this column
        sample_values = []
        for row in data_rows:
            if index < len(row):
                sample_values.append(str(row[index]))
        
        if not sample_values:
            return f"field_{index+1}"
        
        # Analyze content patterns
        content = " ".join(sample_values[:3])  # Look at first 3 samples
        
        # Common patterns for log data
        patterns = [
            (r'\d{4}-\d{2}-\d{2}', 'date'),
            (r'\d{2}:\d{2}:\d{2}', 'time'),
            (r'\[.*\]', 'context'),
            (r'\(.*\)', 'parentheses_content'),
            (r'[Pp]ed', 'currency'),
            (r'[Vv]alue', 'amount'),
            (r'[Rr]eceived', 'action'),
            (r'[Ss]hrapnel', 'item_type'),
            (r'[Ss]ystem', 'source'),
            (r'x\s*\d+', 'quantity'),
        ]
        
        for pattern, name in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return name
        
        # Check data type patterns
        if all(self._looks_like_date(v) for v in sample_values[:3]):
            return "date"
        elif all(self._looks_like_time(v) for v in sample_values[:3]):
            return "time"
        elif all(self._looks_like_number(v) for v in sample_values[:3]):
            if any('.' in v for v in sample_values[:3]):
                return "amount"
            else:
                return "quantity"
        elif all(len(v) <= 5 for v in sample_values[:3]):  # Short values
            return "code"
        elif any(v in ['[System]', '[Global]', '[Local]'] for v in sample_values[:3]):
            return "channel"
        
        # Default based on position and content
        if original_name.startswith('field_'):
            # Try to infer from sample content
            first_sample = sample_values[0].lower() if sample_values else ""
            if 'received' in first_sample:
                return "action"
            elif any(word in first_sample for word in ['shrapnel', 'component', 'item']):
                return "item_name"
            elif first_sample.isdigit():
                return "count"
            elif re.match(r'\d+\.\d+', first_sample):
                return "value"
        
        return original_name  # Keep original if it's already meaningful
    
    def _looks_like_date(self, value):
        """Check if value looks like a date"""
        return re.match(r'\d{4}-\d{2}-\d{2}', str(value)) is not None
    
    def _looks_like_time(self, value):
        """Check if value looks like a time"""
        return re.match(r'\d{2}:\d{2}:\d{2}', str(value)) is not None
    
    def _looks_like_number(self, value):
        """Check if value looks like a number"""
        try:
            float(str(value).strip('()'))
            return True
        except (ValueError, TypeError):
            return False

    def detect_data_type(self, values):
        """Detect the data type of a field based on sample values - WITH TIME DETECTION"""
        if not values:
            return "text"
        
        # Remove empty values
        clean_values = [v for v in values if v and str(v).strip()]
        if not clean_values:
            return "text"
        
        # Check if all values can be integers
        try:
            if all(self._is_integer(str(v)) for v in clean_values):
                return "integer"
        except:
            pass
        
        # Check if all values can be floats
        try:
            if all(self._is_float(str(v)) for v in clean_values):
                return "float"
        except:
            pass
        
        # Check for currency patterns
        currency_count = sum(1 for v in clean_values if self._is_currency(str(v)))
        if currency_count > len(clean_values) * 0.8:  # 80% match currency pattern
            return "currency"
        
        # Check for dates
        date_count = sum(1 for v in clean_values if self._is_date(str(v)))
        if date_count > len(clean_values) * 0.8:
            return "date"
        
        # Check for time patterns (NEW)
        time_count = sum(1 for v in clean_values if self._is_time(str(v)))
        if time_count > len(clean_values) * 0.8:
            return "time"
        
        # Check for datetime patterns (NEW)
        datetime_count = sum(1 for v in clean_values if self._is_datetime(str(v)))
        if datetime_count > len(clean_values) * 0.8:
            return "datetime"
        
        # Check for boolean patterns (NEW)
        boolean_count = sum(1 for v in clean_values if self._is_boolean(str(v)))
        if boolean_count > len(clean_values) * 0.8:
            return "boolean"
        
        # Default to text
        return "text"
    
    def _is_time(self, value):
        """Check if value looks like a time"""
        time_patterns = [
            r'^\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$',  # HH:MM:SS or HH:MM
            r'^\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*(AM|PM)$',  # 12-hour format
        ]
        return any(re.match(pattern, str(value).strip(), re.IGNORECASE) for pattern in time_patterns)
    
    def _is_datetime(self, value):
        """Check if value looks like a datetime"""
        datetime_patterns = [
            r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',  # ISO format
            r'^\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}',  # MM/DD/YYYY HH:MM
            r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',  # YYYY-MM-DD HH:MM:SS
        ]
        return any(re.match(pattern, str(value).strip()) for pattern in datetime_patterns)
    
    def _is_boolean(self, value):
        """Check if value looks like a boolean"""
        boolean_values = ['true', 'false', 'yes', 'no', '1', '0', 'on', 'off', 'enabled', 'disabled']
        return str(value).lower().strip() in boolean_values
        
    def _is_integer(self, value):
        """Check if value can be integer"""
        try:
            int(value.strip('()'))
            return True
        except:
            return False
    
    def _is_float(self, value):
        """Check if value can be float"""
        try:
            float(value.strip('()'))
            return True
        except:
            return False
    
    def _is_currency(self, value):
        """Check if value looks like currency"""
        return re.match(r'^-?\$?\d+(\.\d+)?$', value.strip()) is not None
    
    def _is_date(self, value):
        """Check if value looks like a date"""
        return re.match(r'\d{4}-\d{2}-\d{2}', value) is not None
    
    def get_type_color(self, data_type):
        """Get color for data type display"""
        colors = {
            "integer": "blue",
            "float": "green", 
            "currency": "darkgreen",
            "date": "purple",
            "time": "darkblue",
            "datetime": "magenta",
            "boolean": "orange",
            "text": "black"
        }
        return colors.get(data_type, "black")

    def set_all_fields(self, selected):
        """Select or deselect all fields"""
        for var in self.field_selection_vars.values():
            var.set(selected)
    
    def apply_data_structure(self):
        """Apply the selected field structure to analytics"""
        try:
            # Get selected fields and their new names
            selected_fields = {}
            for original_name, use_var in self.field_selection_vars.items():
                if use_var.get():  # Field is selected
                    new_name = self.field_name_vars[original_name].get()
                    selected_fields[original_name] = new_name
            
            if not selected_fields:
                tk.messagebox.showwarning("No Fields Selected", "Please select at least one field for analytics.")
                return
            
            # Prepare the data structure for analytics
            analytics_structure = self.prepare_analytics_structure(selected_fields)
            
            # Show preview of the final structure
            self.show_analytics_preview(analytics_structure)
            
            # Store for later use
            self.analytics_structure = analytics_structure
            
            tk.messagebox.showinfo("Success", 
                                  f"Data structure applied!\n\n"
                                  f"Selected {len(selected_fields)} fields for analytics.\n"
                                  f"You can now use the Analytics tab for advanced calculations.")
            
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to apply data structure: {e}")
    
    def prepare_analytics_structure(self, selected_fields):
        """Prepare the final data structure for analytics - USING USER-SELECTED TYPES"""
        structure = {
            'fields': {},
            'data': [],
            'summary': {
                'total_records': len(self.extracted_data),
                'selected_fields': len(selected_fields),
                'field_types': {}
            }
        }
        
        # Create field mapping with explicit capture group indices
        # The order in selected_fields should match the regex capture group order
        field_mapping = {}
        for i, original_name in enumerate(self.extracted_columns):
            if original_name in selected_fields:
                field_mapping[i] = selected_fields[original_name]
        
        # Build field definitions with CORRECT INDICES
        for i, original_name in enumerate(self.extracted_columns):
            if original_name in selected_fields:
                new_name = selected_fields[original_name]
                data_type = self.field_type_vars[original_name].get()
            
                # CRITICAL: Use the same index as the regex capture group
                structure['fields'][new_name] = {
                    'original_name': original_name,
                    'data_type': data_type,
                    'index': i  # This must match the regex capture group position
                }
                structure['summary']['field_types'][new_name] = data_type
        
        # Transform data using selected fields and user-selected types
        for row in self.extracted_data:
            transformed_row = {}
            for i, new_name in field_mapping.items():
                if i < len(row):
                    # Convert data based on USER-SELECTED TYPE
                    value = row[i]
                    data_type = structure['fields'][new_name]['data_type']
                    transformed_row[new_name] = TypeDetector.convert_value_by_type(self, value, data_type)
            
            structure['data'].append(transformed_row)
        
        return structure
    
    def convert_value_by_type(self, value, data_type):
        """Convert value to appropriate type based on user selection"""
        if value is None or str(value).strip() == '':
            return None
        
        try:
            if data_type == 'integer':
                return int(str(value).strip('()'))
            elif data_type == 'float':
                return float(str(value).strip('()'))
            elif data_type == 'currency':
                # Remove currency symbols and convert to float
                cleaned = re.sub(r'[^\d.-]', '', str(value))
                return float(cleaned)
            elif data_type == 'boolean':
                val_lower = str(value).lower().strip()
                return val_lower in ['true', 'yes', '1', 'on', 'enabled']
            elif data_type in ['date', 'time', 'datetime']:
                # Keep as string for now, could be converted to datetime objects later
                return str(value).strip()
            else:  # text
                return str(value).strip()
        except (ValueError, TypeError):
            # If conversion fails, return original value as string
            return str(value).strip()
            
    def show_analytics_preview(self, analytics_structure):
        """Show preview of the analytics structure"""
        preview_window = tk.Toplevel()
        preview_window.title("Analytics Structure Preview")
        preview_window.geometry("600x400")
        
        # Title
        ttk.Label(preview_window, text="Final Data Structure for Analytics", 
                  font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Summary
        summary_frame = ttk.LabelFrame(preview_window, text="Summary", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=5)
        
        summary_text = (f"• Total records: {analytics_structure['summary']['total_records']}\n"
                       f"• Selected fields: {analytics_structure['summary']['selected_fields']}\n"
                       f"• Field types: {', '.join([f'{k}({v})' for k, v in analytics_structure['summary']['field_types'].items()])}")
        
        ttk.Label(summary_frame, text=summary_text, justify=tk.LEFT).pack(anchor=tk.W)
        
        # Data preview
        data_frame = ttk.LabelFrame(preview_window, text="Data Preview", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview
        if analytics_structure['data']:
            columns = list(analytics_structure['data'][0].keys())
            tree = ttk.Treeview(data_frame, columns=columns, show='headings', height=8)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            for row in analytics_structure['data'][:10]:  # Show first 10 rows
                tree.insert('', tk.END, values=[row.get(col, '') for col in columns])
            
            scrollbar = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Close button
        ttk.Button(preview_window, text="Close", command=preview_window.destroy).pack(pady=10)

    def test_pattern_on_all_lines(self, pattern):
        """Test pattern against all sample lines and return summary"""
        try:
            compiled_pattern = re.compile(pattern)
            matches_count = 0
            total_lines = len(self.sample_lines)
            
            for line in self.sample_lines:
                matches = compiled_pattern.findall(line)
                if matches:
                    matches_count += 1
            
            result = f"Pattern tested on {total_lines} sample lines:\n"
            result += f"• Matches found: {matches_count} lines\n"
            result += f"• Success rate: {(matches_count/total_lines)*100:.1f}%\n"
            
            if matches_count == 0:
                result += "\n❌ No matches found in any sample lines. Please check your pattern."
            elif matches_count < total_lines:
                result += f"\n⚠️  Pattern matched {matches_count} out of {total_lines} lines."
            else:
                result += "\n✅ Pattern matches all sample lines!"
                
            return result
            
        except Exception as e:
            return f"Error testing pattern: {e}"
    
    def prepare_data_preview(self, pattern):
        """Prepare extracted data for display in treeview"""
        try:
            compiled_pattern = re.compile(pattern)
            
            # Get field names from configuration
            field_names = []
            groups = self._build_field_groups()
            for group in groups:
                if len(group) == 1:
                    field_names.append(group[0]['field_name'])
                else:
                    field_names.append(group[0]['field_name'])  # Use first field's name for group
            
            # Extract data from matching lines
            data_rows = []
            for line in self.sample_lines:
                matches = compiled_pattern.findall(line)
                for match in matches:
                    if isinstance(match, tuple):
                        data_rows.append(match)
                    else:
                        data_rows.append([match])
            
            return field_names, data_rows
            
        except Exception as e:
            print(f"Error preparing data preview: {e}")
            return [], []
    
    def generate_basic_analytics(self, columns, data_rows):
        """Generate basic analytics from extracted data"""
        analytics_text = "Basic Statistics:\n\n"
        
        # Identify numeric columns and calculate stats
        numeric_columns = {}
        
        for i, col_name in enumerate(columns):
            # Try to detect if column contains numeric data
            numeric_values = []
            for row in data_rows:
                if i < len(row):
                    value = row[i]
                    # Try to convert to float
                    try:
                        # Clean value (remove parentheses, etc.)
                        cleaned = str(value).strip('()')
                        num_val = float(cleaned)
                        numeric_values.append(num_val)
                    except (ValueError, TypeError):
                        continue
            
            if numeric_values:
                numeric_columns[col_name] = numeric_values
        
        # Generate statistics for numeric columns
        if numeric_columns:
            for col_name, values in numeric_columns.items():
                analytics_text += f"📊 {col_name}:\n"
                analytics_text += f"   Count: {len(values)}\n"
                analytics_text += f"   Sum: {sum(values):.2f}\n"
                analytics_text += f"   Average: {sum(values)/len(values):.2f}\n"
                analytics_text += f"   Min: {min(values):.2f}\n"
                analytics_text += f"   Max: {max(values):.2f}\n"
                analytics_text += f"   Range: {max(values)-min(values):.2f}\n\n"
        else:
            analytics_text += "No numeric fields detected for analysis.\n"
        
        # Label-based rupture analysis
        analytics_text += "Label-based Analysis:\n"
        label_columns = {}
        
        for i, col_name in enumerate(columns):
            if col_name not in numeric_columns:  # Assume it's a label column
                label_values = {}
                for row in data_rows:
                    if i < len(row):
                        value = str(row[i])
                        label_values[value] = label_values.get(value, 0) + 1
                
                if len(label_values) > 1:  # Only show if there are different values
                    label_columns[col_name] = label_values
        
        if label_columns:
            for col_name, value_counts in label_columns.items():
                analytics_text += f"🏷️  {col_name}:\n"
                for value, count in value_counts.items():
                    percentage = (count / len(data_rows)) * 100
                    analytics_text += f"   '{value}': {count} ({percentage:.1f}%)\n"
                analytics_text += "\n"
        else:
            analytics_text += "No categorical fields with multiple values detected.\n"
        
        return analytics_text
    
    def apply_to_main_tab(self):
        """Apply the generated pattern to the main regex builder tab"""
        try:
            # Get the final pattern and field configurations
            final_pattern = self.generate_regex_pattern()
            groups = self._build_field_groups()
            
            # Transfer to main plugin
            self.plugin.sample_text.delete(1.0, tk.END)
            self.plugin.sample_text.insert(1.0, self.selected_line)
            
            # Set delimiter if it matches
            self.plugin.delimiter_var.set(self.delimiter_var.get())
            
            # Trigger the split and analysis in the main tab
            self.plugin.split_sample_line()
            
            # TODO: Transfer field configurations to main tab
            # This would require mapping our wizard configs to the main tab's field configs
            
            tk.messagebox.showinfo("Success", 
                                  "Pattern has been applied to the main tab!\n\n" +
                                  "You can now:\n" +
                                  "1. Fine-tune field configurations\n" +
                                  "2. Register the filter for real-time extraction\n" +
                                  "3. Use the Analytics tab for advanced analysis")
            
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to apply pattern to main tab: {e}")
    
    # =============================================================================
    
    def previous_step(self):
        """Go to previous step"""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)
    
    def next_step(self):
        """Go to next step or finish"""
        # Validate current step before proceeding
        if not self.validate_current_step():
            return
            
        if self.current_step < 3:
            self.show_step(self.current_step + 1)
        else:
            self.finish_wizard()
    
    def validate_current_step(self):
        """Validate the current step before proceeding"""
        if self.current_step == 0:
            # Validate input
            text = self.input_text.get(1.0, tk.END).strip()
            if not text:
                tk.messagebox.showerror("Error", "Please paste at least one log line")
                return False
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            self.sample_lines = lines
            
            if len(lines) == 1:
                self.selected_line = lines[0]
            else:
                # Let user select which line to use
                self.show_line_selection_dialog(lines)
                # Wait until user has made a selection
                if not self.selected_line:
                    return False  # User canceled or didn't select
        
        elif self.current_step == 1:
            # Validate delimiter
            if self.delimiter_var.get() == "custom" and not self.custom_delimiter.get().strip():
                tk.messagebox.showerror("Error", "Please enter a custom delimiter")
                return False
        
        return True
    
    def finish_wizard(self):
        """Finish the wizard and apply the pattern"""
        tk.messagebox.showinfo("Wizard Complete", 
                              "Pattern wizard completed! The pattern has been applied to the main tab.")
        # Here we'll transfer the created pattern to the main tab
        
    def finish_and_apply(self):
        """Finish wizard and apply data structure to analytics"""
        try:
            # Get selected fields and their new names
            selected_fields = {}
            for original_name, use_var in self.field_selection_vars.items():
                if use_var.get():
                    new_name = self.field_name_vars[original_name].get()
                    selected_fields[original_name] = new_name

            print("=== WIZARD FIELD SELECTION ===")
            print(f"DEBUG: Selected fields: {selected_fields}")

            if not selected_fields:
                tk.messagebox.showwarning("No Fields Selected", "Please select at least one field for analytics.")
                return
        
            # Prepare the data structure
            analytics_structure = self.prepare_analytics_structure(selected_fields)

            # DEBUG: Check what we're creating
            print("=== ANALYTICS STRUCTURE CREATED ===")
            print(f"DEBUG: Fields: {list(analytics_structure['fields'].keys())}")
            print(f"DEBUG: Fields: {list(analytics_structure)}")
            print(f"DEBUG: Fields: {analytics_structure}")
        
            for field_name, field_info in analytics_structure['fields'].items():
                print(f"  {field_name}: index={field_info.get('index')}, type={field_info.get('data_type')}")
                # Apply to plugin's analytics engine
                self.plugin.analytics_engine.extracted_data = analytics_structure['data']
                self.plugin.analytics_structure = analytics_structure
        
            # Update analytics display if available
            if hasattr(self.plugin, 'update_analytics_display'):
                self.plugin.update_analytics_display()
        
            print("=== AUTOMATIC FILTER REGISTRATION ===")
            regex_pattern = self.generate_regex_pattern()
            self.auto_register_filter_from_wizard(analytics_structure, selected_fields, regex_pattern)
            #self.auto_register_filter_from_wizard(analytics_structure, selected_fields)
        
            tk.messagebox.showinfo("Wizard Complete", 
                                f"Pattern wizard completed successfully!\n\n"
                                f"Selected {len(selected_fields)} fields for analytics.\n"
                                f"Total records: {len(analytics_structure['data'])}\n\n"
                                f"Records: {analytics_structure['data']}\n\n"
                                f"Structures: {analytics_structure}\n\n"
                                f"You can now use the Analytics tab for advanced calculations.")
        
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to apply data structure: {e}")

    def auto_register_filter_from_wizard(self, analytics_structure, selected_fields, regex_pattern):
        """Automatically register a filter when wizard completes"""
        try:
           
            if not regex_pattern or regex_pattern.startswith("#"):
                print("DEBUG: No valid regex pattern generated by wizard")
                return False
            
            # Create filter ID
            filter_id = f"wizard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Prepare filter configuration
            filter_config = {
                'regex': regex_pattern,
                'field_definitions': analytics_structure['fields'],  # This has the correct indices!
                'field_names': list(selected_fields.values()),
                'sample_line': getattr(self, 'selected_line', ''),
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'last_used': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'match_count': 0
            }
            
            # DEBUG: Verify what we're registering
            print("=== AUTO-REGISTERING FILTER ===")
            print(f"Filter ID: {filter_id}")
            print(f"Regex: {regex_pattern}")
            print(f"Field definitions with indices:")
            for field_name, field_info in filter_config['field_definitions'].items():
                print(f"  {field_name}: index={field_info.get('index')}, type={field_info.get('data_type')}")

        except Exception as e:
            print(f"DEBUG: Error in auto_register_filter_from_wizard from {self.__class__.__name__}:  {e}")
            return False
            
        # Register with main app
        
        if self.__class__.__name__ == "DataExtractorPlugin":
            print(f"DEBUG: Class calling is {self.__class__.__name__}")
            success = self.app.register_plugin_filter(
                self.name,
                regex_pattern,
                filter_id,
                self.on_plugin_filter_match
            )
            if success:
                # Save to filter manager
                self.filter_manager.save_filter(filter_id, filter_config)
                print(f"DEBUG: Successfully registered and saved filter: {filter_id}")
                # Update filter display if available
                if hasattr(self, 'update_filters_display'):
                    self.update_filters_display()
                return True
            else:
                print("DEBUG: Failed to register filter with main app")
                return False
        else:
            success = self.plugin.app.register_plugin_filter(
                self.plugin.name,
                regex_pattern,
                filter_id,
                self.plugin.on_plugin_filter_match
            )
            if success:
                # Save to filter manager
                self.plugin.filter_manager.save_filter(filter_id, filter_config)
                print(f"DEBUG: Successfully registered and saved filter: {filter_id}")
                # Update filter display if available
                if hasattr(self.plugin, 'update_filters_display'):
                    self.plugin.update_filters_display()
                return True
            else:
                print("DEBUG: Failed to register filter with main app")
                return False
                
            
    def manual_register_filter(self):
        """Manual filter registration from wizard"""
        if hasattr(self, 'analytics_structure') and self.analytics_structure:
            selected_fields = {info['original_name']: name for name, info in self.analytics_structure['fields'].items()}
            self.auto_register_filter_from_wizard(self.analytics_structure, selected_fields)
        else:
            tk.messagebox.showwarning("No Data", "Please complete the wizard first.")
# plugins/data_extractor_plugin.py
from etail_plugin import ETailPlugin
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import csv
import re
from pathlib import Path
from datetime import datetime

class DataExtractorPlugin(ETailPlugin):
    def __init__(self, app):
        super().__init__(app)
        self.name = "Data Extractor"
        self.version = "1.0"
        self.description = "Extract and organize data from regex matches into structured formats"
        
        # Configuration
        self.config_file = Path("~/.etail/data_extractor_config.json").expanduser()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.config = {
            "extraction_profiles": {
                "default": {
                    "clean_patterns": [r"-", r"\.", r":", r"\s+"],  # Characters to remove
                    "field_separator": ",",  # For multiple values in one match
                    "output_format": "csv",
                    "auto_calculate": True,
                    "calculations": ["count", "sum", "average"]
                }
            },
            "current_profile": "default",
            "output_directory": str(Path("~/.etail/extracted_data").expanduser()),
            "auto_save": False
        }
        
        # Data storage
        self.extracted_data = []
        self.current_session_data = []
        
        self.load_configuration()
        
    def setup(self):
        """Setup the data extractor"""
        self.app.messages(2, 9, "Data Extractor enabled - Ready to process regex matches")
        return True
        
    def teardown(self):
        """Stop the data extractor"""
        self.save_configuration()
        self.app.messages(2, 9, "Data Extractor disabled")
        
    def load_configuration(self):
        """Load plugin configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception as e:
            print(f"Error loading data extractor config: {e}")
            
    def save_configuration(self):
        """Save plugin configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving data extractor config: {e}")
            
            
            
    def process_regex_matches(self, matches, pattern_name="unknown"):
        """Process regex findall results and extract structured data"""
        if not matches:
            return None
            
        profile = self.config["extraction_profiles"][self.config["current_profile"]]
        processed_data = []
        
        for i, match in enumerate(matches):
            if isinstance(match, (list, tuple)):
                # Handle multiple capture groups
                processed_item = self._process_match_groups(match, profile, i, pattern_name)
            else:
                # Handle single string match
                processed_item = self._process_single_match(str(match), profile, i, pattern_name)
                
            if processed_item:
                processed_data.append(processed_item)
        
        # Store and optionally auto-save
        self.current_session_data.extend(processed_data)
        self.extracted_data.extend(processed_data)
        
        # Perform calculations
        calculations = self._perform_calculations(processed_data)
        
        # Auto-save if enabled
        if self.config.get("auto_save", False):
            self.export_to_csv(processed_data, f"auto_{pattern_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        return {
            "processed_data": processed_data,
            "calculations": calculations,
            "summary": f"Processed {len(processed_data)} matches from pattern '{pattern_name}'"
        }
    
    def _process_single_match(self, match_text, profile, index, pattern_name):
        """Process a single string match"""
        # Clean the text
        cleaned_text = match_text
        for pattern in profile.get("clean_patterns", []):
            cleaned_text = re.sub(pattern, '', cleaned_text)
        
        # Extract numeric values
        numbers = self._extract_numbers(cleaned_text)
        
        return {
            "id": f"{pattern_name}_{index}",
            "original_text": match_text,
            "cleaned_text": cleaned_text,
            "numbers": numbers,
            "pattern_name": pattern_name,
            "timestamp": datetime.now().isoformat(),
            "match_index": index
        }
    
    def _process_match_groups(self, match_groups, profile, index, pattern_name):
        """Process multiple capture groups"""
        cleaned_groups = []
        all_numbers = []
        
        for group in match_groups:
            cleaned = str(group)
            # Clean each group
            for pattern in profile.get("clean_patterns", []):
                cleaned = re.sub(pattern, '', cleaned)
            cleaned_groups.append(cleaned)
            
            # Extract numbers from each group
            numbers = self._extract_numbers(cleaned)
            all_numbers.extend(numbers)
        
        return {
            "id": f"{pattern_name}_{index}",
            "original_groups": list(match_groups),
            "cleaned_groups": cleaned_groups,
            "numbers": all_numbers,
            "pattern_name": pattern_name,
            "timestamp": datetime.now().isoformat(),
            "match_index": index
        }
    
    def _extract_numbers(self, text):
        """Extract all numeric values from text"""
        # Find integers and decimals
        number_pattern = r"-?\d+\.?\d*"
        matches = re.findall(number_pattern, text)
        return [float(match) if '.' in match else int(match) for match in matches]
        
        
    def _perform_calculations(self, data):
        """Perform calculations on extracted data"""
        if not data:
            return {}
            
        profile = self.config["extraction_profiles"][self.config["current_profile"]]
        calculations = profile.get("calculations", [])
        results = {}
        
        # Extract all numbers from all items
        all_numbers = []
        for item in data:
            all_numbers.extend(item.get("numbers", []))
        
        if not all_numbers:
            return {"message": "No numeric data found for calculations"}
        
        for calc in calculations:
            if calc == "count":
                results["total_matches"] = len(data)
                results["total_numbers"] = len(all_numbers)
                
            elif calc == "sum" and all_numbers:
                results["sum"] = sum(all_numbers)
                
            elif calc == "average" and all_numbers:
                results["average"] = sum(all_numbers) / len(all_numbers)
                
            elif calc == "min" and all_numbers:
                results["min"] = min(all_numbers)
                
            elif calc == "max" and all_numbers:
                results["max"] = max(all_numbers)
        
        return results
        
    def export_to_csv(self, data=None, filename_prefix="extracted_data"):
        """Export data to CSV file"""
        if data is None:
            data = self.extracted_data
            
        if not data:
            messagebox.showwarning("No Data", "No data to export")
            return
            
        output_dir = Path(self.config["output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{filename_prefix}_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if data and "numbers" in data[0]:
                    # Simple format - just numbers
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Pattern", "Numbers", "Cleaned Text"])
                    for item in data:
                        numbers_str = ", ".join(map(str, item.get("numbers", [])))
                        writer.writerow([
                            item.get("id", ""),
                            item.get("pattern_name", ""),
                            numbers_str,
                            item.get("cleaned_text", item.get("cleaned_groups", [""])[0])
                        ])
                else:
                    # Complex format with all fields
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                    
            self.app.messages(2, 9, f"Data exported to {filename}")
            return str(filename)
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")
            return None
    
    def clear_data(self, session_only=True):
        """Clear extracted data"""
        if session_only:
            self.current_session_data = []
            self.app.messages(2, 9, "Session data cleared")
        else:
            self.extracted_data = []
            self.current_session_data = []
            self.app.messages(2, 9, "All data cleared")
    
    def get_data_summary(self):
        """Get summary of extracted data"""
        total_items = len(self.extracted_data)
        session_items = len(self.current_session_data)
        
        all_numbers = []
        for item in self.extracted_data:
            all_numbers.extend(item.get("numbers", []))
        
        return {
            "total_records": total_items,
            "session_records": session_items,
            "total_numbers": len(all_numbers),
            "number_sum": sum(all_numbers) if all_numbers else 0,
            "unique_patterns": len(set(item.get("pattern_name", "") for item in self.extracted_data))
        }

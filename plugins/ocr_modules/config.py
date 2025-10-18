# plugins/ocr_modules/config.py
import json
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    def __init__(self):
        self.config_file = Path("~/.etail/ocr_plugin_config.json").expanduser()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Your default config (copied from main file)
        self.default_config = {
            "tesseract_path": "",
            "check_interval": 2.0,
            "confidence_threshold": 70,
            "language": "eng",
            "ocr_engine_mode": 3,
            "page_segmentation_mode": 6,
            "regions": [],
            "use_mss": True,
            
            # Capture method settings
            "capture_method": "auto",  # Default capture method
            "region_capture_methods": {},  # Per-region capture methods
            
            # Gaming optimization settings
            "enable_preprocessing": True,
            "enable_fuzzy_matching": False,
            "fuzzy_threshold": 85,
            "tts_alerts": False,
            "performance_monitoring": True,
            
            # Game-specific OCR profiles
            "game_profiles": {
                "default": {"psm": 6, "oem": 3, "contrast": 1.5, "scale_factor": 1.0},
                "small_text": {"psm": 7, "oem": 3, "contrast": 2.0, "scale_factor": 2.0},
                "console_text": {"psm": 6, "oem": 3, "contrast": 1.8, "scale_factor": 1.5},
                "ui_text": {"psm": 6, "oem": 3, "contrast": 1.3, "scale_factor": 1.0}
            },
            "current_profile": "default",
            
            # COLOR FILTERING SETTINGS
            "enable_color_filtering": True,
            "color_tolerance": 30,
            "color_filters": {
                "default": {
                    "target_colors": [
                        {"r": 255, "g": 255, "b": 255},  # White text
                        {"r": 255, "g": 255, "b": 0},    # Yellow text  
                        {"r": 255, "g": 0, "b": 0},      # Red text
                        {"r": 0, "g": 255, "b": 0}       # Green text
                    ],
                    "invert_after_filter": True
                },
                "dark_text": {
                    "target_colors": [
                        {"r": 0, "g": 0, "b": 0},        # Black text
                        {"r": 50, "g": 50, "b": 50},     # Dark gray
                        {"r": 100, "g": 0, "b": 0}       # Dark red
                    ],
                    "invert_after_filter": False
                }
            },
            "current_color_profile": "default"
        }

        self.config = self.default_config.copy()
        self.load_configuration()
    
    def load_configuration(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Handle nested updates (game_profiles, color_filters)
                    if 'game_profiles' in loaded_config:
                        self.config['game_profiles'].update(loaded_config['game_profiles'])
                        loaded_config.pop('game_profiles', None)
                    if 'color_filters' in loaded_config:
                        self.config['color_filters'].update(loaded_config['color_filters'])
                        loaded_config.pop('color_filters', None)
                    self.config.update(loaded_config)
        except Exception as e:
            print(f"Error loading OCR plugin config: {e}")
    
    def save_configuration(self):
        try:
            # Update regions before saving
            if hasattr(self, 'app') and hasattr(self.app, 'plugins'):
                plugin = self.app.plugins.get('OCRMonitorPlugin')
                if plugin and hasattr(plugin, 'regions'):
                    self.config["regions"] = plugin.regions
                    print(f"DEBUG: Saving {len(plugin.regions)} regions")

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"? DEBUG: Config saved to {self.config_file}")
        except Exception as e:
            print(f"? DEBUG: Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        self.save_configuration()
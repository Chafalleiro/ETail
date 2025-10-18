import PyInstaller.__main__
import os

def build_main_app():
    PyInstaller.__main__.run([
        'etail.py',
        '--onefile',
        #'--windowed',
        '--name=Etail',
        '--icon=Etail.ico',
        '--add-data=Etail.ico;.',
        '--add-data=default_filters.json:.',
        '--add-data=thunk.wav:.', 
        '--add-data=LICENSE:.',
        '--add-data=README.md:.',
        '--add-data=fonts:fonts',
        # Only include the plugin INTERFACE, not the actual plugins
        #'--add-data=plugins/__init__.py:plugins',
        #'--add-data=plugins/etail_plugin.py:plugins',
        '--hidden-import=importlib',
        '--clean'
    ])

if __name__ == "__main__":
    build_main_app()
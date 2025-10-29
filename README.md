# ETail

Entropia Universe Logging Tool. Now more flexible and capable of monitoring every kind of text logfiles, not just the game chat log. Binary logs are out of the scope of this program.

V0.2 October 2025.

Features:

* Real time log monitoring, only last lines loaded so medium logs (50-100MB) are loaded seamlessly.
* Fast response.
* Plugin system to upgrade capabilities. App comes with an OCR screen reader, a sample plugin and a statistic app.
* Track strings, simple words or complez regular expressions.
* Regular expression helper to create complex searches.
* Configurable alerts, Text to speech, sound alert, system notifications or popup windows.
* Configuration and filters load and save in separate files to have several configurations for each kind of log monitoring.
* Matching lines can be hidden from display.

This tool comes in two ways, a python script that can be used within a system with Python installed, or a standalone compiled exe (ATM only windows 64 version) that can be downloaded from the releases section. The precompiled plugins are also there.

Caveats:

Although this is the third version of ETail, it was completely refactored and rewitten in Python from the HTML/VBScript HTA in wich was launched before. Application is recently finished for beta testing. Expect some bugs and GUI typos.

Although the goal is simple, monitor a text logfile, the program is complex and full of options. Start with the provided filters to check how it works and keep track of your saved configurations.

INSTALLING:

 Installing script: Just put it anywhere in your system, after the first lauch a config file will be writen in your home directory "(Drive):\Users\(username)\.etail" which tracks las dir used for autoloading purposes. Plugin data will also be stored in the user dir.

 Installing binaries: Just do the same thing, put etail.exe in any directory you see fit.
 
# QUICK SETUP:



# CONFIGURATION AND RUNNING:

The program is divided into tabs, each one has a function.

## Log View Tab
	
You will se several buttons.

**Start Tail** will start monitoring the selected logfile.

**Stop Tail** will stop the monitoring.

**Pause/Resume** will pause and resume the monitoring without closins/opening the log.

**Search field** Enter simple strings to search into the log display. Note that the log window display will only have a limited numbner of lines in memory (50k) configurable in the script source and old lines will be clened and rotated.

**Find** Start the search, found strings will be colored and can be navigated using the arro buttos that will activate once the search is done.

**Clear** Clear the file and the search

**Log Content** Main window display. Here the log tailed will be shown, matched lines will have different configurable colors. It has a 50.000 lines buffer that will be rotated every 10k lines after reaching the limit.

## Configuration Tab

#### File Settings

**Default log file** Browse for a log file to monitor here, the path will be saver for later use and loasded if autoload is marked.

**Filters file** Here you can load and save yor filter. Since this tool was initially intended forn Entropia Uneverse, there are some premade filters you can use in the releases section.

**Advanced filters file** The same as above.

#### Application Settings

**Initial lines** Number of lines to load when the monitorig starts. It will load from the end, so 55 lines means that the las 55 lines of the log will be loaded.

**Refresh Interval** In miliseconds, tiome between checks of the log, adjust it for your need and system load.

**Autoload las coniguration** If checked it wil load the last filters and log file you saved.

**Change theme** Change between a list of predefined GUI themes.

#### Recent Files

**Recent filters** List of the last filter saved files, you can load one of the list.

**Recent advanced filters** Same as above but with advanced filters

#### Conf Saving and loading controls.

**Save configuration** Save the current configuration (log file and filters) into a file for later use.

**Load configuration** Load a saved configuration.

**Reset to defaults*** Empty the filter and log info.

## Simple Filters Tab

**Filter Pattern** Here you can enter a predefined regex pattern that you already had saved elsewhere, or enter a simple string to be matched against the lines read in the log. Check the regex box for using the regex in full.

**Text color** Select the text color of the line where the pattern is matched.

**Text color** Select the background color of the line where the pattern is matched.

**Action** Select what happens when a match if found.

* None - The line is just tinted with the selected colors.
* Sound - A sound will be played, you can select wave, ogg or mp3 sounds.
* TTS - Text to speech. When a line matches the search field read the text you can enter in "Action modifier" field. Select a voice installed in your system in the adjacent dropdown. You can test it.
* Skip - The line with the match will not be shown in the log window.
* Notification - A system tray alert will be lauched with the text you enter in the action modifier field.
* Dialog - A blocking popup will be shown in the program window when a match is found.

**Add filter** - When you have finished configuring the filter, add it to the list of aplicable filters. They are automatically saved in the active filter file, But its always a good idea to do it manually later, when you have finished editing filters.

**Edit selected** - Select a filter from the list below and edit it with this button.

**Update filter** - Update and save a filter you loaded for editing.

**Cancel edit** - Unload the filter frrom the editing fields.

**Remove selected filter** - Remove a filter selected on the list. WARNING not undo at the moment.

## Advanced Filters Tab

This tab has the colapsible sections. Regex builder, Actions and Saved Advanced Filters. At the bottom you have control buttons for saving, displaying and testing.

### Regex Builder

Add up to ten positional vale fields. You can treat the values entered as strings, words, plain regexes or insert a predefined expresion made of some of the most common patterns found in a log file. Positional means thatevery field must be satisfied in its place to count as valid. So if we fill first a field with a date matching pattern, and then a string, if the string is found before the date it won't count as a valid match. Useful to match lines with variable values between patterns.

**Common patterns** - In this dropdown you can select whithin a variety of patterns that are common in logs, dates, time, IP addresses, e-mail, MAC adresses, etc.

**Insert pattern** - Insert the selected pattern in the active field that is editing.

**Preview** - See the selected pattern regex and its uses.

**Filter Name** Name this filter for better organization.

**Enable**	Use this checkbox to enable the filter after storing it.

**Field x** There are up to ten fields to use. This way you can create a complex regex with grouping, sorted matcheng, etc. Here you can add a part of th e pattern you want.

 **Combobox 1** Decide how to treat the field. As a string it will be a common string. As word will be surrounded by \b modifiers. As reges will be inserted as is. Predefined will let you choose between several predefined common patterns.

**Remove** **Insert** Helpers for predefined patterns. Remove them or insert a predefined pattern.

**Add field*** Add up to ten fields to the expression. There is a combobox on how to separate them. Lazy anything in between (.*), inmediate after just insert the field. Word boundary add \b, whitespace \s+ or a user defined separator.


**Generated regex** Here the generated regex will be shown.

**Test Regex Pattern** Will open adialog where you can test the expression with a given text. You can add or paste any text you want to match against your expression.

**Copy to clippboard** Copy your regular expression and test it or save it for later. Sometimes is easier to make here a regex, test it and edit the tricky parts and then paste it as a simple filter. This is a very noce site to test yout patterns. https://regex101.com/

### Actions

This is just as the actions of the simple filters tab.

### Saved Advanced filters

In this section you can view, prepare for editing, activate or deactivate your saved advanced filters.

**Load selected** Load the filter into the builder section for editing.

**Delete selected** Delete the selected filter.

**Toogle enabled** Enable/disable the filter.

### General Tab Buttons

**Store advanced filter** Store a filter that is being edited.

**Clear form** Clear the filter editing fields and unload a loaded one.

**Test** Test the pattern.

**Expand all** Expand and view all the sections.

**Collapse all** Collapse and hide all the sections in tab.


## Plugins Tab

The plugins must be put into the plugins directory of the application home dir. There is a sample plugin included in the release files and the code. Documentation of integration is on the way. Note that while the main app could load whl files, is still a testing feature, the safest option is to import the modules needed into the main application if you want to compile it.

The app can use uncompiled and source plugins, the compiled ones take precedence in case there are two of the same version.

For safety plugins are by default unloaded at the star of the application.

The application comes with three plugins. A sample plugin, an OCR monitoring plugin and a data analysis plugin. Their documentations is provided in their own repositories and readmes.

**Discover plugins** Rescan the plugins directory.

**Reload all** Try to reload the plugins found.

**Open plugins folder** Open the older where plugins are stored.

**Available plugins** A list of the plugins discovereed and ready to use. Also presents information about the plugin and it's state.

**Enable plugin** Enable the selected plugin. It will start running its code after enebled.

**Disable plugin** Uload and stops plugin execution.

**Settings** Open the plugin settings and GUI.

**Plugin information** Shows the information provided abut the plugin.


TODO:
* Skinning and styling the app.
* Keep cleaning the code and bug hunting.
* Documentation for plugin making, regular expression creation and general use.
* Help system and popup tags.
* Cleanup and adjust the GUI.
* Refactor the code.
* Get rid of Pyautogui to downsize the exe.
* Remake some parts of the regex creator. It needs to be more intuitive and complete.
* Activation routines for simple filters.

Totally rewritten from HTA to Python. 
Authors Deepseek AI and Alfonso Abelenda Escudero.

Old 0.11 version installer and sources can be downloaded from here ATM
https://github.com/Chafalleiro/ETMaps/releases/tag/ETMAPS

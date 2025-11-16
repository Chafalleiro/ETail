# **ETAIL PLUGINS**

_________________________________________________________________

These plugins serve as example and add functionalities to the main ETail application. As the main app ATM are only tested and compiled in win64.



## **OCR screen monitor**

It read the screen, a window or a portion of them and checks if the given text is found. After that you can choose to issue a Text to Speech alert, a system notification alert or both. You must enable the notifications for the app (or Python is you are runnig the sources) in order for them to work. It uses pytesseract, and you will need to install tesseract to run it.

The configuration of this plugin is not instanced, so every tab of ETail will share its configs.


#### **Tesseract tab**

To check if Tesseract is on the system. It will try to find the executable in default path, but you have a browse button to manually put its path.

You can verify if it's the correct program with a test button.

#### **Regions tab**
Here you can select regions in screen or windows, pick colors from regions to ease the detection. Edit, test and switch their activity state.

After selecting a region it will be active and staart capturing.

**Select Region**: After clicking the button you can draw a rectangle to watch. 
* After drawing it you will be presented a dialog in wich you can fine tune the dimensios of the area, adjust the cooldown of the OCR to reread the screen in the first tab Basic Settings.
* Patterns and TTS. Edit the pattern to match and the message that will be sent to the main app to alert via TTS or notification. You can add more patterns and do combinations to raise the probability of a match. Notice that if several patterns have the same message they will be counted instead of repeating.
* Cooldown: Default 5 min. Time between alerts, capturing is set in another tab.

 Remove pattern to erase one.
 
 Add Pattern to add new ones.

* Advanced.
 Select the capture method, or let the app test them.
 Select a color profile for the color filtering.
 
 **Add Manual**: Opens the manual region dialog, the same as the select region.
 
  **Select Window (List)**: To select a window and a region within it. You can configure patterns and TTS, and capture options like the other dialogs.
 * Select form List: Will present a list of active windows in your computer. Select wich to monitor.
 * After selecting a window you can select a subregion of it.
 * **Test capture** to see wich method will capture the window you selected. If the capture is black try another metohd from the advanced list.
 * Cooldown is at 300s. (5 min) for default. Change it to suit your needs.
 
  **Pick Colors**: Select the color of the text you want to capture.

  **Region Preview**: Shows the regions and states you have configured.

  **Configured Regions**: A list of the regions you have configured. Select one to Test, Edit, Remove or Activate.

  **Test Region**: Shows a capture of the region you selected in the list to check and configure it's settings.

  **Edit**: Shows a dialog to edit the subregions, patters and advanced settings of the selected region.

  **Remove**: Remove the selected region

  **Toogle**: Activate or deactivate a region capture.

#### **OCR Settings**

Change settings on how the OCR works.

* Check Interval: Interval between captures.
* OCR Language: Select the language the OCR will try to decode.
* Default cooldown: Time to rest between checks.
* Enable TTS alerts: If checked when a pattern matches it will tell the main app to say the text configured. The interval between alerts is set in the cooldown setting of the regions dialogs.
* Enable notification alerts: System notifications, remember to authorize the Main app and plugin.
* Apply: Apply and save your settings.


#### **Gaming**

Settings to help games text capturing.

* Profile: Set the text profile the app will read.
* Enable Image Pre-Processing:  will accelerate the processing of the captured region.
* Enable Fuzzy Text Matching: Enebla and set the threshold of pixels to recognize a letter.
* Enable Performance monitoring: Shows the succes percentage.

#### **Colors**

* Enable color filtering. Helps the OCR select the color of the font you look into.
* Default color profile: Select wich color profile will be used as default.
* Color Tolerance: Select the thereshold of the colors.
* Available color profiles: List of saved color profiles.
* Delete Selected Profile: As it says.
* Apply color settings: Aply the slected profile and settings.


## **Data Extractor**
A plugin that extract data from matched regular expressions in the logs. You have two ways to create a data exractor regex, a pattern wizard and a Regex Builder from a given regular expression Already prepared elsewhere.

#### **Pattern Wizard**

From a line of the log monitored you can select what to search andwhat to extract.

1. Input: Paste here the log lines you want to analyze. If you haven't, a dialog to select one of them will open.
2. Delimiter: Chose a delimiter to split the line, space is default but you can select other common delimeter for txt data files or enter a custom one. Space is default-
3. Fields: The wizard will traverse the splitted content, each part will be a field for seacrh pattern. You can:
	* See the field contents.
	* Choose to join with the next field or make it independent.
	* Include or exclude this portion from the search pattern.
	* Select what type of pattern will be:
		1. Exact text (literal) will be matched.
		2. Single word. The field will search a word separated with spaces.
		3. Any text: Any text chars will match.
		4. Whole number: Will match any integer.
		5. Decimal number. Will match any decimal number with decimal point.
		6. Currency
		7. Date: Will match any date in AAAA-MM-DD foprmat.
		8. Time: Will match any time in HH:MM:SS format.
	* Set the name of the field.
	* You will see how the match are being done, and what data is being extracted in the pattern preview window.
	* When you are done with one field, up right there are control buttons to traverse the line and configure yur matchings.

4. When you are done the Next button in lower right will actvate. Review and select wich fields will be used in the analytics.
5. Finish. The pattern you created will be added to the filter management list and will be activated.

#### **Regex builder**

A "faster" way to create your extractor data. You'll need to have prepared your regular expression in advance, eithor the main app regex builder, the aforetold wizard or a tool like this ones: https://regex-generator.olafneumann.org/ https://regex101.com/
 
 * Paste your regex in the first field.
 * Paste the log you want to check. 
 * Click test.
 * Observe the results at the bottoma and edit the regex as needed.
 * Proceed to field selecting and then you are done.
 

#### **Filter management**

Manage the filters, export and import for later use. Edit and make a friendly name for fields and filter. You can add profit loss info.


	**Edit PL**

* Enable Profit/loos tracking: Enable all the concepts
* In each concept tab you can enable or disable that concept accounting.

When a filter is matched, you can associate up to three accounting concepts to it. You can use numeric fields gathered or make a fixed value. Edit the amount for fixed fields and set is a OProfit of Loss.
If a field is used use a multiplier if needed.


#### **Analytics**

Check the data extracted and track the profit loss.
The tab for exporting lets you make a CSV with gathered data.
Señect one filter or export all of them You can include timestamps for each row and also the original log line.



## TODO.

OCR
Remake the UI. Clen up the code. Enable reading and line adding to monitors and sahre with plugins.
Data Extractor.
Remake the UI. Search items when changed. Clean up. Dinamically update the P/L parameters, datasets and APIs. Add more regex presets, IP, Tlf. CC, email, URL. Integrate Decimal Point is Comma. Crypto adresses, hashes and contracts. More datetime options. Full edit for filters.
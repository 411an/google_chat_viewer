## Google Chat Archive Viewer

This code allows you to work with Google Chat archives obtained using the Google Archiver tool (takeout.google.com)

### Features:

- ini file: manually specify `locale` and the name of the first message author
(locale needs to parse the date from messages
first message author needs for structuring the chat window; messages with the first name are displayed on the left).
- By default, it uses the computer's locale and the name of the first message author in the database.

Pyinstaller build string `pyinstaller --onefile --noconsole --icon="GCR.ico" --add-data "GCR.ico;." --add-data "GCR.ui;." --add-data "config.ini;." main_form.py`

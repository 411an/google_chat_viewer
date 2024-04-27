import configparser
import sys
import os
import shutil

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def check_config_file():
    # Checjing INI file
    # config.ini near onefile
    #users_ini = os.path.join(os.getcwd(), 'config.ini')
    executable_path = os.path.abspath(sys.argv[0])
    executable_dir = os.path.dirname(executable_path)
    users_ini = os.path.join(executable_dir, 'config.ini')
    default_ini = resource_path('config.ini')

    if default_ini == users_ini:
        pass
    else:
        # set config.ini
        if os.path.exists(users_ini):
            shutil.copy(users_ini, default_ini)
        else:
            shutil.copy(default_ini, users_ini)

# There are classes to keep data

class Settings:
    def __init__(self):
        check_config_file()
        self._config = configparser.ConfigParser()
        self._config.read(resource_path('config.ini'), encoding='utf-8')

    def get_locale(self):
        return self._config.get('settings', 'locale')

    def get_external_pictures(self):
        return self._config.getboolean('settings', 'external_pictures', fallback=False)
    
    def get_first_name(self):
        return self._config.get('settings', 'first_name', fallback=None)    

    def set_locale(self, locale):
        self._config.set('settings', 'locale', locale)
        with open('config.ini', 'w') as configfile:
            self._config.write(configfile)

class ChatData:


    _instance = None

    def __new__(cls, total_messages=0, text_browser_width=0, date_structure = None, first_message_name=None, start_message=1, end_message=50, main_dir = None, messages_list = None, original_messages_list = None, lastMessageFlag = False, searchingFlag = False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.total_messages = total_messages
            cls._instance.text_browser_width = text_browser_width
            cls._instance.first_message_name = first_message_name
            cls._instance.start_message = start_message
            cls._instance.end_message = end_message
            cls._instance.main_dir = main_dir
            cls._instance.date_structure = date_structure
            cls._instance.messages_list = messages_list
            cls._instance.original_messages_list = original_messages_list
            cls._instance.searchingFlag = searchingFlag
            cls._instance.lastMessageFlag = lastMessageFlag
        return cls._instance

first_name = Settings().get_first_name()
chat_data = ChatData(first_message_name=first_name)

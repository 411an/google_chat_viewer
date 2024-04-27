import json
import icu
import os
import cv2
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
import datetime
from messages_model import Settings, chat_data
from calendar import month_name, different_locale
from collections import defaultdict
import numpy as np

class ProgressEmitter(QObject):
    progress_changed = pyqtSignal(int)

    def emit_progress(self, progress):
        self.progress_changed.emit(progress)

progress_emitter = ProgressEmitter()        


def prepare_date_structure(messages_list):
    
    locale_str = Settings().get_locale()
    # The months dictionary
    year_month_structure = defaultdict(list)

    # Looking for date
    for message in messages_list:
        # Получаем год и месяц из сообщения
        year = message.get("year_date")
        month = message.get("month_date")
        
        # Making structure
        if year is not None and month is not None:
            month_name = get_month_name(month, locale_str)
            if (month, month_name) not in year_month_structure[year]:
                year_month_structure[year].append((month, month_name))
    chat_data.date_structure = year_month_structure


def get_month_list(months, locale):
    # Creating the full month dictionary
    temporary_dict = {}
    with different_locale(locale):
        for i in range(1, 13):
            temporary_dict[month_name[i]] = i  
    
    # Sorting the real dictionary
    sorted_months = sorted(months, key=lambda month: temporary_dict.get(month))
   
    return sorted_months

def get_month_name(month_no, locale):
    with different_locale(locale):
        return month_name[month_no]

def parse_date_with_locale(date_str):
    
    date_str = date_str.replace("\u202f", " ")

    locale_str = Settings().get_locale()

    if locale_str:
        # Use loaded locale
        locale = icu.Locale(locale_str)
    else:
        # Use default
        locale = icu.Locale.getDefault()

    # Parcing date from messages
    date_parser = icu.SimpleDateFormat("EEEE, dd MMMM yyyy 'г.' 'в' HH:mm:ss z", locale)
    
    parsed_date = date_parser.parse(date_str)
    dt_object = datetime.datetime.fromtimestamp(parsed_date, datetime.timezone.utc)
    m = int(dt_object.strftime("%m"))
    y = dt_object.strftime("%Y")

    return dt_object, m, y

def load_json(file_path):
    # Main file loader
    with open(file_path, encoding='utf-8') as f:
        m_data = json.load(f)
        messages_data = m_data.get('messages', [])
        # zero message for comfortable iteration
        messages_data.insert(0, {})
        total_messages = len(messages_data) 
        chat_data.total_messages = total_messages
        directory = os.path.dirname(file_path)
        chat_data.main_dir = directory
        # Numeration and date parsing
        for i, message_data in enumerate(messages_data):
            message_data['message_number'] = i
            if 'created_date' in message_data:
                message_data['main_date'], message_data['month_date'], message_data['year_date'] = parse_date_with_locale(message_data['created_date'])
            elif 'updated_date' in message_data:
                message_data['main_date'], message_data['month_date'], message_data['year_date'] = parse_date_with_locale(message_data['updated_date'])
                
            else:
                message_data['main_date'] = None
                message_data['month_date'] = None
                message_data['year_date'] = None            
            
            # Progress Bat
            progress = int((i + 1) / total_messages * 100)
            progress_emitter.emit_progress(progress)


        return messages_data, directory

def create_html_page(text_browser_width, dir, messages_data, start_index, end_index):
    # Main function for building the page
    first_message_name = chat_data.first_message_name
    html = ""
    half_width = text_browser_width / 2

    # Checking borders
    if start_index < 1:
        start_index = 1
    if end_index > len(messages_data):
        end_index = len(messages_data)    
    
    for i, message_data in enumerate(messages_data[start_index:end_index], start=start_index):
            name = message_data['creator']['name']
            if first_message_name:
                pass
            else:
                first_message_name = name        
                chat_data.first_message_name = name        
            message_number = message_data['message_number']
            message_id = message_data['message_id']
            created_date = message_data.get("updated_date", "")
            if not created_date:
                created_date = message_data.get("created_date", "")

            # It can be non-text message but I want to have at least space
            text = message_data.get('text', ' ')
            text = text.replace("\n", "<br>")
            
            # Style of message according the name
            alignment = f"text-align: {'left' if name == first_message_name else 'right'}; {'margin-right' if name == first_message_name else 'margin-left'}:{half_width}px;"
            
            # Annotations checking
            annotations = message_data.get("annotations", [])
            if annotations:
                annotation_html = annotation_parser(message_data)            
                text = annotation_html

            # Quotes
            quoted_text = ""
            quoted_message_metadata = message_data.get("quoted_message_metadata")
            if quoted_message_metadata:
                quoted_creator_name = quoted_message_metadata["creator"]["name"]
                quoted_text = quoted_message_metadata["text"]
                quoted_text = f"<i>From: {quoted_creator_name}:<br/>{quoted_text}<br/></i><br/>"            
                
                text = f"<div>{quoted_text}<br/>{text}<br/></div>"

            # Thereis a main text message with ID (TextBrowser will change id ="" to <a name="">)
            message_html = f"<div id='{message_number}' data-id='{message_id}' style='{alignment}'; -qt-block-indent:1;>{name}<br/>{created_date}<br/>{text}</div>"


            # Working on pictures and other links and files
            if 'attached_files' in message_data:
                for attached_file in message_data['attached_files']:
                    export_name = attached_file.get('export_name')
                    if export_name.endswith(('.jpg', '.png', '.jpeg', '.gif')):
                        img_path = os.path.join(dir, export_name)
                        if os.path.exists(img_path):

                            #image = cv2.imread(encoded_img_path)
                            # CV2 cannot read non-latin filenames, so we are encoding this
                            f = open(img_path, "rb")
                            chunk = f.read()
                            chunk_arr = np.frombuffer(chunk, dtype=np.uint8)
                            image = cv2.imdecode(chunk_arr, cv2.IMREAD_COLOR)

                            if image is not None:
                                height_original, width_original, _ = image.shape
                                width, height = resize_image(text_browser_width,width_original,height_original)
                                img_url = QUrl.fromLocalFile(img_path).toString()
                                # Sadly text browser doesnt support relative size so I need to use cv2 and text_browser_width to count the relative size in pixels
                                img_html = f"<p><div style='text-align: {'left' if name == first_message_name else 'right'};'><a href='{img_url}' ><img src='{img_url}' width={width}  height={height} style='-qt-block-indent: 1;'/></a></div></p>"
                                message_html += img_html
                            if image is None and img_path is not None:
                                img_url = QUrl.fromLocalFile(img_path).toString()
                                # It also doesnt work with animated gifs so we have it as files only
                                # Other files also can be download here
                                img_html = f"<p style='text-align: {'left' if name == first_message_name else 'right'};'><a href='{img_url}'>(Open the file)</a></p>"
                                message_html += img_html
                        else:
                            img_html = f"<p>No file {img_path} in {dir}</p>"
                            message_html += img_html

            message_html += "<br/><br/></div>"
            html += message_html

    return html


def annotation_parser(message_data):
    # Google chat has annotations, links etc
    html_output = ""
    
    text = message_data.get("text", "")
    annotations = message_data.get("annotations", [])
    
    formatted_text = text.replace("\n", "<br>")
    
    if annotations:
        for annotation in annotations:
            start_index = annotation.get("start_index", 0)
            length = annotation.get("length", 0)
            url_metadata = annotation.get("url_metadata", {})
            
            preceding_text = text[start_index:start_index+length]
            
            preceding_text = preceding_text.replace("\n", "<br>")
            
            html_output += f"<p>Text link: {preceding_text}</p>"
            
            title = url_metadata.get("title", "")
            if title:
                html_output += f"<p><strong>{title}</strong></p>"

            snippet = url_metadata.get("snippet", "")
            if snippet:
                html_output += f"<p><i>{snippet}</i></p>"     

            image_url = url_metadata.get("image_url", "")
            if image_url:
                # We can download the image and put into the browser and I have an option in Settings but I didnt want to work on it
                #html_output += f'<a href="{image_url}"><img src="{image_url}" alt="Image"></a>'
                html_output += f'<a href="{image_url}">Image</a>'
                
                if title:
                    html_output += "<br>"
                
            material_url = url_metadata.get("url", {}).get("private_do_not_access_or_else_safe_url_wrapped_value", "")
            if material_url:
                if image_url:
                    html_output += "<br>"
                
                html_output += f'<a href="{material_url}">Material Link</a>'
    text_with_html = formatted_text + html_output     
    return text_with_html


def resize_image(browser_width, img_width, img_height):
    # New image size is the browser window will resize
    new_width = browser_width // 3

    new_height = int(new_width * img_height / img_width)

    return new_width, new_height
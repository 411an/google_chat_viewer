from PyQt5.QtWidgets import QMainWindow, QFileDialog, QTextBrowser, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices, QTextCursor, QTextDocument, QFont
from PyQt5.uic import loadUi
from messages_loader import load_json, create_html_page, progress_emitter, prepare_date_structure
from messages_model import Settings, chat_data, resource_path
import re
from calendar import month_name, different_locale

class ResizableTextBrowser(QTextBrowser):
    resized = pyqtSignal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

class ScrollListener(QObject):
    scrollChanged = pyqtSignal()

    def __init__(self, textBrowser):
        super().__init__()
        self.textBrowser = textBrowser
        self.textBrowser.verticalScrollBar().valueChanged.connect(self.scroll_changed)

    def scroll_changed(self):
        self.scrollChanged.emit()   

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Message Viewer")
        
        # Loading the form
        #loadUi('GCR.ui', self)
        loadUi(resource_path('GCR.ui'), self)
        
        text_browser_widget = self.findChild(QTextBrowser, "textBrowser")

        # Replace original textBrowser
        if text_browser_widget:
            self.textBrowser = ResizableTextBrowser()
            self.verticalLayout.replaceWidget(text_browser_widget, self.textBrowser)
            text_browser_widget.deleteLater()

        for f in range(8, 17, 2):
            self.comboBox_F.addItem(str(f))
        
        self.comboBox_F.setCurrentIndex(3)
        self.comboBox_F.currentIndexChanged.connect(self.on_font_changed)

        # Font
        self.font = QFont()
        self.font.setPointSize(14)
        self.textBrowser.setFont(self.font) 

        # Main load button
        self.loadButton.clicked.connect(self.load_json)
        
        # Listening for events
        self.textBrowser.installEventFilter(self)
        
        self.scroll_listener = ScrollListener(self.textBrowser)
        
        self.scroll_listener.scrollChanged.connect(self.on_scroll_changed)
        
        # Access to local files and links
        self.textBrowser.setOpenExternalLinks(True)
        self.textBrowser.setOpenLinks(False)
        self.textBrowser.anchorClicked.connect(self.open_link)

        self.textBrowser.resized.connect(self.on_textBrowser_resize)

        progress_emitter.progress_changed.connect(self.update_progress_bar)

        self.updating_scrollbar = False

        # Searching buttons
        self.pushButton_S.clicked.connect(self.search_in_browser)
        self.search_text = ""
        self.search_cursor = None

        self.pushButton_B.clicked.connect(self.search_in_database)
        self.pushButton_Clean.clicked.connect(self.search_clean)
        self.monthButton.clicked.connect(self.monthLoader)

        # Year-Month combo
        self.comboBox_y.currentIndexChanged.connect(lambda: self.update_month_combo_box(chat_data.date_structure, self.comboBox_y, self.comboBox_m))

    def on_font_changed(self):
            selected_size = int(self.comboBox_F.currentText())
            self.font.setPointSize(selected_size)
            self.textBrowser.setFont(self.font)

    def on_messages_list_changed(self):
            # Rebuilding year-month list
            prepare_date_structure(chat_data.messages_list)
            self.populate_comboboxes(chat_data.date_structure, self.comboBox_y, self.comboBox_m)

    
    def populate_comboboxes(self, year_month_structure, combo_box_year, combo_box_month):
        # For filling up year-month comboboxes
        combo_box_year.clear()
        combo_box_month.clear()

        years = sorted(year_month_structure.keys())
        combo_box_year.addItems(years)

        selected_year = combo_box_year.currentText()
        months = year_month_structure.get(selected_year, [])
        month_names = [month_name for _, month_name in months]
        combo_box_month.addItems(month_names)
        

    def update_month_combo_box(self, year_month_structure, combo_box_year, combo_box_month):
        # For changing year-month comboboxes
        combo_box_month.clear()
        selected_year = combo_box_year.currentText()
        months = year_month_structure.get(selected_year, [])
        month_names = [month_name for _, month_name in months]
        combo_box_month.addItems(month_names)

    def monthLoader(self):
        # Jumping to a specific month
        locale_str = Settings().get_locale()

        # Temporary dict with months names in the local language
        temporary_dict = {}
        with different_locale(locale_str):
            for i in range(1, 13):
                temporary_dict[month_name[i]] = i
    
        selected_month_name = self.comboBox_m.currentText() 

        month_index_in_year = temporary_dict.get(selected_month_name)

        selected_year = self.comboBox_y.currentText()

        # Looking for 1st message of the month
        start_index = None
        for i, message in enumerate(chat_data.messages_list):
            if message.get("year_date") == selected_year:
                if message.get("month_date") == month_index_in_year:
                    start_index = i
                    break
        else:
            QMessageBox.information(self, "No Results", "No results")
            return

        # Moving the position to this message
        end_index = min(start_index + 50, len(chat_data.messages_list))

        self.updating_scrollbar = True
        self.textBrowser.clear()  # Cleaning textBrowser
        self.updating_scrollbar = False

        html_source = create_html_page(chat_data.text_browser_width, chat_data.main_dir, chat_data.messages_list, start_index, end_index)
        self.textBrowser.setHtml(html_source)
        chat_data.start_message = start_index
        chat_data.end_message = end_index

    # Just searching in the browser
    def search_in_browser(self):
        self.search_text = self.lineEdit_S.text()
        if self.search_text:
            if self.search_cursor is None:
                self.search_cursor = self.textBrowser.textCursor()
            flags = QTextDocument.FindFlags()
            if self.checkBox.isChecked():
                flags |= QTextDocument.FindWholeWords
            cursor = self.textBrowser.document().find(self.search_text, self.search_cursor, flags)
            if not cursor.isNull():
                cursor.select(QTextCursor.WordUnderCursor)
                self.textBrowser.setTextCursor(cursor)
                self.textBrowser.ensureCursorVisible()
                self.search_cursor = cursor
            else:
                # Сбросить курсор для следующего поиска
                self.search_cursor = None


    # Searching in the whole base
    def search_in_database(self):
        search_text = self.lineEdit_B.text()
        if search_text and len(search_text)>4: 
            
            # Reapeating the process of messaging in load_json with selected ones
            searched_list = []
            searched_list.insert(0, {})
            x = 0


            for i,message in enumerate(chat_data.messages_list):
                if 'text' in message:
                    if search_text.lower() in message["text"].lower():
                        searched_message = message.copy() 
                        x = x + 1 
                        searched_message['message_number'] = x
                        searched_list.append(searched_message)
                else:
                    pass
                progress = int((i + 1) / chat_data.total_messages * 100)
                progress_emitter.emit_progress(progress)

            if len(searched_list)>1:
                chat_data.messages_list = searched_list
                self.on_messages_list_changed()
                html_source = create_html_page(chat_data.text_browser_width, chat_data.main_dir, chat_data.messages_list, 0, 50)
                self.updating_scrollbar = True
                self.textBrowser.clear()  # Очищаем содержимое textBrowser
                self.updating_scrollbar = False                
                self.textBrowser.setHtml(html_source)
                chat_data.searchingFlag = True
                chat_data.start_message = 0 
                chat_data.end_message = 50
                #print(len(chat_data.messages_list))
                self.pushButton_Clean.setEnabled(True)
            else:
                QMessageBox.information(self, "No Results", f"No results found for '{search_text}'")

    def search_clean(self):
        # Returning to dataset of all messages, not just founded
        self.updating_scrollbar = True
        self.textBrowser.clear() 
        self.updating_scrollbar = False

        chat_data.messages_list = chat_data.original_messages_list
        self.on_messages_list_changed()
        html_source = create_html_page(chat_data.text_browser_width, chat_data.main_dir, chat_data.messages_list, 0, 50)
        self.textBrowser.setHtml(html_source)
        chat_data.searchingFlag = False
        chat_data.start_message = 0 
        chat_data.end_message = 50        
        self.pushButton_Clean.setEnabled(False)


    def get_visible_lines(self, text_browser):
        # We got the visible area
        visible_rect = text_browser.viewport().rect()
        
        # We got coordinates
        visible_start = text_browser.cursorForPosition(visible_rect.topLeft()).block().blockNumber()
        visible_end = text_browser.cursorForPosition(visible_rect.bottomRight()).block().blockNumber()

        lines = abs(visible_end - visible_start)
        # There is count of lines in the visible area
        return lines

    def get_anchor_position(self, text_browser, anchor_id):
        # We are looking here anchor_id in the text browser
        
        anchor_position = 1
        # Original HTML
        original_html = text_browser.toHtml()

        # Changing anchors in the code to normal text
        unique_marker = "U_N_"
        u_m = "U_!"
        replaced_html = original_html

        pattern = r'<a name="\d+">'
        matches = re.findall(pattern, replaced_html)

        for match in matches:
            index = re.search(r'\d+', match).group() 
            replaced_html = replaced_html.replace(match, f'{unique_marker}{index}{u_m}')

        # The new HTML is sending to hidden browser
        hidden_browser = QTextBrowser()
        hidden_browser.setHtml(replaced_html)
        hidden_browser.resize(text_browser.size())

        # Looking for the new text position
        for match in matches:
            index = re.search(r'\d+', match).group() 
            
            if str(index) == str(anchor_id):
                anchor_position = hidden_browser.document().find(f'{unique_marker}{index}{u_m}').position()
                if anchor_position != -1:
                    break
        
        return anchor_position 

    def get_id(self, text_browser):
        # In this function we have the first and the last anchors in the visible area

        first_id = None
        last_id = None

        # Getting the visible area 
        visible_rect = text_browser.viewport().visibleRegion().boundingRect()

        # Getting the text from the visible area
        first_position = text_browser.cursorForPosition(visible_rect.topLeft()).position()
        last_position = text_browser.cursorForPosition(visible_rect.bottomRight()).position()

        cursor = QTextCursor(text_browser.document())
        cursor.setPosition(first_position)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.setPosition(last_position, QTextCursor.KeepAnchor)
        visible_text = cursor.selection().toHtml()
        
        # looking for anchors
        matches = re.findall(r'<a\s+name="([^"]*)"', visible_text)
        if matches:
            first_id = matches[0] 
            last_id = matches[-1] 
        else:
            first_id = first_id
            last_id = last_id
        #print(first_id, last_id)
        return first_id, last_id

    def on_textBrowser_resize(self):
        chat_data.text_browser_width = self.textBrowser.width()

    def update_progress_bar(self, progress):
            dir = chat_data.main_dir

            if progress < 100:
                self.progressBar.setValue(progress)
            else:
                self.progressBar.setValue(0) 
                message = f"Main folder: {dir}"
                self.statusBar().showMessage(message)            

    def open_link(self, url):
        QDesktopServices.openUrl(QUrl(url.toString()))
    
    def load_json(self):
        self.updating_scrollbar = True
        self.textBrowser.clear()  
        self.updating_scrollbar = False
    
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', '/home', "JSON files (*.json)")

        if fname:
            # Get locale
            locale_str = Settings().get_locale()
            # Get main data
            messages, dir = load_json(fname)
            # Save list of messages
            chat_data.messages_list = messages
            self.on_messages_list_changed()
            chat_data.original_messages_list = messages

            # Getting size of browser

            text_browser_width = self.textBrowser.width()
            chat_data.text_browser_width = text_browser_width

            # Loading first data
            html_source = create_html_page(text_browser_width, dir, messages, start_index=1, end_index=50)
            self.textBrowser.setHtml(html_source)

    def on_scroll_changed(self):

        # Stop if its a start position
        if chat_data.start_message < 0:
            chat_data.start_message = 0
            chat_data.end_message = 100
            return
        
        # Stop if its self-upfate
        if not self.updating_scrollbar:
            # Получаем текущую позицию полосы прокрутки
            scroll_bar = self.textBrowser.verticalScrollBar()
            current_position = scroll_bar.value()
            max_position = scroll_bar.maximum()

            # Stop if its the last message
            if len(chat_data.messages_list) == chat_data.end_message and current_position == max_position:
                        return

            # Check of the norders
            if current_position == max_position or current_position == 0:
                first_id, last_id = self.get_id(self.textBrowser)
                # If its the enf
                if current_position == max_position:
                    #print("User scrolled to the bottom of the chat.")
                    remaining_messages = len(chat_data.messages_list) - chat_data.end_message
                    #print("Start message:", chat_data.start_message)
                    #print("End message:", chat_data.end_message)
                    #print(remaining_messages)
                    # Moving the border
                    if remaining_messages < 50:
                        # If its almost end we can just expand it
                        chat_data.end_message = len(chat_data.messages_list)
                        if chat_data.end_message > 100:
                            chat_data.start_message = chat_data.end_message - 100
                        else:
                            chat_data.start_message = 0
                        chat_data.lastMessageFlag = True
                    else:
                        # in other case we just move the visible part of database
                        chat_data.end_message += 50
                        chat_data.start_message = chat_data.end_message - 100
                    
                else:

                    # Moving up
                    if chat_data.start_message == 0: 
                        return
                    if chat_data.start_message >= 50:
                        chat_data.start_message -= 50
                    else:
                        chat_data.start_message = 0
                    chat_data.end_message = chat_data.start_message + 100

                #print("Start message:", chat_data.start_message)
                #print("End message:", chat_data.end_message)
                # We need to sidable scrollbar listening before every updating
                self.updating_scrollbar = True
                # Loading the new data
                html_source = create_html_page(chat_data.text_browser_width, chat_data.main_dir, chat_data.messages_list, start_index=chat_data.start_message, end_index=chat_data.end_message)
                self.textBrowser.setHtml(html_source)
                
                # Here is a new cursor for moving inside the browser and set the correct position after updating
                main_cursor = QTextCursor(self.textBrowser.document())


                # This code works only if there was a small part of last messages that was merged with screen before the last one
                if len(chat_data.messages_list) == chat_data.end_message and chat_data.lastMessageFlag == True:
                    scroll_bar.setValue(scroll_bar.maximum())                     
                    main_cursor.movePosition(QTextCursor.End)
                    self.textBrowser.setTextCursor(main_cursor)
                    self.textBrowser.ensureCursorVisible()
                    chat_data.lastMessageFlag = False
                    self.updating_scrollbar = False
                    return
                
                # Checking the size of the browser window for moving correction data 
                visible_lines = self.get_visible_lines(self.textBrowser)
                correction = visible_lines // (int(last_id) - int(first_id))

                # checking the direction we are moving
                if current_position == max_position:
                    line_id = last_id
                    correction = correction * -1
                    
                else:
                    line_id = first_id
                    correction =  (visible_lines // 2) - correction - 1
                
                # This code is moving scrollbar to the position near the message that user have seen before data was changed
                # Bad imitation of real scrolling

                # Here is the position of the last of first ID in the visible browser window
                anc_pos = self.get_anchor_position(self.textBrowser, line_id)
                #print(last_id, first_id)

                # We set our cursor on this position and move the screen on it
                main_cursor.setPosition(anc_pos)
                block = main_cursor.block()
                line_number = block.blockNumber()
                line_number = line_number + correction if chat_data.searchingFlag == True else line_number
                target_position = self.textBrowser.document().findBlockByLineNumber(line_number).position()
                main_cursor.setPosition(target_position)
                self.textBrowser.setTextCursor(main_cursor)
                self.textBrowser.ensureCursorVisible()

                self.updating_scrollbar = False


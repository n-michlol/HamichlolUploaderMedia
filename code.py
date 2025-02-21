import sys 
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QFileDialog, 
                            QLineEdit, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, 
                            QListWidget, QMessageBox, QCheckBox, QProgressBar, QComboBox,
                            QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap

import requests
import json
import configparser
import base64

class UploadThread(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    
    def __init__(self, files, site, username, password, description, summary, target_filenames):
        QThread.__init__(self)
        self.files = files
        self.site = site
        self.username = username
        self.password = password
        self.description = description
        self.summary = summary
        self.target_filenames = target_filenames
        self.results = []
        self.session = requests.Session()

    def run(self):
        try:
            self.status_signal.emit("מתחבר למכלול...")
            
            api_url = f"https://{self.site}/w/api.php"
            
            login_token_params = {
                'action': 'query',
                'meta': 'tokens',
                'type': 'login',
                'format': 'json'
            }
            r = self.session.get(api_url, params=login_token_params)
            login_token = r.json()['query']['tokens']['logintoken']
            
            login_params = {
                'action': 'login',
                'lgname': self.username,
                'lgpassword': self.password,
                'lgtoken': login_token,
                'format': 'json'
            }
            r = self.session.post(api_url, data=login_params)
            login_result = r.json()
            
            if login_result.get('login', {}).get('result') != 'Success':
                raise Exception(f"התחברות נכשלה: {json.dumps(login_result)}")
            
            self.status_signal.emit("התחברות למכלול הצליחה")
            
            csrf_params = {
                'action': 'query',
                'meta': 'tokens',
                'format': 'json'
            }
            r = self.session.get(api_url, params=csrf_params)
            csrf_token = r.json()['query']['tokens']['csrftoken']
            
            total_files = len(self.files)
            
            for i, file_path in enumerate(self.files):
                try:
                    filename = os.path.basename(file_path)
                    target_name = self.target_filenames.get(file_path, filename)
                    
                    self.status_signal.emit(f"מעלה קובץ {i+1}/{total_files}: {filename}")
                    
                    with open(file_path, 'rb') as f:
                        file_contents = f.read()
                    
                    upload_params = {
                        'action': 'upload',
                        'filename': target_name,
                        'comment': self.summary,
                        'text': self.description,
                        'token': csrf_token,
                        'ignorewarnings': 1,
                        'format': 'json'
                    }
                    
                    files = {'file': (target_name, file_contents)}
                    
                    r = self.session.post(api_url, data=upload_params, files=files)
                    result = r.json()
                    
                    if 'upload' in result and result['upload']['result'] == 'Success':
                        self.results.append(f"הקובץ {target_name} הועלה בהצלחה")
                    else:
                        error_msg = result.get('error', {}).get('info', json.dumps(result))
                        self.results.append(f"שגיאה בהעלאת {target_name}: {error_msg}")
                
                except Exception as e:
                    self.results.append(f"שגיאה בהעלאת {filename}: {str(e)}")
                
                progress = int(((i + 1) / total_files) * 100)
                self.progress_signal.emit(progress)
            
            self.status_signal.emit("העלאה הסתיימה")
            self.finished_signal.emit(self.results)
            
        except Exception as e:
            self.status_signal.emit(f"שגיאה: {str(e)}")
            self.finished_signal.emit([f"שגיאה כללית: {str(e)}"])

class HamichlolUploader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.default_site = "www.hamichlol.org.il"
        self.default_username = ""
        self.default_password = ""
        self.default_description = "{{יצירה נגזרת|מרוטש=כן}}"
        self.default_summary = "העלאת תמונה מרוטשת"
        
        self.selected_files = []
        self.target_filenames = {}
        
        self.settings = QSettings('HamichlolUploader', 'WindowState')
        self.initUI()
        self.loadSettings()
        
        size = self.settings.value('window_size', QSize(800, 600))
        self.resize(size)
        
    def initUI(self):
        self.setWindowTitle("מעלה קבצים למכלול")
        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, "logo.png")
            
        logo_path = resource_path("logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        self.setMinimumSize(600, 400)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        self.setStyleSheet("""
            QMainWindow, QScrollArea {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #f0f8ff, stop:1 #e6f2ff);
            }
            QLabel {
                font-size: 14px;
                color: #333366;
            }
            QLineEdit, QTextEdit {
                border: 2px solid #aabbcc;
                border-radius: 6px;
                padding: 8px;
                background-color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                selection-background-color: #4a7eff;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #6699ff;
                background-color: white;
            }
            QCheckBox {
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        
        title_layout = QHBoxLayout()
        title_widget = QWidget()
        title_widget.setFixedHeight(80)
        title_widget.setStyleSheet("background-color: rgba(255, 255, 255, 0.5); border-radius: 10px;")
        
        title_label = QLabel("העלאת קבצים למכלול")
        title_font = QFont("Segoe UI", 22, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2a4494; padding: 10px;")
        
        title_layout.addWidget(title_label)
        title_widget.setLayout(title_layout)
        main_layout.addWidget(title_widget)
        
        connection_group = QWidget()
        connection_group.setStyleSheet("background-color: rgba(255, 255, 255, 0.5); border-radius: 10px; padding: 10px;")
        connection_layout = QHBoxLayout(connection_group)
        connection_layout.setContentsMargins(10, 10, 10, 10)
        connection_layout.setSpacing(10)
        
        site_layout = QVBoxLayout()
        site_label = QLabel("כתובת האתר:")
        self.site_input = QLineEdit(self.default_site)
        site_layout.addWidget(site_label)
        site_layout.addWidget(self.site_input)
        
        username_layout = QVBoxLayout()
        username_label = QLabel("שם משתמש:")
        self.username_input = QLineEdit(self.default_username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        
        password_layout = QVBoxLayout()
        password_label = QLabel("סיסמה:")
        self.password_input = QLineEdit(self.default_password)
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        
        connection_layout.addLayout(site_layout)
        connection_layout.addLayout(username_layout)
        connection_layout.addLayout(password_layout)
        
        main_layout.addWidget(connection_group)

        file_group = QWidget()
        file_group.setStyleSheet("background-color: rgba(255, 255, 255, 0.5); border-radius: 10px; padding: 10px;")
        file_layout = QVBoxLayout(file_group)
        
        button_layout = QHBoxLayout()
        
        self.select_files_btn = QPushButton("בחר קבצים להעלאה")
        self.select_files_btn.clicked.connect(self.selectFiles)
        self.select_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a7eff;
                color: white;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3060d0;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
        """)
        
        self.clear_files_btn = QPushButton("נקה רשימה")
        self.clear_files_btn.clicked.connect(self.clearFiles)
        self.clear_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border-radius: 6px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #e05050;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
        """)
        
        button_layout.addWidget(self.select_files_btn)
        button_layout.addWidget(self.clear_files_btn)
        file_layout.addLayout(button_layout)
        
        file_name_layout = QHBoxLayout()
        target_name_label = QLabel("שם יעד:")
        self.target_name_input = QLineEdit()
        self.target_name_input.textChanged.connect(self.updateTargetFilename)
        file_name_layout.addWidget(target_name_label)
        file_name_layout.addWidget(self.target_name_input)
        file_layout.addLayout(file_name_layout)
        
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        self.file_list.currentItemChanged.connect(self.fileSelectionChanged)
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #aabbcc;
                border-radius: 8px;
                background-color: rgba(245, 248, 255, 0.8);
                padding: 5px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e8f0ff;
            }
            QListWidget::item:selected {
                background-color: #4a7eff;
                color: white;
            }
            QListWidget::item:alternate {
                background-color: #eef5ff;
            }
        """)
        file_layout.addWidget(self.file_list)
        
        main_layout.addWidget(file_group)
        
        upload_options = QWidget()
        upload_options.setStyleSheet("background-color: rgba(255, 255, 255, 0.5); border-radius: 10px; padding: 10px;")
        upload_layout = QVBoxLayout(upload_options)
        
        description_layout = QHBoxLayout()
        description_label = QLabel("תיאור העמוד:")
        self.description_input = QTextEdit()
        self.description_input.setText(self.default_description)
        self.description_input.setMaximumHeight(100)

        description_layout.addWidget(description_label)
        description_layout.addWidget(self.description_input)
        upload_layout.addLayout(description_layout)
        
        summary_layout = QHBoxLayout()
        summary_label = QLabel("תקציר העריכה:")
        self.summary_input = QLineEdit(self.default_summary)

        summary_layout.addWidget(summary_label)
        summary_layout.addWidget(self.summary_input)
        upload_layout.addLayout(summary_layout)
        
        main_layout.addWidget(upload_options)
        
        progress_container = QWidget()
        progress_container.setStyleSheet("background-color: rgba(255, 255, 255, 0.5); border-radius: 10px; padding: 10px;")
        progress_layout = QVBoxLayout(progress_container)
        
        self.progress_bar = QProgressBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% הושלמו")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 8px;
                text-align: center;
                height: 28px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #4CAF50, stop:1 #45a049);
                border-radius: 6px;
            }
        """)
        
        self.status_label = QLabel("מוכן להעלאה")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #333366; margin-top: 5px;")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        main_layout.addWidget(progress_container)
        
        self.upload_btn = QPushButton("העלה למכלול")
        self.upload_btn.clicked.connect(self.uploadFiles)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border-radius: 8px;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #45a049, stop:1 #3d9040);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        main_layout.addWidget(self.upload_btn)
        
        self.scroll.setWidget(main_widget)
        self.setCentralWidget(self.scroll)
        
        self.setLayoutDirection(Qt.RightToLeft)
        
    def fileSelectionChanged(self, current, previous):
        if current:
            file_path = self.selected_files[self.file_list.currentRow()]
            self.target_name_input.setText(self.target_filenames.get(file_path, os.path.basename(file_path)))
            
    def updateTargetFilename(self, new_name):
        if self.file_list.currentItem():
            current_file = self.selected_files[self.file_list.currentRow()]
            if new_name:
                self.target_filenames[current_file] = new_name
            else:
                self.target_filenames.pop(current_file, None)
    
    def selectFiles(self):
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "בחר קבצים להעלאה",
            downloads_path,
            "קבצי תמונה (*.png *.jpg *.jpeg *.gif *.svg *.pdf);;כל הקבצים (*.*)"
        )
        
        if files:
            self.selected_files.extend(files)
            self.updateFileList()
    
    def updateFileList(self):
        self.file_list.clear()
        for file in self.selected_files:
            self.file_list.addItem(os.path.basename(file))
        
        self.upload_btn.setEnabled(len(self.selected_files) > 0)
        
        if self.selected_files:
            self.file_list.setCurrentRow(0)
    
    def clearFiles(self):
        self.selected_files = []
        self.target_filenames = {}
        self.target_name_input.clear()
        self.updateFileList()
    
    def uploadFiles(self):
        if not self.selected_files:
            QMessageBox.warning(self, "שגיאה", "אנא בחר לפחות קובץ אחד להעלאה")
            return
        
        site = self.site_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        description = self.description_input.toPlainText()
        summary = self.summary_input.text()
        
        self.saveSettings()
        
        self.upload_thread = UploadThread(
            self.selected_files, site, username, password, 
            description, summary, self.target_filenames
        )
        
        self.upload_thread.progress_signal.connect(self.updateProgress)
        self.upload_thread.status_signal.connect(self.updateStatus)
        self.upload_thread.finished_signal.connect(self.uploadFinished)
        
        self.upload_btn.setEnabled(False)
        self.select_files_btn.setEnabled(False)
        self.clear_files_btn.setEnabled(False)

        self.upload_thread.start()
    
    def updateProgress(self, value):
        self.progress_bar.setValue(value)
    
    def updateStatus(self, message):
        self.status_label.setText(message)
    
    def uploadFinished(self, results):
        self.upload_btn.setEnabled(True)
        self.select_files_btn.setEnabled(True)
        self.clear_files_btn.setEnabled(True)
        
        result_dialog = QMessageBox(self)
        result_dialog.setWindowTitle("תוצאות העלאה")
        result_dialog.setText("\n".join(results))
        result_dialog.setIcon(QMessageBox.Information)
        result_dialog.setStyleSheet("""
            QMessageBox {
                background-color: #f9f9f9;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                background-color: #4a7eff;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3060d0;
            }
        """)
        result_dialog.setLayoutDirection(Qt.RightToLeft)
        result_dialog.exec_()
    
    def saveSettings(self):
        self.settings.setValue('window_size', self.size())
        
        config = configparser.ConfigParser()
        config['DEFAULT'] = {
            'site': self.site_input.text(),
            'username': self.username_input.text(),
            'password': self.password_input.text(),
            'description': self.description_input.toPlainText(),
            'summary': self.summary_input.text()
        }
        
        try:
            with open('hamichlol_uploader_settings.ini', 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"שגיאה בשמירת הגדרות: {e}")
    
    def loadSettings(self):
        try:
            config = configparser.ConfigParser()
            config.read('hamichlol_uploader_settings.ini', encoding='utf-8')
            
            if 'DEFAULT' in config:
                self.site_input.setText(config['DEFAULT'].get('site', self.default_site))
                self.username_input.setText(config['DEFAULT'].get('username', self.default_username))
                self.password_input.setText(config['DEFAULT'].get('password', self.default_password))
                self.description_input.setText(config['DEFAULT'].get('description', self.default_description))
                self.summary_input.setText(config['DEFAULT'].get('summary', self.default_summary))
        except Exception as e:
            print(f"שגיאה בטעינת הגדרות: {e}")
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.saveSettings()
    
    def closeEvent(self, event):
        self.saveSettings()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    window = HamichlolUploader()
    window.show()
    sys.exit(app.exec_())
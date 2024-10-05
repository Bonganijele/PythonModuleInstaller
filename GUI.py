# Copyright (c) 2024, Bongani. All rights reserved.
# This file is part of the Python Module Installer project.
# For more details, visit [Your Project's URL]+

# Author: Bongani Jele <jelebongani43@gmail.com>

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QLabel, QMessageBox, QComboBox, QProgressBar,
                               QTextEdit, QDialog, QMenuBar, QMenu, QSpacerItem, QSizePolicy,QToolTip, QScrollArea, QStackedWidget,
                               QFormLayout, QCheckBox, QInputDialog, QDialogButtonBox, QFileDialog, QStyle, QGroupBox, QGridLayout, QTabWidget, QFrame)
from PySide6.QtGui import QIcon, QAction,  QCursor, QShowEvent, QColor, QPainter, QFont
from PySide6.QtCore import QSize, QThread, Signal, QEvent, QTimer, QPoint, Slot, QSettings,QProcess, QMetaObject, Qt, Q_ARG, QRect
from threading import Thread
from packaging import version
import importlib.metadata

from package import MODULE_POPULARITY, MODULE_CATEGORIES, MODULE_DEPENDENCIES, MODULE_DOCS
from system_service_window import PackageSystemService
from environment_window import SettingsDialog
from settings import SystemPackages
import subprocess
import threading
import requests
import getpass
import logging 
import shutil
import psutil  # For system health monitoring
import signal
import time
import json
import re
import sys
import os


class InstallThread(QThread):
    progress = Signal(float)  # Signal to update the progress bar with percentage
    status_message = Signal(str)
    error_occurred = Signal(str)
    conflict_message = Signal(str)
    module_not_installed = Signal(str)
    module_uninstalled = Signal(str)  # Fix the signal name here
    finished = Signal()

    def __init__(self, modules, action):
        super().__init__()
        self.modules = modules
        self.action = action
        
        self.error_occurred_flag = False
        self.proc = None  # Store subprocess instance here for termination
        
    def is_module_installed(self, module):
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'show', module],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode == 0 and 'Name:' in result.stdout
        except Exception as e:
            self.error_occurred.emit(f"Error checking installation status of {module}: {str(e)}")
            return False

    def run(self):
        for module in self.modules:
            if self.isInterruptionRequested():
                self.cleanup()
                return

            try:
                if self.action == 'install':
                    command = [sys.executable, '-m', 'pip', 'install', module]
                elif self.action == 'uninstall':
                        if not self.is_module_installed(module):
                            self.module_not_installed.emit(f"{module} is not installed")
                            continue
                        
                        command = [sys.executable, '-m', 'pip', 'uninstall', '-y', module]
                elif self.action == 'update':
                    command = [sys.executable, '-m', 'pip', 'install', '--upgrade', module]
                else:
                    self.error_occurred.emit(f"Unknown action: {self.action}")

                self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Monitor the process for output and interruption requests
                for line in iter(self.proc.stdout.readline, ''):
                    if self.isInterruptionRequested():
                        self.proc.terminate()  # Terminate the subprocess if cancellation is requested
                        self.cleanup()
                        return

                    self.parse_progress(line)

                stdout, stderr = self.proc.communicate()  # Wait for the process to complete

                if self.proc.returncode == 0:
                    self.module_uninstalled.emit(module)
                    self.status_message.emit(f"{module} {self.action}ed successfully.")
                else:
                    error_message = stderr.strip()
                    self.error_occurred_flag = True
                    self.error_occurred.emit(f"Error {self.action}ing {module}: {error_message}")
                    self.error_occurred(f"Error uninstalling {module}: {error_message}")
                    if 'conflict' in error_message.lower():
                        self.conflict_message.emit(f"Conflict detected: {error_message}")

            except Exception as e:
                self.error_occurred_flag = True
                self.error_occurred.emit(f"An unexpected error occurred while {self.action}ing {module}: {str(e)}")

        self.progress.emit(0)  # Reset progress bar to 0 after finishing
        self.finished.emit()

    def parse_progress(self, line):
        # This regex matches patterns like 'Downloading XX MB', 'Downloading XX kB', etc.
        match = re.search(r'(\d+\.\d+|\d+)\s*(kB|MB|GB)', line)
        if match:
            size, unit = match.groups()
            size = float(size)
            if unit == 'kB':
                size /= 1024  # Convert kB to MB
            elif unit == 'GB':
                size *= 1024  # Convert GB to MB
            self.progress.emit(size)

    def cleanup(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()  # Ensure the subprocess is terminated
            self.proc.wait()  # Wait for it to exit
        self.finished.emit()
        self.quit()
        
        

        

################################################################################################################
                    #ModuleInputDialog  QDialog
                    
class ModuleInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Install Module')
        self.setFixedSize(300, 120)  # Set the fixed size of the dialog

        # Layout
        layout = QVBoxLayout()

        # Label
        self.label = QLabel('Enter module name to install:')
        layout.addWidget(self.label)

        # Input field
        self.input_field = QLineEdit()
        # self.input_field.setFixedWidth(250)  # Set the fixed width of the input field
        layout.addWidget(self.input_field)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        
#######################################################################################################
                            ## InstalledModulesWindow  QDialog

class InstalledModulesWindow(QDialog):
    def __init__(self, installed_modules, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Installed Modules')
        self.resize(500, 400)
        
       

        layout = QVBoxLayout()

        # Search bar for filtering installed modules
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Search installed modules...')
        self.search_bar.textChanged.connect(self.filter_modules)
        layout.addWidget(self.search_bar)
        
        # List to display installed modules
        self.installed_modules_list = QListWidget()
        self.installed_modules_list.addItems(installed_modules)
        layout.addWidget(self.installed_modules_list)

        self.setLayout(layout)
        
    def filter_modules(self):
        search_text = self.search_bar.text().lower()
        for index in range(self.installed_modules_list.count()):
            item = self.installed_modules_list.item(index)
            item.setHidden(search_text not in item.text().lower())
    
    
#############################################################################################
                        # CustomTooltip  QWidget
                        
class CustomTooltip(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        layout = QVBoxLayout()
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setOpenExternalLinks(True)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def show_tooltip(self, pos):
        # self.move(pos + QPoint(2, 2))
        # self.show()
        # QTimer.singleShot(3000, self.hide)  # Hide after 6 seconds
        global_pos = self.parent_widget.mapToGlobal(QPoint(0, 0))
        tooltip_pos = pos + QPoint(1, 1)
        
        if tooltip_pos.x() + self.width() > global_pos.x() + self.parent_widget.width():
            
                tooltip_pos.setX(global_pos.x() + self.parent_widget.width() - self.width() - 2)
        
        # Ensure tooltip doesn't go beyond the bottom edge of the parent
        if tooltip_pos.y() + self.height() > global_pos.y() + self.parent_widget.height():
            tooltip_pos.setY(global_pos.y() + self.parent_widget.height() - self.height() - 2)
        
        # Ensure tooltip doesn't go beyond the top or left edges of the parent
        tooltip_pos.setX(max(tooltip_pos.x(), global_pos.x() + 2))
        tooltip_pos.setY(max(tooltip_pos.y(), global_pos.y() + 2))

        self.move(tooltip_pos)
        self.show()
        
        # Hide the tooltip after 4 seconds
        QTimer.singleShot(4000, self.hide)

    def update_tooltip_position(self):
        # Method to reposition the tooltip when the parent widget moves
        if self.isVisible():
            current_pos = self.mapToParent(self.pos())
            self.show_tooltip(current_pos)

#####################################################################################################
                    # HoverListWidget QListWidget

class HoverListWidget(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("QListWidget::item { border: 1px solid transparent; }")
        self.setMouseTracking(True)  # Enable mouse tracking for hover detection
        self.hovered_item = None
        self.tooltip = CustomTooltip(self)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        current_item = self.itemAt(pos)

        if current_item != self.hovered_item:
            self.hovered_item = current_item
            self.viewport().update()  # Trigger a repaint to update hover effect
        super().mouseMoveEvent(event)
        
        

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        for index in range(self.count()):
            item = self.item(index)
            rect = self.visualItemRect(item)
            # if item == self.hovered_item:
            #     painter.fillRect(rect, QColor(0,159,255))  # Background color for hovered items   


###################################################################################################################
                            ##CommandThread QThread

class CommandThread(QThread):
    output_received = Signal(str)
    error_received = Signal(str)
    finished = Signal(int)

    def __init__(self, command, password, parent=None):
        super().__init__(parent)
        self.command = command
        self.password = password

    def run(self):
        env = {f"DEBIAN_FRONTEND": "noninteractive"}
        full_command = ['sudo', '-S'] + self.command
        process = subprocess.Popen(full_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=env)
        stdout, stderr = process.communicate(input=self.password + '\n')
        for line in stdout.splitlines():
            self.output_received.emit(line)
        for line in stderr.splitlines():
            self.error_received.emit(line)
        self.finished.emit(process.returncode)




##################################################################################################################
             # Subclass QMainWindow to customize your application's main window
##################################################################################################################


                   
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() 
        self.module_list =HoverListWidget(self)
        self.tooltip = None
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_custom_tooltip)

        self.last_cursor_pos = None
        self.install_thread = None # Initialize install_thread here
        self.load_settings()
        self.iniUI()
        
        # Initialize cancel_requested to False in the constructor
        self.cancel_requested = False

    def iniUI(self):
        
        self.setWindowTitle("Python Module Installer")
        # self.resize(1020, 590)
        
        #Applying stylesheet to the QListWidget to ensure text visibility and hover effect
        self.module_list.setStyleSheet("""
            QListWidget::item {
                color: white; 
            }
            QListWidget::item:selected {
                background-color: #3b3b3b; 
                color:  black; 
            }
            QListWidget::item:hover {
                background-color: #3b3b3b; 
                color: white; 
            }
            QListWidget::item:focus {
                background-color: #3b3b3b; 
                color: white; 
            }
    """)

        
     
        minimizeAction = QAction("&Minimize", self)
        minimizeAction.setShortcut('Ctrl+N')
        minimizeAction.triggered.connect(self.minimize_window)
        
        
        maximizeAction = QAction("&Maximize", self)
        maximizeAction.setShortcut('Ctrl+X')
        maximizeAction.triggered.connect(self.maximize_window)
        
        exitAction = QAction("&Exit", self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        
       
        
        menu = self.menuBar()
        
        file_menu = menu.addMenu("&File")
        file_menu.addAction(minimizeAction)
        file_menu.addAction(maximizeAction)
        file_menu.addAction(exitAction)
        
         
    
        help_menu = self.menuBar()
        

        
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
       
        self.menu_bar3 = self.menuBar()
        self.system_service_action = QAction("&System Services") 
        self.system_service_action.triggered.connect(self.open_systems_services)
        self.system_service_action.setShortcut("Ctrl+V")
        self.menu_bar3.addAction(self.system_service_action)
        
        self.menu_bar2 = self.menuBar()
        self.setting_action = QAction("&Envs && Packages", self)
        self.setting_action.triggered.connect(self.open_settings)
        self.setting_action.setShortcut("Ctrl+P")
        self.menu_bar2.addAction(self.setting_action)
        
        
         # Create a menu bar
        self.menu_bar1 = self.menuBar()
        self.system_packages_action = QAction("&Settings", self)
        self.system_packages_action.setShortcut("Ctrl+S")
        self.system_packages_action.triggered.connect(self.open_system_packages)
        self.menu_bar1.addAction(self.system_packages_action)
        
        # Setup layout
        layout = QVBoxLayout()
        self.main_widget.setLayout(layout)
        
        documentation = QAction("&Documentation", self)
        documentation.setShortcut('Ctrl+D')
        documentation.triggered.connect(self.open_doc)
        
        
        appUsage = QAction("&App Usage", self)
        appUsage.setShortcut('Ctrl+G')
        appUsage.triggered.connect(self.show_help)
        
        
        get_updates = QAction("&Check for Updates..", self)
        get_updates.setShortcut("Ctrl+F")
        get_updates.triggered.connect(self.check_updates)    
            
        aboutAction = QAction("&About", self)
        aboutAction.setShortcut('Ctrl+A')
        aboutAction.triggered.connect(self.about_app)
        
        file_menu = help_menu.addMenu("&Help")
        file_menu.addAction(documentation)
        file_menu.addAction(appUsage)
        file_menu.addAction(get_updates)
        file_menu.addAction(aboutAction)
    
        
        
      
  
        ##############################################################################
        
        # MAIN LAYOUT
        
        #############################################################################
        
       
        
        top_widget = QWidget()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_widget.setLayout(top_layout)
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Search for modules...")
        self.line_edit.setFixedHeight(30)
        self.line_edit.textChanged.connect(self.filter_modules)
        
        
        self.combo_box1 = QComboBox()
        self.combo_box1.addItems(['All Categories','Data Science',
                                      'Web Development','Machine Learning',
                                      'Sound Output','Speech Synthesis',
                                      'Speech Recognition','Databases',
                                      'Networking','Security' ,
                                      'IoT Development','GUI Development',
                                      'Data Processing','Others'])
        self.combo_box1.setFixedHeight(30)
        self.combo_box1.currentTextChanged.connect(self.filter_modules)
        
        combo_box2 = QComboBox()
        combo_box2.setFixedHeight(30)
        combo_box2.addItems(["Sort by", "Name", "Popularity", "Version"])
        
        top_layout.addWidget(self.line_edit)
        top_layout.addWidget(self.combo_box1)
        top_layout.addWidget(combo_box2)
        
        
        
        # Package list widget
        self.install_thread = None
        self.modules = list(MODULE_CATEGORIES.keys())
        self.update_module_list()
        


        #The main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add the top widget to the layout
        layout.addWidget(top_widget)
       
        layout.addWidget(self.module_list)

        # Create the main content widget
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout()
        main_content_widget.setLayout(main_content_layout)

      
        

        # Set the central widget with the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
       
        
    
        self.setMenuBar(menu)
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        layout.setStretch(2, 1)
    
    
        # Add a label to show the download size
        self.download_size_label = QLabel("Progress bar:", self)
        self.download_size_label.setVisible(True)
        self.download_size_label.setContentsMargins(6, 6, 6, 6)
    
        
      # Initialize the progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(True)  # Hide by default

        
        
        layout.addWidget(self.download_size_label) 
        layout.addWidget(self.progress_bar)
        
    
        # Add main content widget to the layout
        self.module_list.setMinimumSize(165, 250)
        layout.addWidget(main_content_widget)
        layout.setContentsMargins(0, 20, 0, 0)
        
        

        # Log Output and Dependencies List
        log_and_deps_layout = QHBoxLayout()

        # Log Output Area
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setContentsMargins(10, 10, 10, 10)
        log_layout.addWidget(QLabel("Log Output:"))
        log_layout.setSpacing(0)
        log_layout.addWidget(self.log_output)
        log_and_deps_layout.addLayout(log_layout)

        # Dependencies List Area
        deps_layout = QVBoxLayout()
        self.dependencies_list = QListWidget()
        self.dependencies_list.setContentsMargins(10, 10, 10, 10)
        deps_layout.addWidget(QLabel("Dependencies:"))
        deps_layout.addWidget(self.dependencies_list)
        deps_layout.setSpacing(0)
        log_and_deps_layout.addLayout(deps_layout)

        layout.addLayout(log_and_deps_layout)
        
       

        # Action Buttons
        button_layout = QHBoxLayout()  # Layout for buttons

        self.install_button = QPushButton('Install Selected Module')
        self.install_button.setIcon(QIcon('icons/easy-installation.png'))  
        self.install_button.setIconSize(QSize(20, 20))  
        # self.install_button.setStyleSheet('background-color: #16c1f5; color: white;')
        self.install_button.setFixedWidth(200) 
        self.install_button.setFixedHeight(30)
        self.install_button.setToolTip('Install selected modules from the list.')
        self.install_button.setShortcut('Ctrl+I')
        self.install_button.clicked.connect(self.install_modules)
        button_layout.addWidget(self.install_button)

        self.uninstall_button = QPushButton('Uninstall Selected Module')
        self.uninstall_button.setIcon(QIcon('icons/bin.png'))  
        self.uninstall_button.setIconSize(QSize(19, 19)) 
        # self.uninstall_button.setStyleSheet('background-color: #DA3B46; color: white;')
        self.uninstall_button.setFixedWidth(209) 
        self.uninstall_button.setFixedHeight(30)
        self.uninstall_button.setToolTip('Uninstall selected modules from the list.')
        self.uninstall_button.setShortcut('Ctrl+Y')
        self.uninstall_button.clicked.connect(self.uninstall_modules)
        button_layout.addWidget(self.uninstall_button)

        self.update_button = QPushButton('Update Selected Module')
        self.update_button.setIcon(QIcon('icons/updating.png'))  
        self.update_button.setIconSize(QSize(20, 20)) 
        # self.update_button.setStyleSheet('background-color: #28a745; color: white;')
        self.update_button.setFixedWidth(200)  
        self.update_button.setFixedHeight(30)
        self.update_button.setToolTip('Update selected modules to their latest versions.')
        self.update_button.setShortcut('Ctrl+U')
        self.update_button.clicked.connect(self.update_modules)
        button_layout.addWidget(self.update_button)
        
        
        self.show_installed_pkg_btn = QPushButton('List all installed pakages')
        self.show_installed_pkg_btn.setIcon(QIcon('icons/clipboard.png'))
        self.show_installed_pkg_btn.setIconSize(QSize(19, 19))
        # self.show_installed_pkg_btn.setStyleSheet('background-color: #1E1D1D; color: white;')
        self.show_installed_pkg_btn.setFixedWidth(200)
        self.show_installed_pkg_btn.setFixedHeight(30)
        self.show_installed_pkg_btn.setShortcut("Ctrl+L")
        self.show_installed_pkg_btn.setToolTip('List installed modules from the list.')
        self.show_installed_pkg_btn.clicked.connect(self.show_installed_modules)
        button_layout.addWidget(self.show_installed_pkg_btn)
        
        self.canel_button = QPushButton('Cancel')
        self.canel_button.setIcon(QIcon('icons/cross.png'))
        self.canel_button.setIconSize(QSize(19, 19))
        # self.canel_button.setStyleSheet('background-color: #1E1D1D; color: white;')
        self.canel_button.setFixedWidth(120)
        self.canel_button.setFixedHeight(30)
        self.canel_button.setToolTip('Uninstall selected modules from the list.')
        self.canel_button.setShortcut('Ctrl+C')
        self.canel_button.clicked.connect(self.cancel_installation)
        button_layout.addWidget(self.canel_button)
        
       
        button_layout.addStretch()  # Add stretchable space to push buttons to the left
        button_layout.setSpacing(2)
        
        
        layout.addLayout(button_layout)
       

        # Status Label
        self.status_label = QLabel('')
        layout.addWidget(self.status_label)
        

       
        
        self.setLayout(layout)
        
        
            # Connect module selection to version update and dependencies display
        self.module_list.currentItemChanged.connect(self.display_dependencies)
    
    
    
    
    # Enable mouse tracking and connect the itemEntered signal to show tooltips
        self.module_list.setMouseTracking(True)
        self.module_list.itemEntered.connect(self.show_custom_tooltip)
        
    def open_systems_services(self):
        system_services = PackageSystemService(self)
        system_services.exec()
     
     
    def open_system_packages(self):
        system_packages = SystemPackages(self)
        system_packages.exec()  # Opens the dialog modally
        
    def open_settings(self):
        setting_dialog = SettingsDialog(self)
        setting_dialog.exec()
        
    def show_custom_tooltip(self, item):
        # Hide the default tooltip
        QToolTip.hideText()

        # Hide any existing custom tooltip
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.hide()

        # Create and show a new custom tooltip
        tooltip_text = item.data(Qt.UserRole)  # Get tooltip text from custom data
        self.tooltip = CustomTooltip(tooltip_text, self)

        # Get the cursor's position (global screen coordinates)
        cursor_pos = QCursor.pos()

        # Get the main window geometry (to prevent overlap)
        main_window_rect = self.geometry()  # Geometry of the main window

        # Adjust the tooltip position if it would overlap the main window
        if main_window_rect.contains(self.mapFromGlobal(cursor_pos)):
            # Shift the tooltip position slightly below the cursor to avoid overlap
            cursor_pos.setY(cursor_pos.y() + 50)

        # Show the tooltip at the adjusted position
        self.tooltip.show_tooltip(cursor_pos)

    def get_installed_version(self, module_name):
        try:
            version = importlib.metadata.version(module_name)
            return version
        except importlib.metadata.PackageNotFoundError:
            return "Not installed"
   
    def update_module_list(self):
        self.module_list.clear()
        
        for module in self.modules:
            module_name = str(module).strip()
            
            installed_version = self.get_installed_version(module)

            docs_url = MODULE_DOCS.get(module, '#')
            tooltip_text = (
                f"Category: {self.get_module_category(module_name)}<br>"
                f"Popularity: {MODULE_POPULARITY.get(module_name, 0)}<br>"
                f"Version: {installed_version}<br>"
                f"Documentation: <a href='{docs_url}'>Docs</a>"
            )

            item = QListWidgetItem(module)
            item.setData(Qt.UserRole, tooltip_text)  # Store tooltip in UserRole to suppress default

            # Do not set a tooltip using setToolTip() to prevent default behavior
            self.module_list.addItem(item)

        # Connect the custom tooltip display to item hover
        self.module_list.itemEntered.connect(self.show_custom_tooltip)
    
    ########################################################################################################################
                         # check_updates func
    
    def check_updates(self):
        """Check for application updates by comparing the current version with the latest available version."""
        try:
           
            update_url = "https://api.example.com/latest-version"

            
            response = requests.get(update_url)

            if response.status_code == 200:
                latest_version_info = json.loads(response.text)
                latest_version = latest_version_info.get("version")

                # current version with the latest version
                if version.parse(latest_version) > version.parse(self.current_version):
                    QMessageBox.information(self, 'Update Available', 
                        f"A new version {latest_version} is available. Please update the application.")
                else:
                    QMessageBox.information(self, 'No Updates', 'You have the latest version of the application.')
            else:
                QMessageBox.warning(self, 'Error', 'Failed to check for updates.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"An error occurred while checking for updates: {e}")

    
    
    def closeEvent(self, event):
        # Save the settings (size and position) when the window is closed
        self.save_settings()
        event.accept()  # Accept the close event to allow the window to close

    def save_settings(self):
        """Save the current window size and position"""
        settings = QSettings("MyApp", "MainWindow")
        
        # Save the current window geometry (position and size)
        settings.setValue("windowPosition", self.pos())  
        settings.setValue("windowSize", self.size())  
        # print("Window size and position saved.")

    def load_settings(self):
        """Load the saved window size and position"""
        settings = QSettings("MyApp", "MainWindow")
        
        # Restore the window position and size if they exist in settings
        pos = settings.value("windowPosition", QPoint(200, 200)) 
        size = settings.value("windowSize", QSize(1020, 690))  
        
        # Set the window size and position
        self.resize(size)
        self.move(pos)
        # print(f"Window size and position restored to {size}, {pos}")

    def resizeEvent(self, event):
        """Save the window size when resized"""
        self.save_settings()
        super().resizeEvent(event)

    def moveEvent(self, event):
        """Save the window position when moved"""
        self.save_settings()
        super().moveEvent(event)


    #help dailog
    def show_help(self):
        
        help_message = (
            "To use this application:\n"
            "- Search for modules using the search bar.\n"
            "- Filter modules by category and sort them as needed.\n"
            "- Select a module to see available versions and dependencies.\n"
            "- Use the Install, Uninstall, or Update buttons to perform actions on the selected modules.\n"
            "- The progress bar and log output will show the status of your actions."
        )
        QMessageBox.information(self, 'App Usage', help_message)
  
        
    def about_app(self):
        about_message = (
          "<h3 style='font-size: 20px'>Python Module Installer\n</h3>" 
          "<p>Version: 1.0</p>"
          "<p>Copyright © 2024 Python Module Installer Pty Ltd</p>" 
            
        )
        QMessageBox.information(self, 'Python Module Installer', about_message)
         # Handling window maximize & minimize
        self.setWindowState(Qt.WindowNoState)
        
    def open_doc(self):
        documentaion_url = ''
        try:
            import webbrowser
            webbrowser.open(documentaion_url)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to open documentation: {str(e)}')
        

    def showEvent(self, event):
        super().showEvent(event)
        # Handle the maximize behavior to fill the screen but keep window buttons
        if self.windowState() & Qt.WindowMaximized:
            screen_geometry = QApplication.primaryScreen().geometry()
            self.setGeometry(screen_geometry)
        else:
            self.setGeometry(self.geometry())  # Set to the current size

    def maximize_window(self):
        # Toggle maximize state
        if self.windowState() & Qt.WindowMaximized:
            self.setWindowState(Qt.WindowNoState)
        else:
            self.setWindowState(Qt.WindowMaximized)
        
    
    def minimize_window(self):
        # Toggle minimize state
        if self.windowState() & Qt.WindowMinimized:
            self.setWindowState(Qt.WindowState)
        else:
            self.setWindowState(Qt.WindowMinimized)
        
        
        
    def get_installed_modules(self):
        """Retrieve the list of installed modules."""
        try:
            result = subprocess.check_output([sys.executable, '-m', 'pip', 'list'], text=True)
            installed_modules = [line.split()[0] for line in result.split('\n')[2:] if line]
            return installed_modules
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f"Failed to retrieve installed modules: {e}")
            return []

    def show_installed_modules(self):
        """Show the installed modules in a new window."""
        installed_modules = self.get_installed_modules()  # Retrieve the list of installed modules
        dialog = InstalledModulesWindow(installed_modules)  # Pass the list of installed modules to the dialog
        dialog.exec()  # Show the dialog


  
    def filter_modules(self):
        search_text = self.line_edit.text().lower()
        category = self.combo_box1.currentText()
        print(f"Filtering modules with search text: '{search_text}' and category: '{category}'")
        
        for index in range(self.module_list.count()):
            item = self.module_list.item(index)
            module_name = item.text()
            item_category = self.get_module_category(module_name)
            print(f"Module: {module_name}, Category: {item_category}")
            
            item.setHidden(
                (search_text not in module_name.lower()) or
                (category != 'All Categories' and self.get_module_category(item.text()) != category)
            )
           


        # # Update dependencies after filtering
        
        self.display_dependencies()

  
    def sort_modules(self, sort_by):
        if sort_by == 'Name':
            self.modules.sort()
        elif sort_by == 'Popularity':
            self.modules.sort(key=lambda m: MODULE_POPULARITY.get(m, 0), reverse=True)
        elif sort_by == 'Version':
            self.modules.sort(key=lambda m: self.get_installed_version(m), reverse=True)
        
     
    def get_module_category(self, module):
        # Return module category from mock data
        return MODULE_CATEGORIES.get(module, 'Others')
    

    def display_dependencies(self):
        selected_module = self.module_list.currentItem()
        if selected_module:
            module_name = selected_module.text()
            dependencies = MODULE_DEPENDENCIES.get(module_name, [])
            self.dependencies_list.clear()
            self.dependencies_list.addItems(dependencies if dependencies else ['No dependencies'])

########################################################################################
                                # UNINSTALL MODULE FUNC
    def uninstall_modules(self):
        selected_modules = [self.module_list.item(i).text() for i in range(self.module_list.count()) if self.module_list.item(i).isSelected()]
        uninstall_action = 'uninstall'
        
        if not selected_modules:
            QMessageBox.warning(self, 'Warning', 'No modules selected for uninstallation.')
            return

        # Start the uninstallation thread
        self.uninstall_thread = InstallThread(selected_modules, uninstall_action)
        
        self.modules_not_installed = [] 
        self.module_uninstalled = []

        
        # Connect signals and slots
        self.uninstall_thread.progress.connect(self.update_progress_bar)
        self.uninstall_thread.finished.connect(self.on_uninstall_finished)
        self.uninstall_thread.finished.connect(self.re_enable_buttons)
        # self.uninstall_thread.error_occurred.connect(self.show_error_message)
        self.uninstall_thread.status_message.connect(self.show_status_message)
        self.uninstall_thread.conflict_message.connect(self.show_conflict_message)
        self.uninstall_thread.error_occurred.connect(self.handle_uninstall_error)
        self.uninstall_thread.finished.connect(self.check_uninstallation_status)
        
    
        # self.uninstall_thread.finished.connect(lambda: self.status_label.setText('Uninstallation completed.'))
         # Capture the module_uninstalled and module_not_installed signals
        self.uninstall_thread.module_uninstalled.connect(lambda module: self.module_uninstalled.append(module))
        self.uninstall_thread.module_not_installed.connect(lambda module: self.modules_not_installed.append(module))


        # Start the thread
        self.uninstall_thread.start()
        
        
    def check_uninstallation_status(self):
        
        """
         Function to indicate the uninstallation status of modules.
            - If modules are uninstalled successfully, it shows a 'Uninstallation Complete' message.
            - If modules are not installed, it shows a 'Module Not Installed' message.
        """
            
        if not hasattr(self, '_display_message_shown'):
            self._display_message_shown = False

        # Prevent multiple dialogs by using the flag
        if not self._display_message_shown:
            self._display_message_shown = True  # Set the flag to prevent multiple dialogs

            # Track whether any module was uninstalled
            any_uninstalled = False

            # Check if there are modules not installed
            if hasattr(self, 'modules_not_installed') and self.modules_not_installed:
                not_installed_modules = self.modules_not_installed.copy()  # Capture and clear list
                self.modules_not_installed.clear()
                self.progress_bar.setValue(0)
                QMessageBox.information(self, 'Module Not Installed', '\n'.join(not_installed_modules))

            # Check if any module was uninstalled
            if hasattr(self, 'module_uninstalled') and self.module_uninstalled:
                uninstalled_modules = self.module_uninstalled.copy()  # Capture and clear list
                self.module_uninstalled.clear()
                self.progress_bar.setValue(0)
                QMessageBox.information(self, 'Uninstallation Complete', '\n'.join(uninstalled_modules))
                any_uninstalled = True

            if not any_uninstalled and not self.modules_not_installed:
                # Show only if no modules were uninstalled and no modules were reported as not installed
                QMessageBox.information(self, 'Uninstallation Status', 'No uninstallation actions were performed.')

            # Reset the flag after showing the message
            self._display_message_shown = False


    def on_uninstall_finished(self):
        self.re_enable_buttons()

        # Close the cancel message if it's open
        if hasattr(self, 'cancel_message'):
            self.cancel_message.close()

        # Call the function to check uninstallation status and display the appropriate message
        self.check_uninstallation_status()

        # Ensure progress bar ends at 100%
        self.progress_bar.setValue(100)

        
    def handle_module_not_installed(self, module_name):
         self.module_not_installed = module_name

    def handle_uninstall_error(self, error_message):
        # Update the status label or log the error message
        self.status_label.setText(f"Error: {error_message}")
        self.log_output.append(f"Error occurred during uninstallation: {error_message}")

     
     # The function that I use to check wheather the internet connection is available before installation
    def is_internet_available(self):
        try: 
            import socket
            socket.create_connection(('www.google.com', 80), timeout=6)
            return True
        except OSError:
            return False
######################################################################################################
                                # INSTALL MODULE FUNC.
    @Slot()
    def install_modules(self):
         # Reset cancel_requested when starting a new installation
        self.cancel_requested = False
        
        if self.install_thread and self.install_thread.isRunning():
            # Request the current thread to stop
            self.install_thread.requestInterruption()
            self.install_thread.wait()  # Wait for the thread to finish

        selected_modules = [self.module_list.item(i).text() for i in range(self.module_list.count()) if self.module_list.item(i).isSelected()]
        action = 'install'

        if not selected_modules:
            QMessageBox.warning(self, 'Warning', 'No modules selected for installation.')
            return

        # Check for internet connection
        if not self.is_internet_available():
            QMessageBox.critical(self, 'No Internet', 'No internet connection detected. Please check your connection and try again.')
            self.status_label.setText('Installation failed: No internet connection')
            return
            
        # List to hold selected modules that are already installed
        already_installed_modules = []

        # Check if each selected module is already installed
        for module in selected_modules[:]:
            if self.is_module_installed(module):
                already_installed_modules.append(module)
                selected_modules.remove(module)

        if already_installed_modules:
            QMessageBox.information(self, 'Information', f'Modules already installed: {", ".join(already_installed_modules)}')

        if not selected_modules:
            self.status_label.setText('All selected modules are already installed.')
            return

        # Start the installation thread for the selected modules
        self.install_thread = InstallThread(selected_modules, action)
        
        # Connect signals and slots
        self.install_thread.progress.connect(self.update_progress_bar)
        self.install_thread.finished.connect(self.on_install_finished)
        self.install_thread.finished.connect(self.re_enable_buttons)
        # self.install_thread.error_occurred.connect(self.show_error_message)
        self.install_thread.status_message.connect(self.show_status_message)
        self.install_thread.conflict_message.connect(self.show_conflict_message)
        self.install_thread.error_occurred.connect(self.handle_install_error)

        # Handle successful completion
        self.install_thread.finished.connect(lambda: self.status_label.setText('Installation completed.'))

        # Start the thread
        self.install_thread.start()

    def update_progress_bar(self, progress):
        # Update the progress bar based on the emitted progress (can be % or download size)
        if isinstance(progress, str):
            self.progress_bar.setFormat(progress)  # Set the text format for MB downloaded
        else:
            self.progress_bar.setValue(progress)  # 
            
   
    def cancel_installation(self):
        if self.install_thread and self.install_thread.isRunning():
            # Set the flag to indicate cancellation is requested
            self.cancel_requested = True
            
            # Show a message box without buttons to alert the user
            self.cancel_message = QMessageBox(self)
            self.cancel_message.setWindowTitle("Cancelling Installation")
            self.cancel_message.setText("Cancelling the installation process. Please wait...")
            self.cancel_message.setStandardButtons(QMessageBox.NoButton)  # No buttons in the message box
            self.cancel_message.setIcon(QMessageBox.Information)
            self.cancel_message.show()

            # Request cancellation of the thread
            self.install_thread.requestInterruption()
            self.status_label.setText("Cancelling...")

            # Start checking for thread completion
            QTimer.singleShot(200, self.check_cancel_complete)  # Poll every 200ms
        else:
            QMessageBox.critical(self, "Warning", "No installation to canel")
            self.status_label.setText('No installation to cancel')

    def on_install_finished(self):
        self.re_enable_buttons()

        # Close the cancel message if it's open
        if hasattr(self, 'cancel_message') and self.cancel_message:
            self.cancel_message.close()

        if not hasattr(self, '_installation_complete_shown'):
            self._installation_complete_shown = False
            self.progress_bar.setValue(0)

        if self.install_thread:
            if not self.install_thread.error_occurred_flag and not self.cancel_requested:
                self.progress_bar.setValue(100)
                if not self._installation_complete_shown:
                    self._installation_complete_shown = True
                    QMessageBox.information(self, 'Installation Complete', 'Installation has completed.')
            elif self.cancel_requested:
                
            # Reset the cancel_requested flag for future operations
                self.cancel_requested = False

            # Clean up the thread
            if self.install_thread.isRunning():
                self.install_thread.quit()
                self.install_thread.wait()
            
            self.install_thread = None

        self._installation_complete_shown = False

    def check_cancel_complete(self):
        if not self.install_thread or not self.install_thread.isRunning():
            # If the thread is no longer running, update the cancel message
            if hasattr(self, 'cancel_message') and self.cancel_message:
                self.cancel_message.setText("Cancellation completed.")
                self.cancel_message.setStandardButtons(QMessageBox.Ok)  # Add "OK" button
                self.cancel_message.setIcon(QMessageBox.Information)
                self.status_label.setText("Installation cancelled.")
                
                # Optionally, remove the message box after a few seconds
                QTimer.singleShot(3000, self.cancel_message.close)  # Close the message box after 3 seconds

        else:
            # Continue checking
            QTimer.singleShot(200, self.check_cancel_complete)  # Poll every 200ms

       
    def closeEvent(self, event):
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.isInterruptionRequested()
            self.install_thread.wait()
        event.accept()
    
            
    def handle_install_error(self, error_message):
        if error_message:
            # Create a QMessageBox instance
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error")
            msg.setText("An error occurred during installation.")
            msg.setDetailedText(error_message)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setSizeGripEnabled(True)
            msg.exec()
            
            
    @Slot(str)   
    # def display_error(self, error_message):
    #         if not hasattr(self, "_display_error_show"):
    #             self.__display_error_show = False
    #         if not self.__display_error_show:
    #             self.__display_error_show = True
    #             QMessageBox.critical(self, 'Error', error_message)
    #             self.__display_error_show = False
        
    def re_enable_buttons(self):
        
        self.install_button.setDisabled(False)
        self.uninstall_button.setDisabled(False)
        self.update_button.setDisabled(False)
        
        if not hasattr(self, '__warning_messagebox'):
            self.__warning_messagebox = False
        
        if self.install_thread and self.install_thread.isRunning():
            if not self.__warning_messagebox or not self.__warning_messagebox.isVisible():
                self.__warning_messagebox =  QMessageBox.warning(self, 'Warning', 'Another operation is still running. Please wait.')
                
            return
        
        self.__warning_messagebox = False
    
    def is_module_installed(self, module_name):
        try:
            import pkg_resources
            pkg_resources.get_distribution(module_name)
            return True
        except pkg_resources.DistributionNotFound:
            return False
        
#################################################################################################################### 
                            # UPDATE MODULES FUNC.
        
    def update_modules(self):
        selected_modules = [self.module_list.item(i).text() for i in range(self.module_list.count()) if self.module_list.item(i).isSelected()]
        update_action = 'update'
        if not selected_modules:
            QMessageBox.warning(self, 'Warning', 'No modules selected for update.')
            return
        
         # Check for internet connection
        if not self.is_internet_available():
            QMessageBox.critical(self, 'No Internet', 'No internet connection detected. Please check your connection and try again.')
            self.status_label.setText('Installation failed: No internet connection')
            
            
        self.update_thread = InstallThread(selected_modules, update_action)
        self.update_thread.progress.connect(self.update_progress_bar)
        self.update_thread.finished.connect(self.on_update_finished)
    
        self.update_thread.status_message.connect(self.show_status_message)
        self.update_thread.conflict_message.connect(self.show_conflict_message)
        self.update_thread.error_occurred.connect(self.handle_update_error)
        self.update_thread.finished.connect(lambda: self.status_label.setText('Update completed.'))
        self.update_thread.start()
         
        
    def on_update_finished(self):
        if not hasattr(self, '_update_complete_shown'):
            self._update_complete_shown = False

        if not self._update_complete_shown:
            self.progress_bar.setValue(100)  # Ensure it ends at 100%
            self._update_complete_shown = True
            QMessageBox.information(self, 'Update Complete', 'Update has completed.')
            self._update_complete_shown = False  # Reset flag after closing  
             
    def handle_update_error(self, error_message):
        if error_message:  # Add some condition check if needed
            QMessageBox.critical(self, 'Error', error_message)
     

            
    def show_conflict_message(self, message):
        QMessageBox.critical(self, 'Conflict', message)     
            
    
    def change_version(self, version):
        # This method is triggered when a version is selected from the combobox
        selected_version = version.strip()  # Get the selected version
        if selected_version:
            self.selected_version = selected_version
          
        
    # The following  Function is for Qmessagebox
    def show_status_message(self, message):
        self.log_output.append(message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


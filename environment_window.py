from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QLabel, QMessageBox, QComboBox, QProgressBar,
                               QTextEdit, QDialog, QMenuBar, QMenu, QSpacerItem, QSizePolicy,QToolTip, QScrollArea, QStackedWidget,
                               QFormLayout, QCheckBox, QInputDialog, QDialogButtonBox, QFileDialog, QStyle, QGroupBox, QGridLayout, QTabWidget, QFrame)
from PySide6.QtGui import QIcon, QAction,  QCursor, QShowEvent, QColor, QPainter, QFont, QTextCursor
from PySide6.QtCore import QSize, QThread, Signal, QEvent, QTimer, QPoint, Slot, QSettings,QProcess, QMetaObject, Qt, Q_ARG, QRect
from threading import Thread
from packaging import version
import importlib.metadata
from package import MODULE_POPULARITY, MODULE_CATEGORIES, MODULE_DEPENDENCIES, MODULE_DOCS

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


class InstallWorker(QThread):
    progress_signal = Signal(int)  # Signal to emit progress updates

    def __init__(self, pip_path, module_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pip_path = pip_path
        self.module_name = module_name

    def run(self):
        # Emulate installation with progress (you'll replace this with the actual subprocess run)
        for i in range(0, 101, 10):  # Simulate progress from 0% to 100%
            self.progress_signal.emit(i)  # Emit progress signal
            self.sleep(1)  # Simulate time delay for installation

        # Once done, emit 100% progress
        self.progress_signal.emit(100)



    
    


class DebugLevelDialog(QDialog):
    def __init__(self, deb_file, append_output_debug):
        super().__init__()
        self.deb_file = deb_file
        self.append_output_debug = append_output_debug  # Reference to the output display
        self.initUI()

    def initUI(self):
        
          # Initialize last authentication time
        self.last_password_time = None
        self.password_cache_duration = 15 * 60  # 15 minutes in seconds
        self.cached_password = None  # Store the password after first authentication
        
        
        
        # Create a ComboBox for selecting the debug level
        self.debug_level_combo = QComboBox(self)
        self.debug_level_combo.addItems([
            "1 - General",
            "2 - Scripts",
            "10 - Each File",
            "20 - Configuration Files",
            "100 - Config Files Detail",
            "40 - Dependencies",
            "400 - Dependencies Detail",
            "10000 - Triggers",
            "20000 - Triggers Detail",
            "40000 - Triggers Silly"
        ])

        # Create a button to confirm the selection
        self.confirm_button = QPushButton("Confirm Debug Level", self)
        self.confirm_button.clicked.connect(self.confirm_selection)

        # Create a label to show the selected file
        self.info_label = QLabel(f"Selected .deb file:\n {self.deb_file}", self)

        # Layout setup
        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addWidget(self.debug_level_combo)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)
        self.setWindowTitle("Select Debug Level")
        self.setFixedSize(480, 300)

    def confirm_selection(self):
        # Get the selected debug level
        debug_level = self.debug_level_combo.currentText().split(" ")[0]

        # Construct the dpkg command with debug level
        reinstall_deb_passwd = self.prompt_for_password()
        if reinstall_deb_passwd is not None:
            reinstall_deb_command = f"echo {reinstall_deb_passwd} | sudo dpkg --install --debug={debug_level} {self.deb_file}"

        # Run the subprocess to execute the dpkg command
        try:
            reinstall_deb_output = subprocess.check_output(reinstall_deb_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            self.append_output_debug.append_output(f"Successfully ran:\n{reinstall_deb_command}\nOutput:\n{reinstall_deb_output}")
        except subprocess.CalledProcessError as e:
            error_message = f"Failed to run command:\n{e.output}"
            self.append_output_debug.append_output(error_message)

        # Close the dialog
        self.accept()
        
        
    def prompt_for_password(self):
        # Check if password is still within the cache period
        if self.last_password_time and (time.time() - self.last_password_time < self.password_cache_duration):
            # Return cached password if it's still valid
            return self.cached_password
        
        # If no valid cached password, prompt the user for the password
        while True:
            password = self.show_password_dialog()
            if password is None:
                return None
            if self.verify_password(password):
                self.last_password_time = time.time()
                self.cached_password = password
                return password
            else:
                QMessageBox.warning(self,"Authentication Failed", "The password you entered is incorrect. Please try again.")

    def verify_password(self, password):
        try:
            command =['sudo', '-S', '-k', 'true']
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout , stderr = process.communicate(input=password + '\n')
            
            return process.returncode == 0
        except subprocess.CalledProcessError:
            return False
    
    
   
    def show_password_dialog(self):
        # Create a dialog to input the password
        dialog = QDialog(self)
        dialog.setWindowTitle('Password Required')
        dialog.setFixedSize(330, 130)
        
        # Layout for the dialog
        dialog_layout = QVBoxLayout()
        
        # Password input field
        password_input = QLineEdit(dialog)
        password_input.setEchoMode(QLineEdit.Password)  # Hide password input
        password_input.setPlaceholderText("Enter your password")
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.button(QDialogButtonBox.Ok).setText("Authenticate")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        dialog_layout.addWidget(QLabel('Enter your password to proceed:'))
        dialog_layout.addWidget(password_input)
        dialog_layout.addWidget(buttons)
        
        dialog.setLayout(dialog_layout)
        
        if dialog.exec() == QDialog.Accepted:
            return password_input.text()
        else:
           return None
        
  
        

class DebugWithDpkg(QWidget):
    def __init__(self):
        super().__init__()
        self.output_signal.command_output_signal1.connect(self.update_output_for_dpkg)
        self.initUI()

    def initUI(self):
        # Create a button to choose a .deb file
        self.select_deb_button = QPushButton("Select .deb File", self)
        self.select_deb_button.clicked.connect(self.select_deb_file)

         # Create a QTextEdit for output display
        self.output_display1 = QTextEdit()
        self.output_display1.setFixedHeight(250)
        self.output_display1.setReadOnly(True)

        # Layout setup
        layout = QVBoxLayout(self)
        layout.addWidget(self.select_deb_button)
        layout.addWidget(self.output_display1)
        self.setLayout(layout)


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


class SettingsDialog(QDialog):
    command_output_signal = Signal(str)
    command_output_signal1 = Signal(str)
    command_output_signal2 = Signal(str)
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Environment & Packages")
        self.setFixedSize(920, 720)
        
        # self.setMinimumSize(920, 720)
        
   

        
        self.current_directory = os.getcwd()
        self.process = None
        
        
        # Initialize last authentication time
        self.last_password_time = None
        self.password_cache_duration = 15 * 60  # 15 minutes in seconds
        self.cached_password = None  # Store the password after first authentication
        
        
        # Main layout
        main_layout = QVBoxLayout()
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)
        
        # Add sections to the layout
        self.setup_env_section(content_layout, parent)
        self.setup_pip_cache_section(content_layout)
        self.setup_system_package_section(content_layout)
        self.setup_dpkg_management_section(content_layout)
        
        # Spacer to push content upwards and buttons at the bottom
        content_layout.addSpacerItem(QSpacerItem(5, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

    # Environment section
    def setup_env_section(self, layout, parent):
        env_combined_layout = QVBoxLayout()
        
         # Font style for buttons and labels
        font = QFont()
        font.setPointSize(10)

        # Python Environment
        env_layout = QHBoxLayout()
        self.env_label = QLabel("<b>Python Environment:</b>")
        self.env_combo = QComboBox()
        self.env_combo.addItems(["System", "Virtualenv", "Conda"])
        self.env_combo.setFont(font)
        self.env_combo.setToolTip("Choose and select the environment you require.")
        self.env_combo.setCurrentText(parent.python_env if hasattr(parent, 'python_env') else 'System')
        self.env_combo.currentTextChanged.connect(self.on_env_change)
        env_layout.addWidget(self.env_label)
        env_layout.addWidget(self.env_combo)

        # Environment Name and Directory (Initially hidden)
        name_layout = QHBoxLayout()
        self.env_name_label = QLabel("Environment Name:")
        self.env_name_label.setFont(font)
        self.env_name_input = QLineEdit()
        name_layout.addWidget(self.env_name_label)
        name_layout.addWidget(self.env_name_input)
        self.env_name_label.hide()
        self.env_name_input.hide()
        self.dir_button = QPushButton("Choose Directory")
        self.dir_button.setFont(font)
        self.dir_button.clicked.connect(self.select_directory)
        self.dir_button.hide()

        # Add elements to combined layout
        env_combined_layout.addLayout(env_layout)
        env_combined_layout.addLayout(name_layout)
        env_combined_layout.addWidget(self.dir_button)

        # Save and Install buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Create Environment")
        self.save_button.setFont(font)
        self.save_button.clicked.connect(self.save_settings)
        self.install_modules_button = QPushButton("Install Modules")
        self.install_modules_button.setFont(font)
        self.install_modules_button.clicked.connect(self.install_modules)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.install_modules_button)
        env_combined_layout.addLayout(button_layout)
        
    
        
        #The progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setFixedWidth(420)
        self.progress_bar.setContentsMargins(10, 10, 10, 10)
        self.progress_bar.setFont(font)
        
        
        
        

        # Create a horizontal layout to hold the progress bar
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, alignment=Qt.AlignRight)  # Align the progress bar to the left

        # Add the progress bar layout to the main combined layout
        env_combined_layout.addLayout(progress_layout)
        
        self.downloading_status = QLabel("Downloading..")
        self.downloading_status.setFont(font)
        self.downloading_status.setVisible(False)
        env_combined_layout.addWidget(self.downloading_status, alignment=Qt.AlignRight)

        
    
        
        
        

        # Note about environment activation
        note_label = QLabel("<b>Note:</b> Please use the terminal to activate and deactivate the environment.")
        env_combined_layout.addWidget(note_label)

        layout.addLayout(env_combined_layout)

    # Pip Cache Management
    def setup_pip_cache_section(self, layout):
        
        font = QFont()
        font.setPointSize(10)
        
        pip_cache_layout = QVBoxLayout()
        pip_cache_label = QLabel("<b>Pip Cache Management:</b>")
        # pip_cache_label.setFont(font)
        pip_cache_layout.addWidget(pip_cache_label)
        
        pip_button_layout = QHBoxLayout()
        self.pip_list_button = QPushButton("List Pip Cache")
        self.pip_info_button = QPushButton("Show Pip Cache Info")
        self.pip_purge_button = QPushButton("Purge Pip Cache")
        self.pip_remove_button = QPushButton("Remove Pip Cache")
        
        self.pip_list_button.setFont(font)
        self.pip_info_button.setFont(font)
        self.pip_purge_button.setFont(font)
        self.pip_remove_button.setFont(font)
        
        
        self.pip_list_button.clicked.connect(self.list_pip_cache)
        self.pip_info_button.clicked.connect(self.pip_cache_info)
        self.pip_purge_button.clicked.connect(self.purge_pip_cache)
        self.pip_remove_button.clicked.connect(self.remove_pip_cache)

        pip_button_layout.addWidget(self.pip_list_button)
        pip_button_layout.addWidget(self.pip_info_button)
        pip_button_layout.addWidget(self.pip_purge_button)
        pip_button_layout.addWidget(self.pip_remove_button)

        pip_cache_layout.addLayout(pip_button_layout)

        # Output display for Pip Cache and file removal input
        self.output_display = QTextEdit()
        self.output_display.setFixedHeight(150)
        self.output_display.setReadOnly(True)
        pip_cache_layout.addWidget(self.output_display)
        
       

        self.file_remove_input = QTextEdit()
        self.file_remove_input.setPlaceholderText("Enter filename to remove (leave blank to remove all)")
        self.file_remove_input.setFixedHeight(60)
        pip_cache_layout.addWidget(self.file_remove_input)

        self.command_output_signal.connect(self.update_command_output)
        
         # Toggle button for output visibility
        self.toggle_button = QPushButton("\u25B2")
        # self.toggle_button.setToolTip("Show the system package management area.")
        self.toggle_button.setFixedHeight(15)
        self.toggle_button.setFixedWidth(35)
        self.toggle_button.clicked.connect(self.toggle_button_display0)
        pip_cache_layout.addWidget(self.toggle_button)

 

        layout.addLayout(pip_cache_layout)

    # System Package Management
    def setup_system_package_section(self, layout):
        
        font = QFont()
        font.setPointSize(10)
        
        system_package_layout = QVBoxLayout()
        system_package_label = QLabel("<b>System Package Management:</b>")
        system_package_layout.addWidget(system_package_label)

        # Package install/uninstall buttons
        system_package_btns_layout = QHBoxLayout()
        self.system_package_install = QPushButton("Install Package")
        self.system_package_run_command = QPushButton("Run Command")
        self.system_package_uninstall = QPushButton("Remove Package")
        
        self.system_package_install.setFont(font)
        self.system_package_uninstall.setFont(font)
        self.system_package_run_command.setFont(font)
        
        self.system_package_install.clicked.connect(self.install_package)
        self.system_package_uninstall.clicked.connect(self.remove_package)
        self.system_package_run_command.clicked.connect(self.system_run_command)
        system_package_btns_layout.addWidget(self.system_package_install)
        system_package_btns_layout.addWidget(self.system_package_run_command)
        system_package_btns_layout.addWidget(self.system_package_uninstall)
        
        

        # Input field and output for package management
        self.sys_package_input = QLineEdit()
        self.sys_package_input.setPlaceholderText("Command Prompt")
        self.sys_package_input.setFocus()
        self.sys_package_input.setFixedHeight(30)
        self.sys_package_input.returnPressed.connect(self.system_run_command)
        # self.sys_package_input.returnPressed.connect(self.clear_sys_package_output)
        system_package_layout.addWidget(self.sys_package_input)
        
        system_package_layout.addLayout(system_package_btns_layout)
        
        
        
        self.sudo_checkbox = QCheckBox("Run as sudo", self)
        system_package_layout.addWidget(self.sudo_checkbox)

        self.sys_package_output = QTextEdit()
        self.sys_package_output.setFixedHeight(250)
        self.sys_package_output.setReadOnly(True)
        self.sys_package_output.setVisible(False) 
        system_package_layout.addWidget(self.sys_package_output)
        


        # Toggle button for output visibility
        self.toggle_button = QPushButton("\u25B2")
        # self.toggle_button.setToolTip("Show the system package management area.")
        self.toggle_button.setFixedHeight(15)
        self.toggle_button.setFixedWidth(35)
        self.toggle_button.clicked.connect(self.toggle_button_display)
        system_package_layout.addWidget(self.toggle_button)

        self.load_toggle_state()
        layout.addLayout(system_package_layout)
    
    
    def select_deb_file(self):
        # Open the file dialog to select a .deb file
        deb_file, _ = QFileDialog.getOpenFileName(self, "Select .deb file", "", "Debian Package Files (*.deb)")

        if deb_file:
            # Open the debug level dialog
            debug_dialog = DebugLevelDialog(deb_file, self)  # Pass output_display to the dialog
            if debug_dialog.exec() == QDialog.Accepted:
                # The dialog's confirm_selection method handles the subprocess
                pass  # No need to do anything here, handled in the dialog

        else:
            QMessageBox.warning(self, "No File Selected", "Please select a .deb file before proceeding.")

    def append_output(self, text):
        """Append text to the output display without clearing it."""
        self.output_display1.append(text)  # Append new text


    

    # Dpkg Management
    def setup_dpkg_management_section(self, layout):
        
        font = QFont()
        font.setPointSize(10)
        
        dpkg_management_layout = QVBoxLayout()
        dpkg_management_label = QLabel("<b>Dependencies Management:</b>")
        dpkg_management_layout.addWidget(dpkg_management_label)
        
        
        
        tab_widget = QTabWidget()
        
        action_selection_tab = QWidget()
        action_selection_layout = QGridLayout()
        
        
        action_selection_btn = [
            ("Debug", self.select_deb_file, "Debug"),
            ("Install", self.dpkg_installation, "Install Specific file"),
            ("Remove", self.dpkg_remove, "Remove Files"),
            # ("Hold", self.dpkg_hold, "Hold File(s)"),
            ("Purge", self.purge_remove, "Purge Remove File(s)")
            
        ]
        self.add_buttons_to_layout(action_selection_btn, action_selection_layout )
        
        action_selection_tab.setLayout(action_selection_layout)
        action_selection_tab.setFont(font)
        tab_widget.addTab(action_selection_tab, "Action Selection")
        
        #Package Status tab
        
        package_status_tab = QWidget()
        package_status_layout = QGridLayout()

        package_status_buttons = [
            ("Get Selection", self.get_selection,  "Get list of selections to stdout."),
            ("Configure", self.dpkg_configure, "configure specific file(s)"),
            ("Status", self.dpkg_check_status, "Check for package weather is installed or not."),
            ("Unpacked", self.unpacked_dpkg, ""),
            ("List", self.dpkg_list, "List Architecture Description."),
            # ("Awaiting triggers", self.awaiting_triggs, ""),
            ("Installed", self.installed_dpkg, "Check for Installed .deb file(s).")
            
        ]  
        self.add_buttons_to_layout(package_status_buttons, package_status_layout)
        
        package_status_tab.setLayout(package_status_layout)
        package_status_tab.setFont(font)
        tab_widget.addTab(package_status_tab, "Package Status")      
        
        dpkg_management_layout.addWidget(tab_widget)

        
       # Create the layout for the search input and button
        search_input_layout = QHBoxLayout()

        # Set up the search input (QLineEdit)
        self.dpkg_search_input = QLineEdit()
        self.dpkg_search_input.setPlaceholderText("Search dependency..")
        self.dpkg_search_input.setFixedHeight(29)
        self.dpkg_search_input.setMaxLength(50)
       
        
        self.dpkg_search_input.setFocus()
        self.dpkg_search_input.returnPressed.connect(self.gpkg_search_input)

        # Add the search input to the horizontal layout
        search_input_layout.addWidget(self.dpkg_search_input)

        # Set up the search button (QPushButton)
        self.search_input_btn = QPushButton()
        self.search_input_btn.setIcon(QIcon('icons/search.png'))
        self.search_input_btn.setFixedWidth(25)
        self.search_input_btn.clicked.connect(self.gpkg_search_input)

        # Add the search button to the same horizontal layout
        search_input_layout.addWidget(self.search_input_btn)

        # Finally, add the horizontal layout to the main layout
        dpkg_management_layout.addLayout(search_input_layout)


        # Output display for Dpkg management
        self.output_display1 = QTextEdit()
        self.output_display1.setFixedHeight(250)
        self.output_display1.setReadOnly(True)
        dpkg_management_layout.addWidget(self.output_display1)
        
        self.command_output_signal1.connect(self.update_output_for_dpkg)
        
          # Toggle button for output visibility
        self.toggle_button = QPushButton("\u25B2")
        # self.toggle_button.setToolTip("Show the system package management area.")
        self.toggle_button.setFixedHeight(15)
        self.toggle_button.setFixedWidth(35)
        self.toggle_button.clicked.connect(self.toggle_button_display1)
        dpkg_management_layout.addWidget(self.toggle_button)


        layout.addLayout(dpkg_management_layout)


    
        
    
    def load_toggle_state(self):
        # Initialize QSettings to read from a persistent storage (e.g., config file)
        settings = QSettings("PythonModule", "PythonModuleInstaller")

        # Get the saved state, default is False (hidden)
        toggle_state = settings.value("sys_package_output_visible", False, type=bool)

        # Apply the saved state
        self.sys_package_output.setVisible(toggle_state)
        if toggle_state:
            self.toggle_button.setText("\u25B2")  # Up arrow if visible
        else:
            self.toggle_button.setText("\u25BC")  # Down arrow if hidden

    def save_toggle_state(self, is_visible):
        # Initialize QSettings to write to a persistent storage
        settings = QSettings("PythonModule", "PythonModuleInstaller")

        # Save the state of the output display visibility
        settings.setValue("sys_package_output_visible", is_visible)

    def toggle_button_display(self):
        # Check the current visibility state and toggle it
        is_visible = self.sys_package_output.isVisible()
        self.sys_package_output.setVisible(not is_visible)
        
    def toggle_button_display0(self):
        is_visible = self.output_display.isVisible()
        self.output_display.setVisible(not is_visible)
        
    def toggle_button_display1(self):
        is_visible = self.output_display1.isVisible()
        # Toggle visibility
        self.output_display1.setVisible(not is_visible)
        
        
        # Update button text and save the state
        if is_visible:
            self.toggle_button.setText("\u25BC")  # Down arrow (hidden)
            self.toggle_button.setToolTip("Display")
            self.save_toggle_state(False)
        else:
            self.toggle_button.setText("\u25B2")  # Up arrow (visible)
            self.toggle_button.setToolTip("Hide")
            self.save_toggle_state(True)
            

    def prompt_for_password(self):
        # Check if password is still within the cache period
        if self.last_password_time and (time.time() - self.last_password_time < self.password_cache_duration):
            # Return cached password if it's still valid
            return self.cached_password
        
        # If no valid cached password, prompt the user for the password
        while True:
            password = self.show_password_dialog()
            if password is None:
                return None
            if self.verify_password(password):
                self.last_password_time = time.time()
                self.cached_password = password
                return password
            else:
                QMessageBox.warning(self,"Authentication Failed", "The password you entered is incorrect. Please try again.")

    def verify_password(self, password):
        try:
            command =['sudo', '-S', '-k', 'true']
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout , stderr = process.communicate(input=password + '\n')
            
            return process.returncode == 0
        except subprocess.CalledProcessError:
            return False
    
    
   
    def show_password_dialog(self):
        # Create a dialog to input the password
        dialog = QDialog(self)
        dialog.setWindowTitle('Password Required')
        dialog.setFixedSize(330, 130)
        
        # Layout for the dialog
        dialog_layout = QVBoxLayout()
        
        # Password input field
        password_input = QLineEdit(dialog)
        password_input.setEchoMode(QLineEdit.Password)  # Hide password input
        password_input.setPlaceholderText("Enter your password")
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.button(QDialogButtonBox.Ok).setText("Authenticate")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        dialog_layout.addWidget(QLabel('Enter your password to proceed:'))
        dialog_layout.addWidget(password_input)
        dialog_layout.addWidget(buttons)
        
        dialog.setLayout(dialog_layout)
        
        if dialog.exec() == QDialog.Accepted:
            return password_input.text()
        else:
           return None
    

     # Clear the previous output
        self.sys_package_output.clear()

    def install_package(self):
        package_name = self.sys_package_input.text().strip()  # Strip whitespace
        if package_name:
           
             

            self.set_monospace_font_sys_package()
            # Update QTextEdit to show the command being run
            self.sys_package_output.setText(f"Running command: sudo apt-get install -y {package_name}")

            password = self.prompt_for_password()
            if password is not None:
                # Create the command to run
                command = f"echo {password} | sudo -S apt-get install -y {package_name}"

                # Run the command and capture output
                process = subprocess.Popen(command, shell=True, 
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           universal_newlines=True)

                # Read the output in real-time
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.set_monospace_font_sys_package()  # Ensure the font is set
                        self.append_to_output1(output)  # Append the output to the QTextEdit

                # Wait for the process to complete
                process.wait()
            else:
                self.sys_package_output.setText("Password input was canceled or empty.")
        else:
            self.sys_package_output.setText("No package name provided.")
            
        
        self.sys_package_input.clear()  
        

  
    def system_run_command(self):
        package_name_run = self.sys_package_input.text().strip()
        
        if package_name_run:
            # Handle the 'clear' command separately
            if package_name_run == 'clear':
                self.clear_sys_package_output()  # Clear the output and return
                return

            # Retrieve the user's shell environment
            self.user_shell = os.getenv('SHELL', '/bin/bash')  # Default to /bin/bash if no SHELL is found

            # Check if sudo is required
            if self.sudo_checkbox.isChecked():
                sudo_dialog = QMessageBox()
                sudo_dialog.setIcon(QMessageBox.Warning)
                sudo_dialog.setWindowTitle("Sudo Required")
                sudo_dialog.setFixedSize(330, 130)
                sudo_dialog.setText(f"The command will be run with 'sudo': {package_name_run}")
                sudo_dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

                result = sudo_dialog.exec()  # This opens the dialog and waits for user input
                if result == QMessageBox.Cancel:
                    return  # User canceled the sudo operation

                sudo_password = self.prompt_for_password()
                if sudo_password is not None:
                    # Prepare the command with sudo and password
                    command_to_run = f"echo {sudo_password} | sudo -S {package_name_run}"
                else:
                    return  # If no password was provided, exit the function
            else:
                # If no sudo is needed, just run the command directly
                command_to_run = package_name_run

            # Start the command in a separate thread
            thread = threading.Thread(target=self.run_command_thread, args=(command_to_run, self.user_shell))
            thread.start()

        # Clear the input field after processing the command
        self.sys_package_input.clear()

    def clear_sys_package_output(self):
        """Clear the output widget."""
        self.sys_package_output.clear()
        self.sys_package_input.clear()
     

    def run_command_thread(self, command_to_run, user_shell):
        try:
            if command_to_run.startswith('cd'):
                self.change_directory(command_to_run)
            elif command_to_run == 'dmesg':
                self.read_dmesg()
            elif command_to_run == 'top':
                self.run_interactive_command(command_to_run)
            else:
                run_output = subprocess.check_output(command_to_run, shell=True, stderr=subprocess.STDOUT, cwd=self.current_directory, executable=user_shell)
                self.set_monospace_font_sys_package()
                
                output_text = run_output.decode('utf-8')
                # self.sys_package_output.setText(run_output.decode("utf-8"))
                self.command_output_signal.emit(output_text)  # Emit the output signal
                # self.append_to_output1(output_text)  # Append output to display

        except subprocess.CalledProcessError as e:
            error_message = f"Error running the command:\n{e.output.decode('utf-8')}"
            self.command_output_signal.emit(error_message)
            # self.append_to_output(error_message)  # Append error message to display

    # def append_to_output(self, text):
    #     """Append text to the output display without clearing it"""
    #     self.sys_package_output.moveCursor(QTextCursor.End)
    #     self.sys_package_output.insertPlainText(text + '\n')

        
        
       
    def read_dmesg(self):
        try:
            
            
            output = subprocess.check_output(['dmesg'], text=True)
            self.command_output_signal.emit(output)
        except subprocess.CalledProcessError as e:
            # self.command_output_signal.emit(f"Error reading dmesg:\n{e.output.encode('utf-8')}")
            self.command_output_signal.emit(f"dmesg: read kernel buffer failed: Operation not permitted {e.output}")

    def run_interactive_command(self, command):
        try:
            self.process = subprocess.Popen(command, shell=True, cwd=self.current_directory, executable=self.user_shell,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            while True:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    self.command_output_signal.emit(output.strip())
        except Exception as e:
            self.command_output_signal.emit(f"Error running {command}: \n{str(e)}")

    def send_input(self, user_input):
        if self.process and self.process.stdin:
            self.process.stdin.write(user_input + '\n')
            self.process.stdin.flush()

    def change_directory(self, command):
        try:
            parts = command.split()
            if len(parts) == 2:
                new_dir = parts[1]
                os.chdir(new_dir)
                self.current_directory = os.getcwd()
                self.command_output_signal.emit(f"Changed directory to {self.current_directory}")
            elif len(parts) == 1:
                home_dir = os.path.expanduser('~')
                os.chdir(home_dir)
                self.current_directory = home_dir
                self.command_output_signal.emit(f"Changed directory to {self.current_directory}")
            else:
                self.command_output_signal.emit(f"Invalid `cd` command.")
        except Exception as e:
            self.command_output_signal.emit(f"Error changing directory: {str(e)}")

    def update_command_output(self, output_text):
        self.append_to_output(output_text)
        
          
    def remove_package(self):
        package_name1 = self.sys_package_input.text().strip()  # Strip whitespace
        if package_name1:
            # Clear the previous output
            self.sys_package_output.clear()

            # Update QTextEdit to show the command being run
            self.sys_package_output.setText(f"Running command: sudo apt-get remove -y {package_name1}")

            password = self.prompt_for_password()
            if password is not None:
                # Create the command to run
                command = f"echo {password} | sudo -S apt-get remove -y {package_name1}"

                # Run the command and capture output
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

                # Read the output in real-time
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.set_monospace_font_sys_package()  # Ensure the font is set
                        self.append_to_output1(output)  # Append the output to the QTextEdit

                # Wait for the process to complete
                process.wait()
            else:
                self.sys_package_output.setText("Password input was canceled or empty.")
        else:
            self.sys_package_output.setText("No package name provided.")
                

    def run_command(self, command):
        try:
            # Run the command and capture the output
            output = subprocess.check_output(command, shell=True, universal_newlines=True, stderr=subprocess.STDOUT)
            
            self.set_monospace_font_sys_package()
            self.sys_package_output.setText(output)  # Ensure output is displayed in the GUI
            # self.append_to_output(output)
        except subprocess.CalledProcessError as e:
            error_message = f"Error executing command: {e.output}"
            print(error_message)  # Log the error
            self.sys_package_output.setText(error_message)  # Display error in the GUI

       

    def set_monospace_font_sys_package(self):
        font = QFont("Source Code Pro")
        font.setStyleHint(QFont.Monospace)
        self.sys_package_output.setFont(font)
        
        
        
        
################################################################################################################

                # THe PIP MANAGEMENT FUNCTIONS SECTION

#################################################################################################################

    
    # Pip cache operations
    def list_pip_cache(self):
        try:
            output = subprocess.check_output(["pip", "cache", "list"], universal_newlines=True)
            self.set_monospace_pip()
            self.output_display.setText(output)  # You can display this in the UI if needed
        except subprocess.CalledProcessError as e:
            print(f"Error listing pip cache: {e}")

    def pip_cache_info(self):
        try:
            output = subprocess.check_output(["pip", "cache", "info"], universal_newlines=True)
            self.set_monospace_pip()
            self.output_display.setText(output) # You can display this in the UI if needed
        except subprocess.CalledProcessError as e:
            print(f"Error showing pip cache info: {e}")

    def purge_pip_cache(self):
        try:
            output = subprocess.check_output(["pip", "cache", "purge"], universal_newlines=True)
            self.set_monospace_pip()
            self.output_display.setText(output)  # You can display this in the UI if needed
        except subprocess.CalledProcessError as e:
            print(f"Error purging pip cache: {e}")

    def remove_pip_cache(self):
        file_to_remove = self.file_remove_input.toPlainText().strip()
        
        if file_to_remove:
            try :
                output = subprocess.check_output(["pip", "cache", "remove", "*"], universal_newlines=True)
                self.set_monospace_pip()
                self.output_display.setText(f"Removed specific file: {file_to_remove}\n\n{output}")
                
            except subprocess.CalledProcessError as e:
                self.output_display.setText(f"Error removing pip cache file: {e}")         
        else:
            try:
                output = subprocess.check_output(["pip", "cache", "remove", "*"], universal_newlines=True)
                self.output_display.setText(f"Removed all pip cache files\n\n{output}")
            except subprocess.CalledProcessError as e:
                self.output_display.setText(f"Error removing all pip cache files: {e}")
     
    def set_monospace_pip(self):
        font = QFont("Source Code Pro")  
        font.setStyleHint(QFont.Monospace)
        self.output_display.setFont(font)
        
        
                   
 ###################################################################################################################   
 
        # THE DPKG MANAGEMENT FUNCTIONS
 
 ###################################################################################################################      
    def reinstall_command(self):
        #Debugging tool
        
        
        
            
            
        
        
        pass

    def dpkg_hold(self):
        pass
    
    def purge_remove (self):
        purge_remove, ok = QInputDialog.getText(self, "Purge Remove", "Enter the package name to remove ")
        
        if not ok or not purge_remove:
            QMessageBox.warning("Error", "Package name input was canceled or empty.")
            return
        
        passwrd = self.prompt_for_password()
        if passwrd is not None:
            run_command = f"echo {passwrd} | sudo dpkg -P {purge_remove}"
        
        
        try:
            command = subprocess.check_output(run_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            self.command_output_signal1.emit(command)
        except subprocess.CalledProcessError as e:
            self.command_output_signal1.emit(f"Failed to purge remove file")
    
    def add_buttons_to_layout(self, buttons, layout):
        """ Helper function to add buttons to a layout with consistent styling """
        for idx, (text, func, tooltip) in enumerate(buttons):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.clicked.connect(func)
            btn.setFixedWidth(150)
            layout.addWidget(btn, idx // 2, idx % 2)  # Arrange in a 2-column grid
            

    def get_selection(self):
        get_selection_input, ok = QInputDialog.getText(self, "Get Selection", "Enter the package name for selection.(Leave it blank to list all..)")
        
        # if not ok or not get_selection_input:
        #     QMessageBox.warning(self, "Error", "Package name input was canceled or empty.")
        #     return
        
        if get_selection_input is not None:
           process = f"dpkg --get-selections {get_selection_input}"
        else:
            process = "dpkg --get-selections"

        try:
            process_output = subprocess.check_output(process, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            self.command_output_signal1.emit(process_output)
            self.append_to_output(process_output)
        except subprocess.CalledProcessError as e:
            # self.command_output_signal1.emit(f"Error: failed to show package content: {e.output}")
            self.append_to_output(f"Error: failed to get selections {e.output}")
        
    
    def unpacked_dpkg(self):
        unpack_package_input, ok= QInputDialog(self, "Unpack Package", "Enter the package name to unpack")
        if not ok or not unpack_package_input:
            QMessageBox.warning(self, "Error", "Package name input was canceled or empty.")
            return
        
        try: 
            unpack_command = f"dpkg --unpack {unpack_package_input}"
            
            unpack_process = subprocess.check_output(unpack_command, shell=True, stderr=subprocess.STDOUT,
                                                     universal_newlines=True)
            # self.command_output_signal1.emit(unpack_process)
            self.append_to_output(unpack_process)
        except subprocess.CalledProcessError as e :
            self.append_to_output(f"Error:\n failed to unpack package file {unpack_package_input}")
            # self.command_output_signal1.emit(f"Error:\n failed to unpack package file {unpack_package_input} ")

    
    def installed_dpkg(self):
        check_for_installed, ok = QInputDialog.getText(self, "Check Installed Package", "Enter the package name to check:")
        
        if not ok or not check_for_installed:
            QMessageBox.warning(self, "Error", "Package name input was canceled or empty.")
            return
        
        # passwd = self.prompt_for_password()
        # if passwd is not None:
        run_command = f"dpkg -L {check_for_installed}"
            
        thread = threading.Thread(target=self.check_installed_files, args=(run_command,))
        thread.start()
            
    
    def check_installed_files(self, run_command):
        try:
            check_installed_files_output = subprocess.check_output(run_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            # self.command_output_signal1.emit(check_installed_files_output)
            self.append_to_output(check_installed_files_output)
        except subprocess.CalledProcessError as e:
            # self.command_output_signal1.emit(f"Failed to check installed package files: {e.output}")
            self.append_to_output(f"Failed to check installed package files: {e.output}")
    
    def dpkg_installation(self):
        # Open file dialog to select .deb file
        deb_file, _ = QFileDialog.getOpenFileName(self, "Select .deb file", "", "Debian Package Files (*.deb)")
        
        # Check if the user selected a file
        if not deb_file:
            QMessageBox.warning(self, "No File Selected", "Please select a .deb file before proceeding.")
            return
        
        dpkg_passrd = self.prompt_for_password()
        if dpkg_passrd is not None:
            dpkg_command = f"sudo dpkg -i {deb_file}"
            
            thread = threading.Thread(target=self.dpkg_run_installation, args=(dpkg_command,))
            thread.start()
            
    def dpkg_run_installation(self, dpkg_command):
            
        try:
            # Proceed with installation using dpkg
            dpkg_output_command = subprocess.check_output(dpkg_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            # QMessageBox.information(self, "Success", f"The package {deb_file} has been installed successfully.")
            self.command_output_signal1.emit(dpkg_output_command)
            self.append_to_output(dpkg_output_command)
        except subprocess.CalledProcessError as e:
            # QMessageBox.critical(self, "Installation Error", f"Failed to install the package: {e}")
            self.append_to_output(f"Failed to install the package : {e.output}")
            # self.command_output_signal1.emit(f"Failed to install the package: {e.output}")
            
            
            
            
    def dpkg_remove(self):
        # Ask the user for the package name through an input dialog
        dpkg_to_remove, ok = QInputDialog.getText(self, 'Remove Package', 'Enter the package name to remove:')

        if not ok or not dpkg_to_remove:
            QMessageBox.warning(self, "Error", "Package name input was canceled or empty.")
            return

        # Prompt for the password
        password, ok = QInputDialog.getText(self, 'Password', 'Enter your password:', QLineEdit.Password)

        if not ok or not password:
            QMessageBox.warning(self, "Error", "Password input was canceled or empty.")
            return

        try:
            # Run dpkg remove command with sudo and provided password
            command = f" sudo -S dpkg -r {dpkg_to_remove}"
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT,  universal_newlines=True)
            self.set_monospace_font_dpkg_output()
            self.append_to_output(output)
            # self.output_display1.setText(output)
            
        except subprocess.CalledProcessError:
            # Show error message
            # QMessageBox.critical(self, "Error", f"Failed to remove package {dpkg_to_remove}.")
            self.append_to_output(f"Failed to remove package {dpkg_to_remove}")
            # print(f"Failed to remove package {dpkg_to_remove}.")
            
            # Display the error output in the QTextEdit
            # error_output = e.output
            # output_dialog = OutputDialog(error_output, self)
            # output_dialog.exec()


            
                    
    def dpkg_list(self):
            try:
                output = subprocess.check_output([ 'dpkg', '-l'], universal_newlines=True)
                self.set_monospace_font_dpkg_output()
                self.append_to_output(output)
                self.output_display1.setText(output)
            except subprocess.CalledProcessError as e:
                self.append_to_output(f"Failed to list installed packages: {e.output}")
                # print(f"Failed to list installed packages: {e}" )
                
                
                
                
    def dpkg_check_status(self):
        dpkg_check_package, ok = QInputDialog.getText(self, "Check Package", "Enter the package to check.")
        
        if not ok or not dpkg_check_package:
            QMessageBox.warning(self, "Error", "Package name input was canceled or empty.")
            return
        
        try:

            dpkg_check_command = f" dpkg -s {dpkg_check_package}" 
            check_dpkg_output = subprocess.check_output(dpkg_check_command, shell=True, stderr=subprocess.STDOUT,
                                                        universal_newlines=True)
            self.set_monospace_font_dpkg_output()
            self.append_to_output(check_dpkg_output)
            # self.output_display1.setText(check_dpkg_output)
        except subprocess.CalledProcessError:
            self.append_to_output(f"Failed to check the package: {check_dpkg_output}")
            # print(f"Failed to Check the package{dpkg_check_package}")
            
            
    def dpkg_configure(self):
        dpkg_configure_package, ok = QInputDialog.getText(self, "Package Configuration", "Enter the package to configure.")
        
        if not ok or not dpkg_configure_package:
            QMessageBox.warning(self, "Error", "Package name input was canceled or empty." )
            return
        
        
         # Prompt for the password
        password2 = self.prompt_for_password()
        if password2 is not None:
            dpkg_configure_command = f"echo {password2} | sudo dpkg --configure  {dpkg_configure_package}"
            
            
        thread = threading.Thread(target=self.run_dpkg_configure, args=(dpkg_configure_command,)) 
        thread.start()
        
        
    def run_dpkg_configure(self, dpkg_configure_command):        
        try:
            
            configure_output = subprocess.check_output(dpkg_configure_command, shell=True,
                                                       stderr=subprocess.STDOUT,
                                                       universal_newlines=True)
            self.append_to_output(configure_output)
            # self.command_output_signal1.emit(configure_output)
        except subprocess.CalledProcessError as e:
            self.append_to_output(f"Failed to configure the package:\n {e.output}")
            # self.command_output_signal1.emit(f"Failed to configure the package:\n {e.output}")
            
    def setup_signal(self):
        self.command_output_signal1.connect(self.update_output_for_dpkg)
    
    def set_dpkg_monospace(self):
        font = QFont('Source Code Pro')
        font.setStyleHint(QFont.Monospace)
        self.output_display1.setFont(font)
            
    def update_output_for_dpkg(self, text):
        self.set_dpkg_monospace()
        self.output_display1.setText(text)
    
    def set_monospace_font_dpkg_output(self):
        font = QFont("Source Code Pro", 10)  # Set to 10 due when listing the text will be large...
        font.setStyleHint(QFont.Monospace)
        self.output_display1.setFont(font) 
        
    
    def append_to_output(self, text):
        """Append text to the output display without clearing it"""
        self.output_display1.moveCursor(QTextCursor.End)  # Move cursor to the end
        self.output_display1.insertPlainText(text + '\n')  # Append the text
        
    def append_to_output1(self, text):
        self.sys_package_output.moveCursor(QTextCursor.End)
        self.sys_package_output.insertPlainText(text + '\n')
            
    
    # Helper function to prompt for password with QTimer
    def show_dpkg_dailog(self):
        # Create a dialog to input the password
        dialog = QDialog(self)
        dialog.setWindowTitle('Password Required')
        dialog.setFixedSize(330, 130)
        
        # Layout for the dialog
        dialog_layout = QVBoxLayout()
        
        # Password input field
        password_input = QLineEdit(dialog)
        password_input.setEchoMode(QLineEdit.Password)  # Hide password input
        password_input.setPlaceholderText("Enter your password")
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.button(QDialogButtonBox.Ok).setText("Authenticate")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        dialog_layout.addWidget(QLabel('Enter your password to proceed:'))
        dialog_layout.addWidget(password_input)
        dialog_layout.addWidget(buttons)
        
        dialog.setLayout(dialog_layout)
        
        if dialog.exec() == QDialog.Accepted:
            return password_input.text()
        else:
           return None
       
    
    def  gpkg_search_input(self):
         search_input = self.dpkg_search_input.text()
         if search_input:
            # self.output_display1.clear()
            
            try:   
                search_command = f" dpkg --search {search_input}"
                search_output = subprocess.check_output(search_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True )
                
                # self.output_display1.setText(search_output)
                self.append_to_output2(search_output)
            except subprocess.SubprocessError as e:
                self.append_to_output2(search_output)
                print(f"Failed to search: {e}")
                
    def append_to_output2(self, text):
        """Append text to the output display without clearing it"""
        self.output_display1.moveCursor(QTextCursor.End)  # Move cursor to the end
        self.output_display1.insertPlainText(text + '\n')  # Append the text
        self.set_monospace_font_dpkg_output()
        
        
                
        
    
     
        
        
###################################################################################################################

        #Show or hide environment input and directory button based on environment selection.

#####################################################################################################################


    def on_env_change(self):
        """Show or hide environment input and directory button based on environment selection."""
        selected_env = self.env_combo.currentText()
        if selected_env in ['Virtualenv', 'Conda']:
            self.env_name_label.show()
            self.env_name_input.show()
            self.dir_button.show()
        else:
            self.env_name_label.hide()
            self.env_name_input.hide()
            self.dir_button.hide()

    def select_directory(self):
        """Prompt the user to select a directory where the environment will be saved."""
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
        if selected_dir:
            self.selected_dir = selected_dir

    def save_settings(self):
        selected_env = self.env_combo.currentText()
        env_name = self.env_name_input.text()

        # Ensure an environment name is provided when Virtualenv or Conda is selected
        if selected_env in ['Virtualenv', 'Conda'] and not env_name:
            QMessageBox.warning(self, "Error", "Please provide a name for the virtual environment.")
            return

        # Ensure a directory is selected
        if selected_env in ['Virtualenv', 'Conda'] and not getattr(self, 'selected_dir', None):
            QMessageBox.warning(self, "Error", "Please select a directory to save the environment.")
            return

        if selected_env == "Virtualenv":
            self.create_virtualenv(env_name, self.selected_dir)
        elif selected_env == "Conda":
            self.create_conda_env(env_name, self.selected_dir)

        # Save the selected environment type to the parent
        if self.parent():
            self.parent().python_env = selected_env

        # Show a success message
        QMessageBox.information(self, "Settings Saved", f"Settings saved successfully for {selected_env}.")
        
        # Keep the window open after saving
        self.setVisible(True)

    def create_virtualenv(self, env_name, directory):
        """Create a Virtualenv environment in the selected directory."""
        try:
            subprocess.run(['virtualenv', f'{directory}/{env_name}'], check=True)
            QMessageBox.information(self, "Success", f"Virtual environment '{env_name}' created successfully in {directory}.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to create virtualenv: {e}")

    def create_conda_env(self, env_name, directory):
        """Create a Conda environment in the selected directory."""
        try:
            subprocess.run(['conda', 'create', '--prefix', f'{directory}/{env_name}', 'python=3.8', '-y'], check=True)
            QMessageBox.information(self, "Success", f"Conda environment '{env_name}' created successfully in {directory}.")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to create conda environment: {e}")

    # def activate_and_run_command(self, command):
    #     """Activate the virtual environment and run a command."""
    #     env_type = self.env_combo.currentText()
    #     env_name = self.env_name_input.text()
        
    #     if env_type == "Virtualenv":
    #         if env_name:
    #             activate_script = f'source {self.selected_dir}/{env_name}/bin/activate'
    #             full_command = f'{activate_script} && {command}'
    #             try:
    #                 subprocess.run(full_command, shell=True, check=True)
    #                 QMessageBox.information(self, 'Success', f'Command executed successfully in virtualenv.')
    #             except subprocess.CalledProcessError as e:
    #                 QMessageBox.critical(self, 'Error', f'Error executing command in virtualenv: {e}')
    #         else:
    #             QMessageBox.warning(self, 'Warning', 'Please enter a virtualenv name.')

    #     elif env_type == "Conda":
    #         if env_name:
    #             full_command = f'conda run -n {env_name} {command}'
    #             try:
    #                 subprocess.run(full_command, shell=True, check=True)
    #                 QMessageBox.information(self, 'Success', f'Command executed successfully in Conda environment.')
    #             except subprocess.CalledProcessError as e:
    #                 QMessageBox.critical(self, 'Error', f'Error executing command in Conda environment: {e}')
    #         else:
    #             QMessageBox.warning(self, 'Warning', 'Please enter a Conda environment name.')


    # def deactivate_environment(self):
    #     """Deactivate the current environment (Virtualenv or Conda)."""
    #     env_type = self.env_combo.currentText()
    #     try:
    #         if env_type == "Virtualenv":
    #             subprocess.run('deactivate', shell=True)
    #             QMessageBox.information(self, 'Success', 'Deactivated virtualenv.')
            
    #         elif env_type == "Conda":
    #             subprocess.run(['conda', 'deactivate'], check=True)
    #             QMessageBox.information(self, 'Success', 'Deactivated Conda environment.')
        
    #     except subprocess.CalledProcessError as e:
    #         QMessageBox.critical(self, 'Error', f'Error deactivating environment: {e}')
    
    def update_progress_bar(self, progress):
        # Update the progress bar based on the emitted progress (can be % or download size)
        if isinstance(progress, str):
            self.progress_bar.setFormat(progress)  # Set the text format for MB downloaded
        else:
            self.progress_bar.setValue(progress)  # 
    
    
    def install_modules(self):
        """Install modules into the activated environment."""
        dialog = ModuleInputDialog(self)
        if dialog.exec() == QDialog.Accepted:
            module_name = dialog.input_field.text() # Access the text directly
            
            if module_name:
                env_type = self.env_combo.currentText()
                env_name = self.env_name_input.text()

                if env_type == "Virtualenv" and  env_name:
                    
                    pip_path = f'{self.selected_dir}/{env_name}/bin/pip'
                        
                        
                    # Reset progress bar before starting installation
                    self.progress_bar.setValue(0)
                    self.downloading_status.setVisible(True)

                    # Create and start the worker thread for installation
                    self.worker = InstallWorker(pip_path, module_name)
                    self.worker.progress_signal.connect(self.update_progress_bar)  # Connect signal to update method
                    self.worker.start()  # Start the worker thread

                    # Optionally handle completion of the thread
                    self.worker.finished.connect(lambda: self.on_installation_complete(module_name))
                else:
                    QMessageBox.warning(self, 'Warning', 'Please enter a virtualenv name.')
                       
       


            elif env_type == "Conda" and env_name:
                # For Conda, use subprocess to install with progress tracking
                conda_command = f"conda install -n {env_name} {module_name} -y"

                try:
                    # Run the subprocess with output capture
                    process = subprocess.Popen(
                        conda_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )

                    self.progress_bar.setValue(0)
                    self.downloading_status.setVisible(True)
                    self.track_conda_installation_progress(process)  # Track installation progress

                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(self, 'Error', f'Error installing module in Conda environment: {e}')
                    self.progress_bar.setValue(0)
            else:
                QMessageBox.warning(self, 'Warning', 'Please enter a valid environment name.')

        else:
            QMessageBox.warning(self, 'Warning', 'Please provide a module name.')

    def track_conda_installation_progress(self, process):
        """Track the installation progress for Conda installation."""
        progress = 0
        while True:
            output = process.stdout.readline()
            
            if output == "" and process.poll() is not None:
                break

            if output:
                print(output.strip())  # Print for debugging

                # You can implement logic to increment progress based on output
                if "Downloading" in output:
                    progress += 10  # Example increment, customize based on actual output
                    self.progress_bar.setValue(progress)

        self.progress_bar.setValue(100)  # Ensure the progress bar is fully filled when done
        self.on_installation_complete("Module")  # Call completion handler



            

       # Method to handle the completion of the installation
    def on_installation_complete(self, module_name):
        """Called when the installation completes."""
        self.downloading_status.setVisible(False)  # Hide the downloading label
        QMessageBox.information(self, 'Success', f'Module {module_name} installed in virtualenv.')
        


if __name__ == '__main__':
    window = DebugWithDpkg()
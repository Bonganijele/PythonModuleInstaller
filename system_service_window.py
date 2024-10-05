from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QLabel, QMessageBox, QComboBox, QProgressBar,
                               QTextEdit, QDialog, QMenuBar, QMenu, QSpacerItem, QSizePolicy,QToolTip, QScrollArea, QStackedWidget,
                               QFormLayout, QCheckBox, QInputDialog, QDialogButtonBox, QFileDialog, QStyle, QFontDialog,
                               QGroupBox, QGridLayout, QTabWidget, QFrame)
from PySide6.QtGui import QIcon, QAction,  QCursor, QShowEvent, QColor, QPainter, QFont, QTextCursor
from PySide6.QtCore import (QSize, QThread, Signal, QEvent, QTimer,
                            QPoint, Slot, QSettings,QProcess, QMetaObject,
                            Qt, Q_ARG, QRect)
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



class FixedSizeInputDialog(QInputDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(500, 600)


class PackageSystemService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Services")
        self.setFixedSize(800, 660)
        
        # Main Layout
        main_layout = QVBoxLayout()

        # Title Label
        title_label = QLabel("System Service Management")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        main_layout.addWidget(title_label)
        
        # Tab Widget for grouping buttons
        tab_widget = QTabWidget()
        
        # Control Tab
        control_tab = QWidget()
        control_layout = QGridLayout()
        
        control_buttons = [
            ("Start", self.enable_systemctl, "Start Systemctl Service"),
            ("Stop", self.disable_systemctl, "Stop Systemctl Service"),
            ("Restart", self.restart_systemctl, "Restart Systemctl Service"),
            ("Status", self.status_systemctl, "Systemctl Status Service")
        ]
        self.add_buttons_to_layout(control_buttons, control_layout)
        
        control_tab.setLayout(control_layout)
        tab_widget.addTab(control_tab, "Control")

        # Status Tab
        status_tab = QWidget()
        status_layout = QGridLayout()

        status_buttons = [
            ("All Services", self.list_systemctl_all_services, "List All Systemctl Services"),
            ("Unit Files", self.list_unit_files_services, "List Unit Files Services"),
            ("Active", self.active_systemctl, "Check Active Services"),
            ("Inactive", self.inactive_systemctl, "Check Inactive Services"),
            ("Running", self.running_systemctl, "Check Running Services"),
            ("Failed", self.failed_systemctl, "Check Failed Services"),
        ]
        self.add_buttons_to_layout(status_buttons, status_layout)
        
        status_tab.setLayout(status_layout)
        tab_widget.addTab(status_tab, "Status")

        main_layout.addWidget(tab_widget)

        # Output Section
        output_group_box = QGroupBox("Service Output")
        output_group_box.setStyleSheet("font-size: 14px;")
        output_layout = QVBoxLayout(output_group_box)
        
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Enter service to search...")
        self.search_input.setFixedHeight(29)
        self.search_input.setFocus()
        self.search_input.returnPressed.connect(self.input_search)
        
        
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton()
        self.search_btn.setIcon(QIcon('icons/search.png'))
        self.search_btn.clicked.connect(self.input_search)
        search_layout.addWidget(self.search_btn)
        
        
        search_layout.addWidget(self.search_btn)
        
        output_layout.addLayout(search_layout)    
        
        
    
        self.output_display_system_service = QTextEdit(self)
        self.output_display_system_service.setFixedHeight(310)
        
        self.output_display_system_service.setReadOnly(True)
        output_layout.addWidget(self.output_display_system_service)
        
        
      

        main_layout.addWidget(output_group_box)
        
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self.clear_output)
        main_layout.addWidget(self.clear_btn)

        self.setLayout(main_layout)
    
    
    def clear_output(self):
        self.output_display_system_service.clear()
            
    
    def input_search(self):
        search_input = self.search_input.text()
        if search_input:
            try:
                # Search command to list dependencies of the service
                search_command = f"systemctl list-dependencies {search_input}"
                search_output = subprocess.check_output(search_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
                
               
                self.set_monospace_font_dpkg_output()
                self.append_to_output(search_output)
            except subprocess.CalledProcessError as e:
                self.append_to_output(f"Failed to search: {e}")
        
        self.search_input.clear()       

  

    def append_to_output(self, text):
        """Append text to the output display without clearing it"""
        self.output_display_system_service.moveCursor(QTextCursor.End)  # Move cursor to the end
        self.output_display_system_service.insertPlainText(text + '\n')  # Append the text
            
    
    
    def set_monospace_font_dpkg_output(self):
        font = QFont("Source Code Pro")  
        font.setStyleHint(QFont.Monospace)
        self.output_display_system_service.setFont(font)  

    def add_buttons_to_layout(self, buttons, layout):
        """ Helper function to add buttons to a layout with consistent styling """
        for idx, (text, func, tooltip) in enumerate(buttons):
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.clicked.connect(func)
            btn.setFixedWidth(150)
            layout.addWidget(btn, idx // 2, idx % 2)  # Arrange in a 2-column grid
            
        
        
        self.last_password_time = None
        self.password_cache_duration = 15 * 60  # 15 minutes in seconds
        self.cached_password = None  # Store the password after first authentication
    
    def verify_password(self, password):
        try:
            command =['sudo', '-S', '-k', 'true']
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout , stderr = process.communicate(input=password + '\n')
            
            return process.returncode == 0
        except subprocess.CalledProcessError:
            return False   
            
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
    
    def status_systemctl(self):
        
        # dialog1 = QInputDialog(self)
        # dialog1.setWindowTitle("Status Service")
        # dialog1.setLabelText("Enter the service name")
        # dialog1.setFixedSize(400, 200)
        
        service_name, ok = FixedSizeInputDialog.getText(self, "Status Service", "Enter the service name")
        print(f'{service_name}')
        
        if not ok or not service_name:
            QMessageBox.warning(self, "Error", "Service name input was canceled or empty.")
            return

        password = self.prompt_for_password()
        if password is not None:
            command_status = f"echo {password} | sudo -S systemctl status {service_name}"
            
            try:
                subprocess.check_output(command_status, shell=True, stderr=subprocess.STDOUT, 
                                                universal_newlines=True)
                self.set_monospaced_font()
            except subprocess.CalledProcessError as e:
                # Capture both stdout and stderr
                self.output_display_system_service.setText(f'Status for service {service_name}\nError: {e.output}')
          
    def restart_systemctl(self):
        
        
        restart_systemd, ok = FixedSizeInputDialog.getText(self, 'Restart Service', 'Enter the service name' )
        
        if not ok or not restart_systemd:
            QMessageBox.warning(self, "Error", "Service name input was canceled or empty.")
            return
        
        restart_systemd_sudo_passwd = self.prompt_for_password()
        if restart_systemd_sudo_passwd is not None:
            command = f"sudo systemctl restart {restart_systemd}"
            return
        
        try:
                
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            self.set_monospaced_font()
            self.output_display_system_service.setText(process)
            print(f'outcome error: {process}')

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to restart the service {restart_systemd} \nError: {str(e)}")    
    
        
    
    def enable_systemctl(self):
        
        
        enable_systemd, ok = FixedSizeInputDialog.getText(self, "Start Service", "Enter the service name")
        
        if not ok or not enable_systemd:
            QMessageBox.warning(self, "Error", "Service name input was canceled or empty.")
            return
        
     
        enable_systemd_sudo_passwd = self.prompt_for_password()
        if enable_systemd_sudo_passwd is not None:
            command = f"echo {enable_systemd_sudo_passwd} | sudo -S systemctl start {enable_systemd}"
        else:
            
            return
                    
        try:
            # Start the service
            # enable_systemd_commd = f"echo {enable_systemd_sudo_passwd} | sudo -S systemctl start {enable_systemd}"
            process_start = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            _, enable_systemd_error = process_start.communicate()

            if process_start.returncode != 0:
                self.set_monospaced_font()
                self.output_display_system_service.setPlainText(f"Failed to start the service {enable_systemd}.\nError: {enable_systemd_error}")
                return

            # Get the status of the service
            status_commd = f"echo {enable_systemd_sudo_passwd} | sudo -S systemctl status {enable_systemd}"
            process_status = subprocess.Popen(status_commd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            enable_systemd_output, enable_systemd_error = process_status.communicate()

            if process_status.returncode == 0:
                self.set_monospaced_font()
                self.output_display_system_service.setPlainText(enable_systemd_output)
            else:
                self.output_display_system_service.setPlainText(f"Failed to get the status of the service {enable_systemd}.\nError: {enable_systemd_error}")
        
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to enable the service {enable_systemd}.\nError: {str(e)}")
            
    
    def disable_systemctl(self):
        # dialog = FixedSizeInputDialog()
        stop_systemd, ok = FixedSizeInputDialog.getText(self, "Stop Service", "Enter the service name")
        
        if not ok or not stop_systemd:
            QMessageBox.warning(self, "Error", "Service name input was canceled or empty.")
            return
    
        disable_systemd_sudo_passwd = self.prompt_for_password()
        if disable_systemd_sudo_passwd is not None:
            command = f"echo {disable_systemd_sudo_passwd} | sudo -S systemctl stop {stop_systemd}"
        else:
            
            return
        
        try:
           
            process_stop = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _, stop_systemd_error = process_stop.communicate()

            if process_stop.returncode != 0:
                self.set_monospaced_font()
                self.output_display_system_service.setPlainText(f"Failed to stop the service {stop_systemd}.\nError: {stop_systemd_error}")
                return

            # Get the status of the service
            status_commd = f" sudo -S systemctl status {stop_systemd}"
            process_status = subprocess.Popen(status_commd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            status_output, status_error = process_status.communicate()

            if process_status.returncode == 0:
                
                self.set_monospaced_font()
                self.output_display_system_service.setPlainText(status_output)
            else:
                self.output_display_system_service.setPlainText(f"Failed to get the status of the service {stop_systemd}.\nError: {status_error}")
        
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to stop the service {stop_systemd}.\nError: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred.\nError: {str(e)}")

    
     
    # Setting monospaced font for QTextEdit
    def set_monospaced_font(self):
        font = QFont("Source Code Pro")  # You can also use "Courier New", "Consolas", etc.
        font.setStyleHint(QFont.Monospace)
       
        self.output_display_system_service.setFont(font)
        
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

    def list_unit_files_services(self):
        try:
            # Run the systemctl list-unit-files command
            command_output = subprocess.check_output(['systemctl', 'list-unit-files'], universal_newlines=True)
            
            # Set monospaced font before displaying the output
            self.set_monospaced_font()

            # Display the output in the QTextEdit
            self.output_display_system_service.setText(command_output)

        except subprocess.CalledProcessError as e:
            print(f"Error running systemctl list-unit-files: {e}")
            
            
            
    def list_systemctl_all_services(self):
        try:
            command_output = subprocess.check_output(['systemctl', 'list-units', '--type=service'], universal_newlines=True)
            
            self.set_monospaced_font()
            
            self.output_display_system_service.setText(command_output)
        except subprocess.CalledProcessError as e:
            print(f"Error list  systemctl list-units service {e} ") 
    
    def active_systemctl(self):
        try:
            command_output = subprocess.check_output(['systemctl', 'list-units', '-a', '--state=active'], universal_newlines=True)
            self.output_display_system_service.setText(command_output)
            self.set_monospaced_font()
            
        except subprocess.CalledProcessError as e:
            print(f"Error list  systemctl list-units  active services {e} ") 
            
    def inactive_systemctl(self):
        try:
            command_output = subprocess.check_output(['systemctl', 'list-units', '-a', '--state=inactive'], universal_newlines=True)
            self.set_monospaced_font()
            self.output_display_system_service.setText(command_output)
        except subprocess.CalledProcessError as e:
            print(f"Error list  systemctl list-units inactive services {e} ") 
    
    def running_systemctl(self):
        try:
            command_output = subprocess.check_output(['systemctl', 'list-units', '--type=service', '--state=running'], universal_newlines=True)
            self.set_monospaced_font()
            self.output_display_system_service.setText(command_output)
        except subprocess.CalledProcessError as e:
            print(f"Error list  systemctl list-units running services {e} ") 
    
    def failed_systemctl(self):
        try:
            command_output = subprocess.check_output(['systemctl', 'list-units', '--type=service', '--state=failed'], universal_newlines=True)
            self.set_monospaced_font()
            self.output_display_system_service.setText(command_output)
        except subprocess.CalledProcessError as e:
            print(f"Error list  systemctl list-units running services {e} ") 
                        
        
        
    

from typing import Union
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QLabel, QMessageBox, QComboBox, QProgressBar,
                               QTextEdit, QDialog, QMenuBar, QMenu, QSpacerItem, QSizePolicy,QToolTip, QScrollArea, QStackedWidget,
                               QFormLayout, QCheckBox, QInputDialog, QDialogButtonBox, QFileDialog,  QFontDialog, 
                                
                               QStyle, QGroupBox, QGridLayout, QTabWidget, QFrame)
from PySide6.QtGui import QIcon, QAction,  QCursor, QShowEvent, QColor, QPainter, QFont, QTextCursor
from PySide6.QtCore import (QSize, QThread, Signal, QEvent, QTimer,
                            QPoint, Slot, QSettings,QProcess,
                            QMetaObject, Qt, Q_ARG, QRect)
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

################################################################

# PYTOGGLE QCHECKBOX FOR THE INTERNET INTERFACE QDIALOG

#####################################################################################################################



class PyToggle(QCheckBox):
    def __init__(self, width=50, bg_color="lightgrey", circle_color="grey", active_color="#00BCff"):
        super().__init__()

        self.setFixedSize(width, 25)
        self.setCursor(Qt.PointingHandCursor)

        self._bg_color = bg_color
        self._circle_color = circle_color
        self._active_color = active_color

        # Connect state change signal
        self.stateChanged.connect(self.debug)

    def debug(self):
        print(f"Status: {self.isChecked()}")

    def hitButton(self, pos: QPoint):
        # Check if the click is within the toggle button's rectangle
        return self.contentsRect().contains(pos)

    # Corrected paintEvent method
    def paintEvent(self, event):
        # Set painter
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Set no pen for drawing
        p.setPen(Qt.NoPen)

        # Define the rectangle for drawing
        rect = QRect(0, 0, self.width(), self.height())

        # Background color
        if self.isChecked():
            p.setBrush(QColor(self._active_color))
        else:
            p.setBrush(QColor(self._bg_color))

        # Draw the rounded rectangle for the toggle background
        p.drawRoundedRect(0, 0, rect.width(), self.height(), self.height() / 2, self.height() / 2)

        # Draw the circle (toggle knob)
        circle_x = rect.width() - self.height() if self.isChecked() else 0
        p.setBrush(QColor(self._circle_color))
        p.drawEllipse(circle_x, 0, self.height(), self.height())

        p.end()
    


class SystemPackages(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(900, 600)
        
        #Initialize UI elements, including the checkbox and history display
        self.record_history_checkbox = QCheckBox("Record History")
        self.history_display = QLabel("History state will be displayed here.")
        
        # restotre check box state on startup
        self.load_checkbox_state()
        
        #Connecting the checkbox to func that handles history saving
        self.record_history_checkbox.stateChanged.connect(self.dont_save_history)
        
        self.last_password_time = None
        self.password_cache_duration = 15 * 60  # 15 minutes in seconds
        self.cached_password = None  # Store the password after first authentication
        

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Group Box for System Settings
        system_group_box = QGroupBox("System Settings")
        system_layout = QVBoxLayout()

        # Font style for buttons and labels
        font = QFont()
        font.setPointSize(10)

        # Buttons for history and password management
        history_button_layout = QHBoxLayout()

        # List History Button
        self.list_history_btn = QPushButton("List History")
        self.list_history_btn.setFont(font)
        self.list_history_btn.clicked.connect(self.list_history)
        history_button_layout.addWidget(self.list_history_btn)

        # Clear History Button
        self.clear_history_btn = QPushButton("Clear History")
        self.clear_history_btn.setFont(font)
        self.clear_history_btn.clicked.connect(self.clear_history)
        history_button_layout.addWidget(self.clear_history_btn)

        # Change System Password Button
        self.change_password_btn = QPushButton("Save History")
        self.change_password_btn.setFont(font)
        self.change_password_btn.clicked.connect(self.save_history_to_file)
        history_button_layout.addWidget(self.change_password_btn)

        system_layout.addLayout(history_button_layout)

        # Checkbox for recording terminal history
        
        self.record_history_checkbox = QCheckBox("Do not record terminal history")
        self.record_history_checkbox.setFont(font)
        self.record_history_checkbox.clicked.connect(self.dont_save_history)
        self.record_history_checkbox.setChecked(False)  # Default unchecked
        system_layout.addWidget(self.record_history_checkbox)
        
        # History Display
        self.history_display = QTextEdit()
        self.history_display.setFixedHeight(210)
        self.history_display.setReadOnly(True)
        system_layout.addWidget(self.history_display)
        
        system_group_box.setLayout(system_layout)
        main_layout.addWidget(system_group_box)
        
        
        
        main_layout.addSpacerItem(QSpacerItem(5, 5, QSizePolicy.Minimum, QSizePolicy.Expanding))
        

        # System Health Monitoring Section
        health_group_box = QGroupBox("System Health Monitoring")
        health_layout = QVBoxLayout()

        # Horizontal Layout for System Health Labels
        health_labels_layout = QHBoxLayout()

        # Labels for CPU, Memory, and Disk Usage
        self.cpu_usage_label = QLabel("CPU Usage: 0%")
        self.memory_usage_label = QLabel("Memory Usage: 0%")
        self.swap_mem_label = QLabel("Swap Memory")
        self.disk_usage_label = QLabel("Disk Usage: 0%")

        health_labels_layout.addWidget(self.cpu_usage_label)
        health_labels_layout.addWidget(self.memory_usage_label)
        health_labels_layout.addWidget(self.swap_mem_label)
        health_labels_layout.addWidget(self.disk_usage_label)
        

        health_layout.addLayout(health_labels_layout)

        # Disk Management Button
        self.disk_management_btn = QPushButton("Manage Disk Space")
        self.disk_management_btn.setFont(font)
        self.disk_management_btn.clicked.connect(self.manage_disk_space)
        health_layout.addWidget(self.disk_management_btn)

        health_group_box.setLayout(health_layout)
        main_layout.addWidget(health_group_box)

        # Placeholder for other settings group
        irrelevant_group_box = QGroupBox("Other Settings")
        irrelevant_layout = QVBoxLayout()

        # Add more buttons related to other settings
        
        self.report_btn = QPushButton("Problem Reporting")
        self.report_btn.setFont(font)
        self.report_btn.clicked.connect(self.report_dialog)
        irrelevant_layout.addWidget(self.report_btn)
        
        

        self.network_settings_btn = QPushButton("Network Settings")
        self.network_settings_btn.setFont(font)
        self.network_settings_btn.clicked.connect(self.network_settings)
        irrelevant_layout.addWidget(self.network_settings_btn)
        
        

        irrelevant_group_box.setLayout(irrelevant_layout)
        main_layout.addWidget(irrelevant_group_box)

        # Add padding and spacing to make the layout more spacious
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        

        # Setup logging
        self.setup_logging()

        # Update system health on initialization
        self.update_system_health()
    
    
    def input_search(self):
        search_input = self.search_input.text()
        if search_input:
            try:
                # Search command to list dependencies of the service
                search_command = f"systemctl list-dependencies {search_input}"
                search_output = subprocess.check_output(search_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
                
                # Append the search result to the output display without clearing
                self.set_monospace_service_search()
                self.append_to_output(search_output)
            except subprocess.CalledProcessError as e:
                self.append_to_output(f"Failed to search: {e}")
        
        self.search_input.clear()       

   
    def set_monospace_service_search(self):
        font = QFont("Source Code Pro")
        font.setStyleHint(QFont.Monospace)
        self.output_display_system_service.setFont(font)

    def append_to_output(self, text):
        self.output_display_system_service.moveCursor(QTextCursor.End)
        self.output_display_system_service.insertPlainText(text + '\n')
        
                
        
    
    def setup_logging(self):
        logging.basicConfig(filename='system_packages.log', level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info('System Packages Dialog Initialized')

    def update_system_health(self):
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()
        disk = psutil.disk_usage('/')

        self.cpu_usage_label.setText(f"CPU Usage: {cpu_usage}%")
        self.memory_usage_label.setText(f"Memory Usage: {memory.percent}%")
        self.swap_mem_label.setText(f"Swap Memory: {swap_mem.percent}%")
        self.disk_usage_label.setText(f"Disk Usage: {disk.percent}%")

    def manage_disk_space(self):
        # Create a dialog to manage disk space
        dialog = QDialog(self)
        dialog.setWindowTitle("Disk Space Management")
        dialog.setFixedSize(400, 300)
        
        # Layout for the dialog
        layout = QVBoxLayout()

        # Display current disk usage
        disk_usage = shutil.disk_usage('/')
        disk_info = (
            f"Total: {disk_usage.total / (1024 ** 3):.2f} GB\n"
            f"Used: {disk_usage.used / (1024 ** 3):.2f} GB\n"
            f"Free: {disk_usage.free / (1024 ** 3):.2f} GB\n"
        )
        disk_info_label = QLabel(f"<b>Disk Usage:</b><br>{disk_info}")
        layout.addWidget(disk_info_label)
        
        font = QFont()
        font.setPointSize(10)
        
        # Button to clean up temporary files
        cleanup_button = QPushButton("Clean Up Temporary Files")
        cleanup_button.clicked.connect(self.cleanup_temp_files)
        layout.addWidget(cleanup_button)
        
        self.tmp_sudo_chbox = QCheckBox("Run Clean Up Temporary Files as Sudo", self)
        self.tmp_sudo_chbox.setFont(font)
        self.tmp_sudo_chbox.setChecked(False)
        # self.tmp_sudo_chbox.clicked.connect(self.tmp_sudo_chbox)
        layout.addWidget(self.tmp_sudo_chbox)
        
        # Button to delete specific files
        delete_button = QPushButton("Delete Specific Files")
        delete_button.clicked.connect(self.delete_files)
        layout.addWidget(delete_button)
        
        choose_button = QPushButton("Choose Files To Delete")
        choose_button.clicked.connect(self.choose_button_to_del)
        layout.addWidget(choose_button)
        
        # Add layout to dialog
        dialog.setLayout(layout)
        dialog.exec()

    def cleanup_temp_files(self):
        temp_dirs = ['/tmp', '/var/tmp/']
        
        for temp_dir in temp_dirs:
            # Check if the directory exists before deletion
            if os.path.exists(temp_dir):
                
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    
                # If the 'sudo' checkbox is checked
                if self.tmp_sudo_chbox.isChecked():
                    tmp_sudo_dialog = QMessageBox()
                    tmp_sudo_dialog.setIcon(QMessageBox.Warning)
                    tmp_sudo_dialog.setWindowTitle("Sudo Required")
                    tmp_sudo_dialog.setFixedSize(330, 130)
                    tmp_sudo_dialog.setText(f"The temporary files will be deleted with 'sudo' in {item_path}.")    
                    tmp_sudo_dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                    
                    if tmp_sudo_dialog.exec() == QMessageBox.Cancel:
                        return
                    
                    tmp_sudo_passwrd = self.prompt_for_password()
                    if tmp_sudo_passwrd is not None:
                        # Construct the sudo deletion command
                        command_to_del = f"echo {tmp_sudo_passwrd} | sudo -S rm -rf {item_path}"
                else:
                    # Non-sudo deletion
                    command_to_del = f"rm -rf {item_path}"
                
                
                try:
                    subprocess.check_output(command_to_del, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
                    print(f"Delete: {item_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to clean up temporary files in {temp_dir}: {e}")
            else:
                print(f"{item_path} does not exist.")
        
        QMessageBox.information(self, "Clean Up", "Temporary files cleaned up successfully.")

    def delete_files(self):
        # Get a file or directory to delete from the user
        file_to_delete, ok = QInputDialog.getText(self, "Delete File", "Enter file or directory path to delete:")
        
        if ok and file_to_delete:
            if os.path.exists(file_to_delete):
                try:
                    # Delete the specified file or directory
                    if os.path.isfile(file_to_delete):
                        os.remove(file_to_delete)
                    elif os.path.isdir(file_to_delete):
                        shutil.rmtree(file_to_delete)
                    
                    QMessageBox.information(self, "Delete File", "File or directory deleted successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete file or directory: {e}")
            else:
                QMessageBox.warning(self, "Delete File", "The specified file or directory does not exist.")
                
                
    def choose_button_to_del(self):
        """Prompt the user to select a directory where the environment will be saved."""
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
        if selected_dir:
            self.selected_dir = selected_dir
            
          

            
        if os.path.exists(selected_dir):
            try:
                if os.path.isfile(selected_dir):
                    os.remove(selected_dir)
                elif os.path.isdir(selected_dir):
                    shutil.rmtree(selected_dir)
                QMessageBox.information(self, "Delete File", "File or directory deleted successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file or directory: {e}")
        else:
            QMessageBox.warning(self, "Delete File", "The specified file or directory does not exist." )
            
     
       
    # Function placeholders
    def list_history(self):
        history_path = os.path.expanduser('~/.bash_history')
        
        try:
            if os.path.exists(history_path):
                command_output = subprocess.check_output(['cat', history_path], universal_newlines=True)
                self.set_history_monospace()
                self.history_display.setText(command_output)
            else:
                self.history_display.setText(f"No history file found at {history_path}.")
        except subprocess.CalledProcessError as e:
            self.history_display.setText(f"Error fetching history: {e}")

    def set_history_monospace(self):
        font = QFont("Source Code Pro")
        font.setStyleHint(QFont.Monospace)
        self.history_display.setFont(font)
        
        
    def clear_history(self):
        try:
            # Get the user's shell environment
            shell = os.getenv('SHELL')

            # Check if the shell is bash
            if shell and 'bash' in shell:
                # Clear the bash history by clearing the ~/.bash_history file
                with open(os.path.expanduser('~/.bash_history'), 'w'):
                    pass  # Empty the file

                # Update the history display
                self.set_history_monospace()
                self.history_display.setText("History Cleared.")
            else:
                self.history_display.setText("History clearing is disabled or not a bash shell.")
        except Exception as e:
            self.history_display.setText(f"Error clearing history: {e}")

     
             
    def save_history_to_file(self):
        
       try:
           shell = os.getenv('SHELL')
           if shell.endswith('bash'):
               history_file = os.path.expanduser('~/.bash_history')
           elif shell.endswith('zsh'):
               history_file = os.path.expanduser('~/.bash_history')
            
           else:
               QMessageBox.warning(self, "Shell Not Supported", "This function currently supports Bash and Zsh only.")
               return
           
           save_file, _ = QFileDialog.getSaveFileName(self, "Save Command History", "", "Text Files (*.txt);; All Files (*)")
           if not save_file:
            return

           shutil.copy(history_file, save_file)
           
           QMessageBox.information(self, "History Saved", f"Command history saved to {save_file}")
       except Exception as e:
           QMessageBox.critical(self, "Error", f"Failed to save command history: {e}")           
           
            
    def dont_save_history(self):
        try:
            # Load and save the checkbox state using QSettings (persistent)
            settings = QSettings("pythonModuleInstaller", "pythonModuleInstallerSettings")
            
            # Check the state of the checkbox
            if self.record_history_checkbox.isChecked():
                # Disable history saving by unsetting HISTFILE
                subprocess.call(['bash', '-c', 'unset HISTFILE'])
                self.set_history_monospace()
                self.history_display.setText("History saving disabled successfully.")
         
                print("History display updated")
                
                # Save the checkbox state as 'checked'
                settings.setValue("record_history_checkbox", True)
            else:
                self.history_display.setText("History saving remains enabled.")
                
                # Save the checkbox state as 'unchecked'
                settings.setValue("record_history_checkbox", False)

        except subprocess.SubprocessError as e:
            self.history_display.setText(f"Error unsetting history: {e}")

    # Function to restore the state of the checkbox on startup
    def load_checkbox_state(self):
        settings = QSettings("pythonModuleInstaller", "pythonModuleInstallerSettings")
        checkbox_state = settings.value("record_history_checkbox", False, type=bool)  # Default is unchecked
        print(f"Loading checkbox state: {checkbox_state}")
        self.record_history_checkbox.setChecked(checkbox_state)

    def closeEvent(self, event):
        print("Window is closing. Saving checkbox state...")
        settings = QSettings("pythonModuleInstaller", "pythonModuleInstallerSettings")
        settings.setValue("record_history_checkbox", self.record_history_checkbox.isChecked())
        print(f"Saved checkbox state {self.record_history_checkbox.isChecked()}")
        event.accept()


                
###################################################################################################################
# THE NETWORK SETTING INTERFACE DIALOG
#####################################################################################################################
                    
            
            
    
     
    def network_settings(self):
        # Create a dialog for network settings
        dialog = QDialog(self)
        dialog.setWindowTitle("Network Settings")
        dialog.setFixedSize(600, 380)

        layout = QVBoxLayout()

        # Network Interface Info
        network_info_label = QLabel("<b>Network Interfaces:</b>")
        layout.addWidget(network_info_label)

        # Fetch network interfaces
        self.interfaces = psutil.net_if_addrs()
        
        # Create a combo box to select network interfaces
        self.network_combo = QComboBox()
        for iface in self.interfaces:
            self.network_combo.addItem(iface)
        self.network_combo.currentIndexChanged.connect(self.update_network_info)
        layout.addWidget(self.network_combo)
        
        # Show network interface info
        self.network_info_display = QLabel()
        layout.addWidget(self.network_info_display)
        
        
        layout.addSpacerItem(QSpacerItem(5, 5, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # # Toggle Button
        # self.toggle_button = QPushButton("Enable Interface")
        # self.toggle_button.clicked.connect(self.toggle_network_interface)
        # layout.addWidget(self.toggle_button)
        

        toggle_layout = QHBoxLayout()
        
        toggle_label = QLabel("Enable the network interface")
        toggle_layout.addWidget(toggle_label)
        
        self.toggle = PyToggle()
        self.toggle.clicked.connect(self.toggle_network_interface)
        toggle_layout.addWidget(self.toggle)
        
        layout.addLayout(toggle_layout)
        
        
        # self.toggle_button1 = QPushButton("Disable Interface")
        # self.toggle_button1.clicked.connect(self.toggle_network_interface1)
        # layout.addWidget(self.toggle_button1)

        dialog.setLayout(layout)
        dialog.exec()
        

###################################################################################################################
# REPORT DIALOG
#####################################################################################################################


                
    def report_dialog(self): 
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle("Problem Reporting")
        report_dialog.setFixedSize(390, 200)
        
        report_dialog_layout = QVBoxLayout() # Corrected HTML with an anchor tag at the end 
        
        report_label = QLabel("""To send a report, include the issue details, system<br> 
                              information, and any logs or screenshots to help<br>
                              diagnose the problem. <a href="https://www.example.com">Learn more</a> 
                            """) 
        report_label.setOpenExternalLinks(True) 
        
        report_dialog_layout.addWidget(report_label)
        report_dialog_layout.addSpacerItem(QSpacerItem(9, 5, QSizePolicy.Minimum, QSizePolicy.Expanding)) 
        report_dialog.setLayout(report_dialog_layout) 
        report_dialog.exec()
        
        

    def update_network_info(self):
        iface = self.network_combo.currentText()
        if iface:
            info = self.get_network_info(iface)
            self.network_info_display.setText(info)

    def get_network_info(self, iface):
        try:
            # IPv4 and IPv6 addresses
            # Retrieve IPv4 and IPv6 addresses
            cmd = f"ip -br addr show {iface}"
            output = subprocess.check_output(cmd, shell=True, text=True)

            ipv4_addrs = re.findall(r'\binet\s+(\d{1,3}(?:\.\d{1,3}){3})\b', output)

            ipv6_addrs = re.findall(r'\binet6\s+([a-fA-F0-9:]+)\b', output)

                
            addrs = psutil.net_if_addrs()[iface]
            # ipv4_addrs = [addr.address for addr in addrs if addr.family == psutil.AF_INET]
            # ipv6_addrs = [addr.address for addr in addrs if addr.family == psutil.AF_INET6]
            hw_addr = next((addr.address for addr in addrs if addr.family == psutil.AF_LINK), "N/A")

            # Link speed
            speed = self.get_link_speed(iface)

            # Default route and DNS
            default_route = self.get_default_route()
            dns_servers = self.get_dns_servers()
            
            return (f"<div style='width: 50%; margin: 0 auto; text-align: center; padding: 400px'>"
                
                f"<b>Interface:</b> {iface}<br>"
                f"<b>Link Speed:</b> {speed}<br>"
                f"<b>IPv4 Addresses:</b> {', '.join(ipv4_addrs) or 'N/A'}<br>"
                f"<b>IPv6 Addresses:</b> {', '.join(ipv6_addrs) or 'N/A'}<br>"
                
                f"<b>Hardware Address:</b> {hw_addr}<br>"
                f"<b>Default Route:</b> {default_route}<br>"
                f"<b>DNS Servers:</b> {', '.join(dns_servers) or 'N/A'}"
                
                f"</div>")
        except Exception as e:
            return f"Error retrieving network information: {e}"
            
                
    def get_link_speed(self, iface):
        try:
            result = subprocess.check_output(['ethtool', iface], universal_newlines=True)
            for line in result.splitlines():
                if 'Speed:' in line:
                    return line.split(':')[1].strip()
            return "Unknown"
        except subprocess.CalledProcessError:
            return "Error"

    def get_default_route(self):
        try:
            result = subprocess.check_output(['ip', 'route', 'show', 'default'], universal_newlines=True)
            return result.split()[2] if result else "N/A"
        except subprocess.CalledProcessError:
            return "Error"

    def get_dns_servers(self):
        try:
            with open('/etc/resolv.conf', 'r') as f:
                lines = f.readlines()
            return [line.split()[1] for line in lines if line.startswith('nameserver')] if lines else []
        except IOError:
            return ["Error"]


    
    
    def prompt_for_password(self):
        # Check if password is still within the cache period
        if self.last_password_time and (time.time() - self.last_password_time < self.password_cache_duration):
            # Return cached password if it's still valid
            return self.cached_password
        
        # If no valid cached password, prompt the user for the password
        while True:
            password = self.show_interface_dailog()
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
        
        
    def get_interface_status(self, iface):
        """
        Check if the network interface is enabled (up) or disabled (down).
        Returns True if the interface is up, False otherwise.
        """
        try:
            result = subprocess.check_output(['ip', 'link', 'show', iface], universal_newlines=True)
            if "state UP" in result:
                return True
            else:
                return False
        except subprocess.CalledProcessError:
            return False

    def setup_ui(self):
        """
        Set up the UI, including the initial state of the toggle button based on the interface status.
        """
        # Assume self.toggle is the QPushButton used to toggle the network interface
        iface = self.network_combo.currentText()  # Get the selected network interface

        # Check if the interface is up or down and update the toggle button accordingly
        if self.get_interface_status(iface):
            self.toggle.setText("Disable Interface")
            self.toggle.setToolTip("Disable the selected network interface")
        else:
            self.toggle.setText("Enable Interface")
            self.toggle.setToolTip("Enable the selected network interface")

    def toggle_network_interface(self):
        iface = self.network_combo.currentText()

        # Check if the interface is selected
        if not iface:
            QMessageBox.warning(self, "Error", "No network interface selected.")
            return

        # Prompt for sudo password
        password_for_interface = self.prompt_for_password()

        # If the user cancels or doesn't provide a password, the toggle button stays disabled
        if password_for_interface is None:
            QMessageBox.information(self, "Cancelled", "Operation was cancelled.")
            self.toggle.setEnabled(False)  # Keep toggle button disabled
            return

        # Determine the command to run (enable/disable interface)
        if self.toggle.text() == "Enable Interface":
            command = f'echo {password_for_interface} | sudo -S ifconfig {iface} up'
            self.toggle.setToolTip("Disable")  # Update tooltip
            self.toggle.setText("Disable Interface")  # Change the button text
        else:
            command = f'echo {password_for_interface} | sudo -S ifconfig {iface} down'
            self.toggle.setToolTip("Enable")  # Update tooltip
            self.toggle.setText("Enable Interface")  # Change the button text

        # Run the command only if a password was successfully entered
        self.run_interface_command(command, iface)

        # After running the command, check and update the interface status
        if self.get_interface_status(iface):
            self.toggle.setText("Disable Interface")
        else:
            self.toggle.setText("Enable Interface")

    def run_interface_command(self, command, iface):
        try:
            # Run the command
            subprocess.run(command, shell=True, check=True, stderr=subprocess.STDOUT)
            QMessageBox.information(self, "Network Interface", f"Network interface {iface} has been toggled.")
            self.update_network_info()  # Update network info after toggling

            # Update the toggle button based on the new interface status
            if self.get_interface_status(iface):
                self.toggle.setText("Disable Interface")
            else:
                self.toggle.setText("Enable Interface")

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle network interface: {e}")

            

# Helper function to prompt for password with QTimer
    def show_interface_dailog(self):
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
 
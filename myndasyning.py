import os
import requests
import ctypes
import time
import json
import threading
import keyboard
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageTk
import tkinter as tk
from pystray import Icon, Menu, MenuItem
from io import BytesIO
import logging

class WallpaperSlideshow:
    def __init__(self, unsplash_access_key, download_dir="wallpapers"):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.unsplash_access_key = unsplash_access_key
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Windows API constant for setting wallpaper
        self.SPI_SETDESKWALLPAPER = 0x0014
        self.SPIF_UPDATEINIFILE = 0x01
        self.SPIF_SENDCHANGE = 0x02
        
        # Control flags
        self.running = True
        self.current_wallpaper = None
        self.drag_data = {"x": 0, "y": 0}
        
        # Initialize UI elements
        self.button_window = None
        self.icon = None
        self.init_ui()

    def init_ui(self):
        """Initialize all UI elements"""
        try:
            self.init_floating_button()
            self.init_system_tray()
            self.setup_keyboard_shortcut()
            self.logger.info("UI initialization completed successfully")
        except Exception as e:
            self.logger.error(f"Error initializing UI: {e}")

    def init_floating_button(self):
        """Initialize the floating button window"""
        self.button_window = tk.Tk()
        self.button_window.title("Wallpaper Control")
        
        # Configure window
        self.button_window.attributes('-topmost', True)
        self.button_window.overrideredirect(True)
        self.button_window.configure(bg='#2d2d2d')
        
        # Create main frame
        self.frame = tk.Frame(
            self.button_window,
            bg='#2d2d2d',
            highlightbackground='#404040',
            highlightthickness=1
        )
        self.frame.pack(padx=2, pady=2)
        
        # Create button with modern styling
        self.change_button = tk.Button(
            self.frame,
            text="New Wallpaper",
            command=self.force_new_wallpaper,
            bg='#2196F3',
            fg='white',
            relief='flat',
            pady=8,
            padx=15,
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        self.change_button.pack()
        
        # Status label
        self.status_label = tk.Label(
            self.frame,
            text="Ready",
            bg='#2d2d2d',
            fg='#aaaaaa',
            font=('Segoe UI', 8)
        )
        self.status_label.pack(pady=(5, 2))
        
        # Bind dragging events to both frame and button
        for widget in (self.frame, self.change_button):
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.drag)
        
        # Position window in top-right corner
        screen_width = self.button_window.winfo_screenwidth()
        self.button_window.geometry(f'+{screen_width-200}+50')
        
        # Protocol handler for window close button
        self.button_window.protocol("WM_DELETE_WINDOW", self.toggle_button)

    def setup_keyboard_shortcut(self):
        """Set up the keyboard shortcut"""
        try:
            keyboard.unhook_all()  # Clear any existing hooks
            keyboard.add_hotkey('ctrl+alt+y', self.force_new_wallpaper, suppress=True)
            self.logger.info("Keyboard shortcut (Ctrl+Alt+Y) registered successfully")
        except Exception as e:
            self.logger.error(f"Failed to register keyboard shortcut: {e}")

    def init_system_tray(self):
        """Initialize the system tray icon and menu"""
        try:
            menu = Menu(
                MenuItem("New Wallpaper (Ctrl+Alt+N)", self.force_new_wallpaper),
                MenuItem("Show/Hide Button", self.toggle_button),
                MenuItem("Exit", self.quit_app)
            )
            
            # Create a simple icon
            icon_image = Image.new('RGB', (64, 64), color='#2196F3')
            self.icon = Icon("Wallpaper Slideshow", icon_image, "Wallpaper Control", menu)
            
            # Start system tray icon in a separate thread
            threading.Thread(target=self.icon.run, daemon=True).start()
            self.logger.info("System tray icon initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize system tray: {e}")

    def start_drag(self, event):
        """Record initial position for dragging"""
        self.drag_data["x"] = event.x_root - self.button_window.winfo_x()
        self.drag_data["y"] = event.y_root - self.button_window.winfo_y()

    def drag(self, event):
        """Handle dragging of the floating button"""
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.button_window.geometry(f"+{x}+{y}")

    def update_status(self, message, color='#aaaaaa'):
        """Update the status label with a message"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message, fg=color)
            self.button_window.update()

    def toggle_button(self):
        """Toggle the floating button visibility"""
        if self.button_window.winfo_viewable():
            self.button_window.withdraw()
        else:
            self.button_window.deiconify()

    def force_new_wallpaper(self, *args):
        """Force download and set a new wallpaper"""
        try:
            self.update_status("Downloading new image...", '#2196F3')
            image_path = self.download_image()
            
            if image_path:
                self.update_status("Setting wallpaper...", '#2196F3')
                self.set_wallpaper(image_path)
                self.cleanup_old_wallpapers()
                self.update_status("Wallpaper updated!", '#4CAF50')
                threading.Timer(3, lambda: self.update_status("Ready")).start()
            else:
                self.update_status("Failed to download image", '#f44336')
                
        except Exception as e:
            self.logger.error(f"Error in force_new_wallpaper: {e}")
            self.update_status("Error changing wallpaper", '#f44336')

    def download_image(self, query="nature"):
        """Download a random image from Unsplash based on query"""
        try:
            headers = {
                "Authorization": f"Client-ID {self.unsplash_access_key}"
            }
            
            # Get random photo URL
            url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape"
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise exception for bad status codes
            
            data = response.json()
            image_url = data['urls']['raw']
            photographer = data['user']['name']
            
            # Download the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wallpaper_{timestamp}.jpg"
            filepath = self.download_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(image_response.content)
            
            self.logger.info(f"Downloaded image by {photographer}")
            self.current_wallpaper = str(filepath)
            return str(filepath)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Download error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in download_image: {e}")
            return None

    def set_wallpaper(self, image_path):
        """Set the Windows wallpaper"""
        try:
            abs_path = str(Path(image_path).resolve())
            result = ctypes.windll.user32.SystemParametersInfoW(
                self.SPI_SETDESKWALLPAPER, 
                0, 
                abs_path, 
                self.SPIF_UPDATEINIFILE | self.SPIF_SENDCHANGE
            )
            
            if not result:
                raise Exception("SystemParametersInfoW returned 0")
            
            self.logger.info(f"Wallpaper set successfully: {abs_path}")
            
        except Exception as e:
            self.logger.error(f"Error setting wallpaper: {e}")
            raise

    def cleanup_old_wallpapers(self, max_files=10):
        """Keep only the most recent wallpapers"""
        try:
            wallpapers = list(self.download_dir.glob("wallpaper_*.jpg"))
            wallpapers.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for wallpaper in wallpapers[max_files:]:
                wallpaper.unlink()
                self.logger.info(f"Cleaned up old wallpaper: {wallpaper}")
        except Exception as e:
            self.logger.error(f"Error cleaning up wallpapers: {e}")

    def quit_app(self):
        """Cleanup and quit the application"""
        try:
            self.running = False
            if self.icon:
                self.icon.stop()
            if self.button_window:
                self.button_window.quit()
            keyboard.unhook_all()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def run(self, interval_minutes=30, query="nature"):
        """Run the wallpaper slideshow"""
        self.logger.info(f"Starting wallpaper slideshow (interval: {interval_minutes}m, query: {query})")
        print(f"Starting wallpaper slideshow with {interval_minutes} minute intervals")
        print(f"Press Ctrl+Alt+Y for new wallpaper or use the floating button")
        print(f"Searching for images matching: {query}")
        
        def auto_changer():
            while self.running:
                try:
                    self.force_new_wallpaper()
                    time.sleep(interval_minutes * 60)
                except Exception as e:
                    self.logger.error(f"Error in auto_changer: {e}")
                    time.sleep(60)
        
        # Start the automatic changer thread
        changer_thread = threading.Thread(target=auto_changer, daemon=True)
        changer_thread.start()
        
        # Start the main UI loop
        try:
            self.button_window.mainloop()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")

if __name__ == "__main__":
    # You'll need to sign up for a free Unsplash API key at: https://unsplash.com/developers
    UNSPLASH_ACCESS_KEY = "krmfxmLnYYK29-umX4-pmN_09dkbHqJx4V5BYW8cdm4"
    
    slideshow = WallpaperSlideshow(UNSPLASH_ACCESS_KEY)
    slideshow.run(interval_minutes=30, query="nature")
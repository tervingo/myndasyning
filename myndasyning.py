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
from tkinter import filedialog
import random
from urllib.parse import urlparse

class WallpaperSlideshow:
    def __init__(self, flickr_api_key, flickr_api_secret, download_dir="wallpapers"):
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.flickr_api_key = flickr_api_key
        self.flickr_api_secret = flickr_api_secret
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Create favorites directory
        self.favorites_dir = Path("wallpapers")
        self.favorites_dir.mkdir(exist_ok=True)

        # Windows API constant for setting wallpaper
        self.SPI_SETDESKWALLPAPER = 0x0014
        self.SPIF_UPDATEINIFILE = 0x01
        self.SPIF_SENDCHANGE = 0x02
        
        # Control flags
        self.running = True
        self.timer_active = True
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
        
        # Change wallpaper button
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
        self.change_button.pack(pady=5)

       # Timer control button
        self.timer_button = tk.Button(
            self.frame,
            text="Pause Timer",
            command=self.toggle_timer,
            bg='#FF9800',
            fg='white',
            relief='flat',
            pady=8,
            padx=15,
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        self.timer_button.pack(pady=5)
        
        # Favorite button
        self.favorite_button = tk.Button(
            self.frame,
            text="Save to Favorites",
            command=self.save_to_favorites,
            bg='#4CAF50',
            fg='white',
            relief='flat',
            pady=8,
            padx=15,
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        self.favorite_button.pack(pady=5)

        # Load from favorites button
        self.load_favorite_button = tk.Button(
            self.frame,
            text="Load from Favorites",
            command=self.load_from_favorites,
            bg='#9C27B0',  # Purple color
            fg='white',
            relief='flat',
            pady=8,
            padx=15,
            font=('Segoe UI', 9),
            cursor='hand2'
        )
        self.load_favorite_button.pack(pady=5)


        # Status label
        self.status_label = tk.Label(
            self.frame,
            text="Ready",
            bg='#2d2d2d',
            fg='#aaaaaa',
            font=('Segoe UI', 8)
        )
        self.status_label.pack(pady=(5, 2))
        
        # Bind dragging events to all widgets
        for widget in (self.frame, self.change_button, self.timer_button, self.favorite_button, self.load_favorite_button):
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.drag)
         
        # Position window at the right side, vertically centered
        # First, update the window to calculate its actual size
        self.button_window.update_idletasks()
        
        # Get screen dimensions
        screen_width = self.button_window.winfo_screenwidth()
        screen_height = self.button_window.winfo_screenheight()
        
        # Get window dimensions
        window_width = self.button_window.winfo_width()
        window_height = self.button_window.winfo_height()
        
        # Calculate position
        x_position = screen_width - window_width - 20  # 20 pixels padding from right edge
        y_position = (screen_height - window_height) // 2
        
        # Set window position
        self.button_window.geometry(f"+{x_position}+{y_position}")
        
        # Protocol handler for window close button
        self.button_window.protocol("WM_DELETE_WINDOW", self.toggle_button)

    def toggle_timer(self):
        """Toggle the automatic wallpaper timer"""
        self.timer_active = not self.timer_active
        
        if self.timer_active:
            self.timer_button.config(
                text="Pause Timer",
                bg='#FF9800'
            )
            self.update_status("Timer resumed", '#4CAF50')
        else:
            self.timer_button.config(
                text="Resume Timer",
                bg='#f44336'
            )
            self.update_status("Timer paused", '#FF9800')
        
        threading.Timer(3, lambda: self.update_status("Ready")).start()

    def save_to_favorites(self):
        """Save the current wallpaper to favorites folder"""
        try:
            if not self.current_wallpaper:
                self.update_status("No wallpaper to save", '#f44336')
                return
                
            # Create a copy of the current wallpaper in favorites folder
            source_path = Path(self.current_wallpaper)
            if not source_path.exists():
                self.update_status("Wallpaper file not found", '#f44336')
                return
                
            # Generate a filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_path = self.favorites_dir / f"favorite_{timestamp}.jpg"
            
            # Copy the file
            import shutil
            shutil.copy2(source_path, target_path)
            
            self.update_status("Saved to favorites!", '#4CAF50')
            threading.Timer(3, lambda: self.update_status("Ready")).start()
            
            self.logger.info(f"Saved wallpaper to favorites: {target_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving to favorites: {e}")
            self.update_status("Error saving favorite", '#f44336')

    def load_from_favorites(self):
        """Load and set wallpaper from favorites folder"""
        try:
            # Check if favorites directory exists and has files
            if not self.favorites_dir.exists() or not any(self.favorites_dir.glob("*.jpg")):
                self.update_status("No favorites found", '#f44336')
                return

            # Open file dialog in favorites directory
            filepath = filedialog.askopenfilename(
                initialdir=self.favorites_dir,
                title="Select Favorite Wallpaper",
                filetypes=(("JPEG files", "*.jpg"), ("All files", "*.*"))
            )

            if filepath:  # If a file was selected
                # Set as wallpaper
                self.set_wallpaper(filepath)
                self.current_wallpaper = filepath
                
                # Pause the timer
                if self.timer_active:
                    self.toggle_timer()  # This will pause the timer
                
                self.update_status("Favorite wallpaper set!", '#4CAF50')
                threading.Timer(3, lambda: self.update_status("Ready")).start()
                
                self.logger.info(f"Loaded favorite wallpaper: {filepath}")
            else:
                self.update_status("No file selected", '#FF9800')

        except Exception as e:
            self.logger.error(f"Error loading favorite: {e}")
            self.update_status("Error loading favorite", '#f44336')

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
        """Download a random image from Flickr based on query"""
        try:
            # Flickr API endpoint for photo search
            base_url = "https://www.flickr.com/services/rest/"
            
            # Parameters for the API request
            params = {
                'method': 'flickr.photos.search',
                'api_key': self.flickr_api_key,
                'text': query,
                'license': '4,5,6,7',  # Use Creative Commons licensed photos
                'sort': 'relevance',
                'media': 'photos',
                'extras': 'url_k,owner_name',  # Request large size (2048px) and photographer name
                'format': 'json',
                'nojsoncallback': 1,
                'per_page': 100,
                'page': 1,
                'content_type': 1,  # Photos only
                'safe_search': 1,  # Safe content only
                'min_taken_date': '2000-01-01'  # Ensure reasonable photo quality
            }
            
            # Get image list
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('photos', {}).get('photo', []):
                self.logger.error("No images found for the query")
                return None
            
            # Filter for photos that have the 'url_k' (large size) available
            suitable_photos = [photo for photo in data['photos']['photo'] if 'url_k' in photo]
            
            if not suitable_photos:
                self.logger.error("No suitable high-resolution images found")
                return None
            
            # Choose a random image from the results
            photo = random.choice(suitable_photos)
            
            # Get the large version of the image
            image_url = photo['url_k']
            photographer = photo['ownername']
            
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

    def run(self, interval_minutes=60, query="nature"):
        """Run the wallpaper slideshow"""
        self.logger.info(f"Starting wallpaper slideshow (interval: {interval_minutes}m, query: {query})")
        print(f"Starting wallpaper slideshow with {interval_minutes} minute intervals")
        print(f"Press Ctrl+Alt+N for new wallpaper or use the floating button")
        print(f"Searching for images matching: {query}")
        
        def auto_changer():
            while self.running:
                try:
                    if self.timer_active:  # Only change wallpaper if timer is active
                        self.force_new_wallpaper()
                    time.sleep(interval_minutes * 10)
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
    # You'll need to sign up for a Flickr API key at: https://www.flickr.com/services/apps/create/
    FLICKR_API_KEY = "da65ad8de193149ff9348abf03c231db"
    FLICKR_API_SECRET = "81afa406bfe808fb"
    
    slideshow = WallpaperSlideshow(FLICKR_API_KEY, FLICKR_API_SECRET)
    slideshow.run(interval_minutes=30, query="nature")
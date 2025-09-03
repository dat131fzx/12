from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.widget import Widget
import os
import threading
import requests
from io import BytesIO
import time

# Android-specific imports
try:
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission
    ANDROID = True
    Logger.info("Android modules loaded successfully")
except ImportError:
    ANDROID = False
    Logger.warning("Android modules not available - running in desktop mode")

class WallpaperChangerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # URL của ảnh bạn muốn sử dụng làm hình nền
        self.wallpaper_url = "https://scontent.fsgn5-9.fna.fbcdn.net/v/t39.30808-6/536282619_122104944854994196_5841633964594740809_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=127cfc&_nc_ohc=0u5jdDI-r7oQ7kNvwGfdkIe&_nc_oc=AdnoJPHI3a9crqaBiwHzrgCGQfzHGSld6YXjenfrM9v5eah90wzA-YLGUmDzu9558nc&_nc_zt=23&_nc_ht=scontent.fsgn5-9.fna&_nc_gid=LikPNfmANVHo94W2oobyvw&oh=00_AfaB89JitfYObtQP5F8hobrG0mkYTNLaUfVVchvnVCYZOQ&oe=68BE00E5"
        self.image_data = None
        self.download_completed = False
    
    def build(self):
        """Build the minimal UI"""
        Logger.info("Building app interface")
        # Return a minimal widget (won't be visible for long)
        widget = Widget()
        return widget
    
    def on_start(self):
        """Called when the app starts"""
        Logger.info("App started")
        
        if ANDROID:
            Logger.info("Running on Android - requesting permissions")
            # Request necessary permissions
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.SET_WALLPAPER,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ])
            
            # Wait a moment for permissions then start downloading
            Clock.schedule_once(self.start_download, 1.0)
        else:
            Logger.info("Desktop mode - wallpaper change not supported")
            Clock.schedule_once(self.exit_app, 2)
    
    def start_download(self, dt):
        """Start downloading image in background thread"""
        Logger.info("Starting image download...")
        threading.Thread(target=self.download_image, daemon=True).start()
    
    def download_image(self):
        """Download image from URL"""
        try:
            Logger.info(f"Downloading wallpaper from: {self.wallpaper_url}")
            
            # Set headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            }
            
            # Download the image with timeout and verify SSL
            Logger.info("Sending request to download image...")
            response = requests.get(
                self.wallpaper_url, 
                headers=headers, 
                timeout=30,
                verify=True,
                stream=True
            )
            response.raise_for_status()
            
            # Read the image data
            Logger.info("Reading image data...")
            self.image_data = response.content
            self.download_completed = True
            
            Logger.info(f"Image downloaded successfully, size: {len(self.image_data)} bytes")
            Logger.info(f"Content type: {response.headers.get('content-type', 'unknown')}")
            
            # Schedule wallpaper change on main thread
            Clock.schedule_once(self.change_wallpaper, 0)
            
        except requests.exceptions.Timeout:
            Logger.error("Request timeout - image download failed")
            Clock.schedule_once(self.exit_app, 1)
        except requests.exceptions.ConnectionError:
            Logger.error("Connection error - check internet connection")
            Clock.schedule_once(self.exit_app, 1)
        except requests.exceptions.HTTPError as e:
            Logger.error(f"HTTP error: {e}")
            Clock.schedule_once(self.exit_app, 1)
        except requests.exceptions.RequestException as e:
            Logger.error(f"Request failed: {e}")
            Clock.schedule_once(self.exit_app, 1)
        except Exception as e:
            Logger.error(f"Unexpected error downloading image: {e}")
            Clock.schedule_once(self.exit_app, 1)
    
    def change_wallpaper(self, dt):
        """Change the wallpaper using downloaded image data and then exit"""
        try:
            if not self.image_data or not self.download_completed:
                Logger.error("No image data available")
                Clock.schedule_once(self.exit_app, 1)
                return
            
            Logger.info("Setting wallpaper...")
                
            # Get Android classes
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WallpaperManager = autoclass('android.app.WallpaperManager')
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            
            # Get current activity and wallpaper manager
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            wallpaper_manager = WallpaperManager.getInstance(context)
            
            Logger.info("Creating bitmap from image data...")
            
            # Convert Python bytes to Java byte array
            java_byte_array = autoclass('[B')
            java_bytes = java_byte_array(len(self.image_data))
            for i, byte_val in enumerate(self.image_data):
                java_bytes[i] = byte_val
            
            # Create bitmap from byte array
            bitmap = BitmapFactory.decodeByteArray(java_bytes, 0, len(self.image_data))
            
            if bitmap is None:
                Logger.error("Failed to decode image data to bitmap")
                Clock.schedule_once(self.exit_app, 1)
                return
            
            Logger.info(f"Bitmap created successfully: {bitmap.getWidth()}x{bitmap.getHeight()}")
            
            # Set the wallpaper
            Logger.info("Setting wallpaper...")
            wallpaper_manager.setBitmap(bitmap)
            
            Logger.info("Wallpaper changed successfully from URL!")
            
            # Clean up bitmap
            if hasattr(bitmap, 'recycle'):
                bitmap.recycle()
                
        except Exception as e:
            Logger.error(f"Error changing wallpaper: {e}")
            import traceback
            Logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Exit the app after attempting to change wallpaper
        Clock.schedule_once(self.exit_app, 2.0)
    
    def exit_app(self, dt):
        """Exit the application"""
        Logger.info("Exiting application...")
        try:
            # Clean up
            self.image_data = None
            
            # Stop the app
            self.stop()
            
            # Force exit if needed
            if ANDROID:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                activity.finish()
                
        except Exception as e:
            Logger.error(f"Error during app exit: {e}")

# Create and run the app
if __name__ == '__main__':
    try:
        Logger.info("Starting Wallpaper Changer App")
        WallpaperChangerApp().run()
    except Exception as e:
        Logger.error(f"Failed to start app: {e}")
        import traceback
        Logger.error(f"Traceback: {traceback.format_exc()}")

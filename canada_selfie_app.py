#!/usr/bin/env python3
"""
Canada Selfie Webcam App
A PyQt5 application with webcam functionality and Canadian theme
"""

import sys
import os
import logging
from datetime import datetime
import platform
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Suppress OpenCV warnings
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

# Setup logging
def setup_logging():
    """Setup logging configuration with platform-specific log paths"""
    if platform.system() == 'Windows':
        # Use AppData on Windows
        log_dir = os.path.join(os.environ.get('APPDATA', ''), 'CanadaSelfieApp')
    else:
        # Use home directory on other platforms
        log_dir = os.path.join(os.path.expanduser('~'), '.canada_selfie')
    
    # Create directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Log file with timestamp
    log_file = os.path.join(log_dir, f'canada_selfie_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress verbose logs from numba and other libraries
    logging.getLogger('numba').setLevel(logging.WARNING)
    logging.getLogger('numba.core').setLevel(logging.WARNING)
    logging.getLogger('numba.typed').setLevel(logging.WARNING)
    logging.getLogger('onnxruntime').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    # Log initial system info
    logger = logging.getLogger('CanadaSelfie')
    logger.info(f"="*60)
    logger.info(f"Canada Selfie App Started")
    logger.info(f"="*60)
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    return logger

# Initialize logging
logger = setup_logging()

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QLabel, QFrame, QMessageBox, 
                           QSlider, QComboBox, QGroupBox, QGridLayout, QProgressDialog)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QUrl, QThread, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor, QIcon
import random
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path
try:
    logger.info("Attempting to import rembg...")
    logger.info(f"sys.executable: {sys.executable}")
    logger.info(f"sys.prefix: {sys.prefix}")
    if hasattr(sys, '_MEIPASS'):
        logger.info(f"PyInstaller _MEIPASS: {sys._MEIPASS}")
    
    # Try importing onnxruntime first to get better error messages
    try:
        logger.info("Testing onnxruntime import...")
        import onnxruntime
        logger.info(f"✅ onnxruntime version: {onnxruntime.__version__}")
    except Exception as e:
        logger.error(f"❌ onnxruntime import failed: {e}")
        raise
    
    import rembg
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
    logger.info("✅ rembg imported successfully")
    
    # For PyInstaller builds, set custom model path to user's home directory
    if hasattr(sys, '_MEIPASS'):
        # Use home directory for downloaded models (writable location)
        u2net_path = str(Path.home() / '.u2net')
        os.environ['U2NET_HOME'] = u2net_path
        logger.info(f"PyInstaller detected, setting U2NET_HOME to: {u2net_path}")
    else:
        logger.info(f"Development mode, U2NET_HOME: {os.environ.get('U2NET_HOME', 'Not set')}")
        
except ImportError as e:
    REMBG_AVAILABLE = False
    logger.error(f"❌ rembg import failed: {e}")
    logger.exception("Full traceback:")
    # Silent - no warning printed

class Firework:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.original_y = y
        self.color = color
        self.particles = []
        self.exploded = False
        self.life = 100
        self.rise_speed = 8
        
        # Create explosion particles
        for i in range(random.randint(8, 15)):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(2, 8)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': speed * np.cos(angle),
                'vy': speed * np.sin(angle),
                'life': random.randint(30, 60),
                'size': random.randint(2, 6)
            })
    
    def update(self):
        if not self.exploded:
            # Rising phase
            self.y -= self.rise_speed
            if self.y <= self.original_y - random.randint(100, 200):
                self.exploded = True
        else:
            # Explosion phase
            for particle in self.particles:
                particle['x'] += particle['vx']
                particle['y'] += particle['vy']
                particle['vy'] += 0.3  # Gravity
                particle['life'] -= 1
                particle['vx'] *= 0.98  # Air resistance
            
            # Remove dead particles
            self.particles = [p for p in self.particles if p['life'] > 0]
            self.life -= 1
        
        return len(self.particles) > 0 and self.life > 0
    
    def draw(self, frame):
        if not self.exploded:
            # Draw rising firework
            cv2.circle(frame, (int(self.x), int(self.y)), 3, self.color, -1)
            # Trail effect
            for i in range(5):
                trail_y = int(self.y + i * 5)
                if trail_y < frame.shape[0]:
                    alpha = 1.0 - (i * 0.2)
                    color = tuple(int(c * alpha) for c in self.color)
                    cv2.circle(frame, (int(self.x), trail_y), 2, color, -1)
        else:
            # Draw explosion particles
            for particle in self.particles:
                if particle['life'] > 0:
                    alpha = particle['life'] / 60.0
                    color = tuple(int(c * alpha) for c in self.color)
                    cv2.circle(frame, (int(particle['x']), int(particle['y'])), 
                             particle['size'], color, -1)

class ModelDownloadWorker(QThread):
    """Worker thread for downloading rembg model"""
    progress = pyqtSignal(int, str)  # progress percentage, status message
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, model_name='u2netp'):
        super().__init__()
        self.model_name = model_name
        self.logger = logging.getLogger('ModelDownload')
        
    def run(self):
        try:
            self.logger.info(f"="*60)
            self.logger.info(f"Starting model download process")
            self.logger.info(f"Model: {self.model_name}")
            self.logger.info(f"Platform: {platform.system()}")
            
            self.progress.emit(0, "Initializing download...")
            
            # Debug: Print environment variable
            u2net_home = os.environ.get('U2NET_HOME', str(Path.home() / '.u2net'))
            self.logger.info(f"U2NET_HOME: {u2net_home}")
            
            # Check if directory exists and is writable
            u2net_dir = Path(u2net_home)
            try:
                u2net_dir.mkdir(parents=True, exist_ok=True)
                test_file = u2net_dir / 'test_write.tmp'
                test_file.write_text('test')
                test_file.unlink()
                self.logger.info(f"✅ Model directory is writable: {u2net_dir}")
            except Exception as e:
                self.logger.error(f"❌ Cannot write to model directory: {e}")
                self.finished.emit(False, f"Cannot write to model directory: {u2net_home}")
                return
            
            # Import here to catch progress
            self.logger.info("Importing rembg.new_session...")
            from rembg import new_session
            
            self.progress.emit(10, "Connecting to model server...")
            
            # Check if model already exists
            model_path = Path(u2net_home) / f'{self.model_name}.onnx'
            self.logger.info(f"Looking for model at: {model_path}")
            
            if model_path.exists():
                size_mb = model_path.stat().st_size / 1024 / 1024
                self.logger.info(f"✅ Model found at: {model_path} (Size: {size_mb:.1f} MB)")
                self.progress.emit(100, "Model already downloaded!")
                self.finished.emit(True, "Model ready!")
                return
            
            self.progress.emit(20, f"Downloading {self.model_name} model (~180MB)...")
            self.logger.info("Starting model download via new_session()...")
            
            # Log network connectivity
            try:
                import urllib.request
                self.logger.info("Testing network connectivity...")
                with urllib.request.urlopen('https://github.com', timeout=5) as response:
                    self.logger.info(f"✅ Network connection OK (GitHub accessible)")
            except Exception as e:
                self.logger.warning(f"⚠️ Network test failed: {e}")
            
            # This will trigger the download
            self.logger.info("Creating new rembg session (this will download the model)...")
            
            # Add special handling for Windows
            if platform.system() == 'Windows':
                self.logger.info("Windows detected - setting up special handling...")
                # Ensure stdout/stderr are available
                import sys
                if sys.stdout is None:
                    self.logger.warning("stdout is None - creating dummy stdout")
                    import io
                    sys.stdout = io.StringIO()
                if sys.stderr is None:
                    self.logger.warning("stderr is None - creating dummy stderr")
                    import io
                    sys.stderr = io.StringIO()
                    
                # Set Windows-specific environment variables
                os.environ['ONNX_DISABLE_POOL_ALLOCATOR'] = '1'
                
            try:
                session = new_session(self.model_name)
                self.logger.info("✅ Session created successfully")
            except AttributeError as ae:
                if "'NoneType' object has no attribute 'write'" in str(ae):
                    self.logger.error("Known Windows issue with stdout/stderr")
                    # Try alternative download method
                    self.logger.info("Attempting manual model download...")
                    self.manual_download_model()
                    return
                else:
                    raise
            
            self.progress.emit(90, "Finalizing...")
            
            # Verify download
            if model_path.exists():
                size_mb = model_path.stat().st_size / 1024 / 1024
                self.logger.info(f"✅ Model downloaded successfully!")
                self.logger.info(f"Model size: {size_mb:.1f} MB")
                self.logger.info(f"Model location: {model_path}")
                self.progress.emit(100, f"Download complete! ({size_mb:.1f} MB)")
                self.finished.emit(True, "Model downloaded successfully!")
            else:
                self.logger.error(f"❌ Model file not found after download: {model_path}")
                self.finished.emit(False, "Model download failed - file not found!")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"❌ Model download failed with exception: {str(e)}")
            self.logger.error(f"Full traceback:\n{error_details}")
            
            # Send error to Sentry with context
            sentry_sdk.set_context("model_download", {
                "model_name": self.model_name,
                "platform": platform.system(),
                "u2net_home": u2net_home,
                "error_type": type(e).__name__
            })
            sentry_sdk.capture_exception(e)
            
            self.finished.emit(False, f"Download error: {str(e)}")
    
    def manual_download_model(self):
        """Manual download method for Windows when rembg fails"""
        try:
            import urllib.request
            import hashlib
            
            # Model URLs (from rembg repository)
            model_urls = {
                'u2netp': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx',
                'u2net': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx',
                'u2net_human_seg': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx',
                'u2net_cloth_seg': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_cloth_seg.onnx'
            }
            
            if self.model_name not in model_urls:
                self.logger.error(f"Unknown model: {self.model_name}")
                self.finished.emit(False, f"Unknown model: {self.model_name}")
                return
                
            url = model_urls[self.model_name]
            u2net_home = os.environ.get('U2NET_HOME', str(Path.home() / '.u2net'))
            model_path = Path(u2net_home) / f'{self.model_name}.onnx'
            
            self.logger.info(f"Downloading from: {url}")
            self.logger.info(f"Saving to: {model_path}")
            
            # Create directory if needed
            model_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            def download_hook(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100)
                self.progress.emit(int(percent), f"Downloading... {percent:.1f}%")
                
            urllib.request.urlretrieve(url, str(model_path), reporthook=download_hook)
            
            # Verify download
            if model_path.exists():
                size_mb = model_path.stat().st_size / 1024 / 1024
                self.logger.info(f"✅ Model downloaded successfully!")
                self.logger.info(f"Model size: {size_mb:.1f} MB")
                self.progress.emit(100, f"Download complete! ({size_mb:.1f} MB)")
                self.finished.emit(True, "Model downloaded successfully!")
            else:
                self.logger.error(f"❌ Model file not found after download")
                self.finished.emit(False, "Download failed - file not found!")
                
        except Exception as e:
            self.logger.error(f"Manual download failed: {str(e)}")
            sentry_sdk.capture_exception(e)
            self.finished.emit(False, f"Manual download failed: {str(e)}")

class BackgroundRemovalWorker(QThread):
    """Worker thread for background removal processing"""
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.input_queue = queue.Queue(maxsize=2)
        self.running = True
        self.current_bg = None
        self.enabled = False
        
    def process_frame(self, frame, bg):
        """Process a single frame with background removal"""
        if not self.enabled or bg is None:
            return frame
            
        try:
            # Remove background
            input_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            output = remove(input_img, session=self.session, alpha_matting=True, 
                          alpha_matting_foreground_threshold=240,
                          alpha_matting_background_threshold=50,
                          alpha_matting_erode_size=10)
            
            # Convert to BGRA
            if len(output.shape) == 2:
                output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGRA)
            elif output.shape[2] == 3:
                output = cv2.cvtColor(output, cv2.COLOR_RGB2BGRA)
            
            # Get mask from alpha channel
            mask = output[:, :, 3]
            
            # Apply morphological operations to refine mask
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Apply gaussian blur for smoother edges
            mask = cv2.GaussianBlur(mask, (3, 3), 0)
            
            # Resize background to match frame
            bg_resized = cv2.resize(bg, (frame.shape[1], frame.shape[0]))
            
            # Create 3-channel mask
            mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            
            # Blend using weighted addition for smoother edges
            fg = frame.astype(float) * (mask_3ch.astype(float) / 255.0)
            bg = bg_resized.astype(float) * (1.0 - mask_3ch.astype(float) / 255.0)
            
            # Combine and convert back to uint8
            result = (fg + bg).astype(np.uint8)
            return result
        except Exception as e:
            print(f"Background removal error in worker: {e}")
            return frame
    
    def run(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get frame from queue with timeout
                frame, bg = self.input_queue.get(timeout=0.1)
                processed = self.process_frame(frame, bg)
                self.frame_ready.emit(processed)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.wait()

class CanadaSelfieApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_recording = False
        self.maple_leaf_overlay = False
        self.beaver_overlay = False
        self.current_camera = 0
        self.available_cameras = []
        
        # Canadian memes and phrases
        self.canadian_memes = [
            "EH! That's a beauty!",
            "Sorry, not sorry for being this photogenic!",
            "Just out for a rip, bud!",
            "Poutine-level gorgeous!",
            "Tim Hortons approved selfie!",
            "As Canadian as maple syrup!",
            "Hockey night ready!",
            "Double-double selfie, EH!",
            "Toque weather beauty!",
            "Mountie approved, EH!",
            "True North strong and beautiful!",
            "Canuck pride, EH!",
            "Eh-mazing shot, buddy!"
        ]
        
        # Canadian mascots and facts
        self.canadian_mascots = [
            {"emoji": "🦫", "name": "Beaver", "phrase": "The national animal, nature's engineer!"},
            {"emoji": "🫎", "name": "Moose", "phrase": "Largest member of the deer family, eh!"},
            {"emoji": "🐻", "name": "Polar Bear", "phrase": "Churchill is the polar bear capital!"},
            {"emoji": "🦌", "name": "Caribou", "phrase": "Featured on the quarter coin!"},
            {"emoji": "🦅", "name": "Canada Goose", "phrase": "Honk if you love Canada!"},
            {"emoji": "🐺", "name": "Grey Wolf", "phrase": "Roams the northern wilderness!"},
            {"emoji": "🦭", "name": "Seal", "phrase": "Atlantic Canada's playful resident!"},
            {"emoji": "🐋", "name": "Beluga Whale", "phrase": "The smiling whale of the St. Lawrence!"},
            {"emoji": "🦉", "name": "Snowy Owl", "phrase": "Quebec's provincial bird!"},
            {"emoji": "🐻", "name": "Black Bear", "phrase": "Found in every province except PEI!"},
            {"emoji": "🦆", "name": "Common Loon", "phrase": "Featured on the loonie coin!"},
            {"emoji": "🐎", "name": "Canadian Horse", "phrase": "National horse breed since 1665!"},
            {"emoji": "🦌", "name": "White-tailed Deer", "phrase": "Saskatchewan's provincial animal!"},
            {"emoji": "🐦", "name": "Blue Jay", "phrase": "Toronto's famous baseball mascot!"},
            {"emoji": "🍁", "name": "Maple Leaf", "phrase": "The eternal symbol of Canada!"}
        ]
        
        # Famous Canadian phrases
        self.canadian_phrases = [
            "Eh? What's that all aboot?",
            "Keep your stick on the ice!",
            "Sorry, didn't mean to bump ya there!",
            "Let's grab a double-double!",
            "Beauty day for a rip, bud!",
            "Give'r! Full send!",
            "That's mint, buddy!",
            "Just gonna send it!",
            "Pitter patter, let's get at 'er!",
            "Figure it out, bud!",
            "Take off, ya hoser!",
            "She's a beaut, Clark!",
            "Can I get a Timmies run?",
            "Gonna hit up the LCBO!",
            "True North strong and free!"
        ]
        
        # Background removal
        self.bg_removal_enabled = False
        self.current_bg = None
        
        # Easter egg variables
        self.secret_sequence = []
        self.secret_code = ["maple_rain", "snow_fall", "hockey_sticks", "beaver_dam"]
        self.easter_egg_active = False
        self.clicks_on_title = 0
        self.last_click_time = 0
        self.konami_sequence = []
        self.konami_code = [Qt.Key_Up, Qt.Key_Up, Qt.Key_Down, Qt.Key_Down, 
                           Qt.Key_Left, Qt.Key_Right, Qt.Key_Left, Qt.Key_Right]
        
        # Fireworks system
        self.fireworks = []
        self.fireworks_active = False
        self.fireworks_timer = 0
        self.current_model = 'u2netp'  # Better for portraits
        self.bg_worker = None
        self.last_processed_frame = None
        self.frame_skip_counter = 0
        self.frame_counter = 0
        
        # Background removal will be initialized after UI is ready
        self.rembg_session = None
        self.bg_removal_available = False
        
        
        self.init_ui()
        self.detect_cameras()
        self.setup_camera()
        self.create_background_images()
        self.load_emoji_icons()
        
        # Initialize background removal after UI is ready
        logger.info(f"REMBG_AVAILABLE: {REMBG_AVAILABLE}")
        if REMBG_AVAILABLE:
            logger.info("Scheduling background removal initialization...")
            QTimer.singleShot(100, self.initialize_background_removal)
        else:
            logger.warning("Background removal not available - rembg import failed")
        
    def init_ui(self):
        """Initialize the user interface with Canada theme"""
        self.setWindowTitle("🍁 Oh Canada! Selfie Cam 🍁")
        self.setGeometry(100, 100, 800, 600)
        
        # Set app icon
        try:
            icon_path = resource_path("emoji_icons/maple_leaf.png")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.setWindowIcon(icon)
                QApplication.instance().setWindowIcon(icon)
        except:
            pass
        
        # Set Canada Flag colors (Official: Red #FF0000, White #FFFFFF)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF0000, stop:0.25 #FF0000, stop:0.3 #FFFFFF, 
                    stop:0.7 #FFFFFF, stop:0.75 #FF0000, stop:1 #FF0000);
            }
            QPushButton {
                background-color: #FF0000;
                color: white;
                border: 2px solid #FFFFFF;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 6px;
                margin: 2px;
                min-height: 24px;
                max-height: 28px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #CC0000;
                border-color: #FFD700;
            }
            QPushButton:pressed {
                background-color: #990000;
            }
            QPushButton:disabled {
                background-color: #FFCCCC;
                color: #FFFFFF;
            }
            QLabel {
                color: #000000;
                font-weight: normal;
                background-color: transparent;
                border-radius: 5px;
                padding: 2px;
                font-size: 11px;
            }
            QFrame {
                border: 3px solid #FF0000;
                border-radius: 10px;
                background-color: #FFFFFF;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 2px solid #FF0000;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 11px;
                min-height: 24px;
                color: #000000;
            }
            QComboBox:disabled {
                background-color: #F0F0F0;
                color: #808080;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF0000;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                padding-bottom: 5px;
                padding-left: 5px;
                padding-right: 5px;
                background-color: rgba(255, 255, 255, 240);
                color: #000000;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #000000;
                background-color: #FFFFFF;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        central_widget.setLayout(main_layout)
        
        # Title
        title_label = QLabel("🍁 Welcome to Canada Selfie Cam, Eh! 🍁")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setMaximumHeight(40)
        title_label.setStyleSheet("""
            QLabel {
                color: #FF0000;
                background-color: #FFFFFF;
                border: 2px solid #FF0000;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(title_label)
        
        # Video display frame
        self.video_frame = QFrame()
        self.video_frame.setMinimumSize(640, 480)
        video_layout = QVBoxLayout()
        self.video_frame.setLayout(video_layout)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("QLabel { background-color: black; color: white; border: none; }")
        self.video_label.setText("🍁 Initializing Canadian Webcam... 🍁")
        video_layout.addWidget(self.video_label)
        
        main_layout.addWidget(self.video_frame, 1)
        
        # Controls panel
        controls_widget = QWidget()
        controls_widget.setMaximumHeight(150)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        controls_widget.setLayout(controls_layout)
        
        # Camera controls group
        camera_group = QGroupBox("📸 Camera")
        camera_layout = QGridLayout()
        camera_layout.setSpacing(6)
        camera_layout.setContentsMargins(10, 8, 10, 10)
        
        # Camera selection
        self.camera_combo = QComboBox()
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        self.camera_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #FF0000;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 10px;
                min-height: 16px;
                max-height: 20px;
                color: #000000;
            }
        """)
        camera_layout.addWidget(self.camera_combo, 0, 0, 1, 2)
        
        self.start_btn = QPushButton("▶")
        self.start_btn.clicked.connect(self.start_camera)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #00C851;
                color: white;
                font-weight: bold;
                font-size: 9px;
                border: 1px solid #00AA44;
                padding: 2px;
                min-height: 18px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #00AA44;
            }
            QPushButton:pressed {
                background-color: #008833;
            }
        """)
        camera_layout.addWidget(self.start_btn, 1, 0)
        
        self.stop_btn = QPushButton("■")
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF4444;
                color: white;
                font-weight: bold;
                font-size: 9px;
                border: 1px solid #DD0000;
                padding: 2px;
                min-height: 18px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #DD0000;
            }
            QPushButton:pressed {
                background-color: #AA0000;
            }
            QPushButton:disabled {
                background-color: #FFCCCC;
                border: 1px solid #FFAAAA;
                color: #FFFFFF;
            }
        """)
        camera_layout.addWidget(self.stop_btn, 1, 1)
        
        self.capture_btn = QPushButton("SNAP")
        self.capture_btn.clicked.connect(self.capture_photo)
        self.capture_btn.setEnabled(False)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                font-weight: bold;
                font-size: 9px;
                border: 1px solid #FFFFFF;
                padding: 3px;
                border-radius: 4px;
                min-height: 20px;
                max-height: 22px;
            }
            QPushButton:hover {
                background-color: #CC0000;
                border: 1px solid #FFD700;
            }
            QPushButton:pressed {
                background-color: #990000;
            }
            QPushButton:disabled {
                background-color: #FFCCCC;
                color: #FFFFFF;
                border: 1px solid #FFEEEE;
            }
        """)
        camera_layout.addWidget(self.capture_btn, 2, 0, 1, 2)
        
        camera_group.setLayout(camera_layout)
        controls_layout.addWidget(camera_group)
        
        # Effects group
        effects_group = QGroupBox("🎨 Effects")
        effects_layout = QGridLayout()
        effects_layout.setSpacing(6)
        effects_layout.setContentsMargins(10, 8, 10, 10)
        
        # Effect selection combo box
        self.effect_combo = QComboBox()
        
        # Add items with icons
        self.effect_combo.addItem("None")
        
        # Add effects with icons from emoji_icons folder
        effects_with_icons = [
            ("Maple Rain", "emoji_icons/maple_leaf.png"),
            ("Snow Fall", "emoji_icons/snowflake.png"),
            ("Hockey Sticks", "emoji_icons/hockey.png"),
            ("Beaver Dam", "emoji_icons/beaver.png"),
            ("Flag Frame", "emoji_icons/flag.png"),
            ("Tim Hortons", "emoji_icons/coffee.png"),
            ("Moose Trail", "emoji_icons/moose.png"),
            ("Northern Stars", "emoji_icons/star.png"),
            ("Smiley Rain", "emoji_icons/smiley.png")
        ]
        
        for effect_name, icon_path in effects_with_icons:
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.effect_combo.addItem(icon, effect_name)
            else:
                self.effect_combo.addItem(effect_name)
        self.effect_combo.currentIndexChanged.connect(self.change_effect)
        self.effect_combo.setEnabled(False)
        
        # Add combo box and arrow buttons in a horizontal layout
        effect_combo_layout = QHBoxLayout()
        effect_combo_layout.setSpacing(2)
        
        # Up arrow button
        self.effect_up_btn = QPushButton("▲")
        self.effect_up_btn.setMaximumWidth(20)
        self.effect_up_btn.setMaximumHeight(25)
        self.effect_up_btn.clicked.connect(lambda: self.change_combo_index(self.effect_combo, -1))
        self.effect_up_btn.setEnabled(False)
        self.effect_up_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 0px;
                background-color: #FFFFFF;
                border: none;
                color: #FF0000;
            }
            QPushButton:hover {
                background-color: #FFE0E0;
            }
            QPushButton:disabled {
                color: #CCCCCC;
            }
        """)
        
        # Down arrow button
        self.effect_down_btn = QPushButton("▼")
        self.effect_down_btn.setMaximumWidth(20)
        self.effect_down_btn.setMaximumHeight(25)
        self.effect_down_btn.clicked.connect(lambda: self.change_combo_index(self.effect_combo, 1))
        self.effect_down_btn.setEnabled(False)
        self.effect_down_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 0px;
                background-color: #FFFFFF;
                border: none;
                color: #FF0000;
            }
            QPushButton:hover {
                background-color: #FFE0E0;
            }
            QPushButton:disabled {
                color: #CCCCCC;
            }
        """)
        
        effect_combo_layout.addWidget(self.effect_combo)
        effect_combo_layout.addWidget(self.effect_up_btn)
        effect_combo_layout.addWidget(self.effect_down_btn)
        
        effects_layout.addLayout(effect_combo_layout, 0, 0, 1, 2)
        
        # Filter buttons
        self.red_filter_btn = QPushButton("🔴 Red Filter")
        self.red_filter_btn.clicked.connect(self.apply_red_filter)
        self.red_filter_btn.setEnabled(False)
        effects_layout.addWidget(self.red_filter_btn, 1, 0)
        
        self.hockey_filter_btn = QPushButton("🏒 Ice Blue")
        self.hockey_filter_btn.clicked.connect(self.apply_hockey_effect)
        self.hockey_filter_btn.setEnabled(False)
        effects_layout.addWidget(self.hockey_filter_btn, 1, 1)
        
        effects_group.setLayout(effects_layout)
        controls_layout.addWidget(effects_group)
        
        # Background group
        bg_group = QGroupBox("🏔️ Backgrounds")
        bg_layout = QGridLayout()
        bg_layout.setSpacing(6)
        bg_layout.setContentsMargins(10, 8, 10, 10)
        
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["None", "🍁 Maple Forest", "🇨🇦 Flag", "🏙️ Toronto", "💦 Niagara", "🔥 Campfire", "🏔️ Mountains", "🌌 Northern Lights"])
        self.bg_combo.currentIndexChanged.connect(self.change_background)
        # Disabled by default until model is downloaded/available
        self.bg_combo.setEnabled(False)
        self.bg_combo.setToolTip("AI model download required for backgrounds")
        
        # Add combo box and arrow buttons in a horizontal layout
        bg_combo_layout = QHBoxLayout()
        bg_combo_layout.setSpacing(2)
        
        # Up arrow button
        self.bg_up_btn = QPushButton("▲")
        self.bg_up_btn.setMaximumWidth(20)
        self.bg_up_btn.setMaximumHeight(25)
        self.bg_up_btn.clicked.connect(lambda: self.change_combo_index(self.bg_combo, -1))
        self.bg_up_btn.setEnabled(False)
        self.bg_up_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 0px;
                background-color: #FFFFFF;
                border: none;
                color: #FF0000;
            }
            QPushButton:hover {
                background-color: #FFE0E0;
            }
            QPushButton:disabled {
                color: #CCCCCC;
            }
        """)
        
        # Down arrow button
        self.bg_down_btn = QPushButton("▼")
        self.bg_down_btn.setMaximumWidth(20)
        self.bg_down_btn.setMaximumHeight(25)
        self.bg_down_btn.clicked.connect(lambda: self.change_combo_index(self.bg_combo, 1))
        self.bg_down_btn.setEnabled(False)
        self.bg_down_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 0px;
                background-color: #FFFFFF;
                border: none;
                color: #FF0000;
            }
            QPushButton:hover {
                background-color: #FFE0E0;
            }
            QPushButton:disabled {
                color: #CCCCCC;
            }
        """)
        
        bg_combo_layout.addWidget(self.bg_combo)
        bg_combo_layout.addWidget(self.bg_up_btn)
        bg_combo_layout.addWidget(self.bg_down_btn)
        
        bg_layout.addLayout(bg_combo_layout, 0, 0, 1, 2)
        
        bg_group.setLayout(bg_layout)
        controls_layout.addWidget(bg_group)
        
        # Quick fact group - make it wider
        fact_group = QGroupBox("🍁 Quick Fact")
        fact_group.setMinimumWidth(250)  # Set minimum width for wider display
        fact_layout = QVBoxLayout()
        fact_layout.setSpacing(0)
        fact_layout.setContentsMargins(5, 5, 5, 5)
        
        # Fact display label (single text label)
        self.fact_label = QLabel()
        self.fact_label.setAlignment(Qt.AlignCenter)
        self.fact_label.setWordWrap(True)
        self.fact_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 12px;
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """)
        
        fact_layout.addWidget(self.fact_label)
        
        fact_group.setLayout(fact_layout)
        controls_layout.addWidget(fact_group)
        controls_layout.setStretch(3, 1)  # Give more space to Quick Fact group
        
        main_layout.addWidget(controls_widget)
        
        # Footer label
        footer_label = QLabel("🍁 PROUDLY CANADIAN 🍁")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                color: #FF0000;
                font-weight: bold;
                font-size: 10px;
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid #FF0000;
                border-radius: 4px;
                padding: 3px;
                margin: 2px;
            }
        """)
        main_layout.addWidget(footer_label)
        
        # Initialize counters
        self.current_filter = None
        self.current_effect = None
        
        # Status label for notifications (hidden but kept for compatibility)
        self.status_label = QLabel()
        self.status_label.hide()
        
        # Initialize mascot display
        self.update_mascot_display()
        
        # Timer for rotating mascots
        self.mascot_timer = QTimer()
        self.mascot_timer.timeout.connect(self.update_mascot_display)
        self.mascot_timer.start(10000)  # Change every 10 seconds
        
    def update_mascot_display(self):
        """Update the mascot and phrase display"""
        mascot = random.choice(self.canadian_mascots)
        phrase = random.choice(self.canadian_phrases)
        
        # Create combined fact text
        fact_text = f"{mascot['emoji']} {mascot['name']}: {mascot['phrase']}\n\n\"{phrase}\""
        self.fact_label.setText(fact_text)
    
    def change_effect(self, index):
        """Change the current overlay effect"""
        effects = [
            None,  # None
            "maple_rain",
            "snow_fall",
            "hockey_sticks",
            "beaver_dam",
            "flag_frame",
            "tim_hortons",
            "moose_trail",
            "northern_stars",
            "smiley_rain"
        ]
        
        if index < len(effects):
            self.current_effect = effects[index]
            
            # Check for easter egg sequence
            if self.current_effect:
                self.secret_sequence.append(self.current_effect)
                # Keep only last 4 effects
                if len(self.secret_sequence) > 4:
                    self.secret_sequence.pop(0)
                
                # Check if secret sequence matches
                if self.secret_sequence == self.secret_code:
                    self.activate_easter_egg()
            if index == 0:
                self.status_label.setText("Effect: None")
            else:
                effect_names = self.effect_combo.itemText(index)
                self.status_label.setText(f"Effect: {effect_names}")
        
    @pyqtSlot(np.ndarray)
    def on_processed_frame(self, frame):
        """Handle processed frame from worker thread"""
        self.last_processed_frame = frame
        
    def detect_cameras(self):
        """Detect available cameras"""
        self.available_cameras = []
        self.camera_list = []
        
        # Cross-platform camera detection
        import platform
        system = platform.system()
        
        try:
            from PyQt5.QtMultimedia import QCameraInfo
            qt_cameras = QCameraInfo.availableCameras()
            
            if system == "Darwin":
                # macOS: Sort by UID to match OpenCV order
                sorted_cameras = sorted(qt_cameras, key=lambda c: c.deviceName())
            else:
                # Windows/Linux: Use Qt order as-is
                sorted_cameras = qt_cameras
            
            for idx, camera_info in enumerate(sorted_cameras):
                # Test if this camera works with OpenCV
                if system == "Windows":
                    # Windows: Use DirectShow backend for better compatibility
                    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(idx)
                    
                if cap.isOpened():
                    self.available_cameras.append(idx)
                    camera_name = camera_info.description()
                    self.camera_list.append((idx, camera_name))
                    print(f"{idx}: {camera_name} | uid={camera_info.deviceName()}")
                    cap.release()
                    
        except ImportError:
            print("QCameraInfo not available, using basic detection")
            # Fallback detection for all platforms
            max_cameras = 3 if system == "Darwin" else 5
            
            for i in range(max_cameras):
                try:
                    if system == "Windows":
                        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    else:
                        cap = cv2.VideoCapture(i)
                        
                    if cap.isOpened():
                        self.available_cameras.append(i)
                        self.camera_list.append((i, f"Camera {i}"))
                        cap.release()
                except:
                    continue
        
        # Add cameras to combo box
        if self.camera_list:
            for idx, name in self.camera_list:
                self.camera_combo.addItem(name)
            # Select first camera
            self.camera_combo.setCurrentIndex(0)
            self.current_camera = self.camera_list[0][0]
        else:
            self.camera_combo.addItem("No camera found - Grant permission & restart")
    
    def change_camera(self, index):
        """Change to selected camera"""
        if index >= 0 and index < len(self.camera_list):
            # Store recording state
            was_recording = self.is_recording
            
            # Stop current camera if running
            if self.is_recording:
                self.stop_camera()
            
            # Release current camera
            if self.cap:
                self.cap.release()
                self.cap = None
            
            # Update camera index from camera_list
            self.current_camera = self.camera_list[index][0]
            camera_name = self.camera_list[index][1]
            print(f"Switching to camera index {self.current_camera}: {camera_name}")
            
            # Setup new camera
            self.setup_camera()
            
            # Restart if was recording
            if was_recording:
                self.start_camera()
    
    def create_background_images(self):
        """Load Canadian-themed background images"""
        self.backgrounds = {}
        
        # Try to load real images first
        bg_files = {
            "maple": "backgrounds/maple_forest.jpg",
            "flag": "backgrounds/canada_flag.jpg",
            "toronto": "backgrounds/toronto_skyline.jpg",
            "niagara": "backgrounds/niagara_falls.jpg",
            "campfire": "backgrounds/campfire.jpg",
            "mountains": "backgrounds/rocky_mountains.jpg",
            "northern_lights": "backgrounds/northern_lights.jpg"
        }
        
        for name, filepath in bg_files.items():
            # Use resource_path for PyInstaller compatibility
            full_path = resource_path(filepath)
            if os.path.exists(full_path):
                img = cv2.imread(full_path)
                if img is not None:
                    # Resize to standard size
                    self.backgrounds[name] = cv2.resize(img, (640, 480))
                else:
                    # Fallback to generated backgrounds
                    self.backgrounds[name] = self._create_fallback_bg(name)
            else:
                # Fallback to generated backgrounds
                self.backgrounds[name] = self._create_fallback_bg(name)
    
    def load_emoji_icons(self):
        """Load emoji icons if available, otherwise use None"""
        self.emoji_icons = {}
        emoji_files = {
            "maple_leaf": "emoji_icons/maple_leaf.png",
            "snowflake": "emoji_icons/snowflake.png",
            "hockey": "emoji_icons/hockey.png",
            "coffee": "emoji_icons/coffee.png",
            "star": "emoji_icons/star.png",
            "flag": "emoji_icons/flag.png",
            "beaver": "emoji_icons/beaver.png",
            "moose": "emoji_icons/moose.png",
            "smiley": "emoji_icons/smiley.png"
        }
        
        for name, filepath in emoji_files.items():
            # Use resource_path for PyInstaller compatibility
            full_path = resource_path(filepath)
            if os.path.exists(full_path):
                img = cv2.imread(full_path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    self.emoji_icons[name] = img
                else:
                    self.emoji_icons[name] = None
            else:
                self.emoji_icons[name] = None
    
    def initialize_background_removal(self):
        """Initialize background removal with model download if needed"""
        logger.info("Initializing background removal...")
        try:
            # Check if model exists
            u2net_home = os.environ.get('U2NET_HOME', str(Path.home() / '.u2net'))
            model_path = Path(u2net_home) / f'{self.current_model}.onnx'
            logger.info(f"Checking for model at: {model_path}")
            
            if not model_path.exists():
                logger.info("Model not found, prompting user for download...")
                # Show download dialog
                reply = QMessageBox.question(
                    self, 
                    "🍁 AI Background Removal Setup",
                    "The AI background removal feature requires downloading a model (~180MB).\n\n"
                    "This is a one-time download that enables:\n"
                    "• Smart background removal\n"
                    "• Canadian scene backgrounds\n"
                    "• Professional selfie effects\n\n"
                    "Download now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.No:
                    logger.info("User declined model download")
                    # Disable background options
                    self.bg_combo.setEnabled(False)
                    self.bg_combo.setToolTip("AI model required for background removal")
                    self.status_label.setText("Background removal disabled - model not downloaded")
                    return
                
                # Create progress dialog
                self.progress_dialog = QProgressDialog(
                    "Downloading AI model...",
                    "Cancel",
                    0,
                    100,
                    self
                )
                self.progress_dialog.setWindowTitle("🍁 Canada Selfie - Model Download")
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setMinimumDuration(0)
                self.progress_dialog.setAutoReset(False)
                self.progress_dialog.setAutoClose(False)
                
                # Start download worker
                self.download_worker = ModelDownloadWorker(self.current_model)
                self.download_worker.progress.connect(self.on_download_progress)
                self.download_worker.finished.connect(self.on_download_finished)
                self.download_worker.start()
                
                self.progress_dialog.show()
            else:
                # Model exists, initialize directly
                logger.info(f"Model found, initializing background removal...")
                self._setup_background_removal()
                
        except Exception as e:
            logger.error(f"Error initializing background removal: {e}")
            logger.exception("Full traceback:")
    
    def on_download_progress(self, value, message):
        """Update download progress"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
    
    def on_download_finished(self, success, message):
        """Handle download completion"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        if success:
            QMessageBox.information(
                self,
                "Download Complete!",
                f"🍁 {message}\n\nBackground removal is now ready to use!"
            )
            self._setup_background_removal()
        else:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"❌ {message}\n\nBackground removal will not be available."
            )
    
    def _setup_background_removal(self):
        """Setup background removal session and worker"""
        try:
            logger.info("Setting up background removal session...")
            from rembg import new_session
            self.rembg_session = new_session(self.current_model)
            logger.info("✅ rembg session created successfully")
            
            # Initialize background removal worker
            self.bg_worker = BackgroundRemovalWorker(self.rembg_session)
            self.bg_worker.frame_ready.connect(self.on_processed_frame)
            self.bg_worker.start()
            
            self.bg_removal_available = True
            
            # Enable background combo if it was disabled
            if hasattr(self, 'bg_combo'):
                self.bg_combo.setEnabled(True)
                self.bg_up_btn.setEnabled(True)
                self.bg_down_btn.setEnabled(True)
                self.bg_combo.setToolTip("Select a Canadian background scene")
                
        except Exception as e:
            logger.error(f"❌ Failed to setup background removal: {e}")
            logger.exception("Full traceback:")
            global REMBG_AVAILABLE
            REMBG_AVAILABLE = False
            self.bg_removal_available = False
            
            # Disable background combo
            if hasattr(self, 'bg_combo'):
                self.bg_combo.setEnabled(False)
                self.bg_combo.setToolTip("AI model required for background removal")
    
    def overlay_emoji(self, frame, emoji_name, x, y, size=40):
        """Overlay an emoji icon on the frame"""
        if emoji_name in self.emoji_icons and self.emoji_icons[emoji_name] is not None:
            emoji = self.emoji_icons[emoji_name]
            # Resize emoji
            emoji_resized = cv2.resize(emoji, (size, size))
            
            # Get region of interest with bounds checking
            y1 = max(0, y - size//2)
            y2 = min(frame.shape[0], y + size//2)
            x1 = max(0, x - size//2)
            x2 = min(frame.shape[1], x + size//2)
            
            # Skip if completely out of bounds
            if y2 <= y1 or x2 <= x1:
                return False
            
            # Adjust emoji crop if partially out of bounds
            emoji_y1 = max(0, size//2 - y)
            emoji_y2 = emoji_y1 + (y2 - y1)
            emoji_x1 = max(0, size//2 - x)
            emoji_x2 = emoji_x1 + (x2 - x1)
            
            try:
                # Handle transparency if available
                if emoji_resized.shape[2] == 4:
                    # Extract alpha channel
                    emoji_crop = emoji_resized[emoji_y1:emoji_y2, emoji_x1:emoji_x2]
                    alpha = emoji_crop[:, :, 3] / 255.0
                    for c in range(3):
                        frame[y1:y2, x1:x2, c] = (1 - alpha) * frame[y1:y2, x1:x2, c] + alpha * emoji_crop[:, :, c]
                else:
                    # No transparency, just overlay
                    frame[y1:y2, x1:x2] = emoji_resized[emoji_y1:emoji_y2, emoji_x1:emoji_x2, :3]
                
                return True
            except:
                return False
        return False
    
    def _create_fallback_bg(self, name):
        """Create fallback backgrounds if images not found"""
        if name == "maple":
            return self.create_maple_leaf_bg()
        elif name == "flag":
            return self.create_canada_flag_bg()
        elif name == "toronto":
            return self.create_toronto_bg()
        elif name == "niagara":
            return self.create_niagara_bg()
        elif name == "campfire":
            return self.create_campfire_bg()
        elif name == "mountains":
            return self.create_mountains_bg()
        else:
            # Default background
            bg = np.ones((480, 640, 3), dtype=np.uint8) * 255
            bg[:, :] = [200, 150, 100]
            return bg
    
    def create_maple_leaf_bg(self):
        """Create maple leaf pattern background"""
        bg = np.ones((480, 640, 3), dtype=np.uint8) * 255
        # Red background
        bg[:, :] = [0, 0, 255]
        # Add maple leaf text pattern
        font = cv2.FONT_HERSHEY_SIMPLEX
        for y in range(0, 480, 80):
            for x in range(0, 640, 100):
                cv2.putText(bg, "MAPLE", (x, y), font, 1, (255, 255, 255), 2)
        return bg
    
    def create_canada_flag_bg(self):
        """Create Canada flag background"""
        bg = np.ones((480, 640, 3), dtype=np.uint8) * 255
        # Red bars on sides
        bg[:, :160] = [0, 0, 255]
        bg[:, 480:] = [0, 0, 255]
        # Add maple leaf text in center
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(bg, "CANADA", (240, 240), font, 2, (0, 0, 255), 3)
        return bg
    
    def create_toronto_bg(self):
        """Create Toronto skyline background"""
        bg = np.ones((480, 640, 3), dtype=np.uint8) * 255
        # Sky gradient
        for i in range(300):
            bg[i, :] = [255 - i//2, 150 - i//3, 100]
        # Simple skyline
        bg[300:, :] = [50, 50, 50]
        # CN Tower
        bg[100:300, 310:330] = [100, 100, 100]
        return bg
    
    def create_niagara_bg(self):
        """Create Niagara Falls background"""
        bg = np.ones((480, 640, 3), dtype=np.uint8) * 255
        # Blue water effect
        for i in range(480):
            bg[i, :] = [200 - i//4, 100 + i//4, 50]
        return bg
    
    def create_campfire_bg(self):
        """Create camping/firepit background"""
        bg = np.zeros((480, 640, 3), dtype=np.uint8)
        # Dark forest
        bg[:300, :] = [20, 40, 20]
        # Fire glow
        cv2.circle(bg, (320, 350), 100, (0, 100, 255), -1)
        cv2.circle(bg, (320, 350), 80, (0, 150, 255), -1)
        return bg
    
    def create_mountains_bg(self):
        """Create mountain background"""
        bg = np.ones((480, 640, 3), dtype=np.uint8) * 255
        # Sky
        bg[:300, :] = [200, 150, 100]
        # Mountains
        points = np.array([[0, 300], [200, 150], [400, 200], [640, 300], [640, 480], [0, 480]])
        cv2.fillPoly(bg, [points], (100, 100, 100))
        return bg
    
    def setup_camera(self):
        """Initialize camera"""
        try:
            if self.cap:
                self.cap.release()
            
            # Platform-specific camera initialization
            import platform
            if platform.system() == "Windows":
                # Windows: Use DirectShow backend for better compatibility
                self.cap = cv2.VideoCapture(self.current_camera, cv2.CAP_DSHOW)
                # Set buffer size to reduce latency on Windows
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                # macOS/Linux: Use default backend
                self.cap = cv2.VideoCapture(self.current_camera)
                
            if not self.cap.isOpened():
                self.show_error("Sorry buddy, couldn't access camera!\n\nIf this is your first time running the app, please:\n1. Grant camera permission when prompted\n2. Restart the app after granting permission\n\nThe app needs to restart to access the camera, eh!")
        except Exception as e:
            self.show_error(f"Camera error, eh: {str(e)}")
    
    def change_combo_index(self, combo, direction):
        """Change combo box index by direction (-1 for up, 1 for down)"""
        current_index = combo.currentIndex()
        new_index = current_index + direction
        
        # Ensure index is within bounds
        if 0 <= new_index < combo.count():
            combo.setCurrentIndex(new_index)
    
    def start_camera(self):
        """Start the camera feed"""
        if self.cap and self.cap.isOpened():
            self.timer.start(30)  # 30ms = ~33 FPS
            self.is_recording = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.capture_btn.setEnabled(True)
            self.effect_combo.setEnabled(True)
            self.effect_up_btn.setEnabled(True)
            self.effect_down_btn.setEnabled(True)
            self.red_filter_btn.setEnabled(True)
            self.hockey_filter_btn.setEnabled(True)
            self.status_label.setText("Camera rolling, eh!")
        else:
            self.show_error("Camera not available!")
    
    def stop_camera(self):
        """Stop the camera feed"""
        self.timer.stop()
        self.is_recording = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.capture_btn.setEnabled(False)
        self.effect_combo.setEnabled(False)
        self.red_filter_btn.setEnabled(False)
        self.hockey_filter_btn.setEnabled(False)
        self.video_label.setText("🍁 Camera stopped - Click Start! 🍁")
        self.status_label.setText("Camera stopped!")
    
    
    def update_frame(self):
        """Update video frame"""
        with sentry_sdk.start_transaction(op="video.frame_update", name="update_frame") as transaction:
            try:
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        # Flip frame horizontally for selfie effect
                        frame = cv2.flip(frame, 1)
                        
                        # Increment frame counter for animations
                        self.frame_counter += 1
                        
                        # Handle background removal with threading
                        with transaction.start_child(op="video.background_removal"):
                            if self.bg_removal_enabled and REMBG_AVAILABLE and self.current_bg is not None:
                                # Skip frames to reduce load (process 1 frame per second at 30 FPS)
                                self.frame_skip_counter += 1
                                if self.frame_skip_counter >= 30:  # Process every 30th frame (1 per second)
                                    self.frame_skip_counter = 0
                                    # Send frame to worker if queue is not full
                                    try:
                                        self.bg_worker.enabled = True
                                        self.bg_worker.input_queue.put_nowait((frame.copy(), self.current_bg))
                                    except queue.Full:
                                        pass
                                
                                # Use last processed frame if available
                                if self.last_processed_frame is not None:
                                    frame = self.last_processed_frame
                            else:
                                if self.bg_worker:
                                    self.bg_worker.enabled = False
                        
                        # Apply current filter
                        with transaction.start_child(op="video.apply_filter"):
                            if self.current_filter == "red":
                                frame = self.apply_red_filter_to_frame(frame)
                            elif self.current_filter == "hockey":
                                frame = self.apply_hockey_effect_to_frame(frame)
                        
                        # Apply current effect overlay
                        with transaction.start_child(op="video.apply_effect"):
                            if self.current_effect:
                                frame = self.apply_effect_overlay(frame)
                        
                        # Update fireworks (easter egg)
                        frame = self.update_fireworks(frame)
                        
                        # Convert to Qt format and display
                        with transaction.start_child(op="video.convert_display"):
                            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            h, w, ch = rgb_image.shape
                            bytes_per_line = ch * w
                            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                            
                            # Scale image to fit the label
                            pixmap = QPixmap.fromImage(qt_image)
                            scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.video_label.setPixmap(scaled_pixmap)
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.error(f"Error in update_frame: {e}")
                self.status_label.setText(f"Frame error: {str(e)}")
    
    def capture_photo(self):
        """Capture and save a photo"""
        with sentry_sdk.start_transaction(op="photo.capture", name="capture_photo") as transaction:
            try:
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        # Flip frame for selfie
                        frame = cv2.flip(frame, 1)
                        
                        # For photo capture, use the last processed frame if available
                        if self.bg_removal_enabled and REMBG_AVAILABLE and self.current_bg is not None:
                            if self.last_processed_frame is not None:
                                frame = self.last_processed_frame.copy()
                        
                        # Apply current filter
                        if self.current_filter == "red":
                            frame = self.apply_red_filter_to_frame(frame)
                        elif self.current_filter == "hockey":
                            frame = self.apply_hockey_effect_to_frame(frame)
                        
                        # Apply current effect overlay
                        if self.current_effect:
                            frame = self.apply_effect_overlay(frame)
                        
                        # Add "EH!" text overlay
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        cv2.putText(frame, "EH!", (50, 100), font, 3, (255, 255, 255), 5)
                        cv2.putText(frame, "EH!", (50, 100), font, 3, (0, 0, 255), 3)
                        
                        # Create filename with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"canada_selfie_{timestamp}.jpg"
                        
                        # Get Desktop path (cross-platform)
                        if platform.system() == 'Windows':
                            desktop_path = Path.home() / 'Desktop'
                        elif platform.system() == 'Darwin':  # macOS
                            desktop_path = Path.home() / 'Desktop'
                        else:  # Linux
                            desktop_path = Path.home() / 'Desktop'
                            if not desktop_path.exists():
                                # Some Linux systems use lowercase
                                desktop_path = Path.home() / 'desktop'
                                if not desktop_path.exists():
                                    # Fallback to home directory
                                    desktop_path = Path.home()
                        
                        # Create full path
                        full_path = desktop_path / filename
                        
                        # Save the photo
                        cv2.imwrite(str(full_path), frame)
                        
                        # Play Canadian sound if available
                        self.play_snap_sound()
                        
                        # Show random Canadian meme
                        meme = random.choice(self.canadian_memes)
                        self.status_label.setText(f"Saved: {filename}")
                        
                        # Show success message
                        QMessageBox.information(self, "Photo Saved, EH!", 
                                              f"🍁 {meme} 🍁\n\nSaved to Desktop as: {filename}")
                        
                        # Add custom event to Sentry
                        sentry_sdk.capture_message(f"Photo captured: {filename}", level="info")
            except Exception as e:
                sentry_sdk.capture_exception(e)
                logger.error(f"Error capturing photo: {e}")
                QMessageBox.critical(self, "Error", f"Failed to capture photo: {str(e)}")
    
    def toggle_maple_leaf(self):
        """Toggle maple leaf overlay"""
        self.maple_leaf_overlay = not self.maple_leaf_overlay
        status = "ON" if self.maple_leaf_overlay else "OFF"
        self.status_label.setText(f"Maple leaf {status}")
    
    def toggle_beaver_overlay(self):
        """Toggle beaver overlay"""
        self.beaver_overlay = not self.beaver_overlay
        status = "ON" if self.beaver_overlay else "OFF"
        self.status_label.setText(f"Beaver overlay {status}")
    
    def add_beaver_overlay(self, frame):
        """Add beaver graphics to frame"""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Add beaver emojis at various positions
        beaver_positions = [
            (w-100, 100),  # Top right
            (50, h-100),   # Bottom left
        ]
        
        for pos in beaver_positions:
            # Add beaver with shadow
            cv2.putText(frame, "BEAVER", (pos[0]+2, pos[1]+2), font, 1, (0, 0, 0), 3)
            cv2.putText(frame, "BEAVER", pos, font, 1, (139, 69, 19), 2)  # Brown color
            cv2.putText(frame, "DAM", (pos[0], pos[1]+30), font, 0.7, (255, 255, 255), 2)
        
        # Add "Dam Good!" text
        cv2.putText(frame, "DAM GOOD!", (w//2-80, h-50), font, 1, (255, 255, 255), 3)
        cv2.putText(frame, "DAM GOOD!", (w//2-80, h-50), font, 1, (139, 69, 19), 2)
        
        # Draw simple beaver tail pattern
        cv2.ellipse(frame, (w//2, h-150), (80, 40), 0, 0, 180, (139, 69, 19), -1)
        cv2.ellipse(frame, (w//2, h-150), (80, 40), 0, 0, 180, (0, 0, 0), 2)
        
        # Add grid pattern on tail
        for i in range(5):
            cv2.line(frame, (w//2-60+i*30, h-150), (w//2-60+i*30, h-130), (0, 0, 0), 1)
            cv2.line(frame, (w//2-80, h-150+i*10), (w//2+80, h-150+i*10), (0, 0, 0), 1)
        
        return frame
    
    def apply_red_filter(self):
        """Toggle red filter"""
        if self.current_filter == "red":
            self.current_filter = None
            self.status_label.setText("Red filter OFF")
        else:
            self.current_filter = "red"
            self.status_label.setText("Red filter ON!")
    
    def apply_hockey_effect(self):
        """Toggle hockey effect"""
        if self.current_filter == "hockey":
            self.current_filter = None
            self.status_label.setText("Ice Blue filter OFF")
        else:
            self.current_filter = "hockey"
            self.status_label.setText("Ice Blue filter ON!")
    
    def apply_effect_overlay(self, frame):
        """Apply the selected pattern overlay"""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        if self.current_effect == "maple_rain":
            # Falling maple leaves
            for i in range(15):
                x = np.random.randint(20, w-20)
                y = int((self.frame_counter * 3 + i * 100) % (h + 100) - 50)
                # Try emoji icon first, fallback to drawn shape
                if not self.overlay_emoji(frame, "maple_leaf", x, y, 50):
                    self.draw_maple_leaf(frame, x, y, 20, (0, 0, 255))
                
        elif self.current_effect == "snow_fall":
            # Falling snowflakes
            for i in range(25):
                x = np.random.randint(0, w)
                y = int((self.frame_counter * 2 + i * 80) % (h + 100) - 50)
                # Try emoji icon first, fallback to drawn shape
                if not self.overlay_emoji(frame, "snowflake", x, y, 35):
                    # Draw snowflake with blue/grey color for visibility
                    self.draw_snowflake(frame, x, y, 8, (200, 100, 0))
                
        elif self.current_effect == "hockey_sticks":
            # Hockey sticks pattern
            stick_positions = [(50, 100), (w-100, 100), (50, h-150), (w-100, h-150)]
            for pos in stick_positions:
                # Try emoji icon first, fallback to drawn shape
                if not self.overlay_emoji(frame, "hockey", pos[0], pos[1], 80):
                    self.draw_hockey_stick(frame, pos[0], pos[1], 40, (139, 69, 19))
                
        elif self.current_effect == "beaver_dam":
            # Beaver icons in corners
            corner_positions = [
                (50, 50),           # Top left
                (w-50, 50),         # Top right
                (50, h-50),         # Bottom left
                (w-50, h-50),       # Bottom right
                (w//2, 100)         # Top center
            ]
            
            for pos in corner_positions:
                if not self.overlay_emoji(frame, "beaver", pos[0], pos[1], 60):
                    # Fallback text if icon not loaded
                    cv2.putText(frame, "BEAVER", (pos[0]-40, pos[1]), font, 0.8, (139, 69, 19), 2)
            
            # Dam logs at bottom
            for i in range(0, w, 80):
                cv2.rectangle(frame, (i, h-60), (i+70, h-40), (101, 67, 33), -1)
                cv2.rectangle(frame, (i, h-60), (i+70, h-40), (61, 43, 31), 2)
                # Wood texture lines
                cv2.line(frame, (i+10, h-55), (i+60, h-55), (81, 53, 21), 1)
                cv2.line(frame, (i+10, h-45), (i+60, h-45), (81, 53, 21), 1)
            
            # DAM text in the middle
            cv2.putText(frame, "DAM GOOD!", (w//2-80, h-90), font, 1.5, (255, 255, 255), 3)
            cv2.putText(frame, "DAM GOOD!", (w//2-80, h-90), font, 1.5, (139, 69, 19), 2)
                
        elif self.current_effect == "flag_frame":
            # Canadian flags in corners
            corner_positions = [
                (50, 50),           # Top left
                (w-50, 50),         # Top right
                (50, h-50),         # Bottom left
                (w-50, h-50),       # Bottom right
            ]
            
            for pos in corner_positions:
                if not self.overlay_emoji(frame, "flag", pos[0], pos[1], 70):
                    # Fallback - draw maple leaf
                    self.overlay_emoji(frame, "maple_leaf", pos[0], pos[1], 50)
            
            # Add "TRUE NORTH" text
            cv2.putText(frame, "TRUE NORTH", (w//2-80, 50), font, 1, (255, 255, 255), 3)
            cv2.putText(frame, "TRUE NORTH", (w//2-80, 50), font, 1, (255, 0, 0), 2)
            
        elif self.current_effect == "tim_hortons":
            # Coffee cups and text
            cup_positions = [(100, 100), (w-150, 100), (w//2-25, h-100)]
            for pos in cup_positions:
                # Try emoji icon first, fallback to drawn shape
                if not self.overlay_emoji(frame, "coffee", pos[0], pos[1], 60):
                    self.draw_coffee_cup(frame, pos[0], pos[1], 30, (139, 69, 19))
            cv2.putText(frame, "Timmies Time!", (w//2-100, 50), font, 1, (255, 0, 0), 2)
            cv2.putText(frame, "Double Double", (w//2-100, h-50), font, 0.8, (139, 69, 19), 2)
            
        elif self.current_effect == "moose_trail":
            # Moose icons in different positions
            moose_positions = [
                (100, 100),
                (w-100, 100),
                (w//2, 200),
                (150, h-100),
                (w-150, h-100),
            ]
            
            for i, pos in enumerate(moose_positions):
                # Rotate moose slightly for variety
                if not self.overlay_emoji(frame, "moose", pos[0], pos[1], 70):
                    # Fallback - draw text
                    cv2.putText(frame, "MOOSE", (pos[0]-30, pos[1]), font, 0.8, (101, 67, 33), 2)
            
            # Add "EH!" text
            cv2.putText(frame, "MOOSE CROSSING EH!", (w//2-120, h-50), font, 1, (255, 255, 255), 3)
            cv2.putText(frame, "MOOSE CROSSING EH!", (w//2-120, h-50), font, 1, (101, 67, 33), 2)
                
        elif self.current_effect == "northern_stars":
            # Northern lights effect
            # Stars
            for i in range(15):
                x = np.random.randint(0, w)
                y = np.random.randint(0, h//3)
                # Try emoji icon first, fallback to drawn shape
                if not self.overlay_emoji(frame, "star", x, y, 25):
                    self.draw_star(frame, x, y, 5, (255, 255, 200))
            # Aurora colors overlay
            overlay = frame.copy()
            cv2.ellipse(overlay, (w//2, -50), (w, 200), 0, 0, 180, (0, 255, 100), -1)
            cv2.ellipse(overlay, (w//2, -30), (int(w*0.8), 150), 0, 0, 180, (0, 200, 255), -1)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            
        elif self.current_effect == "smiley_rain":
            # Falling smiley faces
            for i in range(20):
                x = np.random.randint(20, w-20)
                y = int((self.frame_counter * 3.5 + i * 90) % (h + 100) - 50)
                # Try emoji icon first, fallback to drawn smiley
                if not self.overlay_emoji(frame, "smiley", x, y, 40):
                    self.draw_smiley(frame, x, y, 20, (0, 255, 255))
        
        # Special easter egg effects
        if self.easter_egg_active:
            # Add MOUNTIE hat effect
            cv2.putText(frame, "MOUNTIE MODE", (10, 30), font, 0.7, (255, 255, 255), 3)
            cv2.putText(frame, "MOUNTIE MODE", (10, 30), font, 0.7, (255, 0, 0), 2)
            
            # Add Canadian flag corners
            for corner in [(10, 10), (w-60, 10), (10, h-30), (w-60, h-30)]:
                cv2.rectangle(frame, corner, (corner[0]+50, corner[1]+20), (255, 0, 0), -1)
                cv2.rectangle(frame, (corner[0]+17, corner[1]), (corner[0]+33, corner[1]+20), (255, 255, 255), -1)
                # Add maple leaf using overlay_emoji or draw it
                if not self.overlay_emoji(frame, "maple_leaf", corner[0]+25, corner[1]+10, 20):
                    self.draw_maple_leaf(frame, corner[0]+25, corner[1]+10, 8, (255, 0, 0))
            
        return frame
    
    def draw_maple_leaf(self, frame, x, y, size, color):
        """Draw a simple maple leaf shape"""
        # Simplified maple leaf using lines
        # Stem
        cv2.line(frame, (x, y+size), (x, y+size//2), color, 2)
        # Main body
        points = np.array([
            [x, y-size//2],
            [x-size//2, y-size//4],
            [x-size, y],
            [x-size//2, y],
            [x-size//3, y+size//3],
            [x, y+size//2],
            [x+size//3, y+size//3],
            [x+size//2, y],
            [x+size, y],
            [x+size//2, y-size//4],
            [x, y-size//2]
        ], np.int32)
        cv2.fillPoly(frame, [points], color)
        
    def draw_snowflake(self, frame, x, y, size, color):
        """Draw a snowflake shape"""
        # Six-pointed snowflake
        for angle in range(0, 360, 60):
            x2 = int(x + size * np.cos(np.radians(angle)))
            y2 = int(y + size * np.sin(np.radians(angle)))
            cv2.line(frame, (x, y), (x2, y2), color, 2)
            # Small branches
            x3 = int(x + size*0.6 * np.cos(np.radians(angle-20)))
            y3 = int(y + size*0.6 * np.sin(np.radians(angle-20)))
            cv2.line(frame, (x2, y2), (x3, y3), color, 1)
            x4 = int(x + size*0.6 * np.cos(np.radians(angle+20)))
            y4 = int(y + size*0.6 * np.sin(np.radians(angle+20)))
            cv2.line(frame, (x2, y2), (x4, y4), color, 1)
    
    def draw_hockey_stick(self, frame, x, y, size, color):
        """Draw a hockey stick shape"""
        # Stick shaft
        cv2.rectangle(frame, (x, y), (x+8, y+size), color, -1)
        # Blade
        blade_points = np.array([
            [x, y+size],
            [x+8, y+size],
            [x+20, y+size+15],
            [x+15, y+size+20],
            [x-5, y+size+10],
            [x, y+size]
        ], np.int32)
        cv2.fillPoly(frame, [blade_points], color)
        # Tape on blade
        cv2.line(frame, (x+2, y+size+5), (x+15, y+size+15), (255, 255, 255), 2)
        
    def draw_coffee_cup(self, frame, x, y, size, color):
        """Draw a coffee cup shape"""
        # Cup body
        cv2.rectangle(frame, (x-size//2, y), (x+size//2, y+size), color, -1)
        cv2.rectangle(frame, (x-size//2, y), (x+size//2, y+size), (0, 0, 0), 2)
        # Handle
        cv2.ellipse(frame, (x+size//2, y+size//2), (size//3, size//3), 0, -90, 90, color, 3)
        # Steam lines
        for i in range(3):
            x_steam = x - size//4 + i*size//4
            cv2.line(frame, (x_steam, y-5), (x_steam, y-15), (200, 200, 200), 2)
        # "TH" text on cup
        cv2.putText(frame, "TH", (x-10, y+size//2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def draw_star(self, frame, x, y, size, color):
        """Draw a star shape"""
        # Five-pointed star
        angle = -np.pi/2
        points = []
        for i in range(10):
            if i % 2 == 0:
                r = size
            else:
                r = size // 2
            px = int(x + r * np.cos(angle))
            py = int(y + r * np.sin(angle))
            points.append([px, py])
            angle += np.pi / 5
        points = np.array(points, np.int32)
        cv2.fillPoly(frame, [points], color)
    
    def draw_smiley(self, frame, x, y, size, color):
        """Draw a simple smiley face"""
        # Face circle
        cv2.circle(frame, (x, y), size, color, -1)
        cv2.circle(frame, (x, y), size, (0, 0, 0), 2)
        
        # Eyes
        eye_offset = size // 3
        eye_size = size // 8
        cv2.circle(frame, (x - eye_offset, y - eye_offset), eye_size, (0, 0, 0), -1)
        cv2.circle(frame, (x + eye_offset, y - eye_offset), eye_size, (0, 0, 0), -1)
        
        # Smile
        start_angle = 0
        end_angle = 180
        axes = (size // 2, size // 2)
        cv2.ellipse(frame, (x, y + eye_offset), axes, 0, start_angle, end_angle, (0, 0, 0), 2)
    
    def apply_red_filter_to_frame(self, frame):
        """Apply red color filter to frame"""
        # Increase red channel, decrease others
        frame[:,:,0] = np.clip(frame[:,:,0] * 0.3, 0, 255)  # Blue
        frame[:,:,1] = np.clip(frame[:,:,1] * 0.3, 0, 255)  # Green
        frame[:,:,2] = np.clip(frame[:,:,2] * 1.5, 0, 255)  # Red
        return frame
    
    def apply_hockey_effect_to_frame(self, frame):
        """Apply hockey-themed effect"""
        # Add blue tint and increase contrast
        frame[:,:,0] = np.clip(frame[:,:,0] * 1.3, 0, 255)  # Blue
        frame[:,:,1] = np.clip(frame[:,:,1] * 0.8, 0, 255)  # Green
        frame[:,:,2] = np.clip(frame[:,:,2] * 0.8, 0, 255)  # Red
        
        # Add some "ice" effect by increasing brightness in certain areas
        mask = np.random.random(frame.shape[:2]) > 0.95
        frame[mask] = np.clip(frame[mask] * 1.5, 0, 255)
        
        return frame
    
    def add_maple_leaf_overlay(self, frame):
        """Add maple leaf overlay to frame - improved version"""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Draw maple leafs (using special characters and text)
        maple_positions = [
            (30, 50), (w-150, 50), (30, h-30), (w-150, h-30),
            (w//2-60, 30), (w//2-60, h-50)
        ]
        
        for pos in maple_positions:
            # Use overlay_emoji instead of putText for emojis
            if not self.overlay_emoji(frame, "maple_leaf", pos[0], pos[1], 50):
                # Fallback - draw maple leaf shape
                self.draw_maple_leaf(frame, pos[0], pos[1], 25, (255, 0, 0))
        
        # Add Canadian phrases
        phrases = ["TRUE NORTH", "STRONG & FREE", "EH!", "CANADA"]
        y_offset = 100
        for phrase in random.sample(phrases, 2):
            cv2.putText(frame, phrase, (w//2 - len(phrase)*15, y_offset), 
                       font, 1, (255, 255, 255), 3)
            cv2.putText(frame, phrase, (w//2 - len(phrase)*15, y_offset), 
                       font, 1, (255, 0, 0), 2)
            y_offset += 50
        
        return frame
    
    
    
    def change_background(self, index):
        """Change background image"""
        bg_map = {
            1: "maple", 2: "flag", 3: "toronto", 
            4: "niagara", 5: "campfire", 6: "mountains",
            7: "northern_lights"
        }
        
        if index == 0:
            self.current_bg = None
            self.bg_removal_enabled = False
            self.last_processed_frame = None
            self.status_label.setText("Background: None")
        elif index in bg_map:
            # Check if we need to download the model first
            if REMBG_AVAILABLE and not self.bg_removal_available:
                # Initialize background removal which will prompt for download
                self.initialize_background_removal()
                if not self.bg_removal_available:
                    # User declined or download failed, reset combo
                    self.bg_combo.setCurrentIndex(0)
                    return
            
            self.current_bg = self.backgrounds[bg_map[index]]
            self.bg_removal_enabled = True
            bg_names = {
                "maple": "Maple Forest",
                "flag": "Canada Flag", 
                "toronto": "Toronto",
                "niagara": "Niagara Falls",
                "campfire": "Campfire",
                "mountains": "Mountains",
                "northern_lights": "Northern Lights"
            }
            self.status_label.setText(f"Background: {bg_names.get(bg_map[index], 'Custom')}")
    
    
    
    def play_snap_sound(self):
        """Play a snap sound with Canadian flair"""
        # You could add a sound file here
        pass
    
    def update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Removed as we don't have time_label in new UI
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error, Eh!", message)
        self.status_label.setText(f"Error: {message}")
    
    def activate_easter_egg(self):
        """Activate secret Canadian easter egg"""
        self.easter_egg_active = True
        self.secret_sequence = []  # Reset sequence
        
        # Start MASSIVE fireworks show!
        self.start_fireworks_show()
        
        # Show special message
        msg = QMessageBox()
        msg.setWindowTitle("🍁 SECRET CANADIAN ACHIEVEMENT UNLOCKED! 🍁")
        msg.setText("🎉 CONGRATULATIONS, EH! 🎉\n\n"
                   "You've discovered the SECRET CANADIAN SEQUENCE!\n\n"
                   "🍁 Maple Rain → ❄️ Snow Fall → 🏒 Hockey → 🦫 Beaver 🍁\n\n"
                   "You are now a TRUE CANADIAN, BUDDY!\n\n"
                   "Special bonus: Secret MOUNTIE mode activated!\n"
                   "Your photos will now have extra Canadian magic! 🇨🇦\n\n"
                   "🎆 ENJOY THE FIREWORKS SHOW! 🎆")
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #FF0000;
                color: white;
                font-size: 12px;
            }
            QMessageBox QLabel {
                color: white;
                font-weight: bold;
            }
        """)
        msg.exec_()
        
        # Update status
        self.status_label.setText("🍁 MOUNTIE MODE ACTIVATED! True Canadian detected! 🇨🇦")
        print("🍁 Easter egg activated! Secret Canadian sequence found!")
    
    def start_fireworks_show(self):
        """Start an epic fireworks show"""
        self.fireworks_active = True
        self.fireworks_timer = 300  # 10 seconds at 30fps
        self.fireworks = []
        
        # Create initial burst of fireworks
        for _ in range(5):
            self.add_random_firework()
    
    def add_random_firework(self):
        """Add a random firework to the show"""
        if hasattr(self, 'video_label'):
            # Get video dimensions
            w, h = 640, 480
            
            # Random position
            x = random.randint(50, w - 50)
            y = h - 50  # Start from bottom
            
            # Canadian colors!
            colors = [
                (0, 0, 255),    # Red
                (255, 255, 255), # White  
                (0, 0, 255),    # Red again for more red!
                (255, 215, 0),  # Gold
                (255, 255, 255), # White
                (0, 255, 255),  # Yellow
            ]
            color = random.choice(colors)
            
            firework = Firework(x, y, color)
            self.fireworks.append(firework)
    
    def update_fireworks(self, frame):
        """Update and draw fireworks"""
        if not self.fireworks_active:
            return frame
            
        h, w = frame.shape[:2]
        
        # Update existing fireworks
        self.fireworks = [fw for fw in self.fireworks if fw.update()]
        
        # Add new fireworks during the show
        if self.fireworks_timer > 0 and random.random() < 0.3:  # 30% chance each frame
            self.add_random_firework()
        
        # Draw all fireworks
        for firework in self.fireworks:
            firework.draw(frame)
        
        # No text during fireworks - just the fireworks display
        
        # Countdown timer
        self.fireworks_timer -= 1
        if self.fireworks_timer <= 0 and len(self.fireworks) == 0:
            self.fireworks_active = False
            
        return frame
    
    def keyPressEvent(self, event):
        """Handle key press events for Konami code easter egg"""
        # Konami code easter egg
        self.konami_sequence.append(event.key())
        
        # Keep only last 8 keys
        if len(self.konami_sequence) > 8:
            self.konami_sequence.pop(0)
        
        # Check if Konami code matches
        if self.konami_sequence == self.konami_code:
            self.activate_konami_easter_egg()
        
        # Pass event to parent
        super().keyPressEvent(event)
    
    def activate_konami_easter_egg(self):
        """Activate Konami code easter egg"""
        msg = QMessageBox()
        msg.setWindowTitle("🎮 CLASSIC GAMER DETECTED! 🎮")
        msg.setText("🎉 KONAMI CODE ACTIVATED! 🎉\n\n"
                   "↑↑↓↓←→←→\n\n"
                   "You've unlocked the RETRO CANADIAN mode!\n\n"
                   "Your selfies now have 30 extra lives and\n"
                   "unlimited maple syrup power-ups! 🍁\n\n"
                   "CHEAT CODE MASTER, EH!")
        msg.exec_()
        
        self.konami_sequence = []  # Reset
        print("🎮 Konami code easter egg activated!")
    
    def closeEvent(self, event):
        """Clean up when closing"""
        # Stop background worker
        if hasattr(self, 'bg_worker') and self.bg_worker:
            self.bg_worker.stop()
        
        if self.cap:
            self.cap.release()
        self.timer.stop()
        if hasattr(self, 'mascot_timer'):
            self.mascot_timer.stop()
        event.accept()

def main():
    # Initialize Sentry with full configuration
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn="https://bb63a53044b2492f7d111e5e648dfa1c@o4509594594246656.ingest.us.sentry.io/4509594622164992",
        integrations=[
            sentry_logging,
        ],
        # Add data like request headers and IP for users
        send_default_pii=True,
        # Performance Monitoring (APM)
        traces_sample_rate=1.0,  # Capture 100% of transactions for tracing
        # Profiling
        profiles_sample_rate=1.0,  # Profile 100% of sampled transactions
        # Release tracking
        release="canada-selfie-app@1.0.0",
        # Environment
        environment="production",
        # Attach stacktrace to messages
        attach_stacktrace=True,
        # Maximum breadcrumbs
        max_breadcrumbs=100,
        # Debug mode (set to False in production)
        debug=False,
        # Sample rate for error events
        sample_rate=1.0
    )
    
    # Set user context
    sentry_sdk.set_user({"id": platform.node()})
    
    # Set additional context
    sentry_sdk.set_context("app_info", {
        "version": "1.0.0",
        "platform": platform.system(),
        "python_version": sys.version
    })
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Canada Selfie Cam")
    app.setApplicationDisplayName("Canada Selfie Cam")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Canadian Software, Eh!")
    
    window = CanadaSelfieApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

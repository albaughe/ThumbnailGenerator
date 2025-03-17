import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QPushButton, QSlider, QColorDialog, 
                           QComboBox, QFileDialog, QMessageBox, QSpinBox,
                           QProgressDialog)
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QFontDatabase
from PySide6.QtCore import Qt, QByteArray
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import io
import re

class ThumbnailGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Batch Thumbnail Generator")
        self.setMinimumSize(1200, 800)
        
        # Initialize variables
        self.background_image = None
        self.background_color = QColor(215, 63, 9)  # Default orange
        self.text_color = QColor(255, 255, 255)  # Default white
        self.patterns = {}
        self.current_pattern = None
        self.pattern_opacity = 100  # Full opacity by default
        self.custom_fonts = {}
        self.pil_fonts = {}  # Store PIL font objects for different sizes
        self.text_margins = 100  # Default margin of 100px on each side
        self.line_spacing_factor = 0.3  # Default line spacing (30% of font size)
        
        # Load resources
        self.load_patterns()
        self.load_custom_fonts()
        
        # Create UI
        self.create_ui()
        
        # Generate initial preview
        self.update_preview()
        
    def load_patterns(self):
        """Load pattern overlays from the patterns directory"""
        patterns_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns")
        if not os.path.exists(patterns_dir):
            # Create the directory if it doesn't exist
            os.makedirs(patterns_dir)
            return
            
        for filename in os.listdir(patterns_dir):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                filepath = os.path.join(patterns_dir, filename)
                try:
                    self.patterns[filename] = Image.open(filepath).convert("RGBA")
                except Exception as e:
                    print(f"Error loading pattern {filename}: {e}")
    
    def load_custom_fonts(self):
        """Load custom fonts from the data directory"""
        fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        if not os.path.exists(fonts_dir):
            # Create the directory if it doesn't exist
            os.makedirs(fonts_dir)
            return
            
        # Create a font database to register fonts with Qt
        font_db = QFontDatabase()
        
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith((".ttf", ".otf")):
                filepath = os.path.join(fonts_dir, filename)
                try:
                    # Register font with Qt
                    font_id = font_db.addApplicationFont(filepath)
                    if font_id != -1:
                        font_families = font_db.applicationFontFamilies(font_id)
                        if font_families:
                            # Use the actual font family name from the file
                            font_family = font_families[0]
                            # Store mapping between displayed name and file path
                            name = os.path.splitext(filename)[0]
                            self.custom_fonts[name] = {
                                'path': filepath,
                                'family': font_family
                            }
                            print(f"Loaded font: {name} (family: {font_family})")
                except Exception as e:
                    print(f"Error loading font {filename}: {e}")
    
    def get_pil_font(self, font_name, size):
        """Get a PIL font object for the given font name and size"""
        # Create a cache key
        key = f"{font_name}_{size}"
        
        # Return cached font if available
        if key in self.pil_fonts:
            return self.pil_fonts[key]
        
        try:
            # Check if it's a custom font
            if font_name in self.custom_fonts:
                font_path = self.custom_fonts[font_name]['path']
                font = ImageFont.truetype(font_path, size)
            else:
                # Try as system font
                # Determine font file path based on platform
                font = ImageFont.truetype(font_name, size)
            
            # Cache the font
            self.pil_fonts[key] = font
            return font
        except Exception as e:
            print(f"Error loading font {font_name}: {e}")
            # Fall back to default font
            default_font = ImageFont.load_default()
            self.pil_fonts[key] = default_font
            return default_font
    
    def create_ui(self):
        """Create the application UI"""
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Left panel (controls)
        controls_widget = QWidget()
        controls_layout = QVBoxLayout()
        
        # Course name/number input
        course_label = QLabel("Course Number/Name:")
        self.course_input = QLineEdit("COURSE ###")
        self.course_input.textChanged.connect(self.update_preview)
        controls_layout.addWidget(course_label)
        controls_layout.addWidget(self.course_input)
        
        # Title template input
        title_label = QLabel("Title Template (use # for number):")
        self.title_input = QLineEdit("Week # Overview")
        self.title_input.textChanged.connect(self.update_preview)
        controls_layout.addWidget(title_label)
        controls_layout.addWidget(self.title_input)
        
        # Batch size settings
        batch_label = QLabel("Batch Settings:")
        self.start_number_label = QLabel("Start Number:")
        self.start_number = QSpinBox()
        self.start_number.setMinimum(1)
        self.start_number.setMaximum(1000)
        self.start_number.setValue(1)
        self.start_number.valueChanged.connect(self.update_preview)
        
        self.batch_count_label = QLabel("Number of Thumbnails:")
        self.batch_count = QSpinBox()
        self.batch_count.setMinimum(1)
        self.batch_count.setMaximum(100)
        self.batch_count.setValue(10)
        
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(self.start_number_label)
        batch_layout.addWidget(self.start_number)
        batch_layout.addWidget(self.batch_count_label)
        batch_layout.addWidget(self.batch_count)
        
        controls_layout.addWidget(batch_label)
        controls_layout.addLayout(batch_layout)
        
        # Font selection - custom implementation for limited fonts
        font_label = QLabel("Font:")
        self.font_combo = QComboBox()
        
        # Add custom fonts first
        # Set Stratum as default if available
        stratum_found = False
        for font_name in sorted(self.custom_fonts.keys()):
            self.font_combo.addItem(font_name)
            if font_name.lower().startswith("stratum"):
                stratum_found = True
                stratum_index = self.font_combo.count() - 1
        
        # Add system fonts (limited selection)
        system_fonts = ["Impact", "Arial", "Aptos", "Calibri"]
        for font in system_fonts:
            self.font_combo.addItem(font)
        
        # Set default to Stratum if available
        if stratum_found:
            self.font_combo.setCurrentIndex(stratum_index)
        
        self.font_combo.currentTextChanged.connect(self.update_preview)
        controls_layout.addWidget(font_label)
        controls_layout.addWidget(self.font_combo)
        
        # Font size
        font_size_label = QLabel("Font Size:")
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setMinimum(10)
        self.font_size_slider.setMaximum(200)
        self.font_size_slider.setValue(60)
        self.font_size_slider.valueChanged.connect(self.update_preview)
        controls_layout.addWidget(font_size_label)
        controls_layout.addWidget(self.font_size_slider)
        
        # Text margins
        margins_label = QLabel("Text Margins (pixels from edge):")
        self.margins_slider = QSlider(Qt.Horizontal)
        self.margins_slider.setMinimum(10)
        self.margins_slider.setMaximum(200)
        self.margins_slider.setValue(100)
        self.margins_slider.valueChanged.connect(self.update_text_margins)
        controls_layout.addWidget(margins_label)
        controls_layout.addWidget(self.margins_slider)
        
        # Line spacing
        line_spacing_label = QLabel("Line Spacing:")
        self.line_spacing_slider = QSlider(Qt.Horizontal)
        self.line_spacing_slider.setMinimum(0)
        self.line_spacing_slider.setMaximum(100)  # 0-100% of font size
        self.line_spacing_slider.setValue(30)  # 30% of font size as default
        self.line_spacing_slider.valueChanged.connect(self.update_line_spacing)
        controls_layout.addWidget(line_spacing_label)
        controls_layout.addWidget(self.line_spacing_slider)
        
        # Text color
        text_color_label = QLabel("Text Color:")
        self.text_color_button = QPushButton()
        self.text_color_button.setStyleSheet(f"background-color: {self.text_color.name()}")
        self.text_color_button.clicked.connect(self.choose_text_color)
        controls_layout.addWidget(text_color_label)
        controls_layout.addWidget(self.text_color_button)
        
        # Background color or image
        bg_label = QLabel("Background:")
        self.bg_color_button = QPushButton("Choose Color")
        self.bg_color_button.setStyleSheet(f"background-color: {self.background_color.name()}")
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        self.bg_image_button = QPushButton("Choose Image")
        self.bg_image_button.clicked.connect(self.choose_bg_image)
        self.clear_bg_button = QPushButton("Clear Image")
        self.clear_bg_button.clicked.connect(self.clear_background_image)
        
        bg_buttons_layout = QHBoxLayout()
        bg_buttons_layout.addWidget(self.bg_color_button)
        bg_buttons_layout.addWidget(self.bg_image_button)
        bg_buttons_layout.addWidget(self.clear_bg_button)
        
        controls_layout.addWidget(bg_label)
        controls_layout.addLayout(bg_buttons_layout)
        
        # Pattern overlay
        overlay_label = QLabel("Pattern Overlay:")
        self.overlay_combo = QComboBox()
        self.overlay_combo.addItem("None")
        self.overlay_combo.addItems(list(self.patterns.keys()))
        self.overlay_combo.currentTextChanged.connect(self.update_overlay)
        controls_layout.addWidget(overlay_label)
        controls_layout.addWidget(self.overlay_combo)
        
        # Pattern opacity slider
        pattern_opacity_label = QLabel("Pattern Opacity:")
        self.pattern_opacity_slider = QSlider(Qt.Horizontal)
        self.pattern_opacity_slider.setMinimum(0)
        self.pattern_opacity_slider.setMaximum(100)
        self.pattern_opacity_slider.setValue(100)
        self.pattern_opacity_slider.valueChanged.connect(self.update_pattern_opacity)
        controls_layout.addWidget(pattern_opacity_label)
        controls_layout.addWidget(self.pattern_opacity_slider)
        
        # Generate and Save button
        self.save_button = QPushButton("Generate and Save Thumbnails")
        self.save_button.clicked.connect(self.save_thumbnails)
        controls_layout.addWidget(self.save_button)
        
        # Set controls layout
        controls_widget.setLayout(controls_layout)
        controls_widget.setFixedWidth(400)
        
        # Right panel (preview)
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        
        preview_label = QLabel("Preview:")
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setMinimumSize(800, 600)
        self.preview_image.setStyleSheet("border: 1px solid #cccccc;")
        
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.preview_image)
        preview_widget.setLayout(preview_layout)
        
        # Add panels to main layout
        main_layout.addWidget(controls_widget)
        main_layout.addWidget(preview_widget)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def update_text_margins(self, value):
        """Update text margins and refresh preview"""
        self.text_margins = value
        self.update_preview()
    
    def update_line_spacing(self, value):
        """Update line spacing factor and refresh preview"""
        self.line_spacing_factor = value / 100.0  # Convert to decimal percentage
        self.update_preview()
    
    def choose_text_color(self):
        """Open color dialog for text color"""
        color = QColorDialog.getColor(self.text_color, self)
        if color.isValid():
            self.text_color = color
            self.text_color_button.setStyleSheet(f"background-color: {color.name()}")
            self.update_preview()
    
    def choose_bg_color(self):
        """Open color dialog for background color"""
        color = QColorDialog.getColor(self.background_color, self)
        if color.isValid():
            self.background_color = color
            self.bg_color_button.setStyleSheet(f"background-color: {color.name()}")
            self.update_preview()
    
    def choose_bg_image(self):
        """Open file dialog to select background image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            try:
                self.background_image = Image.open(file_path).convert("RGBA")
                self.update_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
    
    def clear_background_image(self):
        """Clear the background image and use color instead"""
        self.background_image = None
        self.update_preview()
    
    def update_overlay(self, pattern_name):
        """Update the overlay pattern"""
        if pattern_name == "None":
            self.current_pattern = None
        else:
            self.current_pattern = self.patterns.get(pattern_name)
        self.update_preview()
    
    def update_pattern_opacity(self, value):
        """Update the pattern opacity"""
        self.pattern_opacity = value
        self.update_preview()
    
    def wrap_text(self, text, font, max_width, draw):
        """Wrap text to fit within max_width pixels"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Try adding this word to the current line
            test_line = current_line + [word]
            test_text = ' '.join(test_line)
            
            # Get text width
            left, top, right, bottom = draw.textbbox((0, 0), test_text, font=font)
            text_width = right - left
            
            # If it's too wide, start a new line
            if text_width > max_width and current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line = test_line
        
        # Add the last line
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def generate_thumbnail(self, number, width=1200, height=675):
        """Generate the thumbnail image with the specified number"""
        # Create base image (from background image or color)
        if self.background_image:
            # Resize maintaining aspect ratio and crop to fit
            img = ImageOps.fit(self.background_image, (width, height), Image.Resampling.LANCZOS)
        else:
            # Create solid color background
            color = (self.background_color.red(), self.background_color.green(), 
                     self.background_color.blue(), 255)
            img = Image.new("RGBA", (width, height), color=color)
        
        # Apply pattern overlay with opacity if selected
        if self.current_pattern:
            pattern = self.current_pattern.resize((width, height))
            
            # Apply opacity to pattern
            if self.pattern_opacity < 100:
                alpha = ImageEnhance.Brightness(pattern.split()[3])
                alpha = alpha.enhance(self.pattern_opacity / 100)
                r, g, b, _ = pattern.split()
                pattern = Image.merge("RGBA", (r, g, b, alpha))
            
            # Apply pattern to background
            img = Image.alpha_composite(img, pattern)
        
        # Replace # with number in title template
        title_template = self.title_input.text()
        title = title_template.replace('#', str(number))
        
        # Get course name (if provided)
        course_name = self.course_input.text().strip()
        
        # Use just the title for display, but include course name in filename
        display_title = title
        filename_title = title
        if course_name:
            filename_title = f"{course_name} - {title}"
        
        # Add text
        draw = ImageDraw.Draw(img)
        
        # Get font
        font_name = self.font_combo.currentText()
        font_size = self.font_size_slider.value()
        
        # Get appropriate font
        font = self.get_pil_font(font_name, font_size)
            
        text_color = (self.text_color.red(), self.text_color.green(), 
                      self.text_color.blue(), 255)
        
        # Calculate the maximum width for text (width - margins on each side)
        max_text_width = width - (self.text_margins * 2)
        
        # Wrap the text - using display_title instead of full_title
        lines = self.wrap_text(display_title, font, max_text_width, draw)
        
        # Calculate total text height with line spacing
        line_spacing = int(font_size * self.line_spacing_factor)
        text_height = len(lines) * (font_size + line_spacing) - line_spacing  # Remove extra spacing after last line
        
        # Calculate vertical position (centered)
        y_position = (height - text_height) // 2
        
        # Draw each line of text
        for line in lines:
            # Center this line horizontally
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            line_width = right - left
            x_position = (width - line_width) // 2
            
            # Draw the line
            draw.text((x_position, y_position), line, font=font, fill=text_color)
            
            # Move to next line
            y_position += font_size + line_spacing
            
        return img, filename_title
    
    def update_preview(self):
        """Update the preview image with the start number"""
        try:
            # Generate thumbnail at preview size with the start number
            img, _ = self.generate_thumbnail(self.start_number.value(), 800, 450)
            
            # Convert PIL Image to QPixmap for display
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            image = QImage.fromData(QByteArray(buffer.read()))
            pixmap = QPixmap.fromImage(image)
            
            self.preview_image.setPixmap(pixmap)
            
        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Failed to generate preview: {str(e)}")
    
    def save_thumbnails(self):
        """Save multiple thumbnails based on batch settings"""
        try:
            # Ask for directory to save thumbnails
            save_dir = QFileDialog.getExistingDirectory(
                self, "Select Directory to Save Thumbnails"
            )
            
            if not save_dir:
                return
                
            start_num = self.start_number.value()
            count = self.batch_count.value()
            
            # Create progress dialog
            progress = QProgressDialog("Generating thumbnails...", "Cancel", 0, count, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            for i in range(count):
                # Check if user cancelled
                if progress.wasCanceled():
                    break
                    
                current_num = start_num + i
                progress.setValue(i)
                progress.setLabelText(f"Generating thumbnail {i+1} of {count}...")
                
                # Generate the thumbnail
                img, title = self.generate_thumbnail(current_num, 1280, 720)
                
                # Create filename
                filename = f"{title}_Thumbnail.png"
                file_path = os.path.join(save_dir, filename)
                
                # Save the thumbnail
                img.save(file_path)
                
            progress.setValue(count)
            QMessageBox.information(self, "Success", f"{count} thumbnails saved successfully!")
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save thumbnails: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = ThumbnailGenerator()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
import json
import os
from PyQt5.QtWidgets import (QApplication, QCheckBox, QSlider, QWidget,
                             QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PIL import Image


class ImageConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Image to WebP Converter')
        self.setGeometry(800, 400, 400, 200)

        layout = QVBoxLayout()

        # Add check box
        self.checkbox = QCheckBox('Keep ComfyUI workflow', self)
        layout.addWidget(self.checkbox)

        # Label for file selection
        self.file_label = QLabel('Select Images to Convert:', self)
        layout.addWidget(self.file_label)

        # Button for file selection
        self.file_button = QPushButton('Browse Images', self)
        self.file_button.clicked.connect(self.select_images)
        layout.addWidget(self.file_button)

        # Output directory selection
        self.output_label = QLabel('Select Output Directory:', self)
        layout.addWidget(self.output_label)

        # Button for output directory selection
        self.output_button = QPushButton('Browse Output Directory', self)
        self.output_button.clicked.connect(self.select_output_directory)
        layout.addWidget(self.output_button)

        # Input for quality selection
        self.quality_label = QLabel('Enter WebP Quality (1-100): 87', self)
        layout.addWidget(self.quality_label)

        self.quality_slider = QSlider(Qt.Horizontal, self)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(87)  # Default quality
        layout.addWidget(self.quality_slider)
        self.quality_slider.valueChanged.connect(self.update_quality_label)

        # Convert button
        self.convert_button = QPushButton('Convert to WebP', self)
        self.convert_button.clicked.connect(self.convert_images)
        layout.addWidget(self.convert_button)

        self.setLayout(layout)

    def update_quality_label(self):
        current_value = self.quality_slider.value()
        self.quality_label.setText(f'Enter WebP Quality (1-100): {current_value}')

    def select_images(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        self.file_paths, _ = QFileDialog.getOpenFileNames(self, 'Select Images', '',
                                                          'Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)',
                                                          options=options)
        if self.file_paths:
            self.file_label.setText(f'Selected {len(self.file_paths)} image(s)')

    def select_output_directory(self):
        self.output_dir = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
        if self.output_dir:
            self.output_label.setText(f'Selected Output Directory: {self.output_dir}')

    def convert_images(self):
        # Get quality input and validate
        try:
            quality = self.quality_slider.value()
            if quality < 1 or quality > 100:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, 'Error', 'Please enter a valid quality between 1 and 100.')
            return

        if not hasattr(self, 'file_paths') or not self.file_paths:
            QMessageBox.warning(self, 'Error', 'Please select at least one image file.')
            return

        if not hasattr(self, 'output_dir') or not self.output_dir:
            QMessageBox.warning(self, 'Error', 'Please select an output directory.')
            return

        self.convert_button.setEnabled(False)

        if self.checkbox.isChecked():
            self.convert_images_to_webp_with_metadata(self.file_paths, self.output_dir, quality)
        else:
            self.convert_images_to_webp(self.file_paths, self.output_dir, quality)

    def convert_images_to_webp(self, file_paths, output_dir, quality):
        renamed_files = []  # List to keep track of renamed files
        success = []

        for img_path in file_paths:
            try:
                img = Image.open(img_path)
                filename = os.path.basename(img_path)
                output_filename = os.path.splitext(filename)[0] + '.webp'
                output_path = os.path.join(output_dir, output_filename)

                # Check if file already exists
                if os.path.exists(output_path):
                    base_name = os.path.splitext(output_filename)[0]
                    counter = 1
                    # Find a new name by appending a number if it already exists
                    while os.path.exists(output_path):
                        output_filename = f"{base_name}_{counter}.webp"
                        output_path = os.path.join(output_dir, output_filename)
                        counter += 1

                    # Keep track of renamed files
                    renamed_files.append(f"{filename} -> {output_filename}")

                # Save the image as WebP
                img.save(output_path, 'webp', quality=quality)
                success.append(output_path)

            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to convert {filename}: {e}')
                continue

        # Prepare the message to show to the user
        if renamed_files:
            renamed_files_message = "\n".join(renamed_files)
            QMessageBox.information(self, 'Process Completed',
                                    f'Converted {len(file_paths)} image(s).\nThe output directory contained files '
                                    f'with identical names. \nThe following converted files have been renamed:\n'
                                    f'{renamed_files_message}')
        else:
            QMessageBox.information(self, 'Process Completed',
                                    f'Converted {len(success)} image(s).')

        # reset the label
        self.file_label.setText('Select Images to Convert:')
        # reset button
        self.convert_button.setEnabled(True)

    def convert_images_to_webp_with_metadata(self, file_paths, output_dir, quality):
        renamed_files = []  # List to keep track of renamed files
        success = []

        for img_path in file_paths:
            try:
                img = Image.open(img_path)
                filename = os.path.basename(img_path)
                output_filename = os.path.splitext(filename)[0] + '.webp'
                output_path = os.path.join(output_dir, output_filename)

                # Check if file already exists
                if os.path.exists(output_path):
                    base_name = os.path.splitext(output_filename)[0]
                    counter = 1
                    # Find a new name by appending a number if it already exists
                    while os.path.exists(output_path):
                        output_filename = f"{base_name}_{counter}.webp"
                        output_path = os.path.join(output_dir, output_filename)
                        counter += 1

                    # Keep track of renamed files
                    renamed_files.append(f"{filename} -> {output_filename}")

                # Saving
                if filename.lower().endswith(".png"):
                    # get info
                    try:
                        dict_of_info = img.info.copy()
                        # Remove nodes that may cause problems
                        try:
                            c = json.loads(dict_of_info.get("workflow"))
                            nodes: list = c.get('nodes')
                            for n in nodes:
                                if n['type'] == 'LoraInfo':
                                    nodes.remove(n)
                            dict_of_info['workflow'] = json.dumps(c)
                        except Exception as e:
                            print(e)
                            pass

                        # Saving
                        img_exif = img.getexif()
                        user_comment = dict_of_info.get("workflow", "")
                        img_exif[0x010e] = "Workflow:" + user_comment
                        img.convert("RGB").save(output_path, lossless=False,
                                               quality=quality, webp_method=6,
                                               exif=img_exif)
                        success.append(output_path)
                    except Exception as e:
                        print(e)
                else:
                    QMessageBox.warning(self, 'Error', f'Failed to convert {filename} with ComfyUi workflow.\n'
                                                       f'consider using png files with workflow or uncheck keep '
                                                       f'ComfyUI workflow')

            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Failed to convert {filename} \nWith ComfyUi workflow: {e} ')
                continue

        # Prepare the message to show to the user
        if renamed_files:
            renamed_files_message = "\n".join(renamed_files)
            QMessageBox.information(self, 'Process Completed',
                                    f'Converted {len(file_paths)} image(s).\nThe output directory contained files '
                                    f'with identical names. \nThe following converted files have been renamed:\n'
                                    f'{renamed_files_message}')
        else:
            QMessageBox.information(self, 'Process Completed',
                                    f'Converted {len(success)} image(s).')

        # reset the label
        self.file_label.setText('Select Images to Convert:')
        # reset button
        self.convert_button.setEnabled(True)

if __name__ == '__main__':
    app = QApplication([])
    window = ImageConverter()
    window.show()
    app.exec_()

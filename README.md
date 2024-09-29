# ComfyUi-webp-converter
### Image Converter to WebP with Metadata

## Summery
Image Converter to WebP with Metadata. ComfyUi-webp-converter is normal webp-converter tool to convert images to webp but with an additional option to keep ComfyUi workflow after conversion


## Description

This application allows users to convert images (primarily PNG files) to the WebP format while preserving metadata. It provides a simple GUI built with PyQt that enables users to select multiple images, specify the desired quality for the output WebP files, and choose whether to keep metadata from the original images. The application automatically handles filename conflicts by renaming files when necessary.

## Features

- Convert images from [PNG,JPG,JPEG,BMP,TIFF] to WebP format with selected quality.
- Preserve metadata from the original images (PNG only).
- Handle filename conflicts gracefully by renaming output files.
- User-friendly graphical interface for selecting images and specifying conversion settings.

## Prerequisites

Make sure you have the following installed:

- Python 3.6 or higher
- Pip (Python package installer)

## Installation
   1. Clone the repository or download the source code:
      ```
      git clone https://github.com/MohammadAboulEla/ComfyUi-webp-converter.git
      ```
   2. run `install.bat`
   3. start app from `run_app.vbs `

## Manual Installation

1. Clone the repository or download the source code:
   ```
   git clone https://github.com/MohammadAboulEla/ComfyUi-webp-converter.git
   cd <repository-directory>
   ```
2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - On Windows:
   ```
   python -m venv venv
   ```
   - On macOS/Linux:
   ```
   source venv/bin/activate
   ```
4. Install the required libraries:
   ```
   pip install Pillow PyQt5
   ```
5. Running the Application
   - Ensure your virtual environment is activated (if used).
   - Navigate to the directory containing the app.py file.
   - Run the application using Python
      ```
      python app.py
      ```

## Usage
1. Launch the application.
2. Select the images you wish to convert.
3. Specify the desired WebP quality using the slider.
4. Choose whether to keep the original metadata by checking the checkbox.
5. Click the "Convert" button to start the conversion process.
6. The application will inform you of any renamed files due to conflicts and will display a summary of the conversion results.

## Acknowledgments
- Pillow - For image processing.
- PyQt5 - For building the GUI.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing
Feel free to submit issues or pull requests for improvements, bug fixes, or new features!
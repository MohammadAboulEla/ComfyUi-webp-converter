import os
import json
import time
import threading
from PIL import Image

from PyQt5.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal, QSettings
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QSlider,
    QProgressBar,
    QSpinBox,
)


def safe_remove(path, retries=3):
    for _ in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError:
            time.sleep(0.1)
    os.remove(path)


# =========================
# Worker Task
# =========================


class ConvertTask(QRunnable):

    def __init__(self, controller, img_path):
        super().__init__()
        self.controller = controller
        self.img_path = img_path

    def run(self):
        ctrl = self.controller

        # Pause handling
        with ctrl.pause_cond:
            while ctrl.paused:
                ctrl.pause_cond.wait()

        # Cancel check AFTER pause
        if ctrl.cancelled:
            return

        webp_size = 0  # ensures safe scope

        try:
            orig_size = os.path.getsize(self.img_path)

            with Image.open(self.img_path) as img:
                img.load()  # 🔑 required on Windows

                base = os.path.splitext(os.path.basename(self.img_path))[0]
                output_path = ctrl.resolve_name(base)

                if ctrl.keep_metadata:
                    ctrl.save_with_metadata(img, self.img_path, output_path)
                else:
                    img.save(output_path, "webp", quality=ctrl.quality)

            # ⬅ image file is FULLY CLOSED here

            webp_size = os.path.getsize(output_path)
            if webp_size <= 0:
                raise RuntimeError("Empty WEBP")

            if ctrl.delete_originals:
                safe_remove(self.img_path)

            ctrl.task_finished(orig_size, webp_size)

        except Exception as e:
            ctrl.task_error(f"{os.path.basename(self.img_path)} → {e}")


# =========================
# Controller
# =========================


class JobController(QObject):
    progress = pyqtSignal(int)
    eta = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self, files, output_dir, quality, keep_metadata, delete_originals, max_workers
    ):
        super().__init__()

        self.files = files
        self.output_dir = output_dir
        self.quality = quality
        self.keep_metadata = keep_metadata
        self.delete_originals = delete_originals

        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_workers)

        self.total = len(files)
        self.completed = 0
        self.orig_bytes = 0
        self.webp_bytes = 0

        self.start_time = time.monotonic()

        self.cancelled = False
        self.paused = False
        self.pause_cond = threading.Condition()

    def start(self):
        for f in self.files:
            if self.cancelled:
                break
            self.pool.start(ConvertTask(self, f))

    def pause(self):
        with self.pause_cond:
            self.paused = True

    def resume(self):
        with self.pause_cond:
            self.paused = False
            self.pause_cond.notify_all()

    def cancel(self):
        self.cancelled = True

    def resolve_name(self, base):
        path = os.path.join(self.output_dir, f"{base}.webp")
        i = 1
        while os.path.exists(path):
            path = os.path.join(self.output_dir, f"{base}_{i}.webp")
            i += 1
        return path

    def save_with_metadata(self, img, img_path, output_path):
        if not img_path.lower().endswith(".png"):
            raise ValueError("Workflow requires PNG")

        info = img.info.copy()
        workflow = info.get("workflow")

        if workflow:
            try:
                data = json.loads(workflow)
                data["nodes"] = [
                    n for n in data.get("nodes", []) if n.get("type") != "LoraInfo"
                ]
                workflow = json.dumps(data)
            except Exception:
                pass

        exif = img.getexif()
        if workflow:
            exif[0x010E] = "Workflow:" + workflow

        img.convert("RGB").save(
            output_path, "webp", quality=self.quality, method=6, exif=exif
        )

    def task_finished(self, orig, webp):
        self.completed += 1
        self.orig_bytes += orig
        self.webp_bytes += webp

        percent = int((self.completed / self.total) * 100)
        self.progress.emit(percent)

        elapsed = time.monotonic() - self.start_time
        rate = self.completed / elapsed if elapsed else 0
        remaining = self.total - self.completed
        eta = remaining / rate if rate else 0

        self.eta.emit(time.strftime("%H:%M:%S", time.gmtime(eta)))

        if self.completed == self.total:
            self.finished.emit(
                {
                    "converted": self.completed,
                    "saved_bytes": self.orig_bytes - self.webp_bytes,
                }
            )

    def task_error(self, msg):
        self.error.emit(msg)


# =========================
# UI
# =========================


class ImageConverter(QWidget):

    def update_start_state(self):
        ready = (
            hasattr(self, "files")
            and self.files
            and hasattr(self, "output_dir")
            and self.output_dir
        )
        self.btn_start.setEnabled(bool(ready))

    def __init__(self):
        super().__init__()
        self.settings = QSettings("WebPTool", "ImageConverter")
        self.setWindowTitle("Image to WebP Converter")
        self.setGeometry(600, 400, 0, 0)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        # --- Main Layout Configuration ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        # Force the layout to expand items to full width
        layout.setAlignment(Qt.AlignTop)

        # --- 1. Labels for folders ---
        self.input_label = QLabel("Input folder: —")
        self.output_label = QLabel("Output folder: —")
        font = self.input_label.font()
        font.setPointSize(9)
        self.input_label.setFont(font)
        self.output_label.setFont(font)

        layout.addWidget(self.input_label)
        layout.addWidget(self.output_label)

        # --- 2. Options (Checkboxes) ---
        opts_layout = QHBoxLayout()
        self.keep_metadata = QCheckBox("Preserve ComfyUI workflow")
        self.delete_originals = QCheckBox("Delete originals")
        opts_layout.addWidget(self.keep_metadata)
        opts_layout.addWidget(self.delete_originals)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # --- 3. Sliders & Spinbox ---
        ctrl_layout = QHBoxLayout()
        self.quality_label = QLabel("Quality: 87")
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(87)
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"Quality: {v}")
        )

        self.workers = QSpinBox()
        self.workers.setRange(1, os.cpu_count() or 1)

        ctrl_layout.addWidget(self.quality_label)
        ctrl_layout.addWidget(
            self.quality_slider, 1
        )  # '1' makes it take all available space
        ctrl_layout.addSpacing(10)
        ctrl_layout.addWidget(QLabel("Workers:"))
        ctrl_layout.addWidget(self.workers)
        layout.addLayout(ctrl_layout)

        # --- 4. ETA & Progress Bar
        eta_layout = QHBoxLayout()
        self.eta_label = QLabel("ETA: --:--:--")
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setValue(0)
        self.label = QLabel("Status: No images selected")
        eta_layout.addWidget(self.eta_label)
        eta_layout.addWidget(self.progress)
        eta_layout.addWidget(self.label)
        layout.addLayout(eta_layout)

        # # --- 5. Status Text ---

        # layout.addWidget(self.label)

        # --- 6. Buttons ---
        btns_layout = QHBoxLayout()
        self.btn_files = QPushButton("Select Images")
        self.btn_output = QPushButton("Select Output")
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause")
        self.btn_resume = QPushButton("Resume")
        self.btn_cancel = QPushButton("Cancel")

        # Set initial states
        for btn in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_cancel):
            btn.setEnabled(False)

        # Add all buttons
        for b in (
            self.btn_files,
            self.btn_output,
            self.btn_start,
            self.btn_pause,
            self.btn_resume,
            self.btn_cancel,
        ):
            btns_layout.addWidget(b)

        layout.addLayout(btns_layout)

        # Connect signals
        self.btn_files.clicked.connect(self.select_files)
        self.btn_output.clicked.connect(self.select_output)
        self.btn_start.clicked.connect(self.start)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_resume.clicked.connect(self.resume)

    def _load_settings(self):
        self.quality_slider.setValue(self.settings.value("quality", 87, int))
        self.workers.setValue(
            self.settings.value("workers", max(1, (os.cpu_count() or 2) - 1), int)
        )
        self.keep_metadata.setChecked(self.settings.value("keep_meta", False, bool))
        self.delete_originals.setChecked(self.settings.value("delete", False, bool))

    def closeEvent(self, e):
        self.settings.setValue("quality", self.quality_slider.value())
        self.settings.setValue("workers", self.workers.value())
        self.settings.setValue("keep_meta", self.keep_metadata.isChecked())
        self.settings.setValue("delete", self.delete_originals.isChecked())
        super().closeEvent(e)

    def select_files(self):
        self.files, _ = QFileDialog.getOpenFileNames(
            self, "Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        self.label.setText(f"Status: {len(self.files)} images selected")
        if self.files:
            input_dir = os.path.dirname(self.files[0])
            self.input_label.setText(f"Input folder: {input_dir}")

            self.output_dir = input_dir
            self.output_label.setText(f"Output folder: {self.output_dir}")
        self.update_start_state()

    def select_output(self):
        self.output_dir = QFileDialog.getExistingDirectory(self, "Output directory")
        self.output_label.setText(f"Output folder: {self.output_dir}")
        self.update_start_state()

    def start(self):
        self.ctrl = JobController(
            self.files,
            self.output_dir,
            self.quality_slider.value(),
            self.keep_metadata.isChecked(),
            self.delete_originals.isChecked(),
            self.workers.value(),
        )

        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.btn_resume.setEnabled(False)

        self.btn_files.setEnabled(False)
        self.btn_output.setEnabled(False)
        self.ctrl.progress.connect(self.progress.setValue)
        self.ctrl.eta.connect(lambda s: self.eta_label.setText(f"ETA: {s}"))
        self.ctrl.error.connect(lambda m: QMessageBox.warning(self, "Error", m))
        self.ctrl.finished.connect(self.done)

        self.ctrl.start()
        self.btn_start.setEnabled(False)
        self.label.setText("Status: Converting...")

    def cancel(self):
        if hasattr(self, "ctrl"):
            self.ctrl.cancel()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_files.setEnabled(True)
            self.btn_output.setEnabled(True)
            self.update_start_state()
            self.label.setText("Status: Cancelled")

    def pause(self):
        if hasattr(self, "ctrl"):
            self.ctrl.pause()
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            self.label.setText("Status: Paused")

    def resume(self):
        if hasattr(self, "ctrl"):
            self.ctrl.resume()
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
            self.label.setText("Status: Converting...")

    def done(self, stats):
        saved_gb = round(stats["saved_bytes"] / (1024**3), 2)
        QMessageBox.information(self, "Done", f"Saved: {saved_gb} GB")

        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.update_start_state()
        self.btn_files.setEnabled(True)
        self.btn_output.setEnabled(True)
        self.label.setText("Status: Completed")


# =========================
# Entry
# =========================

if __name__ == "__main__":
    app = QApplication([])
    w = ImageConverter()
    w.show()
    app.exec_()

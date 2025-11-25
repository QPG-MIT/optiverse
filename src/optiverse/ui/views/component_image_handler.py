"""
Component Image Handler - Handles image loading, pasting, and asset management.

Extracted from ComponentEditor to reduce file size and improve separation of concerns.
"""
from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Optional, Callable

from PyQt6 import QtCore, QtGui, QtWidgets

from ...core.utils import slugify
from ...platform.paths import assets_dir

if TYPE_CHECKING:
    from ...objects.views import MultiLineCanvas


class ComponentImageHandler:
    """
    Handles all image-related operations for the component editor.
    
    This class manages:
    - Opening images from file dialogs
    - Pasting images from clipboard
    - Extracting pixmaps from mime data
    - Saving asset files (original and normalized)
    """
    
    # Supported image extensions
    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg")
    
    def __init__(
        self,
        canvas: "MultiLineCanvas",
        parent_widget: QtWidgets.QWidget,
        set_image_callback: Callable[[QtGui.QPixmap, Optional[str]], None],
        paste_json_callback: Callable[[], None],
    ):
        """
        Initialize the image handler.
        
        Args:
            canvas: The MultiLineCanvas for image operations
            parent_widget: Parent widget for dialogs
            set_image_callback: Callback to set image on canvas
            paste_json_callback: Callback for pasting JSON when no image found
        """
        self.canvas = canvas
        self.parent = parent_widget
        self._set_image = set_image_callback
        self._paste_json = paste_json_callback
    
    def open_image(self) -> bool:
        """
        Open image file dialog and load selected image.
        
        Returns:
            True if image was loaded successfully, False otherwise
        """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.svg)"
        )
        if not path:
            return False
        
        if path.lower().endswith(".svg"):
            # Import here to avoid circular import
            from ...objects.views import MultiLineCanvas
            pix = MultiLineCanvas._render_svg_to_pixmap(path)
            if not pix:
                QtWidgets.QMessageBox.warning(self.parent, "Load failed", "Invalid SVG.")
                return False
        else:
            pix = QtGui.QPixmap(path)
        
        self._set_image(pix, path)
        return True
    
    def paste_image(self) -> bool:
        """
        Paste image from clipboard.
        
        Returns:
            True if image was pasted successfully, False otherwise
        """
        cb = QtWidgets.QApplication.clipboard()
        mime = cb.mimeData()

        # 1) Direct bitmap/SVG bytes
        pix = self._pixmap_from_mime(mime)
        if pix is not None and not pix.isNull():
            self._set_image(pix, None)
            return True

        # 2) URLs
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    low = path.lower()
                    if low.endswith(self.IMAGE_EXTENSIONS):
                        if low.endswith(".svg"):
                            from ...objects.views import MultiLineCanvas
                            pix = MultiLineCanvas._render_svg_to_pixmap(path)
                            if pix:
                                self._set_image(pix, path)
                                return True
                        else:
                            pix = QtGui.QPixmap(path)
                            if not pix.isNull():
                                self._set_image(pix, path)
                                return True

        # 3) Plain text path
        text = cb.text().strip()
        if text and os.path.exists(text) and text.lower().endswith(self.IMAGE_EXTENSIONS):
            if text.lower().endswith(".svg"):
                from ...objects.views import MultiLineCanvas
                pix = MultiLineCanvas._render_svg_to_pixmap(text)
                if pix:
                    self._set_image(pix, text)
                    return True
            else:
                pix = QtGui.QPixmap(text)
                if not pix.isNull():
                    self._set_image(pix, text)
                    return True

        QtWidgets.QMessageBox.information(
            self.parent,
            "Paste Image",
            "Clipboard doesn't contain an image (PNG/JPEG/TIFF/SVG) or an image file path/URL."
        )
        return False

    def _pixmap_from_mime(self, mime: QtCore.QMimeData) -> Optional[QtGui.QPixmap]:
        """Extract pixmap from mime data."""
        if not mime:
            return None
        
        if mime.hasImage():
            img = mime.imageData()
            if isinstance(img, QtGui.QImage):
                return QtGui.QPixmap.fromImage(img)
            if isinstance(img, QtGui.QPixmap):
                return img
        
        for fmt in ("image/png", "image/jpeg", "image/jpg", "image/tiff", "image/x-qt-image"):
            if fmt in mime.formats():
                ba = mime.data(fmt)
                img = QtGui.QImage()
                if img.loadFromData(ba):
                    return QtGui.QPixmap.fromImage(img)
        
        if "image/svg+xml" in mime.formats():
            from ...objects.views import MultiLineCanvas
            svg_bytes = mime.data("image/svg+xml")
            pix = MultiLineCanvas._render_svg_to_pixmap(bytes(svg_bytes))
            if pix:
                return pix
        
        return None

    def smart_paste(self) -> None:
        """
        Smart paste: detect focus widget, try image, then JSON.
        
        Handles paste based on context:
        - If a text input is focused, paste as text
        - Otherwise try to paste as image
        - If no image, try to paste as JSON
        """
        fw = self.parent.focusWidget()
        if isinstance(fw, (QtWidgets.QLineEdit, QtWidgets.QPlainTextEdit, QtWidgets.QTextEdit)):
            fw.paste()
            return
        
        before = self.canvas.has_image()
        self.paste_image()
        after = self.canvas.has_image()
        
        if not after and not before:
            # No image pasted, try JSON
            self._paste_json()

    def on_image_dropped(self, pix: QtGui.QPixmap, path: str) -> None:
        """Handle image drop event."""
        self._set_image(pix, path or None)

    def ensure_asset_file(self, name: str) -> str:
        """
        Save asset file, preserving original format if possible.
        
        Args:
            name: Component name for the filename
            
        Returns:
            Path to the saved asset file
            
        Raises:
            RuntimeError: If no image is available
        """
        assets_folder = assets_dir()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = f"{slugify(name, separator='-')}-{stamp}"

        src_path = self.canvas.source_path()
        pix = self.canvas.current_pixmap()
        
        if src_path and os.path.exists(src_path):
            ext = os.path.splitext(src_path)[1].lower()
            if ext in self.IMAGE_EXTENSIONS:
                dst = os.path.join(assets_folder, base + ext)
                try:
                    with open(src_path, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                    return dst
                except OSError:
                    pass  # Fall through to PNG save if file copy fails
        
        if pix is None or pix.isNull():
            raise RuntimeError("No image available to save.")
        
        dst = os.path.join(assets_folder, base + ".png")
        pix.save(dst, "PNG")
        return dst
    
    def ensure_asset_file_normalized(self, name: str) -> str:
        """
        Save asset file normalized to 1000px height.
        
        Args:
            name: Component name for the filename
            
        Returns:
            Path to the saved normalized asset file
            
        Raises:
            RuntimeError: If no image is available
        """
        assets_folder = assets_dir()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = f"{slugify(name, separator='-')}-{stamp}"
        dst = os.path.join(assets_folder, base + ".png")
        
        pix = self.canvas.current_pixmap()
        if pix is None or pix.isNull():
            raise RuntimeError("No image available to save.")
        
        # Ensure device pixel ratio = 1.0 before scaling
        img = pix.toImage()
        img.setDevicePixelRatio(1.0)
        pix = QtGui.QPixmap.fromImage(img)
        
        # Normalize to 1000px height while preserving aspect ratio
        if pix.height() != 1000:
            pix = pix.scaledToHeight(1000, QtCore.Qt.TransformationMode.SmoothTransformation)
        
        # Ensure saved image has device pixel ratio = 1.0
        img = pix.toImage()
        img.setDevicePixelRatio(1.0)
        img.save(dst, "PNG")
        return dst


from __future__ import annotations

import json
import os
from typing import List, Dict, Any

from ..platform.paths import get_library_path
from ..core.models import serialize_component, deserialize_component


class StorageService:
    def __init__(self):
        self._lib_path = get_library_path()
        self._initialized = False

    def load_library(self) -> List[Dict[str, Any]]:
        """
        Load component library from disk.
        
        If the library file doesn't exist or is empty, it will be initialized
        with standard components from the ComponentRegistry.
        """
        path = self._lib_path
        
        # If library doesn't exist or is empty, initialize with standard components
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return self._initialize_library()
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return self._initialize_library()
            
            # If library is empty, populate with standard components
            if len(data) == 0:
                return self._initialize_library()

            # Normalize via deserialize (handles paths and migrations)
            # Note: We preserve absolute image paths for UI display, unlike save operations
            normalized: List[Dict[str, Any]] = []
            for row in data:
                rec = deserialize_component(row)
                if rec is None:
                    continue
                # Create dict manually to preserve absolute image_path
                # (serialize_component() would convert to relative for portability)
                component_dict = {
                    "name": rec.name,
                    "image_path": rec.image_path,  # Keep absolute for UI thumbnails
                    "object_height_mm": float(rec.object_height_mm),
                    "angle_deg": float(rec.angle_deg),
                    "notes": rec.notes or "",
                }
                # Include category if present
                if rec.category:
                    component_dict["category"] = rec.category
                if rec.interfaces:
                    component_dict["interfaces"] = [iface.to_dict() for iface in rec.interfaces]
                normalized.append(component_dict)
            return normalized if normalized else self._initialize_library()
        except Exception:
            # On error, initialize with standard components
            return self._initialize_library()

    def _initialize_library(self) -> List[Dict[str, Any]]:
        """
        Initialize library with standard components from ComponentRegistry.
        
        Returns:
            List of standard components
        """
        try:
            from ..objects.component_registry import ComponentRegistry
            standard_components = ComponentRegistry.get_standard_components()
            
            # Save the initialized library to disk
            self.save_library(standard_components)
            self._initialized = True
            
            return standard_components
        except Exception as e:
            # If we can't import ComponentRegistry, return empty list
            print(f"Warning: Could not initialize library with standard components: {e}")
            return []

    def save_library(self, rows: List[Dict[str, Any]]) -> None:
        """
        Save component library to disk.
        
        Args:
            rows: List of component dictionaries to save
        """
        tmp = self._lib_path + ".tmp"
        os.makedirs(os.path.dirname(self._lib_path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        os.replace(tmp, self._lib_path)
    
    def ensure_standard_components(self) -> None:
        """
        Ensure standard components are present in the library.
        
        If the library exists but is missing standard components,
        they will be added.
        """
        try:
            from ..objects.component_registry import ComponentRegistry
            
            # Load existing library
            existing = self.load_library()
            
            # Get standard components
            standard = ComponentRegistry.get_standard_components()
            
            # Track which standard components are already present
            existing_names = {comp.get("name") for comp in existing}
            
            # Add missing standard components
            added = False
            for std_comp in standard:
                if std_comp.get("name") not in existing_names:
                    existing.append(std_comp)
                    added = True
            
            # Save if we added anything
            if added:
                self.save_library(existing)
        except Exception as e:
            print(f"Warning: Could not ensure standard components: {e}")



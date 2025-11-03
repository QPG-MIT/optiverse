from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..platform.paths import (
    get_library_path,
    get_user_library_root,
    get_custom_library_path,
    get_builtin_library_root,
    to_absolute_path,
)
from ..core.models import (
    ComponentRecord,
    serialize_component,
    deserialize_component,
)


def slugify(name: str) -> str:
    """Convert component name to filesystem-safe folder name."""
    import re
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "component"


class StorageService:
    """
    Manages component library storage in folder-based structure.
    
    Each component is stored in its own folder:
        component_folder/
            component.json
            images/
                image_file.png
    
    Supports:
    - User library (default: Documents/Optiverse/ComponentLibraries/user_library/)
    - Custom library locations
    - Migration from legacy flat JSON format
    """
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize storage service.
        
        Args:
            library_path: Optional custom library path. If None, uses default user library.
        """
        if library_path:
            self._library_root = get_custom_library_path(library_path)
            if self._library_root is None:
                raise ValueError(f"Invalid library path: {library_path}")
        else:
            self._library_root = get_user_library_root()
        
        self._legacy_json_path = get_library_path()
        self._migrated = False
        
        # Check if migration is needed
        self._check_and_migrate()
    
    def _check_and_migrate(self) -> None:
        """Check if legacy flat JSON exists and migrate if needed."""
        legacy_path = Path(self._legacy_json_path)
        
        # If user library is empty and legacy JSON exists, migrate
        if self._is_library_empty() and legacy_path.exists() and legacy_path.stat().st_size > 0:
            print(f"[StorageService] Migrating from legacy JSON: {legacy_path}")
            self._migrate_from_legacy_json()
            self._migrated = True
    
    def _is_library_empty(self) -> bool:
        """Check if the current library has any components."""
        try:
            components = list(self._iter_component_folders())
            return len(components) == 0
        except Exception:
            return True
    
    def _migrate_from_legacy_json(self) -> None:
        """Migrate components from legacy flat JSON to folder structure."""
        try:
            legacy_path = Path(self._legacy_json_path)
            
            with open(legacy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                return
            
            migrated_count = 0
            for component_dict in data:
                try:
                    # Deserialize to ComponentRecord
                    rec = deserialize_component(component_dict)
                    if rec is None:
                        continue
                    
                    # Save to folder structure
                    self.save_component(rec)
                    migrated_count += 1
                except Exception as e:
                    print(f"[StorageService] Failed to migrate component: {e}")
                    continue
            
            # Backup the legacy JSON file
            backup_path = legacy_path.with_suffix(".json.backup")
            shutil.copy2(legacy_path, backup_path)
            print(f"[StorageService] Migrated {migrated_count} components. Legacy file backed up to: {backup_path}")
            
        except Exception as e:
            print(f"[StorageService] Migration failed: {e}")
    
    def _iter_component_folders(self) -> List[Path]:
        """Find all component folders in the library."""
        if not self._library_root.exists():
            return []
        
        folders = []
        for item in self._library_root.iterdir():
            if item.is_dir() and (item / "component.json").exists():
                folders.append(item)
        
        return folders
    
    def load_library(self) -> List[Dict[str, Any]]:
        """
        Load all components from the folder-based library.
        
        Returns:
            List of component dictionaries with absolute image paths for UI display
        """
        components: List[Dict[str, Any]] = []
        
        for folder in self._iter_component_folders():
            try:
                json_path = folder / "component.json"
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Resolve image path relative to component folder
                image_path = data.get("image_path", "")
                if image_path and not Path(image_path).is_absolute():
                    # Convert relative path to absolute (relative to component folder)
                    abs_image_path = (folder / image_path).resolve()
                    data["image_path"] = str(abs_image_path)
                
                # Deserialize and re-serialize to normalize
                rec = deserialize_component(data)
                if rec is None:
                    continue
                
                # Convert back to dict with absolute paths for UI
                component_dict = {
                    "name": rec.name,
                    "image_path": rec.image_path,  # Already absolute from deserialize
                    "object_height_mm": float(rec.object_height_mm),
                    "angle_deg": float(rec.angle_deg),
                    "notes": rec.notes or "",
                }
                
                if rec.category:
                    component_dict["category"] = rec.category
                
                if rec.interfaces:
                    component_dict["interfaces"] = [iface.to_dict() for iface in rec.interfaces]
                
                components.append(component_dict)
                
            except Exception as e:
                print(f"[StorageService] Failed to load component from {folder}: {e}")
                continue
        
        return components
    
    def save_component(self, rec: ComponentRecord) -> None:
        """
        Save a component to the folder-based library.
        
        Creates:
            {library_root}/{component_folder}/
                component.json
                images/
                    image_file.png
        
        Args:
            rec: ComponentRecord to save
        """
        # Generate folder name from component name
        folder_name = slugify(rec.name)
        component_folder = self._library_root / folder_name
        component_folder.mkdir(parents=True, exist_ok=True)
        
        # Create images subdirectory
        images_folder = component_folder / "images"
        images_folder.mkdir(exist_ok=True)
        
        # Handle image path
        saved_image_path = ""
        if rec.image_path:
            source_image = Path(rec.image_path)
            
            # Only copy if image exists and is not already in the component folder
            if source_image.exists():
                # Check if image is already in this component's images folder
                try:
                    source_image.resolve().relative_to(images_folder.resolve())
                    # Image is already in the right place
                    saved_image_path = f"images/{source_image.name}"
                except ValueError:
                    # Image is elsewhere, copy it
                    dest_image = images_folder / source_image.name
                    
                    # Handle name collision
                    counter = 1
                    while dest_image.exists() and not self._same_file(source_image, dest_image):
                        stem = source_image.stem
                        suffix = source_image.suffix
                        dest_image = images_folder / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    # Copy image
                    if not self._same_file(source_image, dest_image):
                        shutil.copy2(source_image, dest_image)
                    
                    saved_image_path = f"images/{dest_image.name}"
        
        # Create a copy of the record with relative image path
        serialized = serialize_component(rec)
        serialized["image_path"] = saved_image_path  # Store as relative path
        
        # Save component.json
        json_path = component_folder / "component.json"
        tmp_path = json_path.with_suffix(".json.tmp")
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)
        
        # Atomic replace
        tmp_path.replace(json_path)
    
    def _same_file(self, path1: Path, path2: Path) -> bool:
        """Check if two paths point to the same file."""
        try:
            return path1.resolve() == path2.resolve()
        except Exception:
            return False
    
    def delete_component(self, name: str) -> bool:
        """
        Delete a component from the library.
        
        Args:
            name: Name of the component to delete
        
        Returns:
            True if deleted, False if not found
        """
        folder_name = slugify(name)
        component_folder = self._library_root / folder_name
        
        if component_folder.exists() and component_folder.is_dir():
            shutil.rmtree(component_folder)
            return True
        
        return False
    
    def get_component(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific component by name.
        
        Args:
            name: Component name
        
        Returns:
            Component dictionary if found, None otherwise
        """
        folder_name = slugify(name)
        component_folder = self._library_root / folder_name
        json_path = component_folder / "component.json"
        
        if not json_path.exists():
            return None
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Resolve image path
            image_path = data.get("image_path", "")
            if image_path and not Path(image_path).is_absolute():
                abs_image_path = (component_folder / image_path).resolve()
                data["image_path"] = str(abs_image_path)
            
            return data
        except Exception:
            return None
    
    def export_component(self, name: str, destination: str) -> bool:
        """
        Export a component folder to a destination.
        
        Args:
            name: Component name
            destination: Destination directory path
        
        Returns:
            True if successful, False otherwise
        """
        folder_name = slugify(name)
        component_folder = self._library_root / folder_name
        
        if not component_folder.exists():
            return False
        
        try:
            dest_path = Path(destination)
            dest_path.mkdir(parents=True, exist_ok=True)
            
            dest_component = dest_path / folder_name
            
            # Copy entire component folder
            if dest_component.exists():
                shutil.rmtree(dest_component)
            
            shutil.copytree(component_folder, dest_component)
            return True
        except Exception as e:
            print(f"[StorageService] Export failed: {e}")
            return False
    
    def import_component(self, source_folder: str, overwrite: bool = False) -> bool:
        """
        Import a component from a folder.
        
        Args:
            source_folder: Path to component folder containing component.json
            overwrite: If True, overwrite existing component with same name
        
        Returns:
            True if successful, False otherwise
        """
        source_path = Path(source_folder)
        
        if not source_path.exists() or not source_path.is_dir():
            return False
        
        json_path = source_path / "component.json"
        if not json_path.exists():
            return False
        
        try:
            # Load component to get its name
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            component_name = data.get("name", "")
            if not component_name:
                return False
            
            folder_name = slugify(component_name)
            dest_folder = self._library_root / folder_name
            
            # Check if component already exists
            if dest_folder.exists() and not overwrite:
                return False
            
            # Remove existing if overwriting
            if dest_folder.exists():
                shutil.rmtree(dest_folder)
            
            # Copy the component folder
            shutil.copytree(source_path, dest_folder)
            return True
            
        except Exception as e:
            print(f"[StorageService] Import failed: {e}")
            return False
    
    def save_library(self, rows: List[Dict[str, Any]]) -> None:
        """
        Legacy method for backwards compatibility.
        
        Saves a list of component dictionaries to folder structure.
        Used by old code that expects flat JSON interface.
        
        Args:
            rows: List of component dictionaries
        """
        for row in rows:
            try:
                rec = deserialize_component(row)
                if rec:
                    self.save_component(rec)
            except Exception as e:
                print(f"[StorageService] Failed to save component: {e}")
    
    def ensure_standard_components(self) -> None:
        """
        Ensure standard components are loaded.
        
        Note: Standard components are now loaded from the built-in library,
        not copied to user library. This method is kept for backwards compatibility.
        """
        # No longer needed - standard components are loaded separately
        pass
    
    def get_library_root(self) -> Path:
        """Get the library root directory."""
        return self._library_root

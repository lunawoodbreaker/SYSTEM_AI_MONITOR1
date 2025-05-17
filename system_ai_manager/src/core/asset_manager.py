from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import json
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
import magic
import exifread
import cv2
import numpy as np
from PIL import Image
import pytesseract
import spacy
import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image

@dataclass
class AssetConfig:
    """Configuration for asset management."""
    base_dir: str
    supported_types: List[str]
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    enable_ai_analysis: bool = True
    enable_ocr: bool = True
    enable_image_recognition: bool = True
    enable_text_analysis: bool = True
    backup_enabled: bool = True
    encryption_enabled: bool = True

class AssetManager:
    """AI-driven digital asset management system."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = AssetConfig(
            base_dir="assets",
            supported_types=[
                "image/jpeg", "image/png", "image/gif",
                "application/pdf", "text/plain", "text/markdown",
                "application/json", "application/xml",
                "video/mp4", "audio/mpeg"
            ]
        )
        self.nlp = None
        self.image_model = None
        self.asset_index = {}
        self.initialize()
        
    def initialize(self):
        """Initialize the asset manager."""
        # Create base directory
        os.makedirs(self.config.base_dir, exist_ok=True)
        
        # Initialize AI models if enabled
        if self.config.enable_ai_analysis:
            self._initialize_ai_models()
            
        # Load or create asset index
        self._load_asset_index()
        
    def _initialize_ai_models(self):
        """Initialize AI models for asset analysis."""
        # Initialize spaCy for text analysis
        if self.config.enable_text_analysis:
            self.nlp = spacy.load("en_core_web_sm")
            
        # Initialize ResNet50 for image recognition
        if self.config.enable_image_recognition:
            self.image_model = ResNet50(
                weights='imagenet',
                include_top=False,
                pooling='avg'
            )
            
    def _load_asset_index(self):
        """Load or create asset index."""
        index_path = os.path.join(self.config.base_dir, "asset_index.json")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                self.asset_index = json.load(f)
        else:
            self.asset_index = {
                "assets": {},
                "tags": {},
                "categories": {},
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_assets": 0
                }
            }
            self._save_asset_index()
            
    def _save_asset_index(self):
        """Save asset index to disk."""
        index_path = os.path.join(self.config.base_dir, "asset_index.json")
        with open(index_path, "w") as f:
            json.dump(self.asset_index, f, indent=2)
            
    def add_asset(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a new asset to the system."""
        try:
            # Validate file
            if not self._validate_file(file_path):
                return {
                    "status": "error",
                    "error": "Invalid file"
                }
                
            # Generate asset ID
            asset_id = self._generate_asset_id(file_path)
            
            # Get file metadata
            file_metadata = self._get_file_metadata(file_path)
            
            # Analyze asset content
            content_analysis = self._analyze_asset_content(file_path)
            
            # Combine metadata
            asset_metadata = {
                "id": asset_id,
                "path": file_path,
                "type": file_metadata["type"],
                "size": file_metadata["size"],
                "created": file_metadata["created"],
                "modified": file_metadata["modified"],
                "analysis": content_analysis,
                "tags": content_analysis.get("tags", []),
                "categories": content_analysis.get("categories", []),
                "custom_metadata": metadata or {}
            }
            
            # Add to index
            self.asset_index["assets"][asset_id] = asset_metadata
            
            # Update tags and categories
            self._update_tags_and_categories(asset_metadata)
            
            # Update metadata
            self.asset_index["metadata"]["total_assets"] += 1
            self.asset_index["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # Save index
            self._save_asset_index()
            
            return {
                "status": "success",
                "asset_id": asset_id,
                "metadata": asset_metadata
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _validate_file(self, file_path: str) -> bool:
        """Validate file for asset management."""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False
                
            # Check file size
            if os.path.getsize(file_path) > self.config.max_file_size:
                return False
                
            # Check file type
            mime_type = magic.from_file(file_path, mime=True)
            if mime_type not in self.config.supported_types:
                return False
                
            return True
            
        except Exception:
            return False
            
    def _generate_asset_id(self, file_path: str) -> str:
        """Generate unique asset ID."""
        # Use file content hash as ID
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return file_hash[:16]
        
    def _get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata."""
        stat = os.stat(file_path)
        return {
            "type": magic.from_file(file_path, mime=True),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
        
    def _analyze_asset_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze asset content using AI."""
        analysis = {
            "tags": [],
            "categories": [],
            "text_content": None,
            "image_features": None,
            "metadata": {}
        }
        
        try:
            # Get file type
            mime_type = magic.from_file(file_path, mime=True)
            
            # Analyze based on file type
            if mime_type.startswith("image/"):
                analysis.update(self._analyze_image(file_path))
            elif mime_type.startswith("text/"):
                analysis.update(self._analyze_text(file_path))
            elif mime_type == "application/pdf":
                analysis.update(self._analyze_pdf(file_path))
            elif mime_type.startswith("video/"):
                analysis.update(self._analyze_video(file_path))
            elif mime_type.startswith("audio/"):
                analysis.update(self._analyze_audio(file_path))
                
            # Extract metadata
            analysis["metadata"] = self._extract_metadata(file_path)
            
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
        
    def _analyze_image(self, file_path: str) -> Dict[str, Any]:
        """Analyze image content."""
        analysis = {
            "tags": [],
            "categories": ["image"],
            "image_features": None,
            "text_content": None
        }
        
        try:
            # Load image
            img = image.load_img(file_path, target_size=(224, 224))
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = tf.keras.applications.resnet50.preprocess_input(x)
            
            # Extract features
            if self.image_model:
                features = self.image_model.predict(x)
                analysis["image_features"] = features.tolist()
                
            # Extract text using OCR
            if self.config.enable_ocr:
                text = pytesseract.image_to_string(Image.open(file_path))
                if text.strip():
                    analysis["text_content"] = text
                    
            # Extract EXIF data
            with open(file_path, 'rb') as f:
                exif = exifread.process_file(f)
                if exif:
                    analysis["metadata"]["exif"] = {
                        str(tag): str(value)
                        for tag, value in exif.items()
                    }
                    
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
        
    def _analyze_text(self, file_path: str) -> Dict[str, Any]:
        """Analyze text content."""
        analysis = {
            "tags": [],
            "categories": ["text"],
            "text_content": None
        }
        
        try:
            # Read text content
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                analysis["text_content"] = text
                
            # Analyze text if spaCy is available
            if self.nlp and text:
                doc = self.nlp(text)
                
                # Extract named entities
                entities = [ent.text for ent in doc.ents]
                analysis["tags"].extend(entities)
                
                # Extract key phrases
                key_phrases = [chunk.text for chunk in doc.noun_chunks]
                analysis["tags"].extend(key_phrases)
                
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
        
    def _analyze_pdf(self, file_path: str) -> Dict[str, Any]:
        """Analyze PDF content."""
        # Implement PDF analysis
        return {
            "tags": [],
            "categories": ["document"],
            "text_content": None
        }
        
    def _analyze_video(self, file_path: str) -> Dict[str, Any]:
        """Analyze video content."""
        analysis = {
            "tags": [],
            "categories": ["video"],
            "frames": []
        }
        
        try:
            # Open video file
            cap = cv2.VideoCapture(file_path)
            
            # Extract frames
            frame_count = 0
            while cap.isOpened() and frame_count < 10:  # Limit to 10 frames
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Analyze frame
                frame_analysis = self._analyze_image_frame(frame)
                analysis["frames"].append(frame_analysis)
                
                frame_count += 1
                
            cap.release()
            
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
        
    def _analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """Analyze audio content."""
        # Implement audio analysis
        return {
            "tags": [],
            "categories": ["audio"],
            "duration": None
        }
        
    def _analyze_image_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze a single video frame."""
        analysis = {
            "features": None,
            "objects": []
        }
        
        try:
            # Convert frame to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Prepare for model
            img = Image.fromarray(frame_rgb)
            img = img.resize((224, 224))
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = tf.keras.applications.resnet50.preprocess_input(x)
            
            # Extract features
            if self.image_model:
                features = self.image_model.predict(x)
                analysis["features"] = features.tolist()
                
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
        
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract file metadata."""
        metadata = {}
        
        try:
            # Get basic file info
            stat = os.stat(file_path)
            metadata.update({
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat()
            })
            
            # Get MIME type
            metadata["mime_type"] = magic.from_file(file_path, mime=True)
            
        except Exception as e:
            metadata["error"] = str(e)
            
        return metadata
        
    def _update_tags_and_categories(self, asset_metadata: Dict[str, Any]):
        """Update tags and categories in index."""
        # Update tags
        for tag in asset_metadata.get("tags", []):
            if tag not in self.asset_index["tags"]:
                self.asset_index["tags"][tag] = []
            self.asset_index["tags"][tag].append(asset_metadata["id"])
            
        # Update categories
        for category in asset_metadata.get("categories", []):
            if category not in self.asset_index["categories"]:
                self.asset_index["categories"][category] = []
            self.asset_index["categories"][category].append(asset_metadata["id"])
            
    def search_assets(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search for assets using AI-powered search."""
        try:
            results = []
            
            # Parse query
            if self.nlp:
                doc = self.nlp(query)
                query_terms = [token.text.lower() for token in doc if not token.is_stop]
            else:
                query_terms = query.lower().split()
                
            # Search assets
            for asset_id, asset in self.asset_index["assets"].items():
                score = self._calculate_search_score(asset, query_terms, filters)
                if score > 0:
                    results.append({
                        "asset_id": asset_id,
                        "metadata": asset,
                        "score": score
                    })
                    
            # Sort by score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return {
                "status": "success",
                "results": results,
                "total": len(results)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _calculate_search_score(self, asset: Dict[str, Any], query_terms: List[str], filters: Optional[Dict[str, Any]]) -> float:
        """Calculate search relevance score."""
        score = 0.0
        
        # Check filters
        if filters:
            if not self._check_filters(asset, filters):
                return 0.0
                
        # Check tags
        for tag in asset.get("tags", []):
            if tag.lower() in query_terms:
                score += 1.0
                
        # Check categories
        for category in asset.get("categories", []):
            if category.lower() in query_terms:
                score += 0.5
                
        # Check text content
        if asset.get("text_content"):
            text = asset["text_content"].lower()
            for term in query_terms:
                if term in text:
                    score += 0.3
                    
        return score
        
    def _check_filters(self, asset: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if asset matches filters."""
        for key, value in filters.items():
            if key not in asset:
                return False
            if asset[key] != value:
                return False
        return True
        
    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Get asset by ID."""
        try:
            if asset_id in self.asset_index["assets"]:
                return {
                    "status": "success",
                    "asset": self.asset_index["assets"][asset_id]
                }
            else:
                return {
                    "status": "error",
                    "error": "Asset not found"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def update_asset(self, asset_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update asset metadata."""
        try:
            if asset_id in self.asset_index["assets"]:
                # Update metadata
                self.asset_index["assets"][asset_id].update(metadata)
                
                # Update tags and categories
                self._update_tags_and_categories(self.asset_index["assets"][asset_id])
                
                # Save index
                self._save_asset_index()
                
                return {
                    "status": "success",
                    "asset": self.asset_index["assets"][asset_id]
                }
            else:
                return {
                    "status": "error",
                    "error": "Asset not found"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def delete_asset(self, asset_id: str) -> Dict[str, Any]:
        """Delete asset from system."""
        try:
            if asset_id in self.asset_index["assets"]:
                # Remove from index
                asset = self.asset_index["assets"].pop(asset_id)
                
                # Update tags and categories
                for tag in asset.get("tags", []):
                    if tag in self.asset_index["tags"]:
                        self.asset_index["tags"][tag].remove(asset_id)
                        if not self.asset_index["tags"][tag]:
                            del self.asset_index["tags"][tag]
                            
                for category in asset.get("categories", []):
                    if category in self.asset_index["categories"]:
                        self.asset_index["categories"][category].remove(asset_id)
                        if not self.asset_index["categories"][category]:
                            del self.asset_index["categories"][category]
                            
                # Update metadata
                self.asset_index["metadata"]["total_assets"] -= 1
                self.asset_index["metadata"]["last_updated"] = datetime.now().isoformat()
                
                # Save index
                self._save_asset_index()
                
                return {
                    "status": "success",
                    "message": "Asset deleted"
                }
            else:
                return {
                    "status": "error",
                    "error": "Asset not found"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 
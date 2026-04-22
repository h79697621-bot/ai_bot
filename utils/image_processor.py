import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging
from pathlib import Path

from exceptions import ImageProcessingError, OpenCVError
from .helpers import ProgressTracker

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Core image processing functionality using OpenCV"""
    
    def __init__(self):
        # Set OpenCV thread count for optimal performance
        cv2.setNumThreads(4)
    
    def adapt_image_to_grid(
        self, 
        image: np.ndarray, 
        grid_x: int, 
        grid_y: int, 
        method: str = "pad"
    ) -> np.ndarray:
        """
        Adapt image aspect ratio to match grid dimensions
        
        Args:
            image: Input image as numpy array
            grid_x: Number of columns in grid
            grid_y: Number of rows in grid
            method: Adaptation method - "pad", "stretch", "crop"
        
        Returns:
            Adapted image matching grid aspect ratio
        """
        try:
            current_height, current_width = image.shape[:2]
            current_ratio = current_width / current_height
            target_ratio = grid_x / grid_y
            
            logger.debug(f"Adapting image: {current_width}x{current_height} "
                        f"(ratio {current_ratio:.2f}) to grid {grid_x}x{grid_y} "
                        f"(ratio {target_ratio:.2f}) using method '{method}'")
            
            if method == "pad":
                return self._apply_padding(image, target_ratio)
            elif method == "stretch":
                return self._apply_stretching(image, target_ratio)
            elif method == "crop":
                return self._apply_crop_center(image, target_ratio)
            else:
                raise ImageProcessingError(f"Unknown adaptation method: {method}")
                
        except Exception as e:
            raise ImageProcessingError(f"Failed to adapt image to grid: {e}")
    
    def _apply_padding(
        self, 
        image: np.ndarray, 
        target_ratio: float, 
        fill_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """Smart padding to achieve target aspect ratio"""
        height, width = image.shape[:2]
        current_ratio = width / height
        
        if abs(current_ratio - target_ratio) < 0.01:
            return image
        
        if current_ratio < target_ratio:
            # Need to widen image
            new_width = int(height * target_ratio)
            padding_width = (new_width - width) // 2
            padded = cv2.copyMakeBorder(
                image, 0, 0, padding_width, padding_width,
                cv2.BORDER_CONSTANT, value=fill_color
            )
        else:
            # Need to heighten image
            new_height = int(width / target_ratio)
            padding_height = (new_height - height) // 2
            padded = cv2.copyMakeBorder(
                image, padding_height, padding_height, 0, 0,
                cv2.BORDER_CONSTANT, value=fill_color
            )
        
        return padded
    
    def _apply_stretching(self, image: np.ndarray, target_ratio: float) -> np.ndarray:
        """Non-uniform scaling to match target ratio"""
        height, width = image.shape[:2]
        new_width = int(height * target_ratio)
        return cv2.resize(image, (new_width, height), interpolation=cv2.INTER_LANCZOS4)
    
    def _apply_crop_center(self, image: np.ndarray, target_ratio: float) -> np.ndarray:
        """Center crop to match target ratio"""
        height, width = image.shape[:2]
        current_ratio = width / height
        
        if abs(current_ratio - target_ratio) < 0.01:
            return image
        
        if current_ratio > target_ratio:
            # Image is too wide, crop width
            new_width = int(height * target_ratio)
            start_x = (width - new_width) // 2
            cropped = image[:, start_x:start_x + new_width]
        else:
            # Image is too tall, crop height
            new_height = int(width / target_ratio)
            start_y = (height - new_height) // 2
            cropped = image[start_y:start_y + new_height, :]
        
        return cropped
    
    def split_image_grid(
        self, 
        image: np.ndarray, 
        grid_x: int, 
        grid_y: int,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[np.ndarray]:
        """
        Split adapted image into grid cells
        
        Args:
            image: Adapted image
            grid_x: Number of columns
            grid_y: Number of rows
            progress_tracker: Optional progress tracking
            
        Returns:
            List of grid cell images
        """
        try:
            height, width = image.shape[:2]
            
            cell_width = width // grid_x
            cell_height = height // grid_y
            
            cells = []
            total_cells = grid_x * grid_y
            
            logger.info(f"Splitting image into {total_cells} cells ({grid_x}x{grid_y})")
            
            for row in range(grid_y):
                for col in range(grid_x):
                    y_start = row * cell_height
                    y_end = (row + 1) * cell_height
                    x_start = col * cell_width
                    x_end = (col + 1) * cell_width
                    
                    cell = image[y_start:y_end, x_start:x_end]
                    
                    # Resize to emoji standard (512x512)
                    emoji_cell = self.resize_for_emoji(cell)
                    cells.append(emoji_cell)
                    
                    if progress_tracker:
                        progress_tracker.update(1, f"Processing cell {len(cells)}/{total_cells}")
            
            logger.info(f"Successfully split image into {len(cells)} emoji cells")
            return cells
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to split image into grid: {e}")
    
    def resize_for_emoji(self, image: np.ndarray, size: int = 100) -> np.ndarray:
        """
        Resize image to Telegram custom emoji standard (100x100)
        
        Args:
            image: Input image
            size: Target size (default 100 for custom emoji)
            
        Returns:
            Resized image
        """
        try:
            return cv2.resize(image, (size, size), interpolation=cv2.INTER_LANCZOS4)
        except Exception as e:
            raise OpenCVError(f"Failed to resize image for emoji: {e}")
    
    def enhance_image(self, image: np.ndarray, enhancement_level: str = "medium") -> np.ndarray:
        """
        Apply image enhancements
        
        Args:
            image: Input image
            enhancement_level: "low", "medium", "high"
            
        Returns:
            Enhanced image
        """
        try:
            enhanced = image.copy()
            
            if enhancement_level == "low":
                # Light Gaussian blur for noise reduction
                enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0.5)
                
            elif enhancement_level == "medium":
                # Bilateral filter for edge-preserving smoothing
                enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)
                
            elif enhancement_level == "high":
                # CLAHE for adaptive histogram equalization
                if len(enhanced.shape) == 3:
                    # Convert to LAB color space for better CLAHE results
                    lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    l = clahe.apply(l)
                    
                    enhanced = cv2.merge([l, a, b])
                    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                else:
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(enhanced)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Image enhancement failed, using original: {e}")
            return image
    
    def add_transparency(self, image: np.ndarray, method: str = "white") -> np.ndarray:
        """
        Add transparency to image by removing background
        
        Args:
            image: Input image
            method: Background removal method ("white", "edge", "auto")
            
        Returns:
            Image with alpha channel
        """
        try:
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Convert BGR to BGRA
                bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
            else:
                bgra = image.copy()
            
            if method == "white":
                # Remove white/light backgrounds
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
                bgra[:, :, 3] = 255 - mask
                
            elif method == "edge":
                # Use edge detection for background removal
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.dilate(edges, kernel, iterations=1)
                bgra[:, :, 3] = mask
            
            return bgra
            
        except Exception as e:
            logger.warning(f"Transparency addition failed: {e}")
            return image
    
    def load_image(self, file_path: Path) -> np.ndarray:
        """
        Load image from file using OpenCV
        
        Args:
            file_path: Path to image file
            
        Returns:
            Loaded image as numpy array
        """
        try:
            image = cv2.imread(str(file_path))
            if image is None:
                raise ImageProcessingError(f"Could not load image: {file_path}")
            
            logger.debug(f"Loaded image: {file_path} ({image.shape})")
            return image
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to load image {file_path}: {e}")
    
    def save_image(self, image: np.ndarray, file_path: Path, quality: int = 85) -> bool:
        """
        Save image to file
        
        Args:
            image: Image to save
            file_path: Output file path
            quality: JPEG quality (0-100)
            
        Returns:
            True if successful
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Set compression parameters optimized for emoji files
            if file_path.suffix.lower() == '.jpg' or file_path.suffix.lower() == '.jpeg':
                params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            elif file_path.suffix.lower() == '.png':
                # Use higher compression for PNG to reduce file size
                compression_level = max(6, 9 - (quality // 15))  # Range 6-9 for better compression
                params = [cv2.IMWRITE_PNG_COMPRESSION, compression_level]
            else:
                params = []
            
            success = cv2.imwrite(str(file_path), image, params)
            if not success:
                raise OpenCVError(f"OpenCV failed to save image: {file_path}")
            
            logger.debug(f"Saved image: {file_path}")
            return True
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to save image {file_path}: {e}")
    
    def calculate_target_dimensions(
        self, 
        grid_x: int, 
        grid_y: int, 
        base_size: int = 512
    ) -> Tuple[int, int]:
        """
        Calculate optimal image dimensions for grid
        
        Args:
            grid_x: Number of columns
            grid_y: Number of rows
            base_size: Base size for each cell
            
        Returns:
            (width, height) tuple
        """
        width = grid_x * base_size
        height = grid_y * base_size
        return width, height
import cv2
import numpy as np
from typing import List, Optional, Tuple, Dict
import logging
from pathlib import Path
import zipfile
import json
import time
import subprocess
import tempfile
import shutil

from exceptions import ImageProcessingError
from .helpers import safe_filename, ProgressTracker
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class EmojiGenerator:
    """Generate Telegram-compatible emoji packs"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
    
    def create_emoji_pack(
        self, 
        images: List[np.ndarray], 
        pack_name: str,
        user_id: int,
        output_dir: Path,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[Path]:
        """
        Generate Telegram sticker pack from images
        
        Args:
            images: List of processed emoji images
            pack_name: Name for the emoji pack
            user_id: User ID for file naming
            output_dir: Directory to save emoji files
            progress_tracker: Optional progress tracking
            
        Returns:
            List of saved emoji file paths
        """
        try:
            if not images:
                raise ImageProcessingError("No images provided for emoji pack")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe pack name
            safe_pack_name = safe_filename(pack_name)
            
            saved_files = []
            total_images = len(images)
            
            logger.info(f"Creating emoji pack '{safe_pack_name}' with {total_images} emojis")
            
            for i, image in enumerate(images):
                # Optimize image for Telegram
                optimized_image = self.optimize_emoji_size(image)
                
                # Generate filename
                emoji_filename = f"{safe_pack_name}_emoji_{i+1:03d}.png"
                emoji_path = output_dir / emoji_filename
                
                # Save emoji
                success = self.image_processor.save_image(optimized_image, emoji_path, quality=95)
                if success:
                    saved_files.append(emoji_path)
                    logger.debug(f"Saved emoji: {emoji_path}")
                else:
                    logger.warning(f"Failed to save emoji: {emoji_path}")
                
                if progress_tracker:
                    progress_tracker.update(1, f"Generated emoji {i+1}/{total_images}")
            
            # Create pack metadata
            metadata_path = output_dir / f"{safe_pack_name}_metadata.json"
            self._create_pack_metadata(saved_files, pack_name, user_id, metadata_path)
            
            logger.info(f"Successfully created emoji pack with {len(saved_files)} emojis")
            return saved_files
            
        except Exception as e:
            # Clean up any partially created files
            if 'output_dir' in locals() and output_dir.exists():
                try:
                    # Clean up individual emoji files
                    if 'saved_files' in locals():
                        for file_path in saved_files:
                            try:
                                if file_path.exists():
                                    file_path.unlink()
                            except:
                                pass
                    
                    # Clean up metadata file if it exists
                    if 'safe_pack_name' in locals():
                        metadata_path = output_dir / f"{safe_pack_name}_metadata.json"
                        if metadata_path.exists():
                            metadata_path.unlink()
                    
                    logger.debug(f"Cleaned up partially created emoji files in: {output_dir}")
                    
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup emoji files after error: {cleanup_error}")
            
            raise ImageProcessingError(f"Failed to create emoji pack: {e}")
    
    def optimize_emoji_size(self, image: np.ndarray, target_size: int = 100) -> np.ndarray:
        """
        Optimize image size and quality for Telegram custom emoji
        
        Args:
            image: Input image
            target_size: Target size (100x100 for custom emoji)
            
        Returns:
            Optimized image
        """
        try:
            # Ensure image is the right size
            if image.shape[:2] != (target_size, target_size):
                optimized = cv2.resize(image, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
            else:
                optimized = image.copy()
            
            # Ensure image has proper format (BGR or BGRA)
            if len(optimized.shape) == 3:
                if optimized.shape[2] == 3:
                    # BGR image - add alpha channel for PNG
                    optimized = cv2.cvtColor(optimized, cv2.COLOR_BGR2BGRA)
                elif optimized.shape[2] == 4:
                    # Already BGRA
                    pass
                else:
                    raise ImageProcessingError(f"Unexpected image format: {optimized.shape}")
            else:
                # Grayscale - convert to BGRA
                optimized = cv2.cvtColor(optimized, cv2.COLOR_GRAY2BGRA)
            
            return optimized
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to optimize emoji size: {e}")
    
    def add_transparency(
        self, 
        image: np.ndarray, 
        method: str = "white",
        threshold: int = 240
    ) -> np.ndarray:
        """
        Add transparency to emoji by removing background
        
        Args:
            image: Input image
            method: Background removal method ("white", "black", "edge")
            threshold: Threshold for background detection
            
        Returns:
            Image with transparency
        """
        try:
            # Ensure image has alpha channel
            if len(image.shape) == 3 and image.shape[2] == 3:
                bgra = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
            else:
                bgra = image.copy()
            
            if method == "white":
                # Remove white/light backgrounds
                gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
                bgra[:, :, 3] = 255 - mask
                
            elif method == "black":
                # Remove black/dark backgrounds
                gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray, 255 - threshold, 255, cv2.THRESH_BINARY_INV)
                bgra[:, :, 3] = 255 - mask
                
            elif method == "edge":
                # Use edge detection for better background removal
                gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
                
                # Apply Gaussian blur to reduce noise
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                
                # Edge detection
                edges = cv2.Canny(blurred, 50, 150)
                
                # Dilate edges to create mask
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.dilate(edges, kernel, iterations=2)
                
                # Fill holes in the mask
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.fillPoly(mask, contours, 255)
                
                bgra[:, :, 3] = mask
            
            return bgra
            
        except Exception as e:
            logger.warning(f"Transparency addition failed: {e}")
            return image
    
    def enhance_emoji_quality(self, image: np.ndarray) -> np.ndarray:
        """
        Apply quality enhancements specific to emoji
        
        Args:
            image: Input emoji image
            
        Returns:
            Enhanced emoji image
        """
        try:
            enhanced = image.copy()
            
            # Sharpen the image slightly for better emoji clarity
            kernel = np.array([[-0.5, -0.5, -0.5],
                              [-0.5,  5.0, -0.5],
                              [-0.5, -0.5, -0.5]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            
            # Slight contrast enhancement
            alpha = 1.1  # Contrast control
            beta = 10    # Brightness control
            enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Emoji enhancement failed: {e}")
            return image
    
    def create_animated_emoji_sequence(
        self, 
        frame_sequences: List[List[np.ndarray]],
        pack_name: str,
        user_id: int,
        output_dir: Path,
        fps: int = 10,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[Path]:
        """
        Create animated emoji sequence from video frames
        
        Args:
            frame_sequences: List of frame sequences (each sequence is a list of grid cells)
            pack_name: Name for the emoji pack
            user_id: User ID for file naming
            output_dir: Directory to save emoji files
            fps: Frames per second for animation
            progress_tracker: Optional progress tracking
            
        Returns:
            List of saved animated emoji paths
        """
        try:
            if not frame_sequences:
                raise ImageProcessingError("No frame sequences provided")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe pack name
            safe_pack_name = safe_filename(pack_name)
            
            # Organize frames by cell position
            grid_size = len(frame_sequences[0]) if frame_sequences else 0
            cell_sequences = [[] for _ in range(grid_size)]
            
            for frame_sequence in frame_sequences:
                for cell_idx, cell in enumerate(frame_sequence):
                    if cell_idx < len(cell_sequences):
                        cell_sequences[cell_idx].append(cell)
            
            saved_files = []
            
            logger.info(f"Creating {grid_size} animated emojis from {len(frame_sequences)} frames")
            
            for cell_idx, cell_frames in enumerate(cell_sequences):
                if not cell_frames:
                    continue
                
                # Create GIF-like sequence (save as individual frames for now)
                # In a full implementation, you might use a GIF library or WebM
                cell_dir = output_dir / f"{safe_pack_name}_cell_{cell_idx+1:03d}"
                cell_dir.mkdir(exist_ok=True)
                
                cell_files = []
                for frame_idx, frame in enumerate(cell_frames):
                    frame_filename = f"frame_{frame_idx:03d}.png"
                    frame_path = cell_dir / frame_filename
                    
                    optimized_frame = self.optimize_emoji_size(frame)
                    self.image_processor.save_image(optimized_frame, frame_path)
                    cell_files.append(frame_path)
                
                saved_files.extend(cell_files)
                
                if progress_tracker:
                    progress_tracker.update(1, f"Generated animated emoji {cell_idx+1}/{grid_size}")
            
            logger.info(f"Successfully created animated emoji sequence with {len(saved_files)} frames")
            return saved_files
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to create animated emoji sequence: {e}")
    
    def _create_pack_metadata(
        self, 
        emoji_files: List[Path], 
        pack_name: str, 
        user_id: int, 
        metadata_path: Path
    ):
        """Create metadata file for emoji pack"""
        try:
            metadata = {
                "pack_name": pack_name,
                "user_id": user_id,
                "emoji_count": len(emoji_files),
                "emoji_files": [str(f.name) for f in emoji_files],
                "created_at": int(time.time()),
                "format": "static_png",
                "size": "512x512"
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to create pack metadata: {e}")
    
    def create_pack_archive(
        self, 
        emoji_files: List[Path], 
        pack_name: str, 
        output_path: Path
    ) -> Path:
        """
        Create ZIP archive of emoji pack
        
        Args:
            emoji_files: List of emoji file paths
            pack_name: Name of the pack
            output_path: Path for output ZIP file
            
        Returns:
            Path to created ZIP file
        """
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for emoji_file in emoji_files:
                    if emoji_file.exists():
                        zipf.write(emoji_file, emoji_file.name)
                
                # Add README
                readme_content = f"""
# {pack_name} Emoji Pack

This pack contains {len(emoji_files)} emoji images.

## Usage
Extract the PNG files and upload them to Telegram as stickers.

## Files
{chr(10).join([f"- {f.name}" for f in emoji_files])}
"""
                zipf.writestr("README.txt", readme_content)
            
            logger.info(f"Created emoji pack archive: {output_path}")
            return output_path
            
        except Exception as e:
            # Clean up partially created archive file
            if 'output_path' in locals() and output_path.exists():
                try:
                    output_path.unlink()
                    logger.debug(f"Cleaned up partially created archive: {output_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup partial archive: {cleanup_error}")
            
            raise ImageProcessingError(f"Failed to create pack archive: {e}")
    
    def check_ffmpeg_capabilities(self) -> Dict[str, bool]:
        """Check which codecs are available in ffmpeg"""
        capabilities = {
            'ffmpeg_available': False,
            'vp9_available': False,
            'vp8_available': False,
            'h264_available': False
        }
        
        try:
            # Check if ffmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                capabilities['ffmpeg_available'] = True
                logger.debug(f"FFmpeg version detected")
                
                # Check for codec availability
                result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    encoders = result.stdout
                    capabilities['vp9_available'] = 'libvpx-vp9' in encoders
                    capabilities['vp8_available'] = 'libvpx' in encoders
                    capabilities['h264_available'] = 'libx264' in encoders
                    
                    # Log detailed codec info
                    for line in encoders.split('\n'):
                        if 'libvp9' in line:
                            logger.debug(f"VP9 encoder: {line.strip()}")
                        elif 'libvpx' in line:
                            logger.debug(f"VP8 encoder: {line.strip()}")
                        elif 'libx264' in line:
                            logger.debug(f"H264 encoder: {line.strip()}")
                else:
                    logger.warning("Could not get ffmpeg encoder list")
            else:
                logger.warning(f"FFmpeg not working: {result.stderr}")
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.warning(f"Could not check ffmpeg capabilities: {e}")
        
        return capabilities
    
    def _verify_webm_file(self, file_path: Path) -> bool:
        """Verify that the created file is a valid WebM file"""
        try:
            # Use ffprobe to check file format
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_format', '-show_streams',
                str(file_path)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout
                # Check if it's actually WebM format
                is_webm = 'format_name=matroska,webm' in output or 'format_name=webm' in output
                has_video = 'codec_type=video' in output
                
                if is_webm and has_video:
                    logger.debug(f"Verified WebM file: {file_path}")
                    return True
                else:
                    logger.warning(f"File format verification failed for {file_path}: not WebM or no video stream")
                    return False
            else:
                logger.warning(f"Could not verify file format for {file_path}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.warning(f"File verification failed for {file_path}: {e}")
            return False
    
    def create_animated_emoji_pack(
        self,
        frame_sequences: List[List[np.ndarray]],
        pack_name: str,
        user_id: int,
        output_dir: Path,
        fps: int = 15,
        duration: float = 3.0,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[Path]:
        """
        Create animated emoji pack from video frame sequences
        
        Args:
            frame_sequences: List of frame sequences for each emoji position
            pack_name: Name for the emoji pack
            user_id: User ID for file naming
            output_dir: Directory to save animated emoji files
            fps: Target frame rate (max 30 for Telegram)
            duration: Animation duration in seconds (max 3.0 for Telegram)
            progress_tracker: Optional progress tracking
            
        Returns:
            List of saved animated emoji file paths (.webm files)
        """
        try:
            if not frame_sequences or not frame_sequences[0]:
                raise ImageProcessingError("No frame sequences provided for animated emoji")
            
            # Check FFmpeg capabilities first
            capabilities = self.check_ffmpeg_capabilities()
            if not capabilities['ffmpeg_available']:
                raise ImageProcessingError(
                    "FFmpeg is not available. Please install FFmpeg to create animated emojis:\n"
                    "Ubuntu/Debian: sudo apt install ffmpeg\n"
                    "macOS: brew install ffmpeg\n"
                    "Windows: choco install ffmpeg"
                )
            
            if not any([capabilities['vp9_available'], capabilities['vp8_available'], capabilities['h264_available']]):
                raise ImageProcessingError(
                    "No suitable video codecs found in FFmpeg. Please install FFmpeg with VP9, VP8, or H.264 support."
                )
            
            logger.info(f"FFmpeg capabilities: VP9={capabilities['vp9_available']}, VP8={capabilities['vp8_available']}, H264={capabilities['h264_available']}")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe pack name
            safe_pack_name = safe_filename(pack_name)
            
            # Limit FPS and duration according to Telegram requirements
            fps = min(fps, 30)
            duration = min(duration, 3.0)
            
            # Calculate total frames needed
            total_frames = int(fps * duration)
            
            logger.info(f"Creating animated emoji pack '{safe_pack_name}' with {len(frame_sequences)} emojis")
            logger.info(f"Target: {total_frames} frames, {fps} FPS, {duration}s duration")
            
            saved_files = []
            
            # Process each emoji position
            for emoji_idx, frames in enumerate(frame_sequences):
                if not frames:
                    continue
                    
                # Generate filename
                emoji_filename = f"{safe_pack_name}_animated_emoji_{emoji_idx+1:03d}.webm"
                emoji_path = output_dir / emoji_filename
                
                try:
                    # Create animated emoji from frames
                    success = self._create_animated_webm(
                        frames, emoji_path, fps, duration, total_frames
                    )
                    
                    if success and emoji_path.exists():
                        # Verify the file is a valid WebM before adding to pack
                        if self._verify_webm_file(emoji_path):
                            saved_files.append(emoji_path)
                            logger.debug(f"Created and verified animated emoji: {emoji_path}")
                        else:
                            logger.warning(f"Created file is not valid WebM: {emoji_path}")
                            # Try to delete invalid file
                            try:
                                emoji_path.unlink()
                            except:
                                pass
                    else:
                        logger.warning(f"Failed to create animated emoji: {emoji_path}")
                        
                except Exception as e:
                    logger.warning(f"Failed to create animated emoji {emoji_idx+1}: {e}")
                    continue
                
                if progress_tracker:
                    progress_tracker.update(1, f"Created animated emoji {emoji_idx+1}/{len(frame_sequences)}")
            
            # Create pack metadata for animated emojis
            metadata_path = output_dir / f"{safe_pack_name}_animated_metadata.json"
            self._create_animated_pack_metadata(saved_files, pack_name, user_id, metadata_path, fps, duration)
            
            logger.info(f"Successfully created animated emoji pack with {len(saved_files)} emojis")
            return saved_files
            
        except Exception as e:
            # Clean up any partially created files
            if 'output_dir' in locals() and output_dir.exists():
                try:
                    if 'saved_files' in locals():
                        for file_path in saved_files:
                            try:
                                if file_path.exists():
                                    file_path.unlink()
                            except:
                                pass
                    
                    # Clean up metadata file if it exists
                    if 'safe_pack_name' in locals():
                        metadata_path = output_dir / f"{safe_pack_name}_animated_metadata.json"
                        if metadata_path.exists():
                            metadata_path.unlink()
                    
                    logger.debug(f"Cleaned up partially created animated emoji files in: {output_dir}")
                    
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup animated emoji files after error: {cleanup_error}")
            
            raise ImageProcessingError(f"Failed to create animated emoji pack: {e}")
    
    def _create_animated_webm(
        self,
        frames: List[np.ndarray],
        output_path: Path,
        fps: int,
        duration: float,
        target_frame_count: int
    ) -> bool:
        """
        Create WebM animated emoji from frames
        
        Args:
            frames: List of image frames
            output_path: Path for output WebM file
            fps: Frame rate
            duration: Animation duration
            target_frame_count: Number of frames needed
            
        Returns:
            True if successful
        """
        try:
            if not frames:
                return False
            
            # Prepare frames to match target frame count
            prepared_frames = self._prepare_frames_for_animation(
                frames, target_frame_count
            )
            
            # Create temporary directory for frame files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Save frames as temporary PNG files
                frame_paths = []
                for i, frame in enumerate(prepared_frames):
                    # Resize to 100x100 for Telegram animated custom emoji
                    resized_frame = cv2.resize(frame, (100, 100), interpolation=cv2.INTER_LANCZOS4)
                    
                    # Ensure BGRA format for transparency
                    if len(resized_frame.shape) == 3 and resized_frame.shape[2] == 3:
                        resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2BGRA)
                    
                    frame_filename = f"frame_{i:06d}.png"
                    frame_path = temp_path / frame_filename
                    
                    cv2.imwrite(str(frame_path), resized_frame)
                    frame_paths.append(frame_path)
                
                # Use ffmpeg to create WebM
                success = self._encode_webm_with_ffmpeg(
                    frame_paths, output_path, fps, duration
                )
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to create animated WebM: {e}")
            return False
    
    def _prepare_frames_for_animation(
        self,
        frames: List[np.ndarray],
        target_frame_count: int
    ) -> List[np.ndarray]:
        """
        Prepare frames for animation by interpolating or repeating as needed
        
        Args:
            frames: Source frames
            target_frame_count: Number of frames needed
            
        Returns:
            List of prepared frames
        """
        try:
            if not frames:
                return []
            
            if len(frames) == target_frame_count:
                return frames
            
            prepared_frames = []
            
            if len(frames) > target_frame_count:
                # Downsample frames
                indices = np.linspace(0, len(frames) - 1, target_frame_count, dtype=int)
                for idx in indices:
                    prepared_frames.append(frames[idx])
            else:
                # Upsample frames by repeating and interpolating
                ratio = target_frame_count / len(frames)
                
                for i in range(target_frame_count):
                    source_idx = min(int(i / ratio), len(frames) - 1)
                    prepared_frames.append(frames[source_idx])
            
            # Ensure seamless loop by making last frame blend with first
            if len(prepared_frames) > 1:
                # Optionally blend the last few frames with the first few for smoother looping
                pass
            
            return prepared_frames
            
        except Exception as e:
            logger.error(f"Failed to prepare frames for animation: {e}")
            return frames[:target_frame_count] if frames else []
    
    def _encode_webm_with_ffmpeg(
        self,
        frame_paths: List[Path],
        output_path: Path,
        fps: int,
        duration: float
    ) -> bool:
        """
        Encode WebM using ffmpeg with fallback options
        
        Args:
            frame_paths: List of frame file paths
            output_path: Output WebM path
            fps: Frame rate
            duration: Duration in seconds
            
        Returns:
            True if successful
        """
        try:
            if not frame_paths:
                return False
            
            # Create input pattern file
            temp_dir = frame_paths[0].parent
            input_pattern = temp_dir / "frame_%06d.png"
            
            # Try VP9 first (preferred for Telegram)
            success = self._try_encode_vp9(input_pattern, output_path, fps, duration)
            if success:
                return True
            
            # Fallback to VP8 if VP9 not available
            logger.warning("VP9 encoder not available, trying VP8 fallback")
            success = self._try_encode_vp8(input_pattern, output_path, fps, duration)
            if success:
                return True
            
            # Final fallback to H.264 in WebM container
            logger.warning("VP8 encoder not available, trying H.264 in WebM container fallback")
            success = self._try_encode_h264(input_pattern, output_path, fps, duration)
            if success:
                return True
            
            logger.error("All encoding methods failed")
            return False
                
        except Exception as e:
            logger.error(f"Failed to encode WebM with ffmpeg: {e}")
            return False
    
    def _try_encode_vp9(self, input_pattern: Path, output_path: Path, fps: int, duration: float) -> bool:
        """Try encoding with VP9 codec using Telegram's official specifications"""
        try:
            # Use Telegram's official parameters for WebM video stickers
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-r', '30',  # Constant 30 FPS input (as per Telegram specs)
                '-i', str(input_pattern),  # Input pattern
                '-c:v', 'libvpx-vp9',  # VP9 codec
                '-pix_fmt', 'yuva420p',  # Pixel format with alpha support
                '-r', '30',  # Constant 30 FPS output (as per Telegram specs)
                '-t', str(duration),  # Duration (max 3 seconds)
                '-vf', 'scale=100:100',  # Scale to 100x100 for animated custom emoji
                '-crf', '50',  # Constant Quality (low quality for small file size)
                '-b:v', '0',  # Disable bitrate limit (use only CRF for constant quality)
                '-g', '30',  # GOP size (1 second at 30fps)
                '-auto-alt-ref', '0',  # Disable alt-ref frames
                '-lag-in-frames', '0',  # No lag
                '-row-mt', '1',  # Multi-threading
                '-tile-columns', '0',  # Tiling disabled
                '-frame-parallel', '0',  # Frame parallel processing disabled
                '-an',  # No audio stream (required by Telegram)
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                logger.debug(f"Created VP9 WebM: {output_path} ({file_size} bytes)")
                
                # Check if file size is within Telegram limits (64KB preferred for custom emoji)
                if file_size > 64 * 1024:
                    logger.warning(f"WebM file size ({file_size} bytes) exceeds preferred limit (64KB)")
                    return self._reencode_webm_compressed(output_path, fps, duration)
                
                return True
            else:
                logger.debug(f"VP9 encoding failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("VP9 encoding timed out")
            return False
        except Exception as e:
            logger.debug(f"VP9 encoding failed: {e}")
            return False
    
    def _try_encode_vp8(self, input_pattern: Path, output_path: Path, fps: int, duration: float) -> bool:
        """Try encoding with VP8 codec (fallback) using Telegram specs"""
        try:
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-r', '30',  # Constant 30 FPS input
                '-i', str(input_pattern),  # Input pattern
                '-c:v', 'libvpx',  # VP8 codec
                '-pix_fmt', 'yuva420p',  # Pixel format with alpha
                '-r', '30',  # Constant 30 FPS output
                '-t', str(duration),  # Duration
                '-vf', 'scale=100:100',  # Scale to 100x100 for animated custom emoji
                '-crf', '50',  # Constant Quality (low quality for small file size)
                '-b:v', '0',  # Disable bitrate limit (use only CRF)
                '-g', '30',  # GOP size (1 second at 30fps)
                '-auto-alt-ref', '0',  # Disable alt-ref for compatibility
                '-lag-in-frames', '0',  # Reduce encoding delay
                '-error-resilient', '1',  # Make more robust
                '-an',  # No audio stream
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                logger.info(f"Created VP8 WebM: {output_path} ({file_size} bytes)")
                
                if file_size > 64 * 1024:
                    logger.warning(f"WebM file size ({file_size} bytes) exceeds preferred limit (64KB)")
                    # Try simple recompression
                    return self._simple_recompress_webm(output_path, fps, duration)
                
                return True
            else:
                logger.warning(f"VP8 encoding failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("VP8 encoding timed out")
            return False
        except Exception as e:
            logger.warning(f"VP8 encoding failed: {e}")
            return False
    
    def _try_encode_h264(self, input_pattern: Path, output_path: Path, fps: int, duration: float) -> bool:
        """Try encoding with H.264 codec in WebM container (final fallback)"""
        try:
            # Use WebM container with H.264 codec for Telegram compatibility
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-r', str(fps),  # Input frame rate
                '-i', str(input_pattern),  # Input pattern
                '-c:v', 'libx264',  # H.264 codec
                '-pix_fmt', 'yuv420p',  # Standard pixel format (no alpha)
                '-r', str(fps),  # Output frame rate
                '-t', str(duration),  # Duration
                '-vf', 'scale=100:100',  # Scale to 100x100
                '-b:v', '256k',  # Bitrate limit
                '-crf', '28',  # Quality setting for H.264
                '-preset', 'fast',  # Encoding preset
                '-f', 'webm',  # Force WebM container format
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                logger.info(f"Created H.264 WebM: {output_path} ({file_size} bytes)")
                
                if file_size <= 64 * 1024:
                    return True
                else:
                    logger.warning(f"H.264 WebM file too large ({file_size} bytes), compression needed")
                    return False
            else:
                logger.debug(f"H.264 WebM encoding failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("H.264 WebM encoding timed out")
            return False
        except Exception as e:
            logger.debug(f"H.264 WebM encoding failed: {e}")
            return False
    
    def _simple_recompress_webm(self, webm_path: Path, fps: int, duration: float) -> bool:
        """Simple recompression for VP8 files that are too large"""
        try:
            temp_path = webm_path.with_suffix('.tmp.webm')
            
            cmd = [
                'ffmpeg',
                '-y',
                '-i', str(webm_path),
                '-c:v', 'libvpx',
                '-r', str(fps),
                '-t', str(duration),
                '-vf', 'scale=100:100',
                '-b:v', '128k',  # Lower bitrate
                '-crf', '35',  # Higher CRF (lower quality)
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and temp_path.exists():
                # Replace original with compressed version
                shutil.move(str(temp_path), str(webm_path))
                file_size = webm_path.stat().st_size
                logger.info(f"Re-compressed VP8 WebM to {file_size} bytes")
                return file_size <= 64 * 1024
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to re-compress VP8 WebM: {e}")
            return False
    
    def _reencode_webm_compressed(
        self,
        webm_path: Path,
        fps: int,
        duration: float
    ) -> bool:
        """
        Re-encode WebM with higher compression for smaller file size
        
        Args:
            webm_path: Path to existing WebM file
            fps: Frame rate
            duration: Duration
            
        Returns:
            True if successful
        """
        try:
            temp_path = webm_path.with_suffix('.tmp.webm')
            
            cmd = [
                'ffmpeg',
                '-y',
                '-i', str(webm_path),
                '-c:v', 'libvp9',
                '-pix_fmt', 'yuva420p',
                '-r', str(fps),
                '-t', str(duration),
                '-vf', 'scale=100:100',
                '-b:v', '128k',  # Lower bitrate
                '-crf', '35',  # Higher CRF (lower quality)
                '-g', str(fps),
                '-auto-alt-ref', '0',
                '-lag-in-frames', '0',
                '-row-mt', '1',
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and temp_path.exists():
                # Replace original with compressed version
                shutil.move(str(temp_path), str(webm_path))
                file_size = webm_path.stat().st_size
                logger.info(f"Re-encoded WebM to {file_size} bytes")
                return file_size <= 64 * 1024
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to re-encode WebM: {e}")
            return False
    
    def _create_animated_pack_metadata(
        self,
        emoji_files: List[Path],
        pack_name: str,
        user_id: int,
        metadata_path: Path,
        fps: int,
        duration: float
    ):
        """Create metadata file for animated emoji pack"""
        try:
            metadata = {
                "pack_name": pack_name,
                "user_id": user_id,
                "emoji_count": len(emoji_files),
                "emoji_files": [str(f.name) for f in emoji_files],
                "created_at": int(time.time()),
                "format": "animated_webm",
                "size": "100x100",
                "fps": fps,
                "duration": duration,
                "animated": True
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to create animated pack metadata: {e}")
    
    def create_mixed_pack_archive(
        self,
        static_files: List[Path],
        animated_files: List[Path],
        pack_name: str,
        output_path: Path
    ) -> Path:
        """
        Create ZIP archive with both static and animated emojis
        
        Args:
            static_files: List of static emoji file paths
            animated_files: List of animated emoji file paths  
            pack_name: Name of the pack
            output_path: Path for output ZIP file
            
        Returns:
            Path to created ZIP file
        """
        try:
            all_files = static_files + animated_files
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for emoji_file in all_files:
                    if emoji_file.exists():
                        zipf.write(emoji_file, emoji_file.name)
                
                # Add README
                readme_content = f"""
# {pack_name} Mixed Emoji Pack

This pack contains {len(static_files)} static and {len(animated_files)} animated emoji images.

## Static Emojis ({len(static_files)})
{chr(10).join([f"- {f.name}" for f in static_files])}

## Animated Emojis ({len(animated_files)})  
{chr(10).join([f"- {f.name}" for f in animated_files])}

## Usage
- Static emojis: Extract PNG files and upload to Telegram as stickers
- Animated emojis: Use WebM files for Telegram custom animated emoji
"""
                zipf.writestr("README.txt", readme_content)
            
            logger.info(f"Created mixed emoji pack archive: {output_path}")
            return output_path
            
        except Exception as e:
            # Clean up partially created archive file
            if 'output_path' in locals() and output_path.exists():
                try:
                    output_path.unlink()
                    logger.debug(f"Cleaned up partially created archive: {output_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup partial archive: {cleanup_error}")
            
            raise ImageProcessingError(f"Failed to create mixed pack archive: {e}")
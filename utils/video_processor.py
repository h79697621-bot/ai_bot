import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging
from pathlib import Path

from exceptions import VideoProcessingError, OpenCVError
from .helpers import ProgressTracker
from .image_processor import ImageProcessor

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Video processing functionality using OpenCV"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
    
    def extract_frames(
        self, 
        video_path: Path, 
        frame_count: int = 20,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[np.ndarray]:
        """
        Smart frame extraction from video
        
        Args:
            video_path: Path to video file
            frame_count: Number of frames to extract
            progress_tracker: Optional progress tracking
            
        Returns:
            List of extracted frames
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                raise VideoProcessingError(f"Could not open video: {video_path}")
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"Video: {total_frames} frames, {fps:.1f} FPS, {duration:.1f}s duration")
            
            if total_frames == 0:
                raise VideoProcessingError("Video has no frames")
            
            # Limit frame count to available frames
            frame_count = min(frame_count, total_frames)
            
            # Calculate frame indices to extract
            if frame_count >= total_frames:
                # Extract all frames
                frame_indices = list(range(total_frames))
            else:
                # Extract evenly spaced frames
                frame_indices = [
                    int(i * total_frames / frame_count) 
                    for i in range(frame_count)
                ]
            
            # Extract frames
            frames = []
            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    frames.append(frame)
                    if progress_tracker:
                        progress_tracker.update(1, f"Extracted frame {i+1}/{len(frame_indices)}")
                else:
                    logger.warning(f"Could not read frame {frame_idx}")
            
            cap.release()
            
            if not frames:
                raise VideoProcessingError("No frames could be extracted from video")
            
            logger.info(f"Successfully extracted {len(frames)} frames from video")
            return frames
            
        except Exception as e:
            if 'cap' in locals():
                cap.release()
            raise VideoProcessingError(f"Failed to extract frames from video: {e}")
    
    def detect_scene_changes(
        self, 
        frames: List[np.ndarray], 
        threshold: float = 30.0
    ) -> List[int]:
        """
        Detect scene changes in frame sequence
        
        Args:
            frames: List of frames
            threshold: Difference threshold for scene detection
            
        Returns:
            List of frame indices where scene changes occur
        """
        try:
            if len(frames) < 2:
                return []
            
            scene_frames = [0]  # First frame is always a scene change
            
            for i in range(1, len(frames)):
                # Convert frames to grayscale for comparison
                gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
                
                # Calculate absolute difference
                diff = cv2.absdiff(gray1, gray2)
                
                # Calculate mean difference
                mean_diff = np.mean(diff)
                
                if mean_diff > threshold:
                    scene_frames.append(i)
                    logger.debug(f"Scene change detected at frame {i} (diff: {mean_diff:.1f})")
            
            logger.info(f"Detected {len(scene_frames)} scene changes")
            return scene_frames
            
        except Exception as e:
            logger.warning(f"Scene detection failed: {e}")
            return list(range(min(10, len(frames))))  # Fallback to first 10 frames
    
    def process_video_sequence(
        self, 
        frames: List[np.ndarray], 
        grid_size: Tuple[int, int],
        adaptation_method: str = "pad",
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[List[np.ndarray]]:
        """
        Process video frames into emoji sequences
        
        Args:
            frames: List of video frames
            grid_size: (grid_x, grid_y) tuple
            adaptation_method: Image adaptation method
            progress_tracker: Optional progress tracking
            
        Returns:
            List of frame sequences, each containing grid cells
        """
        try:
            grid_x, grid_y = grid_size
            processed_sequences = []
            
            total_frames = len(frames)
            logger.info(f"Processing {total_frames} frames into {grid_x}x{grid_y} grids")
            
            for i, frame in enumerate(frames):
                # Adapt frame to grid aspect ratio
                adapted_frame = self.image_processor.adapt_image_to_grid(
                    frame, grid_x, grid_y, adaptation_method
                )
                
                # Split frame into grid cells
                cells = self.image_processor.split_image_grid(
                    adapted_frame, grid_x, grid_y
                )
                
                processed_sequences.append(cells)
                
                if progress_tracker:
                    progress_tracker.update(1, f"Processed frame {i+1}/{total_frames}")
            
            logger.info(f"Successfully processed {len(processed_sequences)} frame sequences")
            return processed_sequences
            
        except Exception as e:
            raise VideoProcessingError(f"Failed to process video sequence: {e}")
    
    def extract_key_frames(
        self, 
        video_path: Path, 
        max_frames: int = 50,
        scene_threshold: float = 30.0,
        progress_tracker: Optional[ProgressTracker] = None
    ) -> List[np.ndarray]:
        """
        Extract key frames using scene detection
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract
            scene_threshold: Threshold for scene change detection
            progress_tracker: Optional progress tracking
            
        Returns:
            List of key frames
        """
        try:
            # First, extract a larger sample of frames for scene analysis
            sample_frames = self.extract_frames(
                video_path, 
                frame_count=min(max_frames * 3, 150),
                progress_tracker=progress_tracker
            )
            
            # Detect scene changes
            scene_indices = self.detect_scene_changes(sample_frames, scene_threshold)
            
            # If we have too many scene changes, take evenly spaced ones
            if len(scene_indices) > max_frames:
                step = len(scene_indices) // max_frames
                scene_indices = scene_indices[::step][:max_frames]
            
            # Extract frames at scene change points
            key_frames = [sample_frames[i] for i in scene_indices]
            
            # If we don't have enough frames, fill with evenly spaced frames
            if len(key_frames) < max_frames:
                remaining_count = max_frames - len(key_frames)
                additional_frames = self.extract_frames(
                    video_path, 
                    frame_count=remaining_count
                )
                key_frames.extend(additional_frames)
            
            # Remove duplicates and limit to max_frames
            unique_frames = []
            for frame in key_frames[:max_frames]:
                unique_frames.append(frame)
            
            logger.info(f"Extracted {len(unique_frames)} key frames")
            return unique_frames
            
        except Exception as e:
            # Fallback to regular frame extraction
            logger.warning(f"Key frame extraction failed, using regular extraction: {e}")
            return self.extract_frames(video_path, max_frames, progress_tracker)
    
    def get_video_info(self, video_path: Path) -> dict:
        """
        Get video metadata
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                raise VideoProcessingError(f"Could not open video: {video_path}")
            
            info = {
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'duration': 0,
                'file_size': video_path.stat().st_size,
            }
            
            if info['fps'] > 0:
                info['duration'] = info['frame_count'] / info['fps']
            
            cap.release()
            return info
            
        except Exception as e:
            if 'cap' in locals():
                cap.release()
            raise VideoProcessingError(f"Failed to get video info: {e}")
    
    def validate_video(self, video_path: Path, max_duration: int = 300) -> bool:
        """
        Validate video file
        
        Args:
            video_path: Path to video file
            max_duration: Maximum duration in seconds
            
        Returns:
            True if valid
        """
        try:
            info = self.get_video_info(video_path)
            
            if info['duration'] > max_duration:
                raise VideoProcessingError(
                    f"Video duration ({info['duration']:.1f}s) exceeds limit ({max_duration}s)"
                )
            
            if info['frame_count'] == 0:
                raise VideoProcessingError("Video has no frames")
            
            return True
            
        except Exception as e:
            raise VideoProcessingError(f"Video validation failed: {e}")
    
    def organize_frames_by_position(
        self,
        frame_sequences: List[List[np.ndarray]],
        grid_size: Tuple[int, int]
    ) -> List[List[np.ndarray]]:
        """
        Reorganize frame sequences from [frame][position] to [position][frame]
        for animated emoji generation
        
        Args:
            frame_sequences: List of frame sequences, each containing grid cells
            grid_size: (grid_x, grid_y) tuple
            
        Returns:
            List of position sequences, each containing frames for that position
        """
        try:
            if not frame_sequences or not frame_sequences[0]:
                return []
            
            grid_x, grid_y = grid_size
            total_positions = grid_x * grid_y
            
            # Initialize position sequences
            position_sequences = [[] for _ in range(total_positions)]
            
            # Reorganize frames by position
            for frame_cells in frame_sequences:
                for pos_idx, cell in enumerate(frame_cells):
                    if pos_idx < total_positions:
                        position_sequences[pos_idx].append(cell)
            
            logger.info(f"Organized {len(frame_sequences)} frames into {len(position_sequences)} position sequences")
            return position_sequences
            
        except Exception as e:
            logger.error(f"Failed to organize frames by position: {e}")
            return []

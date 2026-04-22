#!/usr/bin/env python3
"""
FFmpeg WebM Encoding Debug Script
Run this to test VP8/VP9 encoding capabilities
"""

import subprocess
import tempfile
import cv2
import numpy as np
from pathlib import Path

def test_ffmpeg_encoders():
    """Test which encoders are available"""
    print("=== FFmpeg Encoder Test ===")
    
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            encoders = result.stdout
            print(f"✅ FFmpeg available")
            print(f"VP9 (libvp9): {'✅' if 'libvp9' in encoders else '❌'}")
            print(f"VP8 (libvpx): {'✅' if 'libvpx' in encoders else '❌'}")  
            print(f"H264 (libx264): {'✅' if 'libx264' in encoders else '❌'}")
            
            # Show exact encoder lines
            for line in encoders.split('\n'):
                if any(codec in line for codec in ['libvp9', 'libvpx', 'libx264']):
                    print(f"  {line.strip()}")
        else:
            print(f"❌ FFmpeg encoder check failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error checking encoders: {e}")

def create_test_frames():
    """Create test frames for encoding"""
    frames = []
    for i in range(10):
        # Create a 100x100 test frame with different colors
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        color = (i * 25, (i * 30) % 255, (i * 40) % 255)
        cv2.rectangle(frame, (20, 20), (80, 80), color, -1)
        cv2.putText(frame, str(i), (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        frames.append(frame)
    return frames

def test_vp8_encoding():
    """Test VP8 encoding specifically"""
    print("\n=== VP8 Encoding Test ===")
    
    frames = create_test_frames()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Save test frames
        frame_paths = []
        for i, frame in enumerate(frames):
            frame_file = temp_path / f"frame_{i:06d}.png"
            cv2.imwrite(str(frame_file), frame)
            frame_paths.append(frame_file)
        
        # Test VP8 encoding
        output_path = temp_path / "test_vp8.webm"
        input_pattern = temp_path / "frame_%06d.png"
        
        cmd = [
            'ffmpeg', '-y',
            '-r', '15',
            '-i', str(input_pattern),
            '-c:v', 'libvpx',
            '-pix_fmt', 'yuva420p',
            '-r', '15', '-t', '2.0',
            '-vf', 'scale=100:100',
            '-b:v', '256k', '-crf', '30',
            '-g', '15',
            '-auto-alt-ref', '0',
            '-lag-in-frames', '0',
            '-error-resilient', '1',
            str(output_path)
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                print(f"✅ VP8 encoding successful: {file_size} bytes")
                
                # Verify with ffprobe
                probe_result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_format', '-show_streams',
                    str(output_path)
                ], capture_output=True, text=True)
                
                if probe_result.returncode == 0:
                    print("📋 File info:")
                    for line in probe_result.stdout.split('\n'):
                        if any(key in line for key in ['format_name', 'codec_name', 'width', 'height', 'duration']):
                            print(f"  {line}")
                
                return True
            else:
                print(f"❌ VP8 encoding failed:")
                print(f"Return code: {result.returncode}")
                print(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ VP8 encoding timed out")
            return False
        except Exception as e:
            print(f"❌ VP8 encoding error: {e}")
            return False

def test_simple_vp8():
    """Test the simplest possible VP8 command"""
    print("\n=== Simple VP8 Test ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create one test frame
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(frame, (10, 10), (90, 90), (0, 255, 0), -1)
        frame_file = temp_path / "test.png"
        cv2.imwrite(str(frame_file), frame)
        
        output_path = temp_path / "simple_test.webm"
        
        # Simplest possible VP8 command
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', str(frame_file),
            '-c:v', 'libvpx',
            '-t', '1',
            '-pix_fmt', 'yuv420p',
            str(output_path)
        ]
        
        print(f"Simple command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and output_path.exists():
            print(f"✅ Simple VP8 works: {output_path.stat().st_size} bytes")
            return True
        else:
            print(f"❌ Simple VP8 failed: {result.stderr}")
            return False

if __name__ == "__main__":
    test_ffmpeg_encoders()
    test_simple_vp8()
    test_vp8_encoding()
    print("\n=== Debug Complete ===")
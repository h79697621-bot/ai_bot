# Telegram Emoji Pack Bot

A powerful Telegram bot that converts images and videos into custom emoji packs with configurable grid dimensions. Built with Python, OpenCV, and the latest Telegram Bot API features.

## 🌟 Features

- **Image Processing**: Convert static images to emoji grids with advanced OpenCV processing
- **Video Processing**: Extract frames from videos and convert to emoji sequences  
- **🎬 Animated Emojis**: Create animated emoji packs from video input (WebM format)
- **Custom Grid Sizes**: Flexible grid dimensions (1×1 to 20×20)
- **Smart Adaptation**: Automatic image reshaping with padding, stretching, or cropping
- **Custom Emoji Packs**: Create actual Telegram custom emoji packs (requires Premium to add)
- **Background Removal**: Optional transparency for cleaner emojis
- **Quality Control**: Multiple quality levels and optimization options
- **Async Processing**: Non-blocking operations for better performance

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token from [@BotFather](https://t.me/botfather)
- `uv` package manager (recommended) or pip
- **FFmpeg** (required for animated emoji WebM creation)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd emoji_bot
   ```

2. **Install system dependencies:**
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # macOS (with Homebrew)
   brew install ffmpeg
   
   # Windows (with Chocolatey)
   choco install ffmpeg
   ```

3. **Install Python dependencies:**
   ```bash
   # Using uv (recommended)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token
   ```

5. **Run the bot:**
   ```bash
   python main.py
   ```

## 📁 Project Structure

```
emoji_bot/
├── main.py                     # Bot entry point
├── config.py                   # Configuration management
├── pyproject.toml             # Project dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── 
├── exceptions/                # Custom exception classes
│   ├── __init__.py
│   ├── base.py
│   ├── processing.py
│   └── validation.py
├── 
├── filters/                   # Message filters
│   ├── __init__.py
│   ├── media.py              # Media type detection
│   └── user.py               # User validation
├── 
├── handlers/                  # Bot command handlers
│   └── user/
│       ├── __init__.py
│       ├── start.py          # /start command
│       ├── image.py          # Image processing
│       └── video.py          # Video processing
├── 
├── keyboards/                 # Telegram keyboards
│   ├── __init__.py
│   └── inline/
│       └── user/
│           ├── __init__.py
│           ├── grid_size.py  # Grid selection
│           ├── processing.py # Processing controls
│           └── settings.py   # Settings menu
├── 
├── middlewares/              # Bot middlewares
│   ├── __init__.py
│   ├── throttling.py        # Rate limiting
│   └── logging.py           # Request logging
├── 
├── states/                   # FSM state management
│   ├── __init__.py
│   └── user_states.py       # User interaction states
├── 
└── utils/                    # Core utilities
    ├── __init__.py
    ├── image_processor.py    # Image processing logic
    ├── video_processor.py    # Video processing logic
    ├── emoji_generator.py    # Emoji pack creation
    ├── sticker_pack_manager.py # Telegram sticker API
    ├── file_manager.py       # File operations
    ├── validation.py         # Input validation
    └── helpers.py           # Helper functions
```

## 🛠️ Technology Stack

- **Framework**: aiogram 3.13.1 (Telegram Bot API 7.10)
- **Image Processing**: OpenCV 4.8+, NumPy, scikit-image
- **File Operations**: aiofiles (async I/O)
- **Configuration**: python-dotenv
- **Package Management**: uv (ultra-fast Python package manager)

## 📝 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Grid Settings
MAX_GRID_X=20
MIN_GRID_X=1
MAX_GRID_Y=20  
MIN_GRID_Y=1

# File Processing
MAX_FILE_SIZE_MB=50
MAX_VIDEO_DURATION=300
PROCESSING_TIMEOUT=120

# Cache Settings
CACHE_CLEANUP_INTERVAL=3600
CACHE_DIR=./data/cache

# Logging
LOG_LEVEL=INFO
```

### Grid Size Examples

The bot supports flexible grid dimensions:

- **1×3**: Horizontal strips (timelines, progress bars)
- **3×1**: Vertical strips (tall portraits, towers)
- **2×5**: Wide rectangular layouts
- **4×4**: Square grids (balanced compositions)
- **Custom**: Any combination up to 20×20

## 🎯 How It Works

### Image Processing Pipeline

1. **Upload**: User sends image to bot
2. **Configuration**: Choose grid size and adaptation method
3. **Processing**:
   - Image validation and loading
   - Aspect ratio adaptation (pad/stretch/crop)
   - Grid cell extraction
   - Individual emoji optimization
   - Custom emoji pack creation
4. **Delivery**: Telegram custom emoji pack link + ZIP download

### Video Processing Pipeline

1. **Upload**: User sends video file
2. **Mode Selection**: Choose between static frames or animated emojis
3. **Frame Extraction**: Smart frame sampling based on duration
4. **Processing**: 
   - **Static Mode**: Each frame processed as image grid
   - **🎬 Animated Mode**: Frames organized by position, encoded as WebM
5. **Pack Creation**: 
   - **Static**: First frame becomes custom emoji pack
   - **🎬 Animated**: WebM animated emoji pack with configurable FPS/duration
6. **Archive**: All emojis available as ZIP download

### Adaptation Methods

- **Padding**: Adds borders to preserve all content (recommended)
- **Stretching**: Non-uniform scaling (may distort)
- **Cropping**: Center crop to match ratio (may lose content)

## 🎮 Bot Commands

### Basic Commands
- `/start` - Initialize bot and configure settings
- `/help` - Show usage instructions

### Processing Flow
1. Send image or video to bot
2. Configure grid size (e.g., 3×2, 1×4)
3. Choose adaptation method
4. Confirm processing
5. Receive custom emoji pack link

### Interactive Features
- Grid size selection with preview
- Adaptation method comparison
- Quality level options
- Background removal toggle
- Progress tracking
- File management (download/delete)

## 🔧 Core Components

### Image Processor (`utils/image_processor.py`)

Handles all image manipulation using OpenCV:

```python
class ImageProcessor:
    def adapt_image_to_grid(self, image, grid_x, grid_y, method="pad"):
        """Adapt image to match grid aspect ratio"""
        
    def split_image_grid(self, image, grid_x, grid_y):
        """Split image into grid cells"""
        
    def enhance_image(self, image, level="medium"):
        """Apply quality enhancements"""
```

### Sticker Pack Manager (`utils/sticker_pack_manager.py`)

Creates actual Telegram custom emoji packs:

```python
class StickerPackManager:
    async def create_sticker_pack(self, user_id, user_name, emoji_files, grid_size):
        """Create Telegram custom emoji pack"""
        # Returns pack link: t.me/addemoji/pack_name
```

### File Manager (`utils/file_manager.py`)

Handles file downloads and caching:

```python
class FileManager:
    async def download_media(self, file_info, user_id):
        """Download media from Telegram servers"""
        
    def cleanup_cache(self):
        """Clean up temporary files"""
```

## 🎨 Custom Emoji Packs

The bot creates **actual Telegram custom emoji packs** that can be added to Telegram:

- **Pack Format**: Custom emoji type (100×100 pixels)
- **Pack Limits**: Up to 50 custom emojis per pack
- **Access**: Direct link (t.me/addemoji/pack_name)
- **Requirements**: Telegram Premium needed to add packs
- **Visibility**: Everyone can see custom emojis once added

## 📊 Performance & Limits

### File Limits
- **Images**: Up to 50MB
- **Videos**: Up to 50MB, max 5 minutes duration
- **Grid Size**: 1×1 to 20×20 (400 emojis max)

### Processing Optimization
- **Async Operations**: Non-blocking file processing
- **Memory Management**: Efficient OpenCV operations
- **Caching**: Temporary file caching with auto-cleanup
- **Rate Limiting**: Built-in throttling middleware

## 🐛 Error Handling

The bot includes comprehensive error handling:

- **File Validation**: Format, size, and corruption checks
- **Processing Errors**: OpenCV and memory error recovery
- **Telegram API**: Rate limit and upload error handling
- **User Feedback**: Clear error messages with solutions

### Common Issues and Solutions

#### Animated Emoji Issues

**"Unknown encoder 'libvp9'" Error:**
```bash
# Your FFmpeg doesn't have VP9 support. Install full version:

# Ubuntu/Debian - Install from official repository
sudo apt remove ffmpeg
sudo apt update
sudo apt install snapd
sudo snap install ffmpeg

# Or compile with full codec support
sudo apt install software-properties-common
sudo add-apt-repository ppa:savoury1/ffmpeg4
sudo apt update
sudo apt install ffmpeg

# macOS - Reinstall with full codecs
brew uninstall ffmpeg
brew install ffmpeg

# Verify VP9/VP8 support:
ffmpeg -encoders | grep -E "(libvp9|libvpx)"
```

**Large File Size (>64KB) Warnings:**
- Bot automatically tries compression fallbacks
- VP8 fallback used when VP9 not available  
- H.264 final fallback for compatibility
- Reduce FPS or duration for smaller files

## 🔒 Security Features

- **Input Validation**: Strict file type and size checking
- **Rate Limiting**: Prevents abuse and spam
- **Cache Management**: Automatic cleanup of temporary files
- **Error Isolation**: Graceful handling of processing failures

## 📈 Monitoring & Logging

- **Structured Logging**: Detailed operation logs
- **Performance Metrics**: Processing time tracking
- **Error Tracking**: Comprehensive error reporting
- **User Analytics**: Usage pattern monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section in docs
- Review error messages for specific guidance

## 🎉 Examples

### Creating a 1×3 Timeline
1. Send image to bot
2. Select "1×3" grid
3. Choose "Padding" adaptation
4. Get 3 horizontal emojis perfect for timelines

### Creating a 4×4 Avatar Grid  
1. Send portrait photo
2. Select "4×4" grid
3. Choose "Crop" adaptation
4. Get 16 emojis showing different parts of the face

### Video to Emoji Sequence
1. Send short video
2. Choose processing mode (static or animated)
3. Configure grid size
4. **Static Mode**: Get frame sequence as individual emojis
5. **🎬 Animated Mode**: Get WebM animated emojis (15-30 FPS, 1-3s duration)

### Creating Animated Emojis
1. Send video to bot
2. Select "🎬 Create Animated" 
3. Configure FPS (15/30) and duration (1-3s)
4. Get animated WebM emoji pack for Telegram Premium
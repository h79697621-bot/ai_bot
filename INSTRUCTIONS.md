# 🎨 Telegram Emoji Pack Bot - User Instructions

Transform your images and videos into custom emoji packs for Telegram! This bot converts any image or video into a grid of emojis that you can use as stickers.

## 🚀 Quick Start

1. **Start the bot** - Send `/start`
2. **Choose grid size** - Select how many emojis to create (e.g., 2×2, 3×3, 1×5)
3. **Pick adaptation method** - Choose how to fit your image (Pad, Stretch, or Crop)
4. **Send your media** - Upload an image or video
5. **Get your sticker pack** - Automatically created and ready to add to Telegram!
6. **Alternative options** - Download as ZIP or individual files

## 📋 Bot Commands

### Basic Commands
- `/start` - Initialize the bot and begin setup
- `/help` - Show detailed help and guides
- `/settings` - Open settings menu
- `/cancel` - Cancel current operation

### Quick Configuration Commands
- `/setgrid X Y` - Set grid size directly (e.g., `/setgrid 3 3`)
- `/adapt method` - Set adaptation method (`pad`, `stretch`, or `crop`)

### Information Commands
- `/examples` - Show example grid layouts and use cases
- `/stats` - View your usage statistics

## 📐 Grid Sizes Explained

### Common Grid Layouts

| Grid Size | Use Case | Example |
|-----------|----------|---------|
| **1×3** | Horizontal timeline, progress bars | `[🟢][🟡][🔴]` |
| **3×1** | Vertical strip, tall portraits | `[😊]`<br>`[👕]`<br>`[👖]` |
| **2×2** | Simple 4-piece puzzle | `[🌅][🌅]`<br>`[🌊][🌊]` |
| **3×3** | Classic grid, most versatile | Standard 9-emoji pack |
| **2×5** | Wide scenes, landscapes | Perfect for panoramic images |
| **4×4** | Detailed images, 16 emojis | High detail, complex images |

### Custom Sizes
- Any combination from **1×1** to **8×8**
- Examples: `1×5`, `2×7`, `6×2`, `5×3`
- Larger grids = more detail but longer processing time

## 🔄 Adaptation Methods

### 📏 Pad (Recommended)
- **What it does:** Adds white borders to make image fit grid ratio
- **Pros:** Keeps all original content, no distortion
- **Best for:** Text, logos, portraits, most images
- **Example:** Square image → 1×3 grid gets white bars on sides

### ↔️ Stretch
- **What it does:** Changes image proportions to fit exactly
- **Pros:** No borders, uses full space
- **Cons:** May look distorted
- **Best for:** Abstract images, patterns, textures

### ✂️ Crop
- **What it does:** Cuts edges to focus on center
- **Pros:** No distortion, focuses on important center content
- **Cons:** Loses edge content
- **Best for:** Face photos, centered subjects

## 🎨 Quality Settings

### High Quality (Recommended)
- **Processing:** 30-120 seconds
- **Features:** CLAHE enhancement, bilateral filtering
- **Best for:** Final emoji packs, important images

### Medium Quality
- **Processing:** 15-60 seconds  
- **Features:** Basic enhancement
- **Best for:** Testing, general use

### Low Quality (Fast Mode)
- **Processing:** 5-30 seconds
- **Features:** Minimal processing
- **Best for:** Quick tests, simple images

## 📱 Using the Bot - Step by Step

### For Images

1. **Send `/start`** to begin
2. **Choose grid size** from the keyboard or use `/setgrid X Y`
3. **Select adaptation method** (Pad recommended for beginners)
4. **Send your image** (JPG, PNG, WebP, BMP, TIFF up to 50MB)
5. **Review settings** and click "✅ Start Processing"
6. **Wait for processing** (usually 10-60 seconds)
7. **Get your results:**
   - 🎯 **Telegram Sticker Pack** - Direct link to add to Telegram
   - 📦 ZIP file with all emojis
   - 📱 Individual emoji files
   - 👁️ Preview in chat

### For Videos

1. **Configure settings** same as images
2. **Send your video** (MP4, AVI, MOV, WebM, MKV up to 50MB, max 5 minutes)
3. **Bot extracts key frames** automatically
4. **Each frame becomes an emoji set**
5. **First frame becomes Telegram sticker pack**
6. **Download organized by frame** or as complete ZIP

## 🎯 Pro Tips

### Image Selection
- **Use high resolution** (1000×1000+ pixels) for best results
- **Good lighting** improves final quality
- **Square images** work best with square grids
- **Avoid very dark or blurry images**

### Grid Selection Tips
- **Start small** (2×2) for testing
- **Match aspect ratios:**
  - Wide images → `1×X` or `2×X` grids
  - Tall images → `X×1` or `X×2` grids  
  - Square images → `X×X` grids
- **More cells = more processing time**

### Optimization
- **Use "Fast Mode"** for testing settings
- **Process during off-peak hours** for better performance
- **Clean cache regularly** using settings menu

## 📊 File Format Support

### Supported Input Formats

**Images:**
- JPEG/JPG
- PNG (best quality)
- WebP
- BMP
- TIFF

**Videos:**
- MP4 (recommended)
- AVI
- MOV
- WebM
- MKV

### Output Format
- **All emojis:** 512×512 PNG files
- **Telegram ready:** Perfect for sticker packs
- **Transparent backgrounds:** Available with background removal

## ⚙️ Settings Menu Features

### Grid Size Configuration
- Quick presets (1×3, 2×2, 3×3, etc.)
- Custom size input
- Example use cases

### Quality Settings
- High/Medium/Low processing
- Background removal options
- Enhancement levels

### Statistics
- Usage tracking
- Cache management
- Processing history
- Performance metrics

## 🆘 Troubleshooting

### Common Issues

**"Please configure settings first"**
- Solution: Send `/start` and choose grid size + adaptation method

**"File size exceeds limit"**
- Solution: Compress image/video to under 50MB

**"Processing failed"**
- Try different adaptation method
- Use smaller grid size
- Check if file format is supported

**"Bot not responding"**
- Send `/cancel` then `/start` to reset
- Check if file meets requirements

**"Blurry emojis"**
- Use higher resolution input image
- Try smaller grid size
- Use "High Quality" processing

### Performance Tips

**Slow processing?**
- Use "Fast Mode" for testing
- Process smaller files first
- Try during off-peak hours

**Out of storage?**
- Use "🧹 Clean Cache" in settings
- Download and delete old emoji packs

## 📋 Examples by Use Case

### Social Media
- **Profile grid:** 3×3 for Instagram-style layout
- **Story timeline:** 1×5 for progression
- **Reaction set:** 2×2 for simple emotions

### Gaming
- **Character poses:** 2×4 for animation frames  
- **Item grid:** 4×4 for inventory-style layout
- **Health bar:** 1×10 for game UI elements

### Business
- **Logo breakdown:** 2×2 for brand elements
- **Process flow:** 1×6 for step-by-step guides
- **Team photos:** 3×2 for group layouts

### Art & Design
- **Pattern tiles:** 4×4 for repeating designs
- **Color palette:** 1×8 for color schemes
- **Texture samples:** 3×3 for material references

## 🔗 Automatic Telegram Sticker Packs

### How It Works
The bot **automatically creates** a Telegram sticker pack for you! No manual setup required.

### After Processing
1. **Bot creates sticker pack** automatically
2. **You get a direct link** like `t.me/addstickers/pack_123_abc_by_yourbot`  
3. **Click "🎯 Add Sticker Pack"** button
4. **Telegram opens** with your custom pack ready to add
5. **Start using** your emojis immediately!

### Features
- **Instant creation** - No waiting or manual steps
- **Unique pack names** - Each user gets their own pack
- **Direct integration** - Works seamlessly with Telegram
- **High quality** - All emojis are 512×512 PNG format

### Manual Sticker Pack Creation (Alternative)
If you prefer the traditional method:
1. Download emoji PNG files from bot
2. Open Telegram and message [@Stickers](https://t.me/stickers)
3. Send `/newpack`
4. Follow prompts to upload your emojis
5. Set emojis and publish pack

### Best Practices
- **512×512 PNG** format (bot provides this automatically)
- **Transparent backgrounds** (enable background removal option)
- **Clear, simple designs** work best as stickers
- **Consistent style** across emoji set

## 📞 Support

### Getting Help
- Use `/help` command for built-in guides
- Check FAQ section in help menu
- Send `/examples` for inspiration

### Reporting Issues
- Use "🐛 Report Bug" in help menu
- Include error messages and file details
- Describe steps that led to the problem

---

**Happy emoji creating! 🎨✨**

*Transform your images into custom emoji packs and make your Telegram conversations more expressive!*
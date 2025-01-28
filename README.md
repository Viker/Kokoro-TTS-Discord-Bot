# Kokoro TTS Bot

A Discord bot for high-quality text-to-speech conversion using the Kokoro TTS engine. This bot allows users to convert text messages to speech in voice channels with customizable voices, speeds, and other settings.

## Features

- Multiple TTS voices with customizable settings
- Per-user and per-guild settings
- Voice channel auto-join capability
- Message queue system with priorities
- Comprehensive error handling and recovery
- Performance monitoring and metrics
- Admin commands for bot management
- Caching system for improved performance

## Requirements

- Python 3.8 or higher
- FFmpeg installed and in system PATH
- Discord Bot Token
- Kokoro TTS model files (`kokoro-v0_19.onnx` and `voices.bin`)

### System Dependencies

- FFmpeg (for voice processing)
- Python development tools
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Viker/Kokoro-TTS-Discord-Bot.git
cd Kokoro-TTS-Discord-Bot
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a config.yaml file:
```yaml
discord_token: "YOUR_DISCORD_BOT_TOKEN"
command_prefix: "!"
model_path: "kokoro-v0_19.onnx"
voices_path: "voices.bin"
max_cache_size: 1000
max_queue_size: 100
message_ttl: 300
log_level: "INFO"
log_file: "bot.log"
settings_file: "settings.yaml"
```

5. Download the required model files to the working directory:
```bash
# Download either voices.json or voices.bin (bin is preferred)
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin

# Download the model
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx

## Usage

1. Start the bot:
```bash
python -m kokoro_bot.main
```

2. Discord Commands:
```
!join       - Join your voice channel
!leave      - Leave the voice channel
!voice      - List available voices or change voice
!speed      - Change TTS speed (0.5 to 2.0)
!metrics    - Show bot performance metrics (admin only)
!cleanup    - Clean up resources (admin only)
```

3. Any text message sent in the channel will be converted to speech when the bot is in a voice channel.

## Configuration

### Bot Settings

Key configuration options in `config.yaml`:

- `discord_token`: Your Discord bot token
- `command_prefix`: Command prefix (default: "!")
- `max_cache_size`: Maximum number of cached TTS generations
- `max_queue_size`: Maximum messages in queue per guild
- `message_ttl`: Message time-to-live in seconds
- `log_level`: Logging level (INFO, DEBUG, etc.)

### User Settings

Users can customize:
- Voice selection
- Speech speed
- Volume level
- Language preference

### Guild Settings

Administrators can set:
- Default voice
- Auto-join preferences
- Message length limits
- Timeout settings

## Project Structure

```
kokoro_bot/
├── README.md
├── requirements.txt
├── config.yaml
├── setup.py
├── tests/
│   ├── __init__.py
│   └── ...
└── kokoro_bot/
    ├── __init__.py
    ├── main.py
    ├── bot.py
    ├── core/
    │   ├── config.py
    │   ├── tts_engine.py
    │   └── ...
    ├── cogs/
    │   ├── voice.py
    │   └── admin.py
    └── utils/
        ├── cache.py
        ├── error_handler.py
        └── ...
```

## Development

### Setting Up Development Environment

1. Clone the repository
2. Create a virtual environment
3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 guidelines. Use flake8 for linting:
```bash
flake8 kokoro_bot
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

[Insert your chosen license here]

## Acknowledgments

- Discord.py library
- Kokoro TTS engine
- FFmpeg project

## Support

For issues and feature requests, please use the GitHub issue tracker.
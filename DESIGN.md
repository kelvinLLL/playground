# Design Document: opencode_extensions

## 1. Core Concepts
The `opencode_extensions` system is a lightweight framework for adding cross-platform auxiliary features (sound, voice, notifications) to a CLI environment. It follows a modular design to ensure zero impact on core application stability.

### 1.1 Architecture: Observer Pattern
The system uses the **Observer Pattern** to manage events:
- **`PluginManager`**: Acts as the central hub (Subject). It manages a registry of plugins and broadcasts events (e.g., `on_start`, `on_finish`, `on_error`).
- **Plugins**: Decoupled modules that implement specific event hooks. The manager uses duck typing, allowing any class with matching method names to function as a plugin.

## 2. Portability: The "Native Bridge" Pattern
To remain truly "universal" and lightweight, we employ a **Native Bridge** strategy.

### 2.1 Subprocess vs. Libraries
Instead of relying on heavy Python libraries (like `playsound` or `pyaudio`), we prioritize calling native OS utilities via `subprocess`.
- **macOS**: Uses `afplay` (built-in).
- **Windows**: Uses PowerShell's `System.Media.SoundPlayer` (built-in).
- **Linux**: Uses `aplay` (ALSA) or `paplay` (PulseAudio).
- **Why?**: This avoids "dependency hell," reduces install size, and ensures the extension system works "out of the box" on minimal environments.

## 3. Dependency Management: uv Workflow
While we favor native tools, some advanced features (like `VoicePlugin`) may eventually require external libraries.
- **`uv` Integration**: We use [uv](https://github.com/astral-sh/uv) for lightning-fast dependency resolution and virtual environment management.
- **Conditional Imports**: Plugins are designed with "Graceful Degradation." If a library like `speech_recognition` is missing, the plugin automatically enters a "Mock Mode" or disables itself with a clear warning, rather than crashing the application.

## 4. Extension Guide
### 4.1 Adding New Platforms
Adding support for new environments is straightforward:
1.  **Detection**: Use `sys.platform` to identify the environment.
2.  **Native Tooling**: Find a built-in command for the desired action (e.g., `termux-tts-speak` for Android via Termux).
3.  **Implementation**: Add a private handler method in the relevant plugin (e.g., `_play_android`) and call it via `subprocess.run()`.

## 5. Future Roadmap
- **Dynamic Plugin Discovery**: Automatically loading files from `plugins/` directory.
- **Web-based Dashboard**: A local web UI for toggling plugins.
- **Asynchronous Execution**: Native `asyncio` support for high-concurrency event handling.

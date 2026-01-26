# Design Document: opencode_extensions

## 1. Core Concepts
The `opencode_extensions` system is designed as a lightweight, "plug and play" framework for adding auxiliary functionality to the core application without introducing heavy dependencies or tightly coupled logic.

### 1.1 Architecture: Observer Pattern
At the heart of the system is the `PluginManager`, which implements a variation of the **Observer Pattern**. 
- **Manager (Subject)**: Maintains a registry of plugin instances and broadcasts events.
- **Plugins (Observers)**: Objects that implement specific hook methods (e.g., `on_start`, `on_finish`).
- **Decoupling**: The manager does not require plugins to inherit from a specific base class; it uses duck typing to check for the existence of callable hook methods. This simplifies plugin creation and reduces boilerplate.

## 2. Portability: The "Native Bridge" Pattern
One of the primary design goals is to remain "universal" and lightweight. To achieve this, we avoid heavy third-party libraries for simple system tasks (like playing audio).

### 2.1 Dependency-Free Execution
Instead of using libraries like `playsound` (which often require complex native dependencies like GStreamer or platform-specific backends), we use a **Native Bridge** approach via the `subprocess` module.
- **Mechanism**: The application detects the host OS (`sys.platform`) and calls native command-line utilities.
- **Mac**: `afplay`
- **Windows**: PowerShell (`Media.SoundPlayer`)
- **Linux**: `aplay` or `paplay`
- **Benefit**: This avoids "dependency hell" and ensures the extension system works immediately upon cloning the repository on any major OS.

## 3. Technical Stack
- **Language**: Python 3.8+
- **Standard Library**: Primary reliance on `subprocess`, `threading`, `logging`, and `typing`.
- **Environment Management**: [uv](https://github.com/astral-sh/uv) is the recommended tool for managing the environment, ensuring fast and reproducible setups.

## 4. Extension Guide
### 4.1 Adding New Events
To introduce a new event (e.g., `on_error`):
1.  Identify where the event occurs in the main application.
2.  Call `manager.trigger("on_error", error=e)`.
3.  Implement `on_error(self, error)` in any plugin that needs to respond.

### 4.2 Adding New Platforms
For features like the `SoundPlugin`, adding support for a new OS involves:
1.  Checking `sys.platform`.
2.  Identifying a built-in CLI tool for the task on that OS.
3.  Implementing a private `_play_<os>` method using `subprocess`.

## 5. Future Roadmap
- **Dynamic Loading**: Support for loading plugins from a dedicated directory without manual registration.
- **Priority System**: Allowing plugins to define execution order for specific events.
- **Asynchronous Hooks**: Support for `asyncio` based event hooks for non-blocking I/O intensive plugins.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code + Telegram Bot bidirectional communication system that enables:
- **Claude Code → Telegram**: Real-time notifications of task progress with actual output
- **Telegram → Claude Code**: Remote command execution and status queries
- **Interactive Q&A**: AskUserQuestion responses via Telegram inline keyboards
- **Multi-project Support**: Main server + project-specific servers with independent sessions

The system uses Flask webhooks, Claude Code hooks, and tmux for session management.

**IMPORTANT**: Claude Code MUST always run inside a tmux session. This is a core requirement for the bidirectional communication to work, especially for AskUserQuestion callback handling.

## Quick Start

### First-time Setup

```bash
# Install tel-start global command
./.claude/templates/install-tel-start.sh

# Configure main server
# Edit ~/.claude-telegram/config.json with your bot credentials

# Start main server (from any directory)
tel-start

# Or use the Claude Code skill
/tel-start
```

### Using the tel-start Skill

The `/tel-start` skill is the recommended way to start servers from within Claude Code:

1. Automatically starts the main server (port 8000)
2. Reads recent project list from `~/.claude-telegram/sessions.json`
3. Asks which project servers to start (multi-select)
4. Starts selected project servers with proper session names and ports

**Skill location**: `.claude/skills/tel-start/SKILL.md`

## Architecture

### Multi-project System

The system supports two deployment modes:

1. **Main Server** (port 8000)
   - Global server running in `main` tmux session
   - Uses `~/.claude-telegram/config.json`
   - Handles Telegram communication and routing

2. **Project Servers** (ports 8100+)
   - Each project runs in its own tmux session (named after project/repo)
   - Uses project-specific `.claude-telegram/config.json` (falls back to main config)
   - Ports auto-assigned starting from 8100

**Session Naming**: Determined by `claude.session_name` in config, or git repo name, or directory name.

### Core Components

**Modular Architecture**: The codebase has been refactored into a modular structure for better maintainability.

1. **webhook_server.py** - Main entry point (simplified to ~100 lines)
   - Dependency checking
   - Configuration loading
   - Logging setup
   - Flask app initialization
   - Route registration
   - Health check on startup

2. **webhook_modules/** - Modular components
   - **config.py** - Configuration management (loading, saving, accessing config)
   - **telegram_api.py** - Telegram API interactions (sending messages, callbacks)
   - **claude_tmux.py** - Tmux session management (sending tasks, session switching)
   - **question_handler.py** - AskUserQuestion handling (inline keyboards, answer processing)
   - **history.py** - Event history management (loading, saving, querying)
   - **health_check.py** - System health checks (Telegram API, tmux server)
   - **notification.py** - Smart notification filtering
   - **commands.py** - Telegram command handlers (/status, /sessions, /help, etc.)
   - **routes.py** - Flask route definitions and request handling
   - **state.py** - Global state management (last_outputs, server uptime)

3. **notify-telegram-smart.sh** - Hook script that processes Claude Code events
   - Receives JSON via stdin from Claude Code hooks
   - Formats messages based on event type (stop, tool_use, subagent, notification)
   - Sends formatted data to webhook server
   - Located in `.claude/` directory

4. **Configuration Files**
   - `~/.claude-telegram/config.json` - Main/global configuration
   - `<project>/.claude-telegram/config.json` - Project-specific configuration (optional, higher priority)
   - Contains: Telegram credentials, webhook settings, tmux session names, security settings

### Data Flow

```
Claude Code Task Completion
    ↓
Hook Event Triggered (Stop/PostToolUse/SubagentStop)
    ↓
JSON sent to notify-telegram-smart.sh via stdin
    ↓
Script formats message and POSTs to /claude-hook
    ↓
Webhook server forwards to Telegram API
    ↓
User receives notification

User sends Telegram command
    ↓
Telegram POSTs to /telegram-webhook
    ↓
Webhook validates secret_token and chat_id
    ↓
Command executed (tmux capture, send-keys, etc.)
    ↓
Result sent back to Telegram

Claude Code calls AskUserQuestion
    ↓
Notification hook triggered (idle_prompt)
    ↓
Hook script extracts questions data
    ↓
Sent to webhook server (is_question=true)
    ↓
Generate Telegram inline keyboard
    ↓
User clicks button in Telegram
    ↓
Webhook receives callback_query
    ↓
Send answer to Claude Code via tmux
```

## Development Commands

### Using tel-start (Recommended)

```bash
# Start main server + select project servers (interactive)
/tel-start  # Use this in Claude Code

# Or directly in bash
tel-start   # Starts server for current directory

# Check if tel-start is installed
which tel-start

# Install if missing
./.claude/templates/install-tel-start.sh
```

### CRITICAL: Always Run in Tmux

**Before starting any work, ensure Claude Code is running in a tmux session:**

```bash
# Check if already in tmux
echo $TMUX

# If not in tmux, create and attach to a session
# Session name should match config (default: project name or "claude")
tmux new-session -s <session-name>

# Or attach to existing session
tmux attach -t <session-name>

# List all sessions
tmux list-sessions
```

### Running the Server

**Recommended**: Use `tel-start` (see above)

**Manual start** (if needed):

```bash
# Start webhook server directly
python3 webhook_server.py

# Server runs on configured port (default: 8000 for main, 8100+ for projects)

# Restart server after code changes
pkill -f "python3 webhook_server.py" && nohup python3 webhook_server.py > logs/server.log 2>&1 &

# Check server health
curl http://localhost:8000/health
```

### Testing

```bash
# Test Telegram API connection
./tests/test_telegram.sh

# Test hook → webhook → Telegram flow
./tests/test_hook.sh

# Test Telegram → webhook flow
./tests/test_webhook.sh

# Test complete local flow (no external dependencies)
./tests/test_local_only.sh

# Manual hook test
echo '{"response":"test","duration_ms":123}' | ./.claude/notify-telegram-smart.sh stop
```

### Tmux Session Management

```bash
# List all sessions
tmux list-sessions

# View recent project sessions
cat ~/.claude-telegram/sessions.json

# Capture current output
tmux capture-pane -t <session-name> -p

# Send command to session
tmux send-keys -t <session-name> "echo test" C-m

# Kill a session
tmux kill-session -t <session-name>
```

### Logs

```bash
# View webhook logs
tail -f logs/webhook.log

# View hook logs
tail -f ~/.claude/hooks.log

# Check health
curl http://localhost:8000/health
```

## Configuration

### Configuration File Hierarchy

1. **Main config**: `~/.claude-telegram/config.json` (global defaults)
2. **Project config**: `<project>/.claude-telegram/config.json` (overrides main config)

### Initial Setup

1. Install global command:
```bash
./.claude/templates/install-tel-start.sh
```

2. Create main configuration at `~/.claude-telegram/config.json`:
```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID",
    "secret_token": "RANDOM_SECRET"
  },
  "webhook": {
    "host": "127.0.0.1",
    "port": 8000,
    "port_range_start": 8100
  },
  "claude": {
    "session_name": "main"
  }
}
```

3. Get Telegram credentials:
   - `bot_token`: From @BotFather
   - `chat_id`: Get from `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - `secret_token`: Change to random string

4. (Optional) Create project-specific config at `<project>/.claude-telegram/config.json` to override settings

5. Ensure hook script is executable:
```bash
chmod +x .claude/notify-telegram-smart.sh
```

### Claude Code Hooks

The `.claude/settings.json` configures hooks that trigger on:
- **Stop**: Task completion (sends response preview, duration, timestamp)
- **PostToolUse**: After Bash/Read/Write/Edit tools (sends tool name, input, output)
- **SubagentStop**: Subagent completion (sends type, description, result)
- **Notification**: Generic notifications

Hooks receive JSON via stdin and pass it to `notify-telegram-smart.sh`.

## Telegram Commands

**Key commands for development**:

- `/status` - Get current tmux output (last 20 lines)
- `/last_output` - Get full last response from Claude Code
- `/projects` - List all running projects and switch between them
- `/help` - Show available commands
- `/claude <command>` - Execute command in Claude Code tmux session

**Note**: See README.md for complete command list including `/ask`, `/session`, `/history`, etc.

## Test Mode

Set `TEST_MODE=1` environment variable to disable actual Telegram API calls (logs messages instead):

```bash
TEST_MODE=1 python3 webhook_server.py
```

## Security Notes

- Webhook validates `X-Telegram-Bot-Api-Secret-Token` header
- Only configured `chat_id` can send commands
- Dangerous commands (rm, dd, format, shutdown) are blacklisted in config
- Command whitelist can be enabled via `security.command_whitelist`

## File Structure

```
claude-code-with-telegram/
├── webhook_server.py              # Main entry point (~100 lines, simplified)
├── webhook_server.py.old          # Backup of original monolithic file
├── webhook_modules/               # Modular components
│   ├── __init__.py                # Module exports
│   ├── config.py                  # Configuration management
│   ├── telegram_api.py            # Telegram API interactions
│   ├── claude_tmux.py             # Tmux session management
│   ├── question_handler.py        # AskUserQuestion handling
│   ├── history.py                 # Event history management
│   ├── health_check.py            # System health checks
│   ├── notification.py            # Smart notification filtering
│   ├── commands.py                # Telegram command handlers
│   ├── routes.py                  # Flask route definitions
│   └── state.py                   # Global state management
├── config.json                    # Configuration (contains secrets, gitignored)
├── requirements.txt               # Python dependencies
├── .claude/
│   ├── notify-telegram-smart.sh   # Hook script
│   ├── settings.json              # Claude Code hooks config
│   ├── settings.local.json        # Local overrides
│   ├── skills/tel-start/          # tel-start skill
│   └── templates/                 # Template scripts
│       ├── tel-start.sh           # Main startup script
│       ├── install-tel-start.sh   # Installation script
│       ├── check-dependencies.sh  # Dependency checker
│       ├── validate-config.sh     # Config validator
│       └── list-sessions.sh       # Session lister
├── tests/                         # Test scripts
├── logs/                          # Log files
├── docs/
│   ├── prds/                      # Product requirements
│   ├── architecture/              # Architecture docs
│   └── ui_guide.md                # Telegram UI design guide
└── ~/.claude-telegram/            # Global config directory
    ├── config.json                # Main configuration
    ├── sessions.json              # Recent project sessions
    └── logs/                      # Global logs
```

## Common Issues

### Telegram not receiving messages
- Verify bot_token and chat_id in config.json
- Test with: `./tests/test_telegram.sh`
- Check logs: `tail -f logs/webhook.log`

### Hooks not triggering
- Verify script permissions: `ls -la .claude/notify-telegram-smart.sh`
- Test manually: `echo '{"response":"test"}' | ./.claude/notify-telegram-smart.sh stop`
- Check hook logs: `tail -f ~/.claude/hooks.log`

### Webhook not receiving requests
- Check if port 8000 is available: `lsof -i :8000`
- Verify server is running: `ps aux | grep webhook_server.py`
- Test health endpoint: `curl http://localhost:8000/health`

## Development Guidelines

### Telegram Message Formatting

When modifying Telegram message output, follow the UI design guide at `docs/ui_guide.md`:

- Use clean, minimal formatting (bold titles, plain body)
- Limit emoji usage (max 1-2 per message)
- Keep button text under 20 characters
- Use proper spacing and hierarchy
- Follow the established symbol conventions (✓ for success, ✗ for error, etc.)

### Template Scripts

The `.claude/templates/` directory contains reusable scripts:

- **tel-start.sh**: Main server startup logic (called by global `tel-start` command)
- **install-tel-start.sh**: Installs global command to `/usr/local/bin/tel-start`
- **check-dependencies.sh**: Validates Python packages and system tools
- **validate-config.sh**: Checks config file structure and required fields
- **list-sessions.sh**: Lists recent project sessions from `sessions.json`

When modifying startup logic, edit the template scripts, not the global command.

### Multi-project Architecture

When adding features that interact with tmux sessions:

1. Always use session names from config (`claude.session_name`)
2. Support both main server (port 8000) and project servers (8100+)
3. Test with multiple concurrent sessions
4. Update `sessions.json` when creating new project sessions

### Hook Development

When modifying `.claude/notify-telegram-smart.sh`:

1. Preserve JSON parsing logic for all event types
2. Test with manual hook invocation: `echo '{"response":"test"}' | ./.claude/notify-telegram-smart.sh stop`
3. Check logs at `~/.claude/hooks.log`
4. Ensure AskUserQuestion handling (idle_prompt event) remains functional

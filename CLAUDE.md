# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code + Telegram Bot bidirectional communication system that enables:
- **Claude Code → Telegram**: Real-time notifications of task progress with actual output
- **Telegram → Claude Code**: Remote command execution and status queries

The system uses Flask webhooks, Claude Code hooks, and tmux for session management.

## Architecture

### Core Components

1. **webhook_server.py** - Flask server handling bidirectional communication
   - `/claude-hook` endpoint: Receives notifications from Claude Code hooks
   - `/telegram-webhook` endpoint: Receives commands from Telegram
   - `/health` endpoint: Health check
   - Stores last outputs in memory for retrieval via `/last_output` command

2. **notify-telegram-smart.sh** - Hook script that processes Claude Code events
   - Receives JSON via stdin from Claude Code hooks
   - Formats messages based on event type (stop, tool_use, subagent, notification)
   - Sends formatted data to webhook server
   - Located in `.claude/` directory

3. **config.json** - Central configuration
   - Telegram bot credentials (bot_token, chat_id, secret_token)
   - Webhook settings (host, port, paths)
   - Claude Code settings (tmux_session, allowed_commands)
   - Security settings (allowed_chat_ids, command_whitelist)

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

### Running the Server

```bash
# Start webhook server
python3 webhook_server.py

# Server runs on http://127.0.0.1:8000
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
# Create Claude Code tmux session
tmux new-session -d -s claude

# List sessions
tmux list-sessions

# Capture current output
tmux capture-pane -t claude -p

# Send command to session
tmux send-keys -t claude "echo test" C-m
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

### Initial Setup

1. Edit `config.json` with your Telegram credentials:
   - `bot_token`: From @BotFather
   - `chat_id`: Get from `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - `secret_token`: Change to random string

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Ensure hook script is executable:
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

- `/status` - Get current tmux output (last 20 lines)
- `/last_output` - Get full last response from Claude Code
- `/help` - Show available commands
- `/claude <command>` - Execute command in Claude Code tmux session

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
claude_code_telegram/
├── webhook_server.py           # Main Flask server
├── config.json                 # Configuration (contains secrets)
├── requirements.txt            # Python dependencies
├── .claude/
│   ├── notify-telegram-smart.sh  # Hook script
│   ├── settings.json            # Claude Code hooks config
│   └── settings.local.json      # Local overrides
├── tests/                      # Test scripts
├── logs/                       # Log files
└── docs/prds/                  # Documentation
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

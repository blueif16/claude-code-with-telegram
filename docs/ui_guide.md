# Telegram Bot UI Design Guide

Elegant, minimal patterns for bot messages and menus.

---

## Core Principles

1. **Breathe** → whitespace > decoration
2. **One idea per message** → don't cram
3. **Hierarchy through typography** → bold titles, plain body
4. **Symbols as punctuation** → not decoration

---

## Message Templates

### Status/Notification
```html
<b>✓ Task Complete</b>

Build deployed to production
<code>v2.4.1</code> → 3 files changed

<a href="url">View details →</a>
```

### Error/Alert
```html
<b>※ Attention Required</b>

Database connection failed
Retry in <code>30s</code>

◆ Check credentials
◆ Verify network
```

### Menu Header
```html
<b>Settings</b>

Select an option below
```

### Data Display
```html
<b>Account</b>

<code>Balance</code>  $1,240.00
<code>Status</code>   Active ✓
<code>Plan</code>     Pro

───────────
<i>Updated just now</i>
```

### Confirmation
```html
<b>Confirm Action</b>

Delete <code>project-alpha</code>?
This cannot be undone.
```

### List/Feed Item
```html
<b>New Order</b> #4821

◆ 2× Widget Pro
◆ 1× Cable Kit

<code>$89.00</code> → Pending
```

---

## Inline Keyboard Patterns

### Simple Actions (1 row)
```
[ ✓ Confirm ]  [ ✗ Cancel ]
```

### Navigation (with back)
```
[  Option A  ]  [  Option B  ]
[         ← Back            ]
```

### Pagination
```
[  ←  ]  [ 2/10 ]  [  →  ]
```

### Settings Toggle
```
[  Notifications: ON ✓  ]
[  Dark Mode: OFF       ]
[       ← Back          ]
```

---

## Button Text Rules

| Do | Don't |
|----|-------|
| `Confirm` | `Click here to confirm` |
| `← Back` | `Go back to menu` |
| `View →` | `View details` |
| `Settings` | `⚙️ Settings ⚙️` |

Keep under 20 chars. One emoji max (or none).

---

## Spacing Pattern

```
<b>Title</b>
                    ← blank line
Body text here
                    ← blank line
◆ Point one
◆ Point two
                    ← blank line
───────────         ← optional divider
<i>Footer/meta</i>
```

---

## Anti-Patterns

```html
<!-- ❌ Too busy -->
🚀 <b>✨ WELCOME!! ✨</b> 🎉
Check out our AMAZING features!!!
👉 Feature 1 💪
👉 Feature 2 🔥
👉 Feature 3 ⭐

<!-- ✓ Clean -->
<b>Welcome</b>

Get started with your dashboard.

◆ Create project
◆ Invite team
◆ Configure settings
```

---

## Symbol Usage

| Context | Symbol |
|---------|--------|
| Success | ✓ |
| Error | ✗ |
| Warning | ※ |
| List item | ◆ ◇ |
| Arrow/CTA | → |
| Divider | ─────── |
| Active | ◉ |
| Inactive | ○ |

---

## Code Snippet (Python)

```python
def format_status(title, items, footer=None):
    lines = [f"<b>{title}</b>", ""]
    for k, v in items.items():
        lines.append(f"<code>{k}</code>  {v}")
    if footer:
        lines += ["", "───────────", f"<i>{footer}</i>"]
    return "\n".join(lines)

# Usage
msg = format_status(
    "Account",
    {"Balance": "$1,240", "Status": "Active ✓"},
    "Updated just now"
)
bot.send_message(chat_id, msg, parse_mode="HTML")
```

---

## Quick Checklist

- [ ] Title is bold, body is plain
- [ ] Max 1-2 blank lines between sections  
- [ ] No emoji overload
- [ ] Buttons are terse
- [ ] Back button exists in submenus
- [ ] Mobile-friendly (no wide tables)
# InlineShell

Run shell commands inline in Sublime Text, with streaming output and history completion.

## Features

- Run the current line or selected text as a shell command
- Pipe selected text into a command using a trailing `|command`
- Stream output inline, without blocking the editor
- History completion for previously run commands
- Confirmation prompt for dangerous commands
- Blocks interactive commands that require a real terminal

## Install

### Package Control

Search for `InlineShell` in Package Control (once the package is accepted).

### Manual

1. Open Sublime Text
2. Menu: `Preferences` -> `Browse Packages...`
3. Create a folder named `InlineShell`
4. Copy the plugin files into that folder

## Usage

### Run a command

1. Type a command, for example `ls -la`
2. Run the command palette entry `Inline Shell: Run Line or Selection`
3. Output appears on the next line

### Run a selection

Select any text and run `Inline Shell: Run Line or Selection`.

### Pipe selection into a command

Select content that ends with a pipe command:

```
{"name": "test", "value": 123}
|grep name
```

Or use an inline pipe:

```
{"name": "test"} |grep name
```

### History completion

Run `Inline Shell: History Complete` to pick a previous command.

## Key bindings

This package does not define default key bindings to avoid overriding Sublime defaults.
Add your own in your user keymap if you want them. Example:

```json
[
  {"keys": ["super+enter"], "command": "run_command_run_line"},
  {"keys": ["ctrl+tab"], "command": "run_command_history_complete"}
]
```

## Shell aliases

If you want custom aliases or PATH entries, create a lightweight shell rc file:

**zsh**: `~/.zshrc_lite`

```
alias ll='ls -la'
alias g='git'
export PATH="$HOME/.local/bin:$PATH"
```

**bash**: `~/.bashrc_lite`

```
alias ll='ls -la'
```

## Blocked commands

The following interactive commands are blocked and will prompt you to use a terminal:

- `vim`, `vi`, `nano`
- `top`, `htop`
- `less`, `more`, `man`
- `watch`

## Dangerous command protection

Commands like these require confirmation:

- `rm -rf`, `rm -f`
- `sudo rm`
- `dd of=/dev/...`
- `mkfs`
- `chmod 777 /`
- `shutdown`, `reboot`

## Requirements

- Sublime Text 4
- macOS or Linux
- zsh or bash

## License

MIT

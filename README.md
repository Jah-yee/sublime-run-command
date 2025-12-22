# RunCommand

在 Sublime Text 中直接执行 Shell 命令的插件。

## 功能

- **快捷执行** - 光标所在行按快捷键直接执行命令
- **选中执行** - 选中任意文本作为命令执行
- **管道支持** - 选中内容 + `|命令` 实现管道操作
- **流式输出** - 命令输出实时显示，不卡编辑器
- **历史补全** - 自动补全历史命令
- **危险命令保护** - `rm -rf` 等危险命令需确认
- **右键菜单** - 选中文本右键可执行

## 安装

### 方法一：手动安装

1. 打开 Sublime Text
2. 菜单 `Preferences` → `Browse Packages...`
3. 在打开的目录中创建 `RunCommand` 文件夹
4. 将所有文件复制到该文件夹

### 方法二：Git Clone

```bash
cd ~/Library/Application\ Support/Sublime\ Text/Packages/  # macOS
# 或
cd ~/.config/sublime-text/Packages/  # Linux

git clone https://github.com/randolph555/RunCommand.git
```

## 使用

### 快捷键

| 操作 | macOS | Linux |
|------|-------|-------|
| 执行命令 | `Cmd+Enter` | `Ctrl+Enter` |
| 历史补全 | `Ctrl+Tab` | `Ctrl+Tab` |

### 基本用法

1. 输入命令，如 `ls -la`
2. 按 `Cmd+Enter`（macOS）或 `Ctrl+Enter`（Linux）
3. 输出显示在命令下方

### 选中执行

选中任意文本，按快捷键或右键选择「执行命令」

### 管道操作

选中内容（包括最后的管道命令）：
```
{"name": "test", "value": 123}
|grep name
```
按快捷键，前面的内容会通过管道传给 `grep`

也支持行内管道：
```
{"name": "test"} |grep name
```

### 历史补全

- 输入命令开头几个字符，自动弹出匹配的历史命令
- 按 `Ctrl+Tab` 打开历史命令列表

## 自定义别名

如果需要使用自定义的 shell 别名或函数，创建轻量配置文件：

**zsh 用户** - 创建 `~/.zshrc_lite`：
```bash
# 只放需要的别名和 PATH
alias ll='ls -la'
alias g='git'
export PATH="$HOME/.local/bin:$PATH"
```

**bash 用户** - 创建 `~/.bashrc_lite`：
```bash
alias ll='ls -la'
```

插件会自动加载这个文件，比加载完整的 `.zshrc` 快很多。

## 被屏蔽的命令

以下交互式命令会提示在终端运行：
- `vim`, `vi`, `nano`
- `top`, `htop`
- `less`, `more`, `man`
- `watch`

## 危险命令保护

以下命令会弹出确认框：
- `rm -rf`、`rm -f` 等删除命令
- `sudo rm`
- `dd of=/dev/xxx`
- `mkfs`
- `chmod 777 /`
- `shutdown`、`reboot`

## 系统要求

- Sublime Text 4
- macOS 或 Linux
- zsh 或 bash

## License

MIT

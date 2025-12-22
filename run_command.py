import sublime
import sublime_plugin
import subprocess
import os
import threading
import json
import re
import sys

# 只支持 macOS 和 Linux
IS_WINDOWS = sys.platform == 'win32'

# 获取默认 shell
def get_default_shell():
    for shell in ['/bin/zsh', '/usr/bin/zsh', '/bin/bash', '/usr/bin/bash']:
        if os.path.exists(shell):
            return shell
    return '/bin/sh'

DEFAULT_SHELL = get_default_shell()

# 轻量配置文件路径
def get_lite_rc_path():
    home = os.path.expanduser("~")
    if 'zsh' in DEFAULT_SHELL:
        return os.path.join(home, '.zshrc_lite')
    elif 'bash' in DEFAULT_SHELL:
        return os.path.join(home, '.bashrc_lite')
    return None

BLOCKED = ["top", "htop", "vim", "vi", "nano", "watch", "less", "more", "man"]

# 危险命令模式（需要确认才能执行）
DANGEROUS_PATTERNS = [
    # rm 相关
    (r'\brm\s+(-[rfRvI]*\s+)*/', "删除根目录下的文件"),
    (r'\brm\s+(-[rfRvI]*\s+)*~', "删除用户目录下的文件"),
    (r'\brm\s+-[rfRvI]*r[rfRvI]*\s', "递归删除"),
    (r'\brm\s+-[rfRvI]*f[rfRvI]*\s', "强制删除"),
    # 危险的重定向
    (r'>\s*/dev/sd[a-z]', "写入磁盘设备"),
    # dd 命令
    (r'\bdd\s+.*of=/dev/', "写入设备"),
    # mkfs 格式化
    (r'\bmkfs', "格式化文件系统"),
    # chmod/chown 危险操作
    (r'\bchmod\s+(-R\s+)?777\s+/', "递归修改根目录权限"),
    (r'\bchown\s+-R\s+.*\s+/', "递归修改根目录所有者"),
    # 危险的命令组合
    (r':\(\)\s*\{\s*:\|:\s*&\s*\}\s*;', "Fork 炸弹"),
    (r'\bsudo\s+rm\s', "sudo 删除"),
    (r'\bsudo\s+dd\s', "sudo 写入设备"),
    # 清空文件
    (r'>\s*/etc/', "清空系统配置文件"),
    (r'>\s*~/', "清空用户目录文件"),
    # 关机重启
    (r'\b(shutdown|reboot|halt|poweroff)\b', "关机/重启"),
]

MAX_HISTORY = 100

# 命令历史
_command_history = []
_history_file = os.path.join(sublime.packages_path(), 'User', 'shell_history.json')


def load_history():
    """加载历史记录"""
    global _command_history
    try:
        if os.path.exists(_history_file):
            with open(_history_file, 'r', encoding='utf-8') as f:
                _command_history = json.load(f)
    except:
        _command_history = []


def save_history():
    """保存历史记录"""
    try:
        os.makedirs(os.path.dirname(_history_file), exist_ok=True)
        with open(_history_file, 'w', encoding='utf-8') as f:
            json.dump(_command_history[-MAX_HISTORY:], f, ensure_ascii=False)
    except:
        pass


def add_to_history(cmd):
    """添加命令到历史"""
    cmd = cmd.strip()
    if not cmd:
        return
    # 去重：如果已存在则移到最后
    if cmd in _command_history:
        _command_history.remove(cmd)
    _command_history.append(cmd)
    save_history()


def plugin_loaded():
    """插件加载时读取历史"""
    load_history()


def check_dangerous_command(cmd):
    """检查是否是危险命令，返回 (是否危险, 原因)"""
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return True, reason
    return False, ""


class InsertOutputTextCommand(sublime_plugin.TextCommand):
    """辅助命令：在指定位置插入文本"""
    def run(self, edit, point, text):
        self.view.insert(edit, point, text)


class ShellHistoryCompleteCommand(sublime_plugin.TextCommand):
    """Tab 补全命令"""
    def run(self, edit):
        if not _command_history:
            return
        
        sel = self.view.sel()
        if not sel:
            return
        
        # 获取当前行内容
        line_region = self.view.line(sel[0])
        line = self.view.substr(line_region).strip()
        
        if not line:
            # 空行显示最近的命令
            matches = _command_history[-10:]
        else:
            # 匹配以当前输入开头的命令
            matches = [cmd for cmd in _command_history if cmd.startswith(line)]
        
        if not matches:
            return
        
        # 去重并反转（最近的在前）
        matches = list(dict.fromkeys(reversed(matches)))
        
        def on_select(idx):
            if idx >= 0:
                self.view.run_command('replace_line_content', {'text': matches[idx]})
        
        self.view.window().show_quick_panel(matches, on_select)


class ReplaceLineContentCommand(sublime_plugin.TextCommand):
    """替换当前行内容"""
    def run(self, edit, text):
        sel = self.view.sel()
        if not sel:
            return
        line_region = self.view.line(sel[0])
        self.view.replace(edit, line_region, text)


class ShellHistoryAutoComplete(sublime_plugin.EventListener):
    """自动补全监听器"""
    
    def on_modified_async(self, view):
        """输入时自动触发补全"""
        if not _command_history:
            return
        
        sel = view.sel()
        if not sel:
            return
        
        # 获取当前行内容
        line_region = view.line(sel[0])
        line = view.substr(line_region).strip()
        
        # 至少输入2个字符才触发
        if len(line) < 2:
            return
        
        # 检查是否有匹配的历史命令
        for cmd in reversed(_command_history):
            if cmd.startswith(line) and cmd != line:
                view.run_command('auto_complete', {
                    'disable_auto_insert': True,
                    'next_completion_if_showing': False
                })
                break
    
    def on_query_completions(self, view, prefix, locations):
        if not _command_history:
            return None
        
        # 获取当前行内容（到光标位置）
        line_region = view.line(locations[0])
        line_start = line_region.begin()
        cursor = locations[0]
        line_to_cursor = view.substr(sublime.Region(line_start, cursor)).lstrip()
        
        if not line_to_cursor:
            return None
        
        # 匹配历史命令，返回完整命令作为补全
        completions = []
        for cmd in reversed(_command_history):
            if cmd.startswith(line_to_cursor) and cmd != line_to_cursor:
                # trigger 显示完整命令，completion 也是完整命令
                completions.append(sublime.CompletionItem(
                    trigger=cmd,
                    completion=cmd,
                    kind=(sublime.KIND_ID_SNIPPET, "⌘", "历史")
                ))
            if len(completions) >= 10:
                break
        
        if completions:
            return sublime.CompletionList(completions, flags=sublime.INHIBIT_WORD_COMPLETIONS)
        return None
    
    def on_post_text_command(self, view, command_name, args):
        """补全后修复：如果行内有重复前缀，删除它"""
        if command_name not in ('commit_completion', 'insert_best_completion'):
            return
        
        sel = view.sel()
        if not sel:
            return
        
        line_region = view.line(sel[0])
        line = view.substr(line_region)
        
        # 检查是否有重复（比如 "whwhoami" -> "whoami"）
        for cmd in _command_history:
            # 查找重复模式
            for i in range(1, len(cmd)):
                prefix = cmd[:i]
                if line.strip() == prefix + cmd:
                    # 发现重复，替换为正确的命令
                    view.run_command('replace_line_content', {'text': cmd})
                    return


class RunLineInShellCommand(sublime_plugin.TextCommand):
    """主命令：执行当前行的 shell 命令"""
    def run(self, edit):
        for sel in self.view.sel():
            selected_text = self.view.substr(sel)
            
            # 检查是否有选中的文本
            if sel.size() > 0 and selected_text.strip():
                # 获取选中区域最后一行，看是否有管道命令
                lines = selected_text.split('\n')
                last_line = lines[-1]
                
                # 检查最后一行是否包含管道命令
                pipe_idx = -1
                input_text = ""
                pipe_cmd = ""
                
                if last_line.strip().startswith('|'):
                    # 独立管道行
                    input_text = '\n'.join(lines[:-1])
                    pipe_cmd = last_line.strip()[1:].strip()
                    pipe_idx = 0
                elif '|' in last_line:
                    # 行内管道，找最后一个 | 的位置
                    pipe_idx = last_line.rfind('|')
                    input_text = '\n'.join(lines[:-1])
                    if input_text:
                        input_text += '\n'
                    input_text += last_line[:pipe_idx]
                    pipe_cmd = last_line[pipe_idx + 1:].strip()
                
                if pipe_idx >= 0 and pipe_cmd:
                    insert_point = sel.end()
                    self.view.insert(edit, insert_point, "\n")
                    self._run_pipe_with_stdin(input_text, pipe_cmd, insert_point + 1)
                    continue
                
                # 没有管道，直接执行选中的文本作为命令
                cmd = selected_text.strip()
                if '\n' not in cmd:  # 单行选中
                    cmd_name = cmd.split()[0] if cmd.split() else ""
                    if cmd_name in BLOCKED:
                        self.view.insert(edit, sel.end(), "\n[交互式命令，请在终端运行]")
                        continue
                    
                    is_dangerous, reason = check_dangerous_command(cmd)
                    if is_dangerous:
                        self._confirm_dangerous(cmd, sel, reason)
                        continue
                    
                    add_to_history(cmd)
                    
                    # ll 别名
                    if cmd == "ll" or cmd.startswith("ll "):
                        cmd = "ls -la" + cmd[2:]
                    
                    cwd = os.path.expanduser("~")
                    if self.view.file_name():
                        cwd = os.path.dirname(self.view.file_name())
                    
                    self.view.insert(edit, sel.end(), "\n")
                    insert_point = sel.end() + 1
                    
                    thread = threading.Thread(
                        target=self._run_command,
                        args=(cmd, cwd, self.view, insert_point)
                    )
                    thread.daemon = True
                    thread.start()
                    continue
            
            # 原有逻辑：执行当前行
            line_region = self.view.line(sel)
            line = self.view.substr(line_region).strip()
            
            if not line:
                continue
            
            cmd_name = line.split()[0]
            if cmd_name in BLOCKED:
                self.view.insert(edit, line_region.end(), "\n[交互式命令，请在终端运行]")
                continue
            
            # 检查危险命令
            is_dangerous, reason = check_dangerous_command(line)
            if is_dangerous:
                self._confirm_dangerous(line, line_region, reason)
                continue
            
            self._execute_command(edit, line, line_region)
    
    def _run_pipe_command(self, cmd, insert_point):
        """执行管道命令"""
        cwd = os.path.expanduser("~")
        if self.view.file_name():
            cwd = os.path.dirname(self.view.file_name())
        
        thread = threading.Thread(
            target=self._run_command,
            args=(cmd, cwd, self.view, insert_point)
        )
        thread.daemon = True
        thread.start()
    
    def _run_pipe_with_stdin(self, input_text, pipe_cmd, insert_point):
        """使用 stdin 直接传递内容到管道命令"""
        cwd = os.path.expanduser("~")
        if self.view.file_name():
            cwd = os.path.dirname(self.view.file_name())
        
        def run():
            try:
                # 构建命令
                lite_rc = get_lite_rc_path()
                if lite_rc and os.path.exists(lite_rc):
                    wrapped_cmd = '{} -c "source {} && {}"'.format(
                        DEFAULT_SHELL, lite_rc, pipe_cmd.replace('"', '\\"'))
                else:
                    wrapped_cmd = pipe_cmd
                
                proc = subprocess.Popen(
                    wrapped_cmd,
                    shell=True,
                    executable=DEFAULT_SHELL,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    bufsize=1
                )
                
                # 写入输入内容到 stdin
                proc.stdin.write(input_text.encode('utf-8'))
                proc.stdin.close()
                
                current_point = [insert_point]
                view = self.view
                
                def insert_text(text):
                    def do_insert():
                        if not view.is_valid():
                            return
                        view.run_command('insert_output_text', {
                            'point': current_point[0],
                            'text': text
                        })
                        current_point[0] += len(text)
                    sublime.set_timeout(do_insert, 0)
                
                byte_buffer = b''
                while True:
                    chunk = proc.stdout.read(32)
                    if not chunk:
                        if byte_buffer:
                            insert_text(byte_buffer.decode('utf-8', errors='replace'))
                        break
                    
                    byte_buffer += chunk
                    safe_len = len(byte_buffer)
                    while safe_len > 0:
                        try:
                            byte_buffer[:safe_len].decode('utf-8')
                            break
                        except UnicodeDecodeError:
                            safe_len -= 1
                    
                    if safe_len > 0:
                        text = byte_buffer[:safe_len].decode('utf-8')
                        byte_buffer = byte_buffer[safe_len:]
                        insert_text(text)
                
                proc.wait()
                
            except Exception as e:
                def show_error():
                    if self.view.is_valid():
                        self.view.run_command('insert_output_text', {
                            'point': insert_point,
                            'text': '[错误: ' + str(e) + ']'
                        })
                sublime.set_timeout(show_error, 0)
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    def _confirm_dangerous(self, line, line_region, reason):
        """确认危险命令"""
        def on_confirm(confirmed):
            if confirmed:
                self.view.run_command('execute_confirmed_command', {
                    'line': line,
                    'line_end': line_region.end()
                })
        
        sublime.ok_cancel_dialog(
            "⚠️ 危险命令警告\n\n"
            "命令: {}\n"
            "原因: {}\n\n"
            "确定要执行吗？".format(line, reason),
            "执行"
        ) and on_confirm(True)
    
    def _execute_command(self, edit, line, line_region):
        """执行命令"""
        # 记录到历史
        add_to_history(line)
        
        # ll 别名：只在命令开头或管道后替换
        cmd = line
        if cmd == "ll" or cmd.startswith("ll "):
            cmd = "ls -la" + cmd[2:]
        elif " ll" in cmd:
            cmd = cmd.replace(" ll ", " ls -la ").replace(" ll\n", " ls -la\n")
            if cmd.endswith(" ll"):
                cmd = cmd[:-3] + " ls -la"
        
        # 获取工作目录：优先用当前文件所在目录
        cwd = os.path.expanduser("~")
        if self.view.file_name():
            cwd = os.path.dirname(self.view.file_name())
        
        # 先插入换行
        self.view.insert(edit, line_region.end(), "\n")
        insert_point = line_region.end() + 1
        
        # 启动异步执行
        thread = threading.Thread(
            target=self._run_command,
            args=(cmd, cwd, self.view, insert_point)
        )
        thread.daemon = True
        thread.start()
    
    def _run_command(self, cmd, cwd, view, insert_point):
        """异步执行命令并流式输出"""
        try:
            # 构建命令
            lite_rc = get_lite_rc_path()
            if lite_rc and os.path.exists(lite_rc):
                wrapped_cmd = '{} -c "source {} && {}"'.format(
                    DEFAULT_SHELL, lite_rc, cmd.replace('"', '\\"'))
            else:
                wrapped_cmd = cmd
            
            proc = subprocess.Popen(
                wrapped_cmd,
                shell=True,
                executable=DEFAULT_SHELL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                bufsize=1
            )
            
            current_point = [insert_point]
            
            def insert_text(text):
                def do_insert():
                    if not view.is_valid():
                        return
                    view.run_command('insert_output_text', {
                        'point': current_point[0],
                        'text': text
                    })
                    current_point[0] += len(text)
                sublime.set_timeout(do_insert, 0)
            
            # 流式读取输出（小块读取 + UTF-8 边界处理）
            byte_buffer = b''
            while True:
                chunk = proc.stdout.read(32)
                if not chunk:
                    if byte_buffer:
                        insert_text(byte_buffer.decode('utf-8', errors='replace'))
                    break
                
                byte_buffer += chunk
                
                safe_len = len(byte_buffer)
                while safe_len > 0:
                    try:
                        byte_buffer[:safe_len].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        safe_len -= 1
                
                if safe_len > 0:
                    text = byte_buffer[:safe_len].decode('utf-8')
                    byte_buffer = byte_buffer[safe_len:]
                    insert_text(text)
            
            proc.wait()
            
        except Exception as e:
            def show_error():
                if view.is_valid():
                    view.run_command('insert_output_text', {
                        'point': insert_point,
                        'text': '[错误: ' + str(e) + ']'
                    })
            sublime.set_timeout(show_error, 0)


class ExecuteConfirmedCommandCommand(sublime_plugin.TextCommand):
    """执行已确认的危险命令"""
    def run(self, edit, line, line_end):
        # 记录到历史
        add_to_history(line)
        
        # ll 别名
        cmd = line
        if cmd == "ll" or cmd.startswith("ll "):
            cmd = "ls -la" + cmd[2:]
        
        # 获取工作目录
        cwd = os.path.expanduser("~")
        if self.view.file_name():
            cwd = os.path.dirname(self.view.file_name())
        
        # 插入换行
        self.view.insert(edit, line_end, "\n")
        insert_point = line_end + 1
        
        # 启动异步执行
        thread = threading.Thread(
            target=self._run_command,
            args=(cmd, cwd, self.view, insert_point)
        )
        thread.daemon = True
        thread.start()
    
    def _run_command(self, cmd, cwd, view, insert_point):
        """异步执行命令"""
        try:
            # 使用轻量配置
            lite_rc = get_lite_rc_path()
            if lite_rc and os.path.exists(lite_rc):
                wrapped_cmd = '{} -c "source {} && {}"'.format(
                    DEFAULT_SHELL, lite_rc, cmd.replace('"', '\\"'))
            else:
                wrapped_cmd = cmd
            
            proc = subprocess.Popen(
                wrapped_cmd,
                shell=True,
                executable=DEFAULT_SHELL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                bufsize=1
            )
            
            current_point = [insert_point]
            
            def insert_text(text):
                def do_insert():
                    if not view.is_valid():
                        return
                    view.run_command('insert_output_text', {
                        'point': current_point[0],
                        'text': text
                    })
                    current_point[0] += len(text)
                sublime.set_timeout(do_insert, 0)
            
            byte_buffer = b''
            while True:
                chunk = proc.stdout.read(32)
                if not chunk:
                    if byte_buffer:
                        insert_text(byte_buffer.decode('utf-8', errors='replace'))
                    break
                
                byte_buffer += chunk
                safe_len = len(byte_buffer)
                while safe_len > 0:
                    try:
                        byte_buffer[:safe_len].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        safe_len -= 1
                
                if safe_len > 0:
                    text = byte_buffer[:safe_len].decode('utf-8')
                    byte_buffer = byte_buffer[safe_len:]
                    insert_text(text)
            
            proc.wait()
        except Exception as e:
            def show_error():
                if view.is_valid():
                    view.run_command('insert_output_text', {
                        'point': insert_point,
                        'text': '[错误: ' + str(e) + ']'
                    })
            sublime.set_timeout(show_error, 0)

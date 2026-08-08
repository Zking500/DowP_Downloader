# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\console_handler.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import os
import shlex
import subprocess
import sys
import threading
from typing import Callable, Optional
class ConsoleHandler:
    """\n    Handles command execution from the internal DowP console.\n    Supports running integrated binaries (yt-dlp, ffmpeg) and custom commands (dp).\n    """
    def __init__(self, bin_dir: str, ffmpeg_bin_dir: str):
        self.bin_dir = bin_dir
        self.ffmpeg_bin_dir = ffmpeg_bin_dir
        self._cmd_process = None
        self._output_callback = None
        self._finish_callback = None
    def connect_callbacks(self, output_cb: Callable[[str, str], None], finish_cb: Callable[[], None]):
        """Connects the interface functions that will receive the text and completion notifications."""
        self._output_callback = output_cb
        self._finish_callback = finish_cb
    def _print_to_console(self, text: str, tag: str='normal'):
        if self._output_callback:
            self._output_callback(text, tag)
    def execute_command(self, raw_command: str):
        """Main entry point for processing a command."""
        raw = raw_command.strip()
        if not raw:
            self._on_finished()
            return
        else:
            self._print_to_console(f'\n> {raw}\n', tag='user_command')
            parts = raw.split()
            tool = parts[0].lower()
            args = parts[1:]
            if len(args) == 1 and args[0] == '--m' and (tool in ['w2x', 'srmd', 'upy']):
                self._list_models(tool)
                self._on_finished()
            else:
                if tool == 'ffmpeg':
                    self._run_ffmpeg(raw[len('ffmpeg'):].strip())
                else:
                    if tool == 'yt-dlp':
                        self._run_ytdlp(raw[len('yt-dlp'):].strip())
                    else:
                        if tool == 'w2x':
                            self._run_upscaling_tool('waifu2x', raw[len('w2x'):].strip())
                        else:
                            if tool == 'srmd':
                                self._run_upscaling_tool('srmd', raw[len('srmd'):].strip())
                            else:
                                if tool == 'upy':
                                    self._run_upscaling_tool('upscayl', raw[len('upy'):].strip())
                                else:
                                    if tool == 'dp':
                                        self._run_dp_command(args)
                                    else:
                                        self._print_to_console(f'\n[Console] Tool not recognized: \'{tool}\'.\n          Available commands: dp, ffmpeg, yt-dlp, w2x, srmd, upy\n\n', tag='warning')
                                        self._on_finished()
    def _run_ffmpeg(self, args_str: str):
        ffmpeg_exe = os.path.join(self.ffmpeg_bin_dir, 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        cmd = [ffmpeg_exe] + self._safe_split(args_str)
        self._start_process(cmd, 'ffmpeg')
    def _run_ytdlp(self, args_str: str):
        ytdlp_zip = os.path.join(self.bin_dir, 'ytdlp', 'yt-dlp.zip')
        if not os.path.exists(ytdlp_zip):
            self._print_to_console(f'\n[ERROR] yt-dlp.zip not found in: {ytdlp_zip}\n', tag='error')
            self._on_finished()
            return
        else:
            python_exe = sys.executable
            cmd = [python_exe, ytdlp_zip] + self._safe_split(args_str)
            self._start_process(cmd, 'yt-dlp')
    def _run_upscaling_tool(self, tool_key: str, args_str: str):
        """Runs one of the ncnn-vulkan upscaling tools."""
        upscaling_base = os.path.join(self.bin_dir, 'models', 'upscaling')
        if tool_key == 'waifu2x':
            exe_name = 'waifu2x-ncnn-vulkan.exe' if os.name == 'nt' else 'waifu2x-ncnn-vulkan'
            tool_label = 'Waifu2x'
        else:
            if tool_key == 'srmd':
                exe_name = 'srmd-ncnn-vulkan.exe' if os.name == 'nt' else 'srmd-ncnn-vulkan'
                tool_label = 'SRMD'
            else:
                if tool_key == 'upscayl':
                    exe_name = 'upscayl-bin.exe' if os.name == 'nt' else 'upscayl-bin'
                    tool_label = 'Upscayl'
                else:
                    return None
        exe_path = os.path.join(upscaling_base, tool_key, exe_name)
        if not os.path.exists(exe_path):
            self._print_to_console(f'\n[ERROR] Binary not found: {exe_path}\n', tag='error')
            self._on_finished()
            return
        else:
            cmd = [exe_path] + self._safe_split(args_str)
            self._start_process(cmd, tool_label)
    def _list_models(self, tool: str):
        """Universal model scanner that explores the tool's directory for model folders and files."""
        from src.core.constants import UPSCAYL_MODELS_MAP
        upscaling_base = os.path.join(self.bin_dir, 'models', 'upscaling')
        tool_dirs = {'upy': 'upscayl', 'w2x': 'waifu2x', 'srmd': 'srmd'}
        tool_key = tool_dirs.get(tool)
        if not tool_key:
            return

        tool_path = os.path.join(upscaling_base, tool_key)
        if not os.path.exists(tool_path):
            self._print_to_console(f'\n[ERROR] Tool path not found: {tool_path}\n', tag='error')
            return

        self._print_to_console(f'\n=== Scanning {tool.upper()} Models ===\n')
        found_any = False
        engine_header_printed = False

        try:
            items = os.listdir(tool_path)
        except Exception as e:
            self._print_to_console(f'[ERROR] Could not read directory: {e}\n', tag='error')
            return

        for item in items:
            item_path = os.path.join(tool_path, item)
            if not os.path.isdir(item_path):
                continue

            # 1) Process directories that contain model files
            if item.lower().startswith('models'):
                try:
                    content = os.listdir(item_path)
                except Exception:
                    continue

                params = sorted([f[:-6] for f in content if f.endswith('.param')])   # strip '.param'
                subdirs = sorted([d for d in content if os.path.isdir(os.path.join(item_path, d))])

                if params:
                    self._print_to_console(f'\n[{item}] (Model files found):\n')
                    for p in params:
                        friendly = UPSCAYL_MODELS_MAP.get(p, '') if tool == 'upy' else ''
                        desc = f' ({friendly})' if friendly else ''
                        self._print_to_console(f' - {p:<30}{desc}\n')
                    found_any = True

                if subdirs:
                    self._print_to_console(f'\n[{item}] (Model folders found):\n')
                    for d in subdirs:
                        self._print_to_console(f' - {d}\n')
                    found_any = True

            # 2) For Waifu2x, list directories starting with 'models-' as engines
            if tool == 'w2x' and item.startswith('models-'):
                if not engine_header_printed:
                    self._print_to_console('\n[Found Engines]:\n')
                    engine_header_printed = True
                self._print_to_console(f' - {item}\n')
                found_any = True

        if not found_any:
            self._print_to_console(f'\n[Console] No models detected in: {tool_path}\n', tag='warning')
        self._print_to_console('\n')
    def _run_dp_command(self, args: list[str]):
        """Handles DowP internal commands."""
        if not args or args[0] in ['help', '-h', '--help']:
            self._print_dp_help()
            self._on_finished()
        else:
            subcommand = args[0].lower()
            self._print_to_console(f'\n[DP] Subcommand \'{subcommand}\' not implemented yet.\n\n', tag='warning')
            self._on_finished()
    def _print_dp_help(self):
        help_text = 'Usage: [tool] [options...]\n\nDowP Commands:\n  dp -h, help            Show this help message.\n\nGeneral Options:\n  ffmpeg                 Integrated FFmpeg engine.\n  yt-dlp                 Integrated yt-dlp engine.\n\nUpscaling Options:\n  upy                    Upscayl Global Engine\n  w2x                    Waifu2x Engine\n  srmd                   SRMD Engine\n  [tool] --m             List available models for that engine\n'
        self._print_to_console(help_text, tag='normal')
    def _safe_split(self, args_str: str) -> list[str]:
        try:
            return shlex.split(args_str)
        except ValueError:
            return args_str.split()
    def _start_process(self, cmd: list[str], tool_label: str):
        def _run():
            import time
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self._cmd_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=creationflags, text=True, encoding='utf-8', errors='replace', bufsize=1)
                output_buffer = []
                last_flush_time = time.time()
                while True:
                    chunk = self._cmd_process.stdout.read(4096)
                    if not chunk:
                        break
                    else:
                        output_buffer.append(chunk)
                        current_time = time.time()
                        if current_time - last_flush_time > 0.1:
                            self._print_to_console(''.join(output_buffer), tag='normal')
                            output_buffer = []
                            last_flush_time = current_time
                if output_buffer:
                    self._print_to_console(''.join(output_buffer), tag='normal')
                exit_code = self._cmd_process.wait()
                self._print_to_console(f'\n[{tool_label}] Process finished (code: {exit_code})\n', tag='normal')
            except FileNotFoundError:
                self._print_to_console(f'\n[ERROR] Executable not found: {cmd[0]}\n', tag='error')
            except Exception as e:
                self._print_to_console(f'\n[ERROR] {e}\n', tag='error')
            finally:
                self._cmd_process = None
                self._on_finished()
        threading.Thread(target=_run, daemon=True).start()
    def cancel_process(self):
        """Terminates the running subprocess if it exists."""
        if self._cmd_process is not None and self._cmd_process.poll() is None:
            try:
                self._cmd_process.terminate()
                self._print_to_console('\n[Console] Process canceled by user.\n', tag='warning')
            except Exception as e:
                print(f'WARNING [Console]: Could not cancel process: {e}')
    def _on_finished(self):
        if self._finish_callback:
            self._finish_callback()
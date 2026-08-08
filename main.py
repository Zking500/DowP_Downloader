# Decompiled with PyLingual (https://pylingual.io) & Patched for Multiplatform (Linux/Plasma Multi-Monitor)
import atexit
from datetime import datetime
import json
import multiprocessing
import os
import platform
import re
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pillow_avif


def force_center_on_active_screen(window, width, height):
    """
    Calcula el centrado exacto para configuraciones multimonitor (Horizontal + Vertical)
    y gestiona las peculiaridades del Compositor de KDE Plasma (KWin / Wayland / X11).
    """
    window.update_idletasks()
    
    # 1. Intentar obtener geometría exacta de monitor mediante Screen (Tkinter 8.6+)
    # Si falla, se usa fallback con offset básico
    try:
        # En sistemas con múltiples monitores, obtenemos la posición del puntero o pantalla activa
        pointer_x = window.winfo_pointerx()
        pointer_y = window.winfo_pointery()
        
        # En Tkinter, los monitores secundarios pueden extender la coordenadas.
        # Determinamos en qué monitor está la aplicación basándonos en el puntero del mouse
        vroot_x = window.winfo_vrootx()
        vroot_y = window.winfo_vrooty()
        vroot_w = window.winfo_vrootwidth()
        vroot_h = window.winfo_vrootheight()

        # Si el monitor actual tiene offset (por ejemplo un monitor secundario vertical a la izquierda)
        # o si estamos en el escritorio combinado:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()

        # Si detectamos una resolución anormal (pantalla combinada de múltiples monitores)
        if screen_w > 2560 or screen_h > 1440:
            # Asumimos una pantalla estándar activa para evitar que se desplace al "vacío" entre pantallas
            # Si el puntero está dentro del ancho de la pantalla combinada:
            if pointer_x > 0:
                # Tomamos como referencia los límites del monitor horizontal principal
                target_w = min(1920, screen_w)
                target_h = min(1080, screen_h)
            else:
                target_w, target_h = 1080, 1920 # Monitor vertical
            
            x = max(0, (target_w // 2) - (width // 2)) + vroot_x
            y = max(0, (target_h // 2) - (height // 2)) + vroot_y
        else:
            x = max(0, (screen_w // 2) - (width // 2))
            y = max(0, (screen_h // 2) - (height // 2))

    except Exception:
        # Fallback genérico
        x = max(0, (window.winfo_screenwidth() // 2) - (width // 2))
        y = max(0, (window.winfo_screenheight() // 2) - (height // 2))

    window.geometry(f'{width}x{height}+{x}+{y}')


class TimestampLogger:

    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.at_start_of_line = True
        self._is_timestamped = True

    def write(self, message):
        if not message or self.original_stream is None:
            return None
        lines = message.splitlines(keepends=True)
        for line in lines:
            has_timestamp = bool(re.match(r'^\s*\[\d{2}:\d{2}:\d{2}\]', line))
            if self.at_start_of_line and line.strip() and not has_timestamp:
                timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] "
                self.original_stream.write(timestamp)
            self.original_stream.write(line)
            self.at_start_of_line = line.endswith('\n')

    def flush(self):
        if self.original_stream is not None:
            self.original_stream.flush()


if not hasattr(sys.stdout, '_is_timestamped'):
    sys.stdout = TimestampLogger(sys.stdout)
if not hasattr(sys.stderr, '_is_timestamped'):
    sys.stderr = TimestampLogger(sys.stderr)

APP_VERSION = '1.4.4.1 (lostmedia)'

print("\033[1;33m" + "=" * 60 + "\033[0m")
print("\033[1;37mDowP - Edición Rescatada de Lost Media\033[0m")
print("Código original: \033[9mMarckDP\033[0m (tachado simbólicamente)")
print("\033[1;32mRescatado y restaurado con éxito.\033[0m")
print("\033[1;33m" + "=" * 60 + "\033[0m")

if sys.platform == 'win32':
    if not hasattr(subprocess.Popen, '_is_patched'):
        _original_popen = subprocess.Popen

        class _PatchedPopen(_original_popen):
            _is_patched = True

            def __init__(self, *args, **kwargs):
                cmd = args[0] if args else kwargs.get('args', '')
                cmd_str = ''
                if isinstance(cmd, (list, tuple)):
                    cmd_str = ' '.join(map(str, cmd)).lower()
                elif isinstance(cmd, str):
                    cmd_str = cmd.lower()
                exclude_list = ['ffmpeg', 'yt-dlp', 'ffprobe']
                is_excluded = any((tool in cmd_str for tool in exclude_list))
                if not is_excluded and 'creationflags' not in kwargs:
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                super().__init__(*args, **kwargs)

        subprocess.Popen = _PatchedPopen

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

BIN_DIR = os.path.join(PROJECT_ROOT, 'bin')
FFMPEG_BIN_DIR = os.path.join(BIN_DIR, 'ffmpeg')
DENO_BIN_DIR = os.path.join(BIN_DIR, 'deno')
POPPLER_BIN_DIR = os.path.join(BIN_DIR, 'poppler')
INKSCAPE_BIN_DIR = os.path.join(BIN_DIR, 'inkscape')
GHOSTSCRIPT_BIN_DIR = os.path.join(BIN_DIR, 'ghostscript')
MODELS_DIR = os.path.join(BIN_DIR, 'models')
REMBG_MODELS_DIR = os.path.join(MODELS_DIR, 'rembg')
UPSCALING_DIR = os.path.join(MODELS_DIR, 'upscaling')

os.environ['U2NET_HOME'] = REMBG_MODELS_DIR


class SplashScreen:

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        bg_color = '#2B2B2B'
        text_color = '#FFFFFF'
        self.root.configure(bg=bg_color)

        width, height = 600, 160
        force_center_on_active_screen(self.root, width, height)

        self.tk_image = None
        try:
            base_path = getattr(
                sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))
            )
            icon_path = os.path.join(base_path, 'DowP-icon.ico')
            if os.path.exists(icon_path):
                pil_img = Image.open(icon_path).resize(
                    (40, 40), Image.Resampling.LANCZOS
                )
                self.tk_image = ImageTk.PhotoImage(pil_img)
                self.root.iconphoto(False, self.tk_image)
        except Exception as e:
            print(f'No se pudo cargar el icono en Splash: {e}')

        main_label = tk.Label(
            self.root,
            text=f'DowP v{APP_VERSION} - Rescatado de Lost Media',
            image=self.tk_image,
            compound='left',
            padx=15,
            font=('Segoe UI', 12, 'bold'),
            bg=bg_color,
            fg=text_color,
        )

        main_label.pack(expand=True, fill='both', pady=(15, 0))
        self.status_label = tk.Label(
            self.root,
            text='Cargando...',
            font=('Segoe UI', 9),
            bg=bg_color,
            fg='#AAAAAA',
        )
        sub_label = tk.Label(
            self.root,
            text='(Original por M̶a̶r̶c̶k̶D̶P̶)',
            font=('Segoe UI', 8),
            bg=bg_color,
            fg='#AAAAAA',
        )
        sub_label.pack()
        self.status_label.pack(side='bottom', pady=(0, 15))
        self.root.update()

    def update_status(self, text):
        if self.root:
            self.status_label.config(text=text)
            self.root.update()

    def destroy(self):
        if self.root:
            self.root.destroy()
            self.root = None


class SingleInstance:

    def __init__(self):
        self.lockfile = os.path.join(tempfile.gettempdir(), 'dowp.lock')
        if os.path.exists(self.lockfile):
            try:
                with open(self.lockfile, 'r') as f:
                    pid = int(f.read())
                if self._is_pid_running(pid):
                    messagebox.showwarning(
                        'DowP ya está abierto',
                        f'Ya hay una instancia de DowP en ejecución (PID: {pid}).',
                    )
                    sys.exit(1)
                else:
                    os.remove(self.lockfile)
            except Exception:
                try:
                    os.remove(self.lockfile)
                except OSError:
                    pass

        with open(self.lockfile, 'w') as f:
            f.write(str(os.getpid()))
        atexit.register(self.cleanup)

    def _is_pid_running(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def cleanup(self):
        if os.path.exists(self.lockfile):
            try:
                os.remove(self.lockfile)
            except Exception as e:
                print(f'ADVERTENCIA: No se pudo limpiar el archivo de cerrojo: {e}')


if __name__ == '__main__':
    multiprocessing.freeze_support()

    if len(sys.argv) > 1 and sys.argv[1].endswith('yt-dlp.zip'):
        yt_dlp_zip = sys.argv[1]
        if os.path.exists(yt_dlp_zip):
            if yt_dlp_zip not in sys.path:
                sys.path.insert(0, yt_dlp_zip)
            try:
                import yt_dlp

                yt_dlp.main(sys.argv[2:])
                sys.exit(0)
            except Exception as e:
                print(f'ERROR: Falló la ejecución directa de yt-dlp: {e}')
                sys.exit(1)

    splash = SplashScreen()
    splash.update_status('Verificando instancia única...')
    SingleInstance()

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    yt_dlp_zip = os.path.join(BIN_DIR, 'ytdlp', 'yt-dlp.zip')
    if os.path.exists(yt_dlp_zip) and yt_dlp_zip not in sys.path:
        sys.path.insert(0, yt_dlp_zip)

    splash.update_status('Configurando entorno y rutas...')

    for b_dir in [
        BIN_DIR,
        FFMPEG_BIN_DIR,
        DENO_BIN_DIR,
        POPPLER_BIN_DIR,
        INKSCAPE_BIN_DIR,
        GHOSTSCRIPT_BIN_DIR,
    ]:
        if os.path.isdir(b_dir) and b_dir not in os.environ['PATH']:
            os.environ['PATH'] = b_dir + os.pathsep + os.environ['PATH']

    launch_target = sys.argv[1] if len(sys.argv) > 1 else None
    splash.update_status('Cargando módulos e interfaz...')

    _theme_data = {}
    _theme_warnings = []

    try:
        import customtkinter as ctk

        if sys.platform == 'win32':
            _appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            _appdata = os.path.expanduser('~/.config')

        _settings_path = os.path.join(_appdata, 'DowP', 'app_settings.json')
        _theme, _appearance = 'blue', 'System'

        if os.path.exists(_settings_path):
            with open(_settings_path, 'r') as f:
                _settings = json.load(f)
                _theme = _settings.get('selected_theme_accent', 'blue')
                _appearance = _settings.get('appearance_mode', 'System')

        ctk.set_appearance_mode(_appearance)
        _base_path = getattr(sys, '_MEIPASS', PROJECT_ROOT)
        _user_themes_dir = os.path.join(_appdata, 'DowP', 'themes')
        _internal_themes_dir = os.path.join(_base_path, 'src', 'gui', 'themes')

        _found_path = None
        for _dir in [_user_themes_dir, _internal_themes_dir]:
            _json_path = os.path.join(_dir, f'{_theme}.json')
            if os.path.exists(_json_path):
                _found_path = _json_path
                break

        if _found_path:
            try:
                _base_theme_path = os.path.join(_internal_themes_dir, 'shrek.json')
                _final_theme_data = {}
                if os.path.exists(_base_theme_path):
                    with open(_base_theme_path, 'r', encoding='utf-8') as f:
                        _final_theme_data = json.load(f)
                with open(_found_path, 'r', encoding='utf-8') as f:
                    _user_theme_data = json.load(f)

                def _deep_update(base, over):
                    for k, v in over.items():
                        if (
                            isinstance(v, dict)
                            and k in base
                            and isinstance(base[k], dict)
                        ):
                            _deep_update(base[k], v)
                        else:
                            base[k] = v

                _deep_update(_final_theme_data, _user_theme_data)
                _theme_data = _final_theme_data

                os.makedirs(_user_themes_dir, exist_ok=True)
                _temp_theme_path = os.path.join(
                    _user_themes_dir, '.active_theme_sanitized.json'
                )
                with open(_temp_theme_path, 'w', encoding='utf-8') as f:
                    json.dump(_theme_data, f)
                _theme = _temp_theme_path
            except Exception as e:
                print(f'ADVERTENCIA: No se pudo procesar el tema: {e}')
                _theme = _found_path

        if not _found_path and _theme not in ['blue', 'dark-blue', 'green']:
            _theme = 'blue'

        ctk.set_default_color_theme(_theme)
    except Exception as e:
        print(f'ADVERTENCIA: No se pudo pre-cargar el tema: {e}')
        import customtkinter as ctk

        ctk.set_default_color_theme('blue')

    from src.gui.main_window import MainWindow

    app = MainWindow(
        launch_target=launch_target,
        project_root=PROJECT_ROOT,
        poppler_path=POPPLER_BIN_DIR,
        inkscape_path=INKSCAPE_BIN_DIR,
        splash_screen=splash,
        app_version=APP_VERSION,
        theme_data=_theme_data,
        theme_warnings=_theme_warnings,
    )

    # Lógica de centrado en Nobara / KDE Plasma (Wayland / X11)
    app.update_idletasks()
    
    req_width = app.winfo_width() if app.winfo_width() > 200 else 1000
    req_height = app.winfo_height() if app.winfo_height() > 200 else 650

    # Si estás corriendo sobre Wayland en Nobara, delegamos el centrado a KWin mediante reglas si es necesario,
    # pero forzamos el cálculo considerando el puntero del mouse para saber en qué monitor estás trabajando.
    force_center_on_active_screen(app, req_width, req_height)

    app.mainloop()
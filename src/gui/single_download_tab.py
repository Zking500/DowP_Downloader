# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\gui\\single_download_tab.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

from flask import Flask, jsonify, request
from flask_socketio import SocketIO
import threading
import webbrowser
from tkinter import messagebox
import tkinter
import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image
import requests
from io import BytesIO
import gc
import os
import re
import sys
from pathlib import Path
import subprocess
import json
import time
import shutil
import platform
import yt_dlp
import io
from datetime import datetime, timedelta
from src.core.downloader import get_video_info, download_media, apply_site_specific_rules, apply_yt_patch
from src.core.processor import FFmpegProcessor, CODEC_PROFILES
from src.core.exceptions import UserCancelledError, LocalRecodeFailedError, PlaylistDownloadError
from src.core.processor import clean_and_convert_vtt_to_srt, slice_subtitle
from src.core.tags_manager import TagsManager
from .dialogs import ConflictDialog, LoadingWindow, CompromiseDialog, SimpleMessageDialog, SavePresetDialog, PlaylistErrorDialog, Tooltip
from src.core.constants import VIDEO_EXTENSIONS, AUDIO_EXTENSIONS, SINGLE_STREAM_AUDIO_CONTAINERS, FORMAT_MUXER_MAP, LANG_CODE_MAP, LANGUAGE_ORDER, DEFAULT_PRIORITY, EDITOR_FRIENDLY_CRITERIA, COMPATIBILITY_RULES, WAIFU2X_MODELS, SRMD_MODELS, UPSCALING_TOOLS, AI_ENGINE_HOLDER, AI_MODEL_HOLDER
from contextlib import redirect_stdout
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)
from main import PROJECT_ROOT, MODELS_DIR, UPSCALING_DIR
from src.core.video_upscaler import VideoUpscaler
class SingleDownloadTab(ctk.CTkFrame):
    """\n    Esta clase contendrá TODA la UI y la lógica de la\n    pestaña de descarga única.\n    """
    DOWNLOAD_BTN_COLOR = '#28A745'
    DOWNLOAD_BTN_HOVER = '#218838'
    PROCESS_BTN_COLOR = '#6F42C1'
    PROCESS_BTN_HOVER = '#59369A'
    ANALYZE_BTN_COLOR = '#007BFF'
    ANALYZE_BTN_HOVER = '#0069D9'
    CANCEL_BTN_COLOR = '#DC3545'
    CANCEL_BTN_HOVER = '#C82333'
    DISABLED_TEXT_COLOR = '#D3D3D3'
    DISABLED_FG_COLOR = '#565b5f'
    def __init__(self, master, app):
        """\n        Inicializa la pestaña.\n        \'master\' es el contenedor de la pestaña.\n        \'app\' es la referencia a la ventana principal (MainWindow).\n        """
        super().__init__(master, fg_color='transparent')
        self.app = app
        self.is_initializing = True
        self.pack(expand=True, fill='both')
        self._load_theme_colors()
        self.ffmpeg_processor = self.app.ffmpeg_processor
        self.cancellation_event = self.app.cancellation_event
        self.tags_manager = TagsManager(app)
        self.saved_manual_path = ''
        self.original_video_width = 0
        self.original_video_height = 0
        self.has_video_streams = False
        self.has_audio_streams = False
        self.analysis_is_complete = False
        self.combined_variants = {}
        self.combined_audio_map = {}
        self.video_formats = {}
        self.audio_formats = {}
        self.subtitle_formats = {}
        self.local_file_path = None
        self.thumbnail_label = None
        self.pil_image = None
        self.last_download_path = None
        self.video_duration = 0
        self.video_id = None
        self.analysis_cache = {}
        self.CACHE_TTL = 300
        self.active_subprocess_pid = None
        self.active_operation_thread = None
        self.release_page_url = None
        self.recode_settings = {}
        self.all_subtitles = {}
        self.current_subtitle_map = {}
        self.apply_quick_preset_checkbox_state = False
        self.keep_original_quick_saved = True
        self.analysis_was_playlist = False
        self._last_progress_update_time = 0.0
        self.active_downloads_state = {'ffmpeg': {'text': '', 'value': 0.0, 'active': False}, 'deno': {'text': '', 'value': 0.0, 'active': False}, 'poppler': {'text': '', 'value': 0.0, 'active': False}, 'inkscape': {'text': '', 'value': 0.0, 'active': False}, 'rembg': {'text': '', 'value': 0.0, 'active': False}}
        self.recode_compatibility_status = 'valid'
        self.original_analyze_text = 'Analizar'
        self.original_analyze_command = self.start_analysis_thread
        self.original_analyze_fg_color = None
        self.original_download_text = 'Iniciar Descarga'
        self.original_download_command = self.start_download_thread
        self.original_download_fg_color = None
        self._initialize_presets_file()
        presets_data = self._load_presets()
        self.built_in_presets = presets_data.get('built_in_presets', {})
        self.custom_presets = presets_data.get('custom_presets', [])
        self._create_widgets()
        self._initialize_ui_settings()
    def _load_theme_colors(self):
        """Carga los colores dinámicos desde el tema de la aplicación."""
        self.DOWNLOAD_BTN_COLOR = self.app.get_theme_color('DOWNLOAD_BTN', '#28A745')
        self.DOWNLOAD_BTN_HOVER = self.app.get_theme_color('DOWNLOAD_BTN_HOVER', '#218838')
        self.PROCESS_BTN_COLOR = self.app.get_theme_color('PROCESS_BTN', '#6F42C1')
        self.PROCESS_BTN_HOVER = self.app.get_theme_color('PROCESS_BTN_HOVER', '#59369A')
        self.ANALYZE_BTN_COLOR = self.app.get_theme_color('ANALYZE_BTN', '#007BFF')
        self.ANALYZE_BTN_HOVER = self.app.get_theme_color('ANALYZE_BTN_HOVER', '#0069D9')
        self.CANCEL_BTN_COLOR = self.app.get_theme_color('CANCEL_BTN', '#DC3545')
        self.CANCEL_BTN_HOVER = self.app.get_theme_color('CANCEL_BTN_HOVER', '#C82333')
        self.SECONDARY_BTN_COLOR = self.app.get_theme_color('SECONDARY_BTN', '#555555')
        self.SECONDARY_BTN_HOVER = self.app.get_theme_color('SECONDARY_BTN_HOVER', '#444444')
        self.DND_BORDER_COLOR = self.app.get_theme_color('DND_BORDER', '#007BFF')
        self.DND_BG_COLOR = self.app.get_theme_color('DND_BG', '#1a3d5c')
        self.DND_TEXT_COLOR = self.app.get_theme_color('DND_TEXT', '#00BFFF')
        self.DOWNLOAD_BTN_TEXT = self.app.get_theme_color('DOWNLOAD_BTN_TEXT', 'white')
        self.ANALYZE_BTN_TEXT = self.app.get_theme_color('ANALYZE_BTN_TEXT', 'white')
        self.CANCEL_BTN_TEXT = self.app.get_theme_color('CANCEL_BTN_TEXT', 'white')
        self.PROCESS_BTN_TEXT = self.app.get_theme_color('PROCESS_BTN_TEXT', 'white')
        self.SECONDARY_BTN_TEXT = self.app.get_theme_color('SECONDARY_BTN_TEXT', 'white')
        self.DISABLED_TEXT_COLOR = self.app.get_theme_color('DISABLED_TEXT', '#D3D3D3')
        self.DISABLED_FG_COLOR = self.app.get_theme_color('DISABLED_FG', '#565b5f')
        self.STATUS_SUCCESS = self.app.get_theme_color('STATUS_SUCCESS', ['#28A745', '#218838'])
        self.STATUS_ERROR = self.app.get_theme_color('STATUS_ERROR', ['#DC3545', '#C82333'])
        self.STATUS_WARNING = self.app.get_theme_color('STATUS_WARNING', ['#FFA500', '#FF8C00'])
        self.UPDATE_ALERT = self.app.get_theme_color('UPDATE_ALERT', self.STATUS_WARNING)
        self.SECTION_SUBTITLE = self.app.get_theme_color('SECTION_SUBTITLE', ['gray40', 'gray70'])
    def refresh_theme(self):
        """Actualiza los colores de los widgets críticos según el tema actual."""
        self._load_theme_colors()
        self.original_analyze_fg_color = self.ANALYZE_BTN_COLOR
        self.original_download_fg_color = self.DOWNLOAD_BTN_COLOR
        if hasattr(self, 'analyze_button'):
            self.analyze_button.configure(fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER, text_color=self.ANALYZE_BTN_TEXT)
        if hasattr(self, 'download_button'):
            self.download_button.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT, text_color_disabled=self.DISABLED_TEXT_COLOR)
        if hasattr(self, 'import_preset_button'):
            self.import_preset_button.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
        if hasattr(self, 'export_preset_button'):
            self.export_preset_button.configure(fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER, text_color=self.ANALYZE_BTN_TEXT)
        if hasattr(self, 'delete_preset_button'):
            self.delete_preset_button.configure(fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, text_color=self.CANCEL_BTN_TEXT)
        if hasattr(self, 'open_models_folder_button'):
            self.open_models_folder_button.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        if hasattr(self, 'upscale_add_custom_btn'):
            self.upscale_add_custom_btn.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
        if hasattr(self, 'upscale_delete_btn'):
            self.upscale_delete_btn.configure(fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, text_color=self.CANCEL_BTN_TEXT)
        if hasattr(self, 'upscale_open_btn'):
            self.upscale_open_btn.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        if hasattr(self, 'clear_local_file_button'):
            self.clear_local_file_button.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        if hasattr(self, 'import_button'):
            self.import_button.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
        if hasattr(self, 'dnd_overlay') and self.dnd_overlay.winfo_exists():
                bg_color = self._get_ctk_fg_color(self.thumbnail_container)
                self.dnd_overlay.configure(bg=bg_color)
                if hasattr(self, 'placeholder_label') and self.placeholder_label.winfo_exists():
                        text_color = 'white' if ctk.get_appearance_mode() == 'Dark' else 'black'
                        self.placeholder_label.configure(bg=bg_color, fg=text_color)
        self.update_idletasks()
    def _get_ctk_fg_color(self, ctk_widget):
        """\n        Obtiene el color de fondo de un widget de CustomTkinter según el tema actual.\n        """
        try:
            fg_color = ctk_widget._fg_color
            if isinstance(fg_color, (tuple, list)):
                appearance_mode = ctk.get_appearance_mode()
                return fg_color[1] if appearance_mode == 'Dark' else fg_color[0]
            else:
                return fg_color
        except Exception as e:
            print(f'DEBUG: Error obteniendo color: {e}')
            return '#2B2B2B'
    def _initialize_ui_settings(self):
        self.output_path_entry.delete(0, 'end')
        if self.app.default_download_path:
            self.output_path_entry.insert(0, self.app.default_download_path)
        else:
            try:
                from pathlib import Path
                downloads_path = Path.home() / 'Downloads'
                if downloads_path.exists() and downloads_path.is_dir():
                        self.output_path_entry.insert(0, str(downloads_path))
                        self.app.default_download_path = str(downloads_path)
            except Exception as e:
                print(f'No se pudo establecer la carpeta de descargas por defecto: {e}')
        self.auto_download_subtitle_check.deselect()
        if self.app.apply_quick_preset_checkbox_state:
            self.apply_quick_preset_checkbox.select()
        else:
            self.apply_quick_preset_checkbox.deselect()
        self.apply_quick_preset_checkbox.deselect()
        self._on_quick_recode_toggle()
        if self.app.keep_original_quick_saved:
            self.keep_original_quick_checkbox.select()
        else:
            self.keep_original_quick_checkbox.deselect()
        self.toggle_manual_subtitle_button()
        if self.app.recode_settings.get('keep_original', True):
            self.keep_original_checkbox.select()
        else:
            self.keep_original_checkbox.deselect()
        self.recode_video_checkbox.deselect()
        self.recode_audio_checkbox.deselect()
        self._toggle_recode_panels()
        self._populate_preset_menu()
        self.recode_main_frame.pack(pady=(10, 0), padx=5, fill='both', expand=True)
        print('DEBUG: Panel de recodificación forzado a mostrarse en inicialización')
        self.app.after(100, self._update_save_preset_visibility)
        self.enable_drag_and_drop()
        self.update_tags_combobox()
        self.is_initializing = False
    def _create_widgets(self):
        url_frame = ctk.CTkFrame(self)
        url_frame.pack(pady=(10, 0), padx=10, fill='x')
        ctk.CTkLabel(url_frame, text='URL:').pack(side='left', padx=(10, 5))
        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text='Pega la URL aquí...')
        self.url_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.url_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.url_entry))
        self.url_entry.bind('<Return>', self.start_analysis_thread)
        self.url_entry.bind('<KeyRelease>', self.update_download_button_state)
        self.url_entry.bind('<<Paste>>', lambda e: self.app.after(50, self.update_download_button_state))
        self.analyze_button = ctk.CTkButton(url_frame, text=self.original_analyze_text, command=self.original_analyze_command, fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER)
        self.analyze_button.pack(side='left', padx=(5, 10))
        self.original_analyze_fg_color = self.ANALYZE_BTN_COLOR
        self.analyze_button.pack(side='left', padx=(5, 10))
        self.original_analyze_fg_color = self.analyze_button.cget('fg_color')
        self.info_frame = ctk.CTkFrame(self)
        info_frame = ctk.CTkFrame(self)
        self.info_frame_ref = info_frame
        left_column_container = ctk.CTkFrame(info_frame, fg_color='transparent')
        left_column_container.pack(side='left', padx=10, pady=10, fill='y', anchor='n')
        self.thumbnail_container = ctk.CTkFrame(left_column_container, width=320, height=180)
        self.thumbnail_container.pack(pady=(0, 5))
        self.thumbnail_container.pack_propagate(False)
        import tkinter
        self.dnd_overlay = tkinter.Frame(self.thumbnail_container, bg=self.thumbnail_container._apply_appearance_mode(self.thumbnail_container._fg_color), width=320, height=180)
        self.dnd_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.dnd_overlay.pack_propagate(False)
        self.create_placeholder_label()
        thumbnail_actions_frame = ctk.CTkFrame(left_column_container)
        thumbnail_actions_frame.pack(fill='x')
        thumbnail_buttons_frame = ctk.CTkFrame(thumbnail_actions_frame, fg_color='transparent')
        thumbnail_buttons_frame.pack(fill='x', padx=10, pady=5)
        thumbnail_buttons_frame.grid_columnconfigure((0, 1), weight=1)
        self.save_thumbnail_button = ctk.CTkButton(thumbnail_buttons_frame, text='Descargar Miniatura', state='disabled', command=self.save_thumbnail)
        self.save_thumbnail_button.grid(row=0, column=0, padx=(0, 5), sticky='ew')
        self.send_thumbnail_to_imagetools_button = ctk.CTkButton(thumbnail_buttons_frame, text='Enviar a H.I.', state='disabled', command=self._send_thumbnail_to_image_tools)
        self.send_thumbnail_to_imagetools_button.grid(row=0, column=1, padx=(5, 0), sticky='ew')
        self.auto_save_thumbnail_check = ctk.CTkCheckBox(thumbnail_actions_frame, text='Descargar miniatura con el video', command=self.toggle_manual_thumbnail_button)
        self.auto_save_thumbnail_check.pack(padx=10, pady=(0, 5), anchor='w')
        options_scroll_frame = ctk.CTkScrollableFrame(left_column_container)
        options_scroll_frame.pack(pady=10, fill='both', expand=True)
        ctk.CTkLabel(options_scroll_frame, text='Descargar Fragmento', font=ctk.CTkFont(weight='bold')).pack(fill='x', padx=10, pady=(5, 2))
        fragment_frame = ctk.CTkFrame(options_scroll_frame)
        fragment_frame.pack(fill='x', padx=5, pady=(0, 10))
        self.fragment_checkbox = ctk.CTkCheckBox(fragment_frame, text='Activar corte de fragmento', command=lambda: (self._toggle_fragment_panel(), self.update_download_button_state()))
        self.fragment_checkbox.pack(padx=10, pady=5, anchor='w')
        self.fragment_options_frame = ctk.CTkFrame(fragment_frame, fg_color='transparent')
        self.fragment_options_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.fragment_options_frame, text='Inicio:').grid(row=0, column=0, padx=(0, 5), pady=5, sticky='w')
        start_time_frame = ctk.CTkFrame(self.fragment_options_frame, fg_color='transparent')
        start_time_frame.grid(row=0, column=1, pady=5, sticky='ew')
        self.start_h = ctk.CTkEntry(start_time_frame, width=40, placeholder_text='00')
        self.start_m = ctk.CTkEntry(start_time_frame, width=40, placeholder_text='00')
        self.start_s = ctk.CTkEntry(start_time_frame, width=40, placeholder_text='00')
        self.start_h.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(start_time_frame, text=':', font=ctk.CTkFont(size=14)).pack(side='left', padx=5)
        self.start_m.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(start_time_frame, text=':', font=ctk.CTkFont(size=14)).pack(side='left', padx=5)
        self.start_s.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(self.fragment_options_frame, text='Final:').grid(row=1, column=0, padx=(0, 5), pady=5, sticky='w')
        end_time_frame = ctk.CTkFrame(self.fragment_options_frame, fg_color='transparent')
        end_time_frame.grid(row=1, column=1, pady=5, sticky='ew')
        self.end_h = ctk.CTkEntry(end_time_frame, width=40, placeholder_text='00')
        self.end_m = ctk.CTkEntry(end_time_frame, width=40, placeholder_text='00')
        self.end_s = ctk.CTkEntry(end_time_frame, width=40, placeholder_text='00')
        self.end_h.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(end_time_frame, text=':', font=ctk.CTkFont(size=14)).pack(side='left', padx=5)
        self.end_m.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(end_time_frame, text=':', font=ctk.CTkFont(size=14)).pack(side='left', padx=5)
        self.end_s.pack(side='left', fill='x', expand=True)
        self.precise_clip_check = ctk.CTkCheckBox(self.fragment_options_frame, text='Corte Preciso (Lento/Recodificar)', command=self._on_precise_clip_toggle)
        self.precise_clip_check.grid(row=3, column=0, columnspan=2, pady=(5, 0), sticky='w')
        Tooltip(self.precise_clip_check, 'Activado: Recodifica bordes para exactitud (Lento).\nDesactivado: Corta en keyframes (Rápido, menos preciso).', delay_ms=1000)
        self.force_full_download_check = ctk.CTkCheckBox(self.fragment_options_frame, text='Descargar completo para cortar (Rápido)', command=self._on_force_full_download_toggle)
        self.force_full_download_check.grid(row=4, column=0, columnspan=2, pady=(5, 0), sticky='w')
        Tooltip(self.force_full_download_check, 'Recomendado para internet rápido.\nBaja todo el video a máxima velocidad y lo corta en tu PC.\nEvita la lentitud del procesamiento en la nube de YouTube.', delay_ms=1000)
        self.keep_original_on_clip_check = ctk.CTkCheckBox(self.fragment_options_frame, text='Conservar completo (solo modo URL)', command=self._on_keep_original_clip_toggle)
        self.keep_original_on_clip_check.grid(row=5, column=0, columnspan=2, pady=(5, 0), sticky='w')
        self.time_warning_label = ctk.CTkLabel(self.fragment_options_frame, text='', text_color='orange', wraplength=280, justify='left')
        self.time_warning_label.grid(row=6, column=0, columnspan=2, pady=(5, 0), sticky='w')
        ctk.CTkLabel(options_scroll_frame, text='Subtítulos', font=ctk.CTkFont(weight='bold')).pack(fill='x', padx=10, pady=(5, 2))
        subtitle_options_frame = ctk.CTkFrame(options_scroll_frame)
        subtitle_options_frame.pack(fill='x', padx=5, pady=(0, 10))
        subtitle_selection_frame = ctk.CTkFrame(subtitle_options_frame, fg_color='transparent')
        subtitle_selection_frame.pack(fill='x', padx=10, pady=(0, 5))
        subtitle_selection_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(subtitle_selection_frame, text='Idioma:').grid(row=0, column=0, padx=(0, 10), pady=5, sticky='w')
        self.subtitle_lang_menu = ctk.CTkOptionMenu(subtitle_selection_frame, values=['-'], state='disabled', command=self.on_language_change)
        self.subtitle_lang_menu.grid(row=0, column=1, pady=5, sticky='ew')
        ctk.CTkLabel(subtitle_selection_frame, text='Formato:').grid(row=1, column=0, padx=(0, 10), pady=5, sticky='w')
        self.subtitle_type_menu = ctk.CTkOptionMenu(subtitle_selection_frame, values=['-'], state='disabled', command=self.on_subtitle_selection_change)
        self.subtitle_type_menu.grid(row=1, column=1, pady=5, sticky='ew')
        self.save_subtitle_button = ctk.CTkButton(subtitle_options_frame, text='Descargar Subtítulos', state='disabled', command=self.save_subtitle)
        self.save_subtitle_button.pack(fill='x', padx=10, pady=5)
        self.auto_download_subtitle_check = ctk.CTkCheckBox(subtitle_options_frame, text='Descargar subtítulos con el video', command=self.toggle_manual_subtitle_button)
        self.auto_download_subtitle_check.pack(padx=10, pady=5, anchor='w')
        self.keep_full_subtitle_check = ctk.CTkCheckBox(subtitle_options_frame, text='Mantener subtítulos completos', text_color='orange')
        self.clean_subtitle_check = ctk.CTkCheckBox(subtitle_options_frame, text='Convertir y estandarizar a formato SRT')
        self.clean_subtitle_check.pack(padx=10, pady=(0, 5), anchor='w')
        ctk.CTkLabel(options_scroll_frame, text='Mantenimiento', font=ctk.CTkFont(weight='bold')).pack(fill='x', padx=10, pady=(5, 2))
        maintenance_frame = ctk.CTkFrame(options_scroll_frame)
        maintenance_frame.pack(fill='x', padx=5, pady=(0, 10))
        maintenance_frame.grid_columnconfigure(0, weight=1)
        self.app_status_label = ctk.CTkLabel(maintenance_frame, text=f'DowP v{self.app.APP_VERSION} - Verificando...', justify='left')
        self.app_status_label.grid(row=0, column=0, padx=10, pady=(5, 5), sticky='ew')
        self.update_app_button = ctk.CTkButton(maintenance_frame, text='Buscar Actualización', state='disabled', command=self._open_release_page)
        self.update_app_button.grid(row=1, column=0, padx=10, pady=(0, 15), sticky='ew')
        self.rembg_status_label = ctk.CTkLabel(maintenance_frame, text='Modelos IA: Pendiente...', wraplength=280, justify='left')
        self.rembg_status_label.grid(row=12, column=0, padx=10, pady=(5, 5), sticky='ew')
        self.open_models_folder_button = ctk.CTkButton(maintenance_frame, text='Abrir Carpeta de Modelos', command=self._open_ai_models_folder, fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, height=24)
        self.open_models_folder_button.grid(row=13, column=0, padx=10, pady=(0, 15), sticky='ew')
        details_frame = ctk.CTkFrame(info_frame)
        details_frame.pack(side='left', fill='both', expand=True, padx=(0, 10), pady=10)
        ctk.CTkLabel(details_frame, text='Título:', anchor='w').pack(fill='x', padx=5, pady=(5, 0))
        title_row = ctk.CTkFrame(details_frame, fg_color='transparent')
        title_row.pack(fill='x', padx=5, pady=(0, 10))
        self.title_entry = ctk.CTkEntry(title_row, font=('', 14))
        self.title_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.title_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.title_entry))
        self.tags_menu = ctk.CTkOptionMenu(title_row, width=110, values=['- Etiqueta -'], command=self.on_tag_change)
        self.tags_menu.pack(side='right', padx=(5, 0))
        options_frame = ctk.CTkFrame(details_frame)
        options_frame.pack(fill='x', padx=5, pady=5)
        mode_label = ctk.CTkLabel(options_frame, text='Modo:')
        mode_label.pack(side='left', padx=(0, 10))
        self.mode_selector = ctk.CTkSegmentedButton(options_frame, values=['Video+Audio', 'Solo Audio'], command=self.on_mode_change)
        self.mode_selector.set('Video+Audio')
        self.mode_selector.pack(side='left', expand=True, fill='x')
        mode_tooltip_text = '• Video+Audio: Descarga el video y el audio juntos.\n• Solo Audio: Descarga únicamente la pista de audio.\n\nEsta selección filtra las opciones de calidad y recodificación.'
        Tooltip(mode_label, mode_tooltip_text, delay_ms=1000)
        self.video_quality_label = ctk.CTkLabel(details_frame, text='Calidad de Video:', anchor='w')
        self.video_quality_menu = ctk.CTkOptionMenu(details_frame, state='disabled', values=['-'], command=self.on_video_quality_change)
        self.audio_options_frame = ctk.CTkFrame(details_frame, fg_color='transparent')
        self.audio_quality_label = ctk.CTkLabel(self.audio_options_frame, text='Calidad de Audio:', anchor='w')
        self.audio_quality_menu = ctk.CTkOptionMenu(self.audio_options_frame, state='disabled', values=['-'], command=lambda _: (self._update_warnings(), self._validate_recode_compatibility()))
        self.use_all_audio_tracks_check = ctk.CTkCheckBox(self.audio_options_frame, text='Aplicar la recodificación a todas las pistas de audio', command=self._on_use_all_audio_tracks_change)
        multi_track_tooltip_text = 'Aplica la recodificación seleccionada a TODAS las pistas de audio por separado (no las fusiona).\n\n• Advertencia: Esta función depende del formato de salida. No todos los contenedores (ej: `.mp3`) admiten audio multipista.'
        Tooltip(self.use_all_audio_tracks_check, multi_track_tooltip_text, delay_ms=1000)
        self.audio_quality_label.pack(fill='x', padx=5, pady=(10, 0))
        self.audio_quality_menu.pack(fill='x', padx=5, pady=(0, 5))
        legend_text = 'Guía de etiquetas en la lista:\n✨ Ideal: Formato óptimo para editar sin conversión.\n⚠️ Recodificar: Formato no compatible con editores.'
        self.format_warning_label = ctk.CTkLabel(details_frame, text=legend_text, text_color=self.app.get_theme_color('SECTION_SUBTITLE', 'gray'), font=ctk.CTkFont(size=12, weight='normal'), wraplength=400, justify='left')
        self.recode_main_frame = ctk.CTkScrollableFrame(details_frame)
        recode_title_label = ctk.CTkLabel(self.recode_main_frame, text='Opciones de Recodificación', font=ctk.CTkFont(weight='bold'))
        recode_title_label.pack(pady=(5, 10))
        recode_tooltip_text = 'Permite convertir el archivo a un formato diferente.\nÚtil para mejorar la compatibilidad con editores \n(ej: Premiere, After Effects) o para reducir el tamaño del archivo.'
        Tooltip(recode_title_label, recode_tooltip_text, delay_ms=1000)
        recode_mode_frame = ctk.CTkFrame(self.recode_main_frame, fg_color='transparent')
        recode_mode_frame.pack(fill='x', padx=10, pady=(0, 10))
        ctk.CTkLabel(recode_mode_frame, text='Modo:').pack(side='left', padx=(0, 10))
        self.recode_mode_selector = ctk.CTkSegmentedButton(recode_mode_frame, values=['Modo Rápido', 'Modo Manual', 'Extras'], command=self._on_recode_mode_change)
        self.recode_mode_selector.pack(side='left', expand=True, fill='x')
        self.recode_quick_frame = ctk.CTkFrame(self.recode_main_frame)
        self.apply_quick_preset_checkbox = ctk.CTkCheckBox(self.recode_quick_frame, text='Recodificación no disponible (Detectando FFmpeg...)', command=self._on_quick_recode_toggle, state='disabled')
        self.apply_quick_preset_checkbox.pack(anchor='w', padx=10, pady=(5, 5))
        self.apply_quick_preset_checkbox.deselect()
        self.quick_recode_options_frame = ctk.CTkFrame(self.recode_quick_frame, fg_color='transparent')
        preset_label = ctk.CTkLabel(self.quick_recode_options_frame, text='Preset de Conversión:', font=ctk.CTkFont(weight='bold'))
        preset_label.pack(pady=10, padx=10)
        def on_preset_change(selection):
            self.update_download_button_state()
            self._update_export_button_state()
            self.save_settings()
        self.recode_preset_menu = ctk.CTkOptionMenu(self.quick_recode_options_frame, values=['- Aún no disponible -'], command=on_preset_change)
        self.recode_preset_menu.pack(pady=10, padx=10, fill='x')
        preset_tooltip_text = 'Perfiles pre-configurados para tareas comunes.\n\n• Puedes crear y guardar tus propios presets desde el \'Modo Manual\'.\n• Tus presets guardados aparecerán en esta lista.'
        Tooltip(preset_label, preset_tooltip_text, delay_ms=1000)
        Tooltip(self.recode_preset_menu, preset_tooltip_text, delay_ms=1000)
        preset_actions_frame = ctk.CTkFrame(self.quick_recode_options_frame, fg_color='transparent')
        preset_actions_frame.pack(fill='x', padx=10, pady=(0, 10))
        preset_actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.import_preset_button = ctk.CTkButton(preset_actions_frame, text='📥 Importar', command=self.import_preset_file, fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER)
        self.import_preset_button.grid(row=0, column=0, padx=(0, 5), sticky='ew')
        self.export_preset_button = ctk.CTkButton(preset_actions_frame, text='📤 Exportar', command=self.export_preset_file, state='disabled', fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER)
        self.export_preset_button.grid(row=0, column=1, padx=5, sticky='ew')
        self.delete_preset_button = ctk.CTkButton(preset_actions_frame, text='🗑️ Eliminar', command=self.delete_preset_file, state='disabled', fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER)
        self.delete_preset_button.grid(row=0, column=2, padx=(5, 0), sticky='ew')
        self.keep_original_quick_checkbox = ctk.CTkCheckBox(self.recode_quick_frame, text='Mantener los archivos originales', command=self.save_settings, state='disabled')
        self.keep_original_quick_checkbox.pack(anchor='w', padx=10, pady=(0, 5))
        self.keep_original_quick_checkbox.select()
        self.recode_manual_frame = ctk.CTkFrame(self.recode_main_frame, fg_color='transparent')
        self.recode_toggle_frame = ctk.CTkFrame(self.recode_manual_frame, fg_color='transparent')
        self.recode_toggle_frame.pack(side='top', fill='x', padx=10, pady=(0, 10))
        self.recode_toggle_frame.grid_columnconfigure((0, 1), weight=1)
        self.recode_video_checkbox = ctk.CTkCheckBox(self.recode_toggle_frame, text='Recodificar Video', command=self._toggle_recode_panels, state='disabled')
        self.recode_video_checkbox.grid(row=0, column=0, padx=10, pady=(5, 5), sticky='w')
        video_recode_tooltip = 'Re-codifica solo la pista de video pero copia el audio si \'Recodificar Audio\' está desmarcado.'
        Tooltip(self.recode_video_checkbox, video_recode_tooltip, delay_ms=1000)
        self.recode_audio_checkbox = ctk.CTkCheckBox(self.recode_toggle_frame, text='Recodificar Audio', command=self._toggle_recode_panels, state='disabled')
        self.recode_audio_checkbox.grid(row=0, column=1, padx=10, pady=(5, 5), sticky='w')
        audio_recode_tooltip = 'Re-codifica solo la pista de audio pero copia el video si \'Recodificar Video\' está desmarcado.'
        Tooltip(self.recode_audio_checkbox, audio_recode_tooltip, delay_ms=1000)
        self.keep_original_checkbox = ctk.CTkCheckBox(self.recode_toggle_frame, text='Mantener los archivos originales', state='disabled', command=self.save_settings)
        self.keep_original_checkbox.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky='w')
        self.keep_original_checkbox.select()
        self.recode_warning_frame = ctk.CTkFrame(self.recode_manual_frame, fg_color='transparent')
        self.recode_warning_frame.pack(pady=0, padx=0, fill='x')
        self.recode_warning_label = ctk.CTkLabel(self.recode_warning_frame, text='', wraplength=400, justify='left', font=ctk.CTkFont(weight='bold'))
        self.recode_warning_label.pack(pady=5, padx=5, fill='both', expand=True)
        self.recode_options_frame = ctk.CTkFrame(self.recode_manual_frame)
        ctk.CTkLabel(self.recode_options_frame, text='Opciones de Video', font=ctk.CTkFont(weight='bold')).pack(pady=(5, 10), padx=10)
        self.proc_type_var = ctk.StringVar(value='')
        proc_frame = ctk.CTkFrame(self.recode_options_frame, fg_color='transparent')
        proc_frame.pack(fill='x', padx=10, pady=5)
        self.cpu_radio = ctk.CTkRadioButton(proc_frame, text='CPU', variable=self.proc_type_var, value='CPU', command=self.update_codec_menu)
        self.cpu_radio.pack(side='left', padx=10)
        cpu_tooltip_text = 'Usa el procesador (CPU) para la recodificación.\nEs más lento que la GPU, pero ofrece la máxima calidad y compatibilidad con todos los códecs de software.'
        Tooltip(self.cpu_radio, cpu_tooltip_text, delay_ms=1000)
        self.gpu_radio = ctk.CTkRadioButton(proc_frame, text='GPU', variable=self.proc_type_var, value='GPU', state='disabled', command=self.update_codec_menu)
        self.gpu_radio.pack(side='left', padx=20)
        gpu_tooltip_text = 'Usa la tarjeta gráfica (GPU) para una recodificación acelerada por hardware (más rápida).\nSolo se listarán códecs compatibles con la GPU (ej: NVENC, AMF, QSV).'
        Tooltip(self.gpu_radio, gpu_tooltip_text, delay_ms=1000)
        codec_options_frame = ctk.CTkFrame(self.recode_options_frame)
        codec_options_frame.pack(fill='x', padx=10, pady=5)
        codec_options_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(codec_options_frame, text='Codec:').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.recode_codec_menu = ctk.CTkOptionMenu(codec_options_frame, values=['-'], state='disabled', command=self.update_profile_menu)
        self.recode_codec_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ctk.CTkLabel(codec_options_frame, text='Perfil/Calidad:').grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.recode_profile_menu = ctk.CTkOptionMenu(codec_options_frame, values=['-'], state='disabled', command=self.on_profile_selection_change)
        self.recode_profile_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.custom_bitrate_frame = ctk.CTkFrame(codec_options_frame, fg_color='transparent')
        ctk.CTkLabel(self.custom_bitrate_frame, text='Bitrate (Mbps):').pack(side='left', padx=(0, 5))
        self.custom_bitrate_entry = ctk.CTkEntry(self.custom_bitrate_frame, placeholder_text='Ej: 8', width=100)
        self.custom_bitrate_entry.bind('<KeyRelease>', self.update_download_button_state)
        self.custom_bitrate_entry.pack(side='left')
        self.custom_gif_frame = ctk.CTkFrame(codec_options_frame, fg_color='transparent')
        self.custom_gif_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5)
        self.custom_gif_frame.grid_remove()
        ctk.CTkLabel(self.custom_gif_frame, text='FPS:').pack(side='left', padx=(0, 5))
        self.custom_gif_fps_entry = ctk.CTkEntry(self.custom_gif_frame, placeholder_text='15', width=60)
        self.custom_gif_fps_entry.pack(side='left')
        ctk.CTkLabel(self.custom_gif_frame, text='Ancho:').pack(side='left', padx=(15, 5))
        self.custom_gif_width_entry = ctk.CTkEntry(self.custom_gif_frame, placeholder_text='480', width=60)
        self.custom_gif_width_entry.pack(side='left')
        self.estimated_size_label = ctk.CTkLabel(self.custom_bitrate_frame, text='N/A', font=ctk.CTkFont(weight='bold'))
        self.estimated_size_label.pack(side='right', padx=(10, 0))
        ctk.CTkLabel(self.custom_bitrate_frame, text='Tamaño Estimado:').pack(side='right')
        ctk.CTkLabel(codec_options_frame, text='Contenedor:').grid(row=3, column=0, padx=5, pady=5, sticky='w')
        container_value_frame = ctk.CTkFrame(codec_options_frame, fg_color='transparent')
        container_value_frame.grid(row=3, column=1, padx=5, pady=0, sticky='ew')
        self.recode_container_label = ctk.CTkLabel(container_value_frame, text='-', font=ctk.CTkFont(weight='bold'))
        self.recode_container_label.pack(side='left', padx=5, pady=5)
        self.fps_frame = ctk.CTkFrame(self.recode_options_frame)
        self.fps_frame.pack(fill='x', padx=10, pady=(10, 5))
        self.fps_frame.grid_columnconfigure(1, weight=1)
        self.fps_checkbox = ctk.CTkCheckBox(self.fps_frame, text='Forzar FPS Constantes (CFR)', command=self.toggle_fps_entry_panel)
        self.fps_checkbox.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        fps_tooltip_text = 'Fuerza una tasa de fotogramas constante (CFR).\n\nMuchos videos de internet usan FPS Variable (VFR), lo que causa problemas de audio desincronizado en editores como Premiere o After Effects. Activando esto se soluciona.'
        Tooltip(self.fps_checkbox, fps_tooltip_text, delay_ms=1000)
        self.fps_value_label = ctk.CTkLabel(self.fps_frame, text='Valor FPS:')
        self.fps_entry = ctk.CTkEntry(self.fps_frame, placeholder_text='Ej: 23.976, 25, 29.97, 30, 60')
        self.toggle_fps_entry_panel()
        self.resolution_frame = ctk.CTkFrame(self.recode_options_frame)
        self.resolution_frame.pack(fill='x', padx=10, pady=5)
        self.resolution_frame.grid_columnconfigure(1, weight=1)
        self.resolution_checkbox = ctk.CTkCheckBox(self.resolution_frame, text='Cambiar Resolución', command=self.toggle_resolution_panel)
        self.resolution_checkbox.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        self.resolution_options_frame = ctk.CTkFrame(self.resolution_frame, fg_color='transparent')
        self.resolution_options_frame.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.resolution_options_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.resolution_options_frame, text='Preset:').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.resolution_preset_menu = ctk.CTkOptionMenu(self.resolution_options_frame, values=['Personalizado', '4K UHD', '2K QHD', '1080p Full HD', '720p HD', '480p SD'], command=self.on_resolution_preset_change)
        self.resolution_preset_menu.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.resolution_manual_frame = ctk.CTkFrame(self.resolution_options_frame, fg_color='transparent')
        self.resolution_manual_frame.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.resolution_manual_frame.grid_columnconfigure((0, 2), weight=1)
        ctk.CTkLabel(self.resolution_manual_frame, text='Ancho:').grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.width_entry = ctk.CTkEntry(self.resolution_manual_frame, width=80)
        self.width_entry.grid(row=0, column=1, padx=5, pady=5)
        self.width_entry.bind('<KeyRelease>', lambda event: self.on_dimension_change('width'))
        self.aspect_ratio_lock = ctk.CTkCheckBox(self.resolution_manual_frame, text='🔗', font=ctk.CTkFont(size=16), command=self.on_aspect_lock_change)
        self.aspect_ratio_lock.grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkLabel(self.resolution_manual_frame, text='Alto:').grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.height_entry = ctk.CTkEntry(self.resolution_manual_frame, width=80)
        self.height_entry.grid(row=1, column=1, padx=5, pady=5)
        self.height_entry.bind('<KeyRelease>', lambda event: self.on_dimension_change('height'))
        self.no_upscaling_checkbox = ctk.CTkCheckBox(self.resolution_manual_frame, text='No ampliar resolución')
        self.no_upscaling_checkbox.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky='w')
        self.toggle_resolution_panel()
        self.recode_audio_options_frame = ctk.CTkFrame(self.recode_manual_frame)
        self.recode_audio_options_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.recode_audio_options_frame, text='Opciones de Audio', font=ctk.CTkFont(weight='bold')).grid(row=0, column=0, columnspan=2, pady=(5, 10), padx=10)
        ctk.CTkLabel(self.recode_audio_options_frame, text='Codec de Audio:').grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.recode_audio_codec_menu = ctk.CTkOptionMenu(self.recode_audio_options_frame, values=['-'], state='disabled', command=self.update_audio_profile_menu)
        self.recode_audio_codec_menu.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        ctk.CTkLabel(self.recode_audio_options_frame, text='Perfil de Audio:').grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.recode_audio_profile_menu = ctk.CTkOptionMenu(self.recode_audio_options_frame, values=['-'], state='disabled', command=lambda _: self._validate_recode_compatibility())
        self.recode_audio_profile_menu.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        self.save_preset_frame = ctk.CTkFrame(self.recode_manual_frame)
        self.save_preset_frame.pack(side='bottom', fill='x', padx=0, pady=(10, 0))
        self.save_preset_button = ctk.CTkButton(self.save_preset_frame, text='Guardar como ajuste prestablecido', command=self.open_save_preset_dialog)
        self.save_preset_button.pack(fill='x', padx=10, pady=(10, 5))
        self.recode_extract_frame = ctk.CTkFrame(self.recode_main_frame, fg_color='transparent')
        self.extract_options_frame = ctk.CTkFrame(self.recode_extract_frame)
        self.extract_options_frame.pack(fill='x', padx=0, pady=0)
        self.extract_options_frame.grid_columnconfigure(1, weight=1)
        self.keep_original_extract_checkbox = ctk.CTkCheckBox(self.extract_options_frame, text='Mantener el video original', font=ctk.CTkFont(size=12), command=self.save_settings)
        self.keep_original_extract_checkbox.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 3), sticky='w')
        self.keep_original_extract_checkbox.select()
        self.extract_frames_checkbox = ctk.CTkCheckBox(self.extract_options_frame, text='Extraer fotogramas del video', font=ctk.CTkFont(size=12), command=self._on_extract_frames_toggle)
        self.extract_frames_checkbox.grid(row=1, column=0, columnspan=2, padx=10, pady=(3, 5), sticky='w')
        self.extract_frames_subpanel = ctk.CTkFrame(self.extract_options_frame, fg_color='transparent')
        self.extract_frames_subpanel.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.extract_frames_subpanel.grid_columnconfigure(1, weight=1)
        self.extract_frames_subpanel.grid_remove()
        ctk.CTkLabel(self.extract_frames_subpanel, text='Tipo:', font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(10, 5), pady=(5, 3), sticky='w')
        self.extract_type_menu = ctk.CTkOptionMenu(self.extract_frames_subpanel, values=['Video a Secuencia de Imagenes'], font=ctk.CTkFont(size=12), state='disabled')
        self.extract_type_menu.grid(row=0, column=1, padx=(0, 10), pady=(5, 3), sticky='ew')
        ctk.CTkLabel(self.extract_frames_subpanel, text='Formato:', font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.extract_format_menu = ctk.CTkOptionMenu(self.extract_frames_subpanel, values=['PNG (calidad alta)', 'JPG (tamano reducido)'], font=ctk.CTkFont(size=12), command=self._toggle_extract_options)
        self.extract_format_menu.grid(row=1, column=1, padx=(0, 10), pady=(3, 3), sticky='ew')
        self.extract_jpg_quality_frame = ctk.CTkFrame(self.extract_frames_subpanel, fg_color='transparent')
        self.extract_jpg_quality_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.extract_jpg_quality_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.extract_jpg_quality_frame, text='Calidad JPG:', font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.extract_jpg_quality_value_label = ctk.CTkLabel(self.extract_jpg_quality_frame, text='9', width=30, anchor='e', font=ctk.CTkFont(size=12))
        self.extract_jpg_quality_value_label.grid(row=0, column=2, padx=(5, 10), pady=(3, 3), sticky='e')
        def _on_jpg_quality_slide(value):
            self.extract_jpg_quality_value_label.configure(text=str(int(value)))
        self.extract_jpg_quality_slider = ctk.CTkSlider(self.extract_jpg_quality_frame, from_=1, to=10, number_of_steps=9, command=_on_jpg_quality_slide)
        self.extract_jpg_quality_slider.set(9)
        self.extract_jpg_quality_slider.grid(row=0, column=1, padx=(0, 5), pady=(3, 3), sticky='ew')
        Tooltip(self.extract_jpg_quality_slider, 'Calidad de la imagen JPG.\nEscala de 1 (minima) a 10 (maxima).\nSe recomienda dejar en 9 o superior.', delay_ms=1000)
        self.extract_jpg_quality_frame.grid_remove()
        ctk.CTkLabel(self.extract_frames_subpanel, text='FPS:', font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.extract_fps_entry = ctk.CTkEntry(self.extract_frames_subpanel, placeholder_text='Vacio = Todos los fotogramas', font=ctk.CTkFont(size=12))
        self.extract_fps_entry.grid(row=3, column=1, padx=(0, 10), pady=(3, 3), sticky='ew')
        Tooltip(self.extract_fps_entry, 'Ej: \'10\' para 10 FPS.\nDejalo vacio para extraer CADA fotograma (puede generar miles de archivos)', delay_ms=1000)
        ctk.CTkLabel(self.extract_frames_subpanel, text='Nombre de carpeta:', font=ctk.CTkFont(size=12)).grid(row=4, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.extract_folder_name_entry = ctk.CTkEntry(self.extract_frames_subpanel, placeholder_text='Nombre del video + \'_frames\'', font=ctk.CTkFont(size=12))
        self.extract_folder_name_entry.grid(row=4, column=1, padx=(0, 10), pady=(3, 3), sticky='ew')
        Tooltip(self.extract_folder_name_entry, 'Personaliza el nombre de la carpeta donde se guardaran las imagenes.\nSi lo dejas vacio, se usara el nombre del video.', delay_ms=1000)
        self.extract_results_frame = ctk.CTkFrame(self.extract_frames_subpanel, fg_color='transparent')
        self.extract_results_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(5, 3))
        self.extract_results_frame.grid_columnconfigure((0, 1), weight=1)
        self.extract_success_label = ctk.CTkLabel(self.extract_results_frame, text='', font=ctk.CTkFont(weight='bold'), text_color='#28A745')
        self.extract_success_label.grid(row=0, column=0, columnspan=2, pady=(5, 5), sticky='ew')
        self.send_to_imagetools_button = ctk.CTkButton(self.extract_results_frame, text='Enviar a H.I', command=self._send_folder_to_image_tools, height=32, state='disabled')
        self.send_to_imagetools_button.grid(row=1, column=0, padx=(10, 5), pady=(0, 5), sticky='ew')
        self.extract_save_preset_btn = ctk.CTkButton(self.extract_results_frame, text='Guardar Preset', command=self.open_save_preset_dialog, height=32)
        self.extract_save_preset_btn.grid(row=1, column=1, padx=(5, 10), pady=(0, 5), sticky='ew')
        self.upscale_video_checkbox = ctk.CTkCheckBox(self.extract_options_frame, text='Reescalar video', font=ctk.CTkFont(size=12), command=self._on_upscale_video_toggle)
        self.upscale_video_checkbox.grid(row=3, column=0, columnspan=2, padx=10, pady=(3, 5), sticky='w')
        self.upscale_video_subpanel = ctk.CTkFrame(self.extract_options_frame, fg_color='transparent')
        self.upscale_video_subpanel.grid(row=4, column=0, columnspan=2, sticky='ew')
        self.upscale_video_subpanel.grid_columnconfigure(1, weight=1)
        self.upscale_video_subpanel.grid_columnconfigure(3, weight=1)
        self.upscale_video_subpanel.grid_remove()
        ctk.CTkLabel(self.upscale_video_subpanel, text='Motor:', font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(10, 5), pady=(5, 3), sticky='w')
        self.upscale_engine_menu = ctk.CTkOptionMenu(self.upscale_video_subpanel, values=[AI_ENGINE_HOLDER, 'Upscayl', 'Waifu2x', 'SRMD'], font=ctk.CTkFont(size=12), command=self._on_upscale_engine_change)
        self.upscale_engine_menu.set(AI_ENGINE_HOLDER)
        self.upscale_engine_menu.grid(row=0, column=1, columnspan=3, padx=(0, 10), pady=(5, 3), sticky='ew')
        Tooltip(self.upscale_engine_menu, 'Motor de IA para reescalado.\nUpscayl es el mas recomendado para video.', delay_ms=1000)
        ctk.CTkLabel(self.upscale_video_subpanel, text='Modelo:', font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.upscale_model_container = ctk.CTkFrame(self.upscale_video_subpanel, fg_color='transparent')
        self.upscale_model_container.grid(row=1, column=1, columnspan=3, padx=(0, 10), pady=(3, 3), sticky='ew')
        self.upscale_model_container.grid_columnconfigure(0, weight=1)
        self.upscale_model_menu = ctk.CTkOptionMenu(self.upscale_model_container, values=[AI_MODEL_HOLDER], font=ctk.CTkFont(size=12), command=self._on_upscale_model_change)
        self.upscale_model_menu.set(AI_MODEL_HOLDER)
        self.upscale_model_menu.grid(row=0, column=0, padx=(0, 5), pady=0, sticky='ew')
        Tooltip(self.upscale_model_menu, 'Modelo dentro del motor seleccionado.', delay_ms=1000)
        self.upscale_add_custom_btn = ctk.CTkButton(self.upscale_model_container, text='+', width=30, height=24, fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, font=ctk.CTkFont(size=16, weight='bold'), command=self._on_add_custom_model)
        self.upscale_add_custom_btn.grid(row=0, column=1, padx=0, pady=0, sticky='e')
        Tooltip(self.upscale_add_custom_btn, 'Agregar modelo personalizado (.bin/.param)', delay_ms=500)
        ctk.CTkLabel(self.upscale_video_subpanel, text='Escala:', font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        _initial_scales = ['2x', '3x', '4x', '5x', '6x', '7x', '8x']
        self.upscale_scale_menu = ctk.CTkOptionMenu(self.upscale_video_subpanel, values=_initial_scales, width=70, font=ctk.CTkFont(size=12))
        self.upscale_scale_menu.grid(row=2, column=1, padx=(0, 5), pady=(3, 3), sticky='w')
        ctk.CTkLabel(self.upscale_video_subpanel, text='Tile Size:', font=ctk.CTkFont(size=12)).grid(row=2, column=2, padx=(5, 5), pady=(3, 3), sticky='w')
        self.upscale_tile_entry = ctk.CTkEntry(self.upscale_video_subpanel, width=60, placeholder_text='0', font=ctk.CTkFont(size=12))
        self.upscale_tile_entry.insert(0, '0')
        self.upscale_tile_entry.grid(row=2, column=3, padx=(0, 10), pady=(3, 3), sticky='w')
        Tooltip(self.upscale_scale_menu, 'Factor de reescalado.', delay_ms=1000)
        Tooltip(self.upscale_tile_entry, 'Tamaño de bloque (VRAM). 0 = Auto.', delay_ms=1000)
        ctk.CTkLabel(self.upscale_video_subpanel, text='Potencia:', font=ctk.CTkFont(size=12)).grid(row=3, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.upscale_threads_menu = ctk.CTkOptionMenu(self.upscale_video_subpanel, values=['Automático', 'Seguro (Estabilidad)', 'Equilibrado', 'Máximo (Potente)'], font=ctk.CTkFont(size=12))
        self.upscale_threads_menu.set('Automático')
        self.upscale_threads_menu.grid(row=3, column=1, columnspan=3, padx=(0, 10), pady=(3, 3), sticky='ew')
        Tooltip(self.upscale_threads_menu, 'Control de hilos (concurrencia).', delay_ms=1000)
        self.upscale_denoise_label = ctk.CTkLabel(self.upscale_video_subpanel, text='Reducir Ruido:', font=ctk.CTkFont(size=12))
        self.upscale_denoise_label.grid(row=4, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.upscale_denoise_menu = ctk.CTkOptionMenu(self.upscale_video_subpanel, values=['-1 (Ninguna)', '0 (Baja)', '1 (Media)', '2 (Alta)', '3 (Máxima)'], font=ctk.CTkFont(size=12))
        self.upscale_denoise_menu.set('2 (Alta)')
        self.upscale_denoise_menu.grid(row=4, column=1, columnspan=3, padx=(0, 10), pady=(3, 3), sticky='ew')
        Tooltip(self.upscale_denoise_menu, 'Nivel de reducción de ruido (Solo compatible con Waifu2x y SRMD).', delay_ms=1000)
        ctk.CTkLabel(self.upscale_video_subpanel, text='Contenedor:', font=ctk.CTkFont(size=12)).grid(row=5, column=0, padx=(10, 5), pady=(3, 3), sticky='w')
        self.upscale_container_menu = ctk.CTkOptionMenu(self.upscale_video_subpanel, values=['Mismo que el original', 'MP4', 'MKV', 'MOV', 'AVI'], font=ctk.CTkFont(size=12))
        self.upscale_container_menu.grid(row=5, column=1, columnspan=3, padx=(0, 10), pady=(3, 3), sticky='ew')
        Tooltip(self.upscale_container_menu, 'Formato del video de salida.', delay_ms=1000)
        self.upscale_tta_checkbox = ctk.CTkCheckBox(self.upscale_video_subpanel, text='TTA (Mejor calidad, muy lento)', font=ctk.CTkFont(size=12))
        self.upscale_tta_checkbox.grid(row=6, column=0, columnspan=4, padx=(10, 5), pady=(3, 3), sticky='w')
        self.upscale_tta_checkbox.deselect()
        Tooltip(self.upscale_tta_checkbox, 'Test Time Augmentation.', delay_ms=1000)
        self.upscale_transparency_checkbox = ctk.CTkCheckBox(self.upscale_video_subpanel, text='Preservar Transparencia (Alpha)', font=ctk.CTkFont(size=12), command=self._on_transparency_toggle)
        self.upscale_transparency_checkbox.grid(row=7, column=0, columnspan=4, padx=(10, 5), pady=(3, 3), sticky='w')
        Tooltip(self.upscale_transparency_checkbox, 'Conserva el canal Alpha (transparencia).', delay_ms=1000)
        ctk.CTkLabel(self.upscale_video_subpanel, text='Nombre de salida:', font=ctk.CTkFont(size=12)).grid(row=8, column=0, padx=(10, 5), pady=(3, 5), sticky='w')
        self.upscale_output_name_entry = ctk.CTkEntry(self.upscale_video_subpanel, placeholder_text='Nombre del video + \'_upscaled\'', font=ctk.CTkFont(size=12))
        self.upscale_output_name_entry.grid(row=8, column=1, columnspan=3, padx=(0, 10), pady=(3, 5), sticky='ew')
        Tooltip(self.upscale_output_name_entry, 'Nombre personalizado para el archivo de salida.', delay_ms=1000)
        self.upscale_status_label = ctk.CTkLabel(self.upscale_video_subpanel, text='', font=ctk.CTkFont(size=10))
        self.upscale_status_label.grid(row=9, column=0, columnspan=4, padx=10, pady=(2, 2), sticky='ew')
        self.upscale_mgmt_frame = ctk.CTkFrame(self.upscale_video_subpanel, fg_color='transparent')
        self.upscale_mgmt_frame.grid(row=10, column=0, columnspan=4, padx=10, pady=(0, 5), sticky='ew')
        self.upscale_mgmt_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.upscale_open_btn = ctk.CTkButton(self.upscale_mgmt_frame, text='Abrir', height=22, font=ctk.CTkFont(size=11), fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, command=lambda: self._open_model_folder('upscale'))
        self.upscale_open_btn.grid(row=0, column=0, padx=(0, 5), sticky='ew')
        self.upscale_delete_btn = ctk.CTkButton(self.upscale_mgmt_frame, text='Borrar', height=22, font=ctk.CTkFont(size=11), fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, command=lambda: self._delete_current_model('upscale'))
        self.upscale_delete_btn.grid(row=0, column=1, padx=(5, 5), sticky='ew')
        self.upscale_save_preset_btn = ctk.CTkButton(self.upscale_mgmt_frame, text='Guardar Preset', height=22, font=ctk.CTkFont(size=11), command=self.open_save_preset_dialog)
        self.upscale_save_preset_btn.grid(row=0, column=2, padx=(5, 0), sticky='ew')
        self.app.after(500, lambda: self._on_upscale_engine_change('Upscayl', silent=True))
        local_import_frame = ctk.CTkFrame(self.recode_main_frame)
        local_import_frame.pack(side='bottom', fill='x', padx=10, pady=(15, 5))
        ctk.CTkLabel(local_import_frame, text='¿Tienes un archivo existente?', font=ctk.CTkFont(weight='bold')).pack()
        self.import_button = ctk.CTkButton(local_import_frame, text='Importar Archivo Local para Recodificar', fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, command=self.import_local_file)
        self.import_button.pack(fill='x', padx=10, pady=5)
        self.save_in_same_folder_check = ctk.CTkCheckBox(local_import_frame, text='Guardar en la misma carpeta que el original', command=self._on_save_in_same_folder_change)
        self.clear_local_file_button = ctk.CTkButton(local_import_frame, text='Limpiar y Volver a Modo URL', fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, command=self.reset_to_url_mode)
        progress_frame = ctk.CTkFrame(self)
        progress_frame.pack(side='bottom', pady=(0, 10), padx=10, fill='x')
        self.progress_label = ctk.CTkLabel(progress_frame, text='Esperando...')
        self.progress_label.pack(pady=(5, 0))
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 5), padx=10, fill='x')
        download_frame = ctk.CTkFrame(self)
        download_frame.pack(side='bottom', pady=10, padx=10, fill='x')
        ctk.CTkLabel(download_frame, text='Carpeta de Salida:').pack(side='left', padx=(10, 5))
        self.output_path_entry = ctk.CTkEntry(download_frame, placeholder_text='Selecciona una carpeta...')
        self.output_path_entry.bind('<KeyRelease>', self.update_download_button_state)
        self.output_path_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.output_path_entry))
        self.output_path_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.select_folder_button = ctk.CTkButton(download_frame, text='...', width=40, command=lambda: self.select_output_folder())
        self.select_folder_button.pack(side='left', padx=(0, 5))
        self.open_folder_button = ctk.CTkButton(download_frame, text='📂', width=40, font=ctk.CTkFont(size=16), command=self.open_last_download_folder, state='disabled')
        self.open_folder_button.pack(side='left', padx=(0, 5))
        speed_label = ctk.CTkLabel(download_frame, text='Límite (MB/s):')
        speed_label.pack(side='left', padx=(10, 5))
        self.speed_limit_entry = ctk.CTkEntry(download_frame, width=50)
        tooltip_text = 'Limita la velocidad de descarga (en MB/s).\nÚtil si las descargas fallan por \'demasiadas peticiones\'.'
        Tooltip(speed_label, tooltip_text, delay_ms=1000)
        Tooltip(self.speed_limit_entry, tooltip_text, delay_ms=1000)
        self.speed_limit_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.speed_limit_entry))
        self.speed_limit_entry.pack(side='left', padx=(0, 10))
        self.download_button = ctk.CTkButton(download_frame, text=self.original_download_text, state='disabled', command=self.original_download_command, fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color_disabled=self.DISABLED_TEXT_COLOR)
        self.download_button.pack(side='left', padx=(5, 10))
        if hasattr(self, 'info_frame_ref'):
            self.info_frame_ref.pack(side='top', fill='both', expand=True, padx=10, pady=(5, 10))
        self.on_mode_change(self.mode_selector.get())
        self.on_profile_selection_change(self.recode_profile_menu.get())
        self.start_h.bind('<KeyRelease>', lambda e: (self._handle_time_input(e, self.start_h, self.start_m), self.update_download_button_state()))
        self.start_m.bind('<KeyRelease>', lambda e: (self._handle_time_input(e, self.start_m, self.start_s), self.update_download_button_state()))
        self.start_s.bind('<KeyRelease>', lambda e: (self._handle_time_input(e, self.start_s), self.update_download_button_state()))
        self.end_h.bind('<KeyRelease>', lambda e: (self._handle_time_input(e, self.end_h, self.end_m), self.update_download_button_state()))
        self.end_m.bind('<KeyRelease>', lambda e: (self._handle_time_input(e, self.end_m, self.end_s), self.update_download_button_state()))
        self.end_s.bind('<KeyRelease>', lambda e: (self._handle_time_input(e, self.end_s), self.update_download_button_state()))
        self._toggle_fragment_panel()
        self.recode_mode_selector.set('Modo Rápido')
        self._on_recode_mode_change('Modo Rápido')
        self.recode_main_frame.pack(pady=(10, 0), padx=5, fill='both', expand=True)
        print('DEBUG: Panel de recodificación inicializado y visible')
    def create_entry_context_menu(self, widget):
        """Crea y muestra un menú contextual para un widget de entrada de texto."""
        import tkinter
        from tkinter import TclError

        menu = tkinter.Menu(self, tearoff=0)

        # --- Función Copiar ---
        def copy_text():
            """Copia el texto seleccionado al portapapeles."""
            try:
                selected_text = widget.selection_get()
                if selected_text:
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
            except TclError:
                # No hay selección
                pass
            except Exception as e:
                # Cualquier otro error (p.ej., portapapeles bloqueado)
                print(f'DEBUG: Error al copiar: {e}')

        # --- Función Cortar ---
        def cut_text():
            """Corta el texto seleccionado (copia y borra)."""
            try:
                selected_text = widget.selection_get()
                if selected_text:
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
                    widget.delete('sel.first', 'sel.last')
                    # Actualizar estado del botón después de cortar
                    self.app.after(10, self.update_download_button_state)
            except TclError:
                # No hay selección
                pass
            except Exception as e:
                print(f'DEBUG: Error al cortar: {e}')

        # --- Función Pegar ---
        def paste_text():
            """Pega el texto del portapapeles."""
            # Si hay selección, eliminarla antes de pegar
            try:
                if widget.selection_get():
                    widget.delete('sel.first', 'sel.last')
            except TclError:
                # No hay selección, no hacemos nada
                pass
            try:
                widget.insert('insert', self.clipboard_get())
                self.app.after(10, self.update_download_button_state)
            except TclError:
                # Portapapeles vacío o inaccesible
                pass
            except Exception as e:
                print(f'DEBUG: Error al pegar: {e}')

        # --- Construir menú ---
        menu.add_command(label='Cortar', command=cut_text)
        menu.add_command(label='Copiar', command=copy_text)
        menu.add_command(label='Pegar', command=paste_text)
        menu.add_separator()
        menu.add_command(label='Seleccionar todo', command=lambda: widget.select_range(0, 'end'))

        # --- Mostrar menú contextual ---
        try:
            menu.tk_popup(widget.winfo_pointerx(), widget.winfo_pointery())
        except Exception as e:
            # El widget pudo haber sido destruido antes de mostrar el menú
            print(f'DEBUG: Error al mostrar menú contextual: {e}')
    def paste_into_widget(self, widget):
        """Obtiene el contenido del portapapeles y lo inserta en un widget."""
        try:
            clipboard_text = self.clipboard_get()
            widget.insert('insert', clipboard_text)
        except tkinter.TclError:
            return None
    def _open_release_page(self):
        """Abre la página de la release en el navegador."""
        if self.release_page_url:
            webbrowser.open_new_tab(self.release_page_url)
            return
        else:
            from src.core.setup import check_app_update
            self.app_status_label.configure(text=f'DowP v{self.app.APP_VERSION} - Verificando de nuevo...')
            self.update_app_button.configure(state='disabled')
            threading.Thread(target=lambda: self.app.on_update_check_complete(check_app_update(self.app.APP_VERSION)), daemon=True).start()
    def update_setup_download_progress(self, source, text, value):
        """\n        Callback para actualizar el estado de descarga de UNA dependencia (FFmpeg o Deno).\n        \'source\' debe ser \'ffmpeg\' o \'deno\'.\n        \'value\' está en el rango 0-100.\n        """
        if source not in self.active_downloads_state:
            return
        else:
            progress_value = float(value) / 100.0
            self.active_downloads_state[source]['text'] = text
            self.active_downloads_state[source]['value'] = progress_value
            self.active_downloads_state[source]['active'] = progress_value > 0 and progress_value < 1
            self._render_setup_progress()
    def _render_setup_progress(self):
        ffmpeg_state = self.active_downloads_state['ffmpeg']
        deno_state = self.active_downloads_state['deno']
        poppler_state = self.active_downloads_state.get('poppler', {'text': '', 'value': 0.0, 'active': False})
        inkscape_state = self.active_downloads_state.get('inkscape', {'text': '', 'value': 0.0, 'active': False})
        rembg_state = self.active_downloads_state.get('rembg', {'text': '', 'value': 0.0, 'active': False})
        active_count = sum([ffmpeg_state['active'], deno_state['active'], poppler_state['active'], inkscape_state['active'], rembg_state['active']])
        final_text = 'Esperando...'
        final_progress = 0.0
        if active_count > 0:
            final_text = f'Descargando dependencias ({active_count} activas)...'
            total_val = ffmpeg_state['value'] + deno_state['value'] + poppler_state['value'] + inkscape_state['value'] + rembg_state['value']
            final_progress = total_val / max(1, active_count)
            if active_count == 1:
                if ffmpeg_state['active']:
                    final_text = ffmpeg_state['text']
                    final_progress = ffmpeg_state['value']
                else:
                    if deno_state['active']:
                        final_text = deno_state['text']
                        final_progress = deno_state['value']
                    else:
                        if poppler_state['active']:
                            final_text = poppler_state['text']
                            final_progress = poppler_state['value']
                        else:
                            if inkscape_state['active']:
                                final_text = inkscape_state['text']
                                final_progress = inkscape_state['value']
                            else:
                                if rembg_state['active']:
                                    final_text = rembg_state['text']
                                    final_progress = rembg_state['value']
        else:
            if rembg_state['text']:
                final_text = rembg_state['text']
                final_progress = rembg_state['value']
            else:
                if poppler_state['text']:
                    final_text = poppler_state['text']
                    final_progress = poppler_state['value']
                else:
                    if deno_state['text']:
                        final_text = deno_state['text']
                        final_progress = deno_state['value']
                    else:
                        if ffmpeg_state['text']:
                            final_text = ffmpeg_state['text']
                            final_progress = ffmpeg_state['value']
                        else:
                            if inkscape_state['text']:
                                final_text = inkscape_state['text']
                                final_progress = inkscape_state['value']
        self.update_progress(final_progress, final_text)
    def _execute_fragment_clipping(self, input_filepath, start_time, end_time):
        """\n        Corta un fragmento de un archivo de video/audio usando FFmpeg en modo de copia de stream.\n        \n        🆕 NUEVO: Ahora interpreta correctamente:\n        - Solo inicio → Desde ese tiempo hasta el final\n        - Solo fin → Desde el principio hasta ese tiempo\n        - Ambos → Fragmento específico\n        \n        Args:\n            input_filepath (str): La ruta al archivo de medios original.\n            start_time (str): El tiempo de inicio del corte (formato HH:MM:SS o vacío).\n            end_time (str): El tiempo de finalización del corte (formato HH:MM:SS o vacío).\n            \n        Returns:\n            str: La ruta al archivo de medios recién creado y cortado.\n        \n        Raises:\n            UserCancelledError: Si la operación es cancelada por el usuario.\n            Exception: Si FFmpeg falla durante el proceso de corte.\n        """
        self.app.after(0, self.update_progress, 98, 'Cortando fragmento con ffmpeg...')
        base_name, ext = os.path.splitext(os.path.basename(input_filepath))
        clipped_filename = f'{base_name}_fragmento{ext}'
        desired_clipped_filepath = os.path.join(os.path.dirname(input_filepath), clipped_filename)
        clipped_filepath, backup_path = self._resolve_output_path(desired_clipped_filepath)
        start_seconds = self.time_str_to_seconds(start_time) if start_time else 0
        if end_time:
            end_seconds = self.time_str_to_seconds(end_time)
        else:
            end_seconds = self.video_duration
        fragment_duration = end_seconds - start_seconds
        if fragment_duration <= 0:
            raise Exception('La duración del fragmento es inválida (tiempo final debe ser mayor que inicial)')
        else:
            pre_params = []
            ffmpeg_params = []
            if start_time:
                pre_params.extend(['-ss', start_time])
            duration_str = self._seconds_to_time_str(fragment_duration)
            ffmpeg_params.extend(['-t', duration_str])
            ffmpeg_params.extend(['-c:v', 'copy', '-c:a', 'copy', '-map', '0:v?', '-map', '0:a?'])
            clip_opts = {'input_file': input_filepath, 'output_file': clipped_filepath, 'ffmpeg_params': ffmpeg_params, 'pre_params': pre_params, 'duration': fragment_duration}
            self.ffmpeg_processor.execute_recode(clip_opts, lambda p, m: self.update_progress(p, f'Cortando... {p:.1f}%'), self.cancellation_event)
            if backup_path and os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                    except OSError as e:
                        print(f'ADVERTENCIA: No se pudo limpiar el backup del recorte: {e}')
            return clipped_filepath
    def _seconds_to_time_str(self, seconds):
        """Convierte segundos a formato HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        secs = int(seconds % 60)
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    def _handle_optional_clipping(self, downloaded_filepath, options):
        """
        Verifica si se necesita un recorte y lo ejecuta.
        Maneja la eliminación del archivo original si es necesario.
        
        Args:
            downloaded_filepath (str): Ruta al archivo recién descargado.
            options (dict): Diccionario de opciones de la operación.
            
        Returns:
            str: Ruta final al archivo que debe ser procesado (original o fragmento).
        """
        import os

        # 1) ¿El usuario quiere fragmento?
        user_wanted_fragment = options.get('fragment_enabled') and (options.get('start_time') or options.get('end_time'))
        if not user_wanted_fragment:
            return downloaded_filepath

        # 2) Si ya fue cortado por yt-dlp (y no forzamos descarga completa), saltamos
        if not options.get('force_full_download', False) and options.get('fragment_enabled', False):
            print('DEBUG: ✅ El fragmento ya fue descargado directamente por yt-dlp. Saltando corte local.')
            return downloaded_filepath

        # 3) Realizar corte local con FFmpeg
        print('DEBUG: ✂️ Iniciando corte local con FFmpeg...')
        clipped_filepath = self._execute_fragment_clipping(
            input_filepath=downloaded_filepath,
            start_time=options.get('start_time'),
            end_time=options.get('end_time')
        )

        # Limpiar opciones de fragmento para evitar recortes repetidos
        options['fragment_enabled'] = False
        options['start_time'] = ''
        options['end_time'] = ''

        # 4) Manejar el archivo original (conservar o eliminar)
        if options.get('keep_original_on_clip'):
            # Renombrar el original a *_full.ext
            directory = os.path.dirname(downloaded_filepath)
            filename = os.path.basename(downloaded_filepath)
            name, ext = os.path.splitext(filename)
            new_full_path = os.path.join(directory, f'{name}_full{ext}')
            try:
                # Si ya existe un backup, eliminarlo primero
                if os.path.exists(new_full_path):
                    os.remove(new_full_path)
                os.rename(downloaded_filepath, new_full_path)
                print(f'DEBUG: Archivo original conservado como: {new_full_path}')
            except OSError as err:
                print(f'ADVERTENCIA: Error gestionando el archivo original: {err}')
                # No lanzamos excepción, continuamos con el archivo recortado
        else:
            # Eliminar el archivo original después del recorte
            try:
                os.remove(downloaded_filepath)
                print(f'DEBUG: Archivo original completo eliminado tras el recorte: {downloaded_filepath}')
            except OSError as err:
                print(f'ADVERTENCIA: Error eliminando el archivo original: {err}')

        return clipped_filepath
    def _on_recode_mode_change(self, mode):
        """Muestra el panel de recodificación apropiado."""
        self.recode_quick_frame.pack_forget()
        self.recode_manual_frame.pack_forget()
        self.save_preset_frame.pack_forget()
        if hasattr(self, 'recode_extract_frame'):
            self.recode_extract_frame.pack_forget()
        if mode == 'Modo Rápido':
            self.recode_quick_frame.pack(side='top', fill='x', padx=10, pady=0)
        else:
            if mode == 'Modo Manual':
                self.recode_manual_frame.pack(side='top', fill='x', padx=0, pady=0)
            else:
                if mode == 'Extras':
                    self.recode_extract_frame.pack(side='top', fill='x', padx=10, pady=0)
                    main_mode = self.mode_selector.get()
                    if main_mode == 'Solo Audio':
                        self.upscale_video_checkbox.deselect()
                        self.upscale_video_checkbox.configure(state='disabled')
                        self.extract_frames_checkbox.deselect()
                        self.extract_frames_checkbox.configure(state='disabled')
                        self.upscale_video_subpanel.grid_remove()
                        self.extract_frames_subpanel.grid_remove()
        self.update_download_button_state()
        self._toggle_recode_panels()
        self._validate_recode_compatibility()
        self._update_save_preset_visibility()
    def _on_quick_recode_toggle(self):
        """\n        Muestra/oculta las opciones de recodificación en Modo Rápido\n        según si el checkbox está marcado\n        """
        if self.apply_quick_preset_checkbox.get() == 1:
            self.quick_recode_options_frame.pack(fill='x', padx=0, pady=0)
            if not self.local_file_path:
                self.keep_original_quick_checkbox.configure(state='normal')
            else:
                self.keep_original_quick_checkbox.select()
                self.keep_original_quick_checkbox.configure(state='disabled')
        else:
            self.quick_recode_options_frame.pack_forget()
            self.keep_original_quick_checkbox.configure(state='disabled')
        self.update_download_button_state()
        self.save_settings()
    def _populate_preset_menu(self):
        """\n        Lee los presets disponibles y los añade al menú desplegable del Modo Rápido,\n        filtrando por el modo principal seleccionado (Video+Audio vs Solo Audio).\n        """
        current_main_mode = self.mode_selector.get()
        compatible_presets = []
        for name, data in self.built_in_presets.items():
            if data.get('mode_compatibility') == current_main_mode:
                compatible_presets.append(name)
        custom_presets_found = False
        for preset in getattr(self, 'custom_presets', []):
            if preset.get('data', {}).get('mode_compatibility') == current_main_mode:
                if not custom_presets_found:
                    if compatible_presets:
                        compatible_presets.append('--- Mis Presets ---')
                    custom_presets_found = True
                compatible_presets.append(preset.get('name'))
        if compatible_presets:
            self.recode_preset_menu.configure(values=compatible_presets, state='normal')
            saved_preset = self.app.quick_preset_saved
            if saved_preset and saved_preset in compatible_presets:
                self.recode_preset_menu.set(saved_preset)
            else:
                self.recode_preset_menu.set(compatible_presets[0])
            self._update_export_button_state()
        else:
            self.recode_preset_menu.configure(values=['- No hay presets para este modo -'], state='disabled')
            self.recode_preset_menu.set('- No hay presets para este modo -')
            self.export_preset_button.configure(state='disabled')
    def _update_export_button_state(self):
        """\n        Habilita/desahabilita los botones de exportar y eliminar según si el preset es personalizado\n        """
        selected_preset = self.recode_preset_menu.get()
        is_custom = any((p['name'] == selected_preset for p in self.custom_presets))
        if is_custom:
            self.export_preset_button.configure(state='normal')
            self.delete_preset_button.configure(state='normal')
        else:
            self.export_preset_button.configure(state='disabled')
            self.delete_preset_button.configure(state='disabled')
    def _find_preset_params(self, preset_name):
        """\n        Busca un preset por su nombre, primero en los personalizados y luego en los integrados.\n        Devuelve el diccionario de parámetros si lo encuentra.\n        """
        # ***<module>.SingleDownloadTab._find_preset_params: Failure: Different control flow
        for preset in getattr(self, 'custom_presets', []):
            return preset.get('data', {}) if preset.get('name') == preset_name else None
        if preset_name in self.built_in_presets:
            return self.built_in_presets[preset_name]
        else:
            return {}
    def time_str_to_seconds(self, time_str):
        """Convierte un string HH:MM:SS a segundos."""
        if not time_str:
            return
        else:
            parts = time_str.split(':')
            seconds = 0
            if len(parts) == 3:
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                if len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                else:
                    if len(parts) == 1:
                        seconds = int(parts[0])
            return seconds
    def _get_compatible_audio_codecs(self, target_container):
        """\n        Devuelve una lista de nombres de códecs de audio amigables que son\n        compatibles con un contenedor específico.\n        """
        all_audio_codecs = self.ffmpeg_processor.available_encoders.get('CPU', {}).get('Audio', {})
        if not target_container or target_container == '-':
            return list(all_audio_codecs.keys()) or ['-']
        else:
            rules = self.app.COMPATIBILITY_RULES.get(target_container, {})
            allowed_ffmpeg_codecs = rules.get('audio', [])
            compatible_friendly_names = []
            for friendly_name, details in all_audio_codecs.items():
                ffmpeg_codec_name = next((key for key in details if key != 'container'), None)
                if ffmpeg_codec_name in allowed_ffmpeg_codecs:
                    compatible_friendly_names.append(friendly_name)
            return compatible_friendly_names if compatible_friendly_names else ['-']
    def _toggle_fragment_panel(self):
        """Muestra u oculta las opciones para cortar fragmentos."""
        if self.fragment_checkbox.get() == 1:
            self.fragment_options_frame.pack(fill='x', padx=10, pady=(0, 5))
            if hasattr(self, 'keep_full_subtitle_check'):
                if self.clean_subtitle_check.winfo_ismapped():
                    self.clean_subtitle_check.pack_forget()
                    was_mapped = True
                else:
                    was_mapped = False
                self.keep_full_subtitle_check.pack(padx=10, pady=(0, 5), anchor='w')
                if was_mapped:
                    self.clean_subtitle_check.pack(padx=10, pady=(0, 5), anchor='w')
        else:
            self.fragment_options_frame.pack_forget()
            if hasattr(self, 'keep_full_subtitle_check'):
                self.keep_full_subtitle_check.pack_forget()
                self.keep_full_subtitle_check.deselect()
    def _on_precise_clip_toggle(self):
        """\n        Si se activa Corte Preciso: Desactiva y bloquea Descarga Completa.\n        Si se desactiva: Desbloquea Descarga Completa.\n        """
        if self.precise_clip_check.get() == 1:
            self.force_full_download_check.deselect()
            self.force_full_download_check.configure(state='disabled')
        else:
            self.force_full_download_check.configure(state='normal')
    def _on_force_full_download_toggle(self):
        """\n        Si se activa Descarga Completa: Desactiva y bloquea Corte Preciso.\n        Si se desactiva: Desbloquea Corte Preciso.\n        """
        if self.force_full_download_check.get() == 1:
            self.precise_clip_check.deselect()
            self.precise_clip_check.configure(state='disabled')
        else:
            self.precise_clip_check.configure(state='normal')
    def _on_keep_original_clip_toggle(self):
        """\n        Si se activa Conservar Completo:\n        - Desactiva y bloquea \'Corte Preciso\' y \'Descarga Completa\'.\n        Si se desactiva:\n        - Desbloquea ambas opciones para que el usuario elija.\n        """
        if self.keep_original_on_clip_check.get() == 1:
            self.precise_clip_check.deselect()
            self.precise_clip_check.configure(state='disabled')
            self.force_full_download_check.deselect()
            self.force_full_download_check.configure(state='disabled')
        else:
            self.precise_clip_check.configure(state='normal')
            self.force_full_download_check.configure(state='normal')
    def _handle_time_input(self, event, widget, next_widget=None):
        """Valida la entrada de tiempo y salta al siguiente campo."""
        text = widget.get()
        cleaned_text = ''.join(filter(str.isdigit, text))
        final_text = cleaned_text[:2]
        if text != final_text:
            widget.delete(0, 'end')
            widget.insert(0, final_text)
        if len(final_text) == 2 and next_widget:
                next_widget.focus()
                next_widget.select_range(0, 'end')
    def _get_formatted_time(self, h_widget, m_widget, s_widget):
        """\n        Lee los campos de tiempo segmentados y los formatea como HH:MM:SS.\n        NUEVO: Retorna \"\" si todos los campos están vacíos (se interpreta como \"sin límite\").\n        """
        h = h_widget.get().strip()
        m = m_widget.get().strip()
        s = s_widget.get().strip()
        if not h and (not m) and (not s):
                    return ''
        h = h.zfill(2) if h else '00'
        m = m.zfill(2) if m else '00'
        s = s.zfill(2) if s else '00'
        return f'{h}:{m}:{s}'
    def _clean_ansi_codes(self, text):
        """Elimina los códigos de escape ANSI (colores) del texto."""
        if not text:
            return ''
        else:
            ansi_escape = re.compile('\\x1B(?:[@-Z\\\\-_]|\\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text)
    def import_local_file(self):
        self.reset_to_url_mode()
        filetypes = [('Archivos de Video', '*.mp4 *.mkv *.mov *.avi *.webm'), ('Archivos de Audio', '*.mp3 *.wav *.m4a *.flac *.opus'), ('Todos los archivos', '*.*')]
        filepath = filedialog.askopenfilename(title='Selecciona un archivo para recodificar', filetypes=filetypes)
        self.app.lift()
        self.app.focus_force()
        if filepath:
            self.auto_save_thumbnail_check.pack_forget()
            self.cancellation_event.clear()
            self.progress_label.configure(text=f'Analizando archivo local: {os.path.basename(filepath)}...')
            self.progress_bar.start()
            self.open_folder_button.configure(state='disabled')
            threading.Thread(target=self._process_local_file_info, args=(filepath,), daemon=True).start()
    def import_local_file_from_path(self, filepath):
        """\n        Importa un archivo local directamente sin abrir diálogo.\n        Usado por la integración con Adobe.\n        """
        if not os.path.exists(filepath):
            return
        else:
            self.reset_to_url_mode()
            self.auto_save_thumbnail_check.pack_forget()
            self.cancellation_event.clear()
            self.progress_label.configure(text=f'Analizando archivo local: {os.path.basename(filepath)}...')
            self.progress_bar.start()
            self.open_folder_button.configure(state='disabled')
            threading.Thread(target=self._process_local_file_info, args=(filepath,), daemon=True).start()
    def _process_local_file_info(self, filepath):
        info = self.ffmpeg_processor.get_local_media_info(filepath)
        def update_ui():
            self.keep_original_on_clip_check.configure(state='disabled')
            self.progress_bar.stop()
            if not info:
                self.progress_label.configure(text='Error: No se pudo analizar el archivo.')
                self.progress_bar.set(0)
                return
            else:
                self.reset_ui_for_local_file()
                self.local_file_path = filepath
                self.keep_original_checkbox.select()
                self.keep_original_checkbox.configure(state='disabled')
                self.keep_original_quick_checkbox.select()
                self.keep_original_quick_checkbox.configure(state='disabled')
                self.precise_clip_check.deselect()
                self.precise_clip_check.configure(state='disabled')
                self.force_full_download_check.deselect()
                self.force_full_download_check.configure(state='disabled')
                if hasattr(self, 'keep_original_extract_checkbox'):
                    self.keep_original_extract_checkbox.select()
                    self.keep_original_extract_checkbox.configure(state='disabled')
                self.recode_main_frame._parent_canvas.yview_moveto(0)
                self.save_in_same_folder_check.pack(padx=10, pady=(5, 0), anchor='w')
                self.save_in_same_folder_check.select()
                video_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), None)
                audio_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'audio'), None)
                if video_stream:
                    self.original_video_width = video_stream.get('width', 0)
                    self.original_video_height = video_stream.get('height', 0)
                else:
                    self.original_video_width = 0
                    self.original_video_height = 0
                raw_title = os.path.splitext(os.path.basename(filepath))[0]
                clean_title = self.app.sanitize_title_global(raw_title)
                self.title_entry.insert(0, clean_title)
                self.video_duration = float(info.get('format', {}).get('duration', 0))
                if video_stream:
                    self.mode_selector.set('Video+Audio')
                    self.on_mode_change('Video+Audio')
                    frame_path = self.ffmpeg_processor.get_frame_from_video(filepath)
                    if frame_path:
                        self.load_thumbnail(frame_path, is_local=True)
                    v_codec = video_stream.get('codec_name', 'N/A').upper()
                    v_profile = video_stream.get('profile', 'N/A')
                    v_level = video_stream.get('level')
                    full_profile = f'{v_profile}@L{v_level / 10.0}' if v_level else v_profile
                    v_resolution = f"{video_stream.get('width', '?')}x{video_stream.get('height', '?')}"
                    v_fps = self._format_fps(video_stream.get('r_frame_rate'))
                    v_bitrate = self._format_bitrate(video_stream.get('bit_rate'))
                    v_pix_fmt = video_stream.get('pix_fmt', 'N/A')
                    bit_depth = '10-bit' if any((x in v_pix_fmt for x in ['p10', '10le'])) else '8-bit'
                    color_range = video_stream.get('color_range', '').capitalize()
                    v_label = f'{v_resolution} | {v_codec} ({full_profile}) @ {v_fps} fps | {v_bitrate} | {v_pix_fmt} ({bit_depth}, {color_range})'
                    _, ext_with_dot = os.path.splitext(filepath)
                    ext = ext_with_dot.lstrip('.')
                    self.video_formats = {v_label: {'format_id': 'local_video', 'index': video_stream.get('index', 0), 'width': self.original_video_width, 'height': self.original_video_height, 'vcodec': v_codec, 'ext': ext}}
                    self.video_quality_menu.configure(values=[v_label], state='normal')
                    self.video_quality_menu.set(v_label)
                    self.on_video_quality_change(v_label)
                    audio_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'audio']
                    audio_labels = []
                    self.audio_formats = {}
                    if not audio_streams:
                        self.audio_formats = {'-': {}}
                        self.audio_quality_menu.configure(values=['-'], state='disabled')
                    else:
                        for stream in audio_streams:
                            idx = stream.get('index', '?')
                            title = stream.get('tags', {}).get('title', f'Pista de Audio {idx}')
                            is_default = stream.get('disposition', {}).get('default', 0) == 1
                            default_str = ' (Default)' if is_default else ''
                            a_codec = stream.get('codec_name', 'N/A').upper()
                            a_profile = stream.get('profile', 'N/A')
                            a_channels_num = stream.get('channels', '?')
                            a_channel_layout = stream.get('channel_layout', 'N/A')
                            a_channels = f'{a_channels_num} Canales ({a_channel_layout})'
                            a_sample_rate = f"{int(stream.get('sample_rate', 0)) / 1000:.1f} kHz"
                            a_bitrate = self._format_bitrate(stream.get('bit_rate'))
                            a_label = f'{title}{default_str}: {a_codec} ({a_profile}) | {a_sample_rate} | {a_channels} | {a_bitrate}'
                            audio_labels.append(a_label)
                            self.audio_formats[a_label] = {'format_id': f'local_audio_{idx}', 'acodec': stream.get('codec_name', 'N/A')}
                        self.audio_quality_menu.configure(values=audio_labels, state='normal')
                        default_selection = next((label for label in audio_labels if '(Default)' in label), audio_labels[0])
                        self.audio_quality_menu.set(default_selection)
                        if hasattr(self, 'use_all_audio_tracks_check'):
                            if len(audio_labels) > 1:
                                self.use_all_audio_tracks_check.pack(padx=5, pady=(5, 0), anchor='w')
                                self.use_all_audio_tracks_check.deselect()
                            else:
                                self.use_all_audio_tracks_check.pack_forget()
                            self.audio_quality_menu.configure(state='normal')
                    self._update_warnings()
                else:
                    if audio_stream:
                        self.mode_selector.set('Solo Audio')
                        self.on_mode_change('Solo Audio')
                        self.create_placeholder_label('🎵')
                        a_codec = audio_stream.get('codec_name', 'N/A')
                        a_label = f'Audio Original ({a_codec})'
                        self.audio_formats = {a_label: {'format_id': 'local_audio', 'acodec': a_codec}}
                        self.audio_quality_menu.configure(values=[a_label], state='normal')
                        self.audio_quality_menu.set(a_label)
                        self._update_warnings()
                if self.cpu_radio.cget('state') == 'normal':
                    self.proc_type_var.set('CPU')
                    self.update_codec_menu()
                self.progress_label.configure(text=f'Listo para recodificar: {os.path.basename(filepath)}')
                self.progress_bar.set(1)
                self.update_download_button_state()
                self.download_button.configure(text='Iniciar Proceso', fg_color=self.PROCESS_BTN_COLOR, hover_color=self.PROCESS_BTN_HOVER)
                self.update_estimated_size()
                self._validate_recode_compatibility()
                self._on_save_in_same_folder_change()
        self.app.after(0, update_ui)
    def _format_bitrate(self, bitrate_str):
        """Convierte un bitrate en string a un formato legible (kbps o Mbps)."""
        if not bitrate_str:
            return 'Bitrate N/A'
        else:
            try:
                bitrate = int(bitrate_str)
                if bitrate > 1000000:
                    return f'{bitrate / 1000000:.2f} Mbps'
                else:
                    if bitrate > 1000:
                        return f'{bitrate / 1000:.0f} kbps'
                    else:
                        return f'{bitrate} bps'
            except (ValueError, TypeError):
                return 'Bitrate N/A'
    def _format_fps(self, fps_str):
        """Convierte una fracción de FPS (ej: '30000/1001') a un número decimal."""
        if not fps_str or '/' not in fps_str:
            return fps_str or 'FPS N/A'

        try:
            num, den = map(int, fps_str.split('/'))
            if den == 0:
                return 'FPS N/A'
            return f'{num / den:.2f}'
        except (ValueError, TypeError):
            return 'FPS N/A'
    def reset_ui_for_local_file(self):
        self.title_entry.delete(0, 'end')
        self.video_formats, self.audio_formats = ({}, {})
        self.video_quality_menu.configure(values=['-'], state='disabled')
        self.audio_quality_menu.configure(values=['-'], state='disabled')
        self._clear_subtitle_menus()
        self.clear_local_file_button.pack(fill='x', padx=10, pady=(0, 10))
    def reset_to_url_mode(self):
        self.keep_original_on_clip_check.configure(state='normal')
        self.precise_clip_check.configure(state='normal')
        self.force_full_download_check.configure(state='normal')
        self.local_file_path = None
        self.url_entry.configure(state='normal')
        self.analyze_button.configure(state='normal')
        self.url_entry.delete(0, 'end')
        self.title_entry.delete(0, 'end')
        self.create_placeholder_label('Miniatura')
        self.auto_save_thumbnail_check.pack(padx=10, pady=(0, 5), anchor='w')
        self.auto_save_thumbnail_check.configure(state='normal')
        self.video_formats, self.audio_formats = ({}, {})
        self.video_quality_menu.configure(values=['-'], state='disabled')
        self.audio_quality_menu.configure(values=['-'], state='disabled')
        self.progress_label.configure(text='Esperando...')
        self.progress_bar.set(0)
        self._clear_subtitle_menus()
        self.save_in_same_folder_check.pack_forget()
        self.download_button.configure(text=self.original_download_text, fg_color=self.DOWNLOAD_BTN_COLOR)
        self.clear_local_file_button.pack_forget()
        self.auto_save_thumbnail_check.configure(state='normal')
        self.keep_original_checkbox.configure(state='normal')
        self.keep_original_quick_checkbox.configure(state='normal')
        if hasattr(self, 'keep_original_extract_checkbox'):
            self.keep_original_extract_checkbox.configure(state='normal')
        self.update_download_button_state()
        self.save_in_same_folder_check.deselect()
        self._on_save_in_same_folder_change()
        self.use_all_audio_tracks_check.pack_forget()
    def _execute_local_recode(self, options):
        """
        Función que gestiona el procesamiento de archivos locales, incluyendo recorte y/o recodificación.
        
        🆕 CORREGIDO: Ahora mantiene correctamente el sufijo "_fragmento" en todos los casos.
        """
        import os
        clipped_temp_file = None
        source_path = self.local_file_path
        is_fragment_mode = options.get('fragment_enabled') and (options.get('start_time') or options.get('end_time'))
        is_recode_mode = options.get('recode_video_enabled') or options.get('recode_audio_enabled')

        try:
            # --- Caso 1: Solo recorte (sin recodificación) ---
            if is_fragment_mode and not is_recode_mode:
                final_clipped_path = self._execute_fragment_clipping(
                    input_filepath=source_path,
                    start_time=options.get('start_time'),
                    end_time=options.get('end_time')
                )
                self.app.after(0, self.on_process_finished, True, 'Recorte completado.', final_clipped_path)
                return  # Salir después del recorte

            # --- Caso 2: Recorte + recodificación ---
            input_for_recode = source_path
            if is_fragment_mode and is_recode_mode:
                # Generar archivo temporal recortado
                clipped_temp_file = self._execute_fragment_clipping(
                    input_filepath=source_path,
                    start_time=options.get('start_time'),
                    end_time=options.get('end_time')
                )
                input_for_recode = clipped_temp_file

            # Determinar directorio de salida
            if self.save_in_same_folder_check.get() == 1:
                output_dir = os.path.dirname(source_path)
            else:
                output_dir = self.output_path_entry.get()

            # Construir nombre base
            base_filename = self.sanitize_filename(options['title'])
            if is_fragment_mode:
                base_filename += '_fragmento'
            base_filename += '_recoded'

            # Seleccionar flujos de audio y video
            selected_audio_stream_index = None
            if self.use_all_audio_tracks_check.get() == 1 and len(self.audio_formats) > 1:
                selected_audio_stream_index = 'all'
            else:
                selected_audio_info = self.audio_formats.get(self.audio_quality_menu.get(), {})
                if selected_audio_info.get('format_id', '').startswith('local_audio_'):
                    selected_audio_stream_index = int(selected_audio_info['format_id'].split('_')[-1])

            selected_video_label = self.video_quality_menu.get()
            selected_video_info = self.video_formats.get(selected_video_label, {})
            selected_video_stream_index = selected_video_info.get('index')

            options['selected_audio_stream_index'] = selected_audio_stream_index
            options['selected_video_stream_index'] = selected_video_stream_index

            # Calcular duración si hay fragmento
            if is_fragment_mode:
                start_seconds = self.time_str_to_seconds(options.get('start_time')) if options.get('start_time') else 0
                end_seconds = self.time_str_to_seconds(options.get('end_time')) if options.get('end_time') else self.video_duration
                options['duration'] = end_seconds - start_seconds
            else:
                options['duration'] = self.video_duration

            # Ejecutar recodificación
            final_output_path = self._execute_recode_master(
                input_file=input_for_recode,
                output_dir=output_dir,
                base_filename=base_filename,
                recode_options=options
            )

            self.app.after(0, self.on_process_finished, True, 'Proceso local completado.', final_output_path)

        except (UserCancelledError, Exception) as e:
            # Lanzar excepción personalizada para que la capture el llamador
            raise LocalRecodeFailedError(str(e))

        finally:
            # Limpiar archivo temporal de recorte
            if clipped_temp_file and os.path.exists(clipped_temp_file):
                try:
                    os.remove(clipped_temp_file)
                    print(f'DEBUG: Archivo de recorte temporal eliminado: {clipped_temp_file}')
                except OSError as err:
                    print(f'ADVERTENCIA: No se pudo eliminar el archivo de recorte temporal: {err}')
    def _on_save_in_same_folder_change(self):
        """\n        Actualiza el estado de la carpeta de salida según la casilla\n        \'Guardar en la misma carpeta\'.\n        """
        if self.save_in_same_folder_check.get() == 1 and self.local_file_path:
            output_dir = os.path.dirname(self.local_file_path)
            self.output_path_entry.configure(state='normal')
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, output_dir)
            self.output_path_entry.configure(state='disabled')
            self.select_folder_button.configure(state='disabled')
        else:
            self.output_path_entry.configure(state='normal')
            self.select_folder_button.configure(state='normal')
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, self.app.default_download_path)
        self.update_download_button_state()
    def toggle_resolution_panel(self):
        if self.resolution_checkbox.get() == 1:
            self.resolution_options_frame.grid()
            if hasattr(self, 'original_video_width') and self.original_video_width > 0 and (not self.width_entry.get()) and (not self.height_entry.get()):
                            self.width_entry.delete(0, 'end')
                            self.width_entry.insert(0, str(self.original_video_width))
                            self.height_entry.delete(0, 'end')
                            self.height_entry.insert(0, str(self.original_video_height))
                            if not self.aspect_ratio_lock.get():
                                self.aspect_ratio_lock.select()
                            try:
                                self.current_aspect_ratio = self.original_video_width / self.original_video_height
                            except (ValueError, ZeroDivisionError):
                                self.current_aspect_ratio = None
            self.on_resolution_preset_change(self.resolution_preset_menu.get())
        else:
            self.resolution_options_frame.grid_remove()
    def on_dimension_change(self, source):
        if not self.aspect_ratio_lock.get() or self.is_updating_dimension or (not self.current_aspect_ratio):
            return None
        else:
            try:
                self.is_updating_dimension = True
                if source == 'width':
                    current_width_str = self.width_entry.get()
                    if current_width_str:
                        new_width = int(current_width_str)
                        new_height = int(new_width / self.current_aspect_ratio)
                        self.height_entry.delete(0, 'end')
                        self.height_entry.insert(0, str(new_height))
                else:
                    if source == 'height':
                        current_height_str = self.height_entry.get()
                        if current_height_str:
                            new_height = int(current_height_str)
                            new_width = int(new_height * self.current_aspect_ratio)
                            self.width_entry.delete(0, 'end')
                            self.width_entry.insert(0, str(new_width))
            except (ValueError, ZeroDivisionError):
                pass
            finally:
                self.is_updating_dimension = False
    def on_aspect_lock_change(self):
        if self.aspect_ratio_lock.get():
            try:
                width_str = self.width_entry.get()
                height_str = self.height_entry.get()
                if width_str and height_str:
                    width = int(width_str)
                    height = int(height_str)
                    self.current_aspect_ratio = width / height
                else:
                    if hasattr(self, 'original_video_width') and self.original_video_width > 0:
                        self.current_aspect_ratio = self.original_video_width / self.original_video_height
                    else:
                        self.current_aspect_ratio = None
            except (ValueError, ZeroDivisionError, AttributeError):
                self.current_aspect_ratio = None
        else:
            self.current_aspect_ratio = None
    def on_resolution_preset_change(self, preset):
        # ***<module>.SingleDownloadTab.on_resolution_preset_change: Failure: Different control flow
        PRESET_RESOLUTIONS_16_9 = {'4K UHD': ('3840', '2160'), '2K QHD': ('2560', '1440'), '1080p Full HD': ('1920', '1080'), '720p HD': ('1280', '720'), '480p SD': ('854', '480')}
        if preset == 'Personalizado':
            self.resolution_manual_frame.grid()
            if not hasattr(self, 'original_video_width') or self.original_video_width > 0:
                    if not self.width_entry.get():
                        self.width_entry.delete(0, 'end')
                        self.width_entry.insert(0, str(self.original_video_width))
                        self.height_entry.delete(0, 'end')
                        self.height_entry.insert(0, str(self.original_video_height))
                    if self.aspect_ratio_lock.get():
                        try:
                            self.current_aspect_ratio = self.original_video_width / self.original_video_height
                        except (ValueError, ZeroDivisionError, AttributeError):
                            self.current_aspect_ratio = None
        else:
            if preset in PRESET_RESOLUTIONS_16_9:
                self.resolution_manual_frame.grid_remove()
                try:
                    width_str, height_str = PRESET_RESOLUTIONS_16_9[preset]
                    width, height = (int(width_str), int(height_str))
                    self.width_entry.delete(0, 'end')
                    self.width_entry.insert(0, width_str)
                    self.height_entry.delete(0, 'end')
                    self.height_entry.insert(0, height_str)
                    try:
                        self.current_aspect_ratio = width / height
                    except ZeroDivisionError:
                        self.current_aspect_ratio = None
                    else:
                        return
                except Exception as e:
                    print(f'Error al aplicar el preset de resolución: {e}')
                else:
                    return
            else:
                self.resolution_manual_frame.grid_remove()
    def toggle_audio_recode_panel(self):
        """Muestra u oculta el panel de opciones de recodificación de audio."""
        if self.recode_audio_checkbox.get() == 1:
            self.recode_audio_options_frame.pack(fill='x', padx=5, pady=5)
            self.update_audio_codec_menu()
        else:
            self.recode_audio_options_frame.pack_forget()
        self.update_recode_container_label()
    def update_audio_codec_menu(self):
        """Puebla el menú de códecs de audio, filtrando por compatibilidad con el contenedor de video."""
        target_container = self.recode_container_label.cget('text')
        compatible_codecs = self._get_compatible_audio_codecs(target_container)
        if not compatible_codecs:
            compatible_codecs = ['-']
        self.recode_audio_codec_menu.configure(values=compatible_codecs, state='normal' if compatible_codecs[0] != '-' else 'disabled')
        saved_codec = self.recode_settings.get('video_audio_codec')
        if saved_codec and saved_codec in compatible_codecs:
            self.recode_audio_codec_menu.set(saved_codec)
        else:
            if compatible_codecs:
                self.recode_audio_codec_menu.set(compatible_codecs[0])
        self.update_audio_profile_menu(self.recode_audio_codec_menu.get())
    def update_audio_profile_menu(self, selected_codec_name):
        """Puebla el menú de perfiles basado en el códec de audio seleccionado."""
        profiles = ['-']
        if selected_codec_name != '-':
            audio_codecs = self.ffmpeg_processor.available_encoders.get('CPU', {}).get('Audio', {})
            codec_data = audio_codecs.get(selected_codec_name)
            if codec_data:
                ffmpeg_codec_name = list(filter(lambda k: k != 'container', codec_data.keys()))[0]
                profiles = list(codec_data.get(ffmpeg_codec_name, {}).keys())
        self.recode_audio_profile_menu.configure(values=profiles, state='normal' if profiles[0] != '-' else 'disabled')
        saved_profile = self.recode_settings.get('video_audio_profile')
        if saved_profile and saved_profile in profiles:
            self.recode_audio_profile_menu.set(saved_profile)
        else:
            self.recode_audio_profile_menu.set(profiles[0])
        self._validate_recode_compatibility()
    def on_audio_selection_change(self, selection):
        """Se ejecuta al cambiar el códec o perfil de audio para verificar la compatibilidad."""
        self.update_audio_profile_menu(selection)
        self.update_recode_container_label()
        is_video_mode = self.mode_selector.get() == 'Video+Audio'
        video_codec = self.recode_codec_menu.get()
        audio_codec = self.recode_audio_codec_menu.get()
        incompatible = False
        if is_video_mode and 'ProRes' in video_codec or 'DNxH' in video_codec:
            if 'FLAC' in audio_codec or 'Opus' in audio_codec or 'Vorbis' in audio_codec:
                incompatible = True
        if incompatible:
            self.audio_compatibility_warning.grid()
        else:
            self.audio_compatibility_warning.grid_remove()
    def update_recode_container_label(self, *args):
        """\n        Determina y muestra el contenedor final, asegurando que en modo\n        Video+Audio siempre se use un contenedor de video.\n        """
        container = '-'
        mode = self.mode_selector.get()
        is_video_recode_on = self.recode_video_checkbox.get() == 1
        is_audio_recode_on = self.recode_audio_checkbox.get() == 1
        if mode == 'Video+Audio':
            if is_video_recode_on:
                proc_type = self.proc_type_var.get()
                if proc_type:
                    codec_name = self.recode_codec_menu.get()
                    available = self.ffmpeg_processor.available_encoders.get(proc_type, {}).get('Video', {})
                    if codec_name in available:
                        container = available[codec_name].get('container', '-')
            else:
                if is_audio_recode_on:
                    container = '.mp4'
        else:
            if mode == 'Solo Audio':
                if is_audio_recode_on:
                    codec_name = self.recode_audio_codec_menu.get()
                    available = self.ffmpeg_processor.available_encoders.get('CPU', {}).get('Audio', {})
                    if codec_name in available:
                        container = available[codec_name].get('container', '-')
        self.recode_container_label.configure(text=container)
    def _clear_subtitle_menus(self):
        """Restablece TODOS los controles de subtítulos a su estado inicial e inactivo."""
        self.subtitle_lang_menu.configure(state='disabled', values=['-'])
        self.subtitle_lang_menu.set('-')
        self.subtitle_type_menu.configure(state='disabled', values=['-'])
        self.subtitle_type_menu.set('-')
        self.save_subtitle_button.configure(state='disabled')
        self.auto_download_subtitle_check.configure(state='disabled')
        self.auto_download_subtitle_check.deselect()
        if hasattr(self, 'clean_subtitle_check'):
            if self.clean_subtitle_check.winfo_ismapped():
                self.clean_subtitle_check.pack_forget()
            self.clean_subtitle_check.deselect()
        self.all_subtitles = {}
        self.current_subtitle_map = {}
        self.selected_subtitle_info = None
    def on_profile_selection_change(self, profile):
        self.custom_bitrate_frame.grid_forget()
        self.custom_gif_frame.grid_remove()
        if 'Bitrate Personalizado' in profile:
            self.custom_bitrate_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5)
            if not self.custom_bitrate_entry.get():
                self.custom_bitrate_entry.insert(0, '8')
        else:
            if profile == 'Personalizado':
                if self.recode_codec_menu.get() == 'GIF (animado)':
                    self.custom_gif_frame.grid()
        self.update_estimated_size()
        self.save_settings()
        self._validate_recode_compatibility()
        self.update_audio_codec_menu()
    def update_download_button_state(self, *args):
        """
        Valida TODAS las condiciones necesarias y actualiza el estado del botón de descarga.
        Ahora es consciente del modo de recodificación (Rápido vs Manual).
        """
        try:
            # --- 1. Habilitar/deshabilitar botón de análisis según URL ---
            if self.url_entry.get().strip():
                self.analyze_button.configure(state='normal')
            else:
                self.analyze_button.configure(state='disabled')

            # --- 2. Variables de estado básicas ---
            current_recode_mode = self.recode_mode_selector.get()
            url_mode_ready = self.analysis_is_complete and bool(self.url_entry.get().strip())
            local_mode_ready = self.local_file_path is not None
            app_is_ready_for_action = url_mode_ready or local_mode_ready

            # --- 3. Validación de ruta de salida ---
            output_path_is_valid = bool(self.output_path_entry.get())
            if local_mode_ready and self.save_in_same_folder_check.get() == 1:
                output_path_is_valid = True

            # --- 4. Validación de tiempos (fragmento) ---
            times_are_valid = True
            self.time_warning_label.configure(text='')
            if self.fragment_checkbox.get() == 1 and self.video_duration > 0:
                start_str = self._get_formatted_time(self.start_h, self.start_m, self.start_s)
                end_str = self._get_formatted_time(self.end_h, self.end_m, self.end_s)

                if not start_str and not end_str:
                    times_are_valid = False
                    self.time_warning_label.configure(
                        text='⚠️ Debes especificar al menos un tiempo\n       (inicio o final)',
                        text_color='orange'
                    )
                else:
                    start_seconds = self.time_str_to_seconds(start_str) if start_str else 0
                    end_seconds = self.time_str_to_seconds(end_str) if end_str else self.video_duration

                    if start_seconds >= self.video_duration:
                        times_are_valid = False
                        self.time_warning_label.configure(
                            text=f'⚠️ El tiempo de inicio ({start_str}) supera la duración del video',
                            text_color='orange'
                        )
                    elif end_seconds > self.video_duration:
                        times_are_valid = False
                        self.time_warning_label.configure(
                            text=f'⚠️ El tiempo final ({end_str}) supera la duración del video',
                            text_color='orange'
                        )
                    elif start_str and end_str and start_seconds >= end_seconds:
                        times_are_valid = False
                        self.time_warning_label.configure(
                            text='⚠️ El tiempo de inicio debe ser menor que el final',
                            text_color='orange'
                        )

            # --- 5. Validación de configuración de recodificación ---
            recode_config_is_valid = True

            if current_recode_mode == 'Modo Rápido':
                if self.apply_quick_preset_checkbox.get() == 1:
                    selected_preset = self.recode_preset_menu.get()
                    if selected_preset.startswith('- ') or not selected_preset:
                        recode_config_is_valid = False

            elif current_recode_mode == 'Modo Manual':
                if self.recode_video_checkbox.get() == 1:
                    # Validar bitrate personalizado
                    bitrate_ok = True
                    if 'Bitrate Personalizado' in self.recode_profile_menu.get():
                        try:
                            value = float(self.custom_bitrate_entry.get())
                            if not 0 < value <= 200:
                                bitrate_ok = False
                        except (ValueError, TypeError):
                            bitrate_ok = False
                    if not self.proc_type_var.get() or not bitrate_ok:
                        recode_config_is_valid = False

            # --- 6. Verificar si hay una acción seleccionada para modo local ---
            action_is_selected_for_local_mode = True
            if local_mode_ready:
                if current_recode_mode == 'Modo Rápido':
                    is_recode_on = self.apply_quick_preset_checkbox.get() == 1
                elif current_recode_mode == 'Modo Manual':
                    is_recode_on = self.recode_video_checkbox.get() == 1 or self.recode_audio_checkbox.get() == 1
                elif current_recode_mode == 'Extras':
                    is_recode_on = self.upscale_video_checkbox.get() == 1 or self.extract_frames_checkbox.get() == 1
                else:
                    is_recode_on = False

                is_clip_on = self.fragment_checkbox.get() == 1

                if current_recode_mode in ['Extras', 'Modo Extraer']:
                    action_is_selected_for_local_mode = is_recode_on
                else:
                    if not is_recode_on and not is_clip_on:
                        action_is_selected_for_local_mode = False

            # --- 7. Verificar compatibilidad de recodificación ---
            recode_is_compatible = self.recode_compatibility_status in ['valid', 'warning']

            # --- 8. Decisión final ---
            if (app_is_ready_for_action and
                output_path_is_valid and
                times_are_valid and
                recode_config_is_valid and
                action_is_selected_for_local_mode and
                recode_is_compatible):
                button_color = self.PROCESS_BTN_COLOR if self.local_file_path else self.DOWNLOAD_BTN_COLOR
                hover_color = self.PROCESS_BTN_HOVER if self.local_file_path else self.DOWNLOAD_BTN_HOVER
                self.download_button.configure(
                    state='normal',
                    fg_color=button_color,
                    hover_color=hover_color
                )
            else:
                self.download_button.configure(
                    state='disabled',
                    fg_color=self.DISABLED_FG_COLOR
                )

            # --- 9. Actualizar tamaño estimado (si existe) ---
            self.update_estimated_size()

        except Exception as e:
            print(f'Error inesperado al actualizar estado del botón: {e}')
            self.download_button.configure(state='disabled')
    def update_estimated_size(self):
        """Actualiza la etiqueta con el tamaño estimado del archivo resultante."""
        try:
            duration_s = float(self.video_duration)
            bitrate_mbps = float(self.custom_bitrate_entry.get())
            if duration_s > 0 and bitrate_mbps > 0:
                estimated_mb = bitrate_mbps * duration_s / 8  # bitrate en Mbps, duración en segundos → MB
                size_str = f'~ {estimated_mb / 1024:.2f} GB' if estimated_mb >= 1024 else f'~ {estimated_mb:.1f} MB'
                self.estimated_size_label.configure(text=size_str)
            else:
                self.estimated_size_label.configure(text='N/A')
        except (ValueError, TypeError, AttributeError):
            # Si no se puede calcular o el widget no existe, mostrar N/A
            if hasattr(self, 'estimated_size_label'):
                self.estimated_size_label.configure(text='N/A')
    def save_settings(self, event=None):
        """ \n        Actualiza la configuración de la app principal (self.app).\n        La ventana principal se encargará de escribir el archivo JSON.\n        """
        # ***<module>.SingleDownloadTab.save_settings: Failure: Different control flow
        if hasattr(self, 'app') and self.is_initializing:
            return None
        else:
            if not hasattr(self, 'app'):
                return
            else:
                self.app.default_download_path = self.output_path_entry.get()
                self.app.custom_presets = getattr(self, 'custom_presets', [])
                self.app.apply_quick_preset_checkbox_state = self.apply_quick_preset_checkbox.get() == 1
                self.app.keep_original_quick_saved = self.keep_original_quick_checkbox.get() == 1
                self.app.quick_preset_saved = self.recode_preset_menu.get()
                mode = self.mode_selector.get()
                codec = self.recode_codec_menu.get()
                profile = self.recode_profile_menu.get()
                proc_type = self.proc_type_var.get()
                if proc_type:
                    self.app.recode_settings['proc_type'] = proc_type
                if codec != '-':
                    if mode == 'Video+Audio':
                        self.app.recode_settings['video_codec'] = codec
                    else:
                        self.app.recode_settings['audio_codec'] = codec
                if profile != '-':
                    if mode == 'Video+Audio':
                        self.app.recode_settings['video_profile'] = profile
                    else:
                        self.app.recode_settings['audio_profile'] = profile
                    if self.recode_audio_codec_menu.get() != '-':
                        self.app.recode_settings['video_audio_codec'] = self.recode_audio_codec_menu.get()
                    if self.recode_audio_profile_menu.get() != '-':
                        self.app.recode_settings['video_audio_profile'] = self.recode_audio_profile_menu.get()
                self.app.recode_settings['keep_original'] = self.keep_original_checkbox.get() == 1
                self.app.recode_settings['recode_video_enabled'] = self.recode_video_checkbox.get() == 1
                self.app.recode_settings['recode_audio_enabled'] = self.recode_audio_checkbox.get() == 1
    def _toggle_recode_panels(self):
        is_video_recode = self.recode_video_checkbox.get() == 1
        is_audio_recode = self.recode_audio_checkbox.get() == 1
        is_audio_only_mode = self.mode_selector.get() == 'Solo Audio'
        if self.local_file_path:
            self.keep_original_checkbox.select()
            self.keep_original_checkbox.configure(state='disabled')
        else:
            if is_video_recode or is_audio_recode:
                self.keep_original_checkbox.configure(state='normal')
            else:
                self.keep_original_checkbox.configure(state='disabled')
        if is_video_recode and (not is_audio_only_mode):
            if not self.recode_options_frame.winfo_ismapped():
                self.proc_type_var.set('')
                self.update_codec_menu()
        else:
            self.recode_options_frame.pack_forget()
        if is_audio_recode:
            if not self.recode_audio_options_frame.winfo_ismapped():
                self.update_audio_codec_menu()
        else:
            self.recode_audio_options_frame.pack_forget()
        self.recode_options_frame.pack_forget()
        self.recode_audio_options_frame.pack_forget()
        if is_video_recode and (not is_audio_only_mode):
                self.recode_options_frame.pack(side='top', fill='x', padx=5, pady=5)
        if is_audio_recode:
            self.recode_audio_options_frame.pack(side='top', fill='x', padx=5, pady=5)
        self._validate_recode_compatibility()
        self._update_save_preset_visibility()
    def _update_save_preset_visibility(self):
        """\n        Muestra/oculta el botón \'Guardar como ajuste\' según si hay opciones de recodificación activas\n        """
        is_video_recode = self.recode_video_checkbox.get() == 1
        is_audio_recode = self.recode_audio_checkbox.get() == 1
        mode = self.mode_selector.get()
        should_show = False
        if mode == 'Video+Audio':
            should_show = is_video_recode or is_audio_recode
        else:
            if mode == 'Solo Audio':
                should_show = is_audio_recode
        if should_show:
            self.save_preset_frame.pack(side='bottom', fill='x', padx=0, pady=(10, 0))
        else:
            self.save_preset_frame.pack_forget()
    def _validate_recode_compatibility(self):
        """Valida la compatibilidad de las opciones de recodificación y actualiza la UI."""
        self.recode_warning_frame.pack_forget()
        current_recode_mode = self.recode_mode_selector.get()
        if current_recode_mode == 'Modo Rápido':
            self.recode_compatibility_status = 'valid'
            self.update_download_button_state()
            return
        else:
            if current_recode_mode == 'Extras':
                self.recode_compatibility_status = 'valid'
                self.update_download_button_state()
                return
            else:
                mode = self.mode_selector.get()
                is_video_recode = self.recode_video_checkbox.get() == 1 and mode == 'Video+Audio'
                is_audio_recode = self.recode_audio_checkbox.get() == 1
                if not is_video_recode and (not is_audio_recode):
                    self.recode_compatibility_status = 'valid'
                    self.update_download_button_state()
                    return
                else:
                    def get_ffmpeg_codec_name(friendly_name, proc_type, category):
                        if not friendly_name or friendly_name == '-':
                            return None
                        else:
                            db = self.ffmpeg_processor.available_encoders.get(proc_type, {}).get(category, {})
                            codec_data = db.get(friendly_name)
                            if codec_data:
                                return next((key for key in codec_data if key != 'container'), None)
                            else:
                                return None
                    target_container = None
                    if is_video_recode:
                        proc_type = self.proc_type_var.get()
                        if proc_type:
                            available = self.ffmpeg_processor.available_encoders.get(proc_type, {}).get('Video', {})
                            target_container = available.get(self.recode_codec_menu.get(), {}).get('container')
                    else:
                        if is_audio_recode:
                            if mode == 'Video+Audio':
                                target_container = '.mp4'
                            else:
                                available = self.ffmpeg_processor.available_encoders.get('CPU', {}).get('Audio', {})
                                target_container = available.get(self.recode_audio_codec_menu.get(), {}).get('container')
                    if not target_container:
                        self.recode_compatibility_status = 'error'
                        self.update_download_button_state()
                        return
                    else:
                        self.recode_container_label.configure(text=target_container)
                        status, message = ('valid', f'✅ Combinación Válida. Contenedor final: {target_container}')
                        rules = self.app.COMPATIBILITY_RULES.get(target_container, {})
                        allowed_video = rules.get('video', [])
                        allowed_audio = rules.get('audio', [])
                        video_info = self.video_formats.get(self.video_quality_menu.get()) or {}
                        original_vcodec = (video_info.get('vcodec') or 'none').split('.')[0]
                        audio_info = self.audio_formats.get(self.audio_quality_menu.get()) or {}
                        original_acodec = (audio_info.get('acodec') or 'none').split('.')[0]
                        if mode == 'Video+Audio':
                            if is_video_recode:
                                proc_type = self.proc_type_var.get()
                                ffmpeg_vcodec = get_ffmpeg_codec_name(self.recode_codec_menu.get(), proc_type, 'Video')
                                if ffmpeg_vcodec and ffmpeg_vcodec not in allowed_video:
                                        status, message = ('error', f'❌ El códec de video ({self.recode_codec_menu.get()}) no es compatible con {target_container}.')
                            else:
                                if not allowed_video:
                                    status, message = ('error', f'❌ No se puede copiar video a un contenedor de solo audio ({target_container}).')
                                else:
                                    if original_vcodec not in allowed_video and original_vcodec != 'none':
                                            status, message = ('warning', f'⚠️ El video original ({original_vcodec}) no es estándar en {target_container}. Se recomienda recodificar.')
                        if status in ['valid', 'warning']:
                            is_pro_video_format = False
                            if is_video_recode:
                                codec_name = self.recode_codec_menu.get()
                                if 'ProRes' in codec_name or 'DNxH' in codec_name:
                                    is_pro_video_format = True
                            if is_pro_video_format and (not is_audio_recode) and (original_acodec in ['aac', 'mp3', 'opus', 'vorbis']):
                                status, message = ('error', f'❌ Incompatible: No se puede copiar audio {original_acodec.upper()} a un video {codec_name}. Debes recodificar el audio a un formato sin compresión (ej: WAV).')
                            else:
                                if is_audio_recode:
                                    ffmpeg_acodec = get_ffmpeg_codec_name(self.recode_audio_codec_menu.get(), 'CPU', 'Audio')
                                    if ffmpeg_acodec and ffmpeg_acodec not in allowed_audio:
                                            status, message = ('error', f'❌ El códec de audio ({self.recode_audio_codec_menu.get()}) no es compatible con {target_container}.')
                                else:
                                    if mode == 'Video+Audio':
                                        if original_acodec not in allowed_audio and original_acodec != 'none':
                                                status, message = ('warning', f'⚠️ El audio original ({original_acodec}) no es estándar en {target_container}. Se recomienda recodificar.')
                        self.recode_compatibility_status = status
                        if status == 'valid':
                            color = self.STATUS_SUCCESS
                            self.recode_warning_label.configure(text=message, text_color=color)
                        else:
                            color = self.STATUS_ERROR if status == 'error' else self.UPDATE_ALERT
                            self.recode_warning_label.configure(text=message, text_color=color)
                        self.recode_warning_frame.pack(after=self.recode_toggle_frame, pady=5, padx=10, fill='x')
                        if hasattr(self, 'use_all_audio_tracks_check') and self.use_all_audio_tracks_check.winfo_ismapped():
                                is_multi_track_available = len(self.audio_formats) > 1
                                if target_container in self.app.SINGLE_STREAM_AUDIO_CONTAINERS:
                                    self.use_all_audio_tracks_check.configure(state='disabled')
                                    self.use_all_audio_tracks_check.deselect()
                                    self.audio_quality_menu.configure(state='normal')
                                else:
                                    if is_multi_track_available:
                                        self.use_all_audio_tracks_check.configure(state='normal')
                        self.update_download_button_state()
    def toggle_fps_panel(self):
        """Muestra u oculta el panel de opciones de FPS."""
        if self.fps_checkbox.get() == 1:
            self.fps_options_frame.grid()
            self.fps_mode_var.set('CFR')
            self.toggle_fps_entry()
        else:
            self.fps_options_frame.grid_remove()
    def toggle_fps_entry_panel(self):
        if self.fps_checkbox.get() == 1:
            self.fps_value_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
            self.fps_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        else:
            self.fps_value_label.grid_remove()
            self.fps_entry.grid_remove()
    def update_codec_menu(self, *args):
        proc_type = self.proc_type_var.get()
        mode = self.mode_selector.get()
        codecs = ['-']
        is_recode_panel_visible = self.recode_options_frame.winfo_ismapped()
        if self.ffmpeg_processor.is_detection_complete and is_recode_panel_visible and proc_type:
                    category = 'Audio' if mode == 'Solo Audio' else 'Video'
                    effective_proc = 'CPU' if category == 'Audio' else proc_type
                    available = self.ffmpeg_processor.available_encoders.get(effective_proc, {}).get(category, {})
                    if available:
                        codecs = list(available.keys())
        self.recode_codec_menu.configure(values=codecs, state='normal' if codecs and codecs[0] != '-' else 'disabled')
        key = 'video_codec' if mode == 'Video+Audio' else 'audio_codec'
        saved_codec = self.recode_settings.get(key)
        if saved_codec and saved_codec in codecs:
            self.recode_codec_menu.set(saved_codec)
        else:
            self.recode_codec_menu.set(codecs[0])
        self.update_profile_menu(self.recode_codec_menu.get())
        self.update_download_button_state()
        self.save_settings()
    def update_profile_menu(self, selected_codec_name):
        proc_type = self.proc_type_var.get()
        mode = self.mode_selector.get()
        profiles = ['-']
        container = '-'
        if selected_codec_name != '-':
            category = 'Audio' if mode == 'Solo Audio' else 'Video'
            effective_proc = 'CPU' if category == 'Audio' else proc_type
            available_codecs = self.ffmpeg_processor.available_encoders.get(effective_proc, {}).get(category, {})
            if selected_codec_name in available_codecs:
                codec_data = available_codecs[selected_codec_name]
                ffmpeg_codec_name = list(codec_data.keys())[0]
                container = codec_data.get('container', '-')
                profile_data = codec_data.get(ffmpeg_codec_name, {})
                if profile_data:
                    profiles = list(profile_data.keys())
        self.recode_profile_menu.configure(values=profiles, state='normal' if profiles and profiles[0] != '-' else 'disabled', command=self.on_profile_selection_change)
        key = 'video_profile' if mode == 'Video+Audio' else 'audio_profile'
        saved_profile = self.recode_settings.get(key)
        if saved_profile and saved_profile in profiles:
            self.recode_profile_menu.set(saved_profile)
        else:
            self.recode_profile_menu.set(profiles[0])
        self.on_profile_selection_change(self.recode_profile_menu.get())
        self.recode_container_label.configure(text=container)
        if 'GIF (animado)' in selected_codec_name:
            self.recode_audio_checkbox.deselect()
            self.recode_audio_checkbox.configure(state='disabled')
            self.fps_checkbox.configure(state='disabled')
            self.fps_checkbox.deselect()
            self.resolution_checkbox.configure(state='disabled')
            self.resolution_checkbox.deselect()
        else:
            if self.has_audio_streams or self.local_file_path:
                self.recode_audio_checkbox.configure(state='normal')
            self.fps_checkbox.configure(state='normal')
            self.resolution_checkbox.configure(state='normal')
        self.toggle_fps_entry_panel()
        self.toggle_resolution_panel()
        self.update_download_button_state()
        self.save_settings()
    def update_tags_combobox(self):
        """Actualiza las opciones del menú de etiquetas."""
        tags = self.tags_manager.load_tags()
        tag_names = ['- Etiqueta -'] + list(tags.keys())
        self.tags_menu.configure(values=tag_names)
        current_selection = self.tags_menu.get()
        if current_selection not in tag_names:
            self.tags_menu.set('- Etiqueta -')
            self.on_tag_change('- Etiqueta -')
    def on_tag_change(self, value):
        """Se ejecuta al cambiar la etiqueta en el menú desplegable."""
        if value == '- Etiqueta -':
            self.output_path_entry.configure(state='normal')
            self.select_folder_button.configure(state='normal')
            self.output_path_entry.delete(0, 'end')
            if self.saved_manual_path:
                self.output_path_entry.insert(0, self.saved_manual_path)
            else:
                self.output_path_entry.insert(0, self.app.default_download_path)
            self.saved_manual_path = ''
        else:
            tag_path = self.tags_manager.get_tag_path(value)
            if tag_path:
                if not self.saved_manual_path:
                    self.saved_manual_path = self.output_path_entry.get()
                self.output_path_entry.configure(state='normal')
                self.output_path_entry.delete(0, 'end')
                self.output_path_entry.insert(0, tag_path)
                self.output_path_entry.configure(state='disabled')
                self.select_folder_button.configure(state='disabled')
    def on_mode_change(self, mode):
        print(f'DEBUG: on_mode_change llamado con mode={mode}')
        print(f'  - video_formats vacío: {not self.video_formats}')
        print(f'  - audio_formats vacío: {not self.audio_formats}')
        print(f'  - local_file_path: {self.local_file_path}')
        print(f'  - recode_main_frame empaquetado: {self.recode_main_frame.winfo_ismapped()}')
        if not self.video_formats and (not self.audio_formats) and (not self.local_file_path):
            print('DEBUG: on_mode_change llamado pero formatos no están listos aún (modo URL)')
            return
        else:
            print('DEBUG: ✅ CONTINUANDO con on_mode_change')
            self.format_warning_label.pack_forget()
            self.video_quality_label.pack_forget()
            self.video_quality_menu.pack_forget()
            if hasattr(self, 'audio_options_frame'):
                self.audio_options_frame.pack_forget()
            self.recode_video_checkbox.deselect()
            self.recode_audio_checkbox.deselect()
            self.proc_type_var.set('')
            if mode == 'Video+Audio':
                self.video_quality_label.pack(fill='x', padx=5, pady=(10, 0))
                self.video_quality_menu.pack(fill='x', padx=5, pady=(0, 5))
                if hasattr(self, 'audio_options_frame'):
                    self.audio_options_frame.pack(fill='x')
                self.format_warning_label.pack(fill='x', padx=5, pady=(5, 5))
                self.recode_video_checkbox.grid()
                self.recode_audio_checkbox.configure(text='Recodificar Audio')
                self.upscale_video_checkbox.configure(state='normal')
                self.extract_frames_checkbox.configure(state='normal')
                if not self.local_file_path:
                    self.on_video_quality_change(self.video_quality_menu.get())
            else:
                if mode == 'Solo Audio':
                    self.upscale_video_checkbox.deselect()
                    self.upscale_video_checkbox.configure(state='disabled')
                    self.extract_frames_checkbox.deselect()
                    self.extract_frames_checkbox.configure(state='disabled')
                    self.upscale_video_subpanel.grid_remove()
                    self.extract_frames_subpanel.grid_remove()
                    print('DEBUG: Cambiando a modo Solo Audio')
                    has_any_audio = bool(self.audio_formats) or any((v.get('is_combined', False) for v in self.video_formats.values()))
                    if not has_any_audio:
                        print('⚠️ ERROR: No hay audio disponible en este video')
                        self.audio_quality_menu.configure(state='disabled', values=['⚠️ Este video no tiene audio'])
                        self.audio_quality_menu.set('⚠️ Este video no tiene audio')
                        self.combined_audio_map = {}
                        self.download_button.configure(state='disabled')
                    else:
                        if self.audio_formats:
                            print('DEBUG: Hay pistas de audio dedicadas disponibles')
                        else:
                            print('DEBUG: No hay pistas dedicadas. Extrayendo audio de formatos combinados')
                            audio_from_combined = []
                            seen_configs = set()
                            for video_label, video_info in self.video_formats.items():
                                if video_info.get('is_combined', False):
                                    acodec = video_info.get('acodec', 'unknown').split('.')[0]
                                    format_id = video_info.get('format_id')
                                    config_key = f'{acodec}_{format_id}'
                                    if config_key not in seen_configs:
                                        seen_configs.add(config_key)
                                        label = f"Audio desde {video_label.split('(')[0].strip()} ({acodec})"
                                        audio_from_combined.append({'label': label, 'format_id': format_id, 'acodec': acodec})
                            if audio_from_combined:
                                audio_options = [entry['label'] for entry in audio_from_combined]
                                self.combined_audio_map = {entry['label']: entry['format_id'] for entry in audio_from_combined}
                                self.audio_quality_menu.configure(state='normal', values=audio_options)
                                self.audio_quality_menu.set(audio_options[0])
                            else:
                                self.audio_quality_menu.configure(state='disabled', values=['- Sin Audio -'])
                                self.combined_audio_map = {}
                    if hasattr(self, 'audio_options_frame'):
                        self.audio_options_frame.pack(fill='x')
                    self.format_warning_label.pack(fill='x', padx=5, pady=(5, 5))
                    self.recode_video_checkbox.grid_remove()
                    self.recode_audio_checkbox.configure(text='Activar Recodificación para Audio')
                    self._update_warnings()
            self.recode_main_frame._parent_canvas.yview_moveto(0)
            self.recode_main_frame.pack_forget()
            self.recode_main_frame.pack(pady=(10, 0), padx=5, fill='both', expand=True)
            self._toggle_recode_panels()
            self.update_codec_menu()
            self.update_audio_codec_menu()
            self._populate_preset_menu()
            self._update_save_preset_visibility()
    def _on_use_all_audio_tracks_change(self):
        """Gestiona el estado del menú de audio cuando el checkbox cambia."""
        if self.use_all_audio_tracks_check.get() == 1:
            self.audio_quality_menu.configure(state='disabled')
        else:
            self.audio_quality_menu.configure(state='normal')
    def on_video_quality_change(self, selected_label):
        selected_format_info = self.video_formats.get(selected_label)
        if selected_format_info:
            is_combined = selected_format_info.get('is_combined', False)
            quality_key = selected_format_info.get('quality_key')
            if is_combined and quality_key and (quality_key in self.combined_variants):
                variants = self.combined_variants[quality_key]
                unique_languages = set()
                for variant in variants:
                    lang = variant.get('language', '')
                    if lang:
                        unique_languages.add(lang)
                if len(unique_languages) >= 2:
                    audio_language_options = []
                    self.combined_audio_map = {}
                    for variant in variants:
                        lang_code = variant.get('language')
                        format_id = variant.get('format_id')
                        if lang_code:
                            norm_code = lang_code.replace('_', '-').lower()
                            lang_name = self.app.LANG_CODE_MAP.get(norm_code, self.app.LANG_CODE_MAP.get(norm_code.split('-')[0], lang_code))
                        else:
                            continue
                        abr = variant.get('abr') or variant.get('tbr')
                        acodec = variant.get('acodec', 'unknown').split('.')[0]
                        label = f'{lang_name} - {abr:.0f}kbps ({acodec})' if abr else f'{lang_name} ({acodec})'
                        if label not in self.combined_audio_map:
                            audio_language_options.append(label)
                            self.combined_audio_map[label] = format_id
                    if not audio_language_options:
                        self.audio_quality_menu.configure(state='disabled')
                        self.combined_audio_map = {}
                        print('DEBUG: No hay idiomas válidos en las variantes combinadas')
                    else:
                        def sort_by_lang_priority(label):
                            for variant in variants:
                                if self.combined_audio_map.get(label) == variant.get('format_id'):
                                    lang_code = variant.get('language', '')
                                    norm_code = lang_code.replace('_', '-').lower()
                                    return self.app.LANGUAGE_ORDER.get(norm_code, self.app.LANGUAGE_ORDER.get(norm_code.split('-')[0], self.app.DEFAULT_PRIORITY))
                            return self.app.DEFAULT_PRIORITY
                        audio_language_options.sort(key=sort_by_lang_priority)
                        default_lang_selection = audio_language_options[0]
                        original_video_lang = getattr(self, 'original_video_language', None)
                        for label in audio_language_options:
                            f_id = self.combined_audio_map.get(label)
                            for variant in variants:
                                if variant.get('format_id') == f_id:
                                    note = (variant.get('format_note') or '').lower()
                                    v_lang = variant.get('language')
                                    if 'original' in note:
                                        default_lang_selection = label
                                        print(f'DEBUG: [Multiidioma] Pre-seleccionando idioma ORIGINAL (por nota): {label}')
                                        break
                                    else:
                                        if original_video_lang and v_lang and (v_lang.startswith(original_video_lang) or original_video_lang.startswith(v_lang)):
                                                    default_lang_selection = label
                                                    print(f'DEBUG: [Multiidioma] Pre-seleccionando idioma ORIGINAL (por metadato global): {label}')
                                                    break
                            if default_lang_selection == label:
                                break
                        self.audio_quality_menu.configure(state='normal', values=audio_language_options)
                        self.audio_quality_menu.set(default_lang_selection)
                        print(f'DEBUG: Menú de audio llenado con {len(audio_language_options)} idiomas. Seleccionado: {default_lang_selection}')
                else:
                    self.audio_quality_menu.configure(state='disabled')
                    self.combined_audio_map = {}
                    print(f'DEBUG: Combinado de un solo idioma detectado (quality_key: {quality_key})')
            else:
                print('DEBUG: No es combinado multiidioma, restaurando menú de audio normal')
                self.combined_audio_map = {}
                a_opts = list(self.audio_formats.keys()) or ['- Sin Pistas de Audio -']
                current_audio_selection = self.audio_quality_menu.get()
                default_audio_selection = a_opts[0]
                for option in a_opts:
                    if '✨' in option:
                        default_audio_selection = option
                        break
                selection_to_set = default_audio_selection
                if current_audio_selection in a_opts:
                    selection_to_set = current_audio_selection
                self.audio_quality_menu.configure(state='normal' if self.audio_formats else 'disabled', values=a_opts)
                self.audio_quality_menu.set(selection_to_set)
            new_width = selected_format_info.get('width')
            new_height = selected_format_info.get('height')
            if new_width and new_height and hasattr(self, 'width_entry'):
                        self.width_entry.delete(0, 'end')
                        self.width_entry.insert(0, str(new_width))
                        self.height_entry.delete(0, 'end')
                        self.height_entry.insert(0, str(new_height))
                        if self.aspect_ratio_lock.get():
                            self.on_aspect_lock_change()
        self._update_warnings()
        self._validate_recode_compatibility()
    def _update_warnings(self):
        mode = self.mode_selector.get()
        warnings = []
        compatibility_issues = []
        unknown_issues = []
        if mode == 'Video+Audio':
            video_info = self.video_formats.get(self.video_quality_menu.get())
            audio_info = self.audio_formats.get(self.audio_quality_menu.get())
            if not video_info or not audio_info:
                return None
            else:
                virtual_format = {'vcodec': video_info.get('vcodec'), 'acodec': audio_info.get('acodec'), 'ext': video_info.get('ext')}
                compatibility_issues, unknown_issues = self._get_format_compatibility_issues(virtual_format)
                if 'Lento' in self.video_quality_menu.get():
                    warnings.append('• Formato de video lento para recodificar.')
        else:
            if mode == 'Solo Audio':
                audio_info = self.audio_formats.get(self.audio_quality_menu.get())
                if not audio_info:
                    return
                else:
                    virtual_format = {'acodec': audio_info.get('acodec')}
                    compatibility_issues, unknown_issues = self._get_format_compatibility_issues(virtual_format)
                    if audio_info.get('acodec') == 'none':
                        unknown_issues.append('audio')
        if compatibility_issues:
            issues_str = ', '.join(compatibility_issues)
            warnings.append(f'• Requiere recodificación por códec de {issues_str}.')
        if unknown_issues:
            issues_str = ', '.join(unknown_issues)
            warnings.append(f'• Compatibilidad desconocida para el códec de {issues_str}.')
        if warnings:
            self.format_warning_label.configure(text='\n'.join(warnings), text_color=self.UPDATE_ALERT)
        else:
            legend_text = 'Guía de etiquetas en la lista:\n✨ Ideal: Formato óptimo para editar sin conversión.\n⚠️ Recodificar: Formato no compatible con editores.'
            self.format_warning_label.configure(text=legend_text, text_color=self.SECTION_SUBTITLE)
    def _get_format_compatibility_issues(self, format_dict):
        if not format_dict:
            return ([], [])
        else:
            compatibility_issues = []
            unknown_issues = []
            raw_vcodec = format_dict.get('vcodec')
            vcodec = raw_vcodec.split('.')[0] if raw_vcodec else 'none'
            raw_acodec = format_dict.get('acodec')
            acodec = raw_acodec.split('.')[0] if raw_acodec else 'none'
            ext = format_dict.get('ext') or 'none'
            if vcodec == 'none' and 'vcodec' in format_dict:
                unknown_issues.append('video')
            else:
                if vcodec != 'none' and vcodec not in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_vcodecs']:
                        compatibility_issues.append(f'video ({vcodec})')
            if acodec != 'none' and acodec not in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_acodecs']:
                    compatibility_issues.append(f'audio ({acodec})')
            if vcodec != 'none' and ext not in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_exts']:
                    compatibility_issues.append(f'contenedor (.{ext})')
            return (compatibility_issues, unknown_issues)
    def _initialize_presets_file(self):
        """
        Inicializa el archivo presets.json si no existe.
        Si ya existe, lo deja como está.
        """
        import os
        import json

        presets_file = self.app.PRESETS_FILE

        if not os.path.exists(presets_file):
            print('DEBUG: Archivo presets.json no encontrado. Creando con presets por defecto...')

            # Define default presets with a valid dictionary structure
            default_presets = {
                "Calidad Media (CRF 23)": {
                    "mode_compatibility": "Video+Audio",
                    "recode_video_enabled": True,
                    "recode_audio_enabled": True,
                    "keep_original_file": "CPU",
                    "recode_proc": "H.265 (x265)",
                    "recode_codec_name": "Calidad Media (CRF 24)",
                    "recode_profile_name": "AAC",
                    "recode_audio_codec_name": "Buena Calidad (~192kbps)",
                    "recode_audio_profile_name": ".mp4"
                },
                "Archivo - H.265 Máxima": {
                    "mode_compatibility": "Video+Audio",
                    "recode_video_enabled": True,
                    "recode_audio_enabled": True,
                    "keep_original_file": "recode_proc",
                    "recode_codec_name": "recode_profile_name",
                    "recode_audio_codec_name": "CPU",
                    "recode_audio_profile_name": "H.265 (x265)",
                    "recode_container": ".mov"
                },
                "Web/Móvil - H.264 Máxima": {
                    "mode_compatibility": "Video+Audio",
                    "recode_video_enabled": True,
                    "recode_audio_enabled": True,
                    "keep_original_file": "CPU",
                    "recode_proc": "H.265 (x265)",
                    "recode_codec_name": "Alta Calidad (CRF 18)",
                    "recode_profile_name": "AAC",
                    "recode_audio_codec_name": "AAC"
                }
            }

            try:
                with open(presets_file, 'w', encoding='utf-8') as f:
                    json.dump(default_presets, f, indent=4, ensure_ascii=False)
                print(f'DEBUG: presets.json creado exitosamente en {presets_file}')
            except IOError as e:
                print(f'ERROR: No se pudo crear presets.json: {e}')
        else:
            print('DEBUG: presets.json ya existe. Cargando...')
    def _load_presets(self):
        """
        Carga los presets desde presets.json.
        Retorna un diccionario con built_in_presets y custom_presets.
        """
        import os
        import json

        presets_file = self.app.PRESETS_FILE
        default_return = {'built_in_presets': {}, 'custom_presets': []}

        if not os.path.exists(presets_file):
            print('ERROR: presets.json no encontrado')
            return default_return

        try:
            with open(presets_file, 'r', encoding='utf-8') as f:
                presets_data = json.load(f)
            # Ensure the loaded data has the expected structure
            if not isinstance(presets_data, dict):
                print('ERROR: presets.json no contiene un diccionario válido')
                return default_return
            # Optionally, you can merge with defaults if missing keys
            return presets_data
        except (json.JSONDecodeError, IOError) as e:
            print(f'ERROR: No se pudo cargar presets.json: {e}')
            return default_return
    def open_save_preset_dialog(self):
        """Abre el diálogo para guardar un preset personalizado."""
        dialog = SavePresetDialog(self.app)
        self.app.wait_window(dialog)
        if dialog.result:
            self._save_custom_preset(dialog.result)
    def export_preset_file(self):
        """\n        Exporta el preset seleccionado como archivo .dowp_preset\n        """
        selected_preset_name = self.recode_preset_menu.get()
        if selected_preset_name.startswith('- ') or not selected_preset_name:
            Tooltip.hide_all()
            messagebox.showwarning('Selecciona un preset', 'Por favor, selecciona un preset para exportar.')
            return
        else:
            preset_data = None
            for custom_preset in self.custom_presets:
                if custom_preset['name'] == selected_preset_name:
                    preset_data = custom_preset['data']
                    break
            if preset_data is None:
                Tooltip.hide_all()
                messagebox.showwarning('No se puede exportar', 'Solo puedes exportar presets personalizados.\nLos presets integrados no se pueden exportar.')
                return
            else:
                preset_content = self._create_preset_file_content(preset_data, selected_preset_name)
                file_path = filedialog.asksaveasfilename(defaultextension='.dowp_preset', filetypes=[('DowP Preset', '*.dowp_preset'), ('JSON', '*.json'), ('All Files', '*.*')], initialfile=f'{selected_preset_name}.dowp_preset')
                self.app.lift()
                self.app.focus_force()
                if file_path:
                    try:
                        with open(file_path, 'w') as f:
                            json.dump(preset_content, f, indent=4)
                        Tooltip.hide_all()
                        messagebox.showinfo('Exportado', f'El preset \'{selected_preset_name}\' ha sido exportado exitosamente.\n\nUbicación: {file_path}')
                        print(f'DEBUG: Preset exportado: {file_path}')
                    except Exception as e:
                        Tooltip.hide_all()
                        messagebox.showerror('Error al exportar', f'No se pudo exportar el preset:\n{e}')
                        print(f'ERROR al exportar preset: {e}')
    def import_preset_file(self):
        """
        Importa un archivo .dowp_preset y lo agrega a presets personalizados
        """
        from tkinter import filedialog, messagebox
        import json
        import os

        # Ask user for file
        file_path = filedialog.askopenfilename(
            filetypes=[('DowP Preset', '*.dowp_preset'), ('JSON', '*.json'), ('All Files', '*.*')],
            title='Selecciona un archivo .dowp_preset para importar'
        )
        self.app.lift()
        self.app.focus_force()
        if not file_path:
            return

        # Read and parse JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                preset_content = json.load(f)
        except json.JSONDecodeError:
            Tooltip.hide_all()
            messagebox.showerror('Error', 'El archivo no es un JSON válido.')
            return
        except Exception as e:
            Tooltip.hide_all()
            messagebox.showerror('Error al importar', f'No se pudo leer el archivo:\n{e}')
            return

        # Validate structure
        if not self._validate_preset_file(preset_content):
            Tooltip.hide_all()
            messagebox.showerror('Archivo inválido', 'El archivo no es un preset válido o está corrupto.')
            return

        preset_name = preset_content.get('preset_name', 'Sin nombre')
        preset_data = preset_content.get('data')

        # Check for duplicate
        existing_preset = next((p for p in self.custom_presets if p['name'] == preset_name), None)
        if existing_preset:
            Tooltip.hide_all()
            result = messagebox.askyesno(
                'Preset duplicado',
                f'El preset \'{preset_name}\' ya existe.\n¿Deseas sobrescribirlo?'
            )
            if not result:
                return
            # Remove existing
            self.custom_presets = [p for p in self.custom_presets if p['name'] != preset_name]

        # Add new preset
        self.custom_presets.append({'name': preset_name, 'data': preset_data})

        # Save to file
        try:
            presets_data = self._load_presets()
            presets_data['custom_presets'] = self.custom_presets
            with open(self.app.PRESETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(presets_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            Tooltip.hide_all()
            messagebox.showerror('Error al guardar', f'No se pudo guardar el preset:\n{e}')
            return

        # Refresh menus
        self._populate_preset_menu()
        if hasattr(self.app, 'batch_tab'):
            self.app.batch_tab._populate_batch_preset_menu()
            self.app.batch_tab._populate_global_preset_menu()

        Tooltip.hide_all()
        messagebox.showinfo(
            'Importado',
            f'El preset \'{preset_name}\' ha sido importado exitosamente.\nAhora está disponible en Modo Rápido.'
        )
        print(f'DEBUG: Preset importado: {preset_name}')
    def delete_preset_file(self):
        """\n        Elimina el preset personalizado seleccionado\n        """
        selected_preset_name = self.recode_preset_menu.get()
        if selected_preset_name.startswith('- ') or not selected_preset_name:
            Tooltip.hide_all()
            messagebox.showwarning('Selecciona un preset', 'Por favor, selecciona un preset para eliminar.')
            return
        else:
            is_custom = any((p['name'] == selected_preset_name for p in self.custom_presets))
            if not is_custom:
                Tooltip.hide_all()
                messagebox.showwarning('No se puede eliminar', 'Solo puedes eliminar presets personalizados.\nLos presets integrados no se pueden eliminar.')
                return
            else:
                Tooltip.hide_all()
                result = messagebox.askyesno('Confirmar eliminación', f'¿Estás seguro de que deseas eliminar el preset \'{selected_preset_name}\'?\n\nEsta acción no se puede deshacer.')
                if not result:
                    return
                else:
                    try:
                        self.custom_presets = [p for p in self.custom_presets if p['name'] != selected_preset_name]
                        presets_data = self._load_presets()
                        presets_data['custom_presets'] = self.custom_presets
                        with open(self.app.PRESETS_FILE, 'w') as f:
                            json.dump(presets_data, f, indent=4)
                        self._populate_preset_menu()
                        self.app.batch_tab._populate_batch_preset_menu()
                        self.app.batch_tab._populate_global_preset_menu()
                        Tooltip.hide_all()
                        messagebox.showinfo('Eliminado', f'El preset \'{selected_preset_name}\' ha sido eliminado exitosamente.')
                        print(f'DEBUG: Preset eliminado: {selected_preset_name}')
                    except Exception as e:
                        Tooltip.hide_all()
                        messagebox.showerror('Error al eliminar', f'No se pudo eliminar el preset:\n{e}')
                        print(f'ERROR al eliminar preset: {e}')
    def _save_custom_preset(self, preset_name):
        """
        Guarda la configuración actual como un preset personalizado en presets.json
        """
        from tkinter import messagebox
        import json
        import os

        # --- 1. Recopilar datos del preset actual ---
        # Obtener el contenedor desde la etiqueta (si es '-', usar '.mp4' por defecto)
        recode_container_val = self.recode_container_label.cget('text')
        if recode_container_val == '-':
            recode_container_val = '.mp4'

        # Construir el diccionario de datos (completo y con nombres de clave consistentes)
        current_preset_data = {
            'mode_compatibility': self.mode_selector.get(),
            'recode_video_enabled': self.recode_video_checkbox.get() == 1,
            'recode_audio_enabled': self.recode_audio_checkbox.get() == 1,
            'keep_original_file': self.keep_original_checkbox.get() == 1,
            'recode_proc': self.proc_type_var.get(),
            'recode_codec_name': self.recode_codec_menu.get(),
            'recode_profile_name': self.recode_profile_menu.get(),
            'custom_bitrate_value': self.custom_bitrate_entry.get(),
            'custom_gif_fps': self.custom_gif_fps_entry.get(),
            'custom_gif_width': self.custom_gif_width_entry.get(),  # asumiendo que es Entry
            'recode_container': recode_container_val,  # corregido: usar la variable local
            'recode_audio_codec_name': self.recode_audio_codec_menu.get(),
            'recode_audio_profile_name': self.recode_audio_profile_menu.get(),
            'fps_force_enabled': self.fps_checkbox.get() == 1,
            'fps_value': self.fps_entry.get(),
            'resolution_change_enabled': self.resolution_checkbox.get() == 1,
            'res_width': self.width_entry.get(),
            'res_height': self.height_entry.get()   # clave corregida (antes 'width_entry')
        }

        # --- 2. Cargar presets existentes ---
        try:
            presets_data = self._load_presets()
        except Exception as e:
            messagebox.showerror('Error', f'No se pudieron cargar los presets:\n{e}')
            return

        # --- 3. Verificar si el nombre ya existe en built-in ---
        if preset_name in presets_data.get('built_in_presets', {}):
            messagebox.showerror(
                'Nombre duplicado',
                f'El nombre \'{preset_name}\' ya existe en los presets integrados.\nPor favor, usa otro nombre.'
            )
            return

        # --- 4. Verificar si ya existe en custom y preguntar sobrescritura ---
        existing_preset = next((p for p in presets_data.get('custom_presets', []) if p['name'] == preset_name), None)
        if existing_preset:
            result = messagebox.askyesno(
                'Preset ya existe',
                f'El preset \'{preset_name}\' ya existe.\n¿Deseas sobrescribirlo?'
            )
            if not result:
                return  # Usuario cancela
            # Eliminar el existente
            presets_data['custom_presets'] = [p for p in presets_data['custom_presets'] if p['name'] != preset_name]

        # --- 5. Agregar el nuevo preset ---
        presets_data.setdefault('custom_presets', []).append({
            'name': preset_name,
            'data': current_preset_data
        })

        # --- 6. Guardar en el archivo ---
        try:
            with open(self.app.PRESETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(presets_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror('Error al guardar', f'No se pudo guardar el ajuste:\n{e}')
            return

        # --- 7. Actualizar atributos y menús ---
        self.built_in_presets = presets_data.get('built_in_presets', {})
        self.custom_presets = presets_data.get('custom_presets', [])
        self._populate_preset_menu()

        # Actualizar menús en batch_tab si existe
        if hasattr(self.app, 'batch_tab'):
            self.app.batch_tab._populate_batch_preset_menu()
            self.app.batch_tab._populate_global_preset_menu()

        # --- 8. Notificar éxito ---
        messagebox.showinfo(
            'Éxito',
            f'El ajuste \'{preset_name}\' ha sido guardado.\nAhora está disponible en Modo Rápido.'
        )
        print(f'DEBUG: Preset personalizado \'{preset_name}\' guardado exitosamente.')
    def _create_preset_file_content(self, preset_data, preset_name):
        """\n        Crea el contenido de un archivo .dowp_preset con validación.\n        Retorna un diccionario que será guardado como JSON.\n        """
        import hashlib
        preset_content = {'preset_name': preset_name, 'preset_version': '1.0', 'data': preset_data}
        content_string = json.dumps(preset_data, sort_keys=True)
        checksum = hashlib.sha256(content_string.encode()).hexdigest()
        preset_content['checksum'] = checksum
        return preset_content
    def _validate_preset_file(self, preset_content):
        """\n        Valida la integridad de un archivo .dowp_preset.\n        Retorna True si es válido, False si no.\n        """
        import hashlib
        if not isinstance(preset_content, dict):
            print('ERROR: El archivo no es un preset válido (no es diccionario)')
            return False
        else:
            if 'checksum' not in preset_content or 'data' not in preset_content:
                print('ERROR: El preset no tiene estructura válida')
                return False
            else:
                stored_checksum = preset_content.get('checksum')
                preset_data = preset_content.get('data')
                content_string = json.dumps(preset_data, sort_keys=True)
                calculated_checksum = hashlib.sha256(content_string.encode()).hexdigest()
                if stored_checksum != calculated_checksum:
                    print('ERROR: El checksum no coincide (archivo corrupto o modificado)')
                    return False
                else:
                    return True
    def sanitize_filename(self, filename):
        """\n        Sanitización completa con doble límite (caracteres + bytes).\n        \n        Límites:\n        - 150 caracteres (límite visual/UX)\n        - 220 bytes UTF-8 (límite técnico filesystem)\n        \n        Compatible con todos los idiomas y sistemas modernos.\n        """
        import unicodedata
        original_filename = filename
        filename = unicodedata.normalize('NFC', filename)
        filename = ''.join((char for char in filename if unicodedata.category(char)[0] != 'C'))
        forbidden_chars = '[\\\\/:\\*\\?\"<>|]'
        filename = re.sub(forbidden_chars, '', filename)
        filename = re.sub('\\s+', ' ', filename).strip()
        filename = filename.rstrip('. ')
        max_chars = 150
        if len(filename) > max_chars:
            filename = filename[:max_chars]
            filename = filename.rstrip('. ')
            print(f'ℹ️ Título truncado de {len(original_filename)} a {max_chars} caracteres')
        max_bytes = 220
        if len(filename.encode('utf-8')) > max_bytes:
            filename_bytes = filename.encode('utf-8')[:max_bytes]
            filename = filename_bytes.decode('utf-8', errors='ignore')
            filename = filename.rstrip('. ')
            print(f"ℹ️ Título truncado de {len(filename.encode('utf-8'))} a {max_bytes} bytes")
        if not filename or filename.strip() == '':
            filename = 'video_descargado'
            print('⚠️ Título vacío después de sanitización. Usando fallback.')
        if filename != original_filename:
            print('📝 Nombre ajustado:')
            print(f"   Original: {original_filename[:100]}{('...' if len(original_filename) > 100 else '')}")
            print(f'   Final: {filename}')
        return filename
    def create_placeholder_label(self, text='Miniatura', font_size=14):
        """Crea el placeholder de miniatura"""
        if self.thumbnail_label:
            self.thumbnail_label.destroy()
        if hasattr(self, '_original_image_backup'):
            self._original_image_backup = None
        if hasattr(self, '_hover_text_label') and self._hover_text_label is not None:
                try:
                    if self._hover_text_label.winfo_exists():
                        self._hover_text_label.destroy()
                except:
                    pass
                self._hover_text_label = None
        font = ctk.CTkFont(size=font_size)
        self.thumbnail_label = ctk.CTkLabel(self.dnd_overlay, text=text, font=font)
        self.thumbnail_label.pack(expand=True, fill='both')
        self.pil_image = None
        if hasattr(self, 'save_thumbnail_button'):
            self.save_thumbnail_button.configure(state='disabled')
        if hasattr(self, 'send_thumbnail_to_imagetools_button'):
            self.send_thumbnail_to_imagetools_button.configure(state='disabled')
        if hasattr(self, 'auto_save_thumbnail_check'):
            self.auto_save_thumbnail_check.deselect()
            self.auto_save_thumbnail_check.configure(state='normal')
        self.dnd_overlay.lift()
    def toggle_manual_thumbnail_button(self):
        is_checked = self.auto_save_thumbnail_check.get() == 1
        has_image = self.pil_image is not None
        if is_checked or not has_image:
            self.save_thumbnail_button.configure(state='disabled')
            if hasattr(self, 'send_thumbnail_to_imagetools_button'):
                self.send_thumbnail_to_imagetools_button.configure(state='disabled')
        else:
            self.save_thumbnail_button.configure(state='normal')
            if hasattr(self, 'send_thumbnail_to_imagetools_button'):
                self.send_thumbnail_to_imagetools_button.configure(state='normal')
    def toggle_manual_subtitle_button(self):
        """Activa/desactiva el botón \'Descargar Subtítulos\'."""
        is_auto_download = self.auto_download_subtitle_check.get() == 1
        has_valid_subtitle_selected = hasattr(self, 'selected_subtitle_info') and self.selected_subtitle_info is not None
        if is_auto_download or not has_valid_subtitle_selected:
            self.save_subtitle_button.configure(state='disabled')
        else:
            self.save_subtitle_button.configure(state='normal')
    def on_language_change(self, selected_language_name):
        """Se ejecuta cuando el usuario selecciona un idioma. Pobla el segundo menú."""
        possible_codes = [code for code, name in self.app.LANG_CODE_MAP.items() if name == selected_language_name]
        actual_lang_code = None
        for code in possible_codes:
            primary_part = code.split('-')[0].lower()
            if primary_part in self.all_subtitles:
                actual_lang_code = primary_part
                break
        if not actual_lang_code:
            actual_lang_code = possible_codes[0].split('-')[0].lower() if possible_codes else selected_language_name
        sub_list = self.all_subtitles.get(actual_lang_code, [])
        filtered_subs = []
        added_types = set()
        for sub_info in sub_list:
            ext = sub_info.get('ext')
            is_auto = sub_info.get('automatic', False)
            sub_type_key = (is_auto, ext)
            if sub_type_key in added_types:
                continue
            else:
                filtered_subs.append(sub_info)
                added_types.add(sub_type_key)
        def custom_type_sort_key(sub_info):
            is_auto = 1 if sub_info.get('automatic', False) else 0
            is_srt = 0 if sub_info.get('ext') == 'srt' else 1
            return (is_auto, is_srt)
        sorted_subs = sorted(filtered_subs, key=custom_type_sort_key)
        type_display_names = []
        self.current_subtitle_map = {}
        for sub_info in sorted_subs:
            origin = 'Automático' if sub_info.get('automatic') else 'Manual'
            ext = sub_info.get('ext', 'N/A')
            full_lang_code = sub_info.get('lang', '')
            display_name = self._get_subtitle_display_name(full_lang_code)
            label = f'{origin} (.{ext}) - {display_name}'
            type_display_names.append(label)
            self.current_subtitle_map[label] = sub_info
        if type_display_names:
            self.subtitle_type_menu.configure(state='normal', values=type_display_names)
            self.subtitle_type_menu.set(type_display_names[0])
            self.on_subtitle_selection_change(type_display_names[0])
        else:
            self.subtitle_type_menu.configure(state='disabled', values=['-'])
            self.subtitle_type_menu.set('-')
        self.toggle_manual_subtitle_button()
    def _get_subtitle_display_name(self, lang_code):
        """Obtiene un nombre legible para un código de idioma de subtítulo, simple o compuesto."""
        parts = lang_code.split('-')
        if len(parts) == 1:
            return self.app.LANG_CODE_MAP.get(lang_code, lang_code)
        else:
            if self.app.LANG_CODE_MAP.get(lang_code):
                return self.app.LANG_CODE_MAP.get(lang_code)
            else:
                original_lang = self.app.LANG_CODE_MAP.get(parts[0], parts[0])
                translated_part = '-'.join(parts[1:])
                translated_lang = self.app.LANG_CODE_MAP.get(translated_part, translated_part)
                return f'{original_lang} (Trad. a {translated_lang})'
    def on_subtitle_selection_change(self, selected_type):
        """\n        Se ejecuta cuando el usuario selecciona un tipo/formato de subtítulo.\n        CORREGIDO: Ahora muestra la opción de conversión para CUALQUIER formato que no sea SRT.\n        """
        self.selected_subtitle_info = self.current_subtitle_map.get(selected_type)
        should_show_option = False
        if self.selected_subtitle_info:
            subtitle_ext = self.selected_subtitle_info.get('ext')
            if subtitle_ext != 'srt':
                should_show_option = True
        is_visible = self.clean_subtitle_check.winfo_ismapped()
        if should_show_option:
            if not is_visible:
                self.clean_subtitle_check.pack(padx=10, pady=(0, 5), anchor='w')
        else:
            if is_visible:
                self.clean_subtitle_check.pack_forget()
            self.clean_subtitle_check.deselect()
        print(f'Subtítulo seleccionado final: {self.selected_subtitle_info}')
        self.toggle_manual_subtitle_button()
        self.save_settings()
    def select_output_folder(self):
        folder_path = filedialog.askdirectory()
        self.app.lift()
        self.app.focus_force()
        if folder_path:
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, folder_path)
            self.app.default_download_path = folder_path
            self.save_settings()
            self.update_download_button_state()
    def open_last_download_folder(self):
        """Abre la carpeta contenedora del último resultado (archivo o carpeta)."""
        if not self.last_download_path or not os.path.exists(self.last_download_path):
            print('ERROR: No hay una ruta válida para mostrar.')
            return
        else:
            path = os.path.normpath(self.last_download_path)
            if os.path.isdir(path):
                folder_to_open = os.path.dirname(path)
                print(f'DEBUG: Abriendo carpeta contenedora de: {path}')
            else:
                folder_to_open = path
                print(f'DEBUG: Abriendo carpeta y seleccionando archivo: {path}')
            try:
                system = platform.system()
                if system == 'Windows':
                    if os.path.isdir(path):
                        subprocess.Popen(['explorer', folder_to_open])
                    else:
                        subprocess.Popen(['explorer', '/select,', path])
                else:
                    if system == 'Darwin':
                        if os.path.isdir(path):
                            subprocess.Popen(['open', folder_to_open])
                        else:
                            subprocess.Popen(['open', '-R', path])
                    else:
                        subprocess.Popen(['xdg-open', folder_to_open if os.path.isdir(path) else os.path.dirname(path)])
            except Exception as e:
                print(f'Error al abrir carpeta: {e}')
    def save_thumbnail(self):
        if not self.pil_image:
            return
        else:
            clean_title = self.sanitize_filename(self.title_entry.get() or 'miniatura')
            initial_dir = self.output_path_entry.get()
            if not os.path.isdir(initial_dir):
                initial_dir = self.default_download_path or str(Path.home() / 'Downloads')
            save_path = filedialog.asksaveasfilename(initialdir=initial_dir, initialfile=f'{clean_title}.jpg', defaultextension='.jpg', filetypes=[('JPEG Image', '*.jpg'), ('PNG Image', '*.png')])
            if save_path:
                try:
                    if save_path.lower().endswith(('.jpg', '.jpeg')):
                        self.pil_image.convert('RGB').save(save_path, quality=95)
                    else:
                        self.pil_image.save(save_path)
                    self.on_process_finished(True, f'Miniatura guardada en {os.path.basename(save_path)}', save_path)
                except Exception as e:
                    self.on_process_finished(False, f'Error al guardar miniatura: {e}', None)
    def _execute_subtitle_download_subprocess(self, url, subtitle_info, save_path, cut_options=None):
        try:
            output_dir = os.path.dirname(save_path)
            files_before = set(os.listdir(output_dir))
            lang_code = subtitle_info['lang']
            output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
            command = ['yt-dlp', '--no-warnings', '--write-sub', '--sub-langs', lang_code, '--skip-download', '--no-playlist', '-o', output_template]
            should_convert_to_srt = self.clean_subtitle_check.winfo_ismapped() and self.clean_subtitle_check.get() == 1
            if should_convert_to_srt:
                command.extend(['--sub-format', 'best/vtt/best'])
                command.extend(['--convert-subs', 'srt'])
            else:
                command.extend(['--sub-format', subtitle_info['ext']])
            if subtitle_info.get('automatic', False):
                command.append('--write-auto-sub')
            cookie_mode = self.app.cookies_mode_saved
            if cookie_mode == 'Archivo Manual...' and self.app.cookies_path:
                command.extend(['--cookies', self.app.cookies_path])
            else:
                if cookie_mode != 'No usar':
                    browser_arg = self.app.selected_browser_saved
                    profile = self.app.browser_profile_saved
                    if profile:
                        browser_arg += f':{profile}'
                    command.extend(['--cookies-from-browser', browser_arg])
            command.extend(['--ffmpeg-location', self.ffmpeg_processor.ffmpeg_path])
            command.append(url)
            self.app.after(0, self.update_progress, 0, 'Iniciando proceso de yt-dlp...')
            print(f"\n\nDEBUG: Comando final enviado a yt-dlp:\n{' '.join(command)}\n\n")
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', creationflags=creationflags)
            stdout_lines = []
            stderr_lines = []
            def read_stream(stream, lines_buffer):
                for line in iter(stream.readline, ''):
                    lines_buffer.append(line.strip())
            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines))
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines))
            stdout_thread.start()
            stderr_thread.start()
            stdout_thread.join()
            stderr_thread.join()
            process.wait()
            print('--- [yt-dlp finished] ---\n')
            if process.returncode != 0:
                full_error_output = '\n'.join(stdout_lines) + '\n' + '\n'.join(stderr_lines)
                raise Exception(f'El proceso de yt-dlp falló:\n{full_error_output}')
            else:
                files_after = set(os.listdir(output_dir))
                new_files = files_after - files_before
                if not new_files:
                    raise FileNotFoundError('yt-dlp terminó, pero no se detectó ningún archivo de subtítulo nuevo.')
                else:
                    subtitle_extensions = {'.ssa', '.vtt', '.ass', '.srt'}
                    new_subtitle_files = [f for f in new_files if os.path.splitext(f)[1].lower() in subtitle_extensions]
                    if not new_subtitle_files:
                        raise FileNotFoundError(f'yt-dlp descargó archivos, pero ninguno es un subtítulo. Archivos nuevos: {new_files}')
                    else:
                        new_filename = new_subtitle_files[0]
                        downloaded_subtitle_path = os.path.join(output_dir, new_filename)
                        print(f'DEBUG: Subtítulo descargado: {downloaded_subtitle_path}')
                        downloaded_name = os.path.basename(downloaded_subtitle_path)
                        downloaded_ext = os.path.splitext(downloaded_name)[1]
                        user_chosen_name = os.path.splitext(os.path.basename(save_path))[0]
                        final_filename = f'{user_chosen_name}.{lang_code}{downloaded_ext}'
                        final_output_path = os.path.join(output_dir, final_filename)
                        if downloaded_subtitle_path != final_output_path:
                            if os.path.exists(final_output_path):
                                os.remove(final_output_path)
                            os.rename(downloaded_subtitle_path, final_output_path)
                            print(f'DEBUG: Subtítulo renombrado a: {final_output_path}')
                        if final_output_path.lower().endswith('.srt'):
                            self.app.after(0, self.update_progress, 90, 'Limpiando y estandarizando formato SRT...')
                            final_output_path = clean_and_convert_vtt_to_srt(final_output_path)
                            print(f'DEBUG: Subtítulo limpiado: {final_output_path}')
                        if cut_options and cut_options['enabled'] and (not cut_options['keep_full']):
                                    start_t = cut_options['start']
                                    end_t = cut_options['end']
                                    if start_t or end_t:
                                        print(f'DEBUG: ✂️ Cortando subtítulo manual ({start_t} - {end_t})')
                                        self.app.after(0, self.update_progress, 99, 'Recortando subtítulo...')
                                        cut_sub_path = os.path.splitext(final_output_path)[0] + '_cut.srt'
                                        success_cut = slice_subtitle(self.ffmpeg_processor.ffmpeg_path, final_output_path, cut_sub_path, start_time=start_t or '00:00:00', end_time=end_t)
                                        if success_cut and os.path.exists(cut_sub_path):
                                                try:
                                                    os.remove(final_output_path)
                                                    os.rename(cut_sub_path, final_output_path)
                                                    print('DEBUG: ✅ Subtítulo manual cortado exitosamente.')
                                                except Exception as e:
                                                    print(f'ADVERTENCIA: No se pudo reemplazar el subtítulo cortado: {e}')
                        self.app.after(0, self.on_process_finished, True, f'Subtítulo guardado en {os.path.basename(final_output_path)}', final_output_path)
        except Exception as e:
            self.app.after(0, self.on_process_finished, False, f'Error al descargar subtítulo: {e}', None)
    def save_subtitle(self):
        """\n        Guarda el subtítulo seleccionado, aplicando recorte si es necesario.\n        """
        subtitle_info = self.selected_subtitle_info
        if not subtitle_info:
            self.update_progress(0, 'Error: No hay subtítulo seleccionado.')
            return
        else:
            subtitle_ext = subtitle_info.get('ext', 'txt')
            clean_title = self.sanitize_filename(self.title_entry.get() or 'subtitle')
            initial_filename = f'{clean_title}.{subtitle_ext}'
            save_path = filedialog.asksaveasfilename(defaultextension=f'.{subtitle_ext}', filetypes=[(f'{subtitle_ext.upper()} Subtitle', f'*.{subtitle_ext}'), ('All files', '*.*')], initialfile=initial_filename)
            if save_path:
                video_url = self.url_entry.get()
                cut_options = {'enabled': self.fragment_checkbox.get() == 1, 'start': self._get_formatted_time(self.start_h, self.start_m, self.start_s), 'end': self._get_formatted_time(self.end_h, self.end_m, self.end_s), 'keep_full': getattr(self, 'keep_full_subtitle_check', None) and self.keep_full_subtitle_check.get() == 1}
                self.download_button.configure(state='disabled')
                self.analyze_button.configure(state='disabled')
                threading.Thread(target=self._execute_subtitle_download_subprocess, args=(video_url, subtitle_info, save_path, cut_options), daemon=True).start()
    def cancel_operation(self):
        """\n        Maneja la cancelación de cualquier operación activa.\n        Mata procesos huérfanos de FFmpeg para liberar a yt-dlp inmediatamente.\n        """
        print('DEBUG: Botón de Cancelar presionado.')
        self.cancellation_event.set()
        self.ffmpeg_processor.cancel_current_process()
        if os.name == 'nt':
            try:
                print('DEBUG: Intentando matar procesos FFmpeg externos (yt-dlp)...')
                subprocess.run(['taskkill', '/F', '/IM', 'ffmpeg.exe', '/T'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=134217728)
            except Exception as e:
                print(f'ADVERTENCIA: No se pudieron matar procesos FFmpeg externos: {e}')
        if self.active_subprocess_pid:
            print(f'DEBUG: Intentando terminar el árbol de procesos para el PID: {self.active_subprocess_pid}')
            try:
                subprocess.run(['taskkill', '/PID', str(self.active_subprocess_pid), '/T', '/F'], check=True, capture_output=True, text=True, creationflags=134217728)
                print(f'DEBUG: Proceso {self.active_subprocess_pid} terminado.')
                time.sleep(1.0)
                gc.collect()
            except Exception as e:
                print(f'ADVERTENCIA: Falló taskkill por PID: {e}')
            self.active_subprocess_pid = None
    def start_download_thread(self):
            url = self.url_entry.get()
            output_path = self.output_path_entry.get()
            has_input = url or self.local_file_path
            has_output = output_path
            
            if not has_input or not has_output:
                error_msg = "Error: Falta la carpeta de salida."
                if not has_input:
                    error_msg = "Error: No se ha proporcionado una URL ni se ha importado un archivo."
                self.progress_label.configure(text=error_msg)
                return
            
            # 🆕 VALIDACIÓN: Verificar que hay audio si está en modo Solo Audio
            if self.mode_selector.get() == "Solo Audio":
                audio_label = self.audio_quality_menu.get()
                if "no tiene audio" in audio_label.lower() or audio_label == "-":
                    self.progress_label.configure(text="Error: Este video no tiene audio disponible.")
                    return
            # --- Preparación de UI (Ahora esconde AMBOS botones de resultado) ---
            self.download_button.configure(text="Cancelar", fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, command=self.cancel_operation)
            self.analyze_button.configure(state="disabled") 
            self.save_subtitle_button.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            self.send_to_imagetools_button.pack_forget() # <-- ESCONDER EL NUEVO BOTÓN
            
            self.cancellation_event.clear()
            self.progress_bar.set(0)
            self.update_progress(0, "Preparando proceso...")
            
            # --- Recolección de Opciones Base (Comunes) ---
            options = {
                "url": url, "output_path": output_path,
                "title": self.title_entry.get() or "video_descargado",
                "mode": self.mode_selector.get(),
                "video_format_label": self.video_quality_menu.get(),
                "audio_format_label": self.audio_quality_menu.get(),
                "recode_video_enabled": self.recode_video_checkbox.get() == 1,
                "recode_audio_enabled": self.recode_audio_checkbox.get() == 1,
                "keep_original_file": self.keep_original_checkbox.get() == 1,
                "recode_proc": self.proc_type_var.get(),
                "recode_codec_name": self.recode_codec_menu.get(),
                "recode_profile_name": self.recode_profile_menu.get(),
                "custom_bitrate_value": self.custom_bitrate_entry.get(),
                "custom_gif_fps": self.custom_gif_fps_entry.get() or "15",
                "custom_gif_width": self.custom_gif_width_entry.get() or "480",
                "recode_container": self.recode_container_label.cget("text"),
                "recode_audio_enabled": self.recode_audio_checkbox.get() == 1,
                "recode_audio_codec_name": self.recode_audio_codec_menu.get(),
                "recode_audio_profile_name": self.recode_audio_profile_menu.get(),
                "speed_limit": self.speed_limit_entry.get(),
                "cookie_mode": self.app.cookies_mode_saved,
                "cookie_path": self.app.cookies_path,
                "selected_browser": self.app.selected_browser_saved,
                "browser_profile": self.app.browser_profile_saved,
                "download_subtitles": self.auto_download_subtitle_check.get() == 1,
                "selected_subtitle_info": self.selected_subtitle_info,
                "fps_force_enabled": self.fps_checkbox.get() == 1,
                "fps_value": self.fps_entry.get(),
                "resolution_change_enabled": self.resolution_checkbox.get() == 1,
                "res_width": self.width_entry.get(),
                "res_height": self.height_entry.get(),
                "no_upscaling_enabled": self.no_upscaling_checkbox.get() == 1,
                "resolution_preset": self.resolution_preset_menu.get(),
                "original_width": self.original_video_width,
                "original_height": self.original_video_height,
                "fragment_enabled": self.fragment_checkbox.get() == 1,
                "start_time": self._get_formatted_time(self.start_h, self.start_m, self.start_s),
                "end_time": self._get_formatted_time(self.end_h, self.end_m, self.end_s),
                "precise_clip_enabled": self.precise_clip_check.get() == 1,
                "force_full_download": self.force_full_download_check.get() == 1,
                "keep_original_on_clip": self.keep_original_on_clip_check.get() == 1,
                "keep_full_subtitle": getattr(self, 'keep_full_subtitle_check', None) and self.keep_full_subtitle_check.get() == 1
            }
    
            # --- EL NUEVO "ROUTER" LÓGICO ---
            recode_mode = self.recode_mode_selector.get()
    
            if recode_mode == "Modo Rápido" or recode_mode == "Modo Manual":
                
                # --- Lógica de Recodificación (tu código existente) ---
                print("DEBUG: Iniciando Hilo de Recodificación/Descarga.")
                
                # Recolectar opciones de recodificación
                if recode_mode == "Modo Rápido":
                    if self.apply_quick_preset_checkbox.get() == 1:
                        selected_preset_name = self.recode_preset_menu.get()
                        preset_params = self._find_preset_params(selected_preset_name)
                        options.update(preset_params)
                    options["keep_original_file"] = self.keep_original_quick_checkbox.get() == 1
                    
                    # Llamar al hilo de trabajo
                    self.active_operation_thread = threading.Thread(target=self._execute_download_and_recode, args=(options,), daemon=True)
                    self.active_operation_thread.start()
    
                elif recode_mode == "Modo Manual":
                    manual_options = {
                        "recode_video_enabled": self.recode_video_checkbox.get() == 1,
                        "recode_audio_enabled": self.recode_audio_checkbox.get() == 1,
                        "keep_original_file": self.keep_original_checkbox.get() == 1,
                        "recode_proc": self.proc_type_var.get(),
                        "recode_codec_name": self.recode_codec_menu.get(),
                        "recode_profile_name": self.recode_profile_menu.get(),
                        "custom_bitrate_value": self.custom_bitrate_entry.get(),
                        "custom_gif_fps": self.custom_gif_fps_entry.get() or "15",
                        "custom_gif_width": self.custom_gif_width_entry.get() or "480",
                        "recode_container": self.recode_container_label.cget("text"),
                        "recode_audio_codec_name": self.recode_audio_codec_menu.get(),
                        "recode_audio_profile_name": self.recode_audio_profile_menu.get(),
                        "fps_force_enabled": self.fps_checkbox.get() == 1,
                        "fps_value": self.fps_entry.get(),
                        "resolution_change_enabled": self.resolution_checkbox.get() == 1,
                        "res_width": self.width_entry.get(),
                        "res_height": self.height_entry.get(),
                        "no_upscaling_enabled": self.no_upscaling_checkbox.get() == 1,
                        "resolution_preset": self.resolution_preset_menu.get(),
                        "original_width": self.original_video_width,
                        "original_height": self.original_video_height,
                    }
                    options.update(manual_options)
                    
                    # Llamar al hilo de trabajo
                    self.active_operation_thread = threading.Thread(target=self._execute_download_and_recode, args=(options,), daemon=True)
                    self.active_operation_thread.start()
    
                elif recode_mode == "Modo Extraer":
                    # --- NUEVA Lógica de Extracción ---
                    print("DEBUG: Iniciando Hilo de Extracción.")
                    
                    # Recolectar opciones de EXTRACCIÓN
                    extract_options = {
                        "extract_type": self.extract_type_menu.get(),
                        "extract_format": "jpg" if self.extract_format_menu.get() == "JPG (tamaño reducido)" else "png",
                        "extract_jpg_quality": self.extract_jpg_quality_entry.get() or "2",
                        "extract_fps": self.extract_fps_entry.get() or None
                    }
                    options.update(extract_options)
                    
                    # Llamar al Hilo de trabajo NUEVO
                    self.active_operation_thread = threading.Thread(target=self._execute_extraction_thread, args=(options,), daemon=True)
                    self.active_operation_thread.start()
    
            elif recode_mode == "Modo Extraer":
                
                # --- NUEVA Lógica de Extracción ---
                print("DEBUG: Iniciando Hilo de Extracción.")
                
                # 1. Recolectar opciones de EXTRACCIÓN
                extract_options = {
                    "extract_type": self.extract_type_menu.get(),
                    "extract_format": "jpg" if self.extract_format_menu.get() == "JPG (tamaño reducido)" else "png",
                    "extract_jpg_quality": self.extract_jpg_quality_entry.get() or "2",
                    "extract_fps": self.extract_fps_entry.get() or None
                }
                options.update(extract_options) # Añadirlas a las opciones base
                
                # 2. Llamar al Hilo de trabajo NUEVO
                self.active_operation_thread = threading.Thread(target=self._execute_extraction_thread, args=(options,), daemon=True)
                self.active_operation_thread.start()
    
    def _execute_download_and_recode(self, options):
        # irreducible cflow, using cdg fallback
        import os
        from pathlib import Path
        import threading
        import glob
        from tkinter import messagebox

        meta_start_time = options.get('start_time')
        meta_end_time = options.get('end_time')
        process_successful = False
        downloaded_filepath = None
        recode_phase_started = False
        keep_file_on_cancel = None
        final_recoded_path = None
        cleanup_required = True
        user_facing_title = ''
        backup_file_path = None
        audio_extraction_fallback = False
        temp_video_for_extraction = None
        conflict_resolved = False

        # --- Caso: archivo local ---
        if self.local_file_path:
            try:
                self._execute_local_recode(options)
            except (LocalRecodeFailedError, UserCancelledError) as e:
                # Si falló la recodificación local y hay un temporal, limpiar
                if isinstance(e, LocalRecodeFailedError) and hasattr(e, 'temp_filepath') and e.temp_filepath and os.path.exists(e.temp_filepath):
                    try:
                        os.remove(e.temp_filepath)
                        print(f'DEBUG: Archivo temporal de recodificación eliminado: {e.temp_filepath}')
                    except OSError as a:
                        print(f'ERROR: No se pudo eliminar el archivo temporal \'{e.temp_filepath}\': {a}')
                self.app.after(0, self.on_process_finished, False, str(e), None)
            finally:
                self.active_operation_thread = None
            return  # Terminar aquí, ya que se procesó archivo local

        # --- Preparación para descarga normal ---
        # (el código original sigue aquí, pero ahora envuelto en un gran try/except/finally)
        try:
            # Detectar si es solo audio y necesita fallback
            if options['mode'] == 'Solo Audio':
                audio_info = self.audio_formats.get(options['audio_format_label'], {})
                if not audio_info.get('format_id'):
                    audio_extraction_fallback = True
                    print('DEBUG: No hay pistas de audio dedicadas o formato_id inválido. Se activó el fallback de extracción desde el video.')
                    best_video_label = next(iter(self.video_formats))
                    options['video_format_label'] = best_video_label

            final_output_path_str = options['output_path']
            user_facing_title = self.sanitize_filename(options['title'])
            base_filename = user_facing_title
            output_path = Path(final_output_path_str)

            # Resolver conflicto de nombres
            video_format_info = self.video_formats.get(options['video_format_label'], {})
            audio_format_info = self.audio_formats.get(options['audio_format_label'], {})
            mode = options['mode']
            expected_ext = self._predict_final_extension(video_format_info, audio_format_info, mode)
            final_filename_to_check = f'{user_facing_title}{expected_ext}'
            full_path_to_check = os.path.join(final_output_path_str, final_filename_to_check)
            final_download_path, backup_file_path = self._resolve_output_path(full_path_to_check)
            conflict_resolved = True
            user_facing_title = Path(final_download_path).stem
            base_filename = user_facing_title

            # --- Descarga principal ---
            downloaded_filepath, temp_video_for_extraction = self._perform_download(options, user_facing_title, audio_extraction_fallback)
            self.last_downloaded_original_path = downloaded_filepath

            # Recorte opcional
            filepath_to_process = self._handle_optional_clipping(downloaded_filepath, options)

            if self.cancellation_event.is_set():
                raise UserCancelledError('Proceso cancelado por el usuario.')

            # Guardar miniatura
            self._save_thumbnail_if_enabled(filepath_to_process)

            # --- Procesamiento de subtítulos ---
            if options.get('download_subtitles'):
                subtitle_info = options.get('selected_subtitle_info')
                if subtitle_info:
                    output_dir = os.path.dirname(downloaded_filepath)
                    base_name = os.path.splitext(os.path.basename(downloaded_filepath))[0]
                    lang_code = subtitle_info['lang']
                    # Buscar el archivo de subtítulo descargado
                    possible_patterns = [
                        os.path.join(output_dir, f'{base_name}.{lang_code}.srt'),
                        os.path.join(output_dir, f'{base_name}.{lang_code}.vtt'),
                        os.path.join(output_dir, f'{base_name}.srt'),
                        os.path.join(output_dir, f'{base_name}.vtt')
                    ]
                    found_subtitle_path = None
                    for pattern in possible_patterns:
                        if os.path.exists(pattern):
                            found_subtitle_path = pattern
                            print(f'DEBUG: Encontrado subtítulo: {found_subtitle_path}')
                            break
                    if not found_subtitle_path:
                        search_pattern = os.path.join(output_dir, f'{base_name}.{lang_code}.*')
                        matches = glob.glob(search_pattern)
                        subtitle_matches = [m for m in matches if m.lower().endswith(('.srt', '.vtt', '.ass', '.ssa'))]
                        if subtitle_matches:
                            found_subtitle_path = subtitle_matches[0]
                            print(f'DEBUG: Encontrado subtítulo con glob: {found_subtitle_path}')

                    if found_subtitle_path:
                        try:
                            should_convert = self.clean_subtitle_check.winfo_ismapped() and self.clean_subtitle_check.get() == 1
                            if should_convert and (not found_subtitle_path.lower().endswith('.srt')):
                                self.app.after(0, self.update_progress, 98, 'Convirtiendo subtítulo a SRT...')
                                print(f'DEBUG: Convirtiendo {found_subtitle_path} a SRT')
                                converted_path = clean_and_convert_vtt_to_srt(found_subtitle_path)
                                found_subtitle_path = converted_path
                                print(f'DEBUG: Subtítulo convertido a: {found_subtitle_path}')

                            if found_subtitle_path.lower().endswith('.srt'):
                                self.app.after(0, self.update_progress, 99, 'Estandarizando formato SRT...')
                                print(f'DEBUG: Limpiando subtítulo SRT: {found_subtitle_path}')
                                found_subtitle_path = clean_and_convert_vtt_to_srt(found_subtitle_path)
                                print(f'DEBUG: Subtítulo limpiado: {found_subtitle_path}')

                                # Cortar subtítulo si se requiere
                                needs_cut = not options.get('keep_full_subtitle') and (meta_start_time or meta_end_time)
                                if needs_cut:
                                    print(f'DEBUG: ✂️ Iniciando corte de subtítulo ({meta_start_time} - {meta_end_time})')
                                    self.app.after(0, self.update_progress, 99, 'Sincronizando subtítulo con fragmento...')
                                    cut_sub_path = os.path.splitext(found_subtitle_path)[0] + '_cut.srt'
                                    success_cut = slice_subtitle(self.ffmpeg_processor.ffmpeg_path, found_subtitle_path, cut_sub_path,
                                                                start_time=meta_start_time or '00:00:00',
                                                                end_time=meta_end_time)
                                    if success_cut and os.path.exists(cut_sub_path):
                                        try:
                                            os.remove(found_subtitle_path)
                                            os.rename(cut_sub_path, found_subtitle_path)
                                            print('DEBUG: ✅ Subtítulo cortado y reemplazado exitosamente.')
                                        except Exception as e:
                                            print(f'ADVERTENCIA: No se pudo reemplazar el subtítulo cortado: {e}')
                        except Exception as sub_e:
                            print(f'ADVERTENCIA: Falló el procesamiento automático del subtítulo: {sub_e}')
                    else:
                        print(f'ADVERTENCIA: No se encontró el archivo de subtítulo para \'{base_name}\' con idioma \'{lang_code}\'')

            # --- Extracción de audio (fallback) ---
            if audio_extraction_fallback:
                self.app.after(0, self.update_progress, 95, 'Extrayendo pista de audio...')
                audio_ext = audio_format_info.get('ext', 'm4a')
                final_audio_path = os.path.join(final_output_path_str, f'{user_facing_title}.{audio_ext}')
                filepath_to_process = self.ffmpeg_processor.extract_audio(
                    input_file=temp_video_for_extraction,
                    output_file=final_audio_path,
                    duration=self.video_duration,
                    progress_callback=self.update_progress,
                    cancellation_event=self.cancellation_event
                )
                # Eliminar el video temporal usado para extracción
                try:
                    os.remove(temp_video_for_extraction)
                    print(f'DEBUG: Video temporal \'{temp_video_for_extraction}\' eliminado.')
                    temp_video_for_extraction = None
                except OSError as e:
                    print(f'ADVERTENCIA: No se pudo eliminar el video temporal: {e}')

            # --- Recodificación (si está habilitada) ---
            if options.get('recode_video_enabled') or options.get('recode_audio_enabled'):
                recode_phase_started = True
                recode_base_filename = user_facing_title + '_recoded'
                final_recoded_path = self._execute_recode_master(
                    input_file=filepath_to_process,
                    output_dir=final_output_path_str,
                    base_filename=recode_base_filename,
                    recode_options=options
                )
                if not options.get('keep_original_file', False) and os.path.exists(filepath_to_process):
                    try:
                        os.remove(filepath_to_process)
                    except OSError:
                        pass
                self.app.after(0, self.on_process_finished, True, 'Recodificación completada', final_recoded_path)
                process_successful = True
            else:
                self.app.after(0, self.on_process_finished, True, 'Descarga completada', filepath_to_process)
                process_successful = True

        # --- Manejo de excepciones específicas ---
        except UserCancelledError as e:
            # Cancelación por usuario
            error_message = str(e)
            # Si la recodificación ya había comenzado y no se mantiene el original, preguntar
            if recode_phase_started and (not options.get('keep_original_file', False)) and (not self.app.is_shutting_down):
                self.app.ui_request_data = {
                    'type': 'ask_yes_no',
                    'title': 'Fallo en la Recodificación',
                    'message': 'La descarga del archivo original se completó, pero la recodificación fue cancelada.\n\n¿Deseas conservar el archivo original descargado?'
                }
                self.app.ui_response_event.clear()
                self.app.ui_request_event.set()
                self.app.ui_response_event.wait()
                if self.app.ui_response_data.get('result', False):
                    keep_file_on_cancel = downloaded_filepath
                    self.app.after(0, lambda: self.on_process_finished(False, 'Recodificación cancelada. Archivo original conservado.', keep_file_on_cancel, False))
                else:
                    self.app.after(0, lambda: self.on_process_finished(False, error_message, downloaded_filepath, False))
            else:
                self.app.after(0, lambda: self.on_process_finished(False, error_message, downloaded_filepath, False))

        except PlaylistDownloadError as e:
            # Error específico de playlist
            print(f'DEBUG: Se capturó un error específico de Playlist: {e}')
            if self.analysis_was_playlist:
                print('DEBUG: El análisis original fue de una playlist. Mostrando diálogo.')
                self.app.ui_request_data = {
                    'type': 'ask_playlist_error',
                    'filename': options['url']
                }
                self.app.ui_response_event.clear()
                self.app.ui_request_event.set()
                self.app.ui_response_event.wait()
                user_choice = self.app.ui_response_data.get('result', 'cancel')
                if user_choice == 'send_to_batch':
                    self.app.after(0, self._send_url_to_batch, options['url'])
                    error_message = 'Elemento enviado a la pestaña de Lotes.'
                    self.app.after(0, lambda: self.on_process_finished(False, error_message, None, False))
                else:
                    error_message = 'Descarga de colección cancelada por el usuario.'
                    self.app.after(0, lambda: self.on_process_finished(False, error_message, None, False))
            else:
                print('DEBUG: Error tipo Playlist, pero el análisis no fue de playlist. Mostrando error normal.')
                cleaned_message = self._clean_ansi_codes(str(e))
                self.app.after(0, lambda: self.on_process_finished(False, cleaned_message, downloaded_filepath, True))

        except Exception as e:
            # Cualquier otro error
            cleaned_message = self._clean_ansi_codes(str(e))
            # Preguntar si se debe conservar el archivo original (si la recodificación falló)
            if recode_phase_started and (not options.get('keep_original_file', False)) and (not self.app.is_shutting_down):
                self.app.ui_request_data = {
                    'type': 'ask_yes_no',
                    'title': 'Fallo en la Recodificación',
                    'message': 'La descarga del archivo original se completó, pero la recodificación falló.\n\n¿Deseas conservar el archivo original descargado?'
                }
                self.app.ui_response_event.clear()
                self.app.ui_request_event.set()
                self.app.ui_response_event.wait()
                if self.app.ui_response_data.get('result', False):
                    keep_file_on_cancel = downloaded_filepath
            self.app.after(0, lambda: self.on_process_finished(False, cleaned_message, downloaded_filepath, True))

        finally:
            # --- Limpieza final (se ejecuta siempre) ---
            self._perform_cleanup(
                process_successful=process_successful,
                recode_phase_started=recode_phase_started,
                final_recoded_path=final_recoded_path,
                temp_video_for_extraction=temp_video_for_extraction,
                backup_file_path=backup_file_path,
                cleanup_required=cleanup_required,
                user_facing_title=user_facing_title,
                options=options,
                keep_file_on_cancel=keep_file_on_cancel,
                downloaded_filepath=downloaded_filepath
            )
            # Asegurar que el hilo se limpie
            self.active_operation_thread = None
    def _execute_recode_master(self, input_file, output_dir, base_filename, recode_options):
        """\n        Función maestra y unificada que maneja toda la lógica de recodificación.\n        Es llamada tanto por el modo URL como por el modo Local.\n        """
        final_recoded_path = None
        backup_file_path = None
        try:
            self.app.after(0, self.update_progress, 0, 'Preparando recodificación...')
            final_container = recode_options['recode_container']
            if not recode_options['recode_video_enabled'] and (not recode_options['recode_audio_enabled']):
                    _, original_extension = os.path.splitext(input_file)
                    final_container = original_extension
            final_filename_with_ext = f'{base_filename}{final_container}'
            desired_recoded_path = os.path.join(output_dir, final_filename_with_ext)
            final_recoded_path, backup_file_path = self._resolve_output_path(desired_recoded_path)
            temp_output_path = final_recoded_path + '.temp'
            final_ffmpeg_params = []
            pre_params = []
            container_ext = recode_options['recode_container']
            muxer_name = self.app.FORMAT_MUXER_MAP.get(container_ext, container_ext.lstrip('.'))
            final_ffmpeg_params.extend(['-f', muxer_name])
            print(f'DEBUG: [Muxer] Contenedor: {container_ext}, Muxer: {muxer_name}')
            if recode_options.get('fragment_enabled'):
                if recode_options.get('start_time'):
                    pre_params.extend(['-ss', recode_options.get('start_time')])
                if recode_options.get('end_time'):
                    pre_params.extend(['-to', recode_options.get('end_time')])
            if recode_options['mode'] != 'Solo Audio':
                if recode_options['recode_video_enabled']:
                    final_ffmpeg_params.extend(['-metadata:s:v:0', 'rotate=0'])
                    proc = recode_options['recode_proc']
                    codec_db = self.ffmpeg_processor.available_encoders[proc]['Video']
                    codec_data = codec_db.get(recode_options['recode_codec_name'])
                    ffmpeg_codec_name = next((k for k in codec_data if k != 'container'), None)
                    profile_params_list = codec_data[ffmpeg_codec_name].get(recode_options['recode_profile_name'])
                    if profile_params_list == 'CUSTOM_GIF':
                        try:
                            fps = int(recode_options['custom_gif_fps'])
                            width = int(recode_options['custom_gif_width'])
                            filter_string = f'[0:v] fps={fps},scale={width}:-1,split [a][b];[a] palettegen [p];[b][p] paletteuse'
                            final_ffmpeg_params.extend(['-filter_complex', filter_string])
                        except (ValueError, TypeError):
                            raise Exception('Valores de FPS/Ancho para GIF no son válidos.')
                    else:
                        if isinstance(profile_params_list, str) and 'CUSTOM_BITRATE' in profile_params_list:
                            bitrate_mbps = float(recode_options['custom_bitrate_value'])
                            bitrate_k = int(bitrate_mbps * 1000)
                            if 'nvenc' in ffmpeg_codec_name:
                                params_str = f'-c:v {ffmpeg_codec_name} -preset p5 -rc vbr -b:v {bitrate_k}k -maxrate {bitrate_k}k -pix_fmt yuv420p'
                            else:
                                params_str = f'-c:v {ffmpeg_codec_name} -b:v {bitrate_k}k -maxrate {bitrate_k}k -bufsize {bitrate_k * 2}k -pix_fmt yuv420p'
                            final_ffmpeg_params.extend(params_str.split())
                        else:
                            final_ffmpeg_params.extend(profile_params_list)
                    video_filters = []
                    if recode_options.get('fps_force_enabled') and recode_options.get('fps_value'):
                            video_filters.append(f"fps={recode_options['fps_value']}")
                    if recode_options.get('resolution_change_enabled'):
                        preset = recode_options.get('resolution_preset')
                        target_w, target_h = (0, 0)
                        PRESET_RESOLUTIONS_16_9 = {'4K UHD': (3840, 2160), '2K QHD': (2560, 1440), '1080p Full HD': (1920, 1080), '720p HD': (1280, 720), '480p SD': (854, 480)}
                        try:
                            if preset == 'Personalizado':
                                target_w = int(recode_options['res_width'])
                                target_h = int(recode_options['res_height'])
                            else:
                                if preset in PRESET_RESOLUTIONS_16_9:
                                    w_16_9, h_16_9 = PRESET_RESOLUTIONS_16_9[preset]
                                    original_width = recode_options.get('original_width', 0)
                                    original_height = recode_options.get('original_height', 0)
                                    if original_width > 0 and original_height > 0 and (original_width < original_height):
                                        target_w, target_h = (h_16_9, w_16_9)
                                    else:
                                        target_w, target_h = (w_16_9, h_16_9)
                            if target_w > 0 and target_h > 0:
                                    if recode_options.get('no_upscaling_enabled'):
                                        original_width = recode_options.get('original_width', 0)
                                        original_height = recode_options.get('original_height', 0)
                                        if original_width > 0 and target_w > original_width:
                                                target_w = original_width
                                        if original_height > 0 and target_h > original_height:
                                                target_h = original_height
                                    video_filters.append(f'scale={target_w}:{target_h}')
                        except (ValueError, TypeError) as e:
                            print(f'ERROR: No se pudieron parsear los valores de resolución. {e}')
                    if video_filters and 'filter_complex' not in final_ffmpeg_params:
                            final_ffmpeg_params.extend(['-vf', ','.join(video_filters)])
                else:
                    final_ffmpeg_params.extend(['-c:v', 'copy'])
            is_gif_format = 'GIF' in recode_options.get('recode_codec_name', '')
            if not is_gif_format:
                is_pro_video_format = False
                if recode_options['recode_video_enabled'] and any((x in recode_options['recode_codec_name'] for x in ['ProRes', 'DNxH'])):
                        is_pro_video_format = True
                if is_pro_video_format:
                    final_ffmpeg_params.extend(['-c:a', 'pcm_s16le'])
                else:
                    if recode_options['recode_audio_enabled']:
                        audio_codec_db = self.ffmpeg_processor.available_encoders['CPU']['Audio']
                        audio_codec_data = audio_codec_db.get(recode_options['recode_audio_codec_name'])
                        ffmpeg_audio_codec = next((k for k in audio_codec_data if k != 'container'), None)
                        audio_profile_params = audio_codec_data[ffmpeg_audio_codec].get(recode_options['recode_audio_profile_name'])
                        if audio_profile_params:
                            final_ffmpeg_params.extend(audio_profile_params)
                    else:
                        final_ffmpeg_params.extend(['-c:a', 'copy'])
            command_options = {'input_file': input_file, 'output_file': temp_output_path, 'duration': recode_options.get('duration', 0), 'ffmpeg_params': final_ffmpeg_params, 'pre_params': pre_params, 'mode': recode_options.get('mode'), 'selected_video_stream_index': None if '-filter_complex' in final_ffmpeg_params else recode_options.get('selected_video_stream_index'), 'selected_audio_stream_index': None if is_gif_format else recode_options.get('selected_audio_stream_index')}
            self.ffmpeg_processor.execute_recode(command_options, self.update_progress, self.cancellation_event)
            if os.path.exists(temp_output_path):
                os.rename(temp_output_path, final_recoded_path)
            if backup_file_path and os.path.exists(backup_file_path):
                    os.remove(backup_file_path)
            return final_recoded_path
        except Exception as e:
            if os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except OSError:
                    pass
            if backup_file_path and os.path.exists(backup_file_path):
                    try:
                        os.rename(backup_file_path, final_recoded_path)
                    except OSError:
                        pass
            raise e
    def _perform_download(self, options, user_facing_title, audio_extraction_fallback, override_output_dir=None):
        # irreducible cflow, using cdg fallback
        import os
        import sys
        import threading
        import yt_dlp
        from src.core.downloader import download_media, apply_yt_patch

        downloaded_filepath = None
        temp_video_for_extraction = None

        try:
            # --- 1. Preparación inicial ---
            self.app.after(0, self.update_progress, 0, 'Iniciando descarga...')
            video_format_info = self.video_formats.get(options['video_format_label'], {})
            audio_format_info = self.audio_formats.get(options['audio_format_label'], {})
            mode = options['mode']
            effective_output_dir = override_output_dir if override_output_dir else options['output_path']
            output_template = os.path.join(effective_output_dir, f'{user_facing_title}.%(ext)s')

            video_format_id = video_format_info.get('format_id')
            audio_format_id = audio_format_info.get('format_id')

            # --- 2. Manejo de combinación de audio (idiomas) ---
            if hasattr(self, 'combined_audio_map') and self.combined_audio_map:
                selected_audio_label = options.get('audio_format_label')
                if selected_audio_label in self.combined_audio_map:
                    video_format_id = self.combined_audio_map[selected_audio_label]
                    print(f'DEBUG: ✅ Reemplazando format_id con variante de idioma: {video_format_id}')

            # --- 3. Determinar si es un formato simple ---
            total_formats = len(self.video_formats) + len(self.audio_formats)
            is_combined = video_format_info.get('is_combined', False)
            is_simple_format = total_formats == 1 and (is_combined or not self.audio_formats)
            if is_simple_format and video_format_id:
                protocol_ids = ['http', 'https', 'm3u8', 'm3u8_native', 'hls', 'dash']
                is_simple_id = (
                    video_format_id.isdigit() or
                    video_format_id in ['default', 'best'] or
                    video_format_id in protocol_ids or
                    (len(video_format_id) <= 10 and '+' not in video_format_id)
                )
                if not is_simple_id:
                    is_simple_format = False

            # --- 4. Construir selector preciso ---
            precise_selector = ''
            if audio_extraction_fallback:
                precise_selector = video_format_id
            else:
                if mode == 'Video+Audio':
                    if is_simple_format and video_format_id:
                        precise_selector = video_format_id
                    elif is_combined and video_format_id:
                        precise_selector = video_format_id
                    elif video_format_id and audio_format_id:
                        precise_selector = f'{video_format_id}+{audio_format_id}'
                elif mode == 'Solo Audio':
                    precise_selector = audio_format_id

            print(f'DEBUG: 📌 Selector de formato: {precise_selector}')

            # --- 5. Configurar yt-dlp ---
            if getattr(sys, 'frozen', False):
                project_root = os.path.dirname(sys.executable)
            else:
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

            ydl_opts = {
                'outtmpl': output_template,
                'format': precise_selector,
                'postprocessors': [],
                'noplaylist': True,
                'ffmpeg_location': self.ffmpeg_processor.ffmpeg_path,
                'retries': 2,
                'fragment_retries': 2,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'referer': options['url']
            }

            # --- 6. Configurar fragmento (si está habilitado) ---
            want_fragment = options.get('fragment_enabled') and (options.get('start_time') or options.get('end_time'))
            force_full = options.get('force_full_download', False)
            keep_full = options.get('keep_original_on_clip', False)
            is_fragment_mode = want_fragment and (not force_full) and (not keep_full)

            if is_fragment_mode:
                start_time_str = options.get('start_time') or ''
                end_time_str = options.get('end_time') or ''
                if not start_time_str and not end_time_str:
                    print('DEBUG: ⚠️ Modo fragmento activado pero sin tiempos definidos')
                    is_fragment_mode = False
                else:
                    start_seconds = self.time_str_to_seconds(start_time_str) if start_time_str else 0
                    end_seconds = self.time_str_to_seconds(end_time_str) if end_time_str else None
                    print('DEBUG: 🎬 Configurando descarga de fragmento:')
                    print(f"  - Inicio: {(start_time_str if start_time_str else '00:00:00 (desde el principio)')} ({start_seconds}s)")
                    if end_seconds is not None:
                        print(f'  - Fin: {end_time_str} ({end_seconds}s)')
                    else:
                        print('  - Fin: (hasta el final del video)')
                    try:
                        from yt_dlp.utils import download_range_func
                        if end_seconds is not None:
                            ranges = [(start_seconds, end_seconds)]
                        else:
                            ranges = [(start_seconds, float('inf'))]
                        ydl_opts['download_ranges'] = download_range_func(None, ranges)
                        use_precise = options.get('precise_clip_enabled', False)
                        ydl_opts['force_keyframes_at_cuts'] = use_precise
                        print(f'DEBUG: ✅ download_ranges configurado: {ranges} | Preciso: {use_precise}')
                    except Exception as e:
                        print(f'DEBUG: ⚠️ Error configurando download_ranges: {e}')
                        print('DEBUG: 🔥 Fallback: se descargará completo y se cortará con FFmpeg')
                        is_fragment_mode = False

            # --- 7. Postprocesadores y subtítulos ---
            if mode == 'Solo Audio' and audio_format_info.get('extract_only'):
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                })

            if options['download_subtitles'] and options.get('selected_subtitle_info'):
                subtitle_info = options['selected_subtitle_info']
                if subtitle_info:
                    should_convert_to_srt = self.clean_subtitle_check.winfo_ismapped() and self.clean_subtitle_check.get() == 1
                    ydl_opts.update({
                        'writesubtitles': True,
                        'subtitleslangs': [subtitle_info['lang']],
                        'writeautomaticsub': subtitle_info.get('automatic', False),
                        'embedsubtitles': mode == 'Video+Audio'
                    })
                    if should_convert_to_srt:
                        ydl_opts['subtitlesformat'] = 'best/vtt/best'
                        ydl_opts['convertsubtitles'] = 'srt'
                    else:
                        ydl_opts['subtitlesformat'] = subtitle_info.get('ext', 'best')

            # --- 8. Límite de velocidad y cookies ---
            if options['speed_limit']:
                try:
                    ydl_opts['ratelimit'] = float(options['speed_limit']) * 1024 * 1024
                except ValueError:
                    pass

            cookie_mode = options['cookie_mode']
            using_cookies = False
            cookie_flag = ''
            if cookie_mode == 'Archivo Manual...' and options['cookie_path']:
                ydl_opts['cookiefile'] = options['cookie_path']
                cookie_flag = f" --cookies \"{options['cookie_path']}\""
                using_cookies = True
            elif cookie_mode != 'No usar':
                browser_arg = options['selected_browser']
                if options['browser_profile']:
                    browser_arg += f":{options['browser_profile']}"
                ydl_opts['cookiesfrombrowser'] = (browser_arg,)
                cookie_flag = f' --cookies-from-browser {browser_arg}'
                using_cookies = True

            if using_cookies:
                ydl_opts = apply_yt_patch(ydl_opts)

            # --- 9. Mostrar comando CLI equivalente ---
            download_section_flag = ''
            if is_fragment_mode:
                s_t = options.get('start_time') or '0'
                e_t = options.get('end_time') or 'inf'
                download_section_flag = f' --download-sections "*{s_t}-{e_t}"'
                if options.get('precise_clip_enabled'):
                    download_section_flag += ' --force-keyframes-at-cuts'

            cli_command = (
                f'yt-dlp -f "{precise_selector}"{cookie_flag}{download_section_flag} '
                f'"{options["url"]}" -o "{output_template}"'
            )
            print(f"\n{'=' * 80}")
            print('🔍 COMANDO EQUIVALENTE DE CLI (Cópialo para usar en terminal):')
            print(cli_command)
            print(f"{'=' * 80}\n")
            print('DEBUG: 📋 Opciones de yt-dlp:')
            important_opts = ['format', 'download_ranges', 'force_keyframes_at_cuts', 'postprocessors']
            for key in important_opts:
                if key in ydl_opts:
                    print(f'  - {key}: {ydl_opts[key]}')

            # --- 10. Fallback de extracción de audio ---
            if audio_extraction_fallback:
                print(f'DEBUG: [FALLBACK] Descargando video: {precise_selector}')
                downloaded_filepath = download_media(options['url'], ydl_opts, self.update_progress, self.cancellation_event)
                temp_video_for_extraction = downloaded_filepath
                return (downloaded_filepath, temp_video_for_extraction)

            if not precise_selector:
                raise yt_dlp.utils.DownloadError('Selector preciso no válido')

            # --- 11. Intento de descarga con reintentos (3 pasos) ---
            # Paso 1: Descarga directa con el selector preciso
            print('DEBUG: 🚀 INTENTO 1: Descargando con yt-dlp...')
            if is_fragment_mode:
                print('DEBUG: 🎬 Intentando descarga directa de fragmento')
                try:
                    downloaded_filepath = download_media(options['url'], ydl_opts, self.update_progress, self.cancellation_event)
                    print(f'DEBUG: ✅ Fragmento descargado: {downloaded_filepath}')
                    options['fragment_enabled'] = False
                    options['start_time'] = ''
                    options['end_time'] = ''
                    return (downloaded_filepath, temp_video_for_extraction)
                except Exception as fragment_error:
                    is_cancellation = self.cancellation_event.is_set() or 'cancelada' in str(fragment_error).lower()
                    if is_cancellation:
                        print('DEBUG: 🛑 Cancelación detectada en fragmento. Abortando.')
                        raise UserCancelledError('Descarga cancelada por el usuario.')
                    else:
                        print(f'DEBUG: ❌ Error en descarga de fragmento: {fragment_error}')
                        print(f'DEBUG: 🔍 Tipo de error: {type(fragment_error).__name__}')
                        # Preguntar si descargar completo y cortar localmente
                        self.app.ui_request_data = {
                            'type': 'ask_yes_no',
                            'title': 'Descarga de Fragmento Fallida',
                            'message': (
                                f'No se pudo descargar el fragmento directamente.\n\n'
                                f'Error: {str(fragment_error)[:100]}\n\n'
                                '¿Deseas descargar el video completo y luego cortarlo?\n\n'
                                '(Esto tomará más tiempo y espacio en disco)'
                            )
                        }
                        self.app.ui_response_event.clear()
                        self.app.ui_request_event.set()
                        self.app.ui_response_event.wait()
                        user_choice = self.app.ui_response_data.get('result', False)
                        if not user_choice:
                            raise UserCancelledError('El usuario canceló la descarga del video completo.')
                        else:
                            print('DEBUG: 📥 Descargando video completo para cortar después...')
                            ydl_opts_full = ydl_opts.copy()
                            ydl_opts_full.pop('download_ranges', None)
                            ydl_opts_full.pop('force_keyframes_at_cuts', None)
                            ydl_opts_full.pop('_fragment_range', None)
                            ydl_opts_full['postprocessors'] = [
                                pp for pp in ydl_opts_full.get('postprocessors', [])
                                if pp.get('key') != 'FFmpegVideoRemuxer'
                            ]
                            options['fragment_enabled'] = True
                            downloaded_filepath = download_media(options['url'], ydl_opts_full, self.update_progress, self.cancellation_event)
                            # Después de descarga completa, cortar se hará en _handle_optional_clipping
                            return (downloaded_filepath, temp_video_for_extraction)

            # Si no es fragmento, intento normal con reintentos
            try:
                downloaded_filepath = download_media(options['url'], ydl_opts, self.update_progress, self.cancellation_event)
                return (downloaded_filepath, temp_video_for_extraction)
            except yt_dlp.utils.DownloadError as e:
                print(f'DEBUG: Falló el intento 1. Error: {e}')
                print('DEBUG: Pasando al Paso 2 (selector flexible).')
                try:
                    # Paso 2: selector flexible
                    if is_simple_format:
                        strict_flexible_selector = 'best'
                        print('DEBUG: INTENTO 2 (simple): Usando selector \'best\'')
                    elif 'twitter' in options['url'] or 'x.com' in options['url']:
                        strict_flexible_selector = 'best'
                        print('DEBUG: INTENTO 2 (Twitter): Usando selector \'best\'')
                    elif not self.video_formats and not self.audio_formats:
                        strict_flexible_selector = 'best'
                    else:
                        info_dict = self.analysis_cache.get(options['url'], {}).get('data', {})
                        selected_audio_details = next(
                            (f for f in info_dict.get('formats', []) if f.get('format_id') == audio_format_id),
                            None
                        )
                        language_code = selected_audio_details.get('language') if selected_audio_details else None
                        strict_flexible_selector = ''
                        if self.has_audio_streams:
                            if mode == 'Video+Audio':
                                height = video_format_info.get('height')
                                video_selector = f'bv[height={height}]' if height else 'bv'
                                audio_selector = f'ba[lang={language_code}]' if language_code else 'ba'
                                strict_flexible_selector = f'{video_selector}+{audio_selector}'
                            elif mode == 'Solo Audio':
                                strict_flexible_selector = f'ba[lang={language_code}]' if language_code else 'ba'
                        else:
                            height = video_format_info.get('height')
                            strict_flexible_selector = f'bv[height={height}]' if height else 'bv'

                    ydl_opts['format'] = strict_flexible_selector
                    print(f'DEBUG: INTENTO 2: Descargando con selector flexible: {strict_flexible_selector}')
                    downloaded_filepath = download_media(options['url'], ydl_opts, self.update_progress, self.cancellation_event)
                    return (downloaded_filepath, temp_video_for_extraction)

                except yt_dlp.utils.DownloadError:
                    print('DEBUG: Falló intento 2. Pasando al Paso 3 (compromiso).')
                    # Paso 3: obtener detalles de mejor calidad y preguntar al usuario
                    details_ready_event = threading.Event()
                    compromise_details = {'text': 'Obteniendo detalles...'}

                    def get_details_thread():
                        compromise_details['text'] = self.app._get_best_available_info(options['url'], options)
                        details_ready_event.set()

                    self.app.after(0, self.update_progress, 50, 'Calidad no disponible. Obteniendo detalles de alternativa...')
                    threading.Thread(target=get_details_thread, daemon=True).start()
                    details_ready_event.wait()

                    self.app.ui_request_data = {
                        'type': 'ask_compromise',
                        'details': compromise_details['text']
                    }
                    self.app.ui_response_event.clear()
                    self.app.ui_request_event.set()
                    self.app.ui_response_event.wait()
                    user_choice = self.app.ui_response_data.get('result', 'cancel')

                    if user_choice == 'accept':
                        print('DEBUG: PASO 4: El usuario aceptó. Intentando con selector final.')
                        if not self.video_formats and not self.audio_formats:
                            final_selector = 'best'
                        else:
                            final_selector = 'ba' if mode == 'Solo Audio' else 'bv+ba' if self.has_audio_streams else 'bv'
                        ydl_opts['format'] = final_selector
                        downloaded_filepath = download_media(options['url'], ydl_opts, self.update_progress, self.cancellation_event)
                        return (downloaded_filepath, temp_video_for_extraction)
                    else:
                        raise UserCancelledError('Descarga cancelada por el usuario en el diálogo de compromiso.')

        except Exception as final_e:
            print(f'DEBUG: ❌ Error inesperado: {final_e}')
            raise

        # Si llegamos aquí sin retornar, algo falló
        if not downloaded_filepath or not os.path.exists(downloaded_filepath):
            raise Exception('La descarga falló o el archivo no se encontró.')
        return (downloaded_filepath, temp_video_for_extraction)
    def _perform_cleanup(self, process_successful, recode_phase_started, final_recoded_path, temp_video_for_extraction, backup_file_path, cleanup_required, user_facing_title, options, keep_file_on_cancel, downloaded_filepath):
        """Esta función se encargará de TODA la limpieza del bloque \'finally\'."""
        if not process_successful and (not self.local_file_path):
            output_dir = options.get('output_path', '')
            if output_dir and user_facing_title:
                    base_title_for_cleanup = user_facing_title.replace('_recoded', '')
                    self._cleanup_ytdlp_temp_files(output_dir, base_title_for_cleanup)
                    def deferred_cleanup():
                        time.sleep(3)
                        print('DEBUG: Ejecutando limpieza diferida...')
                        self._cleanup_ytdlp_temp_files(output_dir, base_title_for_cleanup)
                    threading.Thread(target=deferred_cleanup, daemon=True).start()
            if recode_phase_started and final_recoded_path and os.path.exists(final_recoded_path):
                        try:
                            gc.collect()
                            time.sleep(0.5)
                            print(f'DEBUG: Limpiando archivo de recodificación temporal por fallo (Modo URL): {final_recoded_path}')
                            os.remove(final_recoded_path)
                        except OSError as e:
                            print(f'ERROR: No se pudo limpiar el archivo de recodificación temporal (Modo URL): {e}')
            if temp_video_for_extraction and os.path.exists(temp_video_for_extraction):
                    try:
                        print(f'DEBUG: Limpiando video temporal por fallo (Modo URL): {temp_video_for_extraction}')
                        os.remove(temp_video_for_extraction)
                    except OSError as e:
                        print(f'ERROR: No se pudo limpiar el video temporal (Modo URL): {e}')
            if backup_file_path and os.path.exists(backup_file_path):
                print('AVISO: La descarga falló. Restaurando el archivo original desde el respaldo (Modo URL).')
                try:
                    original_path = backup_file_path.removesuffix('.bak')
                    if os.path.exists(original_path) and os.path.normpath(original_path) != os.path.normpath(backup_file_path):
                            os.remove(original_path)
                    os.rename(backup_file_path, original_path)
                    print(f'ÉXITO: Respaldo restaurado a: {original_path}')
                except OSError as err:
                    print(f'ERROR CRÍTICO: No se pudo restaurar el respaldo: {err}')
            else:
                if cleanup_required:
                    print('DEBUG: Iniciando limpieza general por fallo de operación.')
                    try:
                        gc.collect()
                        time.sleep(1)
                        base_title_for_cleanup = user_facing_title.replace('_recoded', '')
                        for filename in os.listdir(options['output_path']):
                            if not filename.startswith(base_title_for_cleanup):
                                continue
                            else:
                                file_path_to_check = os.path.join(options['output_path'], filename)
                                should_preserve = False
                                known_sidecar_exts = ('.srt', '.vtt', '.ass', '.ssa', '.json3', '.srv1', '.srv2', '.srv3', '.ttml', '.smi', '.tml', '.lrc', '.xml', '.jpg', '.jpeg', '.png')
                                if keep_file_on_cancel:
                                    normalized_preserved_path = os.path.normpath(keep_file_on_cancel)
                                    if os.path.normpath(file_path_to_check) == normalized_preserved_path:
                                        should_preserve = True
                                    else:
                                        base_preserved_name = os.path.splitext(os.path.basename(keep_file_on_cancel))[0]
                                        if filename.startswith(base_preserved_name):
                                            if filename.lower().endswith(known_sidecar_exts):
                                                should_preserve = True
                                else:
                                    if options.get('keep_original_file', False) and downloaded_filepath:
                                            normalized_original_path = os.path.normpath(downloaded_filepath)
                                            if os.path.normpath(file_path_to_check) == normalized_original_path:
                                                should_preserve = True
                                            else:
                                                base_original_name = os.path.splitext(os.path.basename(downloaded_filepath))[0]
                                                if filename.startswith(base_original_name):
                                                    if filename.lower().endswith(known_sidecar_exts):
                                                        should_preserve = True
                                if should_preserve:
                                    print(f'DEBUG: Conservando archivo solicitado o asociado: {file_path_to_check}')
                                else:
                                    print(f'DEBUG: Eliminando archivo no deseado: {file_path_to_check}')
                                    os.remove(file_path_to_check)
                    except Exception as cleanup_e:
                        print(f'ERROR: Falló el proceso de limpieza de archivos: {cleanup_e}')
        else:
            if process_successful and backup_file_path and os.path.exists(backup_file_path):
                        try:
                            os.remove(backup_file_path)
                            print('DEBUG: Proceso exitoso, respaldo eliminado.')
                        except OSError as err:
                            print(f'AVISO: No se pudo eliminar el archivo de respaldo: {err}')
        self.active_subprocess_pid = None
        self.active_operation_thread = None
    def _cleanup_ytdlp_temp_files(self, output_dir, base_title):
        """
        Limpia archivos temporales específicos de yt-dlp (.part, fragmentos, etc.)
        Incluye reintentos y manejo de bloqueos de archivo.
        """
        import glob
        import os
        import time
        import gc

        patterns_to_clean = [
            f'{base_title}*.part',
            f'{base_title}*.f[0-9]*',
            f'{base_title}*.ytdl',
            f'{base_title}*.temp',
            '*.f[0-9]*.part',
            f'{base_title}*.temp.*',
            f'{base_title}*.part-*',
            f'.{base_title}*'
        ]

        cleaned_count = 0
        failed_files = []

        for pattern in patterns_to_clean:
            full_pattern = os.path.join(output_dir, pattern)
            for temp_file in glob.glob(full_pattern):
                if not os.path.exists(temp_file):
                    continue

                # Reintentos para eliminar el archivo
                max_retries = 3
                removed = False
                for attempt in range(max_retries):
                    try:
                        # En el primer intento, intentar liberar handles y recolectar basura
                        if attempt > 0:
                            gc.collect()
                            time.sleep(0.5 * (2 ** attempt))  # backoff exponencial

                        os.remove(temp_file)
                        print(f'DEBUG: Eliminado temp de yt-dlp: {temp_file}')
                        cleaned_count += 1
                        removed = True
                        break

                    except PermissionError:
                        # Archivo bloqueado (ej. en uso por otro proceso)
                        if attempt < max_retries - 1:
                            print(f'⚠️ Archivo bloqueado, reintentando ({attempt + 1}/{max_retries}): {temp_file}')
                        else:
                            print(f'⚠️ No se pudo eliminar (bloqueado): {temp_file}')
                            failed_files.append(temp_file)

                    except FileNotFoundError:
                        # El archivo ya fue eliminado por otro proceso
                        cleaned_count += 1
                        removed = True
                        break

                    except OSError as e:
                        # Otros errores de sistema
                        if getattr(e, 'winerror', None) == 2 or e.errno == 2:
                            # ERROR_FILE_NOT_FOUND
                            cleaned_count += 1
                            removed = True
                            break
                        if attempt < max_retries - 1:
                            print(f'⚠️ Error al eliminar {temp_file}: {e}. Reintentando...')
                        else:
                            print(f'⚠️ No se pudo eliminar {temp_file}: {e}')
                            failed_files.append(temp_file)

                # Si no se pudo eliminar después de todos los reintentos, añadir a la lista de fallidos
                if not removed and temp_file not in failed_files:
                    failed_files.append(temp_file)

        # Reporte final
        if cleaned_count > 0:
            print(f'DEBUG: Se eliminaron {cleaned_count} archivos temporales de yt-dlp')

        if failed_files:
            print(f'⚠️ {len(failed_files)} archivo(s) temporal(es) no se pudieron eliminar:')
            for f in failed_files:
                print(f'   - {os.path.basename(f)}')

            # Segundo intento (más agresivo) para los que fallaron
            print('🔄 Reintentando eliminación de archivos fallidos...')
            time.sleep(2)
            remaining_files = []
            for temp_file in failed_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f'✅ Eliminado en reintento final: {os.path.basename(temp_file)}')
                        cleaned_count += 1
                except Exception as e:
                    remaining_files.append(temp_file)
                    print(f'⚠️ No se pudo eliminar en reintento final: {temp_file} - {e}')

            if remaining_files:
                print(f'⚠️ {len(remaining_files)} archivo(s) requieren limpieza manual:')
                for f in remaining_files:
                    print(f'   - {f}')
    def _reset_buttons_to_original_state(self):
        """ Restablece los botones a su estado original, aplicando el color correcto. """
        self.analyze_button.configure(text=self.original_analyze_text, fg_color=self.original_analyze_fg_color, command=self.original_analyze_command, state='normal')
        if self.local_file_path:
            button_text = 'Iniciar Proceso'
            button_color = self.PROCESS_BTN_COLOR
        else:
            button_text = self.original_download_text
            button_color = self.DOWNLOAD_BTN_COLOR
        hover_color = self.PROCESS_BTN_HOVER if self.local_file_path else self.DOWNLOAD_BTN_HOVER
        self.download_button.configure(text=button_text, fg_color=button_color, hover_color=hover_color, command=self.original_download_command)
        self.toggle_manual_subtitle_button()
        self.update_download_button_state()
    def _save_thumbnail_if_enabled(self, base_filepath):
        """Guarda la miniatura si la opción está activada, usando la ruta del archivo base."""
        if self.auto_save_thumbnail_check.get() == 1 and self.pil_image and base_filepath:
                    try:
                        self.app.after(0, self.update_progress, 98, 'Guardando miniatura...')
                        if not os.path.exists(base_filepath):
                            print(f'ADVERTENCIA: No se puede guardar miniatura, archivo no encontrado: {base_filepath}')
                            return
                        else:
                            if os.path.isdir(base_filepath):
                                print('DEBUG: Saltando guardado de miniatura (resultado es una carpeta)')
                                return
                            else:
                                output_directory = os.path.dirname(base_filepath)
                                clean_title = os.path.splitext(os.path.basename(base_filepath))[0]
                                if clean_title.endswith('_recoded'):
                                    clean_title = clean_title.rsplit('_recoded', 1)[0]
                                if clean_title.endswith('_fragmento'):
                                    clean_title = clean_title.rsplit('_fragmento', 1)[0]
                                thumb_path = os.path.join(output_directory, f'{clean_title}.jpg')
                                self.pil_image.convert('RGB').save(thumb_path, quality=95)
                                print(f'DEBUG: Miniatura guardada automáticamente en {thumb_path}')
                                return thumb_path
                    except Exception as e:
                        print(f'ADVERTENCIA: No se pudo guardar la miniatura automáticamente: {e}')
        return None
    def on_process_finished(self, success, message, final_filepath, show_dialog=True):
        """\n        Callback UNIFICADO. Usa las listas de extensiones de la clase para una clasificación robusta.\n        """
        if success and final_filepath:
                output_dir = os.path.dirname(final_filepath)
                base_name = os.path.splitext(os.path.basename(final_filepath))[0]
                if base_name.endswith('_recoded'):
                    base_name = base_name.rsplit('_recoded', 1)[0]
                expected_thumb_path = os.path.join(output_dir, f'{base_name}.jpg')
                thumb_path = expected_thumb_path if os.path.exists(expected_thumb_path) else None
                source_path = getattr(self, 'last_downloaded_original_path', final_filepath)
                self.app.integration_manager.broadcast_import(source_path=source_path, final_path=final_filepath, thumb_path=thumb_path, workflow_type='single')
        self.last_download_path = final_filepath
        self.progress_bar.stop()
        self.progress_bar.set(1 if success else 0)
        final_message = self._clean_ansi_codes(message)
        if success:
            self.progress_label.configure(text=final_message)
            if final_filepath:
                if os.path.isdir(final_filepath):
                    print(f'DEBUG: Proceso finalizado. Resultado: carpeta de frames. Ruta: {final_filepath}')
                    if hasattr(self, 'extract_success_label'):
                        self.extract_success_label.configure(text='✅ Extracción completada')
                    if hasattr(self, 'send_to_imagetools_button'):
                        self.send_to_imagetools_button.configure(state='normal')
                    self.open_folder_button.configure(state='normal')
                else:
                    if os.path.isfile(final_filepath):
                        print(f'DEBUG: Proceso finalizado. Resultado: archivo. Ruta: {final_filepath}')
                        if hasattr(self, 'extract_success_label'):
                            self.extract_success_label.configure(text='')
                        if hasattr(self, 'send_to_imagetools_button'):
                            self.send_to_imagetools_button.configure(state='disabled')
                        self.open_folder_button.configure(state='normal')
                    else:
                        self.open_folder_button.configure(state='disabled')
                        if hasattr(self, 'extract_success_label'):
                            self.extract_success_label.configure(text='')
                        if hasattr(self, 'send_to_imagetools_button'):
                            self.send_to_imagetools_button.configure(state='disabled')
        else:
            if show_dialog:
                self.progress_label.configure(text='❌ Error en la operación. Ver detalles.')
                lowered_message = final_message.lower()
                dialog_message = final_message
                if 'timed out' in lowered_message or 'timeout' in lowered_message:
                    dialog_message = 'Falló la conexión (Timeout).\n\nCausas probables:\n• Conexión a internet lenta o inestable.\n• Un antivirus o firewall está bloqueando la aplicación.'
                else:
                    if '429' in lowered_message or 'too many requests' in lowered_message:
                        dialog_message = 'Demasiadas Peticiones (Error 429).\n\nHas realizado demasiadas solicitudes en poco tiempo.\n\n**Sugerencias:**\n1. Desactiva la descarga automática de subtítulos y miniaturas.\n2. Usa la opción de \'Cookies\' si el problema persiste.\n3. Espera unos minutos antes de volver a intentarlo.'
                    else:
                        if any((keyword in lowered_message for keyword in ['age-restricted', 'login required', 'sign in', 'private video', 'premium', 'members only'])):
                            dialog_message = 'La descarga falló. El contenido parece ser privado, tener restricción de edad o requerir una suscripción.\n\nPor favor, intenta configurar las \'Cookies\' en la aplicación y vuelve a analizar la URL.'
                        else:
                            if 'cannot parse data' in lowered_message and 'facebook' in lowered_message:
                                dialog_message = 'Falló el análisis de Facebook.\n\nEste error usualmente ocurre con videos privados o con restricción de edad. Intenta configurar las \'Cookies\' para solucionarlo.'
                            else:
                                if 'ffmpeg not found' in lowered_message:
                                    dialog_message = 'Error Crítico: FFmpeg no encontrado.\n\nyt-dlp necesita FFmpeg para realizar la conversión de subtítulos.\n\nAsegúrate de que FFmpeg esté correctamente instalado en la carpeta \'bin\' de la aplicación.'
                dialog = SimpleMessageDialog(self.app, 'Error en la Operación', dialog_message)
                self.app.wait_window(dialog)
            else:
                self.progress_label.configure(text=final_message)
            self.open_folder_button.configure(state='disabled')
            self.send_to_imagetools_button.pack_forget()
        self._reset_buttons_to_original_state()
    def _predict_final_extension(self, video_info, audio_info, mode):
        """\n        Predice la extensión de archivo más probable que yt-dlp usará\n        al fusionar los streams de video y audio seleccionados.\n        """
        if mode == 'Solo Audio':
            return f".{audio_info.get('ext', 'mp3')}"
        else:
            if video_info.get('is_combined'):
                return f".{video_info.get('ext', 'mp4')}"
            else:
                v_ext = video_info.get('ext')
                a_ext = audio_info.get('ext')
                if not a_ext or a_ext == 'none':
                    return f'.{v_ext}' if v_ext else '.mp4'
                else:
                    if v_ext == 'mp4' and a_ext in ['m4a', 'mp4']:
                            return '.mp4'
                    if v_ext == 'webm' and a_ext in ['webm', 'opus']:
                            return '.webm'
                    return '.mkv'
    def _resolve_output_path(self, desired_filepath):
        """\n        Comprueba si una ruta de archivo deseada existe. Si existe,\n        lanza el diálogo de conflicto y maneja la lógica de\n        sobrescribir, renombrar o cancelar.\n        \n        Esta función está diseñada para ser llamada desde un HILO SECUNDARIO.\n        \n        Args:\n            desired_filepath (str): La ruta completa del archivo que se\n                                    pretende crear.\n        \n        Returns:\n            tuple (str, str or None):\n                - final_path: La ruta segura y final donde se debe escribir \n                              el archivo (podría ser la original o una renombrada).\n                - backup_path: La ruta a un archivo .bak si se eligió \n                               \"sobrescribir\", o None si no.\n        \n        Raises:\n            UserCancelledError: Si el usuario presiona \"Cancelar\" en el diálogo.\n            Exception: Si falla el renombrado del archivo de respaldo.\n        """
        final_path = desired_filepath
        backup_path = None
        if not os.path.exists(final_path):
            return (final_path, backup_path)
        else:
            print(f'DEBUG: Conflicto de archivo detectado en: {final_path}')
            self.app.ui_request_data = {'type': 'ask_conflict', 'filename': os.path.basename(final_path)}
            self.app.ui_response_event.clear()
            self.app.ui_request_event.set()
            self.app.ui_response_event.wait()
            user_choice = self.app.ui_response_data.get('result', 'cancel')
            if user_choice == 'cancel':
                raise UserCancelledError('Operación cancelada por el usuario en conflicto de archivo.')
            else:
                if user_choice == 'overwrite':
                    print(f'DEBUG: Usuario eligió sobrescribir. Creando backup de {final_path}')
                    try:
                        backup_path = final_path + '.bak'
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        os.rename(final_path, backup_path)
                    except OSError as e:
                        raise Exception(f'No se pudo respaldar el archivo original: {e}')
                else:
                    if user_choice == 'rename':
                        print('DEBUG: Usuario eligió renombrar. Buscando un nuevo nombre...')
                        base, ext = os.path.splitext(final_path)
                        counter = 1
                        while True:
                            new_path_candidate = f'{base} ({counter}){ext}'
                            if not os.path.exists(new_path_candidate):
                                final_path = new_path_candidate
                                print(f'DEBUG: Nuevo nombre encontrado: {final_path}')
                                break
                            else:
                                counter += 1
                return (final_path, backup_path)
    def update_progress(self, percentage, message):
        """\n        Actualiza la barra de progreso. AHORA es inteligente y acepta:\n        - Valores en escala 0-100 (de descargas/recodificación)\n        - Valores en escala 0.0-1.0\n        - Valor especial -1 para activar modo INDETERMINADO\n        """
        now = time.time()
        if percentage != 0 and percentage != 100 and (percentage != (-1)) and (now - self._last_progress_update_time < 0.33):
                        return
        self._last_progress_update_time = now
        try:
            progress_value = float(percentage)
        except (ValueError, TypeError):
            progress_value = 0.0
        if progress_value == (-1):
            def _update():
                self.progress_bar.configure(mode='indeterminate')
                self.progress_bar.start()
                self.progress_label.configure(text=message)
            self.app.after(0, _update)
            return
        else:
            if progress_value > 1.0:
                progress_value = progress_value / 100.0
            capped_percentage = max(0.0, min(progress_value, 1.0))
            def _update():
                if self.progress_bar.cget('mode') == 'indeterminate':
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode='determinate')
                self.progress_bar.set(capped_percentage)
                self.progress_label.configure(text=message)
            self.app.after(0, _update)
    def start_analysis_thread(self, event=None):
        self.analysis_is_complete = False
        url = self.url_entry.get()
        if url and self.local_file_path:
                self.reset_to_url_mode()
                self.url_entry.insert(0, url)
        if self.analyze_button.cget('text') == 'Cancelar':
            return
        if not url:
            return
        if url in self.analysis_cache:
            cached_entry = self.analysis_cache[url]
            if time.time() - cached_entry['timestamp'] < self.CACHE_TTL:
                print('DEBUG: Resultado encontrado en caché. Cargando...')
                self.update_progress(100, 'Resultado encontrado en caché. Cargando...')
                self.on_analysis_complete(cached_entry['data'])
                return
        self.analyze_button.configure(text='Cancelar', fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, command=self.cancel_operation)
        self.download_button.configure(state='disabled')
        self.open_folder_button.configure(state='disabled')
        self.save_subtitle_button.configure(state='disabled')
        self.cancellation_event.clear()
        self.progress_label.configure(text='Analizando...')
        self.progress_bar.start()
        self.create_placeholder_label('Analizando...')
        self.title_entry.delete(0, 'end')
        self.title_entry.insert(0, 'Analizando...')
        self.video_quality_menu.configure(state='disabled', values=['-'])
        self.audio_quality_menu.configure(state='disabled', values=['-'])
        self.subtitle_lang_menu.configure(state='disabled', values=['-'])
        self.subtitle_lang_menu.set('-')
        self.subtitle_type_menu.configure(state='disabled', values=['-'])
        self.subtitle_type_menu.set('-')
        self.toggle_manual_subtitle_button()
        self.analysis_was_playlist = False
        threading.Thread(target=self._run_analysis_subprocess, args=(url,), daemon=True).start()
    def _run_analysis_subprocess(self, url):
        """\n        Ejecuta el análisis usando la API de yt-dlp y captura la salida de texto\n        para preservar la lógica de análisis de subtítulos.\n        \n        ✅ MODIFICADO: Solución para YouTube + Cookies\n        """
        try:
            self.app.after(0, self.update_progress, 0, 'Iniciando análisis de URL...')
            is_youtube = 'youtube.com' in url.lower() or 'youtu.be' in url.lower()
            cookie_mode = self.app.cookies_mode_saved
            using_cookies = cookie_mode != 'No usar'
            if is_youtube and using_cookies:
                    print(f"\n{'============================================================'}")
                    print('⚠️ YOUTUBE + COOKIES DETECTADO')
                    print('   Aplicando configuración especial...')
                    print(f"{'============================================================'}\n")
            ydl_opts = {'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'referer': url, 'noplaylist': True, 'playlist_items': '1', 'listsubtitles': True, 'progress_hooks': [lambda d: self.cancellation_event.is_set() and (_ for _ in []).throw(UserCancelledError('Análisis cancelado.'))]}
            if cookie_mode == 'Archivo Manual...' and self.app.cookies_path:
                ydl_opts['cookiefile'] = self.app.cookies_path
            else:
                if cookie_mode != 'No usar':
                    browser_arg = self.app.selected_browser_saved
                    profile = self.app.browser_profile_saved
                    if profile:
                        browser_arg += f':{profile}'
                    ydl_opts['cookiesfrombrowser'] = (browser_arg,)
            if using_cookies:
                ydl_opts = apply_yt_patch(ydl_opts)
                print('🔧 Parche de YouTube aplicado (cookies habilitadas)')
                if is_youtube:
                    print(f"\n{'============================================================'}")
                    print('🔧 Ajustando configuración para YouTube + Cookies')
                    print(f"{'============================================================'}")
                    if 'extractor_args' in ydl_opts and 'youtube' in ydl_opts['extractor_args']:
                            ydl_opts['extractor_args']['youtube']['skip'] = []
                            youtube_config = ydl_opts['extractor_args']['youtube']
                            print(f"✅ player_client: {youtube_config.get('player_client')}")
                            print(f"✅ n_client: {youtube_config.get('n_client')}")
                            print(f"✅ skip: {youtube_config.get('skip')}")
                    print(f"{'============================================================'}\n")
            else:
                print('📝 Modo sin cookies - usando configuración predeterminada de yt-dlp')
            text_capture = io.StringIO()
            info = None
            with redirect_stdout(text_capture), yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            info = self._normalize_info_dict(info)
                    except Exception as e:
                        print(f'\nError interno de yt-dlp: {e}')
            if self.cancellation_event.is_set():
                raise UserCancelledError('Análisis cancelado por el usuario.')
            else:
                captured_text = text_capture.getvalue()
                other_lines = captured_text.strip().splitlines()
                if info is None:
                    raise Exception(f"yt-dlp falló: {' '.join(other_lines)}")
                else:
                    formats_raw = info.get('formats', [])
                    print(f'\n🔍 DEBUG: Formatos RAW recibidos de yt-dlp: {len(formats_raw)}')
                    storyboard_formats = [f for f in formats_raw if f.get('format_id', '').startswith('sb')]
                    non_storyboard_formats = [f for f in formats_raw if not f.get('format_id', '').startswith('sb')]
                    if storyboard_formats:
                        print(f'   ⚠️ {len(storyboard_formats)} storyboards detectados')
                    if non_storyboard_formats:
                        print(f'   ✅ {len(non_storyboard_formats)} formatos reales encontrados')
                        info['formats'] = non_storyboard_formats
                        formats_raw = non_storyboard_formats
                    else:
                        if storyboard_formats and is_youtube and using_cookies:
                                    print(f"\n{'============================================================'}")
                                    print('❌ ERROR: YouTube devolvió SOLO storyboards')
                                    print(f"{'============================================================'}")
                                    print('Posibles causas:')
                                    print('1. Las cookies están expiradas o inválidas')
                                    print('2. El navegador debe estar cerrado al usar cookies')
                                    print('3. Las cookies no coinciden con la cuenta/región')
                                    print('\nSoluciones:')
                                    print('• Actualizar cookies (volver a iniciar sesión)')
                                    print('• Cerrar completamente el navegador')
                                    print('• Probar sin cookies temporalmente')
                                    print(f"{'============================================================'}\n")
                    for idx, f in enumerate(formats_raw[:10]):
                        print(f"  [{idx}] id={f.get('format_id')}, ext={f.get('ext')}, vcodec={f.get('vcodec')}, acodec={f.get('acodec')}, resolution={f.get('resolution')}")
                    if len(formats_raw) > 10:
                        print(f'  ... y {len(formats_raw) - 10} formatos más')
                    if 'subtitles' not in info and 'automatic_captions' not in info:
                            info['subtitles'], info['automatic_captions'] = self._parse_subtitle_lines_from_text(other_lines)
                    if info.get('is_live'):
                        self.app.after(0, lambda: self.on_analysis_complete(None, 'AVISO: La URL apunta a una transmisión en vivo.'))
                        return
                    else:
                        self.app.after(0, self.on_analysis_complete, info)
        except UserCancelledError:
            self.app.after(0, lambda: self.on_process_finished(False, 'Análisis cancelado.', None, show_dialog=False))
        except Exception as e:
            error_message = f'ERROR: {e}'
            if isinstance(e, yt_dlp.utils.DownloadError):
                error_message = f"ERROR de yt-dlp: {str(e).replace('ERROR:', '').strip()}"
            self.app.after(0, lambda: self.on_analysis_complete(None, error_message))
        finally:
            self.active_subprocess_pid = None
    def on_analysis_complete(self, info, error_message=None):
        """
        Callback que se ejecuta cuando el análisis de formato ha terminado.
        info: diccionario con la información del video (o None si error)
        error_message: mensaje de error (opcional)
        """
        # --- Restaurar estado del botón de análisis ---
        self.analyze_button.configure(
            text=self.original_analyze_text,
            fg_color=self.original_analyze_fg_color,
            command=self.original_analyze_command,
            state='normal'
        )
        self.progress_bar.stop()

        if error_message:
            self.update_progress(0, f'Error: {error_message}')
            self.progress_label.configure(text=f'❌ {error_message}')
            self.download_button.configure(state='disabled')
            self.analysis_is_complete = False
            # Limpiar menús de formatos
            self.video_quality_menu.configure(values=['-'], state='disabled')
            self.audio_quality_menu.configure(values=['-'], state='disabled')
            self._clear_subtitle_menus()
            self.create_placeholder_label('❌')
            return

        if not info:
            self.update_progress(0, 'No se obtuvo información del video.')
            self.progress_label.configure(text='❌ No se obtuvo información del video.')
            self.download_button.configure(state='disabled')
            self.analysis_is_complete = False
            self.create_placeholder_label('❌')
            return

        # --- Guardar información en caché y en atributos ---
        url = self.url_entry.get()
        if url:
            self.analysis_cache[url] = {'data': info, 'timestamp': time.time()}

        # --- Extraer datos básicos ---
        title = info.get('title', 'video_descargado')
        clean_title = self.app.sanitize_title_global(title)
        self.title_entry.delete(0, 'end')
        self.title_entry.insert(0, clean_title)

        # Duración y dimensiones
        self.video_duration = info.get('duration', 0)
        width = info.get('width', 0)
        height = info.get('height', 0)
        if width and height:
            self.original_video_width = width
            self.original_video_height = height

        # --- Determinar si tiene video/audio ---
        formats = info.get('formats', [])
        has_video = any(f.get('vcodec') not in ('none', None) for f in formats)
        has_audio = any(f.get('acodec') not in ('none', None) for f in formats)

        # --- Poblar menús de formatos ---
        try:
            self.populate_format_menus(info, has_video, has_audio)
        except Exception as e:
            self.update_progress(0, f'Error al procesar formatos: {e}')
            self.progress_label.configure(text=f'❌ Error al procesar formatos: {e}')
            self.download_button.configure(state='disabled')
            self.analysis_is_complete = False
            return

        # --- Cargar miniatura ---
        thumbnail_url = info.get('thumbnail')
        if thumbnail_url:
            threading.Thread(
                target=lambda: self.load_thumbnail(thumbnail_url, is_local=False),
                daemon=True
            ).start()
        else:
            self.create_placeholder_label('🎬')

        # --- Detectar si es una playlist ---
        entries = info.get('entries')
        if entries and len(entries) > 1:
            self.analysis_was_playlist = True
            self.progress_label.configure(text='ℹ️ Esta URL contiene varios videos')
            self.download_button.configure(state='disabled')
            # Opción para enviar a lotes
            self.analyze_button.configure(
                text='Enviar a Lotes',
                command=lambda: self._send_url_to_batch(url)
            )
        else:
            self.analysis_was_playlist = False
            self.progress_label.configure(text='✅ Análisis completado')

        # --- Habilitar descarga ---
        self.analysis_is_complete = True
        self.download_button.configure(state='normal')
        self.update_download_button_state()

        # --- Actualizar estado de subtítulos ---
        if self.all_subtitles:
            self.auto_download_subtitle_check.configure(state='normal')
        else:
            self.auto_download_subtitle_check.configure(state='disabled')
            self.auto_download_subtitle_check.deselect()
        self.toggle_manual_subtitle_button()

        # --- Guardar configuración ---
        self.save_settings()
    def _normalize_info_dict(self, info):
        """\n        Normaliza el diccionario de info...\n        """
        if not info:
            return info
        else:
            info = apply_site_specific_rules(info)
            formats = info.get('formats', [])
            if formats:
                return info
            else:
                url = info.get('url')
                ext = info.get('ext')
                vcodec = info.get('vcodec', 'none')
                acodec = info.get('acodec')
                is_audio_content = False
                if url and ext and (vcodec == 'none' or not vcodec) and acodec and (acodec != 'none'):
                    is_audio_content = True
                else:
                    if ext in self.app.AUDIO_EXTENSIONS:
                        is_audio_content = True
                        if not acodec or acodec == 'none':
                            acodec = {'mp3': 'mp3', 'opus': 'opus', 'aac': 'aac', 'm4a': 'aac'}.get(ext, ext)
                    else:
                        if info.get('extractor_key', '').lower() in ['applepodcasts', 'soundcloud', 'audioboom', 'spreaker', 'libsyn']:
                            is_audio_content = True
                            if not acodec:
                                acodec = 'mp3'
                if is_audio_content:
                    print(f'DEBUG: 🎵 Contenido de audio directo detectado (ext={ext}, acodec={acodec})')
                    synthetic_format = {'format_id': '0', 'url': url or info.get('manifest_url') or '', 'ext': ext or 'mp3', 'vcodec': 'none', 'acodec': acodec or 'unknown', 'abr': info.get('abr'), 'tbr': info.get('tbr'), 'filesize': info.get('filesize'), 'filesize_approx': info.get('filesize_approx'), 'protocol': info.get('protocol', 'https'), 'format_note': info.get('format_note', 'Audio directo')}
                    info['formats'] = [synthetic_format]
                    print(f"DEBUG: ✅ Formato sintético creado: {synthetic_format['format_id']}")
                else:
                    if info.get('is_live') and info.get('manifest_url'):
                            print('DEBUG: 🔴 Livestream detectado sin formats')
                            synthetic_format = {'format_id': 'live', 'url': info.get('manifest_url'), 'ext': info.get('ext', 'mp4'), 'protocol': 'm3u8_native', 'format_note': 'Livestream'}
                            info['formats'] = [synthetic_format]
                return info
    def _parse_subtitle_lines_from_text(self, lines):
        """\n        Parsea una lista de líneas de texto (salida de --list-subs) y la convierte\n        en diccionarios de subtítulos manuales y automáticos.\n        """
        subtitles = {}
        auto_captions = {}
        current_section = None
        for line in lines:
            if 'Available subtitles for' in line:
                current_section = 'subs'
            else:
                if 'Available automatic captions for' in line:
                    current_section = 'auto'
                    continue
                else:
                    if line.startswith('Language') or line.startswith('ID') or line.startswith('---'):
                        continue
                    else:
                        parts = re.split('\\s+', line.strip())
                        if len(parts) < 3:
                            continue
                        else:
                            lang_code = parts[0]
                            formats = [p.strip() for p in parts[1:(-1)] if p.strip()]
                            if current_section == 'subs':
                                target_dict = subtitles
                            else:
                                if current_section == 'auto':
                                    target_dict = auto_captions
                                else:
                                    continue
                            if lang_code not in target_dict:
                                target_dict[lang_code] = []
                            for fmt in formats:
                                target_dict[lang_code].append({'ext': fmt, 'url': None, 'name': ''})
        return (subtitles, auto_captions)
    def load_thumbnail(self, path_or_url, is_local=False):
        try:
            # Limpiar backup anterior
            if hasattr(self, '_original_image_backup'):
                self._original_image_backup = None
                print('DEBUG: Backup de imagen limpiado')

            # Destruir etiqueta de hover si existe
            if hasattr(self, '_hover_text_label') and self._hover_text_label is not None:
                try:
                    if self._hover_text_label.winfo_exists():
                        self._hover_text_label.destroy()
                except:
                    pass
                self._hover_text_label = None

            self.app.after(0, self.create_placeholder_label, 'Cargando miniatura...')

            # Obtener datos de imagen (local o remota)
            if is_local:
                with open(path_or_url, 'rb') as f:
                    img_data = f.read()
            else:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://imgur.com/'
                }
                max_retries = 2
                timeout = 15
                img_data = None
                for attempt in range(max_retries):
                    try:
                        response = requests.get(path_or_url, headers=headers, timeout=timeout, allow_redirects=True)
                        response.raise_for_status()
                        img_data = response.content
                        break
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429:
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt
                                print(f'⚠️ Rate limit en miniatura. Reintentando en {wait_time}s...')
                                time.sleep(wait_time)
                            else:
                                raise Exception('Rate limit de Imgur (429). La miniatura no está disponible temporalmente.')
                        else:
                            raise
                    except requests.exceptions.Timeout:
                        if attempt < max_retries - 1:
                            print('⚠️ Timeout descargando miniatura. Reintentando...')
                        else:
                            raise Exception('Timeout al descargar la miniatura')
                if img_data is None:
                    raise Exception('No se pudo obtener la miniatura')

            if not img_data or len(img_data) < 100:
                raise Exception('La miniatura descargada está vacía o corrupta')

            # Procesar imagen
            from PIL import Image
            from io import BytesIO
            self.pil_image = Image.open(BytesIO(img_data))
            display_image = self.pil_image.copy()
            display_image.thumbnail((320, 180), Image.Resampling.LANCZOS)

            import customtkinter as ctk
            ctk_image = ctk.CTkImage(light_image=display_image, dark_image=display_image, size=display_image.size)

            def set_new_image():
                if self.thumbnail_label:
                    self.thumbnail_label.destroy()
                parent_widget = self.dnd_overlay if hasattr(self, 'dnd_overlay') else self.thumbnail_container
                self.thumbnail_label = ctk.CTkLabel(parent_widget, text='', image=ctk_image)
                self.thumbnail_label.pack(expand=True)
                self.thumbnail_label.image = ctk_image
                print(f'DEBUG: ✅ Miniatura cargada. self.pil_image existe: {self.pil_image is not None}, is_local: {is_local}')
                self.save_thumbnail_button.configure(state='normal')
                if hasattr(self, 'send_thumbnail_to_imagetools_button'):
                    self.send_thumbnail_to_imagetools_button.configure(state='normal')
                self.toggle_manual_thumbnail_button()

            self.app.after(0, set_new_image)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
            if status_code == 429:
                placeholder = '⏳'
                msg = 'Rate limit (429)'
            elif status_code == 404:
                placeholder = '❌'
                msg = 'Miniatura no encontrada (404)'
            elif status_code in (403, 401):
                placeholder = '🔒'
                msg = f'Acceso denegado ({status_code})'
            else:
                placeholder = '❌'
                msg = f'Error HTTP {status_code}'
            print(f'⚠️ Error al cargar miniatura: {msg} - URL: {path_or_url}')
            self.app.after(0, self.create_placeholder_label, placeholder, font_size=60)

        except requests.exceptions.Timeout:
            print(f'⚠️ Timeout al cargar miniatura: {path_or_url}')
            self.app.after(0, self.create_placeholder_label, '⏱️', font_size=60)

        except Exception as e:
            print(f'⚠️ Error al cargar miniatura: {e}')
            self.app.after(0, self.create_placeholder_label, '❌', font_size=60)
    def _classify_format(self, f):
        """
        Clasifica un formato (v3.2 - Manejo de codecs 'unknown')
        """
        ext = f.get('ext', '')
        vcodec = f.get('vcodec', '')
        acodec = f.get('acodec', '')
        format_id = (f.get('format_id') or '').lower()
        format_note = (f.get('format_note') or '').lower()
        protocol = f.get('protocol', '')

        # Casos especiales por nota
        if 'audio directo' in format_note or 'livestream' in format_note:
            return 'AUDIO' if 'audio' in format_note else 'VIDEO'

        # Clasificación por vcodec
        vcodec_special = {'audio only': 'AUDIO', 'images': 'VIDEO', 'slideshow': 'VIDEO'}
        if vcodec in vcodec_special:
            return vcodec_special[vcodec]

        # GIF o similar
        if ext == 'gif' or vcodec == 'gif':
            return 'VIDEO'

        # Si tiene dimensiones, probablemente vídeo
        if f.get('height') or f.get('width'):
            vcodec_is_unknown = not vcodec or vcodec in ['unknown', 'N/A', '']
            acodec_is_unknown = not acodec or acodec in ['unknown', 'N/A', '']
            if vcodec_is_unknown and acodec_is_unknown:
                print(f"DEBUG: Formato {f.get('format_id')} con codecs desconocidos → asumiendo VIDEO combinado")
                return 'VIDEO'
            return 'VIDEO_ONLY' if acodec in ['none'] else 'VIDEO'

        # Si es live, vídeo
        if f.get('is_live') or 'live' in format_id:
            return 'VIDEO'

        # Buscar patrones de resolución
        resolution_patterns = ['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p', '4320p']
        if any(res in format_note for res in resolution_patterns):
            return 'VIDEO_ONLY' if acodec in ['none'] else 'VIDEO'

        # Análisis por palabras clave en format_id/note
        if 'audio' in format_id or 'audio' in format_note:
            return 'AUDIO'
        if 'video' in format_id or 'video' in format_note:
            return 'VIDEO_ONLY' if acodec in ['none'] else 'VIDEO'

        # Extensiones conocidas
        # Definir listas por defecto si no existen en self.app
        audio_exts = getattr(self.app, 'AUDIO_EXTENSIONS', ('.mp3', '.m4a', '.aac', '.opus', '.flac', '.wav', '.ogg'))
        video_exts = getattr(self.app, 'VIDEO_EXTENSIONS', ('.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv', '.m4v'))

        if ext in audio_exts:
            return 'AUDIO'
        if ext in video_exts:
            return 'VIDEO'

        # Si vcodec o acodec tienen valores válidos
        valid_vcodecs = {'h264', 'h265', 'vp8', 'vp9', 'av1', 'hevc', 'mpeg4', 'xvid', 'theora'}
        valid_acodecs = {'aac', 'mp3', 'opus', 'vorbis', 'flac', 'ac3', 'eac3', 'pcm'}
        vcodec_lower = (vcodec or '').lower()
        acodec_lower = (acodec or '').lower()

        if vcodec_lower in valid_vcodecs:
            return 'VIDEO_ONLY' if acodec_lower not in valid_acodecs else 'VIDEO'
        if acodec_lower in valid_acodecs:
            return 'AUDIO'

        # Protocolos de streaming
        if 'm3u8' in protocol or 'dash' in protocol:
            return 'VIDEO'

        # Basado en tasas de bits
        if f.get('tbr') and not f.get('abr'):
            return 'VIDEO'
        if f.get('abr') and not f.get('vbr'):
            return 'AUDIO'

        # Último recurso: asumir por extensión si es video o audio
        if ext in video_exts:
            print(f"⚠️ ADVERTENCIA: Formato {f.get('format_id')} ambiguo → asumiendo VIDEO combinado por extensión")
            return 'VIDEO'

        # Si llegamos aquí, no clasificado
        print(f"⚠️ ADVERTENCIA: Formato sin clasificación clara: {f.get('format_id')} (vcodec={vcodec}, acodec={acodec}, ext={ext})")
        return 'UNKNOWN'
    def populate_format_menus(self, info, has_video, has_audio):
        is_live = info.get('is_live', False)
        if is_live:
            self.video_duration = 0
            print('DEBUG: 🔴 Contenido en vivo detectado (duración desconocida)')
        formats = info.get('formats', [])
        if not formats:
            error_msg = 'Error: No se pudieron extraer formatos de esta URL'
            if is_live:
                error_msg = 'Error: No se puede analizar este livestream (puede estar offline)'
            else:
                if info.get('extractor_key', '').lower() in ['applepodcasts', 'soundcloud']:
                    error_msg = 'Error: El extractor no devolvió información de formatos'
            print(f'⚠️ ADVERTENCIA: {error_msg}')
            self.progress_label.configure(text=error_msg)
            self._clear_subtitle_menus()
            return
        else:
            print(f'\nDEBUG: Total de formatos recibidos: {len(formats)}')
            for f in formats:
                format_id = f.get('format_id', 'unknown')
                format_type = self._classify_format(f)
                vcodec = f.get('vcodec', 'N/A')
                acodec = f.get('acodec', 'N/A')
                height = f.get('height', 'N/A')
                protocol = f.get('protocol', 'N/A')
                print(f'  {format_id}: type={format_type}, vcodec={vcodec}, acodec={acodec}, height={height}, protocol={protocol}')
            has_any_audio_source = False
            for f in formats:
                format_type = self._classify_format(f)
                if format_type == 'AUDIO':
                    has_any_audio_source = True
                    break
                else:
                    if format_type == 'VIDEO':
                        acodec = f.get('acodec')
                        if acodec and acodec != 'none':
                                has_any_audio_source = True
                                break
            print(f'DEBUG: 🔊 has_any_audio_source = {has_any_audio_source}')
            video_entries, audio_entries = ([], [])
            self.video_formats.clear()
            self.audio_formats.clear()
            self.combined_variants = {}
            for f in formats:
                format_type = self._classify_format(f)
                if format_type in ['VIDEO', 'VIDEO_ONLY']:
                    vcodec_raw = f.get('vcodec')
                    acodec_raw = f.get('acodec')
                    vcodec = vcodec_raw.split('.')[0] if vcodec_raw else 'none'
                    acodec = acodec_raw.split('.')[0] if acodec_raw else 'none'
                    is_combined = acodec != 'none' and acodec is not None
                    if is_combined:
                        fps = f.get('fps')
                        height = f.get('height', 0)
                        fps_val = int(fps) if fps else 0
                        ext = f.get('ext', 'N/A')
                        tbr = f.get('tbr', 0)
                        tbr_rounded = round(tbr / 100) * 100 if tbr else 0
                        quality_key = f'{height}p{fps_val}_{ext}_{vcodec}_{acodec}_tbr{tbr_rounded}'
                        if quality_key not in self.combined_variants:
                            self.combined_variants[quality_key] = []
                        self.combined_variants[quality_key].append(f)
            real_multilang_keys = set()
            for quality_key, variants in self.combined_variants.items():
                unique_languages = set()
                for variant in variants:
                    lang = variant.get('language', '')
                    if lang:
                        unique_languages.add(lang)
                if len(unique_languages) >= 2:
                    real_multilang_keys.add(quality_key)
                    print(f'DEBUG: Grupo multiidioma detectado: {quality_key} con idiomas {unique_languages}')
            combined_keys_seen = set()
            for f in formats:
                format_type = self._classify_format(f)
                size_mb_str = 'Tamaño desc.'
                size_sort_priority = 0
                filesize = f.get('filesize') or f.get('filesize_approx')
                if filesize:
                    size_mb_str = f'{filesize / 1048576:.2f} MB'
                    size_sort_priority = 2
                else:
                    bitrate = f.get('tbr') or f.get('vbr') or f.get('abr')
                    if bitrate and self.video_duration:
                            estimated_bytes = bitrate * 1000 / 8 * self.video_duration
                            size_mb_str = f'Aprox. {estimated_bytes / 1048576:.2f} MB'
                            size_sort_priority = 1
                vcodec_raw = f.get('vcodec')
                acodec_raw = f.get('acodec')
                vcodec = vcodec_raw.split('.')[0] if vcodec_raw else 'none'
                acodec = acodec_raw.split('.')[0] if acodec_raw else 'none'
                ext = f.get('ext', 'N/A')
                if format_type in ['VIDEO', 'VIDEO_ONLY']:
                    is_combined = acodec != 'none' and acodec is not None
                    fps = f.get('fps')
                    fps_tag = f'{fps:.0f}' if fps else ''
                    quality_key = None
                    if is_combined:
                        height = f.get('height', 0)
                        fps_val = int(fps) if fps else 0
                        tbr = f.get('tbr', 0)
                        tbr_rounded = round(tbr / 100) * 100 if tbr else 0
                        quality_key = f'{height}p{fps_val}_{ext}_{vcodec}_{acodec}_tbr{tbr_rounded}'
                        if quality_key in real_multilang_keys:
                            if quality_key in combined_keys_seen:
                                continue
                            else:
                                combined_keys_seen.add(quality_key)
                    label_base = f"{f.get('height', 'Video')}p{fps_tag} ({ext}"
                    label_codecs = f', {vcodec}+{acodec}' if is_combined else f', {vcodec}'
                    no_audio_tag = ''
                    if format_type == 'VIDEO_ONLY' and (not has_any_audio_source):
                            no_audio_tag = ' [Sin Audio]'
                    audio_lang_tag = ''
                    if is_combined and quality_key:
                            if quality_key in real_multilang_keys:
                                audio_lang_tag = ' [Multiidioma]'
                            else:
                                lang_code = f.get('language')
                                if lang_code:
                                    norm_code = lang_code.replace('_', '-').lower()
                                    lang_name = self.app.LANG_CODE_MAP.get(norm_code, self.app.LANG_CODE_MAP.get(norm_code.split('-')[0], lang_code))
                                    audio_lang_tag = f' | Audio: {lang_name}'
                    label_tag = ' [Combinado]' if is_combined else ''
                    note = f.get('format_note') or ''
                    note_tag = ''
                    informative_keywords = ['hdr', 'premium', 'dv', 'hlg', 'storyboard']
                    if any((keyword in note.lower() for keyword in informative_keywords)):
                        note_tag = f' [{note}]'
                    protocol = f.get('protocol', '')
                    protocol_tag = ' [Streaming]' if 'm3u8' in protocol else ''
                    label = f'{label_base}{label_codecs}){label_tag}{audio_lang_tag}{no_audio_tag}{note_tag}{protocol_tag} - {size_mb_str}'
                    tags = []
                    compatibility_issues, unknown_issues = self._get_format_compatibility_issues(f)
                    if not compatibility_issues and (not unknown_issues):
                        tags.append('✨')
                    else:
                        if compatibility_issues or unknown_issues:
                            tags.append('⚠️')
                    if tags:
                        label += f" {' '.join(tags)}"
                    video_entries.append({'label': label, 'format': f, 'is_combined': is_combined, 'sort_priority': size_sort_priority, 'quality_key': quality_key})
                else:
                    if format_type == 'AUDIO':
                        format_id = f.get('format_id', 'unknown')
                        lang_code_raw = f.get('language')
                        format_note = f.get('format_note', '')
                        print(f'DEBUG AUDIO: id={format_id}, language={lang_code_raw}, format_note={format_note}')
                        abr = f.get('abr') or f.get('tbr')
                        lang_code = f.get('language')
                        lang_name = 'Idioma Desconocido'
                        if lang_code:
                            norm_code = lang_code.replace('_', '-').lower()
                            lang_name = self.app.LANG_CODE_MAP.get(norm_code, self.app.LANG_CODE_MAP.get(norm_code.split('-')[0], lang_code))
                            print(f'  → norm_code={norm_code}, mapeado a: {lang_name}')
                        else:
                            print('  → Sin código de idioma')
                        lang_prefix = f'{lang_name} - ' if lang_code else ''
                        note = f.get('format_note') or ''
                        drc_tag = ' (DRC)' if 'DRC' in note else ''
                        protocol = f.get('protocol', '')
                        protocol_tag = ' [Streaming]' if 'm3u8' in protocol else ''
                        label = f'{lang_prefix}{abr:.0f}kbps ({acodec}, {ext}){drc_tag}{protocol_tag}' if abr else f'{lang_prefix}Audio ({acodec}, {ext}){drc_tag}{protocol_tag}'
                        if acodec in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_acodecs']:
                            label += ' ✨'
                        else:
                            label += ' ⚠️'
                        audio_entries.append({'label': label, 'format': f, 'sort_priority': size_sort_priority})
                        abr = f.get('abr') or f.get('tbr')
                        lang_code = f.get('language')
                        lang_name = 'Idioma Desconocido'
                        if lang_code:
                            norm_code = lang_code.replace('_', '-').lower()
                            lang_name = self.app.LANG_CODE_MAP.get(norm_code, self.app.LANG_CODE_MAP.get(norm_code.split('-')[0], lang_code))
                        lang_prefix = f'{lang_name} - ' if lang_code else ''
                        note = f.get('format_note') or ''
                        drc_tag = ' (DRC)' if 'DRC' in note else ''
                        protocol = f.get('protocol', '')
                        protocol_tag = ' [Streaming]' if 'm3u8' in protocol else ''
                        label = f'{lang_prefix}{abr:.0f}kbps ({acodec}, {ext}){drc_tag}{protocol_tag}' if abr else f'{lang_prefix}Audio ({acodec}, {ext}){drc_tag}{protocol_tag}'
                        if acodec in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_acodecs']:
                            label += ' ✨'
                        else:
                            label += ' ⚠️'
                        audio_entries.append({'label': label, 'format': f, 'sort_priority': size_sort_priority})
            video_entries.sort(key=lambda e: (-(e['format'].get('height') or 0), 1 if '[Combinado]' in e['label'] else 0, 0 if '✨' in e['label'] else 1, -(e['format'].get('tbr') or 0)))
            def custom_audio_sort_key(entry):
                f = entry['format']
                lang_code_raw = f.get('language') or ''
                norm_code = lang_code_raw.replace('_', '-')
                lang_priority = self.app.LANGUAGE_ORDER.get(norm_code, self.app.LANGUAGE_ORDER.get(norm_code.split('-')[0], self.app.DEFAULT_PRIORITY))
                quality = f.get('abr') or f.get('tbr') or 0
                return (lang_priority, -quality)
            audio_entries.sort(key=custom_audio_sort_key)
            self.video_formats = {e['label']: {k: e['format'].get(k) for k in ['format_id', 'vcodec', 'acodec', 'ext', 'width', 'height']} | {'is_combined': e.get('is_combined', False), 'quality_key': e.get('quality_key')} for e in video_entries}
            self.audio_formats = {e['label']: {k: e['format'].get(k) for k in ['format_id', 'acodec', 'ext']} for e in audio_entries}
            has_any_audio = bool(audio_entries) or any((v.get('is_combined', False) for v in self.video_formats.values()))
            print(f'DEBUG: audio_entries={len(audio_entries)}, has_any_audio={has_any_audio}')
            print(f"DEBUG: video_formats con audio combinado: {sum((1 for v in self.video_formats.values() if v.get('is_combined')))}")
            if not has_any_audio:
                self.mode_selector.set('Video+Audio')
                self.mode_selector.configure(state='disabled', values=['Video+Audio'])
                print('⚠️ ADVERTENCIA: No hay pistas de audio disponibles. Modo Solo Audio deshabilitado.')
            else:
                if not video_entries and audio_entries:
                    self.mode_selector.set('Solo Audio')
                    self.mode_selector.configure(state='disabled', values=['Solo Audio'])
                    print('✅ Solo hay audio. Modo Solo Audio activado.')
                else:
                    current_mode = self.mode_selector.get()
                    self.mode_selector.configure(state='normal', values=['Video+Audio', 'Solo Audio'])
                    self.mode_selector.set(current_mode)
                    print(f'✅ Ambos modos disponibles. Modo actual: {current_mode}')
            self.on_mode_change(self.mode_selector.get())
            self.on_mode_change(self.mode_selector.get())
            v_opts = list(self.video_formats.keys()) or ['- Sin Formatos de Video -']
            a_opts = list(self.audio_formats.keys()) or ['- Sin Pistas de Audio -']
            default_video_selection = v_opts[0]
            for option in v_opts:
                if '✨' in option:
                    default_video_selection = option
                    break
            target_audio = None
            candidate_original_incompatible = None
            candidate_preferred_compatible = None
            for entry in audio_entries:
                f = entry['format']
                label = entry['label']
                note = (f.get('format_note') or '').lower()
                acodec = str(f.get('acodec', '')).split('.')[0]
                is_original = 'original' in note
                is_compatible = acodec in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_acodecs']
                if is_original and is_compatible:
                        target_audio = label
                        break
                if is_original and candidate_original_incompatible is None:
                        candidate_original_incompatible = label
                if is_compatible and candidate_preferred_compatible is None:
                        candidate_preferred_compatible = label
            if target_audio:
                default_audio_selection = target_audio
            else:
                if candidate_original_incompatible:
                    default_audio_selection = candidate_original_incompatible
                else:
                    if candidate_preferred_compatible:
                        default_audio_selection = candidate_preferred_compatible
                    else:
                        default_audio_selection = a_opts[0]
            self.video_quality_menu.configure(state='normal' if self.video_formats else 'disabled', values=v_opts)
            self.video_quality_menu.set(default_video_selection)
            self.audio_quality_menu.configure(state='normal' if self.audio_formats else 'disabled', values=a_opts)
            self.audio_quality_menu.set(default_audio_selection)
            if self.video_formats.get(default_video_selection, {}).get('is_combined'):
                print('DEBUG: Forzando refresco de audio para variante combinada inicial...')
                self.on_video_quality_change(default_video_selection)
            self.all_subtitles = {}
            def process_sub_list(sub_list, is_auto):
                lang_code_map_3_to_2 = {'spa': 'es', 'eng': 'en', 'jpn': 'ja', 'fra': 'fr', 'deu': 'de', 'por': 'pt', 'ita': 'it', 'kor': 'ko', 'rus': 'ru'}
                for lang_code, subs in sub_list.items():
                    primary_part = lang_code.replace('_', '-').split('-')[0].lower()
                    grouped_lang_code = lang_code_map_3_to_2.get(primary_part, primary_part)
                    for sub_info in subs:
                        sub_info['lang'] = lang_code
                        sub_info['automatic'] = is_auto
                        self.all_subtitles.setdefault(grouped_lang_code, []).append(sub_info)
            process_sub_list(info.get('subtitles', {}), is_auto=False)
            process_sub_list(info.get('automatic_captions', {}), is_auto=True)
            def custom_language_sort_key(lang_code):
                priority = self.app.LANGUAGE_ORDER.get(lang_code, self.app.DEFAULT_PRIORITY)
                return (priority, lang_code)
            available_languages = sorted(self.all_subtitles.keys(), key=custom_language_sort_key)
            if available_languages:
                self.auto_download_subtitle_check.configure(state='normal')
                lang_display_names = [self.app.LANG_CODE_MAP.get(lang, lang) for lang in available_languages]
                self.subtitle_lang_menu.configure(state='normal', values=lang_display_names)
                self.subtitle_lang_menu.set(lang_display_names[0])
                self.on_language_change(lang_display_names[0])
            else:
                self._clear_subtitle_menus()
            self.toggle_manual_subtitle_button()
    def _send_url_to_batch(self, url: str):
        """\n        Toma una URL y la envía a la pestaña de Lotes para análisis\n        y la cambia a esa pestaña.\n        """
        try:
            print(f'INFO: Enviando URL a la pestaña de Lotes: {url}')
            batch_tab = self.app.batch_tab
            if not batch_tab:
                print('ERROR: No se encontró la pestaña de lotes (batch_tab).')
                return
            else:
                batch_tab.url_entry.delete(0, 'end')
                batch_tab.url_entry.insert(0, url)
                self.app.after(10, batch_tab._on_analyze_click)
                self.app.tab_view.set('Descarga por Lotes')
        except Exception as e:
            print(f'ERROR: No se pudo enviar la URL a Lotes: {e}')
    def manual_poppler_update_check(self):
        """Inicia una comprobación manual de la actualización de Poppler."""
        self.update_poppler_button.configure(state='disabled', text='Buscando...')
        self.poppler_status_label.configure(text='Poppler: Verificando...')
        self.active_downloads_state['ffmpeg']['active'] = False
        self.active_downloads_state['deno']['active'] = False
        self.active_downloads_state['poppler'] = {'text': '', 'value': 0.0, 'active': False}
        from src.core.setup import check_poppler_status
        def check_task():
            status_info = check_poppler_status(lambda text, val: self.update_setup_download_progress('poppler', text, val))
            self.app.after(0, self.app.on_poppler_check_complete, status_info)
        self.active_operation_thread = threading.Thread(target=check_task, daemon=True)
        self.active_operation_thread.start()
    def manual_inkscape_check(self):
        """Verificación manual de Inkscape."""
        self.check_inkscape_button.configure(state='disabled', text='Verificando...')
        self.inkscape_status_label.configure(text='Inkscape: Buscando...')
        from src.core.setup import check_inkscape_status
        def check_task():
            status_info = check_inkscape_status(lambda t, v: None)
            self.app.after(0, self.app.on_inkscape_check_complete, status_info)
        threading.Thread(target=check_task, daemon=True).start()
    def _toggle_extract_options(self, *args):
        """Muestra u oculta las opciones de calidad de JPG en el modo Extras."""
        selected_format = self.extract_format_menu.get()
        if selected_format.startswith('JPG'):
            self.extract_jpg_quality_frame.grid(row=2, column=0, columnspan=2, sticky='ew')
        else:
            self.extract_jpg_quality_frame.grid_remove()
    def _on_extract_frames_toggle(self):
        """Muestra u oculta el sub-panel de extraccion de fotogramas."""
        if self.extract_frames_checkbox.get():
            self.extract_frames_subpanel.grid()
        else:
            self.extract_frames_subpanel.grid_remove()
        self.update_download_button_state()
    def _on_upscale_video_toggle(self):
        """Muestra u oculta el sub-panel de reescalado de video."""
        if self.upscale_video_checkbox.get():
            self.upscale_video_subpanel.grid()
        else:
            self.upscale_video_subpanel.grid_remove()
        self.update_download_button_state()
    def _on_transparency_toggle(self):
        """Si se activa la transparencia, forzar contenedor MOV."""
        if self.upscale_transparency_checkbox.get():
            self.upscale_container_menu.set('MOV')
            self.upscale_container_menu.configure(state='disabled')
        else:
            self.upscale_container_menu.configure(state='normal')
    def _scan_upscayl_models(self):
        """Escanea la carpeta de modelos de Upscayl."""
        from main import UPSCALING_DIR
        import os
        from src.core.constants import UPSCAYL_MODELS_MAP
        upscayl_models_dir = os.path.join(UPSCALING_DIR, 'upscayl', 'models')
        if not os.path.exists(upscayl_models_dir):
            return []
        else:
            models = []
            custom_nicks = getattr(self.app, 'upscayl_custom_models', {})
            for filename in os.listdir(upscayl_models_dir):
                if filename.endswith('.param'):
                    raw_name = filename[:(-6)]
                    friendly_name = custom_nicks.get(raw_name) or UPSCAYL_MODELS_MAP.get(raw_name, raw_name)
                    if friendly_name in ['Anime Video V3 (x2)', 'Anime Video V3 (x3)']:
                        continue
                    else:
                        models.append(friendly_name)
            return sorted(list(set(models)))
    def _on_add_custom_model(self):
        """Inicia el proceso para añadir un modelo personalizado."""
        from src.core.setup import install_custom_upscayl_model
        if install_custom_upscayl_model(self.app):
            self.app.refresh_custom_models_across_tabs()
            model_names = self._scan_upscayl_models()
            if model_names:
                self.upscale_model_menu.set(model_names[(-1)])
    def _on_upscale_engine_change(self, engine: str, silent=False):
        """Carga modelos y ajusta visibilidad según el motor."""
        if engine == AI_ENGINE_HOLDER:
            self.upscale_add_custom_btn.grid_remove()
            self.upscale_model_menu.configure(values=[AI_MODEL_HOLDER])
            self.upscale_model_menu.set(AI_MODEL_HOLDER)
            self._on_upscale_model_change(AI_MODEL_HOLDER, engine=engine, silent=True)
            return
        else:
            engine_map = {'Waifu2x': WAIFU2X_MODELS, 'SRMD': SRMD_MODELS}
            if engine == 'Upscayl':
                self.upscale_add_custom_btn.grid(row=0, column=1, sticky='e')
                model_names = self._scan_upscayl_models()
                if not model_names:
                    model_names = ['Descargar Modelos']
                model_names = [AI_MODEL_HOLDER] + model_names
            else:
                self.upscale_add_custom_btn.grid_remove()
                models_dict = engine_map.get(engine, WAIFU2X_MODELS)
                model_names = [AI_MODEL_HOLDER] + list(models_dict.keys())
            self.upscale_model_menu.configure(values=model_names)
            self.upscale_model_menu.set(AI_MODEL_HOLDER)
            if engine in ['Waifu2x', 'SRMD']:
                self.upscale_denoise_label.grid()
                self.upscale_denoise_menu.grid()
            else:
                self.upscale_denoise_label.grid_remove()
                self.upscale_denoise_menu.grid_remove()
            self._on_upscale_model_change(AI_MODEL_HOLDER, engine=engine, silent=silent)
    def _on_upscale_model_change(self, selected_model_friendly: str, engine=None, silent=False):
        """\n        Actualiza las escalas validas y verifica si el motor esta instalado.\n        Si no esta, ofrece descarga (a menos que silent=True).\n        """
        if self.upscale_video_checkbox.get() != 1:
            return
        else:
            if selected_model_friendly == AI_MODEL_HOLDER:
                self.upscale_status_label.configure(text='Seleccione un modelo para continuar', text_color='gray')
                return
            else:
                if engine is None:
                    engine = self.upscale_engine_menu.get()
                engine_map = {'Waifu2x': ('waifu2x', 'waifu2x-ncnn-vulkan.exe'), 'SRMD': ('srmd', 'srmd-ncnn-vulkan.exe'), 'Upscayl': ('upscayl', 'upscayl-bin.exe')}
                engine_key = engine.split(' ')[0]
                folder, exe = engine_map.get(engine_key, ('upscayl', ''))
                exe_path = os.path.join(UPSCALING_DIR, folder, exe)
                is_installed = os.path.exists(exe_path)
                if is_installed:
                    self.upscale_status_label.configure(text='✅ Motor listo', text_color='gray')
                    self.upscale_delete_btn.configure(state='normal')
                else:
                    self.upscale_status_label.configure(text='⚠️ Motor no instalado', text_color='orange')
                    self.upscale_delete_btn.configure(state='disabled')
                    if not silent:
                        from src.core.setup import get_remote_file_size, format_size, check_and_download_upscaling_tools
                        tool_info = UPSCALING_TOOLS.get(engine_key)
                        if tool_info:
                            self.upscale_status_label.configure(text='Consultando tamaño...', text_color='#52a2f2')
                            self.update()
                            file_size = get_remote_file_size(tool_info['url'])
                            if engine_key == 'Upscayl':
                                size_str = '~300 MB (Motor + Modelos)'
                            else:
                                size_str = format_size(file_size)
                            Tooltip.hide_all()
                            user_response = messagebox.askyesno('Descargar Motor IA', f'El motor \'{engine_key}\' no está instalado.\n\nTamaño de descarga: {size_str}\n\n¿Deseas descargarlo ahora?')
                            if user_response:
                                self.upscale_status_label.configure(text='Iniciando descarga...', text_color='#52a2f2')
                                def download_thread():
                                    def progress_cb(text, val):
                                        self.app.after(0, lambda t=text: self.upscale_status_label.configure(text=t))
                                    success = check_and_download_upscaling_tools(progress_cb, target_tool=engine_key)
                                    if success:
                                        self.app.after(0, lambda: self._on_upscale_engine_change(engine, silent=True))
                                    else:
                                        self.app.after(0, lambda: self.upscale_status_label.configure(text='❌ Error descarga', text_color='red'))
                                threading.Thread(target=download_thread, daemon=True).start()
                            else:
                                self.upscale_status_label.configure(text='⚠️ Descarga cancelada', text_color='orange')
                engine_models_map = {'Waifu2x': WAIFU2X_MODELS, 'SRMD': SRMD_MODELS}
                if engine_key == 'Upscayl':
                    valid_scales = ['2x', '3x', '4x', '5x', '6x', '7x', '8x']
                else:
                    models_dict = engine_models_map.get(engine_key, WAIFU2X_MODELS)
                    valid_scales = models_dict.get(selected_model_friendly, {}).get('scales', ['2x', '4x'])
                self.upscale_scale_menu.configure(values=valid_scales)
                current_scale = self.upscale_scale_menu.get()
                if current_scale not in valid_scales:
                    self.upscale_scale_menu.set(valid_scales[0])
    def _open_model_folder(self, tool_type: str):
        """Abre la carpeta de modelos en el explorador."""
        engine_name = self.upscale_engine_menu.get().split(' ')[0]
        engine_folder_map = {'Waifu2x': 'waifu2x', 'SRMD': 'srmd', 'Upscayl': 'upscayl'}
        folder = engine_folder_map.get(engine_name, 'upscayl')
        target_dir = os.path.join(UPSCALING_DIR, folder)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        try:
            os.startfile(target_dir)
        except Exception as e:
            print(f'Error abriendo carpeta: {e}')
    def _delete_current_model(self, tool_type: str):
        """Borra el motor de IA seleccionado tras confirmar."""
        engine_name = self.upscale_engine_menu.get().split(' ')[0]
        engine_folder_map = {'Waifu2x': 'waifu2x', 'SRMD': 'srmd', 'Upscayl': 'upscayl'}
        folder = engine_folder_map.get(engine_name, '')
        if not folder:
            return
        else:
            target_dir = os.path.join(UPSCALING_DIR, folder)
            if not os.path.exists(target_dir):
                Tooltip.hide_all()
                messagebox.showinfo('Borrar Motor', f'El motor \'{engine_name}\' no parece estar instalado.')
                return
            else:
                Tooltip.hide_all()
                confirm = messagebox.askyesno('Confirmar Borrado', f'¿Estás seguro de que deseas borrar el motor \'{engine_name}\'?\n\nSe eliminarán todos los archivos del binario y modelos asociados.')
                if confirm:
                    try:
                        import shutil
                        shutil.rmtree(target_dir)
                        Tooltip.hide_all()
                        messagebox.showinfo('Motor Borrado', f'El motor \'{engine_name}\' ha sido eliminado correctamente.')
                        self._on_upscale_engine_change(self.upscale_engine_menu.get(), silent=True)
                    except Exception as e:
                        Tooltip.hide_all()
                        messagebox.showerror('Error al borrar', f'No se pudo eliminar la carpeta:\n{e}')
    def _execute_video_upscale_thread(self, options: dict):
        """\n        Hilo de trabajo para reescalado de video.\n        Bridge delgado: prepara rutas, instancia VideoUpscaler, llama upscale_video().\n        """
        downloaded_input_path = None
        clipped_temp_file = None
        try:
            output_dir = options.get('output_path', '')
            title = options.get('title', 'video')
            if self.local_file_path:
                input_path = self.local_file_path
                if not output_dir or self.save_in_same_folder_check.get() == 1:
                    output_dir = os.path.dirname(input_path)
                is_fragment_mode = options.get('fragment_enabled') and (options.get('start_time') or options.get('end_time'))
                if is_fragment_mode:
                    self.app.after(0, self.update_progress, 0, 'Recortando fragmento antes de reescalar...')
                    clipped_temp_file = self._execute_fragment_clipping(input_filepath=input_path, start_time=options.get('start_time'), end_time=options.get('end_time'))
                    input_path = clipped_temp_file
            else:
                self.app.after(0, self.update_progress, (-1), 'Descargando video para reescalar...')
                base_filename = self.sanitize_filename(title)
                downloaded_input_path, _ = self._perform_download(options, base_filename, audio_extraction_fallback=False)
                input_path = downloaded_input_path
            if self.cancellation_event.is_set():
                raise UserCancelledError('Cancelado por el usuario.')
            else:
                custom_name = options.get('upscale_output_name', '').strip()
                if custom_name:
                    out_stem = self.sanitize_filename(custom_name)
                else:
                    orig_stem = os.path.splitext(os.path.basename(input_path))[0]
                    scale_label = str(options.get('upscale_scale', '2')).replace('x', '')
                    out_stem = f'{orig_stem}_upscaled_x{scale_label}'
                desired_out_path = os.path.join(output_dir, out_stem + '.mp4')
                try:
                    out_path, _ = self._resolve_output_path(desired_out_path)
                except UserCancelledError:
                    raise UserCancelledError('Operación cancelada por el usuario (conflicto de archivo).')
                ffmpeg_dir = os.path.dirname(self.ffmpeg_processor.ffmpeg_path)
                upscaler = VideoUpscaler(ffmpeg_dir=ffmpeg_dir, upscaling_dir=UPSCALING_DIR, cancellation_event=self.cancellation_event, progress_callback=self.update_progress)
                final_path = upscaler.upscale_video(input_path, out_path, options)
                keep_originals = options.get('keep_originals', False)
                if downloaded_input_path and os.path.exists(downloaded_input_path):
                        if not keep_originals:
                            try:
                                os.remove(downloaded_input_path)
                            except Exception:
                                pass
                        else:
                            print(f'DEBUG [VideoUpscale] Original descargado conservado en: {downloaded_input_path}')
                self.app.after(0, self.on_process_finished, True, 'Video reescalado correctamente.', final_path)
        except UserCancelledError as e:
            self.app.after(0, self.on_process_finished, False, str(e), None, False)
        except Exception as e:
            cleaned_message = self._clean_ansi_codes(str(e))
            print(f'ERROR [VideoUpscale]: {cleaned_message}')
            self.app.after(0, self.on_process_finished, False, cleaned_message, None, True)
        finally:
            if clipped_temp_file and os.path.exists(clipped_temp_file):
                    try:
                        os.remove(clipped_temp_file)
                        print(f'DEBUG [VideoUpscale]: Fragmento temporal eliminado: {clipped_temp_file}')
                    except OSError as err:
                        print(f'ADVERTENCIA [VideoUpscale]: No se pudo eliminar el fragmento temporal: {err}')
    def _send_folder_to_image_tools(self):
        """\n        Toma la ruta de la carpeta (guardada en self.last_download_path)\n        y la envía a la pestaña de Herramientas de Imagen.\n        """
        folder_path = self.last_download_path
        if not folder_path or not os.path.isdir(folder_path):
            print(f'ERROR: No se encontró la ruta de la carpeta de fotogramas: {folder_path}')
            return
        else:
            if not hasattr(self.app, 'image_tab'):
                print('ERROR: No se puede encontrar la pestaña \'image_tab\' en la app principal.')
                return
            else:
                print(f'INFO: Enviando carpeta \'{folder_path}\' a Herramientas de Imagen.')
                self.app.image_tab.import_folder_from_path(folder_path)
    def _send_thumbnail_to_image_tools(self):
        """\n        Guarda temporalmente la miniatura y la envía a la pestaña de Herramientas de Imagen.\n        """
        if not self.pil_image:
            print('ERROR: No hay miniatura disponible para enviar.')
            return
        else:
            try:
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix='dowp_thumbnail_')
                temp_filename = 'miniatura.jpg'
                temp_path = os.path.join(temp_dir, temp_filename)
                self.pil_image.convert('RGB').save(temp_path, quality=95)
                print(f'DEBUG: Miniatura guardada temporalmente en: {temp_path}')
                if not hasattr(self.app, 'image_tab'):
                    print('ERROR: No se puede encontrar la pestaña \'image_tab\' en la app principal.')
                    messagebox.showerror('Error', 'La pestaña de Herramientas de Imagen no está disponible.')
                else:
                    print(f'INFO: Enviando miniatura (carpeta: {temp_dir}) a Herramientas de Imagen.')
                    self.app.image_tab.import_folder_from_path(temp_dir)
                    self.app.tab_view.set('Herramientas de Imagen')
                    print('✅ Miniatura enviada exitosamente a Herramientas de Imagen')
            except Exception as e:
                print(f'ERROR: No se pudo enviar la miniatura a Herramientas de Imagen: {e}')
                import traceback
                traceback.print_exc()
                messagebox.showerror('Error', f'No se pudo enviar la miniatura:\n{e}')
    def _execute_extraction_thread(self, options):
        """
        (HILO DE TRABAJO)
        Función dedicada para manejar el "Modo Extraer".
        """
        import os
        import threading

        process_successful = False
        downloaded_filepath = None
        final_output_directory = None
        temp_video_for_extraction = None
        filepath_to_process = None

        try:
            # --- Validar formato de extracción ---
            extract_format = options.get('extract_format', 'png')
            if extract_format not in ['png', 'jpg']:
                raise Exception(f'Formato inválido: {extract_format}')

            # --- Validar calidad JPG ---
            if extract_format == 'jpg':
                jpg_quality = options.get('extract_jpg_quality', '2')
                try:
                    quality_int = int(jpg_quality)
                    if not (1 <= quality_int <= 31):
                        self.app.after(0, self.update_progress, -1, f'⚠️ Calidad JPG inválida ({jpg_quality}). Usando calidad alta (2).')
                        options['extract_jpg_quality'] = '2'
                except (ValueError, TypeError):
                    options['extract_jpg_quality'] = '2'

            # --- Validar FPS ---
            fps = options.get('extract_fps')
            if fps:
                try:
                    fps_value = float(fps)
                    if fps_value <= 0:
                        raise ValueError('FPS debe ser positivo')
                except (ValueError, TypeError):
                    self.app.after(0, self.update_progress, -1, f'⚠️ FPS inválido ({fps}). Extrayendo todos los fotogramas.')
                    options['extract_fps'] = None

            # --- Caso: archivo local ---
            if self.local_file_path:
                print('DEBUG: [Modo Extraer] Iniciando desde archivo local.')
                filepath_to_process = self.local_file_path
                output_dir = self.output_path_entry.get()
                if self.save_in_same_folder_check.get() == 1:
                    output_dir = os.path.dirname(filepath_to_process)

                custom_folder_name = self.extract_folder_name_entry.get().strip()
                if custom_folder_name:
                    folder_name = self.sanitize_filename(custom_folder_name)
                else:
                    base_filename = self.sanitize_filename(options['title'])
                    folder_name = f'{base_filename}_frames'
                final_output_directory = os.path.join(output_dir, folder_name)

            # --- Caso: URL ---
            else:
                print('DEBUG: [Modo Extraer] Iniciando desde URL.')
                output_dir = options['output_path']
                base_filename = self.sanitize_filename(options['title'])
                custom_folder_name = self.extract_folder_name_entry.get().strip()
                folder_name = self.sanitize_filename(custom_folder_name) if custom_folder_name else f'{base_filename}_frames'

                # Resolver conflicto de nombre para la carpeta
                temp_check_path = os.path.join(output_dir, f'{folder_name}.check')
                final_download_path, backup_file_path = self._resolve_output_path(temp_check_path)
                final_folder_name = os.path.splitext(os.path.basename(final_download_path))[0]
                final_output_directory = os.path.join(output_dir, final_folder_name)

                # Descargar video temporal
                downloaded_filepath, temp_video_for_extraction = self._perform_download(
                    options,
                    f'{base_filename}_temp_video',
                    audio_extraction_fallback=False
                )
                filepath_to_process = downloaded_filepath

            # --- Verificar cancelación antes de extraer ---
            if self.cancellation_event.is_set():
                raise UserCancelledError('Proceso cancelado por el usuario.')

            # --- Ejecutar extracción ---
            self.app.after(0, self.update_progress, -1, 'Iniciando extracción de fotogramas...')
            extraction_options = {
                'input_file': filepath_to_process,
                'output_folder': final_output_directory,
                'image_format': options.get('extract_format'),
                'fps': options.get('extract_fps'),
                'jpg_quality': options.get('extract_jpg_quality'),
                'duration': self.video_duration,
                'pre_params': []
            }

            output_folder = self.ffmpeg_processor.execute_video_to_images(
                extraction_options,
                lambda p, m: self.update_progress(p, f'Extrayendo... {p:.1f}%'),
                self.cancellation_event
            )
            process_successful = True
            self.app.after(0, self.on_process_finished, True, 'Extracción completada.', output_folder)

        except UserCancelledError as e:
            self.app.after(0, self.on_process_finished, False, str(e), None)

        except Exception as e:
            cleaned_message = self._clean_ansi_codes(str(e))
            self.app.after(0, self.on_process_finished, False, cleaned_message, None)

        finally:
            # --- Limpieza del archivo temporal (si se descargó y no es local) ---
            if downloaded_filepath and os.path.exists(downloaded_filepath):
                # Decidir si eliminar o conservar el video original
                should_delete = not self.local_file_path and (not self.keep_original_extract_checkbox.get())
                if should_delete:
                    try:
                        os.remove(downloaded_filepath)
                        print(f'DEBUG: Archivo de video temporal eliminado: {downloaded_filepath}')
                    except OSError as e:
                        print(f'ADVERTENCIA: No se pudo eliminar el video temporal: {e}')
                else:
                    # Conservar y renombrar quitando "_temp_video"
                    try:
                        dir_path = os.path.dirname(downloaded_filepath)
                        old_basename = os.path.basename(downloaded_filepath)
                        if '_temp_video' in old_basename:
                            new_basename = old_basename.replace('_temp_video', '')
                            new_filepath = os.path.join(dir_path, new_basename)
                            if os.path.exists(new_filepath):
                                print(f'DEBUG: Ya existe un archivo con el nombre final, conservando con \'_temp_video\': {downloaded_filepath}')
                            else:
                                os.rename(downloaded_filepath, new_filepath)
                                print(f'DEBUG: Video renombrado de \'{old_basename}\' a \'{new_basename}\'')
                                downloaded_filepath = new_filepath
                        print(f'DEBUG: Video original conservado en: {downloaded_filepath}')
                    except Exception as e:
                        print(f'ADVERTENCIA: No se pudo renombrar el video conservado: {e}')
                        print(f'DEBUG: Video conservado con nombre temporal: {downloaded_filepath}')
    def _on_drag_enter(self, event):
        """Efecto visual cuando el archivo entra al área de drop"""
        print('DEBUG: 🎯 _on_drag_enter ejecutado')
        self.thumbnail_container.configure(border_width=4, border_color=self.DND_BORDER_COLOR)
        self.dnd_overlay.configure(bg=self.DND_BG_COLOR)
        if hasattr(self, 'thumbnail_label') and self.thumbnail_label and self.thumbnail_label.winfo_exists():
                    self.thumbnail_label.place_forget()
        if hasattr(self, '_drag_label') and self._drag_label and self._drag_label.winfo_exists():
                    self._drag_label.destroy()
        self._drag_label = ctk.CTkLabel(self.dnd_overlay, text='📂 Suelta tu archivo aquí\n\n(Video o Audio)', font=ctk.CTkFont(size=18, weight='bold'), text_color=self.DND_TEXT_COLOR)
        self._drag_label.place(relx=0.5, rely=0.5, anchor='center')
        self.dnd_overlay.lift()
    def _on_drag_leave(self, event):
        """Restaurar estilo normal cuando el archivo sale del área"""
        print('DEBUG: 🔙 _on_drag_leave ejecutado')
        self.thumbnail_container.configure(border_width=0)
        try:
            original_bg = self._get_ctk_fg_color(self.thumbnail_container)
            self.dnd_overlay.configure(bg=original_bg)
        except:
            self.dnd_overlay.configure(bg='#2B2B2B')
        if hasattr(self, '_drag_label') and self._drag_label and self._drag_label.winfo_exists():
                    self._drag_label.destroy()
                    self._drag_label = None
        if hasattr(self, 'thumbnail_label') and self.thumbnail_label and self.thumbnail_label.winfo_exists():
                    if self.pil_image:
                        self.thumbnail_label.pack(expand=True)
                    else:
                        self.thumbnail_label.pack(expand=True, fill='both')
    def _on_file_drop(self, event):
        """Maneja archivos arrastrados"""
        try:
            self._show_drop_feedback()
            files = self.tk.splitlist(event.data)
            if not files:
                print('DEBUG: No se detectaron archivos en el drop')
                self._hide_drop_feedback()
                return
            else:
                file_path = files[0].strip('{}')
                print(f'DEBUG: 📁 Archivo arrastrado: {file_path}')
                if not os.path.isfile(file_path):
                    print('ADVERTENCIA: Solo se aceptan archivos, no carpetas')
                    self.progress_label.configure(text='Solo se aceptan archivos')
                    self._hide_drop_feedback()
                    return
                else:
                    valid_extensions = VIDEO_EXTENSIONS.union(AUDIO_EXTENSIONS)
                    file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
                    if file_ext not in valid_extensions:
                        print(f'ADVERTENCIA: Formato no soportado: {file_ext}')
                        self.progress_label.configure(text=f'Formato \'.{file_ext}\' no soportado')
                        self._hide_drop_feedback()
                    else:
                        self._hide_drop_feedback()
                        self._import_file_from_path(file_path)
        except Exception as e:
            print(f'ERROR en drag & drop: {e}')
            import traceback
            traceback.print_exc()
            self._hide_drop_feedback()
    def _import_file_from_path(self, file_path):
        """\n        Importa un archivo local desde una ruta conocida (usado por drag & drop).\n        Similar a import_local_file pero sin diálogo.\n        """
        self.reset_to_url_mode()
        self.auto_save_thumbnail_check.pack_forget()
        self.cancellation_event.clear()
        self.progress_label.configure(text=f'Analizando archivo: {os.path.basename(file_path)}...')
        self.progress_bar.start()
        self.open_folder_button.configure(state='disabled')
        threading.Thread(target=self._process_local_file_info, args=(file_path,), daemon=True).start()
    def enable_drag_and_drop(self):
        """
        Habilita drag & drop en el overlay nativo de Tkinter.
        """
        from tkinterdnd2 import DND_FILES

        # Verificar que el overlay exista
        if not hasattr(self, 'dnd_overlay'):
            print('ERROR: dnd_overlay no fue creado. Verifica _create_widgets()')
            return

        try:
            # Intentar obtener la versión de tkdnd
            version = self.app.tk.call('package', 'present', 'tkdnd')
            print(f'DEBUG: TkinterDnD versión {version} detectada')
        except Exception as e:
            print(f'ERROR CRÍTICO: TkinterDnD no está cargado: {e}')
            return

        try:
            # Registrar el destino de arrastre y los eventos
            self.dnd_overlay.drop_target_register(DND_FILES)
            self.dnd_overlay.dnd_bind('<<Drop>>', self._on_file_drop)
            self.dnd_overlay.bind('<Enter>', self._on_mouse_enter)
            self.dnd_overlay.bind('<Leave>', self._on_mouse_leave)
            self.dnd_overlay.lift()
            print('DEBUG: [OK] Drag & Drop habilitado en el área de miniatura')
        except Exception as e:
            print(f'ERROR habilitando Drag & Drop: {e}')
            import traceback
            traceback.print_exc()
    def _on_mouse_enter(self, event):
        """
        Se ejecuta cuando el mouse entra en el área de drop.
        Muestra feedback visual: oscurece la imagen o muestra un mensaje.
        """
        import customtkinter as ctk
        from PIL import ImageEnhance

        # --- Validaciones iniciales ---
        if not hasattr(self, 'thumbnail_label') or not self.thumbnail_label:
            return
        try:
            if not self.thumbnail_label.winfo_exists():
                return
        except Exception:
            return  # Si la etiqueta fue destruida, salir

        # Si la etiqueta muestra un mensaje de carga, no hacer nada
        try:
            current_text = self.thumbnail_label.cget('text')
            if 'Analizando' in current_text or 'Cargando' in current_text:
                return
        except Exception:
            pass  # Si no se puede obtener el texto, continuar

        try:
            # --- Caso 1: No hay imagen ni archivo local → mostrar mensaje de arrastre ---
            if not self.pil_image and not self.local_file_path:
                self.thumbnail_label.configure(
                    text='Arrastra un archivo aquí (Video o Audio)\nPara activar el modo de Recodificación Local',
                    font=ctk.CTkFont(size=12, weight='bold'),
                    fg_color=self.DND_BG_COLOR
                )
                return

            # --- Caso 2: Hay imagen → oscurecer y mostrar overlay ---
            if self.pil_image:
                # Guardar copia de la imagen original si no existe
                if not hasattr(self, '_original_image_backup') or self._original_image_backup is None:
                    self._original_image_backup = self.pil_image.copy()
                    print(f'DEBUG: Imagen guardada para oscurecer (local={bool(self.local_file_path)})')

                if hasattr(self, '_original_image_backup') and self._original_image_backup:
                    enhancer = ImageEnhance.Brightness(self._original_image_backup)
                    darkened_image = enhancer.enhance(0.4)
                    display_image = darkened_image.copy()
                    display_image.thumbnail((320, 180), Image.Resampling.LANCZOS)
                    ctk_image = ctk.CTkImage(light_image=display_image, dark_image=display_image, size=display_image.size)
                    self.thumbnail_label.configure(image=ctk_image, text='')
                    self.thumbnail_label.image = ctk_image
                    print('DEBUG: Imagen oscurecida correctamente')

            # --- Crear o mostrar etiqueta de hover (si no existe) ---
            if not hasattr(self, '_hover_text_label') or self._hover_text_label is None:
                self._hover_text_label = ctk.CTkLabel(
                    self.dnd_overlay,
                    text='Arrastra un archivo aquí (Video o Audio)\nPara activar el modo de Recodificación Local',
                    font=ctk.CTkFont(size=12, weight='bold'),
                    text_color='#FFFFFF',
                    fg_color='transparent',
                    bg_color='transparent'
                )
                self._hover_text_label.place(relx=0.5, rely=0.5, anchor='center')
            else:
                # Asegurar que la etiqueta esté visible
                try:
                    if not self._hover_text_label.winfo_ismapped():
                        self._hover_text_label.place(relx=0.5, rely=0.5, anchor='center')
                except Exception:
                    # Si la etiqueta fue destruida, recrearla
                    self._hover_text_label = ctk.CTkLabel(
                        self.dnd_overlay,
                        text='Arrastra un archivo aquí (Video o Audio)\nPara activar el modo de Recodificación Local',
                        font=ctk.CTkFont(size=12, weight='bold'),
                        text_color='#FFFFFF',
                        fg_color='transparent',
                        bg_color='transparent'
                    )
                    self._hover_text_label.place(relx=0.5, rely=0.5, anchor='center')

            # Cambiar el color de fondo del área de drop
            self.thumbnail_label.configure(fg_color=self.DND_BG_COLOR)

        except Exception as e:
            print(f'DEBUG: Error en _on_mouse_enter: {e}')
            import traceback
            traceback.print_exc()
    def _on_mouse_leave(self, event):
        """
        Se ejecuta cuando el mouse sale del área de drop.
        Restaura la imagen original y elimina el overlay de hover.
        """
        import customtkinter as ctk
        from PIL import Image

        # --- Validaciones iniciales ---
        if not hasattr(self, 'thumbnail_label') or not self.thumbnail_label:
            return
        try:
            if not self.thumbnail_label.winfo_exists():
                return
        except Exception:
            return  # Si la etiqueta fue destruida, salir

        try:
            # Si la etiqueta muestra un mensaje de carga, no hacer nada
            current_text = self.thumbnail_label.cget('text')
            if 'Analizando' in current_text or 'Cargando' in current_text:
                return
        except Exception:
            pass  # Si no se puede obtener el texto, continuar

        try:
            # --- Caso 1: No hay imagen ni archivo local → restaurar mensaje genérico ---
            if not self.pil_image and not self.local_file_path:
                try:
                    original_bg = self._get_ctk_fg_color(self.thumbnail_container)
                    self.thumbnail_label.configure(
                        text='Miniatura',
                        font=ctk.CTkFont(size=14),
                        fg_color=original_bg
                    )
                except Exception:
                    # Fallback si no se puede obtener el color
                    self.thumbnail_label.configure(
                        text='Miniatura',
                        font=ctk.CTkFont(size=14),
                        fg_color='#2B2B2B'
                    )
                return

            # --- Caso 2: Hay imagen → restaurar la imagen original guardada ---
            if self.pil_image:
                if hasattr(self, '_original_image_backup') and self._original_image_backup:
                    display_image = self._original_image_backup.copy()
                    display_image.thumbnail((320, 180), Image.Resampling.LANCZOS)
                    ctk_image = ctk.CTkImage(
                        light_image=display_image,
                        dark_image=display_image,
                        size=display_image.size
                    )
                    self.thumbnail_label.configure(image=ctk_image, text='')
                    self.thumbnail_label.image = ctk_image
                    print('DEBUG: Imagen restaurada correctamente')

            # --- Eliminar la etiqueta de hover (si existe) ---
            if hasattr(self, '_hover_text_label') and self._hover_text_label is not None:
                try:
                    if self._hover_text_label.winfo_exists():
                        self._hover_text_label.destroy()
                except Exception:
                    pass
                self._hover_text_label = None

            # --- Restaurar el color de fondo del área de drop ---
            if not self.local_file_path or not self.pil_image:
                # Si no hay imagen local ni imagen cargada, restaurar el color de fondo
                try:
                    original_bg = self._get_ctk_fg_color(self.thumbnail_container)
                    self.thumbnail_label.configure(fg_color=original_bg)
                except Exception:
                    pass

            # Asegurar que la etiqueta de hover esté destruida (por si acaso)
            if hasattr(self, '_hover_text_label') and self._hover_text_label is not None:
                try:
                    if self._hover_text_label.winfo_exists():
                        self._hover_text_label.destroy()
                except Exception:
                    pass
                self._hover_text_label = None

        except Exception as e:
            print(f'DEBUG: Error en _on_mouse_leave: {e}')
            import traceback
            traceback.print_exc()
    def _show_drop_feedback(self):
        """Muestra feedback visual cuando se detecta un drop"""
        try:
            self.thumbnail_container.configure(border_width=2, border_color=self.DND_BORDER_COLOR)
            if hasattr(self, 'thumbnail_label') and self.thumbnail_label:
                    try:
                        if self.thumbnail_label.winfo_exists():
                            self.thumbnail_label.place_forget()
                    except:
                        pass
            if hasattr(self, '_drop_feedback_label') and self._drop_feedback_label:
                    try:
                        if self._drop_feedback_label.winfo_exists():
                            self._drop_feedback_label.destroy()
                    except:
                        pass
            self._drop_feedback_label = ctk.CTkLabel(self.dnd_overlay, text='Procesando archivo...', font=ctk.CTkFont(size=12, weight='bold'), fg_color='transparent', bg_color='transparent')
            self._drop_feedback_label.place(relx=0.5, rely=0.5, anchor='center')
        except Exception as e:
            print(f'DEBUG: Error en _show_drop_feedback: {e}')
    def _hide_drop_feedback(self):
        """Oculta el feedback visual del drop"""
        try:
            self.thumbnail_container.configure(border_width=0)

            # Destruir etiqueta de feedback si existe
            if hasattr(self, '_drop_feedback_label') and self._drop_feedback_label is not None:
                try:
                    if self._drop_feedback_label.winfo_exists():
                        self._drop_feedback_label.destroy()
                except Exception:
                    pass
                self._drop_feedback_label = None

            # Restaurar la etiqueta de miniatura
            if hasattr(self, 'thumbnail_label') and self.thumbnail_label is not None:
                if self.thumbnail_label.winfo_exists():
                    if self.pil_image:
                        self.thumbnail_label.pack(expand=True)
                    else:
                        self.thumbnail_label.pack(expand=True, fill='both')
        except Exception as e:
            print(f'DEBUG: Error en _hide_drop_feedback: {e}')
    def manual_ghostscript_check(self):
        """Verificación manual de Ghostscript."""
        self.check_ghostscript_button.configure(state='disabled', text='Verificando...')
        self.ghostscript_status_label.configure(text='Ghostscript: Buscando...')
        from src.core.setup import check_ghostscript_status
        def check_task():
            status_info = check_ghostscript_status(lambda t, v: None)
            self.app.after(0, self.app.on_ghostscript_check_complete, status_info)
        threading.Thread(target=check_task, daemon=True).start()
    def _open_ai_models_folder(self):
        """Abre la carpeta donde se guardan los modelos de IA."""
        if not os.path.exists(MODELS_DIR):
            try:
                os.makedirs(MODELS_DIR, exist_ok=True)
            except:
                pass
        print(f'INFO: Abriendo carpeta de modelos: {MODELS_DIR}')
        try:
            if os.name == 'nt':
                os.startfile(MODELS_DIR)
            else:
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', MODELS_DIR])
                else:
                    subprocess.Popen(['xdg-open', MODELS_DIR])
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo abrir la carpeta:\n{e}')
# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\gui\\batch_download_tab.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import customtkinter as ctk
import threading
import os
from tkinter import StringVar, Menu
from customtkinter import filedialog
from src.core.batch_processor import QueueManager, Job
import sys
import yt_dlp
import io
import time
import queue
import re
from tkinter import StringVar, Menu
from customtkinter import filedialog
from contextlib import redirect_stdout
from src.core.exceptions import UserCancelledError
from src.core.downloader import get_video_info, apply_site_specific_rules, apply_yt_patch
from src.core.batch_processor import Job
from src.core.constants import FAST_MODE_SUPPORTED_DOMAINS
from .dialogs import Tooltip, messagebox, PlaylistSelectionDialog
from src.core.tags_manager import TagsManager
import requests
from PIL import Image
from io import BytesIO
try:
    from tkinterdnd2 import DND_FILES
except ImportError:
    print('ERROR: tkinterdnd2 no encontrado en batch_tab')
    DND_FILES = None
INTERACTIVE_WIDGETS = (ctk.CTkButton, ctk.CTkEntry, ctk.CTkOptionMenu, ctk.CTkCheckBox, ctk.CTkSegmentedButton, ctk.CTkTextbox)
class BatchDownloadTab(ctk.CTkFrame):
    """\n    Contiene toda la UI y la lógica de interacción para la \n    pestaña de descarga por lotes.\n    """
    DOWNLOAD_BTN_COLOR = '#28A745'
    DOWNLOAD_BTN_HOVER = '#218838'
    PROCESS_BTN_COLOR = '#6F42C1'
    PROCESS_BTN_HOVER = '#59369A'
    CANCEL_BTN_COLOR = '#DC3545'
    CANCEL_BTN_HOVER = '#C82333'
    DISABLED_TEXT_COLOR = '#D3D3D3'
    DISABLED_FG_COLOR = '#565b5f'
    def __init__(self, master, app):
        super().__init__(master, fg_color='transparent')
        self.pack(expand=True, fill='both')
        self.app = app
        self.is_initializing = True
        self._load_theme_colors()
        self.last_download_path = None
        self.thumbnail_label = None
        self.current_thumbnail_url = None
        self.current_raw_thumbnail = None
        self.job_widgets = {}
        self.playlist_cache = {}
        self.selected_job_id = None
        self.current_video_formats = {}
        self.current_audio_formats = {}
        self.thumbnail_cache = {}
        self.thumb_queue = queue.Queue()
        self.current_thumb_job_id = None
        threading.Thread(target=self._thumbnail_worker_loop, daemon=True).start()
        self.combined_variants = {}
        self.combined_audio_map = {}
        self.has_video_streams = False
        self.has_audio_streams = False
        self.is_local_mode = False
        self._updating_ui = False
        self.grid_columnconfigure(0, weight=40, uniform='batch_cols')
        self.grid_columnconfigure(1, weight=60, uniform='batch_cols')
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=0)
        self.grid_rowconfigure(5, weight=0)
        self.queue_manager = QueueManager(main_app=app, ui_callback=self.update_job_ui)
        self.queue_manager.start_worker_thread()
        self._selection_timer_id = None
        self._last_ui_update_times = {}
        self.tags_manager = TagsManager(app)
        self._create_widgets()
        self._initialize_ui_settings()
        self._save_timer = None
        self.update_tags_combobox()
        self.is_initializing = False
    def _load_theme_colors(self):
        """Carga los colores desde el sistema de temas de la aplicación."""
        self.DOWNLOAD_BTN_COLOR = self.app.get_theme_color('DOWNLOAD_BTN', ['#28A745', '#218838'])
        self.DOWNLOAD_BTN_HOVER = self.app.get_theme_color('DOWNLOAD_BTN_HOVER', ['#218838', '#1E7E34'])
        self.DOWNLOAD_BTN_TEXT = self.app.get_theme_color('DOWNLOAD_BTN_TEXT', 'white')
        self.ANALYZE_BTN_COLOR = self.app.get_theme_color('ANALYZE_BTN', ['#007BFF', '#0069D9'])
        self.ANALYZE_BTN_HOVER = self.app.get_theme_color('ANALYZE_BTN_HOVER', ['#0069D9', '#0062CC'])
        self.ANALYZE_BTN_TEXT = self.app.get_theme_color('ANALYZE_BTN_TEXT', 'white')
        self.CANCEL_BTN_COLOR = self.app.get_theme_color('CANCEL_BTN', ['#DC3545', '#C82333'])
        self.CANCEL_BTN_HOVER = self.app.get_theme_color('CANCEL_BTN_HOVER', ['#C82333', '#BD2130'])
        self.CANCEL_BTN_TEXT = self.app.get_theme_color('CANCEL_BTN_TEXT', 'white')
        self.PROCESS_BTN_COLOR = self.app.get_theme_color('PROCESS_BTN', ['#6F42C1', '#59369A'])
        self.PROCESS_BTN_HOVER = self.app.get_theme_color('PROCESS_BTN_HOVER', ['#59369A', '#51318D'])
        self.PROCESS_BTN_TEXT = self.app.get_theme_color('PROCESS_BTN_TEXT', 'white')
        self.SECONDARY_BTN_COLOR = self.app.get_theme_color('SECONDARY_BTN', ['#555555', '#444444'])
        self.SECONDARY_BTN_HOVER = self.app.get_theme_color('SECONDARY_BTN_HOVER', ['#444444', '#333333'])
        self.SECONDARY_BTN_TEXT = self.app.get_theme_color('SECONDARY_BTN_TEXT', 'white')
        self.QUEUE_BG = self.app.get_theme_color('DND_BG', ['#F0F0F0', '#1D1D1D'])
        self.QUEUE_BORDER = self.app.get_theme_color('DND_BORDER', ['#565B5E', '#565B5E'])
        self.QUEUE_TEXT = self.app.get_theme_color('DND_TEXT', ['gray', 'gray'])
        self.STATUS_SUCCESS = self.app.get_theme_color('STATUS_SUCCESS', ['#28A745', '#218838'])
        self.STATUS_ERROR = self.app.get_theme_color('STATUS_ERROR', ['#DC3545', '#C82333'])
        self.STATUS_WARNING = self.app.get_theme_color('STATUS_WARNING', ['#FFA500', '#FF8C00'])
        self.STATUS_PENDING = self.app.get_theme_color('STATUS_PENDING', ['#565B5E', '#565B5E'])
        self.JOB_TITLE_COLOR = self.app.get_theme_color('JOB_TITLE_TEXT', ['black', 'white'])
        self.JOB_STATUS_COLOR = self.app.get_theme_color('DND_TEXT', ['gray', 'gray'])
        self.JOB_RUNNING_COLOR = self.app.get_theme_color('ANALYZE_BTN', ['#52a2f2', '#52a2f2'])
        self.JOB_ACTION_ICON_COLOR = self.app.get_theme_color('JOB_ACTION_ICON_COLOR', ['black', 'white'])
        self.JOB_CANCEL_ICON_COLOR = self.app.get_theme_color('JOB_CANCEL_ICON_COLOR', ['#DC3545', '#DC3545'])
        self.DISABLED_TEXT_COLOR = self.app.get_theme_color('DISABLED_TEXT', ['#A0A0A0', '#D3D3D3'])
    def refresh_theme(self):
        """Actualiza los colores de los widgets críticos según el tema actual."""
        if self.is_initializing:
            return
        else:
            self._load_theme_colors()
            if hasattr(self, 'analyze_button'):
                self.analyze_button.configure(fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER, text_color=self.ANALYZE_BTN_TEXT)
            if hasattr(self, 'import_button'):
                self.import_button.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
            if hasattr(self, 'clear_list_button'):
                self.clear_list_button.configure(fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, text_color=self.CANCEL_BTN_TEXT)
            if hasattr(self, 'reset_status_button'):
                self.reset_status_button.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
            if hasattr(self, 'batch_import_preset_button'):
                self.batch_import_preset_button.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
            if hasattr(self, 'batch_export_preset_button'):
                self.batch_export_preset_button.configure(fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER, text_color=self.ANALYZE_BTN_TEXT)
            if hasattr(self, 'batch_delete_preset_button'):
                self.batch_delete_preset_button.configure(fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, text_color=self.CANCEL_BTN_TEXT)
            if hasattr(self, 'start_queue_button'):
                self.start_queue_button.configure(fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
            if hasattr(self, 'queue_scroll_frame'):
                self.queue_scroll_frame.configure(fg_color=self.QUEUE_BG, border_color=self.QUEUE_BORDER)
            if hasattr(self, 'queue_placeholder_label'):
                self.queue_placeholder_label.configure(text_color=self.QUEUE_TEXT)
            if hasattr(self, 'open_folder_button'):
                self.open_folder_button.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
            if hasattr(self, 'select_folder_button'):
                self.select_folder_button.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
            if hasattr(self, 'save_thumbnail_button'):
                self.save_thumbnail_button.configure(fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
    def _create_widgets(self):
        """Crea los componentes visuales de la pestaña."""
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='ew')
        self.input_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.input_frame, text='URL:').grid(row=0, column=0, padx=(10, 5), pady=0)
        self.url_entry = ctk.CTkEntry(self.input_frame, placeholder_text='Pega una URL de video o playlist...')
        self.url_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.url_entry))
        self.url_entry.bind('<Return>', lambda event: self._on_analyze_click())
        self.url_entry.grid(row=0, column=1, padx=5, pady=0, sticky='ew')
        self.analyze_button = ctk.CTkButton(self.input_frame, text='Analizar', width=100, command=self._on_analyze_click, fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER, text_color=self.ANALYZE_BTN_TEXT)
        self.analyze_button.grid(row=0, column=2, padx=5, pady=0)
        self.import_button = ctk.CTkButton(self.input_frame, text='Importar ▼', width=100, state='normal', command=self._show_import_menu, fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT)
        self.import_button.grid(row=0, column=3, padx=(0, 10), pady=0)
        import_tooltip_text = 'Activa el modo de recodificación local.\nPermite seleccionar múltiples archivos de video/audio de tu PC para añadirlos a la cola y procesarlos.'
        Tooltip(self.import_button, import_tooltip_text, delay_ms=1000)
        self.global_options_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.global_options_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky='ew')
        self.global_options_frame.grid_columnconfigure(0, weight=1)
        global_line1_frame = ctk.CTkFrame(self.global_options_frame, fg_color='transparent')
        global_line1_frame.grid(row=1, column=0, sticky='ew', padx=5, pady=(3, 0))
        self.playlist_analysis_check = ctk.CTkCheckBox(global_line1_frame, text='Análisis de Playlist', onvalue=True, offvalue=False, command=self._on_playlist_analysis_toggle)
        self.playlist_analysis_check.pack(side='left', padx=5)
        self.playlist_analysis_check.select()
        playlist_tooltip_text = 'Activado: Analiza la playlist/colección completa.\nDesactivado: Analiza solo el video individual de la URL.'
        Tooltip(self.playlist_analysis_check, playlist_tooltip_text, delay_ms=1000)
        self.fast_mode_check = ctk.CTkCheckBox(global_line1_frame, text='Modo Rápido', command=self.save_settings, width=100)
        self.fast_mode_check.pack(side='left', padx=5)
        self.fast_mode_check.select()
        fast_tooltip = 'Activado: Análisis instantáneo (Flat). Abre el selector de videos.\nDesactivado: Análisis profundo (Lento). Añade todos los videos a la cola uno por uno.'
        Tooltip(self.fast_mode_check, fast_tooltip, delay_ms=1000)
        ctk.CTkLabel(global_line1_frame, text='Aplicar Modo Global:').pack(side='left', padx=(15, 5))
        self.global_mode_var = StringVar(value='Video+Audio')
        self.global_mode_menu = ctk.CTkOptionMenu(global_line1_frame, values=['Video+Audio', 'Solo Audio'], width=140, variable=self.global_mode_var, command=self._on_apply_global_mode)
        self.global_mode_menu.pack(side='left', padx=5)
        self.global_quality_var = StringVar(value='-')
        self.global_quality_menu = ctk.CTkOptionMenu(global_line1_frame, values=['-'], width=160, variable=self.global_quality_var, command=self._on_apply_global_quality)
        self.global_quality_menu.pack(side='left', padx=5)
        Tooltip(self.global_quality_menu, 'Aplica un criterio de calidad (ej: 1080p) a todos los videos individuales de la lista.\nNO afecta a las Playlists (Modo Rápido).', delay_ms=1000)
        self._update_global_quality_options('Video+Audio')
        global_line2_frame_placeholder = ctk.CTkFrame(self.global_options_frame, fg_color='transparent', height=10)
        global_line2_frame_placeholder.grid(row=2, column=0, sticky='ew', padx=5, pady=0)
        global_line3_frame = ctk.CTkFrame(self.global_options_frame, fg_color='transparent')
        global_line3_frame.grid(row=3, column=0, sticky='ew', padx=5, pady=(0, 3))
        thumbnail_label = ctk.CTkLabel(global_line3_frame, text='Miniaturas:', font=ctk.CTkFont(weight='bold'))
        thumbnail_label.pack(side='left', padx=(5, 5))
        thumbnail_tooltip_text = 'Controla cómo se deben descargar las miniaturas para todos los ítems de la cola.'
        Tooltip(thumbnail_label, thumbnail_tooltip_text, delay_ms=1000)
        self.thumbnail_mode_var = StringVar(value='normal')
        self.radio_normal = ctk.CTkRadioButton(global_line3_frame, text='Modo Manual', variable=self.thumbnail_mode_var, value='normal', command=self._on_thumbnail_mode_change)
        self.radio_normal.pack(side='left', padx=5)
        self.radio_with_thumbnail = ctk.CTkRadioButton(global_line3_frame, text='Con video/audio', variable=self.thumbnail_mode_var, value='with_thumbnail', command=self._on_thumbnail_mode_change)
        self.radio_with_thumbnail.pack(side='left', padx=5)
        self.radio_only_thumbnail = ctk.CTkRadioButton(global_line3_frame, text='Solo miniaturas', variable=self.thumbnail_mode_var, value='only_thumbnail', command=self._on_thumbnail_mode_change)
        self.radio_only_thumbnail.pack(side='left', padx=5)
        self.auto_send_to_it_checkbox = ctk.CTkCheckBox(global_line3_frame, text='Auto-enviar a H.I.', width=120, state='disabled')
        self.auto_send_to_it_checkbox.pack(side='left', padx=(15, 5))
        Tooltip(self.auto_send_to_it_checkbox, 'Al terminar la descarga, envía automáticamente la miniatura a la pestaña \'Herramientas de Imagen\' para editarla, escalar o quitar fondo.', delay_ms=1000)
        self.queue_actions_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.queue_actions_frame.grid(row=2, column=0, padx=(10, 5), pady=(0, 0), sticky='ew')
        self.queue_actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.clear_list_button = ctk.CTkButton(self.queue_actions_frame, text='Limpiar Lista', height=24, font=ctk.CTkFont(size=12), command=self._on_clear_list_click, fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, text_color=self.CANCEL_BTN_TEXT)
        self.clear_list_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        self.reset_status_button = ctk.CTkButton(self.queue_actions_frame, text='Resetear Estado', height=24, font=ctk.CTkFont(size=12), command=self._on_reset_status_click, fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        self.reset_status_button.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.global_recode_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.global_recode_frame.grid(row=2, column=1, padx=(5, 10), pady=(0, 0), sticky='e')
        self.global_recode_checkbox = ctk.CTkCheckBox(self.global_recode_frame, text='Recodificación Global:', command=self._on_global_recode_toggle, state='disabled')
        self.global_recode_checkbox.pack(side='left', padx=(0, 5))
        global_recode_tooltip = 'Activa la recodificación para TODOS los ítems de la cola.\nEsto anula la configuración individual de cada ítem y aplica el mismo preset (seleccionado a la derecha) a todos.'
        Tooltip(self.global_recode_checkbox, global_recode_tooltip, delay_ms=1000)
        self.global_recode_preset_menu = ctk.CTkOptionMenu(self.global_recode_frame, values=['-'], width=200, state='disabled', command=self._apply_global_recode_settings)
        self.global_recode_preset_menu.pack(side='left', padx=(0, 5))
        self.queue_scroll_frame = ctk.CTkScrollableFrame(self, fg_color=self.QUEUE_BG, border_width=1, border_color=self.QUEUE_BORDER)
        self.queue_scroll_frame.grid(row=3, column=0, padx=(10, 5), pady=(0, 10), sticky='nsew')
        self.queue_placeholder_label = ctk.CTkLabel(self.queue_scroll_frame, text='Arrastra videos/carpetas aquí\no pega una URL arriba', font=ctk.CTkFont(size=14), text_color=self.QUEUE_TEXT)
        self.queue_placeholder_label.pack(expand=True, pady=50, padx=20)
        if DND_FILES:
            try:
                self.queue_scroll_frame.drop_target_register(DND_FILES)
                self.queue_scroll_frame.dnd_bind('<<Drop>>', self._on_batch_drop)
                self.queue_scroll_frame._parent_canvas.drop_target_register(DND_FILES)
                self.queue_scroll_frame._parent_canvas.dnd_bind('<<Drop>>', self._on_batch_drop)
                self.queue_placeholder_label.drop_target_register(DND_FILES)
                self.queue_placeholder_label.dnd_bind('<<Drop>>', self._on_batch_drop)
                print('DEBUG: Drag & Drop activado en TODAS las capas de la cola')
            except Exception as e:
                print(f'ADVERTENCIA: No se pudo activar DnD en lotes: {e}')
        self.config_panel = ctk.CTkFrame(self)
        self.config_panel.grid(row=3, column=1, padx=(5, 10), pady=(0, 10), sticky='nsew')
        self.config_panel.grid_rowconfigure(0, weight=0)
        self.config_panel.grid_rowconfigure(1, weight=1)
        self.config_panel.grid_columnconfigure(0, weight=1)
        self.top_config_frame = ctk.CTkFrame(self.config_panel)
        self.top_config_frame.grid(row=0, column=0, sticky='new', padx=5, pady=5)
        self.top_config_frame.grid_columnconfigure(0, weight=0)
        self.top_config_frame.grid_columnconfigure(1, weight=1)
        self.miniature_frame = ctk.CTkFrame(self.top_config_frame)
        self.miniature_frame.grid(row=0, column=0, padx=(5, 10), pady=5, sticky='n')
        self.thumbnail_container = ctk.CTkFrame(self.miniature_frame, width=160, height=90)
        self.thumbnail_container.pack(pady=(0, 5))
        self.thumbnail_container.pack_propagate(False)
        self.create_placeholder_label(self.thumbnail_container, 'Miniatura')
        self.save_thumbnail_button = ctk.CTkButton(self.miniature_frame, text='Guardar Miniatura...', command=self._on_save_thumbnail_click, fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        self.save_thumbnail_button.pack(fill='x', pady=5)
        self.auto_save_thumbnail_check = ctk.CTkCheckBox(self.miniature_frame, text='Descargar miniatura', command=self._on_auto_save_thumbnail_toggle)
        self.auto_save_thumbnail_check.pack(fill='x', padx=10, pady=5)
        self.auto_save_thumbnail_check.configure(state='normal')
        self.info_frame = ctk.CTkFrame(self.top_config_frame, fg_color='transparent')
        self.info_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.info_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.info_frame, text='Título:', anchor='w').pack(fill='x', padx=5, pady=(0, 0))
        title_row = ctk.CTkFrame(self.info_frame, fg_color='transparent')
        title_row.pack(fill='x', padx=5, pady=(0, 5))
        self.title_entry = ctk.CTkEntry(title_row, font=('', 14), placeholder_text='Título del archivo...')
        self.title_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.title_entry))
        self.title_entry.bind('<KeyRelease>', self._on_batch_config_change)
        self.title_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.tags_menu = ctk.CTkOptionMenu(title_row, width=90, values=['- Etiqueta -'], command=self.on_tag_change)
        self.tags_menu.pack(side='right', padx=(5, 0))
        self.mode_selector = ctk.CTkSegmentedButton(self.info_frame, values=['Video+Audio', 'Solo Audio'], command=self._on_item_mode_change_and_save)
        self.mode_selector.set('Video+Audio')
        self.mode_selector.pack(fill='x', padx=5, pady=5)
        self.video_quality_label = ctk.CTkLabel(self.info_frame, text='Calidad de Video:', anchor='w')
        self.video_quality_label.pack(fill='x', padx=5, pady=(5, 0))
        self.video_quality_menu = ctk.CTkOptionMenu(self.info_frame, values=['-'], command=self._on_batch_video_quality_change_and_save)
        self.video_quality_menu.pack(fill='x', padx=5, pady=(0, 5))
        self.audio_options_frame = ctk.CTkFrame(self.info_frame, fg_color='transparent')
        self.audio_quality_label = ctk.CTkLabel(self.audio_options_frame, text='Calidad de Audio:', anchor='w')
        self.audio_quality_label.pack(fill='x', padx=5, pady=(5, 0))
        self.audio_quality_menu = ctk.CTkOptionMenu(self.audio_options_frame, values=['-'], command=self._on_batch_audio_quality_change_and_save)
        self.audio_quality_menu.pack(fill='x', padx=5, pady=(0, 5))
        self.batch_use_all_audio_tracks_check = ctk.CTkCheckBox(self.audio_options_frame, text='Recodificar todas las pistas', command=self._on_batch_use_all_audio_tracks_change)
        multi_track_tooltip_text = 'Aplica la recodificación seleccionada a TODAS las pistas de audio por separado (no las fusiona).\n\n• Advertencia: Esta función depende del formato de salida. No todos los contenedores (ej: `.mp3`) admiten audio multipista.'
        Tooltip(self.batch_use_all_audio_tracks_check, multi_track_tooltip_text, delay_ms=1000)
        self.audio_options_frame.pack(fill='x', pady=0, padx=0)
        self.recode_main_scrollframe = ctk.CTkScrollableFrame(self.config_panel, label_text='Opciones de Recodificación')
        self.recode_main_scrollframe.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        self.recode_main_scrollframe.grid_columnconfigure(0, weight=1)
        self.batch_apply_quick_preset_checkbox = ctk.CTkCheckBox(self.recode_main_scrollframe, text='Activar Recodificación', command=self._on_batch_quick_recode_toggle_and_save)
        self.batch_apply_quick_preset_checkbox.pack(anchor='w', padx=10, pady=(5, 5))
        self.batch_apply_quick_preset_checkbox.deselect()
        self.batch_quick_recode_options_frame = ctk.CTkFrame(self.recode_main_scrollframe, fg_color='transparent')
        self.batch_quick_recode_options_frame.pack(fill='x', padx=0, pady=0)
        self.batch_keep_original_quick_checkbox = ctk.CTkCheckBox(self.batch_quick_recode_options_frame, text='Mantener los archivos originales', command=self._on_batch_config_change, state='disabled')
        self.batch_keep_original_quick_checkbox.pack(anchor='w', padx=10, pady=(0, 5))
        self.batch_keep_original_quick_checkbox.select()
        preset_label = ctk.CTkLabel(self.batch_quick_recode_options_frame, text='Preset de Conversión:', font=ctk.CTkFont(weight='bold'))
        preset_label.pack(pady=10, padx=10)
        preset_tooltip_text = 'Perfiles pre-configurados para tareas comunes.\n\n• Puedes crear y guardar tus propios presets desde el \'Modo Manual\' de la pestaña \'Proceso Único\'.\n• Tus presets guardados aparecerán aquí.'
        Tooltip(preset_label, preset_tooltip_text, delay_ms=1000)
        self.batch_recode_preset_menu = ctk.CTkOptionMenu(self.batch_quick_recode_options_frame, values=['-'], command=self._on_batch_preset_change_and_save, state='disabled')
        self.batch_recode_preset_menu.pack(pady=10, padx=10, fill='x')
        Tooltip(self.batch_recode_preset_menu, preset_tooltip_text, delay_ms=1000)
        batch_preset_actions_frame = ctk.CTkFrame(self.batch_quick_recode_options_frame, fg_color='transparent')
        batch_preset_actions_frame.pack(fill='x', padx=10, pady=(0, 10))
        batch_preset_actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.batch_import_preset_button = ctk.CTkButton(batch_preset_actions_frame, text='📥 Importar', command=self.app.single_tab.import_preset_file, fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT, state='disabled')
        self.batch_import_preset_button.grid(row=0, column=0, padx=(0, 5), sticky='ew')
        self.batch_export_preset_button = ctk.CTkButton(batch_preset_actions_frame, text='📤 Exportar', command=self.app.single_tab.export_preset_file, state='disabled', fg_color=self.ANALYZE_BTN_COLOR, hover_color=self.ANALYZE_BTN_HOVER, text_color=self.ANALYZE_BTN_TEXT)
        self.batch_export_preset_button.grid(row=0, column=1, padx=5, sticky='ew')
        self.batch_delete_preset_button = ctk.CTkButton(batch_preset_actions_frame, text='🗑️ Eliminar', command=self.app.single_tab.delete_preset_file, state='disabled', fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER, text_color=self.CANCEL_BTN_TEXT)
        self.batch_delete_preset_button.grid(row=0, column=2, padx=(5, 0), sticky='ew')
        self.download_frame = ctk.CTkFrame(self)
        self.download_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        line1_frame = ctk.CTkFrame(self.download_frame, fg_color='transparent')
        line1_frame.pack(fill='x', padx=0, pady=(0, 5))
        line1_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(line1_frame, text='Carpeta de Salida:').grid(row=0, column=0, padx=(10, 5), pady=5, sticky='w')
        self.output_path_entry = ctk.CTkEntry(line1_frame, placeholder_text='Selecciona una carpeta...')
        self.output_path_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.output_path_entry))
        self.output_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.select_folder_button = ctk.CTkButton(line1_frame, text='...', width=40, command=self.select_output_folder, fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        self.select_folder_button.grid(row=0, column=2, padx=(0, 5), pady=5)
        self.open_folder_button = ctk.CTkButton(line1_frame, text='📁', width=40, font=ctk.CTkFont(size=16), command=self._open_batch_output_folder, state='disabled', fg_color=self.SECONDARY_BTN_COLOR, hover_color=self.SECONDARY_BTN_HOVER, text_color=self.SECONDARY_BTN_TEXT)
        self.open_folder_button.grid(row=0, column=3, padx=(0, 5), pady=5)
        speed_label = ctk.CTkLabel(line1_frame, text='Límite (MB/s):')
        speed_label.grid(row=0, column=4, padx=(10, 5), pady=5, sticky='w')
        self.speed_limit_entry = ctk.CTkEntry(line1_frame, width=50)
        tooltip_text = 'Limita la velocidad de descarga (en MB/s).\nÚtil si las descargas fallan por \'demasiadas peticiones\'.'
        Tooltip(speed_label, tooltip_text, delay_ms=1000)
        Tooltip(self.speed_limit_entry, tooltip_text, delay_ms=1000)
        self.speed_limit_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.speed_limit_entry))
        self.speed_limit_entry.grid(row=0, column=5, padx=(0, 10), pady=5)
        line2_frame = ctk.CTkFrame(self.download_frame, fg_color='transparent')
        line2_frame.pack(fill='x', padx=0, pady=0)
        line2_frame.grid_columnconfigure(5, weight=1)
        conflict_label = ctk.CTkLabel(line2_frame, text='Si existe:')
        conflict_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky='w')
        self.conflict_policy_menu = ctk.CTkOptionMenu(line2_frame, width=100, values=['Sobrescribir', 'Renombrar', 'Omitir'])
        self.conflict_policy_menu.set('Renombrar')
        self.conflict_policy_menu.grid(row=0, column=1, padx=(0, 10), pady=5, sticky='w')
        conflict_tooltip_text = 'Determina qué hacer si un archivo con el mismo nombre ya existe:\n• Sobrescribir: Reemplaza el archivo antiguo.\n• Renombrar: Guarda como \'archivo (1).mp4\'.\n• Omitir: Salta la descarga de este ítem.'
        Tooltip(conflict_label, conflict_tooltip_text, delay_ms=1000)
        Tooltip(self.conflict_policy_menu, conflict_tooltip_text, delay_ms=1000)
        self.create_subfolder_checkbox = ctk.CTkCheckBox(line2_frame, text='Crear carpeta', command=self._toggle_subfolder_name_entry)
        self.create_subfolder_checkbox.grid(row=0, column=2, padx=(5, 5), pady=5, sticky='w')
        subfolder_tooltip_text = 'Guarda todos los archivos en una subcarpeta.\nSe puede poner un nombre personalizado, pero si se deja vacío, el nombre será \'DowP List\'.\nSi el nombre ya existe (ej: \'DowP List\'), se creará una nueva (ej: \'DowP List 01\').'
        Tooltip(self.create_subfolder_checkbox, subfolder_tooltip_text, delay_ms=1000)
        self.subfolder_name_entry = ctk.CTkEntry(line2_frame, width=100, placeholder_text='DowP List')
        self.subfolder_name_entry.bind('<Button-3>', lambda e: self.create_entry_context_menu(self.subfolder_name_entry))
        self.subfolder_name_entry.grid(row=0, column=3, padx=(0, 10), pady=5, sticky='w')
        self.subfolder_name_entry.configure(state='disabled')
        self.auto_download_checkbox = ctk.CTkCheckBox(line2_frame, text='Auto-descarga')
        self.auto_download_checkbox.grid(row=0, column=4, padx=5, pady=5, sticky='w')
        auto_tooltip_text = 'Si está activo, la cola comenzará a descargarse automáticamente después de que el análisis de una URL finalice.'
        Tooltip(self.auto_download_checkbox, auto_tooltip_text, delay_ms=1000)
        self.start_queue_button = ctk.CTkButton(line2_frame, text='Iniciar Cola', state='disabled', command=self.start_queue_processing, fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, text_color=self.DOWNLOAD_BTN_TEXT, text_color_disabled=self.DISABLED_TEXT_COLOR, width=120)
        self.start_queue_button.grid(row=0, column=6, padx=(5, 10), pady=5, sticky='e')
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky='ew')
        self.progress_label = ctk.CTkLabel(self.progress_frame, text='Esperando para iniciar la cola...')
        self.progress_label.pack(pady=(5, 0))
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 5), padx=10, fill='x')
        batch_path = self.app.batch_download_path
        if not batch_path:
            batch_path = self.app.default_download_path
        if batch_path:
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, batch_path)
        else:
            try:
                from pathlib import Path
                downloads_path = Path.home() / 'Downloads'
                if downloads_path.exists() and downloads_path.is_dir():
                        self.output_path_entry.delete(0, 'end')
                        self.output_path_entry.insert(0, str(downloads_path))
                        self.app.batch_download_path = str(downloads_path)
            except Exception as e:
                print(f'No se pudo establecer la carpeta de descargas por defecto para Lotes: {e}')
        final_path = self.output_path_entry.get()
        if final_path and os.path.isdir(final_path):
                self.open_folder_button.configure(state='normal')
        self._set_config_panel_state('disabled')
    def _on_playlist_analysis_toggle(self):
        """\n        Activa/Desactiva el checkbox de Modo Rápido según el estado de Análisis de Playlist.\n        Se activa automáticamente por defecto al habilitar playlist.\n        """
        if self.playlist_analysis_check.get():
            self.fast_mode_check.configure(state='normal')
            self.fast_mode_check.select()
        else:
            self.fast_mode_check.deselect()
            self.fast_mode_check.configure(state='disabled')
        self.save_settings()
    def _thumbnail_worker_loop(self):
        """
        Procesa las miniaturas en serie para no congelar la UI.
        Descarta solicitudes obsoletas si el usuario cambia rápido de ítem.
        """
        import time
        import gc
        import os
        import requests
        from PIL import Image
        from io import BytesIO
        import customtkinter as ctk

        while True:
            try:
                # Obtener la siguiente tarea de la cola
                task = self.thumb_queue.get()
                job_id, path_or_url, is_local = task

                # Si el job ya no es el seleccionado, descartar
                if job_id != self.selected_job_id:
                    continue

                # Si ya está en caché, actualizar la UI y continuar
                if path_or_url in self.thumbnail_cache:
                    self._update_thumbnail_ui(path_or_url)
                    continue

                img_data = None

                if is_local:
                    # Extraer un frame del video local usando ffmpeg
                    frame_path = self.app.ffmpeg_processor.get_frame_from_video(path_or_url)
                    if frame_path and os.path.exists(frame_path):
                        with open(frame_path, 'rb') as f:
                            img_data = f.read()
                        os.remove(frame_path)
                else:
                    # Descargar la imagen desde una URL
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://imgur.com/'
                    }
                    try:
                        resp = requests.get(path_or_url, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            img_data = resp.content
                    except Exception as e:
                        print(f"Error descargando miniatura: {e}")

                if img_data:
                    # Convertir a CTkImage
                    pil_image = Image.open(BytesIO(img_data))
                    display_image = pil_image.copy()
                    display_image.thumbnail((160, 90), Image.Resampling.LANCZOS)
                    ctk_image = ctk.CTkImage(
                        light_image=display_image,
                        dark_image=display_image,
                        size=display_image.size
                    )

                    # Rotación automática de caché si excede 40 elementos
                    if len(self.thumbnail_cache) > 40:
                        keys_to_remove = list(self.thumbnail_cache.keys())[:10]
                        for k in keys_to_remove:
                            del self.thumbnail_cache[k]
                        gc.collect()
                        print('DEBUG: 🧹 Caché de miniaturas limpiado (rotación automática)')

                    self.thumbnail_cache[path_or_url] = {'ctk': ctk_image, 'raw': img_data}

                    # Si el job sigue siendo el seleccionado, actualizar UI (desde el hilo principal)
                    if job_id == self.selected_job_id:
                        self.app.after(0, lambda: self._update_thumbnail_ui(path_or_url))
                else:
                    # No se pudo obtener datos de imagen (opcional: logging)
                    print(f"No se obtuvieron datos de imagen para: {path_or_url}")

            except Exception as e:
                print(f"Error crítico en worker de miniaturas: {e}")
                time.sleep(1)  # Evita un bucle rápido si el error persiste
    def _update_thumbnail_ui(self, cache_key):
        """Actualiza la etiqueta de miniatura usando datos de la caché."""
        if cache_key not in self.thumbnail_cache:
            return
        else:
            cached_data = self.thumbnail_cache[cache_key]
            image = cached_data['ctk'] if isinstance(cached_data, dict) else cached_data
            if self.thumbnail_label:
                self.thumbnail_label.configure(image=image, text='')
                self.thumbnail_label.image = image
            self.save_thumbnail_button.configure(state='normal')
            if isinstance(cached_data, dict):
                self.current_raw_thumbnail = cached_data['raw']
    def _toggle_subfolder_name_entry(self):
        """Habilita/deshabilita el entry de nombre de carpeta según el checkbox."""
        if self.create_subfolder_checkbox.get():
            self.subfolder_name_entry.configure(state='normal')
        else:
            self.subfolder_name_entry.configure(state='disabled')
    def _set_config_panel_state(self, state: str='normal'):
        """\n        Habilita o deshabilita todos los widgets interactivos dentro del panel de configuración derecho.\n        state: \"normal\" o \"disabled\"\n        """
        widgets_to_toggle = [self.save_thumbnail_button, self.title_entry, self.mode_selector, self.video_quality_menu, self.audio_quality_menu, self.batch_apply_quick_preset_checkbox, self.batch_recode_preset_menu, self.batch_keep_original_quick_checkbox]
        for widget in widgets_to_toggle:
            if widget:
                widget.configure(state=state)
    def create_placeholder_label(self, container, text='Miniatura', font_size=12):
        """Crea el placeholder para la miniatura."""
        for widget in container.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.destroy()
        font = ctk.CTkFont(size=font_size)
        label = ctk.CTkLabel(container, text=text, font=font)
        label.pack(expand=True, fill='both')
        if container == self.thumbnail_container:
            self.thumbnail_label = label
    def _on_batch_audio_quality_change_and_save(self, selected_label: str):
        """Guarda cuando cambia el audio."""
        if not self._updating_ui:
            self._on_batch_config_change()
    def _on_batch_video_quality_change(self, selected_label: str):
        """\n        Solo actualiza la UI según el formato de video seleccionado.\n        Ahora maneja correctamente formatos multiidioma.\n        """
        selected_format_info = self.current_video_formats.get(selected_label)
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
                        return
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
                        original_video_lang = None
                        try:
                            selected_items = self.queue_tree.selection()
                            if selected_items:
                                job = self.app.queue_manager.get_job(selected_items[0])
                                if job and job.analysis_data:
                                        original_video_lang = job.analysis_data.get('language')
                        except Exception:
                            pass
                        for label in audio_language_options:
                            f_id = self.combined_audio_map.get(label)
                            for variant in variants:
                                if variant.get('format_id') == f_id:
                                    note = (variant.get('format_note') or '').lower()
                                    v_lang = variant.get('language')
                                    if 'original' in note:
                                        default_lang_selection = label
                                        print(f'DEBUG: [Lote Multiidioma] Pre-seleccionando idioma ORIGINAL (por nota): {label}')
                                        break
                                    else:
                                        if original_video_lang and v_lang and (v_lang.startswith(original_video_lang) or original_video_lang.startswith(v_lang)):
                                                    default_lang_selection = label
                                                    print(f'DEBUG: [Lote Multiidioma] Pre-seleccionando idioma ORIGINAL (por metadato global): {label}')
                                                    break
                            if default_lang_selection == label:
                                break
                        self.audio_quality_menu.configure(state='normal', values=audio_language_options)
                        self.audio_quality_menu.set(default_lang_selection)
                else:
                    self.audio_quality_menu.configure(state='disabled')
                    self.combined_audio_map = {}
                    print(f'DEBUG: Combinado de un solo idioma detectado (quality_key: {quality_key})')
            else:
                print('DEBUG: No es combinado multiidioma, restaurando menú de audio normal')
                self.combined_audio_map = {}
                a_opts = list(self.current_audio_formats.keys()) or ['-']
                current_audio_selection = self.audio_quality_menu.get()
                default_audio_selection = a_opts[0]
                for option in a_opts:
                    if '✨' in option:
                        default_audio_selection = option
                        break
                selection_to_set = default_audio_selection
                if current_audio_selection in a_opts:
                    selection_to_set = current_audio_selection
                self.audio_quality_menu.configure(state='normal' if self.current_audio_formats else 'disabled', values=a_opts)
                self.audio_quality_menu.set(selection_to_set)
    def _on_batch_video_quality_change_and_save(self, selected_label: str):
        """\n        Wrapper que actualiza la UI Y guarda la configuración.\n        """
        self._on_batch_video_quality_change(selected_label)
        if not self._updating_ui:
            self._on_batch_config_change()
    def _on_item_mode_change_and_save(self, mode: str):
        """Función wrapper que actualiza la UI Y guarda."""
        self._on_item_mode_change(mode)
        if not self._updating_ui:
            self._on_batch_config_change()
    def _on_batch_use_all_audio_tracks_change(self):
        """Gestiona el estado del menú de audio cuando el checkbox multipista cambia."""
        if self.batch_use_all_audio_tracks_check.get() == 1:
            self.audio_quality_menu.configure(state='disabled')
        else:
            self.audio_quality_menu.configure(state='normal')
        if not self._updating_ui:
            self._on_batch_config_change()
    def _on_item_mode_change(self, mode: str):
        """\n        Muestra/oculta los menús de calidad en orden CONSISTENTE.\n        """
        if mode == 'Video+Audio':
            self.video_quality_label.pack_forget()
            self.video_quality_menu.pack_forget()
            self.audio_options_frame.pack_forget()
            self.video_quality_label.pack(fill='x', padx=5, pady=(5, 0))
            self.video_quality_menu.pack(fill='x', padx=5, pady=(0, 5))
            self.audio_options_frame.pack(fill='x', pady=0, padx=0)
            self._on_batch_video_quality_change(self.video_quality_menu.get())
        else:
            if mode == 'Solo Audio':
                self.video_quality_label.pack_forget()
                self.video_quality_menu.pack_forget()
                self.audio_options_frame.pack_forget()
                self.audio_options_frame.pack(fill='x', pady=0, padx=0)
        self._populate_batch_preset_menu()
    def update_job_ui(self, job_id: str, status: str, message: str, progress_percent: float=0.0):
        """\n        Punto de entrada para actualizaciones desde QueueManager.\n        Maneja el throttling y asegura que la UI se actualice en el hilo principal.\n        """
        now = time.time()
        if status == 'RUNNING':
            last_time = self._last_ui_update_times.get(job_id, 0)
            if now - last_time < 0.5:
                return
        self._last_ui_update_times[job_id] = now
        self.after(0, lambda: self._do_update_job_ui(job_id, status, message, progress_percent))
    def _do_update_job_ui(self, job_id: str, status: str, message: str, progress_percent: float=0.0):
        """\n        Ejecuta la actualización real de los widgets. \n        DEBE ejecutarse en el hilo principal.\n        """
        if job_id == 'QUEUE_STATUS':
            if status == 'RUNNING':
                self.start_queue_button.configure(text='Pausar Cola', fg_color=self.CANCEL_BTN_COLOR, hover_color=self.CANCEL_BTN_HOVER)
                self.progress_label.configure(text='Procesando cola...')
            else:
                if status == 'PAUSED':
                    self.start_queue_button.configure(text='Reanudar Cola', fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER)
                    self.progress_label.configure(text='Cola pausada.')
            return None
        else:
            if job_id == 'GLOBAL_PROGRESS':
                if status == 'UPDATE':
                    self.progress_label.configure(text=message)
                    self.progress_bar.set(progress_percent)
                else:
                    if status == 'RESET':
                        self.progress_label.configure(text=message)
                        self.progress_bar.set(0)
                return None
            else:
                job_exists = self.queue_manager.get_job_by_id(job_id)
                job_frame = self.job_widgets.get(job_id)
                if not job_frame:
                    if not job_exists:
                        return
                    else:
                        job_frame = ctk.CTkFrame(self.queue_scroll_frame, border_width=1, border_color=self.STATUS_PENDING)
                        job_frame.pack(fill='x', padx=5, pady=(0, 5))
                        job_frame.grid_columnconfigure(0, weight=1)
                        job_frame.grid_columnconfigure(1, weight=0)
                        job_frame.grid_columnconfigure(2, weight=0)
                        job_frame.grid_columnconfigure(3, weight=0)
                        job_frame.grid_columnconfigure(4, weight=0)
                        job_frame.title_label = ctk.CTkLabel(job_frame, text=message, anchor='w', wraplength=400, text_color=self.JOB_TITLE_COLOR)
                        job_frame.title_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky='ew')
                        job_frame.status_label = ctk.CTkLabel(job_frame, text='Pendiente...', anchor='w', text_color=self.JOB_STATUS_COLOR, font=ctk.CTkFont(size=11))
                        job_frame.status_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky='ew')
                        job_frame.progress_bar = ctk.CTkProgressBar(job_frame, height=4)
                        job_frame.progress_bar.set(0)
                        job_frame.progress_bar.grid(row=2, column=0, columnspan=5, padx=10, pady=(0, 2), sticky='ew')
                        job_frame.progress_bar.grid_remove()
                        job_frame.config_button = ctk.CTkButton(job_frame, text='⚙️', width=28, height=28, font=ctk.CTkFont(size=14), fg_color='transparent', hover_color=self.SECONDARY_BTN_HOVER, text_color=self.JOB_ACTION_ICON_COLOR, command=lambda jid=job_id: self._reconfigure_playlist_job(jid))
                        job_frame.config_button.grid(row=0, column=1, rowspan=2, padx=(0, 0), pady=5)
                        job_frame.folder_button = ctk.CTkButton(job_frame, text='📂', width=28, height=28, font=ctk.CTkFont(size=14), fg_color='transparent', hover_color=self.SECONDARY_BTN_HOVER, text_color=self.JOB_ACTION_ICON_COLOR, command=lambda jid=job_id: self._open_job_folder(jid))
                        job_frame.folder_button.grid(row=0, column=2, rowspan=2, padx=(0, 0), pady=5)
                        job_frame.restore_button = ctk.CTkButton(job_frame, text='◁', width=28, height=28, font=ctk.CTkFont(size=16), fg_color='transparent', hover_color=self.SECONDARY_BTN_HOVER, text_color=self.JOB_ACTION_ICON_COLOR, command=lambda jid=job_id: self._on_reset_single_job(jid))
                        job_frame.restore_button.grid(row=0, column=3, rowspan=2, padx=(0, 0), pady=5)
                        job_frame.close_button = ctk.CTkButton(job_frame, text='⨉', width=28, height=28, fg_color='transparent', hover_color=self.CANCEL_BTN_HOVER, text_color=self.JOB_CANCEL_ICON_COLOR, command=lambda jid=job_id: self._remove_job(jid))
                        job_frame.close_button.grid(row=0, column=4, rowspan=2, padx=(0, 5), pady=5)
                        job_frame.folder_button.grid_remove()
                        job_frame.restore_button.grid_remove()
                        if job_exists and job_exists.job_type == 'PLAYLIST':
                            job_frame.config_button.grid()
                        else:
                            job_frame.config_button.grid_remove()
                        job_frame.bind('<Button-1>', lambda e, jid=job_id: self._on_job_select(jid))
                        job_frame.title_label.bind('<Button-1>', lambda e, jid=job_id: self._on_job_select(jid))
                        job_frame.status_label.bind('<Button-1>', lambda e, jid=job_id: self._on_job_select(jid))
                        self.job_widgets[job_id] = job_frame
                else:
                    if status == 'RUNNING':
                        job_frame.configure(border_color=self.ANALYZE_BTN_COLOR)
                        job_frame.title_label.configure(text_color=self.JOB_TITLE_COLOR)
                        job_frame.status_label.configure(text=message, text_color=self.JOB_RUNNING_COLOR)
                        job_frame.progress_bar.grid()
                        if progress_percent > 0:
                            job_frame.progress_bar.set(progress_percent / 100.0)
                        else:
                            if '...' in message:
                                if '%' in message:
                                    try:
                                        percent_str = message.split('...')[1].split('%')[0].strip()
                                        percent_float = float(percent_str) / 100.0
                                        job_frame.progress_bar.set(percent_float)
                                    except:
                                        return
                    else:
                        if status == 'COMPLETED':
                            job_frame.configure(border_color=self.STATUS_SUCCESS)
                            job_frame.title_label.configure(text_color=self.STATUS_SUCCESS)
                            job_frame.status_label.configure(text=message, text_color=self.STATUS_SUCCESS)
                            job_frame.progress_bar.set(1)
                            job_frame.progress_bar.grid()
                            job_frame.folder_button.grid()
                            job_frame.restore_button.grid()
                            job_frame.config_button.grid_remove()
                            if self.auto_send_to_it_checkbox.get() == 1:
                                job_obj = self.queue_manager.get_job_by_id(job_id)
                                if job_obj and hasattr(job_obj, 'thumbnail_path') and job_obj.thumbnail_path and os.path.exists(job_obj.thumbnail_path):
                                                print(f'INFO: Auto-enviando miniatura a H.I.: {job_obj.thumbnail_path}')
                                                self.app.image_tab._process_imported_files([job_obj.thumbnail_path])
                        else:
                            if status == 'SKIPPED':
                                job_frame.configure(border_color=self.STATUS_WARNING)
                                job_frame.title_label.configure(text_color=self.STATUS_WARNING)
                                job_frame.status_label.configure(text=message, text_color=self.STATUS_WARNING)
                                job_frame.progress_bar.grid_remove()
                                job_frame.restore_button.grid()
                            else:
                                if status == 'NO_AUDIO':
                                    job_frame.configure(border_color=self.STATUS_WARNING)
                                    job_frame.title_label.configure(text_color=self.STATUS_WARNING)
                                    job_frame.status_label.configure(text=message, text_color=self.STATUS_WARNING)
                                    job_frame.progress_bar.grid_remove()
                                    job_frame.restore_button.grid()
                                else:
                                    if status == 'FAILED':
                                        job_frame.configure(border_color=self.STATUS_ERROR)
                                        if job_frame.title_label.cget('text') == 'Analizando...':
                                            job_frame.title_label.configure(text='Error de Análisis', text_color=self.STATUS_ERROR)
                                        else:
                                            job_frame.title_label.configure(text_color=self.STATUS_ERROR)
                                        job_frame.status_label.configure(text=message, text_color=self.STATUS_ERROR, wraplength=400)
                                        job_frame.progress_bar.grid_remove()
                                        job_frame.restore_button.grid()
                                    else:
                                        if status == 'PENDING':
                                            job_frame.configure(border_color=self.STATUS_PENDING)
                                            job_frame.title_label.configure(text_color=self.JOB_TITLE_COLOR)
                                            job_frame.status_label.configure(text=message, text_color=self.JOB_STATUS_COLOR)
                                            job_frame.progress_bar.grid_remove()
                                            job_frame.restore_button.grid_remove()
                                            job_frame.folder_button.grid_remove()
                                            if not job_exists or job_exists.job_type == 'PLAYLIST':
                                                    job_frame.config_button.grid()
    def _open_job_folder(self, job_id: str):
        """Abre la carpeta y selecciona el archivo de un job específico."""
        job = self.queue_manager.get_job_by_id(job_id)
        if not job or not job.final_filepath or (not os.path.exists(job.final_filepath)):
            print(f'ERROR: No se encontró archivo para job {job_id}')
            return
        else:
            file_path = os.path.normpath(job.final_filepath)
            try:
                import subprocess
                import platform
                system = platform.system()
                if system == 'Windows':
                    subprocess.Popen(['explorer', '/select,', file_path])
                else:
                    if system == 'Darwin':
                        subprocess.Popen(['open', '-R', file_path])
                    else:
                        subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
                print(f'INFO: Abriendo: {file_path}')
            except Exception as e:
                print(f'ERROR al abrir carpeta: {e}')
    def _remove_job(self, job_id: str):
        """Elimina un trabajo de la UI y de la cola."""
        print(f'DEBUG: El usuario presionó la \'X\' para eliminar el trabajo {job_id[:8]}...')
        if job_id in self.job_widgets:
            self.job_widgets[job_id].destroy()
            del self.job_widgets[job_id]
        if job_id in self.playlist_cache:
            del self.playlist_cache[job_id]
            print(f'DEBUG: 🗑️ Caché de playlist eliminada para {job_id[:6]}')
        self.queue_manager.remove_job(job_id)
        if self.selected_job_id == job_id:
            self.selected_job_id = None
            self._set_config_panel_state('disabled')
            self.create_placeholder_label(self.thumbnail_container, 'Miniatura')
        if not self.job_widgets:
            self.queue_placeholder_label.configure(text='Arrastra videos/carpetas aquí\no pega una URL arriba')
            self.queue_placeholder_label.pack(expand=True, pady=50, padx=20)
            self.start_queue_button.configure(state='disabled')
            self.progress_label.configure(text='Cola vacía. Analiza una URL para empezar.')
            self.global_recode_checkbox.configure(state='disabled')
            self.global_recode_preset_menu.configure(state='disabled')
            self.global_recode_checkbox.deselect()
    def _on_job_select(self, job_id: str):
        """\n        MODIFICADO: Usa DEBOUNCE para evitar lag al cambiar rápido de ítems.\n        Solo procesa la selección si el usuario se detiene por 150ms.\n        """
        if self.selected_job_id and self.selected_job_id in self.job_widgets:
                try:
                    self.job_widgets[self.selected_job_id].configure(border_color=self.QUEUE_BORDER)
                except:
                    pass
        new_frame = self.job_widgets.get(job_id)
        if new_frame:
            new_frame.configure(border_color=self.ANALYZE_BTN_COLOR)
        if job_id == self.selected_job_id:
            return
        else:
            if self.selected_job_id and (not self._updating_ui):
                    self._on_batch_config_change()
            self.selected_job_id = job_id
            if self._selection_timer_id:
                self.after_cancel(self._selection_timer_id)
            self._selection_timer_id = self.after(150, lambda: self._process_job_selection_delayed(job_id))
    def _process_job_selection_delayed(self, job_id: str):
        """\n        (NUEVO MÉTODO) Ejecuta la carga pesada de la UI y miniaturas.\n        Solo se llama si el usuario deja de hacer clic frenéticamente.\n        """
        self._selection_timer_id = None
        job = self.queue_manager.get_job_by_id(job_id)
        if not job:
            return
        else:
            if not job.analysis_data:
                self._set_config_panel_state('disabled')
                return
            else:
                self._set_config_panel_state('normal')
                self._populate_config_panel(job)
                if job.job_type == 'LOCAL_RECODE':
                    local_path = job.config.get('local_file_path')
                    if job.analysis_data.get('local_info', {}).get('video_stream'):
                        self.thumb_queue.put((job_id, local_path, True))
                    else:
                        self.create_placeholder_label(self.thumbnail_container, '🎵', font_size=60)
                else:
                    if job.job_type == 'PLAYLIST':
                        return
                    else:
                        thumbnail_url = job.analysis_data.get('thumbnail')
                        if thumbnail_url:
                            self.thumb_queue.put((job_id, thumbnail_url, False))
                        else:
                            formats = job.analysis_data.get('formats', [])
                            has_audio_only = any((self._classify_format(f) == 'AUDIO' for f in formats)) and (not any((self._classify_format(f) in ['VIDEO', 'VIDEO_ONLY'] for f in formats)))
                            if has_audio_only:
                                self.create_placeholder_label(self.thumbnail_container, '🎵', font_size=60)
                            else:
                                self.create_placeholder_label(self.thumbnail_container, 'Miniatura')
    def _populate_config_panel(self, job: Job):
        # irreducible cflow, using cdg fallback
        """\n        MODIFICADO: Usa el flag _updating_ui para prevenir eventos recursivos.\n        """
        if self._updating_ui:
            return
        else:
            self._updating_ui = True
            selected_tag = job.config.get('selected_tag', '- Etiqueta -')
            self.tags_menu.set(selected_tag)
        if job.job_type == 'PLAYLIST':
            print('DEBUG: Llenando panel para trabajo PLAYLIST.')
            raw_title = job.config.get('title', 'Playlist')
            clean_title = self.app.sanitize_title_global(raw_title)
            self.title_entry.insert(0, clean_title)
            thumb_url = None
            info = job.analysis_data
            if info.get('thumbnails'):
                thumbnails = info['thumbnails']
                valid_thumbs = [t for t in thumbnails if t.get('url')]
                if valid_thumbs:
                    sorted_thumbs = sorted(valid_thumbs, key=lambda x: x.get('width', 0) or 0, reverse=True)
                    thumb_url = sorted_thumbs[0].get('url')
                    print(f'DEBUG: Miniatura de playlist encontrada (mejor calidad): {thumb_url[:80]}')
            if not thumb_url and info.get('thumbnail'):
                    thumb_url = info['thumbnail']
                    print(f'DEBUG: Usando miniatura simple de playlist: {thumb_url[:80]}')
            if not thumb_url:
                entries = info.get('entries', [])
                if entries and len(entries) > 0:
                        first_video = entries[0]
                        if first_video.get('thumbnails'):
                            best = max(first_video['thumbnails'], key=lambda x: x.get('width', 0) or 0)
                            thumb_url = best.get('url')
                            print(f"DEBUG: Usando miniatura del primer video: {(thumb_url[:80] if thumb_url else 'N/A')}")
                        else:
                            if first_video.get('thumbnail'):
                                thumb_url = first_video['thumbnail']
            if thumb_url:
                self.thumb_queue.put((job.job_id, thumb_url, False))
            else:
                print('DEBUG: ⚠️ No se encontró miniatura para esta playlist')
                self.create_placeholder_label(self.thumbnail_container, 'Playlist\n(Sin miniatura)', font_size=16)
            self.mode_selector.configure(state='disabled')
            self.video_quality_menu.configure(state='disabled', values=['Configurado en Playlist'])
            self.video_quality_menu.set('Configurado en Playlist')
            self.audio_quality_menu.configure(state='disabled', values=['Configurado en Playlist'])
            self.audio_quality_menu.set('Configurado en Playlist')
            is_recode_enabled = job.config.get('recode_enabled', False)
            is_keep_original = job.config.get('recode_keep_original', True)
            if is_recode_enabled:
                self.batch_apply_quick_preset_checkbox.select()
            else:
                self.batch_apply_quick_preset_checkbox.deselect()
            if is_keep_original:
                self.batch_keep_original_quick_checkbox.select()
            else:
                self.batch_keep_original_quick_checkbox.deselect()
            self.batch_apply_quick_preset_checkbox.configure(state='normal')
            playlist_mode = job.config.get('playlist_mode', 'Video+Audio')
            self.mode_selector.set(playlist_mode)
            self._populate_batch_preset_menu()
            self._on_batch_quick_recode_toggle()
            return
        self._updating_ui = False
        if job.job_type == 'LOCAL_RECODE':
                print('DEBUG: Llenando panel para trabajo LOCAL_RECODE.')
                info = job.analysis_data
                local_info = info.get('local_info', {})
                video_stream = local_info.get('video_stream')
                audio_streams = local_info.get('audio_streams', [])
                format_info = local_info.get('format', {})
                raw_title = info.get('title', 'archivo_local')
                clean_title = self.app.sanitize_title_global(raw_title)
                self.title_entry.insert(0, clean_title)
                local_path = job.config.get('local_file_path')
                if not self.selected_job_id or self.selected_job_id != job.job_id:
                    pass
                else:
                    if video_stream:
                        self.thumb_queue.put((job.job_id, local_path, True))
                    else:
                        self.create_placeholder_label(self.thumbnail_container, '🎵', font_size=60)
                video_labels = ['- Sin Video -']
                self.current_video_formats = {}
                if video_stream:
                    v_codec = video_stream.get('codec_name', 'N/A').upper()
                    v_profile = video_stream.get('profile', 'N/A')
                    v_level = video_stream.get('level')
                    full_profile = f'{v_profile}@L{float(v_level) / 10.0:.1f}' if v_level else v_profile
                    v_resolution = f"{video_stream.get('width', '?')}x{video_stream.get('height', '?')}"
                    v_fps = self._format_fps(video_stream.get('r_frame_rate'))
                    v_bitrate = self._format_bitrate(video_stream.get('bit_rate') or format_info.get('bit_rate'))
                    v_pix_fmt = video_stream.get('pix_fmt', 'N/A')
                    bit_depth = '10-bit' if any((x in v_pix_fmt for x in ['p10', '10le'])) else '8-bit'
                    color_range = video_stream.get('color_range', '').capitalize()
                    v_label = f'{v_resolution} | {v_codec} ({full_profile}) @ {v_fps} fps | {v_bitrate} | {v_pix_fmt} ({bit_depth}, {color_range})'
                    video_labels = [v_label]
                    self.current_video_formats[v_label] = video_stream
                audio_labels = ['- Sin Audio -']
                self.current_audio_formats = {}
                if audio_streams:
                    audio_labels = []
                    for stream in audio_streams:
                        idx = stream.get('index', '?')
                        title = stream.get('tags', {}).get('title', f'Pista {idx}')
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
                        self.current_audio_formats[a_label] = stream
                self.video_quality_menu.configure(state='normal' if video_stream else 'disabled', values=video_labels)
                self.video_quality_menu.set(video_labels[0])
                self.audio_quality_menu.configure(state='normal' if audio_streams else 'disabled', values=audio_labels)
                default_audio = next((l for l in audio_labels if '(Default)' in l), audio_labels[0])
                self.audio_quality_menu.set(default_audio)
                if len(audio_streams) > 1:
                    self.batch_use_all_audio_tracks_check.pack(padx=5, pady=(5, 0), anchor='w')
                    use_all_tracks = job.config.get('recode_all_audio_tracks', False)
                    if use_all_tracks:
                        self.batch_use_all_audio_tracks_check.select()
                        self.audio_quality_menu.configure(state='disabled')
                    else:
                        self.batch_use_all_audio_tracks_check.deselect()
                        self.audio_quality_menu.configure(state='normal')
                else:
                    self.batch_use_all_audio_tracks_check.pack_forget()
                    self.batch_use_all_audio_tracks_check.deselect()
                saved_mode = job.config.get('mode', 'Video+Audio')
                self.mode_selector.set(saved_mode)
                if not video_stream and audio_streams:
                    self.mode_selector.set('Solo Audio')
                    self.mode_selector.configure(state='disabled', values=['Solo Audio'])
                else:
                    if video_stream:
                        self.mode_selector.configure(state='normal', values=['Video+Audio', 'Solo Audio'])
                    else:
                        self.mode_selector.set('Video+Audio')
                        self.mode_selector.configure(state='disabled', values=['Video+Audio'])
                self._on_item_mode_change(self.mode_selector.get())
                self.auto_save_thumbnail_check.deselect()
                self.auto_save_thumbnail_check.configure(state='disabled')
                self.save_thumbnail_button.configure(state='normal' if video_stream else 'disabled')
                is_recode_enabled = job.config.get('recode_enabled', False)
                is_keep_original = job.config.get('recode_keep_original', True)
                if is_recode_enabled:
                    self.batch_apply_quick_preset_checkbox.select()
                else:
                    self.batch_apply_quick_preset_checkbox.deselect()
                if is_keep_original:
                    self.batch_keep_original_quick_checkbox.select()
                else:
                    self.batch_keep_original_quick_checkbox.deselect()
                self._populate_batch_preset_menu()
                self._on_batch_quick_recode_toggle()
                self._validate_batch_recode_compatibility()
        else:
            info = job.analysis_data
            self.batch_use_all_audio_tracks_check.pack_forget()
            self.title_entry.delete(0, 'end')
            self.create_placeholder_label(self.thumbnail_container, 'Cargando...')
            self.current_video_formats.clear()
            self.current_audio_formats.clear()
            title = job.config.get('title', '').strip()
            if not title or title in ['Analizando...', 'Sin título', '-']:
                title = (info.get('title') or '').strip()
            if not title:
                title = f'video_{job.job_id[:6]}'
            title = self.app.sanitize_title_global(title)
            job.config['title'] = title
            self.title_entry.insert(0, title)
            print(f'DEBUG: Título establecido para job {job.job_id[:8]}: \'{title}\'')
            formats = info.get('formats', [])
            has_audio_only = any((self._classify_format(f) == 'AUDIO' for f in formats)) and (not any((self._classify_format(f) in ['VIDEO', 'VIDEO_ONLY'] for f in formats)))
            if has_audio_only:
                self.create_placeholder_label(self.thumbnail_container, '🎵', font_size=60)
            else:
                self.create_placeholder_label(self.thumbnail_container, 'Miniatura')
            formats = info.get('formats', [])
            video_entries, audio_entries = ([], [])
            video_duration = info.get('duration', 0)
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
                    if bitrate and video_duration:
                            estimated_bytes = bitrate * 1000 / 8 * video_duration
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
            self.current_video_formats = {e['label']: {k: e['format'].get(k) for k in ['format_id', 'vcodec', 'acodec', 'ext', 'width', 'height']} | {'is_combined': e.get('is_combined', False), 'quality_key': e.get('quality_key')} for e in video_entries}
            self.current_audio_formats = {e['label']: {k: e['format'].get(k) for k in ['format_id', 'acodec', 'ext', 'format_note']} for e in audio_entries}
            has_any_audio = bool(audio_entries) or any((v.get('is_combined', False) for v in self.current_video_formats.values()))
            if not has_any_audio:
                self.mode_selector.set('Video+Audio')
                self.mode_selector.configure(state='disabled', values=['Video+Audio'])
            else:
                if not video_entries and audio_entries:
                    self.mode_selector.set('Solo Audio')
                    self.mode_selector.configure(state='disabled', values=['Solo Audio'])
                else:
                    saved_mode = job.config.get('mode', 'Video+Audio')
                    self.mode_selector.configure(state='normal', values=['Video+Audio', 'Solo Audio'])
                    self.mode_selector.set(saved_mode)
            self._on_item_mode_change(self.mode_selector.get())
            v_opts = list(self.current_video_formats.keys()) or ['-']
            a_opts = list(self.current_audio_formats.keys()) or ['-']
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
            self.video_quality_menu.configure(state='normal' if v_opts[0] != '-' else 'disabled', values=v_opts)
            self.audio_quality_menu.configure(state='normal' if a_opts[0] != '-' else 'disabled', values=a_opts)
            saved_video = job.config.get('video_format_label', '-')
            saved_audio = job.config.get('audio_format_label', '-')
            resolved_v_id = job.config.get('resolved_video_format_id')
            video_selection_to_set = default_video_selection
            if resolved_v_id:
                for label, info in self.current_video_formats.items():
                    if info.get('format_id') == resolved_v_id:
                        video_selection_to_set = label
                        break
            else:
                if saved_video in v_opts:
                    video_selection_to_set = saved_video
            self.video_quality_menu.set(video_selection_to_set)
            self._on_batch_video_quality_change(video_selection_to_set)
            current_audio_opts = self.audio_quality_menu.cget('values')
            audio_selection_to_set = default_audio_selection
            resolved_a_id = job.config.get('resolved_audio_format_id')
            id_match_found = False
            if resolved_a_id:
                for label, info in self.current_audio_formats.items():
                    if info.get('format_id') == resolved_a_id:
                        if label in current_audio_opts:
                            audio_selection_to_set = label
                            id_match_found = True
                        break
            if not id_match_found:
                if saved_audio in current_audio_opts:
                    audio_selection_to_set = saved_audio
                else:
                    if saved_audio in a_opts:
                        audio_selection_to_set = saved_audio
            if audio_selection_to_set not in current_audio_opts and len(current_audio_opts) > 0:
                    audio_selection_to_set = current_audio_opts[0]
            self.audio_quality_menu.set(audio_selection_to_set)
            job.config['audio_format_label'] = audio_selection_to_set
            v_label_set = self.video_quality_menu.get()
            v_info_set = self.current_video_formats.get(v_label_set, {})
            v_id_to_save = v_info_set.get('format_id')
            if v_info_set.get('is_combined'):
                if hasattr(self, 'combined_audio_map'):
                    if self.combined_audio_map and audio_selection_to_set in self.combined_audio_map:
                            v_id_to_save = self.combined_audio_map[audio_selection_to_set]
                            print(f'DEBUG: [Populate] Detectado multiidioma. Video ID resuelto: {v_id_to_save}')
            job.config['video_format_label'] = v_label_set
            job.config['resolved_video_format_id'] = v_id_to_save
            if audio_selection_to_set != '-' and audio_selection_to_set in self.current_audio_formats:
                    sel_audio_data = self.current_audio_formats.get(audio_selection_to_set, {})
                    job.config['resolved_audio_format_id'] = sel_audio_data.get('format_id')
            print(f'DEBUG: Configuración inteligente guardada en Job {job.job_id[:6]}')
            saved_thumbnail = job.config.get('download_thumbnail', False)
            if saved_thumbnail:
                self.auto_save_thumbnail_check.select()
            else:
                self.auto_save_thumbnail_check.deselect()
            self.auto_save_thumbnail_check.configure(state='normal')
            is_recode_enabled = job.config.get('recode_enabled', False)
            is_keep_original = job.config.get('recode_keep_original', True)
            if is_recode_enabled:
                self.batch_apply_quick_preset_checkbox.select()
            else:
                self.batch_apply_quick_preset_checkbox.deselect()
            if is_keep_original:
                self.batch_keep_original_quick_checkbox.select()
            else:
                self.batch_keep_original_quick_checkbox.deselect()
            self._populate_batch_preset_menu()
            self._on_batch_quick_recode_toggle()
            thumbnail_url = job.analysis_data.get('thumbnail')
            if thumbnail_url:
                self.thumb_queue.put((job.job_id, thumbnail_url, False))
            self._updating_ui = False
    def load_thumbnail(self, path_or_url: str, is_local: bool=False):
        # irreducible cflow, using cdg fallback
        """Carga una miniatura (desde URL o archivo local) de forma segura."""
        cache_key = path_or_url
        self.current_thumbnail_url = path_or_url if not is_local else None
        try:
            cached_item = self.thumbnail_cache[cache_key]
            if isinstance(cached_item, dict) and 'ctk' in cached_item:
                cached_image = cached_item['ctk']
                self.current_raw_thumbnail = cached_item.get('raw')
                def set_cached_image():
                    if self.thumbnail_label:
                        self.thumbnail_label.destroy()
                    self.thumbnail_label = ctk.CTkLabel(self.thumbnail_container, text='', image=cached_image)
                    self.thumbnail_label.pack(expand=True)
                    self.thumbnail_label.image = cached_image
                    self.save_thumbnail_button.configure(state='normal')
                self.app.after(0, set_cached_image)
                return
        except KeyError:
            pass
        except Exception as e:
            print(f'ERROR cargando miniatura en caché: {e}')
        self.app.after(0, lambda: self.create_placeholder_label(self.thumbnail_container, 'Cargando...'))
        img_data = None
        try:
            if is_local:
                job = self.queue_manager.get_job_by_id(self.selected_job_id)
                duration = job.analysis_data.get('duration', 0) if job else 0
                frame_path = self.app.ffmpeg_processor.get_frame_from_video(path_or_url, duration)
                if frame_path and os.path.exists(frame_path):
                    with open(frame_path, 'rb') as f:
                        img_data = f.read()
                    os.remove(frame_path)
                else:
                    raise Exception('No se pudo generar el fotograma local.')
            else:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                if 'i.ytimg.com' in path_or_url or 'ytimg.com' in path_or_url:
                    clean_url = path_or_url.split('?')[0]
                    video_id_match = re.search('/vi/([^/]+)/', clean_url)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        max_res_url = f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg'
                    else:
                        max_res_url = re.sub('/(hq|mq|sd|default)default', '/maxresdefault', clean_url)
                    if max_res_url != path_or_url:
                        try:
                            resp_hd = requests.get(max_res_url, headers=headers, timeout=3)
                            if resp_hd.status_code == 200:
                                img_data = resp_hd.content
                                self.current_thumbnail_url = max_res_url
                                self.current_raw_thumbnail = img_data
                                print('DEBUG: ✅ Miniatura HD cargada: maxresdefault')
                        except Exception:
                            pass
                if img_data is None:
                    response = requests.get(path_or_url, headers=headers, timeout=15)
                    response.raise_for_status()
                    img_data = response.content
            if not img_data or len(img_data) < 100:
                raise Exception('Datos de imagen inválidos')
            from PIL import Image, ImageOps
            from io import BytesIO
            pil_image = Image.open(BytesIO(img_data))
            display_image = ImageOps.fit(pil_image, (160, 90), method=Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=display_image, dark_image=display_image, size=display_image.size)
            self.thumbnail_cache[cache_key] = {'ctk': ctk_image, 'raw': img_data}
            self.current_raw_thumbnail = img_data
            def set_new_image():
                if self.thumbnail_label:
                    self.thumbnail_label.destroy()
                self.thumbnail_label = ctk.CTkLabel(self.thumbnail_container, text='', image=ctk_image)
                self.thumbnail_label.pack(expand=True)
                self.thumbnail_label.image = ctk_image
                self.save_thumbnail_button.configure(state='normal')
            self.app.after(0, set_new_image)
        except Exception as e:
            print(f'⚠️ Error al cargar miniatura: {e}')
            self.current_raw_thumbnail = None
            self.app.after(0, lambda: self.create_placeholder_label(self.thumbnail_container, '❌', font_size=60))
    def get_smart_thumbnail_extension(self, image_data):
        # irreducible cflow, using cdg fallback
        """
        Detecta el formato óptimo para guardar la miniatura:
        - PNG si tiene transparencia
        - JPG en otros casos (más compacto)
        """
        from PIL import Image
        import io
        try:
            img = Image.open(io.BytesIO(image_data))
            if img.mode in ['RGBA', 'LA'] or (img.mode == 'P' and 'transparency' in img.info):
                return '.png'
            return '.jpg'
        except Exception as e:
            print(f'ERROR detectando formato de miniatura: {e}')
            return '.jpg'
    def _detect_thumbnail_format(self, image_data):
        """
        Detect the optimal format for saving the thumbnail:
        - PNG if it has transparency
        - JPG otherwise (more compact)
        """
        from PIL import Image
        import io

        try:
            img = Image.open(io.BytesIO(image_data))
            # Check for transparency
            if img.mode in ['RGBA', 'LA'] or (img.mode == 'P' and 'transparency' in img.info):
                return '.png'
            else:
                return '.jpg'
        except Exception as e:
            print(f'ERROR detecting thumbnail format: {e}')
            return '.jpg'  # fallback

    def _on_auto_save_thumbnail_toggle(self):
        """
        Callback when the individual thumbnail checkbox changes.
        Disables the manual save button and saves the state.
        """
        if self.auto_save_thumbnail_check.get():
            self.save_thumbnail_button.configure(state='disabled')
        else:
            self.save_thumbnail_button.configure(state='normal')

        if not self._updating_ui:
            self._on_batch_config_change()
    def _on_thumbnail_mode_change(self):
        """Callback cuando cambia el modo de descarga global."""
        mode = self.thumbnail_mode_var.get()
        current_job_type = None
        if self.selected_job_id:
            job = self.queue_manager.get_job_by_id(self.selected_job_id)
            if job:
                current_job_type = job.job_type
        if mode == 'normal':
            self.auto_save_thumbnail_check.configure(state='normal')
            self.auto_send_to_it_checkbox.deselect()
            self.auto_send_to_it_checkbox.configure(state='disabled')
            if self.selected_job_id:
                if current_job_type == 'PLAYLIST':
                    self._set_config_panel_state('disabled')
                    self.title_entry.configure(state='normal')
                    self.save_thumbnail_button.configure(state='normal')
                    self.batch_apply_quick_preset_checkbox.configure(state='normal')
                    self._on_batch_quick_recode_toggle()
                else:
                    self._set_config_panel_state('normal')
                    self._on_batch_quick_recode_toggle()
        else:
            if mode == 'with_thumbnail':
                self.auto_save_thumbnail_check.configure(state='disabled')
                self.auto_send_to_it_checkbox.configure(state='normal')
                if self.selected_job_id:
                    if current_job_type == 'PLAYLIST':
                        self._set_config_panel_state('disabled')
                        self.title_entry.configure(state='normal')
                        self.save_thumbnail_button.configure(state='normal')
                        self.batch_apply_quick_preset_checkbox.configure(state='normal')
                        self._on_batch_quick_recode_toggle()
                    else:
                        self._set_config_panel_state('normal')
                        self._on_batch_quick_recode_toggle()
            else:
                if mode == 'only_thumbnail':
                    self.auto_save_thumbnail_check.configure(state='disabled')
                    self.auto_send_to_it_checkbox.configure(state='normal')
                    if self.selected_job_id:
                        self._set_config_panel_state('disabled')
                        self.title_entry.configure(state='normal')
    def _on_apply_global_mode(self, selected_mode: str):
        """\n        Aplica el modo (Video+Audio o Solo Audio) a TODOS los trabajos \n        actuales en la cola.\n        """
        self._update_global_quality_options(selected_mode)
        if self.global_recode_checkbox.get() == 1:
            self._populate_global_preset_menu()
            self._apply_global_recode_settings()
        print(f'INFO: Aplicando modo global \'{selected_mode}\' a todos los trabajos...')
        with self.queue_manager.jobs_lock:
            all_jobs = list(self.queue_manager.jobs)
        if not all_jobs:
            print('INFO: No hay trabajos en la cola para aplicar el modo.')
            return
        else:
            for job in all_jobs:
                job.config['mode'] = selected_mode
            if self.selected_job_id:
                current_job = self.queue_manager.get_job_by_id(self.selected_job_id)
                if current_job:
                    print(f'DEBUG: Refrescando panel de configuración para {self.selected_job_id[:6]}...')
                    self._populate_config_panel(current_job)
            print(f'INFO: Modo global aplicado a {len(all_jobs)} trabajos.')
    def _update_global_quality_options(self, mode):
        """Actualiza las opciones del menú de calidad global según el modo."""
        if mode == 'Video+Audio':
            options = ['Mejor Compatible ✨', 'Mejor Calidad (Auto)', '4K (2160p)', '2K (1440p)', '1080p', '720p', '480p']
        else:
            options = ['Mejor Compatible (MP3/WAV) ✨', 'Mejor Calidad (Auto)', 'Alta (320kbps)', 'Media (128kbps)', 'Baja (64kbps)']
        self.global_quality_menu.configure(values=options)
        self.global_quality_menu.set(options[0])
    def _on_apply_global_quality(self, selected_quality):
        # irreducible cflow, using cdg fallback
        """\n        Recorre la lista de trabajos y selecciona el formato específico\n        que mejor coincida con el criterio global seleccionado.\n        """
        print(f'INFO: Aplicando calidad global \'{selected_quality}\'...')
        mode = self.global_mode_var.get()
        with self.queue_manager.jobs_lock:
            pass
        for job in self.queue_manager.jobs:
                if job.job_type == 'PLAYLIST':
                    continue
                if job.status not in ['PENDING', 'RUNNING']:
                    continue
                if not job.analysis_data:
                    continue
                best_label = self._find_best_label_match(job, mode, selected_quality)
                if best_label:
                    print(f'DEBUG: Job {job.job_id[:6]} -> Seleccionado: \'{best_label}\'')
                    if mode == 'Video+Audio':
                        job.config['video_format_label'] = best_label
                        job.config['mode'] = 'Video+Audio'
                        job.config['audio_format_label'] = best_label
                        job.config['mode'] = 'Solo Audio'
                        if self.selected_job_id:
                            current_job = self.queue_manager.get_job_by_id(self.selected_job_id)
                            if not current_job or current_job.job_type != 'PLAYLIST':
                                    self._populate_config_panel(current_job)
    def _find_best_label_match(self, job, mode, criteria):
        # irreducible cflow, using cdg fallback
        """\n        Busca el mejor formato priorizando: ORIGINAL > Idioma Preferido > Calidad.\n        """
        info = job.analysis_data
        formats = info.get('formats', [])
        duration = info.get('duration', 0)
        video_original_lang = info.get('language')
        if not formats:
            return
        candidates = []
        import re
        for f in formats:
            format_type = self._classify_format(f)
            bitrate = f.get('abr') or f.get('tbr') or 0
            if bitrate == 0:
                note = f.get('format_note', '').lower()
                match = re.search('(\\d+)k', note)
                if match:
                    bitrate = float(match.group(1))
                else:
                    if 'premium' in note or 'high' in note:
                        bitrate = 256
                    else:
                        if 'medium' in note:
                            bitrate = 128
                        else:
                            if 'low' in note or 'ultralow' in note:
                                bitrate = 48
            if bitrate == 0 and duration > 0:
                    filesize = f.get('filesize') or f.get('filesize_approx') or 0
                    if filesize > 0:
                        bitrate = filesize * 8 / duration / 1000
            is_valid_candidate = False
            height = f.get('height', 0)
            if mode == 'Video+Audio':
                if format_type in ['VIDEO', 'VIDEO_ONLY']:
                    is_valid_candidate = True
            else:
                if mode == 'Solo Audio':
                    if format_type == 'AUDIO':
                        is_valid_candidate = True
                        height = 0
                    else:
                        if format_type == 'VIDEO':
                            acodec = f.get('acodec', 'none')
                            if acodec and acodec != 'none':
                                    is_valid_candidate = True
                                    height = 0
            if is_valid_candidate:
                f_note = (f.get('format_note') or '').lower()
                f_lang = f.get('language')
                is_original = False
                if 'original' in f_note:
                    is_original = True
                else:
                    if video_original_lang and f_lang and f_lang.startswith(video_original_lang):
                        is_original = True
                    else:
                        if f.get('language_preference', (-1)) >= 10:
                            is_original = True
                lang_code_raw = f.get('language') or ''
                norm_code = lang_code_raw.replace('_', '-')
                lang_prio = self.app.LANGUAGE_ORDER.get(norm_code, self.app.LANGUAGE_ORDER.get(norm_code.split('-')[0], self.app.DEFAULT_PRIORITY))
                candidates.append({'format': f, 'height': height, 'abr': bitrate, 'is_original': is_original, 'lang_prio': lang_prio, 'ext': f.get('ext', '')})
        if not candidates:
            return
        candidates.sort(key=lambda x: (not x['is_original'], x['lang_prio'], -(x['height'] or 0), -(x['abr'] or 0)))
        selected_format = None
        if mode == 'Solo Audio':
            if 'Mejor Calidad' in criteria:
                originals = [c for c in candidates if c['is_original']]
                if originals:
                    selected_format = originals[0]
                    print(f"DEBUG: Audio Mejor Calidad - Original encontrado: {selected_format['abr']:.0f}kbps")
                else:
                    selected_format = candidates[0]
                    print(f"DEBUG: Audio Mejor Calidad - Fallback (sin originales): {selected_format['abr']:.0f}kbps")
                if 'Mejor Compatible' in criteria:
                    for c in candidates:
                        if c['ext'] in ['m4a', 'mp3']:
                            selected_format = c
                            break
                    if not selected_format:
                        selected_format = candidates[0]
                    if 'Media' in criteria:
                        originals = [c for c in candidates if c['is_original'] and c['abr'] > 0]
                        work_list = originals if originals else [c for c in candidates if c['abr'] > 0]
                        if not work_list:
                            selected_format = candidates[0]
                        else:
                            mid_index = len(work_list) // 2
                            candidate_middle = work_list[mid_index]
                            if candidate_middle['abr'] >= 100:
                                selected_format = candidate_middle
                                print(f"DEBUG: Audio Media - Centro de lista: {selected_format['abr']:.0f}kbps")
                            else:
                                found = False
                                for c in work_list:
                                    if c['abr'] >= 100:
                                        selected_format = c
                                        found = True
                                        print(f"DEBUG: Audio Media - Primero ≥100kbps: {selected_format['abr']:.0f}kbps")
                                        break
                                if not found:
                                    selected_format = candidate_middle
                                    print(f"DEBUG: Audio Media - Centro (todos <100): {selected_format['abr']:.0f}kbps")
                        if 'Baja' in criteria:
                            threshold = 96
                            for c in candidates:
                                if c['abr'] > 0 and c['abr'] <= threshold:
                                        selected_format = c
                                        break
                            if not selected_format:
                                originals = [c for c in candidates if c['is_original'] and c['abr'] > 0]
                                if originals:
                                    originals.sort(key=lambda x: x['abr'])
                                    selected_format = originals[0]
                                else:
                                    candidates_with_bitrate = [c for c in candidates if c['abr'] > 0]
                                    if candidates_with_bitrate:
                                        candidates_with_bitrate.sort(key=lambda x: x['abr'])
                                        selected_format = candidates_with_bitrate[0]
                                    else:
                                        selected_format = candidates[0]
            if 'Mejor Compatible' in criteria:
                for c in candidates:
                    if mode == 'Video+Audio' and c['ext'] == 'mp4' and ('avc' in (c['format'].get('vcodec') or '')):
                                selected_format = c
                                break
                if not selected_format:
                    selected_format = candidates[0]
            else:
                if 'p' in criteria and mode == 'Video+Audio':
                    target_h = 0
                    if '4K' in criteria:
                        target_h = 2160
                    else:
                        if '2K' in criteria:
                            target_h = 1440
                        else:
                            if '1080p' in criteria:
                                target_h = 1080
                            else:
                                if '720p' in criteria:
                                    target_h = 720
                                else:
                                    if '480p' in criteria:
                                        target_h = 480
                    candidates.sort(key=lambda x: (not x['is_original'], abs((x['height'] or 0) - target_h), x['lang_prio']))
                    selected_format = candidates[0]
                else:
                    selected_format = candidates[0]
        if selected_format:
            f = selected_format['format']
            target_id = f.get('format_id')
            print(f"DEBUG: Seleccionado -> {target_id} ({selected_format['abr']:.0f}kbps) [Original: {selected_format['is_original']}]")
            if mode == 'Video+Audio':
                job.config['resolved_video_format_id'] = target_id
                job.config['video_format_label'] = f'Global: {target_id} (Auto)'
            else:
                job.config['resolved_audio_format_id'] = target_id
                job.config['audio_format_label'] = f'Global: {target_id} (Auto)'
            return
    def _on_save_thumbnail_click(self):
        # irreducible cflow, using cdg fallback
        """
        Abre diálogo para guardar la miniatura actual, la re-codifica con PIL
        (preservando transparencia) y la importa a Adobe si está marcado.
        """
        if not self.current_raw_thumbnail:
            print('ERROR: No hay miniatura cargada (datos raw) para guardar.')
            return
        file_name = self.title_entry.get().strip()
        if not file_name:
            file_name = 'thumbnail'
        image_data = self.current_raw_thumbnail
        smart_ext = self.get_smart_thumbnail_extension(image_data)
        file_path = filedialog.asksaveasfilename(
            defaultextension=smart_ext,
            filetypes=[('Imagen Óptima', f'*{smart_ext}'), ('JPEG', '*.jpg'), ('PNG', '*.png'), ('Todos', '*.*')],
            initialfile=f'{file_name}{smart_ext}'
        )
        self.app.lift()
        self.app.focus_force()
        if not file_path:
            return
        try:
            pil_image = Image.open(BytesIO(image_data))
            final_ext_chosen = os.path.splitext(file_path)[1].lower()
            if final_ext_chosen == '.png':
                pil_image.save(file_path, 'PNG')
                print(f'INFO: Miniatura guardada como PNG (con transparencia): {file_path}')
            else:
                pil_image.convert('RGB').save(file_path, 'JPEG', quality=95)
                print(f'INFO: Miniatura guardada como JPG (sin transparencia): {file_path}')
            self.app.integration_manager.broadcast_import(source_path=file_path, thumb_path=None, workflow_type='batch', bin_name=None)
        except Exception as e:
            print(f'ERROR: No se pudo guardar o importar la miniatura manualmente: {e}')
    def _classify_format(self, f):
        """\n        Clasifica un formato (v3.2 - Manejo de codecs \'unknown\')\n        """
        ext = f.get('ext', '')
        vcodec = f.get('vcodec', '')
        acodec = f.get('acodec', '')
        format_id = (f.get('format_id') or '').lower()
        format_note = (f.get('format_note') or '').lower()
        protocol = f.get('protocol', '')
        if 'audio directo' in format_note or 'livestream' in format_note:
            if 'audio' in format_note:
                return 'AUDIO'
            else:
                return 'VIDEO'
        else:
            vcodec_special_cases = {'audio only': 'AUDIO', 'images': 'VIDEO', 'slideshow': 'VIDEO'}
            if vcodec in vcodec_special_cases:
                return vcodec_special_cases[vcodec]
            else:
                if ext == 'gif' or vcodec == 'gif':
                    return 'VIDEO'
                else:
                    if f.get('height') or f.get('width'):
                        vcodec_is_unknown = not vcodec or vcodec in ['unknown', 'N/A', '']
                        acodec_is_unknown = not acodec or acodec in ['unknown', 'N/A', '']
                        if vcodec_is_unknown and acodec_is_unknown:
                            print(f"DEBUG: Formato {f.get('format_id')} con codecs desconocidos → asumiendo VIDEO combinado")
                            return 'VIDEO'
                        else:
                            if acodec in ['none']:
                                return 'VIDEO_ONLY'
                            else:
                                return 'VIDEO'
                    else:
                        if f.get('is_live') or 'live' in format_id:
                            return 'VIDEO'
                        else:
                            resolution_patterns = ['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p', '4320p']
                            if any((res in format_note for res in resolution_patterns)):
                                if acodec in ['none']:
                                    return 'VIDEO_ONLY'
                                else:
                                    return 'VIDEO'
                            else:
                                if 'audio' in format_id or 'audio' in format_note:
                                    return 'AUDIO'
                                else:
                                    if 'video' in format_id or 'video' in format_note:
                                        if f.get('height') or (vcodec == 'unknown' and acodec == 'unknown'):
                                            return 'VIDEO'
                                        else:
                                            return 'VIDEO_ONLY' if acodec in ['none'] else 'VIDEO'
                                    else:
                                        if ext in self.app.AUDIO_EXTENSIONS:
                                            return 'AUDIO'
                                        else:
                                            if vcodec == 'none' and acodec and (acodec not in ['none', '', 'N/A', 'unknown']):
                                                        return 'AUDIO'
                                            if acodec == 'none' and vcodec and (vcodec not in ['none', '', 'N/A', 'unknown']):
                                                        return 'VIDEO_ONLY'
                                            if ext in self.app.VIDEO_EXTENSIONS:
                                                if vcodec in ['unknown', ''] and acodec in ['unknown', '']:
                                                        return 'VIDEO'
                                                return 'VIDEO'
                                            else:
                                                valid_vcodecs = ['h264', 'h265', 'vp8', 'vp9', 'av1', 'hevc', 'mpeg4', 'xvid', 'theora']
                                                valid_acodecs = ['aac', 'mp3', 'opus', 'vorbis', 'flac', 'ac3', 'eac3', 'pcm']
                                                vcodec_lower = (vcodec or '').lower()
                                                acodec_lower = (acodec or '').lower()
                                                if vcodec_lower in valid_vcodecs:
                                                    if acodec_lower in valid_acodecs:
                                                        return 'VIDEO'
                                                    else:
                                                        return 'VIDEO_ONLY'
                                                else:
                                                    if 'm3u8' in protocol or 'dash' in protocol:
                                                        return 'VIDEO'
                                                    else:
                                                        if f.get('tbr') and (not f.get('abr')):
                                                                return 'VIDEO'
                                                        if f.get('abr') and (not f.get('vbr')):
                                                                return 'AUDIO'
                                                        if ext in self.app.VIDEO_EXTENSIONS:
                                                            print(f"⚠️ ADVERTENCIA: Formato {f.get('format_id')} ambiguo → asumiendo VIDEO combinado por extensión")
                                                            return 'VIDEO'
                                                        else:
                                                            print(f"⚠️ ADVERTENCIA: Formato sin clasificación clara: {f.get('format_id')} (vcodec={vcodec}, acodec={acodec}, ext={ext})")
                                                            return 'UNKNOWN'
    def _get_format_compatibility_issues(self, format_dict):
        """Comprueba compatibilidad."""
        if not format_dict:
            return ([], [])
        else:
            issues = []
            unknown = []
            vcodec = (format_dict.get('vcodec') or 'none').split('.')[0]
            acodec = (format_dict.get('acodec') or 'none').split('.')[0]
            ext = format_dict.get('ext') or 'none'
            if vcodec != 'none' and vcodec not in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_vcodecs']:
                    issues.append(f'video ({vcodec})')
            if acodec != 'none' and acodec not in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_acodecs']:
                    issues.append(f'audio ({acodec})')
            if vcodec != 'none' and ext not in self.app.EDITOR_FRIENDLY_CRITERIA['compatible_exts']:
                    issues.append(f'contenedor (.{ext})')
            return (issues, unknown)
    def _on_global_options_toggle(self):
        """Activa o desactiva la cadena de menús globales."""
        is_enabled = self.global_options_checkbox.get()
        state = 'normal' if is_enabled else 'disabled'
        self.mode_menu.configure(state=state)
        if is_enabled:
            self._on_mode_change(self.mode_menu.get())
        else:
            self.container_menu.configure(state='disabled', values=['- (Opciones Desact.) -'])
            self.quality_menu.configure(state='disabled', values=['- (Opciones Desact.) -'])
            self.container_menu.set('- (Opciones Desact.) -')
            self.quality_menu.set('- (Opciones Desact.) -')
    def _on_mode_change(self, mode: str):
        """Actualiza el menú de Contenedores global."""
        if not self.global_options_checkbox.get():
            return
        else:
            containers = ['-']
            if mode == 'Video+Audio':
                containers = ['mp4', 'mkv', 'mov', 'webm']
            else:
                if mode == 'Solo Audio':
                    containers = ['mp3', 'wav', 'm4a', 'flac', 'opus']
            self.container_menu.configure(state='normal', values=containers)
            if containers:
                self.container_menu.set(containers[0])
                self._on_container_change(containers[0])
            else:
                self._on_container_change(None)
    def _on_container_change(self, container: str | None):
        """Actualiza el menú de Calidad global."""
        if not self.global_options_checkbox.get() or container is None:
            self.quality_menu.configure(state='disabled', values=['-'])
            self.quality_menu.set('-')
            return
        else:
            mode = self.mode_menu.get()
            qualities = ['-']
            if mode == 'Video+Audio':
                qualities = ['Mejor (bv+ba/b)', '4K (2160p)', '2K (1440p)', '1080p', '720p', '480p', 'Peor (wv+wa/w)']
            else:
                if mode == 'Solo Audio':
                    qualities = ['Mejor Audio (ba)', 'Alta (256k)', 'Media (192k)', 'Baja (128k)']
            self.quality_menu.configure(state='normal', values=qualities)
            if qualities:
                self.quality_menu.set(qualities[0])
    def start_queue_processing(self):
        """Inicia o pausa el procesamiento de la cola."""
        # 1. Crear subcarpeta si es necesario (solo una vez)
        if not getattr(self.queue_manager, 'subfolder_created', False) and self.create_subfolder_checkbox.get():
            output_dir = self.output_path_entry.get()
            subfolder_name = self.subfolder_name_entry.get().strip() or 'DowP List'
            subfolder_path = os.path.join(output_dir, subfolder_name)

            # Evitar duplicados
            counter = 1
            while os.path.exists(subfolder_path):
                new_name = f'{subfolder_name} {counter:02d}'
                subfolder_path = os.path.join(output_dir, new_name)
                counter += 1

            try:
                os.makedirs(subfolder_path, exist_ok=True)
                self.queue_manager.subfolder_path = subfolder_path
                self.queue_manager.subfolder_created = True
                print(f'INFO: Subcarpeta creada: {subfolder_path}')
                self.open_folder_button.configure(state='normal')
            except Exception as e:
                print(f'ERROR: No se pudo crear la subcarpeta: {e}')
                return  # Salir sin iniciar la cola

        # 2. Control de pausa/reanudación
        if self.queue_manager.pause_event.is_set():
            # Si está pausada, reanudar
            print('INFO: Reanudando la cola de lotes.')
            self.queue_manager.start_queue()
        else:
            # Si no está pausada, pausar
            print('INFO: Pausando la cola de lotes.')
            self.queue_manager.pause_queue()
    def select_output_folder(self):
        """Abre el diálogo para seleccionar la carpeta de salida."""
        folder_path = filedialog.askdirectory()
        self.app.lift()
        self.app.focus_force()
        if folder_path:
            self.output_path_entry.delete(0, 'end')
            self.output_path_entry.insert(0, folder_path)
            self.save_settings()
            self.open_folder_button.configure(state='normal')
    def _open_batch_output_folder(self):
        """
        Abre la carpeta de salida principal del lote.
        Prioritiza la subcarpeta del lote si fue creada.
        """
        path_to_open = None
        if hasattr(self.queue_manager, 'subfolder_path') and self.queue_manager.subfolder_path:
            if os.path.isdir(self.queue_manager.subfolder_path):
                path_to_open = self.queue_manager.subfolder_path
            else:
                path_to_open = os.path.dirname(self.queue_manager.subfolder_path)
        if not path_to_open:
            path_to_open = self.output_path_entry.get()
        if not path_to_open or not os.path.isdir(path_to_open):
            print(f'ERROR: La carpeta de salida \'{path_to_open}\' no es válida o no existe.')
            return
        try:
            print(f'INFO: Abriendo carpeta de salida del lote: {path_to_open}')
            if os.name == 'nt':
                import subprocess
                subprocess.Popen(['explorer', os.path.normpath(path_to_open)])
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', path_to_open])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path_to_open])
        except Exception as e:
            print(f'Error al intentar abrir la carpeta: {e}')
    def create_entry_context_menu(self, widget):
        """Crea un menú contextual simple para los Entry widgets."""
        menu = Menu(self, tearoff=0)
        def copy_text():
            """Copia el texto seleccionado al portapapeles."""
            try:
                selected_text = widget.selection_get()
                if selected_text:
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
            except Exception:
                return None
        def cut_text():
            """Corta el texto seleccionado (copia y borra)."""
            try:
                selected_text = widget.selection_get()
                if selected_text:
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
                    widget.delete('sel.first', 'sel.last')
            except Exception:
                return None
        def paste_text():
            """Pega el texto del portapapeles."""
            try:
                if widget.selection_get():
                    widget.delete('sel.first', 'sel.last')
            except Exception:
                pass
            try:
                widget.insert('insert', self.clipboard_get())
            except Exception:
                return None
        menu.add_command(label='Cortar', command=cut_text)
        menu.add_command(label='Copiar', command=copy_text)
        menu.add_command(label='Pegar', command=paste_text)
        menu.add_separator()
        menu.add_command(label='Seleccionar todo', command=lambda: widget.select_range(0, 'end'))
        menu.tk_popup(widget.winfo_pointerx(), widget.winfo_pointery())
    def _on_clear_list_click(self):
        """\n        Elimina todos los trabajos de la cola y resetea la sesión de lote.\n        """
        print('INFO: Limpiando la lista de trabajos y reseteando la sesión de lote...')
        self.queue_manager.pause_queue()
        all_job_ids = list(self.job_widgets.keys())
        for job_id in all_job_ids:
            self._remove_job(job_id)
        self.playlist_cache.clear()
        print('DEBUG: 🧹 Caché completa de playlists limpiada')
        if hasattr(self.queue_manager, 'subfolder_path'):
            delattr(self.queue_manager, 'subfolder_path')
        if hasattr(self.queue_manager, 'subfolder_created'):
            delattr(self.queue_manager, 'subfolder_created')
        self.start_queue_button.configure(text='Iniciar Cola', fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, state='disabled')
        self.global_recode_checkbox.configure(state='disabled')
        self.global_recode_preset_menu.configure(state='disabled')
        self.global_recode_checkbox.deselect()
        self.progress_label.configure(text='Cola vacía. Analiza una URL para empezar.')
        self._set_local_batch_mode(False)
        print('INFO: Sesión de lote finalizada.')
    def _on_reset_status_click(self):
        """\n        Resetea el estado de trabajos (COMPLETED/FAILED -> PENDING) \n        y resetea la sesión de lote para una nueva ejecución.\n        """
        print('INFO: Reseteando estado de trabajos para un nuevo lote...')
        self.queue_manager.pause_queue()
        self.queue_manager.reset_progress()
        jobs_to_reset = []
        with self.queue_manager.jobs_lock:
            for job in self.queue_manager.jobs:
                if job.status in ['COMPLETED', 'FAILED', 'SKIPPED', 'NO_AUDIO']:
                    jobs_to_reset.append(job)
        if not jobs_to_reset:
            print('INFO: No hay trabajos completados/fallidos que resetear.')
        else:
            for job in jobs_to_reset:
                job.status = 'PENDING'
                self.app.after(0, self.update_job_ui, job.job_id, 'PENDING', 'Listo para descargar')
            print(f'INFO: {len(jobs_to_reset)} trabajos reseteados a PENDIENTE.')
        if hasattr(self.queue_manager, 'subfolder_path'):
            delattr(self.queue_manager, 'subfolder_path')
            print('INFO: Reseteada la subcarpeta del lote anterior.')
        if hasattr(self.queue_manager, 'subfolder_created'):
            delattr(self.queue_manager, 'subfolder_created')
        jobs_exist = len(self.job_widgets) > 0
        if self.is_local_mode:
            self.start_queue_button.configure(text='Iniciar Proceso', fg_color=self.PROCESS_BTN_COLOR, hover_color=self.PROCESS_BTN_HOVER, state='normal' if jobs_exist else 'disabled')
        else:
            self.start_queue_button.configure(text='Iniciar Cola', fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER, state='normal' if jobs_exist else 'disabled')
        self.global_recode_checkbox.configure(state='normal' if jobs_exist else 'disabled')
        if not jobs_exist:
            self.global_recode_preset_menu.configure(state='disabled')
            self.global_recode_checkbox.deselect()
        if jobs_exist:
            self.progress_label.configure(text='Estado reseteado. Listo para iniciar un nuevo lote.')
        else:
            self.progress_label.configure(text='Cola vacía. Analiza una URL para empezar.')
        print('INFO: Sesión de lote finalizada. Listo para un nuevo lote.')
    def _on_reset_single_job(self, job_id: str):
        """Resetea un único trabajo (COMPLETED/FAILED/SKIPPED) a PENDING."""
        job = self.queue_manager.get_job_by_id(job_id)
        if not job:
            print(f'ERROR: No se encontró job {job_id} para resetear.')
            return
        else:
            if job.status in ['COMPLETED', 'FAILED', 'SKIPPED', 'NO_AUDIO']:
                print(f'INFO: Reseteando estado para job {job_id}.')
                job.status = 'PENDING'
                self.update_job_ui(job_id, 'PENDING', 'Listo para descargar')
                if self.queue_manager.pause_event.is_set():
                    current_text = self.start_queue_button.cget('text')
                    if current_text != 'Pausar Cola':
                        self.start_queue_button.configure(state='normal')
                        self.progress_label.configure(text='Trabajo reseteado. Listo para reanudar la cola.')
            else:
                print(f'INFO: Job {job_id} ya está PENDING o RUNNING, no se resetea.')
    def _on_analyze_click(self):
        """Inicia el análisis de la URL en un hilo separado."""
        if self.is_local_mode:
            print('INFO: Saliendo del modo local. Limpiando cola de recodificación.')
            self._on_clear_list_click()
            self._set_local_batch_mode(False)
        url = self.url_entry.get().strip()
        if not url:
            return
        else:
            print(f'INFO: Iniciando análisis de lotes para: {url}')
            config = {'url': url, 'title': 'Analizando...', 'mode': 'Video+Audio', 'video_format_label': '-', 'audio_format_label': '-'}
            temp_job = Job(config=config)
            if self.job_widgets:
                pass
            else:
                self.queue_placeholder_label.pack_forget()
            self.queue_manager.add_job(temp_job)
            self.app.after(0, lambda: self.update_job_ui(temp_job.job_id, 'RUNNING', 'Analizando URL...'))
            threading.Thread(target=self._run_analysis, args=(url, temp_job.job_id), daemon=True).start()
            self.url_entry.delete(0, 'end')
    def _run_analysis(self, url: str, job_id: str):
        """\n        Hilo de trabajo que ejecuta yt-dlp para obtener información.\n        Soporta cancelación y reporte de progreso de playlist en UI.\n        """
        class AnalysisCancelled(Exception):
            # return None
            pass
        class MyLogger:
            def __init__(self, parent_tab, j_id):
                self.parent = parent_tab
                self.job_id = j_id
            def _process_message(self, msg):
                # irreducible cflow, using cdg fallback
                clean_msg = re.sub('\\x1B(?:[@-Z\\\\-_]|\\[[0-?]*[ -/]*[@-~])', '', msg)
                if 'Downloading item' in clean_msg or 'Downloading video' in clean_msg:
                    pass
                match = re.search('(?:item|video)\\s+(\\d+)\\s+of\\s+(\\d+)', clean_msg, re.IGNORECASE)
                if match:
                    current = match.group(1)
                    total = match.group(2)
                    try:
                        self.parent.app.after(0, self.parent.update_job_ui, self.job_id, 'RUNNING', f'Analizando {current} de {total}...')
                    except Exception:
                        return
            def debug(self, msg):
                self._process_message(msg)
                print(msg)
            def info(self, msg):
                self._process_message(msg)
                print(msg)
            def warning(self, msg):
                print(f'WARNING: {msg}')
            def error(self, msg):
                print(f'ERROR: {msg}')
            def debug(self, msg):
                self._process_message(msg)
            def info(self, msg):
                self._process_message(msg)
            def warning(self, msg):
                return
            def error(self, msg):
                print(f'Logger Error: {msg}')
        try:
            single_tab = self.app.single_tab
            try:
                analizar_playlist = self.playlist_analysis_check.get()
                user_wants_fast = self.fast_mode_check.get()
            except Exception as e:
                print(f'ADVERTENCIA: No se pudo leer las casillas: {e}')
                analizar_playlist = True
                user_wants_fast = True
            print(f'DEBUG: Iniciando análisis. Playlist: {analizar_playlist}, Rápido: {user_wants_fast}')
            is_fast_compatible = any((domain in url.lower() for domain in FAST_MODE_SUPPORTED_DOMAINS))
            use_fast_mode = is_fast_compatible and analizar_playlist and user_wants_fast
            if use_fast_mode:
                print('DEBUG: 🚀 Modo Rápido activado (extract_flat)')
            else:
                print('DEBUG: 🐢 Modo Lento/Profundo activado (Análisis completo)')
            def check_if_cancelled(info_dict, *args, **kwargs):
                job = self.queue_manager.get_job_by_id(job_id)
                if not job:
                    print(f'DEBUG: 🛑 Análisis abortado para {job_id} (El trabajo fue eliminado).')
                    raise AnalysisCancelled('Análisis cancelado por el usuario.')
            ydl_opts = {'no_warnings': True, 'quiet': False, 'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.0 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'referer': url, 'noplaylist': not analizar_playlist, 'listsubtitles': False, 'ignoreerrors': True, 'match_filter': check_if_cancelled, 'logger': MyLogger(self, job_id)}
            if use_fast_mode:
                ydl_opts['extract_flat'] = 'in_playlist'
            cookie_mode = self.app.cookies_mode_saved
            using_cookies = False
            browser_arg = None
            profile = None
            if cookie_mode == 'Archivo Manual...' and self.app.cookies_path:
                ydl_opts['cookiefile'] = self.app.cookies_path
                using_cookies = True
            else:
                if cookie_mode != 'No usar':
                    browser_arg = self.app.selected_browser_saved
                    profile = self.app.browser_profile_saved
                    if profile:
                        browser_arg_with_profile = f'{browser_arg}:{profile}'
                        ydl_opts['cookiesfrombrowser'] = (browser_arg_with_profile,)
                        using_cookies = True
                    else:
                        ydl_opts['cookiesfrombrowser'] = (browser_arg,)
                        using_cookies = True
            if using_cookies:
                ydl_opts = apply_yt_patch(ydl_opts)
                print('🔧 Batch: Parche aplicado (cookies habilitadas)')
            else:
                print('📝 Batch: Sin cookies - configuración predeterminada')
            info_dict = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                check_if_cancelled(None)
                self.app.after(0, self.update_job_ui, job_id, 'RUNNING', 'Conectando...')
                info_dict = ydl.extract_info(url, download=False)
            if not info_dict:
                raise Exception('No se pudo obtener información.')
            else:
                info_dict = self._normalize_info_dict(info_dict)
                if self.queue_manager.get_job_by_id(job_id):
                    self.app.after(0, self._on_analysis_complete, info_dict, job_id)
                else:
                    print('DEBUG: Análisis completado pero descartado (Job eliminado).')
        except AnalysisCancelled:
            print('INFO: Análisis detenido limpiamente (Cancelado por usuario).')
        except Exception as e:
            if not self.queue_manager.get_job_by_id(job_id):
                print(f'DEBUG: Error en análisis silenciado (Job eliminado): {e}')
                return
            else:
                error_message = f'ERROR: Falló el análisis de lotes: {e}'
                print(error_message)
                error_str = str(e)
                self.app.after(0, self._on_analysis_failed, job_id, error_str)
    def _on_analysis_failed(self, job_id: str, error_message: str):
        """Callback del hilo principal cuando un análisis falla."""
        self.update_job_ui(job_id, 'FAILED', f'Error: {error_message[:80]}')
    def _on_analysis_complete(self, info_dict: dict, job_id: str):
        """Se ejecuta en el hilo principal cuando el análisis termina."""
        job = self.queue_manager.get_job_by_id(job_id)
        if not job:
            return
        else:
            job_widget = self.job_widgets.get(job_id)
            if not info_dict or not isinstance(info_dict, dict):
                print(f'ERROR: info_dict inválido para job {job_id}')
                self.update_job_ui(job_id, 'FAILED', 'Error: Datos de análisis inválidos')
                return
            else:
                global_recode_enabled = self.global_recode_checkbox.get() == 1
                global_preset_name = self.global_recode_preset_menu.get()
                global_preset_params = self._find_preset_params(global_preset_name)
                if not global_preset_params or global_preset_name.startswith('---'):
                    global_recode_enabled = False
                global_preset_mode = global_preset_params.get('mode_compatibility', 'Video+Audio')
                global_keep_original = global_preset_params.get('keep_original_file', True)
                if global_recode_enabled:
                    print(f'DEBUG: Aplicando config global a nuevos jobs (Preset: {global_preset_name})')
                is_playlist = info_dict.get('_type') == 'playlist' or (info_dict.get('entries') and len(info_dict.get('entries')) > 0)
                if is_playlist and info_dict.get('extractor_key') != 'Generic':
                    first_entry = info_dict.get('entries', [{}])[0]
                    is_flat_result = first_entry.get('_type') in ['url', 'url_transparent']
                    if is_flat_result:
                        print('INFO: Resultado \'flat\' detectado. Abriendo selector de playlist...')
                        for i, entry in enumerate(info_dict.get('entries', [])):
                            if not entry.get('title'):
                                fallback = entry.get('id') or entry.get('url', '').split('/')[(-1)] or f'Item {i + 1}'
                                entry['title'] = fallback
                        self.playlist_cache[job_id] = {'info_dict': info_dict, 'thumbnails': {}}
                        print(f'DEBUG: 💾 Playlist cacheada para job {job_id[:6]}')
                        self._open_playlist_selector(job, info_dict)
                        return
                    else:
                        entries = info_dict.get('entries', [])
                        if not entries:
                            self.update_job_ui(job_id, 'FAILED', 'Error: Playlist/Colección está vacía.')
                            return
                        else:
                            print(f'INFO: Playlist detectada con {len(entries)} videos (Modo Clásico).')
                            all_jobs = [job]
                            for i in range(1, len(entries)):
                                all_jobs.append(Job(config={}))
                            for i, (entry, current_job) in enumerate(zip(entries, all_jobs)):
                                if not entry:
                                    continue
                                else:
                                    video_url = entry.get('webpage_url') or entry.get('url') or job.config.get('url')
                                    title = entry.get('title') or entry.get('id') or f'Video {i + 1}'
                                    playlist_index = entry.get('playlist_index', i + 1)
                                    current_job.config['url'] = video_url
                                    current_job.config['title'] = title
                                    current_job.config['playlist_index'] = playlist_index
                                    current_job.analysis_data = entry
                                    if global_recode_enabled:
                                        current_job.config['mode'] = global_preset_mode
                                        current_job.config['recode_enabled'] = True
                                        current_job.config['recode_preset_name'] = global_preset_name
                                        current_job.config['recode_keep_original'] = global_keep_original
                                    else:
                                        current_job.config['mode'] = self.global_mode_var.get()
                                        current_job.config['recode_enabled'] = False
                                        current_job.config['recode_preset_name'] = '-'
                                        current_job.config['recode_keep_original'] = True
                                    if current_job == job:
                                        if job_widget:
                                            job_widget.title_label.configure(text=title)
                                    else:
                                        self.queue_manager.add_job(current_job)
                else:
                    print('INFO: Video único detectado.')
                    title = (info_dict.get('title') or '').strip()
                    if not title:
                        title = f'video_{job.job_id[:8]}'
                    job.config['title'] = title
                    job.analysis_data = info_dict
                    job.config['playlist_index'] = None
                    if global_recode_enabled:
                        job.config['mode'] = global_preset_mode
                        job.config['recode_enabled'] = True
                        job.config['recode_preset_name'] = global_preset_name
                        job.config['recode_keep_original'] = global_keep_original
                    else:
                        job.config['mode'] = self.global_mode_var.get()
                        job.config['recode_enabled'] = False
                        job.config['recode_preset_name'] = '-'
                        job.config['recode_keep_original'] = True
                    if job_widget:
                        job_widget.title_label.configure(text=title)
                self.update_job_ui(job_id, 'PENDING', 'Listo para descargar')
                self.start_queue_button.configure(state='normal')
                self.global_recode_checkbox.configure(state='normal')
                if self.global_recode_checkbox.get() == 1:
                    self._populate_global_preset_menu()
                    self.global_recode_preset_menu.configure(state='normal')
                self._on_job_select(job_id)
                if self.auto_download_checkbox.get():
                    print('INFO: Auto-descargar activado.')
                    if not self.queue_manager.user_paused:
                        if self.queue_manager.pause_event.is_set():
                            print('INFO: Auto-descargar iniciando/reanudando la cola...')
                            if hasattr(self.queue_manager, 'subfolder_created'):
                                delattr(self.queue_manager, 'subfolder_created')
                            self.start_queue_processing()
                            self.progress_label.configure(text='Descargando automáticamente...')
                        else:
                            print('INFO: Auto-descargar: La cola ya estaba corriendo.')
                    else:
                        print('INFO: Auto-descargar: La cola está pausada por el usuario, no se reanudará.')
                        self.progress_label.configure(text=f'Cola pausada. {len(self.job_widgets)} trabajos en espera.')
                else:
                    self.progress_label.configure(text='Análisis completado. Presiona \'Iniciar Cola\' para empezar.')
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
        self._on_batch_config_change()
    def _on_batch_config_change(self, event=None):
        if self._updating_ui:
            return
        else:
            if not self.selected_job_id:
                return
            else:
                job = self.queue_manager.get_job_by_id(self.selected_job_id)
                if not job:
                    return
                else:
                    job.config['title'] = self.title_entry.get()
                    job.config['mode'] = self.mode_selector.get()
                    job.config['video_format_label'] = self.video_quality_menu.get()
                    job.config['audio_format_label'] = self.audio_quality_menu.get()
                    job.config['download_thumbnail'] = self.auto_save_thumbnail_check.get()
                    is_recode_enabled = self.batch_apply_quick_preset_checkbox.get() == 1
                    is_keep_original = self.batch_keep_original_quick_checkbox.get() == 1
                    job.config['recode_enabled'] = is_recode_enabled
                    job.config['recode_preset_name'] = self.batch_recode_preset_menu.get()
                    job.config['recode_keep_original'] = is_keep_original
                    job.config['recode_all_audio_tracks'] = self.batch_use_all_audio_tracks_check.get() == 1
                    selected_tag = self.tags_menu.get()
                    job.config['selected_tag'] = selected_tag
                    if selected_tag == '- Etiqueta -':
                        job.config['custom_output_path'] = None
                    else:
                        job.config['custom_output_path'] = self.tags_manager.get_tag_path(selected_tag)
                    print(f'DEBUG: [Guardando Job {job.job_id[:6]}] Recodificación: {is_recode_enabled}, Mantener Original: {is_keep_original}')
                    v_label = self.video_quality_menu.get()
                    a_label = self.audio_quality_menu.get()
                    v_info = self.current_video_formats.get(v_label, {})
                    a_info = self.current_audio_formats.get(a_label, {})
                    v_id = v_info.get('format_id')
                    if v_info.get('is_combined') and hasattr(self, 'combined_audio_map') and self.combined_audio_map and (a_label in self.combined_audio_map):
                                    v_id = self.combined_audio_map[a_label]
                                    print(f'DEBUG: [ConfigChange] Guardando format_id multiidioma: {v_id}')
                    job.config['resolved_video_format_id'] = v_id
                    if job.job_type == 'LOCAL_RECODE':
                        job.config['resolved_audio_stream_index'] = a_info.get('index')
                        print(f"DEBUG: [Guardando Job Local] Índice de audio resuelto: {a_info.get('index')}")
                    else:
                        job.config['resolved_audio_format_id'] = a_info.get('format_id')
    def _normalize_info_dict(self, info):
        """\n        Normaliza el diccionario de info para casos donde yt-dlp no devuelve \'formats\'.\n        Maneja contenido de audio directo, GIF, directos, etc.\n        """
        if not info:
            return info
        else:
            info = apply_site_specific_rules(info)
            formats = info.get('formats', [])
            if formats:
                return info
            else:
                print(f"DEBUG: ℹ️ Info sin formatos detectada. Extractor: {info.get('extractor_key')}")
                url = info.get('url')
                ext = info.get('ext')
                vcodec = info.get('vcodec', 'none')
                acodec = info.get('acodec')
                is_audio_content = False
                if url and ext and (vcodec == 'none' or not vcodec) and acodec and (acodec != 'none'):
                    is_audio_content = True
                    print('DEBUG: 🎵 Audio directo detectado por codecs')
                else:
                    if ext in self.app.AUDIO_EXTENSIONS:
                        is_audio_content = True
                        print(f'DEBUG: 🎵 Audio directo detectado por extensión (.{ext})')
                        if not acodec or acodec == 'none':
                            acodec = {'mp3': 'mp3', 'opus': 'opus', 'aac': 'aac', 'm4a': 'aac'}.get(ext, ext)
                    else:
                        if info.get('extractor_key', '').lower() in ['applepodcasts', 'soundcloud', 'audioboom', 'spreaker', 'libsyn']:
                            is_audio_content = True
                            print('DEBUG: 🎵 Audio directo detectado por extractor')
                            if not acodec:
                                acodec = 'mp3'
                if is_audio_content:
                    synthetic_format = {'format_id': '0', 'url': url or info.get('manifest_url') or '', 'ext': ext or 'mp3', 'vcodec': 'none', 'acodec': acodec or 'unknown', 'abr': info.get('abr'), 'tbr': info.get('tbr'), 'filesize': info.get('filesize'), 'filesize_approx': info.get('filesize_approx'), 'protocol': info.get('protocol', 'https'), 'format_note': 'Audio directo'}
                    info['formats'] = [synthetic_format]
                    print('DEBUG: ✅ Formato sintético creado (audio)')
                    return info
                else:
                    if url and ext and (ext in self.app.VIDEO_EXTENSIONS):
                        is_video_content = False
                        if vcodec and vcodec != 'none':
                                is_video_content = True
                                print('DEBUG: 🎬 Video directo detectado por vcodec')
                        if ext in ['gif', 'mp4', 'webm', 'mov', 'avi']:
                            is_video_content = True
                            print(f'DEBUG: 🎬 Video directo detectado por extensión (.{ext})')
                        extractor = info.get('extractor_key', '').lower()
                        if any((x in extractor for x in ['imgur', 'gfycat', 'giphy', 'tenor'])):
                            is_video_content = True
                            print(f'DEBUG: 🎬 Video directo detectado por extractor: {extractor}')
                        if is_video_content:
                            synthetic_format = {'format_id': '0', 'url': url or info.get('manifest_url') or '', 'ext': ext or 'mp4', 'vcodec': vcodec or 'h264', 'acodec': acodec or 'none', 'abr': info.get('abr'), 'tbr': info.get('tbr'), 'width': info.get('width'), 'height': info.get('height'), 'filesize': info.get('filesize'), 'filesize_approx': info.get('filesize_approx'), 'protocol': info.get('protocol', 'https'), 'format_note': 'Video directo'}
                            info['formats'] = [synthetic_format]
                            print('DEBUG: ✅ Formato sintético creado (video directo)')
                            return info
                    if info.get('is_live') and info.get('manifest_url'):
                        print('DEBUG: 📡 Livestream detectado sin formatos')
                        synthetic_format = {'format_id': 'live', 'url': info.get('manifest_url'), 'ext': info.get('ext', 'mp4'), 'protocol': 'm3u8_native', 'format_note': 'Livestream', 'vcodec': info.get('vcodec', 'h264'), 'acodec': info.get('acodec', 'aac')}
                        info['formats'] = [synthetic_format]
                        print('DEBUG: ✅ Formato sintético creado (livestream)')
                        return info
                    else:
                        print('DEBUG: ⚠️ No se pudo determinar tipo de contenido')
                        print(f'     ext={ext}, vcodec={vcodec}, acodec={acodec}')
                        print(f"     extractor={info.get('extractor_key')}")
                        synthetic_format = {'format_id': 'best', 'url': url or info.get('manifest_url') or '', 'ext': ext or 'mp4', 'vcodec': vcodec or 'unknown', 'acodec': acodec or 'unknown', 'format_note': 'Contenido genérico'}
                        info['formats'] = [synthetic_format]
                        print('DEBUG: ✅ Formato genérico fallback creado')
                        return info
    def _initialize_ui_settings(self):
        """Carga la configuración guardada en la UI al iniciar."""
        if self.app.batch_playlist_analysis_saved:
            self.playlist_analysis_check.select()
        else:
            self.playlist_analysis_check.deselect()
        if self.app.batch_fast_mode_saved:
            self.fast_mode_check.select()
        else:
            self.fast_mode_check.deselect()
        self._on_playlist_analysis_toggle()
        self.is_initializing = False
    def save_settings(self, event=None):
        """\n        Guarda la configuración con un retraso (Debounce) para evitar\n        congelamientos por escritura excesiva en disco.\n        """
        if hasattr(self, 'app') and self.is_initializing:
            return None
        else:
            if self._save_timer is not None:
                self.after_cancel(self._save_timer)
            self._save_timer = self.after(1000, self._perform_save_settings_real)
    def _perform_save_settings_real(self):
        """Ejecuta la escritura en disco real."""
        self._save_timer = None
        self.app.batch_download_path = self.output_path_entry.get()
        self.app.batch_playlist_analysis_saved = self.playlist_analysis_check.get() == 1
        self.app.batch_fast_mode_saved = self.fast_mode_check.get() == 1
        self.app.save_settings()
    def _on_batch_quick_recode_toggle(self):
        """\n        Habilita o deshabilita los controles de recodificación (Preset, Mantener Original, etc.)\n        según el estado del checkbox principal, sin ocultarlos.\n        """
        is_enabled = self.batch_apply_quick_preset_checkbox.get() == 1
        target_state = 'normal' if is_enabled else 'disabled'
        self.batch_recode_preset_menu.configure(state=target_state)
        self.batch_import_preset_button.configure(state=target_state)
        if is_enabled:
            job = self.queue_manager.get_job_by_id(self.selected_job_id)
            if job and job.job_type == 'LOCAL_RECODE':
                self.batch_keep_original_quick_checkbox.select()
                self.batch_keep_original_quick_checkbox.configure(state='disabled')
            else:
                self.batch_keep_original_quick_checkbox.configure(state='normal')
        else:
            self.batch_keep_original_quick_checkbox.configure(state='disabled')
        if is_enabled:
            self._update_batch_export_button_state()
        else:
            self.batch_export_preset_button.configure(state='disabled')
            self.batch_delete_preset_button.configure(state='disabled')
    def _on_batch_quick_recode_toggle_and_save(self):
        """\n        Llamado solo por el CLIC del usuario.\n        Actualiza la UI Y guarda el estado.\n        """
        self._on_batch_quick_recode_toggle()
        self._on_batch_config_change()
    def _populate_batch_preset_menu(self):
        """\n        Lee los presets disponibles y filtra por el modo.\n        CORREGIDO: Respeta el estado del checkbox al actualizar el menú.\n        """
        current_item_mode = self.mode_selector.get()
        if self.selected_job_id:
            job = self.queue_manager.get_job_by_id(self.selected_job_id)
            if job and job.job_type == 'PLAYLIST':
                    current_item_mode = job.config.get('playlist_mode', 'Video+Audio')
        print(f'DEBUG: Poblando presets para modo: {current_item_mode}')
        compatible_presets = []
        for name, data in self.app.single_tab.built_in_presets.items():
            if data.get('mode_compatibility') == current_item_mode:
                compatible_presets.append(name)
        custom_presets_found = False
        for preset in getattr(self.app.single_tab, 'custom_presets', []):
            if preset.get('data', {}).get('mode_compatibility') == current_item_mode:
                if not custom_presets_found:
                    if compatible_presets:
                        compatible_presets.append('--- Mis Presets ---')
                    custom_presets_found = True
                compatible_presets.append(preset.get('name'))
        if compatible_presets:
            self.batch_recode_preset_menu.configure(values=compatible_presets)
            job = self.queue_manager.get_job_by_id(self.selected_job_id) if self.selected_job_id else None
            preset_to_select = compatible_presets[0]
            if job:
                saved_preset = job.config.get('recode_preset_name')
                if saved_preset and saved_preset in compatible_presets:
                        preset_to_select = saved_preset
            self.batch_recode_preset_menu.set(preset_to_select)
            self._on_batch_quick_recode_toggle()
        else:
            self.batch_recode_preset_menu.configure(values=['- No hay presets para este modo -'], state='disabled')
            self.batch_recode_preset_menu.set('- No hay presets para este modo -')
        self._update_batch_export_button_state()
    def _find_preset_params(self, preset_name):
        """\n        Busca un preset por su nombre (personalizados y luego integrados).\n        Adaptado de single_download_tab.py.\n        """
        for preset in getattr(self.app.single_tab, 'custom_presets', []):
            if preset.get('name') == preset_name:
                return preset.get('data', {})
        if preset_name in self.app.single_tab.built_in_presets:
            return self.app.single_tab.built_in_presets[preset_name]
        else:
            return {}
    def _on_batch_preset_change_and_save(self, selection):
        """Llamado cuando el menú de preset cambia."""
        self._on_batch_config_change()
        self._update_batch_export_button_state()
        self._validate_batch_recode_compatibility()
    def _update_batch_export_button_state(self):
        """\n        Habilita/desahabilita los botones de exportar y eliminar\n        basado en si el preset es personalizado.\n        Copiado de single_download_tab.py\n        """
        selected_preset = self.batch_recode_preset_menu.get()
        is_custom = any((p['name'] == selected_preset for p in self.app.single_tab.custom_presets))
        if is_custom:
            self.batch_export_preset_button.configure(state='normal')
            self.batch_delete_preset_button.configure(state='normal')
        else:
            self.batch_export_preset_button.configure(state='disabled')
            self.batch_delete_preset_button.configure(state='disabled')
    def _validate_batch_recode_compatibility(self):
        """\n        (NUEVA FUNCIÓN)\n        Valida si el preset de recodificación seleccionado es compatible con multipista.\n        Deshabilita la casilla \'Recodificar todas las pistas\' si no lo es.\n        """
        if not hasattr(self, 'batch_use_all_audio_tracks_check'):
            return
        else:
            target_container = None
            selected_preset_name = self.batch_recode_preset_menu.get()
            if selected_preset_name and (not selected_preset_name.startswith('-')):
                    preset_params = self._find_preset_params(selected_preset_name)
                    if preset_params:
                        target_container = preset_params.get('recode_container')
            if self.batch_use_all_audio_tracks_check.winfo_ismapped():
                job = self.queue_manager.get_job_by_id(self.selected_job_id)
                is_multi_track_available = False
                if job and job.job_type == 'LOCAL_RECODE':
                        audio_streams = job.analysis_data.get('local_info', {}).get('audio_streams', [])
                        is_multi_track_available = len(audio_streams) > 1
                if target_container in self.app.SINGLE_STREAM_AUDIO_CONTAINERS:
                    print(f'DEBUG: Preset usa {target_container}, incompatible con multipista. Deshabilitando casilla.')
                    self.batch_use_all_audio_tracks_check.configure(state='disabled')
                    self.batch_use_all_audio_tracks_check.deselect()
                    self.audio_quality_menu.configure(state='normal')
                else:
                    if is_multi_track_available:
                        self.batch_use_all_audio_tracks_check.configure(state='normal')
                    else:
                        self.batch_use_all_audio_tracks_check.configure(state='disabled')
    def _populate_global_preset_menu(self):
        """\n        Puebla el menú de presets GLOBALES, listando TODOS los presets\n        (Video+Audio Y Solo Audio) para que el usuario elija.\n        """
        print('\n--- DEBUG: Ejecutando _populate_global_preset_menu ---')
        all_presets = []
        try:
            built_in_count = len(self.app.single_tab.built_in_presets)
            custom_count = len(getattr(self.app.single_tab, 'custom_presets', []))
            print(f'DEBUG: Fuente de datos: {built_in_count} presets integrados, {custom_count} presets personalizados.')
        except Exception as e:
            print(f'--- ERROR CRÍTICO: No se pudo acceder a los presets de single_tab: {e} ---')
            self.global_recode_preset_menu.configure(values=['- Error de carga -'], state='disabled')
            self.global_recode_preset_menu.set('- Error de carga -')
            return None
        all_presets.append('--- Presets de Video ---')
        for name, data in self.app.single_tab.built_in_presets.items():
            if data.get('mode_compatibility') == 'Video+Audio':
                all_presets.append(name)
        all_presets.append('--- Presets de Audio ---')
        for name, data in self.app.single_tab.built_in_presets.items():
            if data.get('mode_compatibility') == 'Solo Audio':
                all_presets.append(name)
        custom_video_presets = []
        custom_audio_presets = []
        for preset in getattr(self.app.single_tab, 'custom_presets', []):
            if preset.get('data', {}).get('mode_compatibility') == 'Video+Audio':
                custom_video_presets.append(preset.get('name'))
            else:
                custom_audio_presets.append(preset.get('name'))
        if custom_video_presets:
            all_presets.append('--- Mis Presets de Video ---')
            all_presets.extend(custom_video_presets)
        if custom_audio_presets:
            all_presets.append('--- Mis Presets de Audio ---')
            all_presets.extend(custom_audio_presets)
        real_presets_count = sum((1 for p in all_presets if not p.startswith('---')))
        print(f'DEBUG: Total de presets y separadores encontrados: {len(all_presets)}')
        print(f'DEBUG: Total de presets REALES encontrados: {real_presets_count}')
        if all_presets:
            print(f'INFO: Configurando menú global con {real_presets_count} presets.')
            self.global_recode_preset_menu.configure(values=all_presets)
            current_global_mode = self.global_mode_var.get()
            target_preset = None
            for preset_name in all_presets:
                if preset_name.startswith('---'):
                    continue
                else:
                    params = self._find_preset_params(preset_name)
                    if params and params.get('mode_compatibility') == current_global_mode:
                            target_preset = preset_name
                            break
            if not target_preset:
                target_preset = next((p for p in all_presets if not p.startswith('---')), all_presets[0])
            self.global_recode_preset_menu.set(target_preset)
        else:
            print('ADVERTENCIA: No se encontraron presets reales. Configurando menú a \'No hay presets\'.')
            self.global_recode_preset_menu.configure(values=['- No hay presets -'], state='disabled')
            self.global_recode_preset_menu.set('- No hay presets -')
        print('--- DEBUG: Fin de _populate_global_preset_menu ---\n')
    def _on_global_recode_toggle(self):
        """Habilita/deshabilita el menú de preset global y aplica los cambios."""
        if self.global_recode_checkbox.get() == 1:
            self._populate_global_preset_menu()
            self.global_recode_preset_menu.configure(state='normal')
        else:
            self.global_recode_preset_menu.configure(state='disabled')
        self._apply_global_recode_settings()
    def _apply_global_recode_settings(self, event=None):
        """\n        Aplica la configuración de recodificación global a TODOS los jobs\n        en la cola y actualiza la UI del job seleccionado.\n        """
        is_enabled = self.global_recode_checkbox.get() == 1
        selected_preset_name = self.global_recode_preset_menu.get()
        if not selected_preset_name or selected_preset_name.startswith('---'):
            is_enabled = False
        preset_params = self._find_preset_params(selected_preset_name)
        if not preset_params:
            is_enabled = False
        preset_mode = preset_params.get('mode_compatibility', 'Video+Audio')
        preset_keep_original = preset_params.get('keep_original_file', True)
        print('--- APLICANDO CONFIGURACIÓN GLOBAL ---')
        print(f'Activado: {is_enabled}')
        print(f'Preset: {selected_preset_name}')
        print(f'Modo del Preset: {preset_mode}')
        with self.queue_manager.jobs_lock:
            jobs_list = self.queue_manager.jobs
            for job in jobs_list:
                job.config['recode_enabled'] = is_enabled
                job.config['recode_preset_name'] = selected_preset_name
                job.config['recode_keep_original'] = preset_keep_original
                job.config['mode'] = preset_mode
        print(f'Configuración aplicada a {len(jobs_list)} jobs.')
        if self.selected_job_id:
            current_job = self.queue_manager.get_job_by_id(self.selected_job_id)
            if current_job:
                print(f'Refrescando UI para el job seleccionado: {self.selected_job_id[:6]}')
                self._populate_config_panel(current_job)
    def _set_local_batch_mode(self, is_local: bool):
        """Activa o desactiva la UI para el modo de recodificación local por lotes."""
        self.is_local_mode = is_local
        if is_local:
            print('INFO: Entrando en modo de Recodificación Local por Lotes.')
            self.playlist_analysis_check.configure(state='disabled')
            self.auto_download_checkbox.configure(state='disabled')
            self.radio_normal.configure(state='disabled')
            self.radio_with_thumbnail.configure(state='disabled')
            self.radio_only_thumbnail.configure(state='disabled')
            self._populate_global_preset_menu()
            self.global_recode_checkbox.configure(state='normal')
            if self.global_recode_checkbox.get() == 1:
                self.global_recode_preset_menu.configure(state='normal')
            self.start_queue_button.configure(text='Iniciar Proceso', fg_color=self.PROCESS_BTN_COLOR, hover_color=self.PROCESS_BTN_HOVER)
            self.queue_manager.reset_progress()
            self.progress_label.configure(text='Modo Local. Listo para procesar.')
        else:
            print('INFO: Saliendo del modo local. Volviendo a modo Descarga.')
            self.url_entry.configure(state='normal')
            self.playlist_analysis_check.configure(state='normal')
            self.auto_download_checkbox.configure(state='normal')
            self.radio_normal.configure(state='normal')
            self.radio_with_thumbnail.configure(state='normal')
            self.radio_only_thumbnail.configure(state='normal')
            self.start_queue_button.configure(text='Iniciar Cola', fg_color=self.DOWNLOAD_BTN_COLOR, hover_color=self.DOWNLOAD_BTN_HOVER)
            self.progress_label.configure(text='Cola vacía. Analiza una URL para empezar.')
    def _show_import_menu(self):
        """Despliega un menú para elegir entre archivos o carpeta."""
        menu = Menu(self, tearoff=0)
        menu.add_command(label='Seleccionar Archivos...', command=self._on_import_local_files_click)
        menu.add_command(label='Escanear Carpeta Completa...', command=self._import_folder_action)
        try:
            x = self.import_button.winfo_rootx()
            y = self.import_button.winfo_rooty() + self.import_button.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
    def _import_folder_action(self):
        """Pide una carpeta y lanza el escaneo en segundo plano."""
        folder_path = filedialog.askdirectory(title='Seleccionar carpeta para analizar')
        self.app.lift()
        self.app.focus_force()
        if not folder_path:
            return
        else:
            if not self.is_local_mode:
                self._on_clear_list_click()
                self._set_local_batch_mode(True)
            if self.queue_placeholder_label.winfo_ismapped():
                self.queue_placeholder_label.pack_forget()
            print(f'INFO: Escaneando carpeta seleccionada: {folder_path}')
            threading.Thread(target=self._scan_batch_drop_thread, args=([folder_path],), daemon=True).start()
    def _on_import_local_files_click(self):
        """\n        Abre el diálogo para seleccionar múltiples archivos locales\n        y los añade a la cola como trabajos de recodificación.\n        """
        filetypes = [('Archivos de Video', '*.mp4 *.mkv *.mov *.avi *.webm *.mts *.m2ts *.mxf'), ('Archivos de Audio', '*.mp3 *.wav *.m4a *.flac *.opus'), ('Todos los archivos', '*.*')]
        filepaths = filedialog.askopenfilenames(title='Importar archivos locales para Recodificar en Lote', filetypes=filetypes)
        self.app.lift()
        self.app.focus_force()
        if not filepaths:
            print('INFO: Importación local cancelada por el usuario.')
            return
        else:
            if not self.is_local_mode:
                self._on_clear_list_click()
                self._set_local_batch_mode(True)
            if self.queue_placeholder_label.winfo_ismapped():
                self.queue_placeholder_label.pack_forget()
            print(f'INFO: Importando {len(filepaths)} archivos locales...')
            threading.Thread(target=self._run_local_file_analysis, args=(filepaths,), daemon=True).start()
    def _run_local_file_analysis(self, filepaths: tuple[str]):
        """\n        (Hilo de trabajo) Analiza cada archivo local con ffprobe y lo añade a la cola.\n        """
        global_recode_enabled = self.global_recode_checkbox.get() == 1
        global_preset_name = self.global_recode_preset_menu.get()
        global_preset_params = self._find_preset_params(global_preset_name)
        if not global_preset_params or global_preset_name.startswith('---'):
            global_recode_enabled = False
        global_preset_mode = global_preset_params.get('mode_compatibility', 'Video+Audio')
        global_keep_original = global_preset_params.get('keep_original_file', True)
        if global_recode_enabled:
            print(f'DEBUG: [Modo Local] Aplicando config global (Preset: {global_preset_name})')
        first_job_id = None
        for i, filepath in enumerate(filepaths):
            if not os.path.exists(filepath):
                print(f'ADVERTENCIA: El archivo {filepath} no existe. Omitiendo.')
                continue
            else:
                base_name = os.path.basename(filepath)
                temp_config = {'title': f'Analizando: {base_name}', 'local_file_path': filepath}
                temp_job = Job(config=temp_config, job_type='LOCAL_RECODE')
                self.queue_manager.add_job(temp_job)
                self.app.after(0, self.update_job_ui, temp_job.job_id, 'RUNNING', f'Analizando {base_name}...')
                if i == 0:
                    first_job_id = temp_job.job_id
                try:
                    info_dict = self.app.ffmpeg_processor.get_local_media_info(filepath)
                    analysis_data = self._translate_ffprobe_to_analysis_data(info_dict, filepath)
                    temp_job.analysis_data = analysis_data
                    real_title = analysis_data.get('title', base_name)
                    temp_job.config['title'] = real_title
                    self.app.after(0, lambda j=temp_job.job_id, t=real_title: self.job_widgets[j].title_label.configure(text=t) if j in self.job_widgets else None)
                    if global_recode_enabled:
                        temp_job.config['mode'] = global_preset_mode
                        temp_job.config['recode_enabled'] = True
                        temp_job.config['recode_preset_name'] = global_preset_name
                        temp_job.config['recode_keep_original'] = global_keep_original
                    else:
                        temp_job.config['mode'] = 'Video+Audio'
                        temp_job.config['recode_enabled'] = False
                        temp_job.config['recode_preset_name'] = '-'
                        temp_job.config['recode_keep_original'] = True
                    self.app.after(0, self.update_job_ui, temp_job.job_id, 'PENDING', f'Listo para procesar: {base_name}')
                except Exception as e:
                    print(f'ERROR: Falló el análisis local de {base_name}: {e}')
                    self.app.after(0, self.update_job_ui, temp_job.job_id, 'FAILED', f'Error al analizar: {e}')
        if first_job_id:
            self.app.after(100, self._on_job_select, first_job_id)
        if len(self.queue_manager.jobs) > 0:
            def _activate_buttons():
                self.start_queue_button.configure(state='normal', text='Iniciar Proceso', fg_color=self.PROCESS_BTN_COLOR, hover_color=self.PROCESS_BTN_HOVER)
                self.global_recode_checkbox.configure(state='normal')
                if self.global_recode_checkbox.get() == 1:
                    self.global_recode_preset_menu.configure(state='normal')
            self.app.after(0, _activate_buttons)
            if global_recode_enabled:
                self.app.after(0, self.global_recode_preset_menu.configure, {'state': 'normal'})
    def _translate_ffprobe_to_analysis_data(self, ffprobe_info: dict, filepath: str) -> dict:
        """\n        Convierte la salida de ffprobe (get_local_media_info) en un\n        diccionario \'analysis_data\' que imita la estructura de yt-dlp.\n        """
        if not ffprobe_info:
            raise Exception('No se recibió información de ffprobe.')
        else:
            streams = ffprobe_info.get('streams', [])
            format_info = ffprobe_info.get('format', {})
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
            title = os.path.splitext(os.path.basename(filepath))[0]
            duration = float(format_info.get('duration', 0))
            analysis_data = {'title': title, 'duration': duration, 'formats': [], 'local_info': {'video_stream': video_stream, 'audio_streams': audio_streams, 'format': format_info}}
            if video_stream:
                v_codec = video_stream.get('codec_name', 'N/A')
                v_profile = video_stream.get('profile', 'N/A')
                v_width = video_stream.get('width', 0)
                v_height = video_stream.get('height', 0)
                v_fps_str = video_stream.get('r_frame_rate', '0/1')
                try:
                    num, den = map(int, v_fps_str.split('/'))
                    v_fps = float(num / den) if den > 0 else 0.0
                except Exception:
                    v_fps = 0.0
                _, ext_with_dot = os.path.splitext(filepath)
                ext = ext_with_dot.lstrip('.')
                video_format_entry = {'format_id': f"local_video_{video_stream.get('index', 0)}", 'vcodec': v_codec, 'acodec': 'none', 'ext': ext, 'width': v_width, 'height': v_height, 'fps': v_fps, 'is_combined': False, 'stream_index': video_stream.get('index')}
                analysis_data['formats'].append(video_format_entry)
            for audio_stream in audio_streams:
                a_codec = audio_stream.get('codec_name', 'N/A')
                a_bitrate = int(audio_stream.get('bit_rate', 0)) // 1000
                audio_format_entry = {'format_id': f"local_audio_{audio_stream.get('index', 0)}", 'vcodec': 'none', 'acodec': a_codec, 'abr': a_bitrate if a_bitrate > 0 else None, 'tbr': a_bitrate if a_bitrate > 0 else None, 'ext': a_codec, 'language': audio_stream.get('tags', {}).get('language'), 'stream_index': audio_stream.get('index')}
                analysis_data['formats'].append(audio_format_entry)
            return analysis_data
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
    def _on_batch_drop(self, event):
        """Maneja archivos/carpetas soltados en la cola de lotes."""
        try:
            paths = self.tk.splitlist(event.data)
            if not paths:
                return
            print(f'INFO: Drop en Lotes detectado ({len(paths)} elementos). Escaneando...')
            if self.queue_placeholder_label.winfo_ismapped():
                self.queue_placeholder_label.configure(text='Escaneando archivos...')
            threading.Thread(target=self._scan_batch_drop_thread, args=(paths,), daemon=True).start()
        except Exception as e:
            print(f'ERROR en Batch Drag & Drop: {e}')
    def _scan_batch_drop_thread(self, paths):
        """(HILO) Escanea rutas buscando videos/audios válidos."""
        try:
            valid_files = []
            valid_exts = self.app.VIDEO_EXTENSIONS.union(self.app.AUDIO_EXTENSIONS)
            for path in paths:
                path = path.strip('\"')
                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower().lstrip('.')
                    if ext in valid_exts:
                        valid_files.append(path)
                elif os.path.isdir(path):
                    print(f'DEBUG: Escaneando carpeta: {path}')
                    for root, _, filenames in os.walk(path):
                        for f in filenames:
                            ext = os.path.splitext(f)[1].lower().lstrip('.')
                            if ext in valid_exts:
                                full_path = os.path.join(root, f)
                                valid_files.append(full_path)

            if valid_files:
                print(f'INFO: Se encontraron {len(valid_files)} archivos multimedia válidos.')
                self.app.after(0, self._handle_dropped_batch_files, valid_files)
            else:
                print('INFO: No se encontraron archivos multimedia válidos.')
                self.app.after(0, lambda: [
                    Tooltip.hide_all(),
                    messagebox.showinfo('Sin resultados', 'No se encontraron archivos de video/audio compatibles en la selección.')
                ])
                # Si la cola está vacía, mostrar el placeholder
                if not self.job_widgets:
                    self.app.after(0, lambda: self.queue_placeholder_label.pack(expand=True, pady=50, padx=20))
        except Exception as e:
            print(f'ERROR escaneando: {e}')
    def _handle_dropped_batch_files(self, filepaths):
        """\n        (UI PRINCIPAL) Configura el modo local y lanza el análisis.\n        """
        if not self.is_local_mode:
            print('INFO: Drop detectado -> Cambiando a Modo Local automáticamente.')
            self._on_clear_list_click()
            self._set_local_batch_mode(True)
        self.queue_placeholder_label.pack_forget()
        threading.Thread(target=self._run_local_file_analysis, args=(filepaths,), daemon=True).start()
    def _open_playlist_selector(self, job, info_dict):
        """\n        Abre la ventana de selección y configura el Job como contenedor de playlist.\n        """
        try:
            self.app.lift()
            self.app.focus_force()
            self.app.attributes('-topmost', True)
            self.app.update()
            self.app.after(100, lambda: self.app.attributes('-topmost', False))
            cached_thumbs = None
            if job.job_id in self.playlist_cache:
                cached_thumbs = self.playlist_cache[job.job_id].get('thumbnails', {})
                print(f'DEBUG: ✅ Recuperando {len(cached_thumbs)} miniaturas del caché')
            dialog = PlaylistSelectionDialog(self, info_dict, cached_thumbnails=cached_thumbs)
            self.wait_window(dialog)
            result = dialog.result
            if not result:
                self.update_job_ui(job.job_id, 'FAILED', 'Selección cancelada por el usuario.')
                return
            else:
                if job.job_id not in self.playlist_cache:
                    self.playlist_cache[job.job_id] = {'info_dict': info_dict, 'thumbnails': {}}
                self.playlist_cache[job.job_id]['thumbnails'] = dialog.thumbnail_cache
                print(f'DEBUG: 💾 {len(dialog.thumbnail_cache)} miniaturas guardadas en caché para {job.job_id[:6]}')
                job.job_type = 'PLAYLIST'
                job.status = 'PENDING'
                job.config['playlist_mode'] = result['mode']
                job.config['playlist_quality'] = result['quality']
                job.config['selected_indices'] = result['selected_indices']
                job.config['total_videos'] = result['total_videos']
                job.analysis_data = info_dict
                playlist_title = info_dict.get('title', 'Playlist Desconocida')
                job.config['title'] = playlist_title
                count = len(result['selected_indices'])
                self.update_job_ui(job.job_id, 'PENDING', f'Playlist: {count} videos listos')
                if job.job_id in self.job_widgets:
                    self.job_widgets[job.job_id].title_label.configure(text=playlist_title)
                self._on_job_select(job.job_id)
                self.start_queue_button.configure(state='normal')
                self.progress_label.configure(text='Playlist configurada. Presiona Iniciar Cola.')
        except Exception as e:
            print(f'ERROR en selector de playlist: {e}')
            import traceback
            traceback.print_exc()
            self.update_job_ui(job.job_id, 'FAILED', f'Error UI: {e}')
    def _reconfigure_playlist_job(self, job_id):
        """Reabre la ventana de selección para una playlist existente."""
        job = self.queue_manager.get_job_by_id(job_id)
        if not job or job.job_type != 'PLAYLIST':
            return None
        else:
            if job.status == 'RUNNING':
                Tooltip.hide_all()
                messagebox.showwarning('Ocupado', 'Pausa la cola antes de editar.')
                return
            else:
                print(f'INFO: Reconfigurando playlist {job_id[:6]}')
                info_dict = None
                cached_thumbs = None
                if job_id in self.playlist_cache:
                    print(f'DEBUG: ✅ Usando datos cacheados para {job_id[:6]} (carga instantánea)')
                    cache_entry = self.playlist_cache[job_id]
                    info_dict = cache_entry['info_dict']
                    cached_thumbs = cache_entry.get('thumbnails', {})
                    print(f'DEBUG: {len(cached_thumbs)} miniaturas disponibles en caché')
                else:
                    print(f'DEBUG: ⚠️ No hay caché para {job_id[:6]}, usando analysis_data')
                    info_dict = job.analysis_data
                if not info_dict:
                    Tooltip.hide_all()
                    messagebox.showerror('Error', 'No se encontraron datos de la playlist.')
                    return
                else:
                    dialog = PlaylistSelectionDialog(self, info_dict, title='Editar Selección', cached_thumbnails=cached_thumbs)
                    saved_mode = job.config.get('playlist_mode')
                    if saved_mode:
                        dialog.mode_var.set(saved_mode)
                        dialog.mode_menu.set(saved_mode)
                        dialog._update_quality_options(saved_mode)
                    saved_quality = job.config.get('playlist_quality')
                    if saved_quality:
                        dialog.quality_menu.set(saved_quality)
                    saved_indices = job.config.get('selected_indices', [])
                    for i, var in enumerate(dialog.check_vars):
                        var.set(i in saved_indices)
                    self.wait_window(dialog)
                    result = dialog.result
                    if result:
                        if job_id in self.playlist_cache:
                            self.playlist_cache[job_id]['thumbnails'] = dialog.thumbnail_cache
                            print(f'DEBUG: 🔄 Caché de miniaturas actualizado ({len(dialog.thumbnail_cache)} imágenes)')
                        job.config['playlist_mode'] = result['mode']
                        job.config['playlist_quality'] = result['quality']
                        job.config['selected_indices'] = result['selected_indices']
                        job.config['total_videos'] = result['total_videos']
                        count = len(result['selected_indices'])
                        self.update_job_ui(job.job_id, 'PENDING', f'Playlist actualizada: {count} videos')
                        print('INFO: Configuración de playlist actualizada.')
                        if self.selected_job_id == job_id:
                            print(f'DEBUG: Refrescando panel lateral tras reconfigurar {job_id[:6]}')
                            self._populate_config_panel(job)
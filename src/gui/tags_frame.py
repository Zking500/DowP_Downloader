# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\gui\\tags_frame.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import customtkinter as ctk
import os
from tkinter import filedialog, messagebox
from src.core.tags_manager import TagsManager
from src.gui.dialogs import apply_icon
class TagDialog(ctk.CTkToplevel):
    def __init__(self, parent, tags_manager, on_success_callback, edit_name=None, edit_path=None):
        super().__init__(parent)
        self.tags_manager = tags_manager
        self.on_success_callback = on_success_callback
        self.edit_name = edit_name
        self.edit_path = edit_path
        title_text = 'Editar Etiqueta' if edit_name else 'Añadir Nueva Etiqueta'
        self.title(title_text)
        self.geometry('450x220')
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        apply_icon(self)
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = parent.winfo_x() + parent.winfo_width() // 2 - width // 2
        y = parent.winfo_y() + parent.winfo_height() // 2 - height // 2
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.bg_color = parent.cget('fg_color')
        self.configure(fg_color=self.bg_color)
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        ctk.CTkLabel(main_frame, text='Nombre de la Etiqueta:', font=ctk.CTkFont(weight='bold')).pack(anchor='w', pady=(0, 5))
        self.name_entry = ctk.CTkEntry(main_frame, placeholder_text='Ej: SFX, Música, Memes...')
        self.name_entry.pack(fill='x', pady=(0, 15))
        if edit_name:
            self.name_entry.insert(0, edit_name)
        ctk.CTkLabel(main_frame, text='Carpeta de Salida:', font=ctk.CTkFont(weight='bold')).pack(anchor='w', pady=(0, 5))
        path_row = ctk.CTkFrame(main_frame, fg_color='transparent')
        path_row.pack(fill='x', pady=(0, 20))
        self.path_entry = ctk.CTkEntry(path_row, placeholder_text='Selecciona una carpeta de destino...')
        self.path_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        cancel_color = tags_manager.app.get_theme_color('SECONDARY_BTN', ['gray50', 'gray30'])
        cancel_hover = tags_manager.app.get_theme_color('SECONDARY_BTN_HOVER', ['gray60', 'gray40'])
        cancel_text = tags_manager.app.get_theme_color('SECONDARY_BTN_TEXT', ['white', 'white'])
        self.browse_btn = ctk.CTkButton(path_row, text='...', width=40, fg_color=cancel_color, hover_color=cancel_hover, text_color=cancel_text, command=self._browse_folder)
        self.browse_btn.pack(side='right')
        if edit_path:
            self.path_entry.insert(0, edit_path)
        actions_row = ctk.CTkFrame(main_frame, fg_color='transparent')
        actions_row.pack(fill='x')
        self.cancel_btn = ctk.CTkButton(actions_row, text='Cancelar', fg_color=cancel_color, hover_color=cancel_hover, text_color=cancel_text, command=self.destroy)
        self.cancel_btn.pack(side='left', padx=(0, 10), fill='x', expand=True)
        save_color = tags_manager.app.get_theme_color('DOWNLOAD_BTN', ['#3B8ED0', '#1F6AA5'])
        save_hover = tags_manager.app.get_theme_color('DOWNLOAD_BTN_HOVER', ['#367fb8', '#1a5a8a'])
        save_text = tags_manager.app.get_theme_color('DOWNLOAD_BTN_TEXT', ['white', 'white'])
        self.save_btn = ctk.CTkButton(actions_row, text='Guardar', fg_color=save_color, hover_color=save_hover, text_color=save_text, command=self._save_tag)
        self.save_btn.pack(side='right', fill='x', expand=True)
        self.focus_force()
        self.name_entry.focus()
    def _browse_folder(self):
        folder = filedialog.askdirectory(parent=self, title='Seleccionar Carpeta de Destino')
        if folder:
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, os.path.normpath(folder))
    def _save_tag(self):
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()
        try:
            if not name:
                raise ValueError('El nombre de la etiqueta no puede estar vacío.')
            else:
                if not path or not os.path.isdir(path):
                    raise ValueError('La ruta seleccionada no es válida o no existe.')
                else:
                    if self.edit_name:
                        if name != self.edit_name:
                            tags = self.tags_manager.load_tags()
                            if name in tags:
                                raise ValueError(f'Ya existe una etiqueta con el nombre \'{name}\'.')
                            else:
                                if self.edit_name in tags:
                                    del tags[self.edit_name]
                                tags[name] = path
                                self.tags_manager.save_tags(tags)
                                print(f'INFO: Etiqueta \'{self.edit_name}\' renombrada a \'{name}\' y actualizada a la ruta: {path}')
                                if hasattr(self.tags_manager.app, 'batch_tab') and hasattr(self.tags_manager.app.batch_tab, 'queue_manager'):
                                        with self.tags_manager.app.batch_tab.queue_manager.jobs_lock:
                                            for job in self.tags_manager.app.batch_tab.queue_manager.jobs:
                                                if job.config.get('selected_tag') == self.edit_name:
                                                    job.config['selected_tag'] = name
                                                    job.config['custom_output_path'] = path
                                if hasattr(self.tags_manager.app, 'single_tab'):
                                    single_tab = self.tags_manager.app.single_tab
                                    if single_tab.tags_menu.get() == self.edit_name:
                                        single_tab.tags_menu.set(name)
                        else:
                            self.tags_manager.add_tag(name, path)
                            if hasattr(self.tags_manager.app, 'batch_tab') and hasattr(self.tags_manager.app.batch_tab, 'queue_manager'):
                                    with self.tags_manager.app.batch_tab.queue_manager.jobs_lock:
                                        for job in self.tags_manager.app.batch_tab.queue_manager.jobs:
                                            if job.config.get('selected_tag') == name:
                                                job.config['custom_output_path'] = path
                    else:
                        self.tags_manager.add_tag(name, path)
                    self.on_success_callback()
                    self.destroy()
        except ValueError as e:
            messagebox.showerror('Error', str(e), parent=self)
class TagsSection(ctk.CTkScrollableFrame):
    def __init__(self, master, app, config_tab=None, *args, **kwargs):
        super().__init__(master, *args, fg_color='transparent', **kwargs)
        self.app = app
        self.config_tab = config_tab
        self.tags_manager = TagsManager(app)
        c_tab = config_tab or getattr(app, 'config_tab', None)
        self.card_bg = getattr(c_tab, 'CONFIG_CARD_BG', app.get_theme_color('CONFIG_CARD_BG', ['gray85', 'gray20']))
        self.card_border = getattr(c_tab, 'CONFIG_CARD_BORDER', app.get_theme_color('CONFIG_CARD_BORDER', ['gray75', 'gray30']))
        self.cancel_btn = getattr(c_tab, 'CANCEL_BTN', app.get_theme_color('CANCEL_BTN', ['#dc3545', '#c82333']))
        self.cancel_hover = getattr(c_tab, 'CANCEL_HOVER', app.get_theme_color('CANCEL_BTN_HOVER', ['#c82333', '#bd2130']))
        self.cancel_text = getattr(c_tab, 'CANCEL_TEXT', app.get_theme_color('CANCEL_BTN_TEXT', ['white', 'white']))
        self.edit_btn = getattr(c_tab, 'SECONDARY_BTN', app.get_theme_color('SECONDARY_BTN', ['gray50', 'gray30']))
        self.edit_hover = getattr(c_tab, 'SECONDARY_HOVER', app.get_theme_color('SECONDARY_BTN_HOVER', ['gray60', 'gray40']))
        self.edit_text = getattr(c_tab, 'SECONDARY_TEXT', app.get_theme_color('SECONDARY_BTN_TEXT', ['white', 'white']))
        self.add_btn_color = getattr(c_tab, 'DOWNLOAD_BTN', app.get_theme_color('DOWNLOAD_BTN', ['#3B8ED0', '#1F6AA5']))
        self.add_btn_hover = getattr(c_tab, 'DOWNLOAD_HOVER', app.get_theme_color('DOWNLOAD_BTN_HOVER', ['#367fb8', '#1a5a8a']))
        self.add_btn_text = getattr(c_tab, 'DOWNLOAD_TEXT', app.get_theme_color('DOWNLOAD_BTN_TEXT', ['white', 'white']))
        ctk.CTkLabel(self, text='Gestión de Etiquetas', font=ctk.CTkFont(size=20, weight='bold')).pack(anchor='w', pady=(10, 5), padx=10)
        ctk.CTkLabel(self, text='Configura atajos rápidos para tus carpetas de descarga favoritas. Ideal para organizar SFX, música, b-roll o renders al instante.', text_color='gray60', justify='left', wraplength=600).pack(anchor='w', pady=(0, 15), padx=10)
        actions_bar = ctk.CTkFrame(self, fg_color='transparent')
        actions_bar.pack(fill='x', padx=10, pady=(0, 15))
        self.btn_add = ctk.CTkButton(actions_bar, text='Nueva Etiqueta', fg_color=self.add_btn_color, hover_color=self.add_btn_hover, text_color=self.add_btn_text, font=ctk.CTkFont(weight='bold'), command=self._open_add_dialog)
        self.btn_add.pack(side='left')
        self.list_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.list_frame.pack(fill='both', expand=True, padx=5)
        self.refresh_tags_list()
    def _open_add_dialog(self):
        def on_success():
            self.refresh_tags_list()
            self.notify_tabs_update()
        dialog = TagDialog(self.winfo_toplevel(), self.tags_manager, on_success)
        self.app.wait_window(dialog)
    def _open_edit_dialog(self, name, path):
        def on_success():
            self.refresh_tags_list()
            self.notify_tabs_update()
        dialog = TagDialog(self.winfo_toplevel(), self.tags_manager, on_success, edit_name=name, edit_path=path)
        self.app.wait_window(dialog)
    def refresh_tags_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        tags = self.tags_manager.load_tags()
        if not tags:
            empty_frame = ctk.CTkFrame(self.list_frame, fg_color=self.card_bg, corner_radius=8, border_width=1, border_color=self.card_border)
            empty_frame.pack(fill='x', pady=10)
            ctk.CTkLabel(empty_frame, text='No hay etiquetas creadas todavía. Pulsa \'Nueva Etiqueta\' para empezar.', text_color='gray50', font=ctk.CTkFont(size=12, slant='italic')).pack(pady=20)
        else:
            for name, path in tags.items():
                card = ctk.CTkFrame(self.list_frame, fg_color=self.card_bg, corner_radius=8, border_width=1, border_color=self.card_border)
                card.pack(fill='x', pady=4)
                text_container = ctk.CTkFrame(card, fg_color='transparent')
                text_container.pack(side='left', fill='both', expand=True, padx=15, pady=10)
                name_lbl = ctk.CTkLabel(text_container, text=name, font=ctk.CTkFont(size=14, weight='bold'), anchor='w')
                name_lbl.pack(fill='x')
                path_lbl = ctk.CTkLabel(text_container, text=path, font=ctk.CTkFont(size=11), text_color='gray60', anchor='w')
                path_lbl.pack(fill='x')
                btn_container = ctk.CTkFrame(card, fg_color='transparent')
                btn_container.pack(side='right', padx=15, pady=10)
                edit_btn = ctk.CTkButton(btn_container, text='Editar', width=80, fg_color=self.edit_btn, hover_color=self.edit_hover, text_color=self.edit_text, font=ctk.CTkFont(size=12, weight='bold'), command=lambda n=name, p=path: self._open_edit_dialog(n, p))
                edit_btn.pack(side='left', padx=(0, 5))
                del_btn = ctk.CTkButton(btn_container, text='Eliminar', width=80, fg_color=self.cancel_btn, hover_color=self.cancel_hover, text_color=self.cancel_text, font=ctk.CTkFont(size=12, weight='bold'), command=lambda n=name: self._delete_tag(n))
                del_btn.pack(side='left')
    def notify_tabs_update(self):
        """Avisa a las pestañas de descargas que actualicen sus listas."""
        if hasattr(self.app, 'single_tab') and hasattr(self.app.single_tab, 'update_tags_combobox'):
                self.app.single_tab.update_tags_combobox()
        if hasattr(self.app, 'batch_tab') and hasattr(self.app.batch_tab, 'update_tags_combobox'):
                self.app.batch_tab.update_tags_combobox()
    def _delete_tag(self, name):
        if messagebox.askyesno('Confirmar eliminación', f'¿Estás seguro de que quieres eliminar la etiqueta \'{name}\'?', parent=self.winfo_toplevel()):
            self.tags_manager.delete_tag(name)
            if hasattr(self.app, 'batch_tab') and hasattr(self.app.batch_tab, 'queue_manager'):
                    with self.app.batch_tab.queue_manager.jobs_lock:
                        for job in self.app.batch_tab.queue_manager.jobs:
                            if job.config.get('selected_tag') == name:
                                job.config['selected_tag'] = '- Etiqueta -'
                                job.config['custom_output_path'] = None
            self.refresh_tags_list()
            self.notify_tabs_update()
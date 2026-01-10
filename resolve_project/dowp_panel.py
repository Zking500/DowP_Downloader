# dowp_panel.py
# DowP Connector for DaVinci Resolve
# Requiere: python-socketio, PySide6

import sys, os, json, platform, traceback
import socketio
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QCheckBox
from PySide6.QtGui import QColor, QPalette

# ------------------- CONFIGURACIÓN DE RESOLVE -------------------
RESOLVE_INSTALL_PATH = "C:/Program Files/Blackmagic Design/DaVinci Resolve"
# ----------------------------------------------------------------

def setup_resolve_environment(install_path):
    """Prepara el entorno para la API de scripting de DaVinci Resolve."""
    if platform.architecture()[0] != "64bit":
        print("❌ ERROR: Se requiere una instalación de Python de 64 bits.")
        return False
    
    try:
        os.add_dll_directory(install_path)
    except AttributeError:
        os.environ["PATH"] = install_path + os.pathsep + os.environ["PATH"]

    script_module_path = os.path.join(os.getenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting", "Modules")
    if not os.path.isdir(script_module_path):
        print(f"❌ ERROR: No se encuentra el directorio de módulos de scripting en: {script_module_path}")
        return False
    sys.path.append(script_module_path)

    os.environ["RESOLVE_SCRIPT_API"] = os.path.join(os.getenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting")
    os.environ["RESOLVE_SCRIPT_LIB"] = os.path.join(install_path, "fusionscript.dll")
    
    if not os.path.exists(os.environ["RESOLVE_SCRIPT_LIB"]):
         print(f"❌ ERROR: No se encuentra fusionscript.dll en: {os.environ['RESOLVE_SCRIPT_LIB']}")
         return False
    return True

def import_resolve_api():
    """Importa la librería DaVinciResolveScript de forma robusta."""
    try:
        import DaVinciResolveScript as bmd
        return bmd
    except ImportError:
        print("\n❌ ERROR CRÍTICO: No se pudo importar 'DaVinciResolveScript'.")
        print("   Causas: Python 3.10 (64-bit) no usado, falta C++ Redistributable, o ruta de Resolve incorrecta.")
        return None
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO al importar: {e}")
        traceback.print_exc()
        return None

# --- Inicialización del Entorno y API de Resolve ---
if not setup_resolve_environment(RESOLVE_INSTALL_PATH):
    sys.exit(1)

bmd = import_resolve_api()
if not bmd:
    # Si no se puede importar, mostramos un panel de error simple en lugar de la UI completa.
    app = QApplication(sys.argv)
    error_widget = QWidget()
    error_widget.setWindowTitle("Error Crítico")
    layout = QVBoxLayout()
    label = QLabel("No se pudo conectar con DaVinci Resolve.\n\n"
                   "Verifica que:\n"
                   "- Usas Python 3.10 (64-bit).\n"
                   "- Tienes 'Microsoft Visual C++ Redistributable (x64)' instalado.\n"
                   "- La ruta a DaVinci Resolve es correcta en el script.\n"
                   "- El scripting externo está habilitado en las preferencias de Resolve.")
    layout.addWidget(label)
    error_widget.setLayout(layout)
    error_widget.show()
    sys.exit(app.exec())
# ----------------------------------------------------

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".dowp_config.json")


class DowPPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DowP Connector for Resolve")
        self.resize(350, 220)

        # API Resolve
        self.resolve = bmd.scriptapp("Resolve")
        self.project = self.resolve.GetProjectManager().GetCurrentProject()
        self.media_pool = self.project.GetMediaPool() if self.project else None

        # Estado
        self.dowp_path = None
        self.import_to_timeline = False
        self.load_config()

        # UI
        layout = QVBoxLayout()
        self.status = QLabel("Estado: Desconectado")
        self.set_status("Desconectado", "red")
        layout.addWidget(self.status)

        self.btn_launch = QPushButton("🚀 Iniciar DowP")
        self.btn_launch.clicked.connect(self.launch_dowp)
        layout.addWidget(self.btn_launch)

        self.btn_link = QPushButton("🔗 Enlazar DowP")
        self.btn_link.clicked.connect(self.link_dowp)
        layout.addWidget(self.btn_link)

        self.timeline_toggle = QCheckBox("🎬 Importar a timeline")
        self.timeline_toggle.stateChanged.connect(self.toggle_timeline)
        layout.addWidget(self.timeline_toggle)

        self.btn_import_video = QPushButton("📁 Importar Video Manualmente")
        self.btn_import_video.clicked.connect(self.import_video_manually)
        layout.addWidget(self.btn_import_video)

        self.btn_settings = QPushButton("⚙️ Configurar ruta DowP")
        self.btn_settings.clicked.connect(self.set_dowp_path)
        layout.addWidget(self.btn_settings)

        self.setLayout(layout)

        # SocketIO
        self.sio = socketio.Client()

        @self.sio.on("connect")
        def on_connect():
            self.set_status("Conectado", "green")
            self.sio.emit("register", {"appIdentifier": "resolve"})
            print("✅ Conectado a DowP")

        @self.sio.on("disconnect")
        def on_disconnect():
            self.set_status("Desconectado", "red")
            print("⚠️ Desconectado de DowP")

        @self.sio.on("new_file")
        def on_new_file(data):
            print(f"📦 Evento new_file recibido: {data}")
            self.import_file(data.get("filePackage", {}))

    # -------------------------------
    # Config persistente
    # -------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.dowp_path = cfg.get("dowp_path")
                    print(f"⚙️ Config cargada: {self.dowp_path}")
            except Exception as e:
                print(f"❌ Error al cargar config: {e}")

    def save_config(self):
        try:
            cfg = {"dowp_path": self.dowp_path}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"💾 Config guardada en {CONFIG_PATH}")
        except Exception as e:
            print(f"❌ Error al guardar config: {e}")

    # -------------------------------
    # UI helpers
    # -------------------------------
    def set_status(self, text, color):
        self.status.setText(f"Estado: {text}")
        palette = self.status.palette()
        palette.setColor(QPalette.WindowText, QColor(color))
        self.status.setPalette(palette)

    # -------------------------------
    # Botones
    # -------------------------------
    def launch_dowp(self):
        if not self.dowp_path:
            self.set_status("Configura DowP primero", "orange")
            return
        # Lanzar DowP
        if sys.platform.startswith("win"):
            os.startfile(self.dowp_path)
        elif sys.platform == "darwin":
            os.system(f'open "{self.dowp_path}"')
        else:
            os.system(f'sh "{self.dowp_path}" &')
        print(f"🚀 Lanzando DowP desde: {self.dowp_path}")
        self.connect_socket()

    def link_dowp(self):
        self.connect_socket()
        if self.sio.connected:
            self.sio.emit("set_active_target", {"targetApp": "resolve"})
            print("🔗 Solicitado enlace con DowP")

    def set_dowp_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona run_dowp.bat o main.py")
        if path:
            self.dowp_path = path
            self.save_config()
            self.set_status("Ruta guardada", "blue")
            print(f"⚙️ Ruta configurada: {self.dowp_path}")

    def toggle_timeline(self, state):
        self.import_to_timeline = (state == 2)
        print(f"🎬 Importar a timeline: {self.import_to_timeline}")

    def import_video_manually(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de video", "", "Video Files (*.mp4 *.mov *.mkv)")
        if file_path:
            print(f"📁 Video seleccionado manualmente: {file_path}")
            # Usamos la misma lógica de importación, empaquetando la ruta en el formato esperado
            file_pkg = {"video": file_path}
            self.import_file(file_pkg)

    # -------------------------------
    # Socket
    # -------------------------------
    def connect_socket(self):
        if not self.sio.connected:
            try:
                self.sio.connect("http://127.0.0.1:7788")
            except Exception as e:
                self.set_status("DowP no abierto", "red")
                print(f"❌ Error al conectar con DowP: {e}")

    # -------------------------------
    # Importar archivos
    # -------------------------------
    def import_file(self, file_pkg):
        if not self.project or not self.media_pool:
            self.set_status("No hay proyecto abierto", "red")
            return

        files = []
        if file_pkg.get("video"): files.append(file_pkg["video"])
        if file_pkg.get("thumbnail"): files.append(file_pkg["thumbnail"])
        if file_pkg.get("subtitle"): files.append(file_pkg["subtitle"])

        if not files: 
            self.set_status("Sin archivos para importar", "red")
            print("⚠️ new_file recibido pero sin archivos válidos")
            return

        print(f"📂 Importando archivos: {files}")

        # Crear carpeta DowP Imports
        root = self.media_pool.GetRootFolder()
        target = None
        for f in root.GetSubFolders().values():
            if f.GetName() == "DowP Imports":
                target = f
                break
        if not target:
            target = self.media_pool.AddSubFolder(root, "DowP Imports")
            print("📁 Carpeta 'DowP Imports' creada")

        self.media_pool.SetCurrentFolder(target)
        clips = self.media_pool.ImportMedia(files)
        if not clips:
            self.set_status("Error al importar archivos", "red")
            return

        if self.import_to_timeline:
            # Simplificamos la lógica para usar AppendToTimeline, que es más robusto.
            if not self.media_pool.AppendToTimeline(clips):
                self.set_status("Error al añadir a timeline", "red")
                print("❌ Error al usar AppendToTimeline.")
            else:
                print("✅ Clips añadidos a la timeline.")

        self.set_status("¡Importado con éxito!", "green")

    def find_free_track(self, timeline, track_type, tc, clip, fps):
        num_tracks = timeline.GetTrackCount(track_type)
        clip_len = clip.GetClipProperty().get("Duration", "1.0")  # en segundos
        start_frame = self.timecode_to_frames(tc, fps)
        end_frame = start_frame + int(float(clip_len) * fps)

        print(f"🔎 Buscando pista libre ({track_type}) para rango {start_frame}-{end_frame}")

        for i in range(1, num_tracks + 1):
            items = timeline.GetItemsInTrack(track_type, i)
            overlap = False
            for _, item in items.items():
                istart = self.timecode_to_frames(item.GetStart(), fps)
                iend = self.timecode_to_frames(item.GetEnd(), fps)
                if not (end_frame <= istart or start_frame >= iend):
                    overlap = True
                    break
            if not overlap:
                print(f"🟢 Encontrada pista libre {track_type.upper()}{i}")
                return i

        new_index = num_tracks + 1
        timeline.InsertTrack(track_type, new_index)
        print(f"➕ Nueva pista {track_type.upper()}{new_index} creada")
        return new_index

    def timecode_to_frames(self, tc_str, fps):
        try:
            if ":" in tc_str:
                h, m, s, f = [int(x) for x in tc_str.split(":")]
                return int(((h * 3600 + m * 60 + s) * fps) + f)
            else:
                return int(float(tc_str) * fps)
        except Exception:
            return 0


def main():
    app = QApplication(sys.argv)
    panel = DowPPanel()
    panel.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
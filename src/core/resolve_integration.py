import os
import sys
import platform
import traceback

# ------------------- CONFIGURACIÓN DE RESOLVE -------------------
RESOLVE_INSTALL_PATH = "C:/Program Files/Blackmagic Design/DaVinci Resolve"
# ----------------------------------------------------------------

class ResolveIntegration:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResolveIntegration, cls).__new__(cls)
            cls._instance.initialized = False
            cls._instance.resolve = None
            cls._instance.project = None
            cls._instance.media_pool = None
            cls._instance.setup_done = False
        return cls._instance

    def _setup_environment(self):
        """Prepara el entorno para la API de scripting de DaVinci Resolve."""
        if self.setup_done:
            return True

        if platform.architecture()[0] != "64bit":
            print("❌ [ResolveIntegration] ERROR: Se requiere una instalación de Python de 64 bits.")
            return False
        
        try:
            # Intentar añadir la DLL directory si estamos en una versión reciente de Python en Windows
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(RESOLVE_INSTALL_PATH)
        except AttributeError:
            pass
            
        # Asegurar que la ruta está en el PATH
        if RESOLVE_INSTALL_PATH not in os.environ["PATH"]:
             os.environ["PATH"] = RESOLVE_INSTALL_PATH + os.pathsep + os.environ["PATH"]

        # Rutas de los módulos de scripting
        script_module_path = os.path.join(os.getenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting", "Modules")
        if not os.path.isdir(script_module_path):
            print(f"❌ [ResolveIntegration] ERROR: No se encuentra el directorio de módulos de scripting en: {script_module_path}")
            return False
        
        if script_module_path not in sys.path:
            sys.path.append(script_module_path)

        os.environ["RESOLVE_SCRIPT_API"] = os.path.join(os.getenv("PROGRAMDATA"), "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting")
        os.environ["RESOLVE_SCRIPT_LIB"] = os.path.join(RESOLVE_INSTALL_PATH, "fusionscript.dll")
        
        if not os.path.exists(os.environ["RESOLVE_SCRIPT_LIB"]):
             print(f"❌ [ResolveIntegration] ERROR: No se encuentra fusionscript.dll en: {os.environ['RESOLVE_SCRIPT_LIB']}")
             return False
        
        self.setup_done = True
        return True

    def _is_resolve_running(self):
        """Verifica si el proceso de DaVinci Resolve está en ejecución."""
        try:
            # Usar tasklist para verificar si Resolve.exe está corriendo
            import subprocess
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq Resolve.exe"', shell=True).decode()
            if "Resolve.exe" in output:
                return True
            return False
        except Exception:
            # Si falla el chequeo, asumimos que podría estar corriendo y dejamos que connect() lo intente
            return True

    def connect(self):
        """Intenta conectar con la instancia de DaVinci Resolve."""
        if not self._is_resolve_running():
             print("⚠️ [ResolveIntegration] Proceso 'Resolve.exe' no detectado en el sistema.")
             return False

        if not self._setup_environment():
            return False

        try:
            print("INFO: [ResolveIntegration] Importando módulo DaVinciResolveScript...")
            import DaVinciResolveScript as bmd
            print("INFO: [ResolveIntegration] Buscando instancia de Resolve...")
            self.resolve = bmd.scriptapp("Resolve")
            
            if self.resolve:
                print("✅ [ResolveIntegration] Conectado a DaVinci Resolve.")
                return True
            else:
                print("⚠️ [ResolveIntegration] No se pudo conectar a DaVinci Resolve.")
                print("   -> Posibles causas: Versión Free (limitada), Resolve no iniciado, o API deshabilitada.")
                return False
        except ImportError:
            print("❌ [ResolveIntegration] No se pudo importar 'DaVinciResolveScript'.")
            return False
        except Exception as e:
            print(f"❌ [ResolveIntegration] Error inesperado al conectar: {e}")
            return False

    def _refresh_context(self):
        """Actualiza las referencias al proyecto y media pool."""
        if not self.resolve:
            if not self.connect():
                return False
        
        self.project = self.resolve.GetProjectManager().GetCurrentProject()
        self.media_pool = self.project.GetMediaPool() if self.project else None
        
        if not self.project:
             print("⚠️ [ResolveIntegration] No hay proyecto abierto en Resolve.")
             return False
        return True

    def import_files(self, file_paths, target_bin_name="DowP Imports", import_to_timeline=False):
        """
        Importa una lista de archivos a DaVinci Resolve.
        
        :param file_paths: Lista de rutas de archivos a importar.
        :param target_bin_name: Nombre de la carpeta (Bin) donde importar.
        :param import_to_timeline: Si es True, intenta añadir los clips a la timeline actual.
        :return: True si se importó con éxito, False en caso contrario.
        """
        if not file_paths:
            return False

        if not self._refresh_context():
            return False

        print(f"📂 [ResolveIntegration] Importando archivos: {file_paths}")

        # 1. Buscar o Crear carpeta destino (Bin)
        root = self.media_pool.GetRootFolder()
        target_folder = None
        
        # Buscar si ya existe
        for f in root.GetSubFolders().values():
            if f.GetName() == target_bin_name:
                target_folder = f
                break
        
        # Si no existe, crearla
        if not target_folder:
            try:
                target_folder = self.media_pool.AddSubFolder(root, target_bin_name)
                print(f"📁 [ResolveIntegration] Carpeta '{target_bin_name}' creada.")
            except Exception as e:
                print(f"⚠️ [ResolveIntegration] No se pudo crear la carpeta, usando raíz. Error: {e}")
                target_folder = root

        # 2. Importar Medios
        self.media_pool.SetCurrentFolder(target_folder)
        try:
            clips = self.media_pool.ImportMedia(file_paths)
        except Exception as e:
             print(f"❌ [ResolveIntegration] Excepción al importar media: {e}")
             return False

        if not clips:
            print("❌ [ResolveIntegration] Falló la importación (ImportMedia devolvió vacío).")
            return False

        # 3. Importar a Timeline (Opcional)
        if import_to_timeline:
            try:
                # AppendToTimeline añade al final de la timeline activa
                if not self.media_pool.AppendToTimeline(clips):
                    print("⚠️ [ResolveIntegration] Error al añadir a timeline (AppendToTimeline falló).")
                else:
                    print("✅ [ResolveIntegration] Clips añadidos a la timeline.")
            except Exception as e:
                print(f"❌ [ResolveIntegration] Error al intentar añadir a timeline: {e}")

        print("✅ [ResolveIntegration] Importación finalizada con éxito.")
        return True

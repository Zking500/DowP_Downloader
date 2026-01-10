# -*- coding: utf-8 -*-
import os
import sys
import platform
import traceback

# ------------------- CONFIGURACIÓN -------------------
# ¡¡¡ATENCIÓN!!!
# Asegúrate de que esta ruta apunte a tu instalación de DaVinci Resolve.
RESOLVE_INSTALL_PATH = "C:/Program Files/Blackmagic Design/DaVinci Resolve"
VIDEO_FILE_PATH = "Y:/videos/Grabaciones de pantalla/Grabación de pantalla 2025-03-03 210917.mp4"
TIMELINE_NAME = "MiTimeline"
# -----------------------------------------------------


def setup_environment(install_path):
    """
    Prepara el entorno para la API de scripting de DaVinci Resolve.
    """
    print("--- INICIO DE VERIFICACIÓN DE RUTAS Y ENTORNO ---")

    # 1. Verificar arquitectura de Python
    if platform.architecture()[0] != "64bit":
        print("❌ ERROR: Se requiere una instalación de Python de 64 bits.")
        sys.exit(1)
    print("✅ Verificación de arquitectura: Python es 64bit.")

    # 2. Añadir la ruta de las DLLs de Resolve
    try:
        # Para Python 3.8+
        os.add_dll_directory(install_path)
        print(f"ℹ️ Ruta de DLLs añadida (usando add_dll_directory): {install_path}")
    except AttributeError:
        # Para versiones anteriores de Python
        os.environ["PATH"] = install_path + os.pathsep + os.environ["PATH"]
        print(f"ℹ️ Ruta de DLLs añadida (modificando PATH): {install_path}")
    except Exception as e:
        print(f"⚠️ Advertencia al añadir la ruta de DLLs: {e}")

    # 3. Añadir la ruta de los módulos de scripting
    script_module_path = os.path.join(
        os.getenv("PROGRAMDATA"),
        "Blackmagic Design",
        "DaVinci Resolve",
        "Support",
        "Developer",
        "Scripting",
        "Modules",
    )
    if not os.path.isdir(script_module_path):
        print(f"❌ ERROR: No se encuentra el directorio de módulos de scripting en: {script_module_path}")
        sys.exit(1)
    sys.path.append(script_module_path)
    print(f"ℹ️ Ruta de módulos de Scripting añadida: {script_module_path}")

    # 4. Establecer variables de entorno cruciales
    script_api_path = os.path.join(
        os.getenv("PROGRAMDATA"),
        "Blackmagic Design",
        "DaVinci Resolve",
        "Support",
        "Developer",
        "Scripting",
    )
    os.environ["RESOLVE_SCRIPT_API"] = script_api_path
    print(f"ℹ️ Variable de entorno 'RESOLVE_SCRIPT_API' establecida: {script_api_path}")

    script_lib_path = os.path.join(install_path, "fusionscript.dll")
    if not os.path.exists(script_lib_path):
         print(f"❌ ERROR: No se encuentra fusionscript.dll en: {script_lib_path}")
         sys.exit(1)
    os.environ["RESOLVE_SCRIPT_LIB"] = script_lib_path
    print(f"ℹ️ Variable de entorno 'RESOLVE_SCRIPT_LIB' establecida: {script_lib_path}")

    print("--- FIN DE VERIFICACIÓN DE RUTAS Y ENTORNO ---\n")
    return True

def import_resolve_script_api():
    """
    Importa la librería DaVinciResolveScript y maneja errores de forma robusta.
    """
    try:
        print("ℹ️ Intentando importar 'DaVinciResolveScript'...")
        import DaVinciResolveScript as bmd
        print("✅ ¡'DaVinciResolveScript' importado exitosamente!")
        return bmd
    except ImportError:
        print("\n❌ ERROR CRÍTICO: No se pudo importar 'DaVinciResolveScript'.")
        print("   Causas posibles:")
        print("   1. DaVinci Resolve no está instalado o la ruta es incorrecta.")
        print("   2. La versión de Python no es 3.10 (64-bit).")
        print("   3. Falta o está corrupto el 'Microsoft Visual C++ Redistributable (x64)'.")
        print("   4. Las variables de entorno no se configuraron correctamente.")
        return None
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO al importar 'DaVinciResolveScript': {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        print("   Este es un error grave a bajo nivel (crash), usualmente causado por:")
        print("   - Incompatibilidad de Python (debe ser 3.10 64-bit).")
        print("   - Una instalación corrupta de 'Microsoft Visual C++ Redistributable (x64)'.")
        print("   - Un problema con la instalación de DaVinci Resolve.")
        traceback.print_exc()
        return None

def main():
    """
    Función principal del script.
    """
    if not setup_environment(RESOLVE_INSTALL_PATH):
        sys.exit(1)

    bmd = import_resolve_script_api()
    if not bmd:
        sys.exit(1)

    # El resto del código se ejecuta solo si la importación fue exitosa
    print("\n--- INICIO DE OPERACIONES EN DAVINCI RESOLVE ---")
    
    try:
        resolve = bmd.scriptapp("Resolve")
        if not resolve:
            print("❌ ERROR: No se pudo obtener el objeto 'Resolve'. Asegúrate de que DaVinci Resolve está en ejecución.")
            sys.exit(1)
        
        print("✅ Conectado a DaVinci Resolve.")

        project_manager = resolve.GetProjectManager()
        project = project_manager.GetCurrentProject()
        
        if not project:
            print("❌ ERROR: No hay un proyecto abierto en DaVinci Resolve.")
            sys.exit(1)
        
        print(f"✅ Proyecto actual: '{project.GetName()}'")

        media_pool = project.GetMediaPool()
        
        # Asegurar que la timeline exista
        timeline = project.GetCurrentTimeline()
        if not timeline or timeline.GetName() != TIMELINE_NAME:
            print(f"ℹ️ Timeline '{TIMELINE_NAME}' no es la activa. Buscando o creando...")
            timeline = None
            for i in range(1, project.GetTimelineCount() + 1):
                current_timeline = project.GetTimelineByIndex(i)
                if current_timeline.GetName() == TIMELINE_NAME:
                    timeline = current_timeline
                    project.SetCurrentTimeline(timeline)
                    break
            
            if not timeline:
                print(f"ℹ️ Timeline '{TIMELINE_NAME}' no encontrada. Creando una nueva...")
                timeline = media_pool.CreateEmptyTimeline(TIMELINE_NAME)
                if not timeline:
                    print(f"❌ ERROR: No se pudo crear la timeline '{TIMELINE_NAME}'.")
                    sys.exit(1)
                project.SetCurrentTimeline(timeline)

        print(f"✅ Usando la línea de tiempo: '{timeline.GetName()}'")

        # Verificar que haya al menos una pista de video
        if timeline.GetTrackCount("video") < 1:
            print("ℹ️ La timeline no tiene pistas de video. Creando una...")
            if not timeline.AddTrack("video"):
                 print("❌ ERROR: No se pudo añadir una pista de video a la timeline.")
                 sys.exit(1)
            print("✅ Pista de video creada.")

        # Importar el clip al Media Pool
        print(f"ℹ️ Importando clip: '{VIDEO_FILE_PATH}'...")
        
        # Comprobar si el clip ya existe para no re-importarlo
        clip_to_add = None
        # La API no provee una forma directa de buscar por ruta, así que iteramos
        existing_clips = media_pool.GetRootFolder().GetClipList()
        for clip in existing_clips:
            # GetClipProperty("File Path") puede ser inconsistente, comparamos el nombre
            if clip.GetName() == os.path.basename(VIDEO_FILE_PATH):
                print("ℹ️ El clip ya existe en el Media Pool (basado en el nombre).")
                clip_to_add = clip
                break

        if not clip_to_add:
            clips_imported = media_pool.ImportMedia([VIDEO_FILE_PATH])
            if not clips_imported:
                print("❌ ERROR: No se pudo importar el clip al Media Pool.")
                print("   Verifica que la ruta del archivo es correcta y accesible.")
                sys.exit(1)
            clip_to_add = clips_imported[0]
        
        print(f"✅ Clip listo para usar: {clip_to_add.GetName()}")

        # Añadir el clip a la timeline
        print(f"ℹ️ Añadiendo clip a la timeline...")
        if not media_pool.AppendToTimeline([clip_to_add]):
            print("❌ ERROR: No se pudo añadir el clip a la timeline.")
            sys.exit(1)
            
        print("✅ ¡ÉXITO! Clip añadido a la timeline.")

    except Exception as e:
        print(f"\n❌ ERROR durante la ejecución de las operaciones en Resolve: {e}")
        traceback.print_exc()

    print("\n--- FIN DE OPERACIONES ---")


if __name__ == "__main__":
    main()
    print("El proyecto está finalizado. ¡Buen trabajo! 😎")
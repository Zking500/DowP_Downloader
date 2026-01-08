# Este script se ejecuta desde un terminal EXTERNO a DaVinci Resolve.
# Su propósito es conectarse a Resolve y ordenarle que ejecute un script Lua.

import sys
import os
import platform

# --- VERIFICACIÓN DE ENTORNO (¡MUY IMPORTANTE!) ---

# 1. Verificar si Python es de 64-bit. DaVinci Resolve es 64-bit y requiere un intérprete de Python de 64-bit.
if not platform.architecture()[0] == "64bit":
    print("="*60)
    print("❌ ERROR FATAL: Estás usando una versión de Python de 32-bit.")
    print("   DaVinci Resolve requiere una versión de Python de 64-bit para el scripting externo.")
    print(f"   Tu versión: {platform.architecture()[0]}")
    print("   Por favor, instala y ejecuta este script con una versión de Python de 64-bit.")
    print("="*60)
    sys.exit(1)
else:
    print(f"✅ Verificación de arquitectura: Python es {platform.architecture()[0]}.")

# --- CONFIGURACIÓN DE RUTAS Y VARIABLES DE ENTORNO ---
# Esta sección intenta replicar el entorno que Resolve espera.

try:
    # Construir rutas de forma más robusta
    PROGRAM_FILES = os.environ.get("PROGRAMFILES", "C:\\Program Files")
    PROGRAM_DATA = os.environ.get("ALLUSERSPROFILE", "C:\\ProgramData")

    # Ruta a la instalación principal de Resolve
    RESOLVE_INSTALL_PATH = os.path.join(PROGRAM_FILES, "Blackmagic Design", "DaVinci Resolve")
    
    # Ruta a la carpeta de Scripting
    RESOLVE_SCRIPT_FOLDER = os.path.join(PROGRAM_DATA, "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting")
    
    # Ruta al módulo de Python de Resolve
    RESOLVE_SCRIPT_API_PATH = os.path.join(RESOLVE_SCRIPT_FOLDER, "Modules")
    
    # Ruta a la librería fusionscript.dll (¡CRUCIAL!)
    FUSION_SCRIPT_LIB_PATH = os.path.join(RESOLVE_INSTALL_PATH, "fusionscript.dll")

    # --- Aplicar configuración ---

    # 1. Añadir la ruta de instalación principal al path de DLLs
    if sys.version_info.major >= 3 and sys.version_info.minor >= 8:
        os.add_dll_directory(RESOLVE_INSTALL_PATH)
    else:
        os.environ["PATH"] = RESOLVE_INSTALL_PATH + ";" + os.environ["PATH"]
    print(f"ℹ️ Ruta de DLLs añadida: {RESOLVE_INSTALL_PATH}")

    # 2. Añadir la ruta de los módulos de scripting al path de Python
    sys.path.append(RESOLVE_SCRIPT_API_PATH)
    print(f"ℹ️ Ruta de módulos de Scripting añadida: {RESOLVE_SCRIPT_API_PATH}")

    # 3. Establecer las variables de entorno que Resolve podría necesitar
    os.environ["RESOLVE_SCRIPT_API"] = RESOLVE_SCRIPT_FOLDER
    os.environ["RESOLVE_SCRIPT_LIB"] = FUSION_SCRIPT_LIB_PATH
    print(f"ℹ️ Variable de entorno 'RESOLVE_SCRIPT_API' establecida: {os.environ['RESOLVE_SCRIPT_API']}")
    print(f"ℹ️ Variable de entorno 'RESOLVE_SCRIPT_LIB' establecida: {os.environ['RESOLVE_SCRIPT_LIB']}")

except Exception as e:
    print(f"❌ ERROR durante la configuración de rutas: {e}")
    sys.exit(1)


# --- CARGA MANUAL Y FORENSE DE FUSIONSCRIPT ---
print("\n--- INICIO DE CARGA MANUAL DE FUSIONSCRIPT ---")
bmd = None
lib_path = os.getenv("RESOLVE_SCRIPT_LIB")

if not lib_path or not os.path.exists(lib_path):
    print(f"❌ ERROR: No se encuentra fusionscript.dll en la ruta especificada por RESOLVE_SCRIPT_LIB: {lib_path}")
    sys.exit(1)

print(f"✅ Ruta de fusionscript.dll encontrada: {lib_path}")

try:
    import importlib.machinery
    import importlib.util
    print("ℹ️ [Paso 1/6] Módulos importlib cargados.")

    print("ℹ️ [Paso 2/6] Creando ExtensionFileLoader...")
    loader = importlib.machinery.ExtensionFileLoader("fusionscript", lib_path)
    print("✅ [Paso 2/6] Loader creado.")

    print("ℹ️ [Paso 3/6] Creando spec_from_loader...")
    spec = importlib.util.spec_from_loader("fusionscript", loader)
    print("✅ [Paso 3/6] Spec creado.")

    print("ℹ️ [Paso 4/6] Creando module_from_spec...")
    script_module = importlib.util.module_from_spec(spec)
    print("✅ [Paso 4/6] Módulo base creado.")

    print("ℹ️ [Paso 5/6] Ejecutando loader.exec_module()... (ESTE ES EL PUNTO CRÍTICO)")
    loader.exec_module(script_module)
    print("✅ [Paso 5/6] ¡¡¡Fusionscript cargado y ejecutado exitosamente!!!")
    
    bmd = script_module
    print("✅ [Paso 6/6] Módulo asignado a la variable 'bmd'.")

except Exception as e:
    print(f"❌ ERROR INESPERADO durante la carga manual: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if bmd is None:
    print("❌ ERROR FATAL: La carga del módulo 'fusionscript' falló silenciosamente.")
    print("   El proceso probablemente terminó de forma abrupta. Esto sugiere un problema de dependencias de bajo nivel (ej. C++ Redistributable).")
    sys.exit(1)

# --- CONEXIÓN CON DAVINCI RESOLVE ---
print("\n--- CONECTANDO CON DAVINCI RESOLVE ---")
resolve = bmd.scriptapp("Resolve")
if not resolve:
    print("❌ ERROR: No se pudo obtener el objeto 'Resolve'.")
    print("Asegúrate de que DaVinci Resolve está en ejecución.")
    sys.exit(1)

print("✅ Conexión con DaVinci Resolve establecida.")

# --- LÓGICA DE EDICIÓN ---
print("\n--- INICIANDO LÓGICA DE EDICIÓN ---")
projectManager = resolve.GetProjectManager()
project = projectManager.GetCurrentProject()

if not project:
    print("❌ ERROR: No hay un proyecto abierto en DaVinci Resolve.")
    sys.exit(1)

mediaPool = project.GetMediaPool()
timeline_name = "MiTimeline"
video_path = r"Y:\videos\Grabaciones de pantalla\Grabación de pantalla 2025-03-03 210917.mp4"

# 1. Buscar o crear la línea de tiempo
timeline = project.GetCurrentTimeline()
if not timeline or timeline.GetName() != timeline_name:
    print(f"ℹ️ Timeline '{timeline_name}' no es la activa. Buscando o creando...")
    timeline = None
    for i in range(1, project.GetTimelineCount() + 1):
        current_timeline = project.GetTimelineByIndex(i)
        if current_timeline.GetName() == timeline_name:
            timeline = current_timeline
            project.SetCurrentTimeline(timeline)
            break
    
    if not timeline:
        print(f"ℹ️ Timeline '{timeline_name}' no encontrada. Creando una nueva...")
        timeline = mediaPool.CreateEmptyTimeline(timeline_name)
        if not timeline:
            print(f"❌ ERROR: No se pudo crear la línea de tiempo '{timeline_name}'.")
            sys.exit(1)
        project.SetCurrentTimeline(timeline)

print(f"✅ Usando la línea de tiempo: '{timeline.GetName()}'")

# 2. Asegurar que hay una pista de vídeo
if timeline.GetTrackCount("video") == 0:
    print("ℹ️ No hay pistas de vídeo. Añadiendo una nueva...")
    if not timeline.AddTrack("video"):
         print("❌ ERROR: No se pudo añadir una pista de vídeo.")
         sys.exit(1)

# 3. Importar el clip
print(f"ℹ️ Importando clip: {video_path}")
# Comprobar si el clip ya existe para no re-importarlo
existing_clips = mediaPool.GetRootFolder().GetClipList()
clip_to_add = None
for clip in existing_clips:
    if clip.GetClipProperty("File Path") == video_path:
        print("ℹ️ El clip ya existe en el Media Pool.")
        clip_to_add = clip
        break

if not clip_to_add:
    clips_imported = mediaPool.ImportMedia([video_path])
    if not clips_imported:
        print("❌ ERROR: La importación del clip falló. Revisa la ruta del vídeo y los permisos.")
        sys.exit(1)
    clip_to_add = clips_imported[0]

print(f"✅ Clip listo para usar: {clip_to_add.GetName()}")

# 4. Añadir clip a la línea de tiempo
print("ℹ️ Añadiendo clip a la línea de tiempo...")
if not mediaPool.AppendToTimeline([clip_to_add]):
    print("❌ ERROR: Falló la operación AppendToTimeline.")
    sys.exit(1)

print("\n✅ ¡ÉXITO! El clip debería estar en la línea de tiempo.")
print("El proyecto está finalizado. ¡Buen trabajo! 😎")
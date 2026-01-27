import PyInstaller.__main__
import os
import platform
import shutil
import customtkinter

def build():
    # Configuración básica
    app_name = "DowP_Downloader"
    main_script = "main.py"
    icon_file = "DowP-icon.ico"
    theme_file = "red_theme.json"
    system_os = platform.system()

    if not os.path.exists(main_script):
        print(f"Error: No se encuentra {main_script}")
        return
    
    # Argumentos base para PyInstaller
    args = [
        main_script,
        f'--name={app_name}',
        '--onefile',
        '--clean',
    ]

    # --- AJUSTES POR SISTEMA OPERATIVO ---
    if system_os == "Darwin":  # macOS
        print("🍎 Detectado macOS. Preparando bundle .app...")
        args.append('--windowed')  # Sin consola en Mac
        sep = ":" # Separador de rutas para macOS
    else:  # Windows/Otros
        print(f"🪟 Detectado {system_os}. Preparando ejecutable...")
        args.append('--noconsole')
        sep = ";" # Separador de rutas para Windows

    # --- ARCHIVOS DE DATOS (Temas e Iconos) ---
    if os.path.exists(theme_file):
        args.append(f'--add-data={theme_file}{sep}.')

    if os.path.exists(icon_file):
        args.append(f'--icon={icon_file}')
        args.append(f'--add-data={icon_file}{sep}.')

    # --- CUSTOMTKINTER (Ruta dinámica desde el venv) ---
    ctk_path = os.path.dirname(customtkinter.__file__)
    args.append(f'--add-data={ctk_path}{sep}customtkinter')

    # --- DEPENDENCIAS OCULTAS ---
    hidden_imports = [
        'PIL._tkinter_finder',
        'yt_dlp.utils',
        'customtkinter',
        'tkinterdnd2',
    ]
    for imp in hidden_imports:
        args.append(f'--hidden-import={imp}')

    # Carpeta src para que Python encuentre los módulos
    args.append('--paths=src')

    print(f"Iniciando PyInstaller con argumentos: {args}")
    PyInstaller.__main__.run(args)
    
    print("\n" + "="*50)
    print(f"CONSTRUCCIÓN FINALIZADA PARA {system_os}")
    print(f"Busca tu archivo en la carpeta 'dist/'")
    print("="*50)

if __name__ == "__main__":
    build()
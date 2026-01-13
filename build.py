import PyInstaller.__main__
import os
import shutil

def build():
    # Definir nombre del ejecutable
    app_name = "DowP_Downloader"
    main_script = "main.py"
    icon_file = "DowP-icon.ico"
    theme_file = "red_theme.json"

    # Verificar existencia de archivos clave
    if not os.path.exists(main_script):
        print(f"Error: No se encuentra {main_script}")
        return
    
    # Argumentos para PyInstaller
    args = [
        main_script,
        f'--name={app_name}',
        '--noconsole',  # No mostrar consola (para GUI)
        '--onefile',    # Crear un único archivo .exe
        '--clean',      # Limpiar caché antes de construir
    ]

    # Añadir icono si existe
    if os.path.exists(icon_file):
        args.append(f'--icon={icon_file}')
        args.append(f'--add-data={icon_file};.')

    # Añadir tema si existe
    if os.path.exists(theme_file):
        args.append(f'--add-data={theme_file};.')

    # Añadir carpeta src para que Python la encuentre (aunque PyInstaller suele detectarla)
    args.append('--paths=src')

    # Recolectar datos de CustomTkinter (necesario para temas y fuentes)
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    args.append(f'--add-data={ctk_path};customtkinter')
    
    # Importaciones ocultas necesarias (dependencias dinámicas)
    hidden_imports = [
        'PIL._tkinter_finder',
        'yt_dlp.utils',
        'customtkinter',
        'tkinterdnd2',
        'engineio.async_drivers.threading', # A veces necesario para socketio si se usara
    ]
    
    for imp in hidden_imports:
        args.append(f'--hidden-import={imp}')

    print("Iniciando construcción con PyInstaller...")
    print(f"Argumentos: {args}")
    
    # Ejecutar PyInstaller
    PyInstaller.__main__.run(args)
    
    print("\n" + "="*50)
    print("CONSTRUCCIÓN FINALIZADA")
    print("="*50)
    print(f"El ejecutable se encuentra en la carpeta 'dist/{app_name}.exe'")
    print("IMPORTANTE: Asegúrate de que la carpeta 'bin' esté junto al ejecutable")
    print("para que funcionen herramientas externas (FFmpeg, etc.).")

if __name__ == "__main__":
    # Instalar pyinstaller si no existe (opcional, mejor asumir que el usuario corre pip install)
    # os.system("pip install pyinstaller") 
    build()

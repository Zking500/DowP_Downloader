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

    # Añadir carpeta src para que Python la encuentre
    args.append('--paths=src')

    # --- SOLUCIÓN ERROR CAIRO (0x7e) ---
    # Detectar y empaquetar DLLs de Cairo y sus dependencias si existen en MSYS2
    msys_bin = r"C:\msys64\mingw64\bin"
    if os.path.exists(msys_bin):
        print(f"Detectado entorno MSYS2 en {msys_bin}. Buscando dependencias de Cairo...")
        
        # Lista de DLLs críticas para Cairo (dependencias recursivas comunes)
        cairo_deps = [
            "libcairo-2.dll",
            "libfontconfig-1.dll",
            "libfreetype-6.dll",
            "libpixman-1-0.dll",
            "libpng16-16.dll",
            "zlib1.dll",
            "libexpat-1.dll",
            "libharfbuzz-0.dll",
            "libbrotlidec.dll",
            "libbrotlicommon.dll",
            "libbz2-1.dll",
            "libintl-8.dll",
            "libglib-2.0-0.dll",
            "libgraphite2.dll",
            "libpcre2-8-0.dll",
            "libiconv-2.dll",
            "libgcc_s_seh-1.dll",
            "libstdc++-6.dll",
            "libwinpthread-1.dll",
            "libdatrie-1.dll",
            "libthai-0.dll",
            "libsystre-0.dll",
            "libtre-5.dll",
            "libfribidi-0.dll",
            "libpango-1.0-0.dll",
            "libpangocairo-1.0-0.dll",
            "libpangoft2-1.0-0.dll",
            "libpangowin32-1.0-0.dll",
            "libffi-8.dll",
            "libxml2-2.dll",
            "liblzma-5.dll",
            "libzstd.dll"
        ]
        
        found_deps = 0
        for dll in cairo_deps:
            dll_path = os.path.join(msys_bin, dll)
            if os.path.exists(dll_path):
                # Añadir como binario a la raíz del ejecutable (.)
                args.append(f'--add-binary={dll_path};.')
                found_deps += 1
                print(f"  [OK] Añadido: {dll}")
            else:
                # Algunas son opcionales o pueden tener otro nombre, solo avisar
                print(f"  [INFO] No encontrado (puede ser opcional): {dll}")
        
        if found_deps > 0:
            print(f"Total DLLs de Cairo añadidas: {found_deps}")
    else:
        print("ADVERTENCIA: No se encontró C:\\msys64\\mingw64\\bin. Si tu app usa Cairo/SVG, el .exe podría fallar en otros PCs.")

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

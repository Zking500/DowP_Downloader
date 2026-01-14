# DowP Downloader - Descargador de Videos para DaVinci Resolve

Aplicación de escritorio que permite descargar videos de plataformas populares e importarlos directamente a DaVinci Resolve con un solo clic.

## ⚠️ Requisitos Previos

**IMPORTANTE: Lee todos los requisitos antes de comenzar**

1.  **DaVinci Resolve 18 o superior** instalado y abierto
2.  **Python 3.10 (64-bit)** - Versiones distintas causarán errores
3.  **Habilitar scripting externo en DaVinci Resolve**:
    -   Ve a `Preferences -> System -> General`
    -   En `External scripting`, selecciona `Local`
    -   Reinicia DaVinci Resolve

## 🚀 Opciones de Instalación

### Opción A: Ejecutable (.exe) - RECOMENDADO para usuarios principiantes

1. **Descarga el archivo `DowP_Downloader.exe` de la carpeta `dist/`**
2. **Asegúrate de que DaVinci Resolve esté abierto**
3. **Ejecuta el archivo .exe** (puede que Windows te pida permisos)
4. **Listo para usar**

### Opción B: Ejecutar desde código fuente

**Para usuarios avanzados o desarrolladores**

1. **Instala Python 3.10** (verifica con: `python --version`)

2. **Instala las dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Ejecuta la aplicación**:
    ```bash
    python main.py
    ```

## 📋 Guía Rápida de Uso

1. **Abre DaVinci Resolve** (¡debe estar abierto antes de usar la app!)
2. **Ejecuta DowP Downloader**
3. **Pega la URL del video** que quieres descargar
4. **Selecciona calidad y formato**
5. **Activa "Importar a DaVinci"** si quieres que se importe automáticamente
6. **Descarga y disfruta**

## 🔧 Solución de Problemas

**Si la aplicación no se conecta a DaVinci Resolve:**
- Verifica que DaVinci esté abierto
- Comprueba que el scripting externo esté habilitado
- Reinicia ambas aplicaciones

**Errores de DLL (0x7e)**: Usa el ejecutable .exe, ya incluye todas las librerías necesarias

**Python 3.10 es obligatorio**: Versiones 3.9 o 3.11+ causarán errores de conexión

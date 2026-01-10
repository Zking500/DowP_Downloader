# Proyecto de Control de DaVinci Resolve

Este proyecto te permite controlar DaVinci Resolve usando Python.

## Prerrequisitos

1.  **DaVinci Resolve 18+**: Asegúrate de tener instalada la versión 18 o más reciente de DaVinci Resolve.
2.  **Python 3.10 (64-bit)**: Este es un requisito estricto de la API de scripting de DaVinci Resolve.
3.  **Microsoft Visual C++ Redistributable (x64)**: Descárgalo e instálalo desde [aquí](https://aka.ms/vs/17/release/vc_redist.x64.exe).
4.  **Habilitar Scripting Externo en Resolve**:
    *   Abre DaVinci Resolve.
    *   Ve a `DaVinci Resolve > Preferences > System > General`.
    *   En "External scripting", selecciona `Local`.
    *   Haz clic en "Save" y reinicia DaVinci Resolve.

## Configuración del Proyecto

1.  **Abrir PowerShell y establecer la política de ejecución**:
    Antes de crear el entorno virtual, puede que necesites permitir la ejecución de scripts. Abre una terminal de PowerShell y ejecuta el siguiente comando:
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
    Cuando se te pida, escribe `S` y presiona Enter.

2.  **Crear y activar un entorno virtual**:
    ```bash
    python -m venv venv-resolve
    .\venv-resolve\Scripts\activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecutar el script**:
    ```bash
    python dowp_panel.py
    ```
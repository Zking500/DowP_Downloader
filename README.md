# Proyecto de Control de DaVinci Resolve

Este script de Python permite controlar DaVinci Resolve de forma remota para automatizar tareas de edición, como la importación de clips y su adición a una línea de tiempo.

## ⚠️ Requisitos Previos

Para que este script funcione, el entorno de ejecución debe cumplir con los siguientes requisitos **OBLIGATORIAMENTE**:

1.  **DaVinci Resolve 18 o superior** instalado.
2.  **Python 3.10 (64-bit)**. Versiones más recientes (3.11+) o más antiguas no son compatibles con las librerías de scripting nativas de Resolve y provocarán errores de sistema silenciosos.
4.  **Habilitar "External scripting" en DaVinci Resolve**:
    -   Ve a `Preferences -> System -> General`.
    -   En la sección `External scripting`, selecciona `Local`.
    -   Guarda y reinicia DaVinci Resolve.

## 🚀 Instalación y Uso

1.  **Instala los Requisitos Previos**: Asegúrate de haber instalado todo lo mencionado arriba.

2.  **Clona este repositorio**:
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_DIRECTORIO>
    ```

3.  **Crea y activa un entorno virtual de Python 3.10**:
    ```powershell
    # Desde la raíz del proyecto
    py -3.10 -m venv venv-resolve-test
    .\venv-resolve-test\Scripts\Activate.ps1
    ```

4.  **Ejecuta el script**:
    Asegúrate de que DaVinci Resolve esté abierto.
    ```powershell
    python prueba.py
    ```

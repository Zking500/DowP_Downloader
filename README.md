# DowP – Edición Rescatada de Lost Media 🕵️‍♂️

**Versión 1.4.4.1 (2026)** – Rescatado por [Zking500](https://github.com/Zking500)

> *"Lo que una vez se perdió, ahora ha sido restaurado."*

![DowP Splash](https://i.imgur.com/placeholder.png) <!-- Puedes añadir una captura si quieres -->

## 📜 La Historia

Este proyecto es un **rescate de código perdido** (lost media). La versión original de DowP (1.4.4) fue creada por **~~MarckDP~~** a inicios de 2026, pero desapareció de Internet y se consideraba irrecuperable. Tras un arduo proceso de ingeniería inversa y reconstrucción, esta versión ha sido **resucitada, adaptada y mejorada** para funcionar en sistemas modernos.

**No es un fork oficial**, sino un **homenaje y continuación** del trabajo original.

## ✨ Créditos

- **Código original**: ~~MarckDP~~ (lost media) – gracias por la base.
- **Rescate, restauración y mejoras**: [Zking500](https://github.com/Zking500)
- **Inspiración**: La comunidad de preservación de software.

## 🚀 Características

- ✅ Descarga videos de YouTube y otras plataformas (mediante `yt-dlp`).
- ✅ Soporte para **playlists** y selección de calidad.
- ✅ **Recodificación** de videos (códecs, resolución, FPS, etc.).
- ✅ **Extracción de fotogramas** y **reescalado por IA** (Upscayl, Waifu2x, SRMD).
- ✅ **Integración con DaVinci Resolve** (importación automática a la Media Pool).
- ✅ Interfaz gráfica con **CustomTkinter** (tema oscuro/claro).
- ✅ **Modo por lotes** para descargar múltiples URLs o archivos locales.
- ✅ **Portable** – no requiere instalación, solo ejecutar.

## ⚠️ Requisitos Previos

### Para Linux (recomendado)

- **Python 3.10 o superior** (3.11+ también funciona).
- **pip** y **entorno virtual** (opcional pero recomendado).
- **FFmpeg** instalado en el sistema (`sudo apt install ffmpeg` en Debian/Ubuntu).
- **Deno** (opcional pero recomendado para YouTube – se puede instalar desde la app).

### Para Windows (en desarrollo)

- Python 3.10 (64-bit) con **tcl/tk** habilitado.
- DaVinci Resolve 18+ (si quieres la integración).

## 📦 Instalación y Ejecución

### Opción A: Ejecutable (próximamente)

Pronto estarán disponibles los ejecutables para Linux y Windows en la sección [Releases](https://github.com/Zking500/DowP_Downloader/releases).

### Opción B: Desde el código fuente (recomendado para contribuir)

```bash
# 1. Clona el repositorio
git clone https://github.com/Zking500/DowP_Downloader.git
cd DowP_Downloader

# 2. Crea y activa un entorno virtual (Linux/macOS)
python3 -m venv venv
source venv/bin/activate

# En Windows: venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Ejecuta la aplicación
python main.py

Nota: Si te da error de tkinter, asegúrate de tener instalada la librería Tk (en Linux: sudo apt install python3-tk).

🖥️ Uso Básico
Abre la aplicación.

Pega una URL de YouTube (o de otra plataforma compatible).

Selecciona calidad y formato (o usa el modo rápido).

(Opcional) Activa la recodificación o la importación a DaVinci Resolve.

Haz clic en "Iniciar Descarga".

Para lotes, usa la pestaña "Proceso por Lotes".

🛠️ Solución de Problemas
Problema	Solución
Error 403 (Forbidden)	Configura cookies desde la sección "Cookies" (usa la opción "Desde Navegador" o archivo manual).
Falta FFmpeg	Instálalo con sudo apt install ffmpeg (Linux) o descárgalo desde la app.
No se conecta a DaVinci Resolve	Asegúrate de que Resolve esté abierto y que el scripting externo esté habilitado (Preferencias → Sistema → General → External scripting → Local).
Error de Python 3.10	Usa Python 3.10 o superior; si usas 3.11, funciona igual.
📌 Estado del Proyecto
✅ Linux: Totalmente funcional.

🔄 Windows: En pruebas (la integración con Resolve requiere ajustes).

🧪 macOS: No probado (pero debería funcionar con ajustes menores).

🤝 Contribuciones
¡Las contribuciones son bienvenidas! Si encuentras un bug o quieres mejorar algo, abre un issue o un pull request. Eso sí, por favor, respeta el espíritu de "rescate" y mantén los créditos originales.

📄 Licencia
Este proyecto se distribuye bajo la licencia MIT (al igual que el original). Consulta el archivo LICENSE para más detalles.

🙏 Agradecimientos
A ~~MarckDP~~ por el trabajo original (aunque se haya perdido, su legado perdura).

A la comunidad de yt-dlp y ffmpeg por las herramientas que hacen posible esto.

A ti, por usar y mantener vivo este proyecto.

Hecho con ❤️ y un poco de nostalgia digital.

text

---

## 🖼️ ¿Quieres añadir una imagen?

Si tienes una captura de pantalla de la aplicación, súbela a la carpeta del repositorio y referencia con `![DowP Splash](ruta/a/la/imagen.png)`. Puedes usar la que tengas para darle más vida al README.

---

## 📌 Nota sobre el tachado

El texto `~~MarckDP~~` se renderiza como tachado en GitHub Markdown. Así queda ese toque de humor y dramatismo que pedías.

---

## ✅ Próximo paso

1. **Copia este contenido** y reemplaza el `README.md` en tu repositorio.
2. **Haz commit y push**:

```bash
git add README.md
git commit -m "Actualiza README con la historia del rescate"
git push
Ve a la página del repositorio y verifica que se vea bien.


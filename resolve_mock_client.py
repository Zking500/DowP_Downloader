import socketio
import time

# --- Configuración ---
SERVER_URL = "http://localhost:7788"
APP_ID = "DaVinci Resolve"
TEST_FILE_PATH = "C:/path/to/your/test/file.mov"

# --- Cliente Socket.IO ---
sio = socketio.Client()

@sio.event
def connect():
    print(f"✅ Conectado al servidor en {SERVER_URL}")
    print(f"   Registrando como: '{APP_ID}'")
    sio.emit('register', {'appIdentifier': APP_ID})
    
    # Esperar un momento para que el servidor procese el registro
    time.sleep(1)
    
    # Pedir ser el objetivo activo
    print(f"   Solicitando ser el objetivo activo...")
    sio.emit('set_active_target', {'targetApp': APP_ID})

@sio.event
def disconnect():
    print("❌ Desconectado del servidor.")

@sio.on('active_target_update')
def on_active_target_update(data):
    active_target = data.get('activeTarget')
    print(f"📢 Actualización del objetivo activo: {active_target}")
    
    # Si ahora somos el objetivo, enviamos el archivo de prueba
    if active_target == APP_ID:
        print(f"   ¡Somos el objetivo! Enviando archivo de prueba: {TEST_FILE_PATH}")
        sio.emit('push_files', {'files': [TEST_FILE_PATH]})
        
        # Desconectar después de enviar
        time.sleep(1)
        sio.disconnect()

def main():
    try:
        print("🚀 Iniciando cliente de prueba para DaVinci Resolve...")
        sio.connect(SERVER_URL)
        sio.wait()
    except socketio.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: No se pudo conectar a {SERVER_URL}")
        print("   Asegúrate de que la aplicación DowP se esté ejecutando.")
    except Exception as e:
        print(f"🔥 Ocurrió un error inesperado: {e}")

if __name__ == '__main__':
    main()
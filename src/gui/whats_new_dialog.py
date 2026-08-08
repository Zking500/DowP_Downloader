import customtkinter as ctk

class WhatsNewDialog(ctk.CTkToplevel):
    def __init__(self, parent, app_version="1.4.4", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title(f"Novedades v{app_version}")
        self.geometry("420x320")
        self.resizable(False, False)
        
        # Mantener la ventana emergente sobre la principal
        self.transient(parent)
        self.grab_set()

        # Encabezado
        label = ctk.CTkLabel(
            self, 
            text=f"¡Novedades en DowP v{app_version}!", 
            font=("Segoe UI", 16, "bold")
        )
        label.pack(pady=(20, 10))

        # Cuadro de texto con las notas
        textbox = ctk.CTkTextbox(self, width=370, height=180)
        textbox.pack(padx=15, pady=5)
        textbox.insert("1.0", "• Versión adaptada y optimizada para Linux.\n• Corrección en la integración de componentes multimedia y GUI.")
        textbox.configure(state="disabled")

        # Botón para cerrar
        btn_close = ctk.CTkButton(self, text="Entendido", command=self.destroy)
        btn_close.pack(pady=12)

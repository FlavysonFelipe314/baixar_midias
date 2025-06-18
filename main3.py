import os
import asyncio
import threading
import nest_asyncio
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from telethon import TelegramClient, errors

nest_asyncio.apply()

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class TelegramDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Telegram Downloader")
        self.geometry("600x520")
        self.resizable(False, False)

        # Único event loop do app
        self.loop = asyncio.new_event_loop()
        nest_asyncio.apply(self.loop)

        self.client = None
        self.session_name = "session"

        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.code = None
        self.channel = None

        self.create_frames()
        self.show_frame(self.frame_api)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_frames(self):
        # Frame 1 - API ID, API HASH, Canal
        self.frame_api = ctk.CTkFrame(self)
        self.frame_api.pack(fill="both", expand=True)

        ctk.CTkLabel(self.frame_api, text="Passo 1: Informe API ID, API HASH e canal", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        self.api_id_entry = ctk.CTkEntry(self.frame_api, placeholder_text="API ID (números)")
        self.api_id_entry.pack(pady=10, padx=40, fill='x')
        self.api_hash_entry = ctk.CTkEntry(self.frame_api, placeholder_text="API HASH")
        self.api_hash_entry.pack(pady=10, padx=40, fill='x')
        self.channel_entry = ctk.CTkEntry(self.frame_api, placeholder_text="Canal (ex: @nome_canal)")
        self.channel_entry.pack(pady=10, padx=40, fill='x')

        ctk.CTkButton(self.frame_api, text="Próximo", command=self.validate_api).pack(pady=30)

        # Frame 2 - Telefone
        self.frame_phone = ctk.CTkFrame(self)

        ctk.CTkLabel(self.frame_phone, text="Passo 2: Informe seu número de telefone", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        self.phone_entry = ctk.CTkEntry(self.frame_phone, placeholder_text="Número com DDI (ex: +5511999999999)")
        self.phone_entry.pack(pady=10, padx=40, fill='x')

        ctk.CTkButton(self.frame_phone, text="Próximo", command=self.validate_phone).pack(pady=30)
        ctk.CTkButton(self.frame_phone, text="Voltar", command=lambda: self.show_frame(self.frame_api)).pack()

        # Frame 3 - Código SMS
        self.frame_code = ctk.CTkFrame(self)

        ctk.CTkLabel(self.frame_code, text="Passo 3: Digite o código enviado pelo Telegram", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        self.code_entry = ctk.CTkEntry(self.frame_code, placeholder_text="Código de verificação")
        self.code_entry.pack(pady=10, padx=40, fill='x')

        ctk.CTkButton(self.frame_code, text="Iniciar Download", command=self.validate_code).pack(pady=30)
        ctk.CTkButton(self.frame_code, text="Voltar", command=lambda: self.show_frame(self.frame_phone)).pack()

        # Log - sempre visível na parte inferior
        self.log_box = ctk.CTkTextbox(self, height=150, state="disabled")
        self.log_box.pack(side="bottom", fill="x", padx=20, pady=10)

    def show_frame(self, frame):
        for f in [self.frame_api, self.frame_phone, self.frame_code]:
            f.pack_forget()
        frame.pack(fill="both", expand=True)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def validate_api(self):
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        channel = self.channel_entry.get().strip()

        if not api_id.isdigit():
            messagebox.showerror("Erro", "API ID deve conter só números.")
            return
        if not api_hash or len(api_hash) < 10:
            messagebox.showerror("Erro", "API HASH inválido.")
            return
        if not channel:
            messagebox.showerror("Erro", "Informe o canal.")
            return

        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.channel = channel
        self.show_frame(self.frame_phone)

    def validate_phone(self):
        phone = self.phone_entry.get().strip()
        if not phone.startswith("+") or len(phone) < 10:
            messagebox.showerror("Erro", "Número inválido. Use o formato +5511999999999.")
            return

        self.phone = phone
        self.show_frame(self.frame_code)
        threading.Thread(target=self.send_code_thread, daemon=True).start()

    def send_code_thread(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.send_code())

    async def send_code(self):
        self.log("[*] Conectando ao Telegram...")
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.connect()
        if await self.client.is_user_authorized():
            self.log("[+] Já autenticado!")
            return
        try:
            await self.client.send_code_request(self.phone)
            self.log("[*] Código enviado para o telefone.")
        except Exception as e:
            self.log(f"[!] Erro ao enviar código: {e}")

    def validate_code(self):
        code = self.code_entry.get().strip()
        if not code or len(code) < 4:
            messagebox.showerror("Erro", "Informe o código de verificação recebido.")
            return
        self.code = code
        self.disable_buttons()
        threading.Thread(target=self.sign_in_and_download_thread, daemon=True).start()

    def disable_buttons(self):
        for frame in [self.frame_api, self.frame_phone, self.frame_code]:
            for widget in frame.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    widget.configure(state="disabled")

    def enable_buttons(self):
        for frame in [self.frame_api, self.frame_phone, self.frame_code]:
            for widget in frame.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    widget.configure(state="normal")

    def sign_in_and_download_thread(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.sign_in_and_download())

    async def sign_in_and_download(self):
        try:
            await self.client.sign_in(self.phone, self.code)
        except errors.SessionPasswordNeededError:
            password = simpledialog.askstring("Senha 2FA", "Digite sua senha 2FA:", show='*', parent=self)
            if password:
                await self.client.sign_in(password=password)
            else:
                self.log("[!] Senha 2FA não informada.")
                self.enable_buttons()
                return
        except Exception as e:
            self.log(f"[!] Erro ao autenticar: {e}")
            self.enable_buttons()
            return

        self.log("[+] Autenticado com sucesso! Iniciando download...")

        await self.download_media()

        self.enable_buttons()

    async def download_media(self):
        os.makedirs("midias", exist_ok=True)
        total = 0
        try:
            async for msg in self.client.iter_messages(self.channel):
                if msg.photo:
                    path = await self.client.download_media(msg.photo, file="midias/")
                    self.log(f"📷 Imagem salva: {path}")
                    total += 1
                elif msg.video:
                    path = await self.client.download_media(msg.video, file="midias/")
                    self.log(f"🎥 Vídeo salvo: {path}")
                    total += 1
                elif msg.document:
                    path = await self.client.download_media(msg.document, file="midias/")
                    self.log(f"📄 Documento salvo: {path}")
                    total += 1
            self.log(f"\n✅ Download finalizado! Total: {total} arquivos.")
        except Exception as e:
            self.log(f"[!] Erro no download: {e}")

    def on_closing(self):
        if self.client and self.client.is_connected():
            self.log("[*] Desconectando do Telegram...")
            self.loop.run_until_complete(self.client.disconnect())
        self.destroy()

if __name__ == "__main__":
    app = TelegramDownloaderApp()
    app.mainloop()

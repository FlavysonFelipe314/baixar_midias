import os
import asyncio
import threading
import nest_asyncio
import json
import customtkinter as ctk
from tkinter import messagebox, simpledialog, filedialog
from telethon import TelegramClient, errors

nest_asyncio.apply()

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

OFFSET_FILE = "offsets.json"

class TelegramDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Telegram Downloader")
        self.geometry("600x580")
        self.resizable(False, False)

        self.loop = asyncio.new_event_loop()
        nest_asyncio.apply(self.loop)

        self.client = None
        self.session_name = "session"

        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.code = None
        self.channel = None
        self.output_dir = os.path.abspath("midias")

        self.authenticated = False
        self.download_active = False

        self.offsets = self.load_offsets()

        self.create_frames()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_frames(self):
        self.frame_api = ctk.CTkFrame(self)
        self.frame_api.pack(fill="both", expand=True)

        ctk.CTkLabel(self.frame_api, text="Configuração Inicial", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        self.api_id_entry = ctk.CTkEntry(self.frame_api, placeholder_text="API ID")
        self.api_id_entry.pack(pady=5, padx=40, fill='x')
        self.api_hash_entry = ctk.CTkEntry(self.frame_api, placeholder_text="API HASH")
        self.api_hash_entry.pack(pady=5, padx=40, fill='x')
        self.channel_entry = ctk.CTkEntry(self.frame_api, placeholder_text="@canal")
        self.channel_entry.pack(pady=5, padx=40, fill='x')

        self.dir_button = ctk.CTkButton(self.frame_api, text="Selecionar Pasta de Destino", command=self.select_output_dir)
        self.dir_button.pack(pady=5)
        self.dir_label = ctk.CTkLabel(self.frame_api, text=f"Pasta atual: {self.output_dir}")
        self.dir_label.pack(pady=5)

        ctk.CTkButton(self.frame_api, text="Conectar ou Trocar Canal", command=self.setup_and_start_download).pack(pady=15)

        self.log_box = ctk.CTkTextbox(self, height=150, state="disabled")
        self.log_box.pack(side="bottom", fill="x", padx=20, pady=10)
        self.pause_button = ctk.CTkButton(self, text="Pausar Download", command=self.pause_download)
        self.pause_button.pack(side="bottom", pady=5)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def select_output_dir(self):
        selected = filedialog.askdirectory()
        if selected:
            self.output_dir = selected
            self.dir_label.configure(text=f"Pasta atual: {self.output_dir}")

    def load_offsets(self):
        if os.path.exists(OFFSET_FILE):
            try:
                with open(OFFSET_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"[!] Falha ao carregar offsets: {e}")
        return {}

    def save_offsets(self):
        try:
            with open(OFFSET_FILE, "w") as f:
                json.dump(self.offsets, f)
        except Exception as e:
            self.log(f"[!] Falha ao salvar offsets: {e}")

    def setup_and_start_download(self):
        try:
            self.api_id = int(self.api_id_entry.get().strip())
            self.api_hash = self.api_hash_entry.get().strip()
            new_channel = self.channel_entry.get().strip()
            if not new_channel.startswith("@"):
                raise ValueError("Canal inválido")
        except Exception as e:
            messagebox.showerror("Erro", f"Verifique os dados: {e}")
            return

        # Troca canal somente se for diferente
        if new_channel != self.channel:
            self.log(f"[*] Trocando canal de {self.channel} para {new_channel}")
            self.channel = new_channel
            self.download_active = False  # para qualquer download anterior

        if not self.authenticated:
            self.phone = simpledialog.askstring("Telefone", "Digite seu número com DDI:", initialvalue="+55")
            threading.Thread(target=self.send_code_thread, daemon=True).start()
        else:
            if not self.download_active:
                self.download_active = True
                threading.Thread(target=self.download_media_thread, daemon=True).start()

    def send_code_thread(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.send_code())

    async def send_code(self):
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.connect()
        if await self.client.is_user_authorized():
            self.authenticated = True
            self.log("[+] Já autenticado. Iniciando download...")
            self.download_active = True
            await self.download_media()
            return
        try:
            await self.client.send_code_request(self.phone)
            self.log("[*] Código enviado para o telefone.")
            self.code = simpledialog.askstring("Código", "Digite o código recebido:")
            await self.client.sign_in(self.phone, self.code)
            self.authenticated = True
            self.log("[+] Autenticado com sucesso.")
            self.download_active = True
            await self.download_media()
        except errors.SessionPasswordNeededError:
            password = simpledialog.askstring("2FA", "Senha 2FA:", show='*')
            await self.client.sign_in(password=password)
            self.authenticated = True
            self.log("[+] Autenticado com sucesso com 2FA.")
            self.download_active = True
            await self.download_media()
        except Exception as e:
            self.log(f"[!] Erro ao autenticar: {e}")

    def download_media_thread(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.download_media())

    async def download_media(self):
        os.makedirs(self.output_dir, exist_ok=True)
        total = 0

        # Busca offset_id salvo para canal atual, default 0
        offset_id = self.offsets.get(self.channel, 0)

        try:
            # Usar reverse=True para baixar mensagens da mais antiga para mais recente após offset
            async for msg in self.client.iter_messages(self.channel, offset_id=offset_id, reverse=True):
                if not self.download_active:
                    self.log("[*] Download pausado pelo usuário.")
                    break

                media = msg.photo or msg.video or msg.document
                if media:
                    path = await self.client.download_media(media, file=self.output_dir)
                    self.log(f"[+] Arquivo salvo: {path}")
                    total += 1

                # Atualiza o offset para última msg baixada
                self.offsets[self.channel] = msg.id
                self.save_offsets()

            self.log(f"[✓] Download finalizado. Total: {total} arquivos.")
        except Exception as e:
            self.log(f"[!] Erro no download: {e}")

    def pause_download(self):
        self.download_active = False
        self.log("[*] Download pausado.")

    def on_closing(self):
        if self.client and self.client.is_connected():
            self.loop.run_until_complete(self.client.disconnect())
        self.save_offsets()
        self.destroy()

if __name__ == "__main__":
    app = TelegramDownloaderApp()
    app.mainloop()

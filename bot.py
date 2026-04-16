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
        # Añadimos rutas críticas manuales para asegurar hallazgos
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
        bot.send_message(chat_id, "⚠️ El proceso finalizó sin encontrar datos relevantes.")

# --- COMANDOS RECON (MEJORADOS PARA TU PÁGINA) ---

@bot.message_handler(commands=['dir'])
def cmd_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para buscar PHP/Directorios:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_dir, m))

def do_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"res_dir_{int(time.time())}.txt")
    wordlist = obtener_wordlist_maestra()
    bot.send_message(message.chat.id, "🚀 Escaneando con modo --wildcard (Precision Mode)...")
    # -x php,txt,html: asegura buscar archivos php
    # --wildcard: evita que tu hosting te engañe con falsos positivos
    cmd = f"gobuster dir -u {url} -w {wordlist} -x php,txt,html,json,bak -o {path} -k --wildcard --no-error"
    subprocess.run(cmd, shell=True)
    enviar_reporte(message.chat.id, path, f"📂 Archivos encontrados en `{url}`")

@bot.message_handler(commands=['buscar_cc'])
def cmd_cc(message):
    msg = bot.send_message(message.chat.id, "💳 **URL para buscar CC en la Web:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_cc, m))

def do_cc(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"cc_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "💳 Analizando código fuente y JS en busca de tarjetas...")
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
    bot.send_message(message.chat.id, "🔍 Buscando .sql, .xls y copias de seguridad...")
    cmd = f"gobuster dir -u {url} -w {wordlist} -x sql,xls,xlsx,bak,zip,db -o {path} -k --wildcard"
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
    # Cadenas crudas (r'') para evitar los SyntaxWarnings de Termux
    regex = r'http[s]?://[^\s\'"]+|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
    subprocess.run(f"strings '{tmp}' | grep -E '{regex}' > '{res}'", shell=True)
    if os.path.exists(tmp): os.remove(tmp)
    enviar_reporte(message.chat.id, res, "📱 Secretos del APK")

# --- COMANDOS RESTAURADOS (LOS QUE FALTABAN) ---

@bot.message_handler(commands=['fuerza'])
def cmd_hydra(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: [IP] [Servicio] [Usuario]**\nEj: `1.1.1.1 ssh root`")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_hydra, m))

def do_hydra(message):
    try:
        ip, svc, usr = message.text.split()
        report = os.path.join(BASE_DIR, f"hydra_{ip}.txt")
        bot.send_message(message.chat.id, f"⚡ Iniciando Brute Force en {ip}...")
        # Usa passwords.txt de tu carpeta
        subprocess.run(f"hydra -l {usr} -P passwords.txt {ip} {svc} -o {report}", shell=True)
        enviar_reporte(message.chat.id, report, f"⚡ Resultados Hydra: {ip}")
    except:
        bot.send_message(message.chat.id, "❌ Error. Usa: `IP Servicio Usuario`")

@bot.message_handler(commands=['fuzz'])
def cmd_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ (ej: http://site.com/FUZZ):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_fuzz, m))

def do_fuzz(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, "fuzz_res.txt")
    bot.send_message(message.chat.id, "🔍 Ejecutando FFUF...")
    subprocess.run(f"ffuf -u {url} -w {obtener_wordlist_maestra()} -mc 200,403 -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "🔍 Resultados FFUF")

@bot.message_handler(commands=['crawl'])
def cmd_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **URL para Crawling:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_crawl, m))

def do_crawl(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "crawl_res.txt")
    bot.send_message(message.chat.id, "🕸️ Katana mapeando endpoints...")
    subprocess.run(f"katana -u {target} -silent -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "🕸️ Resultados Crawling")

@bot.message_handler(commands=['subs'])
def cmd_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el Dominio:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_subs, m))

def do_subs(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "subs_res.txt")
    bot.send_message(message.chat.id, "📡 Buscando subdominios...")
    subprocess.run(f"subfinder -d {target} -silent -all -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, f"🏁 Subdominios de {target}")

@bot.message_handler(commands=['auditar'])
def cmd_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **URL para Nuclei:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(do_audit, m))

def do_audit(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, "audit_res.txt")
    bot.send_message(message.chat.id, "🛰️ Nuclei buscando vulnerabilidades...")
    subprocess.run(f"nuclei -u {target} -silent -o {path}", shell=True)
    enviar_reporte(message.chat.id, path, "📄 Reporte de Vulnerabilidades")

@bot.message_handler(commands=['help', 'start'])
def cmd_help(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        txt = (
            "🚀 **Bugtin Bot v17.0 Full Suite**\n\n"
            "📂 `/dir` - Fuerza bruta (Precision PHP)\n"
            "💳 `/buscar_cc` - Buscar Tarjetas en Web\n"
            "🗄️ `/buscar_db` - Buscar .sql, .xls y backups\n"
            "📱 `/apk` - Analizar Secretos de APK\n"
            "⚡ `/fuerza` - Hydra (Brute Force)\n"
            "🔍 `/fuzz` - FFUF (Fuzzing)\n"
            "🕸️ `/crawl` - Katana (Crawling)\n"
            "📡 `/subs` - Subdominios\n"
            "🔓 `/auditar` - Nuclei Scan"
        )
        bot.send_message(message.chat.id, txt, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bugtin Bot v17.0 Online - Suite Completa Cargada")
    bot.polling(none_stop=True)

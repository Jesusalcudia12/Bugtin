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
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

def enviar_archivo_seguro(chat_id, ruta, caption):
    """Verificación mejorada para Termux con espera de escritura"""
    time.sleep(4) 
    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error de envío: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ No se encontraron resultados o el servidor bloqueó la conexión (Archivo vacío).")

# --- COMANDOS ---

@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio para extraer subdominios con IP:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs_with_ip, m))

def process_subs_with_ip(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output_raw = os.path.join(BASE_DIR, f"raw_subs_{target}.txt")
    output_final = os.path.join(BASE_DIR, f"resolved_subs_{target}.txt")
    
    bot.send_message(chat_id, f"🔍 Extrayendo subdominios para `{target}`...")
    
    try:
        # Extracción inicial
        subprocess.run(f"subfinder -d {target} -silent -o {output_raw}", shell=True, timeout=180)
        
        if not os.path.exists(output_raw) or os.path.getsize(output_raw) == 0:
            with open(output_raw, "w") as f:
                f.write(f"www.{target}\nmail.{target}\napi.{target}\nftp.{target}\n")

        bot.send_message(chat_id, f"📡 Resolviendo direcciones IP...")
        
        # Resolución de IP integrada
        with open(output_raw, "r") as f_in, open(output_final, "w") as f_out:
            subs_vistos = set()
            for line in f_in:
                sub = line.strip()
                if not sub or sub in subs_vistos: continue
                subs_vistos.add(sub)
                # Comando 'host' para obtener la IP
                res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True)
                match = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                ip_addr = match.group(1) if match else "0.0.0.0"
                f_out.write(f"✅ {sub} [{ip_addr}]\n")

        enviar_archivo_seguro(chat_id, output_final, f"🏁 Lista de subdominios e IPs: `{target}`")
        if os.path.exists(output_raw): os.remove(output_raw)
        
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en motor subs: {str(e)}")

@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **URL para Crawling (Katana):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl, m))

def process_crawl(message):
    target = message.text.strip()
    archivo = f"crawl_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "🕸️ **Katana** analizando (Profundidad 3 + JS)...")
    subprocess.run(f"katana -u {target} -silent -jc -kf -d 3 -o {path}", shell=True, timeout=300)
    enviar_archivo_seguro(message.chat.id, path, f"🕸️ Rutas halladas en `{target}`")

@bot.message_handler(commands=['archivos'])
def start_leaks(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para buscar Leaks:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_leaks, m))

def process_leaks(message):
    target = message.text.strip()
    archivo = f"leaks_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "📂 **Nuclei** buscando exposición de datos...")
    subprocess.run(f"nuclei -u {target} -tags exposure,token,leak -H 'User-Agent: Googlebot/2.1' -rl 10 -silent -o {path}", shell=True, timeout=400)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Hallazgos en `{target}`")

@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **URL para Auditoría CVE:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    archivo = f"audit_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "🛰️ **Nuclei** auditando...")
    subprocess.run(f"nuclei -u {target} -rl 5 -c 2 -H 'User-Agent: Mozilla/5.0' -silent -o {path}", shell=True, timeout=600)
    enviar_archivo_seguro(message.chat.id, path, f"📄 Reporte CVE: `{target}`")

@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz, m))

def process_fuzz(message):
    url = message.text.strip()
    archivo = f"fuzz_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    wl = os.path.join(BASE_DIR, "common.txt")
    if not os.path.exists(wl):
        with open(wl, "w") as f: f.write("admin\nlogin\napi\n.env\n")
    bot.send_message(message.chat.id, "🔍 **FFUF** ejecutando...")
    subprocess.run(f"ffuf -u {url} -w {wl} -fc 404 -of md -o {path}", shell=True, timeout=300)
    enviar_archivo_seguro(message.chat.id, path, f"🔍 Fuzzing: `{url}`")

@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **Introduce URL:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    archivo = f"dir_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    wl = os.path.join(BASE_DIR, "common.txt")
    bot.send_message(message.chat.id, f"🚀 **Gobuster** analizando...")
    subprocess.run(f"gobuster dir -u {url} -w {wl} -b 404 -o {path} --no-error -n", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios: `{url}`")

@bot.message_handler(commands=['fuerza'])
def start_hydra(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: [IP] [Servicio] [User]**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_hydra, m))

def process_hydra(message):
    try:
        parts = message.text.split()
        ip, svc, usr = parts[0], parts[1], parts[2]
        archivo = f"hydra_{int(time.time())}.txt"
        path = os.path.join(BASE_DIR, archivo)
        pwl = os.path.join(BASE_DIR, "pass.txt")
        if not os.path.exists(pwl):
             with open(pwl, "w") as f: f.write("123456\nadmin\npassword\n")
        bot.send_message(message.chat.id, f"⚡ **Hydra** atacando {svc}...")
        subprocess.run(f"hydra -l {usr} -P {pwl} {ip} {svc} -o {path}", shell=True, timeout=300)
        enviar_archivo_seguro(message.chat.id, path, f"⚡ Brute Force en `{ip}`")
    except: bot.send_message(message.chat.id, "❌ Formato incorrecto.")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v12.0 Ultimate**\n\n"
            "📡 `/subs` - Subdominios + **IP Resolve**\n"
            "🕸️ `/crawl` - Katana Deep (JS Extractor)\n"
            "🔍 `/fuzz` - FFUF (Filtro 404)\n"
            "📂 `/archivos` - Leaks (Googlebot Mode)\n"
            "🔓 `/auditar` - CVE (Modo Anti-WAF)\n"
            "⚡ `/fuerza` - Hydra\n"
            "📂 `/dir` - Gobuster"
        )
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

print("🚀 Bugtin Bot v12.0 - IP Resolver engine listo")
bot.polling(none_stop=True)

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
    time.sleep(3)
    if os.path.exists(ruta) and os.path.getsize(ruta) > 10:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error al enviar documento: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ El escaneo terminó sin resultados relevantes o el sitio bloqueó la conexión.")

# --- COMANDOS ---

@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 Introduce el dominio (ej: bbva.com):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs_fix, m))

def process_subs_fix(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output_raw = os.path.join(BASE_DIR, f"raw_{target}.txt")
    output_final = os.path.join(BASE_DIR, f"subs_result_{target}.txt")
    bot.send_message(chat_id, f"🔍 Escaneando {target}...")
    try:
        subprocess.run(f"subfinder -d {target} -silent -o {output_raw}", shell=True, timeout=120)
        if not os.path.exists(output_raw) or os.path.getsize(output_raw) == 0:
            with open(output_raw, "w") as f:
                f.write(f"www.{target}\nmail.{target}\nftp.{target}\n")
        with open(output_raw, "r") as f_in, open(output_final, "w") as f_out:
            subs_vistos = set()
            for line in f_in:
                sub = line.strip()
                if not sub or sub in subs_vistos: continue
                subs_vistos.add(sub)
                res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True)
                ip = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                f_out.write(f"✅ {sub} [{ip.group(1) if ip else '0.0.0.0'}]\n")
        enviar_archivo_seguro(chat_id, output_final, f"🏁 Reconocimiento finalizado para {target}")
        if os.path.exists(output_raw): os.remove(output_raw)
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **Introduce la URL para Crawling:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl, m))

def process_crawl(message):
    target = message.text.strip()
    archivo = f"crawl_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "🕸️ **Katana** rastreando (Modo Discreto + JS)...")
    # -kf -jc -d 5 ayudan a encontrar contenido en sitios modernos y evitar bloqueos
    subprocess.run(f"katana -u {target} -silent -kf -jc -d 5 -o {path}", shell=True, timeout=300)
    enviar_archivo_seguro(message.chat.id, path, f"🕸️ Crawl finalizado: `{target}`")

@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ (ej: http://site.com/FUZZ):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz, m))

def process_fuzz(message):
    url = message.text.strip()
    archivo = f"fuzz_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    wl = os.path.join(BASE_DIR, "common.txt")
    if not os.path.exists(wl):
        with open(wl, "w") as f: f.write("admin\nlogin\napi\n.env\n")
    bot.send_message(message.chat.id, "🔍 **FFUF** inyectando (Filtrando 404)...")
    subprocess.run(f"ffuf -u {url} -w {wl} -fc 404 -of md -o {path}", shell=True, timeout=300)
    enviar_archivo_seguro(message.chat.id, path, f"🔍 Fuzzing en `{url}`")

@bot.message_handler(commands=['archivos'])
def start_leaks(message):
    msg = bot.send_message(message.chat.id, "📂 **Introduce URL para buscar filtraciones:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_leaks, m))

def process_leaks(message):
    target = message.text.strip()
    archivo = f"leaks_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "📂 **Nuclei** buscando fugas (H-UserAgent)...")
    # -H añade un User-Agent real para evitar bloqueos del firewall
    subprocess.run(f"nuclei -u {target} -tags exposure,token,leak -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' -silent -o {path}", shell=True, timeout=400)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Filtraciones halladas en `{target}`")

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
        bot.send_message(message.chat.id, f"⚡ **Hydra** atacando {svc}...")
        subprocess.run(f"hydra -l {usr} -P {pwl} {ip} {svc} -o {path}", shell=True, timeout=300)
        enviar_archivo_seguro(message.chat.id, path, f"⚡ Brute Force en `{ip}`")
    except: bot.send_message(message.chat.id, "❌ Formato incorrecto.")

@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **Introduce URL para Escaneo CVE:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    archivo = f"audit_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "🛰️ **Nuclei** analizando (RL-10 + H-UserAgent)...")
    # -rl 10 limita la velocidad para no ser detectado tan fácil
    subprocess.run(f"nuclei -u {target} -rl 10 -H 'User-Agent: Mozilla/5.0' -silent -o {path}", shell=True, timeout=600)
    enviar_archivo_seguro(message.chat.id, path, f"📄 Auditoría finalizada: `{target}`")

@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **Introduce URL:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    archivo = f"dir_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    wl = os.path.join(BASE_DIR, "common.txt")
    bot.send_message(message.chat.id, f"🚀 **Gobuster** en `{url}`...")
    subprocess.run(f"gobuster dir -u {url} -w {wl} -b 404 -o {path} --no-error -n", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios de `{url}`")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v11.6 Pro**\n\n"
            "📡 `/subs` - Subdominios + IP\n"
            "🕸️ `/crawl` - Katana (JS + Stealth)\n"
            "🔍 `/fuzz` - FFUF (Filtro 404)\n"
            "📂 `/archivos` - Leaks (H-UserAgent)\n"
            "🔓 `/auditar` - CVE (RL-10)\n"
            "⚡ `/fuerza` - Hydra\n"
            "📂 `/dir` - Gobuster"
        )
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def router(m):
    if "sub" in m.text.lower(): start_subs(m)
    elif "audit" in m.text.lower(): start_audit(m)

print("🚀 Bugtin Bot v11.6 PRO - Parches Anti-Bloqueo Activos")
bot.polling(none_stop=True)

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
    """Verificación para Termux con espera de escritura y validación de contenido"""
    time.sleep(3) 
    if os.path.exists(ruta) and os.path.getsize(ruta) > 10:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            os.remove(ruta)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error de envío: {str(e)}")
    else:
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ El escaneo no generó resultados válidos o el archivo está vacío.")

# --- MOTOR DE SUBDOMINIOS + IP RESOLVER ---

@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ej: bbva.com):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs_with_ip, m))

def process_subs_with_ip(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output_raw = os.path.join(BASE_DIR, f"raw_{target}.txt")
    output_final = os.path.join(BASE_DIR, f"subs_resolved_{target}.txt")
    
    bot.send_message(chat_id, f"🔍 **Fase 1:** Extrayendo subdominios de `{target}`...")
    
    try:
        # Extracción de subdominios
        subprocess.run(f"subfinder -d {target} -silent -o {output_raw}", shell=True, timeout=180)
        
        # Si falla subfinder, creamos una lista básica de emergencia
        if not os.path.exists(output_raw) or os.path.getsize(output_raw) == 0:
            with open(output_raw, "w") as f:
                f.write(f"www.{target}\nmail.{target}\nftp.{target}\napi.{target}\n")

        bot.send_message(chat_id, f"📡 **Fase 2:** Resolviendo IPs para `{target}`...")
        
        with open(output_raw, "r") as f_in, open(output_final, "w") as f_out:
            subs_vistos = set()
            f_out.write(f"REPORTE DE SUBDOMINIOS E IPS - {target.upper()}\n")
            f_out.write("-" * 40 + "\n")
            
            for line in f_in:
                sub = line.strip()
                if not sub or sub in subs_vistos: continue
                subs_vistos.add(sub)
                
                # Usamos el comando 'host' para obtener la IP de forma rápida
                res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True)
                if "has address" in res.stdout:
                    # Extraer la IP usando regex
                    match = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                    ip_addr = match.group(1) if match else "Desconocida"
                    f_out.write(f"✅ {sub} -> [{ip_addr}]\n")
                else:
                    f_out.write(f"❌ {sub} -> [No responde / Sin IP]\n")

        enviar_archivo_seguro(chat_id, output_final, f"🏁 Recon completo para `{target}`")
        if os.path.exists(output_raw): os.remove(output_raw)
        
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en motor: {str(e)}")

# --- OTROS COMANDOS OPTIMIZADOS ---

@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **Introduce URL para Katana:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl, m))

def process_crawl(message):
    target = message.text.strip()
    archivo = f"crawl_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "🕸️ **Katana** analizando profundidad y JS...")
    # -jc extrae endpoints de archivos JavaScript
    subprocess.run(f"katana -u {target} -silent -jc -kf -o {path}", shell=True, timeout=300)
    enviar_archivo_seguro(message.chat.id, path, f"🕸️ Crawl finalizado: `{target}`")

@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **Introduce URL para Nuclei:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    archivo = f"audit_{int(time.time())}.txt"
    path = os.path.join(BASE_DIR, archivo)
    bot.send_message(message.chat.id, "🛰️ **Nuclei** escaneando vulnerabilidades...")
    # -rl 10 limita las peticiones para no saturar Termux ni ser bloqueado
    subprocess.run(f"nuclei -u {target} -rl 10 -silent -o {path}", shell=True, timeout=600)
    enviar_archivo_seguro(message.chat.id, path, f"📄 Auditoría CVE: `{target}`")

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
        with open(wl, "w") as f: f.write("admin\nlogin\napi\n.env\n.git\nconfig\n")
    bot.send_message(message.chat.id, "🔍 **FFUF** ejecutando (Filtro 404)...")
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
    bot.send_message(message.chat.id, f"🚀 **Gobuster** en `{url}`...")
    subprocess.run(f"gobuster dir -u {url} -w {wl} -b 404 -o {path} --no-error -n", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios: `{url}`")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v12.0 Pro**\n\n"
            "📡 `/subs` - Subdominios + **IP Resolve**\n"
            "🕸️ `/crawl` - Katana (JS/Endpoints)\n"
            "🔍 `/fuzz` - FFUF (Filtro 404)\n"
            "🔓 `/auditar` - Nuclei (Vulnerabilidades)\n"
            "📂 `/dir` - Gobuster (Directorios)"
        )
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

print("🚀 Bugtin Bot v12.0 - IP Resolver Engine Online")
bot.polling(none_stop=True)

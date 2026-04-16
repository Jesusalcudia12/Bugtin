import telebot
from telebot import types
import subprocess
import os
import time
import re
import threading

# --- CONFIGURACIÓN ---
# Token de acceso y ID de administrador para seguridad
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- UTILIDADES DE SISTEMA ---

def ejecutar_en_hilo(func, message):
    """Ejecuta funciones en segundo plano para no congelar el bot"""
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

def enviar_archivo_seguro(chat_id, ruta, caption):
    """Verifica que el archivo exista y tenga contenido antes de enviarlo"""
    # Espera hasta 10 segundos a que el proceso de escritura de disco termine
    for _ in range(10):
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            break
        time.sleep(1)

    if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
        try:
            with open(ruta, "rb") as f:
                bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
            # Eliminar archivo local después de enviarlo para ahorrar espacio
            os.remove(ruta) 
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error al enviar el reporte: {str(e)}")
    else:
        # Si el archivo existe pero está vacío, se borra y se avisa al usuario
        if os.path.exists(ruta): os.remove(ruta)
        bot.send_message(chat_id, "⚠️ El escaneo no generó resultados o el archivo está vacío.")

# --- 1. SUBS (Subdominios Instantáneos) ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ej: google.com):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs, m))

def process_subs(message):
    target = message.text.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    path = os.path.join(BASE_DIR, f"subs_{target}.txt")
    bot.send_message(message.chat.id, f"📡 **Extrayendo subdominios para `{target}`...**")
    
    try:
        # Modo rápido: Obtiene la lista y la guarda sin resolver IPs individuales
        res = subprocess.run(f"subfinder -d {target} -silent", shell=True, capture_output=True, text=True)
        subdominios = res.stdout.splitlines()
        
        if not subdominios:
            bot.send_message(message.chat.id, "⚠️ No se encontraron subdominios públicos.")
            return

        with open(path, "w") as f:
            f.write(f"--- LISTA DE SUBDOMINIOS: {target.upper()} ---\n\n")
            for sub in subdominios:
                if sub:
                    # Formato optimizado para visualización rápida
                    f.write(f"✅ {sub.ljust(40)} | [IP: ---]\n")
        
        enviar_archivo_seguro(message.chat.id, path, f"🏁 Lista de subdominios: `{target}`")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error en SUBS: {str(e)}")

# --- 2. APK (Análisis de Secretos) ---
@bot.message_handler(commands=['apk'])
def start_apk(message):
    msg = bot.send_message(message.chat.id, "📱 **Sube el archivo .apk:**")
    bot.register_next_step_handler(msg, process_apk_file)

def process_apk_file(message):
    if not message.document or not message.document.file_name.lower().endswith('.apk'):
        bot.send_message(message.chat.id, "❌ Error: Debes subir un archivo con extensión .apk")
        return
    
    chat_id = message.chat.id
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    local_path = os.path.join(BASE_DIR, message.document.file_name)
    report = os.path.join(BASE_DIR, f"secretos_{message.document.file_name}.txt")
    
    with open(local_path, 'wb') as f: f.write(downloaded)
    bot.send_message(chat_id, "⚙️ **Analizando binario APK...** (Extrayendo URLs e IPs)")
    
    try:
        # Regex corregido para evitar SyntaxWarning
        regex = r'http://|https://|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|AIza[0-9A-Za-z-_]{35}'
        subprocess.run(f"strings '{local_path}' | grep -E '{regex}' > '{report}'", shell=True)
        
        if os.path.exists(local_path): os.remove(local_path)
        enviar_archivo_seguro(chat_id, report, f"📱 Análisis de secretos: `{message.document.file_name}`")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error en APK: {str(e)}")

# --- 3. FUERZA (Hydra) ---
@bot.message_handler(commands=['fuerza'])
def start_hydra(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: [IP] [Servicio] [Usuario]**\nEj: `1.1.1.1 ssh admin`")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_hydra, m))

def process_hydra(message):
    try:
        parts = message.text.split()
        if len(parts) < 3: raise ValueError
        ip, svc, usr = parts[0], parts[1], parts[2]
        report = os.path.join(BASE_DIR, f"hydra_{ip}.txt")
        
        bot.send_message(message.chat.id, f"⚡ Atacando `{svc}` en `{ip}` con usuario `{usr}`...")
        # Nota: Requiere archivo pass.txt en la misma carpeta
        subprocess.run(f"hydra -l {usr} -P pass.txt {ip} {svc} -o {report}", shell=True)
        enviar_archivo_seguro(message.chat.id, report, f"⚡ Reporte Brute Force: `{ip}`")
    except:
        bot.send_message(message.chat.id, "❌ Formato incorrecto. Usa: `IP Servicio Usuario`")

# --- 4. CRAWL (Katana) ---
@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **URL para Crawling (Katana):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl, m))

def process_crawl(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, f"crawl_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🕸️ Katana mapeando endpoints y archivos JS...")
    subprocess.run(f"katana -u {target} -silent -jc -kf -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🕸️ Crawl finalizado: `{target}`")

# --- 5. FUZZ (FFUF) ---
@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con palabra FUZZ:**\nEj: `http://site.com/FUZZ`")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz, m))

def process_fuzz(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"fuzz_{int(time.time())}.txt")
    # Usa common.txt como diccionario por defecto
    bot.send_message(message.chat.id, "🔍 FFUF buscando directorios ocultos...")
    subprocess.run(f"ffuf -u {url} -w common.txt -fc 404 -of md -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"🔍 Fuzzing finalizado: `{url}`")

# --- 6. AUDITAR (Nuclei) ---
@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **URL para Auditoría (Nuclei):**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    path = os.path.join(BASE_DIR, f"audit_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🛰️ Nuclei escaneando vulnerabilidades conocidas...")
    subprocess.run(f"nuclei -u {target} -rl 10 -silent -o {path}", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📄 Vulnerabilidades detectadas: `{target}`")

# --- 7. DIR (Gobuster) ---
@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para Gobuster:**")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    path = os.path.join(BASE_DIR, f"dir_{int(time.time())}.txt")
    bot.send_message(message.chat.id, "🚀 Gobuster buscando rutas y carpetas...")
    subprocess.run(f"gobuster dir -u {url} -w common.txt -b 404 -o {path} --no-error -n", shell=True)
    enviar_archivo_seguro(message.chat.id, path, f"📂 Directorios hallados: `{url}`")

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_txt = (
            "🤖 **Bugtin Bot v14.3 Speed Edition**\n\n"
            "📡 `/subs` - Subdominios (Instantáneo)\n"
            "📱 `/apk` - Análisis estático de Apps\n"
            "⚡ `/fuerza` - Hydra (Brute Force)\n"
            "🕸️ `/crawl` - Katana (Endpoints)\n"
            "🔍 `/fuzz` - FFUF (Fuzzing)\n"
            "🔓 `/auditar` - Nuclei (Vulnerabilidades)\n"
            "📂 `/dir` - Gobuster (Directorios)"
        )
        bot.send_message(message.chat.id, help_txt, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bugtin Bot v14.3 Online - Suite de seguridad cargada")
    bot.polling(none_stop=True)

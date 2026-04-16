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

# --- UTILIDAD: EJECUCIÓN EN SEGUNDO PLANO ---
def ejecutar_en_hilo(func, message):
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

# --- MOTOR DE INTELIGENCIA V7.5 ---
def motor_inteligencia(archivo_reporte):
    analisis = "🧠 **ANÁLISIS DE SEGURIDAD V7.5**\n"
    prioridad = "🟢 INFO"
    hallazgos = []
    
    try:
        if not os.path.exists(archivo_reporte): return "⚠️ Error: Reporte no generado."
        with open(archivo_reporte, "r", errors='ignore') as f:
            content = f.read().lower()

        if "sql syntax" in content or "mysql_fetch" in content:
            hallazgos.append("💉 Posible Inyección SQL")
            prioridad = "🔴 CRÍTICA"
        if "<script>" in content or "alert(" in content:
            hallazgos.append("🧪 Posible XSS detectado")
            prioridad = "🟠 ALTA"
        if "root:x:0:0" in content:
            hallazgos.append("📂 Filtración de /etc/passwd")
            prioridad = "🔴 CRÍTICA"
        
        if hallazgos:
            analisis += f"Nivel: {prioridad}\n\n" + "\n".join(hallazgos)
        else:
            analisis += "✅ No se hallaron patrones comunes de vulnerabilidad."
    except Exception as e:
        analisis = f"⚠️ Error en análisis: {str(e)}"
    
    return analisis

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Subdominios", "📂 Directorios")
        markup.add("🔍 Fuzzing", "🔓 Auditoría")
        markup.add("⚡ Hydra")
        
        welcome_text = (
            "🤖 **Bugtin Bot v7.5**\n\n"
            "📡 `/subs` - Recon de subdominios e IPs\n"
            "📂 `/dir` - Escaneo de directorios (Gobuster)\n"
            "🔍 `/fuzz` - Fuzzing de parámetros\n"
            "🔓 `/auditar` - Escaneo Nuclei + IA\n"
            "⚡ `/fuerza` - Fuerza bruta Hydra"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- COMANDO: SUBDOMINIOS (LÓGICA V7.5) ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs, m))

def process_subs(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output = f"subs_{target}.txt"
    
    bot.send_message(chat_id, f"🔎 Buscando subdominios para `{target}`...")
    
    try:
        # Comando clásico de la v7.5
        subprocess.run(f"subfinder -d {target} -silent -o {output}", shell=True, timeout=120)
        
        if os.path.exists(output) and os.path.getsize(output) > 0:
            final_output = f"final_{target}.txt"
            with open(output, "r") as f_in, open(final_output, "w") as f_out:
                for line in f_in:
                    sub = line.strip()
                    # Resolución de IP mediante ping (Formato v7.5)
                    res = subprocess.run(f"ping -c 1 {sub} | head -n 1", shell=True, capture_output=True, text=True)
                    ip = re.search(r'\((.*?)\)', res.stdout)
                    ip_addr = ip.group(1) if ip else "0.0.0.0"
                    f_out.write(f"{sub} - {ip_addr}\n")
            
            with open(final_output, "rb") as f:
                bot.send_document(chat_id, f, caption=f"✅ Subdominios de `{target}`")
            
            os.remove(output)
            os.remove(final_output)
        else:
            bot.send_message(chat_id, "❌ No se encontraron resultados.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: DIRECTORIOS (GOBUSTER) ---
@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para Gobuster:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    output = "dirs.txt"
    bot.send_message(message.chat.id, "🚀 Iniciando Gobuster...")
    try:
        # Usamos common.txt como wordlist por defecto en v7.5
        subprocess.run(f"gobuster dir -u {url} -w common.txt -t 20 -o {output} -n -e", shell=True)
        if os.path.exists(output):
            with open(output, "rb") as f:
                bot.send_document(message.chat.id, f, caption=f"📂 Directorios: {url}")
            os.remove(output)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- COMANDO: FUZZING ---
@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz, m))

def process_fuzz(message):
    url = message.text.strip()
    output = "fuzz.txt"
    try:
        subprocess.run(f"ffuf -u {url} -w payloads.txt -o {output}", shell=True)
        if os.path.exists(output):
            with open(output, "rb") as f:
                bot.send_document(message.chat.id, f)
            os.remove(output)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- COMANDO: AUDITORÍA ---
@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **URL para Nuclei:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    output = "audit.txt"
    bot.send_message(message.chat.id, "🛰️ Escaneando con Nuclei...")
    try:
        subprocess.run(f"nuclei -u {target} -o {output} -silent", shell=True)
        if os.path.exists(output):
            bot.send_message(message.chat.id, motor_inteligencia(output), parse_mode="Markdown")
            with open(output, "rb") as f:
                bot.send_document(message.chat.id, f)
            os.remove(output)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- COMANDO: HYDRA ---
@bot.message_handler(commands=['fuerza'])
def start_hydra(message):
    msg = bot.send_message(message.chat.id, "⚡ **Formato: IP Servicio Usuario**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_hydra, m))

def process_hydra(message):
    try:
        data = message.text.split()
        ip, svc, user = data[0], data[1], data[2]
        subprocess.run(f"hydra -l {user} -P pass.txt {ip} {svc} -o res.txt", shell=True)
        if os.path.exists("res.txt"):
            with open("res.txt", "r") as f:
                bot.send_message(message.chat.id, f"🎯 **Hallazgo:**\n{f.read()}")
            os.remove("res.txt")
    except:
        bot.send_message(message.chat.id, "❌ Error en Hydra.")

# --- ROUTER DE BOTONES ---
@bot.message_handler(func=lambda m: True)
def router(m):
    if m.text == "📡 Subdominios": start_subs(m)
    elif m.text == "📂 Directorios": start_dir(m)
    elif m.text == "🔍 Fuzzing": start_fuzz(m)
    elif m.text == "🔓 Auditoría": start_audit(m)
    elif m.text == "⚡ Hydra": start_hydra(m)

print("🚀 Bugtin Bot v7.5 ONLINE - Estable")
bot.polling(none_stop=True)

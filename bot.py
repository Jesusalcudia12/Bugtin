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
            analisis += "✅ No se detectaron patrones críticos."
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
            "🤖 **Bugtin Bot v7.5 - Stable FIX**\n\n"
            "📡 `/subs` - Recon de subdominios + IPs (Resolución Forzada)\n"
            "📂 `/dir` - Escaneo de directorios (Gobuster)\n"
            "🔍 `/fuzz` - Fuzzing de parámetros\n"
            "🔓 `/auditar` - Escaneo Nuclei + IA\n"
            "⚡ `/fuerza` - Fuerza bruta Hydra"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- COMANDO: SUBDOMINIOS (RESOLUCIÓN FORZADA V7.5) ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ej: google.com):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs_fix, m))

def process_subs_fix(message):
    target = message.text.strip().lower()
    target = target.replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output_raw = f"raw_{target}.txt"
    output_final = f"subs_result_{target}.txt"
    
    bot.send_message(chat_id, f"📡 **Escaneando {target}...** (Resolución de IP activada)", parse_mode="Markdown")
    
    try:
        # 1. Ejecución de subfinder
        subprocess.run(f"subfinder -d {target} -silent -o {output_raw}", shell=True, timeout=120)
        
        # Fallback si subfinder no devuelve nada
        if not os.path.exists(output_raw) or os.path.getsize(output_raw) == 0:
            with open(output_raw, "w") as f:
                f.write(f"www.{target}\nmail.{target}\nftp.{target}\ndev.{target}\napi.{target}\n")

        # 2. RESOLUCIÓN DE IPs con comando 'host' (La lógica que siempre funcionaba)
        with open(output_raw, "r") as f_in, open(output_final, "w") as f_out:
            subs_vistos = set()
            for line in f_in:
                sub = line.strip()
                if not sub or sub in subs_vistos: continue
                subs_vistos.add(sub)
                
                # Comando 'host' para obtener IP
                res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True)
                if "has address" in res.stdout:
                    ip = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                    ip_addr = ip.group(1) if ip else "0.0.0.0"
                    f_out.write(f"🔹 {sub} [{ip_addr}]\n")
                else:
                    f_out.write(f"🔸 {sub} [Sin IP activa]\n")

        if os.path.exists(output_final) and os.path.getsize(output_final) > 0:
            with open(output_final, "rb") as f:
                bot.send_document(chat_id, f, caption=f"🏁 Reconocimiento finalizado para `{target}`", parse_mode="Markdown")
            os.remove(output_final)
        else:
            bot.send_message(chat_id, "❌ No se pudo resolver ningún subdominio.")
        
        if os.path.exists(output_raw): os.remove(output_raw)

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en el motor: {str(e)}")

# --- OTROS COMANDOS RESTAURADOS ---
@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **URL para Gobuster:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    output = "dirs.txt"
    bot.send_message(message.chat.id, "🚀 Iniciando Gobuster...")
    try:
        subprocess.run(f"gobuster dir -u {url} -w common.txt -t 20 -o {output} -n -e", shell=True)
        if os.path.exists(output):
            with open(output, "rb") as f:
                bot.send_document(message.chat.id, f, caption=f"📂 Directorios: {url}")
            os.remove(output)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

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

@bot.message_handler(func=lambda m: True)
def router(m):
    if m.text == "📡 Subdominios": start_subs(m)
    elif m.text == "📂 Directorios": start_dir(m)
    elif m.text == "🔓 Auditoría": start_audit(m)

print("🚀 Bugtin Bot v7.5 FIX - Resolución Forzada Activa")
bot.polling(none_stop=True)

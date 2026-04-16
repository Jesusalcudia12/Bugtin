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
            "🤖 **Bugtin Bot v6.7 - Reportes Directos**\n\n"
            "📡 `/subs` - Reconocimiento de subdominios.\n"
            "🔓 `/archivos` - Escaneo de vulnerabilidades.\n\n"
            "📥 *Los hallazgos de Nuclei y Gobuster se envían directamente aquí.*"
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- FUNCIONES DE APOYO ---
def run_command(command):
    try:
        # Ejecutamos con shell=True y capturamos errores silenciosamente
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
        # 1. Subfinder (Modo silencioso)
        run_command(f"subfinder -d {target} -o subs_pasivos.txt -silent")

        # 2. Gobuster DNS (Sintaxis compatible y lenta para evitar timeout)
        if os.path.exists("common.txt"):
            run_command(f"gobuster dns --domain {target} --wordlist common.txt --delay 100ms -t 10 --quiet --output res_esp.txt")
        
        if os.path.exists("tecnico.txt"):
            run_command(f"gobuster dns --domain {target} --wordlist tecnico.txt --delay 100ms -t 10 --quiet --output res_tec.txt")

        # Unificar resultados
        run_command("touch total_subs.txt")
        for f in ["subs_pasivos.txt", "res_esp.txt", "res_tec.txt"]:
            if os.path.exists(f) and os.path.getsize(f) > 0:
                run_command(f"cat {f} >> total_subs.txt")
        
        run_command("sort -u total_subs.txt -o total_subs.txt")

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Lista de subdominios: {target}")
        else:
            bot.send_message(chat_id, "❌ No se encontraron subdominios.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- LÓGICA: ARCHIVOS/VULNS (REPORTE AL BOT) ---
@bot.message_handler(commands=['archivos'])
def start_archivos(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Escribe el subdominio a escanear:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_vulns_step)

def process_vulns_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output_file = f"reporte_{target}.txt"
    
    bot.send_message(chat_id, f"🔍 Escaneando `{target}`... Los resultados aparecerán aquí.", parse_mode="Markdown")
    
    try:
        # 1. Nuclei (Envía salida al archivo y se mantiene en silencio en terminal)
        run_command(f"nuclei -u {target} -tags exposure,cve,critical,panel -o {output_file} -silent")
        
        # 2. Gobuster Dir para rutas críticas
        for l in ["api-routes.txt", "logins.txt"]:
            if os.path.exists(l):
                temp_dir = "temp_dir.txt"
                run_command(f"gobuster dir --url {target} --wordlist {l} --delay 200ms -t 5 --quiet --output {temp_dir}")
                if os.path.exists(temp_dir):
                    run_command(f"cat {temp_dir} >> {output_file}")
                    run_command(f"rm {temp_dir}")

        # 3. Enviar el reporte final al chat de Telegram
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            # Obtener una pequeña vista previa de los primeros hallazgos
            with open(output_file, "r") as f:
                content = f.readlines()
                preview = "".join(content[:5]) # Primeras 5 líneas

            bot.send_message(chat_id, f"✅ **Escaneo completado**\n\n**Hallazgos detectados:**\n`{preview}...`", parse_mode="Markdown")
            
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"📄 Reporte completo: {target}")
        else:
            bot.send_message(chat_id, f"✅ No se encontraron fallos críticos ni archivos expuestos en `{target}`.")
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error durante el escaneo: {str(e)}")

# --- MANEJADORES DE BOTONES ---
@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def b1(m): start_subs(m)

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def b2(m): start_archivos(m)

print("🚀 Bugtin Bot v6.7 Online. Todo listo.")
bot.polling()

import telebot
from telebot import types
import subprocess
import os

# --- CONFIGURACIÓN ---
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)

# --- MENÚ PRINCIPAL ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = (
            "🤖 **Bugtin Bot v6.3 Pro**\n\n"
            "📡 `/subs` - Iniciar reconocimiento de subdominios.\n"
            "🔓 `/archivos` - Buscar filtraciones y accesos.\n\n"
            "💡 El bot te guiará paso a paso para evitar errores en la terminal."
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- LÓGICA DE PREGUNTAS INTERACTIVAS ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Paso 1:** Escribe el dominio objetivo (ej: `bbva.com`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_subdomains_step)

def process_subdomains_step(message):
    target = message.text.strip().lower()
    if "." not in target:
        bot.send_message(message.chat.id, "❌ Dominio inválido. Intenta de nuevo con `/subs`.")
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 Procesando `{target}`... Por favor, espera.", parse_mode="Markdown")
    
    # Limpieza
    subprocess.run("rm -f total_subs.txt res_esp.txt res_tec.txt subs_pasivos.txt", shell=True)

    try:
        # 1. Subfinder (Suele funcionar siempre bien en Termux)
        subprocess.run(f"subfinder -d {target} -o subs_pasivos.txt", shell=True)

        # 2. Gobuster DNS con Sintaxis Alternativa (Basada en tu error de parseo)
        # Probamos una sintaxis sin el flag -d pegado al valor si el anterior falló
        if os.path.exists("common.txt"):
            # Intentamos la sintaxis que Gobuster sugiere en su ayuda (de tu captura)
            cmd_esp = f"gobuster dns --domain {target} --wordlist common.txt --quiet --output res_esp.txt"
            subprocess.run(cmd_esp, shell=True)
        
        if os.path.exists("tecnico.txt"):
            cmd_tec = f"gobuster dns --domain {target} --wordlist tecnico.txt --quiet --output res_tec.txt"
            subprocess.run(cmd_tec, shell=True)

        # Consolidación de archivos
        subprocess.run("touch total_subs.txt", shell=True)
        for f in ["subs_pasivos.txt", "res_esp.txt", "res_tec.txt"]:
            if os.path.exists(f) and os.path.getsize(f) > 0:
                subprocess.run(f"cat {f} >> total_subs.txt", shell=True)
        
        subprocess.run("sort -u total_subs.txt -o total_subs.txt", shell=True)

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Resultados para: {target}")
        else:
            bot.send_message(chat_id, f"⚠️ No se generaron resultados para {target}. Revisa si los diccionarios tienen contenido.")
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error crítico: {str(e)}")

# --- LÓGICA DE ARCHIVOS ---
@bot.message_handler(commands=['archivos'])
def start_archivos(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Paso 1:** Escribe el dominio para buscar archivos (ej: `bbva.com`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_vulns_step)

def process_vulns_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output_file = "vulnerabilidades.txt"
    if os.path.exists(output_file): os.remove(output_file)

    bot.send_message(chat_id, f"🔍 Escaneando `{target}` con Nuclei y Gobuster Dir...", parse_mode="Markdown")
    try:
        # Nuclei
        subprocess.run(f"nuclei -u {target} -tags exposure,backup,config,db -o {output_file} -silent", shell=True)
        
        # Gobuster Dir (Sintaxis larga para evitar errores de parseo)
        for l in ["api-routes.txt", "logins.txt"]:
            if os.path.exists(l):
                subprocess.run(f"gobuster dir --url {target} --wordlist {l} --quiet --output temp.txt", shell=True)
                if os.path.exists("temp.txt"):
                    subprocess.run(f"cat temp.txt >> {output_file}", shell=True)
                    os.remove("temp.txt")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ Hallazgos en {target}")
        else:
            bot.send_message(chat_id, f"✅ No se encontraron vulnerabilidades expuestas en {target}.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- BOTONES ---
@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def btn_s(m): start_subs(m)

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def btn_a(m): start_archivos(m)

print("🚀 Bugtin Bot v6.3 Online.")
bot.polling()

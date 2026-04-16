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
            "🤖 **Panel de Control Bugtin v5.9 Pro**\n\n"
            "📡 `/subs [dominio]`\n"
            "Busca subdominios (Pasiva + Español + Técnica).\n\n"
            "🔓 `/archivos [dominio]`\n"
            "Busca filtraciones, paneles y **formularios de Login**.\n"
            "Usa: `Nuclei`, `api_routes.txt` y `logins.txt`.\n\n"
            "💡 **Ejemplo:** `/archivos objetivo.com`"
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- COMANDOS DIRECTOS ---
@bot.message_handler(commands=['subs'])
def cmd_subs(message):
    args = message.text.split()
    if len(args) > 1: process_subdomains_only(message, args[1])
    else: bot.send_message(message.chat.id, "⌨️ Uso: `/subs dominio.com`", parse_mode="Markdown")

@bot.message_handler(commands=['archivos'])
def cmd_archivos(message):
    args = message.text.split()
    if len(args) > 1: process_vulns(message, args[1])
    else: bot.send_message(message.chat.id, "⌨️ Uso: `/archivos dominio.com`", parse_mode="Markdown")

# --- BOTONES ---
@bot.message_handler(func=lambda message: message.text in ["📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos"])
def handle_buttons(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        text = "🎯 Envíame el dominio:"
        msg = bot.send_message(message.chat.id, text)
        if message.text == "📡 Solo Subdominios":
            bot.register_next_step_handler(msg, lambda m: process_subdomains_only(m, m.text))
        else:
            bot.register_next_step_handler(msg, lambda m: process_vulns(m, m.text))

# --- LÓGICA: PROCESAR VULNERABILIDADES + LOGINS ---
def process_vulns(message, target_raw):
    target = target_raw.strip().lower()
    chat_id = message.chat.id
    output_file = "vulnerabilidades.txt"
    
    bot.send_message(chat_id, f"🔍 Escaneando `{target}`...\n(Nuclei + Paneles + Logins)", parse_mode="Markdown")
    if os.path.exists(output_file): os.remove(output_file)

    try:
        # 1. Nuclei (Filtraciones)
        subprocess.run(f"nuclei -u {target} -tags exposure,backup,config,db -o {output_file} -silent", shell=True)
        
        # 2. Gobuster Dir con api_routes.txt (Consul/Paneles)
        subprocess.run(f"gobuster dir -u {target} -w api_routes.txt --quiet -o extra.txt", shell=True)
        if os.path.exists("extra.txt"):
            subprocess.run(f"cat extra.txt >> {output_file}", shell=True)
            os.remove("extra.txt")

        # 3. NUEVO: Gobuster Dir con logins.txt (Páginas de acceso)
        subprocess.run(f"gobuster dir -u {target} -w logins.txt --quiet -o log_found.txt", shell=True)
        if os.path.exists("log_found.txt"):
            subprocess.run(f"echo '\n--- PÁGINAS DE LOGIN ENCONTRADAS ---' >> {output_file}", shell=True)
            subprocess.run(f"cat log_found.txt >> {output_file}", shell=True)
            os.remove("log_found.txt")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ Hallazgos en {target}")
        else:
            bot.send_message(chat_id, f"✅ No se hallaron rutas críticas en {target}.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- LÓGICA: PROCESAR SUBDOMINIOS ---
def process_subdomains_only(message, target_raw):
    target = target_raw.strip().lower()
    chat_id = message.chat.id
    subprocess.run("rm -f total_subs.txt res_esp.txt res_tec.txt subs_pasivos.txt", shell=True)
    bot.send_message(chat_id, f"🚀 Búsqueda profunda en `{target}`...", parse_mode="Markdown")

    try:
        subprocess.run(f"subfinder -d {target} -o subs_pasivos.txt", shell=True)
        subprocess.run(f"gobuster dns -d {target} -w common.txt --quiet -o res_esp.txt", shell=True)
        subprocess.run(f"gobuster dns -d {target} -w tecnico.txt --quiet -o res_tec.txt", shell=True)
        subprocess.run("cat subs_pasivos.txt res_esp.txt res_tec.txt | sort -u > total_subs.txt", shell=True)

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Subdominios de {target}")
        else:
            bot.send_message(chat_id, "❌ No se encontraron resultados.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- INICIO ---
print("🚀 Bugtin Bot v5.9 Online.")
bot.polling()

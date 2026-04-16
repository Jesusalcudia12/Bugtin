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
            "🤖 **Bugtin Bot v6.4 Pro**\n\n"
            "📡 `/subs` - Fase 1: Encontrar Subdominios (Recon).\n"
            "🔓 `/archivos` - Fase 2: Buscar Vulnerabilidades (Scan).\n\n"
            "💡 Ya tienes subdominios, ahora usa `/archivos` para ver cuáles son vulnerables."
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- LÓGICA DE SUBDOMINIOS ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Fase Recon:** Escribe el dominio (ej: `bbva.com`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_subdomains_step)

def process_subdomains_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 Extrayendo subdominios de `{target}`...", parse_mode="Markdown")
    
    subprocess.run("rm -f total_subs.txt res_esp.txt res_tec.txt subs_pasivos.txt", shell=True)

    try:
        # Subfinder
        subprocess.run(f"subfinder -d {target} -o subs_pasivos.txt", shell=True)

        # Gobuster DNS (Sintaxis compatible con tu Termux)
        if os.path.exists("common.txt"):
            subprocess.run(f"gobuster dns --domain {target} --wordlist common.txt --quiet --output res_esp.txt", shell=True)
        
        if os.path.exists("tecnico.txt"):
            subprocess.run(f"gobuster dns --domain {target} --wordlist tecnico.txt --quiet --output res_tec.txt", shell=True)

        # Unificar
        subprocess.run("touch total_subs.txt", shell=True)
        for f in ["subs_pasivos.txt", "res_esp.txt", "res_tec.txt"]:
            if os.path.exists(f):
                subprocess.run(f"cat {f} >> total_subs.txt", shell=True)
        
        subprocess.run("sort -u total_subs.txt -o total_subs.txt", shell=True)

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Lista de Subdominios de {target}\n\nUsa `/archivos` con uno de estos para buscar fallos.")
        else:
            bot.send_message(chat_id, "❌ No se hallaron subdominios.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- LÓGICA DE VULNERABILIDADES (LO QUE NECESITAS AHORA) ---
@bot.message_handler(commands=['archivos'])
def start_archivos(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Fase Escaneo:** Escribe el subdominio específico (ej: `dev.bbva.com` o el dominio principal):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_vulns_step)

def process_vulns_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output_file = f"reporte_{target}.txt"
    
    bot.send_message(chat_id, f"🔍 Buscando vulnerabilidades en `{target}`...\nEsto puede tardar unos minutos.", parse_mode="Markdown")
    
    try:
        # 1. Nuclei (Busca fallos conocidos: CVEs, Misconfigurations)
        subprocess.run(f"nuclei -u {target} -tags exposure,cve,critical,db,panel -o {output_file} -silent", shell=True)
        
        # 2. Gobuster Dir (Busca archivos ocultos y logins)
        for l in ["api-routes.txt", "logins.txt"]:
            if os.path.exists(l):
                # Sintaxis compatible para búsqueda de directorios
                subprocess.run(f"gobuster dir --url {target} --wordlist {l} --quiet --output temp_dir.txt", shell=True)
                if os.path.exists("temp_dir.txt"):
                    subprocess.run(f"cat temp_dir.txt >> {output_file}", shell=True)
                    os.remove("temp_dir.txt")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ Reporte de Vulnerabilidades: {target}")
        else:
            bot.send_message(chat_id, f"✅ No se encontraron fallos evidentes en `{target}`.")
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en escaneo: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def btn_s(m): start_subs(m)

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def btn_a(m): start_archivos(m)

print("🚀 Bugtin Bot v6.4 Online.")
bot.polling()

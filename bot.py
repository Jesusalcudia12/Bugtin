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
            "🤖 **Panel de Control Bugtin v6.2 Pro**\n\n"
            "📡 `/subs [dominio]`\n"
            "Busca subdominios (Pasiva + Español + Técnica).\n\n"
            "🔓 `/archivos [dominio]`\n"
            "Busca filtraciones, paneles y **formularios de Login**.\n\n"
            "💡 **Ejemplo:** `/subs google.com`"
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- LÓGICA CORE: SUBDOMINIOS (FIXED FOR TERMUX) ---
def process_subdomains_only(message, target_raw):
    target = target_raw.strip().lower()
    chat_id = message.chat.id
    
    # Limpieza previa
    subprocess.run("rm -f total_subs.txt res_esp.txt res_tec.txt subs_pasivos.txt", shell=True)
    bot.send_message(chat_id, f"🚀 Iniciando reconocimiento en `{target}`...", parse_mode="Markdown")

    try:
        # 1. Subfinder (Pasivo)
        subprocess.run(f"subfinder -d {target} -o subs_pasivos.txt", shell=True)

        # 2. Gobuster DNS (Sintaxis simplificada para evitar parse error)
        # Probamos enviando los flags de forma más directa
        if os.path.exists("common.txt"):
            cmd_esp = f"gobuster dns -d {target} -w common.txt --quiet -o res_esp.txt"
            subprocess.run(cmd_esp, shell=True)
        
        if os.path.exists("tecnico.txt"):
            cmd_tec = f"gobuster dns -d {target} -w tecnico.txt --quiet -o res_tec.txt"
            subprocess.run(cmd_tec, shell=True)

        # Unificar resultados de forma segura
        subprocess.run("touch total_subs.txt", shell=True)
        files_to_merge = ["subs_pasivos.txt", "res_esp.txt", "res_tec.txt"]
        for f in files_to_merge:
            if os.path.exists(f) and os.path.getsize(f) > 0:
                subprocess.run(f"cat {f} >> total_subs.txt", shell=True)
        
        # Ordenar y limpiar
        subprocess.run("sort -u total_subs.txt -o total_subs.txt", shell=True)

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Reporte de subdominios: {target}")
        else:
            bot.send_message(chat_id, "❌ No se encontraron subdominios activos o hubo un error de red.")
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en ejecución: {str(e)}")

# --- LÓGICA CORE: VULNERABILIDADES ---
def process_vulns(message, target_raw):
    target = target_raw.strip().lower()
    chat_id = message.chat.id
    output_file = "vulnerabilidades.txt"
    if os.path.exists(output_file): os.remove(output_file)

    bot.send_message(chat_id, f"🔓 Escaneando vulnerabilidades en `{target}`...", parse_mode="Markdown")
    try:
        subprocess.run(f"nuclei -u {target} -tags exposure,backup,config,db -o {output_file} -silent", shell=True)
        
        lists = ["api-routes.txt", "logins.txt"]
        for l in lists:
            if os.path.exists(l):
                subprocess.run(f"gobuster dir -u {target} -w {l} --quiet -o temp.txt", shell=True)
                if os.path.exists("temp.txt"):
                    subprocess.run(f"cat temp.txt >> {output_file}", shell=True)
                    os.remove("temp.txt")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ Hallazgos críticos en {target}")
        else:
            bot.send_message(chat_id, f"✅ Objetivo limpio de archivos críticos.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error: {str(e)}")

# --- MANEJADORES DE MENÚ Y COMANDOS ---
@bot.message_handler(commands=['subs'])
def h_subs(m):
    args = m.text.split()
    if len(args) > 1: process_subdomains_only(m, args[1])
    else: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 Dominio:"), lambda x: process_subdomains_only(x, x.text))

@bot.message_handler(commands=['archivos'])
def h_arch(m):
    args = m.text.split()
    if len(args) > 1: process_vulns(m, args[1])
    else: bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 Dominio:"), lambda x: process_vulns(x, x.text))

@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def btn_subs(m): bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 Dominio:"), lambda x: process_subdomains_only(x, x.text))

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def btn_arch(m): bot.register_next_step_handler(bot.send_message(m.chat.id, "🎯 Dominio:"), lambda x: process_vulns(x, x.text))

print("🚀 Bugtin Bot v6.2 Online.")
bot.polling()

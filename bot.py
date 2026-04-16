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
            "🤖 **Bugtin Bot v6.5 - Advanced Hunter**\n\n"
            "📡 `/subs` -> Fase 1: Encontrar Subdominios (Recon).\n"
            "🔓 `/archivos` -> Fase 2: Escaneo Crítico (RCE, SQLi, XSS, Paneles).\n\n"
            "💡 **Prioridad:** Buscando fallos de alto impacto (OWASP Top 10)."
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📡 Solo Subdominios", "🔓 Buscar Archivos Expuestos")
        bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode="Markdown")

# --- LÓGICA DE SUBDOMINIOS (FASE 1) ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Fase Recon:** Escribe el dominio (ej: `bbva.com`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_subdomains_step)

def process_subdomains_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 Extrayendo subdominios de `{target}`...", parse_mode="Markdown")
    
    # Limpieza de archivos temporales de sesiones anteriores
    subprocess.run("rm -f total_subs.txt res_esp.txt res_tec.txt subs_pasivos.txt", shell=True)

    try:
        # Subfinder para búsqueda pasiva
        subprocess.run(f"subfinder -d {target} -o subs_pasivos.txt", shell=True)

        # Gobuster DNS con sintaxis compatible para Termux (--domain y --wordlist)
        if os.path.exists("common.txt"):
            subprocess.run(f"gobuster dns --domain {target} --wordlist common.txt --quiet --output res_esp.txt", shell=True)
        
        if os.path.exists("tecnico.txt"):
            subprocess.run(f"gobuster dns --domain {target} --wordlist tecnico.txt --quiet --output res_tec.txt", shell=True)

        # Unificar resultados evitando errores de archivos inexistentes
        subprocess.run("touch total_subs.txt", shell=True)
        for f in ["subs_pasivos.txt", "res_esp.txt", "res_tec.txt"]:
            if os.path.exists(f) and os.path.getsize(f) > 0:
                subprocess.run(f"cat {f} >> total_subs.txt", shell=True)
        
        # Ordenar por orden alfabético y eliminar duplicados
        subprocess.run("sort -u total_subs.txt -o total_subs.txt", shell=True)

        if os.path.exists("total_subs.txt") and os.path.getsize("total_subs.txt") > 0:
            with open("total_subs.txt", "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"🏁 Lista de Subdominios: {target}\n\nUsa `/archivos` con uno de estos para buscar vulnerabilidades.")
        else:
            bot.send_message(chat_id, "❌ No se hallaron subdominios activos.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en Fase 1: {str(e)}")

# --- LÓGICA DE VULNERABILIDADES CRÍTICAS (FASE 2) ---
@bot.message_handler(commands=['archivos'])
def start_archivos(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        msg = bot.send_message(message.chat.id, "🎯 **Fase Escaneo Crítico:** Escribe el subdominio objetivo (ej: `dev.bbva.com`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_vulns_step)

def process_vulns_step(message):
    target = message.text.strip().lower()
    chat_id = message.chat.id
    output_file = f"reporte_{target}.txt"
    
    bot.send_message(chat_id, f"🔍 Iniciando escaneo de Alto Impacto en `{target}`...\nPriorizando RCE, SQLi, XSS y Exposición de Datos.", parse_mode="Markdown")
    
    try:
        # 1. Nuclei con Tags de Alto Impacto (Tus prioridades)
        # rce = Ejecución de código, sqli = Inyección SQL, xss = Scripts maliciosos
        # ssti = Server Side Template Injection, lfi = Local File Inclusion
        vuln_tags = "rce,sqli,xss,ssti,lfi,exposure,cve,takeover"
        subprocess.run(f"nuclei -u {target} -tags {vuln_tags} -severity critical,high,medium -o {output_file} -silent", shell=True)
        
        # 2. Gobuster Dir para búsqueda de Paneles y Logins (Control de acceso defectuoso)
        for l in ["api-routes.txt", "logins.txt"]:
            if os.path.exists(l):
                subprocess.run(f"gobuster dir --url {target} --wordlist {l} --quiet --output temp_dir.txt", shell=True)
                if os.path.exists("temp_dir.txt"):
                    subprocess.run(f"echo '\n--- Resultados de Fuzzing ({l}) ---' >> {output_file}", shell=True)
                    subprocess.run(f"cat temp_dir.txt >> {output_file}", shell=True)
                    os.remove("temp_dir.txt")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            with open(output_file, "rb") as doc:
                bot.send_document(chat_id, doc, caption=f"❗ Reporte de Vulnerabilidades: {target}")
        else:
            bot.send_message(chat_id, f"✅ No se encontraron fallos críticos evidentes en `{target}`.")
            
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en fase de escaneo: {str(e)}")

# --- MANEJADORES DE BOTONES ---
@bot.message_handler(func=lambda m: m.text == "📡 Solo Subdominios")
def btn_s(m): start_subs(m)

@bot.message_handler(func=lambda m: m.text == "🔓 Buscar Archivos Expuestos")
def btn_a(m): start_archivos(m)

print("🚀 Bugtin Bot v6.5 Online - Hunter Mode.")
bot.polling()

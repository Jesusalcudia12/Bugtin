import telebot
from telebot import types
import subprocess
import os
import time
import re
import threading

# --- CONFIGURACIÓN ---
TOKEN = "8760818918:AAEPZfrcH5L5qVLHymarv0e-IfljRfyb9rY"
YOUR_CHAT_ID = "6280594821"

bot = telebot.TeleBot(TOKEN)

def ejecutar_en_hilo(func, message):
    thread = threading.Thread(target=func, args=(message,))
    thread.start()

# --- RECONOCIMIENTO MEJORADO ---
@bot.message_handler(commands=['subs'])
def start_subs(message):
    msg = bot.send_message(message.chat.id, "📡 Introduce el dominio (ej: bbva.com):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: ejecutar_en_hilo(process_subs_fix, m))

def process_subs_fix(message):
    target = message.text.strip().lower()
    target = target.replace("https://", "").replace("http://", "").split("/")[0]
    chat_id = message.chat.id
    output_raw = f"raw_{target}.txt"
    output_final = f"subs_result_{target}.txt"
    
    bot.send_message(chat_id, f"🔍 Escaneando {target}... (Esto puede tardar 1-2 min)")
    
    try:
        # Intentamos subfinder pero con un fallback si falla
        subprocess.run(f"subfinder -d {target} -silent -o {output_raw}", shell=True, timeout=120)
        
        # Si subfinder falló o dio archivo vacío, intentamos un escaneo rápido de DNS común
        if not os.path.exists(output_raw) or os.path.getsize(output_raw) == 0:
            with open(output_raw, "w") as f:
                f.write(f"www.{target}\nmail.{target}\nftp.{target}\ndev.{target}\napi.{target}\n")

        # RESOLUCIÓN DE IPs (Lógica que siempre funcionaba)
        with open(output_raw, "r") as f_in, open(output_final, "w") as f_out:
            subs_vistos = set()
            for line in f_in:
                sub = line.strip()
                if not sub or sub in subs_vistos: continue
                subs_vistos.add(sub)
                
                # Intentamos obtener la IP con el comando 'host' que es más estable en Termux
                res = subprocess.run(f"host {sub}", shell=True, capture_output=True, text=True)
                if "has address" in res.stdout:
                    ip = re.search(r'address\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', res.stdout)
                    ip_addr = ip.group(1) if ip else "0.0.0.0"
                    f_out.write(f"✅ {sub} [{ip_addr}]\n")
                else:
                    # Si no tiene IP pública, lo anotamos igual para que veas que algo hizo
                    f_out.write(f"❌ {sub} [Sin IP activa]\n")

        if os.path.exists(output_final) and os.path.getsize(output_final) > 0:
            with open(output_final, "rb") as f:
                bot.send_document(chat_id, f, caption=f"🏁 Reconocimiento finalizado para {target}")
            os.remove(output_final)
        else:
            bot.send_message(chat_id, "⚠️ No se pudo resolver ningún subdominio. Revisa tu conexión.")
        
        if os.path.exists(output_raw): os.remove(output_raw)

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Error en el motor: {str(e)}")

# --- RESTO DE COMANDOS (IGUAL QUE V7.5) ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if str(message.chat.id) == YOUR_CHAT_ID:
        help_text = "🤖 Bugtin Bot v7.5 - Fix Activo\n/subs - Subdominios + IP\n/auditar - Nuclei\n/dir - Gobuster"
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def router(m):
    if "sub" in m.text.lower(): start_subs(m)

print("🚀 Bugtin Bot v7.5 FIX - Resolución Forzada Activa")
bot.polling(none_stop=True)

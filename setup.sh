#!/data/data/com.termux/files/usr/bin/bash

echo "[+] Actualizando sistema..."
pkg update && pkg upgrade -y

echo "[+] Instalando lenguajes y herramientas base..."
pkg install python golang git wget zip unzip -y

echo "[+] Instalando herramientas de Recon..."
# Instalación de Nuclei
pkg install nuclei -y
nuclei -ut

# Instalación de Gobuster
pkg install tur-repo -y
pkg install gobuster -y

# Instalación de Subfinder
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
ln -sf ~/go/bin/subfinder $PREFIX/bin/subfinder

echo "[+] Instalando dependencias de Python..."
pip install -r requirements.txt

echo "[+] Configurando permisos..."
chmod +x recon.sh
chmod +x bot.py

echo "[✅] ¡Todo listo! Ejecuta 'python bot.py' para iniciar."

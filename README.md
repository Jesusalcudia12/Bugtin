# 🤖 Bugtin Bot v5.9 Pro 🚀

**Bugtin Bot** es una herramienta de reconocimiento (Recon) automatizada diseñada para ejecutarse en entornos móviles (Termux) o servidores Linux. Utiliza herramientas líderes en ciberseguridad para identificar subdominios, archivos expuestos y paneles de administración en cuestión de minutos.

---

## 🛠️ ¿Para qué sirve?

Este bot centraliza las fases críticas del **Bug Bounty** y **Pentesting** en una interfaz de Telegram:

1.  **Reconocimiento de Subdominios:** Combina fuentes pasivas y fuerza bruta activa usando diccionarios especializados en español y términos técnicos.
2.  **Detección de Filtraciones:** Localiza archivos sensibles como `.env`, `.sql`, configuraciones de base de datos y backups.
3.  **Caza de Paneles (Fuzzing):** Identifica interfaces de administración expuestas (Consul, Hashicorp) y formularios de inicio de sesión (`Logins`).

---

## 📥 Instalación (Termux / Linux)

Sigue estos pasos para configurar el entorno y las dependencias necesarias.

### 1. Actualizar el sistema e instalar Python
```bash
pkg update && pkg upgrade -y
pkg install python git -y

Instalar herramientas de Go
El bot depende de Subfinder, Gobuster y Nuclei. Asegúrate de tener Go instalado o las herramientas configuradas:

pkg install golang -y
go install -v [github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest](https://github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest)
go install -v [github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest](https://github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest)
go install [github.com/OJ/gobuster/v3@latest](https://github.com/OJ/gobuster/v3@latest)

Nota: Asegúrate de mover los binarios a tu carpeta de comandos: cp ~/go/bin/* /data/data/com.termux/files/usr/bin/

Clonar el repositorio e instalar librerías

git clone [https://github.com/jesusalcudia12/NOMBRE_DE_TU_REPO.git](https://github.com/jesusalcudia12/NOMBRE_DE_TU_REPO.git)
cd NOMBRE_DE_TU_REPO
pip install pyTelegramBotAPI

Descargar Diccionarios Críticos (SecLists)
Para que el bot funcione, descarga estas listas indispensables:

# Diccionario en Español
wget [https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-spanish.txt](https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-spanish.txt) -O common.txt

# Diccionario Técnico
wget [https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt](https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt) -O tecnico.txt

# Rutas de API y Paneles
wget [https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api_routes.txt](https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api_routes.txt) -O api_routes.txt

# Páginas de Login
wget [https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/Logins.fuzz.txt](https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/Logins.fuzz.txt) -O logins.txt

---

## 🚀 Modo de Uso

Una vez configurado tu `TOKEN` y `YOUR_CHAT_ID` en el archivo `bot.py`, inicia el bot con:

```bash
python bot.py

Comandos Disponibles:
/start o /help: Muestra el menú interactivo y la guía de uso.

/subs [dominio]: Inicia búsqueda profunda de subdominios (Ej: /subs google.com).

/archivos [dominio]: Inicia el escaneo de vulnerabilidades, paneles y logins.

---

## 📋 Estructura de Diccionarios
common.txt: Optimizado para objetivos en México, España y Colombia.

tecnico.txt: Enfocado en infraestructura global y servidores.

api_routes.txt: Especializado en encontrar rutas de Consul y microservicios.

logins.txt: Diseñado para detectar formularios de acceso y autenticación.

---

## 👤 Créditos y Desarrolladores
Este proyecto es mantenido por:

Jesús Alcudia - OwenDarck

---

## Descargo de responsabilidad:
El uso de esta herramienta para atacar objetivos sin consentimiento previo es ilegal. Los desarrolladores no se hacen responsables del mal uso de este software.


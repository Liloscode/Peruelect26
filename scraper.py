#!/usr/bin/env python3
import os
import sys
import time
import json
import urllib.request
import urllib.parse
import logging
import argparse
from datetime import datetime, timezone, timedelta

# Configuración de Logging
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Log a consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# Log a archivo
log_file = os.path.join(os.path.dirname(__file__), 'scraper.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# URLs de la API de la ONPE y Cabeceras
ONPE_API_URL = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/eleccion-presidencial/participantes-ubicacion-geografica-nombre?idEleccion=10&tipoFiltro=eleccion"
ONPE_TOTALS_URL = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/resumen-general/totales?idEleccion=10&tipoFiltro=eleccion"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
    "Referer": "https://resultadosegundavuelta.onpe.gob.pe/main/resumen",
    "Origin": "https://resultadosegundavuelta.onpe.gob.pe",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="140", "Chromium";v="140"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Connection": "keep-alive",
}

# DNI Identificadores de los candidatos para buscar en el JSON
DNI_SANCHEZ = "16002918"  # ROBERTO HELBERT SANCHEZ PALOMINO
DNI_KEIKO = "10001088"    # KEIKO SOFIA FUJIMORI HIGUCHI

def load_dotenv():
    """Carga variables de entorno desde un archivo .env si existe."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        logging.info("Cargando variables desde archivo .env...")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    # Quitar comillas si existen
                    val = val.strip().strip('"').strip("'")
                    os.environ[key.strip()] = val
    else:
        logging.warning("No se encontró el archivo .env. Asegúrate de configurar las variables de entorno.")

def fetch_onpe_results():
    """Consulta la API de la ONPE y obtiene los votos de los candidatos."""
    req = urllib.request.Request(ONPE_API_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("success") and "data" in data:
                    return data["data"]
                else:
                    logging.error(f"Error en respuesta ONPE: {data.get('message')}")
            else:
                logging.error(f"Respuesta inesperada del servidor ONPE. Status: {response.status}")
    except Exception as e:
        logging.error(f"Error al conectar con la API de la ONPE: {e}")
    return None

def fetch_onpe_totals():
    """Consulta la API de la ONPE para obtener totales de actas y fecha de actualización."""
    req = urllib.request.Request(ONPE_TOTALS_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("success") and "data" in data:
                    return data["data"]
                else:
                    logging.error(f"Error en respuesta ONPE totales: {data.get('message')}")
            else:
                logging.error(f"Respuesta inesperada de ONPE totales. Status: {response.status}")
    except Exception as e:
        logging.error(f"Error al conectar con la API de ONPE totales: {e}")
    return None

def format_update_time(timestamp_ms):
    """Convierte una marca de tiempo en milisegundos a la hora local de Perú (UTC-5)."""
    try:
        timestamp_s = timestamp_ms / 1000.0
        dt_utc = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
        peru_tz = timezone(timedelta(hours=-5))
        dt_peru = dt_utc.astimezone(peru_tz)
        return dt_peru.strftime("%d/%m/%Y %H:%M:%S")
    except Exception as e:
        logging.error(f"Error al formatear fecha de actualización: {e}")
        return "Desconocido"

def process_votes(candidates_data):
    """Procesa los datos de votos de ONPE y calcula el reporte de diferencia."""
    sanchez_votes = None
    keiko_votes = None

    for candidate in candidates_data:
        dni = candidate.get("dniCandidato")
        votes = candidate.get("totalVotosValidos", 0)
        
        if dni == DNI_SANCHEZ:
            sanchez_votes = votes
        elif dni == DNI_KEIKO:
            keiko_votes = votes

    if sanchez_votes is None or keiko_votes is None:
        logging.error("No se pudieron encontrar los votos para ambos candidatos en el reporte.")
        return None

    logging.info(f"Votos extraídos -> SANCHEZ: {sanchez_votes:,} | KEIKO: {keiko_votes:,}")

    # Determinar quién va ganando y la diferencia
    if sanchez_votes > keiko_votes:
        diff = sanchez_votes - keiko_votes
        return f"SANCHEZ=+{diff}"
    elif keiko_votes > sanchez_votes:
        diff = keiko_votes - sanchez_votes
        return f"KEIKO=+{diff}"
    else:
        return "SANCHEZ=0"

def send_telegram_message(message):
    """Envía un mensaje de texto al bot de Telegram configurado."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id or "here" in token or "here" in chat_id:
        logging.warning("Configuración de Telegram incompleta o por defecto (.env sin editar). Omitiendo envío.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("ok"):
                logging.info("Mensaje enviado con éxito a Telegram.")
                return True
            else:
                logging.error(f"Error devuelto por Telegram: {res}")
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, "read"):
            try:
                err_msg += f" - Response: {e.read().decode('utf-8')}"
            except Exception:
                pass
        logging.error(f"Excepción al enviar mensaje a Telegram: {err_msg}")
    return False

def run_once():
    """Ejecuta una única consulta, genera el reporte con información detallada y lo envía."""
    logging.info("Iniciando consulta de resultados y totales...")
    
    # 1. Obtener los votos de los candidatos
    candidates = fetch_onpe_results()
    if not candidates:
        logging.error("No se pudieron obtener resultados de candidatos de la ONPE.")
        return False
        
    # 2. Obtener el porcentaje de actas y fecha de actualización
    totals = fetch_onpe_totals()
    if not totals:
        logging.error("No se pudieron obtener totales generales de la ONPE.")
        return False

    report = process_votes(candidates)
    if not report:
        return False

    actas_contabilizadas = totals.get("actasContabilizadas", 0.0)
    fecha_ms = totals.get("fechaActualizacion")
    fecha_str = format_update_time(fecha_ms) if fecha_ms else "Desconocido"

    # Formato solicitado por el usuario:
    # ACTAS CONTABILIZADAS: {%}
    # {NAME}=+<diferencia>
    # ACTUALIZADO AL: Fecha y hora de última actualización
    final_message = (
        f"ACTAS CONTABILIZADAS: {actas_contabilizadas}%\n"
        f"{report}\n"
        f"ACTUALIZADO AL: {fecha_str}"
    )

    logging.info(f"Reporte generado:\n{final_message}")
    send_telegram_message(final_message)
    return True

def main():
    parser = argparse.ArgumentParser(description="Scraper de Elecciones ONPE Segunda Vuelta con envío a Telegram")
    parser.add_argument('--test', '-t', action='store_true', help="Ejecuta una sola vez para verificar y finaliza")
    args = parser.parse_args()

    load_dotenv()

    if args.test:
        success = run_once()
        sys.exit(0 if success else 1)

    logging.info("Iniciando el scraper de elecciones en bucle continuo (cada 10 minutos)...")
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            logging.info("Proceso detenido por el usuario.")
            break
        except Exception as e:
            logging.error(f"Excepción inesperada en el bucle principal: {e}")
        
        logging.info("Esperando 10 minutos para la siguiente actualización...")
        time.sleep(600)

if __name__ == "__main__":
    main()

# Scraper de Elecciones ONPE - Segunda Vuelta

Esta aplicación de consola en Python se conecta de manera segura a la API oficial de presentación de resultados de la ONPE para la segunda vuelta, compara los votos entre los candidatos **ROBERTO HELBERT SANCHEZ PALOMINO** y **KEIKO SOFIA FUJIMORI HIGUCHI**, y envía un reporte simplificado con la diferencia de votos a Telegram cada 10 minutos.

El formato del mensaje enviado es:
- Si va ganando Sánchez: `SANCHEZ=+X` (donde X es la ventaja de votos sobre Keiko)
- Si va ganando Keiko: `KEIKO=+X` (donde X es la ventaja de votos sobre Sánchez)

## 📋 Requisitos

- **Python 3** (viene preinstalado en macOS).
- No requiere instalar librerías externas de `pip`, ya que utiliza exclusivamente la biblioteca estándar de Python (`urllib`, `json`, `logging`, `time`, etc.).

---

## ⚙️ Configuración

### 1. Crear el archivo de configuración `.env`

Copia el archivo de ejemplo `.env.example` y cámbiale el nombre a `.env`:

```bash
cp .env.example .env
```

Abre el archivo `.env` recién creado en tu editor y configura tus credenciales de Telegram:

```env
TELEGRAM_BOT_TOKEN=tu_token_de_telegram_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

### 2. Cómo obtener el Token de Telegram Bot y tu Chat ID

1. **Crear el Bot de Telegram:**
   - Abre Telegram y busca al usuario `@BotFather`.
   - Envía el comando `/newbot` y sigue las instrucciones para ponerle un nombre y un usuario.
   - Al finalizar, `@BotFather` te dará el **Token** del bot (un código largo de números y letras). Cópialo en la variable `TELEGRAM_BOT_TOKEN` del archivo `.env`.

2. **Obtener tu Chat ID:**
   - Inicia un chat con tu nuevo bot (búscalo por su usuario y presiona **Iniciar / Start**).
   - Envía cualquier mensaje de prueba a tu bot.
   - En tu navegador, accede a la siguiente URL reemplazando `<TOKEN>` con el token de tu bot:
     `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Busca en el JSON resultante la sección `"chat"` -> `"id"`. Verás un número entero (ej. `123456789`). Copia ese número en la variable `TELEGRAM_CHAT_ID` en tu archivo `.env`.
   - *Nota:* Si quieres enviar el mensaje a un grupo, añade el bot al grupo, envíale un mensaje con `/` y obtén el ID de grupo del mismo enlace (los IDs de grupos usualmente empiezan con un signo menos, ej. `-100123456789`).

---

## 🚀 Uso de la Aplicación

### Prueba de Ejecución Única (Modo Test)

Antes de dejar corriendo el scraper de forma permanente, puedes ejecutar una sola iteración para probar que se conecta con la ONPE correctamente y (si tienes configurado Telegram) que envía el mensaje.

Ejecuta el siguiente comando en tu terminal:

```bash
python3 scraper.py --test
```

**Resultado esperado en consola:**
```text
2026-06-10 16:55:00,123 [INFO] Cargando variables desde archivo .env...
2026-06-10 16:55:00,125 [INFO] Iniciando consulta única de resultados...
2026-06-10 16:55:00,680 [INFO] Votos extraídos -> SANCHEZ: 9,018,130 | KEIKO: 9,008,779
2026-06-10 16:55:00,681 [INFO] Reporte generado: SANCHEZ=+9351
2026-06-10 16:55:01,230 [INFO] Mensaje enviado con éxito a Telegram.
```

Si no has configurado las claves de Telegram todavía en `.env`, el script imprimirá los votos y la diferencia en tu consola pero omitirá el envío a Telegram sin fallar.

### Ejecución en Bucle Continuo (Producción)

Para ejecutar el scraper en primer plano de manera indefinida (se actualiza automáticamente cada 10 minutos):

```bash
python3 scraper.py
```

### Ejecutar en Segundo Plano (macOS/Linux)

Para dejar corriendo el scraper en segundo plano incluso si cierras la ventana de la terminal, puedes usar `nohup`:

```bash
nohup python3 scraper.py > /dev/null 2>&1 &
```

Esto ejecutará el script en segundo plano. Toda la actividad de la aplicación (incluyendo errores, marcas de tiempo y confirmación de envíos) se guardará automáticamente en el archivo local **`scraper.log`**.

Para detener el scraper en segundo plano en cualquier momento:

```bash
pkill -f scraper.py
```

Y para ver los logs en tiempo real:

```bash
tail -f scraper.log
```

---

## ☁️ Ejecutar de forma Gratuita en la Nube (GitHub Actions)

Si no quieres dejar tu laptop encendida, puedes usar **GitHub Actions** para ejecutar el scraper automáticamente en los servidores de GitHub de forma totalmente gratuita y segura.

### Pasos para configurarlo:

1. **Crear un repositorio en GitHub:**
   - Ve a tu cuenta de GitHub y crea un nuevo repositorio (puede ser **Público** para minutos de Actions ilimitados y gratuitos, o **Privado** para hasta 2000 minutos libres al mes).
   - *Nota: Es totalmente seguro usar un repositorio público porque tus credenciales no se subirán al repositorio (se guardan encriptadas en la configuración).*

2. **Subir los archivos de tu proyecto:**
   - Inicializa git, añade los archivos y súbelos a tu repositorio (¡asegúrate de que tu archivo `.env` NO se suba!).
   - Los únicos archivos necesarios en el repositorio son:
     - `scraper.py`
     - `.github/workflows/scraper.yml` (que ya está creado en tu espacio de trabajo)

3. **Configurar los Secretos de Telegram en GitHub:**
   - En tu repositorio de GitHub, ve a la pestaña **Settings** (Configuración) -> **Secrets and variables** -> **Actions**.
   - Haz clic en **New repository secret** (Nuevo secreto del repositorio) y crea dos secretos:
     - Nombre: `TELEGRAM_BOT_TOKEN` | Valor: *tu token de bot*
     - Nombre: `TELEGRAM_CHAT_ID` | Valor: *tu chat id del canal/grupo*
   - Estos valores estarán encriptados y solo la máquina virtual temporal de GitHub los leerá al ejecutar el script.

4. **Activar las ejecuciones (Actions):**
   - Ve a la pestaña **Actions** en tu repositorio de GitHub.
   - Si ves un aviso sobre flujos de trabajo desactivados, haz clic en **"I understand my workflows, go ahead and enable them"**.
   - Selecciona el flujo `"ONPE Scraper Automático"` a la izquierda y pulsa en **Run workflow** para forzar una ejecución manual de prueba.
   - El script correrá automáticamente en los servidores de GitHub cada 10 minutos y te enviará las notificaciones al canal de Telegram de manera continua y autónoma.

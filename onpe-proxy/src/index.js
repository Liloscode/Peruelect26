const HEADERS = {
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
  "Connection": "keep-alive"
};

const DNI_SANCHEZ = "16002918";
const DNI_KEIKO = "10001088";

async function runScraper(env) {
  const token = env.TELEGRAM_BOT_TOKEN;
  const chat_id = env.TELEGRAM_CHAT_ID;

  if (!token || !chat_id || token.includes("here") || chat_id.includes("here")) {
    console.log("Configuración de Telegram incompleta o por defecto. Omitiendo envío.");
    return "Configuración de Telegram incompleta.";
  }

  // 1. Obtener votos de candidatos
  const candidatesUrl = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/eleccion-presidencial/participantes-ubicacion-geografica-nombre?idEleccion=10&tipoFiltro=eleccion";
  const candidatesRes = await fetch(candidatesUrl, { headers: HEADERS });
  if (!candidatesRes.ok) {
    throw new Error(`Error ONPE candidatos: Status ${candidatesRes.status}`);
  }
  const candidatesData = await candidatesRes.json();
  if (!candidatesData.success || !candidatesData.data) {
    throw new Error(`Error en formato ONPE candidatos: ${candidatesData.message}`);
  }

  // 2. Obtener totales
  const totalsUrl = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/resumen-general/totales?idEleccion=10&tipoFiltro=eleccion";
  const totalsRes = await fetch(totalsUrl, { headers: HEADERS });
  if (!totalsRes.ok) {
    throw new Error(`Error ONPE totales: Status ${totalsRes.status}`);
  }
  const totalsData = await totalsRes.json();
  if (!totalsData.success || !totalsData.data) {
    throw new Error(`Error en formato ONPE totales: ${totalsData.message}`);
  }

  // 3. Procesar votos
  let sanchez_votes = null;
  let keiko_votes = null;
  for (const candidate of candidatesData.data) {
    const dni = candidate.dniCandidato;
    const votes = candidate.totalVotosValidos || 0;
    if (dni === DNI_SANCHEZ) {
      sanchez_votes = votes;
    } else if (dni === DNI_KEIKO) {
      keiko_votes = votes;
    }
  }

  if (sanchez_votes === null || keiko_votes === null) {
    throw new Error("No se encontraron los votos de ambos candidatos en los resultados.");
  }

  let report = "";
  if (sanchez_votes > keiko_votes) {
    report = `SANCHEZ=+${sanchez_votes - keiko_votes}`;
  } else if (keiko_votes > sanchez_votes) {
    report = `KEIKO=+${keiko_votes - sanchez_votes}`;
  } else {
    report = "SANCHEZ=0";
  }

  // 4. Procesar totales y fecha
  const actas_contabilizadas = totalsData.data.actasContabilizadas || 0.0;
  const fecha_ms = totalsData.data.fechaActualizacion;
  
  let fecha_str = "Desconocido";
  if (fecha_ms) {
    const date = new Date(fecha_ms);
    const formatter = new Intl.DateTimeFormat('es-PE', {
      timeZone: 'America/Lima',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    fecha_str = formatter.format(date).replace(',', '');
  }

  // 5. Compilar mensaje final
  const finalMessage = (
    `ACTAS CONTABILIZADAS: ${actas_contabilizadas}%\n` +
    `${report}\n` +
    `ACTUALIZADO AL: ${fecha_str}`
  );

  // 6. Enviar a Telegram
  const telegramUrl = `https://api.telegram.org/bot${token}/sendMessage`;
  const telegramRes = await fetch(telegramUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chat_id,
      text: finalMessage
    })
  });

  if (!telegramRes.ok) {
    const errText = await telegramRes.text();
    throw new Error(`Error al enviar a Telegram: Status ${telegramRes.status} - ${errText}`);
  }

  console.log("Reporte enviado con éxito:", finalMessage);
  return finalMessage;
}

export default {
  // Manejador del Cron Trigger (ejecución automática cada 10 min)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runScraper(env));
  },

  // Manejador de llamadas HTTP (ejecución manual abriendo la URL, y proxy)
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Si es una llamada al proxy, mantenemos la funcionalidad original
    const allowedPaths = [
      "/presentacion-backend/eleccion-presidencial/participantes-ubicacion-geografica-nombre",
      "/presentacion-backend/resumen-general/totales"
    ];

    if (allowedPaths.includes(url.pathname)) {
      const upstreamUrl = "https://resultadosegundavuelta.onpe.gob.pe" + url.pathname + url.search;
      try {
        const response = await fetch(upstreamUrl, {
          method: "GET",
          headers: HEADERS
        });
        const body = await response.arrayBuffer();
        return new Response(body, {
          status: response.status,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
          }
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: "proxy_error", message: String(e) }), {
          status: 502,
          headers: { "Content-Type": "application/json" }
        });
      }
    }

    // Si es a la raíz "/", ejecuta el scraper de inmediato y muestra el resultado en pantalla
    if (url.pathname === "/" || url.pathname === "") {
      try {
        const msg = await runScraper(env);
        return new Response(JSON.stringify({
          success: true,
          message: "Scraping manual ejecutado con éxito y enviado a Telegram",
          reporte: msg
        }), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
          }
        });
      } catch (e) {
        return new Response(JSON.stringify({
          success: false,
          error: String(e.message || e)
        }), {
          status: 502,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
          }
        });
      }
    }

    // Ruta no encontrada
    return new Response(JSON.stringify({ error: "Ruta no permitida" }), {
      status: 404,
      headers: { "Content-Type": "application/json" }
    });
  }
};

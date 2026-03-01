// =============================================================
// static/js/app.js — Intento 2
// Maneja estado, fetch al servidor, renderiza UI
// =============================================================

// ── Estado global ─────────────────────────────────────────
let state = {
  id_usuario: 0,
  year:       null,
  month:      null,
  fecha_dia:  null,   // null = vista mes
};

const MESES = [
  "", "Enero","Febrero","Marzo","Abril","Mayo","Junio",
  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
];

// ── Init ──────────────────────────────────────────────────
function initDashboard(uid, year, month) {
  state.id_usuario = uid;
  state.year       = year;
  state.month      = month;
  fetchDashboard();
}

// ── Fetch principal ───────────────────────────────────────
async function fetchDashboard() {
  spinnerOn();
  const url = `/api/dashboard?id_usuario=${state.id_usuario}&year=${state.year}&month=${state.month}`;
  try {
    const res  = await fetch(url);
    const data = await res.json();
    renderKpis(data.kpis, data.historica);
    if (data.meds) renderMedicamentos(data.meds);
    renderCalendario(data.semanas);
    document.getElementById("titulo-mes").textContent = data.titulo_mes;
    document.getElementById("fraccion").textContent =
      `${data.kpis.tomadas}/${data.kpis.totales}`;
  } catch(e) {
    console.error("Error fetch dashboard:", e);
  } finally {
    spinnerOff();
  }
}

// ── Fetch vista día ───────────────────────────────────────
async function fetchDia(fecha) {
  spinnerOn();
  const url = `/api/dia?id_usuario=${state.id_usuario}&fecha=${fecha}`;
  try {
    const res  = await fetch(url);
    const data = await res.json();
    state._eventos_dia = data.eventos;
    renderVistaDia(fecha, data);
    renderKpisDia(data.resumen, fecha);
    if (data.meds) renderMedicamentos(data.meds);
  } catch(e) {
    console.error("Error fetch día:", e);
  } finally {
    spinnerOff();
  }
}

// ── Render KPIs — vista mes ───────────────────────────────
function renderKpis(kpis, historica) {
  setKpi("val-general", kpis.adh_general, "%", "kpi-general");
  setKpi("val-online",  kpis.adh_online,  "%", "kpi-online");
  setKpi("val-offline", kpis.adh_offline, "%", "kpi-offline");
  document.getElementById("val-tiempo").textContent = `${kpis.tiempo_respuesta} min`;
  document.getElementById("val-hist").textContent   = `${historica}%`;
}

// ── Render KPIs — vista día ────────────────────────────────
function renderKpisDia(resumen, fecha) {
  // Adherencia general del día
  setKpi("val-general", resumen.pct, "%", "kpi-general");

  // Online y offline desde los eventos del día
  const eventos = state._eventos_dia || [];
  const online  = eventos.filter(e => e.modo === "online");
  const offline = eventos.filter(e => e.modo === "offline");

  const pctOnline  = online.length  > 0
    ? Math.round(online.filter(e  => e.estado === "tomado").length / online.length  * 100)
    : null;
  const pctOffline = offline.length > 0
    ? Math.round(offline.filter(e => e.estado === "tomado").length / offline.length * 100)
    : null;

  if (pctOnline !== null)  setKpi("val-online",  pctOnline,  "%", "kpi-online");
  else { document.getElementById("val-online").textContent = "—"; document.getElementById("kpi-online").className = "kpi-card kpi-neutro"; }

  if (pctOffline !== null) setKpi("val-offline", pctOffline, "%", "kpi-offline");
  else { document.getElementById("val-offline").textContent = "—"; document.getElementById("kpi-offline").className = "kpi-card kpi-neutro"; }

  // Tiempo promedio del día
  const tiempos = eventos.filter(e => e.minutos !== null).map(e => e.minutos);
  const avgMin  = tiempos.length > 0
    ? (tiempos.reduce((a,b) => a+b, 0) / tiempos.length).toFixed(1)
    : "—";
  document.getElementById("val-tiempo").textContent = avgMin !== "—" ? `${avgMin} min` : "—";

  // Fecha del día como label en histórica
  const [y, m, d] = fecha.split("-");
  document.getElementById("val-hist").textContent = `${parseInt(d)} ${MESES[parseInt(m)]}`;
  document.getElementById("kpi-hist").className   = "kpi-card kpi-historico";
}

function setKpi(valId, pct, sufijo, cardId) {
  document.getElementById(valId).textContent = `${pct}${sufijo}`;
  const card  = document.getElementById(cardId);
  card.classList.remove("bueno", "regular", "malo");
  if (pct >= 80)      card.classList.add("bueno");
  else if (pct >= 60) card.classList.add("regular");
  else                card.classList.add("malo");
}

// ── Render Calendario ─────────────────────────────────────
function renderCalendario(semanas) {
  const grid = document.getElementById("cal-grid");
  grid.innerHTML = "";

  semanas.forEach(semana => {
    semana.forEach(dia => {
      const cell = document.createElement("div");
      if (!dia) {
        cell.className = "dia-cell vacio";
      } else {
        cell.className = `dia-cell ${dia.clase}`;
        const pctHtml = dia.label !== "—"
          ? `<span class="dia-pct">${dia.label}</span>`
          : "";
        cell.innerHTML = `
          <span class="dia-num">${dia.num}</span>
          ${pctHtml}
        `;
        if (dia.clase !== "sin-datos") {
          cell.onclick = () => clickDia(dia.fecha);
        }
      }
      grid.appendChild(cell);
    });
  });
}

// ── Render Vista Día ──────────────────────────────────────
function renderVistaDia(fecha, data) {
  document.getElementById("vista-mes").classList.add("oculto");
  const vistaDiv = document.getElementById("vista-dia");
  vistaDiv.classList.remove("oculto");

  // Título con fecha legible
  const [y, m, d] = fecha.split("-");
  document.getElementById("dia-titulo").textContent =
    `${parseInt(d)} de ${MESES[parseInt(m)]} de ${y}`;

  // Resumen
  const r = data.resumen;
  document.getElementById("dia-resumen").textContent =
    `${r.tomados} de ${r.total} tomas confirmadas — ${r.pct}%`;

  // Eventos
  const cont = document.getElementById("dia-eventos");
  cont.innerHTML = "";

  if (data.eventos.length === 0) {
    cont.innerHTML = `<div style="color:var(--text-muted);padding:12px">Sin eventos registrados.</div>`;
    return;
  }

  data.eventos.forEach(ev => {
    const row = document.createElement("div");
    row.className = `evento-row ${ev.estado}`;
    row.innerHTML = `
      <span class="evento-hora">${ev.hora}</span>
      <span class="evento-estado ${ev.estado}">${ev.estado}</span>
      <span class="evento-casilla">Med. ${ev.casilla}</span>
      <span class="evento-modo">${ev.modo}</span>
      <span class="evento-min">${ev.minutos !== null ? ev.minutos + " min" : "—"}</span>
    `;
    cont.appendChild(row);
  });
}

// ── Navegación ────────────────────────────────────────────
function cambiarMes(delta) {
  state.month += delta;
  if (state.month > 12) { state.month = 1;  state.year++; }
  if (state.month < 1)  { state.month = 12; state.year--; }
  volverMes(false);   // solo oculta vista día, no recarga
  fetchDashboard();   // una sola llamada con el nuevo mes
}

function clickDia(fecha) {
  state.fecha_dia = fecha;
  fetchDia(fecha);
}

function volverMes(recargar = true) {
  state.fecha_dia    = null;
  state._eventos_dia = [];
  document.getElementById("vista-dia").classList.add("oculto");
  document.getElementById("vista-mes").classList.remove("oculto");
  if (recargar) fetchDashboard();  // restaura KPIs + gráfica mensual
}

// ── Dropdown ──────────────────────────────────────────────
function toggleDropdown() {
  document.getElementById("dropdown").classList.toggle("open");
}

function selectPaciente(id, nombre) {
  state.id_usuario = id;
  document.getElementById("dropdown-label").textContent = nombre;
  document.getElementById("dropdown").classList.remove("open");

  // Marcar opción activa
  document.querySelectorAll(".dropdown-opt").forEach(el => {
    el.classList.toggle("selected", parseInt(el.dataset.value) === id);
  });

  fetchDashboard();
}

// Cerrar dropdown al clic fuera
document.addEventListener("click", e => {
  const dd = document.getElementById("dropdown");
  if (!dd.contains(e.target)) dd.classList.remove("open");
});

// ── Spinner ───────────────────────────────────────────────
function spinnerOn()  { document.getElementById("spinner-cal").classList.remove("oculto"); }
function spinnerOff() { document.getElementById("spinner-cal").classList.add("oculto"); }

// ── Gráfica medicamentos HTML/CSS ─────────────────────────
function renderMedicamentos(meds) {
  const chart    = document.getElementById("meds-chart");
  const sinDatos = document.getElementById("meds-sin-datos");
  const eje      = document.getElementById("meds-eje");

  chart.querySelectorAll(".meds-row").forEach(el => el.remove());

  const maxProg  = Math.max(...meds.map(m => m.programadas), 1);
  const hayDatos = meds.some(m => m.programadas > 0);

  if (!hayDatos) {
    sinDatos.style.display = "flex";
    eje.innerHTML = "";
    return;
  }
  sinDatos.style.display = "none";

  // C6 arriba → C1 abajo (orden descendente)
  const ordenados = [...meds].reverse();

  ordenados.forEach(m => {
    const pctTom  = m.programadas > 0 ? (m.tomadas / maxProg * 100) : 0;
    const pctOmit = m.programadas > 0 ? ((m.programadas - m.tomadas) / maxProg * 100) : 0;
    const omitidas = m.programadas - m.tomadas;
    const etiq = m.programadas > 0 ? `${m.tomadas}/${m.programadas}` : "";

    const row = document.createElement("div");
    row.className = "meds-row";
    row.style.marginBottom = "18px";

    const etiqHTML = etiq
      ? `<span class="meds-etiqueta">${etiq}</span>`
      : "";

    row.innerHTML = `
      <span class="meds-label">${m.casilla}</span>
      <div class="meds-bar-wrap" style="position:relative">
        <div class="meds-bar-tomadas" style="width:${pctTom}%; position:relative">
          ${etiqHTML}
        </div>
        <div class="meds-bar-omitidas" style="width:${pctOmit}%"></div>
        <span class="meds-nombre">${m.medicamento}</span>
      </div>
    `;
    chart.appendChild(row);
  });

  // Eje X — 5 marcas
  eje.innerHTML = "";
  for (let i = 0; i <= 5; i++) {
    const val  = Math.round(maxProg / 5 * i);
    const span = document.createElement("span");
    span.textContent = val;
    eje.appendChild(span);
  }
}
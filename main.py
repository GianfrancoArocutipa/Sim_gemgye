from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import time
import random
import threading

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────
# ESTADO GLOBAL
# ─────────────────────────────────────────
motor = {
    "encendido": True,
    "tiempo_inicio": time.time(),
    "rpm": 800,
    "velocidad": 0,
    "temperatura_refrigerante": 20.0,
    "temperatura_aire": 25.0,
    "carga_motor": 10.0,
    "acelerador": 0.0,
    "voltaje_bateria": 12.6,
    "km_totales": random.randint(15000, 120000),
    "dtcs_activos": [],
    "ciclo_conduccion": "ralenti",
    "tiempo_ciclo": 0,
    "ciclo_manual": False,   # True = no cambia automático
    "tick": 0
}

CATALOGO_DTC = {
    "P0100": {"descripcion": "Sensor de flujo de masa de aire - fallo de circuito", "gravedad": "alta", "categoria": "sensor_maf"},
    "P0101": {"descripcion": "Sensor de flujo de masa de aire - rango/rendimiento", "gravedad": "media", "categoria": "sensor_maf"},
    "P0103": {"descripcion": "Sensor de flujo de masa de aire - señal alta", "gravedad": "media", "categoria": "sensor_maf"},
    "P0115": {"descripcion": "Sensor de temperatura de refrigerante - fallo de circuito", "gravedad": "alta", "categoria": "sensor_temperatura"},
    "P0117": {"descripcion": "Sensor de temperatura de refrigerante - señal baja", "gravedad": "media", "categoria": "sensor_temperatura"},
    "P0118": {"descripcion": "Sensor de temperatura de refrigerante - señal alta", "gravedad": "media", "categoria": "sensor_temperatura"},
    "P0120": {"descripcion": "Sensor de posición del acelerador A - fallo de circuito", "gravedad": "alta", "categoria": "sensor_acelerador"},
    "P0125": {"descripcion": "Temperatura insuficiente para control de mezcla", "gravedad": "media", "categoria": "sensor_temperatura"},
    "P0128": {"descripcion": "Termostato - temperatura por debajo del umbral", "gravedad": "baja", "categoria": "termostato"},
    "P0130": {"descripcion": "Sensor de oxígeno banco 1 sensor 1 - fallo", "gravedad": "media", "categoria": "sensor_o2"},
    "P0171": {"descripcion": "Sistema demasiado pobre - banco 1", "gravedad": "media", "categoria": "mezcla"},
    "P0172": {"descripcion": "Sistema demasiado rico - banco 1", "gravedad": "media", "categoria": "mezcla"},
    "P0201": {"descripcion": "Circuito del inyector cilindro 1 - fallo", "gravedad": "alta", "categoria": "inyeccion"},
    "P0202": {"descripcion": "Circuito del inyector cilindro 2 - fallo", "gravedad": "alta", "categoria": "inyeccion"},
    "P0203": {"descripcion": "Circuito del inyector cilindro 3 - fallo", "gravedad": "alta", "categoria": "inyeccion"},
    "P0204": {"descripcion": "Circuito del inyector cilindro 4 - fallo", "gravedad": "alta", "categoria": "inyeccion"},
    "P0217": {"descripcion": "Condición de sobretemperatura del motor", "gravedad": "alta", "categoria": "temperatura_critica"},
    "P0300": {"descripcion": "Fallo de encendido aleatorio/múltiple detectado", "gravedad": "alta", "categoria": "encendido"},
    "P0301": {"descripcion": "Fallo de encendido cilindro 1", "gravedad": "alta", "categoria": "encendido"},
    "P0302": {"descripcion": "Fallo de encendido cilindro 2", "gravedad": "alta", "categoria": "encendido"},
    "P0303": {"descripcion": "Fallo de encendido cilindro 3", "gravedad": "alta", "categoria": "encendido"},
    "P0304": {"descripcion": "Fallo de encendido cilindro 4", "gravedad": "alta", "categoria": "encendido"},
    "P0400": {"descripcion": "Fallo en el flujo del sistema EGR", "gravedad": "baja", "categoria": "emisiones"},
    "P0420": {"descripcion": "Eficiencia del catalizador por debajo del umbral", "gravedad": "media", "categoria": "catalizador"},
    "P0440": {"descripcion": "Sistema de evaporación de combustible - fallo", "gravedad": "baja", "categoria": "evaporacion"},
    "P0455": {"descripcion": "Fuga grande en sistema de evaporación", "gravedad": "media", "categoria": "evaporacion"},
    "P0700": {"descripcion": "Sistema de control de transmisión - fallo", "gravedad": "alta", "categoria": "transmision"},
    "P0730": {"descripcion": "Relación de cambio incorrecta", "gravedad": "alta", "categoria": "transmision"},
    "B0001": {"descripcion": "Módulo de control del airbag conductor - fallo", "gravedad": "alta", "categoria": "airbag"},
    "B0010": {"descripcion": "Módulo de climatización - fallo de comunicación", "gravedad": "baja", "categoria": "climatizacion"},
    "C0031": {"descripcion": "Sensor de velocidad rueda delantera derecha - fallo", "gravedad": "alta", "categoria": "abs"},
    "C0110": {"descripcion": "Motor de la bomba ABS - fallo de circuito", "gravedad": "alta", "categoria": "abs"},
    "U0001": {"descripcion": "Bus CAN de alta velocidad - fallo de comunicación", "gravedad": "alta", "categoria": "can_bus"},
    "U0100": {"descripcion": "Comunicación perdida con ECM/PCM", "gravedad": "alta", "categoria": "can_bus"},
}

# ─────────────────────────────────────────
# FÍSICA DEL MOTOR
# ─────────────────────────────────────────
def actualizar_motor():
    while True:
        time.sleep(1)
        m = motor
        m["tick"] += 1
        m["tiempo_ciclo"] += 1

        if not m["ciclo_manual"] and m["tiempo_ciclo"] > random.randint(15, 30):
            ciclos = ["ralenti", "acelerando", "crucero", "frenando"]
            pesos  = [0.2, 0.3, 0.35, 0.15]
            m["ciclo_conduccion"] = random.choices(ciclos, pesos)[0]
            m["tiempo_ciclo"] = 0

        ciclo = m["ciclo_conduccion"]

        if ciclo == "ralenti":
            objetivo_rpm = random.randint(750, 900)
            objetivo_vel = 0
            m["acelerador"] = random.uniform(0, 5)
        elif ciclo == "acelerando":
            objetivo_rpm = random.randint(2500, 5500)
            objetivo_vel = (m["rpm"] - 1000) / 40
            m["acelerador"] = random.uniform(40, 90)
        elif ciclo == "crucero":
            objetivo_rpm = random.randint(1800, 2800)
            objetivo_vel = random.randint(60, 100)
            m["acelerador"] = random.uniform(20, 40)
        else:
            objetivo_rpm = random.randint(900, 1400)
            objetivo_vel = max(0, m["velocidad"] - random.randint(3, 8))
            m["acelerador"] = random.uniform(0, 10)

        m["rpm"]       += (objetivo_rpm - m["rpm"]) * 0.15
        m["rpm"]        = max(650, min(7200, m["rpm"]))
        m["velocidad"] += (objetivo_vel - m["velocidad"]) * 0.1
        m["velocidad"]  = max(0, min(180, m["velocidad"]))
        m["carga_motor"] = (m["rpm"] / 7200) * 50 + (m["acelerador"] / 100) * 50
        m["carga_motor"] = max(5, min(100, m["carga_motor"]))

        tiempo_enc = time.time() - m["tiempo_inicio"]
        temp_obj   = 90.0 if tiempo_enc > 300 else 20 + (70 * tiempo_enc / 300)
        temp_obj  += (m["carga_motor"] - 50) * 0.05
        temp_obj  -= (m["velocidad"] / 180) * 5
        m["temperatura_refrigerante"] += (temp_obj - m["temperatura_refrigerante"]) * 0.02
        m["temperatura_refrigerante"]  = max(20, min(115, m["temperatura_refrigerante"]))
        m["temperatura_aire"]          = 25 + (m["carga_motor"] / 100) * 15 + random.uniform(-1, 1)

        if ciclo == "ralenti":
            m["voltaje_bateria"] = random.uniform(13.8, 14.2)
        else:
            m["voltaje_bateria"] = random.uniform(13.5, 14.8)

        m["km_totales"] += m["velocidad"] / 3600

        # DTCs automáticos por condición física (no elimina los manuales)
        dtcs_auto = []
        if m["temperatura_refrigerante"] > 108:
            dtcs_auto.append("P0217")
        if m["rpm"] > 6500 and m["carga_motor"] > 85:
            dtcs_auto.append("P0300")
        # Fusionar sin duplicar
        for d in dtcs_auto:
            if d not in m["dtcs_activos"]:
                m["dtcs_activos"].append(d)

hilo = threading.Thread(target=actualizar_motor, daemon=True)
hilo.start()

# ─────────────────────────────────────────
# HELPERS HEX
# ─────────────────────────────────────────
def rpm_a_hex(v):
    r = int(v) * 4; return f"41 0C {(r>>8)&0xFF:02X} {r&0xFF:02X}"
def vel_a_hex(v):
    return f"41 0D {int(v):02X}"
def temp_a_hex(v):
    return f"41 05 {int(v)+40:02X}"
def aire_a_hex(v):
    return f"41 0F {int(v)+40:02X}"
def carga_a_hex(v):
    return f"41 04 {int(v*255/100):02X}"
def acel_a_hex(v):
    return f"41 11 {int(v*255/100):02X}"
def volt_a_hex(v):
    r = int(v*1000); return f"41 42 {(r>>8)&0xFF:02X} {r&0xFF:02X}"
def dtcs_a_hex(dtcs):
    if not dtcs: return "43 00"
    res = f"43 {len(dtcs):02X}"
    prefijos = {"P":"0","C":"4","B":"8","U":"C"}
    for d in dtcs[:3]:
        b1 = int(prefijos.get(d[0],"0"),16)*16+int(d[1])
        b2 = int(d[2:4],16)
        res += f" {b1:02X} {b2:02X}"
    return res

# ─────────────────────────────────────────
# PANEL DE CONTROL HTML
# ─────────────────────────────────────────
PANEL_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OBD Simulator — GEM Motors</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }

  header { background: #1a1d2e; border-bottom: 2px solid #3b82f6; padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.3rem; color: #fff; }
  .badge { background: #22c55e; color: #fff; font-size: 0.7rem; padding: 2px 8px; border-radius: 99px; font-weight: 700; }
  .badge.off { background: #ef4444; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 20px; max-width: 1100px; margin: 0 auto; }
  @media(max-width:700px){ .grid { grid-template-columns: 1fr; } }

  .card { background: #1a1d2e; border: 1px solid #2d3148; border-radius: 12px; padding: 18px; }
  .card h2 { font-size: 0.85rem; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; margin-bottom: 14px; }

  /* Gauges */
  .gauges { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .gauge-wrap { text-align: center; }
  .gauge-label { font-size: 0.7rem; color: #94a3b8; margin-top: 4px; }
  .gauge-val { font-size: 1.1rem; font-weight: 700; color: #fff; }
  .gauge-unit { font-size: 0.65rem; color: #64748b; }
  svg.gauge { width: 80px; height: 80px; }

  /* Ciclo */
  .ciclos { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
  .btn-ciclo { flex: 1; min-width: 80px; padding: 8px; border: 1px solid #3b82f6; border-radius: 8px;
    background: transparent; color: #3b82f6; cursor: pointer; font-size: 0.8rem; transition: all .2s; }
  .btn-ciclo:hover, .btn-ciclo.activo { background: #3b82f6; color: #fff; }
  .btn-ciclo.auto { border-color: #a855f7; color: #a855f7; }
  .btn-ciclo.auto:hover, .btn-ciclo.auto.activo { background: #a855f7; color: #fff; }

  /* DTCs */
  .dtc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; max-height: 220px; overflow-y: auto; }
  .dtc-item { display: flex; align-items: center; gap: 6px; background: #0f1117; border: 1px solid #2d3148;
    border-radius: 6px; padding: 6px 8px; cursor: pointer; transition: border-color .2s; }
  .dtc-item:hover { border-color: #ef4444; }
  .dtc-item.activo { border-color: #ef4444; background: #1f0f0f; }
  .dtc-code { font-size: 0.75rem; font-weight: 700; color: #f87171; min-width: 52px; }
  .dtc-desc { font-size: 0.65rem; color: #94a3b8; line-height: 1.3; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #2d3148; flex-shrink: 0; }
  .dot.on { background: #ef4444; box-shadow: 0 0 6px #ef4444; }

  /* gravedad badge */
  .grav { font-size: 0.6rem; padding: 1px 5px; border-radius: 4px; margin-left: auto; flex-shrink: 0; }
  .grav.alta { background:#7f1d1d; color:#fca5a5; }
  .grav.media { background:#78350f; color:#fcd34d; }
  .grav.baja { background:#14532d; color:#86efac; }

  /* DTCs activos */
  .activos-list { min-height: 40px; }
  .dtc-activo-tag { display: inline-flex; align-items: center; gap: 4px; background: #7f1d1d;
    color: #fca5a5; border-radius: 6px; padding: 4px 8px; font-size: 0.75rem; margin: 3px; }
  .dtc-activo-tag button { background: none; border: none; color: #fca5a5; cursor: pointer; font-size: 0.9rem; line-height: 1; }

  /* Log */
  .log { background: #0f1117; border: 1px solid #2d3148; border-radius: 8px; padding: 10px;
    font-family: monospace; font-size: 0.72rem; height: 120px; overflow-y: auto; color: #4ade80; }

  .ciclo-badge { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; }
  .ciclo-ralenti  { background:#1e3a5f; color:#93c5fd; }
  .ciclo-acelerando { background:#3b1f00; color:#fcd34d; }
  .ciclo-crucero  { background:#14532d; color:#86efac; }
  .ciclo-frenando { background:#3b0764; color:#d8b4fe; }

  .btn-limpiar { width:100%; margin-top:10px; padding:8px; background:#1f2937; border:1px solid #374151;
    border-radius:8px; color:#94a3b8; cursor:pointer; font-size:0.8rem; }
  .btn-limpiar:hover { border-color:#ef4444; color:#f87171; }

  /* Estado pendiente (seleccionado pero no confirmado) */
  .dtc-item.pendiente { border-color: #f59e0b; background: #1c1500; }
  .dtc-item.pendiente .dot { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }

  /* Barra de confirmación */
  .confirm-bar { display:none; align-items:center; justify-content:space-between; gap:12px;
    background:#1c1500; border:1px solid #f59e0b; border-radius:10px; padding:10px 14px;
    margin-top:10px; }
  .confirm-bar.visible { display:flex; }
  .confirm-bar span { font-size:0.8rem; color:#fcd34d; }
  .btn-confirmar { padding:8px 18px; background:#f59e0b; border:none; border-radius:8px;
    color:#000; font-weight:700; cursor:pointer; font-size:0.82rem; }
  .btn-confirmar:hover { background:#fbbf24; }
  .btn-cancelar-sel { padding:8px 12px; background:transparent; border:1px solid #6b7280;
    border-radius:8px; color:#9ca3af; cursor:pointer; font-size:0.8rem; }
  .btn-cancelar-sel:hover { border-color:#ef4444; color:#f87171; }
</style>
</head>
<body>

<header>
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
  <h1>OBD Simulator — GEM Motors</h1>
  <span class="badge" id="badge-estado">● ONLINE</span>
</header>

<div class="grid">

  <!-- GAUGES -->
  <div class="card" style="grid-column: span 2">
    <h2>📊 Parámetros en tiempo real</h2>
    <div class="gauges" id="gauges-container">
      <!-- se renderizan con JS -->
    </div>
  </div>

  <!-- CONTROL DE CICLO -->
  <div class="card">
    <h2>🚗 Ciclo de conducción</h2>
    <div class="ciclos">
      <button class="btn-ciclo auto activo" onclick="setCiclo('auto')">🔄 Auto</button>
      <button class="btn-ciclo" onclick="setCiclo('ralenti')">🅿️ Ralentí</button>
      <button class="btn-ciclo" onclick="setCiclo('acelerando')">⚡ Acelerando</button>
      <button class="btn-ciclo" onclick="setCiclo('crucero')">🛣️ Crucero</button>
      <button class="btn-ciclo" onclick="setCiclo('frenando')">🛑 Frenando</button>
    </div>
    <div>Estado: <span id="ciclo-actual" class="ciclo-badge ciclo-ralenti">ralenti</span></div>
    <div style="margin-top:10px; font-size:0.75rem; color:#64748b">
      Tiempo encendido: <span id="tiempo-enc">0s</span> &nbsp;|&nbsp;
      Km: <span id="km-totales">0</span>
    </div>
  </div>

  <!-- DTCs ACTIVOS -->
  <div class="card">
    <h2>🔴 DTCs activos ahora</h2>
    <div class="activos-list" id="dtcs-activos-list">
      <span style="color:#4b5563;font-size:0.8rem">Sin fallos activos</span>
    </div>
    <button class="btn-limpiar" onclick="limpiarDTCs()">🧹 Limpiar todos los DTCs</button>
  </div>

  <!-- CATÁLOGO DTC -->
  <div class="card" style="grid-column: span 2">
    <h2>⚠️ Inyectar fallo — selecciona y confirma</h2>
    <div class="dtc-grid" id="dtc-catalogo">
      <!-- se renderizan con JS -->
    </div>
    <div class="confirm-bar" id="confirm-bar">
      <span id="confirm-msg">0 fallos seleccionados</span>
      <div style="display:flex;gap:8px">
        <button class="btn-cancelar-sel" onclick="cancelarSeleccion()">✕ Cancelar</button>
        <button class="btn-confirmar" onclick="confirmarSeleccion()">✔ Confirmar selección</button>
      </div>
    </div>
  </div>

  <!-- LOG -->
  <div class="card" style="grid-column: span 2">
    <h2>📋 Log de actividad</h2>
    <div class="log" id="log"></div>
  </div>

</div>

<script>
const PIDS = [
  { key: 'rpm',       label: 'RPM',         unit: 'rpm',  max: 8000, color: '#3b82f6' },
  { key: 'velocidad', label: 'Velocidad',    unit: 'km/h', max: 200,  color: '#22c55e' },
  { key: 'temp',      label: 'Temp. Ref.',   unit: '°C',   max: 120,  color: '#ef4444' },
  { key: 'carga',     label: 'Carga Motor',  unit: '%',    max: 100,  color: '#f59e0b' },
  { key: 'acelerador',label: 'Acelerador',   unit: '%',    max: 100,  color: '#a855f7' },
  { key: 'voltaje',   label: 'Voltaje',      unit: 'V',    max: 16,   color: '#06b6d4' },
]

// Render gauges SVG
const gc = document.getElementById('gauges-container')
PIDS.forEach(p => {
  gc.innerHTML += `
  <div class="gauge-wrap">
    <svg class="gauge" viewBox="0 0 80 80">
      <circle cx="40" cy="40" r="32" fill="none" stroke="#1e293b" stroke-width="8"/>
      <circle cx="40" cy="40" r="32" fill="none" stroke="${p.color}" stroke-width="8"
        stroke-dasharray="0 201" stroke-linecap="round"
        transform="rotate(-90 40 40)" id="arc-${p.key}" style="transition:stroke-dasharray .5s"/>
      <text x="40" y="38" text-anchor="middle" fill="#fff" font-size="13" font-weight="700" id="val-${p.key}">0</text>
      <text x="40" y="52" text-anchor="middle" fill="#64748b" font-size="7">${p.unit}</text>
    </svg>
    <div class="gauge-label">${p.label}</div>
  </div>`
})

// Render catálogo DTC
fetch('/dtc/catalogo').then(r=>r.json()).then(res => {
  const grid = document.getElementById('dtc-catalogo')
  Object.entries(res.data).forEach(([code, info]) => {
    grid.innerHTML += `
    <div class="dtc-item" id="dtc-item-${code}" onclick="toggleDTC('${code}')">
      <div class="dot" id="dot-${code}"></div>
      <div>
        <div class="dtc-code">${code}</div>
        <div class="dtc-desc">${info.descripcion}</div>
      </div>
      <span class="grav ${info.gravedad}">${info.gravedad}</span>
    </div>`
  })
})

function setCiclo(ciclo) {
  fetch('/motor/ciclo', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ciclo})})
  document.querySelectorAll('.btn-ciclo').forEach(b => b.classList.remove('activo'))
  event.target.classList.add('activo')
  log(`Ciclo cambiado a: ${ciclo}`)
}

const seleccionPendiente = new Set()

function toggleDTC(codigo) {
  // Si ya está activo en el simulador, lo desactiva directo (botón × de la lista)
  const estaActivo = document.getElementById(`dtc-item-${codigo}`)?.classList.contains('activo')
  if (estaActivo && !seleccionPendiente.has(codigo)) {
    fetch('/dtc/toggle', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({codigo})})
      .then(r=>r.json()).then(res => {
        log(`DTC ${codigo}: ⚪ desactivado`)
      })
    return
  }
  // Toggle en la selección pendiente
  if (seleccionPendiente.has(codigo)) {
    seleccionPendiente.delete(codigo)
    const item = document.getElementById(`dtc-item-${codigo}`)
    item.classList.remove('pendiente')
    if (!item.classList.contains('activo'))
      document.getElementById(`dot-${codigo}`).className = 'dot'
  } else {
    seleccionPendiente.add(codigo)
    document.getElementById(`dtc-item-${codigo}`).classList.add('pendiente')
    document.getElementById(`dot-${codigo}`).className = 'dot'
  }
  actualizarBarraConfirmacion()
}

function actualizarBarraConfirmacion() {
  const bar = document.getElementById('confirm-bar')
  const msg = document.getElementById('confirm-msg')
  if (seleccionPendiente.size > 0) {
    bar.classList.add('visible')
    msg.textContent = `${seleccionPendiente.size} fallo${seleccionPendiente.size > 1 ? 's' : ''} seleccionado${seleccionPendiente.size > 1 ? 's' : ''}`
  } else {
    bar.classList.remove('visible')
  }
}

function confirmarSeleccion() {
  const codigos = [...seleccionPendiente]
  Promise.all(codigos.map(c =>
    fetch('/dtc/toggle', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({codigo: c})})
      .then(r=>r.json())
  )).then(() => {
    log(`✔ Confirmados ${codigos.length} DTC(s): ${codigos.join(', ')}`)
    seleccionPendiente.clear()
    actualizarBarraConfirmacion()
  })
}

function cancelarSeleccion() {
  seleccionPendiente.forEach(c => {
    const item = document.getElementById(`dtc-item-${c}`)
    item.classList.remove('pendiente')
    if (!item.classList.contains('activo'))
      document.getElementById(`dot-${c}`).className = 'dot'
  })
  seleccionPendiente.clear()
  actualizarBarraConfirmacion()
}

function limpiarDTCs() {
  fetch('/dtc/limpiar', {method:'POST'}).then(() => log('🧹 Todos los DTCs limpiados'))
}

function log(msg) {
  const l = document.getElementById('log')
  const t = new Date().toLocaleTimeString()
  l.innerHTML += `[${t}] ${msg}\n`
  l.scrollTop = l.scrollHeight
}

// Actualizar dashboard cada 1.5s
function actualizarDashboard() {
  fetch('/dashboard').then(r=>r.json()).then(res => {
    const d = res.data
    PIDS.forEach(p => {
      const val = d[p.key]?.valor ?? 0
      document.getElementById(`val-${p.key}`).textContent = typeof val === 'number' ? val.toFixed(p.key==='voltaje'?1:0) : val
      const pct = Math.min(val / p.max, 1)
      const circ = 201
      document.getElementById(`arc-${p.key}`).setAttribute('stroke-dasharray', `${pct*circ} ${circ}`)
    })

    // Ciclo
    const ciclo = res.ciclo_conduccion
    const el = document.getElementById('ciclo-actual')
    el.textContent = ciclo
    el.className = `ciclo-badge ciclo-${ciclo}`

    // Tiempo y km
    const seg = res.tiempo_encendido
    document.getElementById('tiempo-enc').textContent = seg < 60 ? seg+'s' : Math.floor(seg/60)+'m '+seg%60+'s'
    document.getElementById('km-totales').textContent = Math.round(d.km_totales?.valor ?? 0).toLocaleString()

    // DTCs activos
    const dtcs = res.dtcs_activos
    const lista = document.getElementById('dtcs-activos-list')
    lista.innerHTML = dtcs.length === 0
      ? '<span style="color:#4b5563;font-size:0.8rem">Sin fallos activos</span>'
      : dtcs.map(d => `<span class="dtc-activo-tag">⚠️ ${d} <button onclick="toggleDTC('${d}')">×</button></span>`).join('')

    // Sincronizar dots del catálogo
    document.querySelectorAll('.dot').forEach(dot => {
      const code = dot.id.replace('dot-','')
      const on = dtcs.includes(code)
      dot.className = 'dot' + (on ? ' on' : '')
      document.getElementById(`dtc-item-${code}`)?.classList.toggle('activo', on)
    })
  })
}

setInterval(actualizarDashboard, 1500)
actualizarDashboard()
log('🟢 Simulador iniciado')
</script>
</body>
</html>
"""

# ─────────────────────────────────────────
# ENDPOINTS API
# ─────────────────────────────────────────
@app.route("/")
def panel():
    return render_template_string(PANEL_HTML)

@app.route("/health")
def health():
    return jsonify({"status":"ok","servicio":"OBD Simulator GEM Motors",
                    "ciclo":motor["ciclo_conduccion"],
                    "tiempo_encendido":int(time.time()-motor["tiempo_inicio"])})

@app.route("/dashboard")
def dashboard():
    m = motor
    return jsonify({
        "success": True,
        "ciclo_conduccion": m["ciclo_conduccion"],
        "tiempo_encendido": int(time.time()-m["tiempo_inicio"]),
        "dtcs_activos": m["dtcs_activos"],
        "data": {
            "rpm":        {"valor": round(m["rpm"]),                        "hex": rpm_a_hex(m["rpm"]),   "unidad":"rpm"},
            "velocidad":  {"valor": round(m["velocidad"]),                  "hex": vel_a_hex(m["velocidad"]), "unidad":"km/h"},
            "temp":       {"valor": round(m["temperatura_refrigerante"],1), "hex": temp_a_hex(m["temperatura_refrigerante"]), "unidad":"°C"},
            "carga":      {"valor": round(m["carga_motor"],1),              "hex": carga_a_hex(m["carga_motor"]), "unidad":"%"},
            "acelerador": {"valor": round(m["acelerador"],1),               "hex": acel_a_hex(m["acelerador"]), "unidad":"%"},
            "temp_aire":  {"valor": round(m["temperatura_aire"],1),         "hex": aire_a_hex(m["temperatura_aire"]), "unidad":"°C"},
            "voltaje":    {"valor": round(m["voltaje_bateria"],2),           "hex": volt_a_hex(m["voltaje_bateria"]), "unidad":"V"},
            "km_totales": {"valor": round(m["km_totales"]),                  "hex": "N/A", "unidad":"km"},
        }
    })

@app.route("/pid")
def pid():
    p = request.args.get("pid","").strip().upper()
    m = motor
    mapa = {
        "01 0C": {"valor":round(m["rpm"]),          "hex":rpm_a_hex(m["rpm"]),   "parametro":"RPM",          "unidad":"rpm"},
        "01 0D": {"valor":round(m["velocidad"]),     "hex":vel_a_hex(m["velocidad"]), "parametro":"Velocidad","unidad":"km/h"},
        "01 05": {"valor":round(m["temperatura_refrigerante"],1), "hex":temp_a_hex(m["temperatura_refrigerante"]), "parametro":"Temperatura","unidad":"°C"},
        "01 04": {"valor":round(m["carga_motor"],1), "hex":carga_a_hex(m["carga_motor"]), "parametro":"Carga Motor","unidad":"%"},
        "01 11": {"valor":round(m["acelerador"],1),  "hex":acel_a_hex(m["acelerador"]), "parametro":"Acelerador","unidad":"%"},
        "01 0F": {"valor":round(m["temperatura_aire"],1), "hex":aire_a_hex(m["temperatura_aire"]), "parametro":"Temp Aire","unidad":"°C"},
        "01 42": {"valor":round(m["voltaje_bateria"],2), "hex":volt_a_hex(m["voltaje_bateria"]), "parametro":"Voltaje","unidad":"V"},
        "03":    {"valor":m["dtcs_activos"], "hex":dtcs_a_hex(m["dtcs_activos"]), "parametro":"DTCs","unidad":"codigos"},
        "04":    {"valor":"OK", "hex":"44", "parametro":"Limpiar DTCs","unidad":""},
        "AT Z":  {"valor":"ELM327 v2.1","hex":"ELM327 v2.1","parametro":"Reset","unidad":""},
        "AT DP": {"valor":"ISO 15765-4 (CAN)","hex":"ISO 15765-4 (CAN)","parametro":"Protocolo","unidad":""},
    }
    if p == "04":
        m["dtcs_activos"] = []
    resultado = mapa.get(p, {"valor":None,"hex":"NO DATA","parametro":"Desconocido","unidad":""})
    return jsonify({"success":True,"data":resultado})

@app.route("/dtc/catalogo")
def catalogo():
    g = request.args.get("gravedad")
    c = request.args.get("categoria")
    res = CATALOGO_DTC
    if g: res = {k:v for k,v in res.items() if v["gravedad"]==g}
    if c: res = {k:v for k,v in res.items() if v["categoria"]==c}
    return jsonify({"success":True,"total":len(res),"data":res})

@app.route("/dtc/interpretar/<codigo>")
def interpretar(codigo):
    c = codigo.upper()
    if c in CATALOGO_DTC:
        return jsonify({"success":True,"data":{"codigo":c,**CATALOGO_DTC[c],"encontrado":True}})
    return jsonify({"success":True,"data":{"codigo":c,"descripcion":"No encontrado","encontrado":False}})

@app.route("/dtc/toggle", methods=["POST"])
def toggle_dtc():
    codigo = request.json.get("codigo","").upper()
    if codigo in motor["dtcs_activos"]:
        motor["dtcs_activos"].remove(codigo)
        return jsonify({"success":True,"codigo":codigo,"activo":False})
    else:
        motor["dtcs_activos"].append(codigo)
        return jsonify({"success":True,"codigo":codigo,"activo":True})

@app.route("/dtc/limpiar", methods=["POST"])
def limpiar_dtcs():
    motor["dtcs_activos"] = []
    return jsonify({"success":True,"mensaje":"DTCs limpiados"})

@app.route("/motor/ciclo", methods=["POST"])
def set_ciclo():
    ciclo = request.json.get("ciclo","auto")
    if ciclo == "auto":
        motor["ciclo_manual"] = False
    else:
        motor["ciclo_conduccion"] = ciclo
        motor["ciclo_manual"] = True
        motor["tiempo_ciclo"] = 0
    return jsonify({"success":True,"ciclo":ciclo})

@app.route("/motor/estado")
def estado():
    m = motor
    return jsonify({"success":True,"data":{
        "ciclo":m["ciclo_conduccion"],
        "tiempo_encendido_seg":int(time.time()-m["tiempo_inicio"]),
        "temperatura":round(m["temperatura_refrigerante"],1),
        "motor_caliente":m["temperatura_refrigerante"]>=85,
        "dtcs_activos":m["dtcs_activos"],
        "km_totales":round(m["km_totales"])
    }})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
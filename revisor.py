# ============================================================================
# NIVEL 1: revisor.py — genera la página local de revisión de duplicados
# ============================================================================
# El importador decide "duplicado / dudoso / nueva" con una heurística de
# texto, pero la decisión final es humana: sólo mirando las dos canciones
# COMPLETAS, lado a lado, se ve si son la misma o no. Comparar fragmentos
# ya demostró llevar a errores.
# Cuando son la misma, no alcanza con descartar la candidata: hay que
# poder elegir CUÁL de las dos versiones es la correcta -- la que está en
# el catálogo puede ser la peor (incompleta, con errores). La elegida se
# queda, la otra se elimina.
# Genera un HTML local (no se publica en ningún lado) + un JSON de
# veredictos que después aplica importar.py --veredictos.

import json

PLANTILLA = """<!doctype html>
<meta charset="utf-8">
<title>Revisar duplicados — Cancionero</title>
<style>
  :root{
    --fondo:#0E1116; --superficie:#171C24; --superficie-alta:#1F2632;
    --borde:#2A3240; --letra:#E8EDF2; --tenue:#8A94A6;
    --acento:#00B0F0; --si:#3FB950; --no:#F85149; --duda:#D29922;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--fondo);color:var(--letra);
       font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
  header{position:sticky;top:0;z-index:10;background:var(--superficie);
         border-bottom:1px solid var(--borde);padding:12px 16px;
         display:flex;gap:12px;align-items:center;flex-wrap:wrap}
  .contador{font-weight:600;font-size:16px}
  .clase{font-size:12px;padding:3px 10px;border-radius:20px;
         border:1px solid var(--borde);color:var(--tenue)}
  .clase.duplicado{color:var(--no);border-color:var(--no)}
  .clase.dudoso{color:var(--duda);border-color:var(--duda)}
  .motivo{color:var(--tenue);font-size:13px;margin-left:auto}
  main{padding:16px;max-width:1400px;margin:0 auto}
  .par{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}
  @media(max-width:900px){.par{grid-template-columns:1fr}}
  .lado{background:var(--superficie);border:2px solid var(--borde);
        border-radius:10px;overflow:hidden;min-width:0;
        display:flex;flex-direction:column}
  .lado.elegida{border-color:var(--si)}
  .lado h2{margin:0;padding:12px 14px;font-size:15px;
           border-bottom:1px solid var(--borde);background:var(--superficie-alta)}
  .lado .origen{display:block;font-weight:600;font-size:11px;
                margin-top:5px;letter-spacing:.4px;text-transform:uppercase}
  .lado .origen.ya{color:var(--acento)}      /* ya está en el cancionero */
  .lado .origen.nueva{color:var(--duda)}     /* viene del archivo a importar */
  .lado .origen .meta{color:var(--tenue);font-weight:400;text-transform:none;
                      letter-spacing:0}
  .cuerpo{padding:12px 14px;white-space:pre-wrap;overflow-wrap:anywhere;
          font-family:ui-monospace,Consolas,monospace;font-size:14px;line-height:1.7}
  .cuerpo .dif{background:rgba(210,153,34,.22);border-radius:3px;
               box-shadow:0 0 0 2px rgba(210,153,34,.22)}
  .acordes{color:var(--acento)}
  .rotulo{color:#BFBFBF;font-style:italic}
  .elegir{margin:0;padding:12px 14px;border-top:1px solid var(--borde);
          background:var(--superficie-alta);display:flex;gap:8px}
  .elegir button{flex:1}
  .elegir button.editar{flex:0 0 auto}
  button.editar{border-color:var(--tenue);color:var(--tenue)}
  button.editar.activo{border-color:var(--duda);color:var(--duda)}
  /* La letra se edita con la misma tipografía monoespaciada con que se
     muestra: los espacios son contenido (alinean el acorde sobre la
     sílaba), así que el textarea tiene que respetarlos igual. */
  .editor{width:100%;min-height:340px;background:var(--fondo);
          color:var(--letra);border:1px solid var(--duda);border-radius:6px;
          padding:12px 14px;font-family:ui-monospace,Consolas,monospace;
          font-size:14px;line-height:1.7;white-space:pre;overflow-wrap:normal;
          overflow-x:auto;resize:vertical}
  .editado{font-size:11px;color:var(--duda);padding:0 14px 10px}
  footer{position:sticky;bottom:0;background:var(--superficie);
         border-top:1px solid var(--borde);padding:12px 16px;
         display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  button{font:inherit;padding:10px 16px;border-radius:8px;cursor:pointer;
         border:1px solid var(--borde);background:var(--superficie-alta);
         color:var(--letra)}
  button:hover{border-color:var(--tenue)}
  button.quedarme{border-color:var(--si);color:var(--si);font-weight:600}
  button.quedarme.activa{background:rgba(63,185,80,.18)}
  button.distintas{border-color:var(--acento);color:var(--acento)}
  button.distintas.activa{background:rgba(0,176,240,.18)}
  button.saltear{color:var(--tenue)}
  button.cortar{border-color:var(--duda);color:var(--duda)}
  .nav{margin-left:auto;display:flex;gap:8px}
  .marca{font-size:13px;padding:4px 10px;border-radius:6px;color:var(--tenue)}
  #resumen{padding:16px;max-width:1400px;margin:0 auto}
  #resumen textarea{width:100%;height:260px;background:var(--superficie);
    color:var(--letra);border:1px solid var(--borde);border-radius:8px;
    padding:12px;font-family:ui-monospace,Consolas,monospace;font-size:13px}
  .oculto{display:none}
  .listo{text-align:center;padding:30px 16px 0}
  .listo h1{color:var(--si);margin-bottom:6px}
  .ayuda{color:var(--tenue);font-size:13px;padding:0 16px 10px;
         max-width:1400px;margin:0 auto}
</style>

<header>
  <span class="contador" id="contador"></span>
  <span class="clase" id="clase"></span>
  <span class="motivo" id="motivo"></span>
</header>

<main id="vista">
  <p class="ayuda">A la <b>izquierda</b>, la que <span style="color:var(--duda)">recién
     llega</span> y todavía no está guardada. A la <b>derecha</b>, la que
     <span style="color:var(--acento)">ya está en el cancionero</span>
     (salvo que el rótulo diga otra cosa: a veces las dos son nuevas, porque el
     archivo trae la misma canción repetida).<br>
     Si son la <b>misma canción</b>, elegí cuál se queda: la otra se elimina.
     Si son <b>dos canciones distintas</b>, quedan las dos.
     En amarillo, lo que <b>no</b> aparece del otro lado.</p>
  <div class="par">
    <div class="lado" id="lado-izq">
      <h2 id="t-izq"></h2>
      <div class="editado oculto" id="marca-ed-izq">letra corregida</div>
      <div class="cuerpo" id="c-izq"></div>
      <div class="elegir">
        <button class="quedarme" id="btn-izq" onclick="quedarme('candidata')">
          Quedarme con ESTA
        </button>
        <button class="editar" id="ed-izq" onclick="alternarEdicion('izq')">
          Corregir letra
        </button>
      </div>
    </div>
    <div class="lado" id="lado-der">
      <h2 id="t-der"></h2>
      <div class="editado oculto" id="marca-ed-der">letra corregida</div>
      <div class="cuerpo" id="c-der"></div>
      <div class="elegir">
        <button class="quedarme" id="btn-der" onclick="quedarme('existente')">
          Quedarme con ESTA
        </button>
        <button class="editar" id="ed-der" onclick="alternarEdicion('der')">
          Corregir letra
        </button>
      </div>
    </div>
  </div>
</main>

<div class="listo oculto" id="listo">
  <h1 id="listo-titulo">Revisión terminada</h1>
  <p>Copiá este resultado y pegámelo en el chat.<br>
     <span style="color:var(--tenue);font-size:13px">Lo decidido queda guardado:
     si volvés a abrir esta página, seguís donde dejaste.</span></p>
</div>

<div id="resumen" class="oculto">
  <textarea id="salida" readonly></textarea>
  <p>
    <button onclick="copiar()">Copiar al portapapeles</button>
    <button onclick="bajarJson()">Descargar veredictos.json</button>
    <button onclick="volver()">Volver a revisar</button>
  </p>
</div>

<footer id="pie">
  <button class="quedarme" id="pie-izq" onclick="quedarme('candidata')">
    ← Queda la izquierda
  </button>
  <button class="quedarme" id="pie-der" onclick="quedarme('existente')">
    Queda la derecha →
  </button>
  <button class="distintas" id="btn-dist" onclick="marcarDistintas()">
    Son DOS distintas
  </button>
  <button class="saltear" onclick="saltear()">Decidir después</button>
  <span class="marca" id="marca"></span>
  <span class="nav">
    <button onclick="ir(-1)">←</button>
    <button onclick="ir(1)">→</button>
    <button class="cortar" onclick="terminar()">Cortar acá y guardar</button>
  </span>
</footer>

<script>
const PARES = __DATOS__;

/* Las decisiones se guardan en localStorage después de cada una: una
   revisión de cientos de pares no puede perderse por recargar sin
   querer, cerrar la pestaña o que se corte la luz. La clave incluye la
   cantidad de pares para no mezclar dos revisiones distintas. */
const CLAVE = "cancionero:revision:" + PARES.length;
let veredictos = {};
let ediciones = {};   /* id -> {izq:[bloques], der:[bloques]} corregidos a mano */
try {
  const g = JSON.parse(localStorage.getItem(CLAVE)) || {};
  veredictos = g.veredictos || g;   /* 'g' pelado: formato viejo, sin ediciones */
  ediciones = g.ediciones || {};
} catch(e){}

const editando = {izq:false, der:false};

function guardar(){
  try { localStorage.setItem(CLAVE, JSON.stringify({veredictos, ediciones})); } catch(e){}
}

/* Arranca en el primero sin decidir, no en el 1: al volver se sigue
   donde se dejó en vez de recorrer de nuevo lo ya revisado. */
let i = PARES.findIndex(p => !veredictos[p.id]);
if (i < 0) i = 0;

function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function normalizar(l){
  return l.toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"")
          .replace(/[^a-z0-9 ]/g," ").replace(/\\s+/g," ").trim();
}
/* Resalta lo que no aparece del otro lado: lo que hay que mirar son las
   diferencias, no releer lo que ya coincide. */
function pintar(bloques, otrasLineas){
  const otras = new Set(otrasLineas.map(normalizar).filter(Boolean));
  return bloques.map(b => {
    if (b.t === "v") return "";
    const txt = b.v || "";
    if (b.t === "r") return '<span class="rotulo">' + esc(txt) + '</span>';
    if (b.t === "a") return '<span class="acordes">' + esc(txt) + '</span>';
    const n = normalizar(txt);
    return (n && !otras.has(n)) ? '<span class="dif">' + esc(txt) + '</span>' : esc(txt);
  }).join("\\n");
}
function lineasDe(bloques){ return bloques.filter(b => b.t === "l").map(b => b.v || ""); }

/* --- Corregir la letra -------------------------------------------------
   Mismo dialecto que el editor de la app (':Rótulo', '>fuerza acorde',
   '.fuerza letra', linea en blanco = separador, sin marca = se detecta
   solo). Es un puerto de textoABloques()/bloquesATexto(): si acá se
   usara otro formato, lo corregido no volveria igual al cancionero. */
const RE_CIFRADO = /^[A-G](?:#|b)?(?:maj|Maj|M|min|m|sus|add|dim|aug|°|ø|\\+|-|[0-9]|#|b|\\(|\\)|,)*$/;
const RE_ADORNO = /^(\\|\\||\\||\\/\\/|\\/|-|–|x\\d+|\\(x\\d+\\))$/;

function esCifrado(tok){
  if (RE_ADORNO.test(tok)) return true;
  const partes = tok.split("/");
  return partes.length > 0 && partes.every(p => p && RE_CIFRADO.test(p));
}
function esLineaDeAcordes(t){
  const toks = t.split(/\\s+/).filter(Boolean);
  return toks.length > 0 && toks.every(esCifrado);
}
function bloquesATexto(bloques){
  return bloques.map(b => {
    if (b.t === "v") return "";
    const v = b.v || "";
    if (b.t === "r") return ":" + v;
    if (b.t === "a") return esLineaDeAcordes(v) ? v : ">" + v;
    return esLineaDeAcordes(v) ? "." + v : v;
  }).join("\\n");
}
function textoABloques(txt){
  const salida = [];
  let vacioPendiente = false;
  txt.replace(/\\r/g, "").split("\\n").forEach(linea => {
    if (!linea.trim()){ vacioPendiente = true; return; }
    if (vacioPendiente && salida.length) salida.push({t:"v"});
    vacioPendiente = false;
    const marca = linea[0];
    if (marca === ":") salida.push({t:"r", v: linea.slice(1).trim()});
    else if (marca === ">") salida.push({t:"a", v: linea.slice(1)});
    else if (marca === ".") salida.push({t:"l", v: linea.slice(1).trim()});
    else if (esLineaDeAcordes(linea)) salida.push({t:"a", v: linea});
    else salida.push({t:"l", v: linea.trim()});
  });
  return salida;
}

/* Bloques efectivos de un lado: los corregidos si se editó, si no los
   originales. Todo lo que dibuja o compara pasa por acá. */
function bloquesDe(p, lado){
  const ed = ediciones[p.id] && ediciones[p.id][lado];
  return ed ? ed : (lado === "izq" ? p.cand_bloques : p.ex_bloques);
}

function alternarEdicion(lado){
  if (editando[lado]) { guardarEdicion(lado); return; }
  const p = PARES[i];
  const cont = document.getElementById("c-" + lado);
  const ta = document.createElement("textarea");
  ta.className = "editor";
  ta.id = "ta-" + lado;
  ta.value = bloquesATexto(bloquesDe(p, lado));
  cont.innerHTML = "";
  cont.appendChild(ta);
  editando[lado] = true;
  document.getElementById("ed-" + lado).textContent = "Guardar corrección";
  document.getElementById("ed-" + lado).className = "editar activo";
}

function guardarEdicion(lado){
  const p = PARES[i];
  const ta = document.getElementById("ta-" + lado);
  if (ta){
    const bloques = textoABloques(ta.value);
    const original = lado === "izq" ? p.cand_bloques : p.ex_bloques;
    if (!ediciones[p.id]) ediciones[p.id] = {};
    if (JSON.stringify(bloques) === JSON.stringify(original)){
      delete ediciones[p.id][lado];                       /* volvió al original */
      if (!Object.keys(ediciones[p.id]).length) delete ediciones[p.id];
    } else {
      ediciones[p.id][lado] = bloques;
    }
    guardar();
  }
  editando[lado] = false;
  render();
}

function render(){
  const p = PARES[i];
  const decididas = Object.keys(veredictos).length;
  document.getElementById("contador").textContent =
    (i+1) + " / " + PARES.length + "  ·  " + decididas + " decididas";
  const cl = document.getElementById("clase");
  cl.textContent = p.clase === "duplicado" ? "yo dije: duplicada" : "yo dije: dudosa";
  cl.className = "clase " + p.clase;
  document.getElementById("motivo").textContent =
    "coincide por " + p.por + " (" + p.ratio + "%)";

  /* El rótulo dice si esa versión ya está guardada o si recién llega:
     es el dato con el que se decide, así que va destacado y con color
     propio, no como texto gris al lado del título. */
  const rotulo = (nombre, origen, meta) => {
    const ya = origen.startsWith("YA ");
    return esc(nombre) + '<span class="origen ' + (ya ? "ya" : "nueva") + '">'
         + esc(origen) + ' <span class="meta">· ' + esc(meta) + '</span></span>';
  };
  document.getElementById("t-izq").innerHTML =
    rotulo(p.cand_nombre, p.cand_origen, p.cand_meta);
  document.getElementById("t-der").innerHTML =
    rotulo(p.ex_nombre, p.ex_origen, p.ex_meta);
  /* Se dibuja lo corregido, no lo original: el resaltado de diferencias
     tiene que reflejar el texto que realmente se va a guardar. */
  const bIzq = bloquesDe(p, "izq"), bDer = bloquesDe(p, "der");
  document.getElementById("c-izq").innerHTML = pintar(bIzq, lineasDe(bDer));
  document.getElementById("c-der").innerHTML = pintar(bDer, lineasDe(bIzq));
  editando.izq = editando.der = false;
  for (const lado of ["izq", "der"]){
    const btn = document.getElementById("ed-" + lado);
    btn.textContent = "Corregir letra";
    btn.className = "editar";
    const marca = document.getElementById("marca-ed-" + lado);
    const hay = ediciones[p.id] && ediciones[p.id][lado];
    marca.className = hay ? "editado" : "editado oculto";
  }

  const v = veredictos[p.id];
  const li = document.getElementById("lado-izq"), ld = document.getElementById("lado-der");
  const bi = document.getElementById("btn-izq"), bd = document.getElementById("btn-der");
  const bdist = document.getElementById("btn-dist");
  li.className = "lado"; ld.className = "lado";
  bi.className = "quedarme"; bd.className = "quedarme"; bdist.className = "distintas";
  const m = document.getElementById("marca");
  m.textContent = "";

  if (v && v.tipo === "misma"){
    if (v.quedarse === "candidata"){ li.className = "lado elegida"; bi.className = "quedarme activa";
      m.textContent = "se queda la de la IZQUIERDA, se elimina la de la derecha"; }
    else { ld.className = "lado elegida"; bd.className = "quedarme activa";
      m.textContent = "se queda la de la DERECHA, se elimina la de la izquierda"; }
  } else if (v && v.tipo === "distintas"){
    bdist.className = "distintas activa";
    m.textContent = "son distintas: quedan las dos";
  }
  window.scrollTo(0,0);
}

function avanzar(){
  if (i < PARES.length - 1){ i++; render(); } else { terminar(); }
}
function quedarme(cual){
  veredictos[PARES[i].id] = {tipo:"misma", quedarse:cual};
  guardar();
  avanzar();
}
function marcarDistintas(){
  veredictos[PARES[i].id] = {tipo:"distintas"};
  guardar();
  avanzar();
}
function saltear(){
  delete veredictos[PARES[i].id];
  guardar();
  avanzar();
}
function ir(d){
  const n = i + d;
  if (n >= 0 && n < PARES.length){ i = n; render(); }
  else if (n >= PARES.length) terminar();
}

function datosVeredictos(){
  return PARES.map(p => {
    const v = veredictos[p.id] || {tipo:"pendiente"};
    const e = ediciones[p.id] || {};
    return {id:p.id, candidata:p.cand_nombre, existente:p.ex_nombre,
            tipo:v.tipo, quedarse:v.quedarse || null,
            /* Bloques corregidos a mano, si los hay. El importador los
               aplica sobre la version que corresponda. */
            correccion_candidata: e.izq || null,
            correccion_existente: e.der || null};
  });
}
function terminar(){
  const quedaCand = [], quedaExist = [], distintas = [], pendientes = [];
  PARES.forEach(p => {
    const v = veredictos[p.id];
    if (!v) pendientes.push(p.cand_nombre + "  ~  " + p.ex_nombre);
    else if (v.tipo === "distintas") distintas.push(p.cand_nombre);
    else if (v.quedarse === "candidata") quedaCand.push("queda: " + p.cand_nombre + "   |   se elimina: " + p.ex_nombre);
    else quedaExist.push("queda: " + p.ex_nombre + "   |   se elimina: " + p.cand_nombre);
  });
  let t = "VEREDICTOS DE REVISIÓN\\n\\n";
  t += "MISMA — elegí la de la IZQUIERDA: " + quedaCand.length + "\\n";
  quedaCand.forEach(s => t += "  - " + s + "\\n");
  t += "\\nMISMA — elegí la de la DERECHA: " + quedaExist.length + "\\n";
  quedaExist.forEach(s => t += "  - " + s + "\\n");
  t += "\\nDISTINTAS — quedan las dos: " + distintas.length + "\\n";
  distintas.forEach(s => t += "  - " + s + "\\n");
  if (pendientes.length){
    t += "\\nSIN DECIDIR: " + pendientes.length + "\\n";
    pendientes.forEach(s => t += "  - " + s + "\\n");
  }
  const nEd = Object.keys(ediciones).length;
  if (nEd){
    t += "\\nCON LETRA CORREGIDA A MANO: " + nEd + "\\n";
    t += "  (para que se apliquen hace falta el archivo, no este texto:\\n";
    t += "   usá 'Descargar veredictos.json')\\n";
    PARES.forEach(p => {
      const e = ediciones[p.id]; if (!e) return;
      const lados = [e.izq ? "izquierda" : null, e.der ? "derecha" : null].filter(Boolean);
      t += "  - " + p.cand_nombre + "  [" + lados.join(" y ") + "]\\n";
    });
  }
  document.getElementById("salida").value = t;
  document.getElementById("listo-titulo").textContent =
    pendientes.length ? "Revisión cortada acá" : "Revisión terminada";
  document.getElementById("vista").classList.add("oculto");
  document.getElementById("pie").classList.add("oculto");
  document.getElementById("listo").classList.remove("oculto");
  document.getElementById("resumen").classList.remove("oculto");
}
function volver(){
  document.getElementById("vista").classList.remove("oculto");
  document.getElementById("pie").classList.remove("oculto");
  document.getElementById("listo").classList.add("oculto");
  document.getElementById("resumen").classList.add("oculto");
  render();
}
function copiar(){
  const t = document.getElementById("salida");
  t.select(); document.execCommand("copy");
}
function bajarJson(){
  const blob = new Blob([JSON.stringify(datosVeredictos(), null, 1)],
                        {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "veredictos.json";
  a.click();
}
document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft") ir(-1);
  if (e.key === "ArrowRight") ir(1);
});
render();
</script>
"""


def meta_de(c):
    """Línea corta con tono/bpm -- mismo criterio que muestra la app."""
    partes = [c.get("tono") or "sin tono"]
    if c.get("bpm"):
        partes.append(str(c["bpm"]) + " bpm")
    return " · ".join(partes)


def generar(pares, ruta="revisar_duplicados.html"):
    """pares: lista de dicts con id, clase, por, ratio, cand_*, ex_*."""
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(PLANTILLA.replace("__DATOS__", json.dumps(pares, ensure_ascii=False)))
    return ruta

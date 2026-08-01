// Ejecuta el JavaScript de la app en Node con un DOM mínimo simulado.
// No reemplaza probar en el celular, pero atrapa lo que más costó encontrar
// hasta ahora: funciones inexistentes, identificadores mal escritos y
// errores en tiempo de ejecución al dibujar.

const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(process.argv[2] || "plantilla.html", "utf8");
const catalogo = fs.readFileSync("catalogo.json", "utf8");
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join("\n");

// --- DOM simulado ---------------------------------------------------------
// Cada elemento es un Proxy que acepta cualquier propiedad, así no hay que
// enumerar toda la API del navegador. Lo que importa es que no explote.
const creados = [];
function elemento(id = "?") {
  const base = {
    id,
    className: "",
    textContent: "",
    innerHTML: "",
    value: "",
    disabled: false,
    scrollTop: 0,
    style: {},
    classList: {
      add() {}, remove() {}, toggle() {}, contains() { return false; },
    },
    appendChild(hijo) { creados.push(hijo); return hijo; },
    insertAdjacentHTML() {},
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return elemento("querySelector"); },
    querySelectorAll() { return []; },
    focus() {}, select() {}, blur() {},
    matches() { return false; },
    getBoundingClientRect() { return {top:0,left:0,width:0,height:0}; },
  };
  return new Proxy(base, {
    get(t, k) {
      if (k in t) return t[k];
      if (typeof k === "string" && k.startsWith("on")) return null;
      return undefined;
    },
    set(t, k, v) { t[k] = v; return true; },
  });
}

const registro = {};
global.document = {
  getElementById(id) {
    if (id === "datos-catalogo") {
      const e = elemento(id);
      e.textContent = catalogo;
      return e;
    }
    if (!registro[id]) registro[id] = elemento(id);
    return registro[id];
  },
  createElement: () => elemento("creado"),
  addEventListener() {},
  documentElement: { requestFullscreen: async () => {} },
  exitFullscreen: async () => {},
  fullscreenElement: null,
  visibilityState: "visible",
};
global.window = { storage: undefined };
global.navigator = { clipboard: { writeText: async () => {} } };
global.localStorage = {
  datos: {},
  getItem(k) { return this.datos[k] ?? null; },
  setItem(k, v) { this.datos[k] = String(v); },
};
global.confirm = () => true;
global.alert = () => {};
global.setInterval = () => 0;
global.setTimeout = (f) => { if (typeof f === "function") f(); return 0; };
global.clearTimeout = () => {};

// --- Ejecutar -------------------------------------------------------------
let fallo = null;
process.on("unhandledRejection", e => { fallo = e; });

try {
  // El script llama arrancar() al final, que a su vez intenta conectar.
  // Sin projectId configurado tiene que degradar sin romperse.
  eval(js + `
    ;globalThis.__app = {
      get CATALOGO(){ return CATALOGO },
      get est(){ return est },
      get PORID(){ return PORID },
      pintarCatalogo, pintarReunion, abrir, pintarLector, abrirEditor,
      refrescarPrevia, abrirExportar, alternarEnLista,
      bloquesATexto, textoABloques, guardarEditor,
    };
  `);
} catch (e) {
  fallo = e;
}

// Dar una vuelta al bucle de eventos para que corran las promesas
setImmediate(() => {
  if (fallo) {
    console.log("FALLA al ejecutar:", fallo.message);
    console.log(fallo.stack.split("\n").slice(0, 5).join("\n"));
    process.exit(1);
  }

  // --- Ejercitar los caminos que el usuario recorre de verdad ------------
  const pasos = [];
  function paso(nombre, fn) {
    try { fn(); pasos.push(["ok", nombre]); }
    catch (e) { pasos.push(["FALLA", nombre + " -> " + e.message]); }
  }

  paso("catálogo cargado (96 canciones)", () => {
    if (__app.CATALOGO.length !== 96) throw new Error("hay " + __app.CATALOGO.length);
  });
  paso("dibujar la lista de canciones", () => __app.pintarCatalogo());
  paso("sumar una canción a la reunión", () => __app.alternarEnLista(__app.CATALOGO[0].id));
  paso("dibujar la pestaña Reunión", () => { __app.est.pestana = "reunion"; __app.pintarReunion(); });
  paso("abrir una canción en el lector", () => __app.abrir(__app.CATALOGO[0].id, false));
  paso("transportar +2 semitonos", () => { __app.est.semis = 2; __app.pintarLector(); });
  paso("entrar en modo reunión", () => { __app.est.enReunion = true; __app.est.posicion = 0; __app.pintarLector(); });
  paso("abrir el editor de una canción", () => __app.abrirEditor(__app.CATALOGO[0].id));
  paso("abrir el editor de canción nueva", () => __app.abrirEditor("nueva"));
  paso("vista previa del editor", () => __app.refrescarPrevia());
  paso("pantalla de exportar", () => __app.abrirExportar());
  paso("reordenar el evento (modo Reordenar)", () => {
    __app.est.pestana = "reunion";
    __app.est.lista.ids = [__app.CATALOGO[0].id, __app.CATALOGO[1].id];
    __app.est.reordenando = true;
    __app.pintarReunion();
    __app.est.reordenando = false;
  });

  paso("guardar una edición sin nube configurada", () => {
    __app.abrirEditor(__app.CATALOGO[0].id);
    document.getElementById("ed-nombre").value = "Prueba";
    document.getElementById("ed-cuerpo").value = ":Coro\n| G | D |\nletra de prueba";
    __app.guardarEditor();
  });
  paso("ida y vuelta de una canción real", () => {
    const c = __app.CATALOGO[5];
    const v = __app.textoABloques(__app.bloquesATexto(c.bloques));
    if (JSON.stringify(v) !== JSON.stringify(c.bloques)) throw new Error("no vuelve igual");
  });

  let malos = 0;
  for (const [estado, nombre] of pasos) {
    console.log((estado === "ok" ? "ok    " : "FALLA ") + nombre);
    if (estado !== "ok") malos++;
  }
  console.log("\n" + (pasos.length - malos) + "/" + pasos.length + " pasos sin error");
  process.exit(malos ? 1 : 0);
});

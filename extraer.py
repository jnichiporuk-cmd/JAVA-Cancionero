# EXTRACTOR del cancionero .docx -> catálogo JSON para la app.
#
# Criterio: sólo se exportan las canciones "limpias", es decir aquellas donde
# el estilo de Word de cada párrafo coincide con lo que el párrafo realmente
# es. Las que tienen líneas ambiguas quedan afuera y se listan aparte, para
# revisarlas de a una. Así ninguna canción entra a la app con contenido
# clasificado a fuerza de suposición.

import json
import re
import unicodedata
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# --- Lectura del XML -------------------------------------------------------

def estilo_de(p):
    pPr = p.find(W + "pPr")
    if pPr is None:
        return "Normal"
    s = pPr.find(W + "pStyle")
    return s.get(W + "val") if s is not None else "Normal"


def texto_de(p):
    """Texto del párrafo conservando los espacios exactos. Los espacios son
    contenido acá: son los que alinean el acorde sobre la sílaba."""
    o = []
    for n in p.iter():
        if n.tag == W + "t":
            o.append(n.text or "")
        elif n.tag == W + "tab":
            o.append("    ")
    return "".join(o).replace("\n", "").rstrip()


# --- Detector de acordes (mismo que en la auditoría) -----------------------
NOTA = r"[A-G](?:#|b)?"
SUFIJO = r"(?:maj|Maj|M|min|m|sus|add|dim|aug|°|ø|\+|\-|[0-9]|#|b|\(|\)|,)*"
RE_ACORDE = re.compile(rf"^{NOTA}{SUFIJO}$")
RE_ADORNO = re.compile(r"^(\||\|\||//|/|-|–|x\d+|\(x\d+\)|:)$")


def es_acorde(tok):
    if RE_ADORNO.match(tok):
        return True
    partes = tok.split("/")
    return all(partes) and all(RE_ACORDE.match(x) for x in partes)


def es_linea_de_acordes(t):
    toks = t.split()
    return bool(toks) and all(es_acorde(x) for x in toks)


# --- Título: Nombre - Tono - BPM ------------------------------------------
RE_TONO = re.compile(r"^[A-G](?:#|b)?(?:m|maj|min)?[0-9]*$")


def partir_titulo(bruto):
    """Devuelve (nombre, tono, bpm). tono y bpm pueden ser None.
    No inventa nada: si el tono no está o no se puede identificar con
    certeza, vuelve None y la app desactiva el transporte."""
    t = bruto.replace("\u2013", "-").replace("\u2014", "-")   # guion largo -> corto
    t = re.sub(r"\s*-\s*", " - ", t).strip()                  # normalizar espacios del guion
    partes = [x.strip() for x in t.split(" - ")]

    bpm = None
    if len(partes) >= 2 and re.fullmatch(r"\d+", partes[-1]):
        bpm = int(partes[-1])
        partes = partes[:-1]

    tono = None
    if len(partes) >= 2 and RE_TONO.match(partes[-1]):
        tono = partes[-1]
        partes = partes[:-1]

    return " - ".join(partes), tono, bpm


def hacer_id(nombre, tono, usados):
    base = "".join(c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:44]
    cand = base + ("-" + tono.lower().replace("#", "s") if tono else "")
    n = cand
    i = 2
    while n in usados:            # dos versiones del mismo tono: sufijo numérico
        n = f"{cand}-{i}"
        i += 1
    usados.add(n)
    return n


# --- Recorrido y armado ----------------------------------------------------
NO_SON_CANCIONES = {"Glorario", "Guía de formato del cancionero"}

arbol = etree.parse("desarmado/word/document.xml")
parrafos = arbol.getroot().find(W + "body").findall(W + "p")

crudas = []      # una entrada por ocurrencia de título
actual = None
for i, p in enumerate(parrafos):
    e = estilo_de(p)
    t = texto_de(p)
    if e == "Ttulo1" and t.strip():
        actual = {"p": i, "titulo": t.strip(), "parrafos": []}
        crudas.append(actual)
        continue
    if actual is not None:
        actual["parrafos"].append((e, t))

# Descartar lo que no es canción
crudas = [c for c in crudas if c["titulo"] not in NO_SON_CANCIONES]

limpias, sucias = [], []
usados = set()

for c in crudas:
    problemas = []
    bloques = []
    vacio_pendiente = False

    for e, t in c["parrafos"]:
        if not t.strip():
            vacio_pendiente = True          # varias vacías seguidas -> una sola
            continue

        # ¿El estilo dice lo mismo que el contenido?
        if e == "HTMLconformatoprevio":
            problemas.append(("estilo-sin-formatear", t))
            continue
        if e == "Estilo1" and not es_linea_de_acordes(t):
            problemas.append(("letra-en-acordes", t))
            continue
        if e == "Normal" and es_linea_de_acordes(t):
            problemas.append(("acorde-en-letra", t))
            continue
        if e == "Subttulo" and es_linea_de_acordes(t) and len(t.split()) > 1:
            problemas.append(("acorde-en-rotulo", t))
            continue

        if vacio_pendiente and bloques:
            bloques.append({"t": "v"})
        vacio_pendiente = False

        if e == "Subttulo":
            bloques.append({"t": "r", "v": t.strip()})
        elif e == "Estilo1":
            bloques.append({"t": "a", "v": t})
        else:
            bloques.append({"t": "l", "v": t.strip()})

    nombre, tono, bpm = partir_titulo(c["titulo"])
    registro = {
        "p": c["p"], "titulo": c["titulo"], "nombre": nombre,
        "tono": tono, "bpm": bpm, "bloques": bloques, "problemas": problemas,
    }
    # Un título sin ningún contenido es un lugar reservado, no una canción:
    # en la app se abriría en blanco. Va a la lista de pendientes.
    if not bloques:
        registro["problemas"].append(("sin-contenido", "el título no tiene nada debajo"))
        sucias.append(registro)
    elif problemas:
        sucias.append(registro)
    else:
        limpias.append(registro)

# Asignar id sólo a las que van a la app
for r in limpias:
    r["id"] = hacer_id(r["nombre"], r["tono"], usados)

# --- Informe ---------------------------------------------------------------
print(f"canciones totales : {len(crudas)}")
print(f"limpias (a la app): {len(limpias)}")
print(f"sucias (a revisar): {len(sucias)}")
print(f"sin tono en limpias: {sum(1 for r in limpias if not r['tono'])}")
print(f"sin bpm en limpias : {sum(1 for r in limpias if not r['bpm'])}")

print("\n--- LIMPIAS SIN TONO (transporte desactivado) ---")
for r in limpias:
    if not r["tono"]:
        print(f"  p{r['p']:5}  {r['titulo']!r}")

print("\n--- SUCIAS: tipo y cantidad de problemas ---")
from collections import Counter
for r in sorted(sucias, key=lambda x: -len(x["problemas"])):
    tipos = Counter(k for k, _ in r["problemas"])
    print(f"  p{r['p']:5}  {r['titulo'][:46]:46} {dict(tipos)}")

# --- Salidas ---------------------------------------------------------------
catalogo = [
    {"id": r["id"], "nombre": r["nombre"], "tono": r["tono"], "bpm": r["bpm"], "bloques": r["bloques"]}
    for r in sorted(limpias, key=lambda x: x["nombre"].lower())
]
with open("catalogo.json", "w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False, separators=(",", ":"))

with open("pendientes.json", "w", encoding="utf-8") as f:
    json.dump(sucias, f, ensure_ascii=False, indent=1)

print(f"\ncatalogo.json  -> {len(catalogo)} canciones")
print(f"pendientes.json -> {len(sucias)} canciones")

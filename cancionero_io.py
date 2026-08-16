# ============================================================================
# NIVEL 1: cancionero_io.py — módulo compartido de import/export
# ============================================================================
# Puerto a Python de la lógica texto<->bloques que ya usa el editor de la
# app (textoABloques()/bloquesATexto() en plantilla.html), para que
# importar.py y exportar.py compartan las mismas reglas que ve el usuario
# en el editor -- nunca duplicar la detección de acordes en dos lugares
# que puedan desalinearse con el tiempo.
# No se corre solo: lo importan importar.py y exportar.py.

import sys
import json
import re
import unicodedata
import subprocess

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================================
# NIVEL 2: Detección de líneas de acordes
# Puerto exacto de esCifrado()/esLineaDeAcordes() en plantilla.html
# (~línea 894-905). Mismos regex RE_CIFRADO/RE_ADORNO.
# ============================================================================

RE_CIFRADO = re.compile(
    r"^[A-G](?:#|b)?(?:maj|Maj|M|min|m|sus|add|dim|aug|°|ø|\+|-|[0-9]|#|b|\(|\)|,)*$"
)
RE_ADORNO = re.compile(r"^(\|\||\||\/\/|\/|-|–|x\d+|\(x\d+\))$")


def es_cifrado(tok):
    """Un token es acorde válido, o un adorno de ritmo (| // x2 etc)."""
    if RE_ADORNO.match(tok):
        return True
    partes = tok.split("/")
    return all(p and RE_CIFRADO.match(p) for p in partes)


def es_linea_de_acordes(linea):
    """Una línea es de acordes si TODOS sus tokens matchean como cifrado."""
    toks = linea.split()
    return len(toks) > 0 and all(es_cifrado(t) for t in toks)


# ============================================================================
# NIVEL 2: Texto plano <-> bloques
# Puerto exacto de textoABloques()/bloquesATexto() (~línea 907-939).
# Mismo dialecto que usa el editor: ':Rótulo', '>fuerza acorde',
# '.fuerza letra', línea en blanco = separador, sin marca = autodetecta.
# Este dialecto también cubre texto cifra-style pegado de sitios como
# cifraclub/lacuerda (acorde en línea propia arriba de la letra).
# ============================================================================

def texto_a_bloques(txt):
    salida = []
    vacio_pendiente = False
    for linea in txt.replace("\r", "").split("\n"):
        if not linea.strip():
            vacio_pendiente = True
            continue
        if vacio_pendiente and salida:
            salida.append({"t": "v"})
        vacio_pendiente = False
        marca = linea[0]
        if marca == ":":
            salida.append({"t": "r", "v": linea[1:].strip()})
        elif marca == ">":
            salida.append({"t": "a", "v": linea[1:]})
        elif marca == ".":
            salida.append({"t": "l", "v": linea[1:].strip()})
        elif es_linea_de_acordes(linea):
            salida.append({"t": "a", "v": linea})
        else:
            salida.append({"t": "l", "v": linea.strip()})
    return salida


def bloques_a_texto(bloques):
    """Inverso de texto_a_bloques(): para exportar."""
    lineas = []
    for b in bloques:
        t, v = b.get("t"), b.get("v", "")
        if t == "v":
            lineas.append("")
        elif t == "r":
            lineas.append(":" + v)
        elif t == "a":
            lineas.append(v if es_linea_de_acordes(v) else ">" + v)
        else:  # "l"
            lineas.append(("." + v) if es_linea_de_acordes(v) else v)
    return "\n".join(lineas)


# ============================================================================
# NIVEL 2: Generación de IDs
# Mismo algoritmo que hacer_id() de extraer.py, verificado idéntico a
# nuevoId() en plantilla.html -- por eso es seguro reusar el ID que ya
# tiene una canción en Firestore al graduarla a la capa base: no rompe
# reuniones guardadas que la referencien.
# ============================================================================

def generar_id(nombre, tono, usados):
    base = "".join(
        c for c in unicodedata.normalize("NFD", nombre)
        if unicodedata.category(c) != "Mn"
    )
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:44]
    cand = base + ("-" + tono.lower().replace("#", "s") if tono else "")
    n = cand
    i = 2
    while n in usados:
        n = f"{cand}-{i}"
        i += 1
    usados.add(n)
    return n


# ============================================================================
# NIVEL 2: Normalización para comparar (título y letra)
# ============================================================================

def normalizar_nombre(nombre):
    """Mismo criterio que ya usaban comparar_duplicados.py/limpiar_bien.py."""
    nombre = nombre.lower().strip()
    nombre = (nombre.replace("á", "a").replace("é", "e").replace("í", "i")
                     .replace("ó", "o").replace("ú", "u").replace("ü", "u"))
    return re.sub(r"\s+", " ", nombre)


def extraer_letra(bloques):
    """Sólo las líneas de letra (t='l'), unidas -- ignora acordes/rótulos
    porque lo que importa para detectar 'es la misma canción' es el
    contenido cantado, no cómo está transcripto el cifrado."""
    return " ".join(b.get("v", "") for b in bloques if b.get("t") == "l" and b.get("v"))


def normalizar_letra(texto):
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    texto = texto.lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# ============================================================================
# NIVEL 2: Catálogo existente (base + Firestore) y clasificación de duplicados
# ============================================================================

# Comparación por palabras significativas (Jaccard), no por caracteres:
# SequenceMatcher de caracteres da falsos positivos altos en títulos
# cortos que comparten substrings al azar ('alaba a Dios' vs 'vine a
# alabar a Dios' comparten 'a' y dan 75% con SequenceMatcher, pero son
# canciones distintas). Comparando por palabras, sin las vacías (stopwords
# como 'a', 'el', 'de'), el ruido baja mucho.
_STOPWORDS_ES = {
    "a", "al", "de", "del", "el", "la", "los", "las", "un", "una", "unos", "unas",
    "y", "o", "que", "en", "es", "mi", "tu", "su", "por", "para", "con", "sin",
    "se", "te", "le", "lo", "me", "nos", "ya", "no", "si", "mas", "esta", "este",
}

# Umbrales calibrados contra casos reales de este cancionero, revisados
# a mano por el usuario:
#  - 47% de letra distintiva = canciones DISTINTAS (dos cantos sobre el
#    mismo Salmo) -> tiene que quedar fuera incluso de "dudoso"
#  - 54% = MISMA canción con título distinto -> tiene que entrar
# Por eso el piso de "dudoso" por letra queda alto (0.50): entre esos dos
# valores hay poco margen, y equivocarse hacia "dudoso" de más significa
# hacerle revisar a mano casos obviamente distintos.
UMBRAL_DUPLICADO_TITULO = 0.80
UMBRAL_DUDOSO_TITULO = 0.60
UMBRAL_DUPLICADO_LETRA = 0.54
UMBRAL_DUDOSO_LETRA = 0.50

# Título corto ('A ti', 'Alaba') genera coincidencias artificiales por
# contención: cualquier título más largo que lo contenga da un Jaccard
# alto aunque sean canciones sin ninguna relación. Exigir que el título
# MÁS CORTO de los dos tenga al menos 2 palabras significativas evita
# ese caso -- verificado con casos reales confundiendo 'A ti'/'Alaba'
# con canciones completamente distintas.
MIN_PALABRAS_TITULO = 2

# Vocabulario típico del género (señor, dios, gloria, alabar...) aparece
# en casi todas las canciones del cancionero, así que compartirlo NO es
# evidencia de ser la misma canción -- es lo que hacía que cantos cortos
# distintos sobre el mismo versículo salieran como duplicados. En vez de
# mantener una lista a mano (que envejece mal), se calcula del propio
# catálogo: una palabra que aparece en más de este porcentaje de las
# canciones no distingue nada y se ignora al comparar.
UMBRAL_PALABRA_COMUN = 0.12

# Con el vocabulario común descartado, hace falta un mínimo de palabras
# distintivas de cada lado para que la comparación signifique algo: con
# 2 o 3 palabras raras compartidas por casualidad el Jaccard se dispara.
MIN_PALABRAS_DISTINTIVAS = 6


def palabras_significativas(texto_norm):
    """Set de palabras de 2+ letras, sin stopwords -- para comparar por
    Jaccard en vez de por caracteres."""
    return {p for p in texto_norm.split() if len(p) > 1 and p not in _STOPWORDS_ES}


def calcular_palabras_comunes(listas_de_palabras):
    """Palabras que aparecen en más de UMBRAL_PALABRA_COMUN del catálogo:
    vocabulario del género, sin poder distintivo. Se calcula del propio
    corpus en vez de listarlo a mano."""
    total = len(listas_de_palabras)
    if not total:
        return set()
    frecuencia = {}
    for palabras in listas_de_palabras:
        for p in palabras:
            frecuencia[p] = frecuencia.get(p, 0) + 1
    return {p for p, n in frecuencia.items() if n / total > UMBRAL_PALABRA_COMUN}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cargar_catalogo_existente(refrescar_firestore=True, incluir_firestore_nuevas=True):
    """Combina catalogo.json + Firestore (canciones nueva=true, sin las
    borradas) en una lista de entradas {id, nombre, nombre_norm,
    letra_norm, origen}. refrescar_firestore=True corre
    descargar_firestore.py antes de leer, para no comparar contra un
    snapshot viejo. incluir_firestore_nuevas=False se usa al graduar
    (fuente='firestore'): esas mismas 84 canciones no pueden ser el
    índice contra el que se comparan a sí mismas, o saldrían todas como
    'duplicado' de sí mismas."""
    if refrescar_firestore:
        print("Actualizando snapshot de Firestore...")
        subprocess.run([sys.executable, "descargar_firestore.py"], check=True)
        print()

    with open("catalogo.json", encoding="utf-8") as f:
        base = json.load(f)
    with open("firestore_canciones.json", encoding="utf-8") as f:
        fs_docs = json.load(f)

    borradas = {d["id"] for d in fs_docs if d.get("borrada")}

    existentes = []
    for c in base:
        if c["id"] in borradas:
            continue
        nombre_norm = normalizar_nombre(c["nombre"])
        letra_norm = normalizar_letra(extraer_letra(c.get("bloques", [])))
        existentes.append({
            "id": c["id"],
            "nombre": c["nombre"],
            "nombre_norm": nombre_norm,
            "nombre_palabras": palabras_significativas(nombre_norm),
            "letra_palabras": palabras_significativas(letra_norm),
            "origen": "catalogo.json",
        })
    if incluir_firestore_nuevas:
        for d in fs_docs:
            if d.get("nueva") and not d.get("borrada"):
                nombre_norm = normalizar_nombre(d["nombre"])
                letra_norm = normalizar_letra(extraer_letra(d.get("bloques", [])))
                existentes.append({
                    "id": d["id"],
                    "nombre": d["nombre"],
                    "nombre_norm": nombre_norm,
                    "nombre_palabras": palabras_significativas(nombre_norm),
                    "letra_palabras": palabras_significativas(letra_norm),
                    "origen": "firestore",
                })

    # Vocabulario común del cancionero, calculado del propio corpus.
    comunes = calcular_palabras_comunes([e["letra_palabras"] for e in existentes])
    for e in existentes:
        e["letra_distintiva"] = e["letra_palabras"] - comunes
    return {"canciones": existentes, "palabras_comunes": comunes}


def clasificar_duplicado(candidata_nombre_norm, candidata_letra_norm, indice):
    """Compara una candidata contra el índice de existentes por título Y
    por letra (pedido explícito: no alcanza con comparar sólo título).
    Devuelve (categoria, detalle) donde categoria es 'duplicado' | 'dudoso'
    | 'nueva'. 'dudoso' no se decide solo -- se lista para que la revise
    una persona, siguiendo el criterio del proyecto de no resolver
    ambigüedad con una regla ciega.

    'indice' es lo que devuelve cargar_catalogo_existente():
    {canciones: [...], palabras_comunes: set}."""
    canciones = indice["canciones"]
    comunes = indice["palabras_comunes"]

    cand_pal_titulo = palabras_significativas(candidata_nombre_norm)
    cand_distintiva = palabras_significativas(candidata_letra_norm) - comunes
    letra_comparable = len(cand_distintiva) >= MIN_PALABRAS_DISTINTIVAS

    if candidata_nombre_norm:
        for ex in canciones:
            if candidata_nombre_norm == ex["nombre_norm"]:
                # Título idéntico, pero si además hay letra comparable de
                # los dos lados y resulta ser otra canción, gana la letra:
                # dos canciones distintas pueden llamarse igual.
                if (letra_comparable and len(ex["letra_distintiva"]) >= MIN_PALABRAS_DISTINTIVAS
                        and _jaccard(cand_distintiva, ex["letra_distintiva"]) < UMBRAL_DUDOSO_LETRA):
                    break
                return "duplicado", {"por": "título", "existente": ex["nombre"], "ratio": 1.0}

    mejor_titulo = (0.0, None)
    mejor_letra = (0.0, None)
    for ex in canciones:
        # Título corto ('A ti') genera coincidencias artificiales por
        # contención: exigir que el más corto de los dos tenga al menos
        # MIN_PALABRAS_TITULO palabras propias.
        if min(len(cand_pal_titulo), len(ex["nombre_palabras"])) >= MIN_PALABRAS_TITULO:
            r_titulo = _jaccard(cand_pal_titulo, ex["nombre_palabras"])
            if r_titulo > mejor_titulo[0]:
                mejor_titulo = (r_titulo, ex)

        # Letra: sólo sobre vocabulario distintivo (sin el común del
        # género), y sólo si ambos lados tienen suficiente como para que
        # la coincidencia signifique algo.
        if letra_comparable and len(ex["letra_distintiva"]) >= MIN_PALABRAS_DISTINTIVAS:
            r_letra = _jaccard(cand_distintiva, ex["letra_distintiva"])
            if r_letra > mejor_letra[0]:
                mejor_letra = (r_letra, ex)

    ratio_t, ex_t = mejor_titulo
    ratio_l, ex_l = mejor_letra

    if ratio_l >= UMBRAL_DUPLICADO_LETRA:
        return "duplicado", {"por": "letra", "existente": ex_l["nombre"], "ratio": ratio_l}
    if ratio_t >= UMBRAL_DUPLICADO_TITULO:
        # Mismo cruce que arriba: un título casi idéntico no alcanza si
        # la letra dice que son canciones distintas. En ese caso baja a
        # "dudoso" en vez de descartarse como duplicado.
        letra_desmiente = (
            letra_comparable
            and len(ex_t["letra_distintiva"]) >= MIN_PALABRAS_DISTINTIVAS
            and _jaccard(cand_distintiva, ex_t["letra_distintiva"]) < UMBRAL_DUDOSO_LETRA
        )
        if not letra_desmiente:
            return "duplicado", {"por": "título", "existente": ex_t["nombre"], "ratio": ratio_t}
        return "dudoso", {"por": "título (letra no coincide)", "existente": ex_t["nombre"], "ratio": ratio_t}
    if ratio_l >= UMBRAL_DUDOSO_LETRA:
        return "dudoso", {"por": "letra", "existente": ex_l["nombre"], "ratio": ratio_l}
    if ratio_t >= UMBRAL_DUDOSO_TITULO:
        return "dudoso", {"por": "título", "existente": ex_t["nombre"], "ratio": ratio_t}
    return "nueva", None

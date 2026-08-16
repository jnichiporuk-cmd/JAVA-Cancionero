# ============================================================================
# NIVEL 1: importar.py — el único importador de canciones
# ============================================================================
# Reemplaza los scripts sueltos de un solo uso (comparar_duplicados.py,
# limpiar_bien.py, remover_duplicados_verdaderos.py). Una sola fuente de
# verdad para: archivo TXT/JSON, URL directa, o graduar desde Firestore.
# Siempre el mismo flujo: parsear -> deduplicar por título Y letra ->
# reporte -> confirmación explícita -> recién ahí escribir.
#
# Uso:
#   python importar.py --fuente "Cancionero completo.txt"
#   python importar.py --fuente https://www.cifraclub.com/artista/cancion
#   python importar.py --fuente firestore

import os
import sys
import json
import re
import argparse
import subprocess
import urllib.request

import cancionero_io as cio
import revisor as rev

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ID = "cancionero-peniel"


# ============================================================================
# NIVEL 2: Parsers — cada fuente devuelve una lista de candidatas
# {nombre, tono, bpm, bloques, [id_original si viene de Firestore]}
# ============================================================================

def _letra_a_bloques_simple(letra):
    """Letra sin acordes: cada línea no vacía es 'l', párrafos separados
    por 'v'. No pasa por texto_a_bloques() porque acá ya sabemos que no
    hay acordes -- una línea corta en mayúsculas no debe interpretarse
    como cifrado por error."""
    salida = []
    vacio_pendiente = False
    for linea in letra.replace("\r", "").split("\n"):
        if not linea.strip():
            vacio_pendiente = True
            continue
        if vacio_pendiente and salida:
            salida.append({"t": "v"})
        vacio_pendiente = False
        salida.append({"t": "l", "v": linea.strip()})
    return salida


def parsear_easyworship_dump(contenido):
    """Estructura del dump recuperado de EasyWorship: bloques separados
    por '====', alternando 'NNNN. Título' y el cuerpo de letra (sin
    acordes). Detectado y verificado sobre 'Cancionero completo.txt'."""
    bloques = re.split(r"\n=+\n", contenido)
    patron = re.compile(r"^(\d{4})\.\s*(.*)$")
    candidatas = []
    i = 0
    while i < len(bloques):
        b = bloques[i].strip()
        m = patron.match(b)
        if m:
            titulo = m.group(2).strip()
            letra = bloques[i + 1].strip() if i + 1 < len(bloques) else ""
            candidatas.append({
                "nombre": titulo, "tono": None, "bpm": None,
                "bloques": _letra_a_bloques_simple(letra),
                "letra_cruda": letra,
            })
            i += 2
        else:
            i += 1
    return candidatas


def es_dump_easyworship(contenido):
    """Detecta el dialecto por su forma: varios bloques 'NNNN. Título'."""
    return len(re.findall(r"^\d{4}\.\s", contenido, re.MULTILINE)) >= 3


# Formato que escribe exportar.py: separador, 'Nombre - Tono - BPM',
# separador, y el cuerpo en el dialecto del editor.
RE_EXPORT = re.compile(
    r"^={10,}\n(?P<enc>.+?)\n={10,}\n(?P<cuerpo>.*?)(?=\n={10,}\n|\Z)",
    re.MULTILINE | re.DOTALL,
)


def es_export_cancionero(contenido):
    return len(RE_EXPORT.findall(contenido)) >= 1 and "\n====" in contenido


def _partir_encabezado(enc):
    """'Nombre - Tono - BPM' -> (nombre, tono, bpm). Se parte desde la
    derecha porque el nombre puede tener guiones ('Alaba - Evan Craft'):
    sólo se consume la última parte si es un número (bpm) y la anterior
    si es un tono válido."""
    partes = [p.strip() for p in enc.split(" - ")]
    bpm = None
    if len(partes) > 1 and partes[-1].isdigit():
        bpm = int(partes.pop())
    tono = None
    if len(partes) > 1 and cio.RE_CIFRADO.match(partes[-1]):
        tono = partes.pop()
    return " - ".join(partes).strip(), tono, bpm


def parsear_export_cancionero(contenido):
    """Lee lo que genera exportar.py -- cierra la ida y vuelta
    export -> import sin pérdida."""
    candidatas = []
    for m in RE_EXPORT.finditer(contenido):
        nombre, tono, bpm = _partir_encabezado(m.group("enc"))
        if not nombre:
            continue
        candidatas.append({
            "nombre": nombre, "tono": tono, "bpm": bpm,
            "bloques": cio.texto_a_bloques(m.group("cuerpo").strip("\n")),
        })
    return candidatas


def parsear_json(contenido):
    datos = json.loads(contenido)
    if isinstance(datos, dict):
        datos = [datos]
    return [{
        "nombre": (d.get("nombre") or "").strip(),
        "tono": d.get("tono"), "bpm": d.get("bpm"),
        "bloques": d.get("bloques", []),
    } for d in datos]


def parsear_txt_cancion_unica(contenido, nombre_por_defecto):
    """Un TXT que no es el dump de EasyWorship = una sola canción, en el
    dialecto Cancionero/cifra-style (texto_a_bloques) -- cubre lo pegado
    tal cual de cifraclub/lacuerda (acorde en línea propia arriba de la
    letra, sin marcas)."""
    bloques = cio.texto_a_bloques(contenido)
    nombre = nombre_por_defecto
    if bloques and bloques[0]["t"] == "l" and len(bloques[0]["v"]) < 80:
        nombre = bloques[0]["v"]
        bloques = bloques[1:]
        if bloques and bloques[0]["t"] == "v":
            bloques = bloques[1:]
    return [{"nombre": nombre, "tono": None, "bpm": None, "bloques": bloques}]


def parsear_archivo(ruta):
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    if ruta.lower().endswith(".json"):
        return parsear_json(contenido)
    if es_dump_easyworship(contenido):
        print("Formato detectado: dump tipo EasyWorship (múltiples canciones numeradas)\n")
        return parsear_easyworship_dump(contenido)
    if es_export_cancionero(contenido):
        print("Formato detectado: export de este mismo cancionero\n")
        return parsear_export_cancionero(contenido)
    print("Formato detectado: canción única, dialecto Cancionero/cifra-style\n")
    nombre_archivo = os.path.splitext(os.path.basename(ruta))[0]
    return parsear_txt_cancion_unica(contenido, nombre_archivo)


def parsear_url(url):
    """Descarga la página y extrae texto plano. Funciona sin proxy: la
    restricción de CORS es del navegador, no de un script Python."""
    import lxml.html

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html_bytes = resp.read()
    doc = lxml.html.fromstring(html_bytes)

    titulo_tag = doc.findtext(".//title") or ""
    nombre = re.split(r"[-|–]", titulo_tag)[0].strip() or "Sin título"

    for tag in doc.xpath("//script | //style | //nav | //header | //footer"):
        tag.drop_tree()

    texto = doc.text_content()
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    bloques = cio.texto_a_bloques(texto)
    return [{"nombre": nombre, "tono": None, "bpm": None, "bloques": bloques}]


def parsear_firestore():
    """Trae las canciones marcadas nueva=true (sin las borradas) para
    graduarlas a la capa base. Conserva id_original: es clave para no
    romper referencias en reuniones guardadas (nuevoId() de la app y
    generar_id() acá son el mismo algoritmo, así que el ID ya es
    estable -- no hace falta regenerarlo)."""
    print("Actualizando snapshot de Firestore...")
    subprocess.run([sys.executable, "descargar_firestore.py"], check=True)
    print()
    with open("firestore_canciones.json", encoding="utf-8") as f:
        docs = json.load(f)
    return [{
        "nombre": d["nombre"], "tono": d.get("tono"), "bpm": d.get("bpm"),
        "bloques": d.get("bloques", []), "id_original": d["id"],
    } for d in docs if d.get("nueva") and not d.get("borrada")]


# ============================================================================
# NIVEL 2: Filtro de basura evidente (nunca se descarta en silencio)
# ============================================================================

def es_candidata_basura(candidata):
    letra = candidata.get("letra_cruda") or cio.bloques_a_texto(candidata["bloques"])
    nombre = candidata["nombre"]
    if len(letra.strip()) < 25:
        return True
    if not re.search(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]{3,}", nombre):
        return True
    return False


# ============================================================================
# NIVEL 2: Marcar como no-nueva en Firestore (graduación)
# No se puede borrar el documento (regla del proyecto: allow delete: if
# false para 'canciones', a propósito -- no se borran, se marcan). Marcar
# borrada:true tampoco sirve: recalcular() usa el mismo set de IDs
# borrados para filtrar tanto la base como las nuevas, así que ocultaría
# también la versión recién agregada a catalogo.json. La solución segura
# es nueva:false: dado que el contenido copiado a catalogo.json es
# idéntico, queda como una "edición" redundante mismo dato, sin duplicar
# ni desaparecer.
# ============================================================================

def consolidar_borrados():
    """Aplica en la capa base los borrados que hoy sólo viven en la capa
    de cambios: saca de catalogo.json las canciones cuyo id está marcado
    `borrada:true` en Firestore.

    No es sólo cosmético. Sin esto, esas canciones **siguen dentro del
    HTML** y sólo desaparecen cuando llega el listener de Firestore, así
    que:
      - al abrir se ve el total viejo y baja unos instantes después, como
        si algo estuviera roto;
      - y sin internet -- el caso que la app está pensada para aguantar --
        los borrados nunca llegan y las canciones eliminadas reaparecen.

    Los documentos de Firestore no se tocan: no se pueden borrar (regla
    del proyecto) y quedan como marcas huérfanas, inofensivas, que ya no
    apuntan a nada.
    """
    with open("catalogo.json", encoding="utf-8") as f:
        catalogo = json.load(f)
    with open("firestore_canciones.json", encoding="utf-8") as f:
        borradas = {d["id"] for d in json.load(f) if d.get("borrada")}

    quitar = [c for c in catalogo if c["id"] in borradas]
    if not quitar:
        print("No hay borrados pendientes de consolidar.")
        return

    print(f"\n{len(quitar)} canciones están marcadas como borradas y todavía")
    print("viven en catalogo.json (por eso el total baja al cargar la app):\n")
    for c in quitar:
        print(f"  • {c['nombre']!r}")

    print()
    if input(f"¿Sacarlas de catalogo.json? (s/n): ").strip().lower() != "s":
        print("Cancelado. No se escribió nada.")
        return

    quedan = [c for c in catalogo if c["id"] not in borradas]
    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(quedan, f, ensure_ascii=False, indent=2)
    print(f"\n✓ catalogo.json: {len(catalogo)} → {len(quedan)} canciones")
    print("  Ahora el número no cambia al cargar, y los borrados también valen sin internet.")


def marcar_no_nueva_en_firestore(doc_id):
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/canciones/{doc_id}?updateMask.fieldPaths=nueva"
    body = json.dumps({"fields": {"nueva": {"booleanValue": False}}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PATCH",
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


# ============================================================================
# NIVEL 2: Reporte y escritura
# ============================================================================

def clasificar_todas(candidatas, indice):
    """Clasifica cada candidata contra el índice existente Y contra las
    candidatas ya aceptadas como 'nueva' en esta misma corrida -- si no,
    dos candidatas que son la misma canción entre sí (ej. la misma
    letra cargada dos veces con mayúsculas distintas) pasarían las dos
    como 'nueva' sin que nada las cruce entre sí."""
    resultado = {"duplicado": [], "dudoso": [], "nueva": []}
    comunes = indice["palabras_comunes"]
    indice_extendido = {
        "canciones": list(indice["canciones"]),
        "palabras_comunes": comunes,
    }
    for c in candidatas:
        nombre_norm = cio.normalizar_nombre(c["nombre"])
        letra_norm = cio.normalizar_letra(cio.extraer_letra(c["bloques"]))
        categoria, detalle = cio.clasificar_duplicado(nombre_norm, letra_norm, indice_extendido)
        resultado[categoria].append((c, detalle))
        if categoria == "nueva":
            letra_palabras = cio.palabras_significativas(letra_norm)
            indice_extendido["canciones"].append({
                "id": None, "nombre": c["nombre"], "nombre_norm": nombre_norm,
                "nombre_palabras": cio.palabras_significativas(nombre_norm),
                "letra_palabras": letra_palabras,
                "letra_distintiva": letra_palabras - comunes,
                "origen": "misma-fuente",
            })
    return resultado


def imprimir_reporte(candidatas, basura, clasificadas):
    print("=" * 70)
    print("REPORTE DE IMPORTACIÓN")
    print("=" * 70)
    print(f"\nTotal candidatas: {len(candidatas)}")
    print(f"Basura evidente (excluidas, listadas abajo): {len(basura)}")
    print(f"Duplicadas: {len(clasificadas['duplicado'])}")
    print(f"Dudosas (revisar a mano): {len(clasificadas['dudoso'])}")
    print(f"Nuevas reales: {len(clasificadas['nueva'])}")

    if basura:
        print("\n" + "-" * 70)
        print(f"BASURA EVIDENTE ({len(basura)}) -- no se van a importar:")
        print("-" * 70)
        for c in basura:
            print(f"  • {c['nombre']!r}")

    if clasificadas["dudoso"]:
        print("\n" + "-" * 70)
        print(f"DUDOSAS ({len(clasificadas['dudoso'])}) -- similitud media, revisar:")
        print("-" * 70)
        for c, det in clasificadas["dudoso"]:
            print(f"  • {c['nombre']!r}")
            print(f"    ~ {det['existente']!r} (por {det['por']}, {det['ratio']:.0%})")

    if clasificadas["duplicado"]:
        print("\n" + "-" * 70)
        print(f"DUPLICADAS ({len(clasificadas['duplicado'])}) -- no se importan:")
        print("-" * 70)
        for c, det in clasificadas["duplicado"][:20]:
            print(f"  • {c['nombre']!r} = {det['existente']!r} (por {det['por']})")
        if len(clasificadas["duplicado"]) > 20:
            print(f"  ... y {len(clasificadas['duplicado']) - 20} más")

    if clasificadas["nueva"]:
        print("\n" + "-" * 70)
        print(f"NUEVAS REALES ({len(clasificadas['nueva'])}) -- se van a importar:")
        print("-" * 70)
        for c, _ in clasificadas["nueva"]:
            print(f"  • {c['nombre']!r}")


def armar_pares_para_revisar(clasificadas, indice, candidatas_por_nombre,
                              techo_revision=100, fuente="el archivo que estás importando"):
    """Junta duplicadas + dudosas con las dos canciones COMPLETAS, para
    que revisor.py arme la página de comparación. La heurística de texto
    propone; la decisión final se toma mirando las dos letras enteras
    lado a lado -- comparar fragmentos ya demostró llevar a error.

    `fuente` describe de dónde salen las candidatas, para rotularlas bien.
    Estuvo hardcodeado como "cargada en la app (Firestore)" y quedó
    mintiendo en cuanto la fuente pasó a ser un archivo: la etiqueta tiene
    que decir la verdad, o se decide mirando un dato falso."""
    # El lado "existente" no siempre está ya en el cancionero: puede ser
    # otra candidata del mismo lote (la misma canción repetida dentro del
    # archivo que se importa).
    etiqueta_nueva = "NUEVA · viene de " + fuente
    bloques_existente, origen_existente = {}, {}
    with open("catalogo.json", encoding="utf-8") as f:
        for c in json.load(f):
            bloques_existente[c["nombre"]] = c
            origen_existente[c["nombre"]] = "YA ESTÁ EN EL CANCIONERO"
    for nombre, c in candidatas_por_nombre.items():
        if nombre not in bloques_existente:
            bloques_existente[nombre] = c
            origen_existente[nombre] = etiqueta_nueva

    pares = []
    for clase in ("duplicado", "dudoso"):
        for c, det in clasificadas[clase]:
            # Las duplicadas de confianza muy alta no aportan nada a la
            # revisión: son las que comparten TODO el vocabulario propio.
            # Meterlas obligaría a pasar por cientos de pantallas obvias y
            # a que la revisión se abandone por larga, que es peor que no
            # revisar las dudosas de verdad.
            if clase == "duplicado" and det["ratio"] * 100 > techo_revision:
                continue
            ex = bloques_existente.get(det["existente"], {})
            pares.append({
                "id": f"{clase}:{c['nombre']}",
                "clase": clase,
                "por": det["por"],
                "ratio": round(det["ratio"] * 100),
                "cand_nombre": c["nombre"],
                "cand_meta": rev.meta_de(c),
                "cand_bloques": c["bloques"],
                "cand_origen": etiqueta_nueva,
                "ex_nombre": det["existente"],
                "ex_meta": rev.meta_de(ex),
                "ex_bloques": ex.get("bloques", []),
                "ex_origen": origen_existente.get(det["existente"], "?"),
            })
    return pares


def ids_borrados_en_firestore():
    """Ids marcados `borrada:true`. Un id nuevo NUNCA puede reusar uno de
    estos: `recalcular()` filtra por id, así que la canción recién
    importada heredaría el borrado de la vieja y quedaría invisible en la
    app aunque esté en catalogo.json. Pasó de verdad con 'Cielo y tierra
    podrán pasar': la version anterior se habia borrado desde la app, y
    la nueva generaba el mismo slug."""
    try:
        with open("firestore_canciones.json", encoding="utf-8") as f:
            return {d["id"] for d in json.load(f) if d.get("borrada")}
    except FileNotFoundError:
        return set()


def planificar_veredictos(veredictos, candidatas_validas, clasificadas):
    """Traduce los veredictos a un plan concreto, sin tocar nada todavía.

    Regla del usuario: "la correcta se queda, la otra se borra".
      - distintas                  -> las dos quedan; la candidata se importa
      - misma / gana la candidata  -> se importa la candidata y se elimina
                                      la perdedora (del catálogo o de la
                                      capa de cambios, según dónde viva)
      - misma / gana la existente  -> la candidata se descarta

    Las que el detector clasificó como 'nueva' (sin par que revisar) se
    importan sin más: nadie las cuestionó.

    **Lo que quedó sin decidir NO se importa.** Todas esas son casos que
    el detector marcó como posible duplicado, así que ante la duda se
    dejan afuera: importarlas meteria cientos de repetidas en el catálogo,
    y no importarlas no pierde nada -- el archivo de origen sigue estando
    y se puede retomar la revisión cuando se quiera.

    Devuelve (a_importar, borrar_del_catalogo, descartar_candidatas).
    """
    descartar = set()          # candidatas que perdieron: no se importan
    postergar = set()          # candidatas sin decidir: quedan para otra vuelta
    borrar_catalogo = set()    # nombres del catálogo que se eliminan

    with open("catalogo.json", encoding="utf-8") as f:
        nombres_catalogo = {c["nombre"] for c in json.load(f)}

    for v in veredictos:
        if v["tipo"] == "pendiente":
            postergar.add(v["candidata"])
        elif v["tipo"] == "misma":
            if v["quedarse"] == "candidata":
                perdedora = v["existente"]
                if perdedora in nombres_catalogo:
                    borrar_catalogo.add(perdedora)
                else:
                    descartar.add(perdedora)   # era otra candidata del mismo lote
            else:
                descartar.add(v["candidata"])

    afuera = descartar | postergar
    a_importar = [c for c in candidatas_validas if c["nombre"] not in afuera]
    return a_importar, borrar_catalogo, descartar, postergar


def aplicar_veredictos(ruta_veredictos, candidatas_validas, clasificadas, es_graduacion):
    """Ejecuta el plan de planificar_veredictos() sobre catalogo.json y,
    si la fuente fue Firestore, deja de marcar como 'nueva' a TODAS las
    candidatas procesadas: las que ganaron ya viven en el catálogo (si
    siguieran como nueva=true aparecerían duplicadas) y las que perdieron
    no deben seguir a la vista. Los documentos no se borran porque las
    reglas del proyecto no lo permiten para 'canciones'."""
    with open(ruta_veredictos, encoding="utf-8") as f:
        veredictos = json.load(f)

    a_importar, borrar_catalogo, descartar, postergar = planificar_veredictos(
        veredictos, candidatas_validas, clasificadas)

    if postergar:
        print(f"\n⚠ {len(postergar)} pares quedaron sin decidir: NO se importan.")
        print("  Eran posibles duplicados, así que ante la duda quedan afuera.")
        print("  El archivo de origen sigue estando: se puede retomar la revisión.")

    # Correcciones de letra hechas a mano durante la revisión. Se aplican
    # antes de decidir nada más, así el resto del flujo trabaja ya con el
    # texto corregido.
    correcciones_cand = {v["candidata"]: v["correccion_candidata"]
                         for v in veredictos if v.get("correccion_candidata")}
    correcciones_exist = {v["existente"]: v["correccion_existente"]
                          for v in veredictos if v.get("correccion_existente")}
    for c in candidatas_validas:
        if c["nombre"] in correcciones_cand:
            c["bloques"] = correcciones_cand[c["nombre"]]

    with open("catalogo.json", encoding="utf-8") as f:
        catalogo = json.load(f)
    antes = len(catalogo)

    corregidas_catalogo = 0
    for c in catalogo:
        if c["nombre"] in correcciones_exist:
            c["bloques"] = correcciones_exist[c["nombre"]]
            corregidas_catalogo += 1

    catalogo = [c for c in catalogo if c["nombre"] not in borrar_catalogo]
    usados = {c["id"] for c in catalogo} | ids_borrados_en_firestore()

    for cand in a_importar:
        id_final = (cand["id_original"] if "id_original" in cand
                    else cio.generar_id(cand["nombre"], cand["tono"], usados))
        usados.add(id_final)
        catalogo.append({
            "id": id_final, "nombre": cand["nombre"], "tono": cand["tono"],
            "bpm": cand["bpm"], "bloques": cand["bloques"],
        })

    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    if correcciones_cand or corregidas_catalogo:
        print(f"\n✓ {len(correcciones_cand)} letras corregidas a mano en las que entran")
        print(f"✓ {corregidas_catalogo} letras corregidas a mano en el catálogo")
    print(f"\n✓ {len(borrar_catalogo)} eliminadas del catálogo (perdieron la comparación)")
    print(f"✓ {len(descartar)} candidatas descartadas (perdieron la comparación)")
    print(f"✓ {len(postergar)} candidatas postergadas (sin decidir)")
    print(f"✓ {len(a_importar)} candidatas agregadas al catálogo")
    print(f"✓ catalogo.json: {antes} → {len(catalogo)} canciones")

    if es_graduacion:
        ids = [c["id_original"] for c in candidatas_validas if "id_original" in c]
        print(f"\nMarcando {len(ids)} documentos como no-nueva en Firestore...")
        for doc_id in ids:
            marcar_no_nueva_en_firestore(doc_id)
        print("✓ Firestore actualizado")


def escribir(nuevas, es_graduacion):
    with open("catalogo.json", encoding="utf-8") as f:
        catalogo = json.load(f)
    usados = {c["id"] for c in catalogo}

    for c, _ in nuevas:
        if es_graduacion:
            id_final = c["id_original"]
        else:
            id_final = cio.generar_id(c["nombre"], c["tono"], usados)
        catalogo.append({
            "id": id_final, "nombre": c["nombre"], "tono": c["tono"],
            "bpm": c["bpm"], "bloques": c["bloques"],
        })

    with open("catalogo.json", "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)
    print(f"\n✓ {len(nuevas)} canciones agregadas a catalogo.json ({len(catalogo)} en total)")

    if es_graduacion:
        print("Marcando como no-nueva en Firestore (no se puede borrar: regla del proyecto)...")
        for c, _ in nuevas:
            marcar_no_nueva_en_firestore(c["id_original"])
        print(f"✓ {len(nuevas)} documentos actualizados en Firestore")


# ============================================================================
# NIVEL 1: main
# ============================================================================

def main():
    ap = argparse.ArgumentParser(description="Importador único de canciones")
    ap.add_argument("--fuente",
                     help="Archivo (.txt/.json), URL (http/https), o 'firestore'")
    ap.add_argument("--revisar", action="store_true",
                     help="Genera la página local de revisión (duplicadas y dudosas, "
                          "lado a lado y completas) y termina, sin escribir nada")
    ap.add_argument("--veredictos",
                     help="Aplica el veredictos.json que descargaste de la página "
                          "de revisión: importa las distintas y reemplaza donde "
                          "hayas elegido la versión candidata")
    ap.add_argument("--consolidar-borrados", action="store_true",
                     help="Saca de catalogo.json las canciones borradas desde la app. "
                          "Sin esto siguen dentro del HTML: el total baja al cargar y "
                          "reaparecen sin internet")
    ap.add_argument("--revisar-hasta", type=int, default=100, metavar="N",
                     help="Con --revisar: incluir las duplicadas con menos de N%% de "
                          "confianza (default 100, o sea todas). Bajarlo deja fuera de "
                          "la revisión las coincidencias obvias")
    args = ap.parse_args()

    if args.consolidar_borrados:
        print("Actualizando snapshot de Firestore...")
        subprocess.run([sys.executable, "descargar_firestore.py"], check=True,
                       stdout=subprocess.DEVNULL)
        consolidar_borrados()
        if not args.fuente:
            print("\nCorré 'python build.py' para regenerar index.html.")
            return

    if not args.fuente:
        ap.error("hace falta --fuente (o --consolidar-borrados)")

    fuente = args.fuente
    es_graduacion = False

    if fuente == "firestore":
        candidatas = parsear_firestore()
        es_graduacion = True
    elif fuente.startswith("http://") or fuente.startswith("https://"):
        candidatas = parsear_url(fuente)
    else:
        candidatas = parsear_archivo(fuente)

    if not candidatas:
        print("No se encontraron canciones para importar.")
        return

    # Con --revisar + --veredictos se retoma una revisión a medio hacer:
    # sólo se vuelven a mirar las que quedaron pendientes. Sin esto, tras
    # importar una tanda las ya importadas volverían a aparecer,
    # comparándose contra sí mismas.
    if args.revisar and args.veredictos:
        with open(args.veredictos, encoding="utf-8") as f:
            pendientes = {v["candidata"] for v in json.load(f)
                          if v["tipo"] == "pendiente"}
        antes = len(candidatas)
        candidatas = [c for c in candidatas if c["nombre"] in pendientes]
        print(f"Retomando revisión: {len(candidatas)} pendientes de {antes} del archivo\n")

    basura, candidatas_validas = [], []
    for c in candidatas:
        if not es_graduacion and es_candidata_basura(c):
            basura.append(c)
        else:
            candidatas_validas.append(c)

    print("Cargando catálogo existente (esto puede tardar por la comparación de letras)...\n")
    indice = cio.cargar_catalogo_existente(
        refrescar_firestore=not es_graduacion,
        incluir_firestore_nuevas=not es_graduacion,
    )
    clasificadas = clasificar_todas(candidatas_validas, indice)

    imprimir_reporte(candidatas_validas, basura, clasificadas)

    if args.revisar:
        if es_graduacion:
            desc_fuente = "la app (cargada por alguien del grupo)"
        elif fuente.startswith("http"):
            desc_fuente = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", fuente)
        else:
            desc_fuente = os.path.basename(fuente)
        candidatas_por_nombre = {c["nombre"]: c for c in candidatas_validas}
        pares = armar_pares_para_revisar(clasificadas, indice, candidatas_por_nombre,
                                          techo_revision=args.revisar_hasta,
                                          fuente=desc_fuente)
        if not pares:
            print("\nNo hay nada para revisar: ninguna duplicada ni dudosa.")
            return
        ruta = rev.generar(pares)
        print("\n" + "=" * 70)
        print(f"Página de revisión generada: {ruta}")
        print(f"{len(pares)} pares para revisar (duplicadas + dudosas).")
        print("Abrila en el navegador, revisá una por una y copiá el resultado final.")
        print("No se escribió nada en el catálogo.")
        return

    if args.veredictos:
        print("\n" + "=" * 70)
        print(f"Aplicando veredictos de {args.veredictos}")
        respuesta = input("¿Confirmar? Esto modifica catalogo.json (s/n): ").strip().lower()
        if respuesta != "s":
            print("Cancelado. No se escribió nada.")
            return
        aplicar_veredictos(args.veredictos, candidatas_validas, clasificadas, es_graduacion)
        print("\nCorré 'python build.py' para regenerar index.html.")
        return

    if not clasificadas["nueva"]:
        print("\nNada nuevo para importar.")
        return

    print("\n" + "=" * 70)
    respuesta = input(f"¿Confirmar import de {len(clasificadas['nueva'])} canciones? (s/n): ").strip().lower()
    if respuesta != "s":
        print("Cancelado. No se escribió nada.")
        return

    escribir(clasificadas["nueva"], es_graduacion)
    print("\nCorré 'python build.py' para regenerar index.html.")


if __name__ == "__main__":
    main()

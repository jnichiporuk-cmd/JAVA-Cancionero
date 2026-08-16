# ============================================================================
# NIVEL 1: exportar.py — el único exportador de canciones
# ============================================================================
# Contraparte de importar.py. Saca canciones del cancionero en un formato
# que se pueda volver a importar sin pérdida: el TXT usa el mismo dialecto
# que el editor de la app (via bloques_a_texto), así la ida y vuelta
# export -> import no degrada nada.
#
# Uso:
#   python exportar.py --formato txt                    # todo el catálogo
#   python exportar.py --formato json --salida cat.json
#   python exportar.py --formato txt --buscar "gloria"  # sólo las que matcheen

import sys
import json
import argparse

import cancionero_io as cio

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SEPARADOR = "=" * 60


# ============================================================================
# NIVEL 2: Selección de qué exportar
# ============================================================================

def cargar_canciones(incluir_firestore):
    """La capa base siempre; la de cambios sólo si se pide (normalmente
    está vacía, pero puede haber canciones cargadas desde la app que
    todavía no se graduaron)."""
    with open("catalogo.json", encoding="utf-8") as f:
        canciones = json.load(f)

    if not incluir_firestore:
        return canciones

    try:
        with open("firestore_canciones.json", encoding="utf-8") as f:
            docs = json.load(f)
    except FileNotFoundError:
        print("(no hay firestore_canciones.json; exportando sólo la capa base)")
        return canciones

    borradas = {d["id"] for d in docs if d.get("borrada")}
    canciones = [c for c in canciones if c["id"] not in borradas]
    for d in docs:
        if d.get("nueva") and not d.get("borrada"):
            canciones.append({
                "id": d["id"], "nombre": d["nombre"], "tono": d.get("tono"),
                "bpm": d.get("bpm"), "bloques": d.get("bloques", []),
            })
    return canciones


def filtrar(canciones, texto):
    """Mismo criterio que el buscador de la app: nombre, tono y letra."""
    if not texto:
        return canciones
    q = cio.normalizar_nombre(texto)
    salida = []
    for c in canciones:
        letra = cio.normalizar_letra(cio.extraer_letra(c.get("bloques", [])))
        if (q in cio.normalizar_nombre(c["nombre"])
                or q in cio.normalizar_nombre(c.get("tono") or "")
                or q in letra):
            salida.append(c)
    return salida


# ============================================================================
# NIVEL 2: Formatos de salida
# ============================================================================

def a_json(canciones, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(canciones, f, ensure_ascii=False, indent=2)


def a_txt(canciones, ruta):
    """Encabezado 'Nombre - Tono - BPM' entre separadores, y el cuerpo en
    el dialecto del editor (bloques_a_texto).

    El nombre va con su capitalización original, NO en mayúsculas como en
    el .docx: este formato existe para volver a importarse, y pasar todo a
    mayúsculas perdería el nombre real."""
    partes = []
    for c in canciones:
        encabezado = c["nombre"]
        if c.get("tono"):
            encabezado += f" - {c['tono']}"
        if c.get("bpm"):
            encabezado += f" - {c['bpm']}"
        partes.append(f"{SEPARADOR}\n{encabezado}\n{SEPARADOR}\n\n"
                      f"{cio.bloques_a_texto(c.get('bloques', []))}\n")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))


# ============================================================================
# NIVEL 1: main
# ============================================================================

def main():
    ap = argparse.ArgumentParser(description="Exportador único de canciones")
    ap.add_argument("--formato", choices=["json", "txt"], default="txt")
    ap.add_argument("--salida", help="Archivo destino (por defecto, cancionero.txt/json)")
    ap.add_argument("--buscar", help="Exportar sólo las que matcheen en nombre, tono o letra")
    ap.add_argument("--con-firestore", action="store_true",
                     help="Incluir también lo cargado desde la app y todavía no graduado")
    args = ap.parse_args()

    canciones = cargar_canciones(args.con_firestore)
    total = len(canciones)
    canciones = filtrar(canciones, args.buscar)
    canciones.sort(key=lambda c: cio.normalizar_nombre(c["nombre"]))

    if not canciones:
        print(f"Ninguna canción coincide con {args.buscar!r}.")
        return

    ruta = args.salida or f"cancionero.{args.formato}"
    (a_json if args.formato == "json" else a_txt)(canciones, ruta)

    detalle = f" (de {total})" if args.buscar else ""
    print(f"✓ {len(canciones)} canciones{detalle} exportadas a {ruta}")
    if args.formato == "txt":
        print("  El TXT usa el dialecto del editor: se puede volver a importar con")
        print(f"  python importar.py --fuente {ruta}")


if __name__ == "__main__":
    main()

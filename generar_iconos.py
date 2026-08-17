# ============================================================================
# NIVEL 1: generar_iconos.py — íconos de la app en todas las medidas
# ============================================================================
# Genera los PNG que usan el manifest (Android) y apple-touch-icon (iOS) a
# partir de icon-512.png, la única fuente. Sin dependencias externas: Pillow
# no está instalado en esta máquina, así que decodifica y codifica PNG a mano
# con zlib + struct.
#
# Uso:  python generar_iconos.py

import sys
import zlib
import struct

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

FUENTE = "icon-512.png"

# Cada medida existe por un motivo concreto, no por completar la lista:
#   180 -> apple-touch-icon; es la medida que pide iOS y la ÚNICA que mira
#          para el ícono de escritorio (ignora los del manifest.json)
#   192 -> mínimo que exige Android para generar un WebAPK instalable
MEDIDAS = [180, 192]


# ============================================================================
# NIVEL 2: PNG a mano (decodificar / codificar)
# ============================================================================

def leer_png(ruta):
    """Devuelve (ancho, alto, bytes RGB sin filtrar). Sólo soporta el PNG que
    genera este mismo script: 8 bits, color type 2 (RGB), sin entrelazado."""
    d = open(ruta, "rb").read()
    p, idat, w, h = 8, b"", 0, 0

    while p < len(d):
        largo = struct.unpack(">I", d[p:p + 4])[0]
        tipo = d[p + 4:p + 8]
        datos = d[p + 8:p + 8 + largo]
        if tipo == b"IHDR":
            w, h, prof, color = struct.unpack(">IIBB", datos[:10])
            if (prof, color) != (8, 2):
                raise ValueError(f"{ruta}: se esperaba 8 bits RGB, vino {prof}/{color}")
        elif tipo == b"IDAT":
            idat += datos
        p += 12 + largo

    crudo = zlib.decompress(idat)
    paso = w * 3
    salida, previa = bytearray(), bytearray(paso)
    i = 0

    # Deshacer el filtro por fila (spec PNG: 0 ninguno, 1 Sub, 2 Up,
    # 3 Average, 4 Paeth). Cada fila viene precedida por su tipo de filtro.
    for _ in range(h):
        filtro = crudo[i]; i += 1
        linea = bytearray(crudo[i:i + paso]); i += paso
        for x in range(paso):
            a = linea[x - 3] if x >= 3 else 0        # píxel izquierdo
            b = previa[x]                             # píxel de arriba
            c = previa[x - 3] if x >= 3 else 0        # diagonal arriba-izq
            if filtro == 1:
                linea[x] = (linea[x] + a) & 255
            elif filtro == 2:
                linea[x] = (linea[x] + b) & 255
            elif filtro == 3:
                linea[x] = (linea[x] + (a + b) // 2) & 255
            elif filtro == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linea[x] = (linea[x] + pred) & 255
        salida += linea
        previa = linea

    return w, h, bytes(salida)


def escribir_png(ruta, w, h, rgb):
    """Escribe PNG 8 bits RGB, filtro 0 en todas las filas."""
    crudo = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def trozo(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    with open(ruta, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(trozo(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(trozo(b"IDAT", zlib.compress(crudo, 9)))
        f.write(trozo(b"IEND", b""))


# ============================================================================
# NIVEL 2: Reducción de tamaño
# ============================================================================

def reducir(w, h, rgb, destino):
    """Promedia el área de origen que cae en cada píxel destino.

    Promediar y no muestrear un píxel suelto importa: el ícono es una figura
    blanca sobre naranja, y quedarse con un solo píxel deja el borde de la
    nota dentado (aliasing) en vez de suavizado."""
    salida = bytearray(destino * destino * 3)
    escala = w / destino

    for y in range(destino):
        y0, y1 = int(y * escala), max(int((y + 1) * escala), int(y * escala) + 1)
        for x in range(destino):
            x0, x1 = int(x * escala), max(int((x + 1) * escala), int(x * escala) + 1)
            r = g = b = n = 0
            for sy in range(y0, min(y1, h)):
                base = sy * w * 3
                for sx in range(x0, min(x1, w)):
                    o = base + sx * 3
                    r += rgb[o]; g += rgb[o + 1]; b += rgb[o + 2]; n += 1
            o = (y * destino + x) * 3
            salida[o], salida[o + 1], salida[o + 2] = r // n, g // n, b // n

    return bytes(salida)


# ============================================================================
# NIVEL 1: main
# ============================================================================

def main():
    w, h, rgb = leer_png(FUENTE)
    print(f"Fuente: {FUENTE} ({w}x{h})")

    for medida in MEDIDAS:
        ruta = f"icon-{medida}.png"
        escribir_png(ruta, medida, medida, reducir(w, h, rgb, medida))
        print(f"  ✓ {ruta}")


if __name__ == "__main__":
    main()

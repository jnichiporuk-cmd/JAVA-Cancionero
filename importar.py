#!/usr/bin/env python3
import sys
import json
import re
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================================
# Importar canciones desde archivo TXT y detectar duplicados
# ============================================================================

def normalizar_nombre(nombre):
    """Normalizar nombre para comparación (minúsculas, sin tildes, etc)"""
    nombre = nombre.lower().strip()
    # Remover tildes
    nombre = nombre.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    nombre = nombre.replace('ó', 'o').replace('ú', 'u').replace('ü', 'u')
    # Remover caracteres especiales múltiples
    nombre = re.sub(r'\s+', ' ', nombre)
    return nombre

def parsear_txt(archivo):
    """Parsear archivo TXT y extraer canciones"""
    canciones = []

    with open(archivo, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Split por separador de canciones (líneas de =)
    bloques = re.split(r'\n={30,}\n', contenido)

    for bloque in bloques:
        lineas = bloque.strip().split('\n')
        if not lineas:
            continue

        # Primera línea debe ser "Título: ..."
        if not lineas[0].startswith('Título:'):
            continue

        titulo = lineas[0].replace('Título:', '').strip()

        # Ignorar títulos vacíos o placeholder
        if not titulo or titulo == '.' or len(titulo) < 2:
            continue

        # Resto es letra
        letra = '\n'.join(lineas[1:]).strip()

        if letra and titulo:
            canciones.append({
                'titulo': titulo,
                'letra': letra,
                'nombre_normalizado': normalizar_nombre(titulo)
            })

    return canciones

# ============================================================================
# MAIN
# ============================================================================

print("🎵 Importador de canciones\n")

# Parsear archivo TXT
print("1. Parseando archivo TXT...")
canciones_nuevas = parsear_txt('Importadas 2026-08-09_10-03-06.txt')
print(f"   ✓ {len(canciones_nuevas)} canciones encontradas\n")

# Cargar catálogo actual
print("2. Cargando catálogo actual...")
with open('catalogo.json', 'r', encoding='utf-8') as f:
    catalogo = json.load(f)
print(f"   ✓ {len(catalogo)} canciones en catálogo\n")

# Normalizar nombres del catálogo
catalogo_normalizados = {
    normalizar_nombre(c['nombre']): c['nombre']
    for c in catalogo
}

# Detectar duplicados
print("3. Detectando duplicados...\n")
duplicados = []
nuevas = []

for cancion in canciones_nuevas:
    if cancion['nombre_normalizado'] in catalogo_normalizados:
        duplicados.append({
            'nueva': cancion['titulo'],
            'existente': catalogo_normalizados[cancion['nombre_normalizado']]
        })
    else:
        nuevas.append(cancion)

# Reporte
print(f"   Duplicadas (ya existen): {len(duplicados)}")
print(f"   Nuevas (se pueden agregar): {len(nuevas)}\n")

# Mostrar duplicados
if duplicados:
    print("━" * 70)
    print("DUPLICADAS (ya están en el catálogo):")
    print("━" * 70)
    for d in duplicados[:10]:  # Mostrar primeras 10
        print(f"  • {d['nueva']}")
        print(f"    → {d['existente']}")
    if len(duplicados) > 10:
        print(f"  ... y {len(duplicados) - 10} más")
    print()

# Mostrar nuevas
if nuevas:
    print("━" * 70)
    print("NUEVAS (se pueden agregar):")
    print("━" * 70)
    for n in nuevas[:10]:  # Mostrar primeras 10
        print(f"  • {n['titulo']}")
    if len(nuevas) > 10:
        print(f"  ... y {len(nuevas) - 10} más")
    print()

# Resumen
print("━" * 70)
print("RESUMEN")
print("━" * 70)
print(f"Total en TXT:        {len(canciones_nuevas)}")
print(f"Duplicadas:          {len(duplicados)}")
print(f"Nuevas para agregar: {len(nuevas)}")
print(f"Catálogo actual:     {len(catalogo)}")
print(f"Total si agrega:     {len(catalogo) + len(nuevas)}")
print()

if nuevas:
    print("✓ Hay canciones nuevas para agregar.")
    print("  Ejecutá: python importar.py --hacer")
else:
    print("✗ Todas las canciones ya están en el catálogo.")

# ============================================================================
# MODO: --hacer (agregar las canciones nuevas)
# ============================================================================

if len(sys.argv) > 1 and sys.argv[1] == '--hacer':
    print("\n" + "=" * 70)
    print("AGREGANDO CANCIONES NUEVAS AL CATÁLOGO")
    print("=" * 70 + "\n")

    def hacer_id(nombre, tono=""):
        """Generar ID de canción (nombre-tono)"""
        # Normalizar nombre
        id_parte = nombre.lower()
        id_parte = id_parte.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        id_parte = id_parte.replace('ó', 'o').replace('ú', 'u').replace('ü', 'u')
        id_parte = re.sub(r'[^a-z0-9]+', '-', id_parte)
        id_parte = id_parte.strip('-')

        if tono:
            tono_norm = tono.lower()
            return f"{id_parte}-{tono_norm}"
        return id_parte

    def textoABloques(texto):
        """Convertir texto a bloques (como hace extraer.py)"""
        bloques = []
        lineas = texto.split('\n')

        for linea in lineas:
            if not linea.strip():
                # Línea vacía
                bloques.append({"t": "v"})
            else:
                # Línea con contenido = letra
                bloques.append({"t": "l", "v": linea})

        return bloques

    # Crear canciones nuevas en formato catálogo
    canciones_a_agregar = []
    for cancion in nuevas:
        nueva = {
            "id": hacer_id(cancion['titulo']),
            "nombre": cancion['titulo'],
            "tono": None,
            "bpm": None,
            "bloques": textoABloques(cancion['letra'])
        }
        canciones_a_agregar.append(nueva)

    # Mergear con catálogo
    catalogo_actualizado = catalogo + canciones_a_agregar

    # Guardar
    with open('catalogo.json', 'w', encoding='utf-8') as f:
        json.dump(catalogo_actualizado, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(canciones_a_agregar)} canciones agregadas")
    print(f"✓ Nuevo total: {len(catalogo_actualizado)} canciones")
    print(f"✓ Guardado en catalogo.json\n")
    print("Próximo paso: python build.py")

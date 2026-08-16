#!/usr/bin/env python3
import sys
import json
import re
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================================
# Descargar todas las canciones de Firestore (sin necesidad de admin SDK)
# Usando REST API de Firestore
# ============================================================================

import urllib.request
import urllib.error


def _valor_firestore(v):
    """Traduce un 'Value' del formato REST de Firestore a Python nativo.
    Necesario para 'bloques' (array de maps) -- los otros campos son
    escalares y ya se leían con .get() directo, pero un array de objetos
    no se puede leer así."""
    if v is None:
        return None
    if "stringValue" in v:
        return v["stringValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return v["doubleValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "nullValue" in v:
        return None
    if "arrayValue" in v:
        return [_valor_firestore(x) for x in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: _valor_firestore(val) for k, val in v["mapValue"].get("fields", {}).items()}
    return None


def descargar_canciones_firestore(project_id="cancionero-peniel", database_id="(default)"):
    """Descargar todas las canciones de Firestore usando REST API"""

    print("🎵 Descargando canciones de Firestore...\n")

    # URL de Firestore REST API
    url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/{database_id}/documents/canciones"

    try:
        print(f"1. Conectando a: {url}")
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode('utf-8'))

        canciones = []
        if 'documents' in data:
            print(f"   ✓ {len(data['documents'])} documentos encontrados\n")

            for doc in data['documents']:
                fields = doc.get('fields', {})

                bpm = fields.get('bpm', {}).get('integerValue')
                cancion = {
                    'id': doc['name'].split('/')[-1],  # último segmento del path
                    'nombre': fields.get('nombre', {}).get('stringValue', 'Sin nombre'),
                    'tono': fields.get('tono', {}).get('stringValue'),
                    'bpm': int(bpm) if bpm is not None else None,
                    'bloques': _valor_firestore(fields.get('bloques')) or [],
                    'nueva': fields.get('nueva', {}).get('booleanValue', False),
                    'borrada': fields.get('borrada', {}).get('booleanValue', False),
                }

                canciones.append(cancion)

            # Guardar en JSON
            with open('firestore_canciones.json', 'w', encoding='utf-8') as f:
                json.dump(canciones, f, ensure_ascii=False, indent=2)

            print(f"✓ {len(canciones)} canciones guardadas en firestore_canciones.json")
            return canciones

        else:
            print("✗ No se encontraron documentos")
            print(f"Respuesta: {data}")
            return []

    except urllib.error.HTTPError as e:
        print(f"✗ Error HTTP {e.code}")
        if e.code == 403:
            print("  → Acceso denegado. Firestore REST API podría requerir autenticación.")
            print("  → Solución: Necesitas una API key o usar Firebase Admin SDK.\n")
        print("=" * 70)
        print("ALTERNATIVA: Usar Firebase Console\n")
        print("1. Ve a Firebase Console → Cancionero Peniel")
        print("2. Firestore Database → Colección 'canciones'")
        print("3. Toca el ícono ⋮ (menú) arriba a la derecha de la colección")
        print("4. Selecciona 'Exportar colección'")
        print("5. Guarda el archivo JSON descargado como 'firestore_canciones.json'")
        return []

    except Exception as e:
        print(f"✗ Error: {e}")
        return []

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    canciones = descargar_canciones_firestore()

    if canciones:
        print("\n" + "=" * 70)
        print("Próximo paso: python comparar_duplicados.py")

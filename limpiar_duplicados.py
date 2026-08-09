#!/usr/bin/env python3
import sys
import json
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================================
# Remover los 76 duplicados de Firestore del catálogo.json
# ============================================================================

print("🎵 Limpiador de duplicados\n")

# 1. Cargar lista de IDs a remover
print("1. Cargando lista de duplicados...")
try:
    with open('duplicados_firestore_ids.json', 'r', encoding='utf-8') as f:
        ids_para_remover = json.load(f)
    print(f"   ✓ {len(ids_para_remover)} IDs para remover\n")
except FileNotFoundError:
    print("   ✗ No encontré duplicados_firestore_ids.json")
    print("   Ejecuta: python comparar_duplicados.py\n")
    sys.exit(1)

# 2. Cargar catálogo actual
print("2. Cargando catálogo actual...")
with open('catalogo.json', 'r', encoding='utf-8') as f:
    catalogo = json.load(f)
print(f"   ✓ {len(catalogo)} canciones actuales\n")

# 3. Remover duplicados
print("3. Removiendo duplicados...")
catalogo_limpio = [
    c for c in catalogo
    if c['id'] not in ids_para_remover
]
print(f"   ✓ {len(catalogo) - len(catalogo_limpio)} removidas")
print(f"   ✓ {len(catalogo_limpio)} canciones restantes\n")

# 4. Guardar
print("4. Guardando catálogo limpio...")
with open('catalogo.json', 'w', encoding='utf-8') as f:
    json.dump(catalogo_limpio, f, ensure_ascii=False, indent=2)
print(f"   ✓ Guardado en catalogo.json\n")

# 5. Resumen
print("=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"Catálogo original:  {len(catalogo)} canciones")
print(f"Removidas:          {len(catalogo) - len(catalogo_limpio)}")
print(f"Catálogo limpio:    {len(catalogo_limpio)} canciones")
print(f"\nProximo paso: python build.py")

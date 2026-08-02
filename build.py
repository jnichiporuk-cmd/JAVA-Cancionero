# ARMADO de la app final.
#
# Junta plantilla.html (la interfaz) con catalogo.json (las canciones sacadas
# del .docx) y escribe el archivo que se usa en el celular.
#
# Este paso se repite cada vez que se agregan canciones al cancionero:
#   python3 extraer.py && python3 build.py
# Así el catálogo nunca se edita a mano y no se desincroniza del .docx.

import json
import re
import subprocess

# Número de armado incremental. Cada build genera un archivo con nombre
# distinto para que no se confunda con los anteriores ya descargados, y el
# número queda visible en el encabezado de la app.
try:
    BUILD = int(open("build_num.txt").read().strip()) + 1
except Exception:
    BUILD = 1
open("build_num.txt", "w").write(str(BUILD))

SALIDA = "index.html"   # lo que sirve GitHub Pages

with open("catalogo.json", encoding="utf-8") as f:
    catalogo = json.load(f)

plantilla = open("plantilla.html", encoding="utf-8").read()

# El JSON va dentro de <script type="application/json">, así que hay que
# escapar la secuencia que cerraría el tag antes de tiempo.
datos = json.dumps(catalogo, ensure_ascii=False, separators=(",", ":"))
datos = datos.replace("</", "<\\/")

if "__CATALOGO__" not in plantilla:
    raise SystemExit("ERROR: la plantilla no tiene el marcador __CATALOGO__")

html = plantilla.replace("__CATALOGO__", datos).replace("__VERSION__", f"v{BUILD}")

# --- Verificaciones antes de escribir --------------------------------------
fallos = []
for marcador in ("__CATALOGO__", "__VERSION__"):
    if marcador in html:
        fallos.append(f"quedó el marcador {marcador} sin reemplazar")
if "CATALOGO_ES_DEMO" in html or "demo-1" in html:
    fallos.append("quedaron restos del catálogo de prueba")
if html.count("<script") != html.count("</script>"):
    fallos.append("tags <script> desbalanceados")
# localStorage es correcto para datos locales de cada dispositivo: ajustes,
# rol elegido, id del dispositivo, evento elegido. Lo que NO debe pasar es
# que los datos compartidos —la lista de la reunión, ediciones, transmisión—
# terminen ahí, porque entonces cada uno vería los suyos y nadie se enteraría.
# Se controla que sólo se use con esas claves específicas.
usos = re.findall(r'localStorage\.\w+\(\s*"([^"]*)"', html)
locales = {"cancionero:ajustes", "cancionero:rol", "cancionero:dispositivoId", "cancionero:eventoId"}
ajenos = [u for u in usos if u not in locales]
if ajenos:
    fallos.append(f"localStorage usado para datos que deberían ser compartidos: {ajenos}")
if "sessionStorage" in html:
    fallos.append("usa sessionStorage: se pierde al cerrar la pestaña")

# El JSON incrustado tiene que volver a parsearse igual
inc = re.search(r'<script type="application/json" id="datos-catalogo">(.*?)</script>', html, re.S)
if not inc:
    fallos.append("no se encuentra el bloque de datos en la salida")
else:
    vuelta = json.loads(inc.group(1).replace("<\\/", "</"))
    if len(vuelta) != len(catalogo):
        fallos.append(f"el JSON incrustado tiene {len(vuelta)} canciones y no {len(catalogo)}")

# Los id que busca el JS tienen que existir en el HTML. Un id mal escrito
# devuelve null y corta la función entera en silencio, sin que se note
# hasta que alguien abre esa pantalla.
declarados = set(re.findall(r'\bid="([^"]+)"', html))
buscados = set(re.findall(r'\$\("([^"]+)"\)', html))
huerfanos = buscados - declarados
if huerfanos:
    fallos.append(f"ids que el JS busca y no existen: {sorted(huerfanos)}")

# Las funciones tienen que estar en el <script>, no en el <style>. Un
# parche mal anclado puede meter código JS dentro del CSS: el navegador lo
# ignora, no da error de sintaxis, y la función queda indefinida hasta que
# alguien abre esa pantalla.
try:
    fin_estilo = html.index("</style>")
    for fn in ("function pintarBloques", "function bloquesATexto",
               "function textoABloques", "function abrirEditor",
               "function guardarEditor", "function recalcular"):
        if fn not in html:
            fallos.append(f"falta {fn}")
        elif html.index(fn) < fin_estilo:
            fallos.append(f"{fn} quedó fuera del bloque JavaScript (está en el CSS)")
except ValueError:
    fallos.append("no se encuentra el cierre de </style>")

if fallos:
    for f_ in fallos:
        print("FALLA:", f_)
    raise SystemExit(1)

# Antes de escribir el archivo definitivo, se ejecuta la app en Node con un
# DOM simulado y se recorren los caminos que usa el grupo. Si algo revienta,
# no se genera el archivo: es mejor fallar acá que en medio de una reunión.
with open("_prueba.html", "w", encoding="utf-8") as f:
    f.write(html)
r = subprocess.run(["node", "probar_app.js", "_prueba.html"],
                   capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode != 0:
    print(r.stderr.strip())
    raise SystemExit("La prueba de ejecucion fallo: no se genera el archivo")

with open(SALIDA, "w", encoding="utf-8") as f:
    f.write(html)

print(f"OK  {SALIDA}")
print(f"    {len(catalogo)} canciones")
print(f"    {sum(len(c['bloques']) for c in catalogo)} líneas")
print(f"    {len(html)/1024:.0f} KB")

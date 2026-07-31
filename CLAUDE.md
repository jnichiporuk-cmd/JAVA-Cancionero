# Cancionero — contexto del proyecto

Este archivo se llama `CLAUDE.md` a propósito: Claude Code lo lee solo al abrir
la carpeta, sin que haya que pegarlo en cada conversación. Está escrito para
que cualquiera —o cualquier Claude— pueda retomar el proyecto sin haber estado
en las conversaciones anteriores.

---

## 1. Qué es esto y para quién

Cancionero web para un grupo de música de iglesia. Se usa **en el celular,
arriba del escenario, durante la reunión**. Lo abren varios músicos a la vez y
todos tienen que ver la misma lista de canciones.

Reemplaza un `.docx` de 133 canciones que se venía manteniendo a mano y se
sigue actualizando cada tanto.

### Restricciones que mandan sobre cualquier otra consideración

- **Se lee con una guitarra en la mano, de reojo, con poca luz.** Por eso fondo
  oscuro, tipografía grande y ajustable, y nada que requiera precisión con el
  dedo.
- **Los acordes tienen que caer sobre la sílaba exacta.** Todo el cuerpo de la
  canción se dibuja con tipografía monoespaciada y `white-space: pre`. **Los
  espacios son contenido, no formato**: cualquier cosa que los normalice,
  recorte o colapse rompe la app.
- **El wifi de la iglesia se cae.** El catálogo va dentro del HTML, así que la
  app abre y funciona sin internet. Solo la lista y las ediciones necesitan red.
- **Varios a la vez.** La lista de la reunión es compartida y en tiempo real.

---

## 2. Arquitectura

### Catálogo en dos capas

| Capa | Dónde vive | Se modifica |
|---|---|---|
| Base: 96 canciones del `.docx` | Dentro del HTML, como JSON | Nunca en runtime |
| Cambios: ediciones, nuevas, borradas | Firestore | Desde la app |

Al abrir, la app suma las dos (`recalcular()`). La capa base intacta es la red
de seguridad: si la capa de cambios se corrompe, se borra y vuelve el
cancionero original.

### Firestore

```
cancionero/activa      ->  { reunionActivaId }
reuniones/{id}         ->  { nombre, ids: [...], semis: {...}, porQuien, creada, actualizada }
canciones/{id}         ->  { nombre, tono, bpm, bloques, nueva, borrada, cuando }
```

`cancionero/activa` es sólo un puntero: dice cuál `reuniones/{id}` es "la
reunión de ahora", la que ve la pestaña Reunión y el modo reunión arriba del
escenario. Cambiar de reunión activa (crear una nueva, o elegir una guardada
desde la pestaña Guardadas) es mover ese puntero; la reunión anterior queda
intacta en su propio documento, no se pisa ni se copia.

**Una canción y una reunión por documento, a propósito.** Si dos personas
editan canciones distintas —o reuniones distintas— al mismo tiempo, escriben
en documentos distintos y no pueden pisarse. La primera versión usaba un
documento único con toda la capa de cambios (y, después, un único documento
para "la lista de la reunión") y el último en guardar borraba el trabajo del
otro.

Los borrados **marcan** `borrada: true`, no eliminan el documento: si se
eliminara, los otros dispositivos no tendrían cómo enterarse.

`onSnapshot` avisa al instante. **No hay sondeo periódico**; si aparece un
`setInterval` consultando datos, es un retroceso.

### Formato de una canción

```json
{
  "id": "glorioso-dia-g",
  "nombre": "Glorioso día",
  "tono": "G",
  "bpm": 72,
  "bloques": [
    {"t": "r", "v": "Intro"},
    {"t": "a", "v": "        D"},
    {"t": "l", "v": "Mi vergüenza me sepultó"},
    {"t": "v"}
  ]
}
```

`t` es el tipo de línea y sale directo de los estilos de Word:

| `t` | Qué es | Estilo Word | Color |
|---|---|---|---|
| `r` | Rótulo de sección | Subtítulo | Gris `BFBFBF`, cursiva |
| `a` | Línea de acordes | Estilo1 | Azul `00B0F0` |
| `l` | Línea de letra | Normal | Negro / blanco |
| `v` | Línea en blanco | — | — |

`tono` y `bpm` pueden ser `null`. Sin tono, la app **apaga el transporte** en
vez de suponer uno.

---

## 3. Guía de formato del cancionero (reglas del `.docx`)

Fuente: Arial Nova Cond, 12 pt. Cada canción empieza en página nueva. Orden:
título → rótulo → acordes/letra → línea en blanco entre secciones. Los acordes
van siempre en línea propia, arriba de la letra.

**Título**: `NOMBRE - Tono - BPM`, en mayúsculas. El nombre alternativo o autor
entre paréntesis se conserva: `Alaba (Evan Craft)`.

**Rótulos**: mayúscula inicial, resto minúscula, sin `:`, sin corchetes ni
barras (`[Coro]`, `/Coro/` → `Coro`). Repetición → `(xN)`: `Puente (x2)`.
Aclaración pegada a la sección se fusiona en minúscula:
`Verso 2 (igual a verso 1)`.

**Acordes**: nunca entre paréntesis, salvo extensiones del acorde
(`G#(add4)`). Compás entre barras: `| E | B | C#m | A |`. Varios acordes en un
compás, juntos con espacios: `| Bm  D | G  A |`. Secuencia sin compás, con
espacios y sin barras: `C  G  Am  F`. **Sin guiones**: `D - Bm` → `D  Bm`.

**Aclaraciones de ejecución**: nota gris, entre paréntesis, en línea propia:
`(Mantenido durante 4 compases)`, `(Drop)`.

**Sección que se repite**: rótulo gris + `…` debajo, también gris.

---

## 4. Decisiones ya tomadas — no revertir sin preguntar

Cada una costó una conversación. Si algo parece una mejora obvia, probablemente
ya se discutió:

- **El BPM sale de los tempos a los que toca el grupo**, no de la web ni de la
  grabación oficial, que difieren. Si falta, se deja vacío. **No se completa
  buscándolo.**
- **No se agrega el artista al nombre**, salvo para distinguir dos canciones
  que se llaman igual.
- **El transporte fuera de una reunión es por dispositivo y no se guarda**:
  mirar una canción desde Canciones arranca siempre en su tono original. Fue
  una decisión explícita, no un olvido. **Dentro de una reunión** el
  transporte sí se guarda, pero por reunión, no en la canción: cada
  `reuniones/{id}` tiene su propio mapa `semis` (`{ [idCanción]: semitonos }`)
  con los desvíos del tono original para esa reunión puntual, sin tocar
  `canciones/{id}`. Al volver a abrir esa reunión, cada canción vuelve a
  aparecer en el tono en que se dejó. Distinto de transportar desde el
  editor (`transportarEditor()`), que reescribe el tono y los acordes de la
  canción en sí: ese cambio es permanente y para todas las reuniones.
- **El catálogo no se edita a mano.** Sale del `.docx` vía `extraer.py`. Editar
  `catalogo.json` directo se pierde en el próximo build.
- **El id de una canción se genera del nombre y el tono** (`hacer_id()` en
  `extraer.py`), y no se guarda en ningún lado entre un build y el siguiente.
  Corregir un título o transportar el original cambia el id, y eso rompe la
  referencia en cualquier reunión guardada que ya tuviera esa canción (la
  fila pasa a decir "Canción no encontrada"). Cuando eso importa —la canción
  ya está en reuniones guardadas—, se fuerza el id viejo a mano en el
  diccionario `IDS_FORZADOS` de `extraer.py`, en vez de rediseñar el esquema
  de ids para que sean estables. Pasó primero con "En la cruz (53)" → "En la
  cruz" y con "Tu amor" transportada de C a D.
- **El nombre del archivo lleva número de versión y la versión se ve en el
  encabezado de la app.** Sin eso es imposible saber si un celular está
  abriendo un archivo viejo cacheado; ya pasó tres veces.
- **Dos canciones con el mismo nombre y distinto tono son versiones a
  propósito** (`Tómalo` en B y D, `Agradecido Estoy` en G y D). No unificar.
- **El catálogo va dentro del HTML, no en la base**, para que abra sin internet
  y el uso de Firestore quede en el plan gratuito.

---

## 5. Flujo de trabajo

```bash
unzip -o Cancionero_2026-06.docx -d desarmado/   # solo si cambió el .docx
python3 extraer.py                               # .docx  -> catalogo.json
python3 build.py                                 # plantilla + catálogo -> index.html
```

**Se edita `plantilla.html`, nunca el HTML generado.**

`build.py` no genera el archivo si alguna de estas verificaciones falla:

1. No quedan marcadores `__CATALOGO__` / `__VERSION__` sin reemplazar.
2. El JSON incrustado se vuelve a parsear con la misma cantidad de canciones.
3. Todos los `id` que busca el JavaScript existen en el HTML.
4. Las funciones clave están en el `<script>` y no dentro del `<style>`.
5. `localStorage` solo se usa para `cancionero:ajustes`.
6. `probar_app.js` ejecuta la app en Node con un DOM simulado y recorre 14
   caminos de uso sin errores.

Cada verificación existe porque un error de esa clase ya se escapó una vez.

### Para probar en el navegador

**No abrir el HTML con doble clic.** Con `file://` el navegador bloquea la
carga de módulos desde `gstatic.com` y Firebase no inicializa; se ve "sin
conexión" y parece un problema de configuración.

```bash
python3 -m http.server 8000
```

---

## 6. Trampas conocidas

- **`file://` rompe Firebase.** Ver arriba.
- **Falta `<meta charset="utf-8">` y los acentos se rompen** al abrir el
  archivo suelto en Chrome. Tiene que ser lo primero del documento.
- **Un `id` mal escrito devuelve `null` y corta la función entera en silencio.**
  Pasó con `lector-pie` vs `l-pie`: rompía el modo reunión sin dar error hasta
  esa pantalla. Por eso la verificación 3.
- **Anclar un parche en un comentario que existe en el CSS y en el JS.** Pasó:
  las funciones terminaron dentro del `<style>`, el navegador las ignoró y no
  hubo error de sintaxis. Por eso la verificación 4.
- **El detector de acordes tiene que partir los `/` antes de validar.** `D/F#`
  son dos notas; validando el token entero, la `F` del bajo parece basura.
- **Editar `index.html` en vez de `plantilla.html`.** Pasó: la configuración de
  Firebase se pegó en el archivo generado y el siguiente build la borró. El
  síntoma es que la app dice "sin configurar" aunque uno juraría haberla
  cargado. Comprobación rápida:
  `Select-String -Path plantilla.html,index.html -Pattern 'projectId:'`
- **Guardar el archivo antes de compilar.** VS Code marca con un punto ● en la
  pestaña los archivos con cambios sin guardar. `build.py` lee el archivo del
  disco, no lo que se ve en pantalla.
- **Una colección nueva en Firestore no funciona hasta agregarla a las
  reglas.** La última regla es `match /{document=**} { allow read, write: if
  false; }`, que niega todo lo que no esté declarado antes. Si se agrega una
  colección y se olvida la regla, la app va a decir "error de permisos" y
  parecerá un error de código.
- **Al transportar hay que conservar las columnas.** Si `G` pasa a `A#` y ocupa
  un carácter más, se come un espacio de al lado en vez de correr toda la línea
  y desalinear la letra.

---

## 7. Estado actual

**96 canciones en la app, de 133 en el `.docx`.** 37 quedaron afuera, con el
motivo de cada una en `pendientes.json`:

| Motivo | Canciones |
|---|---|
| Nunca pasaron por el formateo: acordes y letra comparten el estilo `HTMLconformatoprevio` | 10 |
| Líneas de acordes con estilo de letra (`Normal`) | 9 |
| Letra o anotaciones dentro de la línea de acordes (`Estilo1`) | 15 |
| Título sin nada debajo en el `.docx` | 3 |

Dentro de las 96 que sí entraron hay ~40 líneas que se ven en el color
equivocado: rótulos que quedaron como letra (`[Verso 1]`), acordes en cifrado
latino (`DO RE MI`) y acordes con barras de repetición (`//Em - D - G - C //`).
No pierden información; salen en blanco en vez de gris o azul.

### Pendiente concreto: notación de 9 canciones

| Canción | Línea | Qué corregir |
|---|---|---|
| Seas Exaltado oh Dios | `A   Fm#  Bm` | `Fm#` → `F#m` |
| Cristo te exalto | `Cm#7   F#m` | `Cm#7` → `C#m7` |
| Tu ere el lugar | `A7   D   Fm#` | `Fm#` → `F#m` |
| Mi ser alaba al Señor | `Bb   D-7   C   G-   F` | `D-7` → `Dm7`, `G-` → `Gm` |
| El Dios que adoramos | `G  - D  - Em  - C  - D   x2` | guiones fuera, `x2` → `(x2)` |
| Amigo en lugares altos | `G C, G C, G C, G C` | comas fuera |
| Digno de alabar | `Bm / D  / \| G  / A  / \|` | barras de ritmo fuera (17 líneas) |
| Digno de Adorar | 16 líneas | solo falta cambiarles el estilo |
| Quiero conocer a Jesús (Jeshua) | `D    G` | solo falta cambiarles el estilo |

**Caso sin resolver**, en `Digno de alabar`:

```
   D  / F#       G        D  / A   A
```

`D  / F#` puede ser **D con bajo en F#** (`D/F#`) o **D, golpe, F#**, siguiendo
el patrón de la línea de arriba donde la barra es claramente un tiempo. Suenan
distinto. **Requiere escuchar la canción o mirar el original: no se decide por
regla.**

### Ya está desplegado y funcionando

| | |
|---|---|
| Proyecto Firebase | `cancionero-peniel`, plan Spark (gratuito) |
| Firestore | Edición Standard, `southamerica-east1` (São Paulo), base `(default)` |
| Repositorio | `jnichiporuk-cmd/JAVA-Cancionero`, público |
| Publicado en | `https://jnichiporuk-cmd.github.io/JAVA-Cancionero/` |

`FIREBASE_CONFIG` en `plantilla.html` está completo. La escritura y la lectura
en tiempo real quedaron verificadas entre `localhost` y GitHub Pages: una lista
armada en uno aparece en el otro.

**Falta probar con dos celulares a la vez**: uno suma una canción y el otro
debería verla aparecer sola, sin recargar.

## 8. Entorno de trabajo

Windows con PowerShell, VS Code, Python 3.12, Node v24.

- El comando es **`python`**, no `python3`. Si `python3` no se reconoce, ese es
  el motivo.
- La carpeta está en `OneDrive\Documentos\JAVA-Cancionero`. Funciona, pero
  OneDrive a veces bloquea archivos mientras sincroniza y puede hacer fallar un
  build o un commit con errores de "archivo en uso". Si aparecen, mover la
  carpeta fuera de OneDrive.
- La terminal de PowerShell muestra los acentos mal (`canciÃ³n`). Es solo la
  consola: los archivos están bien.

## 8b. Guardar reuniones — implementado

Ya no hay una sola lista que se pisa: cada reunión (cada domingo, cada
ensayo) es su propio documento en `reuniones/{id}`, y `cancionero/activa`
es un puntero que dice cuál de todas es "la de ahora". Pestaña nueva,
**Guardadas**, lista todas las reuniones y deja crear una nueva o elegir
cuál es la activa (`usarReunion()`).

No quedó un botón "Guardar": cada vez que se toca **+** en una canción ya
se escribe directo en la reunión activa (`alternarEnLista()` → `guardarLista()`
con `setDoc(..., {merge:true})`). Si todavía no hay ninguna reunión activa,
el primer + crea una sola con la fecha de hoy como nombre
(`generarIdReunion()` + `crearReunion()`) y la deja activa. Por eso el
problema de "pisar una lista sin guardar" (uno de los puntos que se había
identificado como difícil) directamente no existe en este modelo: cambiar
de reunión activa es mover el puntero, nunca copiar ni sobrescribir, así
que ninguna reunión vieja se pierde.

El caso de una canción borrada dentro de una reunión guardada usa el mismo
fallback que ya existía en `pintarReunion()` ("Canción no encontrada"), sin
código nuevo para eso.

**Pendiente real**: publicar las reglas de Firestore nuevas (ver
`README.md`, sección 2) desde la consola de Firebase. Sin ese paso, crear o
cambiar de reunión va a fallar con "error de permisos" aunque el código esté
bien. Después de publicarlas, falta la prueba de siempre con dos celulares:
uno toca + y el otro debería ver aparecer la canción sin recargar, y lo
mismo al tocar "Usar esta" en Guardadas.

## 8c. Modo Director / Modo Online

Cualquiera puede prender **Director** (chip en la pestaña Reunión, o botón
`D` en el lector): mientras está prendido, cada canción que abre y cada
transporte que hace se escribe en `cancionero/directorEnVivo`
(`transmitirEstado()`). Quien tenga **Modo Online** prendido (`O` en el
lector, o chip en Reunión) escucha ese documento y su lector salta solo a
lo mismo (`seguirAlDirector()`), tono incluido.

No hay "un" director: no se pelea el control, cualquiera que lo prenda
transmite, y gana la última escritura si dos lo tienen prendido a la vez.
Fue una decisión explícita — el grupo es chico y se asume que se
coordinan solos, no hace falta resolver conflictos en el código.

Mientras se sigue al director (Modo Online prendido y no se es director),
la navegación manual queda bloqueada: `paso()`, los botones del riel,
deslizar para los costados y ♭/♯ no hacen nada (se chequea
`est.modoOnline && !est.esDirector` en cada uno). La tarjeta "Siguiente"
del pie se reemplaza por un aviso de que se está siguiendo, para que no
parezca que dejó de responder.

## 9. Cómo trabajar en este proyecto

**Al arrancar cualquier conversación en esta carpeta**, revisar hace cuánto
fue el último cambio en `catalogo.json` o en el `.docx`
(`git log -1 --format="%ai" -- catalogo.json Cancionero_2026-06.docx`). Si
pasó una semana o más, avisarle al usuario que puede haber cambios en
Firestore (ediciones desde la app) sin graduar al `.docx` todavía, y
preguntar si quiere revisarlos ahora. No hace falta hacer nada más que
avisar: la graduación en sí sigue siendo con revisión antes de publicar,
como se hizo con las primeras 5 canciones.

Convenciones de código:

- Comentarios **en español**, explicando qué hace, para qué sirve y **por qué**,
  pensados para releerlos en unos meses.
- Nombres y sintaxis según el lenguaje.
- Comentar cada sección a modo de ayuda memoria.

Forma de trabajo esperada:

- **No inventar datos.** Si falta un dato, marcarlo con `[COMPLETAR]` o
  `[VERIFICAR]` en vez de rellenarlo con una plantilla o una suposición. Aplica
  fuerte a los BPM y a los tonos ausentes.
- **Auditar la salida completa antes de mostrarla**, contra el criterio que se
  acordó. No hacer que el usuario encuentre el mismo tipo de error ya corregido.
- **Lo que requiere criterio caso por caso no se convierte en un script de
  reglas fijas.** Las 37 canciones pendientes se revisan una por una, aunque
  sea más lento. Ya se intentó resolverlas por regla y por eso hay ~40 líneas
  mal clasificadas dentro de las 96 "limpias".
- **En tareas con varias decisiones, resolver de a una**: proponer opciones,
  mostrar el caso real, esperar confirmación.
- **Cuando haya que guiar una serie de pasos, dar UN paso por vez.** Se puede
  dar un resumen breve de la secuencia completa al principio, pero después se
  entrega un solo paso y se espera la confirmación antes de seguir al
  siguiente. Si el usuario avisa que ya hizo algunos pasos, se saltean sin
  repetirlos.
- Respuestas sin relleno. Tablas cuando ordenan mejor los datos. Código
  completo salvo que se pida una parte.

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

Los borrados de **canciones marcan** `borrada: true`, no eliminan el
documento: si se eliminara, los otros dispositivos no tendrían cómo
enterarse (cada canción se escucha por su propio documento, no hay
ningún listener sobre toda la colección que note que faltó uno).

**Los eventos del historial sí se borran de verdad** (`borrarReunion()`,
sólo el director, nunca el evento activo). Es la excepción a la regla de
arriba, y es segura por lo mismo: a diferencia de `canciones/{id}`, acá
sí hay un `onSnapshot` sobre toda la colección `reuniones` (para listar
el historial), así que un borrado real también se nota al instante en
los demás dispositivos.

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

## 8c. Modo Director / pestaña Online

Cualquiera puede prender **Director** (chip en la pestaña Evento, o botón
`D` en el lector). Ojo: prender Director **no transmite nada solo**. Un
director necesita poder mirar canciones del Evento sin que cada una se
vuelva lo que está en vivo — si no, no hay forma de revisar la letra de
la próxima antes de tocarla. Lo que transmite es el botón **O**
(`online-badge`, al lado de `D` en el `.ctrl`), que aparece en cualquier
canción mientras se es director: apagado si esa canción no es la que
está en vivo, verde si sí lo es. Tocarlo llama a `transmitirEstado()` a
propósito. Abrir otra canción, deslizar o usar el riel sólo cambian la
vista local, sin tocar `cancionero/directorEnVivo` — para eso está el
botón. La única transmisión que sale sola es un transporte (♭/♯)
**cuando la canción que se está viendo ya es la que está en vivo**
(`retransmitirSiYaEstaEnVivo()`): ahí sí tiene sentido que se actualice
al toque, es corregir el tono en el momento, no arrancar algo nuevo.

No hay "un" director: no se pelea el control, cualquiera que lo prenda
transmite, y gana la última escritura si dos lo tienen prendido a la vez.
Fue una decisión explícita — el grupo es chico y se asume que se
coordinan solos, no hace falta resolver conflictos en el código.

**`directorEnVivo.directores` cuenta cuántos dispositivos tienen el chip
prendido** (`+1`/`-1` con `increment()` al prender/apagar, en
`alternarDirector()`). Online se considera vacío en cuanto ese número
llega a 0, aunque el documento todavía tenga un `cancionId` viejo
colgado — así apagar Director vacía la pantalla de todos en vez de dejar
pegada la última canción para siempre. **Límite conocido:** si alguien
cierra la app sin apagar el chip a propósito, ese `+1` no baja solo; se
corrige a mano desde la consola de Firebase (mismo tipo de arreglo que
otros documentos huérfanos de este proyecto, ver sección 8b).

**La pestaña Online no tiene un botón de "activar".** `escucharDirector()`
arranca solo junto con el resto de los listeners (`escuchar()`). Entrar a
la pestaña Online (`pintarOnline()`) alcanza: si hay alguien dirigiendo,
abre directo el `.lector` de siempre con `est.soloLectura = true`
(`mostrarVistaOnline()`); si no, se queda en un aviso de vacío (o "hay
una transmisión en vivo, tocá para verla" si `fondoOnline()` encuentra
algo pero todavía no se abrió — pasa apenas al entrar, se tapa enseguida
por el `.lector`, casi no se llega a ver). La flecha de volver
(`cerrarLector()`) cierra la vista y siempre manda al listado de
canciones del Evento, sea o no director quien la estaba mirando — ahí
nunca se queda nadie parado en Online sin nada para hacer. Si deja de
haber director mientras alguien mira la vista en vivo, se cierra sola
(`cerrarVistaOnline()`, distinta de `cerrarLector()`: no manda a ningún
lado, sólo vuelve al aviso de vacío en la misma pestaña).

**El bloqueo de sólo lectura no es sólo para la vista en vivo: es para
cualquier canción vista dentro de un evento.** Abrir una canción desde el
Evento y abrirla desde Online comparten el mismo `est.enReunion = true`,
así que el bloqueo es `est.enReunion && !est.esDirector` (`bloqueado` en
`pintarLector()`, mismo chequeo al principio de `paso()`) — no
`est.soloLectura`. Sin ser director, dentro de un evento se ve todo
(acordes, letra, riel con la posición) pero no se puede tocar nada:
transportar, el riel, deslizar, Anterior/Siguiente y editar quedan
apagados o escondidos. `guardarSemisSiCorresponde()` repite el mismo
chequeo (`if (!est.esDirector) return`) como segunda barrera, no sólo
apagar el botón. Si quien mira también es director, no se le apaga nada
— sigue con control completo, mire lo que mire. Fuera de un evento
(pestaña Canciones, `abrir(id, false)`, que también apaga `enReunion` y
`soloLectura`) la app queda completamente libre, sea o no director quien
la esté usando: ahí el transporte es de sesión, por dispositivo, y no se
comparte con nadie.

Motivo: antes sólo se bloqueaba mirando la transmisión en vivo: cualquiera
podía abrir una canción del Evento y transportarla, y como `guardarLista()`
manda el mapa `semis` completo (no sólo lo que cambió), dos celulares
transportando canciones distintas —o el mismo, en momentos distintos—
podían pisarse entre sí sin que nadie tocara la misma canción a propósito.
Pasó en la práctica: "Glorioso día" quedó pisada en Eb cuando el original
es D. Limitar el transporte al director bajó cuántos dispositivos escriben
esos campos, pero **no alcanzó**: el diseño permite varios directores a la
vez a propósito (no hay "un" director, ver más abajo), así que el mismo
choque siguió pasando entre dos directores. Se repitió en la práctica una
segunda vez con la misma canción, ya con el bloqueo puesto.

La solución de fondo fue otra: `guardarSemisSiCorresponde()` ya no pasa
por `guardarLista()` para el transporte. Escribe directo con
`updateDoc(ref, { [\`semis.${id}\`]: semis || deleteField() })`, notación
de punto que sólo toca esa clave del mapa en el servidor, sin mandar
`ids` ni el resto de `semis`. Dos directores transportando canciones
distintas —o la misma, en momentos distintos— ya no se pisan, porque cada
transporte es su propia escritura puntual, no una foto completa del
documento. El mismo riesgo sigue latente en `guardarLista()` para `ids`
(agregar, sacar, reordenar canciones): ese camino no se tocó todavía.

## 8d. Notas/Anotaciones en eventos — implementado

**Notas** son anotaciones de texto libre intercaladas entre canciones en la
lista del evento. Sirven para pausas, lecturas, bienvenidas, o instrucciones
que el director quiera que aparezcan en secuencia.

### Estructura y almacenamiento

- **ID**: prefijo `"nota:"` + timestamp + random → `"nota:mselcydlbq2iejn"`
  - Prefijo garantiza cero colisiones con IDs de canciones (que son `name-tono`)
- **Contenido**: objeto `{nombre: "...", contenido: "..."}`
  - `nombre`: título de la anotación ("Pausa", "Lectura Sal 119:1", etc.)
  - `contenido`: texto libre con detalles (multilinea, respeta saltos)
- **Ubicación**: dentro de cada `reuniones/{id}`:
  - `ids`: array que mezcla IDs de canciones y notas en orden
  - `notas`: map `{ [idNota]: {nombre, contenido}, ... }`
  - No toca nada en el catálogo base (`canciones/{id}`)

### Ciclo de vida

1. **Crear**: director toca "+ Nota" en pie de evento
   - Abre diálogo con dos campos (nombre + contenido)
   - Se crea reunión automática si no existe (`alternarEnLista` pattern)
   - Se guarda en Firestore via `guardarLista()`

2. **Editar**: click en la nota desde lista de evento
   - Abre mismo diálogo con valores actuales
   - Persiste con `guardarLista()`

3. **Reordenar**: director entra en modo Reordenar
   - Mismo arrastre que canciones (toca el número, arrastra)
   - Notas participan en el riel numerado como cualquier paso

4. **Eliminar**: menú ⋮ de la nota, "Eliminar anotación"
   - Quita del array `ids` y del map `notas`
   - Persiste con `guardarLista()`

### En el lector

Cuando se abre una nota:
- **Título**: nombre de la nota (tipografía normal, grande)
- **Cuerpo**: contenido con saltos de línea (textarea, monoespaciado)
- **Sin transporte**: botones ♭/♯ apagados (las notas no tienen tono)
- **Riel**: número igual que canciones, navega por todos los pasos
- **Pie**: "+ Agregar" a la izquierda, "Siguiente" a la derecha (si existe)

### En transmisión

- **Online funciona igual para notas que para canciones**
  - Director transmite nota toca botón O (verde si está en vivo)
  - Otros ven en pestaña Transmisión: nombre de la nota y contenido
  - Navegación por riel retransmite automáticamente (mismo que canciones)
  - Sin transporte, pero sí aparece en "Siguiente" en el pie de otros

- **Bug arreglado** (v260): `renderOnline()` solo buscaba en `PORID`
  - Notas no están en `PORID`, así que "Online vacío" cuando era una nota
  - Ahora verifica tanto `PORID[id]` (canciones) como `est.lista.notas[id]`

### Restricciones (como diseño)

- **Solo director puede agregar/editar/eliminar** (check en `pintarReunion()`)
- **Cualquiera puede navegar** (notas son pasos del evento)
- **No hay límite de largo**, pero UI asume < 500 caracteres (textarea)
- **No se transportan** (sin tono, sin semis)
- **Se comparten en tiempo real** (Firestore `onSnapshot` como canciones)

### Funciones clave

- `esNota(id)` — detecta si id empieza con `"nota:"`
- `generarIdNota()` — crea ID único
- `soloCanciones(ids)` — filtra array para contar solo canciones (mostrador de "7 canciones")
- `mostrarDialogoNota(notaInicial, onGuardar)` — modal para crear/editar
- `agregarNota(nota)` — inserta en lista y Firestore
- `mostrarMenuNota(e, idNota)` — menú ⋮ con opciones

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

---

## 10. Referencia exhaustiva de funciones (104 totales)

Índice completo de TODAS las funciones. **Formato:** `` `función()` `` (código/azul) | **UI** (negrita) | texto normal.

**Guía de lectura:**
- `` `nombreFuncion()` `` (~línea): backticks para código, variables, rutas
- **Canciones**, **Botón Guardar**, **Chip D**: negrita para UI que ve el usuario
- "Llamada desde:": puede mezclar backticks (`` `función()` ``) + negrita (**UI**)

### 1. BÚSQUEDA Y FILTRADO

`filtrarCanciones(query, catalogo)` (~758)
- Busca en nombre, tono y letra de canciones
- Llamada desde: campo buscador en **Canciones**; panel **Agregar canción**

`obtenerContexto(cancion, query)` (~778)
- Extrae la línea de letra donde se encontró el resultado
- Llamada desde: `renderCatalogo()` y `renderAgregar()` para mostrar contexto

### 2. TRANSPORTE DE ACORDES (cambiar tono)

`moverNota(nota, semis, usarBemoles)` (~814)
- Transporta una nota individual (+/- semitonos)
- Llamada desde: `moverAcorde()`

`moverAcorde(ac, semis, usarBemoles)` (~822)
- Transporta un acorde completo (ej: "C" → "D")
- Llamada desde: `moverLinea()`

`moverTono(tono, semis)` (~832)
- Transporta el tono original de una canción
- Llamada desde: `transportarEditor()`

`moverLinea(linea, semis, usarBemoles)` (~845)
- Transporta una línea completa de acordes
- Llamada desde: `renderBloques()`

`transportar(delta)` (~2750)
- Botones ♭/♯ en lector: transporta +/- 1 semitono
- Llamada desde: Botones ♭/♯ en **Lector** (solo director en evento)

`transportarEditor(delta)` (~3170)
- Botones ♭/♯ en editor: transporta y reescribe la canción
- Llamada desde: Botones ♭/♯ en **Pantalla Editor**

### 3. RENDERIZADO DE CONTENIDO

`renderBloques(destino, bloques, semis, conBemoles)` (~874)
- Dibuja los bloques de una canción (acordes, letras, rótulos)
- Llamada desde: `renderLector()`

`bloquesATexto(bloques)` (~911)
- Convierte bloques JSON a texto (para editar)
- Llamada desde: `abrirEditor()`; compartirPDF()

`textoABloques(txt)` (~921)
- Convierte texto a bloques JSON (al guardar edición)
- Llamada desde: `guardarEditor()`

`renderCatalogo()` (~1793)
- Dibuja pestaña Canciones (lista con buscador)
- Llamada desde: `render()` cuando est.pestana === "canciones"

`renderLector()` (~2806)
- Dibuja pantalla de lectura de una canción
- Llamada desde: `abrir()`; paso(); transportar()

`renderReunion()` (~1878)
- Dibuja pestaña Evento (lista de canciones del evento)
- Llamada desde: `render()` cuando est.pestana === "reunion"

`renderAgregar()` (~2337)
- Dibuja panel "Agregar canción" dentro de evento
- Llamada desde: `abrirAgregar()`

`renderGuardadas()` (~2382)
- Dibuja pestaña Guardadas (historial de eventos)
- Llamada desde: `render()` cuando est.pestana === "guardadas"

`renderOnline()` (~2513)
- Dibuja pestaña Transmisión (director en vivo)
- Llamada desde: `render()` cuando est.pestana === "online"

`render()` (~1749)
- Renderiza la pantalla actual según est.pestana
- Llamada desde: Automáticamente en listeners de Firestore y tras cada acción

### 4. LECTOR (lectura de canciones)

`abrir(id, enReunion)` (~2744)
- Abre una canción en el lector
- Llamada desde: Tocar canción en lista (Canciones/Evento); links compartidos

`cerrar()` (~2758)
- Cierra el lector y vuelve a la pantalla anterior
- Llamada desde: **Botón** flecha ◀ al abrir canción

`paso(delta)` (~3085)
- Navega anterior/siguiente en evento (+1 o -1 pasos)
- Llamada desde: **Botones** ◀ Anterior, Siguiente ▶ en **Lector** (modo evento)

`cerrarLector()` (~2798)
- Cierra lector y vuelve a la pantalla anterior
- Llamada desde: **Botón** ◀ en pie del lector

`hacerScrollRiel()` (~2765)
- Ajusta scroll del riel (posición dentro del evento)
- Llamada desde: `renderLector()`

`reiniciarColapsoTope()` (~3034)
- Reinicia el colapso de encabezado al abrir canción
- Llamada desde: `abrir()`; cerrar()

`actualizarColapsoTope()` (~3045)
- Actualiza si encabezado está colapsado según scroll
- Llamada desde: Listener de scroll en **Lector**

`actualizarVisibilidadPie()` (~3051)
- Muestra/oculta pie según scroll (para leer)
- Llamada desde: Listener de scroll en **Lector**

`actualizarPieCercaFin()` (~3077)
- Muestra pie completo si está cerca del final
- Llamada desde: Listener de scroll en **Lector**

### 5. EDITOR DE CANCIONES

`abrirEditor(id)` (~3122)
- Abre editor para nueva canción o editar existente
- Llamada desde: **Botón** "+ Nueva canción"; **menú ⋮** Editar

`cerrarEditor()` (~3140)
- Cierra editor sin guardar
- Llamada desde: **Botón** Cancelar en **Editor**

`refrescarPrevia()` (~3147)
- Actualiza vista previa de la canción mientras se edita
- Llamada desde: **Botón** Preview; cambio en campos

`actualizarBotonesTransporteEditor()` (~3155)
- Habilita/deshabilita botones ♭/♯ según si hay tono
- Llamada desde: `refrescarPrevia()`

`guardarEditor()` (~3187)
- Guarda cambios de la canción
- Llamada desde: **Botón** Guardar en **Editor**

### 6. EVENTOS (reuniones)

`abrirNuevaReunion()` (~1424)
- Abre diálogo para crear evento nuevo
- Llamada desde: **Botón** "+ Nuevo evento" en **Canciones**

`abrirEditarReunion(r)` (~1409)
- Abre diálogo para editar evento existente
- Llamada desde: Menú ⋮ de evento en **Guardadas**

`abrirCopiarReunion(r)` (~1432)
- Abre diálogo para copiar evento como base
- Llamada desde: Menú ⋮ de evento en **Guardadas**

`llenarCamposReunion(nombre, ms)` (~1440)
- Llena campos de nombre/fecha en diálogo de evento
- Llamada desde: `abrirNuevaReunion()`; abrirEditarReunion()

`cerrarEditarReunion()` (~1448)
- Cierra diálogo sin guardar cambios
- Llamada desde: **Botón** Cancelar en diálogo evento

`generarIdReunion()` (~1300)
- Genera ID único para nuevo evento
- Llamada desde: `crearReunion()`

`salirDelEvento()` (~1374)
- Marca fin del evento actual (sin borrar)
- Llamada desde: Menú ⋮ evento

`renderEncabezadoEvento(cont)` (~1859)
- Dibuja encabezado de evento (nombre + fecha + menú)
- Llamada desde: `renderReunion()`

### 7. AGREGAR CANCIONES A EVENTO

`abrirAgregar()` (~2095)
- Abre panel flotante para agregar canciones
- Llamada desde: **Botón** "+ Agregar" en **Evento**

`abrirAgregarDesdeCancion(posicionActual)` (~2103)
- Abre diálogo: ¿Agregar canción o nota?
- Llamada desde: **Botón** "+ Agregar" en pie de lector

`mostrarDialogoTipo(posicionActual)` (~2108)
- Diálogo: Canción o Nota
- Llamada desde: `abrirAgregarDesdeCancion()`

`mostrarDialogoUbicacion(posicionActual, tipo)` (~2280)
- Diálogo: dónde insertar (antes/después de qué paso)
- Llamada desde: `mostrarDialogoTipo()` tras elegir tipo

`cerrarAgregar()` (~2334)
- Cierra panel de agregar
- Llamada desde: Al agregar algo o hacer clic fuera

`alternarEnLista(id)` (~2572)
- Suma/quita canción del evento actual
- Llamada desde: **Botón** +/✓ en lista; panel Agregar

### 8. NOTAS/ANOTACIONES

`generarIdNota()` (~741)
- Genera ID único para nota
- Llamada desde: `agregarNota()`

`esNota(id)` (~740)
- Detecta si ID es una nota (prefijo "nota:")
- Llamada desde: `soloCanciones()`; renderReunion(); paso()

`mostrarDialogoNota(notaInicial, onGuardar)` (~2149)
- Abre diálogo para crear/editar nota
- Llamada desde: **Botón** "+ Nota"; **menú ⋮** Editar nota

`agregarNota(nota)` (~2250)
- Guarda nueva nota en evento
- Llamada desde: Diálogo crear/editar nota

`quitarNota(idNota)` (~2061)
- Elimina nota del evento
- Llamada desde: Menú ⋮ de nota "Eliminar anotación"

`mostrarMenuNota(e, idNota, indice)` (~2050)
- Menú ⋮ de una nota (editar, eliminar)
- Llamada desde: Tocar ⋮ en fila de nota

`soloCanciones(ids)` (~742)
- Filtra array para contar solo canciones (excluye notas)
- Llamada desde: `renderReunion()` para mostrador

### 9. DIRECTOR / TRANSMISIÓN EN VIVO

`alternarDirector()` (~3544)
- Prende/apaga chip "D" (director)
- Llamada desde: **Chip D** en **Lector**

`transmitirEstado()` (~2710)
- Transmite la canción actual en vivo
- Llamada desde: **Chip O** (online) en **Lector**

`mostrarVistaOnline(d)` (~1207)
- Abre lector en modo transmisión en vivo
- Llamada desde: Listener de directorEnVivo (cambio en Firestore)

`cerrarVistaOnline()` (~1171)
- Cierra vista de transmisión (sin tocar el lector normal)
- Llamada desde: Listener de Firestore cuando termina transmisión

`transmitirDesdeElPrincipio()` (~1189)
- Transmite el primer paso del evento
- Llamada desde: `mostrarVistaOnline()`

`retransmitirSiYaEstaEnVivo()` (~1293)
- Si la canción abierta ya es la transmitida, actualiza transporte
- Llamada desde: `transportar()` dentro de reunión como director

`fondoOnline()` (~2487)
- Dibuja fondo/aviso en pestaña Transmisión (sin director)
- Llamada desde: `renderOnline()`

### 10. MENÚS CONTEXTUALES

`mostrarMenu(anchorEl, opciones)` (~2013)
- Menú flotante genérico (posición, opciones)
- Llamada desde: Todos los menús ⋮

`mostrarMenuCancion(e, idCancion, indice)` (~2041)
- Menú ⋮ de canción en evento (quitar, editar, copiar link)
- Llamada desde: Tocar ⋮ en fila de canción

`mostrarMenuEvento(e)` (~2072)
- Menú ⋮ de evento (editar, copiar, borrar)
- Llamada desde: Tocar ⋮ en encabezado Evento

`mostrarMenuCancionCatalogo(e, idCancion)` (~2082)
- Menú ⋮ de canción en Canciones (editar, borrar, compartir)
- Llamada desde: Tocar ⋮ en fila de Canciones

`mostrarMenuReunion(r, btnMenu, activa)` (~2448)
- Menú ⋮ de reunión en Guardadas
- Llamada desde: Tocar ⋮ en fila de reunión

### 11. ARRASTRAR Y REORDENAR

`iniciarArrastre(e, i, filaEl)` (~2623)
- Inicia drag&drop de una fila
- Llamada desde: mousedown en fila cuando est.reordenando = true

`moverArrastre(e)` (~2632)
- Actualiza posición visual mientras se arrastra
- Llamada desde: mousemove mientras hay arrastre

`soltarArrastre()` (~2676)
- Termina arrastre y guarda orden nuevo
- Llamada desde: mouseup

`actualizarNumerosOrden()` (~2628)
- Actualiza números de paso después de reordenar
- Llamada desde: `soltarArrastre()`

### 12. COMPARTIR / EXPORTAR

`compartirPDF(cancion)` (~3334)
- Descarga canción como PDF
- Llamada desde: **Botón** 📄 en pie de lector

`compartirLink(cancion)` (~2310)
- Copia link a canción en clipboard
- Llamada desde: **Botón** 📋 en pie de lector

`compartirLinkEvento(evento)` (~2330)
- Copia link a evento en clipboard
- Llamada desde: **Botón** 🔗 en pie de lector (modo evento)

`mostrarMenuCompartir(e, idCancion)` (~3342)
- Menú de opciones de compartir
- Llamada desde: **Botón** de compartir

`abrirExportar()` (~3257)
- Pantalla de exportación (obsoleta, no visible)
- Llamada desde: No usada en interfaz

### 13. FIRESTORE / SINCRONIZACIÓN

`escuchar()` (~1046)
- Inicia listeners de Firestore (canciones, eventos, director)
- Llamada desde: `arrancar()` al iniciar app

`escucharReunionActiva(id)` (~1104)
- Listener de cambios en reunión activa
- Llamada desde: `escuchar()` o cuando cambia reunión activa

`manejarCambioEnVivo()` (~1707)
- Procesa cambios en directorio activo
- Llamada desde: Listener de directorEnVivo

`iniciarLatido(eventoId)` (~1655)
- Envía heartbeat periódico (marca que dispositivo está activo)
- Llamada desde: `escucharReunionActiva()`

`detenerLatido()` (~1679)
- Detiene heartbeat
- Llamada desde: `salirDelEvento()`; cerrarVistaOnline()

`hayDirectorActivo(lista)` (~1699)
- Verifica si hay al menos un director (el contador > 0)
- Llamada desde: `renderOnline()`

`recalcular()` (~710)
- Recalcula catálogo fusionando base + cambios de Firestore
- Llamada desde: Listener de Firestore

`contarCambios()` (~723)
- Cuenta canciones nuevas/editadas/borradas localmente
- Llamada desde: Mostrador de cambios

`marcarSync(clase, texto)` (~1729)
- Muestra indicador de sincronización (ej "✓ guardado")
- Llamada desde: Tras guardar en Firestore

### 14. ALMACENAMIENTO LOCAL

`leerAjustes()` (~1559)
- Lee preferencias (tamaño de fuente, orden, etc) de localStorage
- Llamada desde: `arrancar()`

`guardarAjustes()` (~1566)
- Guarda preferencias
- Llamada desde: Tras cambiar ajustes (tamaño fuente, orden)

`leerRol()` (~1575)
- Lee si dispositivo es director de localStorage
- Llamada desde: `arrancar()`

`guardarRol(esDirector)` (~1584)
- Guarda rol de dispositivo
- Llamada desde: `alternarDirector()`

`leerEventoLocal()` (~1603)
- Lee ID del evento activo local (fallback si Firestore no carga)
- Llamada desde: `arrancar()`

`guardarEventoLocal(id)` (~1609)
- Guarda ID del evento activo local
- Llamada desde: `usarReunion()`; salirDelEvento()

`obtenerDispositivoId()` (~1591)
- Genera/lee ID único del dispositivo
- Llamada desde: `leerRol()`; heartbeat

### 15. UTILIDADES

`flotar(msg)` (~1735)
- Muestra notificación flotante (toast)
- Llamada desde: Tras acciones (guardar, error, etc)

`fechaHoraTexto(ms)` (~2532)
- Convierte timestamp a texto legible (ej "hoy a las 19:30")
- Llamada desde: `renderReunion()`; renderGuardadas()

`metaDe(s, semis)` (~2544)
- Texto meta de canción (tono, BPM, si hay cambios)
- Llamada desde: `renderCatalogo()`; renderReunion(); renderAgregar()

`escapar(t)` (~2557)
- Escapa HTML especial (previene XSS)
- Llamada desde: Antes de poner texto en HTML

`nuevoId(nombre, tono)` (~729)
- Genera ID de canción (nombre-tono normalizado)
- Llamada desde: `guardarCancion()`

`esCifrado(tok)` (~896)
- Detecta si token es cifrado latino (DO RE MI) vs anglosajón
- Llamada desde: `renderBloques()`

`esLineaDeAcordes(t)` (~901)
- Detecta si línea es de acordes
- Llamada desde: `textoABloques()`

### 16. PANTALLA COMPLETA / INTERFAZ

`pedirPantallaCompletaSiCelular()` (~3397)
- Pide permiso de pantalla completa (DESACTIVADO, solo manual)
- Llamada desde: (removido de abrir() y mostrarVistaOnline())

`alternarPantallaCompleta()` (~3403)
- Botón ⛶ en lector: activa/desactiva pantalla completa
- Llamada desde: **Chip expandir** (⛶) en pie del lector

`esCelular()` (~3515)
- Detecta si es dispositivo móvil
- Llamada desde: `pedirPantallaCompletaSiCelular()`; lógica responsiva

### 17. LINKS COMPARTIDOS

`abrirDesdeLink()` (~3530)
- Abre canción cuando se accede desde link compartido
- Llamada desde: Si URL contiene parámetro cancion=...

`abrirEventoDesdeLink()` (~3543)
- Abre evento cuando se accede desde link compartido
- Llamada desde: Si URL contiene parámetro evento=...

### 18. ROLES / CONFIGURACIÓN

`mostrarPantallaRol()` (~3490)
- Abre diálogo para elegir rol (director o músico)
- Llamada desde: **Botón** de rol; arranque sin rol definido

`fijarRol(esDirector)` (~3496)
- Guarda rol elegido
- Llamada desde: Diálogo de rol

### 19. COMPARADORES (ordenamiento)

`compararNombre(a, b)` (~1779)
- Comparador para ordenar alfabéticamente
- Llamada desde: `sort()` en renderCatalogo()

`compararTono(a, b)` (~1782)
- Comparador para ordenar por tono
- Llamada desde: `sort()` en renderCatalogo()

`compararBpm(a, b)` (~1786)
- Comparador para ordenar por BPM
- Llamada desde: `sort()` en renderCatalogo()

### 20. OTROS

`quitar(id)` (~2600)
- Quita canción/nota del evento
- Llamada desde: Menú ⋮ Quitar; alternarEnLista()

`vaciar()` (~2686)
- Vacía el evento actual (borra todos los pasos)
- Llamada desde: Menú ⋮ Vaciar evento

`semisGuardado(id)` (~2701)
- Lee transporte guardado de una canción en evento
- Llamada desde: `abrir()`; mostrarVistaOnline()

---

## PESTAÑA: Canciones (lista de todas las canciones)

**Función que la dibuja:** `renderCatalogo()` (~1795)

**Elementos:**
- **Encabezado:** "Canciones (96)" — muestra cantidad total
- **Buscador:** campo de texto, filtra en tiempo real (`filtrarCanciones()` ~1815)
- **Botones de pie:**
  - `+ Nueva canción` → `abrirEditor("nueva")` (~1810) → abre **Pantalla: Editor de canción**
  - `+ Nuevo evento` → `abrirNuevaReunion()` (~1809) → abre **Pantalla: Crear/editar evento**
- **Lista de canciones:** cada fila muestra:
  - Nombre (mayúsculas)
  - Tono + BPM (gris)
  - Al tocar: abre **Pantalla: Lector** (lectura de canciones)
  - Menú ⋮: editar, borrar, copiar link, descargar PDF

**Restricciones:**
- Solo directores pueden crear canciones nuevas (`est.esDirector`)

---

### PANTALLA: Editor de canción

**Función que la abre:** `abrirEditor(idOpcional)` (~3120)
**Función que guarda:** `guardarEditor()` (~3187)

**Campos:**
- **Nombre** (text input, requerido)
  - Validación: no puede estar vacío
- **Tono** (text input, opcional)
  - Validación: debe ser acorde válido (ej: "C", "D#", "Em7") o vacío
  - Regex: `RE_TONO_VALIDO` (~550)
- **BPM** (text input, opcional)
  - Validación: debe ser número o vacío
- **Cuerpo** (textarea, requerido)
  - Formato: línea por línea, se convierte con `textoABloques()` (~3560)
  - Tipos de línea:
    - `:Nombre` → rótulo (gris)
    - Acordes (ej `D  Bm  G`) → línea de acordes (azul)
    - Letra normal → línea de letra (blanco)
  - Validación: debe tener al menos 1 línea

**Validaciones al guardar (línea ~3194):**
1. Nombre no vacío
2. Tono válido si se pone
3. Debe haber contenido (bloques)

**Botones:**
- Guardar → `guardarEditor()` (~3187)
  - Guarda en `est.cambios` (local)
  - Llama a `guardarCancion(cancion, esNueva)` (~1521) que escribe en Firestore
  - Muestra "Canción agregada" o "Cambios guardados"
- Cancelar → `cerrarEditor()` (~3182)
- Preview → `refrescarPrevia()` (~3160) muestra cómo se verá

**Restricciones:**
- `if (!est.esDirector)` → no permite editar, muestra "Solo directores pueden editar canciones" (~3188)
- Solo director puede guardar

---

### PANTALLA: Lector (visualización de una canción)

**Función que la dibuja:** `renderLector()` (~2030)
**Función que la abre:** `abrir(id, enReunion)` (~3250)

**Elementos principales:**
- **Encabezado:** Nombre - Tono - BPM (tachado si falta tono)
- **Riel de navegación:** número de paso / total (línea ~2100)
  - Al tocar: muestra número actual en evento
- **Cuerpo:** contenido de la canción (monoespaciado)
  - Acordes en azul
  - Rótulos en gris cursiva
  - Letra en blanco
- **Pie (si está en evento):**
  - Botón ◀ Anterior (si existe paso anterior)
  - Botón Siguiente ▶ (si existe paso siguiente)
  - Número de orden en evento (ej "1/5")
  - Si es director: botones ♭/♯ para transportar

**Pie (compartir, siempre visible):**
- 📋 Copiar link → `compartirLink()` (~2310)
- 📄 Descargar PDF → `compartirPDF()` (~2290)
- 🔗 Evento → `compartirLinkEvento()` (~2330) (solo si hay evento activo)

**Chips (si está en evento):**
- **D** (director) → `alternarDirector()` (~3544) prende/apaga transmisión
- **O** (online, solo si es director) → `transmitirEstado()` (~2710) transmite esta canción en vivo

**Transporte (si en evento y es director):**
- Botones ♭ / ♯ → `transportar(delta)` (~2750)
- Muestra semitono actual (ej "+2")
- Se guarda en `est.lista.semis[id]` (solo para esta reunión)

**Bloqueado (si en evento pero NO es director):**
- No se puede transportar
- No se puede editar
- Se puede navegar (anterior/siguiente)
- Se puede leer

---

### PESTAÑA: Evento (lista del evento activo)

**Función que la dibuja:** `renderReunion()` (~1850)

**Elementos:**
- **Encabezado:** Nombre del evento, fecha (editable con menú)
- **Contador:** "N canciones" (solo cuenta canciones, no notas)
- **Lista:** mezcla de canciones (con ✓ si están en la lista) y notas intercaladas
  - Al tocar canción: abre **Pantalla: Lector** en modo evento
  - Al tocar nota: abre **Pantalla: Lector** (nota)
  - Menú ⋮ por canción: quitar, editar, copiar link
  - Menú ⋮ por nota: editar, eliminar

**Botones de pie:**
- `+ Agregar` → abre **Pestaña: Canciones** (misma lógica que tocar en lista)
- `+ Nota` → `mostrarDialogoNota()` (~1917) → abre **Pantalla: Crear/editar nota**
- `Reordenar` → `est.reordenando = true` (~2628) → activa arrastrar

**Chips encabezado:**
- **D** (si director) → muestra que transmite
- Menú ⋮ → editar evento, copiar, usar otra reunión, borrar

**Restricciones:**
- Solo directores pueden crear eventos, agregar canciones, crear notas
- Si no hay evento activo, el primer `+` (agregar canción) crea uno automáticamente

---

### PANTALLA: Crear/editar evento (`abrirNuevaReunion()`, `abrirEditarReunion()`)

**Función que la dibuja/abre:** 
- Nueva: `abrirNuevaReunion()` (~1424)
- Editar existente: `abrirEditarReunion(r)` (~1409)
**Función que guarda:** `guardarEditarReunion()` (~1454)

**Campos:**
- **Nombre** (text input, requerido)
  - Validación: no puede estar vacío (~1456)
- **Fecha** (date input, en formato aaaa-mm-dd)
  - Valor por defecto: hoy
  - Opcional, pero si se pone se procesa
- **Hora** (time input, en formato hh:mm)
  - Valor por defecto: 00:00
  - Se combina con fecha para calcular timestamp

**Botones:**
- Guardar → `guardarEditarReunion()` (~1454)
  - Si es nueva: crea evento vacío, llama a `crearReunion()`
  - Si es existente: edita nombre/fecha con `guardarDatosReunion()`
  - Cierra diálogo, navega a pestaña Evento
- Cancelar → `cerrarEditarReunion()` (~1448)

**Restricciones:**
- Solo directores pueden crear/editar eventos (~1486, 1467)
- Nombre obligatorio (~1456)

---

### PANTALLA: Crear/editar nota (`mostrarDialogoNota()`)

**Función que la dibuja/abre:** `mostrarDialogoNota(notaInicial, onGuardar)` (~2159)

**Campos:**
- **Nombre** (text input, requerido)
  - Ej: "Pausa", "Lectura", "Advertencia"
- **Contenido** (textarea, opcional)
  - Multilinea, respeta saltos de línea
  - Ej: "Esperar 5 segundos", "Leer Juan 3:16"

**Botones:**
- Guardar → guarda en `est.lista.notas[idNota]` y en Firestore
- Cancelar → cierra sin guardar

**Restricciones:**
- Solo directores pueden crear/editar notas
- Nombre requerido

---

### PESTAÑA: Transmisión (si hay director transmitiendo)

**Función que la dibuja:** `renderOnline()` (~2200)

**Elementos:**
- **Encabezado:** "Transmisión en vivo" o "Sin transmisión"
- **Contenido:** si hay director:
  - Nombre de la canción/nota que está transmitiendo
  - Lector en modo solo lectura (no se puede tocar nada)
  - Riel de navegación (muestra paso actual)

**Botones:**
- Si hay transmisión activa: muestra la canción/nota en el lector
- Si cierra transmisión: se cierra el lector automáticamente

**Restricciones:**
- No se puede editar nada (modo solo lectura)
- Si transmisión para: lector se cierra solo

---

### ESTADO GLOBAL (est object) — variables importantes

| Variable | Tipo | Qué controla | Dónde se modifica |
|---|---|---|---|
| `est.pestana` | string | Cuál pestaña está activa ("canciones", "reunion", "online") | Al tocar botones de pestaña (~3393) |
| `est.lista` | object | Evento activo: `{id, nombre, ids, semis, notas, ...}` | `abrirNuevaReunion()`, `guardarEditarReunion()` |
| `est.esDirector` | boolean | Si puede crear/editar eventos, canciones, transmitir | `alternarDirector()` (~3544), listener (~1579) |
| `est.enReunion` | boolean | Si está dentro de un evento (bloquea ediciones) | `abrir(id, true/false)` (~3250) |
| `est.editando` | string | ID de canción que se está editando, o "nueva" | `abrirEditor(id)` (~3120) |
| `est.semis` | number | Transporte actual de la canción abierta (+/- semitonos) | `transportar(delta)` (~2750) |
| `est.cambios` | object | Canciones nuevas/editadas localmente: `{nuevas:[], editados:{}, borradas:[]}` | Listener de Firestore (~1077), `guardarEditor()` |
| `est.reordenando` | boolean | Si modo arrastrar está activo | Al tocar botón "Reordenar" |
| `est.abierta` | string | ID de canción actualmente en el lector | `abrir(id, enReunion)` (~3250) |

---

### FLUJOS COMPLETOS

**Flujo 1: Agregar canción nueva**
1. Toca `+ Nueva canción` en Canciones
2. Se abre **Pantalla: Editor**
3. Completa nombre, tono, BPM, contenido
4. Toca Guardar
5. Se guarda en `est.cambios.nuevas` (local)
6. Se escribe en Firestore con `guardarCancion()` (~1521)
7. Listener (~1077) la detecta y la suma a `est.cambios.nuevas`
8. Aparece en lista de Canciones inmediatamente

**Flujo 2: Crear evento y agregar canciones**
1. Toca `+ Nuevo evento` en Canciones
2. Se abre **Pantalla: Crear evento** con fecha de hoy pre-llenada
3. Pone nombre, opcionalmente fecha/hora
4. Toca Guardar → se crea evento, navega a pestaña Evento
5. Toca canciones en la lista de Canciones → se suman al evento
6. Para cada canción: `alternarEnLista(id)` (~2572) la agrega a `est.lista.ids`
7. Toca Anterior/Siguiente para navegar
8. Toca ♭/♯ para transportar (solo si es director)

**Flujo 3: Transmitir en vivo**
1. Estar en pestaña Evento
2. Tocar chip **D** → pasa a ser director
3. Abrir la canción que quieres transmitir (en el lector)
4. Tocar chip **O** (online) → transmite esta canción
5. Otros ven en pestaña Transmisión: la canción en tiempo real
6. Al navegar con ◀/▶ la transmisión se actualiza automáticamente (si ya era la canción activa)
7. Tocar **O** de nuevo para dejar de transmitir
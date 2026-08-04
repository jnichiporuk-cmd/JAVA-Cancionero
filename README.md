# Cancionero — puesta en marcha

App web de una sola página para usar en el celular durante la reunión. El
catálogo de canciones va dentro del archivo HTML; la lista de la reunión y las
ediciones de acordes se sincronizan por Firestore.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `cancionero_2026-07_v8.html` | La app. Es lo único que se sube al hosting |
| `plantilla.html` | La app **sin** el catálogo. Se edita esto, no el HTML final |
| `catalogo.json` | Las 96 canciones sacadas del `.docx` |
| `extraer.py` | Lee el `.docx` y genera `catalogo.json` |
| `build.py` | Junta plantilla + catálogo y genera el HTML final |
| `probar_app.js` | Ejecuta la app en Node y recorre los caminos de uso |
| `pendientes.json` | Las 37 canciones que quedaron afuera, con el motivo |

Hace falta Python 3 con `lxml` (`pip install lxml`) y Node.js.

---

## 1. Crear la base de datos en Firebase

1. Entrá a `console.firebase.google.com` y creá un proyecto. No necesitás
   activar Google Analytics.
2. En el menú izquierdo: **Build → Firestore Database → Create database**.
   Elegí la región más cercana. Cuando pregunte por el modo, elegí
   **production mode** (las reglas se ponen en el paso 3; el modo de prueba
   caduca a los 30 días y la app dejaría de guardar sin avisar).
3. Volvé al inicio del proyecto y tocá el ícono `</>` (**Add app → Web**).
   Ponele un nombre. Firebase te va a mostrar un bloque así:

   ```js
   const firebaseConfig = {
     apiKey: "AIza...",
     authDomain: "tu-proyecto.firebaseapp.com",
     projectId: "tu-proyecto",
     storageBucket: "tu-proyecto.firebasestorage.app",
     messagingSenderId: "123456789",
     appId: "1:123:web:abc"
   };
   ```

4. Copiá esos seis valores dentro de `plantilla.html`, en el bloque
   `FIREBASE_CONFIG` que está al principio del `<script>`. Después corré el
   armado (paso 4) para regenerar el HTML.

Mientras `projectId` quede vacío, la app funciona igual como cancionero pero
el indicador de arriba dice **sin configurar** y nada se comparte.

---

## 2. Reglas de seguridad

En **Firestore Database → Rules**, reemplazá todo por esto y tocá
**Publish**:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // El puntero a cuál reunión está activa, y el orden manual de Guardadas
    match /cancionero/activa {
      allow read: if true;
      allow write: if request.resource.data.keys().hasOnly(['reunionActivaId','ordenReuniones'])
                   && (!('reunionActivaId' in request.resource.data)
                       || request.resource.data.reunionActivaId is string)
                   && (!('ordenReuniones' in request.resource.data)
                       || request.resource.data.ordenReuniones is list);
    }

    // Cada reunión guardada (la de hoy y las anteriores): un documento por reunión
    match /reuniones/{id} {
      allow read: if true;
      allow write: if request.resource.data.keys().hasOnly(
                        ['nombre','ids','semis','notas','porQuien','creada','actualizada','fechaReunion','enVivo','directoresLatido'])
                   && request.resource.data.ids is list
                   && request.resource.data.ids.size() < 100
                   && (!('semis' in request.resource.data)
                       || request.resource.data.semis is map)
                   && (!('notas' in request.resource.data)
                       || request.resource.data.notas is map)
                   && (!('enVivo' in request.resource.data)
                       || request.resource.data.enVivo is map
                       || request.resource.data.enVivo == null)
                   && (!('directoresLatido' in request.resource.data)
                       || request.resource.data.directoresLatido is map)
                   && (!('fechaReunion' in request.resource.data)
                       || request.resource.data.fechaReunion is number)
                   && (!('nombre' in request.resource.data)
                       || request.resource.data.nombre.size() < 120);
      allow delete: if true;   // borrar un evento del historial (el activo, la app no lo permite)
    }

    // Una canción por documento
    match /canciones/{id} {
      allow read: if true;
      allow write: if request.resource.data.keys().hasOnly(
                        ['nombre','tono','bpm','bloques','nueva','borrada','cuando'])
                   && (!('nombre' in request.resource.data)
                       || request.resource.data.nombre.size() < 120);
      allow delete: if false;   // no se borran documentos, se marcan
    }

    // Nada más queda accesible
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

**Qué protegen y qué no.** Estas reglas evitan que alguien escriba basura o
datos con la forma equivocada, y no permiten borrar documentos. Lo que **no**
pueden evitar es que alguien con el link edite el cancionero: es una app sin
login, así que cualquiera que abra la página puede escribir. Para un
cancionero de iglesia el riesgo es bajo, pero conviene no publicar el link
fuera del grupo.

Si más adelante querés que solo algunos editen, el camino es agregar Firebase
Authentication con cuenta de Google y cambiar `allow write` por
`if request.auth != null && request.auth.token.email in ['mail1@...', 'mail2@...']`.

---

## 3. Publicar en GitHub Pages

1. Creá un repositorio en GitHub. Puede ser público; la clave de Firebase que
   va en el código no es un secreto, lo que protege la base son las reglas del
   paso 2.
2. Subí el HTML con el nombre `index.html` (así la dirección queda limpia).
   Conviene subir también `plantilla.html`, `catalogo.json`, `extraer.py`,
   `build.py` y el `.docx`: el repositorio te queda como respaldo del
   cancionero.
3. **Settings → Pages → Source: Deploy from a branch**, rama `main`, carpeta
   `/ (root)`, **Save**.
4. En un minuto tenés la dirección: `https://TU-USUARIO.github.io/TU-REPO/`

Ese link es el que le pasás al grupo. No caduca, no depende de Claude y no se
puede borrar por accidente como pasaba al despublicar un artifact.

### Que se abra a pantalla completa

En el celular, abrí el link en Chrome → menú **⋮** → **Agregar a pantalla de
inicio**. La app ya trae las etiquetas para arrancar sin la barra del
navegador. Adentro también está el botón `⛶`.

---

## 4. Actualizar el cancionero cuando agregues canciones al `.docx`

```bash
python3 extraer.py    # lee el .docx -> catalogo.json
python3 build.py      # catalogo + plantilla -> HTML, y corre las pruebas
```

`extraer.py` espera encontrar el `.docx` descomprimido en `desarmado/`. Para
descomprimirlo:

```bash
unzip -o Cancionero_2026-06.docx -d desarmado/
```

`build.py` numera cada versión y la deja visible en el encabezado de la app,
para que se pueda saber de un vistazo si un celular está abriendo un archivo
viejo cacheado. Antes de generar el archivo verifica que:

- no queden marcadores sin reemplazar;
- el JSON del catálogo se vuelva a parsear igual;
- ningún identificador buscado por el JavaScript falte en el HTML;
- las funciones estén en el bloque `<script>` y no dentro del CSS;
- `localStorage` no se use para datos que deben ser compartidos;
- la app se ejecute sin errores y los 14 caminos de uso funcionen.

Si algo de eso falla, **no genera el archivo**.

---

## 5. Cómo está organizado el código

El HTML final tiene tres partes: el CSS, el catálogo como JSON dentro de un
`<script type="application/json">`, y el JavaScript de la app.

El catálogo funciona en dos capas:

- **Capa base**: las 96 canciones que vienen del `.docx`, dentro del archivo.
  Nunca se modifica. Por eso la app abre instantánea y funciona sin internet.
- **Capa de cambios**: las ediciones, las canciones nuevas y las borradas,
  en Firestore. Se suma encima de la base al abrir.

En Firestore hay dos lugares:

```
cancionero/reunion    ->  { ids: [...], porQuien, cuando }
canciones/{id}        ->  { nombre, tono, bpm, bloques, nueva, borrada, cuando }
```

Una canción por documento a propósito: si dos personas editan canciones
distintas al mismo tiempo, escriben en documentos distintos y no hay conflicto
posible. Con todo en un documento único, el último en guardar pisaba el
trabajo del otro.

`onSnapshot` avisa en el momento en que algo cambia, así que no hay sondeo
periódico. El indicador de arriba a la derecha dice **al día** cuando lo que
ves viene del servidor y **sin conexión** cuando sale de la caché local.

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

`t` es el tipo de línea: `r` rótulo, `a` acordes, `l` letra, `v` línea en
blanco. Sale directo de los estilos de Word de la guía de formato (Subtítulo,
Estilo1, Normal). **Los espacios de las líneas `a` son contenido**: son los
que ponen el acorde arriba de la sílaba, y por eso todo el cuerpo se dibuja
con tipografía monoespaciada y `white-space: pre`.

### Transporte de acordes

Sólo toca los bloques `a`. Al reescribir la línea conserva las columnas: si
`G` pasa a `A#` y ocupa un carácter más, se come un espacio de al lado en vez
de correr todo y desalinear la letra.

---

## 6. Lo que quedó pendiente

`pendientes.json` tiene las 37 canciones que no entraron, con el motivo de
cada una:

| Motivo | Canciones |
|---|---|
| Nunca pasaron por el formateo: acordes y letra comparten estilo | 10 |
| Líneas de acordes con estilo de letra | 9 |
| Letra o anotaciones dentro de la línea de acordes | 15 |
| Título sin nada debajo en el `.docx` | 3 |

Además, dentro de las 96 que sí entraron hay unas 40 líneas que se ven en el
color equivocado: rótulos que quedaron como letra (`[Verso 1]`), acordes en
cifrado latino (`DO RE MI`) y acordes con barras de repetición
(`//Em - D - G - C //`). No pierden información, pero salen en blanco en vez
de gris o azul. Se pueden arreglar desde el editor de la app, o en el `.docx`
y reimportando.

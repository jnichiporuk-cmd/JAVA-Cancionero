# Guía del cancionero

Todo lo que hay que saber para mantener la app, escrito para leerlo dentro de
seis meses habiendo olvidado los detalles.

---

## Mapa de servicios/infraestructura

| Servicio | Rol | Qué corre ahí |
|---|---|---|
| GitHub | Repositorio de código | Git + histórico de cambios (plantilla.html, build.py, etc.) |
| GitHub Pages | Hosting del frontend | `index.html` compilado (la app web publicada) |
| Firebase (cancionero-peniel) | Base de datos en tiempo real | Firestore: reuniones, canciones, ediciones, transmisión en vivo |
| Local (HTML) | Catálogo base + offline | 96 canciones embebidas en JSON dentro de `index.html` |
| Browser (celular/computadora) | Cliente | JavaScript ejecutado: la app que abre en el navegador |

---

## Decisiones arquitectónicas y alternativas

### Arquitectura actual (2026-08)

| Componente | Actual | Por qué |
|---|---|---|
| **Frontend hosting** | GitHub Pages | Gratis, simple, integrado con repo |
| **Base de datos** | Firebase Firestore | Tiempo real, sin servidor, plan gratuito |
| **Repositorio** | GitHub | Control de versiones, hosting de código |
| **Backend REST** | Ninguno | No necesita — acceso directo desde cliente |
| **Auth** | Ninguna | Por diseño: cualquiera con el link puede usar |

### Alternativas si querés cambiar en el futuro

**Opción 1: Máxima portabilidad (SQL estándar)**
```
Frontend: Vercel o Netlify (deployment automático desde GitHub)
BD:      Supabase PostgreSQL (realtime listeners, SQL estándar)
Backend: No necesita
Ventaja: SQL estándar, menos vendor lock-in
Costo:   Parecido a actual
Esfuerzo: Medio (refactor de capa de datos)
```

**Opción 2: Mantener Firebase + mejor frontend**
```
Frontend: Vercel o Netlify (en lugar de GitHub Pages)
BD:      Firebase Firestore (igual)
Backend: No necesita
Ventaja: Cero cambios en el código, mejor DX
Costo:   Similar
Esfuerzo: Mínimo (solo cambiar deploy)
```

**Opción 3: Control completo (backend + DB)**
```
Frontend: Vercel
BD:      Supabase PostgreSQL + Supabase Auth
Backend: Render o Railway (REST API)
Ventaja: Control total, permisos granulares
Costo:   Más que actual
Esfuerzo: Alto (reescribir aplicación entera)
Nota:    Innecesario para el caso de uso actual
```

**Recomendación:** Si algún día querés cambiar, opción 1 (Supabase + Vercel) es la mejor balance entre portabilidad y esfuerzo.

---

## PWA — instalación en el celular sin barra de navegador (2026-08)

Cancionero es instalable como **PWA (Progressive Web App)**: desde Chrome en
Android, menú **⋮ → Instalar app**, queda como app real con ícono propio,
sin la barra de URL del navegador, con su propio ciclo de vida (botón atrás
minimiza en vez de cerrar, aparece en Ajustes → Apps con opción
Desinstalar).

**Archivos involucrados** (todos en la raíz del repo, servidos como
estáticos por GitHub Pages — `build.py` no los toca):

| Archivo | Rol |
|---|---|
| `manifest.json` | Metadatos de la PWA: nombre, `display: standalone`, íconos |
| `sw.js` | Service Worker: cachea recursos, permite degradar sin red |
| `icon-192.png`, `icon-512.png` | Íconos reales para el ícono de la app |

**Decisión importante — los íconos tienen que ser PNG reales, nunca SVG en
`data:` URI.** La primera versión de `manifest.json` tenía los íconos como
SVG embebido (`data:image/svg+xml,...`). Resultado: Android instalaba sólo
un **acceso directo** (bookmark), no una app real — sin "Desinstalar", sin
minimizar con el botón atrás, sin aparecer en Ajustes → Apps. Sin ningún
error visible.

Motivo: el servicio de Google que empaqueta el WebAPK (el paquete que
Android trata como app instalada de verdad) necesita **rasterizar un PNG**
para meterlo en el `.apk`. Con SVG en `data:` URI esa generación falla en
silencio y Chrome degrada a un acceso directo simple.

Como no había Pillow ni `canvas` de Node disponibles, los PNG se generaron
con un script de un solo uso usando sólo `struct` + `zlib` de la stdlib de
Python (sin dependencias) — un PNG válido es solo firma + chunks
IHDR/IDAT/IEND con los píxeles crudos comprimidos con zlib deflate.

**Cómo verificar que instala como WebAPK real y no como acceso directo:**
en el menú ⋮ de Chrome, el texto tiene que decir **"Instalar app"** (no
sólo "Agregar a pantalla de inicio"). Esa diferencia de wording es la señal
de que el sitio pasó los criterios de instalabilidad de Chrome.

**Trampa al volver a probar:** Chrome/Android cachean el resultado de
instalabilidad anterior. Después de cualquier cambio en `manifest.json` o
`sw.js`, para reprobar en un celular que ya lo tenía instalado hace falta:
desinstalar el acceso directo/app vieja, borrar caché + cookies del sitio
en Chrome, cerrar Chrome del todo (no sólo la pestaña), y recién ahí volver
a visitar el link e instalar.

---

## Datos del proyecto

Cuando algo falle, lo primero es tener esto a mano.

| | |
|---|---|
| App publicada | `https://jnichiporuk-cmd.github.io/JAVA-Cancionero/` |
| Repositorio | `https://github.com/jnichiporuk-cmd/JAVA-Cancionero` |
| Consola de Firebase | `https://console.firebase.google.com/project/cancionero-peniel` |
| Carpeta local | `C:\Users\nichi\OneDrive\Documentos\JAVA-Cancionero` |
| Proyecto Firebase | `cancionero-peniel`, plan Spark (gratis) |
| Región de la base | `southamerica-east1` (São Paulo) |

---

## Cómo funciona, en cuatro frases

1. Las canciones viven dentro de `index.html`. Por eso la app abre al instante
   y funciona sin internet.
2. La lista de la reunión y las ediciones de acordes viven en **Firestore**, la
   base de datos de Google. Por eso todos ven lo mismo al mismo tiempo.
3. `index.html` se genera; **no se edita a mano**. Se edita `plantilla.html` y
   se corre `python build.py`.
4. **GitHub** guarda el código y **GitHub Pages** lo publica como página web.

### Las tres piezas y para qué sirve cada una

| Pieza | Qué guarda | Si se rompe |
|---|---|---|
| Tu carpeta | El código con el que trabajás | Se recupera de GitHub |
| GitHub | El historial del código | Se sube de nuevo desde tu carpeta |
| Firestore | Listas y ediciones del grupo | **No hay copia automática.** Por eso existe el botón Exportar |

---

## Parte 1 — Lo que ya se hizo

No hay que repetirlo. Está acá por si alguna vez hay que rehacerlo desde cero,
o para entender de dónde salió cada cosa.

### 1. Preparar la máquina

- Python 3.12 desde `python.org`, tildando **"Add python.exe to PATH"**.
- Node.js LTS desde `nodejs.org`.
- Después de instalar Node hay que **cerrar VS Code por completo y volver a
  abrirlo**, si no el comando no aparece.

### 2. Crear la base de datos

En `console.firebase.google.com`:

1. Crear proyecto `cancionero-peniel`, sin Google Analytics.
2. **Bases de datos y almacenamiento → Firestore Database → Crear base de
   datos**.
3. Edición **Standard**, base `(default)`, región `southamerica-east1`.
   **La región no se puede cambiar después.**
4. Modo **producción**. El modo de prueba caduca a los 30 días y la app dejaría
   de guardar sin avisar.

### 3. Registrar la app web

Descripción general del proyecto → botón `</>` → sobrenombre `cancionero-web`,
sin tildar Firebase Hosting. Firebase devuelve un bloque `firebaseConfig` con
seis valores, que van pegados en `plantilla.html` dentro de `FIREBASE_CONFIG`.

Esa clave **no es un secreto**: está a la vista en el código de la página y así
tiene que ser. Lo que protege la base son las reglas.

### 4. Cargar las reglas de seguridad

Firestore Database → pestaña **Reglas** → pegar y **Publicar**. Las reglas
actuales están en `README.md`.

Detalle importante: la última regla es `match /{document=**} { allow read,
write: if false; }`, que **niega todo lo que no esté declarado antes**. Cada
colección nueva necesita su propio bloque.

### 5. Publicar en GitHub

Desde VS Code, panel **Control de código fuente** (`Ctrl+Shift+G`):
inicializar repositorio → mensaje de commit → **Confirmar** → **Publicar
Branch** → **público**.

La primera vez Git pide identificarse:

```powershell
git config --global user.name "Juan Andrés"
git config --global user.email "jnichiporuk@gmail.com"
```

### 6. Activar GitHub Pages

En el repositorio: **Settings → Pages → Source: Deploy from a branch**, rama
`main`, carpeta `/ (root)`, **Save**. Tarda entre uno y tres minutos.

El repositorio **tiene que ser público**: con las cuentas gratuitas, Pages no
funciona en repositorios privados.

---

## Parte 2 — Cómo hacer un cambio y publicarlo

Este es el ciclo que vas a repetir siempre. Cinco pasos.

### 1. Editar

Se edita **`plantilla.html`**, nunca `index.html`. Guardar con `Ctrl+S` y
verificar que desaparezca el punto ● de la pestaña.

### 2. Compilar

```powershell
python build.py
```

Tiene que terminar en `14/14 pasos sin error`. Si algo falla, **no genera el
archivo** y hay que corregir antes de seguir.

### 3. Probar local

```powershell
python -m http.server 8000
```

Y abrir `http://localhost:8000`. Para cortar el servidor: `Ctrl+C`.

**Nunca abrir `index.html` con doble clic.** Con `file://` el navegador bloquea
la carga del SDK de Firebase y la app dice "sin conexión" aunque esté todo bien.

Qué mirar arriba a la derecha:

| Dice | Significa |
|---|---|
| **al día**, verde | Conectado y funcionando |
| **sin conexión** | No cargó el SDK, o no hay internet |
| **error de permisos** | Las reglas de Firestore rechazan la operación |
| **sin configurar** | El `FIREBASE_CONFIG` está vacío |

### 4. Subir

Panel de **Control de código fuente**: escribir un mensaje que diga qué
cambiaste, **Confirmar**, y después **Sincronizar cambios** (o **Push**).

### 5. Verificar

Esperar un minuto y abrir la app publicada. Comprobar que el número de versión
del encabezado cambió: si sigue mostrando el anterior, el navegador tiene la
versión vieja guardada y hay que recargar con `Ctrl+F5`.

---

## Parte 3 — Agregar canciones al cancionero

Cuando actualices el `.docx`:

```powershell
Remove-Item -Recurse -Force desarmado
Expand-Archive Cancionero_2026-06.docx -DestinationPath desarmado
python extraer.py
python build.py
```

Después, commit y push como siempre.

`extraer.py` te va a decir cuántas canciones entraron y cuántas quedaron
pendientes por problemas de formato. Las pendientes quedan detalladas en
`pendientes.json` con el motivo de cada una.

---

## Parte 4 — Si algo falla

| Síntoma | Causa | Solución |
|---|---|---|
| `python3 no se reconoce` | En Windows el comando es otro | Usar `python` |
| `node: command not found` | Falta Node, o VS Code no lo ve todavía | Instalarlo y **reiniciar VS Code** |
| `ModuleNotFoundError: lxml` | Falta la librería | `pip install lxml` |
| La app dice **sin configurar** | La configuración se pegó en `index.html` en vez de `plantilla.html` | Ver comprobación abajo |
| La app dice **error de permisos** | Falta una regla para esa colección | Revisar las reglas en Firebase |
| La app dice **sin conexión** en local | Se abrió con doble clic | Usar `python -m http.server 8000` |
| Se ve una versión vieja | Caché del navegador | `Ctrl+F5` |
| Cambié algo y no aparece | Faltó guardar, compilar o subir | Repasar los 5 pasos del ciclo |
| La página publicada da 404 | Pages todavía está construyendo | Esperar, y mirar la pestaña **Actions** |
| Errores raros de "archivo en uso" | OneDrive sincronizando | Mover la carpeta fuera de OneDrive |
| La terminal muestra `canciÃ³n` | PowerShell y los acentos | No es un error, ignorarlo |

### Comprobar dónde quedó la configuración

```powershell
Select-String -Path plantilla.html,index.html -Pattern 'projectId:'
```

Los dos tienen que decir `projectId: "cancionero-peniel"`. Si solo lo tiene
`index.html`, se editó el archivo equivocado y el próximo build lo va a borrar:
hay que pasarlo a `plantilla.html`.

### Volver atrás un cambio que rompió algo

En VS Code, panel de **Control de código fuente**, ícono de historial. También
en GitHub, pestaña **Commits**: cada commit muestra exactamente qué cambió.

Por eso conviene hacer commits chicos y con mensajes claros.

---

## Parte 5 — Trabajar con Claude en VS Code

La carpeta tiene un `CLAUDE.md` que Claude Code lee solo al abrirla. Ahí está
la arquitectura, las decisiones ya tomadas con su motivo, las trampas conocidas
y lo que queda pendiente.

**Antes de pedir un cambio**, asegurate de que no haya trabajo sin subir: hacé
commit de lo que tengas. Así, si algo sale mal, tenés a dónde volver.

**Después de que Claude haga cambios**, el ciclo es el mismo de siempre:
compilar, probar en local, subir. No des por bueno un cambio que no probaste en
el navegador.

Si Claude propone algo que contradice lo que está en `CLAUDE.md`, preguntale
por qué antes de aceptarlo. Esas decisiones están ahí porque costaron trabajo.

---

## Lo que conviene no hacer

- ❌ Editar `index.html` a mano. Se pierde en el próximo build.
- ❌ Abrir el HTML con doble clic para probar Firebase.
- ❌ Hacer el repositorio privado. Pages deja de funcionar.
- ❌ Borrar la colección `canciones` en Firestore. Ahí están las ediciones del
  grupo y no hay copia automática.
- ❌ Repartir el link fuera del grupo. Cualquiera que lo tenga puede editar el
  cancionero: es una app sin contraseña.

## Lo que conviene hacer cada tanto

- ✅ Usar el botón **Exportar** de la app y guardar ese texto. Es la única copia
  de las ediciones que hizo el grupo.
- ✅ Hacer commit y push seguido, aunque el cambio sea chico.
- ✅ Probar la app en el celular antes del domingo, no el domingo.

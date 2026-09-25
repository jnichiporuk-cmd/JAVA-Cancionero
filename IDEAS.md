# Ideas y pendientes — Cancionero

Registro de ideas/mejoras para trabajar, con estado (abierta/resuelta) y fecha de carga.

---

## Abiertos

- **[2026-09-25] Reclasificar en `catalogo.json` las líneas de acordes con
  barras de repetición o guiones que quedaron como letra**
  — El detector ya las reconoce al escribir en el editor, pero las que ya
  están guardadas como letra siguen en blanco en vez de azul. Falta decidir
  si se reclasifican y cómo: revisadas una por una, no por regla. (prioridad: media)

- **[2026-08-04] Permitir reordenar desde mobile sin entrar en modo Reordenar**
  — Hoy hay que tocar un botón y entrar en un modo especial. Sería más rápido poder
  arrastrar directamente desde la lista del evento. (prioridad: media)

- **[2026-08-04] Exportar historial de ediciones (para auditoría)**
  — Quién cambió qué y cuándo. Útil si hay conflicto o hay que deshacer. Guardar en
  archivo o link. (prioridad: baja)

---

## Resueltos

- **[2026-09-25] Reconocer `//C#/A – D//` y `G-D` como líneas de acordes**
  — Barras de repetición y guiones pegados al acorde: el detector los pela
  antes de validar y el transporte los conserva, moviendo cada acorde por
  separado. Decisión en DEVELOPER.md ("Barras de repetición y guiones
  pegados al acorde").

- **[2026-09-25] Editor con formato en el lugar y a pantalla completa**
  — El cuerpo de la canción se ve con los colores del cancionero mientras se
  escribe (textarea transparente sobre una capa pintada), mide al menos una
  pantalla de alto y la vista previa pasó a ser plegable. Decisión y
  alternativas descartadas en DEVELOPER.md ("Editor de canciones: color en el
  lugar sin contenteditable").

- **[2026-07-31] Notas/anotaciones intercaladas en eventos**
  — Agregar texto libre entre canciones (pausas, lecturas, instrucciones).
  Resuelto en commits `1c096ce` y posteriores. Documentado en CLAUDE.md sección 8d.
  Requirió: estructura {nombre, contenido}, prefijo "nota:" en IDs, transmisión,
  riel integrado.

quiero probar si esto está funcionando
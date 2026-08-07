# Ideas y pendientes — Cancionero

Registro de ideas/mejoras para trabajar, con estado (abierta/resuelta) y fecha de carga.

---

## Abiertos

- **[2026-08-04] Permitir reordenar desde mobile sin entrar en modo Reordenar**
  — Hoy hay que tocar un botón y entrar en un modo especial. Sería más rápido poder
  arrastrar directamente desde la lista del evento. (prioridad: media)

- **[2026-08-04] Exportar historial de ediciones (para auditoría)**
  — Quién cambió qué y cuándo. Útil si hay conflicto o hay que deshacer. Guardar en
  archivo o link. (prioridad: baja)

---

## Resueltos

- **[2026-07-31] Notas/anotaciones intercaladas en eventos**
  — Agregar texto libre entre canciones (pausas, lecturas, instrucciones).
  Resuelto en commits `1c096ce` y posteriores. Documentado en CLAUDE.md sección 8d.
  Requirió: estructura {nombre, contenido}, prefijo "nota:" en IDs, transmisión,
  riel integrado.

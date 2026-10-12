# Hoja de ruta: hitos y plan de desarrollo agéntico

- Fecha: 12/10/2026. Autor: responsable técnico, por encargo del usuario ("define nuevos hitos y un plan de desarrollo agéntico para llevarlo al lienzo").
- **Qué sustituye.** Es la única hoja de ruta desde hoy. Reordena lo que quedaba de `docs/specs/002-plan-propuesto.md` (resto de la fase B, B2, C y D) y lo une con las specs 003 (entorno construido) y 004 (experiencia).
- **Qué reutiliza.** Los criterios de salida de 002 se citan aquí, no se copian. Cada tarea concreta vive en el `plan.md` de su spec.
- **Qué cambió desde 002:**
  - el usuario no está en Calp, así que fotos, medidas y planos salen de fuentes en línea (`CLAUDE.md`, 12/10/2026);
  - el objetivo es que el Ajuntament de Calp adopte el proyecto;
  - la interfaz es mínima, flotante y pensada para niños (004).

## 1. Dónde estamos (12/10/2026)

| Bloque | Estado |
|---|---|
| Fase A: terreno, ruta, túnel, corredor, registro de hechos | Hecha |
| B0: contrato de sistemas del mundo (ADR 0010) | Hecho |
| Entorno 003 | **E1** (firmes pintados y escaleras con colisión), **E2** (1.145 árboles y 6.438 matas medidos) y **E3** (edificios del centro) hechos. Pendientes: E1.2 (materiales; texturas ya descargadas), E4 (mobiliario del acceso), E5 (puerto) y E6 (Pobla) |
| Experiencia 004 | Propuesta, diseño de la interfaz (X0.1) e imagen del minimapa (X1.1) hechos. **X0** (fichas, cuaderno, "Más", "Ir a la cima") en programación |
| Datos | 21 de 25 descargas de la fase 5 hechas. Investigación en línea `004-*` y `005-*` hecha |
| Paseo publicado | :3000 en local, de la entrada del parque a la cima. No hay dirección pública |
| Integración continua | GitHub Actions no arranca por facturación de la cuenta: las comprobaciones se hacen en local |

## 2. Los hitos

Cada hito termina en algo que se puede **enseñar y probar**, con criterios observables. El orden sigue el valor para la persona que lo usa y lo que desbloquea a los demás.

### H0 — Cerrar lo abierto (en curso)

- **Objetivo:** que la base esté limpia antes de crecer.
- **Contenido:**
  - terminar X0;
  - regenerar a propósito las capturas de referencia de los puntos fijos (cambiaron por museo, escaleras y vegetación);
  - repetir la prueba de presupuesto que falló con la máquina cargada (calidad alta en el torniquete);
  - anotar en `CLAUDE.md` que Python con IPv6 roto tarda unos 60 s por conexión;
  - dejar escritas las cuatro descargas bloqueadas por TLS.
- **Sale cuando:**
  - la batería e2e completa está en verde en `main`;
  - `verify-generated` sale con 0;
  - :3000 coincide con `main`.

### H1 — Paseo con sentido: el tramo piloto, entregable

- **Objetivo:** del aparcamiento al km 0,421, alguien que nunca ha estado entiende dónde está, aprende algo con fuente y puede llegar a la cima con un botón.
- **Contenido:**
  - 004 X1: minimapa, altitud, mapa grande, viaje rápido y "¿Dónde estoy?";
  - 003 E1.2: firmes con `stone_tiles_02` y grava;
  - 003 E3+: pórtico de arcos, torretas y patio, con las medidas aproximadas de `004-recursos-acceso-centro.md`;
  - 003 E4: talanqueras de rollizos, torniquete, fuentes y pérgolas del aparcamiento;
  - 002 B9: fichas del Centre y del mirador del tramo;
  - 002 B10: tocar para caminar;
  - 002 B11: niveles de calidad automáticos;
  - 002 B4: sonido ambiente básico;
  - 002 B7: caminante animado, si llega el zip de Quaternius.
- **Sale cuando:**
  - se cumplen los criterios de salida de la fase B de 002 (cinco vecinos, comparación fotográfica, p95/p99 en los móviles de referencia, es/va/en revisados). La comparación fotográfica usa fotos en línea con fecha y hora conocidas, de la misma hora solar;
  - se cumplen los criterios de §8 de 004 para quien no puede subir y para el visitante;
  - la lista P0 de accesibilidad de `005-experiencia-referentes.md` pasa en este tramo.

### H2 — El Penyal vivo: luz, cielo, tiempo, mar y sonido

- **Objetivo:** que se sienta el lugar a cualquier hora.
- **Contenido:**
  - 004 X2 (absorbe 002 B1): sol y luna reales con SunCalc, control de hora y fecha, amanecer, atardecer, noche con estrellas BSC5, luna y Vía Láctea, y escenas de tiempo (visibilidad, nubes, viento, lluvia, mar);
  - 002 B2: sombras;
  - 002 B6: oleaje y espuma;
  - el modelo de luz del follaje: la cara de atrás de las acículas, pendiente de la corrección de vegetación;
  - las capas de sonido por hora y estación.
- **El tiempo real de hoy** necesita la dirección pública y la tarea programada de H5. Hasta entonces solo hay escenas.
- **Sale cuando:**
  - orto, ocaso y posición del sol coinciden con las tablas del USNO de `005-tiempo-cielo-memoria.md`;
  - las capturas a la hora de fotos fechadas se comparan con el protocolo de `002-verificacion.md` §4;
  - el móvil de referencia (A7) cumple el presupuesto de noche y de día.

### H3 — Hasta la cima, fiel y contado

- **Objetivo:** todo el recorrido con la calidad del piloto, y cada parada con su historia.
- **Contenido:**
  - 002 B2/C1–C3: túnel con las medidas disponibles o rotulado como aproximado, cuerdas y cadenas de las obras de 2016, plataforma, Carabiners, y cima con el pilar del IGN (1,20 m × Ø 0,30 m sobre base de 1,00 × 0,20 m);
  - 003 E5: puerto a baja resolución (Club Náutico con su torre redonda, pantalanes, aparcamiento y bloques con las plantas del Catastro);
  - 003 E6: Pobla d'Ifac (muralla, torres e iglesia trazadas sobre la ortofoto 2024, con el plano del MARQ como guía);
  - 004 X3: fichas en las paradas oficiales en es, va y en, guía de naturaleza por estaciones y "¿Qué se ve desde aquí?".
- **Sale cuando:**
  - se cumplen los criterios de salida de la fase B2 de 002;
  - cada parada tiene ficha con hechos `verified` o rotulados como `conflict` o `unverified`;
  - la consulta al parque está enviada, y sus respuestas, o su falta, quedan registradas.

### H4 — Para todos: modos y memoria

- **Objetivo:** que cada público tenga su recorrido.
- **Contenido:**
  - 004 X4: 1945, 1956–57, 1977 y 1989 frente a hoy, primero en el mapa y luego en el relieve;
  - 004 X5, que absorbe 002 C:
    - visita guiada y visita exprés de 5 minutos;
    - ruta de clase con 6–8 tareas y guía docente;
    - modo foto y postal con créditos;
    - kiosco para Tourist Info;
    - narración: texto primero, voz si hay grabaciones.
- **Sale cuando:**
  - se cumplen los criterios de salida de la fase C de 002 (docentes de Primaria y ESO la prueban);
  - el kiosco aguanta una jornada sin intervención en un equipo de escritorio;
  - toda postal lleva sus atribuciones.

### H5 — Entrega al Ajuntament

- **Objetivo:** que se pueda publicar, mantener y vender.
- **Contenido:**
  - 002 D: rendimiento de la ruta completa en los móviles de referencia, WCAG 2.2 AA con auditoría y teclado completo (EN 301 549 V4, que se espera vinculante hacia diciembre de 2026), guía en texto, PWA sin conexión, alojamiento, cabeceras de seguridad y revisión de WebGPU sin migrar;
  - además:
    - `weather.json` publicado por una tarea programada (y su licencia de Open-Meteo);
    - integración continua restablecida;
    - auditoría de licencias y créditos, con los ficheros ODbL publicados;
    - declaraciones de accesibilidad y de privacidad para el Ajuntament;
    - guía de mantenimiento;
    - pruebas finales: cinco vecinos, una clase y una persona con movilidad reducida;
    - dossier, vídeo de 1–2 minutos y demo;
    - propuesta de licencia y mantenimiento.
- **Sale cuando:** se cumplen los criterios de salida de la fase D de 002, la dirección pública funciona y el Ajuntament tiene todo lo necesario para decidir.

## 3. Plan de desarrollo agéntico

### 3.1 Quién hace qué

El reparto sigue la tabla de enrutado del estudio (modelo y esfuerzo fijados en cada agente).

| Papel | Agente | En este proyecto |
|---|---|---|
| Responsable técnico (hilo principal) | — | Decide, integra, verifica, publica la vista previa y habla con el usuario. Es el único que toca los contratos del ADR 0010 y los `plan.md` |
| Arquitectura | `architect` | ADRs nuevos: reloj del mundo y tiempo (H2), alojamiento y PWA (H5), cadena de contenido multilingüe (H3) |
| Diseño | `design-engineer` | Cada pieza visible antes de programarla, con prototipo sobre capturas reales y contraste medido |
| Interfaz | `frontend-engineer` | Carril L7: interfaz, fichas, mapa, modos |
| Pipeline y 3D | `implementer` | Pasos deterministas (`penyal …`) con manifiesto de procedencia: mobiliario, Pobla, puerto, imágenes históricas |
| Pruebas | `test-engineer` | e2e por función, accesibilidad automática (axe), medición de rendimiento |
| Revisión | `code-reviewer` | Cada integración, en un contexto distinto del que escribió el código |
| Fallos de causa oscura | `debugger` | Como con las piruletas beis de la vegetación |
| Investigación | `general-purpose`, `docs-researcher` | Fuentes en línea con licencia (`004-*`, `005-*`) y APIs de librerías |
| Infraestructura | `devops-engineer` | Alojamiento, integración continua, tarea de `weather.json`, cabeceras (H5) |
| Textos | `scribe` | Traspasos de sesión, notas de versión, borradores del dossier |
| Escalado | `principal-engineer` | Solo si Opus ha fallado con esfuerzo alto, con el motivo escrito |

### 3.2 Carriles: qué va en paralelo

- Dos agentes van en paralelo **solo si no comparten ficheros**.
- Los carriles siguen el ADR 0010: cada sistema del mundo es un carril y la interfaz es L7.
- Los contratos (`world/systems.ts`, `atmosphere.ts`, `core/quality.ts`, `core/budget.ts`, `content/poi.ts`, `content/notebook.ts`) solo los cambia el responsable técnico.

| Hito | Carril A (interfaz) | Carril B (entorno 3D) | Carril C (luz, mar y sonido) | Carril D (contenido e investigación) | Carril E (calidad) |
|---|---|---|---|---|---|
| H1 | X0 → X1 | E1.2 → E3+ → E4 | B4 sonido básico | Fichas del tramo y consulta al parque | Capturas de referencia, axe, prueba con vecinos |
| H2 | Control de hora y tiempo | Modelo de luz del follaje | X2 sol, luna, cielo, noche y escenas; B2 sombras; B6 mar | Calendario natural para el sonido | Comparación con tablas y fotos fechadas; A7 |
| H3 | "¿Qué se ve desde aquí?" | Túnel, cima, E5 y E6 | Ajuste de luz de las escenas altas | Fichas de todas las paradas en es, va y en | Prueba con vecinos del hito |
| H4 | Modos, foto y kiosco | Capa histórica sobre el relieve | Narración | Ruta de clase y guía docente | Pruebas con docentes |
| H5 | Guía en texto y PWA | — | — | Declaraciones y dossier | Auditoría WCAG, rendimiento, licencias, pruebas finales |

Como mucho, **4 agentes que programan y 3 que investigan** a la vez. Más agentes cuestan más que lo que adelantan, por los conflictos de integración y la carga de la máquina en las e2e.

### 3.3 El ciclo de una tarea

1. **Fila en el `plan.md` de su spec:** objetivo, ficheros, aceptación, comprobación, tamaño y responsable. Sin comprobación no está lista.
2. **Diseño**, si se ve: `design-engineer`, con prototipo sobre capturas y contraste medido.
3. **Implementación en su propio worktree, empezando por la prueba que falla:**
   - los datos se clonan (`cp -cR`), nunca se enlazan;
   - las herramientas se usan con ruta absoluta;
   - cada agente usa su puerto e2e (51xx);
   - commits con rutas explícitas.
4. **Revisión independiente** (`code-reviewer`). Los hallazgos se reparten por ficheros entre los agentes que ya trabajan en ellos.
5. **Integración por el responsable técnico, siempre en este orden:**
   1. `git diff --name-only main...rama`: nada bajo `tools/`, `data/raw/`, `data/manual/`, `app/public/assets/generated/` ni `build/`;
   2. merge;
   3. regenerar los artefactos afectados (`penyal …`);
   4. `verify-generated`;
   5. lint, typecheck y pruebas;
   6. e2e del área;
   7. compilación y prueba de humo en :3000, con capturas que se miran;
   8. push;
   9. quitar el worktree, desenlazando antes cualquier symlink.
6. **Casilla marcada en el `plan.md`**, con commits y cifras.

### 3.4 Puertas de calidad por nivel

| Nivel | Puerta |
|---|---|
| Tarea | Prueba que falla primero; lint, typecheck y pruebas; e2e de su área; capturas a 375, 768 y 1440 px si se ve |
| Integración | Lo anterior en `main`, más `verify-generated`, el e2e de presupuesto y la prueba de humo en :3000 |
| Hito | La batería e2e completa (unos 45 min, en serie y con la máquina libre), la medición en el móvil de referencia, axe sin errores críticos, la revisión del usuario ("¿se parece al Penyal?") y un traspaso en `docs/handoff/` |
| Entrega (H5) | Lo anterior con todo el recorrido, la auditoría manual con lector de pantalla y las pruebas con personas |

### 3.5 Dónde hacen falta personas

| Qué | Quién | Para |
|---|---|---|
| Aprobar descargas (nombre, origen, tamaño, licencia), en una lista por hito | Usuario | Todos |
| Facturación de GitHub Actions | Usuario | Integración continua (H0/H5) |
| Zip de Quaternius (itch.io) | Usuario | B7 (H1) |
| Dos móviles de referencia y la medición A7 | Usuario | H1, H2, H5 |
| Revisión del valenciano | Usuario o servicio lingüístico municipal | H1, H3 |
| Enviar la consulta al parque (`consulta-parque.md`) | Usuario | H1, H3 |
| Prueba con cinco vecinos. Ahora a distancia, con un enlace público | Usuario | H1, H3, H5 |
| Permisos de fotos antiguas (Arxiu Municipal, Fotoclub Ifach, ICGC) y de observadores de flora y fauna | Usuario o Ajuntament | H3, H4 |
| Docentes de Primaria y ESO | Ajuntament o centros | H4 |
| Alojamiento, dominio y condiciones de Open-Meteo | Usuario y Ajuntament | H2 (tiempo real), H5 |
| Voces de la narración | Usuario o Ajuntament | H4 |

### 3.6 Lo aprendido en esta etapa, que ya es regla

- **Las rutas ignoradas no se versionan nunca.** Un commit que versionó `tools/` borró `ktx` en cada checkout que lo integró (`CLAUDE.md`, gotcha). Antes de integrar se revisa la lista de ficheros.
- **Las e2e pesadas no van en paralelo.** Con la máquina cargada, una prueba de presupuesto se quedó en "Cargando el terreno…". Las baterías completas van en serie al cerrar un hito.
- **Los fallos visuales piden la causa raíz, no un parche.** Las piruletas beis eran brillo especular y un color convertido dos veces; quitar la tarjeta lo escondía.
- **La sombra suave no basta para leer sobre el cielo** (1,8:1). Todo texto flotante se mide.
- **Las investigaciones en línea son caras** (400–580 mil tokens cada una). Se acotan por hito y se reutilizan sus documentos.
- **Lo que puede perderse con el contexto va al `plan.md`** antes de un paso largo, y cada sesión termina con un traspaso.

## 4. Esfuerzo orientativo

Son estimaciones, no compromisos. Están en días de trabajo de agentes, como en 002, sin contar el tiempo de las personas.

| Hito | Esfuerzo | Depende sobre todo de |
|---|---|---|
| H0 | 1 día | — |
| H1 | 8–12 días | Móviles de referencia, revisión del valenciano, cinco vecinos |
| H2 | 7–10 días | Medición A7 |
| H3 | 9–13 días | Respuesta del parque, que puede no llegar |
| H4 | 7–10 días | Docentes, permisos de fotos |
| H5 | 6–10 días | Alojamiento y decisiones del Ajuntament |

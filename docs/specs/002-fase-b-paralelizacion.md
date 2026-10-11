# Fase B — Tramo piloto: plan de paralelización

- Estado: **propuesto**, 11/10/2026. Desarrolla la Fase B de `docs/specs/002-plan-propuesto.md`, ya aprobada.
- Ámbito: desde la explanada del Centre d'Informació hasta el kilómetro 0,421 de la ruta (350 m después del torniquete), a calidad de entrega.
- Objetivo de salida: el de la Fase B del plan 002:
  - cinco vecinos completan la sesión;
  - comparación fotográfica en 2–3 puntos;
  - en móvil de referencia, p95 ≤ 33,3 ms, p99 ≤ 50 ms y ≤ 200 llamadas de dibujo;
  - ficha e interfaz en es, va y en, con la revisión de valenciano.
- Condición de arranque: **la Fase A cerrada**, con controles en verde, `main.ts` estable tras A3, A4 y A6, y la trazabilidad de A5 hecha. Los carriles de investigación pueden empezar antes (ver "Arranque anticipado").

## Por qué hace falta una etapa B0

Hoy todo pasa por `app/src/main.ts` (412 líneas): carga, escena, bucle, interfaz. Si seis carriles lo editan a la vez, habrá conflictos continuos. Además, varios sistemas comparten estado:
- el sol lo usan el material, el mar, la vegetación y las sombras;
- el nivel de calidad lo usan todos;
- los escalones afectan a la colisión.

B0 fija esos contratos **antes** de abrir los carriles. A partir de ahí, cada carril añade ficheros propios y se registra, sin tocar `main.ts`.

## B0 — Contratos y andamiaje (secuencial, primero)

**Responsable:** `architect` (diseño y ADR 0010) e `implementer`. **Esfuerzo:** 1–1,5 días. **Bloquea a todos los carriles.**

1. **Registro de sistemas del mundo** (`app/src/world/systems.ts`, ADR 0010):
   - Interfaz: `WorldSystem { id; init(ctx): Promise<void>; update(frame); onQualityChange?(profile); dispose() }`.
   - `ctx` da acceso a escena, cámara, renderer, cargador glTF/KTX2 compartido, atmósfera, perfil de calidad, rutas de recursos, superficies de suelo y el registro de puntos de interés.
   - `main.ts` solo arranca y recorre la lista de sistemas.
   - Los sistemas actuales (terreno, mar, cielo, túnel, depuración del sendero) pasan a registrarse así, sin cambiar su comportamiento. Una prueba E2E de "antes y después" lo demuestra.
2. **Contrato de atmósfera** (`app/src/world/atmosphere.ts`):
   - Un único objeto `Atmosphere`: dirección, color e intensidad del sol, ajuste (`day` o `sunset`), color de horizonte y parámetros de neblina.
   - Un bloque de uniformes compartido que cualquier material puede enganchar (`attachAtmosphere(material)`).
   - El carril L1 lo rellena; los demás solo lo leen.
3. **Perfil de calidad** (`app/src/core/quality.ts`): tres niveles (`low`, `medium`, `high`) con los mandos de cada sistema:
   - sombras: no, precalculadas o en cascada;
   - densidad de vegetación;
   - detalle del mar;
   - juego de texturas;
   - escala de DPR.

   Elección: heurística de partida, 2–3 s de medición real de GPU al arrancar y bajada automática con histéresis (B11 del plan). El `quality.ts` de terreno pasa a leer de aquí.
4. **Presupuesto por sistema**:
   - `app/src/core/budget.ts` declara cuántas llamadas de dibujo, triángulos y milisegundos puede gastar cada sistema (tabla de abajo);
   - una prueba E2E sobre GPU real (`PENYAL_E2E_GPU=metal`) mide cada sistema encendiéndolo y apagándolo.
5. **Contrato de puntos de interés y cuaderno**:
   - Esquema zod de `content/pois/*.json`: id, ancla, radio de descubrimiento, ficha de ≤ 60 palabras en es, va y en, ampliación opcional, ids de datos de `content/facts.json` y créditos de imagen.
   - API del cuaderno: `notebook.add/has/list` sobre `localStorage`, con `try/catch`.
6. **Trabajo en paralelo seguro**:
   - `scripts/worktree-setup.sh`: crea un worktree de git por carril y enlaza los datos que no están en git (`data/raw`, `build/`, `app/public/assets/generated`, `tools/ktx-*`, `tools/bin`).
   - Asigna a cada carril su `E2E_PORT` y su `E2E_OUTPUT_DIR`.
   - Documenta el flujo en `CLAUDE.md`.

**Comprobación de B0:**
- `pnpm lint && pnpm typecheck && pnpm test`;
- la E2E de puntos fijos da las mismas capturas y métricas que antes;
- `scripts/worktree-setup.sh` crea un worktree donde `pnpm --filter @penyal/app e2e -- viewpoints` pasa.

## Carriles (en paralelo tras B0)

Cada carril trabaja en **su worktree y su rama** (`feat/b-<carril>`), solo sobre los ficheros que tiene asignados, y se integra en `main` por separado.

| Carril | Tareas del plan | Ficheros propios | Contratos que usa / aporta | Dependencias de personas | Agente | Esfuerzo |
|---|---|---|---|---|---|---|
| **L1 Luz y atmósfera** | B1, B2 | `app/src/world/atmosphere/**`, `app/src/world/sky*`, `app/src/world/shadows.ts`, `pipeline/src/penyal_pipeline/lightbake.py` | Aporta `Atmosphere` (sol real con SunCalc para Calp, ajustes de día y atardecer), neblina con la luz del sol dispersada, interruptor AgX/ACES, sombras en cascada en calidad alta y máscaras de sombra precalculadas por ajuste para las teselas | Fotos de referencia para decidir AgX o ACES | `implementer` + `design-engineer` (dirección visual) | 3–4 días |
| **L2 Sonido** | B4 | `app/src/audio/**`, entradas `phase = "B"` de audio en `data/catalog.toml` | Aporta `AudioSystem` (capas ambientales por zona, arranque con el primer gesto, volumen y silencio) | Aprobación de las descargas de audio (lista con licencias) | `docs-researcher` (licencias) + `implementer` | 1–1,5 días |
| **L3 Vegetación** | B5 | `pipeline/src/penyal_pipeline/vegetation.py`, `pipeline/src/penyal_pipeline/blender/plants.py`, `app/src/world/vegetation/**` | Usa `Atmosphere` y el perfil de calidad. Aporta `vegetation/pilot.json` (instancias por especie) y modelos optimizados. Especies de las listas de la GVA; colocación con la banda infrarroja y la cartografía 1:5000; nunca la posición real de la silene | Aprobación de las descargas de modelos de plantas CC0 | `docs-researcher` (especies) + `implementer` | 3–4 días |
| **L4 Mar** | B6 | `app/src/world/sea/**`, `pipeline/src/penyal_pipeline/coast.py` | Usa `Atmosphere`. Aporta `sea/coast-distance.ktx2` (distancia a la costa para la espuma) y el oleaje de Gerstner por niveles de calidad | — | `implementer` | 1,5–2 días |
| **L5 Estructuras** | B8 | `pipeline/src/penyal_pipeline/structures.py`, `pipeline/src/penyal_pipeline/blender/structures.py`, `app/src/world/structures.ts` | Aporta `structures/pilot.glb` (los 30 escalones con barandilla de OSM y el edificio del centro con la huella del ICV y las alturas del LiDAR) y una `GroundSurface` para los escalones | — | `implementer` | 2–3 días |
| **L6 Caminante** | B7 | `pipeline/src/penyal_pipeline/blender/character.py`, `app/src/player/character.ts` | Usa el estado del jugador (velocidad, en suelo, cámara). Aporta el modelo animado (quieto, andar, correr) con mezcla por velocidad y una sombra simple. Mientras falte el zip se prueba con un esqueleto mínimo generado en las pruebas | **Zip de Quaternius** (lo descarga el usuario) | `implementer` | 1,5–2 días |
| **L7 Interfaz y contenido** | B9, B10 | `app/src/ui/**` (excepto lo ya hecho en A3/A4), `app/src/input/touch*.ts`, `content/pois/**` | Usa el contrato de puntos de interés y cuaderno. Aporta la ficha con "ampliar", el cuaderno, el selector de idioma, "tocar para caminar", joystick opcional y botón de paseo automático | Revisión de valenciano; el parque confirma el Mirador de Ponent (decide si la ficha es la Pobla o el centro) | `frontend-engineer` + `design-engineer`; textos del responsable técnico | 3–4 días |
| **L8 Validación** | B11 (medición), B12 | `app/e2e/pilot*.spec.ts`, `docs/specs/002/pruebas-vecinos.md`, `docs/specs/002/protocolo-fotos.md`, `pipeline/src/penyal_pipeline/photomatch.py` | Aporta la E2E del piloto, la prueba de rendimiento por sistema sobre GPU real, el protocolo y la herramienta de registro de cámara con fotos (silueta del MDT), y el guion de la prueba con vecinos | Fotos en 2–3 puntos; organizar a los cinco vecinos; móviles de referencia | `test-engineer` + `ui-qa` | 2–3 días |

## Presupuesto repartido (móvil de referencia, nivel `medium`)

| Sistema | Llamadas de dibujo | Coste GPU objetivo* |
|---|---|---|
| Terreno (incluido el material) | ≤ 25 | ≤ 6 ms |
| Vegetación | ≤ 40 (instancias por especie y nivel de detalle) | ≤ 6 ms |
| Estructuras | ≤ 15 | ≤ 1 ms |
| Mar | ≤ 3 | ≤ 3 ms |
| Cielo y atmósfera | ≤ 2 | ≤ 1 ms |
| Caminante | ≤ 5 | ≤ 1 ms |
| Sombras (`high`: cascadas; `medium`: precalculadas) | ≤ 60 en `high`; 0 en `medium` | ≤ 5 ms en `high` |
| Margen | resto hasta 100 de objetivo y 200 de tope | — |

\* Objetivos provisionales para repartir el trabajo. Se calibran con la primera medición real en móvil (A7). Si un carril se pasa, lo detecta la prueba por sistema de B0.

## Orden de integración

1. **B0** a `main`: es el contrato de todos.
2. **Primera tanda** (4 carriles a la vez como máximo; con más carga, las E2E ya fallaron por tiempos):
   - **L1 Luz** (lo más visible y lo que más condiciona al resto);
   - **L5 Estructuras** (afecta a la colisión);
   - **L7 Interfaz** (el camino más largo por la revisión humana);
   - **L2 Sonido** (pequeño).
3. **Segunda tanda:**
   - **L3 Vegetación** (necesita L1 para la luz y la aprobación de descargas);
   - **L4 Mar** (necesita L1);
   - **L6 Caminante** (en cuanto llegue el zip);
   - **L8 Validación** (la E2E del piloto, al final de la tanda).
4. **Cierre:** fotos y comparación forzada; prueba con cinco vecinos; arreglos; revisión de código independiente; medición en móvil; marcar la fase B como hecha.

Protocolo de cada integración:
- el carril vuelve a basarse en `main`;
- pasan los controles y su E2E en su puerto;
- el agente `code-reviewer` revisa;
- se integra en `main`;
- en `main` se repiten la E2E de puntos fijos y la prueba de presupuesto por sistema;
- si algo empeora, se revierte ese carril y el resto sigue.

## Arranque anticipado (mientras termina la Fase A)

Estas tareas no tocan código y pueden empezar ya:
- **L3 (investigación):** lista de especies del tramo según las fuentes de la GVA ya registradas y lista corta de modelos de plantas CC0 con tamaños y licencias, para aprobarla.
- **L2 (investigación):** lista de sonidos con licencia (CC0 o CC BY; CC BY-SA solo para el archivo de audio tal cual), con tamaños, para aprobarla.
- **L8:** borrador del guion de la prueba con vecinos y del protocolo de fotos (puntos, horas y material), para que el vecino del equipo pueda hacer las fotos cuanto antes.
- **L7:** texto de la ficha piloto en castellano (≤ 60 palabras + ampliación), con los datos de `content/facts.json`, listo para traducir.

### Estado del arranque anticipado (11/10/2026)

- [ ] L3: especies y modelos de plantas → `docs/specs/002/vegetacion-especies.md`. En curso.
- [ ] L2: sonidos con licencia → `docs/specs/002/sonido-licencias.md`. En curso.
- [x] L8: guion de vecinos y protocolo de fotos → `docs/specs/002/pruebas-vecinos.md` y `docs/specs/002/protocolo-fotos.md`.
  - Los puntos F1–F5 llevan coordenadas y rumbos calculados a partir de `trail.json`.
- [x] L7: ficha piloto, en dos variantes → `docs/specs/002/ficha-piloto.md`.
- [x] Correo al parque → `docs/specs/002/consulta-parque.md`. Recoge las 11 discrepancias, los 4 datos sin verificar, el Mirador de Ponent, las paradas, la reserva, los menores y las medidas del túnel.
  - **Lo envía el responsable del proyecto.**
  - Abre una decisión: cómo citar una respuesta por correo, porque el esquema exige una URL. Irá como enmienda del ADR 0005.
- [ ] B0: diseño de contratos → `docs/adr/0010-world-systems-and-shared-contracts.md`, del agente `architect`, con estado "Propuesto". En curso.
  - La implementación de B0 espera al cierre de la fase A.
- [ ] Fase A: M5, la carcasa del túnel en la boca este, del agente `implementer`. En curso.
  - Después se regeneran el terreno y el túnel hasta que `penyal verify-generated` salga con 0.
  - El manifiesto de materiales ya está regenerado: las 12 texturas KTX2 son idénticas byte a byte.

## Riesgos de la paralelización

| Riesgo | Respuesta |
|---|---|
| Conflictos en ficheros compartidos | B0 primero; propiedad exclusiva de ficheros por carril; los cambios a contratos solo los hace el integrador |
| Carga de la máquina (10 núcleos, 16 GB) | Como máximo 4 carriles a la vez; E2E con `--workers=1` en cada carril; la E2E completa solo en `main` |
| Rendimiento acumulado (cada carril cumple, pero juntos no) | Presupuesto por sistema y prueba de apagar y encender en `main` tras cada integración |
| Personas no disponibles (zip, fotos, revisión, vecinos) | Los carriles terminan su parte técnica; la fase B no se marca hecha sin la validación humana |
| Descargas sin aprobar | Ningún carril descarga recursos sin que el usuario apruebe la lista con nombre, origen, tamaño y licencia |

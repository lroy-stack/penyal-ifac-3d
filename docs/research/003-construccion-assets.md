# 003 · Construcción de assets: edificios, muros, caminos, mobiliario y vegetación

- Fecha: 2026-10-11. Estado: **investigación; nada descargado; ningún fichero editado salvo este**.
- Versiones fijadas (verificadas en el repo): three **0.186.1** (`app/package.json`, `app/node_modules/three`); bpy **5.2.2** y Python 3.13 (`pipeline/pyproject.toml`, `pipeline/.venv`); `@gltf-transform/cli` **4.5.1** (`package.json`). Blender 5.2 LTS (ADR 0003).
- Ámbito: piloto (Centre d'Informació → km 0,421) y, por extensión, el resto del Penyal. Specs: `docs/specs/002-fase-b-paralelizacion.md` (L3 vegetación, L5 estructuras), `docs/specs/002/vegetacion-especies.md`.

## Resumen (la respuesta primero)

1. **Construir la geometría en Python + bmesh/numpy, no con Geometry Nodes, en la primera versión.** Es lo que ya hacemos en `blender/terrain.py` y `spike.py`, y el determinismo se prueba sin depender de la versión de un nodo. GN queda como opción para repetir modelos, con seeds fijos y versión de bpy fijada (sección 2).
2. **Kits modulares + atlas por material.** Presupuesto real: el riesgo en móvil son las **llamadas de dibujo** y los materiales, no los triángulos. Con 60 k triángulos y 15 llamadas (ADR 0010, `structures`, medium), el piloto cabe holgado si se agrupa por material y por tesela.
3. **Densidad de texel fija por tier** (propuesta: 64 / 128 / 256 px/m) y **ORM en un solo PNG/KTX2** en el orden que ya usa glTF (R = oclusión, G = rugosidad, B = metal). Poly Haven publica `arm` con ese orden.
4. **Instancing**: para vegetación, `InstancedMesh` en runtime (002). Para props repetidos dentro de un GLB, `EXT_mesh_gpu_instancing` (export de Blender `export_gpu_instances` o `gltf-transform instance`). `GLTFLoader` de r186 lo convierte en `InstancedMesh` (verificado en fuente).
5. **Caminos**: la ruta (tierra/grava) va como **máscara en el material del terreno** (0 llamadas, sin z-fighting). Escalones, barandillas, cubiertas y mobiliario van como **mallas separadas** por tesela.
6. **Colisión**: proxy separado (polígonos o cajas en JSON), nunca la malla de render (ADR 0010, `GroundSurface`).
7. **Materiales CC0**: Poly Haven verificado (CC0, API leída hoy). ambientCG: CC0 por fuentes secundarias, sitio inaccesible hoy, **ids no verificados**. Quaternius: **no** usar sin revisar QAL (ADR 0007 solo admite CC0/CC BY).
8. **Pipeline propuesto**: `penyal structures` y `penyal vegetation`, cada uno con `pure core` (numpy/shapely, testeable sin bpy) + `blender/*.py` (solo export), manifest de procedencia como `terrain`, y un golden de métricas (triángulos, llamadas, AABB, sha256).

---

## 1. Buenas prácticas de construcción de assets

| Tema | Regla propuesta | Aplicación en el proyecto | Fuente / estado |
|---|---|---|---|
| Escala | 1 unidad glTF = 1 m; marco local (ADR 0004): `x = E − 767000`, `y = H`, `z = −(N − 4280000)` | `blender/terrain.py` ya convierte `(x,y,z)→(x,−z,y)` en Blender y el exportador con `export_yup` devuelve metros locales sin offsets de nodo | ADR 0004; `terrain.py` cabecera (leído) |
| Pivotes | Origen en la base del objeto (suelo, cara de apoyo), no en el centro | Escalones y postes con origen en el punto de apoyo sobre el terreno, para colocarlos por `y` del DEM | Práctica habitual; no verificada en una guía oficial hoy |
| Nombres | `<sistema>_<tipo>_<id>[_LODn]`, p. ej. `struct_step_017`, `struct_bldg_centre_LOD0`, `veg_pine_LOD1`; el nodo lleva el id de la fuente OSM en `extras` solo si la exportación lo permite (`export_extras` está apagado en el spike) | Así los tests localizan piezas por nombre | Convención propuesta |
| Modular | Kit por **módulos de 1 m o 2 m** (muro, esquina, cubierta, barandilla, escalón) y un **ancho de rejilla** fijo; cada pieza se reutiliza con transformaciones, las sueltas (edificio) van como malla propia | Escalones y barandillas salen de polilíneas; el edificio es una malla única | Práctica habitual |
| Atlas / trim sheets | Un material por familia: piedra/mampostería, enfoscado encalado, teja, metal, madera; UV en tiras (trim) para molduras y bordes | Reduce materiales → llamadas. Un atlas de 2k cubre varias familias si comparten tesela | Propuesta |
| Texel density | Objetivo fijo por tier (tabla 1b) | Medir con `px/m = resolución / metros de UV` en un test | Propuesta; no hay fuente de referencia en este entorno |
| PBR | glTF metallic-roughness: `baseColorTexture` sRGB; `metallicRoughnessTexture` con **G = rugosidad, B = metal** (lineal); `occlusionTexture` con **R** | Poly Haven `arm` (AO en R, rugosidad en G, metal en B) encaja: un solo fichero sirve a `occlusionTexture` y `metallicRoughnessTexture` | glTF 2.0 spec, §pbrMetallicRoughness y §occlusionTexture (registry.khronos.org, leído 2026-10-11) |
| Normales y tangentes | Normal map en espacio tangente, +Y (OpenGL). El exportador de Blender tiene `export_tangents` (apagado en `spike.py`). three usa `vTangent`/`vBitangent` si existen; si no, calcula el marco en el shader | Exportar tangentes solo en materiales con normal map y comprobar en el test que el `TANGENT` existe. Decisión a medir | `bpy` 5.2.2: `export_tangents` (leído); three: `normal_fragment_begin.glsl.js:26` (leído) |
| Vertex colour | `COLOR_0` (tinte, AO barato en geometría): valores **clamp [0,1]** según glTF | Tinte de encalado y AO de base de muro sin textura extra | glTF 2.0 spec, §COLOR_0 (leído); exportador `export_all_vertex_colors` (bpy, leído) |
| LOD | Sin `MSFT_lod` en GLTFLoader ni `THREE.LOD` por distancia al centro (ADR 0002). LOD por SSE propio, como el terreno; cada LOD es un fichero o un nodo con su propio id | Edificio: LOD0 (todo) y LOD1 (cubierta + masas); vegetación: LOD0/LOD1 + tarjeta | ADR 0002 (leído) |
| Impostores / tarjetas | Tarjeta alfa cruzada (2 planos) o billboard para > 60 m; `alphaMode: MASK` (glTF) para hojas; limitar cuantas tarjetas se solapan (overdraw en móvil) | Coherente con `vegetacion-especies.md` (tarjeta a distancia) | Práctica habitual; glTF `alphaMode` en el spec |
| Instancing | Runtime: `InstancedMesh` por especie/LOD. Export: `EXT_mesh_gpu_instancing` solo para props idénticos dentro de un GLB | Ver sección 2 y 3 | `GLTFLoader.js:103, 250, 1683–1765` (three 0.186.1, leído) |
| Merge por tesela | Un mesh por (tesela, material). Las piezas con el mismo material se unen con `join` (gltf-transform) o en bmesh | Objetivo: ≤ 15 llamadas de estructuras por tesela y ≤ 15 en total en el piloto | `gltf-transform join --help` (4.5.1, leído). Nota: `join` puede **aumentar** vértices si hay mucha reutilización; con instancias, no unir |
| Colisión | Proxy separado: polígonos walkable (`GroundSurface`) y cajas para muros; **nunca** la malla de render | `GroundSurface` de escalones (spec L5); salida JSON, no GLB | ADR 0010 (leído) |

**Tabla 1b · Densidad de texel y tamaños por tier (propuesta, no hay fuente externa)**

| Tier | Muros / fachadas | Suelo / camino (tile) | Atlas máx. | Compresión |
|---|---|---|---|---|
| `low` | 64 px/m | 64 px/m | 1k | ETC1S |
| `medium` | 128 px/m | 128 px/m | 2k | ETC1S color/ORM; UASTC para normales (como `make-material-textures.mjs`) |
| `high` | 256 px/m | 256 px/m | 2k (touch) / 4k (desktop) | UASTC para normales |

Cálculo de referencia: a 128 px/m, un atlas de 2k cubre 16 m de muro por lado. Un escalón de 0,30 m de huella necesita ~38 px: muy poco; la forma del escalón la da la geometría, no la textura.

## 2. Modelado procedural determinista en Blender como módulo

**Python + bmesh/numpy (recomendado para la v1)**

- Todo es código propio: el orden de vértices lo decide el script. Ya se prueba así: `pipeline/tests/test_spike.py:83–85` exporta dos veces con `PYTHONHASHSEED` distinto y compara `sha256` (byte-idéntico).
- Los `set`/`dict` no deben influir en el orden: ordenar por id antes de construir (regla de la prueba del spike).
- `mathutils.noise` y `random` solo con `random.Random(seed)` por pieza, con seed derivada de un id estable (hash SHA-256 del id, no `hash()`, que depende de `PYTHONHASHSEED`).

**Geometry Nodes (opción para repetir modelos, no para la v1)**

- El nodo *Random Value* usa como ID el atributo `id` del contexto o el índice, y un *Seed* de entrada; con el mismo ID y seed el resultado es el mismo dentro de una versión (docs 5.2: `modeling/geometry_nodes/utilities/random_value.html`, leído 2026-10-11). **No encontré en la documentación una garantía de reproducibilidad entre versiones de Blender**: no verificado; se asume que hay que fijar `bpy` (ya está fijado a 5.2.2) y repetir el golden al actualizar.
- Dirigir GN desde bpy: `modifier["Socket_x"] = valor` (nombres de socket dependen de la versión). Riesgo: los sockets cambian al renombrar el grupo; por eso el test debe fallar si falta un socket.
- Regla: GN solo si hay ≥ 3 usos repetidos del mismo generador (p. ej. barandillas con postes) y su salida se congela en un GLB con su manifest. El GLB es la fuente de verdad, no el `.blend`.

**Exportador: opciones que ya tenemos y las que añadiríamos**

| Opción (bpy 5.2.2) | Estado en `spike.py` | Recomendación | Motivo |
|---|---|---|---|
| `export_format="GLB"`, `export_yup=True`, `export_apply=True` | sí | mantener | Marco local sin nodos extra |
| `export_texcoords`, `export_normals` | sí | mantener | |
| `export_tangents` | False | **True solo en materiales con normal map** y medir | Ver sección 1 |
| `export_materials="EXPORT"`, `export_image_format="AUTO"` | sí | mantener | Texturas empaquetadas; el optimizador las reescribe a KTX2 |
| `export_extras`, `export_keep_originals`, `export_cameras`, `export_lights` | False | mantener | Sin metadatos ni rutas (la prueba de procedencia lo exige) |
| `export_gpu_instances` | no | solo para props idénticos de un GLB | Docs: "Instances must be meshes… children of the same object… same materials" |
| `export_gn_mesh` | no | solo si usamos GN | Exporta instancias de GN |
| `export_meshopt_compression_enable` | no | **no**: usamos `gltf-transform meshopt` | Un solo compresor para `penyal verify-generated` (`optimize.mjs`) |
| `export_draco_*`, `export_gltfpack_*` | no | no | Draco no es lo que cargamos; gltfpack fuera de la cadena |

Fuentes: Blender 5.2 manual, glTF exporter, sección *GPU Instances* (https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html, leído 2026-10-11). Las propiedades y sus descripciones se leyeron con `bpy.ops.export_scene.gltf.get_rna_type()` en `pipeline/.venv` (bpy 5.2.2).

**Pruebas (golden) para assets**

| Qué | Cómo | Dónde |
|---|---|---|
| Determinismo | dos exportaciones con `PYTHONHASHSEED` distinto → mismo `sha256` | como `test_spike.py` |
| Triángulos y llamadas | contar primitivas tras `join`; comparar con `structures.metrics.json` | `pipeline/tests/test_structures_metrics.py` (nuevo) |
| Bounds | AABB de cada pieza frente a la huella de la fuente ±1 cm; y `y ≥ DEM` | nuevo |
| Escala | un módulo de 1 m mide 1,000 ± 1e-6 m | nuevo |
| Material | ORM en el orden R/G/B; normal map con tangentes; sin materiales huérfanos | como `test_terrain_export.py` (material) |
| Validez | `gltf-transform validate` sin errores (CLI 4.5.1 expone `validate`) | `optimize` o paso nuevo |
| Presupuesto | `structures` ≤ 15 llamadas y ≤ 60 000 triángulos a medium (ADR 0010) | E2E `budget.spec.ts` (ya existe) |

## 3. Edificios, caminos y mobiliario desde datos

**3a. Edificio del centro (spec L5)**

- Huella: OSM `way/…` 651 m² y CV05 `CON04` 623 m² (docs/research/003-inventario-datos-propios.md, líneas 21–22). Diferencia del 4 %: usar la **CV05** como polígono y OSM como control; el polígono final y su fuente se guardan en el manifest.
- Altura: LiDAR 2016 clase 6 dentro de la huella; mediana 4,9 m, p95 6,9 m (inventario, línea 22). Usar la **mediana** de la clase 6 como altura de cornisa y el suelo de la clase 2 en un anillo 1–6 m como base.
- Cubierta plana vs. inclinada: con la nube LiDAR, ajustar un plano por cuadrícula de 1 m a los puntos de clase 6; si el residuo del plano es < 0,15 m y la pendiente < 5°, plana; si no, a dos aguas con la línea de cumbrera en el eje mayor. El color de la cubierta sale de la ortofoto (inventario, línea 94). Verificación: test con un prisma sintético de cubierta conocida.
- Extrusión: `shapely` 2.2.0 (ya en `pipeline/pyproject.toml`) para limpiar el polígono (`buffer`, `simplify`); triangulación con polígonos con huecos **no verificada** en esta sesión (elegir la API al implementar); sin inventar geometría fuera de los datos (regla de `CLAUDE.md`).
- Orden de vértices: ordenar por coordenada redondeada a mm antes de construir la malla (determinismo).

**3b. Caminos y ruta**

| Opción | Coste en llamadas | Z-fighting | Cuándo |
|---|---|---|---|
| **Máscara en el material del terreno** (canal o textura `path_mask` R8, muestreada en el shader de `terrain/material.ts`) | 0 | No | **Recomendada** para la ruta de tierra/grava: el terreno ya tiene parche de detalle (`penyal-terrain-detail-v4`); el coste es una lectura de textura |
| Cinta (ribbon) sobre el DEM con desplazamiento de 3–5 cm | 1 por tesela | Sí si el DEM de 1 m y la malla LOD no coinciden; reducible con `polygonOffset` | Asfalto, escalones pavimentados, aparcamiento |
| Decal (proyección) | 1 | Igual | No recomendada: complica la pila de transparencias en móvil |

- `polygonOffset`, `polygonOffsetFactor`, `polygonOffsetUnits` existen en `Material` de three 0.186.1 (`src/materials/Material.js:375–391`, leído).
- El terreno usa tiles de 256 m con LOD por SSE (ADR 0002): una máscara a 1 m de resolución por tesela (256 × 256 px) cuesta 64 KiB en R8 sin comprimir.
- Asfalto: si en el piloto hay asfalto (acceso al centro), usar cinta con su propio material; si solo hay tierra, máscara.

**3c. Escalones y barandillas desde polilíneas**

- Escalones: los 30 de OSM (spec L5). Contar tramos con la altura del DEM bajo cada escalón; huella y contrahuella **de OSM si existen; si no, derivadas del DEM y marcadas como aproximación** (regla de `CLAUDE.md`: "las aproximaciones se marcan en el código y `CREDITS.md`"). Normas de escalera (contrahuella/huella) **no verificadas** en esta sesión: no usar como dato.
- Cada escalón: caja con origen en el apoyo, una malla con todos los escalones (una llamada), `GroundSurface` = proxy plano (sección 1).
- Barandilla: barrido de un perfil circular (ø 3–4 cm) a lo largo de la polilínea a 0,9–1,0 m de altura (**criterio de diseño, no verificado**); postes como instancias (`InstancedMesh` o `EXT_mesh_gpu_instancing`) cada ~2 m.
- Ambos: la polilínea y su altura provienen de `trail.json`/`tunnel.json` ya existentes (`penyal trail`), no de otra fuente.

**3d. Señalética y textos**

- El texto no se hornea en texturas: (1) es multilingüe (es/va/en, ADR de hechos y `CLAUDE.md`), (2) es accesible en el DOM. Los paneles son geometría + tarjeta HTML o textura de **marco** sin letras.

**3e. Aparcamiento y marcas viales**

- Solo si `amenity=parking` o `CV05` lo muestra dentro del piloto (comprobar antes de construir). Si no hay, no se construye.
- Marcas: cintas de 0,10–0,12 m sobre el asfalto con `polygonOffset`, o una textura de marcas en el material de asfalto (una llamada).

**3f. Mobiliario**

- Ver sección 4 (Poly Haven tiene candidatos CC0, no descargados).
- Bancos, papeleras, señales: un modelo por tipo; instancias por ubicación (sin posiciones reales de protegidas, regla del spec 002).

## 4. Materiales y modelos CC0: candidatos

Todos los ids de Poly Haven se leyeron en `api.polyhaven.com/assets` y `api.polyhaven.com/files/<id>` el 2026-10-11. Tamaños = JPG 1k por mapa (KiB). Ninguno está descargado.

| Necesidad | Id (Poly Haven, textura) | Licencia | 1k: diff / nor_gl / arm (KiB) | Por qué encaja (y límite) |
|---|---|---|---|---|
| Mampostería / muro de piedra seca | `old_stone_wall` | CC0 | 859 / 1159 / 550 | "Rough, uneven masonry with beige-brown stones, visible mortar" (API `info`): parecido a la caliza del Penyal. Muy detallado, pesado para móvil |
| Mampostería ligera (alternativa) | `plaster_stone_wall_01` | CC0 | 688 / 962 / 355 | Piedra embebida en mortero: muros de bancal. Más barato |
| Enfoscado / encalado | `plastered_wall_02`; `clay_plaster` | CC0 | 426 / 937 / 535 (`plastered_wall_02`) | **No hay encalado blanco** en la lista leída: los candidatos son gris/arcilla. Tinte blanco por `COLOR_0` o factor de color. Verificar en la vista previa |
| Teja (árabe o curva) | `clay_roof_tiles_02` (tejas solapadas) | CC0 | 882 / 966 / 551 | Teja de arcilla solapada. **No verificado que sea curva (árabe)**; comprobar la vista antes de usarla |
| Teja (alternativa) | `ceramic_roof_01` | CC0 | — (no medido) | Cerámica vieja con musgo: envejecida, quizá demasiado |
| Asfalto (acceso, aparcamiento) | `asphalt_04` | CC0 | 859 / 962 / 541 | Carretera fisurada; para acceso del centro |
| Pavimento / escalones | `concrete_pavers_02` | CC0 | 683 / 687 / 419 | Losa de hormigón con juntas: escalones y explanada |
| Piedra de camino | `gravel_stones`; `grey_stone_path` | CC0 | 783 / 1450 / 1027 (`gravel_stones`) | Grava para la ruta: pero el `nor_gl` pesa; probar máscara sin normal map |
| Metal oxidado (barandilla) | `metal_plate_02` | CC0 | 611 / 178 / 1050 (`arm`) | Óxido; el `arm` pesa más que el color |
| Madera (bancos) | `brown_planks_09` | CC0 | 745 / 713 / 477 | Tablón oscuro, bancos y tarimas |
| Mobiliario (modelos) | `painted_wooden_bench`, `metal_trash_can` | CC0 (por verificar en `info`) | sin medir | Candidatos de la lista de modelos (`api.polyhaven.com/assets?t=models`); tamaño de malla sin medir |

**ambientCG** (CC0 según fuentes secundarias: [licenseorg.com](https://licenseorg.com/guide/3d-assets/ambientcg) y [Creative Bloq](https://creativebloq.com/3d-tips/find-high-res-textures-1232646), leídas 2026-10-11). El sitio no responde desde este entorno (conexión rechazada), así que **no puedo dar ids verificados**. Búsquedas a considerar: "asphalt", "paving stone", "bricks", "plaster", "roof tiles", "rust metal"; comprobar en `ambientcg.com` licencia y tamaños antes de fijar un id. No inventar ids.

**Kenney** (CC0 según la FAQ de kenney.nl, leída por fragmento de búsqueda; el sitio no respondió a `curl`): packs de urbano/naturaleza candidatos para mobiliario; revisar contenido y tamaño antes de usar (no verificado en esta sesión).

**Quaternius**: ADR 0008 dice que `quaternius.com/license.html` muestra QAL v1.0 (2026-08-28). No pude leer la página hoy. ADR 0007 solo admite CC0 y CC BY para assets: **no usar packs de Quaternius para estructuras ni vegetación sin confirmar la licencia del zip** (ADR 0008 cubre solo al caminante).

**Aviso sobre el encalado y el color**: la tonalidad mediterránea (encalado, caliza, terracota) debería validarse con fotos de referencia del Penyal propias (CC0/CC BY o propias, regla de texturas de ADR 0007: sin fotos CC BY-SA como textura).

## 5. Diseño de pipeline propuesto (para el tech lead)

**Nuevos pasos**

| Paso | Entrada (catálogo) | Salida | Núcleo puro | Export bpy |
|---|---|---|---|---|
| `penyal structures` | `icv-cv05-penyal` (EdificacionesBCV05, CON04), `icv-mdt-2016-0848`, `icv-lidar-2016-*` (clase 6 y 2), `osm-penyal` (steps, barriers), `trail.json` | `build/structures/pilot.glb`, `pilot-collision.json`, `structures.metrics.json` → `app/public/assets/generated/structures/` | `structures.py` (shapely + numpy): extrusión, cubierta, escalones, barandilla | `blender/structures.py` |
| `penyal vegetation` | `polyhaven-pine-*` (solo texturas 1C, 4,5 MB), `polyhaven-shrub-*`, `vegetation/pilot.json` (002) | `vegetation/*.glb` + `pilot.json` | `vegetation.py` (posiciones, LOD, tarjetas) | `blender/plants.py` |

**Catálogo y lock**

- Cada fichero nuevo entra en `data/catalog.toml` con `licence`, `attribution` y, si aplica, `share_alike`. Texturas de Poly Haven: `kind = "file"` con `expected_bytes` y `size_tolerance`, como las existentes.
- ambientCG o Kenney sin API: `data/manual/<vendor>/` (gitignored), registrado con sha256 en `data/manifest.lock.json` (ya es el patrón de Quaternius, ADR 0008).

**Procedencia y verificación**

- `artefacts.py` ya define `_inputs(kind)` y `_tools(kind)`; añadir `structures` y `vegetation` con `("bpy", "gltf-transform", "node")`, como `terrain`. `penyal verify-generated` falla si cambian las entradas.
- Los manifests guardan: entradas con sha256, versión de bpy, de gltf-transform, de ktx y el sha256 del GLB final.

**Presupuesto por tier**

| Sistema | low | medium | high |
|---|---|---|---|
| structures (llamadas / triángulos) | **8 / 25k** (propuesta) | **15 / 60k** (ADR 0010) | **25 / 120k** (propuesta) |
| vegetation | 20 / 100k (ADR 0010) | 40 / 250k (ADR 0010) | 50 / 400k (ADR 0010) |

Las cifras de `structures` en low/high no están en ADR 0010 (solo `vegetation`, `sea`, `shadows`): propuesta a validar con A7.

**Tests**

- Unitarios sin bpy (`pytest -m "not slow"`): extrusión de un cuadrado de 10 m → 4 muros, área de cubierta; escalones de polilínea conocida; barandilla: N postes para L metros; determinismo de seeds.
- Lentos (`pytest -m slow`, con `PENYAL_REQUIRE_DATA=1` para no saltar): export bpy, dos corridas con `PYTHONHASHSEED` distinto, golden de métricas, AABB, ORM, tangentes.
- E2E: `budget.spec.ts` ya cuenta llamadas por sistema: añadir `structures` y `vegetation` a la tabla (ADR 0010 §4).

**Riesgos**

| Riesgo | Mitigación |
|---|---|
| Wheel de bpy sin algún add-on | Ya verificado para el exportador glTF (bpy 5.2.2 expone todas las opciones usadas); lo demás no lo necesitamos |
| `join` aumenta vértices por reutilización | Unir solo lo que no es instancia; medir |
| Texturas pesadas (`old_stone_wall` nor 1,1 MB) | Medir la salida KTX2 antes de elegir; alternativa `plaster_stone_wall_01` |
| Normal map sin tangentes en algunos GPU | Exportar tangentes solo donde hay normal map y medir |
| Modelos de Poly Haven con geometría alta | Decimar en pipeline (`simplify --ratio`, `--error`), no en la app |
| ids de ambientCG cambian | No fijar ids sin verificar; usar manual + sha256 |
| Quaternius: licencia QAL | Excluir de estructuras y vegetación hasta confirmar (ADR 0007/0008) |

## 6. Conflictos y no verificado

- **GitHub** no respondió (conexión rechazada): no pude leer el *Khronos glTF Best Practices* ni la especificación de `EXT_mesh_gpu_instancing` original. Las reglas de la sección 1 de "buenas prácticas" son **propuesta propia** salvo donde se cita el spec 2.0 o la fuente de three/bpy/gltf-transform.
- **Blender Random Value**: la página de docs 5.2 se leyó; no hay garantía documentada de reproducibilidad entre versiones de Blender. No verificado.
- **Texturas**: colores (encalado, terracota) y forma de teja (árabe vs. plana) no se verificaron visualmente; ids de ambientCG no verificados; Kenney y Quaternius solo por fragmentos de búsqueda o ADR.
- **Normativa de escalones y barandillas** (contrahuella, altura de barandilla): no verificada; no usar como dato sin fuente oficial.
- **Presupuestos de `structures` en low/high**: propuesta, no ADR.
- **Rendimiento real** en móvil: sin medir (igual que 002).
- **Este fichero** se escribió porque el encargo lo pedía; el resto del repo no cambió.

## Fuentes (todas accedidas 2026-10-11)

- Repo: `CLAUDE.md`; `docs/adr/0002, 0003, 0007, 0008, 0010, 0011`; `docs/specs/002/vegetacion-especies.md`; `docs/specs/002-fase-b-paralelizacion.md`; `docs/research/003-inventario-datos-propios.md` (líneas 21–22, 94); `pipeline/src/penyal_pipeline/blender/{spike,terrain}.py`; `pipeline/tests/test_spike.py`; `pipeline/tests/test_terrain_export.py`; `pipeline/pyproject.toml`; `scripts/optimize.mjs`; `scripts/make-material-textures.mjs`; `data/catalog.toml`.
- Versiones locales: `app/node_modules/three` **0.186.1** (`examples/jsm/loaders/GLTFLoader.js:103, 250, 643, 1683–1765`; `src/materials/Material.js:375–391`; `src/renderers/shaders/ShaderChunk/normal_fragment_begin.glsl.js:26`); `node_modules/@gltf-transform/cli` **4.5.1** (`gltf-transform help instance|join|partition|tangents|meshopt|simplify`); `pipeline/.venv` **bpy 5.2.2** (`bpy.ops.export_scene.gltf.get_rna_type()`).
- Blender 5.2 manual, glTF 2.0 exporter (sección GPU Instances): https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html
- Blender 5.2 manual, Random Value: https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/utilities/random_value.html
- glTF 2.0 spec (Khronos): https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
- gltf-transform 4.5 CLI (sitio, no leído; ayuda local leída): https://gltf-transform.dev/cli
- Poly Haven: API `https://api.polyhaven.com/assets?t=textures`, `…?t=models`, `https://api.polyhaven.com/files/<id>`, `https://api.polyhaven.com/info/<id>`; licencia CC0: https://polyhaven.com/license
- ambientCG (CC0 por fuentes secundarias): https://licenseorg.com/guide/3d-assets/ambientcg ; https://creativebloq.com/3d-tips/find-high-res-textures-1232646 (sitio https://ambientcg.com inaccesible hoy)
- Kenney (CC0 por fragmento de búsqueda; sitio https://kenney.nl/support inaccesible hoy)
- Quaternius (licencia no leída hoy; ADR 0008): https://quaternius.com/license.html

## Addendum del responsable técnico (11/10/2026)

**Huecos que cierra:** el encargo pedía materiales para lo que el visitante realmente pisa y ve. El inventario (`003-inventario-datos-propios.md`) muestra que el sendero del tramo piloto es **empedrado** y no asfalto, y faltaba un encalado o enlucido blanco.

**ambientCG.**
- La licencia está verificada en la fuente: "All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License" (https://docs.ambientcg.com/license/, consultada el 2026-10-11).
  - `ambientcg.com` solo tiene IPv4; se consultó por el relé NAT64 del proyecto.
- Sus descargas son zips por material de 4–9 MB en 1K-JPG, porque incluyen desplazamiento y otros mapas. Poly Haven, en cambio, permite bajar mapa a mapa.

**Candidatos** (ninguno elegido). La elección se hace comparando con fotos reales del sendero y del centro (`docs/specs/002/protocolo-fotos.md`).

| Uso | Poly Haven (CC0, `api.polyhaven.com/assets?t=textures`) | ambientCG (CC0, API v2) |
|---|---|---|
| Empedrado del sendero (`unhewn_cobblestone` en OSM) | `cobblestone_02` (path, footpath, stones), `cobblestone_floor_02` (plastered, fixed), `cobblestone_floor_05`, `cobblestone_floor_09` | — (la búsqueda `PavingStones` no devolvió nada; sin revisar otros términos) |
| Escaleras de adoquín (`paving_stones`, `sett`) | `brick_pavement_02/03`, `checkered_pavement_tiles` | — |
| Encalado o enlucido blanco | `castle_brick_02_white`, `clay_plaster`, `beige_wall_001` | `Plaster002`–`Plaster006` y `PaintedPlaster017` (etiqueta "white"), 7,5–8,3 MB en 1K-JPG |
| Teja | `clay_roof_tiles`, `clay_roof_tiles_02`, `clay_roof_tiles_03`, `ceramic_roof_01` | — |
| Asfalto (solo si se modela el acceso rodado) | `asphalt_04`, `asphalt_06`, `clean_asphalt` | — |

**Sin verificar:**
- **Cubiertas del centro.** La ortofoto 2024 las muestra planas, ocres y con terrazas (`003-capturas/orto2024-centro-150m.jpg`). La teja puede no hacer falta en el tramo piloto.
- **Aspecto real del empedrado.** No se sabe si es piedra irregular tomada con mortero o canto suelto. Lo dirán las fotos.

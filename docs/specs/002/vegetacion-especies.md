# L3 Vegetación del tramo piloto: especies y modelos (investigación)

- Fecha: 2026-10-11. Estado: **propuesta; nada descargado**; sin cambios de código.
- Ámbito: Centre d'Informació → km 0,421 (350 m tras el torniquete), ladera NO baja, ~70–120 m s. n. m., caliza.
- Spec: `docs/specs/002-fase-b-paralelizacion.md` (carril L3, tarea B5).
- Requisitos que cumple esta investigación: silene nunca en posición real (ADR de hechos; `silene-history`), descargas solo tras aprobación (sección 5).

## Resumen

- **Abundancia (iNaturalist): 79 especies con observaciones de calidad investigación en la caja del tramo** (consulta del responsable técnico vía NAT64, 2026-10-11; sección 2). Encabezan lentisco (16), bayón (13), cantueso (10) y cebolla albarrana (10); palmito 5, pino carrasco 3, efedra 3, romero 3; **sabina e hinojo marino: 0**. Son recuentos de observaciones (interés de quien observa), no de cobertura.
- **GVA: no re-verificada hoy.** `parquesnaturales.gva.es` (en vivo) y `web.archive.org` dan timeout desde curl y WebFetch bloquea Internet Archive. Uso las copias ya registradas en `content/sources.json`, con sus fechas de snapshot.
- **Especies confirmadas en fuentes:** palmito (*Chamaerops humilis*), sabina (*Juniperus phoenicea*) y *Ephedra fragilis* (GVA, vía `flora-rupicola`); pino carrasco (*Pinus halepensis*) como "vegetación arbustiva, salpicada por pino carrasco" (spain.info, leído hoy). El resto de la lista de partida (lentisco, romero, cantueso, hinojo marino, bayón, gramíneas) es **plausible pero no verificada para el Penyal**.
- **Modelos:** Poly Haven (CC0, verificado por API hoy) da arbustos y hierba genéricos aptos para móvil. Su pino (`pine_tree_01`) tiene 17,2 M triángulos y 958 MB: solo sirve si se decima en pipeline. No hay palmito, sabina ni efedra. Para esas, propongo procedural con tarjetas alfa.
- **Protegidas (Silene hifacensis, Teucrium hifacense, Centaurea rouyi, Hippocrepis valentina):** cero instancias 3D y cero posiciones; solo en fichas (sección 4).
- **Decisión que necesito:** pino (958 MB con decimado, 22 MB con `pine_sapling_small`, procedural sin descarga, o **procedural con las texturas CC0 de `pine_tree_01`, 4,5 MB, la opción que recomienda el responsable técnico**) y si se aprueba revisar el Quaternius Stylized Nature MegaKit (104 MB, sin lista de modelos). Total recomendado: **9,18 MB** (sección 5).

## 1. Paleta del tramo

Notación: "GVA" = cita de `content/sources.json`/`facts.json` con snapshot. "[conoc.]" = conocimiento general del redactor, **no verificado en fuente de esta sesión**.

| Especie (científico) | es / va / en | Forma y altura | GVA | iNat (tramo) | Peso visual y nota |
|---|---|---|---|---|---|
| *Pinus halepensis* | pino carrasco / pi d'Alep / Aleppo pine | árbol 8–15 m [conoc.], copa abierta e irregular | spain.info (2026-10-11): "vegetación arbustiva, salpicada por pino carrasco"; no aparece en `flora-rupicola` (GVA) | 3 | Alto: pinos plantados y espontáneos cerca del centro. Confirmar en campo. |
| *Chamaerops humilis* | palmito / paller / European fan palm [conoc.] | mata de 1–3 m, varios troncos | GVA `gva-vegetacion-rupicola` (snap. 2025-09-09), `gva-presentacion` (snap. 2026-07-12) | 5 | Alto, forma reconocible. Sin modelo CC0 directo. |
| *Juniperus phoenicea* | sabina / savina / Phoenician juniper [conoc.] | arbusto o árbol pequeño, 1–5 m | GVA (mismas fuentes) | 0 | Medio. Sin modelo CC0 directo. |
| *Ephedra fragilis* | efedra / efedra / ephedra [conoc.] | arbusto de 0,5–1,5 m, ramas verdes sin hojas | GVA (mismas fuentes) | 3 | Bajo; rupícola, en fisuras. Mejor en tarjeta que en masa. |
| *Pistacia lentiscus* | lentisco / llentisca / mastic tree [conoc.] | arbusto perenne 1–3 m, copa densa | no en fuentes leídas (la guía autonómica lo cita para otro parque, no para el Penyal) | 16 (la más observada) | Medio-alto en matorral. Verificar. |
| *Rosmarinus officinalis* | romero / romaní / rosemary [conoc.] | 0,5–1,5 m, hojas estrechas | no | 3 (como *Salvia rosmarinus*) | Medio. Verificar. |
| *Lavandula dentata* | cantueso / espígol / toothed lavender [conoc.] | 0,5–1 m, hojas grises dentadas | no | 10 | Medio. Verificar. |
| *Crithmum maritimum* | hinojo marino / fonoll marí / rock samphire [conoc.] | 20–40 cm, carnoso, en roquedo | no | 0 | **Bajo a 70–120 m**: típico del roquedo costero. Verificar. |
| *Osyris lanceolata* | bayón / — / African sumac [conoc.] | arbusto 0,5–2 m | no | 13 | Bajo. Nombres es/en sin verificar. |
| Gramíneas de matorral (p. ej. *Brachypodium retusum*, *Hyparrhenia hirta*) | cañuela, herba / — | tapiz bajo, 0,2–0,8 m [conoc.] | no; EUNIS (snippet) cita "pseudo-steppe with annual grasses" para el LIC/ZEPA | 1 cada una: *Lygeum spartum*, *Macrochloa tenacissima*, *Lagurus ovatus*; *Brachypodium* e *Hyparrhenia*: 0 | Alto en suelo entre matas. Especie sin identificar. |

Rupícolas de la GVA que no pongo en la paleta 3D (sección 4): *Teucrium hifacense*, *Centaurea rouyi*, *Pseudoscabiosa saxatilis*, *Hippocrepis valentina*, *Asperula paui* (GVA `flora-rupicola`). Estado de protección de *Teucrium*, *Centaurea* y *Hippocrepis*: **no verificado hoy** (el encargo los llama protegidos o endémicos).

Nota de hábitat: `silene-biology` (verificado) sitúa *Silene hifacensis* en fisuras de acantilado entre 60 y 385 m. Todo el tramo piloto cae en esa franja. Por eso no debe usarse la máscara de cortados para colocar vegetación rupícola.

## 2. Abundancia en iNaturalist

Caja: lat 38,636–38,640, lon 0,0725–0,0760 (≈ 0,44 × 0,30 km). Incluye el tramo, la explanada del centro y la ladera de la Pobla.

Consulta (2026-10-11, hecha por el responsable técnico: `api.inaturalist.org` solo tiene IPv4 y se alcanzó por el relé NAT64 del proyecto, `curl --resolve`):

```
https://api.inaturalist.org/v1/observations/species_counts?swlat=38.636&swlng=0.0725&nelat=38.640&nelng=0.0760&quality_grade=research&iconic_taxa=Plantae&per_page=100&locale=es
```

Resultado: `total_results` = 79 especies. Las de más observaciones:

| Obs. | Especie | Nombre (iNat, es) | Nota para la paleta 3D |
|---|---|---|---|
| 16 | *Pistacia lentiscus* | lentisco | Arbusto denso; candidato principal de matorral alto |
| 13 | *Osyris lanceolata* | bayón | Arbusto; antes "bajo", sube en prioridad |
| 10 | *Lavandula dentata* | cantueso | Mata gris |
| 10 | *Drimia maritima* | cebolla albarrana | Bulbo; vara floral en otoño. No estaba en la lista de partida |
| 7 | *Asphodelus fistulosus* | gamoncillo | Herbácea |
| 6 | *Silene secundiflora* | — | Herbácea anual; **no** es *S. hifacensis* |
| 5 | *Chamaerops humilis* | palmito | Forma reconocible |
| 5 | *Arisarum vulgare*, *Soda oppositifolia* | — | Pequeñas |
| 4 | *Erica multiflora*, *Lonicera implexa*, *Lobularia maritima* | brezo, madreselva, — | Matorral bajo y trepadora |
| 3 | *Pinus halepensis* | pino de Alepo | Árbol; pocas observaciones pero alto peso visual |
| 3 | *Ceratonia siliqua* | algarrobo | Árbol; no estaba en la lista de partida |
| 3 | *Ephedra fragilis*, *Salvia rosmarinus* | efedra, romero | — |
| 3 | *Aeonium arboreum*, *Solandra maxima* | — | **Ornamentales** (jardín junto al centro); no van en la ladera |
| 2 | *Olea europaea*, *Cistus albidus*, *Foeniculum vulgare* | olivo, jara blanca, hinojo | — |
| 1 | *Agave americana*, *Opuntia ficus-indica*, *Iris × germanica* | — | Introducidas u ornamentales |

Cómo leerlo:
- Un recuento de observaciones mide lo que la gente fotografía (flores, rarezas), no cuánto suelo cubre cada planta. Un pino con 3 observaciones puede dominar la vista más que una herbácea con 10.
- **Sabina (0) e hinojo marino (0)** no aparecen en la caja. La sabina está en la lista de la GVA (`flora-rupicola`) pero probablemente más arriba, en roquedo. Se quita de la paleta del tramo piloto salvo que las fotos de referencia la muestren.
- iNaturalist **oculta las coordenadas de los taxones amenazados**. Que *Silene hifacensis* u otras protegidas no salgan aquí no dice nada de su presencia; y este proyecto no busca ni usa su localización (sección 4).
- La caja incluye jardines junto al centro: las ornamentales se excluyen de la ladera.
- GBIF no se consultó (iNaturalist cubre la pregunta para este tramo).

## 3. Modelos 3D (CC0 preferido)

Triángulos contados en el glTF 1k (accessors; `polycount` de la API es de la versión 8K y difiere: p. ej. `shrub_02` 52 317 frente a 27 254). Tamaños: total glTF 1k incluido texturas, desde `api.polyhaven.com/files/<id>`.

| Uso | Candidato | Licencia | Tamaño 1k | Triángulos | Parecido a la especie | LOD / impostor (propuesta) |
|---|---|---|---|---|---|---|
| Pino | `pine_tree_01` | CC0 | 958,1 MB | 17 182 252 | **Genérico**: "tall, slender pine". Un pino carrasco es irregular, a menudo multitronco. | Decimar en pipeline a ≤ 8 k (LOD0), ≤ 1,5 k (LOD1), tarjeta a > 60 m. Sin medir en móvil. |
| Pino (alternativa) | `pine_sapling_small` | CC0 | 21,9 MB | 398 144 | Joven; no representa un árbol adulto | Decimar a ≤ 8 k |
| Pino (sin descarga) | procedural (tronco + nubes de acículas en tarjetas) | — | 0 | — | Menor realismo, cero coste de licencia | Tarjeta cruzada |
| **Pino (recomendado)** | procedural en pipeline (tronco y ramas irregulares, multitronco posible) + tarjetas de acículas con las **texturas** de `pine_tree_01`: `twig_diff`, `twig_alpha`, `twig_nor_gl`, `twig_arm` y `bark_diff`, `bark_nor_gl`, `bark_arm` (JPG 1k) | CC0 | **4,52 MB** (7 JPG; sin el `.bin` de 948,8 MB) | lo que fije el generador (objetivo ≤ 8 k LOD0) | La forma la decide el generador, así que puede imitar la copa abierta e irregular del pino carrasco; textura real de acícula. Forma sin validar contra fotos | Tarjeta a distancia |
| Matorral alto (lentisco) | `shrub_04` | CC0 | 1,90 MB | 27 327 | Aproximado: hojas brillantes, tallos leñosos | Un LOD + tarjeta |
| Matorral bajo (romero) | `shrub_02` | CC0 | 1,96 MB | 27 254 | Aproximado: hojas estrechas, cubre el suelo. No es lavanda. | Un LOD + tarjeta |
| Matorral pequeño (opcional) | `shrub_03` | CC0 | 1,62 MB | 8 287 | Débil: hojas ovaladas pareadas | Un LOD |
| Gramínea | `grass_medium_02` | CC0 | 0,79 MB | 7 842 | Genérica | Tarjeta de haz de hojas |
| Palmito, sabina, efedra, hinojo, cantueso | ninguno CC0 verificado | — | 0 | — | — | Procedural: palmito = grupo de 6–10 tarjetas alfa de hoja palmeada; resto = tarjetas cruzadas con textura generada en código |
| Revisión (no descargar aún) | Quaternius **Stylized Nature MegaKit Standard** | CC0 1.0 (Godot Store) | 104,09 MB zip | sin dato | Store: "40 trees, 35 plants and flowers, 27 rocks, grass, bushes". Sin lista de modelos; puede no tener palmito ni pino concretos | Revisar contenido antes de decidir |
| Revisión (no descargar aún) | Kenney **Nature Kit** | CC0 (OpenGameArt, snippet) | 10,5 MB zip | sin dato | "over 330 objects"; contenido de plantas no listado | Revisar contenido |

Lo que no es: `poly.pizza` lista palmeras y pinos de Quaternius y de Google, pero la página no muestra licencia por modelo; no los uso sin comprobación por modelo. Sketchfab: no (licencias por modelo; no verificable aquí).

Honesto sobre el parecido: un pino de Poly Haven no es un pino carrasco, y un shrub_02 no es un romero. Son sustitutos de volumen y color. La identificación visual la hace la ficha, no el modelo.

Presupuesto de dibujo (B0, ≤ 40 llamadas): una `InstancedMesh` por especie y nivel → 6 especies × 2 LOD + tarjetas ≈ 13–20 llamadas. Coste en móvil: **sin medir**; el umbral de 6 ms de `docs/specs/002-fase-b-paralelizacion.md` se calibra con la primera medición (A7).

## 4. Protegidas: cómo mostrarlas sin ubicarlas

- *Silene hifacensis*, *Teucrium hifacense*, *Centaurea rouyi*, *Hippocrepis valentina*: **ninguna instancia 3D**, ninguna entrada con posición en `vegetation/pilot.json`.
- Propuesta: galería "Flora del parque" en la interfaz, con una tarjeta por especie (nombre es/va/en, texto de `facts.json`, foto con licencia que permita uso en la app). La tarjeta no tiene mapa ni flecha. Para la silene, la tarjeta incluye la nota de `silene-history` ("por conservación no se mostrará la ubicación de plantas reales").
- Guardia técnica (test-engineer): un test falla si `pilot.json` contiene una especie de la lista protegida o si una instancia rupícola cae en la franja de fisuras del hábitat de la silene.
- Ninguna máscara de cortado se usa para plantas rupícolas en el piloto.

## 5. Lista de descargas para aprobación (nada descargado)

Pipeline only: estos ficheros no van al repositorio ni a `app/`; solo entra la salida optimizada.

| # | Fichero(s) | Host | Bytes | Licencia | Atribución (cortesía) | Especie / uso |
|---|---|---|---|---|---|---|
| 1A | `pine_tree_01` glTF 1k (+ includes) | dl.polyhaven.org (`api.polyhaven.com/files/pine_tree_01`) | 958 087 934 | CC0 | "Modelos: Rob Tuytel y Rico Cilliers, Poly Haven (polyhaven.com), CC0" | Pino (decimado) |
| 1C (**recomendado**) | 7 texturas JPG 1k de `pine_tree_01` (twig diff/alpha/nor_gl/arm; bark diff/nor_gl/arm) | dl.polyhaven.org | 4 522 252 | CC0 | "Texturas: Rob Tuytel y Rico Cilliers, Poly Haven, CC0" | Pino procedural |
| 1B | `pine_sapling_small` glTF 1k | dl.polyhaven.org | 21 879 897 | CC0 | "Modelos: Rob Tuytel y Rico Cilliers, Poly Haven, CC0" | Pino joven (alternativa a 1A) |
| 2 | `shrub_04` glTF 1k | dl.polyhaven.org | 1 904 632 | CC0 | "Modelos: Rico Cilliers, Poly Haven, CC0" | Lentisco aprox. |
| 3 | `shrub_02` glTF 1k | dl.polyhaven.org | 1 958 342 | CC0 | "Modelos: Rico Cilliers, Poly Haven, CC0" | Romero/cantueso aprox. |
| 4 | `grass_medium_02` glTF 1k | dl.polyhaven.org | 792 610 | CC0 | "Modelos: Rico Cilliers, Poly Haven, CC0" | Gramíneas |
| 5 (opc.) | `shrub_03` glTF 1k | dl.polyhaven.org | 1 621 497 | CC0 | "Modelos: Rico Cilliers, Poly Haven, CC0" | Matorral pequeño |
| 6 (solo revisión) | Quaternius Stylized Nature MegaKit Standard (zip) | itch.io / Quaternius | 104 090 000 | CC0 1.0 (según Godot Store); **verificar el LICENSE del zip** | "Quaternius (quaternius.com), CC0" | Revisar palmito/pino |
| 7 (solo revisión) | Kenney Nature Kit (zip) | kenney.nl / OpenGameArt | ~10 500 000 | CC0 (OpenGameArt) | "Kenney (kenney.nl), CC0" | Revisar |

Totales (MB = 10^6 bytes):
- Opción recomendada con pino decimado: 1A + 2 + 3 + 4 = **962,7 MB**.
- Opción ligera: 1B + 2 + 3 + 4 = **26,5 MB**; con la opcional 5, **28,1 MB**.
- **Opción recomendada por el responsable técnico** (añadida tras la entrega): 1C + 2 + 3 + 4 = **9,18 MB**; con la opcional 5, **10,80 MB**. El `.bin` de `pine_tree_01` pesa 948,8 MB porque modela cada acícula (17,2 M triángulos): decimarlo cuesta casi 1 GB de descarga para obtener una forma de pino genérico. Comprobado en `api.polyhaven.com/files/pine_tree_01` el 2026-10-11: el modelo publica un mapa `twig_alpha`, que es lo que necesitan las tarjetas.
- Revisión 6 y 7 (solo si se aprueba revisarlas): +114,6 MB.

Estos son bytes de descarga para el pipeline. Lo que llega al móvil es la salida decimada y comprimida (meshopt, KTX2); su tamaño no está medido y debe medirse antes de fijar cifras.

## 6. Conflictos y no verificado

- **Licencia Quaternius:** ADR 0008 dice que `quaternius.com/license.html` muestra QAL v1.0 (actualizada 2026-08-28). Hoy no pude abrir esa página (WebFetch: error; búsqueda sin resultados). La Godot Store dice CC0 para el MegaKit (actualizada 2026-06-09). El `LICENSE` del zip decide. Si el pack es QAL, ADR 0008 **solo cubre al caminante**; ADR 0007 solo admite CC0 y CC BY, así que haría falta enmienda antes de usarlo en vegetación.
- **Atribución de Poly Haven:** CC0, no obligatoria; las cadenas de cortesía son sugerencias. La página de licencia (polyhaven.com/license) dice CC0 con texto de "public domain".
- **Abundancia, GVA y nombres valencianos:** no verificados hoy (ver sección 1 y 2).
- **Protección de *Teucrium*, *Centaurea*, *Hippocrepis*:** no verificada hoy.
- **Calidad de la página `vegetacion-rupicola`:** la copia IA es de 2025-09-09; la página en vivo puede haber cambiado. Confirmar antes de publicar.

## Fuentes

- Repositorio: `content/facts.json` (`flora-rupicola`, `fauna-other`, `silene-*`, checked 2026-10-10); `content/sources.json` (`gva-vegetacion-rupicola`, `gva-presentacion`, `gva-fauna`, copias IA de 2025-09-09, 2026-07-12, 2026-04-11); `docs/adr/0007-licensing.md`; `docs/adr/0008-quaternius-licence-for-the-hiker.md` (2026-10-11); `docs/specs/001-penyal-ifac-3d/assets.md`; `docs/specs/002-fase-b-paralelizacion.md`; `docs/research/002-verificacion.md` (línea 39, paradas oficiales).
- spain.info, parque natural (leído 2026-10-11, sin fecha en la página): https://www.spain.info/es/naturaleza/parque-natural-penon-ifach/
- Poly Haven API, lista de modelos (2026-10-11): https://api.polyhaven.com/assets?t=models; info y ficheros por id: https://api.polyhaven.com/info/<id> y https://api.polyhaven.com/files/<id> (ids: `pine_tree_01`, `pine_sapling_small`, `shrub_02`, `shrub_03`, `shrub_04`, `grass_medium_02`; glTF 1k: https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/<id>/<id>_1k.gltf).
- Poly Haven, licencia (2026-10-11): https://polyhaven.com/license
- Quaternius Stylized Nature MegaKit, Godot Store (página actualizada 2026-06-09, leída 2026-10-11): https://store.godotengine.org/asset/quaternius/stylized-nature-megakit/
- Stylized Nature MegaKit, OpenGameArt (snippet de búsqueda): https://opengameart.org/content/stylized-nature-megakit
- Kenney Nature Kit, OpenGameArt (snippet de búsqueda; 10,5 MB): https://opengameart.org/content/nature-kit
- Quaternius, licencia (no accesible hoy): https://quaternius.com/license.html
- poly.pizza, búsqueda "pine" (licencia no mostrada, 2026-10-11): https://poly.pizza/search/pine
- EUNIS, ES5211009 (solo snippet de búsqueda; fetch fallido): https://eunis.eea.europa.eu/sites/ES5211009
- iNaturalist API, `species_counts` (consultada 2026-10-11 vía NAT64): https://api.inaturalist.org/v1/observations/species_counts

Sin acceso hoy (no verificado): GVA en vivo, Internet Archive, GBIF, Quaternius, Kenney.

# 006 — Assets reales para H1: rocas, barcos, madera, metal, muros y medidas típicas

- Fecha: 12/10/2026. Autor: agente de investigación (tarea H1-R1 de `docs/specs/006-h1-paseo-con-sentido/plan.md`).
- Estado: **investigación; no se ha descargado ningún fichero** y solo se ha escrito este documento. Las descargas salen de la lista del final y necesitan aprobación.
- Cómo se comprobó:
  - **Licencias:** leídas en la página oficial de cada fuente (URL en cada tabla).
  - **Triángulos, tamaños y bytes:** de `api.polyhaven.com` (`/info`, `/files`), `ambientcg.com/api/v2` y `api.sketchfab.com/v3`, leídos con WebFetch.
  - **Aspecto:** miniaturas vistas en el navegador, sin guardarlas.
  - **Colores:** medianas de píxeles de nuestras fotos de referencia (`data/manual/fotos-referencia/commons/`) y de las texturas ya descargadas. Son **orientativos**: las fotos son JPEG de un día nublado, sin calibrar.
- Marcas de fiabilidad: **[P]** página abierta y leída; **[B]** solo fragmento de buscador, la página no se abrió o su PDF no es legible por máquina (no usar como dato firme); **[E]** estimación mía; **[M]** medido por nosotros.
- Reglas del proyecto que aplican (`CLAUDE.md`, ADR 0007): solo CC0 y CC BY; nada de Quixel Megascans (no es CC0), de Mixamo ni de texturas CC BY-SA. No se registra ninguna posición de *Silene hifacensis*.

## Resumen (la respuesta primero)

1. **Rocas: no existe ningún modelo escaneado CC0 de caliza clara y kárstica listo para usar.** Los mejores son de Poly Haven (CC0): `boulder_01`, `rock_moss_set_01` y `rock_moss_set_02`. Sirven **por la forma**, tras decimarlos, y **no por su albedo** (marrón oscuro con óxido o verde de musgo). El material debe ser el de caliza que ya tenemos, `marble_cliff_05`, cuya mediana de color (#989187) casi coincide con la de la pared de la foto 28 (#948E88).
   - Decimar de forma determinista funciona: `gltf-transform weld` + `simplify` dos veces dio el mismo SHA-256 (probado hoy en local).
   - **Recomendación: usar con decimación.**
2. **Barcos: no hay modelos realistas, ligeros y con licencia libre para el puerto de Calp.** Poly Haven solo tiene 4 barcos de vela históricos (69–184 mil triángulos). Sketchfab CC0 solo tiene piezas de museo. Los CC BY son *low poly* estilizados, y los de Kenney o Quaternius también.
   - Hay un único velero moderno realista y libre, CC BY 4.0 (Ocean Autonomy Cluster, NTNU), pero no declara el origen del modelo.
   - **Recomendación: generador procedural** con eslora y manga medidas en la ortofoto. La tabla 3.3 da las proporciones con fuente; la altura de mástil sale de la fuente (1,53–1,55 × eslora de casco) y las alturas de francobordo y cabina **no tienen fuente publicada** (se miden en fotos).
3. **Texturas (1k, CC0):**
   - **Rollizo:** `beam_wall_01` (Rob Tuytel), 440 KB.
   - **Tarima de pantalán:** `brown_planks_03`, 1,21 MB.
   - **Muelle de hormigón:** `concrete_floor_worn_001`, 383 KB.
   - **Metal galvanizado:** no hay una textura de chapa galvanizada limpia en Poly Haven ni en ambientCG. El mejor sustituto es `Metal032` de ambientCG (zip de 3,65 MB). Hay que mirarlo al bajarlo.
   - **Casco blanco y teca:** no hacen falta con barcos procedurales.
4. **Muros de piedra seca:** en la foto 1 los muros del centro son de bloques cuadrados ocres tomados en seco. `stacked_stone_wall` tiene el matiz de color correcto pero está hecha de lajas finas y horizontales. **`rock_wall_11` (Poly Haven, CC0, 2,58 MB en 1k) se parece más en la estructura.** Se decide con una comparación lado a lado a 5 m y a 20 m.
5. **Medidas típicas:** sección 6, con fuente y fiabilidad.
   - **Verificadas en la fuente:** fuente de agua, grifo a 0,80–0,90 m (Orden TMA/851/2021, art. 27); torno trípode, 0,98 m de alto y 0,60 m de paso (ficha de Dahua, ejes sin rotular).
   - **Con fragmento de buscador:** pantalán (franco bordo de 0,45–0,50 m según fabricantes, anchos de 1,7 a 2,6 m).
   - **Sin cifra oficial:** rollizo (los datos de 004 ya recogidos siguen valiendo).
6. **Lista de descargas: 17.913.914 bytes (17,1 MiB) la parte recomendada** y 28.668.235 bytes (27,3 MiB) la opcional (al final).

## 1. Licencias verificadas

| Fuente | Licencia | Página leída (12/10/2026) | Atribución |
|---|---|---|---|
| Poly Haven (texturas, modelos, HDRI) | CC0 1.0. El texto de la web, las miniaturas y las renderizaciones **no** son CC0 | https://polyhaven.com/license | No exigida. Se cita de cortesía, como ya hacemos en `data/catalog.toml` |
| ambientCG (materiales) | CC0 1.0 | https://docs.ambientcg.com/license/ | No exigida. Sugiere: "Created using <asset> from ambientCG.com, licensed under the Creative Commons CC0 1.0 Universal License" |
| ambientCG, tipo `3DModel` | CC0 1.0, pero **solo hay comida, un palo y un tocón** (3D Apple, Avocado, Bread, Cake, Cookie, Cucumber, Kiwi, Lemon, Mango, Melon, Pastry, Pear, Stick, Tree Stump). Ni rocas ni barcos | https://ambientcg.com/list?type=3d-model | — |
| Sketchfab | **Por modelo.** La API da el campo `license` de cada uno (CC0 o CC BY 4.0). Descargar exige sesión de Sketchfab (lo habitual; no se comprobó desde aquí) y la debe abrir el usuario | CC0: https://creativecommons.org/publicdomain/zero/1.0/ · CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ | CC BY: autor, título, URL del modelo y licencia |
| Kenney (Watercraft Kit y otros) | CC0 | https://kenney.nl/support | No exigida |
| Ocean Autonomy Cluster / NTNU (velero) | CC BY 4.0 | https://www.itk.ntnu.no/milliampere-data/gemini/3d_models/Sailboat/ | Autor "Ocean Autonomy Cluster", https://oceanautonomy.no/, fuente de datos y licencia (ver 3.2) |
| Smithsonian 3D | CC0 solo si cada objeto lo marca | https://3d.si.edu/collections/openaccesshighlights | Sin hallazgos útiles (ver 2.2 y 3.2) |
| ShareTextures (Rock 9, Rock 10…) | Etiquetados CC0, pero la página está tras un muro de consentimiento y no da triángulos, formatos ni tamaños | https://www.sharetextures.com/models/nature/rock_10 | No verificable. **Descartado** |
| Quixel Megascans | No es CC0 | — | **Excluido** (regla del proyecto) |

## 2. Rocas

### 2.1 Cómo es la roca del Peñón (referencia)

- Las fotos 17 y 28 (`003-fotos-referencia.md`) muestran:
  - pared de caliza **gris muy clara casi neutra**;
  - estrías verticales de disolución (acanaladuras);
  - fisuras y alvéolos;
  - manchas de liquen amarillo anaranjado (foto 28, bloque de la derecha).
- **Medianas de color [M], indicativas:**

| Muestra | Color | Matiz / saturación / valor |
|---|---|---|
| Pared de la foto 28 (mitad más clara del recorte) | #948E88 | 30° / 8 % / 58 % |
| Pared de la foto 17 (cuarto más claro) | #A1A2A3 | casi neutro |
| `marble_cliff_05` 1k (ya en `data/raw`, usada en el terreno) | #989187 | 35° / 11 % / 60 % |
| Lajas del firme de la foto 17 | #CABFB5 | 26° / 12 % / 79 % |
| Bloque con liquen de la foto 28 | #847B6E | — |

- En la misma foto 17 la roca es entre un 15 y un 23 % más oscura que las lajas del firme (#CABFB5). Aplicando esa proporción al color objetivo del firme del plan (#D5CAB8) saldría un albedo de #A59D8F a #B4ABA0, y `marble_cliff_05` (#989187) queda un 7–15 % por debajo, con el matiz correcto (35° frente a 30°). Un ajuste de brillo en el material lo cubre.
- **Conclusión:** para el albedo de las rocas no hace falta una textura nueva.

### 2.2 Candidatos evaluados

**Poly Haven** (todo CC0; autores según `api.polyhaven.com/info`; "tris" = `polycount`; tamaños en mm convertidos a m, comprobado con la página de `boulder_01`: "1,8 m de ancho"). **Ninguno trae ficheros LOD**: la etiqueta `lods` existe pero no hay entradas `lod` en `gltf`, `fbx` ni `blend`.

| Id | Autor | Tris | Tamaño (m) | Color (miniatura) | Bytes del paquete glTF 1k | Veredicto |
|---|---|---|---|---|---|---|
| `boulder_01` | Rico Cilliers | 123.976 | 1,27 × 1,83 × 1,00 | Marrón oscuro y gris con vetas de óxido; angular, fracturado | 5.771.986 | **Usar con decimación** |
| `rock_moss_set_01` | Kless Gyzen | 63.127 (≈ 5 piedras) | conjunto de 8,0 × 6,9 × 1,8 | Pardo con musgo verde; bloques angulares | 1.937.065 | **Usar la forma**, no el albedo |
| `rock_moss_set_02` | Kless Gyzen | 57.647 (≈ 5 piedras) | conjunto de 8,3 × 3,4 × 1,4 | Igual | 1.942.240 | **Usar la forma** |
| `coast_rocks_05` | Rob Tuytel | 1.446.981 | 3,04 × 2,82 × 1,00 | Ocre/arena claro y poroso, algo de vegetación; afloramiento bajo | 25.281.108 | **Opcional** (para lajas bajas). Pesado de bajar |
| `sand_rocks_small_01` | Rob Tuytel, Rico Cilliers | 1.386.500 | 4,6 × 3,9 × 0,5 | Beige claro, pero **cantos redondeados sobre arena** | — | No: no es karst angular y pesa 1,4 M |
| `rock_07`, `rock_09`, `stone_01` | J. van Heerden (las dos primeras); D. Barresi y R. Cilliers | 27.830 / 23.280 / 71.916 | 17×32×14 cm / 7×14×3 cm / 15×9×7 cm | Marrón oscuro | — | No: tamaño de mano |
| `rock_face_01`, `rock_face_02`, `mountainside` | D. Barresi (+ R. Cilliers) | 20–288 mil | 3,5–10,5 | Estratos pardos y grises, con musgo | — | No: paredes estratificadas, no caliza kárstica |
| `coast_land_rocks_02..04`, `coast_line_01/02`, `coast_rocks_01..03`, `coastal_cliff_04` | R. Tuytel (+ R. Cilliers) | 1,0–2,9 M | 9–87 | Escenas de costa | — | No: escenas enteras, 1–3 M de triángulos |

Fuentes: lista https://api.polyhaven.com/assets?t=models&c=rocks · `info/boulder_01` · `files/boulder_01` · `files/coast_rocks_05` · `files/rock_moss_set_01` · `files/rock_moss_set_02` · miniaturas `https://cdn.polyhaven.com/asset_img/primary/<id>.png`.

**Otras fuentes**

| Candidato | Licencia | Dato | Veredicto |
|---|---|---|---|
| Sketchfab CC0 con "limestone" y ≤ 80 mil caras | CC0 | Solo fósiles de la *Digital Atlas of Ancient Life*, esculturas de museos y hornos de cal de Galway. **Ninguna roca** | No hay |
| *Cliff Rock Boulder Field*, Pers Scans (Sketchfab) | CC BY 4.0 | 122.310 caras, 4 texturas de 8K, Pirineo catalán (Pedraforca). Bloques angulares gris claro; **es una escena, no rocas sueltas**. https://sketchfab.com/3d-models/cliff-rock-boulder-field-d1f2ce6f71aa4c19adbdc541cc888194 | Alternativa B. Requiere sesión de Sketchfab y recortar bloques. No en la primera tanda |
| *Limestone outcrop*, Artyom Tarakanov (Sketchfab) | CC BY 4.0 | 299.999 caras, talud de caliza con escombros (Leningrado). https://sketchfab.com/3d-models/limestone-outcrop-c2cbda05700a473f97c00bbf5cc2a57d | No: escena, 300 mil caras |
| *Rock Cliff (Tirán – Moaña)*, A. González Rivas (Sketchfab) | CC BY 4.0 | 47.835 caras, costa gallega | No: otra geología y otro color |
| Muestras de caliza de universidad (varias, 350 mil–1,1 M caras) | CC BY | Muestras geológicas de mano | No |
| ambientCG 3D | CC0 | No hay rocas (ver tabla 1) | No hay |
| Smithsonian 3D | CC0 solo si se marca | ≈ 2.200 objetos en 2020, de museo (no rocas de afloramiento). Búsqueda sin resultados | No hay |
| Kenney Nature Kit, Quaternius | CC0 (Kenney); Quaternius, ver ADR 0008 | Estilizados, poca fidelidad | No |

### 2.3 Recomendación para H1-B4

1. **Geometría:** `boulder_01` (bloque grande, 1,3–1,8 m; se puede escalar de 0,5 a 3,5 m) más las 10 piedras de `rock_moss_set_01` y `_02` (tamaños por confirmar al bajar: cada conjunto ocupa unos 8 × 7 m). Son unas 11 formas base, que con giro, espejo y escala no uniforme de ±20 % bastan para el instanciado.
2. **Decimación determinista:** hay dos vías.
   - **`gltf-transform weld` + `simplify`** (`@gltf-transform/cli` 4.5.1, ya fijado; usa `meshoptimizer` 1.x). **Probado el 12/10/2026 sobre `spike.glb`: dos ejecuciones dan el mismo SHA-256** (`95dd8435…04d3`, ratio 0,25, error 0,01). Es la vía preferida porque ya está en el repo.
   - `Decimate` (Collapse) de `bpy` 5.2.2, si hace falta controlar bordes o UV. Hay que repetir la prueba de SHA-256 antes de fiarse.
3. **Triángulos propuestos:** LOD0 ≈ 2.000–2.500, LOD1 ≈ 400–600, y a más de ~60 m un cuadrado o la propia instancia con un material plano.
   - Con 80 mil triángulos en pantalla (fila `rocks` del plan §4): unas 15 rocas en LOD0 (≈ 35 mil) + unas 60 en LOD1 (≈ 30 mil) + el resto.
   - A 5 m, una roca de 1,5 m mide ≈ 250 px (cámara de 65° y 1080 px), así que 2.000 triángulos bastan.
4. **Material:** no usar el albedo de los escaneos. Opciones:
   - (a) **reusar `marble_cliff_05` (diff, nor_gl, arm) en triplanar, que el terreno ya carga: 0 MiB nuevos** en la fila `rocks`;
   - (b) bakear una normal desde el modelo de alto poligonaje (Cycles; hay que probar el determinismo).
   - Recomiendo (a) primero y (b) solo si la forma se ve plana.
5. **Se rotula como aproximación** en `CREDITS.md`: las rocas son sustitutas de forma; no son las del Peñón.

## 3. Barcos

### 3.1 Qué hay que representar y a qué tamaño se ve

- La ortofoto 2024 da posición, rumbo, eslora y manga de cientos de barcos (plan §1). En la foto 13 se ven también el puerto pesquero con la lonja, un barco amarillo y naranja junto al muelle que parece de pasaje [E] y muchos veleros y yates en los pantalanes.
- **Tamaño en pantalla** (cámara de 65° en vertical, `app/src/main.ts:111`; focal = alto en px / (2·tan 32,5°)):

| Barco | Eslora | Distancia | Largo en pantalla a 1080 px | A 720 px |
|---|---|---|---|---|
| Pesquero | 24 m | 90 m | ≈ 226 px | ≈ 151 px |
| Velero | 12 m | 150 m | ≈ 68 px | ≈ 45 px |
| Llaüt | 7 m | 100 m | ≈ 59 px | ≈ 40 px |
| Yate | 20 m | 300 m | ≈ 56 px | ≈ 38 px |
| Bote | 5 m | 300 m | ≈ 14 px | ≈ 9 px |

- Con esas longitudes, 100–400 triángulos por barco bastan. Un modelo de 5–20 mil triángulos sería un derroche con 264 amarres.

### 3.2 Modelos evaluados

| Candidato | Licencia | Triángulos / tamaño | Adecuación |
|---|---|---|---|
| Poly Haven `dutch_ship_large_01/02`, `dutch_ship_medium`, `ship_pinnace` | CC0 | 69.162–183.837 tris; 4K | **No**: barcos de vela históricos (holandeses y una pinaza colonial), de madera envejecida |
| Sketchfab CC0: *"Venus", a Shetland fourareen* (Scottish Maritime Museum) | CC0 | 19.895–49.996 caras | No: barca tradicional de Shetland, no mediterránea |
| Sketchfab CC BY (estilizados): *Low poly Greek Fishing Boat* (Muyaya Concept, 4.890), *Trawler* (JasperTobias, 5.253, plano), *fishing trawler 19m* (Aryan, 3.017, sin texturas), *Yacht* (Sergei, 8.534), *Docked venetian boat* (Blue Scans, escaneo, 18.746 y 6 texturas) | CC BY 4.0 | 3–19 mil caras | **No**: estilizados y de proporciones libres. Hay que escalarlos a la eslora y manga medidas |
| **Velero *familiecruise seilbåt*** (Ocean Autonomy Cluster, NTNU) | CC BY 4.0 | `seilbaat.obj` ≈ 5,5 MB, textura `Seilbaat_visual.png` ≈ 5,1 MB; **triángulos no declarados** | Velero de crucero moderno, casco blanco, cubierta de teca, mayor y génova con rayas. **Opcional.** El README no dice de dónde sale el modelo original: riesgo de procedencia |
| Kenney Watercraft Kit | CC0 | Un zip; la página no detalla modelos ni formatos | Estilizado. No |
| Poly Pizza / Quaternius / Poly by Google | Por modelo (no se vio en la página) | — | Estilizados. No |
| Smithsonian 3D, NOAA, NASA, USGS | — | Nada útil: los modelos de buques de NOAA son comerciales y los de NASA son naves espaciales | No hay |

Fuentes: https://api.polyhaven.com/assets?t=models&c=ships · https://api.sketchfab.com/v3/search?type=models&q=fishing%20boat&license=cc0 · https://api.sketchfab.com/v3/models/315a83fe28014d2f890acbe16f04a26f · https://www.itk.ntnu.no/milliampere-data/gemini/3d_models/Sailboat/ · https://kenney.nl/assets/watercraft-kit.

**Atribución, si se usara el velero de NTNU** (texto propuesto): "This work uses data from Ocean Autonomy Cluster (https://oceanautonomy.no/), https://www.itk.ntnu.no/milliampere-data/gemini/, licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)".

### 3.3 Proporciones con fuente (para el generador procedural)

| Clase | Referencia | Eslora (m) | Manga (m) | Eslora/manga | Otros datos | Fuente (fiabilidad) |
|---|---|---|---|---|---|---|
| **Llaüt** (barca de artes menores) | Media de los llaüts | 8 | 3 | 2,7 | De madera, cubierta redondeada, vela cangreja o latina, remos y motor | Balearia, https://www.balearia.com/ca/blog/los-llauts-tradicion-marinera-de-formentera **[B]** |
| | *S'Agaró*, histórico restaurado | 12 | 3,6 | 3,3 | Calado 1,30 m | https://www.ultimahora.es/noticias/sociedad/2021/07/17/1284791/llaut-agaro-excursion-mas-autentica.html **[B]** |
| | Anuncio de un mallorquín | 6,6 | 2,4 | 2,75 | — | https://www.yachtall.com/en/boat/llauet-mallorquin-s312449 **[B]** |
| | Definición | < 10 | — | — | Nombre del tipo "llagut" | https://ca.wikipedia.org/wiki/Llagut **[P]** |
| **Pesquero de 21–27 m** (Calp) | HERMANOS CAPARROS (2000) | 21 | 6 | 3,5 | Escalas en Calp; arte no declarado | https://maritimeoptima.com/public/vessels/pages/imo:8687830/mmsi:224113720/HERMANOS_CAPARROS.html **[P]** (datos AIS, redondeados a 1 m) |
| | NUEVO TACONEO (1998) | 24 | 6 | 4,0 | Ídem | https://maritimeoptima.com/public/vessels/pages/imo:2847828/mmsi:224134470/NUEVO_TACONEO.html **[P]** |
| | CANTALAR | 27,5 | — | — | 105 GT; escala en Calp (mayo 2026) | Resultado de buscador **[B]** |
| **Barco de pasaje** | NOU CALPE QUATRE (Baleària, 127 GT) | 24–27 | 6–7 | ≈ 3,9 | La ficha se contradice (79 ft × 20 ft frente a 27 × 7 m) | https://ports.marinelink.com/vessels/vessel/224205360 **[P]** |
| **Lancha pequeña** | Jeanneau Cap Camarat 6.5 WA | 6,59 (casco 6,06) | 2,48 | 2,4–2,7 | — | https://www.jeanneau.com/boats/powerboat/22-cap-camarat/218-cap-camarat-6-5-wa **[B]** |
| **Velero de 10–12 m** | Jeanneau Sun Odyssey 349 | 9,97 (casco); LOA 10,34 | 3,44 | 2,90 | Altura de mástil sobre el agua 15,45 m = **1,55 × eslora de casco** | LOA y manga: https://en.wikipedia.org/wiki/Jeanneau_Sun_Odyssey_349 **[P]**. Eslora de casco (9,97 m, boat-specs.com) y altura de mástil (15,45 m): https://www.hiswa.nl/en/boats-for-sale/new-boats/75565/jeanneau-sun-odyssey-349-vaste-kiel **[B]** |
| | Beneteau Oceanis 40.1 | 11,99 (casco) | 4,18 | 2,87 | 18,33 m = **1,53 × eslora de casco** | https://www.samboat.com/model/beneteau-oceanis-40-1 **[B]** |
| **Yate a motor de 15–25 m** | Azimut 55 (2010–2014) | 17,51 | 4,75 | 3,7 | — | https://itboat.com/en/model/6329-azimut-55-evolution-o9Ab2/for-sale **[B]** |
| | Azimut 55 Gen 3 | 16,90 | 4,95 | 3,4 | — | https://www.yachtbuyer.com/en-us/yachts/compare/azimut-55-gen3-vs-sessa-marine-fly54-ab9eb90 **[B]** |
| | Sunseeker Manhattan 68 | 21,21 | 5,26 | 4,0 | — | https://sunseeker.com/zh/range/manhattan-68 **[B]** |

- **Contexto de la flota de Calp:** el Ayuntamiento da 22 barcas y unas 160 personas (https://www.calpe.es/sites/default/files/2019-11/archivo531.pdf **[B]**, documento de 2019 o anterior). No encontré el desglose por arte (arrastre, cerco, artes menores) ni un censo con las mangas. El MAPA no abre desde aquí (error de certificado).
- **Lo que **no** encontré con fuente:** francobordo, altura de cabina, altura del puente de un pesquero, ni el reparto de manga a lo largo del casco. En 90–300 m una diferencia de 0,5 m son 1–2 px, así que se pueden **medir en 10–15 fotos de referencia de Commons** de barcos de eslora conocida, y rotular como [E].

### 3.4 Lo que necesita un generador procedural determinista

| Entrada o parámetro | De dónde sale | Estado |
|---|---|---|
| Centro, rumbo, eslora L y manga B | Ortofoto 2024 (H1-B5, detección) | [M] |
| Clase | Regla del plan: bote < 6 m; motor o vela de 6–15 m; yate > 15 m; pesquero junto a la lonja | Plan |
| Comprobación de L/B por clase | Tabla 3.3 (L/B: llaüt 2,7–3,3; velero 2,9; lancha 2,4–2,7; pesquero 3,5–4,0; yate 3,4–4,0) | [B], más la **distribución real medida** en los 30 barcos de la muestra |
| Altura de mástil de un velero | 1,5 × eslora de casco | [P] + [B], dos modelos |
| Francobordo, cabina, proa y popa | Medir en fotos de referencia | [E] |
| Vela o motor | Por forma en la ortofoto, rotulado como aproximado | Plan |

- **Salida:** LOD0 ≤ 400 triángulos (casco por lofting de 8 secciones × 6 puntos, cabina en caja, mástil y dos triángulos de vela), LOD1 ≤ 120, y a más de ~200 m un cuadrilátero de 2 triángulos. Un material plano por clase y colores de vértice; sin texturas por barco (la fila `marina` del plan dispone de 3 MiB de textura).
- **Determinismo:**
  - semilla derivada del hash del id del barco, nunca de `hash()`;
  - orden por id antes de construir;
  - manifiesto con los SHA-256 de la ortofoto y del JSON de detección;
  - `verify-generated`.
- **Pruebas:** caja envolvente igual a L × B ± 1 cm; triángulos ≤ presupuesto; dos exportaciones con el mismo SHA-256.

## 4. Texturas CC0 (1k)

Las de Poly Haven traen `diff` (color sRGB), `nor_gl` (normal OpenGL, la que usa glTF) y `arm` (AO, rugosidad y metal en R, G, B). Los nombres de fichero y los bytes salen de `api.polyhaven.com/files/<id>`. La de ambientCG viene en un zip.

| Uso | Textura | Ficheros 1k (bytes) | Tamaño del azulejo | Evaluación |
|---|---|---|---|---|
| **Rollizo** (postes y travesaños de las talanqueras) | `beam_wall_01` (Rob Tuytel) | `beam_wall_01_diff_1k.jpg` 224.751 · `…_nor_gl_1k.jpg` 120.019 · `…_arm_1k.jpg` 95.017 (total 439.787) | 1 × 1 m. "Vigas redondas apiladas, grano gris envejecido, grietas, nudos y manchas de musgo verde" | **Usar.** Es madera pelada de tronco gris plateado, como los postes de las fotos 17 y 28. Hay que **desaturar el verde** y comprobar el diámetro de las vigas (debería rondar 10–14 cm; **por confirmar al bajarla**) |
| | `rough_wood` (Rob Tuytel), alternativa | `…_diff_1k.jpg` 567.074 · `…_nor_gl_1k.jpg` 790.334 · `…_arm_1k.jpg` 137.749 (total 1.495.157) | 0,5 × 0,5 m | **Opcional.** Madera gris agrietada de cara plana, buena para los travesaños |
| **Metal galvanizado** (torno, postes, barandillas de pantalán) | `Metal032` de **ambientCG** | `Metal032_1K-JPG.zip` 3.650.556 (mapas según la API: color, desplazamiento, normal, rugosidad y metal; los nombres de dentro del zip no se pudieron leer) | — | **Sustituto.** Gris azulado mate con manchas grandes. No hay "galvanizado" en ninguna de las dos bibliotecas. `Metal038` (acero rayado, 5.291.072) es la otra opción. **Mirar al bajar y, si no gusta, usar un material plano gris (#9A9EA0 aprox. [E]) con metal 0,85 y rugosidad 0,45** |
| **Casco blanco, cubierta de teca** | — | — | — | **No hacen falta** con barcos procedurales de color plano |
| **Tarima de pantalán** (las fotos de Joanbanjo 2015 muestran "pantalanes con tarima de madera", `004-recursos-pobla-puerto.md`) | `brown_planks_03` (Rob Tuytel) | `…_diff_1k.jpg` 570.668 · `…_nor_gl_1k.jpg` 516.860 · `…_arm_1k.jpg` 126.038 (total 1.213.566) | 1 × 1 m. Tablas pardo-grises de aspecto costero, con etiqueta "boat" | **Usar.** A 90–125 m casi solo se ve el color |
| **Muelle de hormigón** | `concrete_floor_worn_001` (Dimitrios Savva, Rico Cilliers) | `…_diff_1k.jpg` 118.806 · `…_nor_gl_1k.jpg` 110.906 · `…_arm_1k.jpg` 152.919 (total 382.631) | 3 × 3 m. Losa gris con rayas y desconchones | **Usar** (prioridad baja) |

## 5. Muros de piedra seca (*pedra en sec*)

- **Lo que muestra la foto 1** (centro de visitantes, `003-fotos-referencia.md`): muros de **bloques escuadrados ocres, de unos 15–30 cm [E], sin mortero visible y con ripios pequeños**, en hiladas irregulares. La foto 28 muestra un murete bajo del mismo tipo, con una roca con liquen detrás.
- **Colores [M]** (mediana del recorte entero, juntas y sombras incluidas): muro de la foto 1, #6E5131 (matiz 31°, saturación 55 %). `stacked_stone_wall` 1k, #604530 (matiz 26°, saturación 50 %). Misma familia de matiz y un 12 % más oscura (la exposición de la foto no está calibrada).
- **La diferencia está en la estructura:** `stacked_stone_wall` (Dimitrios Savva, azulejo de 2 × 2 m) son **lajas finas apiladas en capas horizontales**, y los muros de la foto 1 son de bloques casi cuadrados.

| Candidato (Poly Haven, CC0) | Autor | Azulejo | Descripción | Veredicto |
|---|---|---|---|---|
| `stacked_stone_wall` (ya en `data/raw`) | D. Savva | 2,0 × 2,0 m | Lajas pardas en capas | Válida de color; estructura distinta |
| **`rock_wall_11`** | D. Savva | 1,91 × 1,91 m | "Bloques cincelados con decoloración amarillo arena, juntas hondas" | **Mejor ajuste de estructura y de matiz.** Recomendada: comparar lado a lado con `stacked_stone_wall` |
| `broken_wall` | R. Tuytel | 3 × 3 m | Piedras grises apiladas, con huecos y liquen | Alternativa, más gris |
| `rock_wall_06` | D. Barresi, D. Savva | 1,31 × 1,31 m | Fragmentos angulares beige claros | Escala de grava; no |
| `rock_wall_09`, `rock_wall_08`, `rock_wall_16`, `rock_wall_10`, `defense_wall` | varios | — | Oscuras o adoquines | No |

- **Bytes de `rock_wall_11` 1k:** `rock_wall_11_diff_1k.jpg` 762.222 · `…_nor_gl_1k.jpg` 1.134.539 · `…_arm_1k.jpg` 679.322 (total 2.576.083). Como las juntas son hondas, se verá algo de mortero: aceptable en un muro de mampostería en seco a 5 m o más.
- **Decisión pendiente (para B3):** comparar `rock_wall_11` y `stacked_stone_wall` en un render a 5 m y a 20 m con la foto 1 al lado.

## 6. Medidas típicas con fuente

Estas medidas **se rotulan como aproximación** en el código y en `CREDITS.md` (regla de `006/plan.md`). Ninguna sustituye a la medición con cinta.

| Elemento | Medida | Fuente | Fiabilidad |
|---|---|---|---|
| **Talanquera de rollizos**: poste | Ø 12 cm (también 14), 1,5 m de largo con 0,4–0,5 m enterrados, altura vista ≈ 1,0–1,1 m | Urbadep, ficha técnica, ya recogida en `004-recursos-acceso-centro.md` §3.3 | **[B]** (el PDF está comprimido y no se puede leer por máquina) |
| Travesaños | Ø 8 cm × 2 m; dos por tramo; un poste cada ≈ 2 m | Idem; observado en las fotos 17, 26, 28 y 37: postes de 12–15 cm, travesaños de 8–10 cm | **[B]** y **[E]** |
| Altura de barandilla (último recurso) | 0,90 m si la caída es ≤ 6 m; 1,10 m si es mayor | CTE DB-SUA 1 (`004-recursos-acceso-centro.md`), fuente secundaria | **[B]** |
| **Torno peatonal trípode** | Alto 0,98 m; paso libre 0,60 m; cuerpo 1,20 × 0,20 m; acero inoxidable SUS304 | Dahua ASGG5XXT, https://www.dahuasecurity.com/uk/products/All-Products/Access-Control/Turnstiles/ASGG5XXT | **[P]** (la página da "1200 × 200 × 980 mm" sin rotular los ejes; se asume largo × ancho × alto) |
| | Alto 0,97–0,98 m; paso 0,55 m; brazos de 0,51 m (TriLane TL1 y TL2) | Automatic Systems, https://www.specifiedby.com/automatic-systems-uk-ireland/trilane-tl2-tripod-turnstiles | **[B]** |
| | Alto 0,98 m; paso 0,50–0,55 m | Secureye S-VT1000, https://www.secureye.com/?p=822 | **[B]** |
| | **No sabemos qué tipo es el torno del Peñón** (trípode, de brazos o de altura completa; `004` §2.5) | — | Rotular como genérico |
| **Fuente pública de agua** | Al menos un grifo a **0,80–0,90 m**, con 0,70 m libres debajo, y círculo libre de 1,50 m (para itinerario accesible) | Orden TMA/851/2021, art. 27, https://www.boe.es/eli/es/o/2021/07/23/tma851/con (deroga la Orden VIV/561/2010) | **[P]** |
| | Diseño real de los dos grifos del acceso: **ni foto ni modelo** | `004` §2.5 (OSM, 2 nodos) | Genérico, rotulado |
| **Pantalán flotante**: ancho | Módulos de 1,73 / 2,03 / 2,64 m (Walcon System 2000) y de 1,65 / 1,93 / 2,56 m (System 21); 1, 1,5, 2, 2,5 y 3 m (YPMarinas); pantalán principal de 4,00 × 42,50 m con pasarela de 2,50 m (Abandoibarra, Bilbao); módulos de 2 m (Mar Menor) | Catálogos en https://pdf.nauticexpo.com/pdf/walcon-marine/system-2000/22433-14764.html, https://pdf.nauticexpo.com/pdf/walcon-marine/system-21-pontoon/22433-90042.html y https://pdf.nauticexpo.com/pdf/ypmarinas/data-sheet-aluminum-floating-pontoon/44674-87479.html; memoria del pantalán de Abandoibarra (https://www.euskadi.eus/contenidos/anuncio_tablon/dpmt_anun_pantalanabandoibarra/es_def/adjuntos/Memoria.pdf); acta del MITECO sobre Los Nietos, Mar Menor (https://www.miteco.gob.es/content/dam/miteco/es/costas/participacion-publica/20230217actadeconfrontacionaut02-23-30-0010_tcm30-559725.pdf) | **[B]** |
| Pantalán: francobordo | 450 mm (System 2000) y 500 mm (System 21), nominales | Catálogos de Walcon (arriba). Fabricantes del Reino Unido; los pantalanes de Calp pueden diferir | **[B]** |
| Pantalán: tarima | Tablas de madera dura de 145 × 21 mm (Lindley Faro) o de 22 mm de madera tropical | https://pdf.nauticexpo.com/pdf/lindley-marinas/faro-faro-pontoons/56117-108080.html | **[B]** |
| | Los pantalanes de Calp, por la foto de 2015, son de **tarima de madera con barandilla de acero inoxidable** | `004-recursos-pobla-puerto.md` §2.2 | Foto |

**Lo que se deduce para el pantalán:** el 2,5 m del plan (H1-B5) está dentro del rango de los fabricantes. Es un ancho **aproximado**. Si se quiere un dato propio, se puede medir en la ortofoto de 25 cm/px, donde un pantalán de 2,5 m ocupa unos 10 píxeles.

## 7. Qué no se pudo verificar

- **PDFs comprimidos:** Urbadep, Automatic Systems, la memoria de Abandoibarra y las fichas comerciales no se pueden leer por máquina aquí (sin `pdftotext`). Se marcan [B].
- **Origen del velero de NTNU:** el README no lo declara.
- **Censo de la flota de Calp por arte:** no localizado. No consta cuántos de los pesqueros son de arrastre.
- **Sketchfab:** no se pudo conocer el tamaño de los archivos glTF sin sesión.
- **MAPA (censo de flota):** error de certificado al abrirlo.
- **FAO y el artículo de la flota adriática:** el servidor no respondió.

## 8. Lista de descargas para aprobar

Todo CC0. El nombre propuesto es el id de `data/catalog.toml` (`kind = "file"`, `size_tolerance = 0.0`; la fase la asigna el integrador). Los ficheros de texturas de los glTF van en `textures/` junto al `.gltf`, como las entradas ya existentes de `shrub_04`. Los bytes salen de las APIs. Autor: Poly Haven (CC0 1.0, https://polyhaven.com/license).

### 8.1 Recomendada

| # | URL | Nombre propuesto | Bytes | Autor | Para qué |
|---|---|---|---|---|---|
| 1 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/boulder_01/boulder_01_1k.gltf | `polyhaven-boulder-01-gltf-1k` | 2.773 | Rico Cilliers | B4 rocas (bloque grande) |
| 2 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/8k/boulder_01/boulder_01.bin | `polyhaven-boulder-01-bin` | 2.938.808 | Rico Cilliers | B4 |
| 3 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/boulder_01/boulder_01_diff_1k.jpg | `polyhaven-boulder-01-diff-1k` | 987.467 | Rico Cilliers | B4 (solo para comparar el color) |
| 4 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/boulder_01/boulder_01_nor_gl_1k.jpg | `polyhaven-boulder-01-nor-gl-1k` | 1.183.552 | Rico Cilliers | B4 |
| 5 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/boulder_01/boulder_01_arm_1k.jpg | `polyhaven-boulder-01-arm-1k` | 659.386 | Rico Cilliers | B4 |
| 6 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/rock_moss_set_01/rock_moss_set_01_1k.gltf | `polyhaven-rock-moss-set-01-gltf-1k` | 9.987 | Kless Gyzen | B4 (5 piedras) |
| 7 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/8k/rock_moss_set_01/rock_moss_set_01.bin | `polyhaven-rock-moss-set-01-bin` | 1.466.380 | Kless Gyzen | B4 |
| 8 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/rock_moss_set_01/rock_moss_set_01_diff_1k.jpg | `polyhaven-rock-moss-set-01-diff-1k` | 168.099 | Kless Gyzen | B4 |
| 9 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/rock_moss_set_01/rock_moss_set_01_nor_gl_1k.jpg | `polyhaven-rock-moss-set-01-nor-gl-1k` | 209.975 | Kless Gyzen | B4 |
| 10 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/rock_moss_set_01/rock_moss_set_01_rough_1k.jpg | `polyhaven-rock-moss-set-01-rough-1k` | 82.624 | Kless Gyzen | B4 |
| 11 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/rock_moss_set_02/rock_moss_set_02_1k.gltf | `polyhaven-rock-moss-set-02-gltf-1k` | 11.608 | Kless Gyzen | B4 (5 piedras) |
| 12 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/8k/rock_moss_set_02/rock_moss_set_02.bin | `polyhaven-rock-moss-set-02-bin` | 1.316.572 | Kless Gyzen | B4 |
| 13 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/rock_moss_set_02/rock_moss_set_02_diff_1k.jpg | `polyhaven-rock-moss-set-02-diff-1k` | 194.307 | Kless Gyzen | B4 |
| 14 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/rock_moss_set_02/rock_moss_set_02_nor_gl_1k.jpg | `polyhaven-rock-moss-set-02-nor-gl-1k` | 273.527 | Kless Gyzen | B4 |
| 15 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/rock_moss_set_02/rock_moss_set_02_rough_1k.jpg | `polyhaven-rock-moss-set-02-rough-1k` | 146.226 | Kless Gyzen | B4 |
| 16 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/beam_wall_01/beam_wall_01_diff_1k.jpg | `polyhaven-beam-wall-01-diff-1k` | 224.751 | Rob Tuytel | B7 rollizo |
| 17 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/beam_wall_01/beam_wall_01_nor_gl_1k.jpg | `polyhaven-beam-wall-01-nor-gl-1k` | 120.019 | Rob Tuytel | B7 |
| 18 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/beam_wall_01/beam_wall_01_arm_1k.jpg | `polyhaven-beam-wall-01-arm-1k` | 95.017 | Rob Tuytel | B7 |
| 19 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rock_wall_11/rock_wall_11_diff_1k.jpg | `polyhaven-rock-wall-11-diff-1k` | 762.222 | Dimitrios Savva | B3 muros (a comparar con `stacked_stone_wall`) |
| 20 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rock_wall_11/rock_wall_11_nor_gl_1k.jpg | `polyhaven-rock-wall-11-nor-gl-1k` | 1.134.539 | Dimitrios Savva | B3 |
| 21 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rock_wall_11/rock_wall_11_arm_1k.jpg | `polyhaven-rock-wall-11-arm-1k` | 679.322 | Dimitrios Savva | B3 |
| 22 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/brown_planks_03/brown_planks_03_diff_1k.jpg | `polyhaven-brown-planks-03-diff-1k` | 570.668 | Rob Tuytel | B5 tarima de pantalán |
| 23 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/brown_planks_03/brown_planks_03_nor_gl_1k.jpg | `polyhaven-brown-planks-03-nor-gl-1k` | 516.860 | Rob Tuytel | B5 |
| 24 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/brown_planks_03/brown_planks_03_arm_1k.jpg | `polyhaven-brown-planks-03-arm-1k` | 126.038 | Rob Tuytel | B5 |
| 25 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/concrete_floor_worn_001/concrete_floor_worn_001_diff_1k.jpg | `polyhaven-concrete-floor-worn-001-diff-1k` | 118.806 | Dimitrios Savva, Rico Cilliers | B5 muelle (prioridad baja) |
| 26 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/concrete_floor_worn_001/concrete_floor_worn_001_nor_gl_1k.jpg | `polyhaven-concrete-floor-worn-001-nor-gl-1k` | 110.906 | Dimitrios Savva, Rico Cilliers | B5 |
| 27 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/concrete_floor_worn_001/concrete_floor_worn_001_arm_1k.jpg | `polyhaven-concrete-floor-worn-001-arm-1k` | 152.919 | Dimitrios Savva, Rico Cilliers | B5 |
| 28 | https://ambientcg.com/get?file=Metal032_1K-JPG.zip | `ambientcg-metal032-1k-jpg` | 3.650.556 | ambientCG (CC0, https://docs.ambientcg.com/license/) | B7 metal del torno y los postes (sustituto de galvanizado) |

**Total recomendado: 17.913.914 bytes (17,08 MiB), 28 ficheros.**

### 8.2 Opcional (no incluida en el total anterior)

| # | URL | Nombre propuesto | Bytes | Autor | Para qué |
|---|---|---|---|---|---|
| 29 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/coast_rocks_05/coast_rocks_05_1k.gltf | `polyhaven-coast-rocks-05-gltf-1k` | 2.821 | Rob Tuytel | B4, afloramiento bajo (3,0 × 2,8 × 1,0 m, 1,45 M de triángulos a decimar) |
| 30 | https://dl.polyhaven.org/file/ph-assets/Models/gltf/8k/coast_rocks_05/coast_rocks_05.bin | `polyhaven-coast-rocks-05-bin` | 22.102.224 | Rob Tuytel | B4 |
| 31 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/coast_rocks_05/coast_rocks_05_diff_1k.jpg | `polyhaven-coast-rocks-05-diff-1k` | 954.605 | Rob Tuytel | B4 |
| 32 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/coast_rocks_05/coast_rocks_05_nor_gl_1k.jpg | `polyhaven-coast-rocks-05-nor-gl-1k` | 1.327.762 | Rob Tuytel | B4 |
| 33 | https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/coast_rocks_05/coast_rocks_05_arm_1k.jpg | `polyhaven-coast-rocks-05-arm-1k` | 893.696 | Rob Tuytel | B4 |
| 34 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rough_wood/rough_wood_diff_1k.jpg | `polyhaven-rough-wood-diff-1k` | 567.074 | Rob Tuytel | B7 travesaños (alternativa) |
| 35 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rough_wood/rough_wood_nor_gl_1k.jpg | `polyhaven-rough-wood-nor-gl-1k` | 790.334 | Rob Tuytel | B7 |
| 36 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/rough_wood/rough_wood_arm_1k.jpg | `polyhaven-rough-wood-arm-1k` | 137.749 | Rob Tuytel | B7 |
| 37 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/broken_wall/broken_wall_diff_1k.jpg | `polyhaven-broken-wall-diff-1k` | 650.170 | Rob Tuytel | B3, alternativa a `rock_wall_11` |
| 38 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/broken_wall/broken_wall_nor_gl_1k.jpg | `polyhaven-broken-wall-nor-gl-1k` | 1.045.384 | Rob Tuytel | B3 |
| 39 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/broken_wall/broken_wall_arm_1k.jpg | `polyhaven-broken-wall-arm-1k` | 196.416 | Rob Tuytel | B3 |

**Total opcional: 28.668.235 bytes (27,34 MiB), 11 ficheros. Recomendada + opcional: 46.582.149 bytes (44,42 MiB).**

### 8.3 Solo si se decide usar el velero de NTNU (CC BY 4.0, sin incluir en los totales)

Tamaños aproximados, del índice del servidor ("5.5M", "5.1M"); **bytes exactos desconocidos**. No se recomienda hasta saber el origen del modelo y los triángulos.

| URL | Nombre propuesto | Bytes aproximados | Autor | Para qué |
|---|---|---|---|---|
| https://www.itk.ntnu.no/milliampere-data/gemini/3d_models/Sailboat/seilbaat.obj | `ntnu-sailboat-obj` | ≈ 5.500.000 | Ocean Autonomy Cluster (CC BY 4.0) | B5, velero (decimar) |
| https://www.itk.ntnu.no/milliampere-data/gemini/3d_models/Sailboat/textures/Seilbaat_visual.png | `ntnu-sailboat-texture` | ≈ 5.100.000 | Ocean Autonomy Cluster (CC BY 4.0) | B5 |

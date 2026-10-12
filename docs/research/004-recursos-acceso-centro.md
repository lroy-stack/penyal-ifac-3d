# 004 — Recursos en línea para el acceso y los edificios del centro (E1.2, E3, E4)

- Fecha: 2026-10-12. Trabajo de investigación del tramo de acceso; no se ha editado ningún otro archivo ni se ha descargado nada al repositorio.
- Origen del encargo: el usuario no está en Calp y no hará las fotos de `docs/specs/002/protocolo-fotos.md` ("Fotos y medidas para modelar"). Este documento responde con lo que hay publicado.
- Convención de confianza, por dato:
  - **S** = lo dice una fuente (se cita).
  - **E** = estimado por mí a partir de una foto o de datos propios (se dice el método). Es una aproximación y debe marcarse así en `CREDITS.md`.
  - **N** = no encontrado tras una búsqueda razonable.
  - Alta / media / baja = confianza en el dato.
- Clasificación de cada recurso (columna "Uso"):
  - **textura** = CC0 o CC BY (se puede usar como textura, con atribución si es CC BY);
  - **referencia** = CC BY-SA o con derechos de autor pero visible en público: se mira y se mide, nunca se copian píxeles;
  - **dato** = dato abierto medible;
  - **no usable**.
- Cómo se vieron las imágenes: con `WebFetch`, que deja una copia en la caché de la herramienta (fuera del repositorio) y esa copia se abrió con `Read`. No se descargó nada con `curl` ni se escribió nada en `data/`. Los recortes de medida de color están en el directorio temporal de la sesión.
- Limitaciones de esta sesión (todas comprobadas el 2026-10-12):
  - `parquesnaturales.gva.es`, `mediambient.gva.es`, `sede.gva.es`, `cma.gva.es`: no responden (ECONNREFUSED / DNS). Lo que se cita de la GVA viene de **fragmentos de búsqueda** de sus páginas y se marca "fragmento".
  - `web.archive.org`: bloqueado por la herramienta.
  - Flickr (búsqueda), Mapillary (hace falta token) y Openverse (401): inaccesibles. KartaView: sin cobertura.
  - Los PDF de la GVA, del DOGV y del CTE se leen como bytes: solo se pudo extraer texto de los PDF del MARQ y de *El Temps*.
- Nada de lo que sigue es la ubicación de una planta de *Silene hifacensis*; no se describe a ninguna persona de las fotos.

## 0. Resumen

1. **Las dos "casas réplica" tienen fuente, pero la fecha de 1992 no.** La historia local de Calp (A. Ortolà, 2005) dice que, tras declararse el parque en 1987, se derribaron las dos casas de Vicente París y "en el solar" se construyeron "dos imitaciones" para Aula de la Naturaleza. No da año. No he encontrado ninguna fuente que diga 1992. Hay un primer dato fechado del centro en 2005 (zanja de servicios "dirigidos al Centro de Interpretación"). Arquitecto y fecha de apertura: **no encontrados**.
2. **Cuál es el Centro de Información y cuál el de Visitantes no se puede decidir en línea.** La GVA habla de "dos equipamientos" con un único horario. OSM llama "Centro de Interpretación" al edificio de 651 m² (forma en L, con el pórtico de arcos y las torretas) y deja sin nombre el de 483 m² (este, con la fachada acristalada).
3. **Los edificios ya se pueden describir bastante mejor** con tres fotos de Commons de 2013 (CC BY-SA 3.0, solo referencia), la foto 1 de 2014 (CC BY 3.0) y la ortofoto 2024: pórtico de arcos de medio punto sobre pilares blancos con suelo de baldosa roja, torretas almenadas, cubierta de teja curva, lucernario de vigas blancas con paneles, azoteas, patio con dos árboles y bancales de piedra seca. Los números de arcos, ventanas y puertas siguen siendo estimaciones.
4. **Kit de acceso.** El torno está en el vértice del tramo de escaleras de 30 peldaños, a 2,8 m del extremo suroeste del edificio este. No hay un puesto de control de reservas documentado. De fuentes, bancos y papeleras solo hay fotos parciales. De la escalera de 10 peldaños no hay nada más que OSM.
5. **El aparcamiento para personas con discapacidad (592 m²) coincide en planta con el patio de las cuatro pérgolas de madera** que se ve en la foto aérea de 2013 (inferencia con ortofoto, confianza media).
6. **Barandillas del sendero**: talanqueras de madera de rollizos con dos travesaños (fotos y fragmento de la GVA). No hay medidas oficiales; sí una tipología comercial afín y, como último recurso, los valores del CTE DB-SUA.
7. **Firme de la primera parte del sendero**: lajas irregulares de caliza clara con juntas finas de mortero. Entre los CC0 de Poly Haven, la mejor coincidencia de *dibujo* es `stone_tiles_02` (hay que aclararla y calentarla); ninguna textura de ambientCG sirve.
8. **Manual de señalización de la GVA**: existe (Resolución de 25-03-2011, DOGV 19-04-2011), pero el manual en sí no está en línea. No hay dimensiones oficiales de paneles ni postes.
9. **Descargas propuestas**: 15 archivos, **20,95 MB** en total (el mínimo útil son 6,0 MB de texturas CC0; ver §5).

## 1. Qué se pedía a las fotos del usuario y con qué se responde ahora

| Qué pedía el protocolo | Estado | Con qué se responde | Confianza |
|---|---|---|---|
| Fachadas de los dos edificios (de frente y a 45°) | **Parcial** | Tres fotos de Joanbanjo 2013 (referencia) y la de chisloup 2014 (CC BY); ortofoto 2024; OSM. Faltan las caras N, O y S del ala oeste y todo el edificio este salvo su cara S | Media |
| Alto de puerta y ventana, alto de zócalo | **No** | Solo estimación de la luz de los arcos (§2.4). Puertas y ventanas: sin medida | Baja |
| Escalera de 30 y de 10 peldaños (contrahuella, huella, ancho, barandilla) | **No** | Solo OSM (nº de peldaños, `surface`, `handrail=yes`) y lo ya derivado por el proyecto. Ninguna foto de ninguna de las dos | — |
| Empedrado del sendero (foto cenital, ancho en tres puntos) | **Parcial** | Fotos 17, 26 y 37 (ya locales): aspecto y color. Ancho: estimación ≈ 2,0 m (§4.1) | Media (aspecto), baja (ancho) |
| Bordillos, muretes y barandillas | **Parcial** | Barandilla: tipología y fotos; muretes de piedra seca: fotos 1, 28 y 2013 | Media / baja |
| Torno y control de reservas | **Parcial** | Ubicación (OSM, dato) y existencia (Hola 2020, otras). Sin foto ni modelo. No hay puesto de control fijo documentado | Media (ubicación), nula (diseño) |
| Fuentes | **Parcial** | Ubicación (OSM, dos grifos); diseño: nada | Media / nula |
| Paneles, balizas, bancos, papeleras | **Parcial** | Fotos 2013 y 2014: baliza de acero, papelera con envolvente de madera, banco bajo el pórtico, panel naranja de aviso. Auditoría de accesibilidad 2021: tipos de banco y panel | Baja |
| Aparcamiento junto al centro y acceso desde la rotonda del puerto | **Parcial** | OSM (592 m², `parking=surface`), foto aérea 2013 (pérgolas), foto Tagzania 2026 (gravilla); acceso rodado: OSM (asfalto, barrera) | Media / baja |

## 2. Los dos edificios del centro (E3)

### 2.1 Identidad: qué es cada uno y qué dicen las fuentes

| Cuestión | Qué se encontró | Fuente | Tipo / confianza |
|---|---|---|---|
| Nombres oficiales | La GVA: "el Centro de Información y el Centro de Visitantes están emplazados en la cara Norte del Penyal", con un único horario (L–V 8:30–14:30; fines de semana y festivos 9:00–14:00) y C/ Illa de Formentera, s/n | `gva-centro-visitantes` (ya en `sources.json`); fragmento de búsqueda 2026-10-12 | S, fragmento / media |
| Otros nombres | "Centro de Información o Aula de la Natura" (spain.info); "Centro de Interpretación y Aula de la Naturaleza" (blogs 2021–2022); "Centro de Interpretación y Visitantes del Parque" (Conmochila); "Centro de Visitantes y el Museo del Parque" (MARQ, informe de 2006) | spain.info; sendasyleyendas.com; conmochila.com; MARQ 2006 | S / media |
| Cuál es cuál | **No se puede decidir.** OSM etiqueta `way/26330271` (651 m², forma en L) como `tourism=museum`, "Centro de Interpretación Parque Natural del Penyal d'Ifac", con el mismo horario que la GVA y un teléfono (+34 965 83 75 96) distinto del que da la GVA (965 693 300). `way/26330272` (483 m²) no tiene etiquetas más que `building=yes`. Ninguna fuente dice qué hay en cada uno | OSM (`osm-penyal.json`) | N / — |
| Qué hay dentro | Salas con paneles sobre los ambientes del parque, una recreación del acantilado con botones que reproducen cantos de aves (halcón peregrino, jilguero, cormorán moñudo), maquetas del Penyal y una exposición fotográfica pequeña. Un aula educativa. Acceso sin obstáculos a la exposición | GVA (fragmentos); denia.net | S, fragmento / media |
| Pasillos y puertas del interior | Pasillos ≥ 120 cm, puertas ≥ 80 cm de paso libre, rampa de entrada con pendiente < 8 %. Aseos: una cabina masculina y otra femenina, de las que el auditor dice que no cumplen toda la normativa | Equalitas Vitae (datos tomados por una persona usuaria de silla de ruedas en junio de 2021) | S / media |
| ¿Son las "dos casas réplica"? | **Probable, sin prueba directa.** Ver §2.2. El número cuadra (dos edificios, dos casas) y el edificio grande tiene torretas almenadas, pero no he podido ver cómo eran las casas originales | historiadecalp.net; a un tir de pedra | S (hecho) / E (identificación), media |
| "Inauguradas en 1992" | **Sin fuente.** Buscado con varias formulaciones en español y catalán, en BOE/DOGV y en prensa: nada. Conviene quitar el año de `facts.json` hasta tener fuente o dejarlo con estado "sin confirmar" | — | N |
| Proyecto, arquitecto, fecha de apertura | **No encontrados** (ni en contratación pública, ni en el DOGV, ni en publicaciones). Pistas para pedir al parque: Servicio de Espacios Naturales de la GVA, archivo municipal de Calp (licencias), COACV | — | N |

### 2.2 Cronología con fuentes

| Año / fecha | Hecho | Fuente | Confianza |
|---|---|---|---|
| Desde 1957 (según la fuente) | Perdura en la ladera la estructura inacabada del "Ifach Palace Hotel" | historiadecalp.net (A. Ortolà Tomás, feb. 2005) | S / media (fuente local, sin citas) |
| Antes de 1987 (sin año) | Vicente París compra terrenos y construye dos casas ("la casa del casero y la de París") y la carretera de acceso. Túnel de 1918 | historiadecalp.net; GVA (túnel) | S / media |
| 1987-01 (17 o 19) | Declaración de parque natural; la Generalitat compra el peñón por 111 millones de pesetas. El conseller dice que en el peñón hay obras del hotel, una estructura de hormigón y "dues cases, una mig enderrocada i una altra en millor estat", y plantea rehabilitar una como centro de estudios ecológicos o pequeña exposición | *El Temps*, 2-02-1987, pp. 22–23 (PDF escaneado con capa de texto) | S / alta |
| Después de 1987 (sin año) | Las dos casas de París se derriban y "en el solar de las casas se construyeron dos imitaciones" para Aula de la Naturaleza | historiadecalp.net (2005); blog *A un tir de pedra* (16-12-2010) | S / media |
| 1993-12-30 | Decreto 260/1993 (PRUG). Según un fragmento de búsqueda de su texto, prevé una zona de servicios con centro de información, centro de recepción/aula de la naturaleza y cafetería | DOGV 21-01-1994 (escaneado, no legible); fragmento | Fragmento / baja |
| 2005-04-11 a 2005-06-08 | Seguimiento arqueológico de la zanja para saneamiento, electricidad y comunicaciones "dirigidos al Centro de Interpretación del Parque Natural", en el camino de acceso. Promotora: VAERSA | MARQ, *Actuaciones arqueológicas en la provincia de Alicante 2005* (publ. 2007), informe nº 57 | S / alta |
| 2006-07 | Informe del MARQ: la Muralla Norte "se halla en los tramos inmediatos a la subida al Centro de Visitantes y el Museo del Parque" | MARQ, informe nº 72 (publ. 2008) | S / alta |
| 2007-07-31 | Un blogger describe el Aula de Natura: sus estancias "recrean unas antiguas edificaciones aquí existentes" y hay una barrera que limita el tráfico de vehículos | geoelx.blogspot.com (publ. 2008) | S / media |
| 2013-11-02 | Fotos de Joanbanjo (3) del centro | Commons | — |
| 2014-05-27 | Foto 1 de chisloup (la ya local) | Commons | — |
| 2020-07 | "Junto al centro existe un torno para controlar el número de visitantes"; límite de 150 dentro del parque en temporada alta (cifra que luego pasa a 300/día con reserva, dic. 2020) | hola.com (21-07-2020) | S / media |
| 2021-06 | Auditoría de accesibilidad | equalitasvitae.com | S / media |
| 2025-10 | "Nadie comprobó ninguna reserva cuando estuve" | viewfromlavila.com | S / baja (una anécdota) |

Conclusión sobre la historia: lo único firme es la secuencia 1987 (casas existentes y declaración) → después, sin fecha, "dos imitaciones" → 2005 (el centro ya existe como destino de servicios). Para fecharlo hay que preguntar al parque.

### 2.3 Geometría en planta (datos medidos de OSM)

Marco local del proyecto: `x = E − 767000`, `N' = N − 4280000` (en el mundo, `z = −N'`). Coordenadas calculadas con pyproj (EPSG:4326 → 25830) sobre `data/raw/osm-penyal/osm-penyal.json`. Rumbos desde el norte. **Dato medido (OSM), confianza alta en forma y media en posición.**

**Edificio 1** — `way/26330271`, 651 m² (la CV05 da 623 m²). Forma en L: ala oeste N–S de 30 × 13 m y ala norte inclinada ≈ 20° respecto al este, con el patio en el ángulo interior.

| Arista | De → a (x, N') | Largo | Rumbo | Cara hacia | Qué se ve en esa cara (fotos) |
|---|---|---|---|---|---|
| A–B | (511,3; 1051,3) → (513,0; 1021,4) | 30,0 m | 177° | O | Sin fotos |
| B–C | → (526,1; 1022,0) | 13,1 m | 87° | S | Aseos (nodo OSM dentro de la huella) con "rampa de acceso a aseos" (GVA, fragmento) |
| C–D | → (524,8; 1040,7) | 18,7 m | 356° | E (patio) | Arcada visible a lo lejos en la foto cenital 2013 |
| D–E | → (541,1; 1047,0) | 17,5 m | 69° | SSE (patio) | Pórtico de arcos, ventanas con persiana y rejillas, muro de piedra seca delante |
| E–F | → (535,2; 1061,7) | 15,8 m | 338° | ENE (paso hacia el torno) | Extremo del pórtico: pilar macizo blanco y 4 arcos en fuga, puerta de madera, peldaños rojos |
| F–A | → (511,3; 1051,3) | 26,1 m | 247° | NNO | Sin fotos |

**Edificio 2** — `way/26330272`, 483 m² (394 m² en la CV05). Rectángulo de 34,1 × 14,1 m, eje mayor a 80° (casi E–O).

| Arista | Largo | Cara hacia | Qué se ve (foto aérea 2013 y ortofoto) |
|---|---|---|---|
| P(549,6; 1038,8) – Q(583,2; 1044,8) | 34,1 m | N | Cubierta de teja; sin detalle |
| Q – R(585,7; 1030,9) | 14,1 m | E | Sin fotos |
| R – S(552,1; 1024,9) | 34,1 m | **S** | Mitad este: fachada acristalada con carpintería verde-azulada y azotea/terraza con barandilla. Mitad oeste: teja a cuatro aguas |
| S – P | 14,1 m | O (paso y escalera) | Muro blanco bajo la teja |

Relaciones útiles:
- El **torno** (`node/8032598828`, (549,3; 1024,4)) es el vértice central de la escalera de 30 peldaños (`way/26330269`, 16,9 m). Queda a 12,8 m del inicio de la escalera y a **2,8 m al oeste del vértice suroeste del edificio 2** (552,1; 1024,9). La escalera pasa a ≈ 2,8–2,9 m del muro oeste del edificio 2.
- La escalera de 10 peldaños (`way/862108205`, (574,7; 1087,5) → (563,4; 1087,3), 11,3 m) está 63 m al norte del torno.
- Alturas (LiDAR 2016, ya en `CREDITS.md`): edificio 1 con alero a 74,02 m y cumbrera a 76,11 m; edificio 2 con 76,84 m y 79,79 m.

### 2.4 Qué se ve: elementos del edificio 1 y 2

Fuentes visuales (todas vistas): `J1` Joanbanjo, "Centre de visitants del penyal d'Ifac" (2013-11-02 11:54, 4604×2957, CC BY-SA 3.0); `J2` Joanbanjo, "…des de dalt" (14:41, vista oblicua desde la cima, 4563×3034); `J3` Joanbanjo, "Penyal d'Ifac, centre de visitants" (11:57, 4584×2953); `C1` chisloup 2014 (foto 1 local, CC BY 3.0); `O` ortofoto 2024 del ICV (local, CC BY 4.0).

| Elemento | Observación | Cantidad / medida | Método | Confianza |
|---|---|---|---|---|
| Pórtico (arcada) | Arcos de **medio punto sobre jambas rectas**, pilares blancos encalados, suelo de baldosa de barro rojo con dos peldaños del mismo material, alero de teja que vuela sobre la arcada | **≥ 4 arcos** en la cara E del ala norte (J1, C1); **≥ 3** en la cara S (J3, C1, parcialmente tapados por almendros); arcada también en la cara E del ala oeste (J3, a la izquierda). Total probable **8–12** | Conteo en foto; los ocultos no se cuentan | Baja en el total, media en lo visible |
| Luz y altura de los arcos | Arcos esbeltos: pilar ≈ 0,6 m de ancho | **Luz ≈ 2,0 m (1,8–2,4)**; jambas ≈ 2,0 m; **clave ≈ 3,0 m (2,7–3,4)** sobre el suelo del pórtico; paso entre ejes ≈ 2,6 m (2,4–3,0) | Proporción en un recorte ampliado de J1 (radio del arco ≈ 190 px; puerta de madera visible dentro ≈ 415 px, supuesta de 2,0–2,1 m) y comprobación con el alero LiDAR (74,02 m) menos el suelo del patio (≈ 70,5–71 m; el punto F1 del protocolo está a 70 m, sin medir) | **Baja (±25 %)**; es una aproximación a marcar en `CREDITS.md` |
| Pilar de esquina | Muro blanco macizo entre las dos caras de la arcada, de ≈ 2,5–3 m de ancho | 1 | J1 | Media |
| Cubiertas | Teja árabe (curva) terracota, a cuatro aguas con alero, pendiente baja (≈ 20–25°). Una chimenea en el ala oeste | — | J2, J3 | Media (tipo), baja (pendiente) |
| Torretas | Cuerpo cuadrado ocre con parapeto blanco **almenado** (almenas escalonadas); hilos finos sobre el remate (probablemente antiaves) | **≥ 2** vistas desde el suelo (J1, J3, C1); **4** en la foto aérea J2, en las esquinas del cuerpo alto del ala norte. `CREDITS.md` solo modela una (máximo local del LiDAR) | Conteo | Media |
| Lucernario / pérgola | Estructura de vigas blancas inclinadas sobre el faldón sur del cuerpo alto del ala norte, con paneles planos oscuros (solares o claraboyas) en el extremo este. En la ortofoto, tres vanos cuadrados en fila y un campo de paneles claros | 3 vanos + 1 campo | J1, J2, O | Media |
| Terraza / azotea | Azotea plana rojiza con claraboyas y un parapeto oscuro en L en la zona noroeste del ala norte; terraza con barandilla en el extremo este del edificio 2 | 1 + 1 | O, J2 | Media |
| Puerta | Puerta de madera oscura con panel de vidrio con carteles, bajo la arcada del extremo E del ala norte; apliques negros cilíndricos en los pilares | ≥ 1 puerta; ≥ 3 apliques | J1 (ampliado) | Media |
| Ventanas | Ventanas pequeñas de marco rojizo con alféizar y persianas, sobre el muro ocre del patio; una de arco de medio punto; rejillas de ventilación bajas | **No contables** con las fotos disponibles | J1, J3 | N (conteo) |
| Zócalo y muros bajos | Muros de mampostería en seco de piedra ocre dorada, con albardilla plana, a distintas alturas (bancales); cierran el patio y flanquean el paso | Alto ≈ 0,8–1,2 m (no medible) | J1, J3 | Baja |
| Edificio 2: cuerpo este | Planta rectangular; mitad oeste con cubierta de teja; mitad este con azotea plana, pretil blanco y gran fachada acristalada con carpintería verde-azulada en la cara S | 1 fachada acristalada | J2, O | Media |

### 2.5 Materiales y colores

| Superficie | Descripción | Color (cualitativo) | Textura ya elegida en `CREDITS.md` | Comentario |
|---|---|---|---|---|
| Arcada, pilares, parapeto de torretas | Enlucido encalado liso | Blanco | `white_stucco` | Coincide |
| Muros de los cuerpos altos y del patio | Enlucido liso | Ocre amarillo claro | `yellow_plaster` | Coincide |
| Cubiertas | Teja curva envejecida, mezcla de tonos | Terracota y rojizo | `roof_tiles` | Coincide |
| Muros de piedra seca / zócalo | Mampostería ocre dorada, sin mortero visible, con albardilla | Ocre tostado | `stacked_stone_wall` | Coincide |
| Suelo del pórtico y peldaños | Baldosa de barro rojo | Rojo pardo | — | **Nuevo**: candidato `patio_tiles` (§4.2) |
| Paso delante del pórtico y entre edificios | Lajas irregulares de caliza clara con juntas finas (foto 1: mismo dibujo que el sendero) | Crema claro | — | Ver §4 |
| Patio y alrededores del edificio 1 | Empedrado de cantos grises, blanquecinos y ocres con bandas de laja | Gris azulado | — | Candidato a revisar: `multicolored_pebble_floor` (sin ver) |
| Carpintería de puertas y ventanas | Madera barnizada marrón rojiza | Marrón | — | Color plano |
| Carpintería del edificio 2 | Metal o madera pintada | Verde azulado | — | Color plano |

Medidas de color del firme (sRGB, mediana del recorte, en fotos locales; son **indicativas**, dependen de la exposición):
- Lajas de la foto 26 al sol: `#F4EDE2` (probablemente sobreexpuesto); a media luz `#EEE4D8`.
- Lajas de la foto 17 en luz difusa: `#C9BEB4`.
- Gravilla compactada del tramo alto (foto 28): `#978677`.
- Explanada de gravilla (foto Tagzania 46, sol): `#B7977A`.
- Albedo propuesto para las lajas: `#D5CAB8` ± 10 (E: entre la zona al sol y la difusa).
- La foto de Joanbanjo 2013 lleva un perfil de color atípico y no se ha medido el color de las fachadas en ella.

### 2.6 Entorno inmediato

| Elemento | Observación | Fuente | Confianza |
|---|---|---|---|
| Patio | Entre el ala oeste y el ala norte, abierto al sureste, con dos árboles (en la ortofoto, dos copas oscuras; en J2 y J3 se distingue un ciprés y un árbol bajo) y arbustos; bancales de piedra seca escalonados en su borde sur y, al fondo, un elemento circular de piedra (¿rampa o escalera en curva?) | J2, J3, O | Media |
| Paso entre edificios | Calle pavimentada de lajas claras que sube al torno y a la escalera; a su este, el edificio 2 | J2 | Media |
| Papeleras | Columna de listones de madera barnizada con la bolsa y el cubo metálico gris dentro; junto a otro objeto de madera (banco o cartel) | J3 (ampliado) | Media |
| Bancos | Banco oscuro bajo el pórtico (J1). Circuito de Levante: bancos **con respaldo y reposabrazos**. Zona recreativa: mesas con bancos **sin respaldo** | J1; Equalitas Vitae | Media |
| Balizas | Poste de sección rectangular de acero inoxidable, cabeza negra con flecha blanca y tramo rojo, y un pictograma de ave estilizado en negro, rojo y amarillo. Alto estimado 1,1–1,4 m, ancho 0,25–0,35 m (comparado con el muro bajo y los peldaños) | J1, C1 | Media (diseño), baja (medidas) |
| Panel de aviso | Tablero naranja con triángulo de advertencia sobre un poste de madera, junto a la barandilla (tramo alto, foto 28) | Foto 28 local | Media |
| Pérgolas | **4** estructuras de madera con cubierta de lamas, en fila sobre un patio de superficie clara, ≈ 55–90 m al norte del torno. Sus posiciones aproximadas (estimadas sobre la ortofoto 2024, 0,25 m/px, con la huella del edificio 1 como referencia) caen dentro del polígono de `way/862108210` (aparcamiento) o en su borde sur | J2, O, OSM | Media (identificación) |
| Camino de servicio | Vía ancha de gravilla clara compactada con borde de piedra o madera, que rodea el centro por el norte hacia la Pobla | J2 | Media |
| Casetas | Pequeño grupo de edificios de teja naranja al noroeste (OSM `way/261433047`, 547 m², sin nombre) | J2 | Media |

## 3. Kit de acceso (E4)

### 3.1 Elementos

Posiciones: OSM (dato) en el marco local de §2.3.

| Elemento | Qué se sabe | Diseño / medidas | Fuente | Confianza |
|---|---|---|---|---|
| **Barrera de vehículos** | `barrier=gate`, `motor_vehicle=no`, en (449,6; 1188,6), a 185 m al NNO del centro. Una "vía sin asfaltar cerrada al tráfico" lleva al centro. Tres puertas más con `foot=yes, bicycle=no` cerca del puerto | **N** (sin foto) | OSM; hola.com 2020; geoelx 2008 | Media (posición) |
| **Torno** | Vértice de la escalera de 30 peldaños (§2.3). "Junto al centro" (2020). Cuenta personas. Es "la última oportunidad para ir al baño o recargar agua" antes de la ruta (blog, sin fecha visible) | **N** (ni foto ni modelo). Si se modela, ha de ser genérico y marcarse así | OSM; hola.com; conmochila.com; GVA (fragmento) | Alta (existencia y posición), nula (diseño) |
| **Control de reservas** | Reserva en línea gratuita (hasta 300/día). **No hay un puesto de comprobación documentado**; un visitante de 2025 dice que no revisaron ninguna. La autorización llega en PDF. El control físico es el torno | — | GVA (fragmento); viewfromlavila.com | Media |
| **Fuentes** | Dos grifos (`amenity=drinking_water`, `man_made=water_tap`): A en (535,2; 1036,8), en el patio, 7 m al sur de la cara S del ala norte; B en (550,7; 1018,1), 6 m pasado el torno (revisado en OSM el 2025-10-28). La GVA: no hay ninguna fuente en el recorrido | **N** | OSM; GVA (fragmento); `access-safety` | Media (posición) |
| **Aseos** | Nodo `toilets` (gratis, accesible en silla de ruedas) **dentro de la huella del ala oeste**, en su extremo sur, a (522,1; 1028,7). Acceso por rampa (GVA, pie de foto "Rampa acceso aseos"). Dos cabinas (M y F). Hay otro nodo de aseos junto al puerto, a ≈ 205 m | **N** | OSM; GVA (fragmento); Equalitas Vitae | Media |
| **Rampas** | "Rampa de acceso al Centro de Información y a la Ruta Roja" (GVA). Desde el aparcamiento hay dos rampas de gran longitud con pendiente > 12 %; rampa de entrada al centro < 8 % | Pendientes (Equalitas Vitae) | GVA (fragmento); Equalitas | Media |
| **Paneles** | Paneles de alto contraste con espacio libre debajo para acercarse en silla (circuito de Levante); "numerosos" paneles de flora y fauna | **N** (dimensiones) | Equalitas Vitae | Baja |
| **Bancos y mesas** | Ver §2.6 | **N** | Equalitas Vitae | Baja |
| **Circuito de los miradores de Levante** | Circuito cerrado de ≈ 650 m, ancho ≥ 120 cm, tierra compactada, con miradores y zonas de descanso pavimentados (pavimento con relieve en la entrada y en los descansos). Empieza a "escasos metros" del centro. Posibles miradores: nodos `tourism=viewpoint` en (633,1; 1104,7) y (633,7; 1123,3) | Anchura mínima | Equalitas Vitae; hola.com; GVA (fragmento); OSM | Media |
| **Aparcamiento para personas con discapacidad** | `way/862108210`: 592 m², 17,8 × 33,0 m, rumbo 70°, centro a 89 m del torno (hacia el norte-noroeste), `parking=surface`. Solo vehículos acreditados; horario del centro. "No hay plazas marcadas" (2021). Superficie de gravilla (foto Tagzania 2026 cercana) con **4 pérgolas** (§2.6) | Plazas: **N** | OSM; GVA (fragmento); Equalitas Vitae | Media |
| **Aparcamiento público** | Explanada pequeña de tierra y gravilla al final de C/ Illa de Formentera, sin vigilancia ni coste | — | bouger-voyager.com; sendasyleyendas.com; Wikimedia (Tagzania) | Media |
| **Barandilla del sendero** | Talanqueras de madera: rollizos verticales y **dos travesaños** de madera con la corteza quitada, a uno o a ambos lados. En el tramo alto, postes y cuerda | Ver §3.3 | Fotos 5, 13, 16, 17, 26, 28, 37; GVA (fragmento); *A un tir de pedra* | Alta (tipo), baja (medidas) |

### 3.2 Escaleras de 30 y de 10 peldaños

| Dato | 30 peldaños (`way/26330269`) | 10 peldaños (`way/862108205`) | Fuente | Confianza |
|---|---|---|---|---|
| Longitud | 16,9 m | 11,3 m | OSM (medida) | Alta |
| Material del peldaño | `paving_stones` | `sett` (adoquín) | OSM | Media |
| Barandilla | `handrail=yes`, **sin lado** | `handrail=yes`, sin lado | OSM | Media |
| Sentido | `incline=up` hacia el sur | `incline=down`; el MDT sube 2,2 m, así que el proyecto la orienta por el MDT | OSM; `CREDITS.md` | — |
| Contrahuella / huella / ancho | Derivados por el proyecto: 0,166 m y huella media 0,565 m | 0,224 m y huella media 0,90 m | `CREDITS.md` | Baja (derivados) |
| Altura de barandilla, material, separación de postes, lado | **N** | **N** | Búsqueda sin resultados | — |

Hay una cuestión de coherencia que no puedo resolver en línea: con una contrahuella de 0,166 m, la huella media de 0,565 m da 2C+H = 0,90 m, fuera de la regla de 54–70 cm del CTE. Eso encaja con peldaños muy largos o con descansillos, no con una escalera normal. El CTE no obliga en un camino natural, pero indica que el número de peldaños de OSM puede no corresponder a escalones físicos continuos. **Solo una medida en el sitio lo resuelve.**

### 3.3 Barandillas y señalización: lo que hay publicado

- **Tipología observada** (fotos 17, 26, 28, 37): rollizos de madera de pino sin corteza, postes de sección mayor (≈ 12–15 cm de diámetro) y dos travesaños más finos (≈ 8–10 cm), con un poste cada ≈ 2 m. Altura de la barandilla ≈ 1,0–1,1 m. **Todo E**, por comparación con el tamaño de las lajas (0,3–0,7 m) y con la forma del poste; sin un objeto de tamaño conocido en el encuadre.
- **Tipología comercial afín** (no es una especificación del parque): "talanquera" de pino tratado en autoclave con poste de Ø 12 cm (también Ø 14 cm) y 1,5 m de largo total, con dos taladros pasantes, y dos travesaños de Ø 8 cm y 2 m (Urbadep, ficha técnica; dato de un fragmento de búsqueda porque el PDF no se pudo leer). Con 0,4–0,5 m enterrados, la altura vista sería ≈ 1,0–1,1 m, que coincide con lo observado.
- **Manual de señalización**: la Resolución de 25 de marzo de 2011 de la Conselleria de Medio Ambiente, Agua, Urbanismo y Vivienda (DOGV 19-04-2011) aprueba el *Manual de señalización de los parques naturales, parajes naturales, reservas naturales, monumentos naturales, sitios de interés y paisajes protegidos de la Comunitat Valenciana* como "documento director": define la imagen gráfica y los detalles técnicos y constructivos de cada señal, e incorpora criterios de accesibilidad e integración paisajística. Sustituye a un primer manual de 2001. **El manual no está publicado en las páginas accesibles** y no he podido abrir `mediambient.gva.es` (allí figura también la "Normativa de la marca Parcs Naturals"). No hay, por tanto, dimensiones oficiales de panel, poste o banco.
- **Fallback CTE DB-SUA** (último recurso, solo si hace falta un número; **no es obligatorio en un camino natural y no es una fuente del parque**). Texto de SUA 1 transcrito en normatia.com:
  - altura de barandilla (3.2.1): 0,90 m si la caída es ≤ 6 m, 1,10 m si es mayor;
  - pasamanos (4.2.4): entre 90 y 110 cm;
  - huecos (3.2.3): esfera de 10 cm (15 cm en otros usos públicos);
  - peldaños de tramos rectos de uso general (4.2.1): huella ≥ 28 cm, contrahuella 13–17,5 cm (hasta 18,5 cm si hay ascensor alternativo), 54 ≤ 2C+H ≤ 70 cm.
  - Plaza de aparcamiento accesible: el DB-SUA fija la zona de transferencia (1,20 m laterales), no las dimensiones de la plaza (guía del COA de Málaga; fuente secundaria).

## 4. Firmes (E1.2)

### 4.1 Cómo son

| Superficie | OSM | Observación en fotos y fuentes | Confianza |
|---|---|---|---|
| **Primeros ≈ 420 m del sendero** (`way/26330273`, 724 m en total) | `unhewn_cobblestone` | **Lajas irregulares de caliza clara, con forma poligonal y juntas finas de mortero** ("opus incertum"), no canto suelto. Dibujo de lajas de 0,3–0,7 m, bordes redondeados por el uso. El mismo firme que delante del pórtico (foto 1). Desde el aparcamiento "pavimento empedrado y amplio" (GVA, fragmento) | Alta (aspecto) |
| Ancho del sendero | — | **≈ 2,0 m** (1,5–2,5) entre las talanqueras. "Senda ancha" (blog 2022). El circuito de Levante tiene ≥ 1,20 m (Equalitas) | Baja (E: 4–5 lajas de ≈ 0,45 m en el ancho de la foto 26) |
| Accesos al centro (`way/26330270`, `862108204`, `862108209`) | `unhewn_cobblestone` | Empedrado de lajas como el anterior | Media |
| Patio y alrededor del edificio 1 | — | Empedrado de cantos grises y blanquecinos con bandas de laja (J3) | Media |
| Pista de servicio | `unhewn_cobblestone` (150 m) y `compacted` (312 m) | "Vía sin asfaltar cerrada al tráfico" (2020); gravilla clara compactada con borde (J2) | Media |
| Tramo alto antes del túnel | `compacted` / `ground` | Gravilla y zahorra de caliza clara compactada, con restos de lajas y tramos de roca (foto 28): `#978677` | Media |
| Circuito de Levante | `compacted`, `dirt` | Tierra compactada, con miradores y descansos pavimentados con relieve | Media |
| Explanada de gravilla | `parking=surface` | Tierra y gravilla clara con matas ralas (Tagzania 2026; bouger-voyager 2022). `#B7977A` al sol | Media |
| Avinguda del Port y de l'Illa de Formentera | `asphalt` (316 m y 123 m) | Asfalto; no he encontrado una foto fiable del estado. Sin marcas viales documentadas | Media (OSM) |
| Suelo del pórtico | — | Baldosa de barro rojo con peldaños del mismo material | Media |
| Peldaños de las dos escaleras | `paving_stones` / `sett` | **N** | — |

### 4.2 Candidatos CC0

Licencia de Poly Haven: CC0, sin atribución obligatoria (https://polyhaven.com/license, leída 2026-10-12). Tamaños leídos de `api.polyhaven.com/files/<id>` (bytes, JPG). URL de cada mapa: `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/<res>/<id>/<id>_<mapa>_<res>.jpg`, con `<mapa>` = `diff`, `nor_gl`, `arm`. Resoluciones disponibles: 1k, 2k, 4k y 8k para todas; 16k para `forest_ground_05`, `gravel_floor_04`, `asphalt_04`, `rocky_trail_02`, `cobblestone_02`. Vistas en miniatura sobre esfera (vista), no a tamaño completo.

| Uso | Id (autor, fecha) | Vista | 1k diff / nor_gl / arm (B) | 2k diff (B) | Encaje y límites |
|---|---|---|---|---|---|
| **Lajas del sendero** (primera opción) | `stone_tiles_02` (Charlotte Baglioni, 26-03-2023) | Lajas poligonales irregulares con juntas finas y mucho relieve | 817.710 / 873.564 / 623.281 | 3.487.320 | **Mejor coincidencia de dibujo.** Gris verdoso oscuro: hay que subir el brillo y calentar el tono a crema (`#D5CAB8`). Relieve fuerte: probar con el normal atenuado. Escala: el campo `dimensions` de la API es [2000, 2000] (probablemente mm: 2 m de lado); ≈ 25 lajas de ≈ 0,4 m, parecido al sendero |
| Lajas (alternativa) | `stone_tiles` (Christopher Melani, 03-01-2023) | Lajas poligonales irregulares, verde-gris oscuro | 787.339 / 786.125 / 898.517 | 3.512.589 | Parecida; juntas algo más abiertas |
| Lajas grandes (alternativa) | `slab_tiles` | Lajas muy grandes y oscuras con mortero pardo | 492.538 / 510.086 / 744.405 | 1.982.779 | Lajas mayores que las del sendero; la más ligera |
| Descartadas para lajas | `cobblestone_floor_02`, `cobblestone_floor_05`, `cobblestone_02`, `mixed_rock_tiles`, `rock_tile_floor`, `rock_tile_floor_02`, `stone_tiles_03` | Adoquines pequeños, losas rectangulares o pedernal | — | — | Ninguna tiene el dibujo poligonal. `cobblestone_floor_02` y `cobblestone_floor_05` pueden servir para adoquines (`sett`) de la escalera de 10 peldaños; no medidas |
| **Gravilla compactada** (tramo alto, pista, explanada) | `gravel_floor_04` (Poly Haven) | Grava fina arenosa, tono pardo | 952.532 / 1.287.582 / 749.840 | 3.971.898 | Más cercana en tono a `#B7977A` que las otras. Hay que aclarar y desaturar para el tramo alto (`#978677`). Normal pesado (1,3 MB) |
| Gravilla (alternativas vistas) | `forest_ground_05` (Charlotte Baglioni, 08-07-2026), `park_dirt`, `gravel_road`, `dry_ground_rocks` | Marrón oscuro, verde-oliva con hojarasca, rojizo y pardo | `forest_ground_05`: 655.934 / 1.167.042 / 812.641 | 2.760.081 | Demasiado oscuras o con detritos; solo con tinte fuerte |
| **Asfalto** (solo E5) | `asphalt_04` (J. van Heerden, S. Majboroda, 16-11-2023) | Gris medio con grietas finas | 880.083 / 986.045 / 554.776 | 3.999.385 | Ya propuesto en `003-construccion-assets.md`. Alternativas por nombre (sin ver): `asphalt_06`, `asphalt_07`, `worn_asphalt` |
| **Suelo del pórtico** | `patio_tiles` (Dario Barresi, 22-04-2023) | Baldosas rectangulares grandes de barro, rojo-naranja | 700.816 / 302.459 / 474.715 | 3.052.490 | Encaja en el tipo (baldosa de barro). El real es rojo pardo: ajustar tinte y escala |
| Empedrado del patio (por mirar) | `multicolored_pebble_floor` | **Sin ver** | sin medir | — | Solo por sus etiquetas ("pebble mosaic", "stone paving") |

ambientCG (CC0; licencia verificada por el responsable técnico en https://docs.ambientcg.com/license/, no releída hoy):
- La API v2 responde. Ningún material encontrado tiene el dibujo de laja poligonal clara: la búsqueda `PavingStones` no da resultados y `paving` da 165, todos de adoquín o cantería regular.
- Posibles, por etiquetas: `PavingStones150` ("beige", "rustic"; 1K-JPG zip: 5.336.973 B), `Tiles139`, `Tiles142`, `Tiles143` (baldosas de caliza regulares; 4,8–5,1 MB).
- Los zips pesan 4,9–9,4 MB en 1K porque llevan más mapas, y no se pueden bajar mapa a mapa. **No recomendado** frente a Poly Haven.

Alternativa de procedencia propia: la foto 26 (CC BY 3.0) permitiría rectificar un trozo de firme y sacar un albedo real, con atribución. No lo recomiendo: la luz es dura, las lajas son pocas y quedaría una repetición visible.

## 5. Lista de descarga (para aprobar; nada descargado)

Los recursos de referencia irían a `data/manual/fotos-referencia/commons/` (fuera de git), con el mismo `README` que las 15 actuales. Las texturas irían al catálogo con `expected_bytes` y sha256.

| # | URL | Nombre propuesto | Bytes | Licencia | Autor | Para qué | Uso |
|---|---|---|---|---|---|---|---|
| 1 | https://upload.wikimedia.org/wikipedia/commons/0/02/Centre_de_visitants_del_penyal_d%27Ifac.JPG | `J1-centre-visitants-arcada.JPG` | 1.604.739 | CC BY-SA 3.0 | Joanbanjo | Pórtico de arcos, torretas, lucernario, puerta | referencia |
| 2 | https://upload.wikimedia.org/wikipedia/commons/7/70/Centre_de_visitants_del_penyal_d%27Ifac_des_de_dalt.JPG | `J2-centre-visitants-des-de-dalt.JPG` | 3.100.483 | CC BY-SA 3.0 | Joanbanjo | Conjunto: forma, cubiertas, patio, pérgolas, camino | referencia |
| 3 | https://upload.wikimedia.org/wikipedia/commons/5/50/Penyal_d%27Ifac%2C_centre_de_visitants.JPG | `J3-centre-visitants-patio.JPG` | 1.777.793 | CC BY-SA 3.0 | Joanbanjo | Cara S del ala norte, patio, papeleras, empedrado | referencia |
| 4 | https://upload.wikimedia.org/wikipedia/commons/c/c7/Le_penon_de_ifach_-_panoramio_(2).jpg | `chisloup-penon-explanada-2.jpg` | 5.067.776 | CC BY 3.0 | chisloup | Explanada de gravilla y un edificio al pie | textura (con atribución) / referencia |
| 5 | https://upload.wikimedia.org/wikipedia/commons/b/b0/Calpe_-_panoramio_(59).jpg | `chisloup-calpe-59.jpg` | 976.896 | CC BY 3.0 | chisloup | Panorámica desde el sendero con la cubierta del centro en primer plano | textura (con atribución) / referencia |
| 6 | https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/stone_tiles_02/stone_tiles_02_diff_1k.jpg | `stone_tiles_02_diff_1k.jpg` | 817.710 | CC0 | Charlotte Baglioni | Lajas del sendero (E1.2) | textura |
| 7 | …/stone_tiles_02/stone_tiles_02_nor_gl_1k.jpg | `stone_tiles_02_nor_gl_1k.jpg` | 873.564 | CC0 | idem | idem | textura |
| 8 | …/stone_tiles_02/stone_tiles_02_arm_1k.jpg | `stone_tiles_02_arm_1k.jpg` | 623.281 | CC0 | idem | idem | textura |
| 9 | …/patio_tiles/patio_tiles_diff_1k.jpg | `patio_tiles_diff_1k.jpg` | 700.816 | CC0 | Dario Barresi | Suelo del pórtico (E3) | textura |
| 10 | …/gravel_floor_04/gravel_floor_04_diff_1k.jpg | `gravel_floor_04_diff_1k.jpg` | 952.532 | CC0 | Poly Haven | Gravilla (tramo alto, pista, explanada) | textura |
| 11 | …/gravel_floor_04/gravel_floor_04_nor_gl_1k.jpg | `gravel_floor_04_nor_gl_1k.jpg` | 1.287.582 | CC0 | idem | idem | textura |
| 12 | …/gravel_floor_04/gravel_floor_04_arm_1k.jpg | `gravel_floor_04_arm_1k.jpg` | 749.840 | CC0 | idem | idem | textura |
| 13 | …/asphalt_04/asphalt_04_{diff,nor_gl,arm}_1k.jpg | `asphalt_04_*_1k.jpg` | 880.083 + 986.045 + 554.776 = 2.420.904 | CC0 | J. van Heerden / S. Majboroda | Asfalto de las avenidas (solo si se hace E5) | textura |

(Las filas 6–13 usan la base `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/<id>/…`; los "…" la abrevian.)

Totales:

| Conjunto | Bytes | MB (10⁶) |
|---|---|---|
| Referencias CC BY-SA 3.0 (filas 1–3) | 6.483.015 | 6,48 |
| Fotos CC BY 3.0 (filas 4–5) | 6.044.672 | 6,04 |
| Texturas mínimas (6–12: `stone_tiles_02` × 3, `patio_tiles` diff, `gravel_floor_04` × 3) | 6.005.325 | 6,01 |
| Asfalto (fila 13, opcional) | 2.420.904 | 2,42 |
| **Total propuesto** | **20.953.916** | **20,95** |
| Mínimo útil (solo texturas, sin fotos ni asfalto) | 6.005.325 | 6,01 |

No se proponen: fotos de Flickr (inaccesible), fotos históricas de historiadecalp.net (de 20–27 KB, de procedencia y licencia desconocidas, sin utilidad para comparar con los edificios actuales) y las fotos de la web de accesibilidad (con derechos).

## 6. Lo que sigue sin respuesta tras una búsqueda razonable

| Pregunta | Qué se intentó | Qué haría falta |
|---|---|---|
| Año de apertura, arquitecto y proyecto de los edificios | Búsquedas en español y catalán, BOE/DOGV 1990–94, contratación (nada específico), prensa, MARQ | Preguntar al Servicio de Espacios Naturales de la GVA o al archivo municipal de Calp; hemeroteca de 1990–95 |
| Cuál es el Centro de Información y cuál el de Visitantes | Páginas de la GVA (solo fragmentos), OSM, Wikipedia, blogs | Pregunta directa al parque, o plano de planta |
| Fachadas N y O, ala oeste, edificio este (puertas, ventanas) | Commons (cuatro fotos del centro en total), Mapillary (sin acceso), KartaView (sin cobertura) | Fotos propias, Mapillary mirado a mano en el navegador, o Google Street View si hay |
| Número real de arcos, ventanas y puertas | Conteo en fotos | Plano o fotos de cada fachada |
| Medidas de arcos, puerta, zócalo | Estimación en §2.4 | Una medida de campo, o el LiDAR del pórtico (clase 6) en el alero |
| Escaleras: contrahuella, huella, ancho, barandilla (altura, lado, material) | Nada publicado | Medida en el sitio; o foto con un objeto de tamaño conocido |
| Torno, fuentes, papeleras, paneles, bancos: modelo y medidas | Fotos parciales | Fotos de frente y de lado |
| Manual de señalización 2011 | DOGV y buscadores | Pedirlo a la Conselleria; revisar si `mediambient.gva.es` lo publica |
| Distancia real entre la barrera y el centro | OSM da 185 m; un blog de 2021 dice 800 m | Mapa del parque o medida GPS |
| Texto vigente del PRUG (zona de servicios) | DOGV escaneado | Texto consolidado en `dogv.gva.es` |
| Capa de zonificación del PRUG (datos abiertos) | El conjunto `prug-del-penyal-difac-zonificacion-prug` en `dadesobertes.gva.es` da 404 | Buscar otro identificador del conjunto |

## 7. Conflictos entre fuentes

| Dato | Versión A | Versión B | Cómo tratarlo |
|---|---|---|---|
| Fecha de las "casas réplica" | 1992 (`facts.json`, sin fuente) | "Después de 1987", sin año (historiadecalp.net, 2005); centro ya existente en 2005 (MARQ) | No afirmar 1992; "después de 1987" es lo firme |
| Distancia puerta–centro | 800 m, unos 10 minutos (EscapadaRural, feb. 2021) | OSM: barrera de vehículos a 185 m; puertas peatonales a 190–290 m | Probable que el blog cuente desde otra puerta o desde la rotonda; usar OSM para la geometría |
| Aforo | 150 dentro del parque y 20 cada 15 min (2011, 2018, 2020) | 300 al día con reserva (GVA, desde dic. 2020) | Ya registrado en `003-entorno-construido.md` |
| Aparcamiento | Solo acreditados (GVA) | Gravilla libre y gratuita (blogs) | Son dos sitios: el aparcamiento del centro (acreditados) y la explanada pública del final de la calle |
| Longitud de la ruta | 1,6 km ida y vuelta hasta el túnel (GVA, fragmento) | 4,6–5 km a la cima (blogs) | Alcances distintos |
| Nombre del centro | "Centro de Interpretación" (OSM, blogs) | "Centro de Información" y "Centro de Visitantes" (GVA) | Citar el nombre de la GVA en la app |
| Firme del sendero | `unhewn_cobblestone` (OSM) | Lajas poligonales con mortero (fotos) | Las fotos mandan (ya anotado) |
| Fuentes | Fuentes "solo al inicio" (`access-safety`) | Dos grifos en OSM, uno pasado el torno | Compatible: están en el arranque |
| Teléfono del centro | +34 965 83 75 96 (OSM, `way/26330271`) | 965 693 300 y 679 195 912 (GVA, fragmento) | No usar el de OSM sin comprobarlo |
| "Puente" tras el tramo fácil | EscapadaRural: el primer tramo "llega hasta un puente" | OSM: ningún puente en el sendero | Casi seguro es el túnel; no modelar un puente |

## 8. Fuentes

Fecha de consulta: 2026-10-12, salvo indicación. "Lectura" = página leída; "fragmento" = resumen de buscador; "imagen vista" = imagen abierta por la caché de `WebFetch`.

| Id propuesto | URL | Acceso | Uso | Qué aporta |
|---|---|---|---|---|
| `commons-joanbanjo-centre` | https://commons.wikimedia.org/wiki/Category:Penyal_d%27Ifac_Visitor_Centre | Lectura de API + imágenes vistas | referencia (CC BY-SA 3.0) | Tres fotos de 2013 del centro |
| `commons-chisloup-panoramio` | https://commons.wikimedia.org/wiki/File:Calpe_,_penon_de_ifach_-_panoramio.jpg y fotos 5, 7, 13, 16, 17, 26, 28 (locales) y (2), (59), (60)–(63) (vistas) | Imágenes vistas | textura / referencia (CC BY 3.0) | Foto 1 y firmes |
| `commons-tagzania-2026` | https://commons.wikimedia.org/wiki/File:Pe%C3%B1on_de_Ifach_-_Penyal_d%27Ifac_Natural_Park_-_Tagzania_-_1777543739475.jpg (y 3 más) | Imágenes vistas | referencia (CC BY-SA 4.0) | Explanada de gravilla, barandilla junto a la Pobla |
| `historiadecalp-ifach` | http://historiadecalp.net/ifach.htm | Lectura | referencia (texto local) | Casas de París, hotel, "dos imitaciones" |
| `auntirdepedra-ifac` | https://www.auntirdepedra.com/2010/12/el-penyal-difac.html | Lectura | referencia | Réplicas; sendero empedrado con baranda de madera |
| `eltemps-1987` | https://www.eltemps.cat/documents/el-temps_1987_02_0137_0022_0023.pdf | PDF decodificado (capa de texto) | referencia | Dos casas, obras del hotel, propuesta de exposición |
| `marq-2005-infra-centro` | https://www.marqalicante.com/contenido/int_arqueologicas/57%20Infraestructuras%20para%20el%20Centro%20de%20Informaci%C3%B3n%20del%20Parque%20Natural%20del%20Pe%C3%B1%C3%B3n%20de%20Ifach%20%28Calp%29.pdf | PDF decodificado | referencia | Zanja de servicios al centro, 2005, VAERSA |
| `marq-2006-sector-norte` | https://www.marqalicante.com/contenido/int_arqueologicas/72%20Parque%20Natural%20del%20Penyal%20d%27Ifac%20%28Calp%29.pdf | PDF decodificado | referencia | "Centro de Visitantes y el Museo del Parque"; Miradores de Levante |
| `gva-parque` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/centro-de-visitantes ; `.../accessibilitat-al-parc` ; `.../ruta-roja-descripcion` ; `.../como-llegar` | **Solo fragmentos** (el portal no responde) | referencia | Horario, exposición, rampas, torno, aparcamiento de acreditados, talanqueras |
| `gva-res-2011-senalizacion` | https://noticias.juridicas.com/base_datos/CCAA/va-res250311-maauv.html y https://www.iustel.com/diario_del_derecho/noticia.asp?ref_iustel=1049126 | Fragmento (el primero no responde; el segundo, lectura) | dato (normativa) | Resolución de 25-03-2011 |
| `equalitasvitae` | https://equalitasvitae.com/turismo-accesible/parque-natural-penon-de-ifach/ | Lectura | referencia | Rampas, aseos, circuito de Levante, bancos y paneles |
| `hola-2020` | https://www.hola.com/viajes/20200721172373/verano-en-calpe-alicante-excursion-al-penon-de-ifach/ | Lectura | referencia | Torno, vía sin asfaltar, mirador de Levante |
| `conmochila` | https://www.conmochila.com/penon-de-ifach | Lectura | referencia | "Torno que inicia la ruta", agua y baño |
| `escapadarural-2021`, `viewfromlavila-2025`, `bouger-voyager-2022`, `sendasyleyendas-2022`, `geoelx-2008` | https://www.escapadarural.com/blog/ascenso-al-penon-de-ifach-calpe/ ; https://viewfromlavila.com/climbing-el-penon-difach/ ; https://www.bouger-voyager.com/penon-de-ifach-randonnee/ ; https://sendasyleyendas.com/2022/01/penon-de-ifach-calpe/ ; http://geoelx.blogspot.com/2008/02/mapa-ruta-pen-difach.html | Lectura | referencia (con derechos) | Aparcamiento, reservas, barrera, aula |
| `osm-penyal` | `data/raw/osm-penyal/osm-penyal.json` (ya bloqueado en `manifest.lock.json`) | Lectura local | dato (ODbL) | Huellas, torno, escaleras, grifos, puertas, aparcamiento |
| `catastro-bu-wfs` | http://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx (`GetBuildingByParcel`, refcat 7715618YH6871S) | Lectura | dato | **Vacío**: la parcela del centro no tiene edificios en el Catastro; no sirve para fecha ni plantas |
| `polyhaven-api` | https://api.polyhaven.com/assets ; `/files/<id>` ; `/info/<id>` ; licencia https://polyhaven.com/license | Lectura | textura (CC0) | Candidatos y tamaños |
| `ambientcg-api` | https://ambientcg.com/api/v2/full_json | Lectura | textura (CC0) | Sin material adecuado |
| `urbadep-talanquera` | https://urbadep.com/wp-content/uploads/2025/02/TALANQUERA-URBADEP.pdf | Fragmento | referencia | Tipología de talanquera |
| `cte-sua-normatia` | https://normatia.com/es/normativa/cte-db-sua/2022/seccion-sua-1-seguridad-frente-al-riesgo-de-caidas/ | Lectura | referencia (último recurso) | Valores del DB-SUA 1 |

Antes de usar cualquier cosa de esta tabla en `content/facts.json`, dar de alta la fuente en `content/sources.json` y comprobar la política de la página (varias son blogs y webs comerciales).

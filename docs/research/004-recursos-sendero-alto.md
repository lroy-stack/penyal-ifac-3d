# 004 — Recursos para modelar el sendero alto (fin del tramo piloto → túnel → cima y Mirador de Carabiners)

- Fecha: 2026-10-12. Trabajo de investigación en línea; no se ha editado ningún otro archivo del repositorio ni se ha hecho commit.
- Alcance: lo que hace falta para modelar con fidelidad la ruta desde el final del tramo piloto (≈ 417 m desde el inicio del acceso) hasta la cima y el ramal del Mirador de Carabiners: firme y anchura, túnel, equipamiento de seguridad, puntos de interés y mobiliario, normas y cierres.
- Contexto leído antes de empezar: `CLAUDE.md`, `003-inventario-datos-propios.md`, `003-entorno-construido.md`, `003-fotos-referencia.md`, `specs/003-entorno/propuesta.md`, `specs/002/protocolo-fotos.md`, `CREDITS.md`, ADR 0006/0007/0009, `data/curated/tunnel.toml`, `content/facts.json`, `trail.json`, el extracto OSM y los datos IGN/ICV ya descargados.
- Nada de lo que sigue es la ubicación de una planta de *Silene hifacensis*. Tampoco se describe a personas que salgan en las fotos.

## Cómo se leyó y qué no se pudo leer

- Leyenda de fiabilidad usada en todo el documento:
  - **[V]** fuente primaria leída (documento oficial o dato abierto);
  - **[S]** fuente secundaria leída (prensa, guía, blog, web turística);
  - **[F]** solo fragmento de un buscador, sin leer la página;
  - **[P]** observación hecha mirando una foto (se dice cuál);
  - **[E]** cálculo o estimación propia, con su método, siempre aproximada;
  - **[N]** no encontrado tras búsqueda razonable.
- Herramientas: WebFetch y WebSearch, la API de Wikimedia Commons y nuestros datos locales (`osm-penyal.json`, `trail.json`, MDT y LiDAR del ICV). No se ha descargado nada en el repositorio.
- **Efecto lateral que hay que declarar:** WebFetch guarda por su cuenta las respuestas binarias (imágenes y PDF) en la caché de la herramienta, fuera del repositorio (`~/.claude/projects/…/tool-results/`). Así se pudieron *mirar* las fotos y leer tres PDF. Además copié tres PDF (reseña IGN, PRUG, documento IGN de teoría) al directorio temporal de la sesión para extraerles el texto. Todo es borrable; nada entra en `data/`.
- **No accesibles desde esta sesión** (sin que eso demuestre que no haya nada):
  - `parquesnaturales.gva.es` (ECONNREFUSED a 195.77.20.68:443, otra vez; el addendum de 003 ya dice que estos portales solo tienen IPv4);
  - `web.archive.org`, `archive.ph` e `informacion.es` (bloqueados por la herramienta); `wikiloc.com` y `deandar.com` (HTTP 403);
  - Flickr y Mapillary (aplicaciones solo JavaScript: sin resultados legibles);
  - plataformas de contratación (la búsqueda web no devolvió ningún expediente del parque; los portales exigen consulta interactiva).
- Los textos de la GVA que ya están en `content/facts.json` (folleto, descripción de la Ruta Roja, recomendaciones) **no se han releído**; aquí se citan por su identificador de fuente.

---

## 0. Resumen (lo que cambia para el modelado)

1. **El vértice geodésico de la cima ya tiene especificación oficial.** Reseña del IGN nº 84878 «Ifac», construido el 11/12/1987: pilar cilíndrico de 1,20 m de alto y 0,30 m de diámetro, sin centrado forzado, sobre un único cuerpo de base de 0,20 m de alto y 1,00 m de ancho. Es el pilar estándar de la Red de Orden Inferior (ROI) según el propio IGN [V]. Cota de la base: 326,714 m. Foto del IGN de marzo de 2010: la cabeza del pilar está rota, con un lazo de armadura asomando [P].
2. **Eso resuelve (casi) el conflicto de la altitud.** En el marco del proyecto el vértice está en (x 616,03; z −758,43), a 4,75 m del nodo OSM de la cima. El MDT lee 326,68 m ahí (−0,03 m respecto al IGN) y los dos retornos LiDAR más altos en 30 m a la redonda (328,07 m) están a 0,37 y 0,46 m de esas coordenadas: lo más probable es que **los 328,07 m del LiDAR sean la cabeza del pilar, no la roca** [E]. Los 332 m oficiales siguen sin apoyo en ningún dato medido.
3. **Túnel:** sigue sin existir ninguna anchura ni altura publicada [N]. Lo nuevo es de otro tipo: el pasamanos interior **cambió con los años** (cuerdas hasta 2014, obras de 2016 que «renovaron las cuerdas», cadena negra visible en la boca oeste en una foto de 2019) y la geometría OSM sugiere un **quiebro de unos 14° en los 12 m cercanos al portal oeste**.
4. **Equipamiento de seguridad por encima del túnel:** hay una historia documentada. Antes de 2015, cuerdas («pasarelas de cuerda») y una cadena clavada en la roca; cierre de la senda superior de abril de 2015 a agosto de 2016; obras de 2016 (Vaersa): firme nivelado y ensanchado, muros de mampostería en los puntos peligrosos, cadenas en tramos concretos, cuerdas renovadas, señalización cambiada, firme del túnel tratado contra el resbalón [S]. Alturas, grosores y materiales: [N].
5. **Plataforma tras el túnel:** OSM tiene un mirador sin nombre a 1,9 m del portal este (nodo 3635481353). Una foto de 2013 muestra desde dentro del túnel una **valla de madera de dos largueros y un risco claro justo a la salida** [P].
6. **Mirador de Carabiners:** de «ruinas» no hay ninguna descripción física en ninguna fuente. Lo visible en fotos de 2013 es una **explanada de roca desnuda y un poste cuadrado de acero inoxidable con la parte superior pintada de rojo** al borde del cantil [P]. El sendero de acceso es estrecho y de tierra con piedras, sin barandilla [P] (OSM lo etiqueta `surface=rock`, que no encaja).
7. **Cima:** no hay bancos, mesa ni cruz documentados (OSM: `summit:cross=no`, `summit:register=no`). El camino final se marca con círculos rojos pintados en la roca [S].
8. **Normas con fuente y fecha:** reserva obligatoria más allá del torno, 300 al día (PRUG art. 26 de 1993, «en principio»; Junta Rectora 2020). La web del Ayuntamiento de Calp del 21/07/2026 dice «hasta 10 días de antelación» y una noticia del 09/10/2026 dice «al menos cuatro días»: **contradicción abierta**. El PRUG restringe el «camino del mirador» de abril a junio por cría; no he encontrado nada que confirme que hoy se aplique.
9. **Hallazgo fuera de alcance:** una fuente local (A. Ortolà, 2005) afirma que las dos casas de Vicente París fueron derribadas y que «se construyeron dos imitaciones» para el Aula de la Naturaleza. Es la primera fuente que sostiene la nota sin fuente de `facts.json` sobre las «casas réplica» (ver §9).

---

## 1. El recorrido por tramos (datos propios + fuentes)

Distancias acumuladas en planta desde el inicio del tramo `access` de `trail.json` (así el final del tramo piloto cae en 416,6 m, que es el «≈ km 0,42» del protocolo de fotos). Pendientes: medianas y percentiles sobre ventanas de 10 m de la línea de OSM con alturas del MDT [E]; el MDT suaviza los resaltes, así que las trepadas reales son más empinadas que el dato.

| Tramo (`trail.json`) | Desde → hasta (m) | Largo 2D | Altura | Pendiente | OSM (etiquetas) |
|---|---|---|---|---|---|
| `centre-path` (resto tras el piloto) | 416,6 → 796,6 | 380 | 119 → 168 m | mediana 14,5 %; p90 21,6 %; máx. 27,4 % (a 517 m) | `surface=unhewn_cobblestone`, `sac_scale=hiking` |
| `portal-steps` | 796,6 → 813,3 | 16,7 | 168,4 → 171,0 | — | `highway=steps`, `step_count=6`, `handrail=yes`, `surface=rock`, `sac_scale=hiking` |
| `tunnel` | 813,3 → 862,6 | 49,3 (54,0 en 3D) | 171,0 → 193,0 (curado) | media 45 % (≈ 24°) | `tunnel=yes`, `surface=rock`, `sac_scale=demanding_mountain_hiking` |
| `tunnel-bifurcation` | 862,6 → 1217,6 | 355,0 | 193,0 → 225,2 | mediana 9,1 %; p90 22 %; **dos ventanas de 49–54 % a 50–80 m del portal este** | `path`, `surface=rock`, `smoothness=very_bad`, `sac_scale=demanding_mountain_hiking` |
| `summit-ascent` | 1217,6 → 1753,2 | 535,6 | 225,2 → 325,4 | mediana 20 %; p90 39,5 %; máx. 55 % (tramos a 70–100, 150–180 y 440–510 m de la bifurcación) | `path`, `surface=rock`, `smoothness=very_bad`, `sac_scale=demanding_mountain_hiking` |
| `carabiners-branch` | bifurcación → +259,2 | 259,2 | 225 → 226 | mediana 1,2 %; máx. 33 % | misma vía OSM 26330276 que el tramo hasta la bifurcación |

### 1.1 Firme y anchura por tramo

| Tramo | Firme | Anchura | Cambio / dónde | Fuente |
|---|---|---|---|---|
| Final del piloto → portal oeste (km 0,42 → 0,81) | Losas irregulares de caliza clara asentadas con mortero, con arcenes de grava fina a ambos lados y, en algún punto, un borde de tablones de madera en el lado de la ladera [P] | ≈ 1,5 m de losas, ≈ 2–2,5 m con arcenes. **[E]** Estimación en dos fotos de 2013 (Joanbanjo) tomando el poste de la barandilla como 1,0–1,1 m de alto; error probable ±0,4 m | El firme sigue enlosado hasta cerca del portal; **en la terraza exterior del portal oeste pasa a grava compactada** (foto chisloup 2014, nº 28 del repositorio) [P] | Fotos [P]; OSM `unhewn_cobblestone` no describe el aspecto real (ya señalado en 003) |
| Terraza y escalones del portal oeste | Grava compactada; luego 6 escalones de piedra (OSM) | **[N]** | Foto 2019 (nº 38 del repositorio): al menos 5 escalones de bloques de caliza labrados y en parte tomados con mortero, que suben a la boca; los últimos son roca tallada [P] | OSM; foto |
| Túnel | Roca caliza pulida, muy resbaladiza; en una foto de 2013 está mojada y brilla [P] | **[N]** (ver §2) | Las obras de 2016 «trataron» el suelo contra el deslizamiento [S] | calpdigital 2016-08-10 [S]; La Veu 2016-08-09 [S] |
| Portal este → bifurcación | «Senda irregular, bien marcada» [S]; roca pulida y tierra; algunos pasos con cadenas y uso de manos [S]. Foto 2013: sendero estrecho de tierra y roca sobre ladera de roquedo [P] | **[N]**; las obras de 2016 «ensancharon» el firme en puntos concretos [S] | Hasta la bifurcación hay unos 15 min a pie según un blog [S] | Blogs [S] (ver §3.2) |
| Bifurcación → cima | Roca caliza pulida «muy resbaladiza»; trepada fácil con las manos; círculos rojos pintados en la roca [S] | **[N]** | Es el tramo «más montañero» (blogs) [S]; coincide con las ventanas de 40–55 % de pendiente del MDT [E] | Blogs [S] |
| Ramal de Carabiners | Tierra compactada con piedras sueltas y una línea de piedras de caliza como borde en el lado del cantil; pinos [P] | Una persona; **[N]** en cifras | Casi plano (1,2 % mediana) [E]. Contradice `surface=rock` de OSM [P] | Foto Joanbanjo 2013 [P] |

**Contradicción de posición (Carabiners):** una guía (`sendasyleyendas.com`, 2022) lo sitúa «a unas decenas de metros» tras la salida del túnel. Nuestro `trail.json` (OSM) lo pone a **614 m de recorrido** tras el portal este (355 m hasta la bifurcación + 259 m de ramal). Prevalece el dato de OSM y las fotos con hora; la guía está equivocada o habla de otra cosa [S frente a V-OSM].

**Cruce de cifras con una fuente secundaria:** un blog (`cristabeldeviaje.com`) dice que en el cruce el cartel marca la cima a unos 500 m; en `trail.json` hay 535,6 m de bifurcación a cima. Coincide en orden de magnitud [S, E].

---

## 2. El túnel (OSM `way/26330275`) y los 6 escalones del portal oeste (`way/862108208`)

### 2.1 Qué dicen las fuentes

| Dato | Valor | Fuente | Fiabilidad |
|---|---|---|---|
| Construcción | 1918, por iniciativa del propietario Vicente París Morlá; para no rodear la pared norte | `gva-historia` (registro); `macma.org` 2026 («1918 por uno de los amos del Peñón»); calpe.es leído el 2026-10-12 | [V/S] |
| Quién y cómo | París «emprendió la ingente tarea de construir un túnel»; **no hay fecha, medidas ni obreros** en la fuente local | `historiadecalp.net/ifach.htm`, A. Ortolà Tomás, febrero de 2005 | [S] |
| «Dinamita» | Una guía en inglés dice que fue idea de París usar dinamita. Foto de 2013 de un **barreno** en la roca con fracturas radiales, titulada «Restes d'una explosió de dinamita» [P], tomada 4 min antes de la foto del túnel; no se sabe dónde | Commons: *Restes d'una explosió de dinamita* (Joanbanjo) | [S/P] |
| Longitud | ≈ 50 m (GVA folleto y Ruta Roja, registro); **30 m (calpe.es, leído hoy)**; **49,3 m en planta en OSM (54,0 m en 3D)**; ~100 m (blog); «180 m» (blog, error evidente) | registro; calpe.es; OSM | **Conflicto**, ya recogido en `tunnel-length` |
| Ancho y alto | **[N]**. Ninguna fuente oficial ni publicada | — | — |
| Iluminación | Sin luz; «se ve lo suficiente» con la luz de las bocas [S]; conviene linterna de móvil [S]. La prensa de 2015 dice que se avanza «casi a tientas» hasta acostumbrar la vista | Picobarro 2021; siguiendolasenda; La Marina 2015 | [S] |
| Suelo | Roca pulida por el paso, muy resbaladiza; obras de 2016 lo trataron | GVA (registro); calpdigital 2016 | [V/S] |
| Pasamanos | GVA: «dos cuerdas de apoyo» (registro). Ver §2.3 sobre cuerda frente a cadena | — | **Conflicto en el tiempo** |
| Plataforma de salida | Sí (GVA, registro); ver §4.1 | — | — |

### 2.2 Forma y geometría (lo que se puede sacar con apoyo)

- **Eje y quiebro [V-OSM, E]:** la vía OSM tiene tres nodos: portal este (762,17; −817,05), un nodo intermedio (728,73; −833,71) y portal oeste (717,03; −836,19). Tramos de 37,4 m (rumbo 116,5° de oeste a este) y 11,9 m (rumbo 102°). Es decir, **≈ 14° de quiebro a 12 m del portal oeste**. El nodo intermedio es reciente (id 14165597594), lo añadió alguien con imagen o traza; precisión desconocida. Una foto de 2014 desde la boca oeste (nº 27 del repositorio) muestra la salida lejana como una ventana pequeña desplazada a la derecha, compatible con una curva suave [P].
- **Boca oeste [P]:** foto de 2014 (nº 21 del repositorio): vano más alto que ancho, de contorno irregular, tallado en roca; fuera, escalones de roca y un muro bajo de piedra seca. Foto de 2019 (nº 38): boca de contorno casi rectangular con arco irregular de bloques apilados; en la pared interior, una placa pequeña oscura; en el borde de la imagen, el extremo aserrado de un tronco redondo (poste o larguero de una valla).
- **Interior [P]:** bóveda ovoidal sin revestimiento, con marcas de trabajo; en la foto nº 27 del repositorio, un resalte tipo repisa en la pared izquierda cerca de la entrada y una placa pequeña oscura en lo alto de la pared; suelo de roca pulida con pendiente ascendente hacia el este (foto Joanbanjo 2013 «Túnel del penyal d'Ifac»).
- **Boca este [P]:** foto de 2013 desde dentro: contorno ovoidal; fuera, **una valla de madera con dos largueros horizontales** y, detrás, **un risco claro de roca** muy cerca de la salida. No tengo certeza del sentido de la toma (la hora EXIF, 16:08, apunta a un descenso; la pendiente del suelo en la foto sugiere que la cámara está en el extremo bajo mirando a la salida alta). Se anota como interpretación.
- **Escala:** ninguna de las fotos contiene un objeto de dimensión conocida. **No se puede medir** ancho ni alto con fotos de internet; el valor curado (2,0 × 2,6 m, rangos 1,5–2,5 y 2,2–3,2 m) sigue siendo un marcador. Las fotos solo apoyan «unas dos personas de ancho» (ya dicho en `tunnel.toml`).

### 2.3 Pasamanos del túnel a lo largo del tiempo

| Año | Qué se ve o se dice | Fuente |
|---|---|---|
| 2005–2010 | «Hay pasamanos de cuerda donde la roca puede estar más resbaladiza»; «pasarelas de cuerda» en los tramos más expuestos | Apatita (mayo de 2007) [S] |
| 2013-11 | Dos cuerdas oscuras, una por pared, con remate colgante y anclajes metálicos | Joanbanjo [P] |
| 2014-05 | Cuerdas de fibra (crema en la foto nº 27, más oscuras en la nº 21, con luz distinta), con nudos y argollas metálicas empotradas en la roca, una por pared | chisloup, fotos nº 21 y 27 del repositorio [P] |
| 2015-06 | El túnel está sin luz y muy resbaladizo; el único elemento de protección en la senda alta es «una cadena clavada en la roca» | La Marina, 2015-06-26 [S] |
| 2016-08 | Obras de la senda de la cima: «se renovaron las cuerdas del túnel y de varios puntos»; firme del túnel tratado | calpdigital, 2016-08-10 [S]; nota GVA de reapertura [F] |
| 2019-02 | **Cadena negra** colgada en catenaria por la pared izquierda de la boca oeste | Donarreiskoffer, foto nº 38 del repositorio [P] |
| 2020–2026 | Guías hablan de «cuerdas o cadenas» (blogs), «cuerda a modo de pasamanos» (siguiendolasenda), y GVA/Calpe de «cuerdas» | [S] |

**Conclusión:** el modelo debe aceptar las dos opciones. Mientras no haya una foto reciente del interior, lo defendible es **dos líneas de apoyo, una por pared, ancladas a argollas de la roca; material cuerda o cadena según fecha**. El estado actual **[N]**: se pide al parque (§7) o a una visita.

### 2.4 Los 6 escalones del portal oeste

- OSM: `step_count=6`, `handrail=yes` (sin lado). Foto de 2019 (nº 38): **se cuentan al menos cinco escalones de bloque labrado** y varios de roca tallada hacia la boca [P]. No hay barandilla de madera a la vista en el encuadre; sí hay un tronco redondo en el borde izquierdo y una cadena dentro de la boca [P].
- Altura de contrahuella: **[N]**. El valor del proyecto (0,18 m, rango 0,15–0,20) sigue siendo una suposición (`tunnel.toml`).

---

## 3. Equipamiento de seguridad por encima del túnel

### 3.1 Normativa que limita lo que puede existir

- **PRUG (Decreto 260/1993, DOGV 2.190, 21-01-1994, leído por OCR el 2026-10-12) [V]:**
  - art. 16.1: se prohíben, con carácter general, obras de infraestructura; art. 16.2: **no se permiten caminos distintos de los existentes**, y restaurar un camino exige informe aprobado por la Conselleria; art. 16.3: no se permiten edificaciones fuera de las existentes.
  - art. 33: la «zona de uso público» incluye «la senda que, partiendo del centro de información, atravesando el túnel, llega hasta la cumbre», más el área de servicios: centro de información, **«centro de recepción-aula de la naturaleza», cafetería y área de acogida**.
  - art. 26.3.h: se prohíbe hacer señales o pintadas en el parque (el vértice y el poste de Carabiners tienen pintadas [P]).
- **Consecuencia para el modelado:** todo el trazado y las obras visibles son anteriores a 1993 o son «restauraciones» de lo existente. No hay que inventar senderos nuevos.

### 3.2 Qué hay, por fuente (no hay medidas en ninguna)

| Elemento | Dónde | Descripción | Fuente | Fiabilidad |
|---|---|---|---|---|
| Cadenas fijas | Tramo expuesto entre el túnel y la bifurcación («unos 15 min») | «Cadenas fijadas a la pared del acantilado»; «tras dos tramos con cadenas se llega al cruce» | mappingspain.com; cristabeldeviaje.com | [S] |
| Cadenas y cuerdas | Pasos «complicados o expuestos» de la subida | Hay cadenas y cuerdas; «jala la cadena antes de agarrarla» | siguiendolasenda.es; cristabeldeviaje.com | [S] |
| Cadenas, «ocasionales» | Tras el túnel | «cadenas fijas ocasionales y escalones» | lucasgraphic.com (2023, actualizado 2026-02-09) | [S] |
| Escalones | Subida, «tramo final» | Escalones tallados o sendero ensanchado tras unas obras (texto sin fecha, probablemente el de 2016) | EcuRed y un blog, solo en fragmento de buscador | [F, débil] |
| Muros de mampostería | «Puntos más peligrosos» | Construidos o reparados en 2016 | calpdigital 2016 | [S] |
| Valla de madera | Boca oeste, terraza | Postes redondos con dos largueros, algunos con tornapuntas; muro de piedra seca con albardilla por el lado del vacío | chisloup 2014 (nº 28), Joanbanjo 2013 [P] | [P] |
| Cadena clavada en la roca | Senda alta | «el único elemento de protección», 2015 | La Marina 2015 | [S] |
| Puerta y murete de cierre | Entrada a la senda alta | Instalados en junio de 2015 para impedir el paso | La Marina 2015 | [S] |

### 3.3 Obras documentadas

| Fecha | Qué | Quién / cuánto | Fuente |
|---|---|---|---|
| 2005 | «Última rehabilitación» según el cartel del lugar, financiada por la UE y la Administración autonómica | **[N]** detalle | La Marina, 2015-06-26 [S] |
| Abril de 2015 | Cierre de la senda superior por falta de seguridad; puerta y murete | Conselleria de Medio Ambiente | La Marina 2015; La Veu 2016 [S] |
| Junio de 2016 (inicio el 8 de junio según un fragmento de prensa [F]) → 10 de agosto de 2016 | Obras de adecuación y mejora de la seguridad del tramo túnel-cima: remodelado del trazado, firme nivelado y ensanchado, muros de mampostería, retirada de las zonas de más pendiente y riesgo, cadenas en tramos concretos, cuerdas renovadas (túnel y varios puntos), señalización sustituida, firme del túnel tratado | **Vaersa**; **≈ 50.000 €** (calpdigital) frente a **«poc menys de 40.000 €»** (La Veu): contradicción | calpdigital 2016-08-10; La Veu 2016-08-09; nota de la GVA (`parquesnaturales.gva.es/va/web/pn-penyal-d-ifac/noticias/…/reapertura-del-itinerario…`) vista solo como fragmento [F] |
| Reapertura | **10 de agosto de 2016** (según calpdigital, el día anterior se habían contado 1.120 visitas en la parte abierta del parque) | — | calpdigital [S] |
| 16 y 17 de junio (año **no consta**) | Cierre del Peñón «por las obras de acondicionamiento de la senda de acceso a la cima»; la imagen de la noticia está en la carpeta de noviembre de 2019 | Ayuntamiento de Calp | calpe.es [S] |

---

## 4. Puntos de interés y mobiliario

Posiciones: distancia acumulada y cota desde `trail.json` y OSM [E]. «Candidato» significa que la posición sale de nuestra secuencia, no de una fuente.

### 4.1 Plataforma tras el túnel

- **Qué se sabe:** GVA (registro `tunnel-condition`, `ibiza-view`): hay una plataforma a la salida y desde ella se ve Ibiza en días excepcionalmente claros. OSM tiene el mirador sin nombre `node/3635481353`, a 3,9 m del eje y a **864,5 m** del inicio (1,9 m tras el portal este), cota 193,6 m [V-OSM].
- **Cómo es [P]:** valla de madera con dos largueros horizontales y un risco claro de roca junto a la salida (foto 2013). Un blog (`mappingspain.com`, sin fecha) habla de «un buen mirador justo después del túnel» donde pueden parar los menores [S]. Dimensiones: **[N]**.
- **Ibiza:** GVA dice «desde la plataforma» (registro); otras guías dicen «desde la cima» (Apatita 2007, casallibertat, siguiendolasenda) [S]. No son excluyentes. **Comprobación geométrica propia [E]:** desde ambos puntos, con refracción estándar (k = 0,13) y alturas de Ibiza tomadas **de memoria, sin verificar** (380–475 m), el relieve de Ibiza asoma sobre el horizonte marino unos 230 m desde la plataforma y unos 310–350 m desde la cima. La dirección es ENE (acimut ≈ 70–75°), a 101–113 km. Solo prueba que **no es físicamente imposible**, no que se vea en la práctica.

### 4.2 Mirador del Botànic Cavanilles y paradas de antes del túnel

- calpe.es (leído hoy) dice que **los dos miradores del primer tramo son el de Poniente y el de Cavanilles**, sobre las playas y calas de poniente. La GVA y MACMA dan el orden: Mirador de Ponent → restos ibéricos → pinos tumbados («pins tombats») → área de descanso → **Mirador del Botànic Cavanilles**, donde está **el primer panel señalizador de una de las dos microrreservas de flora** del parque → túnel [V/S].
- **Candidatos (OSM, miradores sin nombre):** a 194,8 m (cota 92 m; el de F3, posible Mirador de Ponent), a 571,5 m (cota 141 m) y a **654,7 m (cota 155 m)**. Por el orden oficial, el último antes del túnel sería el de Cavanilles. **Sin confirmar** (pregunta 2 de `consulta-parque.md`).
- **Panel [P]:** una foto de 2014 (chisloup, «Ifach - panoramio.jpg», posición declarada a 14 m del portal oeste, poco fiable) muestra un **panel interpretativo en atril: tablero rectangular inclinado con marco oscuro sobre un único poste de ~1 m (estimación visual)**, junto a una cuerda de apoyo fijada a la roca y un poste cuadrado de madera. No se puede asignar al Cavanilles ni a otra parada.
- **Pins tombats / área de descanso:** «pinos doblados por el viento de levante»; el área es «un pequeño espacio despejado para descansar» (MACMA, GVA) [V/S]. **No hay fuente ni foto que hable de bancos** [N]. **Restos ibéricos:** «ocultos por la vegetación» (MACMA); no hay nada que modelar [S].

### 4.3 Bifurcación y gaviotas

- OSM `node 288472006`, a **1.217,6 m** y cota 225,2 m. Cartel en el cruce [S] (cristabeldeviaje: cima ≈ 500 m, mirador a la izquierda), con círculos rojos pintados en la roca hacia la cima [S].
- Gaviota patiamarilla: ponen en abril y cuidan los pollos en mayo; «bastante agresivas» (Apatita); GVA: agresiva en primavera cerca de la bifurcación (registro `gull-breeding`) [S/V]. No hay censo de parejas [N]. No se da la ubicación de nidos.

### 4.4 Mirador de Carabiners (nodo OSM 288472096, 1.121,8 m, cota 226 m)

- **Qué es:** «antigua plataforma de vigilancia de carabineros» (GVA/MACMA); el PRUG de 1993 lo llama **«camino del mirador de la torre»** (art. 30), lo que sugiere que entonces se identificaba con una torre. Una fuente local (Ortolà 2005) menciona «un fortín o una torre vigía cerca del túnel, posiblemente de origen bizantino». Relacionarlo con el mirador es una hipótesis, no un hecho [S].
- **Qué se ve [P]:** explanada de roca caliza desnuda y cantos, sin barandilla ni obra visible en el encuadre; al borde, **un poste cuadrado de acero inoxidable cepillado con el tercio superior pintado de rojo, con pegatinas y pintadas** (foto 2013 «Mirador de Carrabiners del penyal d'Ifac»). Su función no está documentada; el rojo podría ser el de la «Ruta Roja» (hipótesis). Tamaño: no derivable de la foto.
- **Ruinas:** **[N]**. Ninguna fuente ni foto muestra muros, cimientos o garita.

### 4.5 La cima y el vértice geodésico

- **Reseña IGN nº 84878 «Ifac»** (`datos-geodesia.ign.es/Red_Geodesica/Hoja0848/084878.pdf`, impresa el 10-10-2026) [V]:
  - nombre actual «Ifac» (antes «Ifach»); Calp; **construido el 11-12-1987**;
  - **pilar sin centrado forzado de 1,20 m de alto y 0,30 m de diámetro; último cuerpo de 0,20 m de alto y 1,00 m de ancho; 1 cuerpo en total**;
  - ETRS89: lat 38° 38′ 05,98877″ N, long 0° 04′ 28,14684″ E (±0,12–0,13 m); UTM 31 N (ETRS89): X 245 353,551, Y 4 280 334,049;
  - altitud elipsoidal 376,154 ± 0,171 m y **altitud sobre el nivel medio del mar 326,714 m, ambas referidas a la base del pilar (BP)**;
  - «situado en lo más alto del Peñón de Ifach»; horizonte GPS despejado;
  - estado a 20-07-2014: **pilar «no estacionable»** (el IGN no da el motivo; lo lógico es la cabeza rota, inferencia nuestra), base «bueno».
  - Foto IGN «Ifach (mar-10)» [P]: pilar de hormigón gris, **cabeza irregular rota con un lazo de acero asomando**, fuste con pintadas, sobre una losa de hormigón apoyada en roca caliza; al fondo Calp y la bahía.
  - Croquis de acceso de la misma reseña: **chalet «San Miguel»**, un «hotel en construcción abandonado» junto al camino y «un túnel excavado en la roca» (texto de 1987–1991; ver §9).
- **Especificación estándar (IGN, «¿Qué es la Geodesia?», p. 10) [V]:** la monumentación de la ROI es «una base prismática cuadrada de altura variable y de 1 m de lado» con «un pilar cilíndrico de 1,20 m de altura y 0,3 m de diámetro». **El vértice de Ifac es, por tanto, un pilar ROI estándar** con la base más baja posible. «Tercer orden» (GVA, MACMA) no es un término de la reseña: el IGN lo clasifica como vértice de la ROI. Que ROI y «tercer orden» sean equivalentes es lectura nuestra, sin comprobar.
- **Posición y cota en nuestro marco [E]** (pyproj sobre las coordenadas ETRS89 de la reseña; el proyecto usa EPSG:25830 y la diferencia con UTM 31 es solo de huso):
  - (x 616,03; z −758,43), a 4,75 m del nodo OSM `409151051` («peak») que ancla la cima; ya existe en OSM como `node/948641001` (`man_made=survey_point`, `ref:ES:roi=84878`, `ele=326.71`);
  - MDT 2016 en ese píxel: **326,68 m** (rango 326,64–326,86 m a ±1 m); IGN 326,714 m;
  - LiDAR 2016 (tesela 766-4282): **dos retornos de 328,07 m a 0,37 y 0,46 m** de las coordenadas del IGN, el máximo en 30 m a la redonda (≈ 2 puntos/m²). Cabeza nominal del pilar = 326,714 + 1,20 = 327,91 m: el LiDAR queda 0,16 m por encima, dentro de lo razonable (precisión vertical del ICV sin comprobar).
  - Lectura: **328,07 m (`summit-altitude`) ≈ cabeza del pilar; la roca está en ≈ 326,7 m**. El MDT acierta con la medida geodésica a 3 cm. Los 332 m oficiales y los 325,8 m de la CV05 siguen sin explicar (la CV05 es una cota de mapa 1:5000).
- **Mobiliario:** sin bancos, mesa, cruz ni libro de cumbre documentados (OSM: `summit:cross=no`, `summit:register=no`) [V-OSM]. Ninguna fuente ni foto consultada muestra otro elemento construido en la cima.

### 4.6 Señalización

- **Cartel naranja de peligro** (triángulo de aviso) en poste de madera, en la terraza del portal oeste; y otro pequeño rojo y blanco [P] (fotos 2013 y 2014). Texto ilegible. En 2016 se sustituyó toda la señalización [S], así que estas dos pueden ya no existir.
- «Camino muy peligroso»: cartel citado por un blog en la entrada del tramo duro (siguiendolasenda) [S].
- Círculos rojos pintados en la roca de la subida a la cima [S].
- OSM: panel «Peñón de Ifac: Ruta ornitológica» (`node/9562356617`) en (676; −509): **no está en la Ruta Roja** (zona sur) [V-OSM].

---

## 5. Normas y cierres (para la información práctica de la app)

Estas filas son «hechos con fuente y fecha». Las que ya están en `facts.json` se citan por su id.

| Qué | Dato | Fuente y fecha | Fiabilidad / observación |
|---|---|---|---|
| Reserva y cupo | Reserva previa obligatoria más allá del torno; **300 al día**; personal; una por persona | PRUG art. 26.1 («en principio» 300 paseantes diarios) [V]; Junta Rectora, noticia de calpe.es (sin fecha; imagen de dic. de 2020) [S]; `access-booking`, `access-capacity` (registro) | Estable desde 2020 |
| Antelación | **«hasta 10 días»** de antelación (Calp Comunica, evento del 2026-07-21) frente a **«con al menos cuatro días»** (idealista, 2026-10-09) y «antelación mínima de cuatro días» (noticia de 2020) | calpcomunica.calp.es [S]; idealista [S]; calpe.es [S] | **Contradicción abierta** (parece que la ventana cambió o que se cuentan cosas distintas). El registro ya dice «hasta 10 días» |
| Sin reserva | Si no se ha llegado a 300, se expide autorización in situ (noticia 2020) | calpe.es [S] | Puede haber cambiado; **no mostrar como norma** |
| Control | Un agente puede pedir la reserva en cualquier momento | calpe.es [S] | — |
| Menores más allá del túnel | «No se permite el acceso de menores de edad» en la reapertura de 2016 | calpdigital 2016-08-10 [S]; resto en el registro (`access-minors-past-tunnel`, conflicto) | Sigue en conflicto en las fuentes oficiales |
| Calzado | Calzado de montaña «obligatorio» en el tramo túnel-cima (2016) | calpdigital 2016 [S]; `access-safety` | — |
| «Camino del mirador» (Carabiners) | **Abril, mayo y junio**: el paseo es un uso compatible *excepto* en época de cría; el Director-Conservador puede además restringir el paso previo informe de la Junta Rectora; el art. 32 prohíbe el «acceso libre» en esos meses (no dice que esté cerrado a visitas autorizadas) | PRUG art. 30–32 (zona de reserva) [V] | **No se ha encontrado nada que confirme que hoy se aplique.** El Mirador de Carabiners es una parada oficial de la Ruta Roja. No afirmar cierre alguno en la app; preguntarlo al parque |
| Escalada | Prohibida en la pared norte-noroeste de abril a junio (halcón peregrino) | PRUG art. 31–32 [V]; `access-climbing-ban` | Ya en el registro |
| Reglas de visita | No salir de las sendas, no atajar, no bajar por el canchal; fotos desde los itinerarios; sin fuego; sin pintadas | PRUG art. 26.3 [V] | — |
| Cierres históricos | **Abril de 2015 – 10 de agosto de 2016** (senda superior) | §3.3 | [S] |
| Cierre por incendios | **23 de julio de 2026**: cerrado todo el día por «riesgo extremo de incendios forestales», resolución conjunta de la AVSRE y la Secretaría Autonómica de Medio Ambiente; Preemergencia 3 del PEIF | noticiascv.com, 2026-07-23 (anuncia el Ayuntamiento de Calp) [S] | Muestra que el parque puede cerrarse en el día; no hay fecha de reapertura en la fuente |
| 16–17 de junio | Cierre por obras en la senda a la cima | calpe.es (año no consta) [S] | No usar |
| Aforo antiguo | 150 simultáneos y 20 cada 15 min (2011) | Ecoticias | **Obsoleto** (ver 003) |

---

## 6. Conflictos entre fuentes (nuevos o precisados)

| Dato | Versión A | Versión B | Versión C | Qué hacer |
|---|---|---|---|---|
| Altitud del vértice | **326,714 m (IGN, base del pilar)** [V] | 328,07 m (LiDAR; ≈ cabeza del pilar) [E] | 332 m oficial; 325,8 m (CV05) | Añadir la reseña IGN a `summit-altitude` como cuarto valor, con la nota «base del pilar» |
| Pasamanos del túnel | Dos cuerdas (GVA; fotos 2013–2014) | Cadena (foto 2019; «cuerdas o cadenas» en blogs) | Cuerdas renovadas en 2016 | Aceptar ambos; pedir foto actual |
| Longitud del túnel | 49,3 m (OSM) | 30 m (calpe.es hoy) | ≈ 50 m (GVA); ~100 m (blog) | Ya en el registro; mantener el rango |
| Posición de Carabiners | 614 m tras el túnel (OSM) | «decenas de metros» (sendasyleyendas) | — | Prevalece OSM |
| Antelación de la reserva | Hasta 10 días (Calp, 2026-07-21) | ≥ 4 días (idealista, 2026-10-09) | mín. 4 días (2020) | Preguntar; no fijar |
| Coste de las obras de 2016 | ≈ 50.000 € | < 40.000 € | — | No se muestra la cifra |
| Ibiza | Desde la plataforma (GVA) | Desde la cima (blogs) | — | Mostrar ambas con su fuente |
| Superficie del ramal de Carabiners | `surface=rock` (OSM) | Tierra con piedras (foto 2013) | — | Modelar tierra compactada; proponer corregir OSM (es ODbL: lo decide el usuario) |

---

## 7. Lo que sigue sin respuesta tras una búsqueda honrada

| Falta | Por qué | Qué lo resolvería |
|---|---|---|
| Ancho y alto del túnel; forma exacta de las bocas | Nada publicado; sin objeto de escala en las fotos | Medida con cinta o escaneo LiDAR del móvil (protocolo de fotos); o el proyecto de 2016 (Vaersa) en el parque |
| Estado actual del pasamanos del túnel (cuerda o cadena) | Última foto: 2019 | Foto reciente; pregunta al parque |
| Anchura, alturas de pasamanos y distancia entre postes del sendero de losas | Solo estimaciones sobre fotos | Medidas con cinta (protocolo, sección «Fotos y medidas para modelar») |
| Posición, forma y texto del panel del Cavanilles y de las demás paradas | Ninguna fuente da coordenadas | Pregunta 2 de `consulta-parque.md` |
| Ubicación de los restos ibéricos y del área de descanso | Ocultos por vegetación; sin dato | Idem |
| Qué es el poste rojo y plateado de Carabiners; qué queda de la plataforma | Sin fuente | Foto actual o pregunta al parque |
| Si el PRUG se aplica hoy al «camino del mirador» (abril–junio) | Sin noticia ni aviso | Pregunta al parque (propongo añadirla a `consulta-parque.md`) |
| Si hay bancos en cualquier punto del recorrido alto | Ninguna fuente ni foto | Fotos del usuario |
| Proyecto de 2016 y expediente de contratación | Web de la GVA caída; plataformas de contratación no consultables | Solicitud al parque; o repetir la búsqueda cuando la GVA responda |
| Texto íntegro de la nota GVA de reapertura (2016) | Host de la GVA inaccesible | Releer cuando responda |
| Copias de Internet Archive de la GVA | `web.archive.org` bloqueado en WebFetch | Releer con el relé NAT64 de `CLAUDE.md` (lo hace el responsable técnico) |
| Cobertura de Mapillary y Flickr con licencia CC | Aplicaciones solo JS | Revisión manual en navegador |

**Preguntas nuevas para `consulta-parque.md` (propuesta, no se ha editado el archivo):** (a) ¿el «camino del mirador» (Carabiners) se cierra hoy de abril a junio, como dice el PRUG? (b) ¿puede facilitar la memoria y los planos de las obras de 2016 (muros, cadenas, cuerdas) y la anchura prevista del sendero? (c) ¿cuál es hoy el pasamanos del túnel (cuerda o cadena) y a qué altura va? (d) ¿qué es el poste de acero con la parte superior roja en el Mirador de Carabiners? (e) ¿la ventana de reserva es «hasta 10 días» o «mínimo 4 días»?

---

## 8. Recursos: clasificación y lista de descargas propuestas

### 8.1 Clasificación

| Recurso | Clase | Licencia | Para qué |
|---|---|---|---|
| Reseña IGN 84878 (PDF), ficha API de la ROI | **Dato medido (abierto)** | CC BY 4.0 (IGN, «Condiciones de uso»: `ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf`; la colección `red_roi` enlaza esa licencia; el PDF no la repite) | Dimensiones y posición del vértice; foto como referencia |
| IGN, «¿Qué es la Geodesia?» (PDF) | Documento oficial (cita) | IGN (misma licencia) | Citar la especificación ROI; **no hace falta descargarlo** |
| PRUG, Decreto 260/1993 (DOGV) | Texto legal | Texto oficial público | Citar artículos; ya consta como `dogv-prug-1993` |
| Fotos de Commons CC BY-SA 3.0/4.0 (Joanbanjo, Donarreiskoffer, Vibanezmas, Calpeapie) | **Solo referencia** (mirar, medir, no copiar píxeles) | CC BY-SA | Formas, materiales, equipamiento |
| Fotos de Commons CC BY 3.0 (chisloup) | Referencia; **utilizables como textura en teoría** (CC BY), pero el proyecto no usa fotos como textura | CC BY 3.0 | Ya hay 10 en el repositorio |
| CC0 de Commons (Nicolas Vigier, Marnal) | Utilizables | CC0 | Sin interés para este tramo (vistas lejanas y panorámicas) |
| Blogs, Wikiloc, guías | Solo referencia (con copyright) | Todos los derechos reservados | Texto y fotos: no copiar |
| Mapillary, Flickr | No evaluados | — | — |

### 8.2 Lista de descargas propuestas (a aprobar; ninguna hecha)

Tamaños: los de Commons son el original (bytes que da la API); propondría pedir la versión de 1.600 px, que pesa bastante menos, como en las 15 fotos actuales.

| # | URL | Nombre propuesto | Bytes | Licencia | Autor | Para qué |
|---|---|---|---|---|---|---|
| 1 | `https://datos-geodesia.ign.es/Red_Geodesica/Hoja0848/084878.pdf` | `ign-resena-84878-ifac.pdf` | 1.491.494 | CC BY 4.0 (IGN) | IGN | **Prioritaria.** Dimensiones, coordenadas, altitud y foto del vértice |
| 2 | `https://api-features.ign.es/collections/red_roi/items/84878?f=json` | `ign-roi-84878.json` | no consta (pequeño) | CC BY 4.0 (IGN) | IGN | Dato legible por máquina (lat, long, alturas, fecha) |
| 3 | `https://dogv.gva.es/datos/1994/01/21/pdf/1994_830310.pdf` | `dogv-1994-prug-penyal-ifac.pdf` | 402.591 | Texto oficial público | GVA | Respaldo de los artículos 16, 26, 30–33 (ya está en `sources.json`) |
| 4 | `https://commons.wikimedia.org/wiki/File:T%C3%BAnel_del_penyal_d%27Ifac.JPG` | `joanbanjo-tunel-interior.jpg` | 1.398.220 | CC BY-SA 3.0 | Joanbanjo (2013-11-02) | Interior, pasamanos, valla de la salida |
| 5 | `…/File:Vista_cap_al_t%C3%BAnel,_penyal_d%27Ifac.JPG` | `joanbanjo-portal-oeste.jpg` | 2.409.958 | CC BY-SA 3.0 | Joanbanjo | Portal oeste, muro, valla, cartel |
| 6 | `…/File:Restes_d%27una_explosi%C3%B3_de_dinamita,_penyal_d%27Ifac.JPG` | `joanbanjo-barreno.jpg` | 2.559.921 | CC BY-SA 3.0 | Joanbanjo | Barreno en la roca (detalle) |
| 7 | `…/File:Sender_cap_al_mirador_de_carrabiners,_penyal_d%27Ifac.JPG` | `joanbanjo-sendero-carabiners.jpg` | 2.704.966 | CC BY-SA 3.0 | Joanbanjo | Firme y borde del ramal |
| 8 | `…/File:Mirador_de_Carrabiners,_penyal_d%27Ifac.JPG` | `joanbanjo-carabiners-a.jpg` | 2.333.394 | CC BY-SA 3.0 | Joanbanjo | Explanada |
| 9 | `…/File:Mirador_de_Carrabiners_del_penyal_d%27Ifac.jpg` | `joanbanjo-carabiners-b.jpg` | 2.097.699 | CC BY-SA 3.0 | Joanbanjo | Poste de acero con parte superior roja |
| 10 | `…/File:Cam%C3%AD_cap_al_cim_del_penyal_d%27Ifac.JPG` | `joanbanjo-camino-cima.jpg` | 2.700.430 | CC BY-SA 3.0 | Joanbanjo | Ladera y senda final |
| 11 | `…/File:Cam%C3%AD_de_pujada_al_penyal_d%27Ifac.JPG` | `joanbanjo-camino-pujada.jpg` | 1.876.707 | CC BY-SA 3.0 | Joanbanjo | Losas, barandilla de troncos, borde de tablones |
| 12 | `…/File:Sender_del_Penyal_d%27Ifac.JPG` | `joanbanjo-sender.jpg` | 2.367.594 | CC BY-SA 3.0 | Joanbanjo | Idem, tramo inferior |
| 13 | `…/File:Ifach_-_panoramio.jpg` | `chisloup-ifach-panel.jpg` | 5.154.816 | CC BY 3.0 | chisloup (2014-05-27) | Panel en atril y cuerda sobre roca |
| 14 | `…/File:Vista_cap_al_cim_del_penyal_d%27Ifac.JPG` | `joanbanjo-cima-desde-sender.jpg` | 2.108.800 | CC BY-SA 3.0 | Joanbanjo | Cono final y firme de pedrera |

- **Total propuesto:** los 14 recursos suman **29.606.590 bytes ≈ 28,2 MiB** con los originales (13 con tamaño conocido; la ficha JSON del IGN no declara el suyo y es pequeña). Las 11 fotos de Commons suman 27.712.505 bytes (26,4 MiB); con las versiones de 1.600 px (estimadas de 0,3 a 1 MB cada una, **por confirmar**) bajarían a **≈ 4–8 MiB**. Los datos oficiales (nº 1 a 3) suman **1.894.085 bytes ≈ 1,8 MiB** más el JSON; el PDF de la reseña IGN y el del PRUG ya están en la caché de la herramienta.
- **No proponer** copiar los 20 de Calpeapie (IMG-20200820-WA0014 …): son de baja resolución, sin EXIF y sin tema claro.

### 8.3 Fotos consultadas y qué aportan (todas solo referencia salvo las nuestras)

| Foto | Autor / licencia / fecha | Posición | Qué se ve (no hay personas descritas) |
|---|---|---|---|
| Nº 21, 27, 28 del repositorio | chisloup, CC BY 3.0, 2014-05-27 | 38,635545 N, 0,075574 E; 38,635562, 0,075392; 38,635579, 0,075982 (Panoramio, ± decenas de metros) | Boca oeste hacia la bahía; interior con cuerdas; terraza con valla, muro y cartel |
| Nº 38 del repositorio | Donarreiskoffer, CC BY-SA 4.0, 2019-02-08 15:07 | 38,635556 N, 0,075 E | Escalones y portal oeste con cadena |
| *Túnel del penyal d'Ifac* | Joanbanjo, CC BY-SA 3.0, 2013-11-02 16:08 | sin coordenadas | Interior; valla de dos largueros y risco a la salida |
| *Vista cap al túnel* | Joanbanjo, 2013-11-02 16:13 | sin coordenadas | Portal oeste, muro de piedra seca, valla, cartel |
| *Restes d'una explosió de dinamita* | Joanbanjo, 2013-11-02 16:04 | sin coordenadas | Barreno en roca |
| *Sender cap al mirador…*, *Mirador de Carrabiners* (×2) | Joanbanjo, 2013-11-02 15:28–15:35 | sin coordenadas | Ramal de tierra; explanada; poste rojo |
| *Camí de pujada*, *Sender del Penyal* | Joanbanjo, 2013-11-02 12:24–12:29 | sin coordenadas | Losas con barandilla de troncos |
| *Ifach - panoramio* | chisloup, CC BY 3.0, 2014-05-27 | 38,635587 N, 0,075799 E | Panel en atril, cuerda en la roca |
| IGN, foto de reseña | IGN (CC BY 4.0), marzo de 2010 | cima | Pilar con la cabeza rota |

---

## 9. Hallazgos fuera de alcance (anotados, no resueltos)

1. **Dos casas de Vicente París y sus «imitaciones».** `historiadecalp.net/ifach.htm` (A. Ortolà Tomás, febrero de 2005, cita al P. Llopis) dice que París construyó dos casas (una para él, otra para el casero); que el parque se declaró el «17 de enero de 1987» (así lo devolvió la herramienta sin texto literal comprobado; la GVA da el 19-01-1987); que ambas casas fueron derribadas y que «en el solar de las casas se construyeron dos imitaciones de las mismas para Aula de la Naturaleza». Es la primera fuente leída que respalda la nota sin fuente de `facts.json` sobre las «dos casas réplica»; falta su año (el registro dice 1992) [S]. La reseña IGN de 1987 incluye además un croquis con edificios hatchados junto al arranque del camino y un «chalet San Miguel» que no parece ser lo mismo [P]. El PRUG de 1993 (art. 33) nombra «centro de información», «centro de recepción-aula de la naturaleza» y cafetería como zona de servicios: apoya la idea de **dos equipamientos** [V].
2. **`way/1557553367` (OSM, `highway=path`, 162 m, sin más etiquetas)** une un punto a 12 m del portal este con el propio vértice geodésico, en línea casi recta con 133 m de desnivel. No es la Ruta Roja ni la senda oficial; probablemente una traza de escaladores o un artefacto de mapeo. **No modelar.**
3. **Cuatro vías de escalada** (OSM, `natural=cliff` + `sport=climbing`, `node 10588559105`) pasan a menos de 10 m del sendero a la cima: confirman exposición, no hay que modelarlas.
4. **Cierre por incendios y reservas** en 2026 (julio): ejemplos de avisos que la app podría remitir a la web oficial, sin reproducirlos.

---

## 10. Fuentes (consultadas el 2026-10-12 salvo indicación)

### 10.1 Nuevas, para dar de alta en `content/sources.json` antes de usarlas

| ID propuesto | URL | Qué aporta | Tipo |
|---|---|---|---|
| `ign-roi-84878-resena` | https://datos-geodesia.ign.es/Red_Geodesica/Hoja0848/084878.pdf | Dimensiones, coordenadas, altitud, estado y foto del vértice | Lectura |
| `ign-roi-api-84878` | https://api-features.ign.es/collections/red_roi/items/84878?f=json | Mismo dato en JSON; licencia en la colección `red_roi` | Lectura |
| `ign-que-es-geodesia` | http://www.ign.es/web/resources/docs/IGNCnig/GDS-Teoria-Geodesia.pdf (p. 10) | Especificación de la monumentación ROI | Lectura (OCR local) |
| `ign-licencia-uso` | https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf | Licencia (CC BY 4.0, Orden FOM/2807/2015) | Fragmento de buscador y enlace de la API |
| `dogv-prug-1993` (ya existe) | https://dogv.gva.es/datos/1994/01/21/pdf/1994_830310.pdf | Art. 16, 26, 30–33 (leído por OCR) | Lectura |
| `calpe-penon-live` | https://www.calpe.es/es/descubre-calpe/espacios-naturales/pe%C3%B1on-de-ifach | 30 m de túnel, dos miradores del primer tramo, reserva | Lectura |
| `calpe-cita-previa` | https://www.calpe.es/es/noticias/articulo/la-junta-rectora-implanta-la-cita-previa-para-acceder-al-parque-natural-del | Reserva, 300 al día, más allá del torno (sin fecha explícita) | Lectura |
| `calp-comunica-reserva-2026` | https://calpcomunica.calp.es/events/to-visit-the-penyal-difac-natural-park-prior-booking-is-required/?lang=en | 10 días de antelación, una por persona (2026-07-21) | Lectura |
| `noticiascv-cierre-incendios-2026` | https://noticiascv.com/penon-de-ifach-cerrado-riesgo-extremo-de-incendios/ | Cierre del 2026-07-23 | Lectura |
| `lamarina-cierre-2015` | https://lamarina.eldiario.es/2015/06/26/la-conselleria-de-medio-ambiente-cierra-el-penon-de-ifach/ | Cierre de la senda alta; «cadena clavada en la roca»; rehabilitación de 2005 | Lectura |
| `calpdigital-reapertura-2016` | http://calpdigital.es/art/3748/el-penon-de-ifach-abre-sus-puertas-a-los-visitantes | Obras de 2016 (Vaersa) y reapertura del 10-08-2016 | Lectura |
| `laveu-reapertura-2016` | https://www.diarilaveu.cat/medi-ambient/medi-ambient-reobri-aquest-dimecres-la-senda-del-cim-del-parc-el-penyal-difac-263752/ | Cadenas como pasamanos, <40.000 € | Lectura |
| `gva-reapertura-2016` | https://parquesnaturales.gva.es/va/web/pn-penyal-d-ifac/noticias/-/asset_publisher/2mtCA95SPPqD/content/reapertura-del-itinerario-del-parque-natural-del-penyal-d-ifac-tras-la-finalizacion-de-los-trabajos-de-adecuacion-y-mejora-de-la-seguridad-en-la-senda/80305041 | Nota oficial de reapertura | **Fragmento**, no leída |
| `ortola-ifach-2005` | http://historiadecalp.net/ifach.htm | Túnel, casas y réplicas, torre vigía | Lectura |
| `apatita-ifac-ruta-2007` | https://www.apatita.com/rutas.php?id=ifac (mayo de 2007) y http://www.apatita.com/herbario/ifac.php | Cuerdas, gaviotas, bifurcación | Lectura |
| `macma-ruta-penyal-2026` (ya existe `macma-ruta`) | https://macma.org/turismo/ruta/ruta-penyal-difac | Orden de paradas, panel del Cavanilles, Carabiners, cima | Lectura |
| `wiki-es-penon` | https://es.wikipedia.org/wiki/Parque_natural_del_Pe%C3%B1%C3%B3n_de_Ifach | «Vértice de tercer orden» (sin cita directa) | Lectura (secundaria) |

### 10.2 Blogs y guías (solo referencia, con copyright)

`siguiendolasenda.es/penon-de-ifach/`, `cristabeldeviaje.com/rutas/penon-de-ifach-calpe`, `mappingspain.com/hiking-the-penon-de-ifach-calpe-alicante/`, `casallibertat.com/en/penyal-difac-walk-calpe-guide/`, `linkalicante.com/ruta-penon-ifach/`, `picobarro.com/2021/2021-42_penon_de_ifach.htm`, `lucasgraphic.com/posts/mirador-de-carabiners`, `sendasyleyendas.com/2022/01/penon-de-ifach-calpe/`, `andoyreando.com/…/subir-penon-ifach-calpe/`, `conmochila.com/penon-de-ifach`, `elpaisquenuncaseacaba.blogspot.com/2013/02/…`, `idealista.com/news/…/2026/10/09/…`, `geocaching.com/geocache/GC91A41` (2020; sin detalle útil).

### 10.3 Commons (API, consultada hoy)

- Categoría https://commons.wikimedia.org/wiki/Category:Penyal_d%27Ifac_Natural_Park (≈ 150 ficheros; autores principales Joanbanjo 2013 y 2015, Donarreiskoffer 2019, chisloup 2014, Calpeapie 2021) y subcategorías *Views from Penyal d'Ifac*, *Penyal d'Ifac Visitor Centre* y *Pobla medieval d'Ifach*.
- Búsqueda geográfica en 800 m alrededor de 38,6340 N, 0,0775 E: 84 ficheros, casi todos de vistas o de la cima. Los que muestran el sendero alto, el túnel o el Mirador de Carabiners son **unas dos docenas** (sobre todo de Joanbanjo 2013 y chisloup 2014).

---

## 11. Efecto en los datos y el modelo del proyecto (sin tocar nada)

- `data/curated/tunnel.toml`: no hay medida nueva que cambie `section`. Sí hay dos cosas que anotar: el quiebro de ≈ 14° del eje OSM a 12 m del portal oeste y que el pasamanos puede ser cadena. Sobre los 6 escalones del portal: la foto de 2019 muestra bloques labrados y ninguna barandilla de madera en el encuadre, y OSM dice `handrail=yes` sin lado; el material de la barandilla modelada (metal oscuro, `CREDITS.md`) sigue sin respaldo.
- `CREDITS.md`: si se usa el vértice, citar «© Instituto Geográfico Nacional de España, CC BY 4.0, reseña 84878»; anotar en «Aproximaciones» que su cabeza real está rota y que la altura efectiva puede ser menor de 1,20 m (foto de 2010).
- `content/facts.json`: candidatos (todos con `checked: 2026-10-12`): `summit-vertex` (añadir la reseña IGN y las dimensiones), `summit-altitude` (añadir 326,714 m), `tunnel-condition` (matizar cuerdas/cadenas), y un hecho nuevo `trail-works-2016` (obras de 2016, con la contradicción 50.000 / <40.000 €).
- Posición del vértice en el marco del proyecto: (616,03; 326,71; −758,43). Pilar cilíndrico Ø 0,30 × 1,20 m sobre losa de 1,00 × 0,20 m; orientación de la losa desconocida; cabeza rota. Hormigón gris con pintadas.

# 004 — Recursos en línea para E5 (acceso del puerto) y E6 (la Pobla d'Ifac)

- Fecha: 12/10/2026. Autor: agente de investigación (Sonnet 5.5), para el responsable técnico.
- Alcance: pasos **E5** (acceso rodado y puerto, baja resolución) y **E6** (Pobla d'Ifac: muros y torres) de `docs/specs/003-entorno/propuesta.md` (§3 y §6).
- Premisa: el usuario no está en Calp, no hará fotos ni pedirá planos a instituciones. Aquí solo entra lo que está publicado en línea.
- Complementa `003-inventario-datos-propios.md`, `003-entorno-construido.md` y `003-fotos-referencia.md`. Corrige tres puntos de esos documentos (§6).
- Leyenda de fiabilidad:
  - **[F]** lo afirma una fuente que he leído, con página cuando es un PDF;
  - **[M]** medido por mí en datos propios ya descargados, solo lectura;
  - **[E]** estimación o hipótesis, con su método;
  - **[N]** no encontrado tras buscarlo.
- Nada de lo que sigue localiza plantas de *Silene hifacensis* ni describe personas de las fotos.

## Resumen (lo que cambia para el modelado)

1. **E6 tiene plano publicado y es georreferenciable con nuestros datos.** El *Plano topográfico general* del MARQ (Fig. 4 de Menéndez 2023, p. 49, escala original 1:250, PDF abierto de 6,9 MB) nombra torres, puertas, aduana, iglesia, necrópolis y Edificio 6, y dibuja el Centro de Visitantes, el aparcamiento y un mirador. Esos tres elementos están en nuestras capas (CV05, OSM, ortofoto 2024). Segundo apoyo: la foto aérea con la muralla y las torres numeradas (Fig. 2 de Menéndez et al. 2014, p. 326). Ambos son de copyright: **solo referencia**; se deriva la posición, no se copia el dibujo.
2. **Nuestra ortofoto 2024 (25 cm) ya muestra las estructuras excavadas**: lienzo norte con torres, iglesia con ábside, Edificio 6, necrópolis y la zona de la puerta, además de las tres marquesinas del aparcamiento que salen en la foto de 2014 del MARQ. [M] La ruta más segura es trazar sobre la ortofoto y usar el plano solo para saber qué es cada línea (§1.6).
3. **Ancla vertical que cuadra**: la memoria MARQ 2011 fija el punto cero en una baldosa del mirador de Levante a 59,06 m s. n. m. (p. 10). Nuestro MDT 2016 da 59,20 m y 59,41 m en los dos nodos OSM `tourism=viewpoint` de esa zona (8032598838 y 8032598837). [M]
4. **Alerta**: las coordenadas que publica el MARQ para el yacimiento (X 767.118, Y 4.281.147 en 2011; otra, inválida, en 2006) no valen. La de 2011 cae a 426 m del polígono OSM de la Pobla, dentro de la dársena (MDT 0,04 m). [M]
5. **Las cifras publicadas se contradicen** (11, 7, 10 o 12 torres; más de 800 m o más de 1.000 m de muralla; dos numeraciones de torres distintas). Lo que sí está medido: separación entre torres de unos 25 m, muro de 1,2–1,3 m, torre campanario de 6,19 × 5,84 m, iglesia de 25 × 14 m, Edificio 6 de 20 × 5,5 m interiores (tabla §1.1).
6. **No hay planta, alzado ni sección de cada torre en abierto.** Solo hay medidas sueltas. Los alzados teóricos (muro de unos 10 m, 11–12 m con antepecho) son hipótesis de los autores y no deben modelarse como hecho. Lo que ve el visitante son ruinas bajas y núcleos de tapial/mampostería, a menudo cubiertas con geotextil.
7. **E5**: el WFS INSPIRE de edificios del Catastro responde hoy y entrega `numberOfFloorsAboveGround` por parte de edificio. **Su licencia (v1.0, julio 2016) no es CC BY 4.0**: permite uso público solo de lo transformado y prohíbe difundir la información original. Sirve para validar alturas; el GML crudo no entra al repo ni se publica. Para los volúmenes bastan OSM + LiDAR, que ya tenemos.
8. **Club Náutico, torre y marina**: Club con 2–3 plantas (Catastro) y 6,2–6,9 m de LiDAR; torre redonda de unos 9–10 m (LiDAR, 12 puntos) con escalera de caracol de ladrillo y cúpula con óculo (foto Commons 2015); 264 amarres en 7 pantalanes (Wikipedia, sin verificar en la fuente primaria). Bloques junto a la rotonda: 8–13 plantas según Catastro y 8–15 según OSM; en el entorno llegan a 16 (Catastro) y 18 (OSM).
9. **Fotos**: casi todo lo útil es CC BY-SA (referencia). Solo las de *chisloup* (2010–2014) son CC BY 3.0. Mapillary exige token y es CC BY-SA 4.0; no se ha podido consultar sin crear cuenta.

## 0. Método y límites

- Lecturas con WebFetch y WebSearch los días 11 y 12/10/2026. Respondieron: `marqalicante.com`, Dialnet, Wikimedia Commons (API), Catastro (WFS y web), Persée (solo HTML), ICV (WMS y datos abiertos), `calpe.es`, MACMA, AlicantePlaza. **No respondió** `mediambient.gva.es` (ECONNREFUSED). El PDF de Persée devolvió 403 y no se ha forzado.
- **Nada se ha descargado a mano ni al repo.** Dato que conviene que sepas: WebFetch guarda por sí mismo copia de las respuestas binarias (PDF, JPEG) en su carpeta de resultados, `~/.claude/projects/-Users-lr0y-Workspace-10-Projects-Personal-penyal-ifac-3d/<sesión>/tool-results/`, fuera del repo. Desde ahí extraje el texto con PyMuPDF (entorno efímero `uv run --no-project --with pymupdf`) y miré las figuras. El trabajo temporal está en el scratchpad de la sesión. No cuenta como descarga aprobada; si prefieres borrar esas copias, están en esa carpeta.
- Tres consultas ligeras de solo lectura sobre datos propios, con el entorno `pipeline`: extracto OSM, MDT 2016 (8 puntos) y LiDAR 766-4282 (alturas de 8 huellas). Más un recorte de 220 × 170 m de la ortofoto 2024 en el scratchpad (no está en el repo).
- No se ha hecho ninguna georreferenciación ni ajuste: es la ruta propuesta en §1.6.
- No he forzado ninguna conexión TLS. Hoy WebFetch llegó a `ovc.catastro.meh.es` sin error de certificado; el problema que tuvo el equipo en local sigue sin resolver y no es asunto de este informe.

## 1. E6 — La Pobla d'Ifac

### 1.1 Qué dicen las fuentes

Siglas de fuente (URLs en §5):
- **X1** = Menéndez Fueyo, Pina, Torrecillas y Ferrer 2014, *MARQ Arqueología y Museos* Extra 01, pp. 325–330.
- **A14** = Menéndez Fueyo 2023, *MARQ Arqueología y Museos* 14, pp. 45–78 (la domus domini).
- **M2006, M2008, M2009, M2011** = memorias de campaña del MARQ en *Actuaciones arqueológicas en la provincia de Alicante* (PDF; páginas del PDF, salvo que se diga otra cosa).
- **UA** = ficha de la Universitat d'Alacant. **MACMA** = ficha de la Mancomunitat.

| Elemento | Dato | Fuente | Tipo |
|---|---|---|---|
| Superficie del recinto | 4,3 ha (X1 p. 326). Más de 70.000 m² en la ladera norte (UA). 3,5 ha (castillosricsol, sin fuente). Cerca de 5 ha (Bazzana 1980, citado en M2006 pp. 11–12). Más de 4 ha (nota de prensa 2026) | varias | F, contradictorio |
| Longitud de muralla | Más de 800 m (X1 p. 326; UA; MACMA). Más de 1.000 m (A14 p. 49; notas de 2026) | varias | F, contradictorio |
| Tramo norte conservado | Más de 200 m (X1 p. 326). 250 m continuos con más de 4 m de alzado (M2006 p. 4). Más de 250 m (UA, MACMA). Más de 400 m (guía de castillos, sin fuente) | varias | F, contradictorio |
| Número de torres | 11: nueve en el frente norte y dos en el oeste (X1 p. 327; UA; MACMA). Siete en saliente (A14 p. 49). Doce (guía de castillos). Diez (nota de prensa de 2025, solo fragmento de búsqueda). Seis localizadas (castillosricsol) | varias | F, contradictorio |
| Separación entre torres | Unos 25 m: una torre nueva "como el resto" queda a 25 m de la del ábside (M2009 p. 4) y otra a 25 m de las Torres 1 y 3 (M2009 p. 4) | M2009 | F, una sola mención |
| Planta de las torres | Todas **en saliente**, en cremallera (X1 p. 327). Torre campanario cuadrangular de **6,19 × 5,84 m**, unos 36 m² (X1 p. 329). Torres nuevas con vano de acceso en sillería (M2009 p. 4). Torre 1: muros de 1,20 m de ancho medio, cierra un lienzo E–O de más de 40 m (M2006 p. 6). Torre Laborde (frente oeste): más de 4 m de ancho, muros de 1,30 m forrados de sillería (nota MARQ/AlicantePlaza 22/08/2017) | X1, M2009, M2006 | F |
| Grosor del muro | 1,30 m (guía de castillos; iglesia, X1 p. 328). 1,20 m en los muros de la Torre 1 (M2006 p. 6). 1,08 m en el muro que Bazzana midió en 1975 (M2006 p. 11) | varias | F |
| Alzado conservado | Torres: 6 m de media (X1 p. 326). Lienzo norte: más de 4 m (M2006 p. 4); más de 6 m en algún tramo (guía). "Torre Bazzana": algo más de 8 m visibles (M2006 p. 4). Frente sur: más de 8 m (M2006 pp. 31–32). Campanario: unos 10 m (UA, MACMA) o unos 8 m ("Torre Norte", castillosricsol) | varias | F, contradictorio |
| Alzado teórico | Lienzo de unos 10 m hasta el adarve y 11–12 m con antepecho y almenas, que "creemos" sin pruebas de su existencia (X1 p. 326). Torres de 11–13 m (guía) o 14–15 m (castillosricsol), sin fuente | X1 | **E** (hipótesis de los autores) |
| Fábrica | Base de mampostería grande con mortero de cal y gravas blanquecinas; encima, tapial con mampostería; sillería encadenada en esquinas y vanos (X1 pp. 326–327). Mortero rojizo y esquinas de arenisca en el Edificio 6 (A14 p. 50); mortero anaranjado en el campanario (X1 p. 329). Adarve a la altura del deambulatorio del campanario; aspilleras abocinadas a nivel del pavimento de la pobla (X1 p. 326) | X1, A14 | F |
| Puerta del Norte | Tres puertas consecutivas con acceso en recodo y corredor cubierto (X1 p. 327; A14 p. 49). Vano de unos **3 m de ancho y 4–4,30 m de alto**, con arco de medio punto de sillería, deducido de las piezas halladas (X1 p. 327). Gran torre de guardia al NE de la puerta (X1 p. 327). Más de 20 m de longitud del complejo (guía, sin fuente). Aduana y almacén de la aduana al interior (plano Fig. 4 de A14) | X1, A14 | F |
| Puerta del Oeste | Segundo acceso, a cota más alta, en recodo y cubierto; "casi dos metros de ancho" (EFE/AlicantePlaza 26/08/2019). Junto al baluarte del grabado de Laborde de 1809. Arco de entrada hallado íntegro junto a la puerta oeste en 2022 (AlicantePlaza 11/09/2022); un titular posterior habla de extraer toda la arcada (no leído) | prensa | F |
| Iglesia | **25 × 14 m** (unos 400 m²), 2–3 m conservados en la nave y más de 1 m en las capillas; muros de 1,30 m; capillas de 4,83 × 3,75 m; ábside E–O; techumbre de madera sobre arcos ojivales y crucería en ábside y capillas (X1 p. 328). La memoria 2008 daba más de 9 m de ancho y unos 30 m de largo (p. 3) y también 32 × 10 m (p. 5) | X1, M2008 | F, contradictorio |
| Necrópolis | 21 tumbas y 43 inhumaciones, frente a la puerta de la iglesia (X1 p. 329) | X1 | F |
| Calles y casas | Más de 13 estancias; una calle perpendicular a la vía paralela a la muralla: primer indicio de trazado ortogonal (X1 p. 329). Vía paralela de unos 6,30 m (guía, sin fuente). Edificio 14: cobertizo de más de 18 m, fuera de las murallas (notas MARQ 2025 y 2026). Dos viviendas rectangulares con esquinas de sillería (nota MARQ 2025) | X1, notas | F |
| Edificio 6 (domus) | Interior de **20 × 5,5 m** (unos 100 m²), dos plantas, cubierta a dos aguas de teja árabe, cinco ventanales bíforos, puerta este de 2,10 m, entre las Puertas 1 y 2 del acceso norte (A14 pp. 49–54). Los pilares conservan menos de 1 m (A14 p. 50) | A14 | F |
| Aljibe | **No hay cisterna medieval documentada** en lo leído. El "aljibe" del sector de la iglesia se desmontó en 2011 con los rellenos del hotel (M2011 p. 12). Bazzana vio un aljibe rectangular, en parte colmatado, a espaldas del museo del parque (M2006 pp. 11–12). No se sabe si son el mismo ni si es medieval | M2011, M2006 | N |
| Hotel | Ifach Palace Hotel iniciado hacia 1956 (X1 p. 328); voladura en 1987 y escombros esparcidos por la plataforma de Levante (M2006 p. 7; M2011 p. 8) | X1, M2006, M2011 | F |
| Cota de referencia | **59,06 m s. n. m.** en una baldosa del mirador de Levante, junto al sondeo Muralla Este (M2011 p. 10) | M2011 | F |
| Cronología | Fase I (fundación): 1297–1305 por hallazgo monetario (A14 p. 67). Iglesia: 1320–1340 (M2008 p. 3; M2011 p. 10) o 1344 (otras fuentes) | A14, M2008 | F, contradictorio |

Medidas **sin** fuente en abierto: proyección y ancho de cada torre (salvo campanario y Laborde), altura de cada torre conservada, sección de la muralla, anchura de las calles, planta de las casas, altura del adarve, forma del remate. Un modelo que las fije sería inventado.

### 1.2 Planos y figuras publicados, y si se pueden georreferenciar

| ID | Qué es y dónde | Escala, norte, rejilla | Anclas que también vemos en nuestros datos | Licencia | Veredicto |
|---|---|---|---|---|---|
| P1 | **MARQ, Plano topográfico general** (Fig. 4 de A14, p. 49; PDF abierto de 6,9 MB). Curvas en naranja, estructuras por color y rótulos de torres, puertas, aduana, necrópolis, iglesia, Edificios 6 y 14 | Cajetín "E 1:250" y barra de 0–25 m. No se ve flecha de norte ni rejilla en el recorte publicado. Trama incrustada de solo 691 × 813 px, unos 0,3 m/px **[E]** (se deduce de la barra) | Contorno del Centro de Visitantes, rótulos "parking" y "mirador", "Casal d'Ifac", caminos y escalones; curvas de nivel contra el MDT | © MARQ y autor; sin licencia abierta | **Georreferenciable** con un ajuste afín y 4–6 puntos. Error esperable de 1–2 m **[E]** |
| P2 | MARQ, planta del Edificio 6 (Fig. 5 de A14, p. 50; XII campaña, septiembre 2016; base topográfica de Aerograph Studio) | Barra de 0–2 m y **flecha de norte girada** respecto al dibujo | Ninguna propia; se coloca dentro de P1 | © MARQ | Solo detalle local, una vez colocado P1 |
| P3 | **MARQ, foto aérea casi cenital** del sector norte con la muralla en amarillo, torres numeradas y estructuras en rojo (Fig. 2 de X1, p. 326; PDF abierto de 5,3 MB) | Sin barra ni norte | Las **tres marquesinas del aparcamiento**, el lazo de la pista, el edificio del Casal y la plataforma, todos visibles en la ortofoto 2024 | © MARQ | Georreferenciable por homografía con unos 6 puntos. Da la **numeración de torres de 2014** |
| P4 | MARQ, Fig. 1 de X1: imagen de Google Earth con el perímetro de la pobla a mano | Sin escala | Costa y relieve | © MARQ y Google | Solo orientativo |
| P5 | Imagen de un plano con curvas (rotuladas 50, 100, 250 y 300), barra de 100 m y flecha de norte; muestra la muralla con varias torres cuadradas, sin las excavaciones recientes. Aparece en un blog de castillos sin autor ni fuente. **Parece** el plano de Aranegui y Bazzana (*Mélanges de la Casa de Velázquez* 16, 1980, pp. 421–436), pero no lo he podido confirmar | Barra y norte | Solo curvas de nivel | Blog: "reproducción solo con autorización"; el artículo es de Persée, gratis para leer | Sin valor para E6: es de antes de 2005, impreciso y de procedencia dudosa. No se propone su descarga |
| P6 | Grabado de **Laborde, 1809** (*Itinéraire descriptif de l'Espagne*): muestra el alzado del baluarte oeste (nota MARQ 2017: original en el INHA de París, n.º 20.965) | Ninguna | Posición del baluarte y de la puerta oeste | Dominio público probable (Laborde murió en 1842), sin verificar para cada reproducción | **[N]** No he localizado la lámina en línea; hay que buscarla en el atlas de 1827–1834 |
| P7 | Memorias MARQ de 2006, 2008, 2009 y 2011; ficha UA; MACMA; blog del proyecto | Solo texto y fotos | — | © Colegio de Doctores y Licenciados y autor | **No contienen planos** utilizables |

Comprobado: **no hay planta de la Pobla en Wikimedia Commons** (categoría `Pobla medieval d'Ifach`: 29 ficheros, todos fotos y piezas), ni en OSM más allá del polígono parcial. El blog del proyecto no publica planos.

### 1.3 Cruces con nuestros datos

| Comprobación | Resultado | Tipo |
|---|---|---|
| Polígono OSM `way/1159140951` | Centroide E 767543, N 4281157 (x = 543, z = −1157); caja E 767479–767607, N 4281123–4281185; MDT 57,4 m. Coincide con la zona excavada visible en la ortofoto 2024. Son 2.326 m²: el núcleo excavado, no los 4,3 ha del recinto | M |
| Coordenadas MARQ 2011 (X 767.118, Y 4.281.147) | A 426 m al oeste del centroide, en la dársena (MDT 0,04 m). La de 2006 (X 245.449, Y 4.280.946) no es válida en ETRS89/UTM 30N. **No usar ninguna** | M |
| Cota 59,06 m (M2011 p. 10) frente al MDT 2016 | Nodos OSM 8032598838 (x = 633, z = −1104): 59,20 m; 8032598837 (x = 633, z = −1123): 59,41 m. Diferencia de 0,14 a 0,35 m. Buen ancla y confirma que "el mirador de Levante" de la memoria son esos dos miradores | M, hipótesis fuerte |
| Ortofoto 2024 en el polígono | Se ven el lienzo norte con torres, la iglesia con ábside, el Edificio 6 en diagonal, la necrópolis, los rectángulos de la zona de la puerta oeste y las tres marquesinas del aparcamiento (misma disposición que en P3) | M |
| "Casal d'Ifac" (rótulo de P1; "hoy abandonado y en desuso", M2011 p. 4) | Probable edificio OSM `way/261433047` (547 m², x = 481, z = −1169, máximo de 10 m en LiDAR). Es una hipótesis: ninguna fuente lo dice | E |
| Ortofoto ICV 1956–57 (50 cm, pancromática, CC BY, vía WMS) | La ladera eran bancales con el lazo del camino del hotel; la muralla no se distingue. Sí aparecen construcciones pequeñas en la plataforma del actual Centro (x ≈ 520–570, z ≈ −1040). A esa resolución no se puede decir si son los mismos edificios | M, parcial |

### 1.4 Estado visible hoy frente a lo enterrado

- **Se ve** (ortofoto 2024, fotos Commons de 2013 y 2014, y la barandilla del mirador en la foto 49 de 003, de abril de 2026): ruinas bajas en rojo y ocre; núcleos de tapial y mampostería con mortero anaranjado; sillería casi perdida salvo restos en esquinas; la nave de la iglesia a 2–3 m con sus capillas; el campanario como núcleo con sillares caídos encima (foto Joanbanjo 2013); barandillas de madera del mirador de Levante. [F/M]
- **Se cubre**: al acabar cada campaña los restos se documentan y se tapan con geotextil (M2011 p. 6). La foto de 2013 muestra dos zonas cubiertas con telas. El aspecto depende de la estación.
- **Está cambiando ahora**: la campaña XXI se presentó el 15/09/2026, dura unos 30 días y busca el límite oriental, más allá del ábside; se están delimitando los edificios XV y XVI y estudiando el XIV (nota de 15/09/2026). Un sondeo de 2011 en la muralla este dio negativo (M2011 p. 11).
- **Está por venir y no existe aún**: retirada de los escombros del hotel y reconstrucción del acceso de la puerta oeste (AlicantePlaza 2022), Plan Director, Centro de Interpretación (anunciado para 2014 en X1 p. 330 y "inminente" en 2019). No he encontrado prueba de que ninguno exista.
- **Enterrado o desaparecido**: la planta alta del campanario y la del Edificio 6, las cubiertas, los remates de muralla y cualquier tramo del lado este. Un modelo "de lo que ve el visitante" no debe incluirlos.
- **Torre con teja que no es medieval**: en las fotos Commons de 2013 y 2014 hay en la plataforma norte una torre cuadrada, revestida de sillería, con ventana vertical y cubierta de teja (la de `Calpe - panoramio (58)`, CC BY 3.0). Ninguna fuente MARQ la describe. Por posición y por el máximo de 10 m del LiDAR es probablemente parte del Casal. [E]

### 1.5 Contradicciones entre fuentes (todas)

| Dato | Versión A | Versión B | Otras | Qué hacer |
|---|---|---|---|---|
| Número de torres | 11 (X1 p. 327; UA; MACMA) | 7 en saliente (A14 p. 49) | 12, 10, 6 | Contar sobre la ortofoto y fijar un número con "n.º observado en 2024" |
| Longitud de muralla | Más de 800 m | Más de 1.000 m | — | Medirla sobre lo trazado; mostrar rango |
| Superficie | 4,3 ha (X1) | 3,5 ha, más de 4 ha | 5 ha (Bazzana 1980), 70.000 m² (UA) | No modelar el recinto completo |
| Numeración de torres | 2014: Torre 1 y 4 en muralla norte, 2 y 3 en oeste, campanario, 7 = ábside, 8 y 10 = este (Fig. 2 de X1) | 2023: nombres Prima, Secunda, Tercia, de la Guardia, Laborde, campanario, del Ábside, del Este (Fig. 4 de A14) | A14 p. 68 sitúa las Torres 2, 3 y 7 en el sector NO | Cada publicación usa su sistema; no mezclarlos. Usar los nombres de 2023 |
| Alzado del campanario | Unos 10 m (UA, MACMA) | Unos 8 m (castillosricsol); "Torre Bazzana" más de 8 m (M2006 p. 4) | X1 dice que sus plantas 1.ª y 2.ª "están destruidas" | Medirlo en el LiDAR; no asumir 10 m |
| Identidad "Torre Bazzana" | Torre con sillería in situ que Bazzana describe en el mirador de Levante | Posible campanario | — | Sin resolver. No hay fuente |
| Dimensiones de la iglesia | 25 × 14 m (X1 p. 328) | Más de 9 × unos 30 m (M2008 p. 3); 32 × 10 m (M2008 p. 5) | — | Usar la huella medida en ortofoto; la memoria 2008 es provisional |
| Fecha de la iglesia | 1320–1340 | 1344 | — | Ya recogido en `facts.json` (`pobla-church-date`) |
| Fundación | 8/04/1282 (X1 p. 325) | 10/08/1297 (M2011 p. 1) o "verano de 1297" (X1) | 1298 (UA, MACMA) | Fuera de E6; ya en `facts.json` |
| Fin de la pobla | 1359, ataque castellano-genovés (UA; M2008) | Asedio de enero a marzo de 1365 (A14 p. 68) | Abandono hacia 1356 (M2006 p. 32); hacia 1400 (UA) | Fuera de E6 |
| Tipo y época del recinto | Califal, siglos X–XI (Aranegui y Bazzana 1980; aún en hipótesis en M2006 p. 3) | Fundación cristiana de 1297–1305 (A14 p. 67) | — | Gana la segunda por excavación estratigráfica |
| Protección | "Declarada BIC" (blog del proyecto; notas MARQ de 2010 o 2011) | No aparece en ninguna fuente oficial leída | — | **Sin verificar**. El BOE-A-2010-5429, que salió en una búsqueda, es de Mallorca |
| Coordenadas | MARQ 2011: 767.118 / 4.281.147 | Nuestro polígono OSM: 767.543 / 4.281.157 | — | Usar la nuestra |

### 1.6 Ruta propuesta para modelar E6 sin inventar

1. **Obtener P1 y P3** (lista §3) y extraer las tramas incrustadas a su resolución nativa. No rehacer ni "limpiar" el dibujo.
2. **Puntos de control en nuestros datos**:
   - esquinas del Centro de Visitantes en CV05, cruzado con OSM `way/26330271` y `way/26330272`;
   - las tres marquesinas del aparcamiento y el borde del lazo de la pista, en la ortofoto 2024;
   - el edificio candidato a Casal, `way/261433047`;
   - la barra de 0–25 m como comprobación independiente de escala;
   - las curvas de P1 contra las del MDT.
3. **Ajuste**: afín para P1, homografía para P3. Registrar el error cuadrático medio. Si pasa de 1,5 m, no se traza nada de ese plano y se vuelve a la ortofoto sola.
4. **Trazar sobre la ortofoto 2024**: lienzo, torres, iglesia y Edificio 6 se dibujan siguiendo las coronas visibles a 25 cm (el muro de 1,2–1,3 m son unos 5 píxeles). El plano solo dice qué línea es muro y cómo se llama. Así la geometría es nuestra y cita "ortofoto ICV 2024; posición contrastada con MARQ 2023".
5. **Alturas**:
   - base del muro desde el MDT 1 m;
   - alzado conservado: comprobar con el LiDAR 2016 (primer retorno menos MDT) a lo largo de lo trazado. Es denso en torres y campanario si hay retornos; densidad de 0,5–1 punto/m², así que sirve solo como cota máxima y mínima;
   - donde el LiDAR no alcance, usar solo los valores publicados (torres 6 m de media, lienzo norte más de 4 m, iglesia 2–3 m y capillas 1 m), marcados como aproximación en `CREDITS.md`.
6. **No modelar** parapetos, almenas, techos ni plantas altas. Si alguna vez se quiere una restitución, será otra capa, marcada como hipótesis.
7. **Materiales**: núcleo de tapial/mampostería con mortero anaranjado, base de mampostería de gran tamaño con mortero blanquecino, sillería solo en esquinas, vanos y capillas. Elegir texturas CC0 comparando con las fotos de referencia; las fotos CC BY-SA son solo para mirar.
8. **Validación**: lado a lado con las fotos Commons de 2013 y las de abril de 2026 (referencia, no textura).

### 1.7 Lo que sigue faltando tras una búsqueda razonable

- **Plano vectorial o georreferenciado** del yacimiento. El CAD original a 1:250 existe en el MARQ (topografía y CAD de José Gabriel Gómez Carrasco, según el cajetín de la Fig. 5 de A14) y no está en abierto.
- **Planta y alzado de cada torre**; solo hay campanario y Laborde.
- **Alzados conservados por torre y por tramo**.
- **Monografía de 2018** (*La Pobla medieval de Ifach… 10 años*, Serie Excavaciones Arqueológicas 8, 412 pp. según una reseña): la ficha del MARQ no ofrece descarga y no he localizado el texto completo en línea.
- **"Ifach ad portas"** (Menéndez y Pina, *Jornades d'Arqueologia de la Comunitat Valenciana 2016-2018*, Generalitat 2020, pp. 385–404): el volumen está en abierto (Dialnet, RUA, UJI) pero pesa más de 10 MB y WebFetch no lo lee. **Candidato**: puede traer plantas de las puertas.
- **"El recinto amurallado de la pobla de Ifach"** (2013, *Fortificações e território…*): Dialnet lo lista; no lo he localizado en los PDF del volumen.
- **Paneles interpretativos del parque**: no hay texto en línea.
- **Catálogo oficial del patrimonio valenciano**: la ficha BIC o BRL no se ha encontrado.
- **Lámina de Laborde** y fotos de 1930 y vuelos de 1956 citados por M2008 (p. 5, para una torre desaparecida de la muralla de Levante).

## 2. E5 — Acceso del puerto, a baja resolución

### 2.1 Catastro INSPIRE de edificios (altura en plantas)

- **Servicio**: `http://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx`, WFS 2.0.0, GML 3.2.1. Tipos `BU.BUILDING`, `BU.BUILDINGPART`, `BU.OTHERCONSTRUCTION`. CRS admitidos, entre otros, EPSG:25830. Límite por petición: **caja de 4 km² y 5.000 elementos**. Sin consultas SQL (doc. WFS v1.0, julio 2016, pp. 3–7).
- **Plantas**: `bu-ext2d:numberOfFloorsAboveGround` y `numberOfFloorsBelowGround` vienen en cada `BuildingPart`. Confirmado con peticiones reales hoy. `heightBelowGround` aparece, pero **no hay altura sobre rasante**. [F/M]
- **Ejemplo** (EPSG:25830, un bbox de unos 0,02 km²): `…/wfsBU.aspx?service=wfs&version=2&request=getfeature&typenames=BU.BUILDINGPART&bbox=767300,4281080,767420,4281200&srsname=EPSG::25830`.
- **Licencia** (documento *Licencia de acceso y uso de los servicios y conjuntos de datos INSPIRE*, v1.0, julio 2016, pp. 2–3):
  - **no es CC BY 4.0**: licencia de cesión automática al usar el servicio;
  - uso público, también comercial, **solo de información transformada**; "no se autoriza la difusión… de la información original", que no puede difundirse por Internet sin transformarla;
  - los productos derivados no pueden llamarse "cartografía catastral" ni inducir a confusión, y no pueden alterar el sentido del dato.
  - El conflicto con "CC BY 4.0" que recogía `003-entorno-construido.md` queda así: **la licencia vigente en la página de INSPIRE es la de 2016**. No he encontrado un texto posterior; la página de condiciones de la Sede no se ha leído.
  - Consecuencia: el GML crudo va a `data/raw/` (ignorado, como el resto) y no se commitea nunca. Del Catastro se deriva solo el número de plantas como validación o atributo, y se atribuye. La geometría sale de OSM y LiDAR.
- **Plantas medidas en la zona E5** (4 consultas; las dos mayores se truncaron en WebFetch, así que **faltan partes**):

| Parcela catastral | Qué hay (posición aprox.) | Plantas sobre rasante |
|---|---|---|
| `7413901YH6871S`, 6 partes | Club Náutico y torre (E 767345–767354, N 4281142–4281159) | 2, 2, 2, 2, **3**, 2 |
| `0000101BC4850N`, 2 partes | Edificio del centro de buceo (E 767339–767367, N 4280966–4280980) | 1 y 2 |
| `7514111BC6871S`, 25 partes | Bloques al norte de la rotonda (E 767357–767387, N 4281219–4281275) | de 0 a **13**; la mayoría entre 8 y 12 |
| `7514107BC6871S`, 3 partes | E 767386–767393, N 4281187–4281193 | 4, 5 y 6 |
| `7514112BC6871S`, 5 partes | E 767395–767420, N 4281193–4281225 | 3, 3, 3, 6 y 6 (incompleto) |
| `7117517BC6871N`, 12 partes | Conjunto al NO (E 766939–766979, N 4281517–4281542) | 1 y **16** |
| `7117503BC6871N`, 15 partes | E 767018–767040, N 4281546–4281565 | 9–11 (y partes de 0–1) |

- **Cotejo con OSM** (etiquetas `building:levels`): coincide en los dos bloques comprobados (8 y 8; 12 y 12). **No he podido cotejar** el bloque OSM de 15 plantas junto a la rotonda (`way/375374102`, 1.065 m²) porque su zona quedó en la parte truncada del GML.
- **Cotejo con LiDAR 2016** [M, burdo, el suelo del anillo es ladera]: dos bloques de 12 y 15 plantas en OSM dan 38,5 m y 40,9 m sobre la mediana del suelo próximo, es decir unos 2,7–3,2 m por planta. Úsese 3,0 m como **estimación** y compárese siempre con el LiDAR.
- En OSM, dentro de la ventana de E5 hay edificios de 1 a **18** plantas, no de 4 a 15 como decía el inventario: 21 de 1 planta, y los de 15 (4), 16 (2) y 18 (2). OSM no trae etiquetas de color (`building:colour`, 0).

### 2.2 Elementos del acceso y del puerto

Posiciones en coordenadas locales (x, z) del proyecto. [M] = nuestros datos; el resto, fuente indicada.

| Elemento | Dato | Fuente y tipo |
|---|---|---|
| **Real Club Náutico** | Huella 946 m² (OSM `way/141309218`; x = 351, z = −1139). Altura de 6,2 m a 6,9 m según el método (mediana de clase 6 sobre el suelo; el inventario dio 6,9). 2–3 plantas (Catastro). En la foto de 2010 se ve un edificio bajo de paredes claras y cubiertas inclinadas de teja junto a la torre. Club fundado en 1976, "Real" desde 2005 (Wikipedia, sin verificar). Dirección: Avenida Puerto Pesquero s/n (calpe.es) | M, F; aspecto: **E**, una sola foto |
| **Torre** (`man_made=tower`, `way/159567752`) | Huella 21 m² (x = 348, z = −1146). **Redonda**: la foto de 2010 muestra un cilindro color crema con coronación plana; la de 2015 muestra su interior, una **escalera de caracol de ladrillo con cúpula de ladrillo y óculo** y barandilla de acero inoxidable. Diámetro de unos 5,2 m si es circular **[E]**. Altura de **9,1 m** de mediana y 9,9 m de máximo sobre el suelo (12 puntos de LiDAR 2016) | M y fotos Commons; no he encontrado texto sobre su historia |
| **Centro de buceo** (DIVE&DIVE, `way/168275360`) | Huella 1.558 m², x = 352, z = −969; LiDAR 7,0 m; 1–2 plantas (Catastro). OSM lo etiqueta también `waterway=boatyard`. Los directorios lo sitúan "en el Club Náutico": probablemente es una nave grande de la zona de varadero del club | M, directorios sin confirmar |
| **Varadero y grúas** | Nodos `man_made=crane` en x = 295, z = −931 y x = 351, z = −1034 (`travel_lift`). Grúa de 10 t y travel-lift de 50 t (calpe.es) o de 35 t (Wikipedia); varadero de 3.500 m² (Wikipedia) | M, F con conflicto |
| **Marina** | 264 amarres en 7 pantalanes, esloras hasta 30 m (Wikipedia; calpe.es: 264 amarres). Concesión de 2002 por 30 años (guía masmar, solo fragmento de búsqueda). Calado de 0,5 a 4 m según fuente. Otra guía (Fondear, fragmento) da 276 amarres. En OSM hay 6 `man_made=pier` (C, D, E y tres sin nombre, uno `floating`). Pantalanes de tarima de madera con barandilla de acero inoxidable (foto Commons 2015) | F con conflictos, M |
| **Escollera y bocana** | **No está etiquetada** como `man_made=breakwater` en nuestro extracto OSM (solo costa y pantalanes). Hay que trazarla en la ortofoto 2024 o en CV05. En las fotos tiene faro rojo y muelle de coronación con aparcamiento | M, N |
| **Puerto Blanco (marina nueva)** | Obras iniciadas en septiembre de 2023, 150 amarres con pantalanes flotantes, dique reforzado con unas 20.000 t, pasarela elevada, 2 restaurantes (AlicantePlaza 07/02/2025: apertura prevista para el verano de 2025). Está "junto al puerto viejo" y su playa regenerada gana unos 700 m². **No sé dónde cae respecto a nuestra área** ni si está en la ortofoto de 2024 | F, ubicación **N** |
| **Aparcamiento público junto al club** | OSM `way/375341022`, `access=yes`, 402 m², x = 336, z = −1215, unos 75 m al norte del club. Otro, `way/375101473`, `access=yes`, `fee=no`, 6.012 m², lejos (x = 138, z = −1464) | M |
| **Avinguda del Port / Avinguda de l'Illa de Formentera** | Asfalto (OSM `surface=asphalt`); Avinguda del Port con `maxspeed=30`, 318 m + 265 m + 67 m en tres vías; Avinguda de l'Illa de Formentera de 123 m con `lane_markings=no`. **Puente** de 35 m (`way/37656547`, `bridge=yes`, `layer=1`) con placa "Inauguración del Puente" (nodo `5588818526`). 6 nodos `highway=crossing`. No hay bordillos, farolas ni arbolado etiquetados | M |
| **Rotonda** | `way/168275364`, `junction=roundabout`, **12,1 m** de diámetro (caja del anillo; el islote físico será menor). La ortofoto 2024 muestra palmeras en ella y a lo largo de la avenida | M |
| **Marcas viales y bordillos** | Plazas de aparcamiento marcadas en blanco y acera de adoquín o baldosa rojiza en las fotos de 2023 del puerto pesquero; **no hay medida ni foto de la avenida concreta** | F (foto), N |
| **Bloques de apartamentos** | Ver 2.1. Colores en la foto aérea Commons de 2013 y en la ortofoto: crema, ocre, naranja y blanco, con balcones corridos. Sin etiquetas de color en OSM | **E**, de fotos |

### 2.3 Fotos y vistas de calle

Todas son **referencia**, salvo que se indique CC BY (se pueden usar con atribución, aunque son vistas, no texturas).

| Fotos | Autor y licencia | Fecha | Qué muestran |
|---|---|---|---|
| `Vue sur le port de calpe` (2010), `Calpe - panoramio (55)` (2014); sin mirar: `(84)`, `(91)`, `(10)`, `(54)`, `(57)`, `Le port de calpe et le penon de ifach` (puerto pesquero) | *chisloup*, **CC BY 3.0** | 2010–2014 | La primera muestra la torre redonda y el edificio del club; la segunda, la marina, el faro de la escollera y los bloques de la avenida |
| `Calp, club nàutic del port`, `Club nàutic, port de Calp`, **`Escala de la torre del club nàutic`**, `Port de Calp, zona del club nàutic`, `El port de Calp`, `Rosa dels vents al port de Calp` | *Joanbanjo*, CC BY-SA 4.0 | 21/05/2015 | Pantalanes con tarima y barandilla; **interior de la torre** |
| `Escullera del port de Calp des del Penyal d'Ifac`, `Port de Calp, escullera`, `Edificis de Calp des del penyal d'Ifac` | *Joanbanjo*, CC BY-SA 3.0 | 02/11/2013 | Escollera y fachada urbana desde el Peñón |
| `Port de Calp 02/04/05/06/09`, `Passeig marítim Calp` | *Francesc Fort*, CC BY-SA 4.0 | 26/08/2023 | Puerto pesquero (al oeste, no es el acceso de E5): palmeras, marcas, farolas, pavimento |
| `Puerto deportivo en Calpe` | *LANOEL*, CC BY-SA 3.0 | 03/01/2007 | Marina |
| **Mapillary** | Colaboradores, **CC BY-SA 4.0** (centro de ayuda de Mapillary) | — | Cobertura no comprobada: la API exige `access_token` y no se crean cuentas. Hay que pedirle al usuario un token, o consultarlo él en el navegador |
| **Flickr CC** | — | — | No consultable sin clave de API |
| **KartaView** | — | — | La API no respondió (400) |

### 2.4 Contradicciones y huecos de E5

| Dato | A | B | Qué hacer |
|---|---|---|---|
| Plantas máximas del entorno | OSM del inventario: 4–15 | Catastro 16; OSM 18 (hotel) | Usar LiDAR para la altura y atribuir Catastro solo como validación |
| Travel-lift | 50 t (calpe.es) | 35 t (Wikipedia) | Irrelevante para el modelo |
| Número de amarres | 264 (calpe.es, masmar, Wikipedia) | 276 (Fondear) | Irrelevante: no se modelan barcos individuales |
| Centro de buceo | Edificio propio de 1.558 m² (OSM) | "En el Club Náutico" (directorios) | Tratarlo como nave del club |
| Licencia Catastro | CC BY 4.0 (CODSI, según 003) | Cesión de 2016 con transformación obligatoria (documento de INSPIRE) | Aplicar la segunda |
| Historia de la torre | — | — | **[N]** No hay fuente |
| Ubicación de Puerto Blanco | — | — | **[N]** Mirar la ortofoto 2024 al sur y la web del Ayuntamiento |

### 2.5 Recomendación para E5

- **Volúmenes**: huella de OSM (`ODbL`, ya separada) cruzada con CV05; altura de LiDAR 2016, con 3,0 m por planta como estimación solo para validar. Catastro, solo atributo derivado.
- **Club**: volumen de 946 m² y unos 6,5 m de alto (LiDAR) con cubierta inclinada (una sola foto); torre cilíndrica de unos 5,2 m de diámetro (estimado) y unos 9–10 m (LiDAR). Marcado como aproximación.
- **Marina**: pantalanes planos desde `man_made=pier`; escollera trazada de la ortofoto. Sin barcos individuales, salvo un material de textura de "manchas blancas" si hace falta.
- **Calle**: asfalto y marcas desde la máscara de firmes; puente de 35 m como malla simple; palmeras desde la ortofoto, no desde OSM.
- **Antes de modelar Puerto Blanco**: confirmar si existía en 2024.

## 3. Lista de descargas propuesta (para aprobar después)

No se ha descargado nada. Tamaños en bytes cuando los conozco por la propia respuesta.

### 3.1 Recomendada

| # | URL | Nombre propuesto | Tamaño | Licencia | Autor | Para qué |
|---|---|---|---|---|---|---|
| 1 | `https://www.marqalicante.com/contenido/particulos/pub_227.pdf` | `marq14-2023-menendez-domus-pobla-ifach.pdf` | 6.903.435 B | © MARQ y autor; sin licencia abierta. Referencia | J. L. Menéndez Fueyo | **P1** (Fig. 4, plano 1:250), P2, medidas del Edificio 6 y la Puerta del Norte |
| 2 | `https://dialnet.unirioja.es/descarga/articulo/4939614.pdf` | `marq-extra01-2014-menendez-pobla-ifach.pdf` | 5.305.478 B | © MARQ y autores; referencia | Menéndez, Pina, Torrecillas, Ferrer | **P3** (Fig. 2, torres numeradas), medidas de iglesia, campanario y puerta |
| 3 | `https://www.marqalicante.com/contenido/int_arqueologicas/72%20Parque%20Natural%20del%20Penyal%20d%27Ifac%20%28Calp%29.pdf` | `m2006-marq-penyal-ifac.pdf` | 788.087 B | © Colegio de Doctores y Licenciados; referencia | Menéndez Fueyo | Torre 1, Bazzana (pp. 11–12), alzados |
| 4 | `https://www.marqalicante.com/contenido/int_arqueologicas/74%20Penyal%20d%27Ifac.%20Proyecto%20IFAC.%20Sectores%20Muralla%20de%20Poniente%2C%20Muralla%20Norte%20e%20Iglesia%20%28Calp%29.pdf` | `m2008-marq-ifac.pdf` | 708.568 B | idem | Menéndez Fueyo | Iglesia, patín |
| 5 | `https://www.marqalicante.com/contenido/int_arqueologicas/92%20Penyal%20d%27Ifac.%20Proyecto%20IFAC.%20Sectores%20Muralla%20de%20Poniente%2C%20Muralla%20Norte%20e%20Iglesia%20%28Calp%29.pdf` | `m2009-marq-ifac.pdf` | 862.965 B | idem | Menéndez Fueyo | Separación de torres, Torre Campanario |
| 6 | `https://www.marqalicante.com/contenido/int_arqueologicas/doc_186.pdf` | `m2011-marq-ifac.pdf` | 462.621 B | idem | Menéndez, Ferrer, Pina | Cota 59,06 m, geotextil, hotel, Torre 5 |
| 7 | `https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf` | `catastro-inspire-licencia-v1.pdf` | 100.483 B | Documento oficial | DG del Catastro | Citar la licencia |
| 8 | `https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-bu-WFS.pdf` | `catastro-inspire-bu-wfs-v1.pdf` | 139.132 B | Documento oficial | DG del Catastro | Parámetros y límites del WFS |
| 9 | WMS ICV 1956–57: `https://terramapas.icv.gva.es/0202_1956AMSB0050?service=WMS&version=1.3.0&request=GetMap&layers=1956AMSB0050_PAN&styles=&crs=EPSG:25830&bbox=767380,4281000,767700,4281260&width=1280&height=1040&format=image/jpeg` | `icv1956-pobla-320m.jpg` | 249.905 B (ya visto); recorte menor: 108.677 B | **CC BY** (dataset de datos abiertos de la GVA) | ICV | Estado previo al parque; referencia |
| 10 | Catastro WFS `BU.BUILDINGPART` en 4 cajas de ≤ 0,1 km² cubriendo E 767060–767460, N 4280860–4281600 | `data/raw/catastro-bu-e5-*.gml` | **estimado** de 3 a 5 MB (las tres cajas ya vistas pesaron 117.881 B, 1.247.978 B y 11.128 B) | Licencia de 2016: solo uso transformado; **no commitear** | DG del Catastro | Validar plantas |
| 11 | Miniaturas de 960 px de Commons: `Jaciment arqueològic de la Pobla d'Ifach, Calp`, `Torre campanar de l'església de la pobla d'Ifach`, `Vista de la pobla d'Ifach des del penyal d'Ifac, Calp` | `ref-pobla-*.jpg` | 210.9 KB, 274.2 KB y 266.7 KB (≈ 0,75 MB) | CC BY-SA 3.0 (*Joanbanjo*, 2013). Referencia | Joanbanjo | Estado visible |
| 12 | Miniaturas de 960 px de Commons: `Vue sur le port de calpe`, `Calpe - panoramio (55)`, `Club nàutic, port de Calp`, `Escala de la torre del club nàutic` (500 px), `Port de Calp, zona del club nàutic`, `Calp, club nàutic del port` | `ref-puerto-*.jpg` | 228,1; 169,1; 155,2; 112,4; 175,5; 175,2 KB (≈ 1,0 MB) | *chisloup* CC BY 3.0 (las dos primeras) y *Joanbanjo* CC BY-SA 4.0 (el resto). Referencia | chisloup, Joanbanjo | Club, torre, marina |

**Total medido de lo recomendado**: 15.031.154 B (MARQ) + 239.615 B (Catastro, docs) + 249.905 B (ICV) + unos 0,75 MB y 1,0 MB (miniaturas) ≈ **17,3 MB**. Con una estimación de 3 a 5 MB para el GML, **unos 20 a 22 MB** en total.

### 3.2 Opcional o no posible

| Recurso | Motivo |
|---|---|
| Volumen *Jornades d'Arqueologia de la Comunitat Valenciana 2016-2018* (Dialnet `libro?codigo=784292`; copias en RUA y UJI). Contiene "Ifach ad portas", pp. 385–404 | Tamaño desconocido y superior a 10 MB; WebFetch no lo lee. Descarga manual en navegador |
| Aranegui y Bazzana 1980 (Persée, DOI 10.3406/casa.1980.2332) | Lectura gratis en la web; el PDF devuelve 403 a herramientas automáticas. Descarga manual |
| Ortofoto ICV 1956–57 completa (hoja 1:10.000, TIFF) | Tamaño no publicado; el recorte WMS basta |
| Fotos de Commons a resolución completa | Entre 1,4 y 7,3 MB cada una; no hacen falta |
| Mapillary | Requiere token de desarrollador gratuito; lo debe crear el usuario |

## 4. Clasificación de recursos

- **Usables como textura (CC0 o CC BY)**: ninguno de los hallados para E5 o E6 sirve como textura. Las fotos de *chisloup* (CC BY 3.0) se podrían usar con atribución, pero son vistas, no texturas. La textura sigue saliendo de CC0 de Poly Haven o ambientCG, comparando con fotos.
- **Solo referencia (CC BY-SA o copyright, visibles)**: P1, P2, P3, P4; memorias MARQ; fotos Commons de *Joanbanjo*, *Francesc Fort*, *LANOEL* y *Tagzania*; Mapillary; Wikipedia como texto.
- **Datos medidos o abiertos**:
  - OSM (ODbL, ya separado);
  - ortofoto ICV 2024 y 1956–57 (CC BY; la de 1956 con la licencia del conjunto de datos de la GVA);
  - MDT y LiDAR 2016 (CC BY 4.0);
  - CV05 (CC BY 4.0);
  - Catastro INSPIRE (cesión de 2016: solo transformado).
- **No usables**: el plano del blog de castillos (sin autor y con reproducción restringida); coordenadas MARQ de 2006 y 2011; cualquier cifra del tipo "11–13 m de altura" sin fuente.

## 5. Fuentes consultadas

Pobla d'Ifac:
- MARQ, ficha de la VII campaña: https://www.marqalicante.com/es/intervenciones/proyecto-ifac-pobla-medieval-viia-campana/
- M2011: https://www.marqalicante.com/contenido/int_arqueologicas/doc_186.pdf
- M2006: https://www.marqalicante.com/contenido/int_arqueologicas/72%20Parque%20Natural%20del%20Penyal%20d%27Ifac%20%28Calp%29.pdf
- M2008: https://www.marqalicante.com/contenido/int_arqueologicas/74%20Penyal%20d%27Ifac.%20Proyecto%20IFAC.%20Sectores%20Muralla%20de%20Poniente%2C%20Muralla%20Norte%20e%20Iglesia%20%28Calp%29.pdf
- M2009: https://www.marqalicante.com/contenido/int_arqueologicas/92%20Penyal%20d%27Ifac.%20Proyecto%20IFAC.%20Sectores%20Muralla%20de%20Poniente%2C%20Muralla%20Norte%20e%20Iglesia%20%28Calp%29.pdf
- X1: https://dialnet.unirioja.es/descarga/articulo/4939614.pdf
- A14: https://www.marqalicante.com/contenido/particulos/pub_227.pdf
- Monografía 2018 (ficha): https://www.marqalicante.com/en/product/la-pobla-medieval-de-ifach-calp-alicante-10-anos-de-arqueologia-medieval-en-el-penyal-difac/
- Dialnet, obras de Menéndez Fueyo: https://dialnet.unirioja.es/servlet/autor?codigo=246868 · "Ifach ad portas": https://dialnet.unirioja.es/servlet/libro?codigo=784292
- UA: https://web.ua.es/es/sicos/pobla-medieval-de-ifach.html · MACMA: https://www.macma.org/turismo/patrimonio/la-pobla-difac · Guía de castillos: http://guiacastillosalicante.blogspot.com/2014/03/fortaleza-de-ifach-calpe-alicante-ca-229.html · Fortificaciones de España: https://castillosricsol.es/murallas-de-ifach/ · El Reto Histórico: https://elretohistorico.com/pobla-ifac-muralla-ciudad-medieval-calp · Blog del proyecto: https://proyectoifach.blogspot.com/
- Notas: campaña XXI: https://lamarina.eldiario.es/2026/09/15/el-marq-busca-nuevos-restos-de-la-muralla-medieval-de-la-pobla-difac-en-una-nueva-campana-de-excavaciones/ · torre Laborde (2017): https://alicanteplaza.es/el-marq-descubre-una-gran-torre-defensivaen-la-pobla-medieval-difac · Puerta del Oeste (2019): https://alicanteplaza.es/alicanteplaza/confirman-el-hallazgo-de-la-puerta-del-oeste-de-la-pobla-medieval-de-ifach · 30 m de muralla (2022): https://alicanteplaza.es/descubrenunnuevotramodemurallade30metrosdurantelasexcavacionesenlapobladeifachdecalp · edificio defensivo: https://www.marqalicante.com/en/el-marq-descubre-un-edificio-defensivo-junto-al-sistema-de-acceso-de-la-pobla-medieval-de-ifach/ · dos viviendas (2025): https://www.marqalicante.com/en/las-excavaciones-del-marq-en-la-pobla-difac-sacan-a-la-luz-restos-de-dos-viviendas-medievales-del-siglo-xiv/
- Aranegui y Bazzana 1980: https://www.persee.fr/doc/casa_0076-230x_1980_num_16_1_2332
- Commons: https://commons.wikimedia.org/wiki/Category:Pobla_medieval_d%27Ifach · https://commons.wikimedia.org/wiki/Category:Port_of_Calp
- ICV 1956–57: https://dadesobertes.gva.es/es/dataset/4e371513-50b5-4470-a52d-3074f3d22814 · WMS: https://terramapas.icv.gva.es/0202_1956AMSB0050?service=WMS&request=GetCapabilities

E5:
- Catastro INSPIRE: https://www.catastro.hacienda.gob.es/webinspire/index.html · licencia: https://www.catastro.hacienda.gob.es/webinspire/documentos/Licencia.pdf · WFS BU: https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-bu-WFS.pdf
- Real Club Náutico Calpe: https://www.calpe.es/es/descubre-calpe/turismo-nautico/clubes-nauticos/real-club-nautico-calpe · https://es.wikipedia.org/wiki/Real_Club_N%C3%A1utico_de_Calpe · guía masmar: https://guias.masmar.net/index.php/Puertos/Comunidad-Valenciana/Puerto-Deportivo-Club-N%C3%A1utico-de-Calpe
- Puerto Blanco: https://alicanteplaza.es/alicanteplaza/marina-alta/el-nuevo-puerto-blanco-de-calp-abrira-sus-puertas-este-verano-150-amarres-y-nueva-playa
- DIVE&DIVE: https://cursosdebuceo.com/es/centros/calpe/diveydive-centre-de-busseig/573
- Mapillary: https://www.mapillary.com/developer/api-documentation · https://help.mapillary.com/hc/en-us/articles/115001770409

## 6. Correcciones a documentos 003

1. `003-fotos-referencia.md`, fotos 5 y 7 (Commons `panoramio (56)` y `(58)`, "torre en ruinas, E6"): **no es una ruina medieval**. La (58) muestra una torre cuadrada revestida de sillería, con ventana vertical y cubierta de teja. Panoramio la geolocaliza 156–187 m al sur del polígono de la Pobla (la deriva de Panoramio es de decenas de metros, no tantas). Probable parte del Casal o de una torre del siglo XX. No usarla como referencia de torre medieval.
2. `003-entorno-construido.md`, §2.3 y §6.1: la memoria MARQ 2008 (`marq-2008`) **ya está leída** (6 pp.; sin planos) y también las de 2006, 2009 y 2011. El plano del MARQ **sí existe** en abierto (P1) y está en PDF libre.
3. `003-inventario-datos-propios.md`, §2: el polígono OSM de la Pobla cubre 2.326 m² y su centroide está en x = 543, z = −1157; coincide con lo excavado visible, pero no con las coordenadas que publica el MARQ, que son erróneas (§1.3). Las plantas de los bloques del puerto llegan a 16 (Catastro) y 18 (OSM), no a 15.

# 005 — Tiempo, cielo y memoria: hora del día, clima real, cielo nocturno y "antes y ahora"

- Fecha: 12/10/2026. Autor: agente de investigación. Estado: **investigación; no se ha descargado ningún dato al repositorio**; solo se ha editado este fichero.
- Ámbito: sol y luna reales para Calp, ciclo día/noche, cielo nocturno, clima actual y presets, y un modo "antes y ahora" con ortofotos y documentos históricos. Encaja con el carril L1 (`docs/specs/002-fase-b-paralelizacion.md`: "sol real con SunCalc para Calp", presupuesto de cielo y atmósfera ≤ 2 llamadas de dibujo y ≤ 1 ms) y con el sistema de mar (`app/src/world/sea/system.ts`, hoy plano, "F3 pone olas Gerstner").
- Cómo se verificó (todo hoy, 12/10/2026): llamadas reales a las APIs (cabeceras CORS y cuerpos), lectura de `GetCapabilities` y de `GetMap` de los WMS, lectura de las fichas de licencias y comparación del cálculo del sol y la luna con el USNO. Las imágenes históricas se **miraron** en el panel del navegador, sin guardarlas. Cuando algo no se pudo comprobar, se dice en la sección 8.
- Marco: ADR 0007 (solo CC0 y CC BY; CC BY-SA solo en audio y como fichero aparte, ADR 0011), "sin backend, sin cuentas, sin cookies, sin analítica" y la rejilla local (ADR 0004: `x = E − 767000`, `z = −(N − 4280000)`).

## Resumen (la respuesta primero)

| Necesidad | Fuente recomendada | Licencia | Privacidad del visitante |
|---|---|---|---|
| Clima ahora y próximas 48 h | **Open-Meteo** (forecast + marine + air-quality), pedido por un **job programado** que publica un `weather.json` de ~10 KB junto al sitio | CC BY 4.0 (datos), uso gratuito "no comercial"; enlace "Weather data by Open-Meteo.com" junto a los datos | Si lo hace el job, el navegador **no contacta con nadie**. Si lo hiciera el navegador, la IP del visitante llegaría a Open-Meteo (Suiza) y a sus servidores en Europa y Norteamérica |
| Calima | **CAMS** (`dust` y `aerosol_optical_depth`) a través de la API de calidad del aire de Open-Meteo | Atribución a CAMS ENSEMBLE + Open-Meteo | Igual que arriba |
| Oleaje | Marine API de Open-Meteo (DWD EWAM ~5 km, MFWAM 8 km) | Atribución a DWD + Open-Meteo | Igual que arriba |
| Sol y luna | **SunCalc 2.1.1** (BSD-2-Clause, 8,2 KB gzip). Validado hoy contra el USNO: orto, ocaso y luna dentro del redondeo al minuto; posición del sol al 0,002° | BSD-2-Clause | Cálculo local, sin red |
| Planetas y giro del campo de estrellas | **Astronomy Engine 2.1.19** (MIT, 46,8 KB gzip) cargado solo para el cielo nocturno | MIT | Cálculo local |
| Atmósfera de día | **`Sky` de three r186** (Preetham, ya con nubes) más un retoque propio de crepúsculo y noche. Sin LUT de dispersión en la v1 | MIT (three) | Sin red |
| Estrellas | **Bright Star Catalogue (BSC5)**, 9.096 estrellas; para Calp bastan **2.887 (V ≤ 5,5)** o **5.080 (V ≤ 6,0)**, unos 50–80 KB empaquetadas | **Sin licencia declarada por el productor** (catálogo de hechos de 1991, NASA/ADC); riesgo bajo, ver 3.1 | Sin red |
| Vía Láctea | **ESO/S. Brunier, eso0932a** (panorama 6000 × 3000, centrado en la Galaxia) | **CC BY 4.0**, crédito exacto "ESO/S. Brunier" | Sin red |
| Luna | **NASA CGI Moon Kit** `lroc_color_2k.jpg` (447 KB) | Sin licencia propia en la ficha; política general de NASA (contenido no sujeto a copyright en EE. UU.) | Sin red |
| Ortofotos "antes" | **ICV**: 1945, 1956–57, 1977, 1985, 1989 (color, costa, 10 cm), 1999, 2009 (costa). IGN publica las mismas series en su WMS `pnoa-historico` | **CC BY 4.0** (lo declaran los `GetCapabilities` de los dos servicios) | Se bajan una vez y se empaquetan; sin red en tiempo de ejecución |
| Fotos históricas | **No hay ninguna con CC0 o CC BY** entre las encontradas. Hay cinco pistas con derechos restrictivos (y dos más sin ficha leída) y cuatro vías para conseguir permiso (sección 4.5) | — | — |

Descargas pedidas: unos **10,1 MB** para el conjunto recomendado (sección 6), sin contar las librerías de npm.

Decisiones que se proponen (sección 7): el navegador nunca llama a un tercero; `weather.json` lo genera un job; un único esquema `WeatherState` sirve para el clima real y para los presets; el modo "antes y ahora" muestra en blanco y negro lo que es en blanco y negro.

---

## 1. Clima real

### 1.1 Open-Meteo: lo que se comprobó hoy

| API | Qué da | Celda y modelos | Comprobado |
|---|---|---|---|
| `api.open-meteo.com/v1/forecast` | `current` (datos de 15 min) y `hourly`: nubes baja, media y alta, `visibility`, viento a 10 m (velocidad, dirección, ráfaga), precipitación, `weather_code`, humedad, punto de rocío, presión | Modelo "best match" (por defecto). Para la cima devuelve la celda 38,658 N, 0,056 E, **elevación 74 m**, unos 3 km al norte de la roca. Con `elevation=332` acepta la altura de la cima (responde `elevation: 332.0`). Con `models=icon_eu` la celda es 38,6875 N, 0,0625 E; con `ecmwf_ifs025`, 38,75 N, 0,0; **AROME France HD no cubre Calp** (devuelve `null`) | Llamada real: 511 B con 5 variables; `current` admite `visibility` y `cloud_cover_low/mid/high` |
| `marine-api.open-meteo.com/v1/marine` | `wave_height`, `wave_period`, `wave_direction`, oleaje de fondo (`swell_*`), oleaje de viento, temperatura del mar, corriente, nivel del mar | **El punto de consulta hay que elegirlo a mano**: con 38,62 N, 0,09 E la celda es 38,625 N, 0,125 E (mar abierto al este, ~5 km); con las coordenadas de la cima y `cell_selection=sea` devolvió 38,625 N, 0,042 E, otra celda. DWD EWAM 0,05°, MFWAM 0,08°, ECMWF WAM 9 km. La doc avisa de que la precisión es limitada en la costa y de que no sirve para navegar | Llamada real; hoy: ola 0,14 m, período 3,3 s, dirección 156°, mar a 24,6 °C |
| `air-quality-api.open-meteo.com/v1/air-quality` | `dust` (µg/m³, polvo sahariano cerca de la superficie), `aerosol_optical_depth` (550 nm, indicador de calima), PM10, PM2,5, índice europeo | CAMS Europa 0,1° (~11 km) y CAMS global 0,4° (~45 km); previsión de 4 a 7 días | Llamada real; hoy: `dust` 0,0 y AOD 0,09 (aire limpio) |
| `archive-api.open-meteo.com/v1/archive` | Tiempo de cualquier fecha pasada: ERA5 (0,25°) desde 1940 y ERA5-Land (0,1°) desde 1950, con 5 días de retraso | — | Llamada real para el 15/07/1990 |

- **CORS:** las cuatro devuelven `access-control-allow-origin: *` (cabeceras leídas hoy). Se podrían llamar desde el navegador; no es lo que se recomienda (1.2).
- **Tamaño:** current + 48 h por horas de todo lo que usaríamos son **9,6 KB** de JSON (forecast 4,5 + marine 3,2 + air 1,9), unos 2–3 KB en gzip (estimación; el gzip no se midió).
- **Límites del plan gratuito:** 600 llamadas por minuto, 5.000 por hora, 10.000 por día y 300.000 por mes (el mensual no se aplica hoy, según la página de precios). Con un job cada 15–30 min son 3 llamadas × 48–96 = menos de 300 al día.
- **Sin clave** para uso no comercial: la documentación no pide SDK ni autenticación.

**Licencia y atribución**
- Datos: CC BY 4.0. Hay que poner un enlace junto a cada lugar donde se muestren datos de Open-Meteo; el ejemplo de su página es `<a href="https://open-meteo.com/">Weather data by Open-Meteo.com</a>`. No basta la pantalla de créditos: va **al lado del panel de tiempo**.
- Calidad del aire: debe citarse al proveedor CAMS ENSEMBLE (METEO FRANCE, Ineris y el resto de institutos del conjunto, vía Copernicus Atmosphere Monitoring Service) y a Open-Meteo.
- Oleaje: debe citarse a **DWD** y a Open-Meteo.
- Archivo histórico: "Generated using Copernicus Climate Change Service information" (su página pone el año 2022; para 2026, el año de la consulta).
- Los modelos de origen tienen sus licencias: DWD y ECMWF en CC BY; **Météo-France y NOAA con licencia propia**; el Met Office, CC BY-SA. Para evitar problemas, el job fija el modelo (ICON o ECMWF, ambos CC BY) en lugar de dejar "best match" abierto, cuyo modelo en Calp no he podido identificar.
- Código de Open-Meteo: AGPLv3 (permite autoalojar con Docker).

**Uso "no comercial" y sector público**
- La página de términos pone como no comercial: sitios o apps de entidades sin ánimo de lucro sin suscripciones ni anuncios, investigación pública en instituciones públicas y contenido educativo. **No nombra a las administraciones locales.**
- Un regalo al municipio sin publicidad encaja en el espíritu, pero **conviene pedirlo por escrito** a info@open-meteo.com (dirección que da la página de precios). Si dicen que no: plan comercial (los precios no están publicados), autoalojar (AGPLv3, hay que bajar los modelos) o pasar a AEMET + CAMS directos (más trabajo).

**Privacidad: lo que implicaría llamar desde el navegador**
- La empresa es **OpenMeteo GmbH, Bürglen (UR), Suiza**; ley suiza. La Comisión Europea lista a Suiza entre los países con decisión de adecuación.
- Los términos dicen que pueden recogerse datos no personales, como direcciones IP, para mantenimiento y prevención de abusos, que los registros del servidor pueden contener coordenadas geográficas y que se borran a los **90 días**. No mencionan el RGPD ni un acuerdo de encargado de tratamiento.
- Los servidores están en Europa y Norteamérica, con GeoDNS (no dicen en qué países).
- Una IP es dato personal en el RGPD. Un comprador público tendría que declararlo, justificar la base legal y aceptar la transferencia. **Todo eso se evita** si la llamada la hace un job y no el visitante. Es también lo que mantiene la promesa del proyecto: "sin cookies, sin analítica", y ninguna petición a terceros.
- No he podido comprobar si el límite de 10.000 al día es por IP o por aplicación. Importa solo si se llamara desde el navegador.

### 1.2 Un job programado que publica `weather.json`

Es la opción recomendada. Qué hace falta:

| Pieza | Detalle |
|---|---|
| Programador | Cualquiera de estos dos. **GitHub Actions** `schedule` (verificado en la documentación): mínimo cada 5 min, en UTC, puede retrasarse con carga alta (conviene elegir un minuto poco cargado), solo corre en la rama por defecto y **se desactiva solo tras 60 días sin actividad en el repositorio** si es público. **Cron o timer del servidor del comprador** (lo más natural si el sitio lo aloja el Ayuntamiento): un script de unas 40 líneas. Otras opciones (Cloudflare Workers con cron, etc.) no las he verificado |
| Frecuencia | Cada 15–30 min (el `current` de Open-Meteo se renueva cada 15 min) |
| Qué hace | Pide forecast, marine y air-quality para la cima (38,6334 N, 0,0745 E; `elevation=332`; `timezone=UTC`; unidades SI), valida la respuesta con zod, escribe `weather.json` de forma atómica y añade `generatedAt` y las cadenas de atribución |
| Dónde se publica | Mismo origen, ruta `/weather.json`: no hace falta CORS. `Cache-Control: max-age=300` |
| Claves | Ninguna para Open-Meteo. Si se usara AEMET, la clave va en una variable de entorno del job (nunca en el repositorio ni en el bundle) |
| Si falla | El cliente comprueba `generatedAt`; si falta o tiene más de 3 h, **cae a un preset** (1.7) y lo dice en pantalla. Se avisa al responsable si el fichero lleva más de 6 h sin renovarse |
| Hora elegida por el usuario | Para hoy y mañana se lee la serie horaria del propio `weather.json`. Para otras fechas, un preset, o (ver 1.8) tiempo histórico real |

### 1.3 AEMET OpenData

| Aspecto | Dato (FAQ v1.4 de 28/07/2025, nota legal y pruebas de hoy) |
|---|---|
| Acceso | Clave por correo electrónico, **sin caducidad** (las pedidas desde el 13/09/2017), sin datos personales, varias claves por dirección |
| Límite | **40 conexiones por minuto por usuario** y un límite global |
| CORS | `Access-Control-Allow-Origin: *` en la respuesta 401 (comprobado con una clave falsa). No he probado el segundo paso (la URL `datos` que devuelve la primera llamada) |
| ¿Sitio estático? | **No, con la clave en el bundle**: la cuota de 40 por minuto sería compartida y la clave quedaría pública. Sí desde el job, con la clave como secreto |
| Licencia | **No es CC BY**: nota legal propia (Ley 18/2015), reutilización comercial y no comercial. Atribución: "© AEMET" o "Información elaborada por la Agencia Estatal de Meteorología"; para productos con valor añadido, "Fuente: AEMET". No se puede desnaturalizar el sentido, ni sugerir que AEMET patrocina el uso, y hay que conservar la fecha de actualización. Nota legal de noviembre de 2016 |
| Lo que no hay | Las salidas de modelos numéricos (HARMONIE-AROME, Centro Europeo y **polvo**) **no son datos abiertos** (FAQ 4.3) |
| Para Calp | El municipio es `id03047` en la web de AEMET; hay predicción de playas (Arenal/Bol 0304709, La Fossa 0304704, Cantal Roig 0304707). No he comprobado qué productos de Calp están en la API |

**Conclusión:** AEMET aporta observaciones medidas de estaciones y avisos, no más resolución espacial ni dato que Open-Meteo no dé. **No se usa en la v1.** Queda como contraste opcional y se haría solo desde el job.

### 1.4 Estaciones locales

| Fuente | Qué es | Licencia y acceso | Veredicto |
|---|---|---|---|
| Estación de **Aguas de Calpe** (Davis Vantage Pro 2, 61 m de altitud, 38°38'43" N, 0°02'21" E), publicada por la Universitat de València | Datos cada 5 min (temperatura, humedad, viento, lluvia, radiación solar, UV, presión) | **Sin licencia ni condiciones de reutilización en la página**; solo HTML y ficheros de texto, sin JSON. Contacto: info@aguasdecalpe.es | Útil para contrastar el viento local. **Hay que pedir permiso** antes de reutilizarla |
| **AVAMET** | Red de aficionados de la Comunitat Valenciana | El pie de su web declara **CC BY-NC-ND 4.0**. No encontré API pública ni estación en Calp | **Descartada** (NC y ND) |
| Portal de datos abiertos de la Generalitat (`dadesobertes.gva.es`) | 1.032 conjuntos (marzo de 2025) | Las búsquedas "meteorol" y "estaciones agroclimáticas" dan **0 resultados** hoy | No hay dato de estaciones ahí |
| IVIA / SIAR | Redes agroclimáticas | No he podido comprobar si hay estación ni licencia | Sin verificar |
| AEMET | Estaciones propias | Una noticia de 2016 habla de una estación automática en Benidorm (Salto del Agua). No pude listar las de Calp, Benissa ni Xàbia sin clave | Sin verificar |

### 1.5 Calima

- **Fuente abierta:** `dust` y `aerosol_optical_depth` de CAMS vía Open-Meteo (1.1). AEMET no ofrece el polvo como dato abierto.
- **Estado hoy:** `dust` 0,0 µg/m³ y AOD 0,09 (aire limpio). No hay calima que contrastar hoy.
- **Resolución:** el dominio europeo es de ~11 km y el global de ~45 km; según la doc de Open-Meteo no están acoplados y pueden dar previsiones distintas. Sirve para saber si hay un episodio, no para su estructura.
- **Mapa visual (propuesta, por calibrar):** AOD < 0,15 aire limpio; 0,15–0,3 velo; 0,3–0,5 calima visible; > 0,5 calima intensa, con el horizonte ocre, el sol rojizo y la visibilidad por debajo de 10 km. **Los umbrales son una propuesta y se calibran con fotos de días de calima en Calp.** No hay una fuente que los dé.

### 1.6 Qué variable mueve qué (propuesta)

| Variable (unidad) | Efecto visual | Regla propuesta |
|---|---|---|
| `cloud_cover_low` (%) | Cúmulos y estratos bajos: cobertura, sombra proyectada, nivel de gris | Controla `cloudCoverage` del shader `Sky` de r186 y la atenuación del sol directo |
| `cloud_cover_mid` | Altocúmulos | Segunda capa a mayor altura aparente |
| `cloud_cover_high` | Velo de cirros | Velo fino: halo del sol y tinte del atardecer, sin sombras |
| `visibility` (m) | Niebla y bruma | Distancia de niebla `far ≈ visibilidad` (Koschmieder: extinción β = 3,912 / V). La visibilidad real de hoy es de 39–41 km, así que en el área de trabajo (2,6 × 2,5 km) apenas se nota; manda en días de calima o niebla |
| `precipitation` (mm) | Lluvia: partículas y mojado de la roca | Escala por intensidad; la roca mojada se oscurece y gana brillo |
| `weather_code` (WMO) | Selección del preset | 45/48 niebla; 51–57 llovizna; 61–67 lluvia; 80–82 chubascos; 95–99 tormenta |
| `wind_speed_10m`, `wind_gusts_10m` (m/s) | Balanceo de pinos y matorral; viento en el audio; cabrilleo del mar | Amplitud del balanceo creciente con la velocidad; las ráfagas modulan en el tiempo |
| `wind_direction_10m` (°, de donde viene) | Deriva de las nubes; dirección del oleaje de viento | — |
| `relative_humidity_2m`, `dew_point_2m` | Contraste y bruma | Niebla probable si la temperatura y el rocío están a menos de ~1 °C |
| `dust`, `aerosol_optical_depth` | Calima | Ver 1.5 |
| `wave_height`, `wave_period`, `wave_direction` | Altura, longitud y dirección de las olas (Gerstner); espuma en las rocas | La ola de la celda no es la de la costa de la roca: tratarla como "estado del mar", con espuma por encima de 1 m |
| `is_day` | No se usa | El día y la noche salen del cálculo del sol (sección 2) |

### 1.7 Presets y un único esquema

Una sola estructura `WeatherState` (nubes baja, media y alta, visibilidad, precipitación, viento y ráfaga, dirección, humedad, polvo, AOD, altura, período y dirección de ola), validada con zod. La llena el `weather.json` o un preset, y el resto del código no distingue de dónde viene. Presets propuestos: despejado, parcialmente nublado, nublado, lluvia, tormenta, niebla, calima y **levante** (viento y mar del este). Sus valores son de diseño y se ajustan con fotos.

### 1.8 Tiempo de fechas pasadas

Si el usuario elige una fecha pasada, la API de archivo da el tiempo real (ERA5, 25 km; desde 1940). Es una opción para "antes y ahora", pero **no se llama desde el navegador**: se pueden prefabricar, en un fichero estático, unos pocos días con significado (por ejemplo, el de un vuelo histórico) cuando se decida cuáles. La visibilidad del archivo no se ha comprobado.

---

## 2. Sol y luna

### 2.1 Librerías

| Opción | Licencia | Tamaño | Precisión | Qué cubre |
|---|---|---|---|---|
| **SunCalc 2.1.1** (Agafonkin, `mourner/suncalc`) | **BSD-2-Clause** (texto leído; su `package.json` no declara el campo `license`) | `index.js` 22,9 KB sin minificar, **8,2 KB gzip** | Sol ~0,08° y orto/ocaso ~15 s; luna ~0,09°, orto/ocaso ~15 s, distancia ~20 km (según el autor) | Posición del sol y la luna, fase, orto, ocaso, crepúsculos, tiempos de luna |
| **Astronomy Engine 2.1.19** (cosinekitty) | **MIT** | `astronomy.browser.min.js` 116 KB, **46,8 KB gzip** | ±1 minuto de arco frente a NOVAS | Sol, luna, planetas, rotación J2000 → horizonte (`Rotation_EQJ_HOR`) y galáctica (`Rotation_GAL_EQJ`), magnitud (`Illumination`), fase (`MoonPhase`), tiempo sidéreo |
| NOAA/Meeus propio | Sin dependencia | ~40 líneas (mi script de una sola vez, Python) | Orto y ocaso dentro del redondeo al minuto del USNO (2.2) | Solo sol |

Puntos a vigilar en SunCalc 2.x (cambios respecto a la 1.x, que es la que se suele recordar):
- el **acimut va desde el norte, en el sentido del reloj** (0 = N, 90 = E, 180 = S); en la 1.x iba desde el sur;
- los ángulos son **grados**, no radianes;
- `getPosition` y `getMoonPosition` devuelven la altitud **aparente**, ya corregida de refracción;
- `getTimes` y `getMoonTimes` toman el desfase horario en **minutos**, positivo al este;
- `getMoonTimes` recorre el día UTC de la fecha que se le da.

**Decisión propuesta:** **SunCalc 2.1.1 para el sol y la luna** (en el camino crítico, ya está en el plan de L1) y **Astronomy Engine cargado de forma perezosa** solo cuando el sol esté por debajo de −6° o se active el cielo nocturno, para los planetas y el giro del campo de estrellas. Una prueba exige que ambos coincidan en la posición de la luna dentro de 0,2°. Versiones exactas, sin `^`.

Del sol (en la rejilla local de ADR 0004): con acimut `Az` y altitud `h`, la dirección hacia el sol es `x = sin(Az)·cos(h)`, `y = sin(h)`, `z = −cos(Az)·cos(h)`. Comprobado con el valor actual de `SUN_DIRECTION` en `sky.ts` (sureste, 45° de altura): sale con el signo correcto.

### 2.2 Validación contra el USNO

El USNO (`aa.usno.navy.mil/api`, obra del Gobierno de EE. UU.) se usó como oráculo. Cima (38,6334 N, 0,0745 E), horas locales (UTC+2 en verano, UTC+1 en invierno), nivel del mar y definición estándar de orto y ocaso (−0,833°). "NOAA" es mi script de una sola vez con las fórmulas NOAA/Meeus.

| Fecha | Evento | USNO | SunCalc 2.1.1 | NOAA (propio) |
|---|---|---|---|---|
| 21/06/2026 | Orto / mediodía / ocaso | 06:35 / 14:02 / 21:28 | 06:35:24 / 14:01:32 / 21:27:40 | 06:35:27 / 14:01:31 / 21:27:35 |
| 12/10/2026 | Orto / mediodía / ocaso | 08:06 / 13:46 / 19:26 | 08:05:49 / 13:46:11 / 19:25:59 | 08:06:02 / 13:46:10 / 19:26:18 |
| 21/12/2026 | Orto / mediodía / ocaso | 08:14 / 12:58 / 17:42 | 08:13:50 / 12:57:46 / 17:41:43 | 08:13:55 / 12:57:46 / 17:41:37 |
| 21/06/2026 | Crepúsculo civil (inicio / fin) | 06:03 / 22:00 | 06:03:29 / 21:59:35 | — |
| 12/10/2026 | Crepúsculo civil (inicio / fin) | 07:39 / 19:53 | 07:39:09 / 19:52:37 | — |
| 21/12/2026 | Crepúsculo civil (inicio / fin) | 07:44 / 18:12 | 07:43:58 / 18:11:35 | — |
| 21/06/2026 | Luna: ocaso (madrugada) / salida / tránsito | 01:28 / 13:40 / 19:50 | 01:27 / 13:39 / 19:50 | — |
| 12/10/2026 | Luna: salida / tránsito / ocaso | 10:00 / 15:05 / 20:03 | 09:59 / 15:04 / 20:03 | — |
| 21/12/2026 | Luna: ocaso (madrugada) / salida / tránsito | 05:16 / 15:01 / 22:42 | 05:15 / 15:01 / 22:42 | — |
| 12/10/2026 | Luna: iluminación | 3 % (luna nueva el 10/10 a las 17:50) | 3,7 % a las 14:00 | — |

(Los tiempos de luna de SunCalc se pidieron con `utcOffset` en minutos, 120 en verano y 60 en invierno.)

Posición a una hora concreta (USNO `celnav`, 12/10/2026, 11:00:00 UT, cima):

| Cuerpo | USNO: altura (sin refracción) / acimut | SunCalc 2.1.1: altura aparente / acimut |
|---|---|---|
| **Sol** | 42,639° / 164,345° | 42,658° / 164,343° (la diferencia de altura es la refracción, 0,018°) |
| **Luna** | 25,298° geocéntrica, paralaje −0,841° → 24,46° topocéntrica / 148,329° | 24,498° (con refracción) / 148,328° |
| Venus | 25,735° / 153,243° | — (por validar con Astronomy Engine) |
| Marte | 38,939° / 264,286° | — |
| Júpiter | 46,205° / 249,058° | — |

- El **sol** coincide con el USNO a 0,002° en acimut y dentro del redondeo al minuto en orto y ocaso. La **luna**, al minuto y a 0,001° en acimut.
- Los valores del USNO de las tablas son **fixtures** para las pruebas, con tolerancia de ±60 s en horas (el USNO redondea al minuto) y 0,1° en ángulos.
- **No ejecuté el código de Astronomy Engine** (solo leí su API y su licencia): queda por validar con los planetas de arriba. SunCalc sí se ejecutó, importándolo en memoria desde la versión 2.1.1 de unpkg, sin guardarlo.
- No usar `sunrise-sunset.org` como referencia: su día sale ~1,5 min más largo que el del USNO.

### 2.3 Horizonte real y altura de la cima

- Desde la cima (332 m oficiales; 325–328 m en el MDT) el horizonte del mar está unos **0,53° por debajo** (fórmula estándar `1,76′·√h`, **cálculo mío, sin fuente**). El sol sale en el mar del este unos **3 minutos antes** que a nivel del mar (12/10: 08:03 en lugar de 08:06). Al oeste, el relieve puede adelantar el ocaso; con el MDT en la escena sale solo (no lo he calculado).
- Alturas máximas del sol en Calp: **74,8°** el 21 de junio y **27,9°** el 21 de diciembre (declinación ±23,44°).

### 2.4 Luz según la altura del sol

| Momento | Altura del sol | Iluminación aproximada |
|---|---|---|
| Sol directo | — | 32.000–100.000 lux |
| Fin del crepúsculo civil | −6° | ~3,4 lux |
| Luna llena, noche clara | — | 0,05–0,3 lux |
| Luna cuarto | — | ~0,01 lux |
| Luz de estrellas, o noche cubierta sin luna | — | ~0,0001 lux |

Los crepúsculos náutico (−12°) y astronómico (−18°) los da `getTimes` (`nauticalDawn`, `nightEnd`). La exposición de la cámara debe bajar de forma continua para que la noche sin luna no sea negra y la luna llena sí dé forma al terreno.

### 2.5 Dispersión atmosférica en móvil

| Opción | Licencia | Coste y estado | Veredicto |
|---|---|---|---|
| **`Sky` de three r186** (leído en `node_modules/three`) | MIT (three). El fichero cita a Preetham et al. y a la implementación de Simon Wallner; **no encontré un aviso de licencia distinto en el fichero y no verifiqué la licencia original de ese GLSL** | Un pase de fragmentos sobre un cubo. r186 ya incluye nubes (`cloudCoverage`, `cloudDensity`, `cloudElevation`, `cloudScale`, `cloudSpeed`; fbm de 4 octavas) y el disco solar. Sin estrellas: la noche es un suelo constante (`0.1 × Fex`). El coste en el teléfono de referencia **no está medido** | **Recomendado** para el día. Añadir crepúsculo y noche propios y medir con `?perf` |
| LUT tipo Hillaire 2020 (UE) | El código de ejemplo de `sebh/UnrealEngineSkyAtmosphere` figura como MIT; es solo HLSL para Windows y DX11 | Evita el trazado de rayos en pantalla con una textura pequeña de vista del cielo. **No encontré una versión de three con WebGL2 y licencia confirmada, ni medidas en móvil** | No en la v1 |
| Bruneton 2017 | "BSD", variante sin confirmar | Precálculo de texturas 4D/3D; no verifiqué los requisitos | No en la v1 |
| `@takram/three-atmosphere` 0.19.1 | MIT | 36,9 MB desempaquetado, pares de React, `@react-three/fiber`, `postprocessing`; versión 0.x | **Descartada** para esta app |

Si el crepúsculo de Preetham no convence frente a fotos del lugar, el siguiente paso es una **tabla 1D de colores del cielo según la altura del sol**, medida de fotos de la hora azul y del ocaso en Calp (el usuario es de allí), con el mismo contrato `AtmosphereState` (`horizon`, `zenith`, niebla, sol). Sin dependencias nuevas. Va en el protocolo de fotos.

### 2.6 Luna: fase y textura

- **Fase:** `getMoonIllumination` da la fracción iluminada, la fase y el ángulo del limbo brillante (`angle`, grados en la 2.x), y el signo de creciente o menguante (`waxing`).
- **Dibujo:** en el propio shader del cielo, como disco de 0,52° de diámetro sombreado con la dirección del sol vista desde la luna, con una textura de 1–2k. No hace falta otra llamada de dibujo.
- **Textura:** NASA CGI Moon Kit (SVS 4720): `lroc_color_2k.jpg` (2048 × 1024, 447,2 KB), con mapa de elevación `ldem_3_8bit.jpg` (1024 × 512, 108,9 KB) si se quiere relieve. La ficha avisa de que los mapas están optimizados para el aspecto y no para uso científico, **no declara licencia** y remite a las guías de reproducción. La política general de NASA dice que sus imágenes, en general, no están sujetas a copyright en EE. UU., y permite el uso informativo y educativo, incluidas las webs, con reconocimiento. Habría que enmendar ADR 0007 para admitir "obra del Gobierno de EE. UU. (dominio público)" como categoría. Crédito: "NASA's Scientific Visualization Studio".

### 2.7 Hora y zona horaria

- La app no necesita red para "ahora": usa el reloj del dispositivo y `Intl.DateTimeFormat('es-ES', { timeZone: 'Europe/Madrid' })` para mostrar la hora local.
- El horario de verano termina el **25/10/2026** (último domingo de octubre, 03:00 CEST → 02:00 CET). El control de hora debe manejar la hora repetida.
- Para las pruebas, usar instantes UTC y no depender de la zona del ordenador.

---

## 3. Cielo nocturno

### 3.1 Catálogos de estrellas

| Catálogo | Contenido | Licencia (verificada) | ¿Se puede usar? |
|---|---|---|---|
| **Yale Bright Star Catalogue (BSC5)** | 9.110 objetos, 9.096 estrellas con V; mag ≤ 6,5; posiciones J2000, V, B−V, tipo espectral | La ficha de CDS (V/50, "Hoffleit y Warren 1991", NASA/ADC) **no trae licencia ni condiciones**. La tabla BSC5P de HEASARC tampoco. Una búsqueda mostró la entrada de data.gov con la etiqueta "U.S. Government Works"; no pude abrir esa ficha (404 en data.nasa.gov) | **Sí, con salvedad**: es un catálogo de hechos astrométricos de 1991 con coautoría de NASA. El derecho sui generis de bases de datos de la UE dura 15 años (de memoria, no verificado aquí). **Que lo confirme el asesor jurídico del comprador** y que ADR 0007 lo recoja |
| HYG (astronexus; ahora en Codeberg) | Catálogo derivado de Hipparcos, Yale y Gliese (por su nombre; no leí el README) | **CC BY-SA 4.0** (texto de `LICENSE` leído) | **No**: SA. Obligaría a un fichero aparte con una excepción nueva a ADR 0007 |
| Hipparcos y Tycho (ESA, 1997) | Catálogos astrométricos | **CC BY-NC 3.0 IGO**, "Credit: ESA" (página oficial de ESA) | **No** (NC) |
| Gaia (ESA) | Más de mil millones de estrellas | Las imágenes de ESA/Gaia/DPAC llevan CC BY-SA 3.0 IGO (visto en espejos de Commons; **no leí la licencia del propio catálogo**) | **No** |
| Mapa de estrellas de NASA SVS 4851 | Imagen de 1.700 millones de estrellas | La ficha no declara licencia, pero pide el crédito "ESA/Gaia/DPAC" porque usa Gaia DR2 | **No**, hasta resolver el origen |

**Cuántas estrellas hacen falta** (recuento hecho hoy sobre `catalog.gz` de CDS: 573.921 B):

| Magnitud límite | Estrellas |
|---|---|
| V ≤ 3,0 | 174 |
| V ≤ 4,0 | 518 |
| V ≤ 4,5 | 904 |
| V ≤ 5,0 | 1.630 |
| **V ≤ 5,5** | **2.887** |
| **V ≤ 6,0** | **5.080** |
| V ≤ 6,5 | 8.404 |

- Para un cielo de clase Bortle 5–6 (límite a simple vista 5,1–6,0, según la tabla de la escala) bastan **2.887 estrellas (V ≤ 5,5)**; para un cielo más oscuro, 5.080. Cada estrella cuesta ~16 B (ascensión recta, declinación, magnitud, B−V): **46–81 KB**.
- Se dibujan como `Points` con tamaño y brillo según la magnitud y el color según B−V: **una llamada de dibujo**. El giro del cielo sale de `Rotation_EQJ_HOR`, que incluye la precesión (en 2026 las coordenadas J2000 se han desplazado ~0,36°; cálculo mío). Un parpadeo sutil es opcional.
- Los 5 planetas visibles se añaden a la misma lista con la magnitud de `Illumination(body, date).mag`.
- Una prueba barata de orientación: la **Polar tiene una altura igual a la latitud (38,6°) con un margen de ±1°**, porque está a unos 0,7° del polo (de memoria).

### 3.2 Vía Láctea

| Fuente | Licencia | Tamaño | Veredicto |
|---|---|---|---|
| **ESO/S. Brunier, "The Milky Way panorama" (eso0932a)** | **CC BY 4.0** (política general de ESO, salvo indicación contraria, con adaptaciones permitidas si se indican los cambios; el crédito debe ir **sin alterar**: "ESO/S. Brunier"; la página de la imagen no indica excepción) | 6000 × 3000: JPEG de publicación **4,6 MB**, JPEG grande 7,8 MB, TIFF 27,7 MB | **Recomendada.** Vista hoy en el navegador (JPEG de pantalla de 1280 × 640): es una imagen **2:1 de todo el cielo, con la Galaxia centrada y el plano a lo largo del ecuador**; se ven las Nubes de Magallanes abajo a la derecha. Falta confirmar el sentido de la longitud al mapearla |
| Solar System Scope, `2k_stars_milky_way.jpg` y `8k_...` | CC BY 4.0, que permite incluso el uso comercial; sin crédito concreto | No listado | Su procedencia no se declara (dice basarse en datos de NASA) y puede arrastrar la condición de Gaia. **No** |
| NASA SVS 4851 (mapas profundos) | Ver 3.1 | 34–124 MB (4k y 8k, EXR) | **No** |
| Mellinger (panorama de la Vía Láctea) | No verifiqué | — | No investigada |

Plan: bajar el JPEG de 4,6 MB, **desenfocarlo y reducirlo a 1024 × 512 o 2048 × 1024** (para que no duplique las estrellas, que ya van como puntos) y empaquetarlo en KTX2 en el pipeline, con el crédito literal y la mención "modificada". Se muestrea en el shader del cielo con `Rotation_GAL_EQJ` × `Rotation_EQJ_HOR`. Es una textura más (≈ 0,3–1 MB en KTX2; estimación, no medida).

### 3.3 Contaminación lumínica en Calp

- **No tengo ningún dato medido de Calp ni de la cima.** Las búsquedas no devolvieron valor de Bortle ni de SQM para el municipio.
- El mejor dato abierto del mundo, el *New World Atlas of Artificial Night Sky Brightness* (Falchi et al. 2016, GeoTIFF de 2,9 GB), está hoy en **CC BY-NC 4.0** (según el registro de B2FIND). **No se puede incluir**, aunque sí consultar para fijar el valor.
- Lo que sí se ve en las ortofotos: el casco urbano, el puerto y los bloques están al **noroeste y oeste** de la roca; al este y al sur, mar. Desde la cima, un resplandor cálido bajo el horizonte oeste–noroeste y un horizonte este oscuro son físicamente razonables. No hace falta modelar la ciudad.
- **Valor por defecto propuesto (suposición, no medida):** Bortle 5, límite a simple vista 5,5. Para saber el real, cualquiera de estas dos: leerlo en `lightpollutionmap.info` (capa "World Atlas 2015") sobre la cima, o una medida con un medidor SQM del usuario en la cima (el usuario es de Calp).
- Idea para "antes y ahora": un cielo más oscuro en el modo histórico (no hay fuente que dé cuánto; se marcaría como ilustrativo).

### 3.4 Presupuesto de render

La tabla de L1 da cielo y atmósfera ≤ 2 llamadas de dibujo y ≤ 1 ms. Reparto propuesto: **1** el domo (Preetham, nubes, Vía Láctea y luna dentro del shader) y **1** las estrellas y planetas (`Points`). Sin más. Hay que medirlo en el teléfono de referencia con `?perf`.

---

## 4. Antes y ahora

### 4.1 Ortofotos históricas del ICV (CC BY, con WMS y descarga)

Todas son del Institut Cartogràfic Valencià, en ETRS89 / UTM 30 (EPSG:25830), con WMS 1.3.0 de MapServer, WMTS, y descarga por hoja en ECW y TIFF. Los `GetCapabilities` de las seis primeras series de la tabla (1945 a 1999; el de 2009 no lo leí) dicen: `AccessConstraints` = "**CC BY 4.0 Generalitat**", `Fees` = "No se aplican condiciones", `MaxWidth`/`MaxHeight` = 4096, contacto `responde_icv@gva.es`. La ficha de cada serie en el portal de datos abiertos dice "Creative Commons Attribution" (sin versión) y enlaza `http://www.icv.gva.es/condiciones-de-uso-de-la-geoinformacion-icv` (esa página no respondió hoy).

| Serie (ID del servicio) | Vuelo | Píxel y color | Cubre el Penyal | Lo que se ve |
|---|---|---|---|---|
| **1945** (`0202_1945AMSA0050`, capa `1945AMSA0050_PAN`) | Americano **serie A**, 1945–46 (la ficha da dos fechas finales: 10/1946 y 1947), escala ~1:45.000 | 50 cm, pancromática | **Sí** (visto) | Roca casi sin construir, un pequeño espigón, rectángulos oscuros al noroeste que **parecen** las balsas de las salinas (no verificado), caminos y bancales |
| **1956–57** (`0202_1956AMSB0050`, `1956AMSB0050_PAN`) | Americano **serie B**, 05/05/1956 a 01/08/1957, escala 1:33.000 | 50 cm, pancromática | **Sí** (visto) | No se ven puerto deportivo ni bloques en el Arenal; sí un espigón y un dique, parcelas rectangulares al noroeste y una fuerte **sombra** en la vertiente oeste de la roca |
| **1977** (`0202_1977INTM0025`, `1977INTM0025_PAN`) | **Interministerial**, 1976–78 | **25 cm**, pancromática | **Sí** (visto) | Edificios con sombra larga junto a la playa del Arenal; puerto con dársena; manchas oscuras en el fondo marino al este |
| **1985** (`0202_1985NACI0050`, `1985NACI0050_PAN`) | **Nacional**, 1982–86, escala ~1:30.000 | 50 cm (píxel de origen 0,41 m) | **Sí** (visto; borrosa, con reflejo del sol en el mar) | Dársena con embarcaciones; poco contraste en la roca |
| **1989** costa (`0202_1989COST0010`, `1989COST0010_RGB`) | Dirección General de Costas, 03/1989 a 12/1990, hojas 1:5.000 | **10 cm, color** | **Sí** (visto), solo la franja de costa: quedan huecos blancos en el mar | Marina con pantalanes, bloques, **color**, fondo marino cercano |
| **1999** (`0202_1999QUIN0050`, `1999QUIN0050_RGB`) | **Quinquenal**, 07/1999 a 10/2000 | 50 cm, color | **Sí** (visto) | Marina, urbanización, color |
| **2009** costa (`0202_2009COST0010`, `2009COST0010_RGB`) | 01/07 a 25/11/2009 | **10 cm, color** | **Sí** (visto), solo la franja de costa | Color; las aguas poco profundas dejan ver el fondo cerca de la orilla |

Otras series del ICV en el portal (todas `cc-by`): 2002, 2004, 2005 y 2007 PNOA de Alicante a 50 cm, 2009 PNOA de Alicante a 25 cm, 2007 costa a 10 cm, 2012, 2014, 2017–2024 y otras. La de 2024 es la que ya usamos (`icv-orto-2024-0848-7-2`).

URL de ejemplo para repetir una captura (la caja es el área de trabajo, de 2,6 × 2,55 km):
`https://terramapas.icv.gva.es/0202_1956AMSB0050?service=WMS&version=1.3.0&request=GetMap&layers=1956AMSB0050_PAN&styles=&crs=EPSG:25830&bbox=766400,4279450,769000,4282000&width=1000&height=981&format=image/jpeg`

- La hoja de 2024 que ya tenemos (`0848_7-2`) ocupa E 766.380–770.390 y N 4.279.420–4.282.250 (medido en el fichero local: 16.040 × 11.320 px a 25 cm). **Cubre toda el área de trabajo**; las series históricas se sirven por hojas de la misma familia (MTN10), pero **no he comprobado que sea la misma rejilla**.
- Atribución propuesta (por confirmar con el ICV): "Ortofoto {año} {resolución} © Institut Cartogràfic Valencià, Generalitat (CC BY 4.0)", con, para los vuelos históricos, la mención del origen que dan las fichas: vuelo americano (U.S. Army Map Service) escaneado por el CNIG; el de costas, de la Dirección General de Costas. Esta mención adicional es **una sugerencia mía**.
- Hay un servicio del ICV de "descargas con recorte" (`descargas.icv.gva.es/00/geoprocesos/descarga`), que parece dejar elegir una hoja o un recorte; **no lo probé** (necesita un navegador interactivo).

### 4.2 IGN/CNIG

| Servicio | Contenido | Licencia (leída en `GetCapabilities`) |
|---|---|---|
| **`https://www.ign.es/wms/pnoa-historico`** | 37 capas: PNOA anual 2004–2024, SIGPAC (1997–2003), OLISTAT (1997–98), **Nacional (1981–86)**, **Interministerial (1973–86)** y **Americano serie B (1956–57)** | `AccessConstraints` = "**CC BY 4.0 scne.es**"; `Fees` = "No se aplican condiciones"; 4096 px máximo |
| `https://www.ign.es/wms/primera-edicion-mtn` | Primera edición del MTN50 y las minutas "catastrones" (1910–1970) | "CC BY 4.0 ign.es" |
| **`https://www.ign.es/wms/minutas-cartograficas`** | **Planimetrías manuscritas de municipios (1870–1950)** | Acceso permitido siempre que se cite la autoría y propiedad del IGN con la fórmula «© Instituto Geográfico Nacional de España» |
| `fototeca.cnig.es/wms/fototeca.dll` y el Centro de Descargas del CNIG (`codFamilia=INTMI`) | Fotogramas escaneados del Interministerial, escala ~1:18.000, píxel de 0,27–0,45 m, en ECW | La ficha de datos.gob.es remite a las condiciones de uso del IGN (no verificadas) |

- Las series del IGN y del ICV vienen del mismo vuelo; el ICV las sirve ya como ortofoto por hojas, así que **el ICV es la fuente principal** y el IGN, el respaldo y la fuente de los fotogramas sueltos.
- **Las planimetrías sí cubren Calp**: en la capa `Minutas`, con una caja de 5 × 4,5 km sobre el Penyal, se ve el plano de color crema del término de Calp con la punta del Peñón y los rótulos "Salinas" y "El Salador". No sé la fecha exacta de esa hoja (varía entre 1870 y 1950). Sirve como referencia de lo que había antes del turismo, **no como textura**.
- El vuelo de 1929 (Ruiz de Alda) del visor histórico del ICV cubre el sur de Alicante y la cuenca del Segura, **no Calp** (artículo de 2015). Según esa misma fuente, los fotogramas de los vuelos americanos solo admitían descarga visual; es antigua y hay que confirmarla.

### 4.3 Qué descargaríamos y cuánto pesa (medido hoy)

Recorte de **1,5 × 1,5 km** (E 767.000–768.500, N 4.280.000–4.281.500: el sendero, el centro, el túnel, la cima y el Mirador de Carabiners) a 0,5 m/px = 3000 × 3000 px, JPEG de la propia WMS (tamaño bajado y descartado, sin guardar):

| Serie | Tamaño del JPEG (B) | MB |
|---|---|---|
| 1945 | 1.280.005 | 1,28 |
| 1956–57 | 858.205 | 0,86 |
| 1977 | 1.105.345 | 1,11 |
| 1985 | 1.349.617 | 1,35 |
| 1989 costa | 1.269.991 | 1,27 |
| 1999 | 710.865 | 0,71 |
| 2009 costa | 2.242.035 | 2,24 |

- A la **resolución nativa de 25 cm** (4 teselas de 750 m a 3000 px): 1977, 4 × 1,17 MB = **4,7 MB**; 1989 color, 4 × 1,63 MB = **6,5 MB**. A 10 cm, una tesela de 300 m pesa 1,54 MB; para 1,5 km serían 25 teselas (~39 MB), que no hacen falta.
- La misma ortofoto de 1956 en **PNG sin pérdida** pesa **6,7 MB** (3000 px): el JPEG es 8 veces menor.
- El **área de trabajo completa** (2,6 × 2,55 km) a 0,5 m es ~3 veces el recorte (la razón de áreas, **estimación**).
- Las hojas **nativas** no se midieron (el listado del servidor da 403 y el enlace final se ve solo en el navegador). **Estimación** a partir de la hoja de 2024 (172,8 MB, JPEG, 4 bandas, 726 M de muestras → 0,24 B/muestra): 50 cm pancromática ≈ 11–23 MB por hoja; 25 cm pancromática ≈ 43–90 MB; las de 10 cm de la costa, hojas de 1:5.000, sin estimar. Ese es el camino si se quiere un fichero **con hash** en `data/manifest.lock.json`, como las demás fuentes (tipo `file` del catálogo).
- Un recorte con la WMS exigiría un tipo nuevo `wms` en `data/catalog.toml` (URL, caja, tamaño, formato y sha256 del resultado) y un cambio pequeño en `penyal fetch`. Es **código nuevo**, no solo datos.

### 4.4 Cómo se verían sobre nuestro terreno (advertencias)

- **Blanco y negro:** 1945, 1956, 1977 y 1985 son pancromáticas. **Se muestran en escala de grises**; no se colorean con la ortofoto de 2024, que sería inventar. El color empieza en 1989.
- **Sombras horneadas:** la de 1956 tiene la vertiente oeste casi negra por el sol bajo del vuelo. Con la luz dinámica del juego se sumaría una segunda sombra. Opciones: usarla como textura de **albedo atenuada** y dividir por un sombreado del MDT con el sol del vuelo (la hora exacta sobre Calp no consta en las fichas) o mostrarla solo como capa de comparación, con un deslizador.
- **Ortorrectificación:** estas ortofotos se corrigieron con modelos de elevación de su época; en acantilados y paredes verticales puede haber desplazamientos. Nuestro MDT es de 2016 (CC BY). No se midió el error; se verá al superponer el trazado del sendero y la costa.
- **Qué cambia en la escena en el modo "antes":** los edificios del centro (en `buildings.glb`; una nota del registro, sin fuente, habla de 1992), el puerto deportivo y el paseo marítimo (OSM) y los bloques del Arenal. La roca, el túnel (1918), la Pobla y el sendero no cambian. Hay que decidir por época qué sistemas se ocultan; eso es un fichero de datos por época, no código.
- **Mar:** el fondo y el color del mar no salen de aquí.

### 4.5 Fotografías y documentos históricos

**Resultado: ninguna con CC0 o CC BY**, que es lo que admite ADR 0007.

| Hallazgo | Fecha | Derechos que declara | Dónde |
|---|---|---|---|
| "Penyal d'Ifac i Calp" y panorámicas, **13 fotografías aéreas oblicuas de SACE** (Servicios Aéreos Comerciales Españoles; Rodríguez Escalona, C.), copias de 13 × 13 cm | 29/08/1967 (el fondo se titula "SACE (1960–1986)") | **"In Copyright"** (rightsstatements.org/InC/1.0), en Europeana | Institut Cartogràfic i Geològic de Catalunya, `cartotecadigital.icgc.cat` |
| "Vista de la platja de Calpe i el Peñón de Ifach", Enric Ribas i Virgili (1895–1938), negativo de vidrio | Entre 1920 y 1930 | **CC BY-NC-ND 3.0** | Memòria Digital de Catalunya (Centre Excursionista de Catalunya) |
| "Peña de Ifach vista desde el mar", dibujo de Rafael Monleón y Torres (1843–1900) | 1863–1900 | **CC BY-NC-SA 4.0** | Biblioteca Digital Hispánica (BNE) |
| "Spanien. Blick auf den Peñón de Ifach..." y "Straße bei Peñón de Ifach...", Paul W. John | **1939** | "In Copyright – Educational Use Permitted" | Deutsche Fotothek |
| Diapositiva en color del Penyal, John W. Rhoden (1918–2001) | 1953 | Sin licencia; "© PAFA Archives" | PAFA Archives, `MS.2019.01.1883` |
| Postal "Fotografía Hnos. Galiana" | Sin fecha | No leí la ficha | Museo del Traje, Centro de Investigación del Patrimonio Etnológico (Europeana) |
| Fototeca.cat (imágenes de la Gran Enciclopèdia Catalana sobre el Penyal y Calp) | — | No verificado | — |

- **Wikimedia Commons:** la categoría del Penyal tiene 5 subcategorías (parque natural, centro de visitantes, Pobla medieval, vistas remotas, vistas desde el Penyal); ninguna es histórica. En las primeras 40 de 208 coincidencias de "Peñón de Ifach / Penyal d'Ifac" y en las 25 de "Salinas de Calpe", las fechas de toma que constan van de 2005 a 2022; **no apareció ninguna foto anterior a 1990**. Es una búsqueda limitada (no recorrí las 208), no una prueba de que no exista.
- **Del túnel de 1918, de las salinas en explotación o del puerto antes del turismo:** no encontré ninguna foto con licencia libre.
- **Vías realistas, en orden:**
  1. **Pedir permiso al Arxiu Municipal de Calp / Museu d'Història**, y al **Fotoclub Ifach**, cuyo fondo se donó al Ayuntamiento (nota municipal sobre el calendario turístico de 2020). Lo natural es una licencia CC BY expresa para la app, firmada por el Ayuntamiento.
  2. **ICGC:** pedir a `cartotecadigital.icgc.cat` la licencia de reutilización de las fotos de SACE de 1967 (Europeana dice "In Copyright").
  3. **Dominio público por plazo de autor:** Monleón (†1900) y Ribas (†1938) murieron antes del 7/12/1987, así que según la página de Commons sobre España se les aplica el plazo de 80 años tras la muerte, ya cumplido. La digitalización no debería crear derechos nuevos (art. 14 de la Directiva (UE) 2019/790; de memoria, **no verificado cómo lo traspuso España**). Aun así, las etiquetas NC de los repositorios piden una consulta jurídica antes de usar.
  4. **Fotos simples antiguas:** Commons usa la etiqueta `PD-Spain-photo` para fotografías simples con al menos 25 años; **no pude confirmar desde cuándo se cuentan los 25 años ni qué es una "mera fotografía"**. No se usa nada así sin informe jurídico.
- Mientras tanto, el "antes" se apoya en las **ortofotos** (CC BY), en las **planimetrías del IGN** y en **texto con fuente** (el registro de hechos ya cita 1918 para el túnel y la relación con las salinas).

### 4.6 Propuesta de modo "antes y ahora" (mínimo)

- Épocas: **1945 o 1956–57** (antes del turismo), **1977** (el boom, mejor resolución en blanco y negro), **1989** (color, ya con puerto) y **2024** (hoy). Cuatro es suficiente; 1985 y 1999 no aportan.
- Una textura de macro-color por época (grises donde corresponde) y una lista de sistemas ocultos por época. Mismo contrato que el terreno: la época elige el conjunto de texturas, no la geometría.
- El cielo y el clima no cambian con la época. Lo que sí podría cambiar es la contaminación lumínica (3.3).

---

## 5. Mar (prioridad baja)

| Fuente | Qué da | Licencia y coste | Veredicto |
|---|---|---|---|
| Ortofotos del ICV de **costa** (1989 y 2009, 10 cm, color) | El fondo y el color del agua poco profunda cerca de la orilla; las manchas oscuras de las praderas (de `Posidonia`; **no verificado que lo sean**) | CC BY, ya cubierta en 4.1 | **La opción barata**: sirve para ajustar el color del mar cerca de la orilla. No da profundidad |
| **EMODnet Bathymetry** (DTM 2024) | Batimetría en una rejilla de **1/16′ (~115 m)** | La página no nombra la licencia; remite a un "Terms of Use" que no abrí. Cita: "EMODnet Digital Bathymetry (DTM 2024)", EMODnet Bathymetry Consortium, DOI 10.12770/cf51df64-56f9-4a99-b1aa-36b8d7b743a1 | Demasiado gruesa para la roca (la propia ficha avisa de que la precisión varía). **No** |
| **Copernicus Marine** (turbidez, transparencia, clorofila) | Productos de satélite | Licencia gratuita, mundial, no exclusiva y perpetua; crédito "Generated using E.U. Copernicus Marine Service Information; DOI...". Ofrece registro e inicio de sesión (cuenta personal e intransferible); la página no dice si es obligatorio para descargar | Más trabajo del que merece. **No** |

Conclusión: **mantener el mar procedural** (color y olas por viento y oleaje del marine API) y, si se quiere, ajustar un degradado de profundidad cerca de la orilla a partir de la ortofoto de 2009 o 2024 que ya tenemos. No hay una fuente barata de batimetría de detalle.

---

## 6. Lista de descargas para aprobar

Nada de esto está descargado. Cada fila se descargaría con `penyal fetch` (ficha en `data/catalog.toml`, con hash en el manifiesto).

| # | Qué | Origen | Tamaño | Licencia |
|---|---|---|---|---|
| 1 | Ortofoto 1945 (50 cm, pancromática), recorte de 1,5 km | `terramapas.icv.gva.es/0202_1945AMSA0050` | 1,28 MB | CC BY 4.0 |
| 2 | Ortofoto 1956–57 (50 cm, pancromática), recorte de 1,5 km | `.../0202_1956AMSB0050` | 0,86 MB | CC BY 4.0 |
| 3 | Ortofoto 1977 (25 cm, pancromática), recorte de 1,5 km a 0,5 m (a 25 cm, 4,7 MB) | `.../0202_1977INTM0025` | 1,11 MB | CC BY 4.0 |
| 4 | Ortofoto 1989 costa (10 cm, color), recorte de 1,5 km a 0,5 m (a 25 cm, 6,5 MB) | `.../0202_1989COST0010` | 1,27 MB | CC BY 4.0 |
| 5 | Catálogo BSC5, `catalog.gz` | `cdsarc.cds.unistra.fr/ftp/V/50/catalog.gz` | 0,57 MB (573.921 B) | Sin licencia declarada (3.1) |
| 6 | ESO eso0932a, JPEG de publicación (6000 × 3000) | `eso.org/public/images/eso0932a/` | 4,6 MB | CC BY 4.0 |
| 7 | NASA CGI Moon Kit, `lroc_color_2k.jpg` | `svs.gsfc.nasa.gov/4720/` | 0,45 MB | Política general de NASA (2.6) |
| | **Total del conjunto recomendado** | | **≈ 10,1 MB** | |
| 8 (opcional) | 1985, 1999 y 2009 costa, en recorte de 1,5 km | ICV | 1,35 + 0,71 + 2,24 = 4,3 MB | CC BY 4.0 |
| 9 (opcional) | Las cuatro series recomendadas para el **área de trabajo** completa (2,6 × 2,55 km) en lugar del recorte | ICV | ≈ 3 × 4,5 = 13,6 MB en total, es decir, +9 MB sobre el recorte (estimación por razón de áreas) | CC BY 4.0 |
| 10 (opcional) | Relieve de la luna, `ldem_3_8bit.jpg` | NASA SVS 4720 | 0,11 MB | Ver 2.6 |
| 11 (opcional) | Hojas **nativas** ECW/TIFF por hoja, para tener fichero con hash | `descargas.icv.gva.es` | 100–250 MB (estimación; sin medir) | CC BY 4.0 |

**Librerías (npm, versión exacta, sin `^`):** `suncalc@2.1.1` (8,2 KB gzip) y `astronomy-engine@2.1.19` (46,8 KB gzip, solo en el trozo del cielo nocturno).

**Clima:** ninguna descarga: lo hace el job en tiempo de ejecución (1.2).

---

## 7. Decisiones propuestas y lo que solo puede resolver el usuario o el comprador

**Decisiones propuestas (se confirman al integrarlas; piden ADR donde se indica):**
1. **El navegador nunca llama a un tercero.** El clima llega por `weather.json` generado por un job (ADR corto: afecta al alojamiento y a la CI).
2. **Un único `WeatherState`** con zod; el clima real y los presets lo llenan igual.
3. **SunCalc 2.1.1 para el sol y la luna; Astronomy Engine perezoso** para planetas y giro del cielo. Pruebas con los valores del USNO de 2.2.
4. **`Sky` de three r186** con retoque propio de crepúsculo y noche; una tabla 1D de colores medidos de fotos si Preetham no convence. Sin LUT en la v1.
5. **Estrellas: BSC5 hasta V ≤ 5,5**; Vía Láctea de ESO desenfocada; luna de NASA; todo dentro de 2 llamadas de dibujo.
6. **"Antes y ahora" con las ortofotos del ICV (CC BY)**, en escala de grises donde son pancromáticas; sin fotos hasta tener permiso.
7. **ADR 0007:** añadir "obra del Gobierno de EE. UU." (NASA) y fijar la postura sobre BSC5.

**Solo lo pueden resolver el usuario o el comprador:**
- Escribir a **Open-Meteo** (info@open-meteo.com) y confirmar que este uso es "no comercial".
- Pedir permiso a **Aguas de Calpe** (info@aguasdecalpe.es) si se quiere usar su estación.
- Confirmar con el **ICV** (`responde_icv@gva.es`) la cadena de atribución de los vuelos históricos.
- Pedir fotos históricas con licencia al **Arxiu Municipal de Calp** y al **Fotoclub Ifach**, y a la **ICGC** las de SACE.
- Una **medida SQM** en la cima, o la lectura del mapa de contaminación lumínica.
- Una **consulta jurídica** sobre BSC5 y sobre las obras antiguas (Monleón, Ribas).
- **Fotos de la hora azul y de días de calima** en Calp para calibrar el cielo.

## 8. No verificado

- **Open-Meteo:** si el límite diario es por IP o por aplicación; qué modelo elige "best match" en Calp; si hay un acuerdo de encargado de tratamiento; en qué países están los servidores; el precio comercial; si una administración local cuenta como "no comercial".
- **AEMET:** la lista de estaciones y códigos cerca de Calp; el CORS del segundo paso; los productos de Calp disponibles en la API; el límite global.
- **Estrellas:** la licencia del catálogo BSC5 (no declarada) y el plazo del derecho sui generis; la licencia del catálogo Gaia (solo vi la de sus imágenes).
- **Cielo:** el valor de Bortle o de SQM de Calp; el coste en ms de `Sky` en el teléfono de referencia; la licencia original del GLSL de Wallner; que Astronomy Engine coincide con los planetas del USNO (no ejecuté su código).
- **Vía Láctea:** el sentido de la longitud de la imagen de ESO al mapearla.
- **Históricas:** la fecha exacta de los vuelos sobre Calp; la rejilla de hojas de cada serie; el tamaño de las hojas nativas; el error de ortorrectificación en los acantilados; la fecha de la planimetría de Calp; la ficha de la postal Galiana; las condiciones de uso del IGN para los fotogramas; la transposición española del art. 14 de la Directiva 2019/790; el significado y el plazo de `PD-Spain-photo`.
- **Mar:** la licencia de EMODnet (no abrí su página de términos); que las manchas oscuras sean praderas de `Posidonia`.
- **Hosting:** dónde se alojará el sitio (Cloudflare Workers con cron y otras opciones no se verificaron).

---

## Fuentes

**Clima**
- Open-Meteo, términos y privacidad: https://open-meteo.com/en/terms · precios: https://open-meteo.com/en/pricing · licencia: https://open-meteo.com/en/licence · documentación: https://open-meteo.com/en/docs · marine: https://open-meteo.com/en/docs/marine-weather-api · calidad del aire (CAMS): https://open-meteo.com/en/docs/air-quality-api · archivo: https://open-meteo.com/en/docs/historical-weather-api · código y datos: https://github.com/open-meteo/open-meteo
- Decisiones de adecuación (Suiza): https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en
- GitHub Actions, evento `schedule`: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- AEMET OpenData: https://opendata.aemet.es/centrodedescargas/inicio · FAQ v1.4 (28/07/2025): https://opendata.aemet.es/centrodedescargas/docs/FAQs220424.pdf · nota legal: https://www.aemet.es/es/nota_legal · municipio de Calp: https://www.aemet.es/es/eltiempo/prediccion/municipios/calp-id03047
- Estación de Aguas de Calpe (Universitat de València): https://www.uv.es/femenia/eltempscalp/index.shtml · AVAMET: https://www.avamet.org/ · portal de datos abiertos de la Generalitat: https://dadesobertes.gva.es/

**Sol, luna, atmósfera**
- SunCalc: https://github.com/mourner/suncalc · versiones: https://github.com/mourner/suncalc/releases · paquete: https://unpkg.com/suncalc@2.1.1/
- Astronomy Engine: https://github.com/cosinekitty/astronomy · paquete: https://unpkg.com/astronomy-engine@2.1.19/
- USNO, orto y ocaso: https://aa.usno.navy.mil/api/rstt/oneday · navegación celeste: https://aa.usno.navy.mil/api/celnav
- three.js `Sky`: `app/node_modules/three/examples/jsm/objects/Sky.js` (r186.1) · Hillaire: https://github.com/sebh/UnrealEngineSkyAtmosphere · Bruneton: https://github.com/ebruneton/precomputed_atmospheric_scattering · takram: https://github.com/takram-design-engineering/three-geospatial
- Luna (NASA SVS 4720): https://svs.gsfc.nasa.gov/4720/ · política de medios: https://www.nasa.gov/nasa-brand-center/images-and-media/ · iluminancias: https://en.wikipedia.org/wiki/Lux

**Cielo nocturno**
- BSC5, ReadMe de CDS: https://cdsarc.cds.unistra.fr/ftp/V/50/ReadMe · tabla de HEASARC: https://heasarc.gsfc.nasa.gov/W3Browse/star-catalog/bsc5p.html
- HYG: https://codeberg.org/astronexus/hyg
- Hipparcos y Tycho (ESA): https://www.cosmos.esa.int/web/hipparcos/catalogues
- NASA SVS 4851: https://svs.gsfc.nasa.gov/4851/
- ESO: https://www.eso.org/public/images/eso0932a/ · política de imágenes: https://www.eso.org/public/outreach/copyright/ · prensa: https://eso.org/public/news/eso0932/
- Solar System Scope: https://www.solarsystemscope.com/textures/
- Escala de Bortle: https://en.wikipedia.org/wiki/Bortle_scale · atlas de Falchi (registro): https://b2find.eudat.eu/dataset/df8cd562-df6a-51bf-ad64-7421cf8c8623

**Antes y ahora**
- ICV 1956–57: https://dadesobertes.gva.es/es/dataset/4e371513-50b5-4470-a52d-3074f3d22814 · 1977: https://dadesobertes.gva.es/es/dataset/8330923b-9e26-4075-b9ff-5aca5eadfe41 · API del portal (1945, 1985, 1989, 1999, 2009): https://dadesobertes.gva.es/api/3/action/package_search?q=ortofoto
- WMS del ICV: https://terramapas.icv.gva.es/0202_1945AMSA0050 · …/0202_1956AMSB0050 · …/0202_1977INTM0025 · …/0202_1985NACI0050 · …/0202_1989COST0010 · …/0202_1999QUIN0050 · …/0202_2009COST0010 (todos con `?service=WMS&request=GetCapabilities`)
- IGN: https://www.ign.es/wms/pnoa-historico · https://www.ign.es/wms/primera-edicion-mtn · https://www.ign.es/wms/minutas-cartograficas · ficha del Interministerial: https://datos.gob.es/en/catalogo/e00125901-spaignvuelointerministerial
- Visor histórico del ICV (2015): https://valenciaplaza.com/cvalenciana/una-aplicacion-permite-conocer-la-evolucion-del-territorio-de-la-comunitat-con-imagenes-de-1929-1945-y-1957
- Europeana (búsqueda "Peñón de Ifach"): https://www.europeana.eu/en/search?query=Pe%C3%B1%C3%B3n%20de%20Ifach · SACE: https://www.europeana.eu/en/item/991/https___catalonica_bnc_cat_catalonicahub_lod_oai_cdm21055_contentdm_oclc_org_fsace____23255_ent0 · Ribas i Virgili: https://www.europeana.eu/en/item/773/https___catalonica_bnc_cat_catalonicahub_lod_oai_mdc_csuc_cat_afcecpz____428_ent0 · Monleón: https://www.europeana.eu/en/item/2022717/bnesearch_detalle_bdh0000210987 · Paul W. John: https://www.europeana.eu/en/item/188/item_5HGLHQMQHCH2TTLWDR3C2ESK3JIXJ7CD
- PAFA Archives: https://pafaarchives.org/s/digital/item/82186
- Commons, reglas de copyright en España: https://commons.wikimedia.org/wiki/Commons:Copyright_rules_by_territory/Spain

**Mar**
- EMODnet Bathymetry: https://emodnet.ec.europa.eu/en/bathymetry · Copernicus Marine: https://marine.copernicus.eu/user-corner/service-commitments-and-licence

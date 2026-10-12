# 004 — La experiencia: subir al Penyal de verdad, desde cualquier sitio

- Estado: **borrador del responsable técnico, 12/10/2026**. Encargo del usuario: "empezar a pensar en la experiencia de juego… queda a tu juicio".
- Investigación en la que se apoya:
  - `docs/research/005-experiencia-referentes.md`: referentes, accesibilidad y calendario natural;
  - `docs/research/005-tiempo-cielo-memoria.md`: tiempo real, sol, luna, cielo nocturno e imágenes históricas;
  - `docs/research/004-*`: recursos del acceso, el sendero alto, la Pobla y el puerto.
- Encaje: se construye sobre lo que ya hay (§2) y sobre el contrato de sistemas del ADR 0010. Cada pieza declara su presupuesto por nivel de calidad.
- Reglas que no cambian:
  - nada inventado;
  - cada hecho sale de `content/facts.json`, con sus fuentes y su estado;
  - nunca la ubicación de *Silene hifacensis*;
  - el paso caminando sigue siendo real, 1,4 m/s;
  - sin cuentas, sin cookies y sin analítica.

## 1. Visión

> Que cualquiera, esté donde esté y pueda o no caminar, suba al Penyal tal como es (con su luz de hoy, su tiempo y su historia) y se lleve algo: un recuerdo, un aprendizaje o la cima.

La experiencia tiene que tener valor para cuatro personas distintas. Cada una debe encontrar el suyo en menos de un minuto:

| Quién | Qué busca | Su momento de valor |
|---|---|---|
| Vecino o vecina de Calp | Nostalgia, orgullo | Ve el Penyal con la luz real de este momento. Desliza "1956 ↔ hoy" y reconoce el Calp de antes. Encuentra la foto antigua en el sitio exacto donde se hizo |
| Quien no puede subir: movilidad reducida, mayores, convalecientes | Llegar | Pulsa "Ir a la cima" y sube a ritmo real, sin mareo, con la narración. Arriba recibe su postal de cumbre |
| Escolares y docentes | Aprender en el sitio | Rellenan un cuaderno de campo con especies, historia y geología, cada dato con su fuente. Siguen misiones por curso y tienen una guía para el docente |
| Visitante que prepara la visita | Saber a qué va | Dificultad por tramos, perfil de altitud, tiempo real del recorrido, normas, reservas y cierres, con enlace a la web oficial y la fecha de consulta |

Y un quinto usuario, el comprador: el Ajuntament, con el kiosco de Tourist Info, códigos QR en el inicio del sendero y enlaces a una vista concreta para redes sociales.

## 2. Lo que ya existe

Inventario del código y de los planes, 12/10/2026.

| Pieza | Estado |
|---|---|
| Caminar con teclado, ratón y táctil; primera y tercera persona; 1,4 m/s (correr: 2,6 m/s) | **Hecho** (`app/src/player/controller.ts:10`, `app/src/input/`) |
| Subida automática a cualquier anclaje (tecla P o `?autowalk=`), que frena en escalones y curvas | **Hecho, sin botón en pantalla** (`app/src/player/autowalk.ts`) |
| Empezar en un anclaje (`?start=`); 13 anclajes, entre ellos `park-entrance`, los miradores, el túnel y la cima | **Hecho** |
| Fichas de puntos de interés: datos, esquema y detección por radio | **El sistema existe, pero la ficha no se muestra**: nadie escucha `discover`, no hay elemento en pantalla y solo hay un borrador (`centre`) |
| Cuaderno de campo, guardado en el dispositivo | **Módulo y pruebas hechos, sin conectar** (`app/src/content/notebook.ts`) |
| Registro de hechos: 55 (40 `verified`, 11 `conflict`, 4 `unverified`) y 41 fuentes | **Hecho** (`content/`) |
| Atmósfera con un único escritor (ADR 0010) | **Solo el preset `day`, con el sol fijo** (`app/src/world/sky.ts:26`). El GLSL está por escribir (carril L1) |
| Sonido: 5 grabaciones aprobadas en el catálogo | **Sin sistema de audio** (carril L2) |
| Idiomas es, va, en en la interfaz | Interfaz traducida; contenido solo en es |
| Accesibilidad | Regiones vivas y *reduced motion* en CSS. Falta lo demás |
| Mando, minimapa (F4), sol real (B1, F3), modos y modo foto (fase C), guía en texto y PWA (fase D) | **Planificado**, sin hacer |
| Altímetro, GPS simulado, viaje rápido, tiempo meteorológico, control de la hora, antes/ahora, kiosco, "¿qué estoy viendo?" | **No aparece en ningún plan**: lo añade esta propuesta |

**Consecuencia:** el primer trabajo no es lo más vistoso. Es la base de interfaz del carril L7 (ficha visible, cuaderno conectado y menú de ajustes): sin ella no se ve ningún contenido.

## 3. Principios de diseño

1. **La verdad se ve.**
   - Toda cifra en pantalla (altitud, coordenadas, distancias, tiempos, tiempo atmosférico) es real y lleva su fuente.
   - Lo simulado se llama simulado: "GPS simulado", "hora elegida", "tiempo de ejemplo".
   - Los conflictos se explican, no se esconden. En la cima, el altímetro marca lo que da el modelo y la ficha explica la cifra oficial de 332 m (`summit-altitude`, en estado `conflict`).
   - Lo que sí se sabe: la reseña del IGN pone la base del vértice a 326,714 m y el modelo da 326,68 m en ese punto. Los 328,07 m del LiDAR serán, casi seguro, la cabeza del pilar de 1,20 m (`docs/research/004-recursos-sendero-alto.md`).
2. **Mínima y flotante: el paisaje manda.**
   - No hay cajas ni paneles fijos: texto e iconos pequeños flotan sobre la vista, con una sombra suave para leerse sobre cielo o roca.
   - Por defecto solo se ven cuatro cosas: la hora y el tiempo diminutos, el minimapa, el nombre del sitio cuando llegas y tres botones.
   - Lo demás aparece cuando se pide y se va solo. Todo se puede ocultar ("solo paisaje").
3. **Pensada para niños: todo se ve y se toca.**
   - Ninguna función depende de un atajo de teclado, de un gesto escondido o de pasar el ratón por encima.
   - Cada botón lleva icono **y** palabra, y es grande para un dedo (44 px).
   - Textos cortos en lenguaje sencillo. Las instrucciones se dan con dibujos y palabras ("Arrastra para caminar", "Toca para saber más"), nunca con una lista de teclas.
   - El teclado sigue funcionando entero, como alternativa de accesibilidad.
4. **Ritmo real, sin esperas forzadas.**
   - Se camina a 1,4 m/s. Ir más despacio está permitido; acelerar, no.
   - Para quien no quiere o no puede caminar están el viaje rápido a los miradores y la subida automática.
   - Ninguna de las dos acelera el paso: una salta de punto a punto y la otra camina por ti.
5. **Para todos desde el primer día.**
   - Accesibilidad WCAG 2.1 AA (obligatoria para webs públicas, RD 1112/2018; se espera que la 2.2 sea exigible hacia el 16/12/2026, `005-experiencia-referentes.md`) y opciones contra el mareo.
   - Un modo sentado y una alternativa en texto de toda la ruta.
   - No es una fase final.
6. **Ligera.**
   - Un móvil de gama media es el objetivo.
   - La interfaz va en DOM, sin llamadas de dibujo.
   - Cada sistema 3D nuevo trae su fila de presupuesto (ADR 0010).
   - Todo lo pesado se carga bajo demanda.
7. **Respeto.**
   - Por la privacidad: nada sale del navegador sin decirlo, y nada se rastrea.
   - Por la naturaleza: nunca se anima a salir del sendero, y la *Silene* nunca aparece con ubicación.
   - Por las normas del parque.

## 4. Las capas de la experiencia

La experiencia se organiza en seis capas que se suman sin estorbarse. Cada una se puede encender y apagar, y cada una tiene sentido por sí sola.

### 4.1 Orientación: la pantalla de juego

Boceto sobre capturas reales del juego (12/10/2026, en el torniquete): `docs/specs/004-experiencia/boceto-escritorio.jpg` y `boceto-movil.jpg`. El minimapa es la ortofoto de 2024 con la ruta real, y los 75 m son la altitud real del torniquete. La hora y la temperatura son de ejemplo. Terreno, LiDAR y ortofoto: © Institut Cartogràfic Valencià, CC BY 4.0. Ruta: © colaboradores de OpenStreetMap, ODbL. Texturas: Poly Haven, CC0.

| Pieza | Dónde | Qué muestra | Al tocarla |
|---|---|---|---|
| **Hora y tiempo** | Arriba a la derecha, diminuto | Un icono del cielo, la temperatura y la hora: "ahora en Calp" o "hora elegida" | Abre "Hora y tiempo" |
| **Minimapa** | Abajo a la izquierda en escritorio. Arriba a la izquierda en táctil, porque abajo está el pulgar del joystick | Redondo y con el borde fundido con la escena. Lleva la ruta como línea fina, tu flecha, la N en el borde, y el próximo mirador pegado al borde si queda fuera. El norte va arriba por defecto; girar con tu rumbo es una opción, y con *reduced motion* nunca gira | Abre el mapa grande |
| **Altitud** | Bajo el minimapa | Una cifra: "75 m sobre el mar" | — |
| **Llegada a un sitio** | Centro, abajo | El nombre del sitio y "Toca para saber más ›". Se va solo y no tapa el camino | Abre la ficha |
| **Tres botones** | Abajo a la derecha | Ir a la cima · Cuaderno · Más | — |
| **Créditos** | Esquina inferior derecha, pequeño | Las atribuciones obligatorias (CC BY, ODbL) | Abre los créditos completos |
| **Primera vez** | Sobre la zona del pulgar | "Arrastra para caminar", con una mano dibujada. En escritorio: "Usa las flechas o toca el camino" | Desaparece al moverse |

**"Más"** reúne lo que no hace falta en todo momento:
- mapa y viaje rápido;
- ¿Dónde estoy?;
- hora y tiempo;
- foto;
- ajustes: idioma, sonido, tamaño, contraste, comodidad y "solo paisaje";
- ayuda.

**Mapa grande y viaje rápido:**
- Muestra la ruta, las paradas oficiales y tu posición, con el "GPS simulado" (coordenadas reales del punto, rotuladas como simuladas) y el perfil de altitud con un punto que eres tú.
- Al tocar una parada hay dos opciones:
  - **"Ir ahora"**: la pantalla funde a negro entre 150 y 300 ms, llegas mirando la vista y se anuncia dónde estás, con un botón "Volver";
  - **"Caminar hasta aquí"**: la subida automática, a ritmo real.

**Andar sin joystick:** se podrá tocar un punto del camino para ir hasta allí (B10).

**¿Dónde estoy?**
- Un botón que dice en voz alta, o al lector de pantalla, el lugar, la altitud, el rumbo y la distancia a la próxima parada.
- Así el minimapa no depende de la vista.

**¿Qué se ve desde aquí?**
- Solo en los miradores y a petición, desde la ficha.
- Etiquetas pequeñas sobre el horizonte, con rumbo y distancia reales a lugares con nombre de OSM (fichero ODbL aparte).
- Lo que queda fuera del terreno modelado se rotula "fuera del modelo". Ibiza solo aparece con una fuente que diga que se ve.

### 4.2 Conocimiento: hechos documentados, en su sitio

- **Puntos de interés con ficha**, que ya existen. Se amplían por temas:
  - Historia: la Pobla d'Ifac (siglos XIII–XIV), el túnel de 1918, las salinas, el puerto;
  - Geología, con sus dos versiones documentadas;
  - Flora y Fauna;
  - Paisaje, enlazado con "¿Qué estoy viendo?".

  Cada ficha muestra el estado del dato (`verified`, `conflict`, `unverified`) y sus fuentes, desplegables.
- **Guía de naturaleza por estaciones.** Las especies autóctonas documentadas, con lo que se ve u oye en cada época: floración, aves nidificando, cigarras en verano. Sale del calendario de `005-experiencia-referentes.md`.
  - El calendario es "El Penyal en [mes]". Cada dato se marca como documentado, observado o estimado.
  - Corrige ideas previas:
    - la gaviota de Audouin no cría en el Penyal (pasa por Calp de agosto a octubre); la que cría es la patiamarilla, con puesta en marzo–abril y pollos en mayo–junio;
    - no hay registro abierto de cigarras dentro del parque.
  - Una especie se "encuentra" al pasar por su hábitat, no por una planta concreta. Las especies introducidas, como la *Oxalis* que florece en invierno, se marcan como tales.
  - Imágenes: solo el 1,8 % de las observaciones del parque tienen foto con licencia libre. Hacen falta permisos de observadores concretos, o ilustraciones propias.
  - La *Silene hifacensis* se presenta con su historia y su protección, nunca con un lugar.
- **Cuaderno de campo**, que ya existe, ampliado:
  - sellos por mirador alcanzado, especies encontradas, hechos leídos y la fecha;
  - se descarga como una imagen o un PDF generado en el navegador, sin servidor.
- **Narración**: primero en texto. La voz llega después, grabada en es, va y en, que es lo ideal; la síntesis del navegador queda como respaldo. Se dispara al llegar al sitio y siempre lleva transcripción.

### 4.3 Tiempo vivo: luz, cielo y clima de Calp

- **Reloj del mundo.**
  - Por defecto es "ahora en Calp" (Europe/Madrid). El sol y la luna se calculan en el navegador en su posición real, con la fase de la luna.
  - El usuario puede mover la hora y la fecha: amanecer, mediodía, atardecer, noche y las cuatro estaciones.
  - Un rótulo dice siempre qué hora se ve y si es la real o una elegida.
- **Noche.**
  - Estrellas reales para la fecha y la hora, de un catálogo con licencia libre.
  - La luna con su fase.
  - La Vía Láctea, solo si hay una textura CC0 o CC BY.
  - Luces solo donde hay geometría modelada, el puerto y el centro. La ciudad no se modela, así que no se inventa su resplandor.
- **El tiempo de hoy.** Nubes, viento, visibilidad, lluvia y estado del mar, con datos abiertos actualizados, su atribución y "actualizado a las HH:MM".
  - Privacidad: lo preferible es que el navegador no llame a terceros. Un fichero `weather.json` publicado junto a la web por una tarea programada cumple a la vez la regla de "sin servidor" y la de privacidad. La alternativa es una llamada directa desde el navegador, activada por el usuario.
  - Fuente: Open-Meteo (tiempo, mar y calima con CAMS), CC BY 4.0, con el enlace "Weather data by Open-Meteo.com" junto al tiempo.
  - Su uso gratuito es solo **no comercial**. Si el Ajuntament compra una licencia, hay que confirmar las condiciones o contratar su plan comercial.
  - AEMET no entra en la primera versión, porque su clave quedaría pública en una web estática.
  - Sol y luna: SunCalc 2.1.1 (BSD-2, 8 KB), validado contra el USNO.
  - Cielo de día: el `Sky` de three r186, retocado para el crepúsculo y la noche.
  - Estrellas: el catálogo BSC5 (unas 2.900 hasta magnitud 5,5).
  - Vía Láctea: ESO/S. Brunier, CC BY 4.0.
  - Luna: la textura del NASA CGI Moon Kit.
  - El brillo del cielo nocturno en Calp no tiene ninguna medida. Se usa una suposición (Bortle 5), rotulada como tal.
- **Escenas para jugar con el tiempo**, cada una basada en fenómenos documentados de la zona:
  - día claro, en el que se ve Ibiza solo si hay fuente;
  - temporal de levante;
  - calima;
  - amanecer de verano desde la cima;
  - noche de luna llena;
  - tormenta de otoño.
- **El sonido acompaña.** Gaviotas, mar, viento y cigarras en verano cambian con la hora, la estación y el tiempo, con los sonidos ya catalogados en el ADR 0011.

### 4.4 Memoria: antes y ahora

- **1956 ↔ hoy.**
  - Un deslizador compara en el mapa la fotografía aérea histórica con la ortofoto de 2024.
  - Si cabe en el presupuesto de memoria, la foto histórica también puede sustituir a la ortofoto sobre el relieve 3D: se cambia, no se suma.
  - El ICV tiene ortofotos históricas de 1945, 1956–57, 1977, 1985, 1989, 1999 y 2009, todas en CC BY 4.0. Las cuatro primeras son en blanco y negro y se muestran en gris.
  - La primera versión usa 1945, 1956–57, 1977 y 1989, en un recorte de 1,5 × 1,5 km (unos 4,5 MB).
- **Refotografía.**
  - Algunas fotos antiguas, de dominio público o CC BY, se colocan en el sitio y con el ángulo desde donde se tomaron.
  - Al llegar, "mira cómo era", y la foto se funde con la vista actual.
  - Solo cuando el punto y el ángulo se pueden determinar; si no, va a la galería de la ficha.
  - **No hay fotos antiguas con licencia libre.** Las que existen tienen derechos (SACE 1967, Ribas i Virgili, Monleón).
  - Esta pieza depende de permisos del Arxiu Municipal de Calp, del Fotoclub Ifach o del ICGC. Encaja como aportación del propio Ajuntament.
- **La Pobla d'Ifac.**
  - El trazado excavado se ve en el terreno.
  - Se dibuja sobre la ortofoto de 2024. El plano del MARQ (2023, a 1:250) solo dice qué es cada línea (`004-recursos-pobla-puerto.md`).
  - Una reconstrucción solo se muestra si está publicada y es científica, y se rotula como "hipótesis publicada por…". Nunca una inventada.

### 4.5 Modos de visita

| Modo | Para quién | Qué cambia |
|---|---|---|
| **Paseo libre**, por defecto | Todos | Lo de ahora, más la orientación (§4.1) |
| **Ir a la cima** | Quien no puede o no quiere caminar | La subida automática a ritmo real con narración. Para en los miradores y deja seguir con un toque. Ofrece opciones contra el mareo. Al llegar, la postal de cumbre |
| **Visita guiada** | Visitantes, familias | Salta de parada en parada (viaje rápido) con la narración y las fichas en orden |
| **Escuelas** | Primaria y ESO | Misiones por curso, como encontrar cinco especies o explicar el túnel de 1918, más el cuaderno y una guía para el docente descargable. Sin presión de tiempo y sin datos de los alumnos |
| **Preparar la visita** | Quien va a ir | Una capa práctica: dificultad por tramos, agua, aseos, normas, reserva y cierres. Todo con enlace oficial y fecha de consulta |
| **Kiosco** | Tourist Info, Centre de Visitants | Solo táctil, sin barra de direcciones, con una secuencia de presentación (amanecer, noche, la ruta). Vuelve al inicio tras un rato sin uso |
| **Foto y postal** | Todos | Se oculta la interfaz y la cámara se mueve con libertad cerca de ti, sin salir del corredor. Se pueden elegir la hora y el tiempo. El marco lleva las atribuciones obligatorias y se descarga como PNG. Un enlace "comparte esta vista" codifica posición, hora y tiempo en la dirección, sin rastreo |

### 4.6 Accesibilidad e idiomas

- Teclado completo, lector de pantalla en toda la interfaz, tamaño de texto ajustable y colores seguros para daltonismo en el mapa.
- Subtítulos de toda la narración.
- *Reduced motion*, y opciones contra el mareo: campo de visión, sin balanceo de cabeza, viñeta al moverse y giro por pasos.
- Alternativa en texto: una página "La Ruta Roja en texto" con el perfil, los tramos y todas las fichas. Sirve a lectores de pantalla, a quien no puede usar 3D y a los buscadores.
- es, va y en desde el principio. fr, de y nl quedan a decisión del comprador, por el turismo y los residentes extranjeros.
- La lista de comprobación detallada sale de `005-experiencia-referentes.md`.

## 5. Cómo encaja en la técnica

- **Reloj del mundo** (contrato nuevo y único).
  - Guarda la fecha y la hora en Europe/Madrid y el modo (`real` o `elegida`).
  - Un módulo puro calcula el sol y la luna (posición y fase).
  - El sistema `atmosphere` (L1) es el único escritor de la atmósfera, según el ADR 0010, y traduce todo esto a luz, cielo, niebla y exposición.
  - Los demás leen: el mar (oleaje), la vegetación (viento) y el sonido (L2).
- **Estado del tiempo.**
  - Entrada única: nubes, viento, visibilidad, lluvia, mar y su origen (`real`, `escena` o `por-defecto`).
  - Lo alimenta `weather.json` (instantánea) o una escena.
  - Sin datos, se queda en un tiempo por defecto y lo rotula, nunca falla.
- **Interfaz** (L7).
  - Componentes DOM y SVG, que no gastan llamadas de dibujo: minimapa y mapa grande, altitud y perfil, coordenadas (solo en el mapa grande) y fichas.
  - Leen el estado del jugador a unas 10 veces por segundo, no en cada fotograma, para no forzar el maquetado.
- **Viaje rápido.**
  - `teleport(anclaje, rumbo)` a través del controlador.
  - Antes de terminar el fundido se piden las teselas del destino; si tardan, se ve "cargando" y nunca un terreno vacío.
  - Solo a anclajes dentro del corredor.
- **"¿Qué estoy viendo?"**
  - Un `landmarks.json` derivado de OSM, en fichero ODbL aparte (ADR 0007), con rumbos y distancias calculados.
  - La ocultación se comprueba contra el campo de colisión dentro del modelo; fuera de él, la etiqueta va al horizonte rotulada "fuera del modelo".
- **Antes y ahora.**
  - Un paso nuevo del pipeline genera la foto histórica por tesela cercana, en KTX2 de un canal y con su manifiesto de procedencia.
  - Se carga solo con la capa encendida y **sustituye** a la ortofoto, así que la fila de memoria de textura no crece.
  - El mapa compara dos imágenes.
- **Modo foto.**
  - Se captura el lienzo justo después de dibujar y se compone el marco con las atribuciones en un lienzo 2D. Se descarga en local.
  - "Comparte esta vista" usa el fragmento de la dirección (`#…`), que no llega al servidor.
- **Cuaderno.** Se conecta el módulo existente a `discover`. Se exporta como PNG con un lienzo y como PDF con la impresión del navegador, sin dependencias nuevas.
- **Narración.** Ficheros de audio por ficha e idioma (L2), con subtítulos WebVTT.
- **Kiosco.** El parámetro `?kiosk` activa el temporizador de inactividad y la secuencia de presentación, y quita los enlaces externos.
- **Guía en texto.** Una página HTML generada en la compilación desde `trail.json`, `facts.json` y las fichas. Funciona sin WebGL.
- **Presupuesto.** Cada sistema 3D nuevo trae su fila en `budget.ts`, que solo cambia el integrador:
  - estrellas, 1 llamada (puntos);
  - luna, 1 llamada;
  - lluvia, 1 llamada instanciada, solo en `medium` y `high`;
  - nubes, dentro del sombreador del cielo, sin llamadas extra.

  La interfaz no consume presupuesto 3D.

## 6. Orden: primero lo que lo desbloquea todo, después lo que más valor da

| Fase | Qué | Por qué en este orden | Tamaño |
|---|---|---|---|
| **X0. Base de interfaz** (L7) | Ficha visible al descubrir un punto, cuaderno conectado, menú de ajustes (idioma, sonido, comodidad, calidad), botón "Ir a la cima" y estructura accesible de la interfaz | Sin esto no se ve ningún contenido: es el camino crítico | M |
| **X1. Orientación** | Hora y tiempo diminutos, minimapa con altitud, aviso de llegada, tres botones; mapa grande con GPS simulado, perfil, distancia y tiempo; viaje rápido a las paradas; "¿Dónde estoy?"; opciones contra el mareo | Es lo más útil para los cuatro públicos y no necesita datos nuevos: ortofoto, `trail.json` y el campo de colisión ya están | M |
| **X2. Tiempo vivo** (L1 + L4) | Sol y luna reales, control de hora y fecha, amanecer, atardecer, noche con estrellas y luna. Después, escenas de tiempo (niebla y visibilidad, nubes, viento, lluvia, mar) y por último el tiempo de hoy | Es lo que más emoción da. B1 ya estaba planificado y aquí se amplía | L, se divide |
| **X3. Conocimiento** (L2 + L7) | Fichas en todos los anclajes, guía de naturaleza por estaciones, "¿Qué estoy viendo?", narración con subtítulos en es, va y en | Depende de los datos validados (consulta al parque) y de la base X0 | L, se divide |
| **X4. Memoria** | 1956 ↔ hoy primero en el mapa y luego en el relieve, refotografía, capa de la Pobla | Depende de las imágenes históricas (aprobación de descarga) y de E6 | M |
| **X5. Modos** | Visita guiada, escuelas (misiones y guía docente), preparar la visita, kiosco, foto y postal, guía en texto, PWA sin conexión | Junta las capas anteriores en recorridos para cada público | L, se divide |

Común a todas las fases:
- la accesibilidad de cada pieza en la misma tarea;
- la fila de presupuesto y la prueba e2e de cada sistema;
- la prueba de los cinco vecinos (B12) al terminar X1 y X3;
- la medición en un móvil real (A7) antes de X2.

## 7. Decisiones

**Tomadas por el responsable técnico** (el encargo dejaba esto "a mi juicio"; se pueden revisar):
1. La interfaz es mínima y flotante, con todo visible y táctil, sin atajos (§3.2, §3.3 y §4.1). La dirección la dio el usuario el 12/10/2026.
2. El viaje rápido salta a las paradas del recorrido. El paso caminando no se acelera, y ir más despacio está permitido.
3. Por defecto se ve la hora real de Calp. Cualquier otra se rotula como "hora elegida".
4. Toda cifra lleva su fuente, y lo simulado se rotula.
5. La interfaz va en DOM y SVG.
6. El tiempo de hoy llega como `weather.json` en el mismo dominio, publicado por una tarea programada, para que el navegador no llame a terceros.
7. La narración empieza en texto y la voz grabada llega después.
8. El PDF del cuaderno usa la impresión del navegador.
9. Una reconstrucción de la Pobla solo se muestra si está publicada.
10. Las especies introducidas aparecen marcadas como tales.

**Las que necesitan al usuario o al comprador:**
1. **Publicación:** el alojamiento público de la web y la tarea programada que actualiza `weather.json`.
2. **Open-Meteo:** su uso gratuito es no comercial. Hay que confirmarlo con ellos, o contratar su plan, si la licencia se vende al Ajuntament.
3. **Voces:** quién graba la narración en es, va y en.
4. **Idiomas extra** (fr, de, nl): ahora o a petición del comprador.
5. **Permisos de imágenes:** fotos antiguas (Arxiu Municipal de Calp, Fotoclub Ifach, ICGC) y fotos de flora y fauna de observadores concretos. Las pide una persona, no el equipo.
6. **Descargas:** la lista única del §9.

## 8. Cómo sabremos que está a la altura

| Para quién | Criterio observable |
|---|---|
| Quien no puede subir | Llega a la cima con dos interacciones como máximo desde que carga, sin mareo con las opciones de comodidad, y entiende dónde está en todo momento (mapa y narración) |
| Escolares y docentes | Un docente da una sesión de 45 minutos con la guía, sin conexión si hace falta (PWA). Cada respuesta de una misión lleva a un hecho con su fuente |
| Vecino o vecina | En la prueba de los cinco vecinos reconoce su Penyal (luz, vistas, antes y ahora) sin ayuda |
| Visitante | Encuentra el tiempo del recorrido, la dificultad, las normas y el enlace de reserva en menos de 30 segundos |
| Todos | Cualquier cifra o afirmación lleva a su fuente con un toque |
| Accesibilidad | WCAG 2.1 AA: axe sin errores críticos, prueba manual con lector de pantalla, teclado completo y guía en texto |
| Rendimiento | p95 ≤ 33,3 ms en el móvil de referencia, con cada sistema dentro de su fila de presupuesto |
| Confianza | Ningún dato inventado (revisión de fuentes), ninguna ubicación de *Silene* y ninguna llamada a terceros sin avisar |

## 9. Descargas que necesita el trabajo de 003 y 004

Lista única de las cinco investigaciones (`docs/research/004-*`, `docs/research/005-*`). Tamaños medidos por los agentes salvo donde se indica.

| Grupo | Qué | Licencia | Tamaño |
|---|---|---|---|
| A. Texturas del acceso (E1.2, E3) | `stone_tiles_02` (firme), `patio_tiles` (suelo del pórtico) y `gravel_floor_04`, a 1k | CC0, Poly Haven | 6,0 MB |
| B. Cielo y memoria (X2, X4) | Ortofotos del ICV de 1945, 1956–57, 1977 y 1989 (recorte de 1,5 × 1,5 km), catálogo BSC5, panorama de la Vía Láctea (ESO) y textura de la luna 2k (NASA) | CC BY 4.0 (ICV, ESO). BSC5 sin licencia declarada (catálogo de hechos de 1991). NASA: política general | 10,1 MB |
| C. Sendero alto | Reseña del vértice IGN 84878 (PDF), ficha JSON del IGN y PRUG del DOGV (PDF) | CC BY 4.0 (IGN), documento oficial | 1,9 MB |
| D. Pobla y puerto (E5, E6) | 6 PDF del MARQ (plano de 2023 y memorias) y 2 PDF de licencia del Catastro | Copyright: solo referencia | 15,3 MB |
| **Necesario** | | | **≈ 33 MB** |
| Opcional | Textura `asphalt_04` (E5) | CC0 | 2,4 MB |
| Opcional | GML de plantas del Catastro (E5); se queda en `data/raw/`, nunca en el repo | Licencia del Catastro, restrictiva | 3–5 MB (estimado) |
| Opcional | Fotos de referencia (centre, sendero alto, Pobla y puerto), solo para mirar y medir | CC BY 3.0 y CC BY-SA | ~20 MB a 1.600 px |

Nuevas dependencias de código: `suncalc@2.1.1` (BSD-2-Clause, 8 KB). `astronomy-engine@2.1.19` (MIT, 47 KB) solo si llegan los planetas.

# 003 — Entorno construido y vegetación: propuesta

- Estado: **propuesta para aprobar**, 11/10/2026.
- Investigación en la que se basa:
  - `docs/research/003-inventario-datos-propios.md`: nuestros datos (OSM, CV05, LiDAR, ortofoto);
  - `docs/research/003-entorno-construido.md`: fuentes oficiales, "el museo", puntos de interés y preguntas;
  - `docs/research/003-construccion-assets.md`: cómo construir los modelos y los materiales CC0 candidatos.
- Encaje con lo aprobado: concreta los carriles **L3 (vegetación)** y **L5 (estructuras)** de la fase B (`docs/specs/002-fase-b-paralelizacion.md`). Se implementa sobre B0, con su registro de sistemas, presupuesto y niveles de calidad (ADR 0010).
- Regla: nada se inventa. Todo lo que se modela sale de un dato medido (OSM, CV05, LiDAR, ortofoto) o de una foto de referencia, y la aproximación se marca en `CREDITS.md`.

## 1. Lo que hay (resumen)

| Elemento | Qué sabemos | Qué falta |
|---|---|---|
| "El museo" | La GVA habla de **dos equipamientos** al inicio: el Centro de Información y el Centro de Visitantes. En OSM son dos edificios: "Centro de Interpretación" (651 m², `tourism=museum`, gratuito) y otro de 483 m². Alturas LiDAR: hasta 7,5 m y 6 m. Cubiertas planas ocres con terrazas y placas solares | Qué es cada uno, la exposición interior, las fachadas. En el casco urbano hay otro candidato, el Museu d'Història de Calp |
| Caminos | El tramo piloto es **empedrado**. Las escaleras son de adoquín: 30 peldaños con barandilla y 10 peldaños con barandilla. El asfalto solo está en la avinguda del Port, a unos 150 m | Ancho y aspecto del empedrado; medidas de escalones y barandillas |
| Equipamiento | Torniquete, aseos accesibles, dos fuentes y aparcamiento para personas con discapacidad (592 m²) | Su forma; dónde está el control de reservas |
| Árboles | **186 copas medidas**, de 3 m o más, junto a los primeros 421 m. Mediana 6 m, máximo 10,8 m. Probablemente pino carrasco | Confirmar especies y cambios desde 2016 con la ortofoto de 2024 y fotos |
| Matorral | 27 % de cobertura de más de 0,5 m. Paleta de especies con datos de iNaturalist | — |
| Pobla d'Ifac | Cronología y tamaño con fuente | Un plano: el polígono de OSM es parcial y el MARQ no respondió |
| Acceso rodado y puerto | Avenidas asfaltadas, aparcamiento público junto al Club Náutico, marina, bloques de 4 a 15 plantas, todo con huella y altura medidas | Fachadas |

## 2. Cómo se construye: un método para todo

1. **Pasos deterministas del pipeline:**
   - `penyal vegetation` y `penyal structures`;
   - un núcleo puro en Python que se prueba sin Blender, y una exportación con `bpy` 5.2.2;
   - entradas en `data/catalog.toml` con su sha256;
   - un manifiesto de procedencia por salida, comprobado por `penyal verify-generated`;
   - métricas de referencia: triángulos, llamadas de dibujo, caja envolvente y hash.

   Es el mismo patrón que el terreno.
2. **Caminos dentro del material del terreno:** una máscara por tipo de firme (empedrado, compactado, adoquín, asfalto) sale de las líneas de OSM.
   - No añade llamadas de dibujo.
   - No hay parpadeo de superficies superpuestas.
   - Solo los escalones y los bordillos son mallas.
3. **Kit modular a escala real** (1 unidad = 1 m) para escalones, barandillas, muros, bancos, paneles, fuentes y torniquete:
   - se generan a lo largo de las líneas de OSM;
   - el número de peldaños sale de `step_count`;
   - las medidas de peldaño y barandilla salen de las fotos y, mientras no las haya, se marcan como aproximación.
4. **Edificios desde datos:**
   - huella de OSM, contrastada con la CV05;
   - altura y forma de la cubierta desde los puntos LiDAR;
   - color de cubierta desde la ortofoto;
   - fachada desde las fotos de referencia;
   - un nivel de detalle cercano, otro lejano y un volumen de colisión aparte.
5. **Árboles en su sitio:** cada una de las 186 copas medidas se convierte en una instancia en su posición y con su altura.
   - Pino procedural con las texturas CC0 de `pine_tree_01`, ya descargadas.
   - La semilla solo varía la forma, nunca la posición.
   - El matorral se reparte según la densidad medida de vegetación baja y media.
6. **Materiales CC0** (Poly Haven y ambientCG, licencias verificadas). Se eligen comparando con fotos reales; ninguno está elegido todavía.
7. **Presupuesto:** el de B0 para el nivel `medium`.
   - Vegetación: 40 llamadas de dibujo y 250.000 triángulos.
   - Estructuras: 15 llamadas y 60.000 triángulos.

## 3. Orden propuesto (poco a poco, cada paso visible y verificado)

| Paso | Qué | Carril | Por qué en este orden | Necesita |
|---|---|---|---|---|
| E1 | **Caminos en el terreno**: máscara de firmes con empedrado, compactado y adoquín | L1/L5 | Es el mayor cambio visual con coste cero y no depende de fotos de fachadas | Elegir el empedrado con una foto del sendero; una descarga CC0 pequeña (estimada en 2–3 MB en 1k, por confirmar con la API) |
| E2 | **Árboles reales**: 186 pinos en su posición y con su altura, más el matorral | L3 | Ya están medidos y descargados (fase 4 del catálogo) | Cotejo con la ortofoto de 2024 |
| E3 | **Los dos edificios del centro**: volumen, cubiertas planas, materiales y colisión | L5 | Es el primer punto de interés y la primera vista del visitante | Fotos de fachada; tu confirmación de "el museo" |
| E4 | **Kit del acceso**: escaleras con barandilla, torniquete, fuentes, paneles y bancos | L5 | Completa el tramo piloto | Fotos o medidas de peldaños y barandillas |
| E5 | **Acceso rodado y puerto**, a baja resolución: asfalto, aparcamiento, Club Náutico y bloques como volúmenes | L5 | Es el telón de fondo desde el sendero | Tu decisión de alcance (pregunta 2) |
| E6 | **Pobla d'Ifac**: muros y torres | L5 | Hace falta un plano | Plano del MARQ o del parque |

Cada paso termina con:
- capturas antes y después desde los puntos fijos;
- la prueba de presupuesto por sistema;
- `verify-generated` saliendo con 0;
- la revisión de código.

## 4. Puntos de interés

La propuesta completa está en `003-entorno-construido.md` §4. Los primeros, por tramo:
- **Acceso:**
  - Centre d'Informació i de Visitants, que es la ficha piloto, variante B;
  - aparcamiento, torniquete, fuentes y aseos, como información práctica que siempre remite a la web oficial.
- **Tramo piloto:**
  - Mirador de Ponent, con la Pobla de fondo; es la variante A y depende de que el parque confirme su posición;
  - restos ibéricos, pins tombats y área de descanso, que son paradas oficiales sin posición conocida.
- **Más arriba:**
  - túnel de 1918;
  - plataforma de salida, desde donde se ve Ibiza en días muy claros;
  - Mirador del Botànic Cavanilles;
  - bifurcación con las gaviotas;
  - Mirador de Carabiners;
  - vértice de la cima.
- **Temas sin posición:**
  - *Silene hifacensis*, sin ninguna ubicación;
  - flora rupícola, geología (con sus dos versiones) y halcón peregrino.

## 5. Decisiones que necesito

1. **"El museo":**
   - ¿te refieres a los edificios del Centro de Información y de Visitantes al inicio del sendero, que es lo que proponemos modelar en E3?
   - ¿O al Museu d'Història de Calp, en el casco urbano y fuera del recorrido?
2. **Alcance del entorno:** ¿hasta dónde modelamos?
   - (a) solo el parque, desde el centro;
   - (b) también el acceso desde la rotonda del puerto, a baja resolución (E5);
   - (c) además la fachada urbana de fondo como volúmenes simples.
3. **Fotos:** como vecino de Calp, ¿puedes hacer las fotos de referencia (`docs/specs/002/protocolo-fotos.md`) o encargarlas?
   - Desbloquean la elección de materiales (E1), las fachadas (E3) y las medidas del kit (E4).
   - Si ya tienes fotos del acceso o del centro, también sirven como referencia.
4. **Orden:** ¿apruebas E1 → E6 tal cual, empezando por E1 y E2, que no dependen de fachadas, en cuanto termine B0?

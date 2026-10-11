# 003 — Inventario del entorno construido a partir de nuestros datos

- Fecha: 11/10/2026. Autor: responsable técnico.
- Objetivo: saber qué hay en el acceso al parque y en el tramo piloto antes de modelar nada, usando solo datos que ya tenemos descargados y bloqueados por sha256.
- Datos usados (todos en `data/manifest.lock.json`):
  - extracto de OpenStreetMap `osm-penyal` (ODbL);
  - CV05 1:5000 del ICV, capa de edificaciones (CC BY 4.0);
  - LiDAR 2016 del ICV, tesela 766-4282 (CC BY 4.0);
  - ortofoto 2024 de 25 cm del ICV, hoja 0848_7-2 (CC BY 4.0);
  - el MDT 2016 ya cargado por el pipeline.
- Complementa a dos documentos de investigación de los agentes:
  - `003-entorno-construido.md`: fuentes oficiales, fotos y "el museo";
  - `003-construccion-assets.md`: cómo construir los modelos.
- Método: análisis de solo lectura con scripts de un solo uso (OSM con Node; LiDAR, MDT y ortofoto con el entorno `uv` del pipeline). **No son todavía un paso del pipeline**: cuando se decida qué modelar, se convierten en pasos deterministas con su prueba y su manifiesto de procedencia, como el terreno.

## 1. "El museo" según los datos

| Dato | Valor | Fuente |
|---|---|---|
| Nombre | **Centro de Interpretación Parque Natural del Penyal d'Ifac** | OSM `way/26330271` (`tourism=museum`, `fee=no`) |
| Huella | 651 m² en OSM; 623 m² en la CV05 (`CON04`) | OSM, CV05 |
| Altura sobre el terreno que lo rodea | mediana 4,9 m; percentil 95, 6,9 m; máximo 7,5 m | LiDAR 2016, puntos de clase 6 (edificio) dentro de la huella, frente a la mediana del suelo (clase 2) en un anillo de 1–6 m alrededor |
| Aspecto en planta | Cubiertas planas en tonos ocre y terracota, con terrazas. Hay un sector con placas solares y un patio interior con dos árboles | Ortofoto 2024 (`003-capturas/orto2024-centro-150m.jpg`) |
| Edificio contiguo, al este | 483 m² en OSM y 394 m² en la CV05 (`CON04`). Altura mediana 3,8 m y máxima 6,0 m. Cubierta plana de color arena | OSM `way/26330272`, CV05, LiDAR, ortofoto |

- **Sin verificar:** si estos dos edificios son las "dos casas réplica inauguradas en 1992" de la nota del registro, que no tiene fuente.
- **Sin verificar:** si son lo que el usuario llama "el museo". Lo aclara el documento de fuentes oficiales y, al final, el propio usuario.
- **Medida aproximada:** el suelo alrededor está en pendiente. La "altura" es una diferencia frente a la mediana del suelo cercano, no frente a la cota de la puerta.

## 2. Elementos construidos alrededor del centro (≤ 350 m), según OSM

| Elemento | OSM | Datos | Distancia al centro |
|---|---|---|---|
| Fuente de agua potable (2) | `node/8032598829`, `node/992845708` | `amenity=drinking_water` | 12 y 30 m |
| Escalera de 30 peldaños | `way/26330269` | adoquín (`paving_stones`), con barandilla; 17 m | 21 m |
| Torniquete | `node/8032598828` | `barrier=turnstile` | 24 m |
| Aseos | `node/1795591677` | gratuitos, accesibles en silla de ruedas | 26 m |
| Escalera de 10 peldaños | `way/862108205` | adoquín (`sett`), con barandilla; 11 m | 49 m |
| Aparcamiento para personas con discapacidad | `way/862108210` | en superficie, 592 m² | 67 m |
| Mirador sin nombre | `node/1795591637` | posible Mirador de Ponent, sin confirmar (`consulta-parque.md`, pregunta 1) | 76 m |
| Yacimiento de la Pobla d'Ifac | `way/1159140951` | `historic=archaeological_site`; el polígono cubre 2.326 m², solo una parte de los más de 70.000 m² que da la Universitat d'Alacant | 110 m |
| Edificio sin nombre | `way/261433047` | 547 m²; LiDAR: mediana 4,9 m y máximo 10 m, con vegetación dentro de la huella | 136 m |
| Ruina | `way/665280059` | `historic=ruins`, 16 m² | 241 m |
| Escalera de 6 peldaños de roca | `way/862108208` | con barandilla, junto a la boca oeste del túnel | 269 m |
| Panel "Peñón de Ifac: Ruta ornitológica" | `node/9562356617` | `information=board`, temática de fauna | lejos del centro, en la zona sur |

Hay 7 miradores (`tourism=viewpoint`) en todo el extracto. Solo uno tiene nombre: el Mirador de Carabiners.

**Al pie del Peñón, fuera del parque pero visibles desde el sendero:**
- el Real Club Náutico: 946 m², mediana de 6,9 m según el LiDAR;
- un centro de buceo: 1.559 m², 7,0 m;
- una torre (`man_made=tower`, 21 m²) junto al club;
- los pantalanes de la marina;
- bloques de apartamentos de 4 a 15 plantas, según `building:levels` de OSM;
- un aparcamiento público de 402 m² junto al club, además de muchos privados.

## 3. Caminos y firmes

| Tramo | OSM | Firme | Longitud |
|---|---|---|---|
| Sendero principal hasta el túnel | `way/26330273` | **empedrado** (`unhewn_cobblestone`), `sac_scale=hiking` | 725 m |
| Accesos al centro | `way/26330270`, `way/862108204`, `way/862108209` | empedrado | 54, 68 y 43 m |
| Pista de servicio, sin vehículos a motor | `way/261433046` | empedrado | 150 m |
| Pista de servicio, sin vehículos a motor | `way/37656546` | compactado | 314 m |
| Senderos secundarios | varios `highway=path` y `highway=footway` | compactado, tierra o grava | 30–400 m |
| Avinguda del Port | `way/85587115` | **asfalto** | 318 m; empieza a ~150 m del centro |
| Avinguda de l'Illa de Formentera | `way/37656545` | asfalto | 123 m |
| Passeig del Príncep d'Astúries | `way/85587116` | adoquín | 665 m |
| Túnel | `way/26330275` | roca, `sac_scale=demanding_mountain_hiking` | 49 m |

**Consecuencia para el modelado:**
- En el tramo piloto **no hay asfalto**: el visitante pisa empedrado y escalones de adoquín.
- El asfalto solo aparece en el acceso rodado desde el puerto, si el tramo piloto llega a incluirlo.

## 4. Vegetación medida en el tramo piloto

Zona: franja de 40 m a cada lado de los primeros 421 m del sendero, 27.325 m². Datos del LiDAR 2016, con las clases 3, 4 y 5 (vegetación baja, media y alta). Altura de copas a 1 m de resolución, sobre el MDT.

| Medida | Valor |
|---|---|
| Copas de 3 m o más (máximos locales en ventana de 5 m) | **186** |
| Altura de copa | mediana 6,0 m; percentil 90, 8,0 m; máximo 10,8 m |
| Por altura | 3–5 m: 58; 5–8 m: 108; 8–12 m: 20; más de 12 m: 0 |
| Cobertura de la franja | más de 0,5 m: 27 %; más de 2 m: 16 %; más de 5 m: 6 % |

**Lectura y límites:**
- Las especies salen de `docs/specs/002/vegetacion-especies.md`.
- **Sin verificar:** que las copas de 5–10 m sean sobre todo pino carrasco. Encaja con la ortofoto y con iNaturalist, pero falta confirmarlo con las fotos de referencia.
- El LiDAR es de 2016, y la ortofoto de 2024 puede mostrar cambios. Antes de colocar árboles en sus posiciones medidas, hay que cotejarlas con la ortofoto.

## 5. Qué permite esto, y qué falta

**Permite:**
- **Edificios del centro:** extruir la huella real de OSM, contrastada con la CV05, a la altura medida por el LiDAR. La forma de la cubierta sale de la nube de puntos y su color, de la ortofoto. Así no se inventa geometría.
- **Árboles:** colocar las 186 copas en su posición y con su altura medidas, sin repartirlas al azar. Es determinista, con semilla solo para la variación de forma.
- **Firmes:** usar el tipo de cada camino según OSM: empedrado, adoquín, compactado o asfalto.

**Falta:**
- **El diccionario de códigos de la CV05** (`CON01`…`CON15`). `CON04` coincide con los dos edificios del centro, pero no hemos leído la especificación.
- **La altura y el ancho reales** de escalones, barandillas y muros. OSM da el número de peldaños, pero no sus medidas.
- **El aspecto de las fachadas,** que la ortofoto no muestra. Hace falta mirar fotos de referencia o las que se hagan con el protocolo de fotos.
- **El plano de la Pobla d'Ifac:** el polígono de OSM es parcial.

## Atribución de las capturas

`003-capturas/orto2024-centro-150m.jpg` (150 × 150 m) y `003-capturas/orto2024-acceso-320m.jpg` (320 × 320 m):
- recortes de la ortofoto 2024, 25 cm, hoja 0848_7-2;
- © Institut Cartogràfic Valencià, Generalitat, CC BY 4.0;
- recortadas y convertidas a JPEG.

# Protocolo de fotos de referencia (tramo piloto)

- Estado: **borrador**, arranque anticipado del carril L8. Va dirigido a la persona del equipo que hará las fotos.
- Para qué sirven las fotos:
  1. **Comparación forzada**: se pone la foto junto a la vista de la app desde el mismo punto, a la misma hora y con el mismo encuadre. Es el criterio de salida de la fase B: "comparación fotográfica en 2–3 puntos".
  2. **Registro de cámara**: `photomatch.py` (L8) estima la posición y la orientación de la foto. Parte del GPS y de la focal que guarda la foto, y las ajusta con la silueta del terreno contra el cielo.
  3. **Referencia de luz y color** para elegir el mapeo de tonos AgX o ACES (carril L1).
- Las fotos **no se usan como texturas** salvo que se acuerde por escrito.

## Puntos

Coordenadas en WGS84, sacadas del sendero que genera el proyecto (`trail.json`, de OpenStreetMap) y del modelo del terreno del ICV. Los rumbos se miden desde el norte verdadero. La brújula del móvil vale con un margen de ±5°.

| Punto | Dónde | Coordenadas | Altitud | Fotos (rumbo) |
|---|---|---|---|---|
| **F1** (obligatorio) | Explanada del centro de visitantes | 38,637616 N · 0,073737 E | 70 m | a) Cima, 168°, a 302 m. b) Pobla, 3°, a 111 m. c) Panorámica hacia el puerto y Calp, en la dirección que prefieras |
| **F2** (opcional) | Torniquete | 38,637410 N · 0,073822 E | 75 m | a) Cima, 168°. b) Sendero hacia arriba |
| **F3** (obligatorio) | Mirador sin nombre de OpenStreetMap, nodo 1795591637, a unos 150 m del torniquete. Puede ser el Mirador de Ponent, sin confirmar; ver la pregunta 1 de `consulta-parque.md` | 38,636970 N · 0,073440 E | 92 m | a) Pobla, 10°, a 186 m. b) Cima, 158°, a 240 m. c) Bahía y Calp, hacia el oeste y el noroeste |
| **F4** (obligatorio) | Final del tramo piloto, ≈ km 0,42 de la ruta, 350 m después del torniquete | 38,636353 N · 0,074072 E | 119 m | a) Cima, 168°, a 158 m. b) Hacia la boca oeste del túnel, 119°, a 159 m. c) Vista hacia abajo: Calp y el puerto |
| **F5** (opcional, el mejor para la silueta) | Desde fuera del parque, con el Penyal recortado contra el cielo; por ejemplo, el dique del puerto o la playa | La posición la anota el GPS de la foto | — | a) El Penyal entero, con cielo por encima de la cima |

- **Cómo encontrar cada punto**: abre las coordenadas en el mapa del móvil. Si el punto no coincide con un sitio razonable del sendero, haz la foto en el sitio más cercano **dentro del sendero** y anótalo.
- **Normas del parque**: no salgas del sendero por ninguna foto. Están prohibidos los drones. Antes de ir, comprueba en la web oficial si el tramo exige reserva y en qué horario está abierto.

## Cuándo

- **Sesión 1, sol alto**: entre las 12:30 y las 15:00, hora local. Es la referencia del ajuste de día.
- **Sesión 2, sol bajo**: la última hora antes de la puesta de sol. Es la referencia del atardecer.
  - Si el sendero ya está cerrado o el centro también, haz F1 desde la explanada y F5 desde fuera.
- **Tiempo**: mejor un día despejado. Si hay calima o nubes, haz las fotos igualmente y anótalo, porque también sirven.
- La app calcula la posición del sol con la hora de la foto. No hace falta coincidir con una hora exacta, pero **la hora del móvil debe ser la automática**.

## Cómo

- **Antes de salir**:
  - batería cargada;
  - la localización activada para la cámara (en iPhone: Ajustes → Privacidad → Localización → Cámara);
  - la lente limpia.
- **Cámara**:
  - usa la lente principal ("1×"), sin zoom y sin el gran angular "0,5×";
  - nada de modo retrato, filtros, modo noche ni panorámica;
  - el HDR automático puede quedarse como venga;
  - si tu móvil permite RAW (ProRAW o DNG), haz **además** una foto RAW en F1 y F4, para la referencia de color.
- **Encuadre**:
  - móvil en horizontal, nivelado (activa la cuadrícula) y a la altura de los ojos;
  - el horizonte recto;
  - toca la pantalla sobre el Penyal para enfocar.
  - En cada dirección haz **dos fotos seguidas** sin moverte.
- **Para situar el punto**: haz también una foto del suelo, con los pies, que muestre dónde estabas.
- **Notas** (vale una nota de voz o de texto): punto, hora, tiempo que hace y cualquier cosa rara. Por ejemplo: "F3 desplazado 5 m al sur porque había un grupo".
- **Personas**: espera a que no haya nadie en el encuadre. Si alguien sale reconocible, esa foto no se publica.

## Cómo enviarlas

- **Envía los originales**: AirDrop, cable, la carpeta compartida del equipo o Google Fotos en "calidad original".
- **No las envíes por WhatsApp ni por Telegram**: quitan los datos de la foto (GPS, hora, focal) y entonces no sirven para el registro.
- **No las renombres ni las edites.**
- **Licencia**: con el envío, quien hace las fotos acepta que el proyecto las use con licencia **CC BY 4.0**, con su nombre en los créditos, o **CC0** si lo prefiere.
  - Hay que indicarlo por escrito, en una línea del mensaje de envío.
  - CC BY-SA no vale (ADR 0007).

## Qué hace el proyecto con ellas

1. Las guarda fuera de git, en `data/manual/fotos-referencia/<fecha>/`, con un `README` que recoge la licencia, el autor y las notas. Solo se suben al repositorio las comparaciones que se publiquen.
2. `photomatch.py`:
   - lee el GPS, la hora y la focal equivalente de cada foto;
   - renderiza la silueta del terreno desde esa posición;
   - ajusta posición y orientación hasta que las siluetas coinciden;
   - guarda el error final en píxeles.
3. La app abre la misma vista con `?start=` y la atmósfera a esa hora. Se hace una captura del mismo tamaño y se monta una comparación lado a lado en `docs/audits/`.
4. **Criterio**:
   - la silueta coincide dentro del error que fije L8 al construir la herramienta, que se documentará con el primer resultado;
   - el revisor no señala ninguna diferencia grave de forma, luz o color sin explicar.
   - Las diferencias que sí se encuentren se apuntan como tareas.

# Consulta al Parque Natural del Penyal d'Ifac — borrador

- Estado: **borrador para que lo revise y lo envíe el responsable del proyecto**. No se ha enviado nada.
- Destino: `ifac_cma@gva.es`, la dirección de contacto que el proyecto ya tiene registrada (plan 002, tareas humanas).
- Desbloquea:
  - la ficha piloto, que depende de dónde está el Mirador de Ponent (B9);
  - la colocación de las paradas 2 a 5 (fase C);
  - la formulación sobre menores (fichas del túnel y de la cima);
  - las 11 discrepancias y los 4 datos sin verificar de `content/facts.json`;
  - las medidas del túnel (Q6 de la spec 001).
- Origen de cada pregunta: el identificador entre corchetes es el dato de `content/facts.json`. Sus fuentes están en `content/sources.json`.

## Correo

**Asunto:** Recorrido virtual gratuito de la Ruta Roja del Penyal d'Ifac — consulta sobre algunos datos

Bon dia / Buenos días:

Soy vecino de Calp y estoy preparando, sin ánimo de lucro, un recorrido virtual en 3D de la Ruta Roja del Penyal d'Ifac. Se podrá ver gratis en el navegador, también en el móvil, y es un regalo para el pueblo. Lo construyo con datos públicos:
- el modelo del terreno y el LiDAR del Institut Cartogràfic Valencià;
- OpenStreetMap;
- la información de la web del parque, que cito en cada ficha.

La experiencia dirá claramente que **no es una web oficial del parque**. Para la información práctica (reservas, horarios, normas) remitirá siempre a la web oficial.

Al contrastar las fuentes he encontrado algunos datos en los que la web del parque, el Ajuntament y otras publicaciones no coinciden. También hay otros que no he podido confirmar. Mientras no se aclaren, la experiencia muestra todas las versiones con su fuente y no elige ninguna. Os adjunto las preguntas por orden de prioridad. Cualquier respuesta, aunque sea parcial, me ayuda mucho.

Además:
- no mostraré la ubicación de la *Silene hifacensis* ni de otras especies sensibles;
- si os parece bien, os enseñaré los textos antes de publicarlos.

Moltes gràcies / Muchas gracias,

lr0y

## Anexo — preguntas

### A. Para el primer tramo (lo más urgente)

1. **Mirador de Ponent** [`trail-stops`, `pobla-viewpoint`]. La web del parque lo cita como la primera parada de la Ruta Roja y dice que desde él se ve la muralla de la Pobla.
   - En OpenStreetMap hay un mirador sin nombre en **38,63697 N, 0,07344 E**, a unos 92 m de altitud y unos 150 m después del torniquete.
   - ¿Es el Mirador de Ponent? Si no lo es, ¿dónde está?
2. **Paradas 2 a 5 antes del túnel** [`trail-stops`]: restos ibéricos, pins tombats, área de descanso y Mirador del Botànic Cavanilles.
   - ¿Podéis indicarnos dónde está cada una? Basta con un mapa marcado o unas coordenadas aproximadas.
3. **Reserva** [`access-booking`]. La guía y la web dicen que la reserva es obligatoria "para subir a la cima".
   - ¿Hace falta también para el tramo de antes del túnel?
   - ¿La reserva es gratuita?
4. **Menores después del túnel** [`access-minors-past-tunnel`]. Hemos encontrado tres formulaciones oficiales:
   - "No se permite continuar a menores de 18 años" (Recomendaciones para la visita);
   - "No se recomienda" (portada del parque y guía);
   - "De 16 a 18 años, acompañados de un adulto" (descripción de la Ruta Roja).
   ¿Cuál es la norma vigente? Hasta saberlo, la experiencia no da ninguna y remite a la web oficial.

### B. Datos en los que las fuentes no coinciden

En cada caso basta con saber qué cifra o qué redacción prefiere el parque, o si hay una explicación (por ejemplo, ida o ida y vuelta).

5. **Longitud del túnel** [`tunnel-length`]:
   - unos 50 m (folleto y descripción de la Ruta Roja);
   - unos 30 m (web municipal);
   - 49,2 m (medido en OpenStreetMap).
6. **Longitud y tiempo de la ruta** [`trail-length`, `trail-time`]:
   - longitud: unos 2 km ida y vuelta (parque), 0,83 km y 173 m de desnivel (Mancomunitat de la Marina Alta), 1,68 km de ida medidos en planta (OpenStreetMap);
   - tiempo: 1 h 30 de subida (parque), 1 h (Mancomunitat), 2 h 30 (web municipal).
7. **Altitud de la cima** [`summit-altitude`]:
   - 332 m (parque y web municipal);
   - 325,8 m (cartografía 1:5000 del ICV);
   - 328,07 m (LiDAR 2016 del ICV).
   La experiencia mantiene el terreno medido y explica la diferencia. ¿Hay una explicación oficial, por ejemplo la referencia de la cifra de 332 m?
8. **Número de especies** [`park-species-counts`]:
   - más de 60 aves y más de 400 plantas (parque);
   - unas 80 aves y unas 300 plantas (web municipal).
9. **Origen geológico** [`park-geology`]:
   - calizas del Eoceno sobre margas y calcarenitas del Mioceno, antigua isla unida por un tómbolo (página de geología del parque);
   - desprendimiento de la Serra d'Oltà (web municipal).
10. **Categoría de protección de la *Silene hifacensis*** [`silene-category`]:
    - "Vulnerable" en el catálogo estatal (Orden TED/452/2025);
    - "En peligro de extinción" en el catálogo valenciano.
    ¿Se ha hecho ya el cambio de categoría autonómica que la GVA indica como pendiente?
11. **Pobla d'Ifac** [`pobla-abandonment`, `pobla-church-date`, `pobla-bic`]:
    - abandono: "después de 1359" (parque) o "hacia 1400" (Universitat d'Alacant);
    - iglesia: "ordenada en 1344" (parque) o "construida entre 1320 y 1340" (MARQ, 2008);
    - Bien de Interés Cultural: "declaración incoada" (parque) o "declarada en 2011" (MARQ, 2017); no hemos encontrado el decreto.
    Si estas preguntas corresponden al MARQ, ¿a quién podemos dirigirnos?

### C. Datos que no hemos podido confirmar

12. **Desde cuándo se exige reserva** [`access-booking-start`]. Solo hemos encontrado una nota municipal, según la cual se acordó en la Junta Rectora hacia 2020.
13. **Visitas a la Pobla** [`pobla-visits`]. ¿Se puede visitar hoy? ¿Sigue prevista la musealización?
14. **Aves nidificantes** [`bird-pair-counts`]. ¿Hay cifras publicadas de parejas de gaviota patiamarilla y de halcón peregrino?
15. **Halcón de Eleonora** [`eleonora-falcon`]. Lo menciona la web municipal, pero no aparece entre las especies del parque. ¿Se observa en el Penyal?

### D. Túnel y especies sensibles

16. **Medidas del túnel** (Q6 de la spec 001). ¿Existen planos o medidas de la anchura, la altura y los escalones de entrada y salida? Hoy la sección del túnel es provisional.
17. **Especies sensibles**. ¿Tenéis alguna pauta sobre cómo presentar la *Silene hifacensis* y otras especies protegidas? Nuestra regla es mostrarlas solo en las fichas, nunca en su lugar real.

### E. Añadidas el 12/10/2026 (investigación en línea, `docs/research/004-*`)

18. **Ventana de reserva** [`access-booking`]. Una nota municipal (21/07/2026) dice "hasta 10 días" de antelación y una fuente de prensa (09/10/2026) dice "al menos 4 días". ¿Cuál es la vigente?
19. **Camino del Mirador de Carabiners**. El PRUG (art. 30–32) lo restringe de abril a junio. ¿Se aplica hoy esa restricción?
20. **Obras de 2016 en el sendero**. ¿Pueden facilitarnos la memoria o los planos de las obras de Vaersa (muros de mampostería, cadenas, cuerdas) y la anchura prevista del sendero?
21. **Pasamanos del túnel**. ¿Hoy es cuerda o cadena, y a qué altura va?
22. **Poste de Carabiners**. ¿Qué es el poste de acero con la parte superior roja del Mirador de Carabiners?
23. **Bordes y mobiliario del primer tramo**. ¿Dónde hay talanqueras de rollizos, muros de piedra seca, bancos, papeleras y paneles entre el aparcamiento y el primer mirador? Solo colocamos lo que podemos situar con una fuente.
24. **Los dos edificios del centro**. ¿Cuál es el Centre d'Informació y cuál el Centre de Visitants? ¿En qué año se construyeron?

## Qué hacemos con cada respuesta

- **Antes de cambiar nada en `content/facts.json`**: hay que decidir cómo citar una respuesta por correo.
  - Hoy `app/src/content/schema.ts` exige una URL `https` en cada fuente, y un correo no la tiene.
  - Propuesta, que se decidirá como enmienda del ADR 0005:
    - un tipo nuevo `official-gva-correspondence`, con fecha, oficina remitente y la pregunta respondida, sin URL pública;
    - el correo se guarda fuera de git, en `data/manual/`, porque contiene nombres de personas.
  - Con esa decisión tomada, una discrepancia pasa a `verified` solo si la respuesta del parque da un único valor. Las demás fuentes se conservan en el registro.
  - Mejor todavía: pedir al parque que publique la corrección en su web y citar esa página.
- **Mirador de Ponent (pregunta 1)**:
  - si se confirma, la ficha piloto es la Pobla (variante A de `ficha-piloto.md`);
  - si no, es el centro de visitantes (variante B).
- **Paradas (pregunta 2)**: pasan a `anchors` del sendero solo con coordenadas dadas por el parque o medidas en la visita.
- **Medidas del túnel (pregunta 16)**: se actualiza `data/curated/tunnel.toml`, con su fuente y una entrada en el ADR 0009 si cambia el suelo.
- **Sin respuesta en tres semanas**: se envía un recordatorio. Mientras tanto, la fase B sigue con la variante B de la ficha.

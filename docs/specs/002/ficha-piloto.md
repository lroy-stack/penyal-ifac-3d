# Ficha piloto (B9) — texto en castellano

- Estado: **borrador del responsable técnico**, listo para traducir al valenciano y al inglés en cuanto se apruebe. Arranque anticipado del carril L7.
- Reglas:
  - el texto corto tiene como máximo 60 palabras;
  - "Ampliar" muestra el resto, con las fuentes y las discrepancias a la vista;
  - cada frase cita entre corchetes el dato de `content/facts.json` que la respalda;
  - no hay ninguna frase sin dato.
- Cuál de las dos variantes se usa depende de la pregunta 1 de `consulta-parque.md`:
  - **variante A, la Pobla d'Ifac**, si el parque confirma que el Mirador de Ponent está dentro del tramo piloto;
  - **variante B, el centro de visitantes**, en caso contrario o mientras no responda.
- Tono: tuteo, frases cortas, sin adjetivos de folleto. La información práctica siempre remite a la web oficial, porque puede cambiar.

## Variante A — La Pobla d'Ifac (desde el Mirador de Ponent)

### Texto corto (56 palabras)

> Desde aquí se ve la muralla de la Pobla d'Ifac [`pobla-viewpoint`]. Es una villa fortificada que Roger de Llúria obtuvo permiso para fundar en 1298 [`pobla-founding`]. Tenía más de 800 m de muralla, 11 torres y 3 puertas [`pobla-size`]. Una flota castellana la destruyó en 1359, durante la Guerra de los Dos Pedros [`pobla-destruction`]. Desde 2005 la excava el MARQ [`pobla-excavation`].

### Ampliar

- **Fundación** [`pobla-founding`]:
  - en 1298 Roger de Llúria obtiene permiso para fundar la villa;
  - tras su muerte, en 1305, la continúa su hija Margarida de Llúria;
  - en 1282 Pere III ya había ordenado fundar una villa, sin éxito.
- **Tamaño** [`pobla-size`]: más de 70.000 m², más de 800 m de muralla, 11 torres y 3 puertas.
- **Excavación** [`pobla-excavation`]: desde 2005 la excava el MARQ, de la Diputación de Alicante, con el parque y el Ajuntament de Calp. La dirige José Luis Menéndez Fueyo.
- **Las fuentes no coinciden.** Se muestran todas las versiones y no se elige ninguna:
  - abandono [`pobla-abandonment`]: "después de 1359" (web del parque) o "hacia 1400" (Universitat d'Alacant);
  - iglesia [`pobla-church-date`]: "ordenada en 1344" (web del parque) o "construida entre 1320 y 1340" (MARQ, 2008);
  - protección como Bien de Interés Cultural [`pobla-bic`]: "declaración incoada" (web del parque) o "declarada en 2011" (MARQ, 2017). No hemos encontrado el decreto.
- **Sin confirmar** [`pobla-visits`]: no sabemos si hoy se puede visitar. Consulta la web oficial del parque.
- **Fuentes**: `gva-villa-ifac`, `gva-proyecto-ifac`, `gva-ruta-roja`, `ua-pobla`, `marq-2008`, `marq-2017`, `marq-2024`. En pantalla aparecen con su título, su enlace y la fecha de consulta.

## Variante B — Centro de visitantes

### Texto corto (53 palabras)

> Estás en el Centro de Visitantes del Parque Natural del Penyal d'Ifac [`centre-name`], declarado parque natural en 1987 [`park-declaration`]. Para subir a la cima hace falta reserva: es personal, una por persona y día, incluidos los niños, y se puede hacer con hasta 10 días de antelación [`access-booking`]. El aforo es de 300 personas al día [`access-capacity`].

### Ampliar

- **El centro** [`centre-name`]:
  - en valenciano se llama Centre d'Informació i de Visitants;
  - el mapa oficial lo rotula «Aula de la Natura»;
  - ocupa dos casas réplica inauguradas en 1992.
- **Horario del centro** [`centre-hours`]:
  - de lunes a viernes, de 8:30 a 14:30;
  - fines de semana y festivos, de 9:00 a 14:00;
  - cerrado el 1 y el 6 de enero y el 24, el 25 y el 31 de diciembre.
- **Horario del sendero** [`trail-hours`]: de la salida a la puesta del sol. Está prohibido el acceso nocturno.
- **Antes de subir** [`access-safety`]:
  - calzado de montaña, nada de sandalias ni tacones;
  - agua, porque solo hay fuentes al inicio;
  - con lluvia o niebla, no sigas después del túnel;
  - emergencias: 112.
- **Normas** [`access-prohibitions`]:
  - perros siempre atados;
  - drones prohibidos;
  - sin bicicletas en la subida;
  - no se puede hacer fuego, fumar, acampar ni salir del sendero.
- **El parque**:
  - 53,3 ha desde la ampliación de 2015 [`park-area`];
  - unos 100.000 visitantes al año [`park-visitors`].
- **Aviso fijo**: "Esta experiencia no es la web oficial del parque. Antes de ir, comprueba reservas, horarios y normas en la web oficial." Debe llevar el enlace a `gva-park-home`.
- **Fuentes**: `gva-centro-visitantes`, `gva-accesibilidad`, `gva-park-home`, `gva-guia`, `gva-reservas`, `gva-recomendaciones`, `gva-folleto`, `gva-presentacion`, `dogv-decreto-1-1987`, `dogv-decreto-40-2015`, `dogv-prug-1993`.

## Para la traducción y la integración

- **Traducción**:
  - los nombres propios se mantienen: Pobla d'Ifac, Penyal d'Ifac, Centre d'Informació i de Visitants, MARQ;
  - en valenciano, el texto lo revisa la persona revisora (tarea humana del plan 002);
  - en inglés no hay revisión externa prevista. Se marca como traducción del equipo.
- **Datos, no copias**: cuando exista el contrato de puntos de interés de B0, la ficha guarda los identificadores de los datos y el texto por idioma. Las cifras no se copian a mano. Una prueba compara las cifras del texto con `content/facts.json` para detectar si se desincronizan.
- **Pendiente de decidir en L7**:
  - si los textos de las discrepancias se muestran siempre o tras un toque en "¿Por qué hay dos fechas?";
  - la propuesta es mostrarlos siempre en "Ampliar", con un estilo propio, sin esconderlos.

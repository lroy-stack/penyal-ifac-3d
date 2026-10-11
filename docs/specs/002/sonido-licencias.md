# L2 Sonido ambiente: licencias y candidatos (investigación previa)

- Fecha: 2026-10-11 · Alcance: tramo piloto (ladera baja del Penyal d'Ifac sobre el puerto de Calp, hasta el km 0,421).
- Estado: solo investigación. No se ha descargado nada ni se ha tocado código. Lo que sigue se apoya en lo leído hoy; lo marcado como NO VERIFICADO no se ha podido abrir.
- Base: `CLAUDE.md` (licencias), ADR 0007, `content/facts.json`, `docs/research/002-verificacion.md` §4 y `docs/specs/002-fase-b-paralelizacion.md` (L2).

## Respuesta corta

1. **Todavía no hay un conjunto completo con licencia limpia.** Hoy solo hay tres piezas verificadas con CC0, CC BY o dominio público: mar contra roca, cigarras (solo en verano) y un paso sobre grava. Faltan tres capas con licencia verificada: colonia de gaviota patiamarilla, viento en pinos y canto de paseriforme.
2. **La propuesta del spec (CC BY-SA "tal cual") choca con `CLAUDE.md` línea 44**: "Licences: CC0 / CC BY assets only". ADR 0007 solo prohíbe BY-SA en texturas, así que la contradicción está entre el `CLAUDE.md` y el spec, no con el ADR. Es una decisión tuya. Todos los candidatos BY-SA que he encontrado vienen de xeno-canto, y su licencia original no he podido comprobarla.
3. **Recomendación para cubrir las capas que faltan:** grabación propia en el parque, con permiso del parque, liberada en CC0. Evita la mezcla de licencias y encaja con la prueba de realismo de §4.
4. **Excluidos:** BBC Sound Effects (licencia no comercial) y Sonniss GDC (no pueden distribuirse los archivos sueltos).

## Correcciones a la lista de aves

- **"Collalba negra" es *Oenanthe leucura* (collalba negra, black wheatear), no *Phoenicurus ochruros* (black redstart, colirrojo tizón).** Lo confirma una búsqueda web, aunque las fuentes no coinciden en la familia (Turdidae frente a Muscicapidae). Conviene corregir la etiqueta en el texto del contenido.
- **Paseriformes de la lista de la GVA:** collalba negra y **curruca rabilarga** (*Sylvia undata*, en `fauna-other`). La curruca no está en tu lista.
- No son paseriformes: gaviota patiamarilla (*Larus michahellis*, capa de gaviotas), halcón peregrino, cormorán moñudo (*Gulosus aristotelis*) y vencejo pálido (*Apus pallidus*).
- El cernícalo también está en la lista de la GVA, pero es rapaz.

## Candidatos evaluados (Wikimedia Commons, consultados 2026-10-11)

Los metadatos de Commons vienen de la página del archivo leída con WebFetch. Frecuencia de muestreo, canales y bitrate original no se publican en esas páginas; se confirmarán con `ffprobe` tras aprobar la descarga.

| Capa | Archivo (URL) | Licencia | Autor | Duración · tamaño · formato | Limpio | Lugar | Veredicto |
|---|---|---|---|---|---|---|---|
| Mar/roca | [Oceanwavescrushing.ogg](https://commons.wikimedia.org/wiki/File:Oceanwavescrushing.ogg) | CC BY 3.0 | Luftrum | 2:00 · 2,85 MB · Ogg Vorbis 190 kbps | Sí; menciona un "very distant vessel" (recortar) | Røsnæs, fiordo de Kalundborg (Dinamarca) | **Candidato A** |
| Mar/roca | [Water on Rocks.ogg](https://commons.wikimedia.org/wiki/File:Water_on_Rocks.ogg) | CC BY 3.0 | Dsw4 | 2:35 · 3,19 MB · Ogg Vorbis 173 kbps | Sí | Lago Ontario (EE. UU.), no mar | Alternativa |
| Mar/roca | [Small sea waves at rocky beach.opus](https://commons.wikimedia.org/wiki/File:Small_sea_waves_at_rocky_beach.opus) | CC BY 3.0 | Mnalis | 0:10 · 18 KB · Opus | Sí | No indicado | Descartado (muy corto) |
| Gaviota | [Yellow-legged Gull - Larus michahellis michahellis.ogg](https://commons.wikimedia.org/wiki/File:Yellow-legged_Gull_-_Larus_michahellis_michahellis.ogg) | **CC BY-SA 4.0** | Cedric Mroczko (origen xeno-canto) | 0:38 · 703 KB · Ogg Vorbis 153 kbps | Sí, un canto suelto, no colonia | No indicado | Único *L. michahellis* de audio que he encontrado; BY-SA |
| Gaviota | [Gull 1.ogg](https://commons.wikimedia.org/wiki/File:Gull_1.ogg) | Dominio público | avphillips | 0:18 · 163 KB | Sí | Long Island (EE. UU.) | Descartado: *Larus argentatus* |
| Viento/pinos | [Wind in Swedish pine forest at 25 mps.ogg](https://commons.wikimedia.org/wiki/File:Wind_in_Swedish_pine_forest_at_25_mps.ogg) | **CC BY-SA 4.0** | W.carter | 1:00 · 1,82 MB · Ogg Vorbis 253 kbps | Sí, solo viento | Suecia, pinar | BY-SA; viento fuerte (25 m/s), usar muy bajo |
| Viento/pinos | [20090610 0 ambience.ogg](https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg) | Dominio público | nille | 2:03 · 3,31 MB · Ogg Vorbis 225 kbps | **No**: cuervos, insectos, coro del amanecer | No confirmado (etiqueta "Costa Rica") | Descartado |
| Cigarras | [Cicadas in Greece.ogg](https://commons.wikimedia.org/wiki/File:Cicadas_in_Greece.ogg) | Dominio público (autodeclarado, PD-self) | Channel R | 0:28 · 210 KB · Ogg Vorbis 62 kbps | Sí | Stavros, Ítaca (Grecia), julio 2008 | **Candidato B** (solo verano) |
| Cigarras | [Cicada orni.ogg](https://commons.wikimedia.org/wiki/File:Cicada_orni.ogg) | Dominio público | DavidDelon | 1:03 · 1,67 MB · Ogg Vorbis 220 kbps | **No**: gritos de niños | Hérault (Francia) | Descartado |
| Cigarras | [Canto de las cigarras.ogg](https://commons.wikimedia.org/wiki/File:Canto_de_las_cigarras.ogg) | **CC BY-SA 4.0** | ParaguayitoAlegre | 0:56 · 2,81 MB · Ogg Vorbis 417 kbps | Sí | No indicado | BY-SA |
| Paso (grava) | [Footstep on Gravel (Gravity Sound).mp3](https://commons.wikimedia.org/wiki/File:Footstep_on_Gravel_(Gravity_Sound).mp3) | CC BY 4.0 | Gravity Sound | 0,6 s · 12 KB · MP3 112 kbps | Sí | No indicado | **Candidato C** (un solo paso) |
| Paso (grava) | [Walkingongravel.ogg](https://commons.wikimedia.org/wiki/File:Walkingongravel.ogg) | **CC BY-SA 3.0** | Secretlondon | 0:12 · 248 KB · Ogg Vorbis 171 kbps | Sí | No indicado | BY-SA |
| Paso (grava) | [Walking-on-gravel-38827.ogg](https://commons.wikimedia.org/wiki/File:Walking-on-gravel-38827.ogg) | Figura como CC0 | Desconocido (Pixabay) | 0:06 · 50 KB | Sí | — | Descartado: origen Pixabay, licencia CC0 no verificada |
| Paseriforme | [Curruca rabilarga 01.mp3](https://commons.wikimedia.org/wiki/File:Curruca_rabilarga_(Curruca_undata)_01.mp3) | **CC BY-SA 4.0** | Benoît Van Hecke (XC794239) | 1:09 · 1,59 MB · MP3 192 kbps | No confirmado | 46,36 N 0,29 E (Francia, no mediterráneo) | BY-SA |
| Paseriforme | [Curruca rabilarga 02.wav](https://commons.wikimedia.org/wiki/File:Curruca_rabilarga_(Curruca_undata)_02.wav) | **CC BY-SA 4.0** | Tanguy Loïs (XC894020) | 1:05 · 11,9 MB · WAV | No confirmado | 42,73 N 9,45 E (Córcega) | BY-SA |
| Vencejo | [Cri de martinet pâle, Espagne.wav](https://commons.wikimedia.org/wiki/File:Cri_de_martinet_p%C3%A2le,_Espagne.wav) | **CC BY-SA 4.0** | Xavier Riera (XC932233) | 0:07 · 582 KB · WAV | Sí | 40,88 N 0,80 E (España; zona no nombrada) | BY-SA; no es paseriforme |
| Cormorán | [Cormoran moñudo.ogg](https://commons.wikimedia.org/wiki/File:Cormoran_mo%C3%B1udo.ogg) | **CC BY-SA 4.0** | Sternanita3 | 0:11 · 25 KB · Opus | Sí | No indicado | BY-SA; no es paseriforme |

Nota: los archivos de Commons con origen xeno-canto declaran BY-SA. No he podido abrir xeno-canto, así que no sé si la licencia original es BY-NC-SA. Si lo fuera, el archivo de Commons estaría mal etiquetado y no podría usarse ni como BY-SA.

## Comprobación en xeno-canto (responsable técnico, 2026-10-11)

xeno-canto solo tiene IPv4; se consultó por el relé NAT64 del proyecto (`curl --resolve`). La licencia se leyó en la ficha de cada grabación ("License …"), no en el pie de página.

| Grabación | Licencia en origen | Consecuencia |
|---|---|---|
| Commons "Cri de martinet pâle, Espagne.wav" = XC932233 (Xavier Riera) | **CC BY-NC-SA 4.0** | **Descartada**: Commons la etiqueta BY-SA por error; es no comercial |
| Commons "Yellow-legged Gull - Larus michahellis michahellis.ogg" (Cedric Mroczko, origen xeno-canto sin número) | Todas las grabaciones de gaviota de este autor en xeno-canto (XC237323, XC245734, XC245736, XC245741, XC283599…) son **CC BY-NC-SA 4.0** | **Descartada** por precaución: muy probablemente mal etiquetada en Commons |
| Commons "Curruca rabilarga (Curruca undata) 01.mp3" = XC794239 (Benoît Van Hecke) | CC BY-SA 4.0 | Válida, pero hay una CC BY (abajo) |
| **XC624044**, gaviota patiamarilla, Giovanni Francesco Tartarelli, Livorno (Toscana, Italia), 2021-02-24 | **CC BY 4.0** | **Candidata**: 39,6 s, mono, MP3 128 kbps, reclamo de adulto, sin fondo; 675 686 bytes. Puerto mediterráneo. Es un reclamo, no una colonia: la colonia se compone en la app repitiendo y desplazando reclamos |
| **XC930530**, curruca rabilarga, Camille Vacher, Taillades (Vaucluse, Provenza), 2024-05-31 | **CC BY 4.0** | **Candidata**: 25 s, mono, reclamo, sin fondo; 388 910 bytes |
| Búsquedas `lic:BY` y `lic:CC0` de *Oenanthe leucura* y *Apus pallidus* | sin resultados | Collalba negra y vencejo pálido siguen sin fuente válida |

Con estas dos, la gaviota y el paseriforme ya no necesitan BY-SA. Solo el viento en pinos sigue siendo BY-SA ("Wind in Swedish pine forest at 25 mps.ogg", obra propia del usuario de Commons, 1 909 781 bytes). **Ojo:** 25 m/s es un temporal (~90 km/h), no una brisa; habría que filtrarlo y bajarlo mucho, y puede no sonar natural.

**Descargado** (aprobado por el usuario el 2026-10-11; fase 4 de `data/catalog.toml`, sha256 en `data/manifest.lock.json`): los tres archivos de Commons de la lista de aprobación, XC624044 (gaviota) y XC930530 (curruca rabilarga). El viento en pinos queda pendiente de una fuente mejor; collalba negra y vencejo pálido, sin fuente.

## Otras fuentes

- **Freesound** (búsqueda web, no abierta: freesound.org no respondió desde aquí; NO VERIFICADO). Licencias vigentes: CC0, CC BY y CC BY-NC; Sampling+ está retirada. Los resultados de búsqueda que parecen válidos, todos NO VERIFICADOS:
  - Mar y piedras, Toulon: `freesound.org/people/oedipussimuss/sounds/636006/` (CC0 según el snippet). Es el mejor candidato de mar sobre roca mediterránea.
  - Olas y rocas, Grecia: `freesound.org/people/Profispiesser/sounds/550915/` (CC0 según el snippet).
  - Grava: `freesound.org/people/Fission9/sounds/521588/` (CC0, 2,7 s, cuatro pasos); `freesound.org/people/revolt2563/sounds/352870/` (CC0, 35 s).
  - Gaviotas colonia: no hay ninguna gaviota patiamarilla con CC0 o CC BY. Los resultados son gaviotas de otras especies o con NC.
  - Acceso a la API: requiere token (conocimiento general, no verificado hoy).
- **xeno-canto** (NO VERIFICADO; no respondió). Licencia por grabación; muchas son CC BY-NC-SA, que queda excluida. La API v3 pide clave, pero las fuentes encontradas se contradicen. La clave no está en el repositorio ni debe ponerse en él.
- **BBC Sound Effects / RemArc** (solo fuentes secundarias; las páginas oficiales no respondieron). Uso personal o educativo; el uso comercial requiere licencia aparte. **Excluido.**
- **Sonniss GDC (versión 2.0, vigente desde el 27-08-2026)**, `sonniss.com/gdc-bundle-license/`: se permite el uso sin atribución en proyectos de juegos, películas, podcasts y apps, pero no se pueden suministrar los efectos como archivos (traducción de la cláusula Restrictions c). Servir el archivo sin procesar en una web lo incumple. **Excluido**, salvo que un abogado diga que el uso sincronizado en una mezcla cubre el caso.
- **British Library**: no consultada; no es fuente habitual de sonido ambiente con licencia abierta.

## Conjunto mínimo propuesto (3 a 6 archivos)

| # | Capa | Archivo | Licencia | Estado | Codificación (estimada) | Bucle | Tamaño estimado |
|---|---|---|---|---|---|---|---|
| 1 | Mar sobre roca | Oceanwavescrushing.ogg, extracto de 60 s sin el barco | CC BY 3.0 | Verificado | Opus 48 kbps estéreo | 60 s, con fundido de 2 s | ≈ 360 KB |
| 2 | Gaviotas (colonia) | Pendiente: grabación propia o CC0 verificado | CC0 | **Falta** | Opus 32 kbps mono | 60 s | ≈ 240 KB (presupuesto) |
| 3 | Viento en pinos | Pendiente: grabación propia o CC0 verificado | CC0 | **Falta** | Opus 32 kbps mono | 60 s | ≈ 240 KB (presupuesto) |
| 4 | Cigarras (solo jun.–sep.) | Cicadas in Greece.ogg | Dominio público | Verificado | Opus 32 kbps mono | 28 s, sin bucle o con fundido | ≈ 112 KB |
| 5 | Paso sobre grava | Footstep on Gravel (Gravity Sound).mp3 | CC BY 4.0 | Verificado | Opus 64 kbps mono | Un disparo, con variación de tono | < 10 KB |
| 6 | Paseriforme (curruca rabilarga o collalba) | Pendiente | CC0 | **Falta** | Opus 32 kbps mono | 30 s | ≈ 120 KB (presupuesto) |

- **Total con las capas pendientes en su presupuesto: ≈ 1,08 MB**, dentro de los 2 MB. Son estimaciones de bitrate, no medidas: se medirá tras codificar.
- **Bucle sin coste en tiempo de ejecución:** pegar en el archivo el fundido de 2 s (los últimos 2 s se mezclan con el inicio) y reproducir con `AudioBufferSourceNode` con `loop = true`. No hace falta crossfade en la app.
- **Memoria (gotcha):** un bucle de 60 s a 48 kHz ocupa en RAM ≈ 11,5 MB en mono y ≈ 23 MB en estéreo (float32). Seis capas de 60 s cargadas a la vez suman ≈ 138 MB en estéreo o ≈ 69 MB en mono, demasiado para un móvil de gama media. Recomiendo cargar solo las capas de la zona activa (el spec ya habla de "capas por zona") y usar mono salvo para el mar.
- **Compatibilidad:** Opus en Safari/iOS no está verificado. Hay que probar con un `AudioContext` real o ofrecer AAC (`.m4a`, unos 96 kbps) como alternativa.
- **Arranque:** el `AudioContext` solo arranca con un gesto del usuario (`resume()`), tal como pide L2.

## Lista de descargas para aprobación

Solo archivos verificados. Los bytes son los del original (la app usará un extracto recodificado).

| Archivo | Host | Bytes | Licencia | Atribución (texto para CREDITS.md) |
|---|---|---|---|---|
| Oceanwavescrushing.ogg | upload.wikimedia.org (Commons) | 2 849 514 | CC BY 3.0 | "Oceanwavescrushing" de Luftrum, CC BY 3.0, vía Wikimedia Commons (https://commons.wikimedia.org/wiki/File:Oceanwavescrushing.ogg). Recortado y recodificado. |
| Cicadas in Greece.ogg | upload.wikimedia.org (Commons) | 214 994 | Dominio público (autodeclarado) | "Cicadas in Greece", Channel R, dominio público, vía Wikimedia Commons (https://commons.wikimedia.org/wiki/File:Cicadas_in_Greece.ogg). |
| Footstep on Gravel (Gravity Sound).mp3 | upload.wikimedia.org (Commons) | 12 142 | CC BY 4.0 | "Footstep on Gravel" de Gravity Sound, CC BY 4.0, vía Wikimedia Commons (https://commons.wikimedia.org/wiki/File:Footstep_on_Gravel_(Gravity_Sound).mp3). |
| **Total** | | **3 076 650** (≈ 3,1 MB) | | Tras codificar, ≈ 0,5 MB para estas tres. |

Pendientes, sin bytes todavía: gaviotas, viento y paseriforme (grabación propia o CC0 verificado).

## Conflictos y lo no verificado

- **Conflicto:** spec 002 L2 y `002-plan-propuesto` (BY-SA permitido para audio) frente a `CLAUDE.md` línea 44 (solo CC0/CC BY). Necesita tu decisión; cambiar `CLAUDE.md` o aceptar una excepción registrada.
- **No verificado:** licencia original de los archivos de xeno-canto; todo Freesound; los términos oficiales de BBC; la API de xeno-canto.
- **Límite de búsqueda:** la API de Commons devolvió 429 (límite de peticiones), así que la búsqueda no es exhaustiva. Puede haber una gaviota patiamarilla o un viento mediterráneo con CC BY que no haya encontrado.
- **Gravity Sound:** la licencia viene de Commons; la página del autor no la he abierto.
- **Temporada:** la colonia de gaviotas tiene sentido en primavera-verano. Un estudio de 1986 en la isla del Descubridor (Alicante) visitó colonias de mediados de abril a principios de julio (fuente en la búsqueda, no abierta). No he encontrado en fuentes españolas el periodo "marzo a junio". En octubre la colonia estará casi vacía; la capa de gaviotas debería cambiar según la estación o usarse solo para el tramo de verano.
- **Cigarras:** las fechas de vuelo son orientativas (conocimiento general, no verificado para la Comunidad Valenciana): adultos de finales de primavera a finales de verano, máximo en julio-agosto. En octubre no deben sonar.
- **Grabación en el parque:** hay halcón peregrino en cría (abril a junio, prohibición de escalada en caras norte y noroeste, `content/facts.json`) y *Silene hifacensis*. Grabar en colonias en primavera puede molestar. Se necesita permiso del parque; no se usan drones (prohibidos).
- **Sin validar:** el sonido no se comprueba con gente de la zona, y no hay cifra de parejas (`bird-pair-counts`, unverified).

## Decisiones que necesito de ti

1. ¿Aceptas BY-SA para audio (cambio de `CLAUDE.md` línea 44 y ADR 0007), o solo CC0 y CC BY? Con CC0/CC BY, las capas de gaviota, viento y paseriforme quedan sin fuente verificada.
2. ¿Autorizas una grabación propia en el parque (permiso del parque, CC0), o prefieres buscar en Freesound con clave de API?
3. ¿Aprobamos descargar los tres archivos de la tabla anterior (≈ 3,1 MB en origen)?

---
status: approved
---

# 006 — Hito H1: Paseo con sentido

- Fecha: 12/10/2026. Encargo del usuario: planificar H1 de `docs/roadmap.md` e incluir **assets reales de barcos, rocas y muros de roca** que completen el camino.
- Ámbito geográfico:
  - desde la entrada del parque (`park-entrance`) por el acceso, el aparcamiento, el centro y el torniquete, hasta el km 0,421 de la ruta: el tramo piloto de 002, con 350 m después del torniquete;
  - el puerto se ve desde el tramo, y sus barcos y pantalanes entran en H1.
- Reúne lo que H1 toma de otras specs, sin duplicarlo: 004 X0–X1, 003 E1.2, E3 y E4, y 002 B4, B7, B9, B10, B11 y B12. Las tareas nuevas (inventario por evidencia, muros, rocas, barcos, publicación de prueba) se definen aquí.

## Problema

- El paseo ya es fiel en terreno, vegetación y edificios, pero aún no **se entiende ni se completa**:
  - no hay forma de orientarse ni de leer las fichas;
  - el firme es un color;
  - faltan los muros de piedra seca, las rocas, las barandillas y el mobiliario que dan forma al camino real;
  - el puerto que se ve abajo está vacío.
- Además, nadie de fuera lo ha probado.

## Para quién

Para las cuatro personas de `docs/specs/004-experiencia/propuesta.md` §1: vecinos, quien no puede subir, escolares y visitantes. Los niños son usuarios de pleno derecho.

## Alcance

1. **Orientación e interfaz:** 004 X0–X1, es decir, fichas, cuaderno, "Más", "Ir a la cima", minimapa, altitud, mapa y viaje rápido, y "¿Dónde estoy?". También tocar para caminar (B10) y la calidad automática (B11).
2. **Firme real:** las lajas de caliza con mortero, la grava y el adoquín de las escaleras (E1.2).
3. **Bordes y mobiliario por evidencia:**
   - talanqueras de rollizos, torniquete, fuentes, paneles y pérgolas del aparcamiento (E4);
   - **muros de piedra seca** y **rocas**, solo donde una fuente los sitúa;
   - el pórtico de arcos y las torretas del centro (E3+).
4. **El puerto que se ve:** **barcos medidos** en la ortofoto de 2024 (posición, rumbo, eslora y manga) y los pantalanes de OSM.
5. **Sonido básico:** mar, gaviota patiamarilla, viento y pasos, desde el primer gesto, con volumen y silencio.
6. **Contenido del tramo:**
   - fichas del Centre, el torniquete y la reserva, el mirador y la Pobla vista desde él, en es, va y en;
   - la consulta al parque, enviada.
7. **Prueba con personas:** una dirección de prueba privada, la medición en móviles reales (A7), la comparación con fotos fechadas en línea y la prueba con cinco vecinos a distancia.
8. **Caminante animado** (B7), solo si llega el zip de Quaternius.

## Fuera de alcance

- Hora y tiempo reales, cielo nocturno y sombras: es H2.
- El resto de la ruta, los edificios del puerto, la escollera y la Pobla en 3D: es H3.
- Los modos, la memoria (antes y ahora) y el kiosco: es H4.
- Cualquier objeto sin evidencia de su posición. Un muro, una roca o un barco que no se pueda situar con una fuente **no se coloca**.

## Criterios de aceptación

1. **Orientación.**
   - Dado un visitante nuevo en un móvil de gama media en `park-entrance`, cuando carga la app, entonces ve el paisaje con la interfaz mínima del diseño (`diseno-interfaz.md`): hora, minimapa, altitud y tres botones.
   - Con un toque llega a la ficha de cualquier sitio, y con "Ir a la cima" empieza a subir a ritmo real.
2. **Camino completo.**
   - Dado el tramo piloto, cuando se recorre, entonces el firme se ve como lajas de caliza con mortero (y grava o adoquín donde OSM lo dice).
   - Las barandillas, los muros, las rocas y el mobiliario aparecen **solo** donde los sitúa el inventario por evidencia, y cada objeto colocado tiene un identificador de evidencia (una prueba automática lo comprueba).
3. **El puerto.**
   - Dado el puerto visto desde el tramo, entonces cada barco detectado en la ortofoto de 2024 aparece en su posición y rumbo, con su eslora y su manga.
   - El recuento y las dimensiones se contrastan con la ortofoto en una muestra revisada a mano.
   - El tipo de barco se rotula como aproximado en `CREDITS.md`.
4. **Contenido.** Las fichas del tramo muestran sus hechos con estado y fuentes en es, va y en, y el valenciano está revisado por una persona.
5. **Sonido.** Arranca con el primer gesto, se puede silenciar y ajustar desde "Más", y cada grabación tiene su licencia en `CREDITS.md`. No suena nada que no esté documentado en el parque (las cigarras quedan fuera hasta tener un registro).
6. **Rendimiento.**
   - En los móviles de referencia, dentro del tramo: p95 ≤ 33,3 ms y p99 ≤ 50 ms.
   - La prueba de presupuesto por sistema está en verde en los tres niveles.
   - El terreno es visible en ≤ 10 s con "4G rápido".
7. **Accesibilidad.** La lista P0 de `docs/research/005-experiencia-referentes.md` pasa: axe sin errores críticos, teclado completo, lector de pantalla en la interfaz y nada dependiente de un atajo.
8. **Personas.**
   - Cinco vecinos completan a distancia, sin ayuda, el guion de `docs/specs/002/pruebas-vecinos.md`: llegar, orientarse, leer una ficha, guardarla en el cuaderno e ir a la cima. Lo grave queda corregido o registrado.
   - La comparación con fotos fechadas se hace en 2–3 puntos con el protocolo de `docs/research/002-verificacion.md` §4.

# Prueba con cinco vecinos (B12) — guion

- Estado: **borrador**, arranque anticipado del carril L8. Lo organiza el responsable del proyecto y lo prepara el responsable técnico.
- **Criterio de salida** (plan 002, fase B):
  - **cinco vecinos completan, sin ayuda,** llegar, caminar el tramo, abrir la ficha y guardarla en el cuaderno, en el idioma que elijan;
  - se anotan sus tiempos y comentarios;
  - **todo problema grave queda corregido o registrado.**
- **Cuándo**: cuando la fase B esté integrada y desplegada en una URL de prueba, antes de marcarla como hecha.
  - Si los vecinos no están disponibles, la fase B queda "pendiente de validación", no "hecha" (plan 002, riesgos).
- **Por qué cinco**: se suele citar a Nielsen y Landauer (1993) para justificar que con cinco usuarios aparecen la mayoría de los problemas de uso. **Sin verificar en este proyecto**: no se ha consultado el texto (ver `docs/research/002-verificacion.md`).

## Participantes

- Cinco personas **adultas** de Calp o que conozcan bien el Penyal. No pueden ser del equipo.
- **Mezcla**:
  - al menos dos que hayan hecho la Ruta Roja hace poco;
  - al menos una que no la haya hecho nunca;
  - al menos una mayor de 60 años;
  - si es posible, una que prefiera el valenciano y otra que prefiera el inglés.
- **Dispositivos**:
  - al menos tres con **su propio móvil**, porque el móvil es el uso principal;
  - al menos una con ordenador;
  - una de las pruebas de móvil, con datos móviles en lugar de wifi.
- **Sin menores.** Si más adelante se quiere probar con escolares, se hará en la fase D, con el consentimiento de sus familias y del centro educativo.

## Antes de la sesión

- La URL de prueba funciona y es la versión que se quiere validar.
  - Anota el *commit* de la versión.
  - Comprueba que la app no tiene analítica ni guarda nada fuera del navegador, salvo el cuaderno local.
- Para medir la carga real, cada persona abre el enlace **por primera vez** en su navegador. Si ya lo abrió antes, usa una ventana privada.
- Material:
  - este guion impreso;
  - un cronómetro;
  - la hoja de registro (al final de este documento);
  - un cargador.
- **Una persona facilita.** Si es posible, otra toma notas.
- **Mientras la persona hace las tareas, quien facilita no ayuda ni señala nada en la pantalla.** Si alguien se atasca más de 2 minutos, se da una pista y se anota "con pista".

## Consentimiento (leer en voz alta)

> Gracias por ayudarnos. Estamos probando un recorrido virtual del Penyal d'Ifac. **Probamos la aplicación, no a ti**: si algo no se entiende, es culpa nuestra. Te pediré que hagas unas tareas y que digas en voz alta lo que piensas mientras las haces. No grabamos ni tu cara ni tu voz. Solo apuntamos notas, sin tu nombre, con un código (V1 a V5). Puedes parar cuando quieras. Son unos 25 minutos. ¿Te parece bien?

Se apunta "consentimiento verbal: sí" y la fecha. No se apunta ningún dato personal más, salvo la edad aproximada (tramo de 10 años) y si ha hecho la ruta.

## Tareas

Las tareas se leen tal cual, sin dar pistas sobre cómo hacerlas.

| # | Tarea (en voz alta) | Qué se observa | Se mide |
|---|---|---|---|
| T1 | "Abre este enlace. Avísame cuando puedas empezar a caminar." | Qué entiende de la pantalla de carga; si sabe qué hacer al terminar | Tiempo hasta el primer paso. Completa sin ayuda, con pista o no completa |
| T2 | "Camina por el sendero hasta donde puedas." Termina al llegar al final del tramo piloto o a los 8 minutos | Cómo descubre los controles; si se pierde o se atasca; si entiende el aviso del límite del sendero | Tiempo, número de atascos y si llega al final |
| T3 | "Hay algo interesante cerca. Encuéntralo y entérate de qué es." | Si ve el punto de interés y si abre la ficha | Tiempo hasta abrir la ficha |
| T4 | "¿De dónde sale esta información? ¿Hay algún dato del que las fuentes no estén seguras?" | Si encuentra "Ampliar", las fuentes y las discrepancias | Encuentra las fuentes (sí/no); encuentra una discrepancia (sí/no) |
| T5 | "Guárdalo para poder verlo después." Luego: "Ahora búscalo." | Si guarda la ficha en el cuaderno y la vuelve a encontrar | Completa o no; tiempo |
| T6 | "Pon la aplicación en otro idioma." Se pide solo si no lo eligió al principio | Si encuentra el selector de idioma | Completa o no |

Después de cada tarea se hace una pregunta de facilidad: "Del 1 al 7, ¿cómo de fácil ha sido?" Es la *Single Ease Question*.

## Preguntas finales

1. "¿Has reconocido el sitio? ¿Qué te ha parecido igual que el real y qué distinto?" Se apunta la respuesta y un 1–5: "se parece al Penyal real".
2. "¿Te has mareado o te ha cansado la vista?" De 1, nada, a 5, mucho.
3. Sonido (B4): "¿Has notado el sonido? ¿Te ha ayudado o te ha molestado?"
4. "¿Te fías de lo que dice la ficha? ¿Por qué?"
5. "¿Qué es lo primero que cambiarías?"
6. "¿Se lo enseñarías a alguien? ¿A quién?"

## Hoja de registro (una por persona)

```
Código: V_   Fecha: ____   Edad: __–__   Ha hecho la ruta: sí / no (hace ____)
Dispositivo: ________ (navegador ____)  Red: wifi / datos   Idioma elegido: es / va / en
Versión (commit): ________

T1  tiempo hasta caminar: ____ s   sin ayuda / con pista / no   facilidad 1–7: _
T2  tiempo: ____  atascos: __  llega al final: sí / no         facilidad: _
T3  tiempo hasta la ficha: ____                                 facilidad: _
T4  fuentes: sí / no   discrepancia: sí / no                    facilidad: _
T5  guarda: sí / no   la encuentra: sí / no   tiempo: ____      facilidad: _
T6  idioma: sí / no / no aplica                                 facilidad: _

Reconoce el sitio 1–5: _   Mareo 1–5: _
Comentarios literales:


Problemas observados (uno por línea, con la tarea y la gravedad):
```

## Gravedad y qué se hace con cada problema

| Gravedad | Definición | Qué se hace |
|---|---|---|
| **Grave** | Impide completar una tarea sin ayuda, o da información falsa o peligrosa | Se corrige antes de cerrar la fase B. Si no se puede, se registra con su motivo y la fase queda "pendiente de validación" |
| **Importante** | Retrasa mucho, confunde o hace pedir una pista | Se convierte en una tarea de la fase B2 o C |
| **Menor** | Molestia o detalle estético | Se registra |

## Resultado

- Todo se resume en `docs/audits/002-vecinos.md`:
  - una tabla con las cinco personas;
  - los tiempos (mediana y peor caso);
  - la facilidad media por tarea;
  - los problemas agrupados por gravedad;
  - las citas literales más útiles, sin datos personales.
- **La fase B pasa la prueba solo si**:
  - las cinco personas completan T1, T2, T3 y T5 sin ayuda;
  - no queda ningún problema grave sin corregir ni registrar.

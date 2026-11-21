# Contribuir

¡Gracias por querer colaborar con hex-arena! Esta guía resume cómo trabajamos.

## Flujo de trabajo

1. **Nunca se trabaja directamente en `main`.** La rama `main` está protegida.
2. Crea una rama con un nombre descriptivo:
    - `feature/descripcion-corta` para funcionalidades nuevas;
    - `fix/descripcion-corta` para correcciones;
    - `bot/nombre-del-bot` para bots nuevos.
3. Haz commits pequeños siguiendo [Conventional Commits](https://www.conventionalcommits.org/es/):

    | Prefijo | Uso | Ejemplo |
    |---|---|---|
    | `feat` | Funcionalidad nueva | `feat(bots): add BridgeBot` |
    | `fix` | Corrección de un error | `fix(game): reject boolean coordinates` |
    | `test` | Tests | `test(game): cover 1x1 board` |
    | `docs` | Documentación | `docs: add bot tutorial` |
    | `chore` | Mantenimiento | `chore: update dependencies` |

4. Abre un **pull request** hacia `main`. El CI ejecutará los tests en Python 3.10, 3.11 y 3.12.
5. Otra persona del equipo **revisa** el PR. Hace falta al menos **una aprobación** y que el CI pase para poder fusionar.

## Antes de abrir el PR

- [ ] `pytest` pasa en local.
- [ ] El código nuevo tiene **type hints** y **docstrings** (estilo Google).
- [ ] Hay tests para la funcionalidad nueva.
- [ ] Si cambia el API público, la documentación está actualizada.

## Estilo de código

- Python 3.10+, con type hints en todas las funciones públicas.
- Docstrings en estilo Google: `Args:`, `Returns:`, `Raises:`. Así aparecen en la [referencia del API](api/game.md).
- La lógica del juego (`hexarena.game`) **no depende** de los bots ni de la web.
- La librería no añade dependencias externas: solo librería estándar.

## Añadir un bot

Sigue el [tutorial](tutorial-bot.md). Un bot nuevo debe:

- estar en **un único archivo** en `src/hexarena/bots/`;
- pasar los tests de contrato (`tests/test_bots_contract.py`);
- no acceder a la red ni a archivos, ni ejecutar código peligroso;
- ser razonablemente mejor que `RandomBot`.

## Cómo revisamos un PR de bot

Antes de aprobar el PR de un bot nuevo, quien revisa comprueba estos cinco puntos:

| Punto | Qué miramos |
|---|---|
| **API** | Hereda de `Bot`, está registrado con un nombre único, se crea sin argumentos, devuelve siempre una jugada de `observation.legal_moves` y no modifica la observación |
| **Seguridad** | Solo importa la librería estándar y `hexarena`; no usa la red, archivos ni procesos; no tiene variables globales compartidas. Leemos el código **entero** antes de ejecutarlo |
| **Alcance** | Solo añade su archivo en `src/hexarena/bots/`: no toca el juego, otros bots ni los tests |
| **Tests y tiempos** | El CI está en verde (incluye los tests de contrato, que examinan solos cada bot y su tiempo de respuesta) |
| **Calidad** | El código y la descripción se entienden, la estrategia está explicada y el bot gana con claridad a `RandomBot` |

Los fallos de los tres primeros puntos se piden como **cambios** (*Request changes*); las mejoras de estilo o rendimiento, como **sugerencias**. Si todo está bien, se **aprueba** (*Approve*) y se fusiona. Así se aceptó **Portero**, el primer bot enviado por otro equipo ([PR #22](https://github.com/monianzola/HEX/pull/22)).

## Documentación

```bash
pip install -e ".[docs]"
mkdocs serve
```

Las páginas están en `docs/`. La referencia del API se genera sola a partir de los docstrings con mkdocstrings.

## Reportar un problema

Abre un *issue* en GitHub con los pasos para reproducirlo, lo que esperabas que pasara y lo que pasó en realidad.

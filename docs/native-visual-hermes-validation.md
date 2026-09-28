# Native V2: validación en Hermes y límites del host

Validado el 26 de septiembre de 2026 con el checkout local de Hermes Desktop
0.17.6. Se lanzó una instancia Electron independiente con perfil/HERMES_HOME
temporales, sin proveedor ni conversación personal. Se omitió el onboarding
mediante su acción existente de elegir proveedor más tarde. Los fixtures se
registraron en el store de artifacts y se abrieron con `openArtifact`.
Esto comprueba el panel real; no constituye una prueba de generación vía LLM.

## Resultados

La matriz de cinco fixtures por ocho anchos pasó en Chromium y Firefox:
40 casos por navegador sin overlaps de cards, clipping horizontal, segmentos
atravesando cards, labels superpuestos ni conexiones ausentes. Se revisaron
capturas de branching, Compact/Wide y la instancia real de Hermes.
El gate Chromium incluye además ocho comprobaciones de resize de contenedor,
foco/detalles e iframe sandboxed: 48 casos en total, cero errores de navegador.

En Hermes se arrastró el separador real del panel, manteniendo la ventana:

| Fixture | Ancho del iframe medido | Composición medida | Modo | Columnas | Ancho mínimo de card |
| --- | ---: | ---: | --- | ---: | ---: |
| Arquitectura, 14 nodos | 742 | 691 | Compact | 2 | 293 |
| Arquitectura, 14 nodos | 900 | 849 | Compact | 3 | 232 |
| Hermes, 19 nodos | 650 | 599 | Compact | 2 | 248 |
| Hermes, 19 nodos | 742 | 691 | Compact | 2 | 293 |
| Hermes, 19 nodos | 900 | 849 | Compact | 3 | 232 |

El fixture grande mantuvo sus 19 cards y 21 conexiones. El foco destacó las
relaciones; abrir/cerrar detalles redistribuyó la altura sin colisiones.
El scroll llegó al final del documento. El iframe medía aproximadamente
1085 px de alto, mientras que su documento alcanzaba 3277 px con detalles
abiertos. Los márgenes, scrollbar y escala de Electron explican por qué el
ancho de composición no coincide con el ancho exterior solicitado.

Los informes y capturas se conservan localmente en
`diagrams/generated/v2-validation/`: `report.json`, `firefox-report.json`,
`hermes-report.json` y `hermes-d_hermes_large-742.png`. Esta carpeta está
excluida de Git; los fixtures y el gate están versionados. Un primer intento
de resize del fixture C solicitó 650 px pero midió 870 px: se conservó el
valor real en el informe y no se contó como validación a 650.

## Responsabilidades y altura

El renderer controla cards, filas, lanes, corredores, detalles y altura del
documento. No impone una altura fija ni un segundo contenedor con scrollbar.

Hermes controla ancho/alto y posición del panel. En
`apps/desktop/src/app/chat/right-rail/preview-artifact.tsx`,
`ArtifactLiveView` usa un iframe `sandbox="allow-scripts"` con `size-full`
dentro de un panel flex de altura disponible. No hay negociación automática
de altura con el HTML: el scroll del documento dentro del iframe es esperado.
La política aislada no permite al artifact ampliar la aplicación anfitriona.

La prueba usó esta ruta de artifact HTML. No todas las rutas de preview son
equivalentes: `preview-pane.tsx` usa `sandbox=""` para HTML remoto, donde los
scripts están deshabilitados. En ese caso V2 solo muestra las cards y la lista
de relaciones con un aviso; abrir como artifact ejecutable o externamente.
No se modificaron las políticas ni el código de Hermes.

## Expansión: investigación independiente

El código y la UI local ofrecen resize mediante los separadores del panel;
se probó efectivamente. `preview-artifact.tsx` también ofrece **Open in browser**:
guarda el HTML completo en un archivo temporal mediante el bridge y lo abre
en el navegador del sistema. Su implementación fue inspeccionada; la prueba
Firefox abrió directamente el mismo HTML, sin automatizar ese botón.

`store/preview.ts::popOutBrowserTab` permite una ventana separada para tabs de
tipo `url`; no aplica directamente a registros de tipo `artifact`. No se
identificó una acción de fullscreen específica del artifact en
`ArtifactPreview`. No se presupone que todas las versiones de Hermes tengan
las mismas opciones. Compact funciona sin depender de ninguna expansión.

## Repetir la comprobación del host

1. Generar los fixtures con el gate documentado en `native-visual-artifacts.md`.
2. Abrir los HTML C/D en la ruta de artifacts de una instancia de prueba de
   Hermes. Mantener una copia en disco: el registro del host es memory-only.
3. Arrastrar el divisor a aproximadamente 650, 742 y 900 px; medir el iframe y
   `.composition.clientWidth`, no la resolución del monitor.
4. Comprobar `data-mode`, cantidad de `.node`/`.edge`,
   `data-routing-errors`, foco, detalles, scroll y el resize sin recargar.
5. Comparar con el mismo HTML en Firefox y capturar el resultado.

Si se usa el inspector local de Hermes, seguir su guía
`skills/software-development/inspecting-hermes-desktop-dom/SKILL.md`;
no reiniciar la aplicación personal para habilitar CDP. Usar un perfil y
puerto independientes. En pruebas con varias versiones, usar títulos distintos
por fixture o seleccionar explícitamente la versión nueva: el host puede
conservar una selección anterior aunque cambie el contenido del registro.

# Study Pack — Ley de Gauss

**Materia:** Física II  
**Tema:** Flujo eléctrico y Ley de Gauss  
**Fuente base:** Sears y Zemansky, *Física Universitaria, Volumen 2*, capítulo 22, “Ley de Gauss” (páginas impresas 752–764; páginas del PDF consultadas 68–83).  
**Propósito:** material de estudio listo para cargar como fuente en NotebookLM. Las referencias entre corchetes apuntan a páginas impresas del libro cuando están visibles en el texto recuperado; en caso de duda, verificar en el PDF, porque la paginación impresa y la del archivo pueden diferir.

## 1. Objetivos de aprendizaje

Al terminar, deberías poder:

1. Definir el flujo eléctrico y determinar su signo.
2. Enunciar la Ley de Gauss e identificar la carga encerrada relevante.
3. Explicar por qué la ley es válida para cualquier superficie cerrada, pero solo simplifica el cálculo de \(\mathbf E\) cuando hay suficiente simetría.
4. Elegir una superficie gaussiana que aproveche la simetría esférica, cilíndrica o plana.
5. Resolver campos eléctricos y comprobar unidades, dirección y límites físicos.

## 2. Ideas esenciales

### Flujo eléctrico

El flujo mide cuánto campo eléctrico atraviesa una superficie. Para un elemento de área orientado \(d\mathbf A=\hat{\mathbf n}\,dA\),

\[
d\Phi_E=\mathbf E\cdot d\mathbf A=E\cos\theta\,dA.
\]

Para una superficie cerrada,

\[
\Phi_E=\oint_S \mathbf E\cdot d\mathbf A.
\]

La normal de una superficie cerrada se toma hacia afuera. El flujo es positivo donde el campo sale, negativo donde entra y nulo localmente si el campo es tangente a la superficie. [Sears y Zemansky, cap. 22, pp. 758–760; PDF pp. 77–79]

### Ley de Gauss

\[
\boxed{\oint_S \mathbf E\cdot d\mathbf A=\frac{Q_{\mathrm{enc}}}{\varepsilon_0}}
\]

\(Q_{\mathrm{enc}}\) es la carga neta dentro de la superficie cerrada; \(\varepsilon_0\) es la permitividad del vacío. Cargas exteriores pueden contribuir al campo en la superficie, pero su contribución neta al flujo cerrado se cancela: la ley depende de la carga neta encerrada. Así, flujo neto cero no implica necesariamente campo cero en cada punto. [Sears y Zemansky, cap. 22, pp. 759–761; PDF pp. 77–79]

La ley es general. La estrategia para hallar \(\mathbf E\) usando la ley requiere además que la simetría permita conocer la dirección del campo y simplificar la integral.

## 3. Cómo resolver problemas: receta

1. **Identifica la distribución de carga y su simetría.** Busca simetría esférica, cilíndrica o planar.
2. **Determina la dirección del campo** con la simetría y el signo de la carga.
3. **Elige una superficie cerrada imaginaria** que pase por el punto donde quieres hallar \(E\). Busca que \(E\) sea constante en las partes útiles o que el campo sea perpendicular/tangente de forma sencilla.
4. **Calcula la carga encerrada** \(Q_{\mathrm{enc}}\), no la carga total del sistema si una parte queda afuera.
5. **Evalúa el flujo por partes.** Justifica cuáles caras aportan y cuáles no.
6. **Aplica Gauss y despeja \(E\).** Conserva el signo o describe la dirección por separado de la magnitud.
7. **Comprueba unidades y sentido físico.** El campo debe tener unidades \(\mathrm{N/C}\) (equivalentes a \(\mathrm{V/m}\)); el resultado debe respetar simetría y disminuir/aumentar de forma coherente con la geometría.

## 4. Aplicaciones prototipo por simetría

### A. Simetría esférica: carga puntual o distribución esférica

Toma una esfera gaussiana de radio \(r\) centrada en la distribución. Por simetría, el campo es radial y tiene magnitud constante sobre esa esfera; por tanto,

\[
E(4\pi r^2)=\frac{Q_{\mathrm{enc}}}{\varepsilon_0},\qquad
E=\frac{Q_{\mathrm{enc}}}{4\pi\varepsilon_0r^2}.
\]

Para una carga puntual, \(Q_{\mathrm{enc}}=q\), recuperando el campo de Coulomb. Para una distribución extendida, determina primero qué parte de la carga queda dentro del radio \(r\). Dirección: radial hacia afuera si la carga neta encerrada es positiva, hacia adentro si es negativa. [Sears y Zemansky, cap. 22, pp. 760–762; PDF pp. 78–81]

### B. Simetría cilíndrica: línea larga de carga

Para una línea ideal infinita con densidad lineal \(\lambda\), elige un cilindro coaxial de radio \(r\) y longitud \(L\). El flujo por las tapas es cero porque el campo es paralelo a ellas; por la pared lateral, \(\Phi_E=E(2\pi rL)\). La carga encerrada es \(\lambda L\), así que

\[
E(2\pi rL)=\frac{\lambda L}{\varepsilon_0},\qquad
E=\frac{\lambda}{2\pi\varepsilon_0r}.
\]

El campo es radial y su sentido depende del signo de \(\lambda\). Este resultado presupone simetría cilíndrica ideal (línea infinita). [Sears y Zemansky, cap. 22, pp. 762–763; PDF pp. 81–82]

### C. Simetría planar: plano infinito de carga

Para una lámina infinita con densidad superficial uniforme \(\sigma\), usa una “pastilla” cilíndrica que atraviese el plano. El campo es perpendicular al plano y no hay flujo por la pared curva; las dos tapas aportan flujo. Para una lámina no conductora ideal,

\[
2EA=\frac{\sigma A}{\varepsilon_0},\qquad
E=\frac{\sigma}{2\varepsilon_0}.
\]

El campo apunta hacia afuera de la lámina si \(\sigma>0\), y hacia ella si \(\sigma<0\). En conductores o arreglos de varias láminas, las condiciones y cargas relevantes cambian; no traslades esta fórmula sin revisar el modelo. [Sears y Zemansky, cap. 22, pp. 763–764; PDF pp. 82–83]

## 5. Qué significa —y qué no significa— la superficie gaussiana

- Es una superficie matemática cerrada escogida para calcular una integral; no necesita ser una superficie material.
- Puede tener cualquier forma: la ley sigue siendo válida. La elección útil es la que aprovecha la simetría para sacar \(E\) de la integral o anular partes del flujo.
- La carga fuera de la superficie no cuenta en \(Q_{\mathrm{enc}}\), aunque sí pueda alterar localmente \(\mathbf E\).
- \(Q_{\mathrm{enc}}=0\) implica flujo neto cero, no ausencia de campo.
- La ley no determina por sí sola \(E\) en cada punto para distribuciones arbitrarias: hace falta información de simetría u otros métodos. [Sears y Zemansky, cap. 22, pp. 759–762; PDF pp. 77–80]

## 6. Errores frecuentes

1. **Contar cargas exteriores en \(Q_{\mathrm{enc}}\).** Solo se incluye la carga neta dentro de la superficie.
2. **Confundir flujo cero con campo cero.** Puede haber líneas de campo entrando y saliendo que se cancelen en el flujo neto.
3. **Usar \(EA\) sin justificarlo.** Solo se simplifica así cuando el campo es uniforme y perpendicular en esa parte de la superficie; si es tangente, el flujo es cero.
4. **Elegir una superficie que no respeta la simetría.** La ley sigue valiendo, pero quizás no permite despejar \(E\).
5. **Olvidar orientación y signo.** La normal de una superficie cerrada apunta hacia afuera; flujo entrante es negativo.
6. **Aplicar resultados ideales a geometrías finitas.** Las fórmulas de línea y plano infinitos dependen de idealizaciones de simetría.
7. **Confundir la carga total con la densidad.** \(\lambda\) es carga por longitud, \(\sigma\) es carga por área, y \(\rho\) (cuando corresponda) es carga por volumen.

## 7. Preguntas de repaso

1. ¿Qué representa físicamente el flujo eléctrico?
2. ¿Por qué la integral de Gauss se toma sobre una superficie cerrada?
3. Una superficie cerrada contiene cargas \(+q\) y \(-q\). ¿Cuál es su flujo neto? ¿Se deduce que \(\mathbf E=0\) en toda la superficie?
4. ¿Qué condiciones permiten convertir \(\oint \mathbf E\cdot d\mathbf A\) en \(EA\)?
5. ¿Por qué las tapas de un cilindro coaxial no contribuyen al flujo de una línea ideal infinita?
6. ¿Cómo cambia el campo de una línea infinita al duplicar la distancia? ¿Y el de una carga puntual?
7. Para cada distribución —carga puntual, línea infinita, plano infinito— dibuja la superficie gaussiana apropiada y marca las regiones con flujo nulo.
8. Una superficie gaussiana se agranda sin cambiar la carga encerrada. ¿Qué afirma la ley sobre el flujo total? ¿Qué puede cambiar localmente?
9. ¿Qué información adicional se necesita para calcular \(Q_{\mathrm{enc}}\) cuando la carga está distribuida en volumen?
10. Describe un procedimiento para decidir si Gauss es una herramienta eficaz en un problema dado.

## 8. Respuestas breves

1. Cuantifica la componente neta del campo que atraviesa la superficie.
2. Porque el teorema relaciona el flujo neto cerrado con la carga neta encerrada.
3. \(Q_{\mathrm{enc}}=0\), entonces \(\Phi_E=0\); no necesariamente, puede existir campo local con flujo entrante y saliente compensado.
4. Magnitud constante de \(E\) en la región integrada y campo normal a la superficie; si es tangencial, esa contribución es cero.
5. El campo es radial, paralelo a las tapas, así que \(\mathbf E\cdot d\mathbf A=0\) allí.
6. Línea infinita: \(E\propto 1/r\), así que se reduce a la mitad. Carga puntual: \(E\propto 1/r^2\), así que queda en la cuarta parte.
7. Esfera centrada en la carga; cilindro coaxial; pastilla que cruza el plano.
8. El flujo total permanece en \(Q_{\mathrm{enc}}/\varepsilon_0\); la distribución local de campo y flujo puede variar.
9. La densidad de carga y el volumen encerrado, integrados sobre la región interna.
10. Identificar simetría, inferir dirección y constancia de \(E\), y verificar si una superficie cerrada útil simplifica la integral.

## 9. Mini-glosario

- **Flujo eléctrico \(\Phi_E\):** integral de la componente normal del campo sobre una superficie.
- **Superficie gaussiana:** superficie cerrada matemática usada en la integral de Gauss.
- **Carga encerrada \(Q_{\mathrm{enc}}\):** carga neta dentro de la superficie elegida.
- **Densidad lineal \(\lambda\):** carga por unidad de longitud, \(\mathrm{C/m}\).
- **Densidad superficial \(\sigma\):** carga por unidad de área, \(\mathrm{C/m^2}\).
- **Densidad volumétrica \(\rho\):** carga por unidad de volumen, \(\mathrm{C/m^3}\).
- **Simetría:** invariancia de la distribución que permite inferir cómo se orienta y varía el campo.

## 10. Referencia y alcance

Contenido contrastado con los fragmentos recuperados del Source Engine desde **“LIbro de Sears y Zemansky”**, capítulo 22: flujo eléctrico y carga encerrada (pp. 752–760; PDF pp. 70–79), aplicaciones y elección de superficies gaussianas (pp. 762–764; PDF pp. 80–83). El Source Engine devuelve fragmentos por página, no el capítulo completo; las fórmulas prototipo anteriores son una síntesis didáctica de esos resultados y sus supuestos ideales. Para una cita textual o verificar una demostración, consulta el PDF original en `materials/fisica/Sears_Zemansky_F_sica_Universitaria_Vol_2.pdf`.

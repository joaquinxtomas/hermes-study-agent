# Presentación de assets estáticos

Las solicitudes visuales ahora usan la skill única Hermes `concept-diagrams`. Los
renderers documentados aquí son backends de compatibilidad; la política actual
mantiene chico/mediano inline y expande solo artifacts grandes o densos.

Este presenter histórico sigue disponible en `scripts/render_artifact.py` para
envolver assets SVG/PNG ya renderizados. Los nuevos artifacts `flow`,
`process`, `architecture` y `pipeline` usan el renderer nativo descrito en
[Native Visual Artifact Engine V1](native-visual-artifacts.md). Mermaid,
Graphviz y Matplotlib se mantienen para exportación y los tipos que aún no
tienen renderer nativo.

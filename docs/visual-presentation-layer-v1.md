# Presentación de assets estáticos

Este presenter histórico sigue disponible en `scripts/render_artifact.py` para
envolver assets SVG/PNG ya renderizados. Los nuevos artifacts `flow`,
`process`, `architecture` y `pipeline` usan el renderer nativo descrito en
[Native Visual Artifact Engine V1](native-visual-artifacts.md). Mermaid,
Graphviz y Matplotlib se mantienen para exportación y los tipos que aún no
tienen renderer nativo.

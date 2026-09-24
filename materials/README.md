# Materiales académicos locales

Guarda los originales en una estructura por materia y tipo de material, por
ejemplo:

```text
materials/
├── fisica/
│   ├── books/
│   ├── guides/
│   ├── exams/
│   └── notes/
├── algoritmos/
├── paradigmas/
└── data-engineering/
```

Estos nombres son solo una sugerencia; no están codificados en el programa.
Mantén los archivos originales inmutables. No publiques en un repositorio
público materiales protegidos por copyright ni documentos académicos privados.

El Source Engine indexa únicamente archivos bajo `materials/` que estén
registrados en SQLite. La base conserva metadata y texto extraído por página;
no copia el PDF completo.

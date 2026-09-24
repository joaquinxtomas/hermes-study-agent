"""Render basic numeric plots using optional Matplotlib."""

import math

extension = ".png"


def _series(request):
    data = request.data
    if request.type == "function":
        series = [{"label": data.get("expression", request.title), "x": data.get("x"), "y": data.get("y")}]
    else:
        series = data.get("series")
    if not isinstance(series, list) or not series:
        raise ValueError("Se requiere una lista data.series con x e y numéricos.")

    valid = []
    for item in series:
        if not isinstance(item, dict) or not isinstance(item.get("x"), list) or not isinstance(item.get("y"), list):
            raise ValueError("Cada serie debe incluir listas x e y.")
        if not item["x"] or len(item["x"]) != len(item["y"]) or len(item["x"]) > 5000:
            raise ValueError("Cada serie debe tener entre 1 y 5000 pares x/y.")
        try:
            x, y = [float(v) for v in item["x"]], [float(v) for v in item["y"]]
        except (ValueError, TypeError) as error:
            raise ValueError("Los valores de las series deben ser numéricos.") from error
        if not all(map(math.isfinite, (*x, *y))):
            raise ValueError("Los valores de las series deben ser finitos.")
        valid.append((x, y, item.get("label")))
    return valid


def render(request, path):
    series = _series(request)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("Matplotlib no está instalado; instalalo para crear artifacts PNG de gráficos.") from error

    fig, axis = plt.subplots()
    try:
        for x, y, label in series:
            axis.plot(x, y, label=label)
        axis.set_title(request.title)
        if any(label for _, _, label in series):
            axis.legend()
        fig.tight_layout()
        fig.savefig(path, format="png")
    finally:
        plt.close(fig)

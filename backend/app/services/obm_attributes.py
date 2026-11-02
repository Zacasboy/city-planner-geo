"""Interpretação dos atributos do OpenBuildingMap (taxonomia GEM v2.0).

Os formatos abaixo (``H:3``, ``HHT:12.5``, ``HBET:3,5``, ``HAPP:4``, ``RES3``) vêm da
descrição dos dados do OBM e do artigo; valores que não reconhecemos são tratados como
desconhecidos em vez de adivinhados.
"""

METERS_PER_FLOOR = 3.0

HEIGHT_FLOORS_CODES = ("H", "HAPP")
HEIGHT_RANGE_CODE = "HBET"
HEIGHT_METERS_CODE = "HHT"
TOKEN_SEPARATOR = "+"  # noqa: S105
RANGE_SEPARATORS = (",", "-")

OCCUPANCY_TO_TYPE = {
    "RES": "residential",
    "COM": "commercial",
    "IND": "industrial",
}
UNKNOWN_TYPE = "other_or_unknown"


def _positive_float(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def _range_midpoint(text: str) -> float | None:
    for separator in RANGE_SEPARATORS:
        if separator in text:
            low, _, high = text.partition(separator)
            low_value, high_value = _positive_float(low), _positive_float(high)
            if low_value is not None and high_value is not None:
                return (low_value + high_value) / 2
            return None
    return _positive_float(text)


def parse_height(code: str | None) -> tuple[float, int] | None:
    """Converte o código de altura do OBM em (altura em metros, número de pisos).

    A altura em metros (``HHT``) tem prioridade; nos restantes casos a altura é
    estimada com ``METERS_PER_FLOOR`` por piso.

    Args:
        code: Texto como ``H:2``, ``HHT:99.95``, ``HBET:3,5`` ou ``H:3+HBEX:1``.

    Returns:
        ``(height_m, floors)``, ou None se o código faltar ou não for reconhecido.
    """
    if not code:
        return None
    tokens = dict(
        token.partition(":")[::2] for token in code.split(TOKEN_SEPARATOR) if ":" in token
    )
    if HEIGHT_METERS_CODE in tokens:
        meters = _positive_float(tokens[HEIGHT_METERS_CODE])
        if meters is not None:
            return meters, max(1, round(meters / METERS_PER_FLOOR))
    floors: float | None = None
    for key in HEIGHT_FLOORS_CODES:
        if key in tokens:
            floors = _positive_float(tokens[key])
            break
    if floors is None and HEIGHT_RANGE_CODE in tokens:
        floors = _range_midpoint(tokens[HEIGHT_RANGE_CODE])
    if floors is None:
        return None
    floors_count = max(1, round(floors))
    return floors_count * METERS_PER_FLOOR, floors_count


def building_type(occupancy: str | None) -> str:
    """Mapeia a ocupação GEM (``RES3``, ``COM``, ``UNK``...) para o tipo usado nas métricas."""
    prefix = (occupancy or "").strip().upper().rstrip("0123456789")
    return OCCUPANCY_TO_TYPE.get(prefix, UNKNOWN_TYPE)

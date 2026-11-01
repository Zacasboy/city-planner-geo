"""Seletor de área no mapa.

T1.9: MapSelector (desenho de polígono, validação, envio).
"""

from typing import Any

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

LISBON_CENTER = [38.7223, -9.1393]
DEFAULT_ZOOM = 12
MIN_POLYGON_POINTS = 4  # o primeiro e o último ponto coincidem


def _draw_tool() -> Draw:
    return Draw(
        export=True,
        filename="my_data",
        position="topleft",
        draw_options={
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "polygon": {
                "allowIntersection": False,
                "drawError": {"color": "#e1e100", "message": "Overlapping not allowed"},
                "shapeOptions": {"color": "#6bc2e5", "weight": 2, "opacity": 1},
            },
        },
        edit_options={"edit": False, "remove": True},
    )


def render_map_selector(key: str = "map_selector") -> dict[str, Any] | None:
    """Mostra um mapa com ferramentas de desenho de polígonos.

    Args:
        key: Chave do componente Streamlit.

    Returns:
        A geometria GeoJSON do último polígono desenhado, ou None.
    """
    folium_map = folium.Map(location=LISBON_CENTER, zoom_start=DEFAULT_ZOOM, tiles="OpenStreetMap")
    _draw_tool().add_to(folium_map)
    map_data = st_folium(folium_map, width=700, height=500, key=key)

    drawings = (map_data or {}).get("all_drawings")
    if not drawings:
        return None

    geometry: dict[str, Any] = drawings[-1]["geometry"]
    if geometry["type"] != "Polygon":
        st.info("Please draw a polygon.")
        return None
    if len(geometry["coordinates"][0]) < MIN_POLYGON_POINTS:
        st.warning("Drawn polygon is too small (less than 4 points). Please draw a larger polygon.")
        return None
    return geometry


def validate_polygon(polygon_geojson: dict[str, Any] | None) -> tuple[bool, str]:
    """Valida a geometria de um polígono GeoJSON.

    Args:
        polygon_geojson: Geometria do tipo Polygon.

    Returns:
        Um par (é_válido, mensagem_de_erro); a mensagem é vazia se for válido.
    """
    if not polygon_geojson or polygon_geojson.get("type") != "Polygon":
        return False, "Invalid polygon geometry"
    try:
        coords = polygon_geojson["coordinates"][0]
    except (KeyError, IndexError, TypeError) as e:
        return False, f"Validation error: {e}"
    if len(coords) < MIN_POLYGON_POINTS:
        return False, "Polygon must have at least 4 points"
    if coords[0] != coords[-1]:
        return False, "Polygon must be closed (first and last points must match)"
    return True, ""


def send_polygon_to_backend(polygon_geojson: dict[str, Any]) -> tuple[bool, str]:
    """Guarda o polígono na sessão (o envio real ao backend ainda não existe).

    Args:
        polygon_geojson: Geometria validada.

    Returns:
        Um par (sucesso, mensagem).
    """
    st.session_state.selected_polygon = polygon_geojson
    st.session_state.polygon_sent = True
    return True, "Polygon sent successfully (mock)"

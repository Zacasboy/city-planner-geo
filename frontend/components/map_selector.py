"""
MapSelector Component
T1.9: MapSelector (desenho de polígono, validação, envio)
"""
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import json

def render_map_selector(key="map_selector"):
    """
    Render a map with drawing tools for polygon selection.
    Returns the drawn polygon GeoJSON if a polygon is drawn, else None.
    """
    # Initialize a Folium map centered on a default location (e.g., Lisbon, Portugal)
    m = folium.Map(location=[38.7223, -9.1393], zoom_start=12, tiles="OpenStreetMap")

    # Add drawing tools
    draw = Draw(
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
                "allowIntersection": False,  # Restrict shapes to simple polygons
                "drawError": {
                    "color": "#e1e100",
                    "message": "Overlapping not allowed"
                },
                "shapeOptions": {
                    "color": "#6bc2e5",
                    "weight": 2,
                    "opacity": 1
                }
            },
            "polygon": True
        },
        edit_options={
            "edit": False,  # Disable editing of existing features
            "remove": True  # Allow removing drawn features
        }
    )
    draw.add_to(m)

    # Render the map and get the returned data (includes drawn objects)
    map_data = st_folium(m, width=700, height=500, key=key)

    # Process the returned data to extract the drawn polygon
    if map_data and map_data.get("all_drawings"):
        drawings = map_data["all_drawings"]
        if len(drawings) > 0:
            # Assume the last drawn polygon is the one we want
            # We'll take the first drawing if multiple, but we could allow multiple and validate
            # For simplicity, we take the first polygon
            last_drawing = drawings[-1]
            if last_drawing["geometry"]["type"] == "Polygon":
                # Validate the polygon (e.g., check area > 0)
                # We can compute area using geopy or shapely, but for simplicity we'll just check that it has coordinates
                coords = last_drawing["geometry"]["coordinates"][0]
                if len(coords) >= 4:  # Polygon needs at least 4 points (first==last)
                    # Calculate approximate area to ensure it's not degenerate
                    # We'll skip area calculation for simplicity, but we can add if needed
                    # For now, we'll consider it valid if it has at least 4 points
                    return last_drawing["geometry"]
                else:
                    st.warning("Drawn polygon is too small (less than 4 points). Please draw a larger polygon.")
                    return None
            else:
                st.info("Please draw a polygon.")
                return None
        else:
            return None
    else:
        return None

def validate_polygon(polygon_geojson):
    """
    Validate the polygon GeoJSON.
    Returns True if valid, False otherwise.
    Additionally, returns an error message if invalid.
    """
    try:
        if not polygon_geojson or polygon_geojson.get("type") != "Polygon":
            return False, "Invalid polygon geometry"
        coords = polygon_geojson["coordinates"][0]
        if len(coords) < 4:
            return False, "Polygon must have at least 4 points"
        # Check if first and last coordinates are the same (closed polygon)
        if coords[0] != coords[-1]:
            return False, "Polygon must be closed (first and last points must match)"
        # Optional: check for self-intersection (requires shapely)
        # We'll skip for simplicity
        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def send_polygon_to_backend(polygon_geojson):
    """
    Send the polygon to the backend.
    For now, we'll mock this by storing in session state and showing a success message.
    In the future, this would make an HTTP POST request to the backend.
    """
    try:
        # Mock sending: store in session state
        st.session_state.selected_polygon = polygon_geojson
        st.session_state.polygon_sent = True
        return True, "Polygon sent successfully (mock)"
    except Exception as e:
        return False, f"Failed to send polygon: {str(e)}"
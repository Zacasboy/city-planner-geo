"""
Geo Validation Page
T1.9: MapSelector (desenho de polígono, validação, envio)
"""
import streamlit as st
from components.map_selector import render_map_selector, validate_polygon, send_polygon_to_backend
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

st.title("🌍 Geo Validation - Area Selection")

st.write("Draw a polygon on the map to select an area for analysis.")

# Render the map selector
polygon_geojson = render_map_selector(key="geo_map")

if polygon_geojson:
    st.success("Polygon drawn!")
    # Validate the polygon
    is_valid, error_msg = validate_polygon(polygon_geojson)
    if is_valid:
        st.success("Polygon is valid.")
        # Show polygon details (optional)
        with st.expander("View Polygon Coordinates"):
            st.json(polygon_geojson)
        # Button to send polygon to backend
        if st.button("Send Area for Analysis", type="primary"):
            success, msg = send_polygon_to_backend(polygon_geojson)
            if success:
                st.success(msg)
                # Optionally, clear the drawing after sending? We'll keep it for now.
            else:
                st.error(msg)
    else:
        st.error(f"Invalid polygon: {error_msg}")
else:
    st.info("Please draw a polygon on the map to select an area.")

# Render sidebar and disclaimer banner
render_sidebar()
render_disclaimer_banner()
"""
Tests for geo service.
"""

from backend.app.services.geo_service import (
    GeoService,
    convert_coordinates,
    tm06_to_wgs84,
    validate_coordinates,
    validate_geo_point,
    wgs84_to_tm06,
)


def test_geo_service_import():
    """Test that the geo service can be imported."""
    assert GeoService is not None
    assert validate_coordinates is not None
    assert convert_coordinates is not None
    assert wgs84_to_tm06 is not None
    assert tm06_to_wgs84 is not None
    assert validate_geo_point is not None


def test_geo_service_init():
    """Test geo service initialization."""
    service = GeoService()
    assert service is not None


def test_validate_coordinates():
    """Test coordinate validation."""
    # Outside the supported coverage (Portugal) even if valid WGS84
    assert validate_coordinates(-75.0, 40.0) == False
    assert validate_coordinates(0.0, 0.0) == False

    # Invalid coordinates
    assert validate_coordinates(-181.0, 0.0) == False  # Too far west
    assert validate_coordinates(181.0, 0.0) == False  # Too far east
    assert validate_coordinates(0.0, -91.0) == False  # Too far south
    assert validate_coordinates(0.0, 91.0) == False  # Too far north

    # Portugal region validation (approximate)
    # These should be valid (within Portugal bounds)
    assert validate_coordinates(-8.0, 39.0) == True
    assert validate_coordinates(-6.0, 42.0) == True

    # These should be invalid (outside Portugal bounds)
    assert validate_coordinates(-11.0, 40.0) == False  # Too far west
    assert validate_coordinates(-5.0, 40.0) == False  # Too far east
    assert validate_coordinates(-7.0, 35.0) == False  # Too far south
    assert validate_coordinates(-7.0, 45.0) == False  # Too far north


def test_convert_coordinates():
    """Test coordinate conversion."""
    # Test WGS84 to TM06 conversion
    lng, lat = -8.0, 38.0  # Some point in Portugal
    easting, northing = convert_coordinates(lng, lat, 4326, 3763)

    # Should return reasonable values for Portugal
    # Portugal TM06 coordinates are roughly:
    # Easting: 0 to 300 km
    # Northing: 4,000,000 to 4,800,000 m
    assert isinstance(easting, float)
    assert isinstance(northing, float)
    assert easting > 0
    assert -300000 < northing < 0  # PT-TM06 northing is relative to 39.67N, so negative at 38N

    # Test round-trip conversion
    lng2, lat2 = convert_coordinates(easting, northing, 3763, 4326)
    assert abs(lng2 - lng) < 0.001  # Should be close to original
    assert abs(lat2 - lat) < 0.001  # Should be close to original


def test_wgs84_to_tm06():
    """Test WGS84 to TM06 conversion functions."""
    lng, lat = -8.0, 38.0
    easting, northing = wgs84_to_tm06(lng, lat)

    # Should return reasonable values
    assert isinstance(easting, float)
    assert isinstance(northing, float)
    assert easting > 0
    assert -300000 < northing < 0  # PT-TM06 northing is relative to 39.67N, so negative at 38N

    # Test round-trip
    lng2, lat2 = tm06_to_wgs84(easting, northing)
    assert abs(lng2 - lng) < 0.001
    assert abs(lat2 - lat) < 0.001


def test_tm06_to_wgs84():
    """Test TM06 to WGS84 conversion functions."""
    easting, northing = 20000.0, -100000.0  # Near the PT-TM06 origin (central Portugal)
    lng, lat = tm06_to_wgs84(easting, northing)

    # Should return reasonable WGS84 coordinates for Portugal
    assert isinstance(lng, float)
    assert isinstance(lat, float)
    assert -10.0 < lng < -6.0  # Portugal longitude range
    assert 36.0 < lat < 42.0  # Portugal latitude range

    # Test round-trip
    easting2, northing2 = wgs84_to_tm06(lng, lat)
    assert abs(easting2 - easting) < 1.0
    assert abs(northing2 - northing) < 1.0


def test_validate_geo_point():
    """Test the validate_geo_point endpoint function."""
    # Valid point
    result = validate_geo_point(-8.0, 38.0)
    assert result["valid"] == True
    assert "coordinates" in result
    assert result["coordinates"]["lng"] == -8.0
    assert result["coordinates"]["lat"] == 38.0
    assert result["message"] == "Coordinates are valid"
    assert "converted_coordinates" in result

    # Invalid point
    result = validate_geo_point(-11.0, 38.0)  # Too far west
    assert result["valid"] == False
    assert "coordinates" in result
    assert result["coordinates"]["lng"] == -11.0
    assert result["coordinates"]["lat"] == 38.0
    assert result["message"] == "Coordinates are invalid"
    # May or may not have converted_coordinates depending on implementation


def test_geo_service_class_methods():
    """Test the GeoService class methods directly."""
    service = GeoService()

    # Test validate_coordinates method
    assert service.validate_coordinates(-8.0, 38.0) == True
    assert service.validate_coordinates(-11.0, 38.0) == False

    # Test convert_coordinates method
    lng, lat = -8.0, 38.0
    easting, northing = service.convert_coordinates(lng, lat, 4326, 3763)
    assert isinstance(easting, float)
    assert isinstance(northing, float)

    # Test wgs84_to_tm06 method
    easting, northing = service.wgs84_to_tm06(-8.0, 38.0)
    assert isinstance(easting, float)
    assert isinstance(northing, float)

    # Test tm06_to_wgs84 method
    lng, lat = service.tm06_to_wgs84(150000.0, 4400000.0)
    assert isinstance(lng, float)
    assert isinstance(lat, float)

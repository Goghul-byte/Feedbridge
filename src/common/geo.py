from math import radians, sin, cos, sqrt, atan2

EARTH_RADIUS_KM = 6371


def distance_km(lat1, lng1, lat2, lng2):
    # standard haversine formula - straight-line distance between two GPS points
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    d_lat = lat2 - lat1
    d_lng = lng2 - lng1
    a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def distance_tier(km):
    # maps a distance to the PDF's Section 3.3 tiers
    if km <= 3:
        return 1
    elif km <= 7:
        return 2
    elif km <= 15:
        return 3
    return None  # outside all tiers - not eligible

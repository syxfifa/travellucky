"""AMap-only map dispatch; preserve the existing caller interface."""
def get_map_provider():
    return "amap"

def geocode_unified(address, city, *, address_zh="", address_en=""):
    from .xhs_service import _geocode_amap_raw
    return _geocode_amap_raw(address_zh or address, city)

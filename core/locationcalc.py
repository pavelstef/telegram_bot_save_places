""" A module for calculating the bounding area corners
Math is better than external services API
https://en.wikipedia.org/wiki/Circle_of_latitude
"""
from math import cos, radians

import logging


LOGGER = logging.getLogger('locationcalc.py')

R_EARTH = 6_371_000  # Earth radius in meters.

def get_area_coord(lat: str, long: str, distance: int) -> tuple:
    """ Function for calculating the bounding area corners coordinates """
    LOGGER.debug(msg='Location calculation is using.')
    lat = float(lat)
    long = float(long)
    lat_meters_in_degree = round(40_000 / 360 * 1000)
    long_meters_in_degree = abs(
        round(lat_meters_in_degree * cos(radians(lat)))
    )
    d_lat = round((distance / lat_meters_in_degree), 6)
    d_long = round((distance / long_meters_in_degree), 6)
    area = (round((lat - d_lat), 6), round((long - d_long), 6),
            round((lat + d_lat), 6), round((long + d_long), 6))
    LOGGER.debug(msg='Location area was calculated.')
    return area

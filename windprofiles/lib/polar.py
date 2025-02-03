import numpy as np
import pandas as pd
from numbers import Number

def wind_components(speed, direction, degrees: bool = True):
    """
    Given a wind speed and direction in degrees CW of N,
        return u, v (east, north) Cartesian components of wind.
    Apply generally to vectors.
    Can be used with numerical data types or pd.Series.
    """
    direction_rad = np.deg2rad(direction) if degrees else direction
    u = speed * np.sin(direction_rad)
    v = speed * np.cos(direction_rad)
    if isinstance(speed, Number):
        if speed == 0:
            u = 0.
            v = 0.
    elif type(speed) == pd.Series:
        u.loc[speed == 0] = 0.
        v.loc[speed == 0] = 0.
    else:
        raise(f'windprofiles.lib.polar.wind_components - unknown speed array type {type(speed)}')
    return u, v

def polar_wind(u, v, degrees: bool = True):
    """
    Given u, v (east, north) Cartesian components of wind,
        return wind speed and direction in degrees CW of N.
    """
    speed = np.sqrt(u*u+v*v)
    direction = np.rad2deg(np.arctan2(u, v)) % 360 if degrees else np.arctan2(u, v) % 2*np.pi
    
    return speed, direction

def polar_average(magnitudes, directions, degrees: bool = True):
    """
    Computes true vector average of vectors provided in polar form.
    """
    if (type(magnitudes) not in [int, float]) and (len(magnitudes) != len(directions)):
        raise(f"lib.polar.polar_average: mismatched lengths of magnitudes/directions ({len(magnitudes)/len(directions)})")
    
    directions_rad = np.deg2rad(directions) if degrees else directions

    xs = magnitudes * np.sin(directions_rad) # the polar_wind function uses this swapped convention, so as we are calling it here, we must also use that convention for consistency.
    ys = magnitudes * np.cos(directions_rad)
    
    xavg = np.mean(xs)
    yavg = np.mean(ys)

    return polar_wind(xavg, yavg, degrees = degrees)

def unit_average_direction(directions, degrees: bool = True):
    """
    Computes unit vector average of directions.
    """
    return polar_average(magnitudes = 1, directions = directions, degrees = degrees)[1]

def angular_distance(theta, phi, degrees: bool = True):
    """
    Given two numerical angles theta and phi, computes
    the angular distance (minimal angle) between them
    """
    mod = 360 if degrees else 2*np.pi
    d0 = (theta - phi) % mod
    return min(mod-d0, d0)

def series_angular_distance(theta, phi, degrees: bool = True):
    """
    Extension of angular_distance to pd.Series and dimension-1 np.Array
    """
    mod = 360 if degrees else 2*np.pi    
    d0 = (theta - phi) % mod
    return d0.apply(lambda d : min(mod-d, d))

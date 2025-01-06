import numpy as np
from windprofiles.lib.polar import wind_components
# import pandas as pd

STANDARD_GRAVITY = 9.80665 # standard gravitational parameter g in m/s^2
REFERENCE_PRESSURE = 100. # reference pressure in kPa
WATER_AIR_MWR = 0.622 # water:air molecular weight ratio
R_CP = 0.286 # gas constant of air divided by specific heat capacity at constant pressure 

def saturation_vapor_pressure(temperature, method = 'tetens'):
    """
    Saturation vapor pressure in kPa.
    Assumes temperature is in K.
    Default (and currently only) method is Tetens' approximation.
    """
    if method.lower() == 'tetens':
        return 0.6113 * np.exp(17.2694 * (temperature - 273.15) / (temperature - 35.86))
    else:
        raise(f'lib.atmos.saturation_vapor_pressure: Method {method} unrecognized.')

def water_air_mixing_ratio(actual_vapor_pressure, barometric_air_pressure):
    """
    Dimensionless mixing ratio of water:air given two pressures of the same units.
    """
    return WATER_AIR_MWR * actual_vapor_pressure / (barometric_air_pressure - actual_vapor_pressure)

def virtual_temperature(temperature, barometric_air_pressure):
    """
    Virtual temperature in K, from temperature in K and air pressure in kPa.
    """
    return temperature * (REFERENCE_PRESSURE / barometric_air_pressure)**R_CP

def virtual_potential_temperature(virtual_temperature, mixing_ratio, approximate = False):
    """
    Virtual potential temperature in K.
    Requires virtual temperature in K and mixing ratio (dimensionless).
    If `approximate`, uses a first order approximation of the exact formula
        which is valid within ~1% for mixing ratios between roughly 0.00-0.20,
        but there isn't much reason to use it.
    """
    if approximate:
        return virtual_temperature * (1 + 0.61 * mixing_ratio)
    return  virtual_temperature * (1 + (mixing_ratio / WATER_AIR_MWR)/(1 + mixing_ratio))

def vpt_from_3(relative_humidity, barometric_air_pressure, temperature):
    """
    Full 'pipeline' to compute virtual potential temperature in K, given
        relative humidity in [0,1], air pressure in kPa, and temperature in K.
    """
    svp = saturation_vapor_pressure(temperature) # saturation vapor pressure
    avp = relative_humidity * svp # actual vapor pressure
    w = water_air_mixing_ratio(actual_vapor_pressure = avp,
                               barometric_air_pressure = barometric_air_pressure)
    vT = virtual_temperature(temperature = temperature,
                             barometric_air_pressure = barometric_air_pressure)
    vpT = virtual_potential_temperature(virtual_temperature = vT,
                                        mixing_ratio = w,
                                        approximate = False)
    return vpT

def bulk_richardson_number(vpt_lower: float, vpt_upper: float,
                           height_lower: float, height_upper: float,
                           ws_lower: float, ws_upper: float,
                           wd_lower: float, wd_upper: float, *,
                           gravity = STANDARD_GRAVITY) -> float:
    """
    Compute the bulk Richardson number Ri_bulk using data at two heights
    """
    delta_vpt = vpt_upper - vpt_lower
    delta_z = height_upper - height_lower

    u_lower, v_lower = wind_components(ws_lower, wd_lower)
    u_upper, v_upper = wind_components(ws_upper, wd_upper)

    delta_u = u_upper - u_lower
    delta_v = v_upper - v_lower
    
    shear_term = delta_u * delta_u + delta_v * delta_v

    if shear_term == 0:
        return np.nan
    
    vpt_avg = (vpt_upper + vpt_lower) / 2

    ri = (gravity * delta_vpt * delta_z
          / (vpt_avg * shear_term))

    return ri
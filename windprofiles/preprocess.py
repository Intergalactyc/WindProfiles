# preprocess.py
# Unit conversion, merging booms at a common height, initial QC

import numpy as np
import pandas as pd
import windprofiles.lib.polar as polar
import windprofiles.lib.atmos as atmos
import warnings
from datetime import timedelta

# DO NOT CHANGE STANDARDS WITHOUT ALL CORRESPONDING UPDATES
_standards = {
    'p' : 'kPa', # pressure
    't' : 'K', # temperature
    'rh' : 'decimal', # relative humidity
    'ws' : 'm/s', # wind speed
    'wd' : ('degrees', 'N', 'CW'), # wind direction [angle measure, zero point, orientation]
}

def get_standards():
    return _standards

def print_standards():
    print(_standards)

def _convert_pressure(series, from_unit, gravity = atmos.STANDARD_GRAVITY):
    """
    Conversion of pressure units
    If input has format "{unit}_{number}asl", interpreted
        as sea-level pressure and converted to pressure
        at height of <number> meters
    """
    if _standards['p'] != 'kPa':
        raise Exception(f'preprocess._convert_pressure: Standardized pressure changed from kPa to {_standards["p"]} unexpectedly')
    if '_' in from_unit:
        from_unit, masl = from_unit.split('_')
        meters_asl = float(masl[:-3])
        series = atmos.pressure_above_msl(series, meters_asl, gravity = gravity)
    match from_unit:
        case 'kPa':
            return series
        case 'mmHg':
            return series * 0.13332239
        case 'inHg':
            return series * 3.38639
        case 'mBar':
            return series / 10.
        case _:
            raise Exception(f'preprocess._convert_pressure: Unrecognized pressure unit {from_unit}')
        
def _convert_temperature(series, from_unit):
    """
    Conversion of temperature units
    """
    if _standards['t'] != 'K':
        raise Exception(f'preprocess._convert_temperature: Standardized temperature changed from K to {_standards["t"]} unexpectedly')
    match from_unit:
        case 'K':
            return series
        case 'C':
            return series + 273.15
        case 'F':
            return (series - 32) * (5/9) + 273.15
        case _:
            raise Exception(f'preprocess._convert_temperature: Unrecognized temperature unit {from_unit}')

def _convert_humidity(series, from_unit):
    """
    Relative humidity conversions.
    Does not account for other types of humidity - 
        just for switching between percent [%] (0-100)
        and decimal (0-1) scales
    """
    if _standards['rh'] != 'decimal':
        raise Exception(f'preprocess._convert_humidity: Standardized relative humidity changed from decimal to {_standards["rh"]} unexpectedly')
    match from_unit:
        case 'decimal':
            return series
        case '.':
            return series
        case '%':
            return series / 100.
        case 'percent':
            return series / 100.
        case _:
            raise Exception(f'preprocess._convert_humidity: Unrecognized humidity unit {from_unit}')

def _convert_speed(series, from_unit):
    """
    Conversion of wind speed units
    """
    if _standards['ws'] != 'm/s':
        raise Exception(f'preprocess._convert_speed: Standardized wind speed changed from m/s to {_standards["ws"]} unexpectedly')
    match from_unit:
        case 'm/s':
            return series
        case 'mph':
            return series / 2.23694
        case 'mi/hr':
            return series / 2.23694
        case 'mi/h':
            return series / 2.23694
        case _:
            raise Exception(f'preprocess._convert_speed: Unrecognized wind speed unit {from_unit}')

def _convert_direction(series, from_unit):
    """
    Conversion of wind direction
    """
    if _standards['wd'] != ('degrees', 'N', 'CW'):
        raise Exception(f'preprocess._convert_direction: Standardized wind speed changed from degrees CW of N to {_standards["wd"][0]} {_standards["wd"][2]} of {_standards["wd"][1]} unexpectedly')
    measure, zero, orient = from_unit
    
    # Convert measure to degrees (possibly from radians)
    if measure in ['rad', 'radians']:
        series = np.rad2deg(series)
    elif measure not in ['deg', 'degrees']:
        raise Exception(f'preprocess._convert_direction: Unrecognized angle measure {measure}')
    
    # Convert orientation to clockwise (possibly from counterclockwise)
    if orient.lower() in ['ccw', 'counterclockwise']:
        series = (-series) % 360
    elif orient.lower() not in ['cw', 'clockwise']:
        raise Exception(f'preprocess._convert_direction: Unrecognized angle orientation {orient}')
    
    # Align zero point to north
    if type(zero) is str:
        # From cardinal direction
        match zero.lower():
            case 'n':
                return series
            case 'w':
                return (series - 90) % 360
            case 's':
                return (series - 180) % 360
            case 'e':
                return (series - 270) % 360
    elif type(zero) in [int, float]:
        # From degrees offset
        return (series - zero) % 360
    else:
        raise Exception(f'preprocess._convert_direction: Unrecognized zero type {type(zero)} for {zero}')

def convert_dataframe_units(df, from_units, gravity = atmos.STANDARD_GRAVITY, silent = False):
    """
    Public function for converting units for all 
    (commonly formatted) columns in dataframe based
    on a dictionary of units, formatted in the same
    way as the _standards (use get_standards() or
    print_standards() to view)
    """

    result = df.copy(deep = True)

    conversions_by_type = {
        'p' : _convert_pressure,
        't' : _convert_temperature,
        'ts' : _convert_temperature,
        'rh' : _convert_humidity,
        'wd' : _convert_direction,
        'ws' : _convert_speed,
        'u' : _convert_speed,
        'v' : _convert_speed,
        'w' : _convert_speed,
        'ux' : _convert_speed,
        'uy' : _convert_speed,
        'uz' : _convert_speed,
    }

    for column in result.columns:
        if '_' in column and 'time' not in column:
            column_type = column.split('_')[0]
            if column_type in conversions_by_type.keys():
                conversion = conversions_by_type[column_type]
                if column_type == 'p':
                    result[column] = conversion(series = result[column],
                                                from_unit = from_units[column_type],
                                                gravity = gravity)
                else:
                    result[column] = conversion(series = result[column],
                                                from_unit = from_units[column_type])

    if not silent:
        print('preprocess.convert_dataframe_units() - DataFrame unit conversion completed')

    return result

def correct_directions(df):
    result = df.copy()
    for col in result.columns:
        if col[:3] == 'wd_':
            b = col[3]
            ws_col = f'ws_{b}'
            if ws_col in result.columns:
                result.loc[result[ws_col] == 0, col] = pd.NA
            else:
                print(f'Could not locate column {ws_col}')
    return result

def clean_formatting(df, type = 'float32', silent = False):
    """
    At times when wind speed for a certain height
        is zero, sets the corresponding wind direction
        to NaN (np.nan).
    Also cast data (with '_', o.t. times) to `type`, default float32.
        Disable this by setting `type = None`.
    Finally, fixes duplicates and misordering.
    Assumes that dataframe formatting is already
        otherwise full consistent with guidelines.
    """
    result = df.copy(deep = True)

    for column in result.columns:
        if '_' in column and 'time' not in column:
            result[column] = result[column].astype(type)
            columntype, boomStr, *_ = column.split('_')
            if columntype == 'ws':
                dircol = f'wd_{boomStr}'
                result.loc[result[column] == 0, dircol] = np.nan

    result = result.reset_index(names = 'time').sort_values(by = 'time').set_index('time')
    result = result[~result.index.duplicated(keep = 'first')]
    
    if not silent:
        print('preprocess.clean_formatting() - completed formatting update')
    
    return result

def shadowing_merge(df,
                    speeds,
                    directions,
                    angles,
                    width = 30,
                    drop_old = True,
                    silent = False):
    """
    Merges multiple sets of data at a shared height, accounting
        for tower shadowing effects.
    `speeds` and `directions` should be the names of the columns of
        `df` containing the wind speeds and directions to combine.
    `angles` should be the center wind direction from which 
        shadowing occurs for their respective boom (data set).
    `speeds`, `directions`, and `angles` must be iterables 
        of the same length. 
    At each time, if the wind direction reported by boom `i` is
        within width/2 of its corresponding shadowing angle,
        then its data will be considered shadowed and neither its
        speed or direction will be used. Data from all booms which
        are not shadowed will be (vector) averaged to form the
        resulting wind speed and direction at that time.
    Returns two columns: merged wind speeds and merged wind directions.
    """
    if not (len(speeds) == len(directions) == len(angles)):
        raise Exception(f'preprocess.shadowing_merge: Mismatched lengths for speeds/directions/angles (given lengths {len(speeds)}/{len(directions)}/{len(angles)})')
    nBooms = len(speeds)
    radius = width / 2
    raw_deviations = [(df[dir] - ang) % 360 for dir, ang in zip(directions, angles)]
    indexer = [col.apply(lambda d : min(360 - d, d) > radius) for col in raw_deviations]
    n_shadowed = [len(indexer[i]) - indexer[i].sum() for i in range(nBooms)]
    uList = []
    vList = []
    for i in range(nBooms):
        _spd, _dir, _ang = speeds[i], directions[i], angles[i]
        raw_deviations = (df[_dir] - _ang) % 360
        corr_deviations = raw_deviations.apply(lambda d : min(360 - d, d))
        u, v = polar.wind_components(df[_spd], df[_dir])
        u.loc[corr_deviations < radius] = np.nan
        v.loc[corr_deviations < radius] = np.nan
        uList.append(u)
        vList.append(v)
    # We want the mean(np.nan...) -> np.nan behavior and expect to see it sometimes, so we'll filter the error
    warnings.filterwarnings(action='ignore', message='Mean of empty slice')
    uMeans = np.nanmean(np.stack(uList), axis = 0)
    vMeans = np.nanmean(np.stack(vList), axis = 0)
    sMeans = np.sqrt(uMeans * uMeans + vMeans * vMeans)
    dMeans = (np.rad2deg(np.arctan2(uMeans, vMeans)) + 360) % 360
    if drop_old:
        df.drop(columns = speeds + directions, inplace = True)
    if not silent:
        print('preprocess.shadowing_merge() - completed merge')
        print(f'\tNumber of data points with shadowing, by boom: {[int(n) for n in n_shadowed]}')
    return sMeans, dMeans

def remove_data(df: pd.DataFrame, periods: dict, silent: bool = False) -> pd.DataFrame:
    """
    Removes data within certain specified datetime intervals.
    Removal can be complete (specify 'ALL') or partial (specify 
        list of integer booms).
    See kcc.py's `removal_periods` for an example of proper
        format for `periods`.
    If silent == False then #s of total and partial removals
        will be printed.
    """
    result = df.reset_index(names = 'time')
    
    total_removals = 0
    partial_removals = 0
    
    for interval, which_booms in periods.items():
        
        removal_start, removal_end = interval
        indices = result.loc[result['time'].between(removal_start, removal_end, inclusive='both')].index
        
        if type(which_booms) is str and which_booms.lower() == 'all': # if all data is to be removed, just drop the full row entry
            result.drop(index = indices, inplace = True)
            total_removals += len(indices)
        elif type(which_booms) is list: # otherwise, just set data from the selected booms to NaN
            datatypes = ['p','ws','wd','t','rh']
            for b in which_booms:
                for d in datatypes:
                    selection = f'{d}_{b}'
                    if selection in result.columns:
                        result.loc[indices, selection] = np.nan
            partial_removals += len(indices)
        else:
            raise Exception('preprocess.remove_data: Unrecognized removal-height specification in given periods', periods)
    
    result.set_index('time', inplace = True)
    
    if not silent:
        print('preprocess.remove_data() - completed interval data removal')
        print(f'\tTotal removals: {total_removals}')
        print(f'\tPartial removals: {partial_removals}')
    
    return result

def rolling_outlier_removal(df: pd.DataFrame,
                            window_size_minutes: int = 30,
                            window_size_observations: int = None,
                            sigma: int = 5,
                            column_types = ['ws', 't', 'p', 'rh'],
                            silent: bool = False,
                            remove_if_any: bool = True,
                            return_elims: bool = False) -> pd.DataFrame:
    """
    Eliminate data where values from columns of types `column_types` are more than
        `sigma` (default 5) standard deviations from a rolling mean, rolling in a
        window of width `window_size_minutes` (default 30) minutes. 
    Unable to handle wind direction - don't try to apply it to 'wd'.
    """
    result = df.copy(deep = True)
    window = f'{window_size_minutes}min' if window_size_observations is None else window_size_observations
    eliminations = 0 if remove_if_any else dict()

    for column in result.columns:
        column_type = column.split('_')[0]
        if column_type in column_types:
            rolling_mean = result[column].rolling(window = window).mean()
            rolling_std = result[column].rolling(window = window).std()
            threshold = sigma * rolling_std
            outliers = np.abs(result[column] - rolling_mean) > threshold
            if remove_if_any:
                eliminations += result[outliers].shape[0]
                result = result[~outliers]
            else:
                eliminations[column] = result[outliers].shape[0]
                result.loc[outliers, column] = pd.NA
    
    if not silent:
        print('preprocess.rolling_outlier_removal() - outlier removal complete')
        if remove_if_any:
            print(f'\t{eliminations} outliers eliminated ({100*eliminations/(df.shape[0]):.4f}%)')
        else:
            print(f'Eliminations summary:\n{eliminations}')
    
    if return_elims:
        return result, eliminations
    
    return result

def resample(df: pd.DataFrame,
             all_booms: list[int],
             window_size_minutes: int,
             how: str = 'mean',
             silent: bool = False,
             drms: bool = False,
             pti: bool = False,
             turbulence_reference: int = -1) -> pd.DataFrame:
    
    to_resample = df.copy(deep = True)
    easy_cols = ['t', 'p', 'rh']
    window = f'{window_size_minutes}min'

    for b in all_booms:
        dirRad = np.deg2rad(to_resample[f'wd_{b}'])
        to_resample[f'x_{b}'], to_resample[f'y_{b}'] = polar.wind_components(to_resample[f'ws_{b}'], to_resample[f'wd_{b}'])
    
    rsmp = to_resample.resample(window)
    if how == 'mean':
        resampled = rsmp.mean()
    elif how == 'median':
        resampled = rsmp.median()
    else:
        raise Exception(f'preprocess.resample: Unrecognized resampling method {how}')
    maxs = rsmp.max()
    if pti:
        stds = rsmp.std()
    if drms: # directional RMS per height
        drms_dict = dict()
        for b in all_booms:
            drms_dict[b] = rsmp[f'wd_{b}'].agg(polar.directional_rms)
    
    before_drop = resampled.shape[0]
    resampled.dropna(axis = 0, how = 'all', inplace = True)
    dropped = before_drop - resampled.shape[0]

    for b in all_booms:
        if pti:
            # Compute pseudo-turbulence intensities 'pti_{b}' per height as (mean of wind speeds) / (mean wind speed [direct magnitude average])
                # mean wind speed used is that at height `turbulence_reference` (or at local height if turbulence_reference == -1)
            ref = b if (type(turbulence_reference) is not int or turbulence_reference < 0) else turbulence_reference
            if ref not in all_booms:
                raise Exception(f'preprocess.resample: in pseudo-TI calculation, unrecognized reference boom {ref}')
            resampled[f'pti_{b}'] = stds[f'ws_{b}'] / resampled[f'ws_{ref}'] # divide by raw average wind speed, before vector averaging
        
        if drms:
            # Get directional RMS that was computed above
            resampled[f'drms_{b}'] = drms_dict[b]
        
        # Get maximum wind speed in each interval
        resampled[f'maxws_{b}'] = maxs[f'ws_{b}']

        # Find vector averages
        resampled[f'ws_{b}'] = np.sqrt(resampled[f'x_{b}']**2+resampled[f'y_{b}']**2)
        resampled[f'wd_{b}'] = (np.rad2deg(np.arctan2(resampled[f'x_{b}'], resampled[f'y_{b}'])) + 360) % 360
        resampled.drop(columns=[f'x_{b}',f'y_{b}'], inplace=True)

    if not silent:
        print(f'preprocess.resample() - resampling into {window_size_minutes} minute intervals ({how}s) complete')
        print(f'\tSize reduced from {to_resample.shape[0]} to {before_drop}, before removals')
        print(f'\t{dropped} removals of NaN rows ({100*dropped/before_drop:.4f}%), resulting in {resampled.shape[0]} final data points')
    
    return resampled

def convert_timezone(df: pd.DataFrame, source_timezone: str, target_timezone: str):
    result = df.copy()
    result.index = df.index.tz_localize(source_timezone).tz_convert(target_timezone)
    return result

def determine_weather(df: pd.DataFrame, storm_events: pd.DataFrame, weather_data: pd.DataFrame, trace_float: float = 0.) -> pd.DataFrame:
    HOUR = timedelta(hours = 1)
    # mark times inclusively between storm event start and end times as either hail = True or storm = True
    result = df.copy()
    all_storms = list(storm_events.apply(lambda row : (row['BEGIN_DATE_TIME'], row['END_DATE_TIME'], row['EVENT_TYPE']), axis = 1))
    result['hail'] = False
    result['storm'] = False
    result['heavy_rain'] = False
    result['light_rain'] = False
    for start, end, storm_type in all_storms:
        if start == end:
            start -= 1.5 * HOUR
            end += 1.5 * HOUR
        if storm_type == 'Hail':
            result.loc[(result.index >= start) & (result.index <= end), 'hail'] = True
        elif storm_type.lower() == 'Flash Flood':
            result.loc[(result.index >= start) & (result.index <= end), 'heavy_rain'] = True
        else:
            result.loc[(result.index >= start) & (result.index <= end), 'storm'] = True
    # mark times where precipitation is above trace value as rain = True
        # for each time stamp in the CID data where it is raining, mark df time stamps between the previous timestamp and now as raining
    for index, row in weather_data.iterrows(): # I know this is slower than optimal but there isn't THAT much data and it works fine
        precip = row['precip']
        if precip > trace_float and index > 0: # not really handling the case where index is 0 but we know it's not raining at the start anyway
            start = row['time'] - HOUR
            end = row['time']
            if precip < 5:
                result.loc[(result.index >= start) & (result.index <= end), 'light_rain'] = True
            else:
                result.loc[(result.index >= start) & (result.index <= end), 'light_rain'] = False
                result.loc[(result.index >= start) & (result.index <= end), 'heavy_rain'] = True
    return result

def flagged_removal(df: pd.DataFrame, flags: str|list[str], silent: bool = False, drop_cols = True):
    """
    For each column listed in `flags`, remove rows from `df` where that column is True
    """
    if not silent:
        print(f'preprocess.flagged_removal() - beginning removals based on column(s) {flags}')

    original_size = len(df)
    result = df.copy()

    if type(flags) is str:
        flags = [flags]

    for flag in flags:
        print(result[flag])
        result.drop(result[result[flag] == True].index, inplace = True)

    result.drop(columns = flags, inplace = True)

    if not silent:
        removals = original_size - len(result)
        print(f'\tRemovals complete ({removals} rows dropped, {len(result)} rows remain)')

    return result

def rename_headers(df, mapper, drop_nones: bool = True, drop_others: bool = True, drop_empty: bool = True):
    result = df.copy()
    for col in result.columns:
        col_type, height_str = col.split('_')
        if col_type in mapper:
            if mapper[col_type] is not None:
                new = f'{mapper[col_type]}_{height_str}'
                result.rename(columns = {col : new}, inplace = True)
            elif drop_nones:
                result.drop(columns = [col], inplace = True)
        elif drop_others:
            result.drop(columns = [col], inplace = True)
    if drop_empty:
        result.dropna(axis = 1, how = 'all', inplace = True)
    return result

def strip_missing_data(df: pd.DataFrame, necessary: list[int], minimum: int = 4, silent: bool = False):
    """
    Remove rows where there are fewer than `minimum` wind speed columns or where
        wind speeds are missing at any of the `necessary` booms
    """
    result = df.copy()

    if not silent:
        print('preprocess.strip_missing_data() - beginning removals')

    cols = result.columns

    necessarys = [f'ws_{b}' for b in necessary]
    ws_cols = []
    for col in cols:
        if 'ws_' in col:
           ws_cols.append(col) 

    removed = 0
    iterable = result.iterrows()
    for index, row in iterable:
        drop = False
        for necessary in necessarys:
            if pd.isna(row[necessary]):
                drop = True
                break
        count = 0
        for col in ws_cols:
            if not pd.isna(row[col]):
                count += 1
        if drop or count < minimum:
            result.drop(index = index, inplace = True)
            removed += 1

    if not silent:
        print(f'\tRemovals complete ({removed} rows dropped)')

    return result

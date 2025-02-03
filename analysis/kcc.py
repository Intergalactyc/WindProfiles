import pandas as pd
import numpy as np
import windprofiles.preprocess as preprocess
import windprofiles.compute as compute
import windprofiles.storms as storms
from windprofiles.classify import TerrainClassifier, StabilityClassifier, CoordinateRegion
import finalplots
import json
import sys
import os
from kcc_definitions import *

PARENTDIR = 'C:/Users/22wal/OneDrive/GLWind' # If you are not Elliott and this is not the path for you then pass argument -p followed by the correct path when running!

RULES = {
    'shadowing_width' : 30,
    'storm_radius_km' : 25,
    'storm_removal' : False,
    'default_removals' : True,
    'outlier_window_minutes' : 30,
    'outlier_sigma' : 5,
    'resampling_window_minutes' : 10,
    'stability_classes' : 4,
    'terrain_window_width_degrees' : 60,
    'terrain_wind_height_meters' : 10
}

def load_data(data_directory: str, outer_merges: bool = False):
    print('START DATA LOADING')
    # Read in the data from the booms and set column names to common format
    boom1 = pd.read_csv(f'{data_directory}/Boom1OneMin.csv').rename(columns={'TimeStamp' : 'time',
                                                        'MeanVelocity (m/s)' : 'ws_6m',
                                                        'MeanDirection' : 'wd_6m',
                                                        'MeanTemperature (C )' : 't_6m',
                                                        'MeanPressure (mmHg)' : 'p_6m'})

    boom2 = pd.read_csv(f'{data_directory}/Boom2OneMin.csv').rename(columns={'TIMESTAMP' : 'time',
                                                        'MeanVelocity (m/s)' : 'ws_10m',
                                                        'MeanDirection' : 'wd_10m',
                                                        'MeanTemperature (C )' : 't_10m',
                                                        'MeanRH (%)' : 'rh_10m'})

    boom3 = pd.read_csv(f'{data_directory}/Boom3OneMin.csv').rename(columns={'TIMESTAMP' : 'time',
                                                        'MeanVelocity (m/s)' : 'ws_20m',
                                                        'MeanDirection' : 'wd_20m'})

    boom4 = pd.read_csv(f'{data_directory}/Boom4OneMin.csv').rename(columns={'TimeStamp' : 'time',
                                                        'MeanVelocity' : 'ws_32m',
                                                        'MeanDirection' : 'wd_32m',
                                                        'MeanTemperature' : 't_32m',
                                                        'MeanRH' : 'rh_32m'})

    boom5 = pd.read_csv(f'{data_directory}/Boom5OneMin.csv').rename(columns={'TimeStamp' : 'time',
                                                        'MeanVelocity' : 'ws_80m',
                                                        'MeanDirection' : 'wd_80m',
                                                        'MeanTemperature' : 't_80m',
                                                        'MeanRH' : 'rh_80m'})

    boom6 = pd.read_csv(f'{data_directory}/Boom6OneMin.csv').rename(columns={'TIMESTAMP' : 'time',
                                                        'MeanVelocity (m/s)' : 'ws_106m1',
                                                        'Mean Direction' : 'wd_106m1',
                                                        'MeanTemperature (C )' : 't_106m',
                                                        'MeanRH (%)' : 'rh_106m'})

    boom7 = pd.read_csv(f'{data_directory}/Boom7OneMin.csv').rename(columns={'TimeStamp' : 'time',
                                                        'MeanVelocity (m/s)' : 'ws_106m2',
                                                        'MeanDirection' : 'wd_106m2',
                                                        'MeanPressure (mmHg)' : 'p_106m'})

    # Merge the data together into one pd.DataFrame
    boom_list = [boom1,boom2,boom3,boom4,boom5,boom6,boom7]
    for boom in boom_list:
        boom['time'] = pd.to_datetime(boom['time'])
        boom.set_index('time', inplace=True)
    df = (boom1.merge(boom2, on='time', how='outer' if outer_merges else 'inner')
            .merge(boom6, on='time', how='outer' if outer_merges else 'inner')
            .merge(boom7, on='time', how='outer' if outer_merges else 'inner')
            .merge(boom3, on='time',how='outer' if outer_merges else 'left')
            .merge(boom4, on='time', how='outer' if outer_merges else 'left')
            .merge(boom5, on='time', how='outer' if outer_merges else 'left')
            )

    print("END DATA LOADING")

    return df.reset_index()
    
def perform_preprocessing(df,
                          shadowing_width,
                          removal_periods, # These will be passed in UTC so we will do the removal before converting data time to local US/Central
                          outlier_window,
                          outlier_sigma,
                          resampling_window,
                          storm_events = None,
                          weather_data = None,
                          storm_removal = False):
    print("START DATA PREPROCESSING")
    
    doWeather = not(storm_events is None or weather_data is None)

    # Automatically convert units of all columns to standards as outlined in convert.py
    df = preprocess.convert_dataframe_units(df = df, from_units = SOURCE_UNITS, gravity = LOCAL_GRAVITY)

    # Conditionally merge wind data from booms 6 and 7
    # Boom 6 (106m1, west side) is shadowed near 90 degrees (wind from east)
    # Boom 7 (106m2, east side) is shadowed near 270 degrees (wind from west)
    # Important that we do this after the conversion step, to make sure wind angles are correct
    df['ws_106m'], df['wd_106m'] = preprocess.shadowing_merge(
        df = df,
        speeds = ['ws_106m1', 'ws_106m2'],
        directions = ['wd_106m1', 'wd_106m2'],
        angles = [90, 270],
        width = shadowing_width, # Winds from within 30/2=15 degrees of tower are discarded
        drop_old = True # Discard the 106m1 and 106m2 columns afterwards
    )

    # Final common formatting changes:
    # ws = 0 --> wd = pd.nan; types --> float32; sorting & duplication fixes
    df = preprocess.clean_formatting(df = df, type = 'float32')

    # Remove data according to REMOVAL_PERIODS
    if removal_periods is not None:
        df = preprocess.remove_data(df = df, periods = removal_periods)

    # Convert time index from UTC to local time
    df = preprocess.convert_timezone(df = df,
                                    source_timezone = SOURCE_TIMEZONE,
                                    target_timezone = LOCAL_TIMEZONE)

    # Rolling outlier removal
    df = preprocess.rolling_outlier_removal(df = df,
                                            window_size_minutes = outlier_window,
                                            sigma = outlier_sigma,
                                            column_types = ['ws', 't', 'p', 'rh'])

    # Resampling into 10 minute intervals
    df = preprocess.resample(df = df,
                            window_size_minutes = resampling_window,
                            how = 'mean',
                            all_heights = HEIGHTS,)
                            # deviations = [f'ws_{h}m' for h in HEIGHTS])

    # Remove rows where there isn't enough data (not enough columns, or missing either 10m or 106m data)
    df = preprocess.strip_missing_data(df = df,
                                    necessary = [10, 106],
                                    minimum = 3)
    
    if doWeather:
        print('Matching reported weather events...')
        # Determine where it is rainy/hailing/stormy
        df = preprocess.determine_weather(df = df,
                    storm_events = storm_events,
                    weather_data = cid_data,
                    trace_float = CID_TRACE)

        if storm_removal:
            # Remove data where it is too stormy to rely on data
            df = preprocess.flagged_removal(df = df,
                                            flags = ['hail','storm','heavy_rain'])

    print("END DATA PREPROCESSING")

    return df

def compute_values(df,
                   terrain_classifier,
                   stability_classifier):

    print("BEGIN COMPUTATIONS")

    df = compute.virtual_potential_temperatures(df = df,
                                                heights = [10, 106],
                                                substitutions = {'p_10m' : 'p_6m'})
        
    df = compute.environmental_lapse_rate(df = df,
                                          variable = 'vpt',
                                          heights = [10, 106])
    
    df = compute.bulk_richardson_number(df = df,
                                        heights = [10, 106],
                                        gravity = LOCAL_GRAVITY)
        
    df = compute.classifications(df = df,
                                 terrain_classifier = terrain_classifier,
                                 stability_classifier = stability_classifier)
    
    df = compute.power_law_fits(df = df,
                                heights = HEIGHTS,
                                columns = [None,'alpha'])
    
    df = compute.power_law_fits(df = df,
                                heights = [6, 10, 20, 32, 80],
                                columns = [None,'alpha_no106'])
    
    df = compute.power_law_fits(df = df,
                                heights = [6, 10, 20, 80, 106],
                                columns = [None,'alpha_no32'])
    
    df = compute.strip_failures(df = df,
                                subset = ['Ri_bulk','alpha'])
        
    print("END COMPUTATIONS")

    return df

def generate_plots(df: pd.DataFrame, cid: pd.DataFrame, savedir: str, summary: dict):
    finalplots.generate_plots(df = df, cid = cid, savedir = savedir, summary = summary)

def get_storm_events(start_time, end_time, radius: int|float = 25., unit: str = 'km'):
    region = CoordinateRegion(latitude = LATITUDE, longitude = LONGITUDE, radius = radius, unit = unit)
    results = []
    for filepath in STORM_FILES:
        results.append(storms.get_storms(filepath, region))
    sDf = pd.concat(results)
    # Checking sDf['CZ_TIMEZONE'] shows that all are localized to CST-6 regardless of DST
    #   To account for this in our localization we specify GMT-6
    format_string = "%d-%b-%y %H:%M:%S" # Format can't be inferred so specifying. See strftime documentation.
    sDf['BEGIN_DATE_TIME'] = pd.to_datetime(sDf['BEGIN_DATE_TIME'], format = format_string).dt.tz_localize('etc/GMT-6').dt.tz_convert(LOCAL_TIMEZONE)
    sDf['END_DATE_TIME'] = pd.to_datetime(sDf['END_DATE_TIME'], format = format_string).dt.tz_localize('etc/GMT-6').dt.tz_convert(LOCAL_TIMEZONE)
    sDf = sDf[(sDf['BEGIN_DATE_TIME'] <= end_time) & (sDf['END_DATE_TIME'] >= start_time)]
    return sDf

def get_weather_data(start_time, end_time):
    cid = pd.read_csv(CID_DATA_PATH)
    cid.drop(columns = ['station','dwpc'], inplace = True)
    cid.rename(columns = {
        'valid' : 'time',
        'tmpc' : 't_0m',
        'relh' : 'rh_0m',
        'drct' : 'wd_0m',
        'sped' : 'ws_0m',
        'mslp' : 'p_0m',
        'p01m' : 'precip'
    }, inplace=True)
    cid['time'] = pd.to_datetime(cid['time']).dt.tz_localize('UTC').dt.tz_convert(LOCAL_TIMEZONE)
    cid = preprocess.convert_dataframe_units(cid, from_units = CID_UNITS, gravity = LOCAL_GRAVITY, silent = True)
    cid = cid[(cid['time'] <= end_time) & (cid['time'] >= start_time)].reset_index(drop = True)
    return cid

def dataframe_checksum(df: pd.DataFrame, verbose: bool = False) -> int:
    result = int(pd.util.hash_pandas_object(df).sum())
    if verbose:
        print(result)
        print(f'(type: {type(result)})')
    return result

def save_results(df: pd.DataFrame, storm_events: pd.DataFrame, cid_data: pd.DataFrame, rules: dict, savedir: str):
    print(f'Saving results to directory {savedir}')

    summary = rules
    print('Computing validation checksums for summary file')
    summary['_df_chksum'] = dataframe_checksum(df)
    summary['_storm_chksum'] = dataframe_checksum(storm_events)
    summary['_cid_chksum'] = dataframe_checksum(cid_data)
    with open(f'{savedir}/summary.json', 'w') as f:
        json.dump(summary, f)
    print('Saved summary JSON')

    df.to_csv(f'{savedir}/output.csv')
    df.to_parquet(f'{savedir}/output.parquet')
    print("Saved main 'output' dataframe as CSV and Parquet")

    storm_events.to_csv(f'{savedir}/storms.csv')
    storm_events.to_parquet(f'{savedir}/storms.parquet')
    print("Saved 'storms' dataframe as CSV and Parquet")

    cid_data.to_csv(f'{savedir}/cid.csv')
    cid_data.to_parquet(f'{savedir}/cid.parquet')
    print("Saved 'cid' dataframe as CSV and Parquet")

def load_results(path: str):

    df = pd.read_parquet(f'{path}/output.parquet')
    storm_events = pd.read_parquet(f'{path}/storms.parquet')
    cid_data = pd.read_parquet(f'{path}/cid.parquet')

    with open(f'{path}/summary.json', 'r') as f:
        summary = json.load(f)

    return df, storm_events, cid_data, summary

def validate_summary(summary: dict, df: pd.DataFrame, storm_events: pd.DataFrame, cid_data: pd.DataFrame):
    sums = {
        '_df_chksum' : dataframe_checksum(df),
        '_storm_chksum' : dataframe_checksum(storm_events),
        '_cid_chksum' : dataframe_checksum(cid_data)
    }
    for name, sum in sums.items():
        if summary[name] != sum:
            print(f'* Invalid checksum {name}')
            return False
    return True

if __name__ == '__main__':
    RELOAD = False
    if len(sys.argv) > 1:
        if '-r' in sys.argv:
            RELOAD = True
        if '-p' in sys.argv:
            p_index = sys.argv.index('-p')
            if p_index == len(sys.argv) - 1:
                raise Exception('Must follow -p flag with path to parent directory (directory containing /data/), in UNIX format without any quotation marks')
            PARENTDIR = sys.argv[p_index + 1]
    
    if RELOAD:
        df = load_data(
            data_directory = f'{PARENTDIR}/data/KCC_SlowData',
            outer_merges = False,
        ) # Will return with default (not time) index, which is good for the storm/weather data

        print('Getting storm events')
        storm_events = get_storm_events(start_time = START_TIME, end_time = END_TIME, radius = RULES['storm_radius_km'], unit = 'km')

        print('Getting weather data')
        cid_data = get_weather_data(start_time = START_TIME, end_time = END_TIME)

        df.set_index('time', inplace=True) # Need time index from here on

        df = perform_preprocessing(
            df = df,
            shadowing_width = RULES['shadowing_width'], # width, in degrees, of shadowing bins
            removal_periods = {
                ('2018-03-05 13:20:00','2018-03-10 00:00:00') : 'ALL', # large maintenance gap
                ('2018-04-18 17:40:00','2018-04-19 14:20:00') : [106], # small maintenance-shaped gap
                ('2018-09-10 12:00:00','2018-09-20 12:00:00') : 'ALL' # blip at end
            } if RULES['default_removals'] else None,
            outlier_window = RULES['outlier_window_minutes'], # Duration, in minutes, of rolling outlier removal window
            outlier_sigma = RULES['outlier_sigma'], # Number of standard deviations beyond which to discard outliers in rolling removal
            resampling_window = RULES['resampling_window_minutes'], # Duration, in minutes, of resampling window
            storm_events = storm_events,
            weather_data = cid_data,
            storm_removal = RULES['storm_removal'] # discard stormy data?
        )

        # Define 3-class bulk Richardson number stability classification scheme
        if RULES['stability_classes'] == 3:
            stability_classifier = StabilityClassifier(
                parameter = 'Ri_bulk',
                classes = [
                    ('unstable', '(-inf,-0.1)'),
                    ('neutral', '[-0.1,0.1]'),
                    ('stable', '(0.1,inf)')
                ]
            )
        elif RULES['stability_classes'] == 4:
            stability_classifier = StabilityClassifier(
                parameter = 'Ri_bulk',
                classes = [
                    ('unstable', '(-inf,-0.1)'),
                    ('neutral', '[-0.1,0.1]'),
                    ('stable', '(0.1,0.25]'),
                    ('strongly stable', '(0.25,inf)')
                ]
            )
        else:
            raise Exception(f"Unrecognized number of stability classes ({RULES['stability_classes']})")

        # Define the terrain classification scheme
        terrain_classifier = TerrainClassifier(
            complexCenter = 315,
            openCenter = 135,
            radius = RULES['terrain_window_width_degrees']/2,
            inclusive = True,
            height = RULES['terrain_wind_height_meters']
        )

        df = compute_values(
            df = df,
            terrain_classifier = terrain_classifier,
            stability_classifier = stability_classifier
        )

        df.reset_index(inplace = True)

        print('Complete, saving results')

        save_results(df = df, storm_events = storm_events, cid_data = cid_data, rules = RULES, savedir = f'{PARENTDIR}/results')
        # df.to_csv(f'{PARENTDIR}/results/output.csv')
        # storm_events.to_csv(f'{PARENTDIR}/results/storms.csv')
        # cid_data.to_csv(f'{PARENTDIR}/results/cid.csv')
    else:
        print('RELOAD set to False, will use previous output.')

    print('Loading results...')

    df, storm_events, cid_data, summary = load_results(f'{PARENTDIR}/results')
    if not validate_summary(summary = summary, df = df, storm_events = storm_events, cid_data = cid_data):
        raise Exception('Failed to validate results. Please either fix files or re-run with `-r` flag in order to set RELOAD=True.')

    print('Results loaded successfully!')

    generate_plots(df = df, cid = cid_data, savedir = f'{PARENTDIR}/figs', summary = summary)

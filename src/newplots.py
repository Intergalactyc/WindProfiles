import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import cm
import numpy as np
import helper_functions as hf
import os
from sun_position_calculator import SunPositionCalculator

# Load data
df10 = pd.read_csv('../../outputs/slow/ten_minutes_labeled.csv') # 10-minute averaged data, with calculations and labeling performed by reduce.py
df10['time'] = pd.to_datetime(df10['time'])
df10['local_time'] = df10['time'].dt.tz_localize('UTC').dt.tz_convert('US/Central') # add a local time column

# List of all of the heights, in m, that data exists at
heights = [6,10,20,32,80,106]
zvals = np.linspace(0.,130.,400)

# Latitude and longitude
CRLATITUDE = 41.91 # KCC met tower latitude in degrees
CRLONGITUDE = -91.65 # Met tower longitude in degree

# Months
months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
seasons = {'Fall' : ['Sep', 'Oct', 'Nov'],
           'Winter' : ['Dec', 'Jan', 'Feb'],
           'Spring' : ['Mar', 'Apr', 'May'],
           'Summer' : ['Jun', 'Jul', 'Aug']
           }
seasonal_colors = {'Fall' : 'orange', 'Summer' : 'red', 'Spring' : 'green', 'Winter' : 'blue'}

# Terrain classes
terrain_classes = ['complex', 'open']

# How to classify stability by default
default_stability_classes = ['unstable','neutral','stable','strongly stable']
default_stability_cutoffs = ['Ri<-0.1','-0.1<Ri<0.1','0.1<Ri<0.25','Ri>0.25']
default_stability = {'stability classes' : default_stability_classes,
                     'stability cutoffs' : default_stability_cutoffs,
                     'stability scheme' : hf.stability_class,
                     'stability parameter' : 'ri',
                     'colors' : ['red', 'lime', 'royalblue', 'midnightblue'],
                     }

# Five class scheme
five_stability_classes = ['strongly unstable','unstable','neutral','stable','strongly stable']
five_stability_cutoffs = ['Ri<-0.25','-0.25<Ri<-0.1','-0.1<Ri<0.1','0.1<Ri<0.25','Ri>0.25']
def five_stability_scheme(Ri):
    if Ri < -0.25:
        return 'strongly unstable'
    if Ri < -0.1:
        return 'unstable'
    if -0.1 <= Ri < 0.1:
        return 'neutral'
    if 0.1 <= Ri < 0.25:
        return 'stable'
    return 'strongly stable'
five_stability = {'stability classes' : five_stability_classes,
                     'stability cutoffs' : five_stability_cutoffs,
                     'stability scheme' : five_stability_scheme,
                     'stability parameter' : 'ri',
                     'colors' : ['red', 'orange', 'lime', 'royalblue', 'midnightblue'],
                     }

def mean_wind_profiles_by_terrain_and_stability(
    height = 10,
    stability = default_stability
):
    stability_classes = stability['stability classes']
    stability_parameter = stability['stability parameter']
    stability_scheme = stability['stability scheme']
    colors = stability['colors']
    for tc in terrain_classes:
        df = df10[df10[f'wd_{int(height)}m'].apply(hf.terrain_class) == tc]
        plt.xlabel('Mean Velocity (m/s)')
        plt.ylabel('Height (m)')
        plt.title(f'{tc.title()} terrain wind profile')
        for color, sc in zip(colors, stability_classes):
            df_sc = df[df[stability_parameter].apply(stability_scheme) == sc]
            means = df_sc[[f'ws_{h}m' for h in heights]].mean(axis=0)
            mult, wsc = hf.power_fit(heights, means.values, both=True)
            plt.scatter(means.values, heights, label=r'{sc}: $u(z)={a:.2f}z^{{{b:.3f}}}$'.format(sc=sc.title(),a=mult,b=wsc), color = color)
            plt.plot(mult * zvals**wsc, zvals, color = color)
            print(f'{tc}, {sc[0]}: mult = {mult:.4f}, alpha = {wsc:.4f}')
        plt.legend()
        plt.show()

def mean_wind_profiles_by_stability_only(
    stability = default_stability,
):
    stability_classes = stability['stability classes']
    stability_parameter = stability['stability parameter']
    stability_scheme = stability['stability scheme']
    colors = stability['colors']
    plt.xlabel('Mean Velocity (m/s)')
    plt.ylabel('Height (m)')
    plt.title(f'Overall mean wind profiles')
    for color, sc in zip(colors, stability_classes):
        df_sc = df10[df10[stability_parameter].apply(stability_scheme) == sc]
        height_stratified = df_sc[[f'ws_{h}m' for h in heights]]
        means = height_stratified.mean(axis = 0)
        # stds = height_stratified.std(axis = 0)
        mult, wsc = hf.power_fit(heights, means.values, both=True)
        plt.scatter(means.values, heights, label=r'{sc}: $u(z)={a:.2f}z^{{{b:.3f}}}$'.format(sc=sc.title(),a=mult,b=wsc), color = color)
        # Error bar - looks very bad
        # plt.errorbar(means.values, heights, xerr = stds.values, fmt = 'o', elinewidth = 0, capthick = 1.5, capsize = 4, label=r'{sc}: $u(z)={a:.2f}z^{{{b:.3f}}}$'.format(sc=sc.title(),a=mult,b=wsc), color = color)
        plt.plot(mult * zvals**wsc, zvals, color = color)
        print(f'{sc[0]}: mult = {mult:.4f}, alpha = {wsc:.4f}')
    plt.legend()
    plt.show()

def bar_stability(
    stability = default_stability,
):
    stability_classes = stability['stability classes']
    stability_parameter = stability['stability parameter']
    stability_scheme = stability['stability scheme']
    stability_cutoffs = stability['stability cutoffs']
    colors = stability['colors']
    N = len(stability_classes)
    if len(stability_cutoffs) != N:
        raise('Mismatch in stability setup list lengths')
    # Bar chart of stability classifications
    classifications = df10[stability_parameter].apply(stability_scheme)
    stability_r_freqs = classifications.value_counts(normalize=True)
    plt.bar([f'{stability_classes[i].title()}\n({stability_cutoffs[i]})' for i in range(N)], [stability_r_freqs[sc] for sc in stability_classes], color = colors)
    #plt.bar(['Unstable\n(Ri<-0.1)','Neutral\n(-0.1<Ri<0.1)','Stable\n(0.1<Ri<0.25)','Strongly Stable\n(0.25<Ri)'],[stability_r_freqs['unstable'],stability_r_freqs['neutral'],stability_r_freqs['stable'],stability_r_freqs['strongly stable']], color=['mediumblue','deepskyblue','orange','crimson'])
    plt.ylabel('Relative Frequency')
    plt.title('Wind Data Sorted by Bulk Ri Thermal Stability Classification')
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='-', alpha=0.8)
    plt.show()
    return

def fits_by_stability_and_month(
    stability = default_stability,
    data = df10
):
    stability_classes = stability['stability classes']
    stability_parameter = stability['stability parameter']
    stability_scheme = stability['stability scheme']
    result = pd.DataFrame(index = months, columns = [sc.title() for sc in stability_classes])
    for num, month in enumerate(months, 1):
        df_mon = data[data['time'].dt.month==num]
        for sc in stability_classes:
            dfMsc = df_mon[df_mon[stability_parameter].apply(stability_scheme) == sc]
            means = dfMsc[[f'ws_{h}m' for h in heights]].mean(axis = 0)
            _, wsc = hf.power_fit(heights, means.values, both=True)
            result.loc[month, sc.title()] = wsc
    return result

def plot_fits_summary(data,
                      cmap = 'viridis',
                      pretitle = 'All Data',
                      saveto = None,
                      minmax = (0,0.65),
                      percent = None,
                      clabel = r'$\alpha$',
                      xlabel = 'Month',
                      ylabel = 'Stability Class',
                      title = r'Wind Shear Exponent $\alpha$ by Month and Stability Classification'
    ):
    data = data.astype(np.float64).T
    # first plot
    if percent is not None: 
        percent = percent.astype(np.float64).T
    fig, ax = plt.subplots(figsize=(10,6))
    cax = ax.imshow(data.values, cmap = cmap, vmin = minmax[0], vmax = minmax[1], aspect = 'auto')
    cbar = fig.colorbar(cax)
    cbar.set_label(cabel)
    ax.set_xticks(np.arange(len(data.columns)))
    ax.set_xticklabels(data.columns)
    ax.set_yticks(np.arange(len(data.index)))
    ax.set_yticklabels(data.index)
    for i in range(len(data.index)):
        for j in range(len(data.columns)):
            if percent is not None:
                ax.text(j, i, f'{data.values[i, j]:.3f}' + f'\n({percent.values[i, j]:.0f}%)', ha='center', va='center', color='white', weight = 'bold')
            else:
                ax.text(j, i, f'{data.values[i, j]:.3f}', ha='center', va='center', color='white', weight = 'bold')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.suptitle(pretitle + '\n' + title)
    plt.tight_layout()
    if saveto is not None and type(saveto) is str:
        plt.savefig(saveto)
        plt.close()
    else:
        plt.show()
    # second plot
    #plt.scatter()

# def terrain_breakdown(
#         height = 10,
#         radius = 15
# ):
#     result = pd.DataFrame(index = months, columns = [tc.title() for tc in terrain_classes + ['other']])
#     for num, month in enumerate(months, 1):
#         df_mon = data[data['time'].dt.month==num]
#         for sc in stability_classes:
#             dfMsc = df_mon[df_mon[stability_parameter].apply(stability_scheme) == sc]
#             means = dfMsc[[f'ws_{h}m' for h in heights]].mean(axis = 0)
#             _, wsc = hf.power_fit(heights, means.values, both=True)
#             result.loc[month, sc.title()] = wsc
#     return result
    
# def plot_terrain_summary(
#         height = 10,
#         radius = 15
# ):
#     result = terrain_breakdown(height=height, radius=radius)

#     plot_fits_summary(data=result,
#                       minmax)
#     fig, ax = plt.subplots(figsize = (10,6))
#     for tc in terrain_classes + ['other']:
#         df = df10[df10[f'wd_{int(height)}m'].apply(lambda dir : hf.terrain_class(dir, radius = radius)) == tc]

def terrain_breakdown_monthly(
        data = df10,
        height = 10,
        radius = 15,
        other = True,
        total = True
):
    result = pd.DataFrame(index = months + total * ['Total'], columns = [tc.title() for tc in terrain_classes + ['other']])
    proportions = result.copy()
    for num, month in enumerate(months + total * ['Total'], 1):
        if month == 'Total':
            df_mon = data
        else:
            df_mon = data[data['time'].dt.month==num]
        for tc in terrain_classes + other * ['other']:
            count_tc = len(df_mon[df_mon[f'wd_{int(height)}m'].apply(lambda dir : hf.terrain_class(dir, radius = radius)) == tc])
            result.loc[month, tc.title()] = count_tc
            proportions.loc[month, tc.title()] = count_tc / len(df_mon)
        #proportions.loc[month, 'Total'] = len(df_mon)
    return result, proportions
            # dfMsc = df_mon[df_mon[stability_parameter].apply(stability_scheme) == sc]
            # means = dfMsc[[f'ws_{h}m' for h in heights]].mean(axis = 0)
            # _, wsc = hf.power_fit(heights, means.values, both=True)
            # result.loc[month, sc.title()] = wsc

def plot_terrain_monthly(
        data = df10,
        height = 10,
        radius = 15,
        other = True,
        proportions = False
):
    if proportions:
        data, props = terrain_breakdown_monthly(data=data, height=height, radius=radius, other = True, total=False)
        last_num = pd.Series(np.zeros(len(months), dtype=int))
        last_y = last_num.copy()
        for tc in terrain_classes + other * ['Other']:
            num = data[tc.title()].reset_index(drop = True)
            y = props[tc.title()].reset_index(drop = True)
            plt.bar(months, y, bottom = last_y, label = tc.title())
            for i in range(len(months)):
                plt.text(i, last_y.iloc[i]+y.iloc[i]/2, f'{num.iloc[i]}\n({(100*y.iloc[i]):.1f}%)', ha='center', va='center')
            last_num += num
            last_y += y
        if other:
            top_offset = np.max(last_y) / 150
            for i in range(len(months)):
                plt.text(i, last_y.iloc[i] + top_offset, last_num.iloc[i], ha='center')
        plt.title(f'Terrain Breakdown (Proportions of Total)\nBased on {height}m wind directions, direction cone radius of {radius} degrees')
        plt.ylabel('Fraction')
        plt.xlabel('Month')
        plt.legend()
        plt.show()
    else:
        data = terrain_breakdown_monthly(data=data, height=height, radius=radius, other = True, total=False)[0]
        last = pd.Series(np.zeros(len(months), dtype=int))
        for tc in terrain_classes + other * ['Other']:
            num = data[tc.title()].reset_index(drop = True)
            plt.bar(months, num, bottom = last, label = tc.title())
            for i in range(len(months)):
                plt.text(i, last.iloc[i]+num.iloc[i]/2, num.iloc[i], ha='center', va='center')
            last += num
        if other:
            top_offset = np.max(last) / 150
            for i in range(len(months)):
                plt.text(i, last.iloc[i] + top_offset, last.iloc[i], ha='center')
        plt.title(f'Terrain Breakdown\nBased on {height}m wind directions, direction cone radius of {radius} degrees')
        plt.ylabel('Number of Data Points')
        plt.xlabel('Month')
        plt.legend()
        plt.show()

def print_terrain_monthly(
        data = df10,
        height = 10,
        radius = 15,
        other = True,
        total = True,
):
    data = terrain_breakdown_monthly(data=data, height=height, radius=radius, other=other, total=total)
    print('Terrain breakdown (number of data points):')
    print(data[0])
    print('\n')
    print('Terrain breakdown (proportions):')
    print(data[1])

def fits_process_all(
    stability = default_stability,
    height = 10,
    cmap = 'viridis',
    saveplots = True,
    directory = '../../outputs/results/seasonality/',
):
    # all data
    fits_SM = fits_by_stability_and_month(stability = default_stability)
    fits_SM.to_csv(directory + f'fitsSM.csv', index_label='Month')
    plot_fits_summary(data = fits_SM, saveto = directory + f'fitsSM' if saveplots else None)
    # terrain classes
    results_by_tc = dict()
    for tc in terrain_classes:
        df = df10[df10[f'wd_{int(height)}m'].apply(hf.terrain_class) == tc]
        result_tc = fits_by_stability_and_month(stability = stability, data = df)
        result_tc.to_csv(directory + f'{int(height)}m/' + f'{tc}_fitsSM_{int(height)}m.csv', index_label='Month')
        results_by_tc[tc] = result_tc
        plot_fits_summary(data = result_tc, cmap = cmap, pretitle = tc.title() + f' Terrain (based on {int(height)}m directions)', saveto = directory + f'{int(height)}m/' + f'{tc}_fitsSM_{int(height)}m' if saveplots else None)
    deviation = results_by_tc['complex'] - results_by_tc['open']
    greater = results_by_tc['complex'].combine(results_by_tc['open'], np.maximum)
    percent = 100 * deviation / greater
    plot_fits_summary(data = deviation, cmap = cmap, pretitle = f'COMPLEX - OPEN DISCREPANCIES (based on {int(height)}m directions)', saveto = directory + f'{int(height)}m/' + f'discrepancy_{int(height)}m' if saveplots else None, minmax = (-0.2,0.2), percent = percent)

def terrain_by_month(height = 10,
                     cmap = 'viridis'):
    pass

def stability_plots(height = 10, stability = default_stability, cmap = 'viridis'):
    #mean_wind_profiles_by_stability_only(stability = stability)
    #mean_wind_profiles_by_terrain_and_stability(height = height, stability = stability)
    #bar_stability(stability = stability)
    fits_process_all(stability = stability, height = height, cmap = cmap)
    terrain_by_month(height = height, cmap = cmap)
    # NEXT DO SOMETHING LIKE THE FITS_PROCESS_ALL THING BUT INSTEAD GIVING A BREAKDOWN OF HOW MUCH DATA IS IN EACH TERRAIN CLASS MONTHLY
        # ** TERRAIN CLASS BREAKDOWN BY MONTH **
        # RI HISTOGRAM BY MONTH?
            # MEDIAN RI BY MONTH?
        # RI HISTOGRAM BY TERRAIN TYPE?
        # ALSO FOR FITS_PROCESS_ALL MAYBE PLOT THE DIFFERENCES COMPLEX - OPEN
            # + OPEN QUESTION OF SENSITIVITY TO TERRAIN WINDOW WIDTH (EXTEND TO 45 OR 60 DEGREES (SAME CENTER?)) AND HEIGHT USED
    
def alpha_vs_timeofday(month = None):
    if month is not None:
        dfm = df10[df10['time'].dt.month == month].copy()
        month = 'Month ' + str(month)
    else: 
        dfm = df10.copy() # if no month is specified use full dataset
        month = 'All Data'
    dfm['secondsintoday'] = (dfm['time'].dt.hour * 60 + dfm['time'].dt.minute) * 60 + dfm['time'].dt.second 
    uniquetimes = dfm['secondsintoday'].unique()
    means = [dfm[dfm['secondsintoday'] == time]['alpha'].mean() for time in uniquetimes]
    stds = [dfm[dfm['secondsintoday'] == time]['alpha'].std() for time in uniquetimes]
    plt.title(f'WSE vs Time of Day ({month})')
    plt.errorbar(uniquetimes, means, yerr = stds, fmt = 'o', markersize=3, capsize=3, elinewidth=0.5)
    plt.xlabel('Time of day (seconds past midnight UTC)')
    plt.ylabel(r'$\alpha$')
    plt.tight_layout()
    plt.show()

def alpha_vs_timeofday_with_terrain(month = None, height = 10, errorbars = False):
    if month is not None:
        dfm = df10[df10['time'].dt.month == month].copy()
        month = 'Month ' + str(month)
    else:
        dfm = df10.copy() # if no month is specified use full dataset
        month = 'All Data'
    dfm['secondsintoday'] = (dfm['time'].dt.hour * 60 + dfm['time'].dt.minute) * 60 + dfm['time'].dt.second 
    for tc in terrain_classes:
        dft = dfm[dfm[f'wd_{int(height)}m'].apply(hf.terrain_class) == tc]
        uniquetimes = dft['secondsintoday'].unique()
        means = [dft[dft['secondsintoday'] == time]['alpha'].mean() for time in uniquetimes]
        if errorbars:
            stds = [dft[dft['secondsintoday'] == time]['alpha'].std() for time in uniquetimes]
            plt.errorbar(uniquetimes, means, yerr = stds, fmt = 'o', markersize=3, capsize=3, elinewidth=0.5, label = tc.title())
        else:
            plt.scatter(uniquetimes, means, s=4, label = tc.title())
    plt.legend()
    plt.xlabel('Time of day (seconds past midnight UTC)')
    plt.ylabel(r'$\alpha$')
    plt.title(f'Mean WSE vs Time of Day, by Terrain (based on {int(height)}m directions)')
    plt.tight_layout()
    plt.show()

def alpha_vs_timeofday_with_seasons(terrain = None, height = 10):
    if terrain in terrain_classes:
        dfT = df10[df10[f'wd_{int(height)}m'].apply(hf.terrain_class) == terrain].copy()
        tcstring = terrain.title() + f' based on {height}m'
    else:
        dfT = df10.copy()
        tcstring =  'All Data'
    for S, mons in seasons.items():
        monnums = [months.index(m)+1 for m in mons]
        dfS = dfT[dfT['time'].dt.month.isin(monnums)].copy()
        dfS['secondsintoday'] = (dfS['time'].dt.hour * 60 + dfS['time'].dt.minute) * 60 + dfS['time'].dt.second 
        uniquetimes = np.sort(dfS['secondsintoday'].unique())
        means = [dfS[dfS['secondsintoday'] == time]['alpha'].mean() for time in uniquetimes]
        plt.plot(uniquetimes, means, linewidth=1, label = S, color = seasonal_colors[S])
    plt.legend()
    plt.xlabel('Time of day (seconds past midnight UTC)')
    plt.ylabel(r'$\alpha$')
    plt.title(f'Mean WSE vs Time of Day, by Season ({tcstring})')
    plt.tight_layout()
    plt.show()

def temperature_vs_timeofday_with_seasons(height = 10):
    for S, mons in seasons.items():
        monnums = [months.index(m)+1 for m in mons]
        dfS = df10[df10['time'].dt.month.isin(monnums)].copy()
        dfS['secondsintoday'] = (dfS['time'].dt.hour * 60 + dfS['time'].dt.minute) * 60 + dfS['time'].dt.second 
        uniquetimes = np.sort(dfS['secondsintoday'].unique())
        means = [dfS[dfS['secondsintoday'] == time][f't_{int(height)}m'].mean() for time in uniquetimes]
        plt.plot(uniquetimes, means, linewidth=1, label = S, color = seasonal_colors[S])
    plt.legend()
    plt.xlabel('Time of day (seconds past midnight UTC)')
    plt.ylabel('Temperature (K)')
    plt.title(f'Mean Temperature ({int(height)}m) vs Time of Day, by Season')
    plt.tight_layout()
    plt.show()

def combine_alpha_temperature_seasonality_plots(height = 10):
    for S, mons in seasons.items():
        monnums = [months.index(m)+1 for m in mons]
        dfS = df10#[df10['time'].dt.month.isin(monnums)].copy()
        dfS['secondsintoday'] = (dfS['time'].dt.hour * 60 + dfS['time'].dt.minute) * 60 + dfS['time'].dt.second 
        uniquetimes = np.sort(dfS['secondsintoday'].unique())
        meanalphas = [dfS[dfS['secondsintoday'] == time]['alpha'].mean() for time in uniquetimes]
        meanTs = [dfS[dfS['secondsintoday'] == time][f't_{int(height)}m'].mean() for time in uniquetimes]
        normalized_Ts = (meanTs - np.min(meanTs))/(2*(np.max(meanTs) - np.min(meanTs)))
        plt.plot(uniquetimes, meanalphas, linewidth=1, linestyle = 'solid', label = S + r' $\alpha$', color = seasonal_colors[S])
        plt.plot(uniquetimes, normalized_Ts, linewidth=1, linestyle = 'dashed', label = S + ' normalized temperature', color = seasonal_colors[S])
    plt.legend()
    plt.xlabel('Time of day (seconds past midnight UTC)')
    plt.title(f'Mean WSE vs Time of Day, by Season, with (normalized) temperature ({int(height)}m)')
    plt.tight_layout()
    plt.show()

def alpha_vs_sun_altitude():
    #sun_altitudes = df10['time'].apply(lambda t : get_position(t, CRLATITUDE, CRLONGITUDE)['altitude'])
    calculator = SunPositionCalculator()
    sun_altitudes = np.rad2deg(df10['time'].apply(lambda t : calculator.pos(t.timestamp()*1000, CRLATITUDE, CRLONGITUDE).altitude))
    # plt.scatter(df10['time'],sun_altitudes)
    plt.scatter(sun_altitudes, df10['alpha'], s=0.1)
    plt.ylim(-0.1,1.0)
    plt.show()

# def delta_alpha_vs_delta_temperature(height = 10):
#     d_alpha_dt = df10['alpha'].diff() / df10['time'].diff().dt.seconds
#     d_temp_dt = df10[f't_{int(height)}m'].diff() / df10['time'].diff().dt.seconds
#     plt.scatter(d_temp_dt, df10['alpha'], s=0.1)
#     plt.show()

if __name__ == '__main__':
    import plots
    #plots.boom_data_available()
    # for h in [6, 10, 20]:
    #     stability_plots(stability = default_stability, height = h)
    #stability_plots(stability = five_stability)
    #alpha_vs_timeofday()

    #alpha_vs_timeofday_with_terrain(height = 10)
    #alpha_vs_timeofday_with_terrain(height = 6)
    # temperature_vs_timeofday_with_seasons()
    #combine_alpha_temperature_seasonality_plots()
    #alpha_vs_sun_altitude()

    # alpha_vs_timeofday_with_seasons()
    # alpha_vs_timeofday_with_seasons(terrain = 'open')
    # alpha_vs_timeofday_with_seasons(terrain = 'complex')

    print_terrain_monthly()
    plot_terrain_monthly(other = False, proportions=True)
    plot_terrain_monthly(other = True, proportions=False)

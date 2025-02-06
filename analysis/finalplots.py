import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import windprofiles.lib.stats as stats
import windprofiles.lib.polar as polar
from windprofiles.analyze import get_monthly_breakdown
from windprofiles.lib.other import time_to_hours
from windprofiles.plotting import change_luminosity
import datetime
from astral import LocationInfo
from astral.sun import sun
from kcc_definitions import LATITUDE, LONGITUDE

COLORS_POSTER = {
    'open' : '#1f77b4',
    'complex' : '#ff7f0e',
    'unstable' : '#ef476f',
    'neutral' : '#ffd166',
    'stable' : '#06d6a0',
    'strongly stable' : '#17becf',
    'default1' : '#7f7f7f',
    'default2' : '#2ca02c',
}

COLORS_FORMAL = {
    'open' : 'tab:blue',
    'complex' : 'tab:orange',
    'unstable' : 'tab:red',
    'neutral' : '#3b50d6',
    'stable' : '#9b5445',
    'strongly stable' : 'tab:green',
    'default1' : 'tab:blue',
    'default2' : 'tab:orange'
}

MARKERS = {
    'open' : 'o',
    'complex' : 'v',
    'unstable' : '^',
    'neutral' : 'o',
    'stable' : 'D',
    'strongly stable' : 's',
    'default1' : 'o',
    'default2' : 's'
}

HEIGHTS = [6, 10, 20, 32, 106] # Heights that we are concerned with for plotting, in meters. 80m is left out here.
ZVALS = np.linspace(0.,130.,400) # Linspace for plotting heights
TERRAINS = ['open', 'complex']
LOCATION = LocationInfo(name = 'KCC tower', region = 'IA, USA', timezone = 'US/Central', latitude = LATITUDE, longitude = LONGITUDE)

MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
SEASONS = {
    'fall' : ['Sep', 'Oct', 'Nov'],
    'winter' : ['Dec', 'Jan', 'Feb'],
    'spring' : ['Mar', 'Apr', 'May'],
    'summer' : ['Jun', 'Jul', 'Aug']
}
CENTERDATES = { # Solstices/equinoxes in 2018
    'fall' : datetime.date(2018, 9, 22),
    'winter' : datetime.date(2018, 12, 21),
    'spring' : datetime.date(2018, 3, 20),
    'summer' : datetime.date(2018, 6, 21)
}

def bar_stability(df, summary, size, saveto, poster, details):
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    fig, ax = plt.subplots(figsize = size)
    stability_percents = 100 * df['stability'].value_counts(normalize = True)
    if summary['stability_classes'] == 4:
        ax.bar(
            x = ['Unstable\n'+r'$Ri_b<-0.1$','Neutral\n'+r'$-0.1\leq Ri_b<0.1$','Stable\n'+r'$0.1\leq Ri_b<0.25$','Strongly Stable\n'+r'$0.25\leq Ri_b$'],
            height = [stability_percents['unstable'], stability_percents['neutral'], stability_percents['stable'], stability_percents['strongly stable']],
            color = [COLORS['unstable'], COLORS['neutral'], COLORS['stable'], COLORS['strongly stable']]
        )
        for i, sc in enumerate(['unstable', 'neutral', 'stable', 'strongly stable']):
            ax.text(i, stability_percents[sc] - 2, f'{"N=" if i == 0 else ""}{len(df[df["stability"] == sc])}', ha='center', va='center')
    elif summary['stability_classes'] == 3:
        ax.bar(
            x = ['Unstable\n'+r'$Ri_b<-0.1$','Neutral\n'+r'$-0.1\leq Ri_b<0.1$','Stable\n'+r'$0.1\leq Ri_b$'],
            height = [stability_percents['unstable'], stability_percents['neutral'], stability_percents['stable']],
            color = [COLORS['unstable'], COLORS['neutral'], COLORS['stable']]
        )
        for i, sc in enumerate(['unstable', 'neutral', 'stable']):
            ax.text(i, stability_percents[sc] - 3, f'{"N=" if i == 0 else ""}{len(df[df["stability"] == sc])}', ha='center', va='center')
    else:
        raise Exception(f"Cannot handle {summary['stability_classes']} stability classes in plot 'bar_stability'")
    if poster:
        ax.set_title('Frequency of Wind Data Sorted by \nBulk Richardson Number Thermal Stability Classification')
    ax.set_ylabel('Proportion of Data (%)')
    ax.grid(axis = 'y', linestyle = '-', alpha = 0.75)
    plt.savefig(saveto, bbox_inches = 'tight')
    return

def annual_profiles(df, summary, size, saveto, poster, details):
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    fig, axs = plt.subplots(1, 2, figsize = size, sharey = True)
    if summary['stability_classes'] == 4:
        stabilities = ['unstable', 'neutral', 'stable', 'strongly stable']
    elif summary['stability_classes'] == 3:
        stabilities = ['unstable', 'neutral', 'stable']
    else:
        raise Exception(f"Cannot handle {summary['stability_classes']} stability classes in plot 'annual_profiles'")
    for i, tc in enumerate(TERRAINS):
        ax = axs[i]
        dft = df[df['terrain'] == tc]
        for sc in stabilities:
            short = ''.join([sub[0] for sub in sc.title().split(' ')])
            dfs = dft[dft['stability'] == sc]
            means = dfs[[f'ws_{h}m' for h in HEIGHTS]].mean(axis = 0).values
            mult, wsc = stats.power_fit(HEIGHTS, means)
            ax.plot(mult * ZVALS**wsc, ZVALS, color = change_luminosity(COLORS[sc], 0.85), zorder = 0)
            ax.scatter(means, HEIGHTS, label = r'{sc}: $u(z)={a:.2f}z^{{{b:.3f}}}$'.format(sc=short,a=mult,b=wsc), color = COLORS[sc], zorder = 5, s = 75*3**poster, marker = MARKERS[sc])
        ax.set_xlabel('Mean Wind Speed (m/s)')
        if i == 0: ax.set_ylabel('Height (m)')
        if poster:
            tc_title = (r'Open Terrain (${openL}-{openR}\degree$ at {h}m)'.format(openL = int(135 - summary['terrain_window_width_degrees']/2), openR = int(135 + summary['terrain_window_width_degrees']/2), h = summary['terrain_wind_height_meters'])
                    if tc == 'open'
                    else r'Complex Terrain (${complexL}-{complexR}\degree$ at {h}m)'.format(complexL = int(315 - summary['terrain_window_width_degrees']/2), complexR = int(315 + summary['terrain_window_width_degrees']/2), h = summary['terrain_wind_height_meters'])
                )
            ax.set_title(tc_title)
        ax.legend(loc = 'upper left')
    if poster:
        fig.suptitle('Annual Profiles of Wind Speed, by Terrain and Stability')
    fig.tight_layout()
    plt.savefig(saveto, bbox_inches = 'tight')
    return

def wse_histograms(df, summary, size, saveto, poster, details):
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    if summary['stability_classes'] == 4:
        stabilities = ['unstable', 'neutral', 'stable', 'strongly stable']
        nrows = 2
        ncols = 2
    elif summary['stability_classes'] == 3:
        stabilities = ['unstable', 'neutral', 'stable']
        nrows = 1
        ncols = 3
        size = (size[0] * 1.5, size[1] * 0.7)
    else:
        raise Exception(f"Cannot handle {summary['stability_classes']} stability classes in plot 'wse_histograms'")
    fig, axs = plt.subplots(nrows, ncols, figsize = size, sharex = (nrows > 1))
    for i, ax in enumerate(fig.axes):
        sc = stabilities[i]
        dfs = df[df['stability'] == sc]
        for tc in TERRAINS:
            dft_alpha = dfs.loc[dfs['terrain'] == tc, 'alpha']
            # density = True makes it such that the area under the histogram integrates to 1
            ax.hist(dft_alpha, bins = 35, density = True, alpha = 0.5, color = COLORS[tc], edgecolor = 'k', range = (-0.3, 1.2), label = f'{tc.title()} terrain')
            if details:
                print(f'  {tc} {sc}:')
                print(f'\tMean: {dft_alpha.mean():.2f}')
                print(f'\tMedian: {dft_alpha.median():.2f}')
                print(f'\tStandard deviation: {dft_alpha.std():.2f}')
                print(f'\tMed Ri_b: {dfs.loc[dfs["terrain"] == tc, "Ri_bulk"].median():.2f}')
        if i == ncols - 1:
            ax.legend(loc = 'upper right')
        if nrows == 2 and i >= ncols:
            ax.set_xlabel(r'$\alpha$')
        ax.set_title(sc.title(), loc = 'left', x = 0.025, y = 0.9125)
        ax.vlines(x = [dfs.loc[dfs['terrain'] == tc, 'alpha'].median() for tc in TERRAINS], ymin = 0, ymax = ax.get_ylim()[1], colors = [change_luminosity(COLORS[tc], 1.5) for tc in TERRAINS], alpha = 0.75, linestyle = 'dashed', linewidth = 4*2**poster)
    if poster:
        fig.suptitle(r'Wind Shear Exponent Distributions, by Terrain and Stability')
    fig.tight_layout()
    plt.savefig(saveto, bbox_inches = 'tight')
    return

def veer_profiles(df, summary, size, saveto, poster, details):
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    fig, axs = plt.subplots(1, 2, figsize = size, sharey = True)
    if summary['stability_classes'] == 4:
        stabilities = ['unstable', 'neutral', 'stable', 'strongly stable']
    elif summary['stability_classes'] == 3:
        stabilities = ['unstable', 'neutral', 'stable']
    else:
        raise Exception(f"Cannot handle {summary['stability_classes']} stability classes in plot 'annual_profiles'")
    for i, tc in enumerate(TERRAINS):
        ax = axs[i]
        dft = df[df['terrain'] == tc]
        for sc in stabilities:
            dfs = dft[dft['stability'] == sc]
            means = [polar.unit_average_direction(dfs[f'wd_{h}m']) for h in HEIGHTS]
            ax.plot(means, HEIGHTS, color = change_luminosity(COLORS[sc], 0.85), zorder = 0)
            ax.scatter(means, HEIGHTS, label = sc.title(), zorder = 5, s = 75*3**poster, marker = MARKERS[sc], facecolors = 'none', edgecolors = COLORS[sc], linewidths = 1.5)
        ax.set_xlabel('Mean Wind Direction (degrees)')
        if i == 1:
            ax.set_ylabel('Height (m)')
            ax.legend(loc = 'lower right')
        if poster:
            tc_title = (r'Open Terrain (${openL}-{openR}\degree$ at {h}m)'.format(openL = int(135 - summary['terrain_window_width_degrees']/2), openR = int(135 + summary['terrain_window_width_degrees']/2), h = summary['terrain_wind_height_meters'])
                    if tc == 'open'
                    else r'Complex Terrain (${complexL}-{complexR}\degree$ at {h}m)'.format(complexL = int(315 - summary['terrain_window_width_degrees']/2), complexR = int(315 + summary['terrain_window_width_degrees']/2), h = summary['terrain_wind_height_meters'])
                )
            ax.set_title(tc_title)
    if poster:
        fig.suptitle('Annual Profiles of Wind Direction, by Terrain and Stability')
    fig.tight_layout()
    plt.savefig(saveto, bbox_inches = 'tight')

def tod_wse(df, summary, size, saveto, poster, details):
    OFFSET = 0.15
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    fig, axs = plt.subplots(nrows = summary['stability_classes'], ncols = 1, figsize = size, sharex = True)
    fig.tight_layout()
    if summary['stability_classes'] == 4:
        stabilities = ['unstable', 'neutral', 'stable', 'strongly stable']
    elif summary['stability_classes'] == 3:
        stabilities = ['unstable', 'neutral', 'stable']
    else:
        raise Exception(f"Cannot handle {summary['stability_classes']} stability classes in plot 'tod_wse'")
    for i, ssn in enumerate(['fall','winter','spring','summer']):
        ax = axs[i]
        ax.set_ylim(0,0.7)
        #ax2 = ax.twinx()
        mons = SEASONS[ssn]
        monnums = [MONTHS.index(m)+1 for m in mons]
        dfs = df[df['time'].dt.month.isin(monnums)]
        for j, tc in enumerate(TERRAINS):
            dft = dfs[dfs['terrain'] == tc]
            hourly_wse = [dft[dft['time'].dt.hour == hr]['alpha'].reset_index(drop=True) for hr in range(24)]
            hourly_wse.append(dft[dft['time'].dt.hour == 0]['alpha'].reset_index(drop=True)) # have 0 at both the start and end
            #hourly_rib = [dft[dft['time'].dt.hour == hr]['Ri_bulk'].reset_index(drop=True) for hr in range(24)]
            med_wse = [wse.median() for wse in hourly_wse]
            std_wse = [wse.std() for wse in hourly_wse]
            #med_rib = [rib.median() for rib in hourly_rib]
            ax.errorbar(x = np.array(range(25))+OFFSET*j, y = med_wse, yerr = std_wse, color = COLORS[tc], fmt = MARKERS[tc], markersize = 12*2**poster, label = r'$\alpha$ ({terr})'.format(terr = tc.title()))
            #ax2.scatter(x = range(24), y = med_rib, facecolors = 'none', edgecolors = COLORS[tc], marker = 's', s = 16, label = r'$Ri_b$ ({terr})'.format(terr = tc.title()))
            fitsine, params = stats.fit_sine(range(24), med_wse[:24], std_wse[:24], fix_period=True)
            if details:
                print(f'\t{ssn} alpha = {params[0]:.4f} * sin({params[1]:.4f} * t + {params[2]:.4f}) + {params[3]:.4f}')
            xplot = np.linspace(0, 24, 120)
            ax.plot(xplot+OFFSET*j, fitsine(xplot), color = COLORS[tc], linestyle = 'dashed', alpha = 0.75)
        ax.set_ylabel(r'$\alpha$')
        ax.set_title(ssn.title(), loc = 'center', y = 0.9)
        s = sun(LOCATION.observer, date = CENTERDATES[ssn], tzinfo = LOCATION.timezone)
        ax.vlines([time_to_hours(s['sunrise']), time_to_hours(s['sunset'])], linestyle = 'dashed', ymin = ax.get_ylim()[0], ymax = ax.get_ylim()[1], color = 'green')
        if i == 0:
            ax.legend()
        elif i == 3:
            major_tick_locations = np.array(range(0,25,6)) + OFFSET*j/2
            major_tick_labels = [6*i for i in range(4)] + [0]
            ax.set_xticks(ticks = major_tick_locations, labels = major_tick_labels, minor = False)
            ax.set_xticks(np.array(range(24)) + OFFSET*j/2, range(24), minor = True, size = 10)
            ax.set_xlabel('Local time (hours)')
    plt.savefig(saveto, bbox_inches = 'tight')
    return

def data_gaps(df, summary, size, saveto, poster, details):
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    fig, ax = plt.subplots(figsize = size)
    fig.tight_layout()
    plt.savefig(saveto, bbox_inches = 'tight')
    return

def terrain_breakdown(df, summary, size, saveto, poster, details):
    COLORS = COLORS_POSTER if poster else COLORS_FORMAL
    fig, ax = plt.subplots(figsize = size)
    breakdown, proportions = get_monthly_breakdown(df, 'terrain')
    print(breakdown)
    print(proportions)
    fig.tight_layout()
    plt.savefig(saveto, bbox_inches = 'tight')
    return

ALL_PLOTS = {
    'bar_stability': ('Stability Frequency Bar Plot', bar_stability, (8,6)),
    'annual_profiles' : ('Annual Wind Profiles with Fits, by Terrain', annual_profiles, (13,6)),
    'wse_histograms' : ('Histograms of WSE, by Stability, including Terrain', wse_histograms, (13,9)),
    'veer_profiles' : ('Wind direction profiles, by Terrain', veer_profiles, (13,6)),
    'tod_wse' : ('Time of Day Plots of WSE, by Terrain, including Stability & Fits', tod_wse, (13,16)),
    'data_gaps' : ('Data Gap Visualization', data_gaps, (13,8)),
    'terrain_breakdown' : ('Breakdown of Terrain Characterizations, by Month', terrain_breakdown, (7,10))
}

def list_possible_plots():
    print('Possible plots to generate:')
    for tag in ALL_PLOTS.keys():
        print(f'\t{tag}')

def generate_plots(df: pd.DataFrame, savedir: str, summary: dict, which: list = ALL_PLOTS.keys(), poster: bool = False, details: bool = False, **kwargs):
    plt.rcParams['font.size'] = 26 if poster else 14
    plt.rcParams['font.family'] = 'sans-serif' if poster else 'serif'
    plt.rcParams['mathtext.fontset'] = 'dejavusans' if poster else 'stix'
    print(f'Generating final plots in {"Poster" if poster else "Paper"} mode')
    if not details: print('Details suppressed. Rerun with details = True (-v in kcc.py) to print.')
    not_generated = list(ALL_PLOTS.keys())
    fig_savedir = f'{savedir}/{"P" if poster else ""}{summary["_rules_chksum"]}'
    os.makedirs(fig_savedir, exist_ok = True)
    for tag in which:
        long, plotter, size = ALL_PLOTS[tag]
        print(f"Generating plot {tag}: '{long}'")
        if poster: size = (2*size[0],2*size[1]) # higher quality for poster scaling
        plotter(df = df, summary = summary, size = size, saveto = f'{fig_savedir}/{tag}.png', poster = poster, details = details)
        not_generated.remove(tag)
    if len(not_generated) != 0:
        print(f'Plots not generated: {not_generated}') 
    print(f'Finished generating plots. Final plots saved to:\n\t{fig_savedir}/')
    print('Rules used in analysis to create plot data:')
    for key, val in summary.items():
        if key[0] != '_':
            print(f'\t{key} = {val}')

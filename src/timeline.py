import click
import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os

from argparse import Namespace as attrdict
from datetime import datetime, timedelta

import read

# disable interactive mode
plt.ioff()

def parse_year(y):
    """takes year (e.g. 1732) as a string and returns a datetime"""
    if isinstance(y, str) and '-' in y:
        return datetime.strptime(y, '%Y-%m-%d')

    return datetime.strptime(str(y), '%Y')


def get_data(filename):
    # hand-coded json taking from munging quartet-roulette data.
    # '../quartet-chooser/src/data/data.json'
    def tryint(s):
        c = s.split()[0]
        if '/' in c:
            c = c.split('/')[0]
        try:
            return int(c)
        except Exception as e:
            return 1

    with open(filename) as f:
        d = json.load(f)
        data = []
        for i, row in enumerate(d, 1):
            composer, year, size, name = row

            opus = tryint(name) if composer == 'Haydn' and 0 < size else 0
            data.append(attrdict(composer=composer, year=parse_year(year), size=size, name=name, ix=i, opus=opus))
        # print(json.dumps([d.__dict__ for d in data], indent=4))
        # json-encoding/decoding time is better this way: https://stackoverflow.com/a/52838324/2683
        # print(json.dumps(data, indent=4, default=str))
        """
        [
            "Namespace(composer='Haydn', year=datetime.datetime(1732, 1, 1, 0, 0), size=0, name='born', ix=1, opus=0)",
            "Namespace(composer='Haydn', year=datetime.datetime(1809, 1, 1, 0, 0), size=0, name='died', ix=2, opus=0)",
            "Namespace(composer='Haydn', year=datetime.datetime(1765, 1, 1, 0, 0), size=10, name='The Earlies', ix=3, opus=1)",
            "Namespace(composer='Haydn', year=datetime.datetime(1769, 1, 1, 0, 0), size=6, name='9', ix=4, opus=9)",
            "Namespace(composer='Haydn', year=datetime.datetime(1771, 1, 1, 0, 0), size=6, name='17', ix=5, opus=17)",
            "Namespace(composer='Haydn', year=datetime.datetime(1772, 1, 1, 0, 0), size=6, name=\"20 'Sun'\", ix=6, opus=20)",
            "Namespace(composer='Haydn', year=datetime.datetime(1781, 1, 1, 0, 0), size=6, name=\"33 'Russian'\", ix=7, opus=33)",
            "Namespace(composer='Haydn', year=datetime.datetime(1785, 1, 1, 0, 0), size=1, name='42', ix=8, opus=42)",
            "Namespace(composer='Haydn', year=datetime.datetime(1787, 1, 1, 0, 0), size=6, name=\"50 'Prussian'\", ix=9, opus=50)",
            "Namespace(composer='Haydn', year=datetime.datetime(1788, 1, 1, 0, 0), size=6, name=\"54/55 'Tost I/II'\", ix=10, opus=54)",
            "Namespace(composer='Haydn', year=datetime.datetime(1790, 1, 1, 0, 0), size=6, name=\"64 'Tost III'\", ix=11, opus=64)",
            "Namespace(composer='Haydn', year=datetime.datetime(1793, 1, 1, 0, 0), size=6, name=\"71/74 'Apponyi'\", ix=12, opus=71)",
            "Namespace(composer='Haydn', year=datetime.datetime(1797, 1, 1, 0, 0), size=6, name=\"76 'Erdody'\", ix=13, opus=76)",
            "Namespace(composer='Haydn', year=datetime.datetime(1799, 1, 1, 0, 0), size=2, name=\"77 'Lobkowitz'\", ix=14, opus=77)",
            "Namespace(composer='Haydn', year=datetime.datetime(1803, 1, 1, 0, 0), size=0.5, name='103', ix=15, opus=103)",
            "Namespace(composer='Mozart', year=datetime.datetime(1756, 1, 1, 0, 0), size=0, name='born', ix=16, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1791, 1, 1, 0, 0), size=0, name='died', ix=17, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1770, 1, 1, 0, 0), size=1, name=\"K80 'Lodi'\", ix=18, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1772, 1, 1, 0, 0), size=6, name=\"K155-160 'Milanese'\", ix=19, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1773, 1, 1, 0, 0), size=6, name=\"K168-173 'Viennese'\", ix=20, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1782, 1, 1, 0, 0), size=6, name=\"6 'Haydn'\", ix=21, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1786, 1, 1, 0, 0), size=1, name=\"K499 'Hoffmeister'\", ix=22, opus=0)",
            "Namespace(composer='Mozart', year=datetime.datetime(1789, 1, 1, 0, 0), size=3, name=\"3 'Prussian'\", ix=23, opus=0)",
            "Namespace(composer='Beethoven', year=datetime.datetime(1770, 1, 1, 0, 0), size=0, name='born', ix=24, opus=0)",
            "Namespace(composer='Beethoven', year=datetime.datetime(1800, 1, 1, 0, 0), size=6, name=\"18 'Lobkowitz'\", ix=25, opus=0)",
            "Namespace(composer='Beethoven', year=datetime.datetime(1808, 1, 1, 0, 0), size=3, name=\"59 'Razumovsky'\", ix=26, opus=0)",
            "Namespace(composer='Beethoven', year=datetime.datetime(1809, 1, 1, 0, 0), size=1, name=\"74 'Harp'\", ix=27, opus=0)"
        ]
        """
        return data


def make_plot(data, filename, opus_colors, colors, es):
    # Create the figure and axis
    # fig, ax = plt.subplots(figsize=(11,8.5))
    fig, ax = plt.subplots(figsize=(8.5, 2.4))

    # Plot the data on a timeline
    angle = 35
    # references:
    # markers: https://matplotlib.org/stable/api/markers_api.html
    # ha needs to be one of { 'center', 'right', 'left' }
    # va needs to be one of { 'top', 'bottom', 'center', 'baseline', 'center_baseline' }
    # https://matplotlib.org/stable/gallery/text_labels_and_annotations/text_alignment.html

    # x-axis ticks
    for i, date in enumerate(mdates.drange(parse_year('1758'), parse_year('1809'), timedelta(days=365))):
        ax.plot(date, 1, marker=3, markersize=5, color='k', alpha=.25, markeredgewidth=1)
        # ax.plot(d.year, l, marker=marker, markersize=sz, color=clr, alpha=1, mew=w)

    for d in data:
        if d.size == 0: # birth / death
            clr = colors.get(d.composer)
            if d.composer == 'Haydn':
                marker = 10 # v ## 7 # ^
                # marker = 5 if d.name == 'born' else 4  # > <
            else:
                marker = 11 # v
                # marker = 9 if d.name == 'born' else 8  # > <

            sz = 10
            w = 1
        else: # quartet
            # clr = opus_colors.get(d.opus) if d.composer == 'Haydn' else colors.get(d.composer)
            clr = colors.get(d.composer)
            marker = 2 if d.composer == 'Haydn' else 3 # '|' # 2
            sz = 4*d.size
            w = 5

        l = 1  # plot everything on the same level
        ax.plot(d.year, l, marker=marker, markersize=sz, color=clr, alpha=1, mew=w)

        # let's painstakingly position all the labels because ... if we don't it's illegible
        defaults = dict(xy=(d.year, l), textcoords='offset points', fontsize=10, fontstyle='italic')
        if d.name == 'born':
            if d.ix == 1: # haydn
                ax.annotate(text='fjh\n1732', xytext=(0, 10), ha='center', va='bottom', **defaults)
            elif d.ix == 16: # mozart
                ax.annotate(text='wam\n1756', xytext=(0, 10), ha='center', va='bottom', **defaults)
            elif d.ix == 24: # beethoven
                ax.annotate(text='lvb', xytext=(0, -20), ha='center', va='bottom', **defaults)
        elif d.name == 'died':
            if d.composer == 'Mozart':
                ax.annotate('WAM', xytext=(0, -8), ha='center', va='top', **defaults)
            elif d.composer == 'Haydn':
                ax.annotate('FJH', xytext=(0, 8), ha='center', va='bottom', **defaults)
            else:
                ax.annotate(d.year.year, xytext=(0, 6), ha='center', va='bottom', **defaults)
        else:
            d.name = d.name.replace('-', '–') # en-dash, not hyphen. IYKYK.
            defaults.update(text=d.name)
            if d.ix == 3: # Earlies
                ax.annotate(xytext=(-5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 4: # Opus 9
                ax.annotate(xytext=(-2.5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 5: # Opus 17
                ax.annotate(xytext=(-5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 6: # Opus 20
                ax.annotate(xytext=(-5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 7: # Opus 33
                ax.annotate(xytext=(-5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 8: # Opus 42
                ax.annotate(xytext=(-4.5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 9: # Opus 50
                ax.annotate(xytext=(-6, sz-2), ha='left', va='bottom', **defaults)
            elif d.ix == 10: # Opus 54/55
                ax.annotate(xytext=(-6, sz-2), ha='left', va='bottom', **defaults)
            elif d.ix == 11: # Opus 64
                ax.annotate(xytext=(-4, sz-2), ha='left', va='bottom', **defaults)
            elif d.ix == 12: # Opus 71/74
                ax.annotate(xytext=(-10, sz-2), ha='left', va='bottom', **defaults)
            elif d.ix == 13: # Opus 76
                ax.annotate(xytext=(-5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 14: # Opus 77
                ax.annotate(xytext=(-5, sz+8), ha='left', va='top', **defaults)
            elif d.ix == 15: # Opus 103
                ax.annotate(xytext=(-7, sz+7), ha='left', va='top', **defaults)
                #ax.annotate(xytext=(2, 1), ha='left', va='baseline', **defaults)
            elif d.ix == 18: # K80
                ax.annotate(xytext=(3, -5), ha='right', va='top', **defaults)
            elif d.ix == 19: # Milanese
                ax.annotate(xytext=(-3, -sz-2), ha='left', va='top', **defaults)
            elif d.ix == 20: # Viennese
                ax.annotate(xytext=(3, -sz+8), ha='left', va='top', **defaults)
            elif d.ix == 21: # Haydn
                ax.annotate(xytext=(-3, -sz-1), ha='left', va='top', **defaults)
            elif d.ix == 22: # K499
                # ax.annotate(xytext=(-5, -sz), ha='left', va='top', rotation=-angle, **defaults)
                ax.annotate(xytext=(0, -sz-2), ha='center', va='top', **defaults)
            elif d.ix == 23: # Prussian
                ax.annotate(xytext=(-3, -sz-4), ha='left', va='top', **defaults)
            elif d.ix == 25: # Opus 18
                ax.annotate(xytext=(-5, -sz-2), ha='left', va='top', **defaults)
            elif d.ix == 26: # Opus 59
                ax.annotate(xytext=(-5, -sz-2), ha='left', va='top', **defaults)
            elif d.ix == 27: # Opus 74
                ax.annotate(xytext=(-2, -sz-1), ha='left', va='top', **defaults)
            else:
                print("Default", d.name)
                ax.annotate(xytext=(-2.5, sz+10), ha='left', va='top', **defaults)


    # Attempt to add FJH and WAM bdays
    x, w, l = parse_year('1758'), 4, .85
    ax.plot(x, l, marker="s", markersize=w, color=colors.get('Haydn'), mew=w)
    ax.annotate(xy=(x, l), text='Haydn (1732–1809)', xytext=(w + 1, 0), ha='left', va='center', textcoords='offset points', fontsize=8, fontstyle='italic')
    l -= .03
    ax.plot(x, l, marker="s", markersize=w, color=colors.get('Mozart'), mew=w)
    ax.annotate(xy=(x, l), text='Mozart (1756–1791)', xytext=(w + 1, 0), ha='left', va='center', textcoords='offset points', fontsize=8, fontstyle='italic')
    l -= .03
    ax.plot(x, l, marker="s", markersize=w, color=colors.get('Beethoven'), mew=w)
    ax.annotate(xy=(x, l), text='Beethoven (1770–1827)', xytext=(w + 1, 0), ha='left', va='center', textcoords='offset points', fontsize=8, fontstyle='italic')

    l = 1 # reset for use below
    ax.hlines(l, parse_year('1758'), parse_year('1810'), color='gray', linestyle='-', linewidth=.5, alpha=.5)

    # Add the Eszterhazy Rulers
    y = 1.21
    h = .04

    defaults = dict(textcoords='offset points', fontsize=10, fontstyle='italic')

    # Paul Anton Ruled 1734 - 1762
    start, end = parse_year('1734'), parse_year('1762')
    ax.barh(y, height=h, width=end - start, left=start, align='edge', color=es[1])
    ax.annotate(text='Paul Anton', xy=(parse_year('1757'), y), xytext=(4, 10), ha='left', va='top', **defaults)

    # Nikolaus I "the magnificent" Ruled 1762 - 1790. *Brother* of Paul Antonj
    start, end = parse_year('1762'), datetime(1790, 9, 28),
    ax.barh(y, height=h, width=end - start, left=start, align='edge', color=es[0])
    ax.annotate(text='Nikolaus I "The Magnificent"', xy=(parse_year('1779'), y), xytext=(0, 10), ha='right', va='top', **defaults)

    # Anton I. Ruled 1790 - 1794. Son of Nikolaus I.
    start, end = datetime(1790, 9, 28), datetime(1794, 1, 22)
    ax.barh(y, height=h, width=end - start, left=start, align='edge', color=es[1])
    ax.annotate(text='Anton I', xy=(start, y), xytext=(2, 10), ha='left', va='top', **defaults)

    # Nikolaus II rules 1794 - 1833. Son of Anton I
    start, end = datetime(1794, 1, 22), parse_year('1833')
    ax.barh(y, height=h, width=end - start, left=start, align='edge', color=es[0])
    ax.annotate(text='Nikolaus II', xy=(parse_year('1800'), y), xytext=(10, 10), ha='left', va='top', **defaults)

    # Add London Visits from timeline-verbose.json
    ["Haydn", 1791, 0, "London I: 1/1/1791 - 7/24/1792"],
    y = 1.16
    h = .04
    defaults = dict(textcoords='offset points', fontsize=8, fontstyle='italic')
    start, end = datetime(1791, 1, 1), datetime(1792, 7, 24)
    ax.barh(y, height=h, width=end - start, left=start, align='edge', color='#cccccc')
    ax.annotate(text='LON', xy=(parse_year('1791'), y), xytext=(0, 9), ha='left', va='top', **defaults)

    ["Haydn", 1794, 0, "London II: 2/4/1794 - 8/15/1795"],
    start, end = datetime(1794, 2, 4), datetime(1795, 8, 15)
    ax.barh(y, height=h, width=end - start, left=start, align='edge', color='#cccccc')
    ax.annotate(text='LON', xy=(parse_year('1794'), y), xytext=(1, 9), ha='left', va='top', **defaults)

    # Add Nikolaus I's musical tastes (Baryton trios 1765-1775, Opera after that (do the operas stop?))?
    """
    # see what colors are available in this scheme
    for i, date in enumerate(mdates.drange(start_date, end_date, timedelta(days=365 * 10))):
        ax.plot(date, 3, 'o', markersize=10, color='C%d' % i, alpha=.7, markeredgewidth=w)
    """

    # Format the x-axis as dates
    # ax.xaxis.set_major_locator(mdates.YearLocator(10))
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))


    # Set the x-axis limits
    # Define the start and end dates for the timeline
    # start_date, end_date = parse_year('1732'), parse_year('1809')
    start_date, end_date = parse_year('1757'), parse_year('1814')
    ax.set_xlim(start_date, end_date)

    # Set the y-axis limits
    ax.set_ylim([.75, 1.25])

    # Hide the axis lines (aka "spines")
    for loc in 'top, right, left, bottom'.split(', '):
        ax.spines[loc].set_visible(False)

    # Set the y-axis ticks invisible
    ax.yaxis.set_ticks([])

    """
    # Add x-axis labels for 1732 and 1809
    ticks = list(ax.get_xticks()) + [mdates.date2num(start_date), mdates.date2num(end_date)]
    ax.set_xticks(sorted(ticks))

    tick_labels = sorted(list(ax.get_xticklabels()), key=lambda t: t.get_position()[0])
    tick_labels[0].set_text('')
    tick_labels[-1].set_text('')
    ax.set_xticklabels(tick_labels)
    """

    # Set the title
    # ax.set_title('Timeline of Haydn Quartets with Mozart & Beethoven')

    # Tweak spacing so x-axis labels don't hit the bottom
    plt.subplots_adjust(left=0, bottom=0.10, top=.98, right=.98)

    # Show the plot
    # plt.savefig(filename, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(filename, facecolor='#fff', edgecolor='#fff', transparent=True)
    return filename


@click.command()
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
@click.option('-c', '--color-json', type=click.Path(exists=True), required=True, help="json file specifying colors")
@click.option('-d', '--datadir', type=click.Path(exists=True), required=True, help="data directory")
def main(outfile, color_json, datadir):
    """
    styles
    plt.style.use('Solarize_Light2')
        fivethirtyeight,
        ggplot,
        seaborn-v0_8
        seaborn-v0_8-*,
        Solarize_Light2,
        tableau-colorblind10,
    """
    stylename = 'fivethirtyeight'
    plt.style.use(stylename)
    data = get_data(os.path.join(datadir, 'timeline.json'))

    # get colors
    cmap = read.get_cmap(color_json)
    cols = read.COLS  # get_cmap populates COLS via read.read_colors()
    to_hex = lambda cname: cols[cname]['value'].hexval().replace('0x', '#').upper()
    opus_colors = {opus: to_hex(cname) for (opus, cname) in cmap.items()}
    composer_colors = {
        'Haydn': to_hex('magenta'),
        'Mozart': to_hex('mint'),
        'Beethoven': to_hex('blue')
    }
    es = list(map(to_hex, ['lavender', 'apricot', 'pink']))

    make_plot(data, outfile, opus_colors, composer_colors, es)
    plt.close()


if __name__ == '__main__':
    main()

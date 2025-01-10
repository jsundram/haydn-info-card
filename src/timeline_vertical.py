import click
import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os

from argparse import Namespace as attrdict
from datetime import datetime, timedelta
from dateutil.rrule import rrule, YEARLY
from matplotlib.dates import date2num
from matplotlib.lines import Line2D

import read

plt.ioff()  # disable interactive mode


def parse_year(y):
    """takes year (e.g. 1732) as a string and returns a datetime"""
    if isinstance(y, str) and '-' in y:
        return datetime.strptime(y, '%Y-%m-%d')

    return datetime.strptime(str(y), '%Y')


def get_data(filename):
    with open(filename) as f:
        data = []
        for (c, y, s, n) in json.load(f):
            data.append(attrdict(composer=c, year=parse_year(y), size=s, name=n))
        return data


def make_plot(data, filename, colors):
    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(3, 8.5))

    # y-axis ticks
    for date in rrule(freq=YEARLY, dtstart=datetime(1756, 1, 1), until=datetime(1809, 1, 1)):
        if date.year % 5 != 0:  # avoid overplotting the major_locator lines.
            ax.plot(1, date2num(date), marker="_", markersize=5, color='k', alpha=.25, markeredgewidth=1)

    # m = {'born': {True: 8, False: 9}, 'died': {True: 8, False: 9}, 'default': {True: 0, False: 1}}
    # m = {'born': {True: 8, False: 9}, 'died': {True: 8, False: 9}, 'default': {True: 0, False: 1}}
    for d in data:
        clr = colors.get(d.composer)
        if d.name in {'born', 'died'}:
            marker = 8 if d.composer == 'Haydn' else 9
            w, sz = 1, 10  # marker edge width (mew), size
        else:  # quartet
            marker = 0 if d.composer == 'Haydn' else 1
            w, sz = 5, 4*d.size

        l = 1  # plot everything on the same level
        ax.plot(l, d.year, marker=marker, markersize=sz, color=clr, alpha=1, mew=w)

        # labels
        defaults = dict(xy=(l, d.year), textcoords='offset points', fontsize=10, fontstyle='italic', va='center')
        if d.name == 'born':
            if d.composer == 'Haydn':
                ax.annotate(text='fjh', xytext=(-sz, 0), ha='right', **defaults)
            elif d.composer == 'Mozart':
                ax.annotate(text='wam', xytext=(sz, 0), ha='left', **defaults)
            else:  # d.composer == 'Beethoven':
                ax.annotate(text='lvb', xytext=(sz, 0), ha='left', **defaults)
        elif d.name == 'died':
            if d.composer == 'Haydn':
                ax.annotate('FJH', xytext=(-sz, 0), ha='right', **defaults)
            elif d.composer == 'Mozart':
                ax.annotate('WAM', xytext=(sz, 0), ha='left', **defaults)
            else:  # d.composer == 'Beethoven':
                ax.annotate('LVB', xytext=(sz, 0), ha='left', **defaults)
        else:
            d.name = d.name.replace('-', '–')   # en-dash, not hyphen. IYKYK.
            d.name = d.name.replace('\n', ' ')  # get rid of line breaks
            if d.composer == 'Haydn':
                ax.annotate(text=d.name, xytext=(-sz - 1, -1), ha='right', **defaults)
            else:
                ax.annotate(text=d.name, xytext=(sz + 1, -1), ha='left', **defaults)

    # Legend
    square = lambda s: Line2D([0], [0], linestyle='None',
        marker='s',
        markerfacecolor=colors.get(s), markersize=6, markeredgewidth=0
    )

    legend = ax.legend(
        [square('Haydn'), square('Mozart'), square('Beethoven')],
        ['Haydn (1732–1809)', 'Mozart (1756–1791)', 'Beethoven (1770–1827)'],
        loc='right',             # Legend location relative to the anchor
        bbox_to_anchor=(1, .03), # Adjust this to fine-tune the position
        fontsize=8,
        labelspacing=0.1,        # Reduce vertical spacing between labels
        handletextpad=0.0        # Adjust spacing between marker and text
    )
    # legend.get_frame().set_alpha(0)  # transparent background

    # Add the Eszterhazy Rulers
    x, w = -.5, .25
    defaults = dict(textcoords='offset points', fontsize=10, fontstyle='italic', rotation=270, ha='left', va='center')

    # Paul Anton Ruled 1734 - 1762
    name = 'Paul Anton'
    start, end = parse_year('1734'), parse_year('1762')
    ax.bar(x, width=w, bottom=end, height=start-end, align='edge', color=colors[name])
    ax.annotate(text=name, xy=(x, datetime(1758, 6, 1)), xytext=(0, 0), **defaults)

    # Nikolaus I "the magnificent" Ruled 1762 - 1790. *Brother* of Paul Anton
    name = 'Nikolaus I "The Magnificent"'
    start, end = parse_year('1762'), datetime(1790, 9, 28),
    mid = start + (end - start) / 2
    ax.bar(x, width=w, bottom=end, height=start-end, align='edge', color=colors[name])
    ax.annotate(text=name, xy=(x, mid), xytext=(0, 0), **defaults)

    # Anton I. Ruled 1790 - 1794. Son of Nikolaus I.
    name = 'Anton I'
    start, end = datetime(1790, 9, 28), datetime(1794, 1, 22)
    ax.bar(x, width=w, bottom=end, height=start-end, align='edge', color=colors[name])
    ax.annotate(text=name, xy=(x, start), xytext=(0, -16), **defaults)

    # Nikolaus II rules 1794 - 1833. Son of Anton I
    name = 'Nikolaus II'
    start, end = datetime(1794, 1, 22), parse_year('1833')
    mid = datetime(1805, 1, 1)
    ax.bar(x, width=w, bottom=end, height=start-end, align='edge', color=colors[name])
    ax.annotate(text=name, xy=(x, mid), xytext=(0, 0), **defaults)

    # London Visits
    name = 'LON'
    x, w = .5, .4  # make the bar fat enough to fit the text within it, unrotated.
    defaults = dict(textcoords='offset points', fontsize=8, fontstyle='italic', ha='left', va='center')
    start, end = datetime(1791, 1, 1), datetime(1792, 7, 24)
    ax.bar(x, width=w, bottom=end, height=start-end, align='edge', color=colors[name])
    ax.annotate(text=name, xy=(x, start), xytext=(0, -8), **defaults)

    start, end = datetime(1794, 2, 4), datetime(1795, 8, 15)
    ax.bar(x, width=w, bottom=end, height=start-end, align='edge', color=colors[name])
    ax.annotate(text=name, xy=(x, start), xytext=(0, -8), **defaults)

    # Draw the y-axis line
    ax.vlines(1, parse_year('1755'), parse_year('1810'), color='gray', linestyle='-', linewidth=.5, alpha=.5)

    # Format the y-axis as dates
    ax.yaxis.set_major_locator(mdates.YearLocator(5))
    ax.yaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    # Set the y-axis limits
    ax.set_ylim(parse_year('1755'), parse_year('1814'))

    # earlier = higher
    ax.invert_yaxis()

    # Hide the axis lines (aka "spines")
    for loc in 'top, right, left, bottom'.split(', '):
        ax.spines[loc].set_visible(False)

    # Set the x-axis ticks invisible
    ax.xaxis.set_ticks([])

    # Set the x-axis limits
    ax.set_xlim([-.5, 3.35])

    # Tweak spacing
    plt.subplots_adjust(left=.16, bottom=.0, top=.98, right=1.0)

    # Save the plot
    plt.savefig(filename, facecolor='#fff', edgecolor='#fff', transparent=True)


@click.command()
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
@click.option('-c', '--color-json', type=click.Path(exists=True), required=True, help="json file specifying colors")
@click.option('-d', '--datadir', type=click.Path(exists=True), required=True, help="data directory")
def main(outfile, color_json, datadir):
    plt.style.use('fivethirtyeight')
    data = get_data(os.path.join(datadir, 'timeline.json'))

    cols = read.read_colors(color_json)
    to_hex = lambda cname: cols[cname]['value'].hexval().replace('0x', '#').upper()
    colors = {
        'Haydn': to_hex('magenta'),
        'Mozart': to_hex('mint'),
        'Beethoven': to_hex('blue'),
        'Paul Anton': to_hex('apricot'),
        'Nikolaus I "The Magnificent"': to_hex('lavender'),
        'Anton I': to_hex('apricot'),
        'Nikolaus II': to_hex('lavender'),
        'LON': '#cccccc',
    }

    make_plot(data, outfile, colors)
    plt.close()


if __name__ == '__main__':
    main()

import click
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import patheffects


matplotlib.use('MacOSX')
plt.style.use('classic')


def underline_annotation(text):
    f, ax = plt.gcf(), plt.gca()

    # text isn't drawn immediately and must be given a renderer if one isn't cached.
    # tightbbox return units are in 'figure pixels', transformed to 'figure fraction'.
    tb = text.get_tightbbox(f.canvas.get_renderer()).transformed(f.transFigure.inverted())

    # Use arrowprops to draw a straight line anywhere on the axis.
    # fudging a bit here with the .1 and the 1.5 below
    x = .1 * (tb.xmax - tb.xmin)
    x0, x1, y = tb.xmin-1.5*x, tb.xmax +x, tb.y0
    ax.annotate('', xy=(x0, y), xytext=(x1, y),
               # xycoords="figure fraction",
                arrowprops=dict(arrowstyle="-", color='k', lw=6)
    )

@click.command()
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
def main(outfile):
    with plt.xkcd():
        # Get rid of outlines around text (?)
        # https://stackoverflow.com/questions/50845646/matplotlib-xkcd-and-black-figure-background/54698065#54698065
        plt.rcParams['path.effects'] = [patheffects.withStroke(linewidth=0)]

        # Create a new figure with explicitly set size to make the square appear as intended.
        # The figure size is set to be square to ensure that our square also appears square.
        fig, ax = plt.subplots(figsize=(6, 6))

        b, l, w, h = .1, .1, .8, .8
        # Draw a square
        ax.add_patch(patches.Rectangle((l, b), w, h, fill=None, edgecolor='k'))

        # Draw shaded bars at the top and bottom of the square
        ht = .1
        bt = b + h - ht
        ax.add_patch(patches.Rectangle((l, bt), w, ht, color='#FF00FF', alpha=0.5, lw=None))
        ax.add_patch(patches.Rectangle((l, b), w, ht, color='gray', alpha=0.25))

        arrow = dict(facecolor='black', arrowstyle='->')
        al = -.15 # annotation left
        ts = 20
        # Nickname Text
        plt.text(l + w/2, bt + .25*ht, 'The Razor', ha='center',fontsize=20)
        fx, fy = .25, .02 # fudge factors to accomodate the fact that I am not measuring text extents
        ax.annotate('Nickname', xy=(l + fx, bt + .25*ht + fy), xytext=(al, bt + .25*ht), arrowprops=arrow, ha='center', size=ts)

        # Peters Text
        space = .02
        plt.text(l + w - space, bt - space, 'III', ha='right', va='top', fontsize=20)
        fx, fy = .03, .02
        ax.annotate('Peters Volume', xy=(l + w - 2*space - fx , bt - space - fy), xytext=(al, bt - space - fy), arrowprops=arrow, ha='center', size=ts)

        # Opus Text
        text = plt.text(l + w/2, b + h/2, '55 #2', ha='center', va='center', fontsize=80)
        underline_annotation(text)
        ax.annotate('Opus Number', xy=(l + w/8, b + h/2), xytext=(al, b + h/2 + 4*fy), arrowprops=arrow, ha='center', size=ts)
        fx, fy = .02, .1

        ax.annotate('Underlined\nIf Minor Key', xy=(l + w/8 - fx, b + h/2 - fy), xytext=(al, b + h/2 - 1.5*fy), arrowprops=arrow, ha='center', size=ts)

        # Key
        plt.text(l + space, b + space, 'f   2 / 2', ha='left', va='bottom', fontsize=20)
        #ax.add_patch(patches.Circle((0.5, 0.5), 0.1, fill=False, edgecolor='blue', lw=2))
        fy = .02
        ax.annotate('Key', xy=(l + space, b + space + fy), xytext=(al, b + 4*space), arrowprops=arrow, ha='center', size=ts)
        fx = .07
        tfy = -2*space
        ax.annotate('# quartet in Key', xy=(l + space + fx, b + space + fy), xytext=(al, b + tfy), arrowprops=arrow, ha='center', size=ts)
        fx = .1
        fy = .04
        ax.add_patch(patches.Circle((l + space + fx, b + space + fy), 0.04, fill=False, edgecolor='blue', lw=2))

        fx = .18
        fy = .02
        ax.annotate('Total quartets in Key', xy=(l + space + fx, b + space + fy), xytext=(al+fx, -fy), arrowprops=arrow, ha='center', size=ts)

        # Gray Bar
        ax.annotate('Gray Highlight \n Means Minuet \n is Third', xy=(l + w/2, b + ht/2), xytext=(.7, -.02), arrowprops=arrow, ha='center', va='center',size=ts)

        # Adjust the axis limits to make sure all elements are visible without distortion
        # The limits are set from 0 to 1 in both axes to match our elements' coordinate system.
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')  # Hide the axis for visual clarity
        ax.set_title("Cell Anatomy", fontsize=45, loc='center', x=.45)

        plt.savefig(outfile, bbox_inches='tight')
        plt.close()


if __name__ == '__main__':
    main()

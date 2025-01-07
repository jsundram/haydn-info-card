import click

from argparse import Namespace as attrdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch, cm

from pdfimage import PdfImage
import read as Quartets


def create_graph_paper(pdf_path, clr=colors.grey):
    # Initialize the canvas
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Define the size of the graph paper
    cell_w = .25*cm
    num_minor_rows, num_minor_cols = 4, 4
    num_major_rows, num_major_cols = int(height / (num_minor_rows * cell_w)) + 1, \
                                     int(width  / (num_minor_cols * cell_w)) + 1

    # Generate table data with nested tables
    data = []
    for _ in range(num_major_rows):
        major_row = []
        for _ in range(num_major_cols):
            # Each cell in the major grid contains a smaller table (minor grid)
            minor_data = [[None for _ in range(num_minor_cols)] for _ in range(num_minor_rows)]

            minor_table = Table(minor_data, colWidths=[cell_w] * num_minor_cols, rowHeights=[cell_w] * num_minor_rows)

            # Style for the minor grid
            minor_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, clr),
                ('BOX', (0,0), (-1,-1), 1, clr),
            ]))

            major_row.append(minor_table)
        data.append(major_row)

    # Create the major table
    table = Table(data, colWidths=[num_minor_cols*cell_w]*num_major_cols, rowHeights=[num_minor_rows*cell_w]*num_major_rows)

    # Style for the major grid
    table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'CENTER'),
        ('HALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))

    # Wrap and draw the table on the canvas
    table.wrapOn(c, width, height)
    table.drawOn(c, -10, 0)  # Adjust the position based on your layout

    return c


@click.command()
@click.option('-t', '--timeline-pdf', type=click.Path(exists=True), required=True, help="timeline pdf filepath")
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
@click.option('-d', '--datadir', type=click.Path(exists=True), required=True, help="data directory")
@click.option('-c', '--color-json', type=click.Path(exists=True), required=True, help="json file specifying colors")
def main(timeline_pdf, outfile, datadir, color_json):
    # Create and save the graph paper PDF
    g = colors.Color(.25, .25, .25, 1)
    # TODO: this is a hacky way to get a color to use once, maybe remove or pass in color directly?
    _ = Quartets.get_data(data_dir=datadir, colorf=color_json)  # initialize quartets
    bg_color = Quartets._bgcolor({'opus': 76})
    h_color = colors.Whiter(bg_color, .75)  # colors.Whiter(g, .25)
    pdf = create_graph_paper(outfile, h_color)

    width, height = letter
    page = attrdict(
        width=width,
        height=height,
        margin=attrdict(x=10, y=20),
    )

    # Read output of timeline.py
    # Swap width and height since we are rotating
    timeline = PdfImage(timeline_pdf,
        #height=height-2*page.margin.y,
        width=height - 2*page.margin.y,
        #width=width-2*page.margin.x,
        height=width-2*page.margin.x,
        kind='proportional',
        rotation=270
    )

    tiw, tih = timeline.wrapOn(pdf, page.width, page.height)
    timeline.drawOn(pdf, page.margin.x + tih, page.margin.y)
    pdf.save()


if __name__ == '__main__':
    main()

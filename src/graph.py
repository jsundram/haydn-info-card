import click

from argparse import Namespace as attrdict
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch, cm

from pdfimage import PdfImage
import read


def create_graph_paper(pdf_path, clr):
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


def get_highlight_color(color_dict, color_name):
    match color_name:
        case 'lavender':
            c, l = color_dict[color_name]['value'], .75
        case 'grey':
            c, l = color_dict[color_name]['value'], .25
        case _:
            l = .5
            try:
                c = color_dict[grid_color]['value']
            except KeyError:
                c = colors.Color(.25, .25, .25, 1)

    return colors.Whiter(c, l)


@click.command()
@click.option('-t', '--timeline-pdf', type=click.Path(exists=True), required=True, help="timeline pdf filepath")
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
@click.option('-c', '--color-json', type=click.Path(exists=True), required=True, help="json file specifying colors")
@click.option('-g', '--grid-color', type=str, required=True, help="name of color to use (must be in color_json above).")
def main(timeline_pdf, outfile, color_json, grid_color):
    color_dict = read.read_colors(color_json)
    h_color = get_highlight_color(color_dict, grid_color)

    pdf = create_graph_paper(outfile, h_color)

    width, height = letter
    page = attrdict(
        width=width,
        height=height,
        margin=attrdict(x=10, y=20),
    )

    # Swap width and height since we are rotating
    timeline = PdfImage(timeline_pdf,
        width=height - 2*page.margin.y,
        height=width - 2*page.margin.x,
        kind='proportional',
        rotation=270
    )

    tiw, tih = timeline.wrapOn(pdf, page.width, page.height)
    timeline.drawOn(pdf, page.margin.x + tih, page.margin.y)

    # Add copyright / version info
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.Whiter(colors.gray, .75))
    pdf.drawString(page.margin.x + 15, page.height - 19, '© Jason Sundram, ' + datetime.now().strftime("%Y-%m-%d"))
    # pdf.drawString(page.margin.x + 15, page.height - page.margin.y - tiw - 6, '© Jason Sundram, ' + datetime.now().strftime("%Y-%m-%d"))

    pdf.save()


if __name__ == '__main__':
    main()

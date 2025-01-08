import click
import copy
import glob
import json
import os
from math import cos, sin, pi, sqrt
from datetime import datetime

from argparse import Namespace as attrdict

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.shapes import Polygon
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.platypus.flowables import Flowable

import read as Quartets
from pdfimage import PdfImage

def get_styles():
    # Create Styles
    styles = getSampleStyleSheet()

    peters = copy.deepcopy(styles['BodyText'])
    peters.name = 'Peters'
    peters.alignment = TA_RIGHT
    peters.fontSize = 6
    peters.leading = 5
    peters.spaceAfter = 0
    peters.rightIndent = -5
    styles.add(peters)

    peterspent = copy.deepcopy(styles['BodyText'])
    peterspent.name = 'PetersPent'
    peterspent.alignment = TA_CENTER
    peterspent.fontSize = 6
    peterspent.leading = 4
    peterspent.spaceAfter = 0
    styles.add(peterspent)

    key = copy.deepcopy(styles['Italic'])
    key.name = 'Key'
    key.alignment = TA_LEFT
    key.fontSize = 8
    key.leading = 6.5
    key.leftIndent = -5
    key.fontName = 'ArialUnicode'
    styles.add(key)

    keypent = copy.deepcopy(styles['Key'])
    keypent.name = 'KeyPent'
    keypent.alignment = TA_CENTER
    keypent.leftIndent = 0
    keypent.leading = 6
    keypent.spaceBefore = 0
    keypent.spaceAfter = 0
    styles.add(keypent)

    nick = copy.deepcopy(styles['Italic'])
    nick.name = 'Nickname'
    nick.alignment = TA_CENTER
    nick.fontSize = 6
    nick.leading = 5
    styles.add(nick)

    opus = copy.deepcopy(styles['Title'])
    opus.name = 'Opus'
    opus.alignment = TA_CENTER
    opus.leading = opus.fontSize*1.5
    styles.add(opus)

    opusyear = copy.deepcopy(styles['Opus'])
    opusyear.name = 'OpusYear'
    opusyear.textColor = colors.gray
    styles.add(opusyear)

    opuspent = copy.deepcopy(styles['Opus'])
    opuspent.name = 'OpusPent'
    opuspent.leading = opus.fontSize + 2
    styles.add(opuspent)

    year = copy.deepcopy(styles['Key'])
    year.name = 'Year'
    year.alignment = TA_LEFT
    year.leftIndent=2
    styles.add(year)

    #opusnick = copy.deepcopy(styles['BodyText'])
    opusnick = copy.deepcopy(styles['Italic'])
    opusnick.name = 'OpusNickname'
    opusnick.alignment = TA_LEFT
    opusnick.fontSize = 7
    opusnick.leading = 6
    opusnick.leftIndent = -4
    styles.add(opusnick)

    opusage = copy.deepcopy(styles['BodyText'])
    opusage.name = 'OpusAge'
    opusage.alignment = TA_RIGHT
    opusage.fontSize = 7
    opusage.leading = 5
    opusage.rightIndent = -4
    opusage.textColor = colors.gray
    styles.add(opusage)

    footer = copy.deepcopy(styles['BodyText'])
    footer.name = 'Footer'
    footer.fontSize = 7
    #footer.spaceAfter = 0
    footer.leading = 8
    styles.add(footer)

    return styles


def expose_fonts(directory='/System/Library/Fonts/'):
    """Takes all the fonts in the system and calls registerFont on them"""
    ext = '*.ttf'
    files = glob.glob(directory + ext)
    files.extend(glob.glob(os.path.join(directory, 'Supplemental', ext)))
    files.extend(glob.glob('/Users/jsundram/Librar/Fonts/' + ext))

    print("Adding .ttf fonts from %s . . ." % directory)
    added = set()
    for file in files:
        # '/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf',
        base, ext = os.path.splitext(os.path.basename(file))
        name = base.replace(' ', '')
        try:
            pdfmetrics.registerFont(TTFont(name, file))
            added.add(name)
        except Exception as e:
            pass  # print(name, file, e)

    # for font in sorted(added): print(font)


def add_title(pdf, title, points, page, font="AppleChancery"):
    pdf.setFont(font, points)  # Set the font and size for the title

    # center...
    title_width = pdf.stringWidth(title, font, points)
    title_x = (page.width - title_width) / 2
    title_y = page.height - page.margin - points
    pdf.drawString(title_x, title_y, title)  # Draw the title on the canvas


def add_version(pdf, page):
    """ # print version number / authorship info at the top of the card
    pdf.saveState()
    pdf.translate(page.margin - .1*inch, page.height - 2*page.margin + page.cell_size)
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.Whiter(colors.gray, .75))
    pdf.drawString(0, -00, '© Jason Sundram, ' + datetime.now().strftime("%Y-%m-%d"))
    # pdf.drawString(0, -10, 'https://haydnenthusiasts.org/card')
    pdf.restoreState()
    """

    # Add copyright / version info on the bottom right
    pdf.saveState()
    pdf.translate(page.width - 20, page.margin + 94)
    pdf.rotate(270)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.Whiter(colors.gray, .75))
    pdf.drawString(0, -00, '© Jason Sundram, ' + datetime.now().strftime("%Y-%m-%d"))
    pdf.restoreState()


def get_cell_table(q, cell_size, styles):
    bg_color = Quartets._bgcolor(q)
    h_color = colors.Whiter(bg_color, .75)
    f_color = '#000000'
    fmt = '<u color="%s">%s</u>' if Quartets._minor(q) else '<font color="%s">%s</font>'
    v = q.get('peters', 0) or 0
    vol = ['', 'I', 'II', 'III', 'IV'][v]

    s = cell_size
    keytext = "%s%s%d/%d" % (Quartets._key(q), '&nbsp;'*2, q['key_number'], q['key_count'])
    minuet = Quartets._minuets(q)[0]
    # op, start, stop, weight, colour, cap, dashes, join
    # op: LINEBELOW, LINEABOVE, LINEBEFORE and LINEAFTER
    # cap: 0 butt, 1 round, 2 square
    # join: 0 miter, 1 round, 2 bevel
    highlight = colors.Color(.5, .5, .5, .2)  # h
    # line = ('LINEAFTER', (0, 1), (0, 2), 10, h, 0) if minuet == 2 else ('LINEBELOW', (0, 3), (0, 3), 10, h, 0)
    line = ("BACKGROUND", (0, 3), (0, 3), highlight if minuet == 3 else None)

    return Table(
        [
            [Paragraph(Quartets._name(q), styles["Nickname"])],
            [Paragraph(vol, styles["Peters"])],
            [Paragraph(fmt % (f_color, Quartets._title(q)), styles["Opus"])],
            [Paragraph(keytext, styles["Key"])],
        ],
        colWidths=[s],
        rowHeights=[0.125 * s, 0.125 * s, .615 * s,  0.135 * s],
        style=TableStyle([
            # Nickname
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (0, 0), "BOTTOM"),
            ("TEXTCOLOR", (0, 0), (0, 0), colors.black),
            ("BACKGROUND", (0, 0), (0, 0), h_color),

            # Minuet Indicator
            line,

            # Number
            ("ALIGN", (0, 2), (0, 2), "CENTER"),
            ("VALIGN", (0, 2), (0, 2), "MIDDLE"),

            # Global
            # ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            # ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ])
    )


def get_info_table(info, s, styles):
    return Table(
        [
            [],
            [],
            [],
            [Paragraph(info, styles["Year"])],
        ],
        colWidths=[s],
        rowHeights=[0.125 * s, 0.125 * s, .625 * s, 0.125 * s],
    )


def get_lead_table(q, info, s, styles):
    bg_color = Quartets._bgcolor(q)
    h_color = colors.Whiter(bg_color, .75)
    return Table(
        [
            [Paragraph(str(info['year'] - 1732), styles["OpusAge"])],
            [],
            [Paragraph(str(info['year']), styles["OpusYear"])],
            [Paragraph(info['nickname'].upper(), styles["OpusNickname"])],
        ],
        colWidths=[s],
        rowHeights=[0.125 * s, 0.125*s, 0.625 * s, 0.125 * s],
        style=TableStyle([
            # Nickname
            ("ALIGN", (0, 3), (0, 3), "CENTER"),
            ("VALIGN", (0, 3), (0, 3), "BOTTOM"),
            # ("BACKGROUND", (0, 3), (0, 3), h_color),

            # Number
            ("ALIGN", (0, 2), (0, 2), "CENTER"),
            ("VALIGN", (0, 2), (0, 2), "MIDDLE"),
            # ("BACKGROUND", (0, 2), (0, 2), colors.magenta),

            # Global
            # ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            # ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ])
    )


def build_table(quartets, page, styles, events):
    table_style = TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])

    # Create the table.
    table_data = [[None] * page.columns for _ in range(page.rows)]

    o42 = [q for q in quartets if q['opus'] == 42][0]
    o103 = [q for q in quartets if q['opus'] == 103][0]
    quartets = [q for q in quartets if q['opus'] > 2 and q['opus'] not in {42, 103}]

    prev = None
    row, col = -1, 1
    for q in quartets:
        bg_color = Quartets._bgcolor(q)
        if bg_color != prev:
            opus_data = events[q['opus']]
            prev = bg_color
            row += 1
            col = 1
            table_data[row][0] = get_lead_table(q, opus_data, page.cell_size, styles)
            table_style.add('OUTLINE', (0, row), (0, row), .25, colors.black)

        table_data[row][col] = get_cell_table(q, page.cell_size, styles)
        table_style.add('OUTLINE', (col, row), (col, row), .25, colors.black)
        col += 1

    row, col = 3, 7
    table_data[row][col] = get_lead_table(o42, events[42], page.cell_size, styles)
    table_style.add('OUTLINE', (col, row), (col, row), .25, colors.black)
    row, col = 3, 8
    table_data[row][col] = get_cell_table(o42, page.cell_size, styles)
    table_style.add('OUTLINE', (col, row), (col, row), .25, colors.black)

    row, col = 9, 5
    table_data[row][col] = get_lead_table(o103, events[103], page.cell_size, styles)
    table_style.add('OUTLINE', (col, row), (col, row), .25, colors.black)
    row, col = 9, 6
    table_data[row][col] = get_cell_table(o103, page.cell_size, styles)
    # Purposely omit the outline on 103, so that it only has 2 / 4 sides outlined:
    #table_style.add('OUTLINE', (col, row), (col, row), .25, colors.black)

    # Create the table and style it
    return Table(
        table_data,
        colWidths=page.cell_size,
        rowHeights=page.cell_size,
        style=table_style
    )


class Pentagon(Flowable):
    """A custom flowable that draws a centered pentagon within cell dimensions and includes text"""
    def __init__(self, q, cell_width, cell_height, styles):
        Flowable.__init__(self)
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.q = q
        self.styles = styles

    def draw(self):
        points = []
        x, y = 0, 0
        size = self.cell_width / 2.0
        # offset = math.pi / 2  # Offset by 90 degrees to have a flat top
        offset = 3*pi / 2 # Offset by 270 degrees to have a flat bottom
        for i in range(5):
            angle = 2 * pi * i / 5 - offset
            points.append((x + size * cos(angle), y + size * sin(angle)))

        # Create a clipping path with the pentagon's shape
        path = self.canv.beginPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        path.close()

        self.canv.saveState()
        self.canv.clipPath(path, stroke=0, fill=0)
        # print(points[1][1], points[2][1])
        # distance from top to bust
        bust = self.cell_height / 2.0 - points[1][1]
        # distance from bust to hips
        hips = self.cell_height / 2.0 - points[2][1] - bust
        self.draw_table(hips, bust)
        self.canv.restoreState()

        # Draw the edges of the pentagon
        # points go clockwise from top (0 is top, 4 is leftmost)
        self.canv.setLineWidth(.5)
        for i in range(5):
            start_point = points[i]
            end_point = points[(i + 1) % 5]
            self.canv.line(start_point[0], start_point[1], end_point[0], end_point[1])

        #self.canv.circle(points[0][0], points[0][1], 3)

    def draw_table(self, hips, bust):
        table = get_cell_table(self.q, self.cell_width, self.styles)
        q, cell_size, styles = self.q, self.cell_height, self.styles
        bg_color = Quartets._bgcolor(q)
        h_color = colors.Whiter(bg_color, .75)
        f_color = '#000000'
        fmt = '<u color="%s">%s</u>' if Quartets._minor(q) else '<font color="%s">%s</font>'
        v = q.get('peters', 0) or 0
        vol = ['', 'I', 'II', 'III', 'IV'][v]

        s = cell_size - bust - hips
        peters = (0, 0)
        nick = (0, 1)
        opus = (0, 3)
        key = (0, 4)
        keytext = "%s%s%d/%d" % (Quartets._key(q), '&nbsp;'*2, q['key_number'], q['key_count'])
        table = Table(
            [
                [Paragraph(vol, styles["PetersPent"])],
                [Paragraph(Quartets._name(q), styles["Nickname"])],
                [],
                [Paragraph(fmt % (f_color, Quartets._title(q)), styles["OpusPent"])],
                [Paragraph(keytext, styles["KeyPent"])],
                []  # [Paragraph("what", styles['Key'])]
            ],
            colWidths=[cell_size],
            rowHeights=[bust/2, bust/2, 0, .75*hips, 0.25*hips, s],
            style=TableStyle([
                # Peters
                # ("BACKGROUND", peters, peters, colors.magenta),

                # Nickname
                ("ALIGN", nick, nick, "CENTER"),
                ("VALIGN", nick, nick, "BOTTOM"),
                ("TEXTCOLOR", nick, nick, colors.black),
                ("BACKGROUND", nick, nick, h_color),


                # Opus
                ("ALIGN", opus, opus, "CENTER"),
                #("VALIGN", opus, opus, "BOTTOM"),
                #("BACKGROUND", opus, opus, h_color),

                # Key
                ("ALIGN", key, key, "CENTER"),
                # ("BACKGROUND", key, key, colors.magenta),
                #("VALIGN", opus, opus, "BOTTOM"),

                # Global
                # ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                # ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.red),
            ])
        )
        table.wrapOn(self.canv, self.cell_width, self.cell_height)
        table.drawOn(self.canv, -self.cell_width/2.0, -self.cell_height / 2.0)


def build_earlies(quartets, page, styles, events):
    earlies = [q for q in quartets if q['opus'] <= 2]
    cell_width = (page.width  - 2 * page.margin - page.cell_size) / len(earlies)

    data = [get_lead_table(earlies[0], events[1], page.cell_size, styles)]
    widths = [page.cell_size]
    for e in earlies:
        data.append(Pentagon(e, cell_width, cell_width, styles))
        widths.append(cell_width)

    table = Table([data], colWidths=widths, rowHeights=page.cell_size)

    table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('OUTLINE', (0, 0), (0, 0), .25, colors.black),
        # ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    return table


def build_footer(page, styles):
    text = """*Due to the popularity of the Peters Edition, it was often said that there were 83 Haydn quartets. However, this includes 6 quartets in opus 3, not written by Haydn, opus 1#5, a transcription of symphony A, opus 2#3 and 2#5, which are actually sextets missing two horn parts, and counts each of the movements of The 7 Last Words (an arrangement of an orchestral piece) as its own quartet. It also omits Opus 1#0, sometimes known as Opus 0."""

    text = """* The traditional number of 83 Quartets has been updated due to the new collected edition <i>Joseph Haydn: Werke</i> and reflects the removal of: Opus 1#5 (Symphony 'A' Hob. I:107), Opus 2#3 and Opus 2#5 (Sextets Hob II:21, 22), the 6 quartets in Opus 3 (spurious, probably written by Romanus Hoffstetter (1742-1815)), and each of the individual movements of Haydn's arrangement of <i>7 Last Words</i>. However, Opus 1 #0 (aka 'Opus 0') was rescued from Hob.II:6, and is now included among the quartets, although not present in Peters. The Early quartets were written for Baron Fürnberg but composition year is uncertain. The .5 reflects the half-finished status of Opus 103."""

    cell_width = page.width - 2 * page.margin
    cell_height = page.title_fudge
    return Table(
        [
            [Paragraph(text, styles["Footer"])],
        ],
        colWidths=[cell_width],
        rowHeights=[cell_height],
        style = TableStyle([
            #('GRID', (0,0), (-1,-1), 1, colors.black)
        ])
    )


@click.command()
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
@click.option('-a', '--annotations-pdf', type=click.Path(exists=True), required=True, help="annotations.pdf for overlay")
@click.option('-c', '--color-json', type=click.Path(exists=True), required=True, help="json file specifying colors")
@click.option('-d', '--datadir', type=click.Path(exists=True), required=True, help="data directory")
def main(outfile, annotations_pdf, color_json, datadir):
    quartets = Quartets.get_data(data_dir=datadir, colorf=color_json, extend=False)
    events = Quartets.get_opera()

    expose_fonts()

    # Define the page size and margins, and rows/columns
    pagesize = letter
    page = attrdict(
        width=pagesize[0],
        height=pagesize[1],
        margin=.5*inch,
        rows=10,
        columns=9,
        title_fudge=40,  # need to scootch the table down a bit to fit the title
        table_fudge=6
    )

    # Calculate the maximum cell size for square cells
    page.cell_size = min((page.width  - 2 * page.margin) / page.columns,
                         (page.height - 2 * page.margin) / page.rows)

    # Create the PDF canvas
    pdf = canvas.Canvas(outfile, pagesize=pagesize)
    styles = get_styles()

    add_title(pdf, 'The 67.5* Haydn Quartets', 24, page, 'AppleChancery')

    table = build_earlies(quartets, page, styles, events)
    w, h = table.wrapOn(pdf, page.width - 2 * page.margin, page.height - 2 * page.margin)
    x = (page.width - w) / 2
    y = page.height - h - page.margin - page.title_fudge
    page.table_fudge = h
    table.drawOn(pdf, x, y)

    table = build_table(quartets, page, styles, events)
    w, h = table.wrapOn(pdf, page.width - 2 * page.margin, page.height - 2 * page.margin)
    x = (page.width - w) / 2
    y = (page.height - h - page.margin - page.table_fudge - page.title_fudge)
    page.last_fudge = h
    table.drawOn(pdf, x, y)

    table = build_footer(page, styles)
    w, h = table.wrapOn(pdf, page.width - 2 * page.margin, page.height - 2 * page.margin)
    x = (page.width - w) / 2
    y = (page.height - h - page.margin - page.table_fudge - page.title_fudge - page.last_fudge)
    table.drawOn(pdf, x, y)

    # Show an Annotation to explain the table (output of annotate.py)
    s = page.cell_size*2.5
    explainer = PdfImage(annotations_pdf,
        height=s,
        width=s,
        kind='proportional'
    )
    explainer.drawOn(pdf, page.margin + page.cell_size*7 + 1, page.margin + 3*page.cell_size)

    add_version(pdf, page)

    pdf.save()


if __name__ == '__main__':
    main()

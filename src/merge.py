import click
from pypdf import PdfWriter


@click.command()
@click.option('-f', '--front-pdf', type=click.Path(exists=True), required=True, help="Front of page pdf path")
@click.option('-b', '--back-pdf', type=click.Path(exists=True), required=True, help="Back of page pdf path")
@click.option('-o', '--outfile', type=click.Path(writable=True), required=True, help="output filename")
def main(front_pdf, back_pdf, outfile):
    with PdfWriter() as merger:
        for pdf in [front_pdf, back_pdf]:
            merger.append(pdf)

        merger.write(outfile)


if __name__ == '__main__':
    main()

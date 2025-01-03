# Haydn Info Card

## To Generate the latest card:

1. Make whatever edits need to be made.
2. Run `python3 annotate.py` to generate "annotate.pdf", which is the legend/explainer for the card.
3. Run `python3 table-portrait.py` for the front of the card, which generates "table-portrait-test.pdf". This depends on annotate.pdf
4. Run `python3 timeline.py` which generates "timeline.pdf"
5. Run `python3 graph.py` for the back of the card, which generates "graph_paper.pdf"
6. Open table-portrait-test.pdf in Preview.app
7. In Preview, click "Show Thumbnails" 
8. Drag graph_paper.pdf into the "Thumbnails" window
9. Click "Save"
10. Rename table-portrait-test.pdf to "Haydn Info Card - Sundram - MM-DD-YYYY.pdf"


## Version History
* 2024-04-14 -- first official version of the card with the legend on it.
* 2024-07-15 -- add nickname "lemon" to opus 64#2
* 2024-07-26 -- add nickname "da capo" to opus 1#3
* 2024-10-28 -- added haydn's age during the year of composition to the upper right corner for each opus block.
* 2024-01-02 -- fix a small overlap between the cell anatomy graphic and the table borders.

# Haydn Info Card

## To Generate the latest card:

1. Make whatever edits need to be made.
2. Run `uv run src/annotate.py -o output/annotate.pdf` to generate "annotate.pdf", which is the legend/explainer for the card.
3. Run `uv run src/table-portrait.py -o ./output/table-portrait-test.pdf -a ./output/annotate.pdf -c ./colors/sashamaps.json -d ./data` for the front of the card, which generates "table-portrait-test.pdf". 
4. Run ` uv run src/timeline.py -o output/timeline.pdf -c ./colors/sashamaps.json -d ./data` which generates "timeline.pdf"
5. Run `uv run src/graph.py -t output/timeline.pdf -o output/graph_paper.pdf -d ./data` for the back of the card, which generates "graph_paper.pdf"
6. Run `uv run src/merge.py -f output/table-portrait-test.pdf -b output/graph_paper.pdf -o output/merged.pdf`
7. Rename merged.pdf to "Haydn Info Card - Sundram - MM-DD-YYYY.pdf"


## Version History
* 2024-04-14 -- first official version of the card with the legend on it.
* 2024-07-15 -- add nickname "lemon" to opus 64#2
* 2024-07-26 -- add nickname "da capo" to opus 1#3
* 2024-10-28 -- added haydn's age during the year of composition to the upper right corner for each opus block.
* 2024-01-02 -- fix a small overlap between the cell anatomy graphic and the table borders.

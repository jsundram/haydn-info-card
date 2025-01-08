#!/bin/bash

# generate the explainer graphic
uv run src/annotate.py -o output/annotate.pdf
# create the table (front of card) and overlay the explainer
uv run src/table-portrait.py -o ./output/table-portrait-test.pdf -a ./output/annotate.pdf -c ./colors/sashamaps.json -d ./data
# generate the timeline
uv run src/timeline.py -o output/timeline.pdf -c ./colors/sashamaps.json -d ./data
# generate the graph paper and overlay the timeline on it. (-g lavender for susie)
uv run src/graph.py -t output/timeline.pdf -c ./colors/sashamaps.json -o output/graph_paper.pdf -g grey
# merge the table (front of card) and the graph paper (back of card)
uv run src/merge.py -f output/table-portrait-test.pdf -b output/graph_paper.pdf -o output/merged.pdf
# rename the output from merged.pdf to "Haydn Info Card - Sundram - YYYY-MM-DD.pdf" 
mv output/merged.pdf output/Haydn\ Info\ Card\ -\ Sundram\ -\ $(date +%Y-%m-%d).pdf

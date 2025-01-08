#!/bin/bash

# generate the explainer graphic
uv run src/annotation.py -o output/annotation.pdf
# create the table (front of card) and overlay the explainer
uv run src/quartet-info-table.py -o ./output/front.pdf -a ./output/annotation.pdf -c ./colors/sashamaps.json -d ./data
# generate the timeline
uv run src/timeline.py -o output/timeline.pdf -c ./colors/sashamaps.json -d ./data
# generate the graph paper and overlay the timeline on it. (-g lavender for susie)
uv run src/graph_paper.py -t output/timeline.pdf -c ./colors/sashamaps.json -o output/back.pdf -g grey
# merge the table (front of card) and the graph paper (back of card)
uv run src/merge.py -f output/front.pdf -b output/back.pdf -o output/merged.pdf
# rename the output from merged.pdf to "Haydn Info Card - Sundram - YYYY-MM-DD.pdf" 
mv output/merged.pdf output/Haydn\ Info\ Card\ -\ Sundram\ -\ $(date +%Y-%m-%d).pdf

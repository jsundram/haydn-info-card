#!/bin/bash

OUTDIR="./output"

# 1. Generate the explainer graphic.
uv run src/annotation.py -o ${OUTDIR}/annotation.pdf

# 2. Create the table (front of card) and overlay the explainer.
uv run src/quartet-info-table.py -o ${OUTDIR}/front.pdf -a ${OUTDIR}/annotation.pdf -c ./colors/sashamaps.json -d ./data

# 3. Generate the timeline.
uv run src/timeline.py -o ${OUTDIR}/timeline.pdf -c ./colors/sashamaps.json -d ./data

# 4. Generate the graph paper and overlay the timeline on it (-g lavender for susie).
uv run src/graph_paper.py -t ${OUTDIR}/timeline.pdf -c ./colors/sashamaps.json -o ${OUTDIR}/back.pdf -g grey

# 5. Merge the table (front of card) and the graph paper (back of card).
uv run src/merge.py -f ${OUTDIR}/front.pdf -b ${OUTDIR}/back.pdf -o ${OUTDIR}/merged.pdf

# 6. Rename the output from merged.pdf to "Haydn Info Card - Sundram - YYYY-MM-DD.pdf" 
mv ${OUTDIR}/merged.pdf ${OUTDIR}/Haydn\ Info\ Card\ -\ Sundram\ -\ $(date +%Y-%m-%d).pdf

# 7. Cleanup
rm ${OUTDIR}/annotation.pdf
rm ${OUTDIR}/timeline.pdf
rm ${OUTDIR}/front.pdf
rm ${OUTDIR}/back.pdf

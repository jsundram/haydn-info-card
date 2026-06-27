# TODO

- [x] Move data files to `data` folder
- [x] write intermediate pdf files into a subdirectory
- [x] Get it working with `uv` for dependencies
  - [ ] `uv init haydn-info-card`
  - [ ] `uv pip sync requirements.txt`
    - [ ] this appeared to do nothing

  - [ ] `uv add reportlab==4.1.0` and similar for the rest of requirements.txt
  - [ ] `uv run annotate.py` etc
  - [ ] 

- [x] Figure out how to concatenate pdf files (seems like [pdfmerger](https://stackoverflow.com/questions/3444645/merge-pdf-files) would work.)
- [x] automatically name the output file appropriately
- [ ] instructions / script for adding to haydnenthusiasts.org once I figure out if I want to do that...
  - [ ] git submodule + filename parsing cleverness in jinja? https://gist.github.com/ZhuoyunZhong/2c08c8549616e03b7f508fea64130558
  - [ ] "warning: The following paths are not up to date and were left despite sparse patterns:"

- [ ] refactor ...
  - [x] graph.py -- make background color specification better
  - [ ] table-portrait.py 
    - [x] move hard-coded events into read.py
    - [ ] There are 100 lines for font styles ...

  - [ ] read.py
    - [ ] this does a lot ...

  - [ ] data/
    - [ ] make sourcing clearer and make scripts to generate these files

- [ ] Visual: 
  - [x] Change grid color (back) to gray?
  - [x] Add my name / contact info / link to haydnenthusiasts.org


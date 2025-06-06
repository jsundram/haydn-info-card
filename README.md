# Haydn Info Card

Find out more about this card [here](https://haydnenthusiasts.org/haydn_card.html)

## To Generate the latest card:

1. Make whatever edits need to be made.
2. `run ./make_card.sh`
3. This will create the file  `output/Haydn Info Card - Sundram - YYYY-MM-DD.pdf`
4. You may wish to update [haydnenthusiasts.org](https://github.com/jsundram/haydnenthusiasts.org), running the build script there should take care of pulling the latest, and the post-commit hook will take care of the deploy.
5. You may also wish to update the screenshots which are included on haydnethusiasts.org; modify `./make_card.sh` to uncomment out the lines that generate those images.


## Version History
* 2024-04-14 -- first official version of the card with the legend on it.
* 2024-07-15 -- add nickname "lemon" to opus 64#2
* 2024-07-26 -- add nickname "da capo" to opus 1#3
* 2024-10-28 -- added haydn's age during the year of composition to the upper right corner for each opus block.
* 2025-01-02 -- fix a small overlap between the cell anatomy graphic and the table borders.
* 2025-01-07 -- move title down, add copyright/version info to both sides of card. Gray Graph Paper.
* 2025-01-10 -- add a new vertical timeline to the back of the card.
* 2025-05-08 -- use the more common "Graveyard Largo" nickname for opus 76#5.

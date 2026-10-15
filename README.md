# mse-importer
Small tool to import cards into Magic Set Editor

## Requirements
This tool requires Python 3

If you want to manually edit `.mse-set` files, I recommend using 7z: https://www.7-zip.org/download.html  

## How to use it
First generate the content of the set file:
- Store the list of cards you want to import in a txt file, one card name per line.
- Open a command line and run  `python mse_generate.py <filename>.txt `
. Wait until the program finishes
- The formatted file will be in `results.txt`

Now add the cards to an existing MSE set file (automated):
- Create/open an MSE set and save it (it must exist as a `.mse-set` file)
- Run:
  - `python mod_set.py <cards>.txt <your-set>.mse-set -o output.mse-set`
- Open `output.mse-set` in MSE, your cards should be there.

## TODO
Create an MSE Set instead of requiring an existing `.mse-set`

Specify a full set directly

Allow Multiverse ID's

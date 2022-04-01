# Building a private sourmash database

This directory contains a Makefile that will build a private database
for the 64 genomes used in
[Awad et al., 2017](https://www.biorxiv.org/content/10.1101/155358v3).

Run `make` to run the entire pipeline.  (You'll need sourmash v4.4.0
installed.)

The Makefile does the following:

## 1. Download and unpack the genomes

The Makefile runs curl to download the genomes from
[the OSF project](https://osf.io/vbhy5), and then unpacks them.

## 2. Build a summary of the genomes in the 'fromfile' format

Next, the Makefile uses the script `../fasta-to-fromfile.py` to
scan the genomes and produce a summary file, `build.csv`, that
contains names and source genomes for sourmash signatures.

## 3. Create the signatures using `sourmash sketch`

Finally, the Makefile runs
```
sourmash sketch fromfile build.csv -p dna -o podar-ref.zip
```
to sketch all of the genomes in `build.csv`.  The parameter string `-p
dna` tells sourmash to construct DNA sketches using the default parameters;
any number of [parameter strings](https://sourmash.readthedocs.io/en/latest/sourmash-sketch.html#parameter-strings) can be provided, one with each `-p`.

The names for the output signatures are taken from `build.csv`.

## Finished!

You can run `sourmash sig summarize podar-ref.zip` to get a summary of
the contents of the zip file, or `sourmash sig describe podar-ref.zip`
to get a listing of all the signatures.

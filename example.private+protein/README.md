# Building a private sourmash database with DNA and protein.

This directory contains a Makefile that will build a private database
for the 64 genomes used in
[Awad et al., 2017](https://www.biorxiv.org/content/10.1101/155358v3).

This example extends [example.private](../example.private/) with
gene finding on the input genomes using prodigal.

Run `make` to run the entire pipeline.  (You'll need sourmash v4.4.0
installed, along with snakemake >= 6 and prodigal.)

The Makefile does the following:

## 1. Download and unpack the genomes

The Makefile runs curl to download the genomes from
[the OSF project](https://osf.io/vbhy5), and then unpacks them
into the `podar-ref/` directory.

## 2. Produce amino acid files containing the genes.

The Makefile will next run the snakemake workflow in `Snakefile` to
build `_protein.faa` files for all the `.fa` files in the `podar-ref/`
directory.

## 3. Build a summary of the files in the 'fromfile' format

Next, the Makefile uses the script `../fasta-to-fromfile.py` to scan
the genomes and proteomes and then produces a summary file,
`build.csv`, that contains names and source files for building
sourmash signatures.

Here, `fasta-to-fromfile` uses the identifiers present in the sequences
to connect the genome and proteome so that they are sketched with the same
names.

## 4. Create the signatures using `sourmash sketch`

Finally, the Makefile runs
```
sourmash sketch fromfile build.csv -p dna -p protein -o podar-ref.zip
```
to sketch all of the genomes in `build.csv`.  The parameter string `-p
dna` tells sourmash to construct DNA sketches, and the parameter
string `-p protein` constructs protein sketches.  Here, `sourmash
sketch fromfile` automatically selects the genome for building the DNA
sketches and the proteome for building the protein sketches.

The names for the output signatures are taken from `build.csv`.

## Finished!

You can run `sourmash sig summarize podar-ref.zip` to get a summary of
the contents of the zip file, or `sourmash sig describe podar-ref.zip`
to get a listing of all the signatures.

You can get a detailed listing of just one pair of the signatures by using
the `--include-db-pattern` option for `sig describe`:
```
sourmash sig describe podar-ref.zip --include NZ_FWDH
```

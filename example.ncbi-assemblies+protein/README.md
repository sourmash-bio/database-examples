# Building a sourmash database from NCBI assemblies

This directory contains a Makefile that will build a sourmash database
for the genome in `GCF_000018865.1_ASM1886v1_genomic.fna`, as well
as construct a proteome using prodigal and build a protein signature.

Run `make` to run the entire pipeline.  (You'll need sourmash v4.4.0
installed.)

The Makefile does the following:

## 1. Produce amino acid files containing the genes.

The Makefile will first run the snakemake workflow in `Snakefile` to
build `_protein.faa` files for all the `.fna` files in the current
directory using prodigal.

## 2. Build a summary of the genome and proteome files in the 'fromfile' format

Next, the Makefile uses the script `../genbank-to-fromfile.py` to
scan the genomes and produce a summary file, `build.csv`, that
contains names and source genomes for sourmash signatures.
(In this case, there's only one genome, note!)

Names for the genomes are taken from the NCBI `assembly_summary.txt` file
that is distributed with Refseq and Genbank assemblies.

## 3. Create the signatures using `sourmash sketch`

Finally, the Makefile runs
```
sourmash sketch fromfile build.csv -p dna -p protein -o all.zip
```
to sketch all of the genomes in `build.csv`.  The parameter string `-p
dna` tells sourmash to construct DNA sketches using the default parameters,
and `-p protein` tells sourmash to construct protein sketches, too.

The names for the output signatures are taken from `build.csv`.

## Finished!

You can run `sourmash sig summarize all.zip` to get a summary of
the contents of the zip file, or `sourmash sig describe all.zip`
to get a listing of all the signatures.

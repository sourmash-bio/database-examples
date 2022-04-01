all: all.zip

clean:
	rm -f GCF_000018865.1_ASM1886v1_protein.faa build.csv all.zip

# make proteins with prodigal
GCF_000018865.1_ASM1886v1_protein.faa: GCF_000018865.1_ASM1886v1_genomic.fna
	snakemake -j 1

# build a 'fromfile' for sourmash to use
build.csv: GCF_000018865.1_ASM1886v1_protein.faa
	../genbank-to-fromfile.py *.fna *.faa -o build.csv -S assembly_summary.txt

# build the signature database using sourmash
all.zip: build.csv
	sourmash sketch fromfile build.csv -o all.zip -p dna -p protein

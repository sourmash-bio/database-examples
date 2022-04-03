all: clean test

clean:
	snakemake -s Snakefile.test --delete-all-output -j 1

test:
	snakemake -s Snakefile.test -j 1

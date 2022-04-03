all: all.zip

clean:
	rm -f build.csv all.zip

# build a 'fromfile' for sourmash to use
build.csv: ../genbank-to-fromfile.py
	../genbank-to-fromfile.py *.gz -o build.csv -S assembly_summary.txt

# build the signature database using sourmash
all.zip: build.csv
	sourmash sketch fromfile build.csv -o all.zip -p dna -p protein

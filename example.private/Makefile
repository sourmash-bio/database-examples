all: podar-ref.zip

clean:
	rm -f build.csv podar-ref.zip

# download the ref genomes
podar-ref/:
	mkdir -p podar-ref
	curl -L https://osf.io/download/vbhy5 -o podar-ref/podar-ref.tar.gz
	cd podar-ref/ && tar xzf podar-ref.tar.gz
	rm podar-ref/podar-ref.tar.gz

# build a 'fromfile' for sourmash to use
build.csv: podar-ref/
	../fasta-to-fromfile.py podar-ref/*.fa -o build.csv

# build the signature database using sourmash
podar-ref.zip: build.csv
	sourmash sketch fromfile build.csv -o podar-ref.zip -p dna

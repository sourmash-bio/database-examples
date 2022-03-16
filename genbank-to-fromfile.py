#! /usr/bin/env python3
"""
Summarize a bunch of GenBank-style FASTA files into 'sourmash sketch fromfile'
format for batch processing.
"""
import sys
import argparse
import screed
import csv
import os
import shutil
from kiln import InputFile, OutputRecords

from sourmash.tax.tax_utils import MultiLineageDB
from sourmash.logging import error, notify


def main():
    p = argparse.ArgumentParser()
    p.add_argument('filenames', nargs='+')
    p.add_argument('-o', '--output-csv', required=True)
    p.add_argument('-t', '--taxonomy-db', action='append', default=[],
                   required=True)
    args = p.parse_args()

    tax_info = MultiLineageDB.load(args.taxonomy_db,
                                   keep_full_identifiers=False)
    def get_name(ident, full_ident):
        """
        Use taxonomy to name things in GenBank/GTDB style.
        """
        # get lineage
        lineage = tax_info[ident]
        x = list(lineage)

        # remove to last non-empty name
        while not x[-1].name:
            x.pop()

        # ...use that name.
        name = x[-1].name
        return f"{full_ident} {name}"

    # all the output.
    output = OutputRecords(args.output_csv)
    output.open()

    # track Inputfile objects by name -
    fileinfo_d = {}

    n = 0
    for filename in args.filenames:
        print(f"processing file '{filename}'")

        if os.path.getsize(filename) == 0:
            error(f"** ERROR: '{filename}' has zero size.")
            sys.exit(-1)

        fileinfo = InputFile()

        # split filenames of the format 'GCF_003317655.1_genomic.fna.gz'
        # into identifier 'GCF_003317655.1' and discard the rest.
        basename = os.path.basename(filename)
        idents = basename.split('_')
        assert len(idents) >= 2

        # 'full_ident' keeps version, 'ident' does not - use latter for
        # tax lookup.
        full_ident = "_".join(idents[:2])
        assert full_ident.startswith('GCA_') or full_ident.startswith('GCF_')
        ident = full_ident
        if '.' in ident:
            ident = ident.split('.', 1)[0]

        fileinfo.ident = ident
        fileinfo.full_ident = full_ident
        fileinfo.name = get_name(ident, full_ident)

        # this may require refinement?
        if filename.endswith('.faa.gz') or filename.endswith('.faa'):
            fileinfo.protein_filename = filename
        elif filename.endswith('.fna.gz') or filename.endswith('.fna'):
            fileinfo.genome_filename = filename

        # do we already have this identifer? guess that we're getting
        # the other moltype now. ('merge' will check.)
        previous = fileinfo_d.get(fileinfo.ident)
        if previous is not None:
            print("(merging into existing record)")
            fileinfo = fileinfo.merge(previous)
        else:
            print(f"(new record for name '{fileinfo.name}')")

        # double check & save
        assert not fileinfo.is_empty(), fileinfo.__dict__
        fileinfo_d[fileinfo.ident] = fileinfo

    # write the things!
    for n, (ident, fileinfo) in enumerate(fileinfo_d.items()):
        output.write_record(fileinfo)

    output.close()
    print('---')
    print(f"wrote {len(fileinfo_d)} entries to '{args.output_csv}'")

    return 0

if __name__ == '__main__':
    sys.exit(main())

#! /usr/bin/env python3
"""
"""
import sys
import argparse
import screed
import csv
import os
import shutil
from kiln import InputFile, OutputRecords, check_dna, remove_extension

from sourmash.tax.tax_utils import MultiLineageDB
from sourmash.logging import notify, error

def main():
    p = argparse.ArgumentParser()
    p.add_argument('filenames', nargs='*', help="names of files to process")
    p.add_argument('-F', '--file-list', action='append',
                   help='text files with filenames to add to command line',)
    p.add_argument('-o', '--output-csv', required=True)
    p.add_argument('--ident-from-filename', action='store_true',
                   help="determine identifer from filename prefixes")
    args = p.parse_args()

    if not args.filenames:
        args.filenames = []

    # load --file-list
    if args.file_list:
        for ff in args.file_list:
            with open(ff, 'rt') as fp:
                filelist = [ x.strip() for x in fp ]
            notify(f"Loaded {len(filelist)} entries from '{ff}'")
        args.filenames.extend(filelist)

    if not args.filenames:
        error("** ERROR: no input filenames and no --file-list provided.")
        sys.exit(-1)

    output = OutputRecords(args.output_csv)
    output.open()

    fileinfo_d = {}

    n = 0
    for filename in args.filenames:
        print(f"processing file '{filename}'")

        fileinfo = InputFile()

        record = None
        for record in screed.open(filename):
            record_name = record.name
            break

        if record is None:
            assert 0, f"no sequences in {filename}"

        is_dna = check_dna(record.sequence)

        # figure out identifiers from first record
        if not args.ident_from_filename:
            full_ident, *remainder = record_name.split(' ', 1)

            ident = full_ident
            if '.' in ident:
                ident = ident.split('.', 1)[0]

            fileinfo.ident = ident
            fileinfo.full_ident = full_ident
            fileinfo.name = record_name
        else:
            # should use the same approach as genome grist...
            basename = os.path.basename(filename)
            name = remove_extension(basename)

            fileinfo.ident = name
            fileinfo.full_ident = name
            fileinfo.name = name

        if is_dna:
            fileinfo.genome_filename = filename
        else:
            fileinfo.protein_filename = filename

            
        moltype = "DNA" if is_dna else "protein"

        previous = fileinfo_d.get(fileinfo.ident)
        if previous is not None:
            print("(merging into existing record '{fileinfo.ident}' moltype={moltype})")
            fileinfo = fileinfo.merge(previous)
        else:
            print(f"(new record for identifier '{fileinfo.ident}' moltype={moltype})")

        assert not fileinfo.is_empty(), fileinfo.__dict__
        fileinfo_d[fileinfo.ident] = fileinfo

    for n, (ident, fileinfo) in enumerate(fileinfo_d.items()):
        output.write_record(fileinfo)

    output.close()
    print('---')
    print(f"wrote {len(fileinfo_d)} entries to '{args.output_csv}'")

    return 0

if __name__ == '__main__':
    sys.exit(main())

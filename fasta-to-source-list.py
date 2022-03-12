#! /usr/bin/env python3
"""
"""
import sys
import argparse
import screed
import csv
import os
import shutil
from sourmash.tax.tax_utils import MultiLineageDB


class InputFile(object):
    ident = None
    moltype = None
    genome_filename = None
    protein_filename = None

    def merge(self, other):
        assert self.ident == other.ident
        assert self.name == other.name
        assert not (self.genome_filename and other.genome_filename)
        assert not (self.protein_filename and other.protein_filename)

        if self.genome_filename:
            assert other.protein_filename
            self.protein_filename = other.protein_filename
        else:
            assert self.protein_filename
            self.genome_filename = other.genome_filename

        return self

    def is_empty(self):
        if self.name is None:
            return True
        if self.ident is None:
            return True
        if self.genome_filename is None and self.protein_filename is None:
            return True
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('filenames', nargs='+')
    p.add_argument('-o', '--output-csv', required=True)
    p.add_argument('--ident-from-filename', action='store_true',
                   help="determine identifer from filename prefixes")
    p.add_argument('--names-from-taxonomy', nargs='+')
    p.add_argument(
        '--keep-full-identifiers', action='store_true',
        help='do not split identifiers on whitespace'
    )
    args = p.parse_args()

    get_name = lambda x: x
    if args.names_from_taxonomy:
        tax_info = MultiLineageDB.load(args.names_from_taxonomy,
                                       keep_full_identifiers=args.keep_full_identifiers)
        def get_name(ident):
            lineage = tax_info[ident]
            x = list(lineage)
            while not x[-1].name:
                x.pop()
            name = x[-1].name
            return name

    output_fp = open(args.output_csv, 'w', newline="")
    w = csv.DictWriter(output_fp, fieldnames=['ident',
                                              'name',
                                              'genome_filename',
                                              'protein_filename'])
    w.writeheader()

    fileinfo_d = {}

    n = 0
    for filename in args.filenames:
        print(f"processing genome '{filename}'")

        fileinfo = InputFile()

        for record in screed.open(filename):
            record_name = record.name
            break

        if not args.ident_from_filename:
            ident, *remainder = record_name.split(' ', 1)
            if not args.keep_full_identifiers:
                if '.' in ident:
                    ident = ident.split('.', 1)[0]

            fileinfo.ident = ident
            fileinfo.name = record_name
        else:
            # should use the same approach as genome grist...
            basename = os.path.basename(filename)
            idents = basename.split('_')
            assert len(idents) >= 2

            ident = "_".join(idents[:2])
            if not args.keep_full_identifiers:
                if '.' in ident:
                    ident = ident.split('.', 1)[0]

            fileinfo.ident = ident
            fileinfo.name = get_name(ident)

        if filename.endswith('.faa.gz') or filename.endswith('.faa'):
            fileinfo.protein_filename = filename
        elif filename.endswith('.fna.gz') or filename.endswith('.fna'):
            fileinfo.genome_filename = filename

        previous = fileinfo_d.get(fileinfo.ident)
        if previous is not None:
            fileinfo = fileinfo.merge(previous)

        assert not fileinfo.is_empty(), fileinfo.__dict__
        fileinfo_d[fileinfo.ident] = fileinfo

    for n, (ident, fileinfo) in enumerate(fileinfo_d.items()):
        
        w.writerow(dict(ident=fileinfo.ident,
                        name=fileinfo.name,
                        genome_filename=fileinfo.genome_filename or "",
                        protein_filename=fileinfo.protein_filename or ""))

    output_fp.close()
    print('---')
    print(f"wrote {len(fileinfo_d)} entries to '{args.output_csv}'")

    return 0

if __name__ == '__main__':
    sys.exit(main())

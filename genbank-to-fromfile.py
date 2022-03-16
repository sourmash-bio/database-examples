#! /usr/bin/env python3
"""
Summarize many GenBank-style FASTA files for 'sourmash sketch fromfile'
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
from sourmash.cli.utils import add_picklist_args
from sourmash import sourmash_args
from sourmash.picklist import PickStyle


usage = """


   ./genbank-to-fromfile.py filenames -o <out.csv> -t <taxonomy db>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__, usage=usage)
    p.add_argument('filenames', nargs='*', help="names of files to process")
    p.add_argument('-F', '--file-list', action='append',
                   help='text files with filenames to add to command line',)
    p.add_argument('-o', '--output-csv', required=True,
                   help="output CSV file")
    p.add_argument('-t', '--taxonomy-db', action='append', default=[],
                   required=True,
                   help="one or more sourmash taxonomy database(s)")
    p.add_argument('-v', '--verbose',
                   help='turn on more extensive output')
    add_picklist_args(p)
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

    # load/process picklists
    picklist = sourmash_args.load_picklist(args)
    include_ident = lambda full_ident: True
    if picklist and picklist.coltype not in ('ident', 'identprefix'):
        error("** ERROR: picklist can only use 'ident' or 'identprefix' here.")
        sys.exit(-1)
    elif picklist:
        # code taken from sourmash, src/sourmash/picklist.py:
        def include_ident(full_ident):
            q = full_ident
            # mangle into the kinds of values we support here
            q = picklist.preprocess_fn(q)

            # add to the number of queries performed,
            picklist.n_queries += 1

            # determine if ok or not.
            if picklist.pickstyle == PickStyle.INCLUDE:
                if q in picklist.pickset:
                    picklist.found.add(q)
                    return True
            elif picklist.pickstyle == PickStyle.EXCLUDE:
                if q not in picklist.pickset:
                    picklist.found.add(q)
                    return True
            return False

    # load taxonomy ID
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

    # track Inputfile objects by name:
    fileinfo_d = {}

    n = 0
    total = len(args.filenames)
    for n, filename in enumerate(args.filenames):
        basename = os.path.basename(filename)
        notify(f"processing file '{basename}' ({n}/{total})", end='\r')

        if os.path.getsize(filename) == 0:
            error(f"** ERROR: '{filename}' has zero size.")
            sys.exit(-1)

        fileinfo = InputFile()

        # split filenames of the format 'GCF_003317655.1_genomic.fna.gz'
        # into identifier 'GCF_003317655.1' and discard the rest.
        idents = basename.split('_')
        assert len(idents) >= 2

        # 'full_ident' keeps version, 'ident' does not - use latter for
        # tax lookup.
        full_ident = "_".join(idents[:2])
        assert full_ident.startswith('GCA_') or full_ident.startswith('GCF_')

        if not include_ident(full_ident):
            continue

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
            if args.verbose:
                notify("(merging into existing record)")
            fileinfo = fileinfo.merge(previous)
        else:
            if args.verbose:
                notify(f"(new record for name '{fileinfo.name}')")

        # double check & save
        assert not fileinfo.is_empty(), fileinfo.__dict__
        fileinfo_d[fileinfo.ident] = fileinfo

    # write the things!
    for n, (ident, fileinfo) in enumerate(fileinfo_d.items()):
        output.write_record(fileinfo)

    output.close()

    notify(f"processed {total} files.")
    notify('---')
    notify(f"wrote {len(fileinfo_d)} entries to '{args.output_csv}'")

    if picklist:
        sourmash_args.report_picklist(args, picklist)

    return 0

if __name__ == '__main__':
    sys.exit(main())

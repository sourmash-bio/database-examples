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
    p.add_argument('-v', '--verbose', action='store_true',
                   help='turn on more extensive output')
    p.add_argument('--strict', action='store_true',
                   help='turn on strict success mode')
    p.add_argument('-R', '--report-errors-to',
                   help='output errors to this file; default <csv>.report.txt')
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

    # report file
    report_filename = args.output_csv + '.error-report.txt'
    if args.report_errors_to:
        report_filename = args.report_errors_to
    notify(f"Any survivable errors will be reported to '{report_filename}'")
    report_fp = open(report_filename, "wt")

    num_files_zero_size = 0
    num_duplicate_inputs = 0

    ### begin processing

    # track Inputfile objects by name:
    fileinfo_d = {}

    n = 0
    total = len(args.filenames)
    for n, filename in enumerate(args.filenames):
        basename = os.path.basename(filename)
        notify(f"processing file '{basename}' ({n}/{total})", end='\r')

        if os.path.getsize(filename) == 0:
            num_files_zero_size += 1
            print(f"zero size: {filename}", file=report_fp)
            if args.verbose:
                error(f"** SKIPPING: '{basename}' has zero size.")

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

            try:
                fileinfo = fileinfo.merge(previous)
            except ValueError as exc:
                num_duplicate_inputs += 1
                print(f"{str(exc)}: {filename}", file=report_fp)
                if args.verbose:
                    error(f"** SKIPPING: '{basename}' is duplicate.")
                continue

        else:
            if args.verbose:
                notify(f"(new record for name '{fileinfo.name}')")

        # double check & save
        assert not fileinfo.is_empty(), fileinfo.__dict__
        fileinfo_d[fileinfo.ident] = fileinfo

    # write the things!
    num_genome_only = 0
    num_protein_only = 0
    for n, (ident, fileinfo) in enumerate(fileinfo_d.items()):
        if not fileinfo.protein_filename:
            num_protein_only += 1
            print(f"missing protein file: {ident}", file=report_fp)
        if not fileinfo.genome_filename:
            num_genome_only += 1
            print(f"missing genome file: {ident}", file=report_fp)
        output.write_record(fileinfo)

    output.close()

    notify(f"processed {total} files.")
    notify('---')
    notify(f"wrote {len(fileinfo_d)} entries to '{args.output_csv}'")

    if num_protein_only:
        notify(f"{num_protein_only} entries had only protein (and no genome) files.")
    if num_genome_only:
        notify(f"{num_genome_only} entries had only genome (and no protein) files.")
    if num_protein_only == 0 and num_genome_only == 0:
        notify("all entries had matched genome and protein files!")
    else:
        if args.strict:
            pass
        else:
            notify("(missing files do not cause error exit without --strict)")

    ## report on any errors

    is_problem = False

    # zero size files?
    if num_files_zero_size:
        notify(f"{num_files_zero_size} files had no content (zero size).")
        is_problem = True

    # duplicate inputs?
    if num_duplicate_inputs:
        notify(f"{num_duplicate_inputs} filenames yielded duplicate identifiers.")
        is_problem = True

    # not found all pickvals?
    if picklist:
        if picklist.pickstyle == PickStyle.INCLUDE:
            notify(f"for given picklist, found {len(picklist.found)} matches to {len(picklist.pickset)} distinct values")
            missing_picklist = picklist.pickset - picklist.found
            n_missing = len(missing_picklist)

            notify(f"ERROR: {n_missing} picklist values not found.")
            for value in missing_picklist:
                print(f"missing picklist value: {value}", file=report_fp)

            is_problem = True
        elif picklist.pickstyle == PickStyle.EXCLUDE:
            notify(f"for given picklist, found {len(picklist.found)} matches by excluding {len(picklist.pickset)} distinct values")
            n_missing = 0

    if is_problem:
        error(f"** Errors were encountered ;(. See details in '{report_filename}'.")
        return -1

    return 0

if __name__ == '__main__':
    sys.exit(main())

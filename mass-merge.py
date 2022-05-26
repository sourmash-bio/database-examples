#! /usr/bin/env python
"""
Merge signatures in bulk, based on an attribute in the spreadsheet.

mass-merge.py takes a list of databases along with spreadsheets (w/-F),
and merges signatures by values in the specified `merge-col`.

The spreadsheet must contain two columns, 'ident' and the value of `--merge-col`;
signatures are selected based on 'ident' and renamed to the value found in the merge column.
Singletons (no additional signatures to merge) will be renamed for consistency.
"""
import sys
import argparse
import csv
from collections import defaultdict

import sourmash

from sourmash.picklist import SignaturePicklist
from sourmash.logging import set_quiet, error, notify, print_results, debug
from sourmash import sourmash_args
from sourmash.cli.utils import (add_moltype_args, add_ksize_arg)
#from sourmash.sig import _check_abundance_compatibility

def _check_abundance_compatibility(sig1, sig2):
    if sig1.minhash.track_abundance != sig2.minhash.track_abundance:
        raise ValueError("incompatible signatures: track_abundance is {} in first sig, {} in second".format(sig1.minhash.track_abundance, sig2.minhash.track_abundance))


def massmerge(args):
    """
    merge one or more signatures based on a specified column.
    """
    set_quiet(args.quiet, args.debug)
    moltype = sourmash_args.calculate_moltype(args)
    merge_col = args.merge_col

    # load spreadsheets
    merge_d = defaultdict(list)
    all_idents=set()
    for filename in args.from_spreadsheet:
        count = 0
        with open(filename, newline='') as fp:
            first_entry= True
            r = csv.DictReader(fp)
            for row in r:
                if first_entry:
                    if not merge_col in r.fieldnames:
                        error(f"ERROR on spreadsheet '{filename}'.")
                        error(f"Merge column {merge_col} is not present.")
                        sys.exit(-1)
                    first_entry=False
                merge_name = row[merge_col]
                ident = row['ident']

                assert ' ' not in ident, f"identifiers cannot have spaces - but '{ident}' does."
                assert ident not in all_idents, f"duplicate identifer: '{ident}'"
                all_idents.add(ident)

                merge_d[merge_name].append(ident)
                count += 1
        notify(f"loaded {count} identifiers from '{filename}'")

    num_merge_names = len(merge_d)
    notify(f"found a total of {num_merge_names} distinct values for signature merging.")

    # load each db and check that we can find all idents
    found_idents = set()
    idx_list = []
    for db in args.dblist:
        notify(f"loading index '{db}'")
        idx = sourmash.load_file_as_index(db)

        manifest = idx.manifest
        if manifest is None:
            error(f"ERROR on filename '{db}'.")
            error("No manifest, but a manifest is required.")
            sys.exit(-1)

        ident_picklist = SignaturePicklist('ident')
        ident_picklist.pickset = all_idents
        check_idx = idx.select(ksize=args.ksize,
                                moltype=moltype,
                                picklist=ident_picklist)
        # do we need to do any checks for duplicate idents between dbs?
        found_idents.update(ident_picklist.found)
        idx_list.append(check_idx)

    # make sure that we get all the things.
    if not all_idents.issubset(found_idents):
        remaining = all_idents - found_idents
        error(f"ERROR: {len(remaining)} identifiers from spreadsheet not found.")
        example_missing = "\n".join(remaining)
        error(f"Here are some examples: {example_missing}")
        sys.exit(-1)

    if args.check:
        notify("Everything looks copacetic. Exiting as requested by `--check`")
        sys.exit(0)

    notify("Everything looks copacetic. Proceeding to merge!")

    # go through, do merge, save.
    with sourmash_args.SaveSignaturesToLocation(args.output) as save_sigs:
        n=0
        n_singletons = 0
        for m, (merge_name, idents) in enumerate(merge_d.items()):
            # identifiers can't have spaces
            merge_name = merge_name.replace(" ", "_")

            if m % 100 == 0:
                merge_percent = float(n)/len(found_idents) * 100
                notify(f"...merging sigs for {merge_name} ({merge_percent:.1f}% of sigs merged)", end="\r")

            # build a new picklist for idents to be merged
            ident_picklist = SignaturePicklist('ident')
            ident_picklist.pickset = set(idents)

            # if singleton, just rename
            if len(idents) == 1:
                n_singletons+=1
                this_idx = idx_list[0].select(picklist=ident_picklist)
                ss = next(this_idx.signatures())
                ss._name = merge_name
                save_sigs.add(ss)
                n+=1
            else:
                # otherwise, loop through each idx (db), select sigs, merge mh
                first_sig = None
                mh = None
                merged_ss = None
                for idx in idx_list:
                    this_idx = idx.select(picklist=ident_picklist)
                    for ss in this_idx.signatures():
                        n += 1
                        # first sig? initialize some things
                        if first_sig is None:
                            first_sig = ss
                            mh = first_sig.minhash.copy_and_clear()

                            # forcibly remove abundance?
                            if args.flatten:
                                mh.track_abundance = False

                        try:
                            sigobj_mh = ss.minhash
                            if not args.flatten:
                                _check_abundance_compatibility(first_sig, ss)
                            else:
                                sigobj_mh.track_abundance = False

                            mh.merge(sigobj_mh)
                        except (TypeError, ValueError) as exc:
                            error(f"ERROR when merging signature '{ss}' ({ss.md5sum()[:8]})")
                            error(str(exc))
                            sys.exit(-1)

                # create merged sig and write to output
                merged_ss = sourmash.SourmashSignature(mh, name=merge_name)
                save_sigs.add(merged_ss)
            merge_percent = float(n)/len(found_idents) * 100
            notify(f"...merged {len(idents)} sigs for {merge_name} ({merge_percent:.1f}% of sigs merged)", end="\r")

        notify(f"merged {n} signatures into {len(save_sigs)} signatures by column: {merge_col}")
        notify(f"  of these, {n_singletons} were singletons (no merge; just renamed)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dblist', nargs='+')

    p.add_argument(
        '-q', '--quiet', action='store_true',
        help='suppress non-error output'
    )
    p.add_argument(
        '-d', '--debug', action='store_true',
    )
    p.add_argument(
        '--merge-col', required=True,
        help='the column to merge signatures by (required)'
    )
    p.add_argument(
        '-o', '--output', metavar='FILE', default='-',
        help='output merged database to this file (default stdout)'
    )
    p.add_argument(
        '--flatten', action='store_true',
        help='remove abundances from all signatures while merging'
    )
    p.add_argument(
        '-f', '--force', action='store_true',
        help='try to load all files as signatures'
    )
    p.add_argument(
        '--check', action='store_true',
        help='Just check for ability to merge; do not actually merge signatures.'
    )
    p.add_argument('-F', '--from-spreadsheet',
                   required=True,
                   action='append', default=[],
                   help="input spreadsheet containing 'ident' and '--merge-col` columns")

    add_ksize_arg(p, 31)
    add_moltype_args(p)

    args = p.parse_args()

    massmerge(args)


if __name__ == '__main__':
    sys.exit(main())

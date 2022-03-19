#! /usr/bin/env python
"""
Rename signatures in bulk.

mass-rename.py takes a list of databases along with a spreadsheet (w/-F),
and renames all of the matching signatures in the databases.

The spreadsheet must contain two columns, 'ident' and 'name'; signatures
are selected based on 'ident' and renamed to 'name'. Conveniently this is
the same format as the fromfile format :).
"""
import sys
import argparse
import csv

import sourmash

from sourmash.picklist import SignaturePicklist
from sourmash.logging import set_quiet, error, notify, print_results, debug
from sourmash import sourmash_args
from sourmash.cli.utils import (add_moltype_args, add_ksize_arg)


def massrename(args):
    """
    rename one or more signatures.
    """
    set_quiet(args.quiet, args.quiet)
    moltype = sourmash_args.calculate_moltype(args)
    #CTB _extend_signatures_with_from_file(args)

    # load spreadsheet
    rename_d = {}
    with open(args.from_spreadsheet, newline='') as fp:
        r = csv.DictReader(fp)
        for row in r:
            name = row['name']
            ident = row['ident']

            assert ' ' not in ident, "identifiers cannot have spaces"
            assert ident not in rename_d, "duplicates not allowed"
            rename_d[ident] = name
    notify(f"loaded {len(rename_d)} identifiers w/new names from '{args.from_spreadsheet}'")

    rename_set = set(rename_d)

    # build a new picklist for just the idents
    if args.strip_identifier_versions:
        ident_picklist = SignaturePicklist('identprefix')
    else:
        ident_picklist = SignaturePicklist('ident')
    ident_picklist.pickset = rename_set

    # go through all the database and load etc.
    idx_list = []
    for db in args.dblist:
        notify(f"loading index '{db}'")
        idx = sourmash.load_file_as_index(db)

        manifest = idx.manifest
        if manifest is None:
            error(f"ERROR on filename '{db}'.")
            error("No manifest, but a manifest is required.")
            sys.exit(-1)

        idx = idx.select(ksize=args.ksize,
                         moltype=moltype,
                         picklist=ident_picklist)

        idx_list.append(idx)

    # make sure that we get all the things.
    to_rename = set(rename_d.keys())
    if not to_rename.issubset(ident_picklist.found):
        remaining = to_rename - ident_picklist.found
        error(f"ERROR: {len(remaining)} identifiers from spreadsheet not found.")
        sys.exit(-1)

    # go through, do rename, save.
    with sourmash_args.SaveSignaturesToLocation(args.output) as save_sigs:
        for idx in idx_list:
            for ss in idx.signatures():
                ident = ss.name.split(' ')[0]
                new_name = rename_d[ident]
                ss._name = new_name

                save_sigs.add(ss)

    notify(f"rename {len(save_sigs)} signatures")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dblist', nargs='+')

    p.add_argument(
        '-q', '--quiet', action='store_true',
        help='suppress non-error output'
    )
    p.add_argument(
        '-o', '--output', metavar='FILE', default='-',
        help='output signature to this file (default stdout)'
    )
    p.add_argument(
        '-f', '--force', action='store_true',
        help='try to load all files as signatures'
    )
    p.add_argument('--strip-identifier-versions',
                   help='use only the identifier prefix (w/o version) for matching',
                   action='store_true')
    p.add_argument('-F', '--from-spreadsheet',
                   required=True,
                   help="input spreadsheet containing 'ident' and 'name' columns")

    add_ksize_arg(p, 31)
    add_moltype_args(p)

    args = p.parse_args()

    massrename(args)


if __name__ == '__main__':
    sys.exit(main())

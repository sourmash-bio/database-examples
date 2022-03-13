#! /usr/bin/env python
import sys
import argparse
import csv
from collections import defaultdict

import screed

import sourmash
from sourmash.logging import notify, error
from sourmash.command_sketch import *
from sourmash.command_sketch import _signatures_for_sketch_factory
from sourmash.command_compute import (_compute_individual, _compute_merged,
                                      ComputeParameters, add_seq, set_sig_name)
from sourmash import sourmash_args
from sourmash.signature import SourmashSignature


def manifest_row_to_compute_param_obj(row):
    is_dna = is_protein = is_dayhoff = is_hp = False
    if row['moltype'] == 'DNA':
        is_dna = True
    elif row['moltype'] == 'protein':
        is_protein = True
    elif row['moltype'] == 'hp':
        is_hp = True
    elif row['moltype'] == 'dayhoff':
        is_hp = True
    else:
        assert 0

    p = ComputeParameters([row['ksize']], 42,
                          is_protein, is_dayhoff, is_hp, is_dna,
                          row['num'], row['with_abundance'],
                          row['scaled'])

    return p


def _compute_sigs(to_build, output):
    # this is where output signatures will go.
    save_sigs = sourmash_args.SaveSignaturesToLocation(output)
    save_sigs.open()

    for (name, filename), param_objs in to_build.items():

        #
        # calculate signatures!
        #

        # now, set up to iterate over sequences.
        with screed.open(filename) as screed_iter:
            if not screed_iter:
                notify(f"no sequences found in '{filename}'?!")
                continue

            # @CTB
            sigs = []
            for p in param_objs:
                sig = SourmashSignature.from_params(p)
                sigs.append(sig)

            # consume & calculate signatures
            notify('... reading sequences from {}', filename)
            for n, record in enumerate(screed_iter):
                if n % 10000 == 0:
                    if n:
                        notify('\r...{} {}', filename, n, end='')

                add_seq(sigs, record.sequence, False, False) # @CTB
#                        args.input_is_protein, args.check_sequence) # @CTB

            notify('...{} {} sequences', filename, n, end='')

            set_sig_name(sigs, filename, name)
            for sig in sigs:
                save_sigs.add(sig)

            notify(f'calculated {len(sigs)} signatures for {n+1} sequences in {filename}')


    save_sigs.close()
    notify(f"saved {len(save_sigs)} signature(s) to '{save_sigs.location}'. Note: signature license is CC0.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('csv')
    p.add_argument(
        '-o', '--output',
        help='output computed signatures to this file',
        required=True
    )
    p.add_argument(
        '-p', '--param-string', default=[],
        help='signature parameters to use.', action='append',
    )
    p.add_argument(
        '--license', default='CC0', type=str,
        help='signature license. Currently only CC0 is supported.'
    )
    p.add_argument('--already-done', nargs='+', default=[])
    args = p.parse_args()

    # load manifests from '--already-done' databases => turn into
    # ComputeParameters objects, indexed by name.
    #
    # CTB: note: 'seed' is not tracked by manifests currently. Oops.
    # so we'll have to block 'seed' from being passed in by '-p'.

    already_done = defaultdict(list)
    for filename in args.already_done:
        idx = sourmash.load_file_as_index(filename)
        manifest = idx.manifest
        assert manifest

        # for each manifest row,
        for row in manifest.rows:
            if not row['name']:
                continue

            # build a compute param object
            name = row['name']
            p = manifest_row_to_compute_param_obj(row)

            # save into lists, retrievable by name.
            already_done[name].append(p)

    notify(f"Loaded {len(already_done)} pre-existing names from manifest(s)")

    # now, create the set of desired sketch specs.
    try:
        sig_factory = _signatures_for_sketch_factory(args.param_string,
                                                     None)
    except ValueError as e:
        error(f"Error creating signatures: {str(e)}")
        sys.exit(-1)

    # take the signatures factory => convert into a bunch of ComputeParameters
    # objects.
    build_params = list(sig_factory.get_compute_params(split_ksizes=True))

    #
    # the big loop - cross-product all of the names in the input CSV file
    # with the sketch spec(s) provided on the command line, figure out
    # which ones do not yet exist, and record them to be calculated.
    #

    to_build = defaultdict(list)
    with open(args.csv, newline="") as fp:
        r = csv.DictReader(fp)

        n_skipped = 0
        total = 0
        for row in r:
            name = row['name']
            genome = row['genome_filename']
            proteome = row['protein_filename']

            plist = already_done[name]
            for p in build_params:
                total += 1

                # has this been done?
                if p not in plist:
                    # nope - figure out genome/proteome needed
                    filename = None
                    if p.dna:
                        filename = genome
                    else:
                        assert p.dayhoff or p.protein or p.hp
                        filename = proteome
                    assert filename

                    # add to build list
                    to_build[(name, filename)].append(p)
                else:
                    n_skipped += 1

    if to_build:
        notify(f"** Building {total - n_skipped} sketches for {len(to_build)} files")
        _compute_sigs(to_build, args.output)

    notify(f"** Of {total} total requested in cross-product, skipped {n_skipped}, built {total - n_skipped})")


if __name__ == '__main__':
    sys.exit(main())

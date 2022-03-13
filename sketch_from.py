#! /usr/bin/env python
import sys
import argparse
import csv

import screed

from sourmash.command_sketch import *
from sourmash.command_sketch import _signatures_for_sketch_factory
from sourmash.command_compute import (_compute_individual, _compute_merged,
                                      ComputeParameters, add_seq, set_sig_name)
from sourmash import sourmash_args


def _compute_sigs(filenames, signatures_factory, output):
    # this is where output signatures will go.
    save_sigs = sourmash_args.SaveSignaturesToLocation(output)
    save_sigs.open()

    for (name, filename, _) in filenames: # @CTB

        #
        # calculate signatures!
        #

        # now, set up to iterate over sequences.
        with screed.open(filename) as screed_iter:
            if not screed_iter:
                notify(f"no sequences found in '{filename}'?!")
                continue

            sigs = signatures_factory()

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
    args = p.parse_args()

    moltype='dna'
    try:
        signatures_factory = _signatures_for_sketch_factory(args.param_string,
                                                            moltype,
                                                            mult_ksize_by_3=False)
    except ValueError as e:
        error(f"Error creating signatures: {str(e)}")
        sys.exit(-1)

    with open(args.csv, newline="") as fp:
        r = csv.DictReader(fp)

        filenames = []
        for row in r:
            name = row['name']
            genome = row['genome_filename']
            proteome = row['protein_filename']

            filenames.append((name, genome, proteome))

    _compute_sigs(filenames, signatures_factory, args.output)


if __name__ == '__main__':
    sys.exit(main())

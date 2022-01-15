#! /usr/bin/env python
import sys
import argparse
import screed
import csv
import os
import shutil


def main():
    p = argparse.ArgumentParser()
    p.add_argument('genome_files', nargs='+')
    p.add_argument('-o', '--output-csv', required=True)
    args = p.parse_args()

    output_fp = open(args.output_csv, 'wt')
    w = csv.DictWriter(output_fp, fieldnames=['name',
                                              'genome_filename',
                                              'protein_filename'])
    w.writeheader()

    n = 0
    for filename in args.genome_files:
        print(f"processing genome '{filename}'")

        for record in screed.open(filename):
            record_name = record.name
            break

        w.writerow(dict(name=record_name,
                        genome_filename=filename))
        n += 1

    output_fp.close()
    print('---')
    print(f"wrote {n} entries to '{args.output_csv}'")

    return 0

if __name__ == '__main__':
    sys.exit(main())

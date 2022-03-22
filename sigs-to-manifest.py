#! /usr/bin/env python
import sys
import sourmash
from sourmash.logging import notify, error
import argparse
from sourmash.manifest import CollectionManifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('pathlist', nargs='+')
    p.add_argument('-o', '--output', help='manifest output file',
                   required=True)
    args = p.parse_args()

    rows = []
    for filename in args.pathlist:
        notify(f"Loading filenames from {filename}.")
        n_loaded = 0
        with open(filename, 'rt') as fp:
            for loc in fp:
                loc = loc.strip()

                for ss in sourmash.load_file_as_signatures(loc):
                    if n_loaded % 100 == 0:
                        notify(f'... {n_loaded}', end='\r')
                    row = CollectionManifest.make_manifest_row(ss,
                                                               loc,
                                                               include_signature=False)
                    rows.append(row)
                    n_loaded += 1

        notify(f"Loaded {n_loaded} sigs => manifest from {filename}")

    m = CollectionManifest(rows)
    with open(args.output, 'w', newline='') as outfp:
        m.write_to_csv(outfp, write_header=True)

    return 0


if __name__ == '__main__':
    sys.exit(main())

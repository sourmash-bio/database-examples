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
    p.add_argument('--previous', help='previous manifest file')
    p.add_argument('--merge-previous', action='store_true',
                   help='merge previous and new manifests')
    args = p.parse_args()

    previous_filenames = set()
    previous = CollectionManifest([])
    if args.previous:
        previous = CollectionManifest.load_from_filename(args.previous)

        for row in previous.rows:
            previous_filenames.add(row['internal_location'])

        notify(f"loaded {len(previous)} rows with {len(previous_filenames)} distinct sig files from '{args.previous}'")

    rows = []
    n_files = 0
    n_skipped = 0

    for filename in args.pathlist:
        notify(f"Loading filenames from {filename}.")
        n_loaded = 0
        with open(filename, 'rt') as fp:
            for loc in fp:
                if n_files and n_files % 100 == 0:
                    notify(f'... loaded {n_files} files, skipped {n_skipped}; {n_loaded} sigs', end='\r')
                loc = loc.strip()

                if loc in previous_filenames:
                    n_skipped += 1
                    continue

                for ss in sourmash.load_file_as_signatures(loc):
                    row = CollectionManifest.make_manifest_row(ss,
                                                               loc,
                                                               include_signature=False)
                    rows.append(row)
                    n_loaded += 1

                n_files += 1

        notify(f"Loaded {n_loaded} manifest rows from files in '{filename}'")

    if args.merge_previous:
        notify(f"merging {len(previous.rows)} previous rows into current.")
        rows.extend(previous.rows)

    m = CollectionManifest(rows)
    m.write_to_filename(args.output)

    notify(f"saved {len(m)} manifest rows to '{args.output}'")

    return 0


if __name__ == '__main__':
    sys.exit(main())

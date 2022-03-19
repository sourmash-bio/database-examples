"""
CTB TODO: change ident to identprefix, full_ident to ident.
"""

import csv
import os


def check_dna(seq):
    for ch in 'ACGTN':
        seq = seq.replace(ch, '')
    if len(seq):
        return False
    return True


def remove_extension(basepath, extra=[]):
    exts = set(['.fa', '.gz', '.faa', '.fna'])
    exts.update(extra)

    name, ext = os.path.splitext(basepath)
    while ext in exts:
        basepath = name
        name, ext = os.path.splitext(basepath)

    return basepath


class OutputRecords:
    def __init__(self, filename):
        self.filename = filename
        self.fp = None

    def open(self):
        self.fp = open(self.filename, 'w', newline='')
        self.writer = csv.DictWriter(self.fp,
                                     fieldnames=['identprefix',
                                                 'ident',
                                                 'name',
                                                 'genome_filename',
                                                 'protein_filename'])

        self.writer.writeheader()

        return self.writer

    def write_record(self, input_file_obj):
        input_file_obj.to_csv(self.writer)

    def close(self):
        self.fp.close()
        self.writer = None


class InputFile(object):
    ident = None
    full_ident = None
    genome_filename = None
    protein_filename = None
    name = None

    def merge(self, other):
        assert self.ident == other.ident
        assert self.full_ident == other.full_ident
        assert self.name == other.name

        if (self.genome_filename and other.genome_filename):
            raise ValueError("duplicate genome filename")
        if (self.protein_filename and other.protein_filename):
            raise ValueError("duplicate protein filename")

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
        if self.full_ident is None:
            return True
        if self.genome_filename is None and self.protein_filename is None:
            return True
        return False

    def to_csv(self, w):
        w.writerow(dict(identprefix=self.ident,
                        ident=self.full_ident,
                        name=self.name,
                        genome_filename=self.genome_filename or "",
                        protein_filename=self.protein_filename or ""))

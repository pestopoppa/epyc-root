"""Shared rocprofv3 CSV reader and dispatch duration parser."""
import csv
import glob
import os
import statistics


def read_csvs(odir, suffix):
    rows = []
    for path in glob.glob(os.path.join(odir, '**', '*' + suffix), recursive=True):
        with open(path, newline='') as f:
            rows += list(csv.DictReader(f))
    return rows


def mean_duration_s(rows):
    durations = [(int(r['End_Timestamp']) - int(r['Start_Timestamp'])) * 1e-9 for r in rows]
    return statistics.mean(durations) if durations else None

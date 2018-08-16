#!/usr/bin/env python3
"""
   ibd2graph.py - Process 23andMe IBD sharing data dump
   Copyright (C) 2015-2018 Giulio Genovese (giulio.genovese@gmail.com)

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.

   Written by Giulio Genovese <giulio.genovese@gmail.com>
"""

import sys, argparse, pandas as pd, json, numpy as np

def load_genetic_map(chroms, files):
    gmap = dict()
    for chrom, file in zip(chroms, files):
        df = pd.read_csv(file, delim_whitespace = True, names = ['CHR', 'ID' ,'CM', 'BP'])
        gmap[chrom] = df[['BP', 'CM']]
    return gmap

def get_mb(intervals, flag):
    correction = sum([np.diff(seg)[0] for seg in intervals['X'][0]]) / 2e6 if flag else 0
    return sum([np.diff(seg)[0] for (key, value) in intervals.items() for seg in value[0]]) / 1e6 - correction

# wget http://bochet.gcc.biostat.washington.edu/beagle/genetic_maps/plink.GRCh37.map.zip
def get_cm(intervals, gmap, flag):
    correction = sum([np.diff(np.interp(seg, gmap['X']['BP'], gmap['X']['CM']))[0] for seg in intervals['X'][0]]) / 2 if flag else 0
    return sum([np.diff(np.interp(seg, gmap[key]['BP'], gmap[key]['CM']))[0] for (key, value) in intervals.items() for seg in value[0]]) - correction

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Process 23andMe IBD sharing data dump (16 Aug 2018)', add_help = False, usage = 'ibd2graph.py -h <inheritance> -i <ibdview> [options]')
    parser.add_argument('-h', metavar = '<FILE>', required = True, type = str, help = 'input inheritance table file')
    parser.add_argument('-i', metavar = '<FILE>', required = True, type = str, help = 'input ibdview table file')
    parser.add_argument('-c', metavar = '<STR>', nargs = '+', type = str, help = 'genetic map chromosomes')
    parser.add_argument('-g', metavar = '<STR>', nargs = '+', type = str, help = 'genetic map files')
    try:
        parser.add_argument('-o', metavar = '<FILE>', type = argparse.FileType('w', encoding = 'UTF-8'), default = sys.stdout, help = 'output graph file [stdout]')
    except TypeError:
        sys.stderr.write('Python >= 3.4 is required to run this script\n')
        sys.stderr.write('(see https://docs.python.org/3/whatsnew/3.4.html#argparse)\n')
        exit(2)

    # extract arguments from the command line
    try:
        parser.error = parser.exit
        args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        exit(2)

    if args.c and args.g:
        gmap = load_genetic_map(args.c, args.g)
    df = pd.read_csv(args.h, sep = '\t')
    ehid_label = dict(zip(df['people_ids'], df['people_labels']))
    ehid_gender = dict(zip(df['people_ids'], df['gender']))
    df = pd.read_csv(args.i, sep = '\t')
    idx = df['p1'].apply(lambda x: x in ehid_label) & df['p2'].apply(lambda x: x in ehid_label)
    df = df.loc[idx]
    for i in df.index:
        p1 = df['p1'][i]
        p2 = df['p2'][i]
        intervals = json.loads(df['intervals'][i])
        df.at[i, 'l1'] = ehid_label[p1]
        df.at[i, 'l2'] = ehid_label[p2]
        df.at[i, 'g1'] = ehid_gender[p1]
        df.at[i, 'g2'] = ehid_gender[p2]
        flag = ehid_gender[p1] == 'Male' and ehid_gender[p2] == 'Male'
        df.at[i, 'mb'] = get_mb(intervals, flag)
        if args.c and args.g:
            df.at[i, 'cm'] = get_cm(intervals, gmap, flag)
    df.to_csv(args.o, sep = '\t', columns = ['p1','l1','g1','p2','l2','g2','mb'] + ['cm'] if args.c and args.g else [], index = False)

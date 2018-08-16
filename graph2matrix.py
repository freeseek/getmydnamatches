#!/usr/bin/env python3
"""
   graph2matrix.py - Convert AncestryDNA/23andMe matches graph to matrix
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

import sys, argparse, pandas as pd, re

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Convert AncestryDNA/23andMe matches graph to matrix (16 Aug 2018)', add_help = False, usage = 'graph2matrix.py [options]')
    parser.add_argument('-t', metavar = '<CHAR>', type = str, default = 'tab', help = 'separator [tab]')
    parser.add_argument('-l', action = 'store_true', default = False, help = 'whether to use labels rather than ids [False]')
    parser.add_argument('-v', action = 'store_true', default = False, help = 'whether to remove HapMap/Mendel/Fisher 23andMe individuals [False]')
    parser.add_argument('-c', action = 'store_true', default = False, help = 'whether to convert special characters to _ [False]')
    parser.add_argument('-g', action = 'store_true', default = False, help = 'whether to use genetic distance rather than physical distance [False]')
    parser.add_argument('-h', metavar = '<FILE>', type = str, help = '23andMe inheritance table file')
    try:
        parser.add_argument('-i', metavar = '<FILE>', type = argparse.FileType('r', encoding = 'UTF-8'), default = sys.stdin, help = 'input graph file [stdout]')
        parser.add_argument('-o', metavar = '<FILE>', type = argparse.FileType('w', encoding = 'UTF-8'), default = sys.stdout, help = 'output matrix file [stdout]')
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

    df = pd.read_csv(args.i, sep = '\t')
    if args.v:
        idx = df['p1'].apply(lambda x: x[0:2]!='v$') & df['p2'].apply(lambda x: x[0:2]!='v$')
        df = df.loc[idx]
    if args.c:
        df['l1'] = df['l1'].apply(lambda x: re.sub('[ .]','_',x))
        df['l2'] = df['l2'].apply(lambda x: re.sub('[ .]','_',x))
    if args.h:
        dfh = pd.read_csv(args.h, sep = '\t')
        if args.c:
            dfh['people_labels'] = dfh['people_labels'].apply(lambda x: re.sub('[ .]','_',x))
        columns = dfh['people_labels'].values.tolist() if args.l else dfh['people_ids'].values.tolist()
    else:
        columns = list(set(df['l1']) | set(df['l2']) if args.l else set(df['p1']) | set(df['p2']))
    mat = pd.DataFrame(columns = columns, index = columns, dtype = float)
    mat.fillna(0, inplace = True)
    iid = [None, None]
    for i in df.index:
        i1 = df['l1' if args.l else 'p1'][i]
        if pd.isnull(i1) or not i1 in columns:
            sys.stderr.write('Warning: ' + str(df['l1'][i]) + ', ' + str(df['p1'][i]) + ' not in input inheritance file\n')
            continue
        i2 = df['l2' if args.l else 'p2'][i]
        if pd.isnull(i2) or not i2 in columns:
            sys.stderr.write('Warning: ' + str(df['l2'][i]) + ', ' + str(df['p2'][i]) + ' not in input inheritance file\n')
            continue
        shared = df['cm' if args.g else 'mb'][i] if 'mb' in df or 'cm' in df else 1
        mat[i1][i2] = shared
        mat[i2][i1] = shared
    mat.to_csv(args.o, sep = '\t' if args.t == 'tab' else args.t, na_rep = 'NA')

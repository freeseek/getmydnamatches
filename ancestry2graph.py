#!/usr/bin/env python3
"""
   ancestry2graph.py - Process 23andMe IBD sharing data dump
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

import sys, argparse, pandas as pd

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Process AncestryDNA data dump (16 Aug 2018)', add_help = False, usage = 'ancestry2graph.py -g <guid> -l <label> [options]')
    parser.add_argument('-d', action = 'store_true', default = False, help = 'whether to remove distant cousins [False]')
    try:
        parser.add_argument('-i', metavar = '<FILE>', type = argparse.FileType('r', encoding = 'UTF-8'), default = sys.stdin, help = 'input matches file [stdin]')
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

    df = pd.read_csv(args.i, sep = '\t')
    user_guid = df.iloc[0]['testGuid']
    user_label = df.iloc[0]['matchTestDisplayName']
    user_gender = df.iloc[0]['subjectGender']
    df.loc[~df['matchTestSubjectIsAdmin'],'matchTestDisplayName'] += ' (administered by ' + df.loc[~df['matchTestSubjectIsAdmin'],'matchTestAdminDisplayName'] + ')'
    guid_label = pd.Series(df['matchTestDisplayName'].values, index = df['testGuid']).to_dict()
    guid_gender = pd.Series(df['subjectGender'].values, index = df['testGuid']).to_dict()

    df2 = pd.DataFrame(columns = ['human_id_1', 'name_1', 'sex_1', 'human_id_2', 'name_2', 'sex_2', 'seg_cm'])
    for i in df.index[df['meiosisValue']<10] if args.d else df.index:
        testGuid = df['testGuid'][i]
        if user_guid == testGuid:
            continue
        cm = df['sharedCentimorgans'][i]
        pidx = hash(tuple(sorted([user_guid, testGuid])))
        if not pidx in df2.index:
            df2.at[pidx, 'human_id_1'] = user_guid
            df2.at[pidx, 'name_1'] = user_label
            df2.at[pidx, 'sex_1'] = user_gender
            df2.at[pidx, 'human_id_2'] = testGuid
            df2.at[pidx, 'name_2'] = guid_label[testGuid]
            df2.at[pidx, 'sex_2'] = guid_gender[testGuid]
            df2.at[pidx, 'seg_cm'] = cm
        if pd.notnull(df['matchesInCommon'][i]):
            for guid in df['matchesInCommon'][i].split(','):
                if not guid in guid_label:
                    sys.stderr.write('Warning: ' + guid + ' not in input matches file\n')
                    continue
                pidx = hash(tuple(sorted([testGuid, guid])))
                if not pidx in df2.index:
                    df2.at[pidx, 'human_id_1'] = testGuid
                    df2.at[pidx, 'name_1'] = guid_label[testGuid]
                    df2.at[pidx, 'sex_1'] = guid_gender[testGuid]
                    df2.at[pidx, 'human_id_2'] = guid
                    df2.at[pidx, 'name_2'] = guid_label[guid]
                    df2.at[pidx, 'sex_2'] = guid_gender[guid]
                    df2.at[pidx, 'seg_cm'] = float('NaN')
    df2.to_csv(args.o, sep = '\t', na_rep = 'NA', index = False)

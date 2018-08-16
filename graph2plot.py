#!/usr/bin/env python3
"""
   graph2plot.py - Generate visualization from graph file
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

import sys, argparse, pandas as pd, re, matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

try:
    import networkx as nx
except ImportError:
    sys.stderr.write('You need to install the networkx module first\n')
    sys.stderr.write('(run this in your terminal: "python -m pip install networkx" or "python -m pip install --user networkx")\n')
    exit(2)

rel_alg = {'AUNT': 2,
           'BROTHER': 1,
           'DAUGHTER': 1,
           'DISTANT_COUSIN': 10,
           'FATHER': 1,
           'FIFTH_COUSIN': 9,
           'FIRST_COUSIN': 3,
           'FOURTH_COUSIN': 9,
           'GRANDDAUGHTER': 2,
           'GRANDFATHER': 2,
           'GRANDMOTHER': 2,
           'GRANDSON': 2,
           'MOTHER': 1,
           'NEPHEW': 2,
           'NIECE': 2,
           'SECOND_COUSIN': 5,
           'SISTER': 1,
           'SIXTH_COUSIN': 10,
           'SON': 1,
           'THIRD_COUSIN': 7,
           'UNCLE': 2}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Generate visualization from graph file (16 Aug 2018)', add_help = False, usage = 'graph2plot.py [options]')
    parser.add_argument('-t', metavar = '<CHAR>', type = str, default = 'tab', help = 'separator [tab]')
    parser.add_argument('-n', action = 'store_true', default = False, help = 'whether to omit node names [False]')
    parser.add_argument('-l', action = 'store_true', default = False, help = 'whether to use ids rather than labels [False]')
    #parser.add_argument('-v', action = 'store_true', default = False, help = 'whether to remove HapMap/Mendel/Fisher 23andMe individuals [False]')
    parser.add_argument('-c', action = 'store_true', default = False, help = 'whether to convert special characters to _ [False]')
    parser.add_argument('-r', metavar = '<IID>', nargs = '+', type = str, help = 'list of individuals to remove')
    parser.add_argument('-R', metavar = '<FILE>', type = str, help = 'file with individuals to remove')
    parser.add_argument('-cm', metavar = '<FLOAT>', type = float, help = 'minimum number of centiMorgans')
    parser.add_argument('-anc', metavar = '<FILE>', type = str, help = 'AncestryDNA matches file')
    parser.add_argument('-rel', metavar = '<FILE>', type = str, help = '23andMe matches file')
    parser.add_argument('-f', metavar = '<IID>', nargs = '+', type = str, help = 'list of father proxies')
    parser.add_argument('-F', metavar = '<FILE>', type = str, help = 'matches file for the father')
    parser.add_argument('-m', metavar = '<IID>', nargs = '+', type = str, help = 'list of mother proxies')
    parser.add_argument('-M', metavar = '<FILE>', type = str, help = 'matches file for the mother')
    parser.add_argument('-s', metavar = '<FLOAT>', nargs = 2, type = float, default = [8.0, 6.0], help = 'size in inches [8.0 6.0]')
    parser.add_argument('-o', metavar = '<FILE>', type = str, help = 'output pdf file')
    try:
        parser.add_argument('-i', metavar = '[FILE]', type = argparse.FileType('r', encoding = 'UTF-8'), default = sys.stdin, help = 'sharing table [stdin]')
        # parser.add_argument('-i', metavar = '<FILE>', default = sys.stdin, help = 'input graph file [stdin]')
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

    remove = set()
    if args.r:
        remove |= set(args.r)
    if args.R:
        df = pd.read_csv(args.R, sep = '\t')
        if 'human_id' in df:
            remove |= set(df['human_id'])
        elif 'testGuid' in df:
            remove |= set(df['testGuid'])

    # shapes = 'so^>v<dph8'

    if args.anc:
        df = pd.read_csv(args.anc, sep = '\t')
        meiosis = pd.Series(df['meiosisValue'].values, index = df['testGuid']).to_dict()
        hint = pd.Series(df['hasHint'].values, index = df['testGuid']).to_dict()
        patside = pd.Series(df['patside'].values, index = df['testGuid']).to_dict() if 'patside' in df else pd.Series(False, index = df['testGuid']).to_dict()
        matside = pd.Series(df['matside'].values, index = df['testGuid']).to_dict() if 'matside' in df else pd.Series(False, index = df['testGuid']).to_dict()
        if args.F:
            df = pd.read_csv(args.F, sep = '\t')
            for guid in set(df['testGuid']).intersection(patside):
                patside[guid] = True
        if args.M:
            df = pd.read_csv(args.M, sep = '\t')
            for guid in set(df['testGuid']).intersection(matside):
                matside[guid] = True

    if args.rel:
        df = pd.read_csv(args.rel, sep = '\t')
        # gender = pd.Series(df['sex'].apply(str.lower).values, index = df['human_id']).to_dict()
        meiosis = pd.Series(df['rel_alg'].apply(lambda x: rel_alg[x]).values, index = df['human_id']).to_dict()
        hint = pd.Series(False, index = df['human_id']).to_dict()
        patside = pd.Series(df['patside'].values, index = df['human_id']).to_dict()
        matside = pd.Series(df['matside'].values, index = df['human_id']).to_dict()
        if args.F:
            df = pd.read_csv(args.F, sep = '\t')
            for ehid in set(df['human_id']).intersection(patside):
                patside[ehid] = True
        if args.M:
            df = pd.read_csv(args.M, sep = '\t')
            for ehid in set(df['human_id']).intersection(matside):
                matside[ehid] = True

    df = pd.read_csv(args.i, sep = '\t' if args.t == 'tab' else args.t)
    p1 = 'human_id_1' if args.l else 'name_1'
    p2 = 'human_id_2' if args.l else 'name_2'
    #if args.v:
    #    idx = df['p1'].apply(lambda x: x[0:2]!='v$') & df['p2'].apply(lambda x: x[0:2]!='v$')
    #    df = df.loc[idx]
    if args.c:
        df['name_1'] = df['name_1'].apply(lambda x: re.sub('[ .]','_',x))
        df['name_2'] = df['name_2'].apply(lambda x: re.sub('[ .]','_',x))

    if args.anc or args.rel:
        if args.f:
            for iid in [iid for iid in args.f if iid in patside]:
                patside[iid] = True
            for iid in [df.loc[i,'human_id_1'] for i in df.index if df.loc[i,'human_id_2'] in args.f if df.loc[i,'human_id_1'] in patside]:
                patside[iid] = True
            for iid in [df.loc[i,'human_id_2'] for i in df.index if df.loc[i,'human_id_1'] in args.f if df.loc[i,'human_id_2'] in patside]:
                patside[iid] = True
        if args.m:
            for iid in [iid for iid in args.m if iid in matside]:
                matside[iid] = True
            for iid in [df.loc[i,'human_id_1'] for i in df.index if df.loc[i,'human_id_2'] in args.m if df.loc[i,'human_id_1'] in matside]:
                matside[iid] = True
            for iid in [df.loc[i,'human_id_2'] for i in df.index if df.loc[i,'human_id_1'] in args.m if df.loc[i,'human_id_2'] in matside]:
                matside[iid] = True

    G = nx.Graph()
    for i in df.index:
        if df['human_id_1'][i] in remove or df['human_id_2'][i] in remove or args.rel and not (df['human_id_1'][i] in meiosis and df['human_id_2'][i] in meiosis):
            continue
        if not 'seg_cm' in df or pd.isnull(df['seg_cm'][i]) or not args.cm or df['seg_cm'][i] > args.cm:
            if args.anc or args.rel:
                G.add_node(df[p1][i], gender = df['sex_1'][i].lower(), meiosis = meiosis[df['human_id_1'][i]], hint = hint[df['human_id_1'][i]], patside = patside[df['human_id_1'][i]], matside = matside[df['human_id_1'][i]])
                G.add_node(df[p2][i], gender = df['sex_2'][i].lower(), meiosis = meiosis[df['human_id_2'][i]], hint = hint[df['human_id_2'][i]], patside = patside[df['human_id_2'][i]], matside = matside[df['human_id_2'][i]])
            else:
                G.add_node(df[p1][i], gender = df['sex_1'][i].lower())
                G.add_node(df[p2][i], gender = df['sex_2'][i].lower())
            G.add_edge(df[p1][i], df[p2][i])

    if args.o:
        pp = PdfPages(args.o)
        plt.figure(figsize = (args.s[0], args.s[1]))
    pos = nx.nx_pydot.pydot_layout(G) # python3-pydotplus needs to be installed

    colors = {(False, False, False): 'white',      (False, False, True): 'gray',
              (False, True,  False): 'pink',       (False, True,  True): 'deeppink',
              (True,  False, False): 'lightblue',  (True,  False, True): 'blue',
              (True,  True,  False): 'lightgreen', (True,  True,  True): 'green'}

    shapes = {'male': 's', 'female': 'o', 'unknown': 'd'}

    if args.anc or args.rel:
        sizes = [size for size in [2048, 1536, 1024, 768, 512, 384, 256, 192, 128, 32, 32]]
        for gender in 'male', 'female', 'unknown':
            for meiosis in set([value['meiosis'] for key, value in G.node.items()]):
                for patside in True, False:
                    for matside in True, False:
                        for hint in True, False:
                            nodelist = [key for (key, value) in G.node.items() if value['gender'] == gender and value['meiosis'] == meiosis and value['hint'] == hint and value['patside'] == patside and value['matside'] == matside]
                            nx.draw_networkx_nodes(G, pos, nodelist = nodelist, node_color = colors[(patside, matside, hint)], node_shape = shapes[gender], node_size = sizes[meiosis - 1], alpha = 1)
    else:
        for gender in 'male', 'female', 'unknown':
            nodelist = [key for (key, value) in G.node.items() if value['gender'] == gender]
            nx.draw_networkx_nodes(G, pos, nodelist = nodelist, node_color = 'white', node_shape = shapes[gender], node_size = 100, alpha = .5)
    nx.draw_networkx_edges(G, pos, edge_color = 'gray', alpha = .25)
    if not args.n:
        nx.draw_networkx_labels(G, pos, font_size = 8)

    plt.axis('off')
    if args.o:
        pp.savefig()
        pp.close()
    else:
        plt.show()

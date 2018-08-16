#!/usr/bin/env python3
"""
   matches2plot.py - Creates a plot of sharing
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

import sys, argparse, pandas as pd, numpy as np, matplotlib, matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Creates a plot of sharing (16 Aug 2018)', add_help = False, usage = 'matches2plot.py -a <table1> -b <table2> [options]')
    parser.add_argument('-a', metavar = '<FILE>', required = True, type = str, help = 'table1')
    parser.add_argument('-b', metavar = '<FILE>', required = True, type = str, help = 'table2')
    parser.add_argument('-l', metavar = '<STR>', type = str, help = 'title')
    parser.add_argument('-la', metavar = '<STR>', type = str, help = 'label1')
    parser.add_argument('-lb', metavar = '<STR>', type = str, help = 'label2')
    parser.add_argument('-fs', metavar = '<INT>', type = int, default = 16, help = 'font size')
    parser.add_argument('-o', metavar = '<FILE>', type = str, help = 'output pdf file')

    # extract arguments from the command line
    try:
        parser.error = parser.exit
        args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        exit(2)

    df1 = pd.read_csv(args.a, sep = '\t')
    df2 = pd.read_csv(args.b, sep = '\t')
    if ('ehid' in df1 and 'pct' in df1 and 'ehid' in df2 and 'pct' in df2):
        iid = 'ehid'
        share = 'pct'
        unit = 'pct'
        minvalue = .07
        maxvalue = 2
        ticks = [.1, .2, .5, 1]
    elif ('testGuid' in df1 and 'sharedCentimorgans' in df1 and 'testGuid' in df2 and 'sharedCentimorgans' in df2):
        iid = 'testGuid'
        share = 'sharedCentimorgans'
        unit = 'cM'
        minvalue = 4.5
        maxvalue = 100
        ticks = [5, 10, 20, 50]
    else:
        exit

    df1 = df1[[iid, share]].dropna().rename(columns = {iid: 'iid', share: 'x'})
    df2 = df2[[iid, share]].dropna().rename(columns = {iid: 'iid', share: 'y'})
    if df1['x'].dtype == np.object:
        df1['x'] = df1['x'].replace({'%': ''}, regex = True).astype(float)
        df2['y'] = df2['y'].replace({'%': ''}, regex = True).astype(float)
    df = df1.merge(df2)

    far = abs(df['x'] - df['y']) > min(ticks)

    if args.o:
        pp = PdfPages(args.o)
        plt.figure()
    fig, ax = plt.subplots()
    matplotlib.rcParams.update({'font.size': args.fs})
    ax.scatter(df.ix[~far, 'x'], df.ix[~far, 'y'], color = 'blue', marker = 'x')
    ax.scatter(df.ix[far, 'x'], df.ix[far, 'y'], color = 'red', marker = 'x')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks(ticks)
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_yticks(ticks)
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlim(minvalue, maxvalue)
    ax.set_ylim(minvalue, maxvalue)
    ax.plot([minvalue, maxvalue], [minvalue, maxvalue], '-', color = 'gray', lw = 1)
    ax.grid()
    if args.l:
        ax.set_title(args.l)
    if args.la:
        ax.set_xlabel('shared with ' + args.la + ' (' + unit + ')')
    if args.lb:
        ax.set_ylabel('shared with ' + args.lb + ' (' + unit + ')')
    plt.gcf().subplots_adjust(bottom=0.15)
    # plt.gcf().tight_layout()
    if args.o:
        pp.savefig()
        pp.close()
    else:
        plt.show()

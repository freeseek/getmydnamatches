#!/usr/bin/env python3
"""
   getmy23andme.py - Retrieve DNA matches information from 23andMe
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

import sys, argparse, getpass, time, re, json, html.parser, pandas as pd
from io import StringIO
import itertools

try:        
    import asyncio
except TypeError:
    sys.stderr.write('You need Python >= 3.4 to use the asyncio module\n')
    sys.stderr.write('(see https://docs.python.org/3/whatsnew/3.4.html#asyncio)\n')
    exit(2)

try:
    import requests
except ImportError:
    sys.stderr.write('You need to install the requests module first\n')
    sys.stderr.write('(run this in your terminal: "python3 -m pip install requests" or "python3 -m pip install --user requests")\n')
    exit(2)

class Session:
    def __init__(self, username, password, verbose, logfile, timeout):
        self.username = username
        self.password = password
        self.verbose = verbose
        self.logfile = logfile
        self.timeout = timeout
        self.retry = 0
        self.maxretry = 10
        self.s = requests.Session()
        self.login()

    def login(self):
        url = 'https://auth.23andme.com/login/'
        while True:
            try:
                r = self.s.get(url, timeout = self.timeout)
            except requests.exceptions.ReadTimeout:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Read timed out\n')
                continue
            except requests.exceptions.ConnectionError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Connection aborted\n')
                time.sleep(self.timeout)
                continue
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Status code ' + str(r.status_code) + '\n')

            # extract csrftoken
            cookies = requests.utils.dict_from_cookiejar(self.s.cookies)
            csrftoken = cookies['csrftoken']
            # extract csrfmiddlewaretoken
            text = r.text
            regexp = re.compile('name=\"csrfmiddlewaretoken\" value=\".*\"')
            res = regexp.search(text)
            csrfmiddlewaretoken = text[res.span()[0]+34:res.span()[1]-1]
            data = { 'csrfmiddlewaretoken': csrfmiddlewaretoken, 'username': self.username, 'password': self.password }
            # set header to avoid receiving a 403 response
            headers = { 'referer': url }

            try:
                r = self.s.post(url, cookies = { 'csrftoken': csrftoken }, data = data, headers = headers, timeout = self.timeout)
            except requests.exceptions.ReadTimeout:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Read timed out\n')
                continue
            except requests.exceptions.ConnectionError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Connection aborted\n')
                time.sleep(self.timeout)
                continue
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Status code ' + str(r.status_code) + '\n')
            cookies = requests.utils.dict_from_cookiejar(self.s.cookies)
            self.cookies = { 'sessionid': cookies['sessionid'] }
            self.retry = 0
            return

    def get_url(self, url, xhr = False, data = None):
        headers = { 'X-Requested-With': 'XMLHttpRequest' } if xhr else None
        while True:
            if self.retry > self.maxretry:
                self.login() # here it should also switch back to the previous profile
            try:
                if data:
                    r = self.s.post(url, cookies = self.cookies, data = data, headers = headers, timeout = self.timeout)
                else:
                    r = self.s.get(url, cookies = self.cookies, headers = headers, timeout = self.timeout)
            except requests.exceptions.ReadTimeout:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Read timed out\n')
                self.retry += 1
                continue
            except requests.exceptions.ConnectionError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Connection aborted\n')
                time.sleep(self.timeout)
                self.retry += 1
                continue
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' Status code ' + str(r.status_code) + '\n')
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError:
                if r.status_code == 403:
                    return None
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' HTTPError\n')
                time.sleep(self.timeout)
                self.retry += 1
                continue
            text = html.parser.unescape(r.text)
            if r.text == '191919':
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] ' + url + ' 191919\n')
                self.retry += 1
                continue
            else:
                return text

    # this function retrieves the list of profiles from the https://www.23andme.com/you/ page
    # (maybe there is a more direct way to request this list but I could not figure it out)
    def get_account(self):
        text = self.get_url('https://www.23andme.com/you/')
        text = html.parser.unescape(re.sub(' *\n *', '', text))

#        regexp = re.compile('dataLayer = \[.*?\];')
#        res = regexp.search(text)
#        line = text[res.span()[0]:res.span()[1]]
#        dataLayer = json.loads(line[12:-1])

        regexp = re.compile('new exports.quickInviteModal\(\[\{.*?\}\],"' + '[0-f]'*16 + '"\);new')
        res = regexp.search(text)
        line = text[res.span()[0]+29:res.span()[1]-24]
        profile_data = json.loads(line)
        return profile_data

    # download list of connections
    def get_connections(self):
        text = self.get_url('https://you.23andme.com/tools/your-connections/connection/?limit=1000&offset=0', True)
        return json.loads(text)

    # switch profile
    def switch_profile(self, profile_id):
        self.get_url('https://you.23andme.com/switch-profile/?profile-id=' + profile_id)
        return

    # download list of profiles
    def get_profiles(self):
        text = self.get_url('https://you.23andme.com/tools/relatives/dna/ajax/?limit=1000&offset=0')
        return json.loads(text)

    # download list of relatives
    def get_relatives(self):
        text = self.get_url('https://you.23andme.com/tools/relatives/ajax/?limit=2000&offset=0')
        if text:
            return json.loads(text)
        else:
            return None

    # download aggregate data with all relatives
    def get_aggregate(self):
        text = self.get_url('https://you.23andme.com/tools/relatives/download/')
        return StringIO(text)

    # download list of relatives shared with a match
    def get_relatives_in_common(self, match_id):
        text = self.get_url('https://you.23andme.com/tools/compare/match/relatives_in_common/?remote_id=' + match_id + '&limit=1000&offset=0')
        return json.loads(text)

    # download pairwise IBD information
    def get_ibd(self, human_id_1, human_id_2):
        text = self.get_url('https://you.23andme.com/tools/ibd/?human_id_1=' + human_id_1 + '&human_id_2=' + human_id_2)
        return json.loads(text)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Retrieve DNA matches from 23andMe (16 Aug 2018)', add_help = False, usage = 'getmy23andme.py -u <username> -p <password> [options]')
    parser.add_argument('-u', metavar = '<STR>', type = str, help = '23andMe username [prompt]')
    parser.add_argument('-p', metavar = '<STR>', type = str, help = '23andMe password [prompt]')
    parser.add_argument('-v', action = 'store_false', default = True, help = 'whether to use verbose mode [True]')
    parser.add_argument('-t', metavar = '<INT>', type = int, default = 60, help = 'timeout in seconds [60]')
    parser.add_argument('-o', metavar = '<STR>', type = str, help = 'output prefix [account_id]')
    parser.add_argument('-x', action = 'store_true', default = False, help = 'whether to download inheritance and ibdview tables [False]')
    parser.add_argument('-l', metavar = '<FILE>', type = argparse.FileType('w', encoding = 'UTF-8'), default = sys.stderr, help = 'output log file [stderr]')

    # extract arguments from the command line
    try:
        parser.error = parser.exit
        args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        exit(2)

    username = args.u if args.u else input("Enter 23andMe username: ")
    password = args.p if args.p else getpass.getpass("Enter 23andMe password: ")
    verbose = args.v
    logfile = args.l
    timeout = args.t

    # initialize a session with 23andMe server
    session = Session(username, password, verbose, logfile, timeout)

    # download list of profiles owned by the account
    data = session.get_account()
    out = args.o if args.o else 'out' # dataLayer[0]['account_id']
    df = pd.DataFrame(data)
    df[['id', 'sex', 'first_name', 'last_name']].to_csv(out + '.tsv', sep = '\t', na_rep = 'NA', index = False)
    ehids = df['id']

    data = session.get_connections()
    df = pd.DataFrame(data['data'])
    connections = set(df['profile_id'])
    df.to_csv(out + '.connections.tsv', sep = '\t', na_rep = 'NA', index = False)

    # generate a loop executor in case IBD information is requested
    if args.x:
        pairs = set()
        loop = asyncio.get_event_loop()

    # download list of relatives
    for ehid in ehids:
        session.switch_profile(ehid)

        data = session.get_profiles()
        df = pd.DataFrame(data['profiles'])
        df.to_csv(out + '.' + ehid + '.profiles.tsv', sep = '\t', na_rep = 'NA', index = False)
        
        data = session.get_aggregate()
        df = pd.read_csv(data)
        df.to_csv(out + '.' + ehid + '.aggregate.tsv', sep = '\t', na_rep = 'NA', index = False)

        data = session.get_relatives()
        if data:
            df = pd.DataFrame(data['relatives'])
            df.to_csv(out + '.' + ehid + '.relatives.tsv', sep = '\t', na_rep = 'NA', index = False)

        # download list of IBD pairs
        if args.x and data:
            idx = (df['new_share_status']!='NONE') & (df['new_share_status']!='PRE_YOUDOT_ANON') & (df['new_share_status']!='PRE_YOUDOT_PUBLIC')
            match_ids = df[idx]['match_id']
            if args.v:
                args.l.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] Downloading ' + str(len(match_ids)) + ' DNA matches\n')
            pairs |= {(x[0], x[1]) if x[0]<x[1] else (x[1], x[0]) for x in zip(itertools.repeat(ehid), df[idx]['human_id'])}
            async def donwload_relatives_in_common(loop):
                futures = [loop.run_in_executor(None, session.get_relatives_in_common, match_id) for match_id in match_ids]
                for future in futures:
                    await future
                return futures
            futures = loop.run_until_complete(donwload_relatives_in_common(loop))
            for future in futures:
                df = pd.DataFrame(future.result()['relatives_in_common'])
                if df.empty: continue
                idx = df['is_open_sharing'] | df['owner_ehid'].isin(connections)
                df = df[idx][['local_ehid', 'owner_ehid', 'remote_ehid']]
                for (a, b) in [('local_ehid', 'owner_ehid'), ('local_ehid', 'remote_ehid'), ('owner_ehid', 'remote_ehid')]:
                    pairs |= {(x[0], x[1]) if x[0]<x[1] else (x[1], x[0]) for x in zip(df[a], df[b]) if x[0] and x[1]}

    # download pairwise IBD sharing
    if args.x:
        if args.v:
            args.l.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + '] Downloading ' + str(len(pairs)) + ' IBD matches\n')
        async def donwload_ibd(loop):
            futures = [loop.run_in_executor(None, session.get_ibd, pair[0], pair[1]) for pair in pairs]
            for future in futures:
                await future
            return futures
        futures = loop.run_until_complete(donwload_ibd(loop))
        ibd = [y for x in futures for y in x.result()]
        df = pd.DataFrame(ibd)
        df.to_csv(out + '.ibd.tsv', sep = '\t', na_rep = 'NA', index = False)

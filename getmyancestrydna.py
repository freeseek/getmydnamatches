#!/usr/bin/env python3
"""
   getmyancestrydna.py - Retrieve DNA matches information from AncestryDNA
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

import sys, argparse, getpass, time, re, json, pandas as pd

try:
    import requests
except ImportError:
    sys.stderr.write('You need to install the requests module first\n')
    sys.stderr.write('(run this in your terminal: "python3 -m pip install requests" or "python3 -m pip install --user requests")\n')
    exit(2)

class Session:
    def __init__(self, username, password, verbose, logfile, timeout, urlpfx = 'https://www.ancestry.com/dna/secure/'):
        self.username = username
        self.password = password
        self.verbose = verbose
        self.logfile = logfile
        self.timeout = timeout
        self.urlpfx = urlpfx
        self.s = requests.Session()
        # self.dnaVersion = self.get_dna_version()
        self.login()

    # This does not seem required anymore
    def get_dna_version(self):
        url = 'http://www.ancestry.com/dna/'
        while True:
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Downloading: ' + url + '\n')
            try:
                r = self.s.get(url, timeout = self.timeout)
            except requests.exceptions.ReadTimeout:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Read timed out\n')
                continue
            except requests.exceptions.ConnectionError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Connection aborted\n')
                time.sleep(self.timeout)
                continue
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Status code: ' + str(r.status_code) + '\n')
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: HTTPError\n')
                time.sleep(self.timeout)
                continue
            text = re.findall(r'var dna.*?=\s*(.*?);', r.text, re.DOTALL | re.MULTILINE)[0] # http://stackoverflow.com/questions/18368058/how-can-i-parse-javascript-variables-using-python
            text = re.sub('([a-zA-Z0-9]*) ?: ?({|\'|true|false|!1)', '"\g<1>": \g<2>', text) # enclose property names in double quotes
            text = re.sub('/\*.*\*/', '', text) # remove comments
            text = re.sub('\'(.*)\'', '"\g<1>"', text) # change single quotes to double quotes
            try:
                dna = json.loads(text)
                return dna['app']['version']
            except:
                if self.verbose:
                    self.logfile.write(r.text + '\n')
                time.sleep(self.timeout)
                self.s = requests.Session() # sometimes the session will repeatedly fail and will need to be reset

    def login(self):
        url = 'https://www.ancestry.com/secure/login'
        data = { 'username': self.username, 'password': self.password}
        while True:
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Downloading: ' + url + '\n')
            try:
                r = self.s.post(url, data = data, timeout = self.timeout)
            except requests.exceptions.ReadTimeout:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Read timed out\n')
                continue
            except requests.exceptions.ConnectionError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Connection aborted\n')
                time.sleep(self.timeout)
                continue
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Status code: ' + str(r.status_code) + '\n')
            cookies = requests.utils.dict_from_cookiejar(self.s.cookies)
            self.cookies = { 'ATT': cookies['ATT'] }
            return

    def get_url(self, url):
        while True:
            # headers = { 'dnaVersion' : self.dnaVersion }
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Downloading: ' + url + '\n')
            try:
                r = self.s.get(url, cookies = self.cookies, timeout = self.timeout)
            except requests.exceptions.ReadTimeout:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Read timed out\n')
                continue
            except requests.exceptions.ConnectionError:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Connection aborted\n')
                time.sleep(self.timeout)
                continue
            if self.verbose:
                self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: Status code: ' + str(r.status_code) + '\n')
            if r.status_code == 503:
                time.sleep(self.timeout)
                continue
            if r.status_code == 426:
                if self.verbose:
                    self.logfile.write('[' + time.strftime("%Y-%m-%d %H:%M:%S") + ']: dnaVersion version became outdated during download\n')
                self.dnaVersion = self.get_dna_version()
                continue
            if self.verbose:
                self.logfile.write(r.text + '\n')
            return r.json() if r.text else r.text

    def get_tests(self):
        url = self.urlpfx + 'tests'
        tests = self.get_url(url)
        return tests

    def get_testinfo(self, guid):
        url = self.urlpfx + 'testSettings/' + guid + '/testInfo'
        testinfo = self.get_url(url)
        return testinfo

    def get_matches(self, guid, guidMatch = None):
        page = 1
        pages = list()
        while True:
            if guidMatch:
                # url = 'http://dna.ancestry.com/secure/tests/' + guid + '/matches?relationGuid=' + testGuid + '&page=' + str(page)
                url = self.urlpfx + 'tests/' + guid + '/matchesInCommon?matchTestGuid=' + guidMatch + '&page=' + str(page)
            else:
                url = self.urlpfx + 'tests/' + guid + '/matches?page=' + str(page)
            matches = self.get_url(url)
            pages.append(matches)
            # if page < matches['pageCount']:
            if len(matches['matchGroups']) > 0:
                page += 1
            else:
                break
        return [match for page in pages for group in page['matchGroups'] for match in group['matches']]

    def get_match_info(self, guid, testGuid):
        url = self.urlpfx + 'tests/' + guid + '/matches/' + testGuid
        matchInfo = self.get_url(url)
        return matchInfo

    def get_match_ethnicity(self, guid, testGuid):
        url = self.urlpfx + 'tests/' + guid + '/matches/' + testGuid + '/ethnicity'
        ethnicity = self.get_url(url)
        return ethnicity

    def get_parents(self, guid):
        url = self.urlpfx + 'tests/' + guid + '/parents'
        parents = self.get_url(url)
        return parents

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Retrieve DNA matches from AncestryDNA (16 Aug 2018)', add_help = False, usage = 'getmyancestrydna.py -u <username> -p <password> [options]')
    parser.add_argument('-u', metavar = '<STR>', type = str, help = 'AncestryDNA username [prompt]')
    parser.add_argument('-p', metavar = '<STR>', type = str, help = 'AncestryDNA password [prompt]')
    parser.add_argument('-x', action = 'store_true', default = False, help = 'whether to download the list of shared matches [False]')
    parser.add_argument('-v', action = 'store_false', default = True, help = 'whether to use verbose mode [True]')
    parser.add_argument('-t', metavar = '<INT>', type = int, default = 60, help = 'timeout in seconds [60]')
    parser.add_argument('-o', metavar = '<STR>', type = str, help = 'output prefix [ucdmId]')
    try:        
        parser.add_argument('-l', metavar = '<FILE>', type = argparse.FileType('w', encoding = 'UTF-8'), default = sys.stderr, help = 'output log file [stderr]')
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

    username = args.u if args.u else input("Enter AncestryDNA username: ")
    password = args.p if args.p else getpass.getpass("Enter AncestryDNA password: ")
    extra = args.x
    verbose = args.v
    logfile = args.l
    timeout = args.t
    outfile = args.o

    # initialize a session with AncestryDNA server
    session = Session(username, password, verbose, logfile, timeout)

    # download list of tests handled in the account
    tests = session.get_tests()
    out = outfile if outfile else tests['data']['completeTests'][0]['testAdminUcdmId']
    keys = ['shippedToLabOn', 'activationCode', 'activatedOn', 'role', 'state', 'lastUpdated', 'processingBegan', 'testAdminDisplayName', 'testAdminUcdmId', 'usersSelfTest', 'recollectable', 'adminDisplayName', 'privateName', 'gender', 'surname', 'ucdmId', 'givenNames', 'notificationCount', 'selfTest', 'guid']
    df_tests = pd.DataFrame(columns = keys)
    for test in tests['data']['completeTests']:
        for key, value in test.items():
            if key == 'testSubject':
                for key2, value2 in value.items():
                    df_tests.at[test['guid'], key2] = value2
            else:
                df_tests.at[test['guid'], key] = value
    df_tests.to_csv(out + '.tsv', sep = '\t', na_rep = 'NA', index = False)

    # download match details for each test
    for guid in df_tests['guid']:
        parents = session.get_parents(guid)
        testinfo = session.get_testinfo(guid)
        matches = session.get_matches(guid)
        keys = ['dnaMatch', 'lastLoggedInDate', 'megaBases', 'ignored', 'testGuid', 'hasHint', 'starred', 'matchTreeId', 'matchTreeNodeCount', 'matchTestAdminDisplayName', 'hasNote', 'userPhoto', 'sharedCentimorgans', 'matchTreeDisplayName', 'matchTestDisplayName', 'matchTreeIsPrivate', 'meiosisValue', 'matchTestSubjectIsAdmin', 'note', 'subjectGender', 'viewed', 'confidence', 'relativeDate', 'sharedSegments', 'hideManagedByInfo']
        df = pd.DataFrame(index = [match['testGuid'] for match in matches], columns = keys)
        if extra:
            df.at[guid, 'patside'] = True
            df.at[guid, 'matside'] = True
        df.at[guid, 'testGuid'] = guid
        df.at[guid, 'matchTestDisplayName'] = testinfo['givenNames'] + ' ' + testinfo['surname']
        df.at[guid, 'subjectGender'] = testinfo['gender']
        df.at[guid, 'meiosisValue'] = 0
        df.at[guid, 'hasHint'] = True
        df.at[guid, 'matchTestSubjectIsAdmin'] = True
        for match in matches:
            for key, value in match.items():
                if not key in keys:
                    raise Exception('Key ' + key + ' missing from data frame table')
                df.at[match['testGuid'], key] = value
            if extra:
                ethnicity = session.get_match_ethnicity(guid, match['testGuid'])
                if ethnicity:
                    for key, value in ethnicity.items():
                        df.at[match['testGuid'], key] = ','.join(value) if value else 'NA'
                matchInfo = session.get_match_info(guid, match['testGuid'])
                df.at[match['testGuid'], 'cadGroups'] = str(matchInfo['cadGroups']) if matchInfo['cadGroups'] else 'NA'
                df.at[match['testGuid'], 'sharedSegments'] = str(matchInfo['sharedSegments']) if matchInfo['sharedSegments'] else 0
                matchesInCommon = session.get_matches(guid, match['testGuid'])
                shared = [match['testGuid'] for match in matchesInCommon]
                df.at[match['testGuid'], 'patside'] = parents['father']['testGuid'] in shared
                df.at[match['testGuid'], 'matside'] = parents['mother']['testGuid'] in shared
                df.at[match['testGuid'], 'matchesInCommon'] = ','.join(shared) if shared else 'NA'
                
        df.to_csv(out + '.' + guid + '.tsv', sep = '\t', na_rep = 'NA', index = False)

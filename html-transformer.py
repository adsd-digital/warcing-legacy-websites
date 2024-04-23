# Module based on https://github.com/webrecorder/warcit/blob/help-text-slash/warcit/converter.py,
# Copyright 2017-2020 Webrecorder Software LLC, Rhizome, and Contributors.
# Authored by Ilya Kreymer

# The html-transformer module can be used to adapt html files produced by the web crawlers Teleport Pro and Offline
# Explorer Pro and of files exported from the proprietary data base of Offline Web Archiv to a folder structure.
# The adapted files are written to a transformations folder, the paths are written to a 
# warcit-html-transformation-results.yaml. This yaml file is then the foundation for the warcit process - in the WARC 
# file both the "original" and the transformed files are added.

from __future__ import absolute_import

import csv

import yaml
import logging
import re
import os
import subprocess
import pkgutil
import shutil
import magic
import html
import datetime
import sys


from collections import defaultdict
from argparse import ArgumentParser, RawTextHelpFormatter

from warcit.base import BaseTool, get_version, init_logging, FileInfo
from warcio.timeutils import timestamp_now

logger = logging.getLogger('WARCIT')

RULES_FILE = 'default-html-transformation-rules.yaml'

RESULTS_FILE = 'warcit-html-transformation-results.yaml'

NO_TLD_FILE = 'no-tld-test.csv'

BUFF_SIZE = 2048


# ============================================================================
def main(args=None):
    parser = ArgumentParser(description='Perform transformation of html files based on ' +
                                        'transformation rules (in preparation for WARC storage)')

    parser.add_argument('-V', '--version', action='version', version=get_version())

    parser.add_argument('--dry-run', action='store_true')

    parser.add_argument('--output-dir', help='Root output directory for transformations')

    parser.add_argument('-q', '--quiet', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    parser.add_argument('--results', help='YAML file to write transformation results to',
                        default=RESULTS_FILE)

    parser.add_argument('--no_tld', help='CSV file to write endings not treated as TLD to',
                        default=NO_TLD_FILE)

    parser.add_argument('--rules', help='Transformation rules YAML file')

    parser.add_argument('url_prefix',
                        help='''The base URL for all items to be included, including
                                protocol. Example: https://cool.website:8080/files/''')

    parser.add_argument('inputs', nargs='+',
                        help='''Paths of directories and/or files to be checked for transformation''')

    r = parser.parse_args(args=args)

    init_logging(r)

    transformer = FileConverter(rules_filename=r.rules,
                                inputs=r.inputs,
                                url_prefix=r.url_prefix,
                                output_dir=r.output_dir,
                                results_file=r.results,
                                no_tld_file=r.no_tld)

    transformer.convert_all(dry_run=r.dry_run)


# ============================================================================
class FileConverter(BaseTool):
    def __init__(self, rules_filename, inputs, url_prefix=None, output_dir=None, results_file=None,
                 no_tld_file=None):

        # if no rules specified, load default rules from package
        if not rules_filename:
            rules = yaml.safe_load(pkgutil.get_data('warcit', RULES_FILE))

        else:
            with open(rules_filename, 'rt') as fh:
                rules = yaml.safe_load(fh.read())

        self.convert_stdout = rules.get('convert_stdout')

        self.output_dir = output_dir or rules.get('output_dir', '.')

        url_prefix = url_prefix or rules['url_prefix']

        self.no_tld_file = no_tld_file or NO_TLD_FILE

        self.results_file = results_file or RESULTS_FILE

        self.results = defaultdict(list)

        super(FileConverter, self).__init__(url_prefix=url_prefix,
                                            inputs=inputs)

        for file_type in rules['file_types']:
            if 'regex' in file_type:
                file_type['regex'] = re.compile(file_type.get('regex'))

        self.file_types = rules['file_types']

    def write_results(self):
        filename = os.path.join(self.output_dir, self.results_file)

        self._ensure_dir(filename)

        try:
            with open(filename, 'rt') as fh:
                root = yaml.safe_load(fh.read())
        except:
            root = {}

        if 'transformations' not in root:
            root['transformations'] = {}

        transformations = root['transformations']
        transformations.update(self.results)

        with open(filename, 'wt') as fh:
            fh.write(yaml.dump(root, default_flow_style=False))

    def write_tld(self, row):
        filename = os.path.join(self.output_dir, self.no_tld_file)
        #print(row)

        self._ensure_dir(filename)

        writer = csv.writer(open(filename, "a+"))
        writer.writerow(row)

    def convert_all(self, dry_run=False):
        stdout = None
        if self.convert_stdout:
            stdout = open(self.convert_stdout, 'wt')

        # TODO: change code so that first line is not added for every call of html-transformer
        if not dry_run:
            self.write_tld(["endung", "tld", "file", "pfad", "neuer pfad"])

        try:
            for file_info in self.iter_inputs():
                self.convert_file(file_info,
                                  dry_run=dry_run,
                                  convert_stdout=stdout,
                                  convert_stderr=stdout)

                if not dry_run:
                    self.write_results()

        finally:
            if stdout:
                stdout.close()

    def convert_file(self, file_info, dry_run=False, convert_stdout=None, convert_stderr=None):
        for file_type in self.file_types:
            matched = False
            # first, check by extension if available
            mimetype = self.guess_type(file_info)

            if mimetype == "text/html":
                matched = True
            elif 'ext' in file_type and file_info.url.endswith(file_type['ext']):
                matched = True
            elif 'regex' in file_type and file_type['regex'].match(file_info.url):
                matched = True

            if matched:
                # TODO change rudimentary print output to logging for filetypes
                print(mimetype + ',' + file_info.full_filename + ',' + file_info.url[-4:])
                self.logger.info('Converting: ' + file_info.url)

                for transformation in file_type['transformation_rules']:
                    if transformation.get('skip'):
                        self.logger.debug('Skipping: ' + transformation['name'])
                        continue

                    output = self.get_output_filename(file_info.full_filename,
                                                      dry_run=dry_run,
                                                      root_dir=file_info.root_dir)

                    self.logger.debug('Output Filename: ' + output)
                    original = file_info.full_filename
                    change = False
                    process_result = self.process_html_file(original)
                    processed_html = process_result[0]
                    if process_result[1] > 0:
                        change = True
                        with open(output, 'w', encoding='latin-1') as file:
                            file.write(processed_html)
                    # TODO: at the moment: for testing purposes: new date - if old date is copied to a file
                    # that leads to the effect, that the transformed file can't be accessed in pywb
                    #self.copy_file_timestamps(original, output)

                    result = {'url': file_info.url,
                              'output': output,
                              'metadata': transformation,
                              'type': 'transformation',
                              'change': change,
                              }

                    self.results[file_info.url].append(result)

    def get_output_filename(self, convert_filename, dry_run=False, root_dir=''):
        rel_filename = os.path.relpath(convert_filename, root_dir)
        full_path = os.path.abspath(os.path.join(self.output_dir, os.path.basename(root_dir), rel_filename))

        if not dry_run:
            self._ensure_dir(full_path)

        return full_path

    def _ensure_dir(self, full_path):
        try:
            os.makedirs(os.path.dirname(full_path))
        except OSError as oe:
            if oe.errno != 17:
                self.logger.error(str(oe))

    def process_html_file(self, input_file):
        # Read the HTML content

        with open(input_file, 'rb') as file:
            # Decode the file using 'latin-1' encoding
            html_content = file.read().decode('latin-1')

        # Regex pattern to find relative paths with at least one '../' segments, followed by potential domain
        #     \.\./{1,}: matches at least one "../" segment
        #     ([^./\n]+\.){1,}: matches at least one string of characters, that is ended by a dot
        #                       the string of characters before the dot can contain any character except dot, forward
        #                       slash and new line
        #     ([^./\n\s]+): matches a string of characters, that contains any character except for dot, forward slash,
        #                   new line or space
        pattern2 = r'(\.\.\/){1,}([^./\n]+\.){1,}([^./<>\n\s]+)'
        pattern = r'(\.\.\/){1,}([^.\/\n\s]+\.){1,}([^.\/<>\n\s]+)'
        # TODO get list of Top Level Domains from external document, e.g. transformations-rules.yaml
        tld_list = ["be", "com", "de", "org", "net"]

        def replace_path(match):
            # Replace the matched relative path with 'http://'
            new_path = match.group(0)
            old_path = new_path
            relative_path = match.group(1)
            last_segment = match.group(3)
            if not (last_segment in tld_list):
                self.write_tld([last_segment, "", input_file, old_path])
            else:
                rest = match.group(2)
                # TODO: check: is it necessary to differentiate between http and https?
                # If so: where can the info which case to choose be found?
                new_path = 'http://' + old_path.replace('../', '')
                self.write_tld(([last_segment, "yes", input_file, old_path, new_path]))
            return new_path

        # Replace relative paths in the HTML content
        modified_content = re.subn(pattern, replace_path, html_content)
        return modified_content

    def copy_file_timestamps(self, source, destination):
        # Copy creation and modification timestamps from source to destination
        stat_info = os.stat(source)
        os.utime(destination, (stat_info.st_atime, stat_info.st_mtime))

    def guess_type(self, file_info):
        self.magic = magic.Magic(mime=True)
        with file_info.open() as fh:
            mime = self.magic.from_buffer(fh.read(BUFF_SIZE))

        # TODO for testing purposes: if no type is assigned, treat as text/html;
        # marked with ?? so those files can be retrieved in rudimentary log
        mime = mime or 'text/html??'

        return mime




# ============================================================================
class TransformationSerializer(object):
    def __init__(self, results_filename):
        with open(results_filename, 'rt') as fh:
            results = yaml.safe_load(fh.read())

        self.transformations = results.get('transformations', {})

    def find_transformations(self, url):
        matched = self.transformations.get(url)
        if not matched:
            return

        for transf in matched:
            if not transf.get('change'):
                logger.warn('Skipping unchanged transformation: {0}'.format(transf.get('output')))
                continue

            file_info = FileInfo(url=transf['url'], filename=transf['output'])
            yield file_info, transf.get('type', 'transformation'), transf.get('metadata')




# ============================================================================
if __name__ == "__main__":  # pragma: no cover
    res = main()
    # sys.exit(res)


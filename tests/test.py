#!/usr/bin/env python3

"""Tests for the validity of the channel and repository files.

You can run this script directly or with `python -m unittest` from this or the
root directory. For some reason `nosetests` does not pick up the generated tests
even though they are generated at load time.

However, only running the script directly will generate tests for all
repositories in channel.json. This is to reduce the load time for every test run
by travis (and reduces unnecessary failures).
"""

import os
import re
import json
import unittest

# from collections import OrderedDict
# from functools import wraps
# from urllib.request import urlopen
# from urllib.error import HTTPError


################################################################################
# Utilities


def _open(filepath, *args, **kwargs):
    """Wrapper function that can search one dir above if the desired file
    does not exist.
    """
    if not os.path.exists(filepath):
        filepath = os.path.join("..", filepath)

    return open(filepath, *args, **kwargs)


def get_package_name(data):
    """Gets "name" from a package with a workaround when it's not defined.

    Use the last part of details url for the package's name otherwise since
    packages must define one of these two keys anyway.
    """
    return data.get('name') or data.get('details').rsplit('/', 1)[-1]


################################################################################
# Tests


class TestContainer(object):
    """Contains tests that the generators can easily access (when subclassing).

    Does not contain tests itself, must be used as mixin with unittest.TestCase.
    """

    package_key_types_map = {
        'name': str,
        'details': str,
        'description': str,
        'releases': list,
        'homepage': str,
        'author': str,
        'readme': str,
        'issues': str,
        'donate': str,
        'buy': str,
        'previous_names': list,
        'labels': list
    }

    def _test_repository_keys(self, include, data):
        keys = sorted(data.keys())
        self.assertEqual(keys, ['packages', 'schema_version'])
        self.assertEqual(data['schema_version'], '2.0')
        self.assertIsInstance(data['packages'], list)

    def _test_repository_package_order(self, include, data):
        packages = []
        for pdata in data['packages']:
            pname = get_package_name(pdata)
            if pname in packages:
                self.fail("Package names must be unique: " + pname)
            else:
                packages.append(pname)

        # Check package order
        self.assertEqual(packages, sorted(packages, key=str.lower))

    def _test_repository_indents(self, include, contents):
        for i, line in enumerate(contents.splitlines()):
            self.assertRegex(line, r"^\t*\S",
                             "Indent must be tabs in line %d" % i)

    def _test_package(self, include, data):
        for k, v in data.items():
            self.assertIn(k, self.package_key_types_map)
            self.assertIsInstance(v, self.package_key_types_map[k])

            if k in ('details', 'homepage', 'readme', 'issues', 'donate',
                       'buy'):
                self.assertRegex(v, '^https?://')

            # Test for invalid characters (on file systems)
            if k == 'name':
                # Invalid on Windows (and sometimes problematic on UNIX)
                self.assertNotRegex(v, r'[/?<>\\:*|"\x00-\x19]')
                # Invalid on OS X (or more precisely: hidden)
                self.assertFalse(v.startswith('.'))

        if 'details' not in data:
            for key in ('name', 'homepage', 'author', 'releases'):
                self.assertIn(key, data, '%r is required if no "details" URL '
                                          'provided' % key)

    def _test_release(self, package_name, data, main_repo=True):
        # Fail early
        if main_repo:
            self.assertIn('details', data,
                          'A release must have a "details" key if it is in the '
                          'main repository. For custom releases, a custom '
                          'repository.json file must be hosted elsewhere.')
        elif not 'details' in data:
            for req in ('url', 'version', 'date'):
                self.assertIn(req, data,
                              'A release must provide "url", "version" and '
                              '"date" keys if it does not specify "details"')


        for k, v in data.items():
            self.assertIn(k, ('details', 'sublime_text', 'platforms',
                              'version', 'date', 'url'))

            if main_repo:
                self.assertNotIn(k, ('version', 'date', 'url'),
                                 'The version, date and url keys should not be '
                                 'used in the main repository since a pull '
                                 'request would be necessary for every release')
            else:
                if k == 'date':
                    self.assertRegex(v, r"^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d$")

            if k == 'details':
                self.assertRegex(v, '^https?://')

            if k == 'sublime_text':
                self.assertRegex(v, '^(\*|<=?\d{4}|>=?\d{4})$')

            if k == 'platforms':
                self.assertIsInstance(v, (str, list))
                if isinstance(v, str):
                    v = [v]
                for plat in v:
                    self.assertRegex(plat,
                                     r"^\*|(osx|linux|windows)(-x(32|64))?$")

class PackageTests(TestContainer, unittest.TestCase):

    def test_packages(self):

        repository = "packages.json"
        try:
            with _open(repository) as f:
                contents = f.read()
                data = json.loads(contents)
        except Exception as e:
            self.fail("Could not parse %s" % repository)

        # `repository` is for output during tests only
        self._test_repository_indents(repository, contents)
        self._test_repository_keys(repository, data)
        self._test_repository_package_order(repository, data)

        for package in data['packages']:
            self._test_package(repository, package)

            package_name = get_package_name(package)

            if 'releases' in package:
                for release in package['releases']:
                    self._test_release("%s (%s)" % (package_name, repository), release, False)


################################################################################
# Main


if __name__ == '__main__':
    unittest.main()

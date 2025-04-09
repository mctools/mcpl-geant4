
################################################################################
##                                                                            ##
##  This file is part of MCPL (see https://mctools.github.io/mcpl/)           ##
##                                                                            ##
##  Copyright 2015-2025 MCPL developers.                                      ##
##                                                                            ##
##  Licensed under the Apache License, Version 2.0 (the "License");           ##
##  you may not use this file except in compliance with the License.          ##
##  You may obtain a copy of the License at                                   ##
##                                                                            ##
##      http://www.apache.org/licenses/LICENSE-2.0                            ##
##                                                                            ##
##  Unless required by applicable law or agreed to in writing, software       ##
##  distributed under the License is distributed on an "AS IS" BASIS,         ##
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  ##
##  See the License for the specific language governing permissions and       ##
##  limitations under the License.                                            ##
##                                                                            ##
################################################################################

def discard_whitespace( s ):
    return ''.join(s.strip().split())

def extract_bruteforce(f,linebegin,lineend):
    linebegin = discard_whitespace(linebegin)
    lineend = discard_whitespace(lineend)
    for line in f.read_text().splitlines():
        s = discard_whitespace(line)
        if not s.startswith(linebegin):
            continue
        assert s.endswith(lineend)
        return s[len(linebegin):-len(lineend)].strip()
    assert False

def extract_cmake(reporoot):
    f = reporoot.joinpath('src','mcpl_geant4',
                          'cmake','MCPLGeant4ConfigVersion.cmake')
    return extract_bruteforce(f,'set(PACKAGE_VERSION',')')

def main( reporoot ):
    print("Checking versions...")
    versions = [
        ('VERSION','',''),
        ('src/mcpl_geant4/cmake/MCPLGeant4ConfigVersion.cmake',
         'set(PACKAGE_VERSION "','")'),
        ('pyproject.toml','version = "','"'),
        ('src/mcpl_geant4/__init__.py',"__version__ = '","'")
    ]
    actual_version = None
    for frel, linebegin, lineend in versions:
        print(f"Extracting version from {frel}")
        f = reporoot.joinpath(frel)
        if not linebegin and not lineend:
            v = f.read_text().strip()
        else:
            v = extract_bruteforce(f,linebegin,lineend)
        print(f"  .. got {repr(v)}")
        assert v
        if not actual_version:
            actual_version = v
        elif actual_version != v:
            raise SystemExit('ERROR: Version mismatch!')
    print("Checking versions... DONE")


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

def main( reporoot ):
    print(reporoot)
    import subprocess
    import shutil
    print("Checking ruff...")
    ruff = shutil.which('ruff')
    if not ruff:
        raise SystemExit('ERROR: ruff command not available')
    files = sorted(reporoot.rglob('*.py'))
    rv = subprocess.run(['ruff','check'] + [str(f) for f in files] )
    if rv.returncode!=0:
        raise SystemExit(1)
    print("Checking ruff... DONE")

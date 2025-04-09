
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

def parse_args():
    from argparse import ArgumentParser, RawTextHelpFormatter
    import textwrap
    def wrap(t,w=59):
        return textwrap.fill( ' '.join(t.split()), width=w )

    descr = """Developer utils for MCPLGeant4 installation."""
    parser = ArgumentParser( description=wrap(descr,79),
                             formatter_class = RawTextHelpFormatter )
    parser.add_argument('--check', action='store_true',
                        help=wrap("Perform various code checks"))
    args = parser.parse_args()
    nselect = sum( (1 if e else 0)
                   for e in [args.check,] )
    if nselect == 0:
        parser.error('Invalid usage. Run with -h/--help for instructions.')
    if nselect > 1:
        parser.error('Conflicting options')
    return args

def main():
    args = parse_args()
    import pathlib
    reporoot = pathlib.Path(__file__).parent.parent.parent.parent.absolute()
    if args.check:
        from . import check_ruff
        check_ruff.main(reporoot)
        from . import check_version
        check_version.main(reporoot)
    else:
        assert False, "should not happen"

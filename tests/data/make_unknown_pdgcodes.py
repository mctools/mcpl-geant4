#!/usr/bin/env python3


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

"""Writes unknown_pdgcodes.mcpl.gz, the input of the test of particles with PDG
codes unknown to Geant4 (it needs MCPL 3.0.0 or later, to write the file from
Python). The file has 2 neutrons, followed by 105 particles with an unknown
PDG code (more than the 100 which G4MCPLGenerator warns about one by one).
"""

import pathlib

import mcpl


def main():
    out = pathlib.Path( __file__ ).absolute().parent / 'unknown_pdgcodes.mcpl.gz'
    pdgcodes = [ 2112, 2112 ] + [ 1234567 ] * 105
    n = len( pdgcodes )
    with mcpl.MCPLOutFile( str(out) ) as f:
        f.add_particles( pdgcode = pdgcodes,
                         position = [ ( 0.0, 0.0, 30.0 ) ] * n,
                         direction = [ ( 0.0, 0.0, 1.0 ) ] * n,
                         ekin = [ 1.0 ] * n,
                         time = [ 0.0 ] * n,
                         weight = [ 1.0 ] * n )

if __name__ == '__main__':
    main()

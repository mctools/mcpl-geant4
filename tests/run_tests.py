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
################################################################################

"""Tests of G4MCPLWriter and G4MCPLGenerator.

Builds the test application (mcplg4testapp.cc) against the installed
mcpl-geant4, and runs each case of CASES in its own directory. Each case gives
the arguments of the application (or another command, like mcpltool), and what
to expect: the exit code, texts in the output, the files written and their
contents (checked with the mcpl Python module), and the primary particles
generated from input files. Run with --help for the options.
"""

import argparse
import collections
import math
import pathlib
import shlex
import subprocess
import tempfile
import time

DATADIR = pathlib.Path( __file__ ).absolute().parent / 'data'
FIELDS = ( 'x', 'y', 'z', 'ux', 'uy', 'uz', 'ekin', 'time', 'weight',
           'polx', 'poly', 'polz' )

def flight_time( pdgcode, ekin, distance_cm ):
    #The time in ms for a particle (neutron or photon) to travel the distance:
    mass = { 2112: 939.56542194, 22: 0.0 }[pdgcode]
    beta = ( 1.0 if not mass else
             math.sqrt( 1.0 - ( mass / ( mass + ekin ) )**2 ) )
    return distance_cm * 1e-2 / ( beta * 299792458.0 ) * 1e3

#Neutrons of 1 MeV from the gun (at z=-10cm) reach the detector (at z=30cm)
#after 40 cm:
T_N1 = flight_time( 2112, 1.0, 40 )
AT_DETECTOR = { 'x': 0, 'y': 0, 'z': 30, 'ux': 0, 'uy': 0, 'uz': 1 }
STATSUM_COMMENT = ( 'G4MCPLWriter stat:sum values : geant4_nevts is the number'
                    ' of simulated events, initial_geant4_weights is the sum of'
                    ' the weights of their primary particles' )
EXISTS_INTERMEDIATE = ( 'The output file "out.mcpl.gz" can not be written, since'
                        ' "out.mcpl" (which it is compressed from) already exists.' )
DEFAULT_HEADER = { 'version': 3, 'opt_singleprec': True, 'opt_polarisation': False,
                   'opt_userflags': False, 'opt_universalweight': 0.0,
                   'sourcename': 'G4MCPLWriter [G4MCPLWriter]' }

def statsum( nevts, weights ):
    return { 'geant4_nevts': nevts, 'initial_geant4_weights': weights }

def read( name, extra = None ):
    #A generator case reading the file out.mcpl of the case name:
    return { 'input': ( name, 'out.mcpl' ), 'args': { 'mode': 'read', **( extra or {} ) } }

CASES = [

    #G4MCPLWriter, the particles and the header:
    { 'name': 'write_neutrons',
      'args': { 'particles': 'neutron', 'nevts': '10' },
      'files': { 'out.mcpl': { 'nparticles': 10,
                               'pdgcodes': { 2112: 10 },
                               'weights': { 1.0: 10 },
                               'fields': { **AT_DETECTOR, 'ekin': 1, 'time': T_N1 },
                               'header': DEFAULT_HEADER,
                               'statsum': statsum( 10, 10 ),
                               'comments': [ STATSUM_COMMENT ],
                               'userflags': None } } },
    { 'name': 'write_sdname',
      'args': { 'sdname': 'mydetector', 'nevts': '1' },
      'files': { 'out.mcpl': { 'header': { 'sourcename': 'G4MCPLWriter [mydetector]' } } } },
    { 'name': 'write_doubleprec',
      'args': { 'doubleprec': '1', 'energy': '2.5', 'nevts': '3' },
      'files': { 'out.mcpl': { 'header': { 'opt_singleprec': False },
                               'fields': { **AT_DETECTOR, 'ekin': 2.5,
                                           'time': flight_time( 2112, 2.5, 40 ) },
                               'tolerance': 1e-12,
                               #(the neutron mass in Geant4 differs slightly
                               #from the one in flight_time):
                               'field_tolerances': { 'time': 1e-6 } } } },
    { 'name': 'write_polarisation',
      'args': { 'storepol': '1', 'polarisation': '0,0.6,0.8', 'nevts': '3' },
      'files': { 'out.mcpl': { 'header': { 'opt_polarisation': True },
                               'fields': { 'polx': 0, 'poly': 0.6, 'polz': 0.8 } } } },
    { 'name': 'write_polarisation_not_stored',
      'args': { 'polarisation': '0,0.6,0.8', 'nevts': '1' },
      'files': { 'out.mcpl': { 'header': { 'opt_polarisation': False } } } },
    { 'name': 'write_universal_weight',
      'args': { 'uniweight': '2', 'weight': '2', 'nevts': '3' },
      'files': { 'out.mcpl': { 'header': { 'opt_universalweight': 2.0 },
                               'weights': { 2.0: 3 },
                               'statsum': statsum( 3, 6 ) } } },
    { 'name': 'write_comment_and_blob',
      'args': { 'comment': 'Some comment', 'blob': 'mykey:some data', 'nevts': '1' },
      'files': { 'out.mcpl': { 'comments': [ 'Some comment', STATSUM_COMMENT ],
                               'blobs': { 'mykey': b'some data' } } } },
    { 'name': 'write_direction',
      'args': { 'direction': '0,0.6,0.8', 'nevts': '2' },
      'files': { 'out.mcpl': { 'fields': { 'x': 0, 'y': 30, 'z': 30, 'ux': 0,
                                           'uy': 0.6, 'uz': 0.8, 'ekin': 1,
                                           'time': flight_time( 2112, 1.0, 50 ) } } } },
    { 'name': 'write_optical_photons',
      'args': { 'particles': 'opticalphoton', 'energy': '3e-6', 'nevts': '5' },
      'files': { 'out.mcpl': { 'pdgcodes': { 22: 5 },
                               'fields': { **AT_DETECTOR,
                                           'time': flight_time( 22, 3e-6, 40 ) } } } },
    { 'name': 'write_geantinos',
      'args': { 'particles': 'geantino,chargedgeantino', 'nevts': '6' },
      'files': { 'out.mcpl': { 'pdgcodes': { 0: 6 } } } },
    { 'name': 'write_ions',
      'args': { 'particles': 'ion_2_4,ion_82_208', 'nevts': '4' },
      'files': { 'out.mcpl': { 'pdgcodes': { 1000020040: 2, 1000822080: 2 },
                               'fields': AT_DETECTOR } } },
    { 'name': 'write_userflags',
      'args': { 'writer': 'userflags', 'nevts': '3' },
      'files': { 'out.mcpl': { 'header': { 'opt_userflags': True },
                               'userflags': { 1: 3 },
                               'comments': [ 'UserFlagDescription: Track ID' ] } } },
    { 'name': 'write_poststep',
      'args': { 'writer': 'poststep', 'nevts': '4' },
      'files': { 'out.mcpl': { 'nparticles': 4,
                               'fields': { **AT_DETECTOR, 'z': 50,
                                           'time': flight_time( 2112, 1.0, 60 ) } } } },

    #G4MCPLWriter, the statistics:
    { 'name': 'write_vertex_weight',
      'args': { 'weight': '2.5', 'nevts': '4' },
      'files': { 'out.mcpl': { 'weights': { 2.5: 4 }, 'statsum': statsum( 4, 10 ) } } },
    { 'name': 'write_several_primaries',
      'args': { 'nprimaries': '3', 'weight': '0.5', 'nevts': '4' },
      'files': { 'out.mcpl': { 'nparticles': 12, 'weights': { 0.5: 12 },
                               'statsum': statsum( 4, 6 ) } } },
    { 'name': 'write_zero_weight',
      'args': { 'weight': '0', 'nevts': '3' },
      'files': { 'out.mcpl': { 'weights': { 0.0: 3 }, 'statsum': statsum( 3, 0 ) } } },
    { 'name': 'write_no_particles',
      'args': { 'direction': '0,0,-1', 'nevts': '5' },
      'files': { 'out.mcpl': { 'nparticles': 0, 'statsum': statsum( 5, 5 ),
                               'comments': [ STATSUM_COMMENT ] } } },
    { 'name': 'merge_with_mcpltool',
      'cmd': [ 'mcpltool', '--merge', 'out.mcpl', '{write_neutrons}', '{write_vertex_weight}' ],
      'files': { 'out.mcpl': { 'nparticles': 14, 'statsum': statsum( 14, 20 ) } } },

    #G4MCPLWriter, the output files:
    { 'name': 'write_compressed',
      'args': { 'out': 'out.mcpl.gz', 'nevts': '3' },
      'files': { 'out.mcpl.gz': { 'nparticles': 3 } } },
    { 'name': 'write_name_without_extension',
      'args': { 'out': 'myname', 'nevts': '1' },
      'files': { 'myname.mcpl': { 'nparticles': 1 } } },
    { 'name': 'write_name_with_directory',
      'mkdirs': [ 'sub' ],
      'args': { 'out': 'sub/x', 'nevts': '2' },
      'files': { 'sub/x.mcpl': { 'nparticles': 2 } } },
    { 'name': 'write_existing_mcpl',
      'create': [ 'out.mcpl' ],
      'args': { 'nevts': '1' },
      'exitcode': 'fail',
      'output': [ 'The output file "out.mcpl" already exists.' ],
      'files': { 'out.mcpl': 'unchanged' } },
    { 'name': 'write_existing_mcplgz',
      'create': [ 'out.mcpl.gz' ],
      'args': { 'out': 'out.mcpl.gz', 'nevts': '1' },
      'exitcode': 'fail',
      'output': [ 'The output file "out.mcpl.gz" already exists.' ],
      'files': { 'out.mcpl.gz': 'unchanged' } },
    { 'name': 'write_existing_uncompressed',
      'create': [ 'out.mcpl' ],
      'args': { 'out': 'out.mcpl.gz', 'nevts': '1' },
      'exitcode': 'fail',
      'output': [ EXISTS_INTERMEDIATE ],
      'files': { 'out.mcpl': 'unchanged' } },

    #G4MCPLWriter, with physics:
    { 'name': 'write_shower',
      'args': { 'physics': 'QGSP_BERT', 'target': '1', 'particles': 'proton',
                'energy': '10000', 'nevts': '3' },
      'files': { 'out.mcpl': { 'min_nparticles': 10,
                               'min_npdgcodes': 3,
                               'fields': { 'z': 30 },
                               'statsum': statsum( 3, 3 ) } } },

    #G4MCPLGenerator, the particles:
    { 'name': 'read_neutrons', **read( 'write_neutrons' ),
      'primaries': { 'neutron': 10 },
      'primaries_match_input': {} },
    { 'name': 'read_doubleprec', **read( 'write_doubleprec' ),
      'primaries_match_input': { 'tolerance': 1e-12 } },
    { 'name': 'read_polarisation', **read( 'write_polarisation' ),
      'primaries_match_input': {} },
    { 'name': 'read_direction', **read( 'write_direction' ),
      'primaries_match_input': {} },
    { 'name': 'read_weights', **read( 'write_vertex_weight' ),
      'primaries_match_input': {} },
    { 'name': 'read_ions', **read( 'write_ions' ),
      'primaries': { 'alpha': 2, 'Pb208': 2 },
      'primaries_match_input': {} },
    { 'name': 'read_optical_photons', **read( 'write_optical_photons' ),
      'primaries': { 'gamma': 5 } },
    { 'name': 'read_compressed',
      'input': ( 'write_compressed', 'out.mcpl.gz' ),
      'args': { 'mode': 'read' },
      'primaries': { 'neutron': 3 } },
    { 'name': 'read_shower', **read( 'write_shower' ),
      'primaries_match_input': {},
      'output_count': { 'untranslatable pdg code': 0 } },

    #G4MCPLGenerator, derived classes and skipped particles:
    { 'name': 'read_use_particle', **read( 'write_mixed', { 'generator': 'noneutrons',
                                                            'pdgzero': 'geantino' } ),
      'primaries': { 'geantino': 5 } },
    { 'name': 'read_modify_particle', **read( 'write_neutrons', { 'generator': 'modify' } ),
      'primaries_match_input': { 'shift': { 'z': 1, 'time': 1 },
                                 'scale': { 'weight': 2 } } },
    { 'name': 'read_unknown_pdgcodes',
      'input_data': 'unknown_pdgcodes.mcpl.gz',
      'args': { 'mode': 'read' },
      'primaries': { 'neutron': 2 },
      'output_count': {
          'Ignoring particle in input with untranslatable pdg code (1234567)': 100,
          ( 'Limit reached. Suppressing further warnings regarding'
            ' untranslatable pdg codes' ): 1,
          ( 'Ignored a total of 105 particles in input due to untranslatable'
            ' pdg codes' ): 1 } },
    { 'name': 'read_zero_weights', **read( 'write_zero_weight' ),
      'exitcode': 'any',
      'output': [ 'Not a single suitable particle found in input file' ],
      'output_count': { 'Ignoring particle in input with invalid weight.': 3 },
      'primaries': {} },
    { 'name': 'read_no_particles', **read( 'write_no_particles' ),
      'exitcode': 'any',
      'output': [ 'Not a single suitable particle found in input file' ],
      'primaries': {} },

    #G4MCPLGenerator, particles with PDG code 0 (a file with 5 geantinos and 5
    #neutrons):
    { 'name': 'write_mixed',
      'args': { 'particles': 'geantino,neutron', 'nevts': '10' },
      'files': { 'out.mcpl': { 'pdgcodes': { 0: 5, 2112: 5 } } } },
    { 'name': 'read_pdgzero_default', **read( 'write_mixed' ),
      'output': [ 'SETTING ignored=1 geantino=0 chargedgeantino=0' ],
      'output_count': { 'Ignoring particle in input with PDG code 0': 5 },
      'primaries': { 'neutron': 5 } },
    { 'name': 'read_pdgzero_geantino', **read( 'write_mixed', { 'pdgzero': 'geantino' } ),
      'output': [ 'SETTING ignored=0 geantino=1 chargedgeantino=0' ],
      'output_count': { 'Ignoring particle in input with PDG code 0': 0 },
      'primaries': { 'neutron': 5, 'geantino': 5 } },
    { 'name': 'read_pdgzero_chargedgeantino',
      **read( 'write_mixed', { 'pdgzero': 'chargedgeantino' } ),
      'output': [ 'SETTING ignored=0 geantino=0 chargedgeantino=1' ],
      'primaries': { 'neutron': 5, 'chargedgeantino': 5 } },
    { 'name': 'read_pdgzero_ignored_again', **read( 'write_mixed', { 'pdgzero': 'ignored' } ),
      'output': [ 'SETTING ignored=1 geantino=0 chargedgeantino=0' ],
      'primaries': { 'neutron': 5 } },
    { 'name': 'read_pdgzero_set_too_late', **read( 'write_mixed', { 'late': '1' } ),
      'exitcode': 'fail',
      'output': [ 'SetPDGCodeZeroAsGeantino must be called before the first event.' ] },
]

def file_contents( path ):
    import mcpl
    with mcpl.MCPLFile( str(path) ) as f:
        pdg, weights, uf = collections.Counter(), collections.Counter(), collections.Counter()
        particles = []
        for b in f.particle_blocks:
            pdg.update( int(x) for x in b.pdgcode )
            weights.update( float(x) for x in b.weight )
            if f.opt_userflags:
                uf.update( int(x) for x in b.userflags )
            cols = [ b.pdgcode ] + [ getattr( b, k ) for k in FIELDS ]
            for row in zip( *cols ):
                particles.append( { 'pdgcode': int(row[0]),
                                    **{ k: float(v) for k, v in zip( FIELDS, row[1:] ) } } )
        return { 'nparticles': f.nparticles,
                 'pdgcodes': dict(pdg),
                 'weights': dict(weights),
                 'userflags': dict(uf) if f.opt_userflags else None,
                 'statsum': { k: float(v) for k, v in f.stat_sum.items() },
                 'comments': list(f.comments),
                 'blobs': dict(f.blobs),
                 'header': { k: getattr( f, k ) for k in DEFAULT_HEADER },
                 'particles': particles }

def close( a, b, tolerance ):
    #Relative tolerance, or absolute if the expected value b is 0:
    return abs( a - b ) <= tolerance * ( abs(b) if b else 1.0 )

def check_file( path, expect, problems ):
    if not path.is_file():
        problems.append( f'missing output file {path.name}' )
        return
    if expect == 'unchanged':
        if path.stat().st_size != 0:
            problems.append( f'{path.name} was changed' )
        return
    got = file_contents( path )
    for key in ( 'nparticles', 'pdgcodes', 'weights', 'userflags', 'statsum' ):
        if key in expect and got[key] != expect[key]:
            problems.append( f'{path.name}: {key} is {got[key]}, expected {expect[key]}' )
    for k, v in expect.get( 'header', {} ).items():
        if got['header'][k] != v:
            problems.append( f'{path.name}: {k} is {got["header"][k]!r}, expected {v!r}' )
    for k, v in expect.get( 'blobs', {} ).items():
        if got['blobs'].get( k ) != v:
            problems.append( f'{path.name}: blob {k} is {got["blobs"].get(k)!r}, expected {v!r}' )
    for c in expect.get( 'comments', [] ):
        if c not in got['comments']:
            problems.append( f'{path.name}: missing comment "{c}"' )
    tolerance = expect.get( 'tolerance', 1e-6 )
    for k, v in expect.get( 'fields', {} ).items():
        tol = expect.get( 'field_tolerances', {} ).get( k, tolerance )
        bad = [ p[k] for p in got['particles'] if not close( p[k], v, tol ) ]
        if bad:
            problems.append( f'{path.name}: {len(bad)} particles have {k} different'
                             f' from {v} (like {bad[0]})' )
    if got['nparticles'] < expect.get( 'min_nparticles', 0 ):
        problems.append( f'{path.name}: only {got["nparticles"]} particles' )
    if len(got['pdgcodes']) < expect.get( 'min_npdgcodes', 0 ):
        problems.append( f'{path.name}: only PDG codes {got["pdgcodes"]}' )

def parse_primaries( output ):
    res = []
    for line in output.splitlines():
        if line.startswith( 'PRIMARY ' ):
            parts = line.split()
            p = { 'name': parts[1] }
            for kv in parts[2:]:
                k, v = kv.split( '=' )
                p[k] = float(v)
            res.append( p )
    return res

def check_primaries_match( primaries, input_path, spec, problems ):
    #Compares the primary particles with the particles of the input file:
    expected = file_contents( input_path )['particles']
    if len( primaries ) != len( expected ):
        problems.append( f'{len(primaries)} primaries, but {len(expected)} particles in the input' )
        return
    tolerance = spec.get( 'tolerance', 1e-6 )
    for i, ( prim, part ) in enumerate( zip( primaries, expected ) ):
        for k in ( 'pdgcode', ) + FIELDS:
            v = part[k] * spec.get( 'scale', {} ).get( k, 1 ) + spec.get( 'shift', {} ).get( k, 0 )
            if not close( prim[k], v, tolerance ):
                problems.append( f'primary {i}: {k} is {prim[k]}, expected {v}' )
                return

def run_case( case, app, workdir ):
    d = workdir / case['name']
    d.mkdir()
    for sub in case.get( 'mkdirs', [] ):
        ( d / sub ).mkdir()
    for fn in case.get( 'create', [] ):
        ( d / fn ).touch()
    if 'cmd' in case:
        cmd = [ str( workdir / a[1:-1] / 'out.mcpl' ) if a.startswith('{') else a
                for a in case['cmd'] ]
    else:
        args = dict( case['args'] )
        if 'input' in case:
            args['in'] = str( workdir / case['input'][0] / case['input'][1] )
        if 'input_data' in case:
            args['in'] = str( DATADIR / case['input_data'] )
        cmd = [ str(app) ] + [ f'{k}={v}' for k, v in args.items() ]
    t0 = time.time()
    p = subprocess.run( cmd, cwd = d, capture_output = True, text = True, check = False )
    dt = time.time() - t0
    output = p.stdout + p.stderr
    ( d / 'output.log' ).write_text( output )
    problems = []
    exitcode = case.get( 'exitcode', 0 )
    if exitcode == 'fail' and p.returncode == 0:
        problems.append( 'the command did not fail' )
    elif exitcode == 0 and p.returncode != 0:
        problems.append( f'exit code {p.returncode}' )
    for text in case.get( 'output', [] ):
        if text not in output:
            problems.append( f'missing in output: "{text}"' )
    for text, n in case.get( 'output_count', {} ).items():
        if output.count( text ) != n:
            problems.append( f'"{text}" found {output.count(text)} times in output, expected {n}' )
    primaries = parse_primaries( output )
    if 'primaries' in case:
        got = dict( collections.Counter( p['name'] for p in primaries ) )
        if got != case['primaries']:
            problems.append( f'primaries {got}, expected {case["primaries"]}' )
    if 'primaries_match_input' in case:
        check_primaries_match( primaries, workdir / case['input'][0] / case['input'][1],
                               case['primaries_match_input'], problems )
    for fn, expect in case.get( 'files', {} ).items():
        check_file( d / fn, expect, problems )
    return problems, dt, ' '.join( shlex.quote(c) for c in cmd )

def ordered_cases( names ):
    #The selected cases, with the cases they need input from, each after its
    #inputs:
    byname = { c['name']: c for c in CASES }
    def inputs( c ):
        res = [ c['input'][0] ] if 'input' in c else []
        return res + [ a[1:-1] for a in c.get( 'cmd', [] ) if a.startswith('{') ]
    res, done = [], set()
    def add( c ):
        if c['name'] in done:
            return
        for n in inputs( c ):
            add( byname[n] )
        done.add( c['name'] )
        res.append( c )
    for c in CASES:
        if not names or c['name'] in names:
            add( c )
    return res

def main():
    parser = argparse.ArgumentParser( description = __doc__.split('\n\n')[0] )
    parser.add_argument( '--cmake-arg', action = 'append', default = [],
                         help = 'extra argument for the CMake configuration (repeatable)' )
    parser.add_argument( '--keep', metavar = 'DIR',
                         help = 'work in DIR (which must not exist) and keep it' )
    parser.add_argument( 'names', nargs = '*', help = 'run only these cases' )
    a = parser.parse_args()
    unknown = set( a.names ) - { c['name'] for c in CASES }
    if unknown:
        parser.error( f'unknown cases: {", ".join(sorted(unknown))}' )
    cases = ordered_cases( a.names )
    with tempfile.TemporaryDirectory() as tmpdir:
        top = pathlib.Path( a.keep ).absolute() if a.keep else pathlib.Path( tmpdir )
        if a.keep:
            top.mkdir()
        srcdir = pathlib.Path( __file__ ).absolute().parent
        bld = top / 'build'
        t0 = time.time()
        for cmd in ( [ 'cmake', '-S', str(srcdir), '-B', str(bld),
                       '-DCMAKE_BUILD_TYPE=Release' ] + a.cmake_arg,
                     [ 'cmake', '--build', str(bld), '--parallel' ] ):
            if subprocess.run( cmd, check = False ).returncode != 0:
                raise SystemExit( 'ERROR: failed to build the test application' )
        print( f'Built the test application in {time.time()-t0:.1f} s' )
        app = bld / 'mcplg4testapp'
        workdir = top / 'cases'
        workdir.mkdir()
        nfailed = 0
        t0 = time.time()
        for case in cases:
            problems, dt, cmd = run_case( case, app, workdir )
            print( f'{"FAIL" if problems else "ok  "} {case["name"]} ({dt:.1f} s)' )
            for pr in problems:
                print( f'       {pr}' )
            if problems:
                print( f'       command: {cmd}' )
                print( f'       output: {workdir / case["name"] / "output.log"}' )
                nfailed += 1
        print( f'{len(cases)-nfailed} of {len(cases)} cases passed'
               f' ({time.time()-t0:.1f} s)' )
        if nfailed:
            raise SystemExit( 1 )

if __name__ == '__main__':
    main()

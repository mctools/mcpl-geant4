
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

#Builds the test application used by run_tests.py.

cmake_minimum_required(VERSION 3.16...3.31)

project( MCPLGeant4Tests LANGUAGES CXX )

if( NOT DEFINED MCPLGeant4_DIR )
  execute_process(
    COMMAND mcpl-geant4 --cmakedir
    OUTPUT_VARIABLE MCPLGeant4_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
endif()
find_package( Geant4 11.1.0 REQUIRED )
find_package( MCPLGeant4 0.1.0 REQUIRED )

add_executable( mcplg4testapp mcplg4testapp.cc )
target_link_libraries( mcplg4testapp MCPLGeant4::MCPLGeant4 ${Geant4_LIBRARIES} )
if ( NOT MSVC )
  target_compile_options( mcplg4testapp PRIVATE -Wall -Wextra )
  target_compile_options( MCPLGeant4 PRIVATE -Wall -Wextra )
endif()

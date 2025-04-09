
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

cmake_minimum_required(VERSION 3.16...3.31)

project( MyGeant4Project VERSION 0.0.1 LANGUAGES CXX )

#First we must find both Geant4 and MCPLGeant4. We do so via find_package
#statements, but in order to support pip installed mcpl-geant4, we ask the
#mcpl-geant4 command for where to find the MCPLGeant4 configuration files.

if( NOT DEFINED MCPLGeant4_DIR )
  #Be sure to pick up location when MCPLGeant4 was installed via "pip
  #install mcpl-geant4".
  execute_process(
    COMMAND mcpl-geant4 --cmakedir
    OUTPUT_VARIABLE MCPLGeant4_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
endif()
find_package( Geant4 11.1.0 REQUIRED )
find_package( MCPLGeant4 0.0.1 REQUIRED )

#Now we add our own code, in this case an executable:
add_executable( "myapp" "example.cc" )

#Our executable should link against both NCrystalGeant4 and Geant4:
target_link_libraries(
  "myapp"
  MCPLGeant4::MCPLGeant4
  ${Geant4_LIBRARIES}
)

install(TARGETS "myapp" RUNTIME DESTINATION bin)

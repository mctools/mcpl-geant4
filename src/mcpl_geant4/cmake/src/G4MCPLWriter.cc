
////////////////////////////////////////////////////////////////////////////////
//                                                                            //
//  This file is part of MCPL (see https://mctools.github.io/mcpl/)           //
//                                                                            //
//  Copyright 2015-2025 MCPL developers.                                      //
//                                                                            //
//  Licensed under the Apache License, Version 2.0 (the "License");           //
//  you may not use this file except in compliance with the License.          //
//  You may obtain a copy of the License at                                   //
//                                                                            //
//      http://www.apache.org/licenses/LICENSE-2.0                            //
//                                                                            //
//  Unless required by applicable law or agreed to in writing, software       //
//  distributed under the License is distributed on an "AS IS" BASIS,         //
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  //
//  See the License for the specific language governing permissions and       //
//  limitations under the License.                                            //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

#include "MCPLGeant4/G4MCPLWriter.hh"
#include "G4Track.hh"
#include "G4Event.hh"
#include "G4EventManager.hh"
#include "G4PrimaryVertex.hh"
#include <cstdlib>
#include <filesystem>
#include <sstream>

namespace {
  //The output file names, from mcpl_name_helper:
  std::string G4MCPLWriter_name( const std::string& filename, char mode )
  {
    char * c = mcpl_name_helper( filename.c_str(), mode );
    std::string res( c );
    std::free( c );
    return res;
  }
  bool G4MCPLWriter_pathexists( const std::string& path )
  {
    std::error_code ec;
    return std::filesystem::exists( std::filesystem::symlink_status( path, ec ) );
  }
}

G4MCPLWriter::G4MCPLWriter( const G4String& outputFile,
                            const G4String& name )
  : G4VSensitiveDetector(name),
    m_store_polarisation(false),
    m_store_userflags(false)
{
  //Names ending in .mcpl.gz give compressed files (written uncompressed and
  //compressed when closed), other names give .mcpl files:
  const std::string given( outputFile );
  const std::string gzsuffix( ".mcpl.gz" );
  m_gzip = ( given.size() >= gzsuffix.size()
             && given.compare( given.size() - gzsuffix.size(), gzsuffix.size(),
                               gzsuffix ) == 0 );
  const std::string fn = G4MCPLWriter_name( given, 'M' );
  const std::string fngz = G4MCPLWriter_name( given, 'G' );
  const std::string bn = G4MCPLWriter_name( given, 'm' );
  const std::string bngz = G4MCPLWriter_name( given, 'g' );
  //Refuse existing files right away, rather than when the file is closed:
  std::ostringstream problem;
  if ( m_gzip && G4MCPLWriter_pathexists( fngz ) )
    problem << "The output file \"" << bngz << "\" already exists.";
  else if ( m_gzip && G4MCPLWriter_pathexists( fn ) )
    problem << "The output file \"" << bngz << "\" can not be written, since \""
            << bn << "\" (which it is compressed from) already exists.";
  else if ( !m_gzip && G4MCPLWriter_pathexists( fn ) )
    problem << "The output file \"" << bn << "\" already exists.";
  if ( !problem.str().empty() )
    G4Exception("G4MCPLWriter::G4MCPLWriter()", "G4MCPLWriter02",
                FatalException, problem.str().c_str());
  m_f = mcpl_create_outfile( fn.c_str() );
  m_p = mcpl_get_empty_particle( m_f );

  {
    std::stringstream tmp;
    tmp << "G4MCPLWriter [" << name <<"]";
    mcpl_hdr_set_srcname( m_f, tmp.str().c_str() );
  }

  //Statistics of the simulated events, as stat:sum values (they are added up
  //when files are merged). Space for them is reserved here, and the values are
  //set when the file is closed:
  mcpl_hdr_add_comment( m_f, "G4MCPLWriter stat:sum values : geant4_nevts is the"
                        " number of simulated events, initial_geant4_weights is"
                        " the sum of the weights of their primary particles" );
  mcpl_hdr_add_stat_sum( m_f, "geant4_nevts", -1.0 );
  mcpl_hdr_add_stat_sum( m_f, "initial_geant4_weights", -1.0 );
}

G4MCPLWriter::~G4MCPLWriter()
{
  mcpl_hdr_add_stat_sum( m_f, "geant4_nevts", (double)m_nevts );
  mcpl_hdr_add_stat_sum( m_f, "initial_geant4_weights", m_sumweights );
  if ( m_gzip )
    mcpl_closeandgzip_outfile(m_f);
  else
    mcpl_close_outfile(m_f);
}

G4bool G4MCPLWriter::ProcessHits(G4Step * step,G4TouchableHistory*)
{
  //Only consider particle steps originating at the boundary
  //of the monitored volume:
  if ( step->GetPreStepPoint()->GetStepStatus() != fGeomBoundary )
    return false;

  //Store the state at the beginning of the step, but avoid
  //particles taking their very first step (this would double-
  //count secondary particles created at the volume edge):
  if ( step->GetTrack()->GetCurrentStepNumber() > 1 )
    StorePreStep(step);

  //Tell Geant4 to stop further tracking of the particle:
  Kill(step);
  return true;
}

void G4MCPLWriter::AddComment( const G4String& comment )
{
  mcpl_hdr_add_comment( m_f, comment.c_str() );
}

void G4MCPLWriter::AddData( const G4String& dataKey, size_t dataLength, const char* data )
{
  mcpl_hdr_add_data( m_f, dataKey.c_str(), dataLength, data );
}

void G4MCPLWriter::EnableDoublePrecision()
{
  mcpl_enable_doubleprec(m_f);
}

void G4MCPLWriter::EnablePolarisation()
{
  mcpl_enable_polarisation(m_f);
  m_store_polarisation = true;
}

void G4MCPLWriter::EnableUniversalWeight(G4double w)
{
  mcpl_enable_universal_weight(m_f,w);
}

namespace {
  //The weight of the track of a primary particle is the product of the weights
  //of the vertex and the particle (also for pre-assigned daughters):
  double G4MCPLWriter_sumweights( const G4PrimaryParticle* pp, double vtxweight )
  {
    double w = vtxweight * pp->GetWeight();
    for ( const G4PrimaryParticle* d = pp->GetDaughter(); d; d = d->GetNext() )
      w += G4MCPLWriter_sumweights( d, vtxweight );
    return w;
  }
}

void G4MCPLWriter::Initialize( G4HCofThisEvent* )
{
  //Called at the start of each event, after its primary particles are
  //generated:
  const G4Event * evt = G4EventManager::GetEventManager()->GetConstCurrentEvent();
  if ( !evt )
    return;
  ++m_nevts;
  for ( G4int i = 0; i < evt->GetNumberOfPrimaryVertex(); ++i ) {
    const G4PrimaryVertex * vtx = evt->GetPrimaryVertex(i);
    for ( const G4PrimaryParticle* pp = vtx->GetPrimary(); pp; pp = pp->GetNext() )
      m_sumweights += G4MCPLWriter_sumweights( pp, vtx->GetWeight() );
  }
}

void G4MCPLWriter::Store( const G4Step * step, const G4StepPoint* pt )
{
  if ( !m_userflags_decided ) {
    //Decided here rather than in the constructor, where the virtual
    //UserFlagsDescription of derived classes can not be called (the header is
    //written with the first particle, so it can still be changed):
    m_userflags_decided = true;
    G4String ufdescr = UserFlagsDescription();
    if (!ufdescr.empty()) {
      std::stringstream tmp;
      tmp << "UserFlagDescription: "<<ufdescr;
      mcpl_hdr_add_comment( m_f, tmp.str().c_str() );
      mcpl_enable_userflags( m_f );
      m_store_userflags = true;
    }
  }
  G4Track * trk = step->GetTrack();
  const G4DynamicParticle * dynpar = trk->GetDynamicParticle();
  m_p->pdgcode = dynpar->GetPDGcode();
  if ( m_p->pdgcode == -22 || ( !m_p->pdgcode && dynpar->GetParticleDefinition()->GetParticleName()=="opticalphoton" ) ) {
    m_p->pdgcode=22;//store optical photons as regular photons (Geant4 10.6 and later encode them as -22)
  }

  m_p->time = pt->GetGlobalTime() / CLHEP::millisecond;
  m_p->weight = pt->GetWeight();
  m_p->ekin = pt->GetKineticEnergy();//already in MeV
  const G4ThreeVector& pos = pt->GetPosition();
  const G4ThreeVector& dir = pt->GetMomentumDirection();
  const G4double tocm(1.0/CLHEP::cm);
  m_p->position[0] = pos.x() * tocm;
  m_p->position[1] = pos.y() * tocm;
  m_p->position[2] = pos.z() * tocm;
  m_p->direction[0] = dir.x();
  m_p->direction[1] = dir.y();
  m_p->direction[2] = dir.z();
  G4double dm2 = dir.mag2();
  if (fabs(dm2-1.0)>1.0e-12) {
    if (!dm2) {
      if (m_p->ekin) {
        //inconsistent
        G4Exception("G4MCPLGenerator::GeneratePrimaries()", "G4MCPLWriter01",
                    JustWarning, "Captured particle has no momentum-direction but eKin>0. Choosing momdir (0,0,1).");
      }
      //arguably consistent if ekin=0, but we should in any case only put unit
      //directional vectors in mcpl:
      m_p->direction[0] = m_p->direction[1] = 0.0;
      m_p->direction[2] = 1.0;
    } else {
      //fix normalisation:
      dm2 = 1.0/sqrt(dm2);
      m_p->direction[0] *= dm2;
      m_p->direction[1] *= dm2;
      m_p->direction[2] *= dm2;
    }
  }

  if (m_store_polarisation) {
    const G4ThreeVector& pol = pt->GetPolarization();
    m_p->polarisation[0] = pol.x();
    m_p->polarisation[1] = pol.y();
    m_p->polarisation[2] = pol.z();
  }

  if (m_store_userflags) {
    m_p->userflags = UserFlags(step);
  }

  mcpl_add_particle(m_f,m_p);

}

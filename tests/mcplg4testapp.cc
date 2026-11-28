
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

//Test application for the G4MCPLWriter and G4MCPLGenerator classes, used by
//run_tests.py. All settings are given as key=value arguments, see the Settings
//class below.

#include "MCPLGeant4/G4MCPLGenerator.hh"
#include "MCPLGeant4/G4MCPLWriter.hh"
#include "G4BaryonConstructor.hh"
#include "G4BosonConstructor.hh"
#include "G4Box.hh"
#include "G4Event.hh"
#include "G4IonConstructor.hh"
#include "G4IonTable.hh"
#include "G4LeptonConstructor.hh"
#include "G4MesonConstructor.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PhysListFactory.hh"
#include "G4PrimaryVertex.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4ShortLivedConstructor.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserEventAction.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include <iomanip>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

  struct Settings {
    std::map<std::string,std::string> values = {
      { "mode", "write" },          //write or read
      { "physics", "transport" },   //transport (no interactions) or a
                                    //reference physics list like QGSP_BERT
      { "target", "0" },            //1: 20cm of lead before the detector
      //For mode=write (gun at z=-10cm, detector at z=30..50cm):
      { "out", "out" },             //name of the output file
      { "writer", "default" },      //default, userflags (stores the track ID),
                                    //or poststep (stores the post-step points
                                    //and does not kill the particles)
      { "sdname", "" },             //name of the sensitive detector
      { "particles", "neutron" },   //comma-separated, used in turn per event
                                    //(ions as ion_Z_A)
      { "nprimaries", "1" },        //primary particles per event
      { "energy", "1" },            //MeV
      { "direction", "0,0,1" },
      { "polarisation", "0,0,0" },
      { "weight", "1" },            //weight of the primary vertex
      { "nevts", "10" },
      { "doubleprec", "0" },        //1: EnableDoublePrecision
      { "storepol", "0" },          //1: EnablePolarisation
      { "uniweight", "0" },         //non-zero: EnableUniversalWeight
      { "comment", "" },            //AddComment
      { "blob", "" },               //AddData, as key:value
      //For mode=read:
      { "in", "" },                 //name of the input file
      { "generator", "default" },   //default, noneutrons (UseParticle skips
                                    //neutrons), or modify (ModifyParticle
                                    //shifts z by 1cm and time by 1ms, and
                                    //doubles the weights)
      { "pdgzero", "default" },     //default, geantino, chargedgeantino, or
                                    //ignored (after chargedgeantino)
      { "late", "0" },              //1: call SetPDGCodeZeroAsGeantino after the run
    };
    Settings( int argc, char** argv )
    {
      for ( int i = 1; i < argc; ++i ) {
        std::string a( argv[i] );
        auto eq = a.find('=');
        if ( eq == std::string::npos || !values.count( a.substr(0,eq) ) )
          throw std::runtime_error( "invalid argument: " + a );
        values[a.substr(0,eq)] = a.substr(eq+1);
      }
    }
    const std::string& str( const std::string& k ) const { return values.at(k); }
    double dbl( const std::string& k ) const { return std::stod( values.at(k) ); }
    bool flag( const std::string& k ) const { return values.at(k) == "1"; }
    std::vector<std::string> list( const std::string& k, char sep = ',' ) const
    {
      std::vector<std::string> res;
      std::stringstream ss( values.at(k) );
      for ( std::string e; std::getline( ss, e, sep ); )
        res.push_back( e );
      return res;
    }
    G4ThreeVector vec( const std::string& k ) const
    {
      auto v = list( k );
      if ( v.size() != 3 )
        throw std::runtime_error( "invalid vector: " + values.at(k) );
      return G4ThreeVector( std::stod(v[0]), std::stod(v[1]), std::stod(v[2]) );
    }
  };

  class TransportOnlyPhysics : public G4VUserPhysicsList {
  public:
    void ConstructParticle() override
    {
      G4BosonConstructor::ConstructParticle();
      G4LeptonConstructor::ConstructParticle();
      G4MesonConstructor::ConstructParticle();
      G4BaryonConstructor::ConstructParticle();
      G4IonConstructor::ConstructParticle();
      G4ShortLivedConstructor::ConstructParticle();
    }
    void ConstructProcess() override { AddTransportation(); }
  };

  class UserFlagsWriter : public G4MCPLWriter {
  public:
    using G4MCPLWriter::G4MCPLWriter;
    G4String UserFlagsDescription() const override { return "Track ID"; }
    uint32_t UserFlags( const G4Step* step ) const override
    {
      return (uint32_t)step->GetTrack()->GetTrackID();
    }
  };

  class PostStepWriter : public G4MCPLWriter {
  public:
    using G4MCPLWriter::G4MCPLWriter;
    G4bool ProcessHits( G4Step* step, G4TouchableHistory* ) override
    {
      StorePostStep( step );
      return true;
    }
  };

  //Vacuum world, with a sensitive detector at z = 30..50cm and optionally a
  //lead target at z = 0..20cm:
  class Geometry : public G4VUserDetectorConstruction {
  public:
    Geometry( const Settings& s ) : m_s(s) {}
    G4VPhysicalVolume* Construct() override
    {
      auto nist = G4NistManager::Instance();
      auto vacuum = nist->FindOrBuildMaterial("G4_Galactic");
      auto lead = nist->FindOrBuildMaterial("G4_Pb");
      auto world = new G4LogicalVolume( new G4Box("World",1*m,1*m,1*m), vacuum, "World" );
      auto world_phys = new G4PVPlacement( nullptr, G4ThreeVector(), world, "World", nullptr, false, 0 );
      if ( m_s.flag("target") ) {
        auto target = new G4LogicalVolume( new G4Box("Target",1*m,1*m,10*cm), lead, "Target" );
        new G4PVPlacement( nullptr, G4ThreeVector(0,0,10*cm), target, "Target", world, false, 0 );
      }
      m_detector = new G4LogicalVolume( new G4Box("Detector",1*m,1*m,10*cm), vacuum, "Detector" );
      new G4PVPlacement( nullptr, G4ThreeVector(0,0,40*cm), m_detector, "Detector", world, false, 0 );
      return world_phys;
    }
    void ConstructSDandField() override
    {
      if ( m_s.str("mode") != "write" )
        return;
      const std::string& out = m_s.str("out");
      const std::string& wr = m_s.str("writer");
      const std::string sdname = ( m_s.str("sdname").empty() ? "G4MCPLWriter" : m_s.str("sdname") );
      G4MCPLWriter * w = nullptr;
      if ( wr == "default" )
        w = new G4MCPLWriter( out, sdname );
      else if ( wr == "userflags" )
        w = new UserFlagsWriter( out, sdname );
      else if ( wr == "poststep" )
        w = new PostStepWriter( out, sdname );
      else
        throw std::runtime_error( "invalid writer: " + wr );
      if ( m_s.flag("doubleprec") )
        w->EnableDoublePrecision();
      if ( m_s.flag("storepol") )
        w->EnablePolarisation();
      if ( m_s.dbl("uniweight") != 0.0 )
        w->EnableUniversalWeight( m_s.dbl("uniweight") );
      if ( !m_s.str("comment").empty() )
        w->AddComment( m_s.str("comment") );
      if ( !m_s.str("blob").empty() ) {
        const std::string& b = m_s.str("blob");
        auto colon = b.find(':');
        const std::string data = b.substr( colon + 1 );
        w->AddData( b.substr( 0, colon ), data.size(), data.c_str() );
      }
      G4SDManager::GetSDMpointer()->AddNewDetector( w );
      m_detector->SetSensitiveDetector( w );
    }
  private:
    const Settings& m_s;
    G4LogicalVolume * m_detector = nullptr;
  };

  G4ParticleDefinition * findParticle( const std::string& name )
  {
    if ( name.rfind( "ion_", 0 ) == 0 ) {
      std::stringstream ss( name.substr(4) );
      std::string z, a;
      std::getline( ss, z, '_' );
      std::getline( ss, a, '_' );
      return G4IonTable::GetIonTable()->GetIon( std::stoi(z), std::stoi(a), 0.0 );
    }
    auto pd = G4ParticleTable::GetParticleTable()->FindParticle( name );
    if ( !pd )
      throw std::runtime_error( "unknown particle: " + name );
    return pd;
  }

  class Gun : public G4VUserPrimaryGeneratorAction {
  public:
    Gun( const Settings& s )
      : m_gun( (G4int)s.dbl("nprimaries") ), m_names( s.list("particles") ),
        m_weight( s.dbl("weight") )
    {
      m_gun.SetParticleEnergy( s.dbl("energy") * MeV );
      m_gun.SetParticlePosition( G4ThreeVector( 0, 0, -10*cm ) );
      m_gun.SetParticleMomentumDirection( s.vec("direction") );
      m_pol = s.vec("polarisation");
    }
    void GeneratePrimaries( G4Event* evt ) override
    {
      m_gun.SetParticleDefinition( findParticle( m_names.at( m_ievt++ % m_names.size() ) ) );
      m_gun.SetParticlePolarization( m_pol );
      m_gun.GeneratePrimaryVertex( evt );
      if ( m_weight != 1.0 )
        evt->GetPrimaryVertex(0)->SetWeight( m_weight );
    }
  private:
    G4ParticleGun m_gun;
    std::vector<std::string> m_names;
    double m_weight;
    G4ThreeVector m_pol;
    std::size_t m_ievt = 0;
  };

  class NoNeutronsGenerator : public G4MCPLGenerator {
  public:
    using G4MCPLGenerator::G4MCPLGenerator;
  protected:
    bool UseParticle( const mcpl_particle_t* p ) const override { return p->pdgcode != 2112; }
  };

  class ModifyingGenerator : public G4MCPLGenerator {
  public:
    using G4MCPLGenerator::G4MCPLGenerator;
  protected:
    void ModifyParticle( G4ThreeVector& pos, G4ThreeVector&, G4ThreeVector&,
                         G4double& time, G4double& weight ) const override
    {
      pos += G4ThreeVector( 0, 0, 1*cm );
      time += 1*ms;
      weight *= 2.0;
    }
  };

  //Prints the primary particles of each event, for checks of G4MCPLGenerator
  //(in the units of MCPL files):
  class PrintPrimaries : public G4UserEventAction {
  public:
    void BeginOfEventAction( const G4Event* evt ) override
    {
      for ( G4int i = 0; i < evt->GetNumberOfPrimaryVertex(); ++i ) {
        const G4PrimaryVertex * vtx = evt->GetPrimaryVertex(i);
        for ( auto pp = vtx->GetPrimary(); pp; pp = pp->GetNext() ) {
          const G4ThreeVector dir = pp->GetMomentumDirection();
          const G4ThreeVector pol = pp->GetPolarization();
          G4cout << std::setprecision(17)
                 << "PRIMARY " << pp->GetParticleDefinition()->GetParticleName()
                 << " pdgcode=" << pp->GetPDGcode()
                 << " x=" << vtx->GetX0()/cm << " y=" << vtx->GetY0()/cm
                 << " z=" << vtx->GetZ0()/cm
                 << " ux=" << dir.x() << " uy=" << dir.y() << " uz=" << dir.z()
                 << " ekin=" << pp->GetKineticEnergy()/MeV
                 << " time=" << vtx->GetT0()/ms
                 << " weight=" << vtx->GetWeight() * pp->GetWeight()
                 << " polx=" << pol.x() << " poly=" << pol.y() << " polz=" << pol.z()
                 << G4endl;
        }
      }
    }
  };

}

int main( int argc, char** argv )
{
  const Settings s( argc, argv );
  CLHEP::HepRandom::setTheSeed( 123456 );
  G4RunManager rm;
  rm.SetUserInitialization( new Geometry( s ) );
  if ( s.str("physics") == "transport" )
    rm.SetUserInitialization( new TransportOnlyPhysics );
  else
    rm.SetUserInitialization( G4PhysListFactory().GetReferencePhysList( s.str("physics") ) );

  if ( s.str("mode") == "write" ) {
    rm.Initialize();
    rm.SetUserAction( new Gun( s ) );
    rm.BeamOn( (G4int)s.dbl("nevts") );
    return 0;
  }
  if ( s.str("mode") != "read" )
    throw std::runtime_error( "invalid mode: " + s.str("mode") );

  G4MCPLGenerator * gen = nullptr;
  if ( s.str("generator") == "default" )
    gen = new G4MCPLGenerator( s.str("in") );
  else if ( s.str("generator") == "noneutrons" )
    gen = new NoNeutronsGenerator( s.str("in") );
  else if ( s.str("generator") == "modify" )
    gen = new ModifyingGenerator( s.str("in") );
  else
    throw std::runtime_error( "invalid generator: " + s.str("generator") );
  const std::string& pdgzero = s.str("pdgzero");
  if ( pdgzero == "geantino" )
    gen->SetPDGCodeZeroAsGeantino();
  else if ( pdgzero == "chargedgeantino" || pdgzero == "ignored" )
    gen->SetPDGCodeZeroAsChargedGeantino();
  if ( pdgzero == "ignored" )
    gen->SetPDGCodeZeroIgnored();
  G4cout << "SETTING ignored=" << gen->IsPDGCodeZeroIgnored()
         << " geantino=" << gen->IsPDGCodeZeroAsGeantino()
         << " chargedgeantino=" << gen->IsPDGCodeZeroAsChargedGeantino() << G4endl;
  rm.SetUserAction( gen );
  rm.SetUserAction( new PrintPrimaries );
  rm.Initialize();
  rm.BeamOn( std::numeric_limits<G4int>::max() );
  if ( s.flag("late") )
    gen->SetPDGCodeZeroAsGeantino();
  return 0;
}

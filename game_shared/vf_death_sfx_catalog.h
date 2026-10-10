// Generated offline by vector-fields/build_death_sounds.py.
#ifndef VF_DEATH_SFX_CATALOG_H
#define VF_DEATH_SFX_CATALOG_H
namespace vfds {
struct Profile {const char* id;const char* death;const char* dismemberment;};
static const Profile Profiles[]={
{"standard",0,"vf_death_sfx/dismemberment_standard.wav"},
{"hydro","vf_death_sfx/death_hydro.wav","vf_death_sfx/dismemberment_hydro.wav"},
{"electro","vf_death_sfx/death_electro.wav","vf_death_sfx/dismemberment_electro.wav"},
{"cryo","vf_death_sfx/death_cryo.wav","vf_death_sfx/dismemberment_cryo.wav"},
{"thermal","vf_death_sfx/death_thermal.wav","vf_death_sfx/dismemberment_thermal.wav"},
{"toxic","vf_death_sfx/death_toxic.wav","vf_death_sfx/dismemberment_toxic.wav"},
{"corrosion","vf_death_sfx/death_corrosion.wav","vf_death_sfx/dismemberment_corrosion.wav"},
{"sonic","vf_death_sfx/death_sonic.wav","vf_death_sfx/dismemberment_sonic.wav"},
{"kinetic","vf_death_sfx/death_kinetic.wav","vf_death_sfx/dismemberment_kinetic.wav"},
{"arc_chain","vf_death_sfx/death_arc_chain.wav","vf_death_sfx/dismemberment_arc_chain.wav"},
{"superconduction","vf_death_sfx/death_superconduction.wav","vf_death_sfx/dismemberment_superconduction.wav"},
{"shatter","vf_death_sfx/death_shatter.wav","vf_death_sfx/dismemberment_shatter.wav"},
{"resonant_impact","vf_death_sfx/death_resonant_impact.wav","vf_death_sfx/dismemberment_resonant_impact.wav"},
{"cavitation","vf_death_sfx/death_cavitation.wav","vf_death_sfx/dismemberment_cavitation.wav"},
{"caustic_contagion","vf_death_sfx/death_caustic_contagion.wav","vf_death_sfx/dismemberment_caustic_contagion.wav"},
{"toxic_ignition","vf_death_sfx/death_toxic_ignition.wav","vf_death_sfx/dismemberment_toxic_ignition.wav"},
{"steam_veil","vf_death_sfx/death_steam_veil.wav","vf_death_sfx/dismemberment_steam_veil.wav"},
};
enum {ProfileCount=sizeof(Profiles)/sizeof(Profiles[0])};
inline const Profile& For(int effect){return Profiles[effect>=0&&effect<ProfileCount-1?effect+1:0];}
}
#endif

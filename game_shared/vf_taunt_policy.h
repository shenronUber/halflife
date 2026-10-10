#ifndef VF_TAUNT_POLICY_H
#define VF_TAUNT_POLICY_H
namespace vft {
struct Memory {int source;unsigned int life;float until;};
inline void Reset(Memory& m){m.source=0;m.life=0;m.until=0;}
inline bool Within(float x,float y,float z,float radius){return radius>0&&x*x+y*y+z*z<=radius*radius;}
inline bool Chance(float probability,float roll){return probability>=1||(probability>0&&roll<probability);}
inline void Hear(Memory& m,int source,unsigned int life,float now,float duration,float window){m.source=source;m.life=life;m.until=now+duration+window;}
inline bool Reply(const Memory& m,float now,int source,unsigned int life,bool alive,bool audible){return m.source>0&&now<m.until&&m.source==source&&m.life==life&&alive&&audible;}
}
#endif

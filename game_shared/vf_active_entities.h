/* Dense active IDs, with O(1) membership/removal and no allocation. */
#ifndef VF_ACTIVE_ENTITIES_H
#define VF_ACTIVE_ENTITIES_H
namespace vf {
template<int Capacity> struct ActiveEntities {
 int ids[Capacity],positions[Capacity],count;
 ActiveEntities(){Reset();}
 void Reset(){count=0;for(int i=0;i<Capacity;++i)positions[i]=-1;}
 bool Add(int id){if(id<=0||id>=Capacity)return false;if(positions[id]>=0)return true;
  positions[id]=count;ids[count++]=id;return true;}
 void Remove(int id){if(id<=0||id>=Capacity||positions[id]<0)return;int at=positions[id];
  int last=ids[--count];ids[at]=last;positions[last]=at;positions[id]=-1;}
};
}
#endif

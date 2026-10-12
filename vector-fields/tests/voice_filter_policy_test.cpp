#include "../../game_shared/vf_headgear_feedback.h"
#include "../../game_shared/vf_headgear_audio_catalog.h"
#include "../../game_shared/vf_voice_catalog.h"
#include "../../game_shared/vf_death_catalog.h"
#include <stdio.h>
#include <string.h>
static int failures;
static void Check(bool value,const char* label){if(!value){++failures;printf("FAIL %s\n",label);}}
int main(){
 int expected=0;
 for(int i=0;i<vfv::ClipCount;++i){const vfv::Clip& c=vfv::Clips[i];const char* masked=vfha::Mask(c.path);
  if(c.event==vfv::E_death)Check(!strcmp(masked,c.path),"legacy spoken deaths have no filtered derivative");
  else{++expected;Check(strcmp(masked,c.path)!=0,"every dialogue variant has a filtered recording");
   Check(strlen(masked)<64&&!strncmp(masked,"vf_muffle/",10),"native sound path fits the protocol");}
 }
 Check(vfha::MuffledCount==expected,"filtered bank contains dialogue only");
 for(int i=0;i<vfha::ClipCount;++i)Check(!strcmp(vfha::Mask(vfha::Clips[i].path),vfha::Clips[i].path),"all activation announcements stay normal");
 for(int i=0;i<vfd::ClipCount;++i)Check(!strcmp(vfha::Mask(vfd::Clips[i].path),vfd::Clips[i].path),"all contextual death cries stay original");
 for(int type=1;type<=vf::HeadgearTypes;++type){bool bulky=type==1||type==2||type==5;
  Check(!vf::HeadgearMuffled(type,vf::HeadgearCover(type,1,2,false)),"raised gear leaves speech clear");
  Check(vf::HeadgearMuffled(type,vf::HeadgearCover(type,0,2,false))==bulky,"only closed obstructive gear filters dialogue");
  Check(!vf::HeadgearMuffled(type,vf::HeadgearCover(type,0,0,true)),"lowering begins with an uncovered face");
 }
 printf("%s voice filtering: %d dialogue variants, %d normal announcements, %d original death cries\n",failures?"FAIL":"PASS",expected,vfha::ClipCount,vfd::ClipCount);
 return failures?1:0;
}

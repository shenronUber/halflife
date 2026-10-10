#include "../../game_shared/vf_proc_policy.h"
#include "../../game_shared/vf_status_policy.h"
#include <cassert>
#include <cstdio>
int main(){
 vfp::Accumulator a,b;vfp::Reset(a);vfp::Reset(b);
 for(int i=0;i<5;++i)assert(!vfp::Hit(a,0,float(i)*.1f));assert(a.count[0]==5);assert(vfp::Hit(a,0,.5f)&&a.count[0]==0);
 // A true sliding window must discard only expired hits, not the entire chain.
 vfp::Reset(a);for(int i=0;i<5;++i)assert(!vfp::Hit(a,1,float(i)*.6f));
 assert(!vfp::Hit(a,1,3.1f)&&a.count[1]==5);assert(vfp::Hit(a,1,3.2f));
 vfp::Reset(a);for(int i=0;i<5;++i)assert(!vfp::Hit(a,2,0));vfp::Expire(a,3.01f);assert(a.count[2]==0);assert(!vfp::Hit(a,2,3.1f));
 vfp::Reset(a);for(int i=0;i<5;++i)assert(!vfp::Hit(a,3,0));assert(vfp::Hit(a,3,3));
 vfp::Reset(a);for(int i=0;i<5;++i){assert(!vfp::Hit(a,0,0));assert(!vfp::Hit(a,1,0));}assert(!vfp::Hit(b,0,0));assert(vfp::Hit(a,1,.1f));assert(a.count[0]==5&&b.count[0]==1);
 assert(!vfp::Hit(a,-1,0)&&!vfp::Hit(a,8,0));vfp::Expire(a,-1);assert(a.count[0]==0);
 vfs::State s;vfs::Reset(s);for(int i=0;i<8;++i){vfp::Reset(a);for(int n=0;n<6;++n){bool proc=vfp::Hit(a,i,0);assert(proc==(n==5));}assert(vfs::ApplyPrimary(s,i,0,vfp::Duration).entered);}
 for(int i=0;i<8;++i)assert(vfs::Active(s,i,1));for(int i=8;i<vfs::Count;++i)assert(!vfs::Active(s,i,1));
 assert(!vfs::ApplyPrimary(s,8,1,6).entered);vfs::Expire(s,6);for(int i=0;i<8;++i)assert(!vfs::Active(s,i,6));
 puts("PASS six-hit proc: real sliding window, boundary, independent victims/elements, consumed batches, eight primaries without reactions");
}

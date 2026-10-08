#include "../../game_shared/vf_loadout.h"
#include "../../game_shared/vf_appearance.h"
#include <stdio.h>
#include <string.h>
#include <string>
#include <fstream>
#include <iterator>
#include <stdlib.h>
static int checks;
static void Check(bool ok,const char* message) {
    ++checks;if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(1);}
}
int main(int argc,char** argv) {
    Check(argc==4,"equipment, skins and arsenal catalog paths provided");
    std::ifstream f(argv[1],std::ios::binary);
    std::string text((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
    vf::Catalog c;Check(vf::ParseCatalog(text.data(),text.size(),c),"real catalog parses");
    Check(c.count==215,"214 equipment objects plus empty, including 60 fitted GIGN pieces");
    int selected[vf::SlotCount],totals[vf::BudgetCount];vf::Defaults(c,selected);
    Check(vf::Evaluate(c,selected,totals)==vf::Accepted,"starter build within all six budgets");
    for(int s=0;s<vf::SlotCount;++s) {
        Check(c.items[selected[s]].slot==s,"starter matches slot");
        int a=selected[s],b=vf::Cycle(c,s,a,1);
        Check(b!=a&&b>0&&c.items[b].slot==s,"can select alternate");
        int last=b;
        while(vf::Cycle(c,s,last,1)) last=vf::Cycle(c,s,last,1);
        Check(vf::Cycle(c,s,last,1)==0,"can unequip");
        Check(vf::Cycle(c,s,0,-1)==last,"reverse navigation wraps");
        selected[s]=b;
    }
    Check(vf::Evaluate(c,selected,totals)==vf::OverBudget,"all experimental items exceed capacities");
    vf::Defaults(c,selected);int baseline[6];vf::Evaluate(c,selected,baseline);
    selected[0]=2;vf::Evaluate(c,selected,totals);
    for(int b=0;b<4;++b)Check(totals[b]==baseline[b],"character cannot consume weapon capacity");
    vf::Defaults(c,selected);selected[12]=26;vf::Evaluate(c,selected,totals);
    Check(totals[4]==baseline[4]&&totals[5]==baseline[5],"weapon cannot consume character capacity");
    Check(vf::WeaponBody(c,selected)==1,"drum bodygroup encoding");
    selected[11]=24;Check(vf::WeaponBody(c,selected)==3,"drum plus muzzle bodygroup encoding");
    for(int head=0;head<3;++head)for(int torso=0;torso<3;++torso)for(int legs=0;legs<3;++legs) {
        const int heads[]={1,2,43},torsos[]={7,8,44},pants[]={11,12,45};
        selected[0]=heads[head];selected[3]=torsos[torso];selected[5]=pants[legs];
        Check(vf::OperatorBody(c,selected)==head+3*torso+9*legs,"all 27 character bodygroup combinations");
    }
    vf::Defaults(c,selected);selected[0]=selected[3];
    Check(vf::Evaluate(c,selected,totals)==vf::WrongSlot,"torso cannot equip in head slot");
    selected[0]=9999;Check(vf::Evaluate(c,selected,totals)==vf::BadItem,"invalid network item rejected");
    selected[0]=-1;Check(vf::Evaluate(c,selected,totals)==vf::BadItem,"negative index rejected");
    memset(selected,0,sizeof(selected));Check(vf::Evaluate(c,selected,totals)==vf::Accepted,"empty loadout allowed");
    unsigned int value;Check(!vf::ParseUnsigned("4294967296",value),"integer overflow rejected");
    Check(!vf::ParseUnsigned("-1",value)&&!vf::ParseUnsigned("2x",value),"malformed network integers rejected");
    Check(vf::ParseUnsigned("4294967295",value)&&value==0xffffffffu,"full fingerprint range accepted");
    std::string malformed=text;size_t at=malformed.find("head_standard");malformed.replace(at,13,"torso_standard");
    vf::Catalog bad;Check(!vf::ParseCatalog(malformed.data(),malformed.size(),bad),"duplicate IDs rejected");
    Check(vf::Evaluate(bad,selected,totals)==vf::BadCatalog,"invalid catalog never equippable");
    Check(!vf::ParseCatalog("limits|100|100",14,bad),"truncated metadata rejected");
    std::string overlong(800,'x');Check(!vf::ParseCatalog(overlong.data(),overlong.size(),bad),"oversized row rejected");
    Check(!vf::ParseCatalog(NULL,0,bad),"missing file rejected");
    std::string mixed=text;at=mixed.find("|0|0|0|0|3|3|");mixed[at+1]='1';
    Check(!vf::ParseCatalog(mixed.data(),mixed.size(),bad),"cross-system costs rejected at catalog load");
    std::string badVisual=text;at=badVisual.find("|0\n",badVisual.find("head|head_standard"));badVisual[at+1]='9';
    Check(!vf::ParseCatalog(badVisual.data(),badVisual.size(),bad),"unsupported bodygroup variant rejected");
    std::string changed=text+"\n# changed\n";vf::Catalog other;
    Check(vf::ParseCatalog(changed.data(),changed.size(),other)&&other.fingerprint!=c.fingerprint,"catalog mismatch detectable");
    for(int file=2;file<4;++file){
        std::ifstream a(argv[file],std::ios::binary);std::string data((std::istreambuf_iterator<char>(a)),std::istreambuf_iterator<char>());
        vf::AppearanceCatalog catalog;Check(vf::ParseAppearances(data.data(),data.size(),catalog),"real appearance catalog parses");
        Check(catalog.count>50&&catalog.count<240,"complete library fits wire protocol");
        if(file==2){
            int build[vf::SlotCount],ids[5];vf::GameplayDefaults(c,build);
            Check(vf::Evaluate(c,build,totals)==vf::Accepted,"gameplay defaults fit budgets");
            Check(vf::EquipmentSkins(c,build,catalog,ids),"gameplay default skins resolve");
            for(int z=0;z<5;++z)Check(!strcmp(catalog.entries[ids[z]].model,"persona_scout"),"gameplay uses fitted GIGN model in every body zone");
            for(int slot=0;slot<vf::SlotCount;++slot)Check(vf::GameplayItem(c.items[build[slot]]),"every gameplay slot is a registered loot item");
            int custom=0,provisional=0,reference=0;
            const int zoneSlots[]={0,3,2,5,6};
            for(int i=1;i<c.count;++i){const vf::Item& item=c.items[i];
                if(item.appearance[0]){
                    ++custom;vf::GameplayDefaults(c,build);build[item.slot]=i;
                    Check(vf::EquipmentSkins(c,build,catalog,ids),"custom item resolves its authored appearance");
                    for(int z=0;z<5;++z)Check(!strcmp(catalog.entries[ids[z]].key,zoneSlots[z]==item.slot?item.appearance:"persona_gign"),"custom equipment changes only its mapped GIGN zone");
                }else if(vf::GameplayItem(item)){if(item.slot<vf::GearSlots)++provisional;else ++reference;}
            }
            Check(custom==60&&provisional==24&&reference==26,"gameplay catalog excludes historical body and weapon placeholders");
            vf::Defaults(c,build);build[1]=0;vf::NormalizeGameplay(c,build);
            Check(build[1]==0,"normalizing keeps deliberately unequipped optional accessories");
            for(int slot=0;slot<vf::SlotCount;++slot)if(build[slot])Check(vf::GameplayItem(c.items[build[slot]]),"return from dev normalizes every historical object");
            vf::Defaults(c,build);
            Check(vf::EquipmentSkins(c,build,catalog,ids),"all default equipped looks resolve");
            for(int slot=0;slot<vf::SlotCount;++slot)for(int family=0;family<6;++family){
                int found=0;
                for(int i=1;i<c.count;++i)if(c.items[i].slot==slot){build[slot]=i;if(vf::EquipmentFamily(c,build,slot)==family){found=i;break;}}
                Check(found>0,"every slot represents every family");
                Check(vf::EquipmentSkins(c,build,catalog,ids)&&vf::ValidSkins(catalog,ids),"every equipment object resolves to valid appearance");
                for(int z=0;z<4;++z)Check(vf::EquipmentModule(c,build,z)>=0&&vf::EquipmentModule(c,build,z)<3,"module variant is in donor range");
                vf::Defaults(c,build);
            }
            memset(build,0,sizeof(build));Check(vf::EquipmentSkins(c,build,catalog,ids),"empty operator keeps a valid under-outfit");
            for(int slot=0;slot<vf::SlotCount;++slot)Check(vf::EquipmentFamily(c,build,slot)==-1,"unequipped accessory has no family");
            vf::Defaults(c,build);int before[5],after[5];vf::EquipmentSkins(c,build,catalog,before);build[2]=6;vf::EquipmentSkins(c,build,catalog,after);
            for(int z=0;z<5;++z)Check(z==2?before[z]!=after[z]:before[z]==after[z],"glove choice only changes hands");
        }
        int ids[5]={0,1,2,3,catalog.count-1};Check(vf::ValidSkins(catalog,ids),"mixed sources and last ID accepted");
        ids[2]=catalog.count;Check(!vf::ValidSkins(catalog,ids),"upper-bound skin rejected");ids[2]=-1;Check(!vf::ValidSkins(catalog,ids),"negative skin rejected");
        vf::AppearanceCatalog modified;std::string altered=data+"\n";Check(vf::ParseAppearances(altered.data(),altered.size(),modified)&&modified.hash!=catalog.hash,"appearance drift changes handshake hash");
    }
    const char* invalid[]={"0|../evil|Skin\n","1|skin_a|Skin\n","0|skin_a|Skin\n1|skin_a|Duplicate\n","0|skin_a|Skin|99999999999\n","0|skin_a|Skin|2|extra\n"};
    for(int i=0;i<5;++i){vf::AppearanceCatalog bad;Check(!vf::ParseAppearances(invalid[i],strlen(invalid[i]),bad)&&!bad.valid,"unsafe or ambiguous appearance catalog rejected");}
    const char* family="0|style_a|VF / Test|2|family_a|3\n";vf::AppearanceCatalog familyCatalog;
    Check(vf::ParseAppearances(family,strlen(family),familyCatalog)&&!strcmp(familyCatalog.entries[0].model,"family_a")&&familyCatalog.entries[0].skin==3,"texture variant resolves shared model and skin family");
    const char* badFamilies[]={"0|style_a|Test|2|../model|1\n","0|style_a|Test|2|family_a|32\n","0|style_a|Test|2||1\n","0|style_a|Test|2|family_a|-1\n"};
    for(int i=0;i<4;++i){vf::AppearanceCatalog bad;Check(!vf::ParseAppearances(badFamilies[i],strlen(badFamilies[i]),bad),"unsafe or invalid shared mesh reference rejected");}
    printf("PASS: %d checks; independent equipment budgets and five-zone appearance validation; fingerprint=%u\n",checks,c.fingerprint);
    return 0;
}

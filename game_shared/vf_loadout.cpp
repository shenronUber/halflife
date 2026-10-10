#include "vf_loadout.h"
#include "vf_model_contract.h"
#include <string.h>
#include <stdio.h>
#include <limits.h>
namespace vf {
const char* const SlotKeys[SlotCount]={"head","shoulders","gloves","torso","belt","legs","boots","shield","special","receiver","barrel","muzzle","feed","chamber","ammo","projectile","optic","underbarrel","grip","power","cooling"};
const char* const SlotNames[SlotCount]={"Tete","Epaules","Gants","Torse","Ceinture","Pantalon","Chaussures","Bouclier","Capacite speciale","Chassis / OS","Canon","Bouche","Alimentation","Culasse / cycle","Charge elementaire","Geometrie projectile","Optique","Sous-canon","Poignee / crosse","Batterie / capaciteur","Refroidissement"};
const char* const BudgetCodes[BudgetCount]={"TED","IP","HS","OI","SIG","BIO"};
const char* const BudgetNames[BudgetCount]={"Dissipation thermo-entropique","Profil inertiel","Stabilisation harmonique","Integrite operationnelle","Empreinte detectable","Charge metabolique"};
bool ParseUnsigned(const char* s,unsigned int& value) {
    if(!s || !*s) return false;
    value=0;
    for(;*s;++s) {
        if(*s<'0'||*s>'9') return false;
        unsigned int d=*s-'0';
        if(value>(UINT_MAX-d)/10) return false;
        value=value*10+d;
    }
    return true;
}
static bool Copy(char* dst,size_t cap,const char* src) {
    size_t n=strlen(src); if(!n||n>=cap) return false;
    memcpy(dst,src,n+1); return true;
}
static bool Fail(Catalog& c,int line,const char* why) {
    c.valid=false; snprintf(c.error,sizeof(c.error),"Ligne %d : %s",line,why); return false;
}
bool ParseCatalog(const char* data,size_t size,Catalog& c) {
    memset(&c,0,sizeof(c)); c.count=1;
    c.items[0].slot=-1; strcpy(c.items[0].name,"Emplacement libre");
    if(!data||!size||size>1024*1024) return Fail(c,0,"catalogue absent ou trop grand");
    // Hash the actual file, including ordering: a different client catalog cannot
    // reinterpret server item indexes silently.
    c.fingerprint=2166136261u;
    for(size_t n=0;n<size;++n) c.fingerprint=(c.fingerprint^(unsigned char)data[n])*16777619u;
    bool limits=false; int lineNo=0;
    for(size_t pos=0;pos<size;) {
        char line[768]; int n=0; ++lineNo;
        while(pos<size&&data[pos]!='\n') {
            unsigned char ch=data[pos++];
            if(ch=='\r') continue;
            if(ch<32||ch>126||n>=766) return Fail(c,lineNo,"texte ASCII invalide ou ligne trop longue");
            line[n++]=ch;
        }
        if(pos<size) ++pos;
        line[n]=0; if(!n||line[0]=='#') continue;
        char* f[18]; int fields=1; f[0]=line;
        for(char* p=line;*p;++p) if(*p=='|') {
            if(fields==18) return Fail(c,lineNo,"trop de colonnes");
            *p=0; f[fields++]=p+1;
        }
        if(!strcmp(f[0],"limits")) {
            if(limits||fields!=7) return Fail(c,lineNo,"limites invalides");
            for(int b=0;b<BudgetCount;++b) {
                unsigned int x;
                if(!ParseUnsigned(f[b+1],x)||x<1||x>1000) return Fail(c,lineNo,"limite hors plage");
                c.limits[b]=x;
            }
            limits=true; continue;
        }
        if((fields!=14&&fields!=15&&fields!=17)||c.count>=MaxItems) return Fail(c,lineNo,"format item invalide");
        Item& item=c.items[c.count]; item.slot=-1;
        for(int s=0;s<SlotCount;++s) if(!strcmp(f[0],SlotKeys[s])) item.slot=s;
        unsigned int tier;
        if(item.slot<0||!ParseUnsigned(f[2],tier)||tier<1||tier>3) return Fail(c,lineNo,"slot ou tier invalide");
        item.tier=tier;
        if(!Copy(item.id,sizeof(item.id),f[1])||!Copy(item.name,sizeof(item.name),f[3])||
           !Copy(item.category,sizeof(item.category),f[4])||!Copy(item.flavor,sizeof(item.flavor),f[5])||
           !Copy(item.description,sizeof(item.description),f[12])) return Fail(c,lineNo,"texte vide ou trop long");
        for(int j=1;j<c.count;++j) if(!strcmp(c.items[j].id,item.id)) return Fail(c,lineNo,"identifiant duplique");
        for(int b=0;b<BudgetCount;++b) {
            unsigned int x; if(!ParseUnsigned(f[6+b],x)||x>1000) return Fail(c,lineNo,"cout hors plage");
            item.cost[b]=x;
            if(x&&((item.slot<GearSlots&&b<4)||(item.slot>=GearSlots&&b>=4)))
                return Fail(c,lineNo,"cout attribue au mauvais systeme");
        }
        unsigned int visual;
        int maxVisual=(item.slot==0||item.slot==3||item.slot==5)?2:((item.slot==11||item.slot==12)?1:0);
        if(!ParseUnsigned(f[13],visual)||visual>(unsigned int)maxVisual) return Fail(c,lineNo,"variante visuelle invalide");
        item.visual=visual;
        if(fields==15){
            if(!Copy(item.appearance,sizeof(item.appearance),f[14]))return Fail(c,lineNo,"apparence invalide");
            for(const char* p=item.appearance;*p;++p)if(!((*p>='a'&&*p<='z')||(*p>='0'&&*p<='9')||*p=='_'))return Fail(c,lineNo,"cle apparence invalide");
            if(item.slot!=0&&item.slot!=2&&item.slot!=3&&item.slot!=5&&item.slot!=6)return Fail(c,lineNo,"apparence hors zone");
        }
        if(fields==17){
            if(item.slot<GearSlots||*f[14]||strncmp(item.id,"r01_",4)||
               !Copy(item.model,sizeof(item.model),f[15])||!Copy(item.weaponStyle,sizeof(item.weaponStyle),f[16]))return Fail(c,lineNo,"objet arme invalide");
            for(int k=15;k<=16;++k)for(const char* p=f[k];*p;++p)
                if(!((*p>='a'&&*p<='z')||(*p>='0'&&*p<='9')||*p=='_'))return Fail(c,lineNo,"cle objet arme invalide");
        }
        ++c.count;
    }
    if(!limits||c.count<2) return Fail(c,lineNo,"catalogue incomplet");
    if(!c.fingerprint) c.fingerprint=1;
    c.valid=true;
    for(int i=1;i<c.count;++i)if(c.items[i].model[0]){
        int base=FindItem(c,c.items[i].model);
        if(base<=0||c.items[base].slot!=c.items[i].slot||c.items[base].model[0]||strncmp(c.items[base].id,"r01_",4))return Fail(c,0,"modele objet arme invalide");
        if(memcmp(c.items[base].cost,c.items[i].cost,sizeof(c.items[i].cost))||c.items[base].tier!=c.items[i].tier||strcmp(c.items[base].category,c.items[i].category))return Fail(c,0,"variante mecanique incoherente");
        for(int j=1;j<i;++j)if(!strcmp(c.items[j].model,c.items[i].model)&&!strcmp(c.items[j].weaponStyle,c.items[i].weaponStyle))return Fail(c,0,"variante arme dupliquee");
    }
    return true;
}
Result Evaluate(const Catalog& c,const int selection[SlotCount],int totals[BudgetCount]) {
    memset(totals,0,sizeof(int)*BudgetCount);
    if(!c.valid) return BadCatalog;
    for(int s=0;s<SlotCount;++s) {
        int i=selection[s]; if(i<0||i>=c.count) return BadItem;
        if(!i) continue;
        const Item& item=c.items[i]; if(item.slot!=s) return WrongSlot;
        for(int b=0;b<BudgetCount;++b) totals[b]+=item.cost[b];
    }
    for(int b=0;b<BudgetCount;++b) if(totals[b]>c.limits[b]) return OverBudget;
    return Accepted;
}
Result EvaluateExperiment(const Catalog& c,const int selection[SlotCount],int totals[BudgetCount]) {
    Result result=Evaluate(c,selection,totals);
    if(result!=Accepted&&result!=OverBudget)return result;
    bool reference=false;
    for(int s=GearSlots;s<SlotCount;++s)if(selection[s]&&!strncmp(c.items[selection[s]].id,"r01_",4))reference=true;
    if(reference)for(int s=GearSlots;s<SlotCount;++s)
        if(!selection[s]||strncmp(c.items[selection[s]].id,"r01_",4))return Incompatible;
    return result;
}
Result EvaluateGameplay(const Catalog& c,const int selection[SlotCount],int totals[BudgetCount]) {
    Result result=EvaluateExperiment(c,selection,totals);
    if(result!=Accepted)return result;
    bool authored=false;
    for(int i=1;i<c.count;++i)if(c.items[i].appearance[0])authored=true;
    if(!authored)return Accepted; // Legacy laboratory catalogs have no gameplay subset.
    for(int s=0;s<SlotCount;++s){
        int id=selection[s];bool optional=s==1||s==4||s==7||s==8;
        if((!id&&!optional)||(id&&!GameplayItem(c.items[id])))return Incompatible;
    }
    return Accepted;
}
int FindItem(const Catalog& c,const char* key) {
    if(!c.valid||!key)return -1;
    if(!*key)return 0;
    for(int i=1;i<c.count;++i)if(!strcmp(c.items[i].id,key))return i;
    return -1;
}
void RestoreEquipment(const Catalog& c,const char* const keys[SlotCount],int selection[SlotCount]) {
    GameplayDefaults(c,selection);
    if(!c.valid||!keys)return;
    for(int s=0;s<SlotCount;++s){int id=FindItem(c,keys[s]);if(id==0||(id>0&&c.items[id].slot==s))selection[s]=id;}
}
void Defaults(const Catalog& c,int selection[SlotCount]) {
    memset(selection,0,sizeof(int)*SlotCount);
    if(!c.valid) return;
    for(int i=1;i<c.count;++i) if(!selection[c.items[i].slot]) selection[c.items[i].slot]=i;
    int totals[BudgetCount];
    if(Evaluate(c,selection,totals)!=Accepted) memset(selection,0,sizeof(int)*SlotCount);
}
const char* ItemModel(const Item& item){return item.model[0]?item.model:item.id;}
int ReceiverMount(const Item& item){const ModelTraits* traits=FindModelTraits(ItemModel(item));return traits?traits->feedMount:0;}
bool GameplayItem(const Item& item) {
    return item.appearance[0] || (item.slot>=GearSlots&&item.model[0]&&item.weaponStyle[0]) ||
           item.slot==1||item.slot==4||item.slot==7||item.slot==8;
}
void GameplayDefaults(const Catalog& c,int selection[SlotCount]) {
    memset(selection,0,sizeof(int)*SlotCount);if(!c.valid)return;
    bool authored=false;
    for(int i=1;i<c.count;++i)if(GameplayItem(c.items[i])){int s=c.items[i].slot;if(s!=1&&s!=4&&s!=7&&s!=8&&!selection[s])selection[s]=i;if(c.items[i].appearance[0])authored=true;}
    if(!authored)Defaults(c,selection); // Historical developer deployments remain supported.
}
void NormalizeGameplay(const Catalog& c,int selection[SlotCount]) {
    int base[SlotCount];GameplayDefaults(c,base);
    for(int s=0;s<SlotCount;++s){int id=selection[s];bool optional=s==1||s==4||s==7||s==8;
        if(id<0||id>=c.count||(id&&(!GameplayItem(c.items[id])||c.items[id].slot!=s))||(!id&&!optional))selection[s]=base[s];
    }
    int totals[BudgetCount];if(EvaluateGameplay(c,selection,totals)!=Accepted)memcpy(selection,base,sizeof(base));
}
int Cycle(const Catalog& c,int slot,int current,int direction) {
    if(!c.valid||slot<0||slot>=SlotCount) return 0;
    if(current<0||current>=c.count) current=0;
    for(int n=0;n<c.count;++n) {
        current=(current+(direction<0?c.count-1:1))%c.count;
        if(!current||c.items[current].slot==slot) return current;
    }
    return 0;
}
int Visual(const Catalog& c,const int selection[SlotCount],int slot) {
    if(!c.valid||slot<0||slot>=SlotCount)return 0;
    int i=selection[slot];
    return i>0&&i<c.count&&c.items[i].slot==slot?c.items[i].visual:0;
}
int OperatorBody(const Catalog& c,const int selection[SlotCount]) {
    return Visual(c,selection,0)+3*Visual(c,selection,3)+9*Visual(c,selection,5);
}
int WeaponBody(const Catalog& c,const int selection[SlotCount]) {
    return Visual(c,selection,12)+2*Visual(c,selection,11);
}
}

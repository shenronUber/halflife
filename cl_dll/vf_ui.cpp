#include <cmath>
#include "hud.h"
#include "cl_util.h"
#include "keydefs.h"
#include "vf_ui.h"
#include "vf_ui_font.h"
#include "triangleapi.h"
#include "vf_character.h"
#include "vf_skinmenu.h"
#include "vf_preview.h"
#include "vf_engine.h"
#include "vf_effects.h"
#include "../game_shared/vf_loadout.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace vfui {
const Color bg={10,16,23},panel={19,29,39},edge={43,59,71},muted={143,164,177},white={233,240,239},teal={92,224,199},amber={245,189,102},red={247,112,106};
const Family families[6]={
 {"Baseline","Fondations","Precision, regularite et utilite. Une base lisible pour construire la configuration.",{169,189,204}},
 {"Predator","Detection","Acquisition de cible, lecture des resistances et information tactique.",{245,189,102}},
 {"Fortress","Protection","Resistance, amortissement et controle defensif de l'espace.",{112,171,249}},
 {"Rogue","Mobilite","Deplacement, discretion et changements de rythme.",{92,224,199}},
 {"Engine","Synergies","Amorcage, etats elementaires et enchainements de reactions.",{196,151,246}},
 {"Anomalous","Ruptures","Comportements atypiques, phase et neutralisation avec des contreparties.",{247,112,155}}
};
static float px=640,py=350,pressX=640,pressY=350;
static bool held=false,released=false,drag=false,guide=false;
static bool modeMenu=false,modeDrawing=false;
static int wheel=0,selectedFamily=0,guidePage=0,selectedBudget=4;
static const char* tooltip=NULL;
static char tooltipText[256];
static HSPRITE fontSprite=0;
float SX(){return fminf(ScreenWidth/1280.f,ScreenHeight/720.f);} float SY(){return SX();}
float X(float value){return (ScreenWidth-1280*SX())*.5f+value*SX();}
float Y(float value){return (ScreenHeight-720*SY())*.5f+value*SY();}
static float Clamp(float v,float lo,float hi){return v<lo?lo:v>hi?hi:v;}
void Focus(){fontSprite=0;held=released=drag=false;wheel=0;guide=false;modeMenu=false;tooltip=NULL;}
void Move(float dx,float dy){
 if(!VF_CharacterOpen())return;
 if(drag&&held){VF_PreviewRotate(dx*.35f);return;}
 px=Clamp(px+dx/SX(),2,1275);py=Clamp(py+dy/SY(),2,715);
}
bool Key(int down,int key){
 if(!VF_CharacterOpen())return false;
 if(guide&&guidePage==2&&(key==K_PGUP||key==K_PGDN)){if(down)gEngfuncs.pfnClientCmd(key==K_PGUP?"vf_effect_prev\n":"vf_effect_next\n");return true;}
 if(key==K_MOUSE1){if(down){held=true;pressX=px;pressY=py;}else {released=held&&!drag;held=false;drag=false;}return true;}
 if(key==K_MOUSE2)return true;
 if(key==K_MWHEELUP||key==K_MWHEELDOWN){if(down)wheel+=key==K_MWHEELUP?1:-1;return true;}
 if(modeMenu&&key==K_ESCAPE){if(down)modeMenu=false;return true;}
 if(guide&&key==K_ESCAPE){if(down)guide=false;return true;}
 if(guide&&key!=K_F1&&key!=K_F2&&key!=K_F3&&key!=K_F9&&key!=K_F8&&key!=K_F10&&key!=K_F11)return true;
 return false;
}
void Box(float x,float y,float w,float h,Color c,int a){if(w<=0||h<=0)return;gEngfuncs.pfnFillRGBABlend(int(X(x)),int(Y(y)),int(w*SX()+.5f),int(h*SY()+.5f),c.r,c.g,c.b,a);}
void Frame(float x,float y,float w,float h,Color c){Box(x,y,w,1,c);Box(x,y+h-1,w,1,c);Box(x,y,1,h,c);Box(x+w-1,y,1,h,c);}

static float Width(const char* text){float w=0;for(const unsigned char* p=(const unsigned char*)text;*p;++p)w+=vfFontAdvance[*p>=32&&*p<128?*p-32:'?'-32];return w*SX();}
static void RenderText(float x,float y,const char* text,Color color,float scale){
 if(!fontSprite)fontSprite=gEngfuncs.pfnSPR_Load("sprites/vf_ui/ui_font.spr");
 if(!fontSprite){gEngfuncs.pfnDrawSetTextColor(color.r/255.f,color.g/255.f,color.b/255.f);gEngfuncs.pfnDrawConsoleString(int(X(x)),int(Y(y)),(char*)text);return;}
 triangleapi_t* api=gEngfuncs.pTriAPI;api->RenderMode(kRenderTransAdd);api->CullFace(TRI_NONE);api->SpriteTexture(const_cast<model_s*>(gEngfuncs.GetSpritePointer(fontSprite)),0);api->Color4f(color.r/255.f,color.g/255.f,color.b/255.f,1);api->Begin(TRI_QUADS);
 for(const unsigned char* p=(const unsigned char*)text;*p;++p){int i=*p>=32&&*p<128?*p-32:'?'-32;float glyphWidth=fminf(48.f,ceilf(vfFontAdvance[i]*2)+4);float u=(i%16)*48/1024.f,v=(i/16)*56/512.f,U=u+glyphWidth/1024.f,V=v+48/512.f;
  float X=vfui::X(x),Y=vfui::Y(y),W=glyphWidth*.5f*scale*SX(),H=24*scale*SY();
  api->TexCoord2f(u,v);api->Vertex3f(X,Y,0);api->TexCoord2f(U,v);api->Vertex3f(X+W,Y,0);api->TexCoord2f(U,V);api->Vertex3f(X+W,Y+H,0);api->TexCoord2f(u,V);api->Vertex3f(X,Y+H,0);
  x+=vfFontAdvance[i]*scale;
 }api->End();api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
}
void Text(float x,float y,const char* s,Color c,float width){
 char clipped[256];snprintf(clipped,sizeof(clipped),"%s",s?s:"");
 if(width>0&&Width(clipped)>width*SX()){int n=(int)strlen(clipped);while(n>0){clipped[--n]=0;char test[260];snprintf(test,sizeof(test),"%s...",clipped);if(Width(test)<=width*SX()){strcpy(clipped,test);break;}}}
 RenderText(x,y-3,clipped,c,1);
}
void Wrap(float x,float y,const char* s,float width,Color c,int lines){
 if(!s)return;for(int l=0;*s&&l<lines;++l){char line[256];int n=0,last=0;while(s[n]&&n<250){line[n]=s[n];line[n+1]=0;if(Width(line)>width*SX())break;if(s[n]==' ')last=n;++n;}
 if(s[n]&&last)n=last;if(!n)n=1;memcpy(line,s,n);line[n]=0;Text(x,y+l*21,line,c,width);s+=n;while(*s==' ')++s;}
}
static void Line(float x,float y,float X,float Y,Color c,float thick=2){int n=int(fmax(fabs(X-x),fabs(Y-y)));if(!n)n=1;for(int i=0;i<=n;++i){float t=i/(float)n;Box(x+(X-x)*t,y+(Y-y)*t,thick,thick,c);}}
void Icon(int kind,float x,float y,float size,Color c){
 float k=size/32.f;
 #define L(a,b,d,e) Line(x+(a)*k,y+(b)*k,x+(d)*k,y+(e)*k,c,1.5f*k)
 #define B(a,b,d,e) Box(x+(a)*k,y+(b)*k,(d)*k,(e)*k,c)
 switch(kind){
 case 0:L(5,7,27,7);L(5,16,23,16);L(5,25,27,25);B(11,4,3,6);B(20,13,3,6);B(8,22,3,6);break;
 case 1:L(3,16,12,6);L(12,6,21,6);L(21,6,29,16);L(29,16,21,26);L(21,26,12,26);L(12,26,3,16);Frame(x+12*k,y+12*k,8*k,8*k,c);break;
 case 2:L(5,4,27,4);L(5,4,5,19);L(27,4,27,19);L(5,19,16,29);L(27,19,16,29);L(16,9,16,22);break;
 case 3:L(4,7,19,7);L(19,7,12,16);L(12,16,27,16);L(27,16,11,29);L(4,23,9,18);break;
 case 4:Frame(x+10*k,y+10*k,12*k,12*k,c);L(16,2,16,8);L(16,24,16,30);L(2,16,8,16);L(24,16,30,16);L(5,5,9,9);L(24,24,28,28);L(5,27,9,23);L(23,9,27,5);break;
 case 5:L(16,2,29,16);L(29,16,16,30);L(16,30,3,16);L(3,16,16,2);L(20,8,12,23);L(13,8,9,14);break;
 case 6:Frame(x+11*k,y+2*k,10*k,9*k,c);L(7,14,25,14);L(7,14,5,25);L(25,14,27,25);L(11,16,11,30);L(21,16,21,30);break;
 case 7:B(3,10,24,7);B(25,11,6,3);L(9,18,6,27);L(16,18,18,25);break;
 case 8:Frame(x+4*k,y+4*k,24*k,24*k,c);L(5,23,13,15);L(13,15,19,21);L(19,21,27,11);break;
 case 9:Frame(x+4*k,y+4*k,24*k,24*k,c);L(5,12,27,12);L(12,13,12,28);break;

 case 14:L(5,18,5,10);L(5,10,11,4);L(11,4,23,4);L(23,4,28,12);L(28,12,28,23);L(28,23,15,27);L(15,27,10,20);L(5,15,24,15);break;
 case 15:L(2,22,4,9);L(4,9,12,6);L(12,6,14,22);L(18,22,20,6);L(20,6,28,9);L(28,9,30,22);break;
 case 16:L(8,27,5,18);L(5,18,9,15);L(9,15,12,18);L(12,18,12,5);L(12,5,25,5);L(25,5,25,23);L(25,23,20,28);L(16,6,16,14);L(21,6,21,14);break;
 case 17:L(4,7,11,3);L(11,3,16,9);L(16,9,21,3);L(21,3,28,7);L(28,7,25,28);L(25,28,7,28);L(7,28,4,7);L(16,12,16,27);break;
 case 18:Frame(x+2*k,y+10*k,28*k,12*k,c);Frame(x+11*k,y+8*k,10*k,16*k,c);break;
 case 19:L(7,3,25,3);L(25,3,27,29);L(27,29,19,29);L(19,29,16,14);L(16,14,13,29);L(13,29,5,29);L(5,29,7,3);break;
 case 20:L(5,3,17,3);L(17,3,17,18);L(17,18,28,22);L(28,22,28,29);L(28,29,4,29);L(4,29,5,3);L(7,10,13,10);break;
 case 21:Frame(x+3*k,y+10*k,26*k,12*k,c);L(6,6,23,6);L(11,23,8,29);L(20,23,22,29);break;
 case 22:L(2,11,30,11);L(2,20,30,20);L(5,7,5,24);L(27,7,27,24);break;
 case 23:L(3,12,18,12);L(3,20,18,20);L(19,9,19,23);L(24,8,29,4);L(24,16,31,16);L(24,24,29,28);break;
 case 24:L(9,3,24,3);L(24,3,24,19);L(24,19,18,29);L(18,29,5,26);L(5,26,9,3);L(13,8,11,22);L(18,8,16,24);break;
 case 26:L(16,2,5,19);L(5,19,8,27);L(8,27,24,27);L(24,27,27,19);L(27,19,16,2);break;
 case 27:L(10,28,10,10);L(10,10,16,2);L(16,2,22,10);L(22,10,22,28);L(22,28,10,28);L(10,21,22,21);break;
 case 28:Frame(x+7*k,y+7*k,18*k,18*k,c);L(16,1,16,12);L(16,20,16,31);L(1,16,12,16);L(20,16,31,16);break;
 case 29:L(2,7,30,7);L(4,13,28,13);L(9,16,9,26);L(9,26,24,26);L(24,26,24,16);break;
 case 30:L(5,4,27,4);L(27,4,19,27);L(19,27,9,27);L(9,27,13,12);L(13,12,5,12);L(5,12,5,4);break;
 case 31:Frame(x+7*k,y+5*k,18*k,24*k,c);B(12,1,8,3);L(17,9,12,18);L(12,18,20,18);L(20,18,15,25);break;
 case 32:L(5,3,5,28);L(11,6,11,25);L(17,3,17,28);L(23,6,23,25);L(29,3,29,28);break;
 case 33:L(2,6,11,27);L(11,27,21,4);L(14,27,24,4);L(24,4,31,4);L(20,14,28,14);break;

 case 34: // TED: thermal reservoir and dissipation waves.
  L(8,4,8,21);L(8,21,4,25);L(4,25,7,29);L(7,29,13,29);L(13,29,16,25);L(16,25,12,21);L(12,21,12,4);L(8,4,12,4);
  L(20,27,23,20);L(23,20,20,13);L(20,13,23,5);L(27,27,30,20);L(30,20,27,13);L(27,13,30,5);break;
 case 35: // IP: a mass and the vector of its inertia.
  Frame(x+2*k,y+12*k,10*k,12*k,c);L(15,18,30,18);L(24,12,30,18);L(30,18,24,24);L(4,6,11,6);L(2,2,8,2);break;
 case 36: // HS: two bounded harmonics.
  L(3,3,3,29);L(29,3,29,29);L(6,16,11,7);L(11,7,20,25);L(20,25,26,16);L(6,22,12,17);L(12,17,20,17);L(20,17,26,10);break;
 case 37: // OI: mechanical integrity with a validation mark.
  L(9,3,24,3);L(24,3,29,11);L(29,11,29,24);L(29,24,22,29);L(22,29,8,29);L(8,29,3,22);L(3,22,3,9);L(3,9,9,3);
  L(8,16,14,22);L(14,22,24,11);B(8,7,3,3);B(22,24,3,3);break;
 case 38: // SIG: radar field and detectable return.
  L(4,10,10,4);L(10,4,23,4);L(23,4,29,10);L(29,10,29,23);L(29,23,23,29);L(23,29,10,29);L(10,29,4,23);L(4,23,4,10);
  Frame(x+10*k,y+10*k,13*k,13*k,c);L(16,17,27,6);B(15,15,3,3);B(24,6,3,3);break;
 case 39: // BIO: double helix with paired rungs.
  L(7,2,23,12);L(23,12,23,19);L(23,19,7,30);L(25,2,9,12);L(9,12,9,19);L(9,19,25,30);
  L(12,7,20,7);L(10,15,22,15);L(12,24,20,24);break;
 case 10:L(6,6,26,26);L(6,26,26,6);break;
 case 11:L(21,5,10,16);L(10,16,21,27);break;
 case 12:L(11,5,22,16);L(22,16,11,27);break;
 default:Frame(x+6*k,y+6*k,20*k,20*k,c);L(16,10,16,22);L(10,16,22,16);break;
 }
 #undef L
 #undef B
}
bool Hover(float x,float y,float w,float h){return px>=x&&py>=y&&px<x+w&&py<y+h;}
void Tip(const char* text){snprintf(tooltipText,sizeof(tooltipText),"%s",text);tooltip=tooltipText;}
bool Button(float x,float y,float w,float h,const char* label,bool selected,bool enabled,int icon){
 enabled=enabled&&(!modeMenu||modeDrawing);selected=selected&&enabled;bool hover=Hover(x,y,w,h);Color accent=enabled?(selected?teal:muted):edge;
 Box(x,y,w,h,selected?Color{28,64,65}:hover&&enabled?Color{38,53,65}:panel);Frame(x,y,w,h,hover&&enabled?teal:selected?teal:edge);
 if(selected)Box(x,y,3,h,teal);
 if(icon>=0)Icon(icon,x+10,y+(h-22)*.5f,22,accent);
 Text(x+(icon>=0?41:12),y+(h-16)*.5f,label,enabled?(selected?white:hover?white:muted):Color{86,109,124},w-(icon>=0?52:24));
 bool click=enabled&&released&&hover&&pressX>=x&&pressX<x+w&&pressY>=y&&pressY<y+h;
 if(click){released=false;gEngfuncs.Con_DPrintf("VFUI click: %s\n",label);}return click;
}
int FamilyId(const char* name){for(int i=0;i<6;++i)if(!strcmp(name,families[i].name))return i;return -1;}
void Badge(int f,float x,float y,float w){if(f<0||f>5)return;Box(x,y,w,30,families[f].color,24);Icon(f,x+6,y+5,19,families[f].color);Text(x+34,y+7,families[f].name,families[f].color,w-40);if(Hover(x,y,w,30))Tip(families[f].summary);}
void Viewport(float x,float y,float w,float h){
 if(held&&pressX>=x&&pressX<x+w&&pressY>=y&&pressY<y+h)drag=true;
 if(Hover(x,y,w,h)&&wheel){VF_PreviewZoom(.06f*wheel);wheel=0;}
 Frame(x,y,w,h,drag?teal:edge);Box(x+12,y+h-25,4,4,teal);Text(x+25,y+h-30,"Glisser : rotation   Molette : zoom",muted,w-35);
}
int Scroll(float x,float y,float w,float h){if(!Hover(x,y,w,h))return 0;int value=wheel;wheel=0;return value;}
Color BudgetColor(int b){static const Color colors[6]={{245,160,85},{112,181,249},{192,162,250},{102,218,180},{92,217,232},{159,219,115}};return b>=0&&b<6?colors[b]:teal;}
const char* BudgetTip(int b){static const char* help[]={
 "TED / Dissipation thermo-entropique. Capacite thermique requise par les modules de l'arme.",
 "IP / Profil inertiel. Contrainte d'inertie et de maniement de l'arme.",
 "HS / Stabilisation harmonique. Capacite de stabilisation des modules de l'arme.",
 "OI / Integrite operationnelle. Capacite de fonctionnement et de fiabilite de l'arme.",
 "SIG / Empreinte detectable. Capacite de signature de l'equipement de l'operateur.",
 "BIO / Charge metabolique. Charge biologique de l'equipement de l'operateur."
 };return b>=0&&b<6?help[b]:"";}
void Meter(float x,float y,float w,const char* name,int value,int applied,int limit,Color c,int icon){
 char s[64];snprintf(s,sizeof(s),"%s   %d / %d",name,value,limit);if(icon>=0)Icon(icon,x,y-3,23,c);Text(x+(icon>=0?33:0),y,s,value>limit?red:white,w-(icon>=0?33:0));int delta=value-applied;
 if(delta){snprintf(s,sizeof(s),"%+d",delta);Text(x+w-42,y,s,delta>0?amber:teal,42);}
 Box(x,y+24,w,5,edge);float p=limit?Clamp(value/(float)limit,0,1):0;Box(x,y+24,w*p,5,value>limit?red:c);
 float a=limit?Clamp(applied/(float)limit,0,1):0;Box(x+(w-2)*a,y+22,2,9,white);
}
void Begin(int section){
 tooltip=NULL;gEngfuncs.pfnFillRGBABlend(0,0,ScreenWidth,ScreenHeight,bg.r,bg.g,bg.b,254);Box(0,0,1280,720,bg,254);Box(0,0,1280,4,teal);Icon(33,25,24,32,teal);RenderText(72,12,"VECTOR FIELDS",white,1.5f);Text(72,47,"ATELIER / CONFIGURATION",muted);
 modeDrawing=true;if(Button(640,22,370,38,VF_EngineLinked()?"Apparence : liee a l'equipement  v":"Apparence : libre  v",modeMenu))modeMenu=!modeMenu;modeDrawing=false;
 if(Button(1026,22,138,38,"Guide",guide,true,9)){guide=!guide;released=false;}
 if(Button(1176,22,80,38,"",false,true,10)){VF_CharacterClose();VF_SkinsClose();Focus();}
 const char* tabs[]={"Operateur","Arme / systemes","Apparence","Arme / style","Arsenal"};int icons[]={6,4,8,7,9};
 for(int i=0;i<5;++i)if(Button(24+i*249.f,84,240,43,tabs[i],section==i,true,icons[i])){guide=false;if(i<2)VF_CharacterShow(i);else VF_SkinsShow(i==2?0:i==3?2:1);}
 Box(24,140,1232,1,edge);
}
void OpenEffects(){guide=true;guidePage=2;}
bool Guide(){
 if(!guide)return false;

 if(Button(574,155,155,35,"Relais R-01",guidePage==3))guidePage=3;
 if(Button(744,155,165,35,"Effets",guidePage==2))guidePage=2;
 if(Button(922,155,155,35,"Familles",guidePage==0))guidePage=0;
 if(Button(1091,155,165,35,"Jauges",guidePage==1))guidePage=1;
 if(guidePage==2){VF_EffectsGuide();return true;}

 if(guidePage==3){
  Text(28,162,"RELAIS R-01 / ATELIER MODULAIRE",white,530);
  Text(28,204,"12 emplacements / 26 pieces / 3 alimentations / 8 192 assemblages",teal,1210);
  const char* names[]={"Chassis","Canon","Bouche","Chargeur","Culasse","Charge","Projectile","Optique","Sous-canon","Poignee / crosse","Batterie","Refroidisseur"};
  const char* pairs[]={"Dessous : Atelier, Circuit / Lateral : Traverse / Dessus : Zenith","Chemise ventilee / Induction cuivre","Frein ajoure / Moderateur court","Nervure / Double pile","Levier / Glissiere","Cassette balistique / Energetique","Porte-flechettes / Porte-ampoules","Viseur cadre / Lunette compacte","Poignee inclinee / Tube auxiliaire","Squelette / Amortie","Cellule 24V / Condensateur 48V","Ailettes / Circuit cuivre"};
  const int icons[]={21,22,23,24,4,26,27,28,29,30,31,32};
  for(int i=0;i<12;++i){float x=24+(i%2)*626.f,y=239+(i/2)*59.f;Box(x,y,606,52,panel);Icon(icons[i],x+12,y+12,27,i%2?amber:teal);Text(x+54,y+5,names[i],white,540);Text(x+54,y+29,pairs[i],muted,540);}
  Wrap(28,602,"F11 : atelier. Dessous / Lateral / Dessus change le chassis en conservant le chargeur, les autres pieces et les finitions. Appliquer puis R en jeu : rechargement propre au montage.",1210,white,2);
  Text(28,651,"Memes chargeurs, memes proprietes. Main et extraction adaptees ; viseur decale sur Zenith. Tir MP5 provisoire.",amber,1210);
  if(Button(28,679,268,30,"Ouvrir le Relais R-01",true)){guide=false;VF_CharacterReference(-1);}
  Text(321,686,"Mode lie a l'equipement / 1920 x 1080 sans bordure",muted,900);
  return true;
 }

 Text(28,162,guidePage?"JAUGES / LIRE SA CONFIGURATION":"FAMILLES / INTENTION DE JEU",white,530);
 Text(28,190,guidePage?"Choisir une jauge pour comprendre son role et son calcul actuel.":"Une famille de comportement, un emplacement technique, un univers visuel.",muted,865);
 if(guidePage){
  Text(24,225,"OPERATEUR",teal);Text(24,391,"ARME",amber);
  const int order[]={4,5,0,1,2,3};
  for(int i=0;i<6;++i){int b=order[i];float y=i<2?250+i*61.f:420+(i-2)*57.f;
   char label[96];snprintf(label,sizeof(label),"%s / %s",vf::BudgetCodes[b],b==0?"Dissipation thermique":b==1?"Profil inertiel":b==2?"Stabilisation":b==3?"Integrite":b==4?"Signature":"Charge biologique");
   if(Button(24,y,400,50,label,selectedBudget==b,true,34+b)){selectedBudget=b;gEngfuncs.Con_DPrintf("VFUI budget: %s\n",vf::BudgetCodes[b]);}
  }
  const char* meaning[]={
   "TED represente les exigences thermiques du montage : chaleur et capacite de dissipation sollicitees par les modules de l'arme.",
   "IP represente la contrainte d'inertie du montage : masse, mise en mouvement et exigences de maniement de l'arme.",
   "HS represente la stabilisation demandee par les modules pour maintenir un fonctionnement coherent de l'arme.",
   "OI represente l'exigence de fiabilite du montage : sa capacite a supporter et faire fonctionner les modules assembles.",
   "SIG represente l'empreinte detectable associee a l'equipement de l'operateur. Elle servira a encadrer les compromis de discretion.",
   "BIO represente la charge metabolique et biologique imposee a l'operateur par son equipement et ses capacites."
  };
  const char* future[]={
   "La temperature pendant le tir et le refroidissement ne sont pas encore simules.",
   "Le poids ressenti, le recul et la vitesse de visee ne sont pas encore modifies par IP.",
   "Les effets de stabilisation sur le tir et les synergies restent a implementer.",
   "Les pannes, l'usure et les penalites de fiabilite ne sont pas encore actives.",
   "La detection par les ennemis et le bruit reel ne sont pas encore pilotes par SIG.",
   "La fatigue, la sante et les effets metaboliques en combat ne sont pas encore pilotes par BIO."
  };
  int b=selectedBudget;Color c=BudgetColor(b);
  Box(450,231,806,410,panel);Icon(34+b,473,249,57,c);RenderText(552,239,vf::BudgetCodes[b],c,1.7f);Text(553,284,vf::BudgetNames[b],white,681);
  Wrap(474,335,meaning[b],756,white,2);
  Text(474,394,"CALCUL ACTUEL / PROTOTYPE",c);
  Wrap(474,424,"Somme des couts des pieces equipees, comparee a une limite provisoire. Une valeur plus haute utilise davantage de capacite.",756,muted,2);
  Wrap(474,478,future[b],756,amber,2);
  Text(474,527,"EXEMPLE DE LECTURE",white);
  Meter(474,556,756,vf::BudgetCodes[b],63,44,100,c,34+b);
  Text(474,598,"63 / 100 utilises. Trait blanc : valeur appliquee. +19 : ecart de la proposition.",muted,756);
  Text(40,670,"Depasser une limite bloque Appliquer. Les budgets operateur et arme restent independants.",muted,1200);
  return true;
 }

 for(int i=0;i<6;++i){float x=24+(i%3)*416.f,y=232+(i/3)*114.f;
 if(Button(x,y,400,97,"",selectedFamily==i,true)){selectedFamily=i;}
 Icon(i,x+17,y+23,46,families[i].color);Text(x+83,y+22,families[i].name,families[i].color);Text(x+83,y+51,families[i].role,white);
 }
 Box(24,466,1232,170,panel);Icon(selectedFamily,45,489,48,families[selectedFamily].color);Text(116,486,families[selectedFamily].name,white);Wrap(116,519,families[selectedFamily].summary,720,muted,3);
 Text(906,487,"JAUGES INDEPENDANTES",teal);
 Text(906,514,"OPERATEUR",muted);
 const char* codes[]={"TED","IP","HS","OI","SIG","BIO"};
 for(int b=4;b<6;++b){float x=906+(b-4)*142.f;if(Button(x,532,135,35,"")){selectedBudget=b;guidePage=1;}Icon(34+b,x,537,24,BudgetColor(b));Text(x+35,540,codes[b],BudgetColor(b));if(Hover(x,532,135,35))Tip(BudgetTip(b));}
 Text(906,574,"ARME",muted);
 for(int b=0;b<4;++b){float x=906+b*78.f;if(Button(x,593,77,35,"")){selectedBudget=b;guidePage=1;}Icon(34+b,x,598,23,BudgetColor(b));Text(x+29,600,codes[b],BudgetColor(b));if(Hover(x,593,77,35))Tip(BudgetTip(b));}
 Text(40,651,"Liee a l'equipement : les objets determinent le visuel. Libre : les skins choisis prennent le dessus.",muted,1190);
 Text(40,682,"6 collections / 21 emplacements. Les effets de combat restent a implementer.",teal,1190);
 return true;
}
void End(){
 if(modeMenu){modeDrawing=true;Box(640,64,370,116,bg);Frame(640,64,370,116,teal);
  if(Button(646,70,358,44,"Liee a l'equipement",VF_EngineLinked())){VF_EngineSetAppearanceMode(0);modeMenu=false;}
  if(Button(646,121,358,44,"Apparence libre",!VF_EngineLinked())){VF_EngineSetAppearanceMode(1);modeMenu=false;}
  if(released&&!Hover(640,22,370,158)){modeMenu=false;released=false;}
  modeDrawing=false;
 }

 if(tooltip&&!held){float x=Clamp(px+18,24,906),y=Clamp(py+25,150,635);Box(x,y,340,65,panel);Frame(x,y,340,65,teal);Wrap(x+10,y+8,tooltip,320,white,2);}
 // Draw our pointer in the HUD while SDL retains relative capture for the game.
 for(int i=0;i<16;++i)Box(px,py+i,i*.6f+2,1,bg);
 Line(px,py,px,py+17,white);Line(px,py,px+11,py+11,white);Line(px+1,py+15,px+7,py+10,teal);
 released=false;wheel=0;
}
static void PointerCommand(){
 if(gEngfuncs.pfnGetCvarFloat("developer")<1||gEngfuncs.Cmd_Argc()!=4||!VF_CharacterOpen())return;
 float x=(float)atof(gEngfuncs.Cmd_Argv(1)),y=(float)atof(gEngfuncs.Cmd_Argv(2));int button=atoi(gEngfuncs.Cmd_Argv(3));
 if(!std::isfinite(x)||!std::isfinite(y))return;
 Move((x-px)*SX(),(y-py)*SY());if(button==1)Key(1,K_MOUSE1);else if(button==0)Key(0,K_MOUSE1);else if(button==2)Key(1,K_MWHEELUP);else if(button==3)Key(1,K_MWHEELDOWN);
}
void Init(){Focus();gEngfuncs.pfnAddCommand("vf_ui_pointer",PointerCommand);}
}

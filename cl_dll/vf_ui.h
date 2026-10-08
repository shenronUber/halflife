// Shared native workshop presentation and pointer routing.
#ifndef VF_UI_H
#define VF_UI_H
namespace vfui {
struct Color { int r,g,b; };
extern const Color bg,panel,edge,muted,white,teal,amber,red;
struct Family { const char* name; const char* role; const char* summary; Color color; };
extern const Family families[6];
float SX(); float SY(); float X(float value); float Y(float value);
void Init(); void Focus(); void Move(float dx,float dy); bool Key(int down,int key);
void Begin(int section); void End();
void Text(float x,float y,const char* text,Color c,float width=0);
void Wrap(float x,float y,const char* text,float width,Color c,int maxLines=3);
void Box(float x,float y,float w,float h,Color c,int alpha=255);
void Frame(float x,float y,float w,float h,Color c);
void Icon(int kind,float x,float y,float size,Color c);
int FamilyId(const char* name);
void Badge(int family,float x,float y,float w=148);
bool Button(float x,float y,float w,float h,const char* text,bool selected=false,bool enabled=true,int icon=-1);
bool Hover(float x,float y,float w,float h);
void Tip(const char* text);
void Viewport(float x,float y,float w,float h);
int Scroll(float x,float y,float w,float h);
Color BudgetColor(int budget);
const char* BudgetTip(int budget);
void Meter(float x,float y,float w,const char* name,int value,int applied,int limit,Color color,int icon=-1);
bool Guide();
void OpenEffects();
}
#endif

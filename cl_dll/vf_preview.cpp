// Textured geometry, projected and depth-sorted in the HUD's orthographic pass.
// Uses GoldSrc TriangleAPI; no browser, screenshots or engine-specific GL hooks.
#include <vector>
#include <map>
#include <string>
#include <algorithm>
#include <cmath>
#include "hud.h"
#include "cl_util.h"
#include "triangleapi.h"
#include "const.h"
#include "vf_preview.h"
#include "vf_engine.h"
#include <string.h>
#undef min
#undef max
namespace {
struct Vertex { float x,y,z,nx,ny,nz,u,v; };
struct Triangle { int group,variant,texture;Vertex v[3]; };
static_assert(sizeof(Triangle)==108,"VF3D binary layout");
struct Texture {HSPRITE sprite;int frame;};
struct Mesh { bool attempted,valid;std::vector<Triangle> triangles;std::vector<Texture> textures; };
struct Face { const Mesh* mesh;int index;float depth; };
struct Part { const char* key;int group;const int* variants; };
std::map<std::string,Mesh> meshes;float yaw=20,zoom=1;
bool Load(Mesh& mesh,const char* key) {
    if(mesh.attempted)return mesh.valid;
    mesh.attempted=true;int size=0;
    char file[96];snprintf(file,sizeof(file),"vf/%s.vfm",key);
    byte* bytes=gEngfuncs.COM_LoadFile(file,5,&size);
    if(!bytes)return false;
    unsigned int header[4];
    if(size<16) {gEngfuncs.COM_FreeFile(bytes);return false;}
    memcpy(header,bytes,16);
    unsigned int textures=header[2],triangles=header[3];
    bool valid=!memcmp(bytes,"VF3D",4)&&header[1]==1&&textures>0&&textures<=32&&triangles>0&&triangles<=24000&&size==16+textures*96+triangles*sizeof(Triangle);
    if(valid) {
        for(unsigned int i=0;i<textures;++i) {
            char path[96];memcpy(path,bytes+16+i*96,96);path[95]=0;
            if(strncmp(path,"sprites/vf_preview/",19)||strstr(path,"..")) {valid=false;break;}
            int frame=0;char* suffix=strchr(path,'#');
            if(suffix){*suffix++=0;if(!*suffix){valid=false;break;}for(char* p=suffix;*p;++p){if(*p<'0'||*p>'9'||frame>64){valid=false;break;}frame=frame*10+*p-'0';}if(!valid||frame>=64){valid=false;break;}}
            HSPRITE sprite=gEngfuncs.pfnSPR_Load(path);if(!sprite){valid=false;break;}
            if(frame>=gEngfuncs.pfnSPR_Frames(sprite)){valid=false;break;}
            Texture t={sprite,frame};mesh.textures.push_back(t);
        }
    }
    if(valid) {
        mesh.triangles.resize(triangles);memcpy(&mesh.triangles[0],bytes+16+textures*96,triangles*sizeof(Triangle));
        for(unsigned int i=0;i<triangles&&valid;++i) {
            const Triangle& t=mesh.triangles[i];
            if(t.texture<0||t.texture>=(int)textures||t.group< -1||t.group>4||t.variant<0||t.variant>2) valid=false;
            for(int j=0;j<3;++j) {
                const float* p=&t.v[j].x;
                for(int n=0;n<8;++n) if(!std::isfinite(p[n])||fabs(p[n])>10000)valid=false;
            }
        }
    }
    gEngfuncs.COM_FreeFile(bytes);mesh.valid=valid;
    if(!valid){mesh.triangles.clear();mesh.textures.clear();}
    return valid;
}
void Project(const Vertex& v,bool weapon,float c,float s,float& px,float& py,float& depth) {
    float a=weapon?v.y+14:v.x,b=weapon?v.x+3.63f:v.y,z=weapon?v.z+6:v.z;
    px=a*c-b*s;float d=a*s+b*c;
    py=z*.985f-d*.174f;depth=d*.985f+z*.174f;
}
bool Draw(const Part* parts,int count,bool weapon,bool fit,float x,float y,float w,float h) {
    float rad=yaw*.01745329252f,c=cosf(rad),s=sinf(rad);
    float scale=(weapon?6.8f:4.6f)*zoom*std::min(w/357.f,h/390.f);
    float minX=10000,maxX=-10000,minY=10000,maxY=-10000;
    std::vector<Face> faces;
    for(int p=0;p<count;++p) {
      Mesh& mesh=meshes[parts[p].key];if(!Load(mesh,parts[p].key))return false;
      for(size_t i=0;i<mesh.triangles.size();++i) {
        const Triangle& t=mesh.triangles[i];
        if(parts[p].group>=0&&t.group!=parts[p].group)continue;
        if(parts[p].variants&&t.group>=0&&(t.group>2||t.variant!=parts[p].variants[t.group]))continue;
        float depth=0;
        for(int j=0;j<3;++j){float px,py,d;Project(t.v[j],weapon,c,s,px,py,d);depth+=d;
            minX=std::min(minX,px);maxX=std::max(maxX,px);minY=std::min(minY,py);maxY=std::max(maxY,py);}
        Face face={&mesh,(int)i,depth};faces.push_back(face);
      }
    }
    std::sort(faces.begin(),faces.end(),[](const Face& a,const Face& b){return a.depth>b.depth;});
    if(faces.empty())return false;
    float fitted=std::min(w*.90f/std::max(1.f,maxX-minX),h*.90f/std::max(1.f,maxY-minY));
    scale=fit?fitted*std::min(zoom,1.f):std::min(scale,fitted);
    float centerX=(minX+maxX)*.5f,centerY=(minY+maxY)*.5f;
    triangleapi_t* api=gEngfuncs.pTriAPI;
    api->RenderMode(kRenderNormal);api->CullFace(TRI_NONE);
    int texture=-1;const Mesh* bound=NULL;bool begun=false;
    for(size_t i=0;i<faces.size();++i) {
        const Mesh& mesh=*faces[i].mesh;const Triangle& t=mesh.triangles[faces[i].index];
        if(&mesh!=bound||t.texture!=texture) {
            if(begun)api->End();
            texture=t.texture;bound=&mesh;
            const Texture& tex=mesh.textures[texture];api->SpriteTexture(const_cast<model_s*>(gEngfuncs.GetSpritePointer(tex.sprite)),tex.frame);
            api->Begin(TRI_TRIANGLES);begun=true;
        }
        for(int j=0;j<3;++j) {
            const Vertex& v=t.v[j];float px,py,d;Project(v,weapon,c,s,px,py,d);
            float na=weapon?v.ny:v.nx,nb=weapon?v.nx:v.ny;
            float nx=na*c-nb*s,ny=na*s+nb*c;
            float light=.8f+.2f*std::max(0.f,-nx*.3f-ny*.6f+v.nz*.74f);
            api->Color4f(light,light,light,1);api->TexCoord2f(v.u,v.v);
            api->Vertex3f(x+w*.5f+(px-centerX)*scale,y+h*.5f-(py-centerY)*scale,0);
        }
    }
    if(begun)api->End();api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
    return true;
}
}
float VF_PreviewYaw(){return yaw;}
float VF_PreviewZoomValue(){return zoom;}
void VF_PreviewReset() {meshes.clear();yaw=20;zoom=1;}
void VF_PreviewRotate(float degrees) {yaw=fmodf(yaw+degrees,360.f);}
void VF_PreviewZoom(float amount) {zoom=std::max(.4f,std::min(1.15f,zoom+amount));}
bool VF_PreviewDraw(bool weapon,const int variants[3],float x,float y,float w,float h) {
    if(VF_EngineAvailable())return VF_EnginePreviewModel(weapon?"models/v_9mmar.mdl":"models/vf_operator.mdl",weapon?variants[0]+2*variants[1]:variants[0]+3*variants[1]+9*variants[2],weapon,yaw,zoom,x,y,w,h);
    Part p={weapon?"rifle":"operator",-1,variants};return Draw(&p,1,weapon,false,x,y,w,h);
}
bool VF_PreviewSkins(const char* keys[5],int isolate,float x,float y,float w,float h) {
    if(VF_EngineAvailable())return VF_EnginePreviewSkins(keys,isolate,yaw,zoom,x,y,w,h);
    Part parts[5];int n=0;for(int z=0;z<5;++z)if(isolate<0||z==isolate){parts[n].key=keys[z];parts[n].group=z;parts[n++].variants=NULL;}
    return Draw(parts,n,false,true,x,y,w,h);
}
bool VF_PreviewAsset(const char* key,float x,float y,float w,float h) {
    if(VF_EngineAvailable())return VF_EnginePreviewAsset(key,yaw,zoom,x,y,w,h);
    Part p={key,-1,NULL};return Draw(&p,1,true,true,x,y,w,h);
}
bool VF_PreviewValidateAsset(const char* key) {return Load(meshes[key],key);}
bool VF_PreviewModules(float x,float y,float w,float h){return VF_EnginePreviewModules(yaw,zoom,x,y,w,h);}

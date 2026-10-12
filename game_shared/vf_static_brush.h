/* Immobile BSP candidates still require GoldSrc MOVETYPE_PUSH. Controller
   bytes are already replicated for ordinary entities and available in both
   movement DLLs. Only entities that never translate/rotate may use this tag. */
#ifndef VF_STATIC_BRUSH_H
#define VF_STATIC_BRUSH_H
#define VF_STATIC_BRUSH_TAG_0 86
#define VF_STATIC_BRUSH_TAG_1 70
#define VF_STATIC_BRUSH_TAG_2 83
#define VF_STATIC_BRUSH_TAG_3 1
static int VF_StaticBrush(int movetype,int solid,const unsigned char* controller) {
 return movetype==MOVETYPE_PUSH&&solid==SOLID_BSP&&controller&&
 controller[0]==VF_STATIC_BRUSH_TAG_0&&controller[1]==VF_STATIC_BRUSH_TAG_1&&
 controller[2]==VF_STATIC_BRUSH_TAG_2&&controller[3]==VF_STATIC_BRUSH_TAG_3;
}
#endif

// Generated from measured GIGN cut boundaries by build_deaths.py.
#ifndef VF_WOUND_CATALOG_H
#define VF_WOUND_CATALOG_H
namespace vfwound {
struct Cut { int bone; float offset[3], normal[3]; };
static const Cut Cuts[]={
{12,{3.81157627f,0.76587668f,0.33112985f},{0.99983297f,0.01827668f,-0.00000100f}}, // neck
{15,{1.90000050f,0.28535398f,0.52328322f},{1.00000000f,-0.00000000f,-0.00000020f}}, // arm_left
{22,{1.90000072f,0.27645317f,-0.50153868f},{1.00000000f,0.00000000f,0.00000020f}}, // arm_right
{2,{6.99385522f,0.77009907f,0.85193032f},{0.98663703f,-0.08453574f,0.13928774f}}, // thigh_left
{5,{7.00546315f,0.76742037f,-0.76815913f},{0.98663660f,-0.08453597f,-0.13929064f}}, // thigh_right
};
}
#endif

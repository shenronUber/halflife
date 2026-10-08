// Vector Fields: engine-independent equipment definitions and validation.
#ifndef VF_LOADOUT_H
#define VF_LOADOUT_H
#include <stddef.h>
namespace vf {
enum { BudgetCount=6, GearSlots=9, SlotCount=21, MaxItems=192, Protocol=3 };
extern const char* const SlotKeys[SlotCount];
extern const char* const SlotNames[SlotCount];
extern const char* const BudgetCodes[BudgetCount];
extern const char* const BudgetNames[BudgetCount];
struct Item {
    int slot, tier, cost[BudgetCount], visual;
    char id[40], name[48], category[24], flavor[32], description[180];
};
struct Catalog {
    Item items[MaxItems]; // index zero means no item
    int count, limits[BudgetCount];
    unsigned int fingerprint;
    bool valid;
    char error[128];
};
enum Result { Accepted=0, BadCatalog=1, BadItem=2, WrongSlot=3, OverBudget=4, BadRequest=5 };
bool ParseCatalog(const char* data, size_t size, Catalog& out);
bool ParseUnsigned(const char* text, unsigned int& value);
Result Evaluate(const Catalog& catalog, const int selection[SlotCount], int totals[BudgetCount]);
void Defaults(const Catalog& catalog, int selection[SlotCount]);
int Cycle(const Catalog& catalog, int slot, int current, int direction);
int Visual(const Catalog& catalog, const int selection[SlotCount], int slot);
int OperatorBody(const Catalog& catalog, const int selection[SlotCount]);
int WeaponBody(const Catalog& catalog, const int selection[SlotCount]);
}
#endif

/*
 * Measurement harness for the unmodified Valve SDK movement object files.
 * This is a local SDK diagnostic, not a portable/relicensed movement module.
 * The linked Valve code retains its original license. No engine is embedded.
 * Parameters below are explicit test inputs, not claims about every HL release.
 * No map, complete movement frame, renderer or network is exercised here.
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "mathlib.h"
#include "const.h"
#include "pm_defs.h"
#include "pm_movevars.h"

extern playermove_t *pmove;
void PM_Accelerate(vec3_t wishdir, float wishspeed, float accel);
void PM_AirAccelerate(vec3_t wishdir, float wishspeed, float accel);
void PM_Friction(void);
void PM_PreventMegaBunnyJumping(void);
int PM_ClipVelocity(vec3_t in, vec3_t normal, vec3_t out, float overbounce);

static playermove_t player;
static movevars_t variables;
static int failures;
static int checks;

/* Only the ground-friction test uses this controlled, non-edge surface. */
static pmtrace_t ground_trace(float *start, float *end, int flags, int ignored)
{
    pmtrace_t trace;
    (void)start; (void)end; (void)flags; (void)ignored;
    memset(&trace, 0, sizeof(trace));
    trace.fraction = 0.5f;
    trace.plane.normal[2] = 1.0f;
    return trace;
}

static void reset_player(void)
{
    memset(&player, 0, sizeof(player));
    memset(&variables, 0, sizeof(variables));
    pmove = &player;
    player.movevars = &variables;
    player.frametime = 0.01f;
    player.friction = 1.0f;
    player.maxspeed = 320.0f;
    player.onground = 0;
    player.PM_PlayerTrace = ground_trace;
    variables.friction = 4.0f;
    variables.edgefriction = 2.0f;
    variables.stopspeed = 100.0f;
}

static void expect_near(const char *name, float actual, float expected)
{
    int passed = fabs(actual - expected) < 0.001;
    ++checks;
    if (!passed) ++failures;
    printf("%s,%s,%.6f,%.6f\n", name, passed ? "PASS" : "FAIL", actual, expected);
}

int main(void)
{
    vec3_t forward = {1.0f, 0.0f, 0.0f};
    vec3_t sideways = {0.0f, 1.0f, 0.0f};
    vec3_t velocity = {100.0f, 50.0f, 0.0f};
    vec3_t wall_normal = {-1.0f, 0.0f, 0.0f};
    vec3_t clipped;
    int i;
    printf("scenario,result,actual,expected\n");

    reset_player();
    PM_Accelerate(forward, 320.0f, 10.0f);
    expect_near("ground_acceleration_10ms_no_friction", player.velocity[0], 32.0f);
    for (i = 1; i < 10; ++i) PM_Accelerate(forward, 320.0f, 10.0f);
    expect_near("ground_acceleration_100ms_no_friction", player.velocity[0], 320.0f);
    PM_Accelerate(forward, 320.0f, 10.0f);
    expect_near("ground_acceleration_cap", player.velocity[0], 320.0f);

    reset_player();
    player.velocity[0] = 320.0f;
    PM_Friction();
    expect_near("ground_friction_10ms", player.velocity[0], 307.2f);
    player.onground = -1;
    PM_Friction();
    expect_near("air_has_no_ground_friction", player.velocity[0], 307.2f);

    reset_player();
    player.onground = -1;
    player.velocity[0] = 320.0f;
    PM_AirAccelerate(sideways, 320.0f, 10.0f);
    expect_near("air_perpendicular_input_preserves_forward_speed", player.velocity[0], 320.0f);
    expect_near("air_perpendicular_input_adds_velocity", player.velocity[1], 30.0f);
    PM_AirAccelerate(sideways, 320.0f, 10.0f);
    expect_near("air_cap_is_on_projection_not_total_speed", player.velocity[1], 30.0f);

    reset_player();
    player.dead = 1;
    PM_Accelerate(forward, 320.0f, 10.0f);
    expect_near("dead_player_does_not_accelerate", player.velocity[0], 0.0f);

    reset_player();
    player.velocity[0] = 540.0f;
    PM_PreventMegaBunnyJumping();
    expect_near("speed_below_bunny_threshold_is_preserved", player.velocity[0], 540.0f);
    player.velocity[0] = 600.0f;
    PM_PreventMegaBunnyJumping();
    expect_near("speed_above_bunny_threshold_is_reduced", player.velocity[0], 353.6f);

    PM_ClipVelocity(velocity, wall_normal, clipped, 1.0f);
    expect_near("wall_clip_removes_normal_velocity", clipped[0], 0.0f);
    expect_near("wall_clip_preserves_tangential_velocity", clipped[1], 50.0f);

    fprintf(stderr, "%d/%d checks passed; isolated functions, not a full game test.\n", checks - failures, checks);
    return failures ? 1 : 0;
}

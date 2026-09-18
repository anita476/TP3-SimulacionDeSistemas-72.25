#include "collision.hpp"

#include <algorithm>
#include <cmath>

namespace
{
    double axis_wall_time(double pos, double vel, double r, double length) {
        if (vel > 0.0)
            return std::max(0.0, (length - r - pos) / vel);
        if (vel < 0.0)
            return std::max(0.0, (r - pos)/vel);
        return kNoCollision;
    }
} // namespace

double wall_time_x(const Particle &p, double L) {
    return axis_wall_time(p.x, p.vx, p.r, L);
}

double wall_time_y(const Particle &p, double W) {
    return axis_wall_time(p.y, p.vy, p.r, W);
}

double pair_time(const Particle &a, const Particle &b) {
    const double dx = b.x - a.x, dy = b.y - a.y;
    const double dvx = b.vx - a.vx, dvy = b.vy - a.vy;
    const double sigma = a.r + b.r;
    const double dv_dr = dvx * dx + dvy * dy;

    if (dv_dr >= 0.0) return kNoCollision; // se estan alejando

    const double dv_dv = dvx * dvx + dvy * dvy;
    const double dr_dr = dx * dx + dy * dy;
    const double d = dv_dr * dv_dr - dv_dv * (dr_dr - sigma * sigma);

    if (d < 0.0) return kNoCollision; // pasa por afuera

    return std::max(0.0, -(dv_dr + std::sqrt(d)) / dv_dv);
}

double obstacle_time(const Particle &p, const Obstacle &o) {
    const Particle rest{o.kx, o.ky, o.Rk, 0.0, 0.0};
    return pair_time(p, rest);
}

void bounce_x(Particle &p) {p.vx = -p.vx;}
void bounce_y(Particle &p) {p.vy = -p.vy;}
void collide_pair(Particle &, Particle &) {}
void collide_obstacle(Particle &, const Obstacle &) {}
#pragma once

#include "particle.hpp"

// Two overlap predicates:
//  * within_cutoff (TP1)
//  * discs_overlap (TP3)

// Minimum-image separation on one axis when periodic; raw difference otherwise.
inline double axis_separation(double d, double L, bool periodic) {
  if (!periodic)
    return d;
  const double half_L = 0.5 * L;
  if (d > half_L)
    return d - L;
  if (d < -half_L)
    return d + L;
  return d;
}

// Border-to-border distance < cutoff (centre-to-centre when r = 0).
inline bool within_cutoff(const Particle &a, const Particle &b, double cutoff,
                          double L, double W, bool periodic) {
  const double dx = axis_separation(a.x - b.x, L, periodic);
  const double dy = axis_separation(a.y - b.y, W, periodic);
  const double reach = cutoff + a.r + b.r;
  return dx * dx + dy * dy < reach * reach;
}

inline bool within_cutoff(const Particle &a, const Particle &b, double cutoff,
                          double L, bool periodic) {
  return within_cutoff(a, b, cutoff, L, L, periodic);
}

// d = |centre separation| and sum_radii = R_i + R_j:
//   d < sum_radii  overlapping
//   d = sum_radii  touching, not overlapping
//   d > sum_radii  separated
// Compared on squares (no sqrt)
inline bool discs_overlap(double dx, double dy, double sum_radii) {
  return dx * dx + dy * dy < sum_radii * sum_radii;
}

// If disc of radius R is INSIDE table [0,L]x[0,W]: centre lies in
// [R, L-R]x[R, W-R]. A disc touching a wall is inside.
inline bool disc_inside(double x, double y, double R, double L, double W) {
  return x >= R && x <= L - R && y >= R && y <= W - R;
}

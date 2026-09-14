#pragma once

#include "particle.hpp"

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
                          double L, bool periodic) {
  const double dx = axis_separation(a.x - b.x, L, periodic);
  const double dy = axis_separation(a.y - b.y, L, periodic);
  const double reach = cutoff + a.r + b.r;
  return dx * dx + dy * dy < reach * reach;
}

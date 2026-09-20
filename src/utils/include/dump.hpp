#pragma once

#include <ostream>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

inline void write_dump_header(std::ostream &out, double L, double W, double d,
                              double r, double m, int n,
                              const std::vector<Obstacle> &obstacles) {
  out << "L " << L << '\n';
  out << "W " << W << '\n';
  out << "d " << d << '\n';
  out << "r " << r << '\n';
  out << "m " << m << '\n';
  out << "N " << n << '\n';
  for (const Obstacle &o : obstacles)
    out << "O " << o.kx << ' ' << o.ky << ' ' << o.Rk << '\n';
}

inline void write_dump_frame(std::ostream &out, double t,
                             const std::vector<Particle> &particles) {
  int ng = 0;
  for (const Particle &p : particles)
    ng += p.used ? 1 : 0;
  out << "t " << t << " Ng " << ng << '\n';
  for (const Particle &p : particles)
    out << p.x << ' ' << p.y << ' ' << p.vx << ' ' << p.vy << ' ' << p.used
        << '\n';
}

#pragma once

#include <limits>

#include "obstacle.hpp"
#include "particle.hpp"

// Infinito para expresar NO COLLISION
constexpr double kNoCollision = std::numeric_limits<double>::infinity();

// --- Tiempos de choque (segun sugerencia de docs/Molecular Dynamics Simulation of Hard Spheres.pdf) --
// Choque con pared: x = r (vx < 0) o x = L-r (vx > 0)
double wall_time_x(const Particle &p, double L);
double wall_time_y(const Particle &p, double W);
// Primer choque entre dos particulas (la menor raiz de la cuadratica)
double pair_time(const Particle &a, const Particle &b);
// Choque contra obstaculo
double obstacle_time(const Particle &p, const Obstacle &o);

// -- Operadores de colision -> velocidad post-choque --
// Pared:
void bounce_x(Particle &p); // pared vertical: (vx, vy) -> (-vx, vy)
void bounce_y(Particle &p); // pared horizontal: (vx, vy) -> (vx, -vy)
// Entre particulas:
void collide_pair(Particle &a, Particle &b);
// Contra obstaculo:
void collide_obstacle(Particle &p, const Obstacle &o);

#include "check.hpp"
#include "collision.hpp"

#include <cmath>

int main() {
  const double L = 1.20, W = 0.68, r = 0.0175;

  // Pared derecha: el centro llega a L - r, no a L.
  {
    Particle p{0.5, 0.34, r, 2.0, 0.3};
    CHECK_NEAR(wall_time_x(p, L), (L - r - 0.5) / 2.0, 1e-12);
  }
  // Pared izquierda: numerador y denominador negativos, cociente positivo.
  {
    Particle p{0.5, 0.34, r, -2.0, 0.3};
    CHECK_NEAR(wall_time_x(p, L), (r - 0.5) / -2.0, 1e-12);
    CHECK(wall_time_x(p, L) > 0.0);
  }
  // vx = 0 nunca toca una pared vertical; la horizontal sí.
  {
    Particle p{0.5, 0.34, r, 0.0, 1.0};
    CHECK(wall_time_x(p, L) == kNoCollision);
    CHECK_NEAR(wall_time_y(p, W), (W - r - 0.34) / 1.0, 1e-12);
  }
  // Ya apoyada contra la pared y yendo hacia ella: t_c = 0, nunca negativo.
  {
    Particle p{L - r + 1e-15, 0.34, r, 1.0, 0.0};
    CHECK(wall_time_x(p, L) == 0.0);
  }
  // Choque frontal: se tocan cuando la distancia entre centros vale 2r.
  {
    Particle a{0.2, 0.3, r, 1.0, 0.0};
    Particle b{0.6, 0.3, r, -1.0, 0.0};
    CHECK_NEAR(pair_time(a, b), (0.4 - 2 * r) / 2.0, 1e-12);
    CHECK_NEAR(pair_time(b, a), pair_time(a, b), 1e-12);
  }
  // Alejándose (Δv·Δr >= 0): infinito.
  {
    Particle a{0.2, 0.3, r, -1.0, 0.0};
    Particle b{0.6, 0.3, r, 1.0, 0.0};
    CHECK(pair_time(a, b) == kNoCollision);
  }
  // Se cruzan por afuera (d < 0): infinito.
  {
    Particle a{0.2, 0.3, r, 1.0, 0.0};
    Particle b{0.6, 0.3 + 3 * r, r, -1.0, 0.0};
    CHECK(pair_time(a, b) == kNoCollision);
  }
  // Obstáculo: una partícula quieta de radio Rk.
  {
    Particle p{0.2, 0.34, r, 1.0, 0.0};
    Obstacle o{0.6, 0.34, 0.05};
    CHECK_NEAR(obstacle_time(p, o), 0.4 - 0.05 - r, 1e-12);
  }


    const double m = 0.025;

  // Pared vertical: se invierte vx, vy queda igual (y viceversa).
  {
    Particle p{L - r, 0.3, r, 1.0, 0.4};
    bounce_x(p);
    CHECK_NEAR(p.vx, -1.0, 1e-12);
    CHECK_NEAR(p.vy, 0.4, 1e-12);
  }
  {
    Particle p{0.3, r, r, 1.0, -0.4};
    bounce_y(p);
    CHECK_NEAR(p.vx, 1.0, 1e-12);
    CHECK_NEAR(p.vy, 0.4, 1e-12);
  }
  // Péndulo de Newton: masas iguales y choque frontal intercambian velocidades.
  {
    Particle a{0.3, 0.3, r, 1.0, 0.0, m};
    Particle b{0.3 + 2 * r, 0.3, r, 0.0, 0.0, m};
    collide_pair(a, b);
    CHECK_NEAR(a.vx, 0.0, 1e-12);
    CHECK_NEAR(a.vy, 0.0, 1e-12);
    CHECK_NEAR(b.vx, 1.0, 1e-12);
    CHECK_NEAR(b.vy, 0.0, 1e-12);
  }
  // Oblicuo con masas distintas: conserva momento y energía, y quedan alejándose.
  {
    const double c = std::cos(0.7), s = std::sin(0.7);
    Particle a{0.3, 0.3, r, 1.0, 0.2, 0.025};
    Particle b{0.3 + 2 * r * c, 0.3 + 2 * r * s, r, -0.5, 0.1, 0.05};
    const double px0 = a.m * a.vx + b.m * b.vx;
    const double py0 = a.m * a.vy + b.m * b.vy;
    const double e0 = 0.5 * a.m * (a.vx * a.vx + a.vy * a.vy) +
                      0.5 * b.m * (b.vx * b.vx + b.vy * b.vy);
    collide_pair(a, b);
    const double px1 = a.m * a.vx + b.m * b.vx;
    const double py1 = a.m * a.vy + b.m * b.vy;
    const double e1 = 0.5 * a.m * (a.vx * a.vx + a.vy * a.vy) +
                      0.5 * b.m * (b.vx * b.vx + b.vy * b.vy);
    CHECK_NEAR(px1, px0, 1e-12);
    CHECK_NEAR(py1, py0, 1e-12);
    CHECK_NEAR(e1, e0, 1e-12);
    const double dv_dr = (b.vx - a.vx) * (b.x - a.x) + (b.vy - a.vy) * (b.y - a.y);
    CHECK(dv_dr > 0.0); // Sección 14, trampa 1: después del choque se separan
    CHECK(pair_time(a, b) == kNoCollision);
  }
  // Obstáculo de frente: reflexión especular, la tangencial no cambia.
  {
    Obstacle o{0.6, 0.34, 0.05};
    Particle p{0.6 - 0.05 - r, 0.34, r, 1.0, 0.3};
    collide_obstacle(p, o);
    CHECK_NEAR(p.vx, -1.0, 1e-12);
    CHECK_NEAR(p.vy, 0.3, 1e-12);
  }
  // Obstáculo con normal a 45°: (1, 0) -> (0, -1), |v| se conserva.
  {
    Obstacle o{0.6, 0.34, 0.05};
    const double s = (0.05 + r) / std::sqrt(2.0);
    Particle p{0.6 - s, 0.34 - s, r, 1.0, 0.0};
    collide_obstacle(p, o);
    CHECK_NEAR(p.vx, 0.0, 1e-12);
    CHECK_NEAR(p.vy, -1.0, 1e-12);
  }
  return finish();
}

#include "check.hpp"
#include "collision.hpp"

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
  return finish();
}

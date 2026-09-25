#include <cmath>
#include <stdexcept>

#include "check.hpp"
#include "geometry.hpp"
#include "generator.hpp"

int main() {
  const GeneratorConfig base; // defaults = parámetros del TP
  const double L = base.L, W = base.W, r = base.r;
  constexpr double kPi = 3.14159265358979323846;

  // Sin semilla fija por defecto: 0 significa auto/random.
  CHECK(base.seed == 0);

  // N = 100 en la mesa vacía: dentro de la caja, sin solapamiento, |v| = v0,
  {
    GeneratorConfig cfg = base;
    cfg.seed = 42;
    GeneratorStats stats;
    const std::vector<Particle> ps = generate_particles(cfg, &stats);
    CHECK(ps.size() == 100);
    CHECK(stats.attempts >= 100);
    CHECK(stats.mx > 1 && stats.my > 1);
    CHECK_NEAR(stats.packing_fraction, 100 * kPi * r * r / (L * W), 1e-12);
    for (const Particle &p : ps) {
      CHECK(p.x >= r && p.x <= L - r);
      CHECK(p.y >= r && p.y <= W - r);
      CHECK_NEAR(std::sqrt(p.vx * p.vx + p.vy * p.vy), cfg.v0, 1e-12);
      CHECK_NEAR(p.r, r, 1e-12);
      CHECK_NEAR(p.m, cfg.m, 1e-12);
      CHECK(p.used == 0);
      CHECK(p.collisions == 0);
    }
    CHECK(find_overlap(ps, cfg.obstacles, L, W) == -1);
  }
  // Con un obstáculo grande: ninguna partícula lo pisa
  {
    GeneratorConfig cfg = base;
    cfg.seed = 7;
    cfg.obstacles = {{0.60, 0.34, 0.10}};
    GeneratorStats stats;
    const std::vector<Particle> ps = generate_particles(cfg, &stats);
    for (const Particle &p : ps)
      CHECK(!discs_overlap(p.x - 0.60, p.y - 0.34, r + 0.10));
    CHECK(find_overlap(ps, cfg.obstacles, L, W) == -1);
    CHECK_NEAR(stats.packing_fraction,
               (100 * kPi * r * r + kPi * 0.10 * 0.10) / (L * W), 1e-12);
  }
  // Misma semilla, mismas condiciones iniciales (semilla registrada por corrida).
  {
    GeneratorConfig cfg = base;
    cfg.N = 20;
    cfg.seed = 3;
    const auto a = generate_particles(cfg);
    const auto b = generate_particles(cfg);
    for (std::size_t i = 0; i < a.size(); ++i) {
      CHECK(a[i].x == b[i].x && a[i].y == b[i].y);
      CHECK(a[i].vx == b[i].vx && a[i].vy == b[i].vy);
    }
  }
  // find_overlap es el chequeo de fuerza bruta: devuelve el índice de la
  // primera partícula en falta (-1 si no hay ninguna). Tres faltas posibles:
  {
    // dos partículas solapadas (centros a distancia r < 2r)
    const std::vector<Particle> pair{Particle{0.3, 0.3, r, 0.0, 0.0},
                                     Particle{0.3 + r, 0.3, r, 0.0, 0.0}};
    CHECK(find_overlap(pair, {}, L, W) == 0);
    // una partícula encima de un obstáculo
    const std::vector<Particle> on_obstacle{Particle{0.60, 0.34, r, 0.0, 0.0}};
    CHECK(find_overlap(on_obstacle, {{0.60, 0.34, 0.10}}, L, W) == 0);
    // una partícula que se sale de la mesa (x = 0.01 < r)
    const std::vector<Particle> outside{Particle{0.01, 0.3, r, 0.0, 0.0}};
    CHECK(find_overlap(outside, {}, L, W) == 0);
  }
  // Demasiado denso: aborta con excepción en vez de colgarse
  {
    GeneratorConfig cfg = base;
    cfg.r = 0.06;
    cfg.max_attempts = 1000;
    bool threw = false;
    try {
      generate_particles(cfg);
    } catch (const std::runtime_error &) {
      threw = true;
    }
    CHECK(threw);
  }
  // Parámetros sin sentido: invalid_argument antes de sortear nada
  {
    GeneratorConfig cfg = base;
    cfg.N = 0;
    bool threw = false;
    try {
      generate_particles(cfg);
    } catch (const std::invalid_argument &) {
      threw = true;
    }
    CHECK(threw);
  }
  return finish();
}

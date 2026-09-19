#include <cmath>
#include <random>
#include <sstream>
#include <string>

#include "check.hpp"
#include "geometry.hpp"
#include "generator.hpp"
#include "simulation.hpp"

// Invariantes tras una corrida se verifican con 1e-9 m de margen en la
// aserción: ~1e4 avances x += v dt acumulan redondeo, y un par que acaba de
// chocar queda a sigma ± unos ulp. Es un margen del test, no del motor.

static int count_frames(const std::string &dump) {
  int frames = 0;
  std::istringstream in(dump);
  for (std::string line; std::getline(in, line);)
    if (line.rfind("t ", 0) == 0)
      ++frames;
  return frames;
}

int main() {
  const double L = 1.20, W = 0.68, d = 0.20, r = 0.0175, m = 0.025;

  // Una partícula apuntando al arco derecho: gol en t = (L - r - x) / vx,
  // pasa a usada, t90 (N = 1 -> 1 gol) es ese mismo tiempo de evento, y
  // el reloj queda en el último evento, nunca en tmax.
  {
    std::vector<Particle> ps{Particle{0.5, 0.34, r, 1.0, 0.0, m}};
    Simulation sim(SimParams{L, W, d, 1.0, 0}, ps, {});
    std::ostringstream dump;
    sim.run(&dump);
    const double t_goal = (L - r - 0.5) / 1.0;
    CHECK_NEAR(sim.time(), t_goal, 1e-12);
    CHECK(sim.events() == 1);
    CHECK(sim.goals() == 1);
    CHECK_NEAR(sim.t90(), t_goal, 1e-12);
    CHECK(sim.particles()[0].used == 1);
    CHECK_NEAR(sim.particles()[0].vx, -1.0, 1e-12);
    CHECK_NEAR(sim.particles()[0].x, L - r, 1e-12);
    // Dump: encabezado, cuadro inicial y cuadro del gol (k = 0 -> solo goles).
    CHECK(dump.str().rfind("L 1.2\n", 0) == 0);
    CHECK(count_frames(dump.str()) == 2);
  }
  // Fuera del arco: rebota, no hay gol, y una usada no vuelve a sumar.
  {
    std::vector<Particle> ps{Particle{0.5, 0.10, r, 1.0, 0.0, m}};
    Simulation sim(SimParams{L, W, d, 1.0, 0}, ps, {});
    sim.run(nullptr);
    CHECK(sim.goals() == 0);
    CHECK(sim.t90() < 0.0);
    CHECK_NEAR(sim.particles()[0].vx, -1.0, 1e-12);
  }
  {
    std::vector<Particle> ps{Particle{0.5, 0.34, r, 1.0, 0.0, m}};
    ps[0].used = 1;
    Simulation sim(SimParams{L, W, d, 1.0, 0}, ps, {});
    sim.run(nullptr);
    CHECK(sim.goals() == 0);
  }
  // Obstáculo en el camino: choca contra él antes que contra la pared.
  {
    std::vector<Particle> ps{Particle{0.5, 0.34, r, 1.0, 0.0, m}};
    const std::vector<Obstacle> obs{{0.9, 0.34, 0.05}};
    Simulation sim(SimParams{L, W, d, 0.5, 0}, ps, obs);
    sim.run(nullptr);
    CHECK_NEAR(sim.time(), 0.9 - 0.05 - r - 0.5, 1e-12);
    CHECK(sim.goals() == 0);
    CHECK_NEAR(sim.particles()[0].vx, -1.0, 1e-12);
  }
  // Choque frontal de masas iguales: intercambian velocidades.
  {
    std::vector<Particle> ps{Particle{0.4, 0.34, r, 1.0, 0.0, m},
                             Particle{0.8, 0.34, r, -1.0, 0.0, m}};
    Simulation sim(SimParams{L, W, d, 0.2, 0}, ps, {});
    sim.run(nullptr);
    CHECK_NEAR(sim.time(), (0.4 - 2 * r) / 2.0, 1e-12);
    CHECK(sim.events() == 1);
    CHECK_NEAR(sim.particles()[0].vx, -1.0, 1e-12);
    CHECK_NEAR(sim.particles()[1].vx, 1.0, 1e-12);
  }
  // Choque oblicuo con una en reposo (dataset de COS 226): la que estaba
  // quieta sale exactamente sobre la línea de centros; momento y energía
  // se conservan.
  {
    std::vector<Particle> ps{Particle{0.3, 0.30, r, 1.0, 0.0, m},
                             Particle{0.6, 0.30 + r, r, 0.0, 0.0, m}};
    Simulation sim(SimParams{L, W, d, 0.28, 0}, ps, {});
    sim.run(nullptr);
    // Contacto cuando (0.3 - t)^2 + r^2 = (2r)^2  ->  t = 0.3 - sqrt(3) r
    CHECK_NEAR(sim.time(), 0.3 - std::sqrt(3.0) * r, 1e-12);
    const Particle &a = sim.particles()[0], &b = sim.particles()[1];
    CHECK_NEAR(a.vx + b.vx, 1.0, 1e-12);
    CHECK_NEAR(a.vy + b.vy, 0.0, 1e-12);
    CHECK_NEAR(a.vx * a.vx + a.vy * a.vy + b.vx * b.vx + b.vy * b.vy, 1.0, 1e-12);
    // Línea de centros en el contacto: (sqrt(3) r, r)  ->  vy/vx = 1/sqrt(3)
    CHECK(b.vx > 0.0);
    CHECK_NEAR(b.vy / b.vx, 1.0 / std::sqrt(3.0), 1e-9);
  }
  // N = 50 al azar con un obstáculo, 5 s: energía plana, nadie sale de la
  // caja, nadie se solapa, y el dump cada k eventos tiene 1 + events/k
  // cuadros más los goles.
  {
    GeneratorConfig cfg;
    cfg.N = 50;
    cfg.seed = 11;
    cfg.obstacles = {{0.60, 0.34, 0.05}};
    const std::vector<Obstacle> obs = cfg.obstacles;
    std::vector<Particle> ps = generate_particles(cfg);
    const int k = 25;
    Simulation sim(SimParams{L, W, d, 5.0, k}, ps, obs);
    const double e0 = sim.kinetic_energy();
    std::ostringstream dump;
    sim.run(&dump);
    CHECK(sim.events() > 100);
    CHECK(sim.time() <= 5.0);
    CHECK_NEAR(sim.kinetic_energy(), e0, 1e-9 * e0);
    const std::vector<Particle> &q = sim.particles();
    for (const Particle &p : q) {
      CHECK(p.x >= r - 1e-9 && p.x <= L - r + 1e-9);
      CHECK(p.y >= r - 1e-9 && p.y <= W - r + 1e-9);
      CHECK(!discs_overlap(p.x - 0.60, p.y - 0.34, r + 0.05 - 1e-9));
    }
    for (std::size_t i = 0; i < q.size(); ++i)
      for (std::size_t j = i + 1; j < q.size(); ++j)
        CHECK(!discs_overlap(q[i].x - q[j].x, q[i].y - q[j].y, 2 * r - 1e-9));
    CHECK(count_frames(dump.str()) >= 1 + static_cast<int>(sim.events() / k));
    CHECK(count_frames(dump.str()) <= 1 + static_cast<int>(sim.events() / k) + sim.goals());
    CHECK(sim.goals() >= 0 && sim.goals() <= 50);
  }
  return finish();
}

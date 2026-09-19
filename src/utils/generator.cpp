#include "generator.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <stdexcept>

#include "cell_grid.hpp"
#include "geometry.hpp"
#include "neighbours.hpp"

namespace
{
constexpr double kPi = 3.14159265358979323846;

void validate(const GeneratorConfig &cfg) {
    if (cfg.N < 1) throw std::invalid_argument("N debe ser >= 1");
    if (cfg.L <= 0.0 || cfg.W <= 0.0) throw std::invalid_argument("L y W deben ser positivos");
    if (cfg.r <= 0.0 || cfg.m <= 0.0) throw std::invalid_argument("r y m deben ser positivos");
    if (cfg.max_attempts < 1) throw std::invalid_argument("max_attempts debe ser >= 1");
    if (cfg.L <= 2.0 * cfg.r || cfg.W <= 2.0 * cfg.r) throw std::invalid_argument("la mesa es más chica que el diámetro de la partícula");
}

// Check the candidate's cell and its 8 neighbours.
// cim_grid_dimensions() guarantees cell width and height >= 2*r,
// so any particle that could overlap the candidate must be in this 3x3 block.
bool overlaps_placed(double x, double y, double r, const std::vector<Particle> &placed, const CellGrid &grid){
    const int cx = grid.cell_coord_x(x), cy = grid.cell_coord_y(y);
    for (int dy = -1; dy <=1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            const int nx = cx + dx, ny = cy + dy;
            if (nx < 0 || nx >= grid.side() || ny < 0 || ny >= grid.width()) continue;
            for (int j : grid.cell(grid.cell_index(nx, ny))) {
                if(discs_overlap(x-placed[j].x, y-placed[j].y, r+placed[j].r)) return true;
            }
        }
    }
    return false;
}

// Obstacles may be larger than particles, so the particle-sized 3x3
// neighbourhood is not sufficient for obstacle checks.
// There are few obstacles, so check them all directly.
bool overlaps_obstacle(double x, double y, double r, const std::vector<Obstacle> &obstacles) {
    for (const Obstacle &o : obstacles)
        if (discs_overlap(x - o.kx, y - o.ky, r + o.Rk)) return true;
    return false;
}

} // namespace

std::vector<Particle> generate_particles(const GeneratorConfig &cfg, GeneratorStats *stats) {
    validate(cfg);

    const auto dims = cim_grid_dimensions(cfg.L, cfg.W, 0.0, cfg.r);
    const int mx = std::max(1, dims.first), my = std::max(1, dims.second);
    CellGrid grid(cfg.L, cfg.W, mx, my, cfg.N);

    std::mt19937_64 rng(cfg.seed);
    std::uniform_real_distribution<double> ux(cfg.r, cfg.L - cfg.r);
    std::uniform_real_distribution<double> uy(cfg.r, cfg.W - cfg.r);
    std::uniform_real_distribution<double> angle(0.0, 2.0 * kPi);

    double obstacle_area = 0.0;
    for (const Obstacle &o : cfg.obstacles)
        obstacle_area += kPi * o.Rk * o.Rk;
    
    const double disc_area = kPi * cfg.r * cfg.r;
    const double table_area = cfg.L * cfg.W;
    std::vector<Particle> particles;

    particles.reserve(static_cast<std::size_t>(cfg.N));

    long long attempts = 0;

    for (int i = 0; i < cfg.N; ++i) {
        bool placed = false;
        for (int attempt = 0; attempt < cfg.max_attempts && !placed; ++attempt) {
            ++attempts;
            const double x = ux(rng), y = uy(rng);
            if (overlaps_obstacle(x,y,cfg.r,cfg.obstacles) || overlaps_placed(x,y,cfg.r, particles,grid)) continue;

            grid.insert(i,x,y);

            const double theta = angle(rng);
            particles.push_back(Particle{x,y,cfg.r,cfg.v0*std::cos(theta),cfg.v0*std::sin(theta), cfg.m});
            placed = true;
        }

        if (!placed){
            std::ostringstream msg;
            msg << "no se pudo ubicar la partícula " << i + 1 
                << " de " << cfg.N
                << " tras " << cfg.max_attempts 
                << " intentos (fracción ocupada "
                << (obstacle_area + i * disc_area) / table_area
                << "): bajar N, reducir los obstáculos o aumentar max_attempts";
            throw std::runtime_error(msg.str());
        }
    }

    if (stats != nullptr) {
        stats->attempts=attempts;
        stats->mx=mx;
        stats->my = my;
        stats->packing_fraction=(obstacle_area + cfg.N * disc_area)/table_area;
    }
    return particles;

}

int find_overlap(const std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles, double L, double W) {
    const int n = static_cast<int>(particles.size());

    for (int i = 0; i < n; ++i) {
        const Particle &a = particles[i];
        if (!disc_inside(a.x, a.y, a.r, L, W)) return i;
        for (const Obstacle &o : obstacles) 
            if (discs_overlap(a.x-o.kx, a.y-o.ky, a.r + o.Rk)) return i;
        for (int j = i+1; j<n; ++j)
            if (discs_overlap(a.x - particles[j].x, a.y-particles[j].y, a.r+particles[j].r)) return i;
    }
    return -1;
}

#include "neighbours.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>

#include "cell_grid.hpp"
#include "geometry.hpp"
#include "linked_cell_grid.hpp"

/* returns max mx and my now that we are working with a rectangle*/
std::pair<int, int> cim_grid_dimensions(double L, double W, double rc,
                                        double r_max) {
  const double reach = rc + 2.0 * r_max;
  if (reach <= 0.0 || L <= 0.0 || W <= 0.0)
    return {0, 0};
  return {static_cast<int>(std::floor(L / reach)),
          static_cast<int>(std::floor(W / reach))};
}

double max_radius(const std::vector<Particle> &particles) {
  double r_max = 0.0;
  for (const Particle &p : particles)
    r_max = std::max(r_max, p.r);
  return r_max;
}

NeighborLists brute_force_neighbors(const std::vector<Particle> &particles,
                                    double L, double W, double rc,
                                    bool periodic) {
  const int n = static_cast<int>(particles.size());
  NeighborLists neighbors(n);

  for (int i = 0; i < n; ++i) {
    for (int j = i + 1; j < n; ++j) {
      if (within_cutoff(particles[i], particles[j], rc, L, W, periodic)) {
        neighbors[i].push_back(j);
        neighbors[j].push_back(i);
      }
    }
  }
  return neighbors;
}

// Half-shell offsets (A&T Fig. 5.5): each adjacent cell pair visited once.
//    NW (no)   N (si)   NE (si)
//     W (no)   ·        E  (si)
//    SW (no)   S (no)   SE (si)
constexpr int kHalfShellCount = 4;
constexpr int kHalfShell[kHalfShellCount][2] = {
    {+1, -1}, {+1, 0}, {+1, +1}, {0, +1}};

template <class Grid, bool Trace, bool Count>
NeighborLists cim_sweep(const std::vector<Particle> &particles, double L,
                        double W, double rc, int Mx, int My, bool periodic,
                        std::ostream *trace, CimStats *stats) {
  using Clock = std::chrono::steady_clock;

  const int n = static_cast<int>(particles.size());
  NeighborLists neighbors(n);

  const auto t_build = Clock::now();
  Grid grid(L, W, Mx, My, n);
  for (int i = 0; i < n; ++i) {
    grid.insert(i, particles[i].x, particles[i].y);
  }
  const auto t_built = Clock::now();

  if constexpr (Trace) {
    *trace << "L " << L << "\nW " << W << "\nMX " << Mx << "\nMY " << My
           << "\nRC " << rc << "\nPERIODIC " << (periodic ? 1 : 0) << '\n';
    for (int i = 0; i < n; ++i) {
      *trace << "P " << i << ' ' << particles[i].x << ' ' << particles[i].y
             << ' ' << particles[i].r << '\n';
    }
    for (int cy = 0; cy < My; ++cy) {
      for (int cx = 0; cx < Mx; ++cx) {
        const auto &ids = grid.cell(grid.cell_index(cx, cy));
        if (ids.empty())
          continue;
        *trace << "CELL " << cx << ' ' << cy;
        for (int id : ids)
          *trace << ' ' << id;
        *trace << '\n';
      }
    }
  }

  std::size_t pair_tests = 0;

  auto test_pair = [&](int a, int b, [[maybe_unused]] const char *tag) {
    if constexpr (Count)
      ++pair_tests;
    const bool hit =
        within_cutoff(particles[a], particles[b], rc, L, W, periodic);
    if (hit) {
      neighbors[a].push_back(b);
      neighbors[b].push_back(a);
    }
    if constexpr (Trace)
      *trace << tag << ' ' << a << ' ' << b << ' ' << (hit ? 1 : 0) << '\n';
  };

  // Sweep clock starts after the optional trace preamble.
  const auto t_sweep = Clock::now();

  for (int cy = 0; cy < My; ++cy) {
    for (int cx = 0; cx < Mx; ++cx) {
      const auto &ids = grid.cell(grid.cell_index(cx, cy));

      if (ids.empty())
        continue;

      if constexpr (Trace)
        *trace << "FOCUS " << cx << ' ' << cy << '\n';

      for (auto it = ids.begin(); it != ids.end(); ++it) {
        auto jt = it;
        for (++jt; jt != ids.end(); ++jt) {
          test_pair(*it, *jt, "SELF");
        }
      }

      for (int k = 0; k < kHalfShellCount; ++k) {
        int nx = cx + kHalfShell[k][0];
        int ny = cy + kHalfShell[k][1];

        if (periodic) {
          nx = (nx + Mx) % Mx;
          ny = (ny + My) % My;
        } else if (nx < 0 || nx >= Mx || ny < 0 || ny >= My) {
          continue;
        }
        const auto &nids = grid.cell(grid.cell_index(nx, ny));

        if constexpr (Trace)
          *trace << "SHELL " << nx << ' ' << ny << '\n';

        for (auto it = ids.begin(); it != ids.end(); ++it) {
          for (auto jt = nids.begin(); jt != nids.end(); ++jt) {
            test_pair(*it, *jt, "PAIR");
          }
        }
      }
    }
  }

  if (stats) {
    stats->build_seconds =
        std::chrono::duration<double>(t_built - t_build).count();
    stats->sweep_seconds =
        std::chrono::duration<double>(Clock::now() - t_sweep).count();
    if constexpr (Count) {
      stats->grid_bytes = grid.memory_bytes();
      stats->grid_live_blocks = grid.live_blocks();
      stats->pair_tests = pair_tests;
    }
  }

  return neighbors;
}

template <class Grid>
NeighborLists cim_dispatch(const std::vector<Particle> &particles, double L,
                           double W, double rc, int Mx, int My, bool periodic,
                           std::ostream *trace, CimStats *stats) {
  if (periodic && (Mx < 3 || My < 3)) {
    if (trace) {
      std::cerr << "warning: periodic with Mx=" << Mx << ", My=" << My
                << " degenerates to all pairs, so no sweep trace is written\n";
    }
    return brute_force_neighbors(particles, L, W, rc, periodic);
  }
  return trace ? cim_sweep<Grid, true, false>(particles, L, W, rc, Mx, My,
                                              periodic, trace, stats)
               : cim_sweep<Grid, false, false>(particles, L, W, rc, Mx, My,
                                               periodic, nullptr, stats);
}

NeighborLists cim_neighbors(const std::vector<Particle> &particles, double L,
                            double W, double rc, int Mx, int My, bool periodic,
                            std::ostream *trace, CimStats *stats) {
  return cim_dispatch<CellGrid>(particles, L, W, rc, Mx, My, periodic, trace,
                                stats);
}

NeighborLists cim_linked_neighbors(const std::vector<Particle> &particles,
                                   double L, double W, double rc, int Mx,
                                   int My, bool periodic, std::ostream *trace,
                                   CimStats *stats) {
  return cim_dispatch<LinkedCellGrid>(particles, L, W, rc, Mx, My, periodic,
                                      trace, stats);
}

CimStats cim_untimed_stats(const std::vector<Particle> &particles, double L,
                           double W, double rc, int Mx, int My, bool periodic,
                           bool linked) {
  CimStats stats;

  if (periodic && (Mx < 3 || My < 3)) {
    stats.pair_tests = brute_pair_tests(particles.size());
    return stats;
  }

  if (linked) {
    cim_sweep<LinkedCellGrid, false, true>(particles, L, W, rc, Mx, My,
                                           periodic, nullptr, &stats);
  } else {
    cim_sweep<CellGrid, false, true>(particles, L, W, rc, Mx, My, periodic,
                                     nullptr, &stats);
  }
  stats.build_seconds = 0.0;
  stats.sweep_seconds = 0.0;
  return stats;
}

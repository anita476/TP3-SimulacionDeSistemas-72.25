#pragma once

#include <cstddef>
#include <iosfwd>
#include <utility>
#include <vector>

#include "particle.hpp"

// neighbours[i]: ids with border-to-border distance < rc (symmetric).
using NeighborLists = std::vector<std::vector<int>>;

struct CimStats {
  double build_seconds = 0.0;
  double sweep_seconds = 0.0;
  std::size_t grid_bytes = 0;
  std::size_t grid_live_blocks = 0;
  std::size_t pair_tests = 0;
};

int cim_max_grid_side(double L, double rc, double r_max);
std::pair<int, int> cim_grid_dimensions(double L, double W, double rc,
                                        double r_max);

double max_radius(const std::vector<Particle> &particles);

NeighborLists brute_force_neighbors(const std::vector<Particle> &particles,
                                    double L, double W, double rc, bool periodic);

// Mx by My CIM + half-shell. `cim` uses CellGrid; `cim_linked` uses HEAD/LIST.
// Same pairs; list order may differ. Non-null `trace` logs the sweep.
NeighborLists cim_neighbors(const std::vector<Particle> &particles, double L,
                            double W, double rc, int Mx, int My, bool periodic,
                            std::ostream *trace = nullptr,
                            CimStats *stats = nullptr);

NeighborLists cim_linked_neighbors(const std::vector<Particle> &particles,
                                   double L, double W, double rc, int Mx, int My,
                                   bool periodic,
                                   std::ostream *trace = nullptr,
                                   CimStats *stats = nullptr);

// Counters only (pair_tests / memory); timings are meaningless here.
CimStats cim_untimed_stats(const std::vector<Particle> &particles, double L,
                           double W, double rc, int Mx, int My, bool periodic,
                           bool linked);

inline std::size_t brute_pair_tests(std::size_t n) { return n * (n - 1) / 2; }

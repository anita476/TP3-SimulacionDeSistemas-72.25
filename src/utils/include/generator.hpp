#pragma once

#include <random>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

struct GeneratorConfig {
    int N = 100;
    double L = 1.20, W = 0.68;
    double r = 0.0175, m = 0.025, v0=1.0;
    std::vector<Obstacle> obstacles;
    std::uint64_t seed = 1;
    int max_attempts = 100000;
};

struct GeneratorStats {
    long long attempts = 0;
    int mx = 0, my = 0;
    double packing_fraction = 0.0;
};

// Generates particles assuming cfg.obstacles has already been validated.
// throws: runtime_error if particle does not fit after max_attempts tries
std::vector<Particle> generate_particles(const GeneratorConfig &cfg, GeneratorStats *stats = nullptr);

// brute-force check; -1 if clean else the index of the first offending particle
int find_overlap(const std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles, double L, double W);
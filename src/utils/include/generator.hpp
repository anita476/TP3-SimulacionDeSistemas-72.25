#pragma once

#include <random>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

struct Position {
    double x,y;
};

enum class Placement { Random, Hex };

struct GeneratorConfig {
    int N = 100;
    double L = 1.20, W = 0.68;
    double r = 0.0175, m = 0.025, v0=1.0;
    std::vector<Obstacle> obstacles;
    std::uint64_t seed = 0;
    Placement placement = Placement::Random;
    int max_attempts = 100000;
};

struct GeneratorStats {
    long long attempts = 0;
    int mx = 0, my = 0;
    double packing_fraction = 0.0;
    double lattice_gap = -1.0;
};

// Generates particles assuming cfg.obstacles has already been validated.
// throws: runtime_error if particle does not fit after max_attempts tries
std::vector<Particle> generate_particles(const GeneratorConfig &cfg, GeneratorStats *stats = nullptr);

// brute-force check; -1 if clean else the index of the first offending particle
int find_overlap(const std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles, double L, double W);

// Sites of hexagonal lattice with spacing a
std::vector<Position> hex_sites(double a, double L, double W, double r);

// Number of sites at the minimum spacing (discs touching)
int hex_capacity(double L, double W, double r);

// N lattice sites with the largest spacing that still fits N
// throws: runtime_error if N > hex_capacity
std::vector<Position> hex_positions(int N, double L, double W, double r, double *spacing=nullptr);
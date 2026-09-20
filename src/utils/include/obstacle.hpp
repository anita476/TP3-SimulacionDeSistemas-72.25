#pragma once

#include <string>
#include <vector>

struct Obstacle {
  double kx, ky, Rk; /*position of center and radius*/
};

void validate_obstacles(const std::vector<Obstacle> &obstacles, double L, double W, double r); // for tests
std::vector<Obstacle> load_obstacles(const std::string& path, double L, double W, double particle_radius);
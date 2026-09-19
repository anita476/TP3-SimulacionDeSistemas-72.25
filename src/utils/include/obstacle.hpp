#pragma once

#include <string>
#include <vector>

struct Obstacle {
  double kx, ky, Rk; /*position of center and radius*/
};

std::vector<Obstacle> read_obstacles(const std::string &path);

// restricciones: Rk >= r & integramente dentro de la mesa
void validate_obstacles(const std::vector<Obstacle> &obstacles, double L, double W, double r);
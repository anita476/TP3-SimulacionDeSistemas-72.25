#include "obstacle.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <cmath>

#include "geometry.hpp"

namespace {

std::vector<Obstacle> read_obstacles(const std::string &path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("Could not open " + path);

    std::vector<Obstacle> obstacles;
    std::string line;
    int lineno = 0;
    while (std::getline(in, line)) {
        if (in.bad()) throw std::runtime_error("Error reading " + path);
        ++lineno;
        const std::size_t hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);

        std::istringstream fields(line);
        std::vector<std::string> tokens;
        for (std::string tok; fields >> tok;) tokens.push_back(tok);
        if (tokens.empty()) continue;

        const std::string where = path + ":" + std::to_string(lineno);
        if (tokens.size() != 3) throw std::runtime_error(where + ": expected 3 fields xk yk Rk, but there are " + std::to_string(tokens.size()));
        auto to_double = [&where](const std::string &tok) {
            std::size_t pos = 0;
            double v = 0.0;
            try {
                v = std::stod(tok, &pos);
            } catch (const std::logic_error &) {
                throw std::runtime_error(where + ": not a numeric field '" + tok + "'");
            }
            if (pos != tok.size()) throw std::runtime_error(where + ": not a numeric field '" + tok + "'");
            return v;
        };
        obstacles.push_back({to_double(tokens[0]), to_double(tokens[1]), to_double(tokens[2])});
    }
    return obstacles;
}

}


void validate_obstacles(const std::vector<Obstacle> &obstacles, double L, double W, double r) {
    if (!std::isfinite(L) || L <= 0.0 ||
        !std::isfinite(W) || W <= 0.0 ||
        !std::isfinite(r) || r <= 0.0) {
        throw std::invalid_argument(
            "Obstacle validation: L, W and particle radius must be finite and positive");
    }
    for (std::size_t k = 0; k < obstacles.size(); ++k) {
        const Obstacle &o = obstacles[k];
        const std::string where = "obstacle " + std::to_string(k+1);
        if (!std::isfinite(o.kx) ||
            !std::isfinite(o.ky) ||
            !std::isfinite(o.Rk)) {
            throw std::invalid_argument(
                where + ": coordinates and radius must be finite");
        }
        if (o.Rk < r) throw std::runtime_error(where + ": Rk < r");
        if (!disc_inside(o.kx, o.ky, o.Rk, L, W))
            throw std::runtime_error(where + ": not inside table");

        for (std::size_t j = 0; j < k; ++j) {
            if (discs_overlap(o.kx - obstacles[j].kx, o.ky - obstacles[j].ky, o.Rk + obstacles[j].Rk))
                throw std::runtime_error(where + " overlaps with obstacle " + std::to_string(j+1));
        }
    }
}


std::vector<Obstacle> load_obstacles(const std::string& path,
                                    double L, double W,
                                    double particle_radius) {
    auto obstacles = read_obstacles(path);
    validate_obstacles(obstacles, L, W, particle_radius);
    return obstacles;
}
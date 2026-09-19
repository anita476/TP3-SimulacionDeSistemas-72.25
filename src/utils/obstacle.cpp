#include "obstacle.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

#include "geometry.hpp"

std::vector<Obstacle> read_obstacles(const std::string &path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("No se pudo abrir " + path);

    std::vector<Obstacle> obstacles;
    std::string line;
    int lineno = 0;
    while (std::getline(in, line)) {
        ++lineno;
        const std::size_t hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);

        std::istringstream fields(line);
        std::vector<std::string> tokens;
        for (std::string tok; fields >> tok;) tokens.push_back(tok);
        if (tokens.empty()) continue;

        const std::string where = path + ":" + std::to_string(lineno);
        if (tokens.size() != 3) throw std::runtime_error(where + ": se esperaban 3 campos xk yk Rk, hay " + std::to_string(tokens.size()));
        auto to_double = [&where](const std::string &tok) {
            std::size_t pos = 0;
            double v = 0.0;
            try {
                v = std::stod(tok, &pos);
            } catch (const std::logic_error &) {
                throw std::runtime_error(where + ": campo no numérico '" + tok + "'");
            }
            if (pos != tok.size()) throw std::runtime_error(where + ": campo no numérico '" + tok + "'");
            return v;
        };
        obstacles.push_back({to_double(tokens[0]), to_double(tokens[1]), to_double(tokens[2])});
    }
    return obstacles;
}

void validate_obstacles(const std::vector<Obstacle> &obstacles, double L, double W, double r) {
    for (std::size_t k = 0; k < obstacles.size(); ++k) {
        const Obstacle &o = obstacles[k];
        const std::string where = "obstáculo " + std::to_string(k+1);
        if (o.Rk < r) throw std::runtime_error(where + ": Rk < r");
        if (!disc_inside(o.kx, o.ky, o.Rk, L, W))
            throw std::runtime_error(where + ": no está íntegramente dentro del dominio (mesa)");

        for (std::size_t j = 0; j < k; ++j) {
            if (discs_overlap(o.kx - obstacles[j].kx, o.ky - obstacles[j].ky, o.Rk + obstacles[j].Rk))
                throw std::runtime_error(where + " se solapa con el obstáculo " + std::to_string(j+1));
        }
    }
}

#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

#include "check.hpp"
#include "obstacle.hpp"

// archivos de prueba a temp
static std::string tmp_path(const std::string &name) {
  return (std::filesystem::temp_directory_path() / ("tp3_" + name)).string();
}

static std::string write_file(const std::string &name, const std::string &text) {
  const std::string path = tmp_path(name);
  std::ofstream out(path);
  out << text;
  return path;
}

static bool throws(const std::vector<Obstacle> &obs) {
  try {
    validate_obstacles(obs, 1.20, 0.68, 0.0175);
  } catch (const std::runtime_error &) {
    return true;
  }
  return false;
}

int main() {
  // lineas xk yk Rk; se ignoran blancos y comentarios
  const std::string ok = write_file("obs_ok.txt", "# centro\n0.60 0.34 0.05\n\n0.30 0.20 0.02  # otro\n");
  const std::vector<Obstacle> obs = read_obstacles(ok);
  CHECK(obs.size() == 2);
  CHECK_NEAR(obs[0].kx, 0.60, 1e-12);
  CHECK_NEAR(obs[0].ky, 0.34, 1e-12);
  CHECK_NEAR(obs[0].Rk, 0.05, 1e-12);
  CHECK_NEAR(obs[1].Rk, 0.02, 1e-12);
  CHECK(!throws(obs));

  // Archivo inexistente, campos de más, campo no numérico.
  bool threw = false;
  try {
    read_obstacles(tmp_path("no_existe.txt"));
  } catch (const std::runtime_error &) {
    threw = true;
  }
  CHECK(threw);

  const std::string bad_count = write_file("obs_bad_count.txt", "0.6 0.34\n");
  threw = false;
  try {
    read_obstacles(bad_count);
  } catch (const std::runtime_error &) {
    threw = true;
  }
  CHECK(threw);

  const std::string bad_num = write_file("obs_bad_num.txt", "xk yk Rk\n");
  threw = false;
  try {
    read_obstacles(bad_num);
  } catch (const std::runtime_error &) {
    threw = true;
  }
  CHECK(threw);

  // Restricciones
  CHECK(throws({{0.60, 0.34, 0.01}}));           // Rk < r
  CHECK(throws({{0.03, 0.34, 0.05}}));           // se sale por x = 0
  CHECK(throws({{0.60, 0.66, 0.05}}));           // se sale por y = W
  CHECK(throws({{0.60, 0.34, 0.05}, {0.66, 0.34, 0.05}})); // se solapan
  // Claramente separados. Apoyado en la pared x = L: vale (adentro).
  CHECK(!throws({{0.60, 0.34, 0.05}, {0.71, 0.34, 0.05}}));
  CHECK(!throws({{1.15, 0.34, 0.05}}));
  CHECK(throws({{0.60, 0.34, 0.0174}}));          // Rk < r
  CHECK(!throws({}));                             // sin obstáculos también ok
  for (const std::string &f : {ok, bad_count, bad_num})
    std::filesystem::remove(f);
  return finish();
}
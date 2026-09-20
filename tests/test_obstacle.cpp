#include <exception>
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include "check.hpp"
#include "obstacle.hpp"

namespace {

constexpr double kTableLength = 1.20;
constexpr double kTableWidth = 0.68;
constexpr double kParticleRadius = 0.0175;

// Temporary files used by the loader tests.
std::string tmp_path(const std::string& name) {
    return (std::filesystem::temp_directory_path() /
            ("tp3_" + name)).string();
}

std::string write_file(const std::string& name, const std::string& text) {
    const std::string path = tmp_path(name);
    std::ofstream out(path);

    if (!out)
        throw std::runtime_error("Could not create test file: " + path);

    out << text;
    out.close();

    if (!out)
        throw std::runtime_error("Could not write test file: " + path);

    return path;
}

bool validation_fails(const std::vector<Obstacle>& obstacles) {
    try {
        validate_obstacles(
            obstacles, kTableLength, kTableWidth, kParticleRadius);
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

bool loading_fails(const std::string& path) {
    try {
        load_obstacles(
            path, kTableLength, kTableWidth, kParticleRadius);
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

} // namespace

int main() {
    // Blank lines and comments are accepted.
    const std::string valid_file = write_file(
        "obs_valid.txt",
        "# centre coordinates and radius\n"
        "0.60 0.34 0.05\n"
        "\n"
        "0.30 0.20 0.02  # another obstacle\n");

    const std::vector<Obstacle> obstacles = load_obstacles(
        valid_file, kTableLength, kTableWidth, kParticleRadius);

    CHECK(obstacles.size() == 2);

    // Guard indexing so a failed size check does not crash the test.
    if (obstacles.size() == 2) {
        CHECK_NEAR(obstacles[0].kx, 0.60, 1e-12);
        CHECK_NEAR(obstacles[0].ky, 0.34, 1e-12);
        CHECK_NEAR(obstacles[0].Rk, 0.05, 1e-12);
        CHECK_NEAR(obstacles[1].kx, 0.30, 1e-12);
        CHECK_NEAR(obstacles[1].ky, 0.20, 1e-12);
        CHECK_NEAR(obstacles[1].Rk, 0.02, 1e-12);
    }

    // Ensure the missing-file test cannot find a leftover test file.
    const std::string missing_file = tmp_path("obs_missing.txt");
    std::filesystem::remove(missing_file);
    CHECK(loading_fails(missing_file));

    const std::string missing_field = write_file(
        "obs_missing_field.txt", "0.60 0.34\n");
    CHECK(loading_fails(missing_field));

    const std::string extra_field = write_file(
        "obs_extra_field.txt", "0.60 0.34 0.05 1.0\n");
    CHECK(loading_fails(extra_field));

    const std::string nonnumeric_field = write_file(
        "obs_nonnumeric.txt", "xk yk Rk\n");
    CHECK(loading_fails(nonnumeric_field));

    const std::string partial_number = write_file(
        "obs_partial_number.txt", "0.60abc 0.34 0.05\n");
    CHECK(loading_fails(partial_number));

    // Loading must validate geometry as well as parse the file.
    const std::string invalid_radius = write_file(
        "obs_invalid_radius.txt", "0.60 0.34 0.01\n");
    CHECK(loading_fails(invalid_radius));

    const std::string empty_file = write_file(
        "obs_empty.txt", "# no obstacles\n\n");
    CHECK(load_obstacles(
        empty_file, kTableLength, kTableWidth, kParticleRadius).empty());

    // Radius, table bounds, and obstacle separation.
    CHECK(validation_fails({{0.60, 0.34, 0.01}}));
    CHECK(validation_fails({{0.60, 0.34, 0.0174}}));
    CHECK(validation_fails({{0.03, 0.34, 0.05}}));
    CHECK(validation_fails({{0.60, 0.66, 0.05}}));

    CHECK(validation_fails({
        {0.60, 0.34, 0.05},
        {0.66, 0.34, 0.05}
    }));

    CHECK(!validation_fails({
        {0.60, 0.34, 0.05},
        {0.71, 0.34, 0.05}
    }));

    // The minimum allowed radius is accepted.
    CHECK(!validation_fails({{0.60, 0.34, kParticleRadius}}));

    // Contact with the table wall is allowed by disc_inside().
    CHECK(!validation_fails({{1.15, 0.34, 0.05}}));
    CHECK(!validation_fails({}));

    // Requires explicit finite-value checks in validate_obstacles().
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double infinity = std::numeric_limits<double>::infinity();

    CHECK(validation_fails({{nan, 0.34, 0.05}}));
    CHECK(validation_fails({{0.60, infinity, 0.05}}));
    CHECK(validation_fails({{0.60, 0.34, nan}}));
    CHECK(validation_fails({{0.60, 0.34, infinity}}));

    for (const std::string& path : {
             valid_file, missing_field, extra_field, nonnumeric_field,
             partial_number, invalid_radius, empty_file}) {
        std::filesystem::remove(path);
    }

    return finish();
}
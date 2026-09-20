#include <argparse/argparse.hpp>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "generator.hpp"
#include "obstacle.hpp"
#include "simulation.hpp"

namespace {
double seconds_since(std::chrono::steady_clock::time_point t0) { 
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
}

// creates dump folder if it doesnt exist
std::ofstream open_dump(const std::string &path) {
    const std::filesystem::path parent = std::filesystem::path(path).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);
    std::ofstream file(path);
    if (!file) throw std::runtime_error("could not open " + path);
    file << std::setprecision(12);
    return file;
}

}

int main(int argc, char *argv[]) {
    argparse::ArgumentParser program("EventDriven-TP3", "0.2", argparse::default_arguments::help);
    
    program.add_argument("-L").default_value(1.20).scan<'g', double>().help("table length (m)");
    program.add_argument("-W").default_value(0.68).scan<'g', double>().help("table width (m)");
    program.add_argument("-d").default_value(0.20).scan<'g', double>().help("goal width, centred on each short wall (m)");

    program.add_argument("-N").default_value(100).scan<'i', int>().help("particle count (default 100)");
    program.add_argument("-r").default_value(0.0175).scan<'g', double>().help("particle radius (m)");
    program.add_argument("-m").default_value(0.025).scan<'g', double>().help("particle mass (kg)");
    program.add_argument("-v0").default_value(1.0).scan<'g', double>().help("initial speed (m/s)");

    program.add_argument("-tmax").default_value(30.0).scan<'g', double>().help("maximum simulated time (s) (default 30)");
    program.add_argument("-k").default_value(200).scan<'i', int>().help("dump every k physical events (0 = only at goals) (default 200)");
    program.add_argument("-seed").default_value(1).scan<'i', int>().help("RNG seed");
    program.add_argument("-obstacles").default_value(std::string("")).help("obstacle file: one 'xk yk Rk' line per obstacle (m)");
    program.add_argument("--out").default_value(std::string("")).help("dump path (empty = no dump)");
    

    try {
        program.parse_args(argc, argv);
    } catch (const std::exception &err) {
        std::cerr << err.what() << '\n';
        std::cerr << program;
        return 1;
    }

    const double L = program.get<double>("-L");
    const double W = program.get<double>("-W");
    const double d = program.get<double>("-d");
    const int N = program.get<int>("-N");
    const double r = program.get<double>("-r");
    const double m = program.get<double>("-m");
    const double v0 = program.get<double>("-v0");
    const double tmax = program.get<double>("-tmax");
    const int k = program.get<int>("-k");
    const int seed = program.get<int>("-seed");
    const std::string obstacles_path = program.get<std::string>("-obstacles");
    const std::string out_path = program.get<std::string>("--out");

    try {
        SimParams params{L, W, d, tmax, k};
        std::vector<Obstacle> obstacles;
        if (!obstacles_path.empty()) {
            obstacles = load_obstacles(obstacles_path, L, W, r);
        }

        GeneratorConfig gen;
        gen.N = N;
        gen.L = L;
        gen.W = W;
        gen.r = r;
        gen.m = m;
        gen.v0 = v0;
        gen.obstacles = obstacles;
        gen.seed = static_cast<std::uint64_t>(seed);
        GeneratorStats gen_stats;
        std::vector<Particle> particles = generate_particles(gen, &gen_stats);

        std::ofstream file;
        std::ostream *out = nullptr;
        const std::string out_path = program.get<std::string>("--out");
        if (!out_path.empty()) {
            file.open(out_path);
            if (!file) throw std::runtime_error("Couldn't open " + out_path);
            file << std::setprecision(12);
            out = &file;
        }

        // init = construccion (grilla, indice de obstaculos, predicciones iniciales)
        const auto t_init = std::chrono::steady_clock::now();
        Simulation sim(params, std::move(particles), obstacles);
        const double init_seconds = seconds_since(t_init);
        const double e0 = sim.kinetic_energy();
        const auto t_loop = std::chrono::steady_clock::now();
        sim.run(out);
        const double loop_seconds = seconds_since(t_loop);
        const double e_end = sim.kinetic_energy();
        const SimStats &st = sim.stats();

        std::cout << std::setprecision(10)
            << "N " << N << '\n'
            << "K " << obstacles.size() << '\n'
            << "seed " << seed << '\n'
            << "tmax " << tmax << '\n'
            << "k " << k << '\n'
            << "packing " << gen_stats.packing_fraction << '\n'
            << "events " << sim.events() << '\n'
            << "wall_events " << st.wall_events << '\n'
            << "obstacle_events " << st.obstacle_events << '\n'
            << "pair_events " << st.pair_events << '\n'
            << "discarded " << st.discarded << '\n'
            << "zero_dt " << st.zero_dt << '\n'
            << "max_queue " << st.max_queue << '\n'
            << "t_end " << sim.time() << '\n'
            << "Ng " << sim.goals() << '\n'
            << "t90 " << sim.t90() << '\n'
            << "E0 " << e0 << '\n'
            << "E_end " << e_end << '\n'
            << "energy_drift " << std::fabs(e_end - e0) / e0 << '\n'
            << "init_seconds " << init_seconds << '\n'
            << "loop_seconds " << loop_seconds << '\n'
            << "engine_seconds " << init_seconds + loop_seconds << '\n';

    } catch (const std::exception &err) {
        std::cerr << "error: " << err.what() << '\n';
        return 1;
    }
    return 0;
}

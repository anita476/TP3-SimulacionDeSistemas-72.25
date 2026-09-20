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

int main(int argc, char *argv[]) {
    argparse::ArgumentParser program("EventDriven-TP3", "0.1", argparse::default_arguments::help);
    
    program.add_argument("-N").default_value(100).scan<'i', int>().help("particle count (default 100)");
    program.add_argument("-tmax").default_value(30.0).scan<'g', double>().help("Maximum simulated time (s) (default 30)");
    program.add_argument("-k").default_value(200).scan<'i', int>().help("Dump every k events (0 = only at goals) (default 200)");
    program.add_argument("-seed").default_value(1).scan<'i', int>().help("RNG seed");
    program.add_argument("-obstacles").default_value(std::string("")).help("Path to obstacle input file, one 'xk yk Rk' per line");
    program.add_argument("--out").default_value(std::string("")).help("dump path (empty = no dump)");
    
    // program.add_argument("-L").default_value(1.20).scan<'g', double>().help("box side length");
    // program.add_argument("-W").default_value(0.68).scan<'g', double>().help("box side width");
    // program.add_argument("-d").default_value(0.20).scan<'g', double>().help("goal width");

    try {
        program.parse_args(argc, argv);
    } catch (const std::exception &err) {
        std::cerr << err.what() << '\n';
        std::cerr << program;
        return 1;
    }

    try {
        const double L = 1.20, W = 0.68, d = 0.20;
        GeneratorConfig gen;
        gen.N = program.get<int>("-N");
        gen.seed = static_cast<std::uint64_t>(program.get<int>("-seed"));
        const std::string obstacles_path = program.get<std::string>("-obstacles");
        if (!obstacles_path.empty()) {
            gen.obstacles = read_obstacles(obstacles_path);
            validate_obstacles(gen.obstacles, L, W, gen.r); 
        }
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

        const auto t0 = std::chrono::steady_clock::now();
        Simulation sim(SimParams{L,W,d,program.get<double>("-tmax"), program.get<int>("-k")},std::move(particles),gen.obstacles);
        const double e0 = sim.kinetic_energy();
        sim.run(out);
        const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

        std::cout << std::setprecision(12) << "N " << gen.N << "\npacking " << gen_stats.packing_fraction
        <<"\nevents " << sim.events()
        <<"\nt_end " << sim.time()
        <<"\nNg " << sim.goals()
        <<"\nt90 " << sim.t90()
        <<"\nE0 " << e0
        << "\nE_end " << sim.kinetic_energy()
        <<"\nwall_seconds " << wall << '\n';
    } catch (const std::exception &err) {
        std::cerr << "error: " << err.what() << '\n';
        return 1;
    }
    return 0;
}

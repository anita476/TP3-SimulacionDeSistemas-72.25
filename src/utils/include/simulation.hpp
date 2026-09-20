#pragma once
#include <ostream>
#include <vector>

#include "event_queue.hpp"
#include "obstacle.hpp"
#include "particle.hpp"

struct SimParams {
    double L, W, d;
    double tmax;
    int k;
};

struct SimStats { 
    long wall_events = 0; // choques contra paredes (x o y)
    long obstacle_events = 0; // choques con obstaculos
    long pair_events = 0; // choques entre particulas
    long discarded = 0; // entradas de la queue invalidadas por un choque posterior de una particula
    long zero_dt = 0; // prediciones con dt == 0: empates exactos o particulas a sigma - epsilon
    long pair_tests = 0; // llamadas a pair_time
    long obstacle_tests =0 ; // llamadas a obstacle_time
    std::size_t max_queue = 0; // tamano maximo alcanzado por la queue
};

constexpr double kRoundoff = 1e-9;

class Simulation {
    public:
        Simulation(SimParams params, std::vector<Particle> particles, std::vector<Obstacle> obstacles);

        void run(std::ostream *out);
        double time() const {return t_;}
        long events() const {return events_;}
        int goals() const {return goals_;}
        double t90() const {return t90_;} // -1 while Fu < 0.9
        const std::vector<Particle> &particles() const { return particles_; }
        const SimStats &stats() const { return stats_; }
        double kinetic_energy() const;

    private:
        void validate_inputs() const;
        void push(double dt, EventKind kind, int i, int j);
        void predict_single(int i); // paredes y obstaculos de i
        void predict_pair(int i, int j);
        void predict_all(int i); // single + pares con todas las demas
        bool valid(const Event &e) const;
        void advance_all(double t);
        bool resolve(const Event &e);

        SimParams params_;
        std::vector<Particle> particles_;
        std::vector<Obstacle> obstacles_;
        EventQueue queue_;
        SimStats stats_;
        double t_ = 0.0;
        long events_ = 0;
        int goals_ = 0;
        int goal_target_; // ceil (0.9N)
        double t90_ = -1.0;
};
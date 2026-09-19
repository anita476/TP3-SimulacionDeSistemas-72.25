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

class Simulation {
    public:
        Simulation(SimParams params, std::vector<Particle> particles, std::vector<Obstacle> obstacles);

        void run(std::ostream *out);
        double time() const {return t_;}
        long events() const {return events_;}
        int goals() const {return goals_;}
        double t90() const {return t90_;} // -1 while Fu < 0.9
        const std::vector<Particle> &particles() const { return particles_; }
        double kinetic_energy() const;

    private:
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
        double t_ = 0.0;
        long events_ = 0;
        int goals_ = 0;
        int goal_target_; // ceil (0.9N)
        double t90_ = -1.0;
};
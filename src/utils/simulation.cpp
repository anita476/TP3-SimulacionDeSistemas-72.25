#include "simulation.hpp"

#include <cmath>
#include <utility>

#include "collision.hpp"
#include "dump.hpp"

// Requires a valid initial configuration: particles inside this table,
// no overlaps, valid particle properties, and validated obstacles.

Simulation::Simulation(
    SimParams params,
    std::vector<Particle> particles,
    std::vector<Obstacle> obstacles
)
    : params_(params),
    particles_(std::move(particles)),
    obstacles_(std::move(obstacles)),
    goal_target_(static_cast<int>(
        std::ceil(0.9*static_cast<double>(particles_.size()) - 1e-9)
    ))
{
    validate_inputs();
    const int n = static_cast<int>(particles_.size());

    for (int i = 0; i < n; ++i) {
        predict_single(i);
        for (int j = i + 1; j < n; ++j ) 
            predict_pair(i,j);
    }
}

void Simulation::validate_inputs() const {
    if (!std::isfinite(params_.L) || params_.L <= 0.0 ||
        !std::isfinite(params_.W) || params_.W <= 0.0) {
        throw std::invalid_argument(
            "Simulation: L and W must be finite and positive");
    }
    if (!std::isfinite(params_.d) ||
        params_.d <= 0.0 || params_.d > params_.W) {
        throw std::invalid_argument(
            "Simulation: d must be finite and in (0, W]");
    }
    if (!std::isfinite(params_.tmax) || params_.tmax <= 0.0) {
        throw std::invalid_argument(
            "Simulation: tmax must be finite and positive");
    }

    if (params_.k < 0) {
        throw std::invalid_argument("Simulation: k must be >= 0");
    }

    if (particles_.empty()) {
        throw std::invalid_argument(
            "Simulation: requires at least one particle");
    }
    for (std::size_t i = 0; i < particles_.size(); ++i) {
        const Particle &p = particles_[i];
        const std::string who = "Simulation: particle " + std::to_string(i) + ": ";
        if (!(p.r > 0.0) || !(p.m > 0.0))
            throw std::invalid_argument(who + "r and m must be > 0");
        if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.vx) || !std::isfinite(p.vy))
            throw std::invalid_argument(who + "position or velocity not finite");
    }
}

void Simulation::push(double dt, EventKind kind, int i, int j) {
    if (!std::isfinite(dt)) {
        return; // No valid future collision
    }
    if (dt < 0.0) throw std::logic_error("Simulation: collision time is negative " + std::to_string(dt) + " for particle " + std::to_string(i));
    if (dt == 0.0) ++stats_.zero_dt;

    const int count_j = kind == EventKind::Pair 
        ? particles_[j].collisions
        : -1;
    queue_.push(Event{t_ + dt, kind, i, j, particles_[i].collisions, count_j});
    stats_.max_queue = std::max(stats_.max_queue, queue_.size());
}

void Simulation::predict_single(int i) {
    const Particle &p = particles_[i];
    push(wall_time_x(p, params_.L), EventKind::WallX, i, -1);
    push(wall_time_y(p, params_.W), EventKind::WallY, i, -1);

    for (int k = 0; k < static_cast<int> (obstacles_.size()); ++k) {
        ++stats_.obstacle_tests;
        push(obstacle_time(p, obstacles_[k]), EventKind::Obstacle, i, k);
    }
}

void Simulation::predict_pair(int i, int j) {
    ++stats_.pair_tests;
    push(pair_time(particles_[i], particles_[j]), EventKind::Pair, i, j);
}

void Simulation::predict_all(int i) {
    predict_single(i);
    const int n = static_cast<int>(particles_.size());
    for (int j = 0; j < n; ++j) 
        if (j != i) 
            predict_pair(i,j);
}

bool Simulation::valid(const Event &e) const {
    if (particles_[e.i].collisions != e.count_i)
        return false;
    if (e.kind == EventKind::Pair && particles_[e.j].collisions != e.count_j)
        return false;
    return true;
}

void Simulation::advance_all(double t) {
    const double dt = t - t_;
    for (Particle &p : particles_) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
    }
    t_ = t;
}

bool Simulation::resolve(const Event &e) {
    Particle &p = particles_[e.i];
    bool goal = false;
    switch(e.kind) {
        case EventKind::WallX:
            if (!p.used && std::fabs(p.y - 0.5 * params_.W) <= 0.5 * params_.d) {
                p.used = 1;
                ++goals_;
                goal = true;
                if (goals_ >= goal_target_ && t90_ < 0.0)
                    t90_ = t_;
            }
            bounce_x(p);
            ++p.collisions;
            ++stats_.wall_events;
            break;
        case EventKind::WallY:
            bounce_y(p);
            ++p.collisions;
            ++stats_.wall_events;
            break;
        case EventKind::Obstacle:
            collide_obstacle(p, obstacles_[static_cast<std::size_t>(e.j)]);
            ++p.collisions;
            ++stats_.obstacle_events;
            break;
        case EventKind::Pair:
            collide_pair(p, particles_[e.j]);
            ++p.collisions;
            ++particles_[e.j].collisions;
            ++stats_.pair_events;
            break;
    }
    return goal;
}

double Simulation::kinetic_energy() const {
    double e = 0.0;
    for (const Particle &p : particles_)
        e += 0.5 * p.m * (p.vx * p.vx + p.vy * p.vy);
    return e;
}

void Simulation::run(std::ostream *out) {
    if (out) {
        write_dump_header(*out, params_.L, params_.W, params_.d,  particles_[0].r, particles_[0].m, static_cast<int>(particles_.size()), obstacles_);
        write_dump_frame(*out, t_, particles_);
    }

    while (!queue_.empty()) {
        const Event e = queue_.top();
        queue_.pop();
        if (e.t > params_.tmax) break;
        if (!valid(e)) {
            ++stats_.discarded;
            continue;
        }
        if (e.t < t_) throw std::logic_error("Simulation: the queue returned a past event");
        advance_all(e.t);
        const bool goal = resolve(e);
        ++events_;

        if (out && (goal || (params_.k > 0 && events_ % params_.k == 0)))
            write_dump_frame(*out, t_, particles_);
        
        predict_all(e.i);
        if (e.kind == EventKind::Pair)
            predict_all(e.j);
    }
}
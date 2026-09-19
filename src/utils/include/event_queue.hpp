#pragma once

#include <functional>
#include <queue>
#include <vector>

enum class EventKind { WallX, WallY, Pair, Obstacle };

// i is the current particle, j the other 
// particle (Pair), index of obstacle (Obstacle) or -1 (Wall)]
struct Event {
    double t;
    EventKind kind;
    int i,j;
    int count_i, count_j;
    bool operator>(const Event &o) const { return t > o.t; }
};

// priority queue based on bibliography suggested by professor
// ordered by smallest t
// lazy invalidation
using EventQueue = std::priority_queue<Event, std::vector<Event>, std::greater<Event>>;
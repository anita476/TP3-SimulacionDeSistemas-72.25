#pragma once

#include <cstddef>
#include <vector>

// Mx x My cells over [0,L) x [0,W); each cell stores particle ids by centre.
class CellGrid {
public:
  CellGrid(double L, double W, int Mx, int My, int /*n*/ = 0)
      : L_(L), W_(W), Mx_(Mx), My_(My),
        cells_(static_cast<std::size_t>(Mx) * static_cast<std::size_t>(My)) {}

  int side() const { return Mx_; }
  int width() const { return My_; }
  int cell_count() const { return Mx_ * My_; }
  double cell_size() const { return L_ / Mx_; }

  int cell_coord_x(double v) const {
    const int c = static_cast<int>(v * Mx_ / L_);
    if (c < 0)
      return 0;
    if (c >= Mx_)
      return Mx_ - 1;
    return c;
  }

  int cell_coord_y(double v) const {
    const int c = static_cast<int>(v * My_ / W_);
    if (c < 0)
      return 0;
    if (c >= My_)
      return My_ - 1;
    return c;
  }

  int cell_coord(double v) const { return cell_coord_x(v); }
  int cell_index(int cx, int cy) const { return cy * Mx_ + cx; }

  void insert(int id, double x, double y) {
    cells_[cell_index(cell_coord_x(x), cell_coord_y(y))].push_back(id);
  }

  const std::vector<int> &cell(int index) const { return cells_[index]; }

  void clear() {
    for (std::vector<int> &c : cells_)
      c.clear();
  }

  std::size_t memory_bytes() const {
    std::size_t bytes = cells_.capacity() * sizeof(std::vector<int>);
    for (const std::vector<int> &c : cells_)
      bytes += c.capacity() * sizeof(int);
    return bytes;
  }

  // Outer array + one block per non-empty cell (capacity > 0).
  std::size_t live_blocks() const {
    std::size_t count = cells_.capacity() > 0 ? 1 : 0;
    for (const std::vector<int> &c : cells_) {
      if (c.capacity() > 0)
        ++count;
    }
    return count;
  }

private:
  double L_;
  double W_;
  int Mx_;
  int My_;
  std::vector<std::vector<int>> cells_;
};

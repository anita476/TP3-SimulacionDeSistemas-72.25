#pragma once

#include <cstddef>
#include <vector>

// M x M cells over [0,L) x [0,L); each cell stores particle ids by centre.
class CellGrid {
public:
  // `n` unused; kept so CellGrid and LinkedCellGrid share the same ctor shape.
  CellGrid(double L, int M, int /*n*/ = 0)
      : L_(L), M_(M),
        cells_(static_cast<std::size_t>(M) * static_cast<std::size_t>(M)) {}

  int side() const { return M_; }
  int cell_count() const { return M_ * M_; }
  double cell_size() const { return L_ / M_; }

  int cell_coord(double v) const {
    const int c = static_cast<int>(v * M_ / L_);
    if (c < 0)
      return 0;
    if (c >= M_)
      return M_ - 1;
    return c;
  }

  int cell_index(int cx, int cy) const { return cy * M_ + cx; }

  void insert(int id, double x, double y) {
    cells_[cell_index(cell_coord(x), cell_coord(y))].push_back(id);
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
  int M_;
  std::vector<std::vector<int>> cells_;
};

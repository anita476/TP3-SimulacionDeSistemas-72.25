#pragma once

#include <algorithm>
#include <cstddef>
#include <iterator>
#include <vector>

// A&T HEAD/LIST: head_[c] = first id in cell c (-1 if empty);
// next_[i] = next id in i's cell (-1 at end of chain).
class LinkedCellGrid {
public:
  LinkedCellGrid(double L, double W, int Mx, int My, int n)
      : L_(L), W_(W), Mx_(Mx), My_(My),
        head_(static_cast<std::size_t>(Mx) * static_cast<std::size_t>(My),
              kNone),
        next_(static_cast<std::size_t>(n > 0 ? n : 0), kNone) {}

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
    const int c = cell_index(cell_coord_x(x), cell_coord_y(y));
    next_[static_cast<std::size_t>(id)] = head_[static_cast<std::size_t>(c)];
    head_[static_cast<std::size_t>(c)] = id;
  }

  class Iterator {
  public:
    using iterator_category = std::forward_iterator_tag;
    using value_type = int;
    using difference_type = std::ptrdiff_t;
    using pointer = const int *;
    using reference = int;

    Iterator() = default;
    Iterator(int id, const std::vector<int> *next) : id_(id), next_(next) {}

    int operator*() const { return id_; }

    Iterator &operator++() {
      id_ = (*next_)[static_cast<std::size_t>(id_)];
      return *this;
    }
    Iterator operator++(int) {
      Iterator copy = *this;
      ++*this;
      return copy;
    }

    bool operator==(const Iterator &other) const { return id_ == other.id_; }
    bool operator!=(const Iterator &other) const { return id_ != other.id_; }

  private:
    int id_ = kNone;
    const std::vector<int> *next_ = nullptr;
  };

  class Chain {
  public:
    Chain(int first, const std::vector<int> &next)
        : first_(first), next_(&next) {}

    Iterator begin() const { return Iterator(first_, next_); }
    Iterator end() const { return Iterator(kNone, next_); }
    bool empty() const { return first_ == kNone; }

  private:
    int first_;
    const std::vector<int> *next_;
  };

  Chain cell(int index) const {
    return Chain(head_[static_cast<std::size_t>(index)], next_);
  }

  void clear() { std::fill(head_.begin(), head_.end(), kNone); }

  std::size_t memory_bytes() const {
    return (head_.capacity() + next_.capacity()) * sizeof(int);
  }

  std::size_t live_blocks() const {
    return (head_.capacity() > 0 ? 1u : 0u) + (next_.capacity() > 0 ? 1u : 0u);
  }

private:
  static constexpr int kNone = -1;

  double L_;
  double W_;
  int Mx_;
  int My_;
  std::vector<int> head_;
  std::vector<int> next_;
};

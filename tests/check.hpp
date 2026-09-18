#pragma once

#include <cmath>
#include <cstdio>
#include <cstdlib>

inline int g_failures = 0;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      std::fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,    \
                   #cond);                                                     \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

#define CHECK_NEAR(a, b, tol)                                                  \
  do {                                                                         \
    const double _a = (a), _b = (b);                                           \
    if (!(std::fabs(_a - _b) <= (tol))) {                                      \
      std::fprintf(stderr, "%s:%d: CHECK_NEAR failed: %s = %.12g, %s = %.12g\n", \
                   __FILE__, __LINE__, #a, _a, #b, _b);                        \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

// Call at the end of main(): returns the process exit code for CTest.
inline int finish() {
  if (g_failures) {
    std::fprintf(stderr, "%d failure(s)\n", g_failures);
    return EXIT_FAILURE;
  }
  std::puts("ok");
  return EXIT_SUCCESS;
}

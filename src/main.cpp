#include <argparse/argparse.hpp>

int main(int argc, char *argv[]) {
  argparse::ArgumentParser program("EventDriven-TP3", "0.1",
                                   argparse::default_arguments::help);
  program.add_argument("-L").default_value(1.20).scan<'g', double>().help(
      "box side length");
  program.add_argument("-N").default_value(0).scan<'i', int>().help(
      "particle count");
  program.add_argument("-W").default_value(0.68).scan<'g', double>().help(
      "box side width");
  program.add_argument("-d").default_value(0.68).scan<'g', double>().help(
      "goal width");
  program.add_argument("-tmax").default_value(30).scan<'i', int>().help(
      "Maximum simulated time (default 30)");
  program.add_argument("-obstacles")
      .default_value(std::string(""))
      .help("Path to obstacle input file");
  program.add_argument("--out")
      .default_value(std::string(""))
      .help("simulation output path");

  try {
    program.parse_args(argc, argv);
  } catch (const std::exception &err) {
    std::cerr << err.what() << '\n';
    std::cerr << program;
    return 1;
  }
  /* generate particles*/
  /* generate grid*/ /* only for particle collisions */
  /* generate priority queue for collisions*/
  /* while t_sim < t_max , predict and update */
  return 0;
}
"""Data driven ways of improved sampling

"""
from functools import total_ordering


@total_ordering
class Interval(object):
    def __init__(self, xs, ys):
        self.xs = xs
        self.ys = ys

        self.n_extra = 0

    @property
    def delta(self):
        return (self.ys[-1] - self.ys[0]) / (1 + self.n_extra)

    def new_sample_points(self):
        # Return new x values to sample
        x_delta = (self.xs[-1] - self.xs[0]) / (1 + self.n_extra)

        return [self.xs[0] + x_delta * (i + 1) for i in range(self.n_extra)]

    def add_point(self):
        self.n_extra += 1

    def __eq__(self, other):
        return self.delta == other.delta

    def __lt__(self, other):
        return self.delta < other.delta


def propose_new_pressures(xs, ys, n_new):
    """Find new pressure values to sample based on previous

    Parameters
    ----------
    xs, ys : list
      previous results
    n_new : int
      number of new pressure values required

    Returns
    -------
    new_pressures : tuple
      tuple of new pressure values to sample
    """
    intervals = [Interval(xs=xs[i:i+2], ys=ys[i:i+2])
                 for i in range(len(xs) - 1)]
    # iteratively add new points to the largest gap
    for _ in range(n_new):
        max(intervals).add_point()
    out = []
    for i in intervals:
        out.extend(i.new_sample_points())
    return tuple(out)

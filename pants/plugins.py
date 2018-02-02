import collections
import functools

try:
    import matplotlib.pyplot as plt
    import pandas as pd
except ImportError:
    pass

from .solver import SolverPlugin


class EliteTracer(SolverPlugin):
    def __init__(self, factor=1):
        self.factor = factor

    def on_iteration(self, state, **kwargs):
        state.best.trace(self.solver.q * self.factor)


class PeriodicActionPlugin(SolverPlugin):
    def __init__(self, period=50):
        self.period = period
        self.index = None

    def initialize(self, solver):
        super().initialize(solver)
        self.index = 0

    def on_iteration(self, state, **kwargs):
        self.index = (self.index + 1) % self.period
        if not self.index:
            self.action(state, **kwargs)

    def action(self, state, **kwargs):
        pass


class PeriodicReset(PeriodicActionPlugin):
    def action(self, state, **kwargs):
        for edge in state.graph.edges:
            state.graph.edges[edge]['pheromone'] = 1


class PheromoneFlip(PeriodicActionPlugin):
    def action(self, state, **kwargs):
        data = []
        for edge in state.graph.edges.values():
            datum = edge['pheromone'], edge
            data.append(datum)
        levels, edges = zip(*data)
        for edge, level in zip(edges, reversed(levels)):
            edge['pheromone'] = level


class StatRecorder(SolverPlugin):
    def __init__(self):
        self.stats = collections.defaultdict(list)
        self.data = {'solutions': set()}

    def on_start(self, state):
        levels = [edge['pheromone'] for edge in state.graph.edges.values()]
        num_edges = len(levels)
        total_pheromone = sum(levels)

        stats = {
            'pheromone_levels': levels,
            'total_pheromone': total_pheromone,
            'edge_pheromone': {
                'min': min(levels),
                'max': max(levels),
                'avg': total_pheromone / num_edges,
            },
            'solutions': {
                'best': None,
                'worst': None,
                'avg': None,
                'global_best': None,
            },
            'unique_solutions': {
                'total': len(self.data['solutions']),
                'iteration': 0,
                'new': 0,
            }
        }
        self.pump(stats)

    def on_iteration(self, state, is_new_best):
        levels = [edge['pheromone'] for edge in state.graph.edges.values()]
        distances = [solution.weight for solution in state.solutions]

        solutions = set(state.solutions)
        solutions_seen = self.data['solutions']

        old_count = len(solutions_seen)
        solutions_seen.update(solutions)
        num_new_solutions = len(solutions_seen) - old_count

        num_edges = len(levels)
        num_ants = len(solutions)
        total_pheromone = sum(levels)

        stats = {
            'pheromone_levels': levels,
            'total_pheromone': total_pheromone,
            'edge_pheromone': {
                'min': min(levels),
                'max': max(levels),
                'avg': total_pheromone / num_edges,
            },
            'solutions': {
                'best': min(distances),
                'worst': max(distances),
                'avg': sum(distances) / num_ants,
                'global_best': state.best.weight,
            },
            'unique_solutions': {
                'total': len(self.data['solutions']),
                'iteration': len(solutions),
                'new': num_new_solutions,
            }
        }
        self.pump(stats)

    def on_finish(self, **kwargs):
        self.plot()

    def pump(self, stats):
        for stat, data in stats.items():
            self.stats[stat].append(data)

    def plot(self):
        plt.figure()
        plt.title('Solution Stats')
        self.plot_solutions()

        plt.figure()
        plt.title('Pheromone')
        self.plot_pheromone_levels()

        plt.figure()
        plt.title('Pheromone meta')
        self.plot_edge_pheromone()

        plt.figure()
        plt.title('Unique Solutions')
        self.plot_unique_solutions()

        plt.show()

    def _plot(self, stat, ax=None, **kwargs):
        data = self._extract_and_process(stat)
        data.plot(ax=ax or plt.gca(), **kwargs)

    def __getattr__(self, name):
        if name.startswith('plot_'):
            __, stat = name.split('_', 1)
            return functools.partial(self._plot, stat)
        raise AttributeError(name)

    def _extract_and_process(self, stat):
        extractor = getattr(self, f'extract_{stat}', lambda: self.stats[stat])
        processor = getattr(self, f'process_{stat}', lambda d: pd.DataFrame(d))
        return processor(extractor())

    def extract_ant_distances(self):
        iterations = []
        for distances in self.stats['ant_distances']:
            if all(d is not None for d in distances):
                distances = list(sorted(distances))
            iterations.append(distances)
        return iterations

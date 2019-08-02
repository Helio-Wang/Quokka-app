import datetime
import math
import time
import PyQt5 as qt
import PyQt5.QtWidgets as qtw
from solution import NestedSolution, SolutionGenerator
import reconciliator
import cyclicity
import enumerator
import enumerate_classes as cla
import poly_enum_class as enu
import class_reconciliator


class WorkerData:
    def __init__(self, parasite_tree, host_tree, leaf_map):
        self.parasite_tree = parasite_tree
        self.host_tree = host_tree
        self.leaf_map = leaf_map
        self.multiplier = 1000
        self.threshold = float('Inf')

    def count_solutions(self, cost_vector, task):
        recon = reconciliator.ReconciliatorCounter(self.host_tree, self.parasite_tree, self.leaf_map,
                                                   cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                                   cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                                   self.threshold, task)
        root = recon.run()
        opt_cost = root.cost / self.multiplier

        if task in (2, 3):
            reachable = cla.fill_reachable_matrix(self.parasite_tree, self.host_tree, root)
            root = cla.fill_class_matrix(self.parasite_tree, self.host_tree, self.leaf_map, reachable, task)
        return opt_cost, root

    def enumerate_solutions_setup(self, cost_vector, task, maximum):
        recon = reconciliator.ReconciliatorEnumerator(self.host_tree, self.parasite_tree, self.leaf_map,
                                                      cost_vector[0] * self.multiplier, cost_vector[1] * self.multiplier,
                                                      cost_vector[2] * self.multiplier, cost_vector[3] * self.multiplier,
                                                      self.threshold, task, maximum)
        if task in (2, 3) and maximum == float('Inf'):
            recon.solution_generator = SolutionGenerator(False)
        root = recon.run()
        opt_cost = root.cost / self.multiplier
        return opt_cost, root

    def enumerate_best_k(self, cost_vector, k):
        recon = reconciliator.ReconciliatorBestKEnumerator(self.host_tree, self.parasite_tree, self.leaf_map,
                                                           cost_vector[0] * self.multiplier,
                                                           cost_vector[1] * self.multiplier,
                                                           cost_vector[2] * self.multiplier,
                                                           cost_vector[3] * self.multiplier, self.threshold, k)
        root = recon.run()
        return root.cost / self.multiplier, recon.maximum_cost / self.multiplier, root


class CountThread(qt.QtCore.QThread):
    sig = qt.QtCore.pyqtSignal(str)

    def __init__(self):
        qt.QtCore.QThread.__init__(self)
        self.data, self.cost_vector, self.tasks = None, None, None

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.tasks = options[5:]

    def print_header(self, task):
        if task == 0:
            self.sig.emit(f'Task {task+1}: Counting the number of solutions (cyclic or acyclic)...')
        elif task == 1:
            self.sig.emit(f'Task {task+1}: Counting the number of solutions grouped by event vectors...')
        elif task == 2:
            self.sig.emit(f'Task {task+1}: Counting the number of event partitions...')
        else:
            self.sig.emit(f'Task {task+1}: Counting the number of strong equivalence classes...')

    def run(self):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.sig.emit('------')
        opt_cost = 0
        for task in self.tasks:
            self.print_header(task)

            opt_cost, root = self.data.count_solutions(self.cost_vector, task)
            if task == 0:
                self.sig.emit(f'Total number of solutions = {root.num_subsolutions}')
            elif task == 1:
                num_class = 0
                num_sol = 0
                for target_vector in root.event_vectors:
                    num_class += 1
                    self.sig.emit(f"{num_class}: {target_vector.vector} of size {target_vector.num_subsolutions}")
                    num_sol += target_vector.num_subsolutions
                self.sig.emit(f'Total number of event vectors = {num_class}')
                self.sig.emit(f'Total number of solutions = {num_sol}')
            elif task == 2:
                self.sig.emit(f'Total number of event partitions = {root.num_subsolutions}')
            else:
                self.sig.emit(f'Total number of strong equivalence classes = {root.num_subsolutions}')

            self.sig.emit('------')
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.exit(0)
        self.wait()


class EnumerateThread(qt.QtCore.QThread, enumerator.SolutionsEnumerator):
    sig = qt.QtCore.pyqtSignal(str)
    sig2 = qt.QtCore.pyqtSignal(int)

    def __init__(self):
        qt.QtCore.QThread.__init__(self, data=None, root=None, writer=None, maximum=None, acyclic=None)
        self.num_solutions, self.num_acyclic = 0, 0
        self.data, self.cost_vector, self.task, self.filename = None, None, None, None
        self.maximum, self.acyclic, self.vector, self.label_only = None, None, None, None
        self.writer = None
        self.t0 = 0

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.task = options[5]
        self.filename = options[6]
        self.maximum = options[7]
        self.acyclic = options[8]
        self.vector = options[9]
        self.label_only = options[10]
        self.num_acyclic, self.num_solutions = 0, 0
        self.writer = open(self.filename, 'w')

    def print_header(self):
        if self.task == 0:
            self.sig.emit(f'Task {self.task+1}: Enumerate {"acyclic " if self.acyclic else ""}solutions'
                          f'{" (cyclic or acyclic)" if not self.acyclic else ""}...')
        elif self.task == 1:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per event vector...')
        elif self.task == 2:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per event partition...')
        else:
            self.sig.emit(f'Task {self.task+1}: Enumerate one solution per strong equivalence class...')

    def write_header(self, opt_cost):
        self.writer.write('#--------------------\n')
        self.writer.write('#Host tree          = {}\n'.format(self.data.host_tree))
        self.writer.write('#Parasite tree      = {}\n'.format(self.data.parasite_tree))
        self.writer.write('#Host tree size     = {}\n'.format(self.data.host_tree.size()))
        self.writer.write('#Parasite tree size = {}\n'.format(self.data.parasite_tree.size()))
        self.writer.write('#Leaf mapping       = {{{}}}\n'.format(', '.join(map(lambda x: str(x[0]) + '=' + str(x[1]),
                                                                                self.data.leaf_map.items()))))
        self.writer.write('#--------------------\n')
        if self.task == 0:
            self.writer.write(f'#Task {self.task+1}: Enumerate {"acyclic " if self.acyclic else ""}solutions '
                              f'{"(cyclic or acyclic)" if not self.acyclic else ""}\n')
        elif self.task == 1:
            self.writer.write(f'#Task {self.task+1}: Enumerate one solution per event vector\n')
        elif self.task == 2:
            self.writer.write(f'#Task {self.task+1}: Enumerate one solution per event partition\n')
        else:
            self.writer.write(f'#Task {self.task+1}: Enumerate one solution per strong equivalence class\n')
        self.writer.write('#Co-speciation cost = {}\n'.format(self.cost_vector[0]))
        self.writer.write('#Duplication cost   = {}\n'.format(self.cost_vector[1]))
        self.writer.write('#Host-switch cost   = {}\n'.format(self.cost_vector[2]))
        self.writer.write('#Loss cost          = {}\n'.format(self.cost_vector[3]))
        self.writer.write('#Optimal cost       = {}\n'.format(opt_cost))
        self.writer.write('#--------------------\n')

    def run(self, label=''):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.print_header()

        self.sig2.emit(1)
        opt_cost, root = self.data.enumerate_solutions_setup(self.cost_vector, self.task, self.maximum)
        try:
            self.write_header(opt_cost)
            self.sig2.emit(5)
            self.sig.emit('------')
            self.root = root
            if self.task == 0:
                self.loop_enumerate()
            elif self.task == 1:
                self.loop_vector()
            else:
                if self.maximum == float('Inf'):
                    reachable = cla.fill_reachable_matrix(self.data.parasite_tree, self.data.host_tree, root)
                    cla_root = cla.fill_class_matrix(self.data.parasite_tree, self.data.host_tree, self.data.leaf_map,
                                                     reachable, self.task)
                    self.sig2.emit(30)
                    self.loop_classes(cla_root.num_subsolutions)
                else:
                    self.loop_classes()
            self.writer.write('#--------------------\n')
            if self.maximum == float('Inf'):
                if self.task == 0 and self.acyclic:
                    self.sig.emit(f'Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}')
                    self.writer.write(f'#Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}\n')
                else:
                    self.sig.emit(f'Number of solutions = {self.num_acyclic}')
                    self.writer.write(f'#Number of solutions = {self.num_acyclic}\n')
            else:
                self.sig.emit(f'Number of output solutions = {self.num_acyclic} (maximum {self.maximum})')
                self.writer.write(f'#Number of output solutions = {self.num_acyclic} (maximum {self.maximum})\n')
        except ValueError:
            return
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('Output written to {}'.format(self.filename))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(0)

    def abort(self):
        self.sig.emit('------')
        self.sig.emit(f'Job aborted at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(1)

    def visit_vector(self, solution, target_vector):
        if solution.composition_type == NestedSolution.MULTIPLE:
            for child in solution.children:
                if target_vector in child.event_vectors:
                    self.visit_vector(child, target_vector)
                    return
        elif solution.composition_type == NestedSolution.FINAL:
            self.current_mapping[solution.association.parasite] = solution.association.host
            self.current_text.append(str(solution.association))
        else:
            self.current_mapping[solution.association.parasite] = solution.association.host
            self.current_text.append(str(solution.association))

            for left_vector in solution.children[0].event_vectors:
                for right_vector in solution.children[1].event_vectors:
                    new_vec = left_vector.cartesian(right_vector, solution.event, solution.num_losses)
                    if new_vec == target_vector:
                        self.visit_vector(solution.children[0], left_vector)
                        self.visit_vector(solution.children[1], right_vector)
                        return

    def loop_vector(self):
        percentage = 5
        num_class = 0
        for target_vector in self.root.event_vectors:
            self.current_text = []
            self.current_mapping = {}
            num_class += 1
            if num_class >= self.maximum:
                break
            self.visit_vector(self.root, target_vector)
            self.writer.write(', '.join(self.current_text))
            self.writer.write(f'\n[{num_class if not self.vector else str(target_vector.vector)}]\n')
            if self.maximum == float('Inf'):
                new_percentage = math.ceil(100 * num_class / len(self.root.event_vectors))
            else:
                new_percentage = math.ceil(100 * num_class / self.maximum)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)
        self.num_acyclic = num_class

    def loop_enumerate(self):
        percentage = 5
        while True:
            self.current_mapping = {}
            self.current_text = []
            self.transfer_candidates = []

            self.num_solutions += 1
            current_cell = self.root
            iterator = enumerator.SolutionIterator(self.root)
            while not iterator.done():
                current_cell = self.get_next(current_cell, iterator)
            self.clean_stack()

            is_acyclic = False
            if self.acyclic:
                transfer_edges = cyclicity.find_transfer_edges(self.data.host_tree,
                                                               self.current_mapping, self.transfer_candidates)
                if not transfer_edges:
                    is_acyclic = True
                else:
                    is_acyclic = cyclicity.is_acyclic_stolzer(self.current_mapping, transfer_edges)

            if not self.acyclic or is_acyclic:
                self.num_acyclic += 1
                self.writer.write(', '.join(self.current_text))
                self.writer.write(f'\n[{self.num_acyclic}]\n')

            if not self.merge_stack:
                break
            if self.num_acyclic >= self.maximum:
                break

            if self.maximum == float('Inf'):
                new_percentage = math.ceil(100 * self.num_acyclic / self.root.num_subsolutions)
            else:
                new_percentage = math.ceil(100 * self.num_acyclic / self.maximum)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)

    def loop_classes(self, total_classes=0):
        percentage = 30 if self.maximum == float('Inf') else 5
        num_class = 0
        class_enumerator = enu.ClassEnumerator(self.data.parasite_tree, self.root, self.task)
        for mapping, events in class_enumerator.run():
            num_class += 1
            if self.label_only:
                current_text = []
                for p in self.data.parasite_tree:
                    current_text.append(f'{str(p)}@{"?" if not mapping[p] else str(mapping[p])}|'
                                        f'{"CDS L"[events[p]]}')
                self.writer.write(', '.join(current_text))
                self.writer.write(f'\n[{num_class}]\n')
            else:
                recon_bis = class_reconciliator.ReconValidator(self.data.host_tree, self.data.parasite_tree,
                                                               self.data.leaf_map,
                                                               self.cost_vector[0] * self.data.multiplier,
                                                               self.cost_vector[1] * self.data.multiplier,
                                                               self.cost_vector[2] * self.data.multiplier,
                                                               self.cost_vector[3] * self.data.multiplier,
                                                               float('Inf'), self.task,
                                                               mapping, events)
                root_bis = recon_bis.run()
                recon_enumerator = enumerator.SolutionsEnumerator(self.data, root_bis, self.writer, 1, False)
                recon_enumerator.run(label=str(num_class))

            if num_class >= self.maximum:
                break
            if self.maximum == float('Inf'):
                new_percentage = math.ceil(100 * num_class / total_classes)
            else:
                new_percentage = math.ceil(100 * num_class / self.maximum)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)
        self.num_acyclic = num_class


class BestKEnumerateThread(qt.QtCore.QThread, enumerator.SolutionsEnumerator):
    sig = qt.QtCore.pyqtSignal(str)
    sig2 = qt.QtCore.pyqtSignal(int)

    def __init__(self):
        qt.QtCore.QThread.__init__(self, data=None, root=None, writer=None, maximum=None, acyclic=None)
        self.num_solutions, self.num_acyclic = 0, 0
        self.data, self.cost_vector, self.filename = None, None, None
        self.k, self.acyclic = None, None
        self.writer = None
        self.t0 = 0

    def on_source(self, options):
        self.data = options[0]
        self.cost_vector = options[1:5]
        self.filename = options[5]
        self.k = options[6]
        self.acyclic = options[7]
        self.num_acyclic, self.num_solutions = 0, 0
        self.writer = open(self.filename, 'w')

    def write_header(self, opt_cost, max_cost):
        self.writer.write('#--------------------\n')
        self.writer.write('#Host tree          = {}\n'.format(self.data.host_tree))
        self.writer.write('#Parasite tree      = {}\n'.format(self.data.parasite_tree))
        self.writer.write('#Host tree size     = {}\n'.format(self.data.host_tree.size()))
        self.writer.write('#Parasite tree size = {}\n'.format(self.data.parasite_tree.size()))
        self.writer.write('#Leaf mapping       = {{{}}}\n'.format(', '.join(map(lambda x: str(x[0]) + '=' + str(x[1]),
                                                                                self.data.leaf_map.items()))))
        self.writer.write('#--------------------\n')
        if self.acyclic:
            self.writer.write('Enumerate acyclic solutions among the best K solutions\n')
        else:
            self.writer.write('Enumerate the best K solutions\n')
        self.writer.write('#Co-speciation cost = {}\n'.format(self.cost_vector[0]))
        self.writer.write('#Duplication cost   = {}\n'.format(self.cost_vector[1]))
        self.writer.write('#Host-switch cost   = {}\n'.format(self.cost_vector[2]))
        self.writer.write('#Loss cost          = {}\n'.format(self.cost_vector[3]))
        self.writer.write('#K                  = {}\n'.format(self.k))
        self.writer.write('#Optimal cost       = {}\n'.format(opt_cost))
        self.writer.write('#Maximum cost       = {}\n'.format(max_cost))
        self.writer.write('#--------------------\n')

    def run(self, label=''):
        self.sig.emit('===============')
        self.sig.emit(f'Job started at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.t0 = time.time()
        self.sig.emit(f'Cost vector: {tuple(self.cost_vector)}')
        self.sig.emit(f'K = {self.k}')
        if self.acyclic:
            self.sig.emit('Enumerate acyclic solutions among the best K solutions...')
        else:
            self.sig.emit('Enumerate the best K solutions...')

        self.sig2.emit(1)
        opt_cost, max_cost, root = self.data.enumerate_best_k(self.cost_vector, self.k)
        try:
            self.write_header(opt_cost, max_cost)
            self.sig2.emit(5)
            self.sig.emit('------')
            self.root = root
            self.loop_enumerate()
            self.writer.write('#--------------------\n')
            if self.acyclic:
                self.sig.emit(f'Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}')
                self.writer.write(f'#Number of acyclic solutions = {self.num_acyclic} out of {self.num_solutions}\n')
            else:
                self.sig.emit(f'Number of output solutions = {self.num_acyclic}')
                self.writer.write(f'#Number of output solutions = {self.num_acyclic}\n')
        except ValueError:
            return
        self.sig.emit('Optimal cost = {}'.format(opt_cost))
        self.sig.emit('Maximum cost = {}'.format(max_cost))
        self.sig.emit('Output written to {}'.format(self.filename))
        self.sig.emit('------')
        self.sig.emit(f'Job finished at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(0)

    def abort(self):
        self.sig.emit('------')
        self.sig.emit(f'Job aborted at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.sig.emit(f'Time elapsed: {time.time() - self.t0:.2f} s')
        self.sig.emit('===============')
        self.sig.emit('')
        self.writer.close()
        self.exit(1)

    def loop_enumerate(self):
        percentage = 5
        while True:
            self.current_mapping = {}
            self.current_text = []
            self.transfer_candidates = []

            self.num_solutions += 1
            current_cell = self.root
            iterator = enumerator.SolutionIterator(self.root)
            while not iterator.done():
                current_cell = self.get_next(current_cell, iterator)
            self.clean_stack()

            is_acyclic = False
            if self.acyclic:
                transfer_edges = cyclicity.find_transfer_edges(self.data.host_tree,
                                                               self.current_mapping, self.transfer_candidates)
                if not transfer_edges:
                    is_acyclic = True
                else:
                    is_acyclic = cyclicity.is_acyclic_stolzer(self.current_mapping, transfer_edges)

            if not self.acyclic or is_acyclic:
                self.num_acyclic += 1
                self.writer.write(', '.join(self.current_text))
                self.writer.write(f'\n[{self.num_acyclic}]\n')

            if not self.merge_stack:
                break
            new_percentage = math.ceil(100 * self.num_acyclic / self.k)
            if new_percentage > percentage:
                percentage = new_percentage
                self.sig2.emit(int(percentage))
        self.sig2.emit(100)



"""
# Project Graph processing tools.

# Provides &Queue for managing the processing of projects in dependency order.
# Usage:

#!/pl/python
	from fault.system import files, query
	from fault.projects import root, graph
	ctx = root.Context()
	# Configure paths making up the project context.
	ctx.connect(query.pwd())
	ctx.load()
	q = Queue()
	ext = q.dispatch(ctx)

	def process(projects):
		## Simply print dependency order for this example.
		for x in projects:
			print(x)
		return projects # Signals completion in this example.

	## Unconditionally take initial jobset.
	jobs = list(q.take(4))
	while not q.terminal() and jobs:
		finished_set = process(jobs)
		## Notify queue state of completions.
		jobs = list(q.finish(*finished_set).take(4))

# [ Engineering ]

# The functions here could be easily refactored into a properly generalized form, but
# considering the code size and the benefits of a self-contained implementation,
# it seemed reasonable to leave the weight here. Even in the case of some duplicate
# effort, this should likely stay as-is.
"""
import typing
import collections
import itertools

def collect(context):
	"""
	# Collect the projects and requirements from the &root.Context instance.
	"""
	pj_seq = list()
	local = collections.defaultdict(set)
	for pj in context.iterprojects():
		pj_seq.append(pj.identifier)
		if pj.infrastructure:
			i = set(itertools.chain.from_iterable(pj.infrastructure.values()))
			for rq in i:
				local[rq].add(pj.identifier)

	return pj_seq, local

def structure(collected):
	"""
	# Structure the projects and the required factors produced by &collect
	# into a graph that may be processed with &sequence.
	"""
	projects, local = collected
	pjs = set(projects)
	external = {}
	graphed = set()

	# Inverted requirements.
	irq = collections.defaultdict(set)

	# Counter can be used here as well, but default to dict(set)
	# so that precise status can be observed.
	req = collections.defaultdict(set)

	for rq in list(local):
		if rq[0] not in pjs:
			external[rq] = local.pop(rq)
		else:
			deps = local[rq]
			deps.discard(rq[0])

			if not deps or not rq[1]:
				# self pointer
				del local[rq]
				continue
			else:
				graphed.update(deps)
				graphed.add(rq[0])

			for x in deps:
				req[x].add(rq[0])
				irq[rq[0]].add(x)

	return external, graphed, (req, irq)

def sequence(pair):
	"""
	# Sequence the nodes of a project graph according to the completion order recognized
	# from the generator send calls.
	"""
	req, irq = pair
	complete = (yield [x for x in irq if x not in req])
	while req:
		ns = []
		for c in complete:
			for r in irq.pop(c, ()):
				req[r].discard(c)
				if not req[r]:
					ns.append(r)
					del req[r]

		complete = (yield ns)

class Queue(object):
	"""
	# State object for processing projects in dependency order.
	"""

	def __init__(self):
		"""
		# Allocate instance; follow with &dispatch.
		"""
		self._count = 0
		self._processed = 0
		self._status = None
		self._gs = None
		self._pending = set()
		self._storage = collections.deque()

	def dispatch(self, context:'.root.Context') -> 'Queue':
		"""
		# Dispatch the given &context into the queue.

		# Returns any out-of-context requirements.
		"""
		if self._gs is not None:
			raise Exception("project queue already dispatched context")

		projects, local = collect(context)
		projects.sort()
		self._count = len(projects)

		ext, graphed, g = structure((projects, local))
		self._status = g[0] # Requirements
		self._gs = sequence(g)

		# Graphed projects are given priority in order to ensure maximum saturation.
		self._storage.extend(sorted(self._gs.send(None)))
		self._pending.update(self._storage)

		# Extend in project index order.
		self._storage.extend(x for x in projects if x not in graphed)

		return ext

	def status(self):
		"""
		# A tuple of integers telling how many projects have been reported as
		# finished and the total number of projects.
		"""
		return (self._processed, self._count)

	def finish(self, *projects):
		"""
		# Note the projects as being processed.

		# Returns instance for chaining with &take.
		"""
		self._processed += len(projects)

		if not self._pending:
			return self

		self._pending.difference_update(projects)

		try:
			ns = self._gs.send(projects)
		except StopIteration:
			pass
		else:
			ns.sort()
			self._storage.extendleft(ns)
			self._pending.update(ns)

		return self

	def take(self, quantity) -> typing.Iterator[object]:
		"""
		# Retrieve enqueued project IIDs in graph order.
		"""
		try:
			for i in range(quantity):
				yield self._storage.popleft()
		except IndexError:
			pass

	def terminal(self) -> bool:
		"""
		# Whether or not the queue has released all projects via &take.

		# This can return &True prior to a final finish call.
		"""
		return not bool(self._storage or self._status)

if __name__ == '__main__':
	# Print dependency order of the projects within the product paths supplied as argv.
	import sys
	from ..system import files
	from . import root

	ctx = root.Context()
	for x in map(files.Path.from_path, sys.argv[1:]):
		ctx.connect(x)
	ctx.load()

	q = Queue()
	q.dispatch(ctx)
	def _rprint(p):
		for x in p:
			print(x)
		return p

	## Unconditionally take initial jobset.
	jobs = list(q.take(1))
	while not q.terminal() and jobs:
		finished_set = _rprint(jobs)
		## Notify queue state of completions.
		jobs = list(q.finish(*finished_set).take(1))

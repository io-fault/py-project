"""
# Product directory protocol support.
"""
import typing
import collections
import operator
import itertools

from .. import routes

from . import types

def parse_project_index(lines:typing.Iterable[str]):
	"""
	# Generate tuples from the given space separated fields, &lines.
	# Intended to be interpreted as a dictionary, the items' initial element should
	# be the project's (universal) identifier. The second element is a tuple of the
	# local name and project protocol identifier.
	"""
	for l in lines:
		l = l.strip().split()
		yield (l[0], (types.factor@l[1],) + tuple(l[2:]))

def parse_context_index(lines:typing.Iterable[str], Prefix=types.factor) -> typing.Set[types.FactorPath]:
	"""
	# Interpret the lines in the iterable as &types.FactorPath instances.
	"""
	for l in lines:
		yield Prefix@l.strip()

def parse_protocol_declaration(text:str):
	"""
	# Split the text and return the fields as a tuple.
	"""
	return tuple(text.split())

def scan_product_directory(
		iscontext, read_protocol, route:routes.Selector,
		roots:typing.Iterable[types.FactorPath]=(), limit=1024*4
	):
	"""
	# Identify roots, contexts, and projects within the given route.

	# If the &roots argument is provided, it is emitted back and inhibits filesystem
	# based discovery of root paths.

	# Usually only used through &Product.update.
	"""
	i = 0
	stack = collections.deque()

	# Special cases for the roots.
	# Produces additional root entries.
	if roots:
		for fp in roots:
			yield ('root', fp)

			d = route//fp
			if iscontext(d):
				yield ('context', fp)
				stack.append(d)
			else:
				p = read_protocol(d)
				if p is not None:
					yield ('project', (p[0], (fp,) + p[1:]))
				else:
					# Explicit root was not a context or a project.
					pass
	else:
		for d in route.fs_iterfiles('directory'):
			i += 1
			if i > limit:
				raise RuntimeError("filesystem scan limit exceeded")

			if '.' in d.identifier:
				continue

			fp = types.FactorPath.from_sequence(d.segment(route))
			if iscontext(d):
				yield ('root', fp)
				yield ('context', fp)
				stack.append(d)
			else:
				p = read_protocol(d)
				if p is not None:
					yield ('root', fp)
					yield ('project', (p[0], (d,) + p[1:]))

	while stack:
		current = stack.popleft()

		for d in current.fs_iterfiles('directory'):
			i += 1
			if i > limit:
				raise RuntimeError("filesystem scan limit exceeded")

			if '.' in d.identifier:
				continue

			if iscontext(d):
				fp = types.FactorPath.from_sequence(d.segment(route))
				yield ('context', fp)
				stack.append(d)
			else:
				p = read_protocol(d)
				if p is not None:
					fp = types.FactorPath.from_sequence(d.segment(route))
					yield ('project', (p[0], (fp,) + p[1:]))

# Project protocol implementations.
protocols = {
	'factors/polynomial-1': (__package__ + '.polynomial', 'V1'),
}

class Product(object):
	"""
	# Project set root providing access to contexts and projects.

	# While often annotated as &routes.Selector, usually filesystem operation must be
	# supported by the selector.
	"""

	default_meta_directory = routes.Segment.from_sequence(['.product'])
	protocol_declaration_filenames = [
		'.factor-protocol',
		'.protocol',
	]

	@classmethod
	def import_protocol(Class, identifier:str) -> types.Protocol:
		"""
		# Retrieve the protocol class using the &identifier.
		"""
		module_name, classname = protocols[identifier]
		import importlib
		module = importlib.import_module(module_name)
		return getattr(module, classname)

	@property
	def project_index_route(self, filename='PROJECTS') -> routes.Selector:
		"""
		# Materialized project index file path.
		"""
		return self.cache/filename

	@property
	def context_index_route(self, filename='CONTEXTS') -> routes.Selector:
		"""
		# Materialized project index file path.
		"""
		return self.cache/filename

	@property
	def root_index_route(self, filename='ROOTS') -> routes.Selector:
		"""
		# Materialized project index file path.
		"""
		return self.cache/filename

	def __init__(self, route:routes.Selector, limit:int=1024*4, cache:routes.Selector=None):
		"""
		# Initialize a &Product using &route with an empty local instance cache.

		# &cache parameter is available as an override for the (filename)`.product`
		# directory location, but should normally not be used.
		"""
		self.clear()
		self.route = route.delimit()
		self.limit = limit

		if cache is None:
			self.cache = self.route // self.default_meta_directory

	def __hash__(self):
		return hash(self.route)

	def __eq__(self, operand):
		return self.route == operand.route

	def identifier_by_factor(self, factor:types.FactorPath) -> typing.Tuple[str, types.Protocol]:
		"""
		# Select the project identifier and protocol using a factor path (to the project).
		# Uses the instance local cache populated by &load or &update.
		"""
		ids, proto = self.local[factor]
		return ids, self.import_protocol(proto)

	def factor_by_identifier(self, identifier:str) -> typing.Tuple[types.FactorPath, types.Protocol]:
		"""
		# Select the factor path (to the project) and protocol using the project identifier.
		# Uses the instance local cache populated by &load or &update.
		"""
		ids, proto = self.projects[identifier]
		return ids, self.import_protocol(proto)

	def read_protocol(self, route:routes.Selector):
		"""
		# Retrieve the protocol data from the dot-protocol file
		# contained in &route.

		# &None if no protocol file is present.
		"""
		for x in self.protocol_declaration_filenames:
			if (route/x).fs_type() == 'data':
				return parse_protocol_declaration((route/x).get_text_content())
		return None

	def check_context_status(self, route:routes.Selector) -> bool:
		"""
		# Determines whether the given route is a context (enclosure).
		"""
		if (route/'context').fs_type() == 'directory':
			if self.read_protocol(route/'context') is not None:
				return True
		return False

	@property
	def _spec(self):
		return (self.check_context_status, self.read_protocol, self.route)

	def clear(self):
		"""
		# Remove the instance local cache.
		"""
		self.local = {}
		self.projects = {}
		self.contexts = set()
		self.roots = set()

	def load(self):
		"""
		# Load the snapshot of the projects and contexts data from the product's route.
		"""

		with self.project_index_route.fs_open('tr') as f:
			prj = dict(parse_project_index(f.readlines()))

		with self.context_index_route.fs_open('tr') as f:
			ctx = set(parse_context_index(f.readlines()))

		with self.root_index_route.fs_open('tr') as f:
			roots = set(types.factor@x for x in f.read().split() if x)

		local = {v[0]: (k,) + v[1:] for k, v in prj.items()}

		self.projects = prj
		self.contexts = ctx
		self.local = local
		self.roots = roots

		return self

	def store(self, SortKey=operator.itemgetter(0), Chain=itertools.chain.from_iterable):
		"""
		# Store the snapshot of the projects and contexts data to the product's route.
		"""

		if self.cache.fs_type() != 'directory':
			self.cache.fs_mkdir()

		prjseq = [(k,) + v for k, v in self.projects.items()]
		prjseq.sort(key=SortKey)
		with self.project_index_route.fs_open('tw') as f:
			f.writelines(Chain(' '.join(map(str, x))+'\n' for x in prjseq))

		ctxseq = list(self.contexts)
		ctxseq.sort(key=SortKey)
		with self.context_index_route.fs_open('tw') as f:
			f.writelines(x+'\n' for x in map(str, ctxseq))

		rootseq = list(self.roots)
		rootseq.sort()
		with self.root_index_route.fs_open('tw') as f:
			f.write('\n'.join(map(str, rootseq)))

		return self

	def update(self):
		"""
		# Update the snapshot of the projects and contexts by querying
		# the route's hierarchy. The effects of this should be recorded with
		# a subsequent call to &store.
		"""
		slots = {
			'context': [],
			'project': [],
			'root': [],
		}
		for k, v in scan_product_directory(*self._spec, roots=self.roots, limit=self.limit):
			slots[k].append(v)

		projects = dict(slots['project'])
		local = {v[0]: (k,) + v[1:] for k, v in projects.items()}

		self.roots, self.contexts, self.projects, self.local = (
			set(slots['root']),
			set(slots['context']),
			projects,
			local,
		)

		return self

	def itercontexts(self, limit=1024, prefix=types.factor):
		"""
		# Query the route and retrieve all contexts within the product.

		# Results may be inconsistent with the instance cache.
		"""
		i = 0
		start = self.route//prefix
		stack = collections.deque()
		stack.append(start)

		while stack:
			current = stack.popleft()
			for d in current.fs_iterfiles('directory'):
				i += 1
				if i > limit:
					raise RuntimeError("filesystem scan limit exceeded")

				if self.check_context_status(d):
					stack.append(d)
					yield d

	def iterprojects(self, limit=2048, prefix=types.factor):
		"""
		# Query the route and retrieve all projects within the product.

		# Results may be inconsistent with the instance cache.
		"""
		i = 0
		start = self.route//prefix
		stack = collections.deque()

		p = self.read_protocol(start)
		if p is not None:
			return p + (start,)

		stack.append(start)

		while stack:
			current = stack.popleft()
			for d in current.fs_iterfiles('directory'):
				i += 1
				if i > limit:
					raise RuntimeError("filesystem scan limit exceeded")

				p = self.read_protocol(d)
				if p is None and self.check_context_status(d):
					stack.append(d)
				else:
					yield p + (d,)

if __name__ == '__main__':
	import sys
	from ..system import files
	path, *roots = sys.argv[1:]
	pd = Product(files.Path.fs_select(path))
	if roots:
		pd.roots = set(types.factor@x for x in roots)
	pd.update()
	pd.store()

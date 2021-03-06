"""
# Product and Project directory protocol support.

# Provides three classes of interest: &Project, &Product, and &Context.
# Context manages a project set formed from a sequence of Products that make up a factor search path;
# Projects are cached on Context instances and Products primarily provide access and updates to a
# product directory's index, the (filename)`.product` directory.

# Even in the case of single product directories, a Context should be used to access the projects.
# The primary function of a &Product instance is to merely provide access to the data stored in the index,
# not as a general purpose abstraction for interacting with the product directory as that function usually
# involves multiple directories, an abstraction provided by &Context.
"""
import typing
import collections
import operator
import itertools

from ..context import tools
from ..route.types import Selector, Segment
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
		iscontext, read_protocol, route:Selector,
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
					yield ('project', (p[0], (types.factor // d.segment(route),) + p[1:]))

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

	# While often annotated as &Selector, usually filesystem operation must be
	# supported by the selector.
	"""

	default_meta_directory = Segment.from_sequence(['.product'])
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
	def project_index_route(self, filename='PROJECTS') -> Selector:
		"""
		# Materialized project index file path.
		"""
		return self.cache/filename

	@property
	def context_index_route(self, filename='CONTEXTS') -> Selector:
		"""
		# Materialized project index file path.
		"""
		return self.cache/filename

	@property
	def root_index_route(self, filename='ROOTS') -> Selector:
		"""
		# Materialized project index file path.
		"""
		return self.cache/filename

	@property
	def connections_index_route(self, filename='CONNECTIONS') -> Selector:
		"""
		# Connection list fulfilling requirements.
		"""
		return self.cache/filename

	@property
	def connections(self):
		"""
		# The requirements of the product as a sequence of product directory routes.

		# This sequence is not cached and constructed at access time by opening the
		# file &connections_index_route.
		"""
		rpath = self.route.container
		try:
			paths = self.connections_index_route.get_text_content()
		except FileNotFoundError:
			return []
		else:
			return list(rpath@x for x in paths.split('\n') if x)

	def __init__(self, route:Selector, limit:int=1024*4, cache:Selector=None):
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

	def select(self, constraint:types.FactorPath) -> typing.Iterable[types.FactorPath]:
		"""
		# Retrieve project (path) entries that have the given prefix, &constraint.

		# If the argument identifies a context, generate the projects contained therein.
		# If the argument is a nil &types.FactorPath, generate all project paths.
		"""

		if constraint in self.contexts:
			prefix = str(constraint) + '.'
			for p in self.local:
				if str(p).startswith(prefix):
					yield p
		elif constraint in self.local:
			yield constraint
		elif len(constraint) == 0:
			yield from self.local
		else:
			# No match.
			pass

	def read_protocol(self, route:Selector):
		"""
		# Retrieve the protocol data from the dot-protocol file
		# contained in &route.

		# &None if no protocol file is present.
		"""
		for x in self.protocol_declaration_filenames:
			if (route/x).fs_type() == 'data':
				return parse_protocol_declaration((route/x).get_text_content())
		return None

	def check_context_status(self, route:Selector) -> bool:
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
		# the filesystem. The effects of this should be recorded with
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

	def split(self, fpath:types.FactorPath):
		"""
		# Separate the project portion from &fpath.
		# Returns a pair of &types.FactorPath; the project and the factor.
		"""
		if fpath in self.local:
			return (fpath, types.factor)

		suffix = str(fpath)
		for x in self.local:
			xstr = str(x)
			if suffix.startswith(xstr + '.'):
				return (x, types.factor@suffix[len(xstr)+1:])

class Project(object):
	"""
	# Project Interface joining relavant routes and protocol instances.
	"""

	def __init__(self, pd:Product, pi:str, pf:types.FactorPath, proto:types.Protocol):
		self.product = pd
		self.protocol = proto

		self.identifier = pi
		self.factor = pf
		self.route = self.product.route//pf

	@tools.cachedproperty
	def _iid_corpus_name_pair(self):
		p = self.identifier.rstrip('/').rsplit('/', 1)
		if len(p) < 2:
			# If there is no '/', presume it's just a name.
			p.insert(0, '')
		return tuple(p)

	@property
	def corpus(self) -> str:
		"""
		# The leading portion of the independent identifier.
		"""
		return self._iid_corpus_name_pair[0]

	@property
	def name(self) -> str:
		"""
		# The name of the project as defined by the independent identifier.
		"""
		return self._iid_corpus_name_pair[1]

	@tools.cachedproperty
	def information(self) -> types.Information:
		"""
		# The identifying information of the project.
		"""
		return self.protocol.information(self.route)

	@tools.cachedproperty
	def infrastructure(self):
		"""
		# The infrastructure symbols identifying the requirements of the project.
		"""
		return self.protocol.infrastructure(self.absolute, self.route)

	@tools.cachedproperty
	def canonical(self) -> types.FactorPath:
		"""
		# The canonical factor path that is used to refer to the project.
		"""
		pd = self.product
		path = []
		for fpath in reversed(list(self.itercontexts())):
			pj_route = pd.route // fpath
			iid, Proto = pd.identifier_by_factor(fpath)
			p = Proto({})
			ctxname = p.information(pj_route).name
			path.append(ctxname)

		path.append(self.information.name)
		return types.FactorPath.from_sequence(path)

	def image(self, variants, fp:types.FactorPath, suffix='i'):
		return self.protocol.image(self.route, variants, fp, suffix=suffix)

	def itercontexts(self) -> typing.Iterable[types.FactorPath]:
		"""
		# Generate &types.FactorPath instances identifying the context project stack.
		# Order is near to far.
		"""
		for x in ~(self.factor ** 1):
			yield x/'context'

	def relative(self, fpath:str):
		"""
		# Transform a (possibly project relative) factor path string into
		# a project path, factor path pair.

		# If the &fpath does not start with a series of periods(`.`), this
		# is equivalent to &Product.split.
		"""

		if fpath.startswith('.'):
			product_relative = (self.factor/'project')@fpath
		else:
			product_relative = types.factor@fpath

		return self.product.split(product_relative)

	def absolute(self, fpath:str):
		"""
		# Get the (project identifier, factor path) pair from the given project relative factor path.
		"""
		pj, fp = self.relative(fpath)
		return (self.product.local[pj][0], fp)

	def select(self, factor:types.FactorPath):
		"""
		# Retrieve factors within the given path.
		"""
		for fp, fd in self.protocol.iterfactors(self.route, factor):
			yield ((factor//fp[0], fp[1]), fd)

	def split(self, fp:types.FactorPath, chain=itertools.chain):
		"""
		# Separate the factor path from the element path.
		# Returns a pair, &types.FactorPath and a &str; the project and the factor.
		"""

		xstr = str(fp)
		last = fp
		for p in chain(~fp.container, (types.factor,)):
			for ((f, t), srcdata) in self.select(p):
				if f == last:
					return (f, xstr[len(str(f)) + 1:])

			last = p

		return None

	def fullsplit(self, qpath:types.FactorPath):
		"""
		# Separate the project path, factor path, and fragment path
		# from the given fully qualified factor path.
		"""
		pj, fp = self.product.split(qpath)
		fp, fm = self.split(fp)
		return (pj, fp, fm)

class Context(object):
	"""
	# &Product and &Project instance cache and search path.
	"""

	@classmethod
	def import_protocol(Class, identifier:str) -> typing.Type[types.Protocol]:
		"""
		# Retrieve the protocol class using the &identifier.
		"""
		module_name, classname = protocols[identifier]
		import importlib
		module = importlib.import_module(module_name)
		return getattr(module, classname)

	@classmethod
	def from_product_connections(Class, pd:Product):
		"""
		# Create a &Context initializing it with the immediate connections identified by &pd.
		"""
		i = Class()
		for pdr in pd.connections:
			i.connect(pdr)
		return i

	def __init__(self):
		self.product_sequence = []
		self.instance_cache = {}

	def connect(self, route:Selector) -> Product:
		"""
		# Add a new Product instance to the context.

		# Returns an existing &Product instance if the route was in the cache, otherwise
		# creates a new instance and places it in the cache.
		"""
		key = ('product', route)
		if key in self.instance_cache:
			return self.instance_cache[key]

		pd = Product(route)
		pd.load()

		self.product_sequence.append(pd)
		self.instance_cache[key] = pd
		return pd

	def project(self, id:str) -> Project:
		"""
		# Retrieve a &Project instance from the context's instance cache.

		# [ Exceptions ]
		# /&LookupError/
			# No project with the given identifier has been loadded in the context.
		"""
		return self.instance_cache[('project', id)]

	def itercontexts(self, pj:Project) -> typing.Iterable[Project]:
		"""
		# Generate &Project instances representing the leading contexts of the given Project, &pj.
		"""
		pd = pj.product
		for pj_ctx_path in pj.itercontexts():
			id = pd.identifier_by_factor(pj_ctx_path)[0]
			yield self.project(id)

	def iterprojects(self) -> typing.Iterable[Project]:
		"""
		# Generate &Project instances cached from a prior &load call.

		# This includes any Context Projects.
		"""
		for key, pj in self.instance_cache.items():
			if key[0] == 'project':
				yield pj

	def symbols(self, pj:Project) -> typing.Mapping:
		"""
		# Construct a snapshot of symbols for the project with respect to the given &context.
		"""
		projects = list(self.itercontexts(pj))
		projects.reverse()
		projects.append(pj)

		# Reverse order chain map. Symbols defined nearest to project have priority.
		return collections.ChainMap(*(pj.infrastructure for pj in projects))

	def load(self):
		"""
		# Fully populate the instance cache with all of the projects from
		# all of the connected products.
		"""
		for pd in reversed(self.product_sequence):
			for id, (fp, proto_id) in pd.projects.items():
				key = ('project', id)
				proto = self.import_protocol(proto_id)
				self.instance_cache[key] = Project(pd, id, fp, proto({}))

	def configure(self):
		"""
		# Traverse the cached projects and apply protocol inheritance.
		"""

		# Get all the Context Projects in the Environment Context.
		ctxlist = list()
		for pd in reversed(self.product_sequence):
			for ctxname in pd.contexts:
				ctxlist.append(ctxname)
		ctxlist.sort(key=(lambda k: str(k).count('.')))

		# Sorted by the context's path depth, inherit the leading contexts and descend.
		for ctxname in ctxlist:
			pd, pj, ff = self.split(str(ctxname/'context'/'factor-placeholder'))

			for ascending in self.itercontexts(pj):
				ctxproto = ascending.protocol
				break
			else:
				ctxproto = None

			pj.protocol.inherit(ctxproto, pj.infrastructure.items())

		# Inherit protocol data.
		for pj in (v for k, v in self.instance_cache.items() if k[0] == 'project'):
			for ctx in self.itercontexts(pj):
				ctxproto = ctx.protocol
				break
			else:
				ctxproto = None
			pj.protocol.inherit(ctxproto, pj.infrastructure.items())

	def index(self, product:Selector):
		"""
		# Find the index of the &Product whose route is equal to &product.
		"""
		for i, x in enumerate(self.product_sequence):
			if x.route == product:
				return i

	def split(self, qpath:types.FactorPath):
		"""
		# Identify the product, project, and factor path of the given &qpath.
		# Returns a triple identifying the &Product, &Project, and remaining &types.FactorPath.

		# [ Parameters ]
		# /qpath/
			# The qualified factor path identifying an element, factor, or project.
		"""
		pd = None
		for pd in self.product_sequence:
			parts = pd.split(qpath)
			if parts is not None:
				break
		else:
			raise LookupError("no such project in context")

		pj, fp = parts
		iid = pd.identifier_by_factor(pj)
		pj = self.project(iid[0])

		return (pd, pj, fp)

	def image(self, variants, fp, suffix='i'):
		pd, pj, lfp = self.split(fp)
		return pj.image(variants, lfp, suffix=suffix)

if __name__ == '__main__':
	import sys
	from ..system import files
	path, *roots = sys.argv[1:]
	pd = Product(files.root@path)
	if roots:
		pd.roots = set(types.factor@x for x in roots)
	pd.update()
	pd.store()

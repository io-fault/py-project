"""
# Factored Product Data structures.

# [ IReference ]
# Python &str qualifying an object for use as a reference to a Target.

# [ ISymbols ]
# The effective contents of an (filename)`infrastructure.txt` factor.
# This is a mapping defining Infrastructure Symbols to abstract references.
# The absract references are [data] typed strings that are intended to
# be interpreted by whatever context is processing or reading them.

# [ IDocumentation ]
# The paragraph contents of an (filename)`infrastructure.txt` factor.
# Symbols containing documentation

# [ FactorType ]
# Annotation signature for factor data produced by project protocols.
"""
import typing
from dataclasses import dataclass

from .. import routes

ignored = {
	'__pycache__',
	'__f_cache__',
	'__f-cache__',
	'__f-int__',
	'.git',
	'.svn',
	'.hg',
	'.darcs',
	'.pijul',
}

class FactorPath(routes.Segment):
	"""
	# A &routes.Segment identifying a factor.

	# The path is always relative; usually relative to either a product or project.
	# Identifiers in the path exclude any filename extensions.
	"""

	def __str__(self):
		return '.'.join(self.absolute)

	def __repr__(self):
		return "(factor@%r)" %(str(self),)

	def __matmul__(self, fpath:str):
		"""
		# Relative and absolute constructor.
		"""

		if fpath[:1] == ".":
			rpath = fpath.lstrip(".")
			segment = self ** (len(fpath) - len(rpath))
		else:
			# Plain extension.
			rpath = fpath
			segment = self

		return (segment + rpath.split('.'))

factor = FactorPath(None, ())

@dataclass
class FactorContextPaths(object):
	"""
	# File System Information regarding the context of a Factor.

	# This data structure is used to hold the set of directories related to an
	# Archived Factor.

	# [ Properties ]
	# /root/
		# The route containing either the &project or the &context enclosure.
		# Also known as the Product Directory.
	# /context/
		# The context project relevant to &project.
		# &None if the project is not managed within a Project Context.
	# /project/
		# The route identifying the project.
	"""

	root: (routes.Selector) = None
	context: (FactorPath) = None
	project: (routes.Selector) = None

	@property
	def enclosure(self) -> bool:
		"""
		# Whether the original subject was referring to an enclosure.
		"""
		return self.project is None

	def select(self, factor):
		r = (self.project or (self.root//self.context))
		return r + factor.split('.')

	def factor(self):
		"""
		# Construct a project factor path.
		"""
		return FactorPath(None, tuple(self.project.segment(self.root).absolute)).delimit()

@dataclass
class Information(object):
	"""
	# Project information structure usually extracted from (filename)`project.txt`
	# files.
	"""

	identifier: (typing.Text) = None
	name: (typing.Text) = None
	icon: (typing.Mapping) = None
	abstract: (object) = None
	controller: (str) = None
	contact: (str) = None

IReference = typing.NewType('IReference', str)
IReference.__qualname__ = __name__ + '.IReference'
ISymbols = typing.Mapping[(typing.Text,typing.Collection[IReference])]

IDocumentation = typing.Mapping[(str,"'http://if.fault.io/text'")]

FactorType = typing.Tuple[
	FactorPath, # Project relative path.
	typing.Tuple[
		str, # Domain
		str, # Type
		typing.Set[str], # Symbols
		typing.Iterable[routes.Selector], # Sources
	]
]

class Protocol(object):
	"""
	# A project factor protocol.
	"""
	def __init__(self, parameters:dict):
		self.parameters = parameters

	def infrastructure(self, absolute, route) -> ISymbols:
		return {}

	def information(self, project_route) -> Information:
		raise NotImplementedError("core protocol method must be implemented by subclass")

	def iterfactors(self, route) -> typing.Iterable[FactorType]:
		raise NotImplementedError("core protocol method must be implemented by subclass")

class ProtocolViolation(Exception):
	"""
	# The route was identified as not conforming to the protocol.
	"""

"""
# Factored Projects data structures and types.

# [ ISymbols ]
# The effective contents of an (filename)`infrastructure.txt` factor.
# This is a mapping defining Infrastructure Symbols to abstract references.
# The absract references are [data] typed strings that are intended to
# be interpreted by whatever context is processing or reading them.

# [ FactorType ]
# Annotation signature for factor data produced by project protocols.
"""
import typing
from dataclasses import dataclass

from ..route.types import Segment
from ..system.files import Path

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

class FactorPath(Segment):
	"""
	# A &Segment identifying a factor.

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

	root: (Path) = None
	context: (FactorPath) = None
	project: (Path) = None

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
	# Project information structure usually extracted from (filename)`project.txt` files.

	# [ Properties ]
	# /identifier/
		# A hyperlink or literal attempting to provide a unique string that can identify the project.
	# /name/
		# The canonical local name for the project. Often, this will be the directory name used when
		# the software is installed into the given system.
	# /icon/
		# A property set defining visual symbols that can be used to identify the project.
	# /abstract/
		# A sequence of paragraphs describing the project.
		# The first sentence of the first paragraph may be used in isolation in project lists.
	# /authority/
		# An arbitrary string intended to identify the entity that controls the project.
	# /contact/
		# A string that identifies the appropriate means of contacting the authority
		# regarding the project.
	"""

	identifier: (str) = None
	name: (str) = None
	icon: (dict) = None
	abstract: (object) = None
	authority: (str) = None
	contact: (str) = None

@dataclass(eq=True, frozen=True)
class Reference(object):
	"""
	# A position independent reference to a required factor and the interpretation parameters
	# needed to properly form the relationship for integration.

	# &project and &factor are the only required fields.

	# [ Properties ]
	# /project/
		# The identifier of the project that contains the required factor.
	# /factor/
		# The project relative path to the required factor.
	# /method/
		# The type of connection that is expected to be formed between the requirement
		# and the target factor being integrated.
	# /isolation/
		# The specifier of a format, variant, or factor type.

		# For `type` methods, this is usually a reference to a language identifier.
		# For `control`, it can be the specification of a feature's variant.

		# When referring to normal requirements, this is always the factor type that should
		# be used when integration is performed.
	"""

	project: (str)
	factor: (FactorPath)
	method: (str) = None
	isolation: (str) = None

ISymbols = typing.Mapping[(str, typing.Collection[Reference])]

FactorType = typing.Tuple[
	FactorPath, # Project relative path.
	typing.Tuple[
		str, # Type
		typing.Set[str], # Symbols
		typing.Iterable[typing.Tuple[Reference, Path]], # Format References and Sources
	]
]

class Protocol(object):
	"""
	# A project factor protocol.
	"""
	def __init__(self, parameters:dict):
		self.parameters = parameters

	def infrastructure(self, absolute, route:Path) -> ISymbols:
		return {}

	def information(self, route:Path) -> Information:
		raise NotImplementedError("core protocol method must be implemented by subclass")

	def iterfactors(self, route:Path) -> typing.Iterable[FactorType]:
		raise NotImplementedError("core protocol method must be implemented by subclass")

class ProtocolViolation(Exception):
	"""
	# The route was identified as not conforming to the protocol.
	"""

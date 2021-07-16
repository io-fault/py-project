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

from ..context import tools
from ..route.types import Segment
from ..system.files import Path

ignored = {
	'__pycache__',
	'__f-int__',
	'.git',
	'.svn',
	'.hg',
	'.darcs',
	'.pijul',
}

@dataclass(eq=True, frozen=True)
class Variants(object):
	"""
	# Factor image variant specification.

	# [ Properties ]
	# /system/
		# Identifier of the runtime environment; normally, an operating system name.
		# Often, derived from (system/command)`uname`.
	# /architecture/
		# Identifier for the instruction set or format.
		# Often, derived from (system/command)`uname`.
	# /intention/
		# Identifier for the intended use of the image. Normally, (id)`optimal`.
	# /form/
		# Identifier for the specialization of the image. Normally an empty string.
		# Used in exceptional cases to allow parallel storage with the general form.
	"""

	system:(str)
	architecture:(str)
	intention:(str) = 'optimal'
	form:(str) = ''

	def __str__(self):
		if self.form:
			return "%s-%s/%s[%s]" %(self.system, self.architecture, self.intention, self.form)
		else:
			return "%s-%s/%s" %(self.system, self.architecture, self.intention)

	def get(self, key:str) -> str:
		return getattr(self, key)

@dataclass(eq=True, frozen=True)
class Format(object):
	"""
	# Source format structure holding the language and dialect.
	"""
	language:(str)
	dialect:(typing.Optional[str]) = None

	@classmethod
	def from_string(Class, string, /, separator='.'):
		"""
		# Split the format identifier by the first (char)`.` in &string.
		# Creates an instance using the first field as the &language and second
		# as the &dialect. If there is no (char)`.` or the dialect is an empty string,
		# the dialect will be &None,
		"""
		idx = string.find(separator)
		if idx == -1:
			return Class(string, None)

		return Class(string[:idx].strip(), string[idx+1:].strip() or None)

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
	# /format/
		# In the case of `type` references, &format provides access to a structured
		# form of &isolation: a &Format instance.
	"""

	project: (str)
	factor: (FactorPath)
	method: (str) = None
	isolation: (str) = None

	def isolate(self, isolation:str):
		"""
		# Reconstruct the reference replacing its isolation field the given &isolation.

		# If &isolation is already set, return &self.
		"""
		if isolation == self.isolation:
			return self
		return self.__class__(self.project, self.factor, self.method, isolation)

	def __str__(self):
		absolute = '/'.join((self.project, str(self.factor)))

		if self.isolation:
			return '#'.join((absolute, self.isolation))
		else:
			return absolute

	@property
	def format(self, /, _fmtcache=tools.cachedcalls(8)(Format.from_string)):
		"""
		# Construct the &Format instance representing the &isolation.

		# Format instances are cached and repeat reads across references
		# with the same isolation should normally return the same object.
		"""
		assert self.method == 'type'
		return _fmtcache(self.isolation)

	@classmethod
	def from_ri(Class, method:str, ri:str):
		"""
		# Create a reference from a resource indicator.
		# Splits on the fragment and the final path segment.
		"""
		fragment_offset = ri.rfind('#')
		if fragment_offset == -1:
			isolation = None
			fragment_offset = len(ri)
		else:
			isolation = ri[fragment_offset+1:]

		project_sep = ri.rfind('/', 0, fragment_offset)
		if project_sep == -1:
			factorpath = factor # Empty factor path.
			project_sep = fragment_offset
		else:
			factorpath = factor@ri[project_sep+1:fragment_offset]

		return Class(ri[:project_sep], factorpath, method, isolation)

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

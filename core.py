"""
# Factored Product Data structures.

# [ Types ]

# /IReference/
	# Python &str qualifying an object for use as a reference to a Target.
# /ISymbols/
	# The effective contents of an (filename)`infrastructure.txt` factor.
	# This is a mapping defining Infrastructure Symbols to abstract references.
	# The absract references are [data] typed strings that are intended to
	# be interpreted by whatever context is processing or reading them.
# /IDocumentation/
	# The paragraph contents of an (filename)`infrastructure.txt` factor.
	# Symbols containing documentation
"""
import typing
from dataclasses import dataclass

from fault import routes

ignored = {
	'__pycache__',
	'__f_cache__',
	'__f-cache__',
	'__f-int__',
	'.git',
	'.svn',
	'.hg',
	'.darcs',
}

@dataclass
class FactorContextPaths(object):
	"""
	# File System Information regarding the context of a Factor.

	# This data structure is used to hold the set of directories related to an
	# Archived Factor.

	# [ Properties ]
	# /root/
		# The route containing either the &project or the &context enclosure.
	# /context/
		# The context project relevant to &project.
		# &None if the project is not managed within a Project Context.
	# /project/
		# The route identifying the project.
	"""

	root: (routes.Selector) = None
	context: (routes.Segment) = None
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

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

from fault.routes import types as routes

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
	# /category/
		# The category project declaring the protocol of the factor's project.
	# /project/
		# The filesystem route to the directory containing the project.
	"""
	root: (routes.Selector) = None
	context: (typing.Optional[routes.Selector]) = None
	category: (typing.Optional[routes.Selector]) = None
	project: (routes.Selector) = None

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
	versioning: (str) = None
	controller: (str) = None
	contact: (str) = None

IReference = typing.NewType('IReference', str)
IReference.__qualname__ = __name__ + '.IReference'
ISymbols = typing.Mapping[(typing.Text,typing.Collection[IReference])]

IDocumentation = typing.Mapping[(str,"'http://if.fault.io/text'")]

from enum import Enum, unique

@unique
class Area(Enum):
	"""
	# The relative area that a factor exists within relative to another factor.

	# Whenever a relationship is designated between two Factors, it
	# is often reasonable to identify the locality so that decisions
	# can be made about how resolution is performed.
	"""

	factor = 0
	project = 1
	category = 2
	context = 3
	product = 4
	environment = 5
	system = 6

	# Primarily use to declare that a factor could not be found.
	unavailable = 255
del Enum, unique

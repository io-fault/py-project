"""
# Factored Product Data structures.

# [ Types ]

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

from fault.routes import library as libroutes

ignored = {
	'__pycache__',
	'__f_cache__',
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
	root: (libroutes.Route) = None
	context: (typing.Optional[libroutes.Route]) = None
	category: (typing.Optional[libroutes.Route]) = None
	project: (libroutes.Route) = None

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

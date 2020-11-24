"""
# Project materialization tools for instantiating polynomial-1 organized factor sets.
"""
import functools
import typing

from types import ModuleType
from dataclasses import dataclass

from ..context.types import Cell
from ..route.types import Segment
from ..text.types import Paragraph
from ..text import render
from ..system import files

from . import types

def _ktprotocol(iri):
	return (
		"! CONTEXT:\n\t"
			"/protocol/\n\t\t"
				"&<" + iri + ">\n\n"
	)

# The infrastructure.txt file.
_poly_infrastructure_header = _ktprotocol("http://if.fault.io/project/infrastructure")

# The project.txt file.
_poly_information_header = _ktprotocol("http://if.fault.io/project/information")

# Explicitly Typed Factors
_poly_factor_header = _ktprotocol("http://if.fault.io/project/factor")

def _literal(text):
	return "`" + text.replace("`", "``") + "`"

def _ref(format_id, *text):
	return "&<" + '/'.join(text) + ('#'+format_id if format_id is not None else "") + ">"

def infrastructure_text(infra):
	# Render infrastructure.txt from symbol records.
	for sym, frefs in infra:
		yield "/" + sym + "/"

		for ref in frefs:
			prefix = "\t- "

			if ref.method is not None:
				prefix += "(" + ref.method + ")"

			yield prefix + _ref(ref.isolation, ref.project, str(ref.factor))

def information_text(info, idsuffix=''):
	# Render project.txt from &types.Information instance.
	yield "/identifier/"
	yield "\t" + _literal(info.identifier + idsuffix)
	yield "/name/"
	yield "\t" + _literal(info.name)

	if info.abstract:
		yield "/abstract/"

		if isinstance(info.abstract, Paragraph):
			from ..text import render
			for x in render.paragraph(info.abstract):
				x[:0] = ("\t",)
				yield "".join(x)
		else:
			for x in info.abstract.split("\n"):
				yield "\t" + x

	if info.icon:
		yield "/icon/"
		for k, v in info.icon.items():
			yield ("\t- (%s)" %(k,)) + _literal(v)

	if info.authority:
		yield "/authority/"
		yield "\t" + _literal(info.authority)

	if info.contact:
		yield "/contact/"
		yield "\t" + _literal(info.contact)

def factor_text(type, symbols):
	# factor.txt files serialization for explicitly typed factors
	yield "/type/"
	yield "\t" + _literal(type)

	if symbols:
		yield "/symbols/"
		for s in symbols:
			yield "\t- " + _literal(s)

@dataclass
class Composition(object):
	"""
	# The core data for composing a factor.

	# [ Properties ]
	# /type/
		# The factor type.
	# /symbols/
		# The set of infrastructure symbols needed by the factor in order for
		# integration to succeed.
	# /sources/
		# A sequence of pairs defining the source name and the source content.

		# For polynomial-1, the source name is the extension that will be appended to
		# factor path if sources is a &Cell instance.
	"""
	type: str = None
	symbols: [str] = ()
	sources: typing.Sequence[typing.Tuple[str, typing.Union[str, bytes, files.Path, ModuleType]]] = ()

	@classmethod
	def indirect(Class, extension, source, type=None):
		"""
		# Define an indirectly typed factor's composition.

		# [ Parameters ]
		# /extension/
			# The dot extension that will be appended to the file to identify its type.
		# /source/
			# The data or reference to the data that will be used to initialize the file.
		# /type/
			# An optional factor type string. This is ignored by &plan as this is composing
			# an indirectly typed factor.
		"""
		return Class(type, (), Cell((extension, source)))

	@classmethod
	def explicit(Class, type, symbols, sources):
		"""
		# Define an explicitly typed factor's composition.

		# Equivalent to the default constructor with the exception that &symbols
		# and &sources are copied into a new list.

		# [ Parameters ]
		# /type/
			# The type to be assigned to the factor.
		# /symbols/
			# The set of symbols required by the factor for integration.
		# /sources/
			# The iterable producing pairs defining the relative paths and sources.
		"""
		return Class(type, list(symbols), list(sources))

@dataclass
class Parameters(object):
	"""
	# The necessary data for instantiating a project on the local system.

	# [ Properties ]
	# /information/
		# The &types.Information instance defining the project's identity.
	# /infrastructure/
		# The sequence of symbol identifier and &types.Reference sequence pairs
		# defining the external and internal dependencies of the project's factors.
	# /factors/
		# The set of factors that make up a project; a sequence of factor path-composition pairs.
	"""
	information: (types.Information) = None
	infrastructure: (typing.Sequence[typing.Tuple[str, typing.Sequence[types.Reference]]]) = None
	factors: (typing.Sequence[typing.Tuple[types.FactorPath, Composition]]) = ()

	@staticmethod
	def _index_factor_extensions(infra):
		# Working with an arbitrary iterator; scan for *.extension entries.
		for isym, isfactors in infra:
			if isym[:2] == '*.':
				for ref in isfactors:
					if ref.method == 'type':
						yield ref.factor, isym[2:]

	@classmethod
	def define(Class, information, infrastructure, soles=(), sets=(), extensions=()):
		"""
		# Create a parameter set for project instantiation applying the proper types
		# to factor entries, and translating factor types to file extensions for defining
		# &soles.

		# [ Parameters ]
		# /information/
			# The project identification.
		# /infrastructure/
			# The project symbols.
		# /soles/
			# A sequence of records defining single source factors that should be
			# presented at a path consistent with the factor path.
		# /sets/
			# A sequence of records defining factors with multiple sources.
		# /extensions/
			# A mapping of factor types to their corresponding filename suffix.
			# Extensions for factor types that are not present in &infrastructure
			# must be defined here.
		"""

		factors = []
		index = dict(extensions)

		# Infrastructure overrides anything in &extensions.
		# When the factor is on disk, only infrastructure is referenced; &extensions is lost.
		index.update(Class._index_factor_extensions(infrastructure))

		factors.extend([
			(types.factor@path, Composition.indirect(index[typ], src)) # Indirectly Typed Factors
			for path, typ, src in soles
		])

		factors.extend([
			(types.factor@path, Composition(typ, list(sym), list(src))) # Explicitly Typed Factors
			for path, typ, sym, src in sets
		])

		return Class(information, infrastructure, factors)

def plan(info, infra, factors, dimensions:typing.Sequence[str]=()):
	"""
	# Generate the filesystem paths paired with the data that should be placed
	# into that file relative to the project directory being materialized.
	"""
	seg = Segment.from_sequence(())

	if info:
		suffix = ''
		if dimensions:
			suffix = '//' + '/'.join(dimensions)

		yield (seg/'.protocol', info.identifier + suffix + " factors/polynomial-1")
		kt_body = "\n".join(information_text(info, suffix))
		yield (seg/'project.txt', _poly_information_header + kt_body + "\n")

	if infra:
		kt_body = "\n".join((infrastructure_text(infra)))
		yield (seg/'infrastructure.txt', _poly_infrastructure_header + kt_body + "\n")

	for path, c in factors:
		fpath = types.factor@path

		if isinstance(c.sources, Cell):
			# sole; indirectly typed factor.
			(ext, data), = c.sources # Only one source in cells.
			p = seg // fpath
			p = p.container / (p.identifier + '.' + ext)
			yield (p, data)
		else:
			# set; explicitly typed factor.
			if c.type == 'factor-index':
				# Special case for allowing directory initialization.
				yield (seg//fpath, None)
			else:
				p = (seg//fpath)
				yield (p/'factor.txt', _poly_factor_header + "\n".join(factor_text(c.type, c.symbols)) + "\n")

				p /= 'src'
				for rpath, data in c.sources:
					yield (p + rpath.split('/'), data)

def materialize(route, plans, encoding='utf-8', isinstance=isinstance):
	"""
	# Create a Project instance using the filesystem API's provided by &route
	# from the instructions produced by the given &plans.

	# ! WARNING:
		# Plan entries referring to files will cause the file content to be loaded entirely into memory.
		# Instantiating projects with large resources may require a side channel in order to achieve
		# reasonable memory usage.

		# The unconditional loading of file data is to accommmodate for in memory &route targets.

	# [ Parameters ]
	# /route/
		# A, usually filesystem, route to the directory that plan
		# segments will extend into.
	# /plans/
		# An iterable of pairs where the first item is the segment, relative path,
		# and the second is either the data to be stored or a &files.Path instance
		# referring to the data to be stored.
	"""

	for path, data in plans:
		target_file = (route//path)

		if data is None:
			if target_file.fs_type() != 'directory':
				target_file.fs_mkdir()
			continue
		elif isinstance(data, str):
			data = data.encode(encoding)
		elif isinstance(data, bytes):
			pass
		elif isinstance(data, ModuleType):
			data = files.Path.from_absolute(data.__file__).fs_load()
		else:
			# Presume filesystem reference.
			(target_file).fs_link_relative(data) # Symbolic linke.
			continue

		(target_file).fs_init(data)

def instantiate(project:Parameters, route, *dimensions:str):
	"""
	# Materialize the plan of the given &project using the &route as the root directory of the project.

	# [ Parameters ]
	# /project/
		# The set of parameters needed to plan and materialize a project.
	# /route/
		# A route to the root target directory.
	# /dimensions/
		# An optional sequence of strings that will be appended to the project's identifier.
	"""

	return materialize(route, plan(
		project.information,
		project.infrastructure,
		project.factors,
		dimensions=dimensions
	))
